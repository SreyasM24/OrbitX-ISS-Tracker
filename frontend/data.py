"""Cached data access for the dashboard (Streamlit ``cache_data`` wrappers).

Each wrapper takes only plain, hashable arguments so Streamlit can cache it. The real work is
done by the scientific modules, which know nothing about Streamlit.
"""

from __future__ import annotations

import streamlit as st

from backend import tle_service
from backend.orbital_engine import build_satellite, predict_track
from backend.pass_predictor import find_passes, observer_from_text
from backend.models import DataSource, TleRecord


def load_data(force_refresh: bool = False):
    """Orbital elements with provenance. tle_service has its own 2-hour disk cache."""
    return tle_service.get_orbital_data(force_refresh=force_refresh)


# Maintain load_data.clear() backward compatibility
load_data.clear = lambda: None


def request_refresh() -> None:
    """Button callback: ask for a fresh download on the next run."""
    st.session_state["force_refresh"] = True


def _tle_from_strings(name: str, line1: str, line2: str) -> TleRecord:
    return tle_service.parse_tle_text(f"{name}\n{line1}\n{line2}")


@st.cache_data(show_spinner=False, max_entries=32)
def cached_track(name, line1, line2, start, duration_min, step_s):
    satellite = build_satellite(_tle_from_strings(name, line1, line2))
    return predict_track(satellite, start, duration_min, step_s)


@st.cache_data(show_spinner="Searching for passes…", max_entries=32)
def cached_passes(name, line1, line2, lat, lon, start, hours, min_elevation):
    satellite = build_satellite(_tle_from_strings(name, line1, line2))
    observer = observer_from_text("Observer", lat, lon)
    return find_passes(satellite, observer, start, hours, min_elevation)
