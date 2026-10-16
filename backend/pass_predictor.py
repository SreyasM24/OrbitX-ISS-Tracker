"""ISS pass prediction for a ground observer using Skyfield's ``find_events``.

A "pass" here means the satellite is geometrically above a chosen elevation threshold
(rise -> culmination -> set). That does NOT mean it is visible to the naked eye: that
also needs the satellite to be sunlit while the observer is in darkness, and clear sky.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import NamedTuple

import pandas as pd
from skyfield.api import EarthSatellite, wgs84

from backend import config
from backend.formatting import compass_point
from backend.models import Observer, SatellitePass
from backend.orbital_engine import PredictionError, get_timescale
from backend.validation import (
    ValidationError,
    ensure_utc,
    validate_latitude,
    validate_longitude,
    validate_min_elevation,
    validate_observer_name,
    validate_search_window,
)

RISE, CULMINATE, SET = 0, 1, 2


class PassEvent(NamedTuple):
    """One Skyfield event: kind is 0 (rise), 1 (culmination) or 2 (set)."""

    time_utc: datetime
    kind: int
    elevation_deg: float
    azimuth_deg: float


def make_observer(name: object, latitude_deg: object, longitude_deg: object,
                  elevation_m: float = 0.0) -> Observer:
    """Validate raw user input and build an :class:`Observer`."""
    return Observer(
        name=validate_observer_name(name),
        latitude_deg=validate_latitude(latitude_deg),
        longitude_deg=validate_longitude(longitude_deg),
        elevation_m=float(elevation_m),
    )


def observer_from_text(name: object, latitude_text: object, longitude_text: object) -> Observer:
    """Build an :class:`Observer` from text-box input (blank or partial entries are errors).

    Raises :class:`~backend.validation.ValidationError` with a message fit for the UI.
    """
    lat = str(latitude_text if latitude_text is not None else "").strip()
    lon = str(longitude_text if longitude_text is not None else "").strip()
    if not lat:
        raise ValidationError("Latitude is empty. Enter a number between -90 and 90.")
    if not lon:
        raise ValidationError("Longitude is empty. Enter a number between -180 and 180.")
    return make_observer(name, lat, lon)


def assemble_passes(events: list[PassEvent], min_elevation_deg: float) -> list[SatellitePass]:
    """Group a time-ordered event list into passes, tolerating truncated windows.

    - A leading culmination/set means the pass began before the window: ``rise`` is None.
    - A trailing rise/culmination means the pass continues beyond the window: ``set`` is None.
    - A culmination below the threshold outside any pass is ignored.
    """
    passes: list[SatellitePass] = []
    rise: PassEvent | None = None
    culmination: PassEvent | None = None

    def flush(set_event: PassEvent | None) -> None:
        nonlocal rise, culmination
        passes.append(
            SatellitePass(
                rise_time_utc=rise.time_utc if rise else None,
                culmination_time_utc=culmination.time_utc if culmination else None,
                set_time_utc=set_event.time_utc if set_event else None,
                max_elevation_deg=culmination.elevation_deg if culmination else None,
                rise_azimuth_deg=rise.azimuth_deg if rise else None,
                set_azimuth_deg=set_event.azimuth_deg if set_event else None,
            )
        )
        rise = culmination = None

    for event in sorted(events, key=lambda e: e.time_utc):
        if event.kind == RISE:
            if rise or culmination:  # previous pass never closed; report it as-is
                flush(None)
            rise = event
        elif event.kind == CULMINATE:
            if rise is None and event.elevation_deg < min_elevation_deg - 1e-6:
                continue
            culmination = event
        elif event.kind == SET:
            flush(event)
    if rise or culmination:
        flush(None)
    return passes


def find_passes(
    satellite: EarthSatellite,
    observer: Observer,
    start_utc: datetime,
    search_hours: float,
    min_elevation_deg: float = config.DEFAULT_MIN_ELEVATION_DEG,
) -> list[SatellitePass]:
    """Find passes above ``min_elevation_deg`` within ``[start, start + search_hours]``.

    Returns an empty list when no pass exists (a normal result, not an error).
    """
    start, end = validate_search_window(start_utc, search_hours)
    min_elev = validate_min_elevation(min_elevation_deg)
    lat = validate_latitude(observer.latitude_deg)
    lon = validate_longitude(observer.longitude_deg)

    ts = get_timescale()
    site = wgs84.latlon(lat, lon, elevation_m=observer.elevation_m)
    try:
        times, kinds = satellite.find_events(
            site, ts.from_datetime(start), ts.from_datetime(end), altitude_degrees=min_elev
        )
        if len(kinds) == 0:
            return []
        altitude, azimuth, _ = (satellite - site).at(times).altaz()
    except (ValueError, RuntimeError) as exc:
        raise PredictionError(f"Pass search failed: {exc}") from exc

    events = [
        PassEvent(ensure_utc(t.utc_datetime()), int(kind), float(alt), float(az))
        for t, kind, alt, az in zip(times, kinds, altitude.degrees, azimuth.degrees)
    ]
    return assemble_passes(events, min_elev)


ZONES: dict[str, timezone] = {"UTC": timezone.utc, "IST": config.IST}


def passes_to_frame(
    passes: list[SatellitePass], zones: tuple[str, ...] = ("UTC", "IST")
) -> pd.DataFrame:
    """Tabulate passes. Every time column names its zone, e.g. ``Rise (IST)``.

    ``zones`` is any non-empty subset of ``("UTC", "IST")`` (IST = UTC+05:30, display
    only; all calculation is in UTC). Missing events become blank cells, never guesses.
    """
    unknown = [zone for zone in zones if zone not in ZONES]
    if unknown or not zones:
        raise ValueError(f"zones must be a non-empty subset of {tuple(ZONES)}, got {zones!r}")
    rows = []
    for item in passes:
        row: dict[str, object] = {}
        for label, moment in (
            ("Rise", item.rise_time_utc),
            ("Peak", item.culmination_time_utc),
            ("Set", item.set_time_utc),
        ):
            for zone in zones:
                row[f"{label} ({zone})"] = _fmt(moment, ZONES[zone])
        row["Max elevation (deg)"] = (
            round(item.max_elevation_deg, 1) if item.max_elevation_deg is not None else None
        )
        row["Duration (min)"] = (
            round(item.duration_s / 60, 1) if item.duration_s is not None else None
        )
        row["Rises toward"] = compass_point(item.rise_azimuth_deg)
        row["Sets toward"] = compass_point(item.set_azimuth_deg)
        row["Note"] = pass_note(item)
        rows.append(row)
    return pd.DataFrame(rows)


def pass_note(item: SatellitePass) -> str:
    """Explain truncated passes in words."""
    if item.rise_time_utc is None:
        return "Already in progress at window start"
    if item.set_time_utc is None:
        return "Continues past window end"
    return ""


def _fmt(moment: datetime | None, tz: timezone = timezone.utc) -> str | None:
    if moment is None:
        return None
    return ensure_utc(moment).astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
