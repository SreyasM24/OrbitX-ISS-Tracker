"""Pure orbital calculations (no network, no Streamlit).

Pipeline: TLE -> SGP4 (via Skyfield ``EarthSatellite``) -> geocentric position in the
inertial GCRS frame (Skyfield converts from SGP4's TEME) -> WGS84 geodetic sub-satellite
point (latitude, longitude) plus altitude above the ellipsoid. Note that Skyfield's
``subpoint_of(...).elevation`` is always 0 (the point lies *on* the surface); the
satellite's altitude comes from ``wgs84.height_of``.

Speed reference frame: ``speed_km_s`` is the magnitude of the GCRS velocity, i.e. the
speed relative to Earth's centre in a non-rotating frame (about 7.66 km/s for the ISS).
It is the *orbital* speed, not the ground speed of the sub-satellite point (~7.2 km/s
relative to the rotating Earth surface).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from skyfield.api import EarthSatellite, load, wgs84
from skyfield.timelib import Timescale

from orbitx import config
from orbitx.models import SatellitePosition, TleRecord
from orbitx.validation import ensure_utc, validate_track_request

TRACK_COLUMNS = ["time_utc", "latitude_deg", "longitude_deg", "altitude_km", "speed_km_s"]

_timescale: Timescale | None = None


class PredictionError(RuntimeError):
    """Propagation failed or produced no valid points."""


def get_timescale() -> Timescale:
    """Shared Skyfield timescale (uses data bundled with Skyfield; no download)."""
    global _timescale
    if _timescale is None:
        _timescale = load.timescale()
    return _timescale


def build_satellite(tle: TleRecord) -> EarthSatellite:
    """Create one Skyfield satellite to share between all calculations."""
    try:
        return EarthSatellite(tle.line1, tle.line2, tle.name, get_timescale())
    except (ValueError, RuntimeError) as exc:
        raise PredictionError(f"Could not initialise the satellite model: {exc}") from exc


def compute_position(satellite: EarthSatellite, when_utc: datetime) -> SatellitePosition:
    """Sub-satellite point, altitude and orbital speed at one UTC instant."""
    when = ensure_utc(when_utc)
    try:
        geocentric = satellite.at(get_timescale().from_datetime(when))
        subpoint = wgs84.subpoint_of(geocentric)
        speed = float(np.linalg.norm(geocentric.velocity.km_per_s))
        values = (
            subpoint.latitude.degrees,
            subpoint.longitude.degrees,
            wgs84.height_of(geocentric).km,
        )
    except (ValueError, RuntimeError) as exc:
        raise PredictionError(f"Propagation failed at {when.isoformat()}: {exc}") from exc
    lat, lon, alt = (float(v) for v in values)
    if not all(math.isfinite(v) for v in (lat, lon, alt, speed)):
        raise PredictionError(f"Propagation returned invalid numbers at {when.isoformat()}.")
    return SatellitePosition(when, lat, lon, alt, speed)


def predict_track(
    satellite: EarthSatellite,
    start_utc: datetime,
    duration_min: float,
    step_s: float = 60.0,
) -> pd.DataFrame:
    """Predict the sub-satellite track from ``start_utc`` for ``duration_min`` minutes.

    Returns a DataFrame with :data:`TRACK_COLUMNS`. Points where SGP4 fails are dropped;
    if nothing valid remains a :class:`PredictionError` is raised.
    """
    duration, step = validate_track_request(duration_min, step_s)
    start = ensure_utc(start_utc)
    count = int(duration * 60 // step) + 1
    times = [start + timedelta(seconds=i * step) for i in range(count)]
    try:
        with np.errstate(invalid="ignore"):
            geocentric = satellite.at(get_timescale().from_datetimes(times))
            subpoint = wgs84.subpoint_of(geocentric)
            frame = pd.DataFrame(
                {
                    "time_utc": pd.to_datetime(times, utc=True),
                    "latitude_deg": subpoint.latitude.degrees,
                    "longitude_deg": subpoint.longitude.degrees,
                    "altitude_km": wgs84.height_of(geocentric).km,
                    "speed_km_s": np.linalg.norm(geocentric.velocity.km_per_s, axis=0),
                }
            )
    except (ValueError, RuntimeError) as exc:
        raise PredictionError(f"Propagation failed: {exc}") from exc
    return clean_track(frame)


def clean_track(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop non-finite rows; raise PredictionError if no valid point remains."""
    numeric = frame[TRACK_COLUMNS[1:]].to_numpy(dtype=float)
    valid = np.isfinite(numeric).all(axis=1)
    cleaned = frame.loc[valid].reset_index(drop=True)
    if cleaned.empty:
        raise PredictionError(
            "No valid positions could be computed. The orbital elements may be invalid "
            "or too far from their epoch."
        )
    return cleaned


def split_track_segments(frame: pd.DataFrame) -> list[list[tuple[float, float]]]:
    """Split a track into ``(lat, lon)`` polylines that never cross the antimeridian.

    When consecutive points jump by more than 180 degrees of longitude, the line is cut
    and each side is extended to +/-180 by linear interpolation of latitude, so the map
    shows two clean lines instead of one line across the whole world.
    """
    lats = frame["latitude_deg"].to_numpy(dtype=float)
    lons = frame["longitude_deg"].to_numpy(dtype=float)
    if len(lats) == 0:
        return []
    segments: list[list[tuple[float, float]]] = [[(lats[0], lons[0])]]
    for i in range(1, len(lats)):
        lon_prev, lon_cur = lons[i - 1], lons[i]
        if abs(lon_cur - lon_prev) > 180.0:
            edge = 180.0 if lon_prev > 0 else -180.0  # edge the track leaves through
            # Unwrap the current longitude next to the previous one, then interpolate.
            unwrapped = lon_cur + 360.0 if lon_prev > 0 else lon_cur - 360.0
            fraction = (edge - lon_prev) / (unwrapped - lon_prev)
            lat_cross = lats[i - 1] + fraction * (lats[i] - lats[i - 1])
            segments[-1].append((lat_cross, edge))
            segments.append([(lat_cross, -edge), (lats[i], lon_cur)])
        else:
            segments[-1].append((lats[i], lon_cur))
    return segments


def insert_antimeridian_gaps(frame: pd.DataFrame) -> pd.DataFrame:
    """Insert NaN rows where longitude wraps so Plotly lines break instead of sweeping."""
    lons = frame["longitude_deg"].to_numpy(dtype=float)
    jumps = np.where(np.abs(np.diff(lons)) > 180.0)[0]
    if len(jumps) == 0:
        return frame
    pieces: list[pd.DataFrame] = []
    previous = 0
    for jump in jumps:
        pieces.append(frame.iloc[previous : jump + 1])
        gap = pd.DataFrame({column: [np.nan] for column in frame.columns})
        gap["time_utc"] = frame["time_utc"].iloc[jump] + (
            frame["time_utc"].iloc[jump + 1] - frame["time_utc"].iloc[jump]
        ) / 2
        pieces.append(gap)
        previous = jump + 1
    pieces.append(frame.iloc[previous:])
    return pd.concat(pieces, ignore_index=True)


def epoch_distance_days(tle: TleRecord, when_utc: datetime) -> float:
    """Absolute days between ``when_utc`` and the element epoch."""
    return abs((ensure_utc(when_utc) - tle.epoch_utc).total_seconds()) / 86400.0


def epoch_distance_warning(tle: TleRecord, when_utc: datetime) -> str | None:
    """Warn when asking for a time far from the element epoch (SGP4 error grows)."""
    days = epoch_distance_days(tle, when_utc)
    if days > config.PREDICTION_DISTANCE_WARN_DAYS:
        return (
            f"The requested time is {days:.1f} days from the element epoch. SGP4 error "
            "grows with distance from the epoch; treat results as illustrative."
        )
    return None
