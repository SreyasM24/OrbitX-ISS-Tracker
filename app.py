"""OrbitX: mission-control dashboard for the International Space Station.

Run with:  streamlit run app.py   (or scripts\\run.ps1 on Windows)

This file only handles input, orchestration and presentation. All orbital maths lives in
``src/orbitx`` (tle_service, orbital_engine, pass_predictor, map_view, charts).
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

# Allow `streamlit run app.py` without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st  # noqa: E402
from streamlit_folium import st_folium  # noqa: E402

from orbitx import config, tle_service  # noqa: E402
from orbitx.charts import telemetry_figure, track_figure  # noqa: E402
from orbitx.formatting import (  # noqa: E402
    format_age,
    format_duration,
    format_latitude,
    format_longitude,
    format_utc,
)
from orbitx.map_view import build_map  # noqa: E402
from orbitx.missions import MISSIONS  # noqa: E402
from orbitx.models import DataSource, Freshness, TleRecord  # noqa: E402
from orbitx.orbital_engine import (  # noqa: E402
    PredictionError,
    build_satellite,
    compute_position,
    epoch_distance_warning,
    predict_track,
    split_track_segments,
)
from orbitx.pass_predictor import (  # noqa: E402
    find_passes,
    observer_from_text,
    passes_to_frame,
)
from orbitx.validation import ValidationError, utcnow  # noqa: E402

CUSTOM_LOCATION = "Custom location"
ZONE_CHOICES = {"UTC and IST": ("UTC", "IST"), "UTC only": ("UTC",), "IST only": ("IST",)}

st.set_page_config(page_title="OrbitX ISS Tracker", page_icon="🛰️", layout="wide")


# ----------------------------------------------------------------------------- caching
@st.cache_data(ttl=300, show_spinner="Fetching orbital elements…")
def load_data(force_refresh: bool = False):
    """Orbital elements with provenance. Cached 5 min; tle_service has its own 2 h cache."""
    return tle_service.get_orbital_data(force_refresh=force_refresh)


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


# ------------------------------------------------------------------- observer widgets
def _city_coords(city: str) -> tuple[str, str]:
    lat, lon = config.EXAMPLE_CITIES[city]
    return f"{lat:.4f}", f"{lon:.4f}"


def _apply_city() -> None:
    city = st.session_state["city"]
    if city != CUSTOM_LOCATION:
        st.session_state["lat_text"], st.session_state["lon_text"] = _city_coords(city)


def _mark_custom() -> None:
    st.session_state["city"] = CUSTOM_LOCATION


def _reset_observer() -> None:
    st.session_state["city"] = config.DEFAULT_CITY
    st.session_state["lat_text"], st.session_state["lon_text"] = _city_coords(config.DEFAULT_CITY)


def _request_refresh() -> None:
    load_data.clear()
    st.session_state["force_refresh"] = True


if "city" not in st.session_state:
    _reset_observer()

# ----------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Controls")
    st.button("Re-download orbital elements", on_click=_request_refresh,
              help="Fetches fresh data from CelesTrak. Elements change only every few hours, "
                   "so please don't press this repeatedly.")

    st.subheader("Observer location")
    st.selectbox("Example city", [*config.EXAMPLE_CITIES, CUSTOM_LOCATION], key="city",
                 on_change=_apply_city)
    st.text_input("Latitude (°, north +)", key="lat_text", on_change=_mark_custom)
    st.text_input("Longitude (°, east +)", key="lon_text", on_change=_mark_custom)
    st.button("Reset to default location", on_click=_reset_observer)

    st.subheader("Ground track")
    durations = sorted({*config.TRACK_DURATION_OPTIONS_MIN, config.DEFAULT_TRACK_MINUTES})
    durations = [d for d in durations if d <= config.MAX_TRACK_DURATION_MIN]
    track_minutes = st.select_slider("Prediction length (minutes)", durations,
                                     value=config.DEFAULT_TRACK_MINUTES)
    step_s = st.select_slider("Time step (seconds)", list(config.TRACK_STEP_OPTIONS_S),
                              value=config.DEFAULT_TRACK_STEP_S)

    st.subheader("Observation passes")
    search_hours = st.slider("Search window (hours)", config.MIN_PASS_SEARCH_HOURS,
                             config.MAX_PASS_SEARCH_HOURS, config.DEFAULT_SEARCH_HOURS)
    min_elevation = st.slider("Minimum elevation (°)", 0, 60,
                              int(config.DEFAULT_MIN_ELEVATION_DEG), step=5,
                              help="How high above the horizon the ISS must climb to count.")
    zone_label = st.radio("Show pass times in", list(ZONE_CHOICES))

# ------------------------------------------------------------------------------- header
st.title("🛰️ OrbitX ISS Tracker")
st.caption(
    "Where is the International Space Station right now, where will it go, and when can "
    "you look up? Positions are calculated from public orbital elements (TLE) with the "
    "SGP4 model. They are predictions, not a live telemetry feed."
)

data = load_data(force_refresh=st.session_state.pop("force_refresh", False))
now = utcnow()
tle = data.tle
age_days = tle_service.tle_age_days(tle, now)
freshness = tle_service.classify_freshness(tle, now)

with st.container(border=True):
    left, middle, right = st.columns(3)
    left.markdown("**Data source**")
    if data.source is DataSource.LIVE:
        left.success(f"LIVE · {data.source_label}")
    elif data.source is DataSource.CACHED:
        left.info(f"CACHED · {data.source_label}")
    else:
        left.error("SAMPLE · bundled offline file, NOT live")
    middle.markdown("**Orbital element epoch**")
    middle.write(f"{format_utc(tle.epoch_utc)}  \n{format_age(age_days)} old")
    right.markdown("**Element freshness**")
    badge = {Freshness.FRESH: right.success, Freshness.STALE: right.warning,
             Freshness.EXPIRED: right.error}[freshness]
    badge(freshness.value.upper())
    if data.retrieved_at_utc is not None:
        st.caption(f"Downloaded {format_utc(data.retrieved_at_utc)} · {data.status_message}")
    else:
        st.caption(data.status_message)
for note in data.warnings:
    st.warning(note)

# ------------------------------------------------------------------------ calculations
start = now.replace(second=0, microsecond=0)  # whole minutes keep cache keys stable
try:
    satellite = build_satellite(tle)
    position = compute_position(satellite, now)
    track = cached_track(tle.name, tle.line1, tle.line2, start, track_minutes, step_s)
except (PredictionError, ValidationError) as exc:
    st.error(f"Could not calculate the ISS position: {exc}")
    st.stop()

illustrative = freshness is Freshness.EXPIRED
label = "Illustrative position" if illustrative else "Calculated position"
st.subheader(f"{label} · {format_utc(position.time_utc)}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Latitude", format_latitude(position.latitude_deg))
c2.metric("Longitude", format_longitude(position.longitude_deg))
c3.metric("Altitude", f"{position.altitude_km:.0f} km", help="Height above the WGS84 ellipsoid.")
c4.metric("Orbital speed", f"{position.speed_km_s:.2f} km/s",
          help="Speed relative to Earth's centre in a non-rotating frame, not ground speed.")
distance_note = epoch_distance_warning(tle, start + timedelta(minutes=track_minutes))
if distance_note:
    st.warning(distance_note)

try:
    observer = observer_from_text(
        "Custom location" if st.session_state["city"] == CUSTOM_LOCATION
        else st.session_state["city"],
        st.session_state["lat_text"], st.session_state["lon_text"],
    )
    observer_error = None
except ValidationError as exc:
    observer, observer_error = None, str(exc)
if observer_error:
    st.sidebar.error(f"Observer location: {observer_error}")

# ---------------------------------------------------------------------------------- tabs
tab_map, tab_charts, tab_passes, tab_missions = st.tabs(
    ["🗺️ Map", "📈 Telemetry", "🔭 Passes", "🎯 Missions"]
)

with tab_map:
    st.caption(
        f"Orange dot: ISS sub-satellite point now. Blue line: predicted ground track for the "
        f"next {track_minutes} min (every {step_s} s). Latitude/longitude are geodetic (WGS84)."
    )
    st_folium(
        build_map(position, split_track_segments(track), observer, illustrative=illustrative),
        height=520, width="stretch", returned_objects=[],
    )
    with st.expander("Plain track plot (works without internet)"):
        st.caption(
            "The map above loads its scripts and tiles from the internet; if it stays empty, "
            "this plot shows the same predicted track without a base map."
        )
        st.plotly_chart(track_figure(track, position, observer), width="stretch")

with tab_charts:
    st.plotly_chart(telemetry_figure(track), width="stretch")
    st.caption(
        "Predicted from the orbital elements, starting now. Longitude wraps at ±180°, so the "
        "line is broken there rather than drawn across the whole plot."
    )
    with st.expander("Show the numbers"):
        st.dataframe(track, hide_index=True, width="stretch")
        st.download_button("Download CSV", track.to_csv(index=False), "orbitx_track.csv",
                           "text/csv")

with tab_passes:
    st.info(
        "A **pass** means the ISS is geometrically above your horizon. To actually *see* it "
        "you also need: the ISS in sunlight (usually shortly after sunset or before sunrise), "
        "you in darkness, a clear sky, and a clear view toward it. A pass in this table does "
        "**not** guarantee you can see it."
    )
    if observer is None:
        st.warning("Fix the observer location in the sidebar to see passes.")
    else:
        try:
            passes = cached_passes(
                tle.name, tle.line1, tle.line2,
                f"{observer.latitude_deg}", f"{observer.longitude_deg}",
                start, search_hours, float(min_elevation),
            )
        except (PredictionError, ValidationError) as exc:
            st.error(f"Pass search failed: {exc}")
            passes = None
        if passes is not None:
            st.markdown(
                f"**{observer.name}** · {observer.latitude_deg:.4f}°, {observer.longitude_deg:.4f}° "
                f"· next {search_hours} h · minimum elevation {min_elevation}°"
            )
            if not passes:
                st.info(
                    f"No passes above {min_elevation}° in the next {search_hours} hours. Try a "
                    "longer window or a lower minimum elevation."
                )
            else:
                first = next((p for p in passes if p.is_complete), None)
                if first is not None:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Next full pass (UTC)", first.rise_time_utc.strftime("%d %b %H:%M"))
                    m2.metric("Peak elevation", f"{first.max_elevation_deg:.0f}°")
                    m3.metric("Duration", format_duration(first.duration_s))
                    st.caption(
                        "IST = UTC + 05:30: "
                        + first.rise_time_utc.astimezone(config.IST).strftime("%d %b %H:%M IST")
                    )
                st.dataframe(passes_to_frame(passes, ZONE_CHOICES[zone_label]),
                             hide_index=True, width="stretch")
                if any(not p.is_complete for p in passes):
                    st.caption("Passes marked in the Note column are cut off by the search "
                               "window, so their duration is unknown.")

with tab_missions:
    labels = {m.key: m.title for m in MISSIONS}
    key = st.radio("Mission", list(labels), format_func=labels.get, horizontal=True)
    mission = next(m for m in MISSIONS if m.key == key)
    st.caption(f"About {mission.minutes} minutes · file: missions/{mission.filename}")
    st.markdown(mission.read())

st.divider()
st.caption(
    "Orbital elements: CelesTrak (Dr. T.S. Kelso). Propagation: Skyfield + SGP4. Base map: "
    "© OpenStreetMap contributors. OrbitX is an educational tool; do not use it for "
    "navigation or safety-critical decisions."
)
