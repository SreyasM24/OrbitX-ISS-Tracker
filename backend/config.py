"""Central configuration and constants for OrbitX.

Values can be overridden with environment variables (see ``.env.example``).
Nothing here requires an API key.
"""

from __future__ import annotations

import os
from datetime import timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(__file__).resolve().parent / "data"  # bundled, read-only sample data
MISSIONS_DIR = PROJECT_ROOT / "missions"
SAMPLE_TLE_PATH = DATA_DIR / "sample_iss.tle"

ISS_NORAD_ID = 25544
ISS_NAME_HINTS = ("ISS", "ZARYA")

CELESTRAK_URL = os.environ.get(
    "ORBITX_TLE_URL",
    f"https://celestrak.org/NORAD/elements/gp.php?CATNR={ISS_NORAD_ID}&FORMAT=TLE",
)
HTTP_TIMEOUT_S = float(os.environ.get("ORBITX_HTTP_TIMEOUT_S", "8"))
USER_AGENT = "OrbitX-workshop/1.0 (educational; GITAM Aero Astro Club)"

# CelesTrak refreshes ISS elements every few hours and asks clients not to poll
# more often than every 2 hours.
CACHE_TTL_S = float(os.environ.get("ORBITX_CACHE_TTL_S", str(2 * 3600)))
CACHE_PATH = (
    Path(os.environ.get("ORBITX_CACHE_DIR", str(PROJECT_ROOT / ".orbitx_cache")))
    / "iss_tle.json"
)

# Set ORBITX_OFFLINE=1 to never touch the network (uses cache, then sample).
OFFLINE_ENV_FLAG = os.environ.get("ORBITX_OFFLINE", "").strip().lower() in {"1", "true", "yes"}

# Orbital-element age thresholds (days since the TLE epoch).
STALE_WARN_DAYS = 3.0
STALE_EXPIRED_DAYS = 14.0
# Warn when a requested time is this far from the TLE epoch.
PREDICTION_DISTANCE_WARN_DAYS = 7.0

# Computation bounds (keep the UI responsive).
MAX_TRACK_POINTS = 2000
MIN_TRACK_STEP_S = 10
MAX_TRACK_DURATION_MIN = 24 * 60
MAX_PASS_SEARCH_HOURS = 72
MIN_PASS_SEARCH_HOURS = 1
MAX_MIN_ELEVATION_DEG = 89.0

# Display only: the workshop is in India. All calculations use UTC.
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

DEFAULT_MIN_ELEVATION_DEG = 10.0
DEFAULT_TRACK_MINUTES = 180  # roughly two orbits (the ISS period is about 92 minutes)
DEFAULT_TRACK_STEP_S = 60
DEFAULT_SEARCH_HOURS = 24

# Choices offered in the UI (every combination is still checked by validation.py).
TRACK_DURATION_OPTIONS_MIN = (60, 90, 120, 180, 360, 720)
TRACK_STEP_OPTIONS_S = (30, 60, 120)

# name -> (latitude_deg, longitude_deg). Approximate city-centre coordinates (decimal degrees,
# north/east positive, accurate to roughly 0.01 degrees: ample for pass prediction).
EXAMPLE_CITIES: dict[str, tuple[float, float]] = {
    "Visakhapatnam, India": (17.6868, 83.2185),
    "Hyderabad, India": (17.3850, 78.4867),
    "Chennai, India": (13.0827, 80.2707),
    "Bengaluru, India": (12.9716, 77.5946),
    "Mumbai, India": (19.0760, 72.8777),
    "New Delhi, India": (28.6139, 77.2090),
    "Kolkata, India": (22.5726, 88.3639),
    "London, United Kingdom": (51.5074, -0.1278),
    "New York, USA": (40.7128, -74.0060),
    "Tokyo, Japan": (35.6762, 139.6503),
    "Sydney, Australia": (-33.8688, 151.2093),
    "Reykjavik, Iceland": (64.1466, -21.9426),
}
DEFAULT_CITY = "Visakhapatnam, India"
