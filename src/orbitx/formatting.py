"""Small display-formatting helpers (pure functions)."""

from __future__ import annotations

from datetime import datetime, timezone


def format_latitude(value_deg: float) -> str:
    """e.g. ``17.69° N``."""
    return f"{abs(value_deg):.2f}° {'N' if value_deg >= 0 else 'S'}"


def format_longitude(value_deg: float) -> str:
    """e.g. ``83.22° E``."""
    return f"{abs(value_deg):.2f}° {'E' if value_deg >= 0 else 'W'}"


def format_utc(moment: datetime | None) -> str:
    """``2026-10-21 09:30:00 UTC`` or an en dash for missing values."""
    if moment is None:
        return "–"
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def format_duration(seconds: float | None) -> str:
    """``7 min 05 s`` (or an en dash when unknown)."""
    if seconds is None:
        return "–"
    minutes, secs = divmod(int(round(seconds)), 60)
    return f"{minutes} min {secs:02d} s"


def format_age(days: float) -> str:
    """Human-readable element age: minutes, hours or days."""
    if days < 0:
        return "epoch is in the future"
    if days < 1 / 24:
        return f"{days * 24 * 60:.0f} min"
    if days < 2:
        return f"{days * 24:.1f} h"
    return f"{days:.1f} days"


_COMPASS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")


def compass_point(azimuth_deg: float | None) -> str:
    """Azimuth (0 = north, 90 = east) as ``NW (315°)``; an en dash when unknown."""
    if azimuth_deg is None:
        return "–"
    azimuth = azimuth_deg % 360.0
    return f"{_COMPASS[int((azimuth + 11.25) // 22.5) % 16]} ({azimuth:.0f}°)"
