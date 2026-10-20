"""Safe, read-only diagnostic utilities to test endpoint connectivity and report environment reality.

Logs and formats diagnostic probes for CelesTrak, WhereTheISS, and ARISS without
exposing secrets, modifying states, or executing long-running tasks.
"""

from __future__ import annotations

import logging
import time
from typing import Any
import requests

import backend.config as config
from backend import tle_service

# Safe fallbacks if running in partially reloaded environment
_DEFAULT_TIMEOUT = getattr(config, "HTTP_TIMEOUT", (3.0, 4.0))
_DEFAULT_USER_AGENT = getattr(
    config,
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (OrbitX-ISS-Tracker/1.2.1; educational; GITAM Aero Astro Club)",
)

logger = logging.getLogger("orbitx.diagnostics")


def probe_endpoint(
    url: str,
    timeout_s: float | tuple[float, float] | None = None,
    http_get: Any = None,
) -> dict[str, Any]:
    """Test a single endpoint independently and record comprehensive telemetry.

    Returns a dict with:
    - endpoint: clean display name
    - url: target url
    - timeout_s: configured timeout
    - elapsed_s: measured wall-clock time
    - status_code: HTTP status (or None on failure)
    - phase: "networking", "response_parsing", "validation", "success"
    - error: formatted error string (or None)
    - catalog_number: parsed NORAD ID (or None)
    - epoch_utc: ISO timestamp (or None)
    """
    getter = http_get or requests.get
    name = tle_service._endpoint_display_name(url)
    effective_timeout = timeout_s if timeout_s is not None else getattr(config, "HTTP_TIMEOUT", _DEFAULT_TIMEOUT)
    ua = getattr(config, "USER_AGENT", _DEFAULT_USER_AGENT)
    headers = {"User-Agent": ua, "Accept": "text/plain, */*"}
    start = time.monotonic()

    result: dict[str, Any] = {
        "endpoint": name,
        "url": url,
        "timeout_s": effective_timeout,
        "elapsed_s": 0.0,
        "status_code": None,
        "phase": "networking",
        "error": None,
        "catalog_number": None,
        "epoch_utc": None,
    }

    try:
        logger.info("Diagnostic probe starting for %s (timeout=%s)", name, effective_timeout)
        response = getter(url, timeout=effective_timeout, headers=headers)
        result["elapsed_s"] = round(time.monotonic() - start, 3)
        result["status_code"] = response.status_code
        response.raise_for_status()

        result["phase"] = "response_parsing"
        record = tle_service.parse_tle_text(response.text, source_url=url)

        result["phase"] = "success"
        result["catalog_number"] = record.catalog_number
        result["epoch_utc"] = record.epoch_utc.isoformat()
        result["tle_record"] = record
        logger.info("Diagnostic probe succeeded for %s in %.3fs", name, result["elapsed_s"])
        return result

    except requests.exceptions.Timeout:
        result["elapsed_s"] = round(time.monotonic() - start, 3)
        result["phase"] = "networking"
        result["error"] = f"Request timed out after {result['elapsed_s']:.2f}s"
        logger.warning("Diagnostic probe timeout on %s after %.3fs", name, result["elapsed_s"])
    except requests.exceptions.ConnectionError as exc:
        result["elapsed_s"] = round(time.monotonic() - start, 3)
        result["phase"] = "networking"
        result["error"] = f"Connection error ({type(exc).__name__})"
        logger.warning("Diagnostic probe connection error on %s: %s", name, exc)
    except requests.exceptions.HTTPError as exc:
        result["elapsed_s"] = round(time.monotonic() - start, 3)
        result["phase"] = "networking"
        status = getattr(exc.response, "status_code", "unknown")
        result["error"] = f"HTTP {status}"
        logger.warning("Diagnostic probe HTTP error on %s: %s", name, result["error"])
    except tle_service.TleParseError as exc:
        result["elapsed_s"] = round(time.monotonic() - start, 3)
        result["phase"] = "validation"
        result["error"] = f"TLE validation error: {exc}"
        logger.warning("Diagnostic probe TLE parse error on %s: %s", name, exc)
    except Exception as exc:
        result["elapsed_s"] = round(time.monotonic() - start, 3)
        result["phase"] = "unknown"
        result["error"] = f"Unexpected failure ({type(exc).__name__}: {exc})"
        logger.warning("Diagnostic probe unexpected failure on %s: %s", name, exc)

    return result


def probe_all_endpoints(
    endpoints: tuple[str, ...] | None = None,
    timeout_s: float | tuple[float, float] | None = None,
    http_get: Any = None,
) -> list[dict[str, Any]]:
    """Probe all candidate endpoints sequentially and return full results."""
    _fallback_urls = (
        getattr(config, "CELESTRAK_URL", "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE"),
        getattr(config, "ARISS_TLE_URL", "https://live.ariss.org/iss.txt"),
        getattr(config, "WHERETHEISS_TLE_URL", "https://api.wheretheiss.at/v1/satellites/25544/tles?format=text"),
        getattr(config, "CELESTRAK_FALLBACK_URL", "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"),
    )
    targets = endpoints or getattr(config, "DEFAULT_TLE_URLS", _fallback_urls)
    return [probe_endpoint(url, timeout_s=timeout_s, http_get=http_get) for url in targets]


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Geodesic distance between two (lat, lon) points on a spherical Earth (WGS84 mean radius 6371.0 km)."""
    import math
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians((lon2 - lon1 + 180.0) % 360.0 - 180.0)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return 6371.0 * c


def cross_check_live_position(
    calculated_lat: float,
    calculated_lon: float,
    calculated_alt_km: float,
    calculated_speed_km_s: float,
    when_utc: Any = None,
    timeout_s: float = 4.0,
    http_get: Any = None,
) -> dict[str, Any]:
    """Lightweight, non-blocking independent cross-check against WhereTheISS.at.

    Returns a dict with success, deltas, separation distance, and status.
    Never raises an exception; returns success=False on network or parsing error.
    """
    import json
    from datetime import datetime, timezone

    getter = http_get or requests.get
    ua = getattr(config, "USER_AGENT", _DEFAULT_USER_AGENT)
    headers = {"User-Agent": ua, "Accept": "application/json"}

    when = when_utc or datetime.now(timezone.utc)
    ts = int(when.timestamp())
    url = f"https://api.wheretheiss.at/v1/satellites/25544?timestamp={ts}"

    out: dict[str, Any] = {
        "success": False,
        "source": "WhereTheISS.at (Independent Public API)",
        "timestamp_utc": when.isoformat(),
        "ref_latitude": None,
        "ref_longitude": None,
        "ref_altitude_km": None,
        "ref_speed_km_s": None,
        "delta_latitude_deg": None,
        "delta_longitude_deg": None,
        "delta_altitude_km": None,
        "delta_speed_km_s": None,
        "separation_km": None,
        "error": None,
    }

    try:
        resp = getter(url, timeout=timeout_s, headers=headers)
        if resp.status_code != 200:
            out["error"] = f"HTTP {resp.status_code}"
            return out
        data = resp.json() if hasattr(resp, "json") and callable(resp.json) else json.loads(resp.text)
        ref_lat = float(data["latitude"])
        ref_lon = float(data["longitude"])
        ref_alt = float(data["altitude"])
        ref_speed = float(data["velocity"]) / 3600.0  # km/h to km/s

        sep_km = haversine_distance_km(calculated_lat, calculated_lon, ref_lat, ref_lon)
        d_lat = calculated_lat - ref_lat
        d_lon = (calculated_lon - ref_lon + 180.0) % 360.0 - 180.0
        d_alt = calculated_alt_km - ref_alt
        d_spd = calculated_speed_km_s - ref_speed

        out.update({
            "success": True,
            "ref_latitude": round(ref_lat, 4),
            "ref_longitude": round(ref_lon, 4),
            "ref_altitude_km": round(ref_alt, 2),
            "ref_speed_km_s": round(ref_speed, 4),
            "delta_latitude_deg": round(d_lat, 4),
            "delta_longitude_deg": round(d_lon, 4),
            "delta_altitude_km": round(d_alt, 2),
            "delta_speed_km_s": round(d_spd, 4),
            "separation_km": round(sep_km, 2),
        })
        return out
    except Exception as exc:
        out["error"] = str(exc)
        return out

