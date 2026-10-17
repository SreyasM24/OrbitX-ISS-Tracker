"""Plain data containers shared across OrbitX modules (no I/O, no Skyfield)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DataSource(str, Enum):
    """Where the orbital elements in use came from."""

    LIVE = "live"      # downloaded from the network during this request
    CACHED = "cached"  # previously downloaded, read back from the local cache
    SAMPLE = "sample"  # bundled offline sample (never labelled live)


class Freshness(str, Enum):
    """How old the orbital elements are relative to their epoch."""

    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"


@dataclass(frozen=True)
class TleRecord:
    """A validated two-line element set."""

    name: str
    line1: str
    line2: str
    catalog_number: int
    epoch_utc: datetime  # timezone-aware UTC
    source_url: str = ""


@dataclass(frozen=True)
class OrbitalData:
    """Orbital elements plus honest provenance metadata."""

    tle: TleRecord
    source: DataSource
    retrieved_at_utc: datetime | None  # when the download happened (None for sample)
    source_label: str
    status_message: str
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Observer:
    """A ground observer. Latitude/longitude in degrees, elevation in metres."""

    name: str
    latitude_deg: float
    longitude_deg: float
    elevation_m: float = 0.0


@dataclass(frozen=True)
class SatellitePosition:
    """Sub-satellite point and speed at one UTC instant."""

    time_utc: datetime
    latitude_deg: float
    longitude_deg: float  # in [-180, 180]
    altitude_km: float    # above the WGS84 ellipsoid
    speed_km_s: float     # inertial (GCRS) speed relative to Earth's centre


@dataclass(frozen=True)
class SatellitePass:
    """One pass above the elevation threshold.

    ``rise_time_utc`` is None when the satellite was already above the threshold
    at the search start; ``set_time_utc`` is None when the pass continues past the
    search end. Such passes are reported, but their duration is unknown.
    """

    rise_time_utc: datetime | None
    culmination_time_utc: datetime | None
    set_time_utc: datetime | None
    max_elevation_deg: float | None
    rise_azimuth_deg: float | None = None
    set_azimuth_deg: float | None = None

    @property
    def is_complete(self) -> bool:
        return None not in (self.rise_time_utc, self.culmination_time_utc, self.set_time_utc)

    @property
    def duration_s(self) -> float | None:
        if self.rise_time_utc is None or self.set_time_utc is None:
            return None
        return (self.set_time_utc - self.rise_time_utc).total_seconds()
