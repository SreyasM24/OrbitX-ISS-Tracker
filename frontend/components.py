"""Reusable dashboard sections: header, data-status panel, telemetry cards, footer.

These functions only draw. Anything they need to know (the orbital data, the computed
position) is passed in, and nothing here does orbital maths.
"""

from __future__ import annotations

import importlib
import streamlit as st

import backend.formatting as formatting
if not hasattr(formatting, "format_ist"):
    importlib.reload(formatting)

from backend.formatting import (
    format_age,
    format_ist,
    format_latitude,
    format_longitude,
    format_utc,
)
from backend.version import APP_VERSION
from backend.models import DataSource, Freshness
from backend.validation import utcnow

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
        middle.write(f"{format_ist(tle.epoch_utc)}  \n{format_age(age_days)} old")
        right.markdown("**Element freshness**")
        if data.source is DataSource.SAMPLE and freshness is Freshness.FRESH:
            right.warning("SAMPLE / NOT LIVE")
        else:
            badge = {
                Freshness.FRESH: right.success,
                Freshness.STALE: right.warning,
                Freshness.EXPIRED: right.error,
            }[freshness]
            badge(freshness.value.upper())
        if data.source is DataSource.CACHED and data.retrieved_at_utc is not None:
            cached_age_s = max((utcnow() - data.retrieved_at_utc).total_seconds(), 0)
            st.caption(
                f"Downloaded {format_ist(data.retrieved_at_utc)} ({format_age(cached_age_s / 86400.0)} ago) · {data.status_message} (SGP4 orbital prediction, not direct satellite GPS telemetry)."
            )
        elif data.retrieved_at_utc is not None:
            st.caption(f"Downloaded {format_ist(data.retrieved_at_utc)} · {data.status_message} (SGP4 orbital prediction, not direct satellite GPS telemetry).")
        else:
            st.caption(f"{data.status_message} (Demonstration mode: not tracking live orbit).")

        with st.expander("🔍 Network & Provenance Details", expanded=False):
            st.markdown(f"**Application Version:** `{APP_VERSION}`")
            st.markdown(f"**Calculated Position Time (IST):** `{format_ist(utcnow())}`")
            if getattr(data, "last_attempt_utc", None):
                st.markdown(f"**Last Fetch Attempt (IST):** `{format_ist(data.last_attempt_utc)}`")
            st.markdown(f"**Data Source Mode:** `{data.source.value.upper()}`")
            st.markdown(f"**Local Cache Active:** `{'Yes' if getattr(data, 'cache_used', False) else 'No'}`")
            st.markdown(f"**Element Epoch (IST):** `{format_ist(tle.epoch_utc)}` ({format_utc(tle.epoch_utc)}) · {format_age(age_days)} old")
            if data.retrieved_at_utc:
                st.markdown(f"**Retrieved At (IST):** `{format_ist(data.retrieved_at_utc)}`")
            st.markdown("**Orbital Model & Independent Validation:**")
            st.markdown(
                "- **Model:** SGP4 orbital propagation via Skyfield onto WGS84 geodetic ellipsoid.\n"
                "- **Benchmark:** Independently verified against NASA JSC FOD/TOPO official ISS OEM trajectory (horizontal separation ~0.24 km) and WhereTheISS.at (~0.04 km).\n"
                "- **Nature of data:** High-fidelity orbital prediction from published elements; not a direct satellite GPS telemetry downlink."
            )
            diagnostics = getattr(data, "diagnostics", ())
            if diagnostics:
                st.markdown("**Endpoint Probe History (Most Recent Run):**")
                for d in diagnostics:
                    ep = d.get("endpoint", "Endpoint")
                    el = d.get("elapsed_s", 0.0)
                    ph = d.get("phase", "")
                    code = d.get("status_code")
                    err = d.get("error", "")
                    if ph == "success":
                        st.markdown(f"- ✅ **{ep}**: Success in {el}s (HTTP {code or 200})")
                    else:
                        st.markdown(f"- ❌ **{ep}**: Failed in {el}s [{ph}] ({err or ('HTTP ' + str(code))})")
    for note in data.warnings:
        st.warning(note)


def render_telemetry(position, illustrative: bool) -> None:
    """The four headline numbers for the current position."""
    label = "Illustrative position" if illustrative else "Calculated position"
    st.subheader(f"{label} · {format_ist(position.time_utc)}")
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
        '<div class="ox-footer">Orbital elements: CelesTrak, WhereTheISS & ARISS. Propagation: '
        "Skyfield + SGP4. Base map: © OpenStreetMap contributors. OrbitX is an educational "
        "tool; do not use it for navigation or safety-critical decisions.<br>"
        f"Built for the <b>GITAM Aero Astro Club (GAAC)</b> OrbitX workshop. · <code>OrbitX {APP_VERSION}</code></div>",
        unsafe_allow_html=True,
    )
