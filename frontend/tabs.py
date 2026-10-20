"""The four dashboard tabs: map, telemetry charts, observation passes and mission guides."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from backend import config
from frontend.charts import telemetry_figure, track_figure
from backend.formatting import format_duration, format_ist
from frontend.map_view import build_map
from backend.missions import MISSIONS
from backend.orbital_engine import PredictionError, split_track_segments
from backend.pass_predictor import passes_to_frame
from frontend.data import cached_passes
from backend.validation import ValidationError

TAB_LABELS = ["🗺️ Map", "📈 Telemetry", "🔭 Passes", "🎯 Missions"]


def render_map_tab(position, track, observer, controls, illustrative: bool) -> None:
    st.caption(
        f"Orange dot: ISS sub-satellite point now. Blue line: predicted ground track for the "
        f"next {controls.track_minutes} min (every {controls.step_s} s). "
        "Latitude/longitude are geodetic (WGS84)."
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


def render_charts_tab(track, illustrative: bool = False, source_label: str = "") -> None:
    st.plotly_chart(telemetry_figure(track), width="stretch")
    st.caption(
        "Predicted from the orbital elements, starting now (times displayed in Indian Standard Time, IST = UTC+05:30). "
        "Longitude wraps at ±180°, so the line is broken there rather than drawn across the whole plot."
    )
    with st.expander("Show the numbers"):
        display_df = track.copy()
        if "time_utc" in display_df.columns:
            utc_series = pd.to_datetime(display_df["time_utc"], utc=True)
            display_df.insert(
                1,
                "time_ist",
                utc_series.dt.tz_convert(config.IST).dt.strftime("%d %b %Y, %I:%M:%S %p IST"),
            )
        st.dataframe(display_df, hide_index=True, width="stretch")
        csv_filename = "orbitx_track_illustrative.csv" if illustrative else "orbitx_track.csv"
        export_df = display_df.copy()
        export_df["data_source"] = source_label or ("SAMPLE (illustrative)" if illustrative else "LIVE")
        st.download_button("⬇ Download CSV", export_df.to_csv(index=False), csv_filename,
                           "text/csv")


def render_passes_tab(tle, observer, start, controls) -> None:
    st.info(
        "A **pass** means the ISS is geometrically above your horizon. To actually *see* it "
        "you also need: the ISS in sunlight (usually shortly after sunset or before sunrise), "
        "you in darkness, a clear sky, and a clear view toward it. A pass in this table does "
        "**not** guarantee you can see it."
    )
    if observer is None:
        st.warning("Fix the observer location in the sidebar to see passes.")
        return
    try:
        passes = cached_passes(
            tle.name, tle.line1, tle.line2,
            f"{observer.latitude_deg}", f"{observer.longitude_deg}",
            start, controls.search_hours, float(controls.min_elevation),
        )
    except Exception as exc:
        st.error(f"Pass search failed: {exc}")
        return
    st.markdown(
        f"**{observer.name}** · {observer.latitude_deg:.4f}°, {observer.longitude_deg:.4f}° "
        f"· next {controls.search_hours} h · minimum elevation {controls.min_elevation}°"
    )
    if not passes:
        st.info(
            f"No passes above {controls.min_elevation}° in the next {controls.search_hours} "
            "hours. Try a longer window or a lower minimum elevation."
        )
        return
    first = next((p for p in passes if p.is_complete), None)
    if first is not None:
        m1, m2, m3 = st.columns(3)
        ist_rise = first.rise_time_utc.astimezone(config.IST)
        m1.metric("Next full pass (IST)", ist_rise.strftime("%d %b, %I:%M %p"))
        m2.metric("Peak elevation", f"{first.max_elevation_deg:.0f}°")
        m3.metric("Duration", format_duration(first.duration_s))
        st.caption(
            f"Pass start: {format_ist(first.rise_time_utc)} ({first.rise_time_utc.strftime('%H:%M:%S UTC')})"
        )
    st.dataframe(passes_to_frame(passes, controls.zones), hide_index=True, width="stretch")
    if any(not p.is_complete for p in passes):
        st.caption("Passes marked in the Note column are cut off by the search window, so "
                   "their duration is unknown.")


def render_missions_tab() -> None:
    labels = {m.key: m.title for m in MISSIONS}
    key = st.radio("Mission", list(labels), format_func=labels.get, horizontal=True)
    mission = next(m for m in MISSIONS if m.key == key)
    st.caption(f"About {mission.minutes} minutes · file: missions/{mission.filename}")
    st.markdown(mission.read())
