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
from typing import Any

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


def _temp_cache_fallback_path() -> Path:
    import tempfile
    return Path(tempfile.gettempdir()) / ".orbitx_cache" / "iss_tle.json"


def _endpoint_display_name(target_url: str) -> str:
    """Return a clean, safe label for an endpoint without sensitive query params."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(target_url)
        domain = parsed.netloc or target_url
        if "celestrak" in domain:
            if "group=stations" in (parsed.query or "").lower():
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
    timeout: tuple[float, float] | float | None = None,
    http_get: Callable[..., requests.Response] | None = None,
    out_diagnostics: list[dict[str, Any]] | None = None,
    overall_budget_s: float | None = None,
    *,
    timeout_s: float | None = None,
) -> TleRecord:
    """Download and validate the ISS TLE with deterministic failover. Raises TleFetchError or TleParseError."""
    getter = http_get or requests.get
    chosen_timeout = timeout if timeout is not None else timeout_s
    req_timeout = chosen_timeout if chosen_timeout is not None else config.HTTP_TIMEOUT
    headers = {
        "User-Agent": config.USER_AGENT,
        "Accept": "text/plain, */*",
    }

    # If an explicit URL was provided (custom override or test fixture), use only that URL.
    urls_to_try = [url] if url else list(config.DEFAULT_TLE_URLS)

    last_error: Exception | None = None
    attempt_errors: list[str] = []
    total_start = time.monotonic()
    max_budget = overall_budget_s or config.MAX_TOTAL_FETCH_BUDGET_S

    for target_url in urls_to_try:
        if (time.monotonic() - total_start) >= max_budget:
            budget_msg = f"Overall fetch budget of {max_budget:.1f}s exceeded before attempting remaining endpoints"
            logger.warning(budget_msg)
            attempt_errors.append(budget_msg)
            break

        endpoint_name = _endpoint_display_name(target_url)
        start_time = time.monotonic()
        diag_entry: dict[str, Any] = {
            "endpoint": endpoint_name,
            "url": target_url,
            "timeout_s": req_timeout,
            "elapsed_s": 0.0,
            "status_code": None,
            "phase": "networking",
            "error": None,
        }
        try:
            logger.info("Attempting TLE fetch from %s (timeout=%s)", endpoint_name, req_timeout)
            response = getter(
                target_url,
                timeout=req_timeout,
                headers=headers,
            )
            elapsed = time.monotonic() - start_time
            diag_entry["elapsed_s"] = round(elapsed, 3)
            diag_entry["status_code"] = response.status_code
            response.raise_for_status()
            diag_entry["phase"] = "response_parsing"
            record = parse_tle_text(response.text, source_url=target_url)
            diag_entry["phase"] = "success"
            logger.info(
                "Successfully fetched TLE from %s in %.2fs (NORAD %d, epoch %s)",
                endpoint_name,
                elapsed,
                record.catalog_number,
                record.epoch_utc.isoformat(),
            )
            if out_diagnostics is not None:
                out_diagnostics.append(diag_entry)
            return record
        except requests.exceptions.ConnectTimeout:
            elapsed = time.monotonic() - start_time
            diag_entry["elapsed_s"] = round(elapsed, 3)
            diag_entry["phase"] = "networking"
            diag_entry["error"] = f"Connection timed out after {elapsed:.2f}s"
            if out_diagnostics is not None:
                out_diagnostics.append(diag_entry)
            msg = f"{endpoint_name}: connection timed out after {elapsed:.1f}s"
            logger.warning("TLE connection timeout on %s after %.2fs", endpoint_name, elapsed)
            attempt_errors.append(msg)
            last_error = TleFetchError(msg)
        except requests.exceptions.ReadTimeout:
            elapsed = time.monotonic() - start_time
            diag_entry["elapsed_s"] = round(elapsed, 3)
            diag_entry["phase"] = "networking"
            diag_entry["error"] = f"Read timed out after {elapsed:.2f}s"
            if out_diagnostics is not None:
                out_diagnostics.append(diag_entry)
            msg = f"{endpoint_name}: read timed out after {elapsed:.1f}s"
            logger.warning("TLE read timeout on %s after %.2fs", endpoint_name, elapsed)
            attempt_errors.append(msg)
            last_error = TleFetchError(msg)
        except requests.exceptions.Timeout:
            elapsed = time.monotonic() - start_time
            diag_entry["elapsed_s"] = round(elapsed, 3)
            diag_entry["phase"] = "networking"
            diag_entry["error"] = f"Request timed out after {elapsed:.2f}s"
            if out_diagnostics is not None:
                out_diagnostics.append(diag_entry)
            msg = f"{endpoint_name}: request timed out after {elapsed:.1f}s"
            logger.warning("TLE fetch timeout on %s after %.2fs", endpoint_name, elapsed)
            attempt_errors.append(msg)
            last_error = TleFetchError(msg)
        except requests.exceptions.ConnectionError as exc:
            elapsed = time.monotonic() - start_time
            diag_entry["elapsed_s"] = round(elapsed, 3)
            diag_entry["phase"] = "networking"
            diag_entry["error"] = f"Connection error ({type(exc).__name__})"
            if out_diagnostics is not None:
                out_diagnostics.append(diag_entry)
            msg = f"{endpoint_name}: no network connection ({type(exc).__name__})"
            logger.warning("TLE connection error on %s: %s", endpoint_name, exc)
            attempt_errors.append(msg)
            last_error = TleFetchError(msg)
        except requests.exceptions.HTTPError as exc:
            elapsed = time.monotonic() - start_time
            status = getattr(exc.response, "status_code", "unknown")
            diag_entry["elapsed_s"] = round(elapsed, 3)
            diag_entry["status_code"] = status if isinstance(status, int) else None
            diag_entry["phase"] = "networking"
            diag_entry["error"] = f"HTTP {status}"
            if out_diagnostics is not None:
                out_diagnostics.append(diag_entry)
            msg = f"{endpoint_name}: server returned HTTP {status}"
            logger.warning("TLE HTTP error on %s: %s", endpoint_name, msg)
            attempt_errors.append(msg)
            last_error = TleFetchError(msg)
        except requests.exceptions.RequestException as exc:
            elapsed = time.monotonic() - start_time
            diag_entry["elapsed_s"] = round(elapsed, 3)
            diag_entry["phase"] = "networking"
            diag_entry["error"] = f"Request error ({type(exc).__name__})"
            if out_diagnostics is not None:
                out_diagnostics.append(diag_entry)
            msg = f"{endpoint_name}: request failed ({type(exc).__name__})"
            logger.warning("TLE request exception on %s: %s", endpoint_name, exc)
            attempt_errors.append(msg)
            last_error = TleFetchError(msg)
        except TleParseError as exc:
            elapsed = time.monotonic() - start_time
            diag_entry["elapsed_s"] = round(elapsed, 3)
            diag_entry["phase"] = "validation"
            diag_entry["error"] = f"Parse/validation error: {exc}"
            if out_diagnostics is not None:
                out_diagnostics.append(diag_entry)
            msg = f"{endpoint_name}: {exc}"
            logger.warning("TLE parse error on %s: %s", endpoint_name, exc)
            attempt_errors.append(msg)
            last_error = exc

    if last_error is not None:
        if len(attempt_errors) > 1:
            summary = "; ".join(attempt_errors)
            raise TleFetchError(f"All {len(attempt_errors)} endpoints failed: {summary}")
        raise last_error
    raise TleFetchError("No data received from any endpoint")


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
    targets = [path]
    if path == config.CACHE_PATH:
        targets.append(_temp_cache_fallback_path())

    last_exc: OSError | None = None
    for target in targets:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_suffix(".tmp")
            temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            os.replace(temp, target)
            return
        except OSError as exc:
            last_exc = exc
            if target == path and path != config.CACHE_PATH:
                raise
            continue
    if last_exc:
        raise last_exc


def read_cache(path: Path) -> tuple[TleRecord, datetime] | None:
    """Return ``(tle, retrieved_at_utc)`` from the cache, or None if absent.

    Raises TleParseError if a cache file exists but is unusable.
    """
    targets = [path]
    if path == config.CACHE_PATH:
        targets.append(_temp_cache_fallback_path())

    chosen_path: Path | None = None
    for target in targets:
        if target.exists():
            chosen_path = target
            break
    if chosen_path is None:
        return None
    try:
        payload = json.loads(chosen_path.read_text(encoding="utf-8"))
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
        if "group=stations" in lowered:
            return "CelesTrak stations feed (live download)", "Fetched from CelesTrak stations group."
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
        if "group=stations" in lowered:
            return "CelesTrak stations (cached download)"
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

    diagnostics_log: list[dict[str, Any]] = []

    if cached and not offline and not force_refresh:
        age_s = (current - cached[1]).total_seconds()
        if 0 <= age_s < config.CACHE_TTL_S:
            cache_label = _cached_provider_label(cached[0].source_url)
            return _finish(
                cached[0], DataSource.CACHED, cached[1], cache_label,
                f"Using the download from {_age_text(age_s)} ago (not re-downloading "
                "within the 2-hour courtesy window; press Refresh to force).",
                warnings, current,
                diagnostics=tuple(diagnostics_log),
                cache_used=True,
                last_attempt_utc=current,
            )

    if not offline:
        try:
            tle = fetch_live_tle(url, http_get=http_get, out_diagnostics=diagnostics_log)
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
                diagnostics=tuple(diagnostics_log),
                cache_used=False,
                last_attempt_utc=current,
            )

    if cached:
        reason = "Offline mode" if offline else "Live download unavailable"
        age_s = (current - cached[1]).total_seconds()
        cache_label = _cached_provider_label(cached[0].source_url)
        return _finish(
            cached[0], DataSource.CACHED, cached[1], cache_label,
            f"{reason}: using the last successful download from {_age_text(age_s)} ago.",
            warnings, current,
            diagnostics=tuple(diagnostics_log),
            cache_used=True,
            last_attempt_utc=current,
        )

    sample = load_sample_tle(sample_path)
    reason = "Offline mode" if offline else "No live data and no cache"
    return _finish(
        sample, DataSource.SAMPLE, None, "Bundled sample (data/sample_iss.tle)",
        f"{reason}: using the bundled sample. This is NOT live tracking.",
        warnings, current,
        diagnostics=tuple(diagnostics_log),
        cache_used=False,
        last_attempt_utc=current,
    )


def _finish(
    tle: TleRecord,
    source: DataSource,
    retrieved: datetime | None,
    label: str,
    message: str,
    warnings: list[str],
    now: datetime,
    diagnostics: tuple[dict[str, Any], ...] = (),
    cache_used: bool = False,
    last_attempt_utc: datetime | None = None,
) -> OrbitalData:
    notes = list(warnings)
    stale = freshness_warning(tle, now)
    if stale:
        notes.append(stale)
    return OrbitalData(
        tle,
        source,
        retrieved,
        label,
        message,
        tuple(notes),
        diagnostics=diagnostics,
        cache_used=cache_used,
        last_attempt_utc=last_attempt_utc,
    )


def _age_text(seconds: float) -> str:
    minutes = max(seconds, 0) / 60
    if minutes < 90:
        return f"{minutes:.0f} min"
    hours = minutes / 60
    return f"{hours:.1f} h" if hours < 48 else f"{hours / 24:.1f} days"
