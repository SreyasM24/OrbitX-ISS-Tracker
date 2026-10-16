"""Reusable dashboard sections: header, data-status panel, telemetry cards, footer.

These functions only draw. Anything they need to know (the orbital data, the computed
position) is passed in, and nothing here does orbital maths.
"""

from __future__ import annotations

import streamlit as st

from backend.formatting import (
    format_age,
    format_latitude,
    format_longitude,
    format_utc,
)
from backend.models import DataSource, Freshness

# A generic orbit-ring glyph. It is NOT the club's official logo.
_ORBIT_ICON = (
    '<svg viewBox="0 0 32 32" fill="none" aria-hidden="true">'
    '<circle cx="16" cy="16" r="4.2" fill="#38bdf8"/>'
    '<ellipse cx="16" cy="16" rx="13" ry="5.5" stroke="#7dd3fc" stroke-width="1.4" '
    'transform="rotate(-28 16 16)"/>'
    '<circle cx="27.2" cy="9.8" r="1.8" fill="#f97316"/></svg>'
)


def render_header() -> None:
    """Title, one-line explanation and the small GAAC attribution badge."""
    title_col, badge_col = st.columns([3, 1.25], vertical_alignment="center")
    with title_col:
        st.markdown('<div class="ox-eyebrow">Mission control</div>', unsafe_allow_html=True)
        st.title("OrbitX ISS Tracker")
    with badge_col:
        st.markdown(
            f'<div class="ox-badge">{_ORBIT_ICON}<div><b>GITAM AERO ASTRO CLUB</b>'
            "<span>GAAC · GITAM UNIVERSITY</span></div></div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        '<p class="ox-tagline">Where is the International Space Station right now, where will '
        "it go, and when can you look up? Positions are calculated from public orbital elements "
        "(TLE) with the SGP4 model. They are predictions, not a live telemetry feed.</p>",
        unsafe_allow_html=True,
    )


def render_status(data, tle, age_days: float, freshness: Freshness) -> None:
    """Data provenance, element epoch and freshness (LIVE / CACHED / SAMPLE, FRESH / STALE...)."""
    with st.container(border=True, key="orbitx_status"):
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


def render_telemetry(position, illustrative: bool) -> None:
    """The four headline numbers for the current position."""
    label = "Illustrative position" if illustrative else "Calculated position"
    st.subheader(f"{label} · {format_utc(position.time_utc)}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latitude", format_latitude(position.latitude_deg))
    c2.metric("Longitude", format_longitude(position.longitude_deg))
    c3.metric("Altitude", f"{position.altitude_km:.0f} km",
              help="Height above the WGS84 ellipsoid.")
    c4.metric("Orbital speed", f"{position.speed_km_s:.2f} km/s",
              help="Speed relative to Earth's centre in a non-rotating frame, not ground speed.")


def render_footer() -> None:
    """Data-source and map attributions plus the educational-use disclaimer."""
    st.divider()
    st.markdown(
        '<div class="ox-footer">Orbital elements: CelesTrak (Dr. T.S. Kelso). Propagation: '
        "Skyfield + SGP4. Base map: © OpenStreetMap contributors. OrbitX is an educational "
        "tool; do not use it for navigation or safety-critical decisions.<br>"
        "Built for the <b>GITAM Aero Astro Club (GAAC)</b> OrbitX workshop.</div>",
        unsafe_allow_html=True,
    )
