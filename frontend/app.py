"""OrbitX: mission-control dashboard for the International Space Station.

Run with:  streamlit run frontend/app.py   (or scripts\\run.ps1 on Windows)

This file is the entry point: it wires input, calculations and presentation together.
Orbital maths, data retrieval and validation live in ``backend/``; everything the user sees
(layout, styling, map, charts, video background) lives in ``frontend/``.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

# Allow `streamlit run frontend/app.py` without installing the packages: put the repository
# root on the import path so that ``backend`` and ``frontend`` can be imported.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from backend import tle_service  # noqa: E402
from backend.models import Freshness  # noqa: E402
from backend.orbital_engine import (  # noqa: E402
    PredictionError,
    build_satellite,
    compute_position,
    epoch_distance_warning,
)
from backend.pass_predictor import observer_from_text  # noqa: E402
from frontend import background, components, tabs, theme  # noqa: E402
from frontend.data import cached_track, load_data  # noqa: E402
from frontend.sidebar import CUSTOM_LOCATION, init_state, render_sidebar  # noqa: E402
from backend.validation import ValidationError, utcnow  # noqa: E402

st.set_page_config(page_title="OrbitX ISS Tracker", page_icon="🛰️", layout="wide")

theme.inject_theme()
background.render_background()
init_state()
controls = render_sidebar()
components.render_header()

# ------------------------------------------------------------------------- orbital data
data = load_data(force_refresh=st.session_state.pop("force_refresh", False))
now = utcnow()
tle = data.tle
age_days = tle_service.tle_age_days(tle, now)
freshness = tle_service.classify_freshness(tle, now)
components.render_status(data, tle, age_days, freshness)

# ------------------------------------------------------------------------ calculations
start = now.replace(second=0, microsecond=0)  # whole minutes keep cache keys stable
try:
    satellite = build_satellite(tle)
    position = compute_position(satellite, now)
    track = cached_track(tle.name, tle.line1, tle.line2, start,
                         controls.track_minutes, controls.step_s)
except (PredictionError, ValidationError) as exc:
    st.error(f"Could not calculate the ISS position: {exc}")
    st.stop()

illustrative = freshness is Freshness.EXPIRED
components.render_telemetry(position, illustrative)
distance_note = epoch_distance_warning(tle, start + timedelta(minutes=controls.track_minutes))
if distance_note:
    st.warning(distance_note)

try:
    observer = observer_from_text(
        "Custom location" if st.session_state["city"] == CUSTOM_LOCATION
        else st.session_state["city"],
        st.session_state["lat_text"], st.session_state["lon_text"],
    )
except ValidationError as exc:
    observer = None
    st.sidebar.error(f"Observer location: {exc}")

# ---------------------------------------------------------------------------------- tabs
tab_map, tab_charts, tab_passes, tab_missions = st.tabs(tabs.TAB_LABELS)
with tab_map:
    tabs.render_map_tab(position, track, observer, controls, illustrative)
with tab_charts:
    tabs.render_charts_tab(track)
with tab_passes:
    tabs.render_passes_tab(tle, observer, start, controls)
with tab_missions:
    tabs.render_missions_tab()

components.render_footer()
