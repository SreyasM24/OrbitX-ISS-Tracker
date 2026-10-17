"""Orbital-element retrieval, parsing, caching and offline fallback.

This is the only module that performs network I/O. It never fabricates a result:
the returned :class:`~backend.models.OrbitalData` states whether the elements were
downloaded now (LIVE), read from the local cache (CACHED) or taken from the bundled
sample (SAMPLE), together with the true element epoch.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from backend import config
from backend.models import DataSource, Freshness, OrbitalData, TleRecord
from backend.validation import ensure_utc, tle_checksum_ok, utcnow

logger = logging.getLogger("orbitx.tle")


class TleParseError(ValueError):
    """The text is not a valid, correctly identified two-line element set."""


class TleFetchError(RuntimeError):
    """A network or HTTP failure while downloading elements."""


# --------------------------------------------------------------------------- parsing
def tle_epoch(line1: str) -> datetime:
    """Decode the epoch (UTC) from TLE line 1 (columns 19-32: YYDDD.DDDDDDDD)."""
    try:
        two_digit_year = int(line1[18:20])
        day_of_year = float(line1[20:32])
    except ValueError:
        raise TleParseError("Could not read the epoch from TLE line 1.") from None
    year = 2000 + two_digit_year if two_digit_year < 57 else 1900 + two_digit_year
    if not 1.0 <= day_of_year < 367.0:
        raise TleParseError(f"TLE epoch day-of-year {day_of_year} is out of range.")
    return datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1.0)


def parse_tle_text(
    text: str,
    expected_catalog_number: int = config.ISS_NORAD_ID,
    source_url: str = "",
) -> TleRecord:
    """Parse and validate TLE text (2-line or 3-line form, ``#`` comments allowed).

    Checks line numbers, lengths, checksums, catalogue number on both lines, the
    expected satellite identity and, when a name line is present, the name.
    """
    lines = [
        raw.rstrip()
        for raw in (text or "").splitlines()
        if raw.strip() and not raw.lstrip().startswith("#")
    ]
    candidate_pair: tuple[int, str, str] | None = None
    for index in range(len(lines) - 1):
        if lines[index].startswith("1 ") and lines[index + 1].startswith("2 "):
            l1, l2 = lines[index], lines[index + 1]
            try:
                cat1 = int(l1[2:7])
            except ValueError:
                continue
            if cat1 == expected_catalog_number:
                candidate_pair = (index, l1, l2)
                break
            elif candidate_pair is None:
                candidate_pair = (index, l1, l2)

    if candidate_pair is None:
        snippet = (text or "").strip().splitlines()[:1]
        hint = f" Server said: {snippet[0][:80]!r}." if snippet else ""
        raise TleParseError(f"No two-line element set found in the data.{hint}")

    index, line1, line2 = candidate_pair
    for number, line in ((1, line1), (2, line2)):
        if len(line) != 69:
            raise TleParseError(f"TLE line {number} must be 69 characters, got {len(line)}.")
        if not tle_checksum_ok(line):
            raise TleParseError(f"TLE line {number} failed its checksum (corrupted data?).")

    try:
        catalog_1, catalog_2 = int(line1[2:7]), int(line2[2:7])
    except ValueError:
        raise TleParseError("Could not read the catalogue number from the TLE.") from None
    if catalog_1 != catalog_2:
        raise TleParseError("TLE lines 1 and 2 describe different objects.")
    if catalog_1 != expected_catalog_number:
        raise TleParseError(
            f"Expected NORAD {expected_catalog_number} but the data is for NORAD {catalog_1}."
        )

    name = (
        lines[index - 1].strip()
        if index > 0 and not lines[index - 1].startswith(("1 ", "2 "))
        else ""
    )
    if name and not any(hint in name.upper() for hint in config.ISS_NAME_HINTS):
        raise TleParseError(f"Name {name!r} does not look like the ISS.")

    return TleRecord(
        name=name or f"NORAD {catalog_1}",
        line1=line1,
        line2=line2,
        catalog_number=catalog_1,
        epoch_utc=tle_epoch(line1),
        source_url=source_url,
    )


def load_sample_tle(path: Path | None = None) -> TleRecord:
    """Load the bundled offline sample TLE."""
    sample_path = path or config.SAMPLE_TLE_PATH
    try:
        return parse_tle_text(sample_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise TleParseError(f"Bundled sample TLE could not be read: {exc}") from exc


# ------------------------------------------------------------------------ freshness
def tle_age_days(tle: TleRecord, now: datetime) -> float:
    """Days between the element epoch and ``now`` (negative if epoch is in the future)."""
    return (ensure_utc(now) - tle.epoch_utc).total_seconds() / 86400.0


def classify_freshness(tle: TleRecord, now: datetime) -> Freshness:
    """FRESH / STALE / EXPIRED according to the thresholds in :mod:`backend.config`."""
    age = tle_age_days(tle, now)
    if age > config.STALE_EXPIRED_DAYS:
        return Freshness.EXPIRED
    if age > config.STALE_WARN_DAYS:
        return Freshness.STALE
    return Freshness.FRESH


def freshness_warning(tle: TleRecord, now: datetime) -> str | None:
    """A user-facing warning if the elements are stale, else None."""
    age = tle_age_days(tle, now)
    state = classify_freshness(tle, now)
    if state is Freshness.EXPIRED:
        return (
            f"Orbital elements are {age:.1f} days old. Positions and passes are "
            "illustrative only, not accurate tracking."
        )
    if state is Freshness.STALE:
        return (
            f"Orbital elements are {age:.1f} days old. Accuracy is degrading; treat "
            "predictions as approximate."
        )
    return None


def _endpoint_display_name(target_url: str) -> str:
    """Return a clean, safe label for an endpoint without sensitive query params."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(target_url)
        domain = parsed.netloc or target_url
        if "celestrak" in domain:
            if "GROUP=stations" in (parsed.query or ""):
                return "CelesTrak (stations group)"
            return "CelesTrak (NORAD 25544)"
        if "wheretheiss" in domain:
            return "WhereTheISS.at mirror"
        if "ariss" in domain:
            return "ARISS mirror"
        return domain
    except Exception:
        return target_url


# ---------------------------------------------------------------------------- fetch
def fetch_live_tle(
    url: str | None = None,
    timeout_s: float | None = None,
    http_get: Callable[..., requests.Response] | None = None,
) -> TleRecord:
    """Download and validate the ISS TLE. Raises TleFetchError or TleParseError."""
    getter = http_get or requests.get
    timeout = timeout_s or config.HTTP_TIMEOUT_S
    headers = {"User-Agent": config.USER_AGENT}

    # If an explicit URL was provided (custom override or test fixture), use only that URL.
    urls_to_try = [url] if url else list(config.DEFAULT_TLE_URLS)

    last_error: Exception | None = None
    attempt_errors: list[str] = []
    for target_url in urls_to_try:
        endpoint_name = _endpoint_display_name(target_url)
        start_time = time.monotonic()
        try:
            logger.info("Attempting TLE fetch from %s (timeout=%.1fs)", endpoint_name, timeout)
            response = getter(
                target_url,
                timeout=timeout,
                headers=headers,
            )
            elapsed = time.monotonic() - start_time
            response.raise_for_status()
            record = parse_tle_text(response.text, source_url=target_url)
            logger.info(
                "Successfully fetched TLE from %s in %.2fs (NORAD %d, epoch %s)",
                endpoint_name,
                elapsed,
                record.catalog_number,
                record.epoch_utc.isoformat(),
            )
            return record
        except requests.exceptions.Timeout:
            elapsed = time.monotonic() - start_time
            msg = f"{endpoint_name}: the request timed out (after {elapsed:.1f}s)"
            logger.warning("TLE fetch timeout on %s after %.2fs", endpoint_name, elapsed)
            attempt_errors.append(msg)
            last_error = TleFetchError("the request timed out")
        except requests.exceptions.ConnectionError as exc:
            elapsed = time.monotonic() - start_time
            msg = f"{endpoint_name}: no network connection"
            logger.warning("TLE connection error on %s: %s", endpoint_name, exc)
            attempt_errors.append(msg)
            last_error = TleFetchError("no network connection")
        except requests.exceptions.HTTPError as exc:
            elapsed = time.monotonic() - start_time
            status = getattr(exc.response, "status_code", "unknown")
            msg = f"{endpoint_name}: the server returned HTTP {status}"
            logger.warning("TLE HTTP error on %s: %s", endpoint_name, msg)
            attempt_errors.append(msg)
            last_error = TleFetchError(f"the server returned HTTP {status}")
        except requests.exceptions.RequestException as exc:
            elapsed = time.monotonic() - start_time
            msg = f"{endpoint_name}: request failed ({type(exc).__name__})"
            logger.warning("TLE request exception on %s: %s", endpoint_name, exc)
            attempt_errors.append(msg)
            last_error = TleFetchError(f"request failed ({type(exc).__name__})")
        except TleParseError as exc:
            elapsed = time.monotonic() - start_time
            msg = f"{endpoint_name}: {exc}"
            logger.warning("TLE parse error on %s: %s", endpoint_name, exc)
            attempt_errors.append(msg)
            last_error = exc

    if last_error is not None:
        if len(attempt_errors) > 1:
            summary = "; ".join(attempt_errors)
            raise TleFetchError(f"{last_error} (all {len(attempt_errors)} endpoints failed: {summary})")
        raise last_error
    raise TleFetchError("no data received")


# ---------------------------------------------------------------------------- cache
def write_cache(tle: TleRecord, retrieved_at: datetime, url: str, path: Path) -> None:
    """Atomically store a successful download. Raises OSError on failure."""
    payload = {
        "name": tle.name,
        "line1": tle.line1,
        "line2": tle.line2,
        "retrieved_at_utc": ensure_utc(retrieved_at).isoformat(),
        "source_url": url,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temp, path)


def read_cache(path: Path) -> tuple[TleRecord, datetime] | None:
    """Return ``(tle, retrieved_at_utc)`` from the cache, or None if absent.

    Raises TleParseError if a cache file exists but is unusable.
    """
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        source_url = payload.get("source_url", "")
        tle = parse_tle_text(
            f"{payload['name']}\n{payload['line1']}\n{payload['line2']}",
            source_url=source_url,
        )
        retrieved = ensure_utc(datetime.fromisoformat(payload["retrieved_at_utc"]))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise TleParseError(f"cache file is unusable ({exc})") from exc
    return tle, retrieved


def _provider_label(source_url: str) -> tuple[str, str]:
    """Return (label, description) based on the TLE source URL."""
    lowered = source_url.lower()
    if "celestrak" in lowered:
        return "CelesTrak GP data (live download)", "Fetched directly from CelesTrak."
    if "wheretheiss" in lowered:
        return "WhereTheISS.at (live mirror)", "Fetched from WhereTheISS.at live TLE mirror."
    if "ariss" in lowered:
        return "ARISS (live mirror)", "Fetched from ARISS live TLE mirror."
    return "Live TLE download", f"Fetched from {source_url}."


def _cached_provider_label(source_url: str) -> str:
    """Return cache label based on the original TLE source URL."""
    lowered = source_url.lower()
    if "celestrak" in lowered:
        return "CelesTrak (cached download)"
    if "wheretheiss" in lowered:
        return "WhereTheISS.at (cached download)"
    if "ariss" in lowered:
        return "ARISS (cached download)"
    return "Cached download"


# ------------------------------------------------------------------------ orchestrator
def get_orbital_data(
    *,
    force_refresh: bool = False,
    offline: bool = False,
    now: datetime | None = None,
    http_get: Callable[..., requests.Response] | None = None,
    cache_path: Path | None = None,
    url: str | None = None,
    sample_path: Path | None = None,
) -> OrbitalData:
    """Obtain orbital elements with an honest provenance label.

    Order: fresh cache (unless ``force_refresh``) -> download -> any cache -> sample.
    ``offline=True`` (or ``ORBITX_OFFLINE=1``) skips the network entirely.
    """
    current = ensure_utc(now) if now else utcnow()
    cache_file = cache_path or config.CACHE_PATH
    offline = offline or config.OFFLINE_ENV_FLAG
    warnings: list[str] = []

    cached: tuple[TleRecord, datetime] | None = None
    try:
        cached = read_cache(cache_file)
    except TleParseError as exc:
        warnings.append(f"Ignoring local cache: {exc}.")

    if cached and not offline and not force_refresh:
        age_s = (current - cached[1]).total_seconds()
        if 0 <= age_s < config.CACHE_TTL_S:
            cache_label = _cached_provider_label(cached[0].source_url)
            return _finish(
                cached[0], DataSource.CACHED, cached[1], cache_label,
                f"Using the download from {_age_text(age_s)} ago (not re-downloading "
                "within the 2-hour courtesy window; press Refresh to force).",
                warnings, current,
            )

    if not offline:
        try:
            tle = fetch_live_tle(url, http_get=http_get)
        except (TleFetchError, TleParseError) as exc:
            warnings.append(f"Live download failed: {exc}.")
        else:
            actual_url = tle.source_url or (url or config.CELESTRAK_URL)
            try:
                write_cache(tle, current, actual_url, cache_file)
            except OSError as exc:
                warnings.append(f"Could not write the local cache: {exc}.")
            label, desc = _provider_label(actual_url)
            return _finish(
                tle, DataSource.LIVE, current, label,
                desc, warnings, current,
            )

    if cached:
        reason = "Offline mode" if offline else "Live download unavailable"
        age_s = (current - cached[1]).total_seconds()
        cache_label = _cached_provider_label(cached[0].source_url)
        return _finish(
            cached[0], DataSource.CACHED, cached[1], cache_label,
            f"{reason}: using the last successful download from {_age_text(age_s)} ago.",
            warnings, current,
        )

    sample = load_sample_tle(sample_path)
    reason = "Offline mode" if offline else "No live data and no cache"
    return _finish(
        sample, DataSource.SAMPLE, None, "Bundled sample (data/sample_iss.tle)",
        f"{reason}: using the bundled sample. This is NOT live tracking.",
        warnings, current,
    )


def _finish(
    tle: TleRecord,
    source: DataSource,
    retrieved: datetime | None,
    label: str,
    message: str,
    warnings: list[str],
    now: datetime,
) -> OrbitalData:
    notes = list(warnings)
    stale = freshness_warning(tle, now)
    if stale:
        notes.append(stale)
    return OrbitalData(tle, source, retrieved, label, message, tuple(notes))


def _age_text(seconds: float) -> str:
    minutes = max(seconds, 0) / 60
    if minutes < 90:
        return f"{minutes:.0f} min"
    hours = minutes / 60
    return f"{hours:.1f} h" if hours < 48 else f"{hours / 24:.1f} days"
