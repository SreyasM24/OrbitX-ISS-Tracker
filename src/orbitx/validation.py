"""Input validation helpers. Every validator raises :class:`ValidationError`."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from orbitx import config


class ValidationError(ValueError):
    """User-facing validation failure with an actionable message."""


def ensure_utc(moment: datetime) -> datetime:
    """Return ``moment`` as a timezone-aware UTC datetime.

    Naive datetimes are rejected rather than guessed: silently assuming a zone is a
    classic source of hours-long prediction errors.
    """
    if not isinstance(moment, datetime):
        raise ValidationError("Time must be a datetime.")
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValidationError("Time must be timezone-aware (use UTC).")
    return moment.astimezone(timezone.utc)


def utcnow() -> datetime:
    """Current time as timezone-aware UTC."""
    return datetime.now(timezone.utc)


def _finite_float(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValidationError(f"{label} must be a number.")
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValidationError(f"{label} must be a number.") from None
    if not math.isfinite(number):
        raise ValidationError(f"{label} must be a finite number.")
    return number


def validate_latitude(value: object) -> float:
    """Latitude in degrees, -90..90."""
    lat = _finite_float(value, "Latitude")
    if not -90.0 <= lat <= 90.0:
        raise ValidationError("Latitude must be between -90 and 90 degrees.")
    return lat


def validate_longitude(value: object) -> float:
    """Longitude in degrees east, -180..180."""
    lon = _finite_float(value, "Longitude")
    if not -180.0 <= lon <= 180.0:
        raise ValidationError("Longitude must be between -180 and 180 degrees.")
    return lon


def validate_min_elevation(value: object) -> float:
    """Minimum elevation threshold in degrees, 0..89."""
    elev = _finite_float(value, "Minimum elevation")
    if not 0.0 <= elev <= config.MAX_MIN_ELEVATION_DEG:
        raise ValidationError(
            f"Minimum elevation must be between 0 and {config.MAX_MIN_ELEVATION_DEG:g} degrees."
        )
    return elev


def validate_search_hours(value: object) -> float:
    """Pass-search window length in hours."""
    hours = _finite_float(value, "Search duration")
    if not config.MIN_PASS_SEARCH_HOURS <= hours <= config.MAX_PASS_SEARCH_HOURS:
        raise ValidationError(
            f"Search duration must be between {config.MIN_PASS_SEARCH_HOURS} and "
            f"{config.MAX_PASS_SEARCH_HOURS} hours."
        )
    return hours


def validate_track_request(duration_min: object, step_s: object) -> tuple[float, float]:
    """Validate a ground-track duration (minutes) and step (seconds).

    Also bounds the resulting number of points so the UI stays responsive.
    """
    duration = _finite_float(duration_min, "Prediction duration")
    step = _finite_float(step_s, "Time step")
    if not 1 <= duration <= config.MAX_TRACK_DURATION_MIN:
        raise ValidationError(
            f"Prediction duration must be between 1 and {config.MAX_TRACK_DURATION_MIN} minutes."
        )
    if step < config.MIN_TRACK_STEP_S:
        raise ValidationError(f"Time step must be at least {config.MIN_TRACK_STEP_S} seconds.")
    if duration * 60 / step + 1 > config.MAX_TRACK_POINTS:
        raise ValidationError(
            f"That would create more than {config.MAX_TRACK_POINTS} points. "
            "Use a larger time step or a shorter duration."
        )
    return duration, step


def validate_observer_name(name: object) -> str:
    """Optional label; blank becomes 'Observer'. Length-limited, no control chars."""
    text = "" if name is None else str(name).strip()
    text = "".join(ch for ch in text if ch.isprintable())[:60]
    return text or "Observer"


def validate_search_window(start_utc: datetime, hours: object) -> tuple[datetime, datetime]:
    """Return ``(start, end)`` in UTC for a validated search window."""
    start = ensure_utc(start_utc)
    return start, start + timedelta(hours=validate_search_hours(hours))


def tle_checksum(line: str) -> int:
    """Modulo-10 checksum of the first 68 characters of a TLE line.

    Digits count as their value, '-' counts as 1, everything else as 0.
    """
    total = 0
    for char in line[:68]:
        if char.isdigit():
            total += int(char)
        elif char == "-":
            total += 1
    return total % 10


def tle_checksum_ok(line: str) -> bool:
    """True if the line is 69 characters long and its final digit matches."""
    return len(line) == 69 and line[68].isdigit() and tle_checksum(line) == int(line[68])
