"""Sidebar controls: observer location, ground-track settings and pass-search settings."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from backend import config, tle_service
from frontend.data import request_refresh

CUSTOM_LOCATION = "Custom location"
ZONE_CHOICES = {"UTC and IST": ("UTC", "IST"), "UTC only": ("UTC",), "IST only": ("IST",)}
REFRESH_CHOICES = {
    "10 seconds (Recommended)": 10,
    "5 seconds (Fast)": 5,
    "30 seconds": 30,
    "60 seconds": 60,
    "Paused (Manual only)": 0,
}


@dataclass(frozen=True)
class Controls:
    """What the student chose in the sidebar."""

    track_minutes: int
    step_s: int
    search_hours: int
    min_elevation: int
    zone_label: str
    refresh_seconds: int = 10

    @property
    def zones(self) -> tuple[str, ...]:
        return ZONE_CHOICES[self.zone_label]


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


def init_state() -> None:
    """Give the observer widgets their defaults on the very first run of a session."""
    if "city" not in st.session_state:
        _reset_observer()


def render_sidebar() -> Controls:
    """Draw the sidebar and return the chosen settings."""
    with st.sidebar:
        st.markdown('<div class="ox-side-title">Mission controls</div>', unsafe_allow_html=True)
        st.button("↻ Re-download orbital elements", on_click=request_refresh, key="btn_refresh",
                  help="Fetches fresh data from CelesTrak. Elements change only every few hours, "
                       "so please don't press this repeatedly.")

        st.subheader("Observer location")
        st.selectbox("Example city", [*config.EXAMPLE_CITIES, CUSTOM_LOCATION], key="city",
                     on_change=_apply_city)
        st.text_input("Latitude (°, north +)", key="lat_text", on_change=_mark_custom)
        st.text_input("Longitude (°, east +)", key="lon_text", on_change=_mark_custom)
        st.button("Reset to default location", on_click=_reset_observer, key="btn_reset")

        st.subheader("Ground track")
        durations = sorted({*config.TRACK_DURATION_OPTIONS_MIN, config.DEFAULT_TRACK_MINUTES})
        durations = [d for d in durations if d <= config.MAX_TRACK_DURATION_MIN]
        track_minutes = st.select_slider("Prediction length (minutes)", durations,
                                         value=config.DEFAULT_TRACK_MINUTES)
        step_s = st.select_slider("Time step (seconds)", list(config.TRACK_STEP_OPTIONS_S),
                                  value=config.DEFAULT_TRACK_STEP_S)

        st.subheader("Auto-refresh")
        refresh_label = st.selectbox(
            "ISS position update interval",
            list(REFRESH_CHOICES),
            index=0,
            key="refresh_choice",
            help="Recalculates current ISS position, altitude, speed, map marker, and telemetry at this interval. Uses latest available orbital elements without redundant downloads.",
        )
        refresh_seconds = REFRESH_CHOICES[refresh_label]

        st.subheader("Observation passes")
        search_hours = st.slider("Search window (hours)", config.MIN_PASS_SEARCH_HOURS,
                                 config.MAX_PASS_SEARCH_HOURS, config.DEFAULT_SEARCH_HOURS)
        min_elevation = st.slider("Minimum elevation (°)", 0, 60,
                                  int(config.DEFAULT_MIN_ELEVATION_DEG), step=5,
                                  help="How high above the horizon the ISS must climb to count.")
        zone_label = st.radio("Show pass times in", list(ZONE_CHOICES))

        with st.expander("🛠️ Live Network Diagnostics", expanded=False):
            st.caption("Probe candidate TLE endpoints directly from this running server.")
            if st.button("Run Live Endpoint Probes", key="btn_probe_endpoints"):
                with st.spinner("Probing candidate endpoints..."):
                    try:
                        from backend.diagnostics import probe_all_endpoints
                        results = probe_all_endpoints()
                        for r in results:
                            status = r["status_code"] or "ERR"
                            if r["phase"] == "success":
                                st.success(
                                    f"**{r['endpoint']}**: {r['elapsed_s']}s (HTTP {status}) — NORAD {r['catalog_number']}"
                                )
                            else:
                                st.warning(
                                    f"**{r['endpoint']}**: {r['elapsed_s']}s [{r['phase']}] — {r['error']}"
                                )
                    except Exception as exc:
                        st.error(f"Diagnostic probe failure: {exc}")
            if st.button("🧪 Probe & Apply Live TLE", key="btn_apply_probe",
                         help="Probes all endpoints and saves the first successful live TLE into local cache, then reloads the dashboard."):
                with st.spinner("Probing endpoints and applying live TLE..."):
                    try:
                        from backend.diagnostics import probe_all_endpoints
                        from backend.validation import utcnow
                        results = probe_all_endpoints()
                        applied = False
                        for r in results:
                            if r.get("phase") == "success" and r.get("tle_record"):
                                tle_service.write_cache(r["tle_record"], utcnow(), r["url"], config.CACHE_PATH)
                                st.success(f"Applied live elements from {r['endpoint']}! Reloading...")
                                applied = True
                                st.rerun()
                                break
                        if not applied:
                            st.error("All endpoints failed during live probe.")
                    except Exception as exc:
                        st.error(f"Probe & Apply failure: {exc}")

    return Controls(track_minutes, step_s, search_hours, min_elevation, zone_label, refresh_seconds)
