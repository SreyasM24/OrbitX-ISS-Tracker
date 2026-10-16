"""Visual theme: one CSS block that gives the dashboard its mission-control look.

Streamlit has no theming API for glass panels or pill tabs, so we inject CSS. To keep it safe:
* every rule targets a stable Streamlit ``data-testid`` or one of our own ``ox-`` classes;
* nothing restyles the Folium map, Plotly charts or pop-up menus beyond their outer frame;
* colours live in CSS variables at the top, so changing the look means editing one place.
"""

from __future__ import annotations

import streamlit as st

CSS = """
:root {
  --ox-bg: #050b17;
  --ox-panel: rgba(8, 17, 36, 0.78);
  --ox-panel-strong: rgba(8, 16, 34, 0.86);
  --ox-border: rgba(125, 190, 255, 0.20);
  --ox-border-hover: rgba(56, 189, 248, 0.55);
  --ox-text: #eaf2ff;
  --ox-muted: #9fb3d1;
  --ox-accent: #38bdf8;
  --ox-accent-2: #3b82f6;
  --ox-radius: 14px;
  --ox-radius-sm: 10px;
}

html, body, #root { background: var(--ox-bg) !important; }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
  background: transparent !important;
}
[data-testid="stHeader"] { backdrop-filter: blur(6px); }
.stApp { color: var(--ox-text); }
.block-container { padding-top: 2.4rem; padding-bottom: 2rem; max-width: 1280px; }
:where(p, li, label, span) { overflow-wrap: anywhere; }
h1, h2, h3 { letter-spacing: -0.01em; }

/* ---- background video layer (see ui/background.py) ---- */
.st-key-orbitx_bg { position: fixed; inset: 0; z-index: -1; pointer-events: none; }
.st-key-orbitx_bg > div, .st-key-orbitx_bg [data-testid="stHtml"] { height: 100%; }
.orbitx-bg { position: fixed; inset: 0; overflow: hidden; pointer-events: none; z-index: -1;
  background: radial-gradient(ellipse at 20% 0%, #10264d 0%, var(--ox-bg) 60%); }
.orbitx-bg__video { position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: cover; opacity: 0; transition: opacity 1.6s linear; pointer-events: none; }
.orbitx-bg__video.is-on { opacity: 1; }
.orbitx-bg__shade { position: absolute; inset: 0; pointer-events: none;
  background:
    linear-gradient(180deg, rgba(5, 11, 23, 0.80) 0%, rgba(5, 11, 23, 0.64) 38%, rgba(5, 11, 23, 0.88) 100%),
    radial-gradient(ellipse at 80% 10%, rgba(56, 189, 248, 0.10), transparent 55%); }
.st-key-orbitx_css { display: none; }

/* ---- header ---- */
h1 { font-weight: 750 !important; font-size: clamp(1.9rem, 3.2vw, 2.7rem) !important;
  padding: 0 !important; margin: 0 !important;
  background: linear-gradient(90deg, #ffffff 0%, #9bd7ff 60%, #38bdf8 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent !important; }
.ox-tagline { color: #c3d3ec; text-shadow: 0 1px 8px rgba(0,0,0,.6); font-size: 0.97rem; max-width: 62ch; margin: 0.35rem 0 0.6rem; }
.ox-eyebrow { color: var(--ox-accent); font-size: 0.72rem; letter-spacing: 0.22em;
  text-transform: uppercase; font-weight: 600; margin-bottom: 0.2rem; }
.ox-badge { display: inline-flex; align-items: center; gap: 0.6rem; float: right;
  padding: 0.4rem 0.8rem 0.4rem 0.55rem; border-radius: 999px; line-height: 1.15;
  background: var(--ox-panel); border: 1px solid var(--ox-border); backdrop-filter: blur(10px); }
.ox-badge svg { width: 26px; height: 26px; flex: none; }
.ox-badge b { display: block; font-size: 0.72rem; letter-spacing: 0.14em; color: var(--ox-text); }
.ox-badge span { display: block; font-size: 0.64rem; letter-spacing: 0.1em; color: var(--ox-muted); }

/* ---- glass panels ---- */
.st-key-orbitx_status { background: var(--ox-panel-strong); border: 1px solid var(--ox-border);
  border-radius: var(--ox-radius); backdrop-filter: blur(12px); box-shadow: 0 8px 28px rgba(0,0,0,.3);
  padding: 0.9rem 1rem; }
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] [data-testid="stAlert"]),
[data-testid="stExpander"], [data-testid="stMetric"],
[data-testid="stDataFrame"], [data-testid="stPlotlyChart"] {
  border-radius: var(--ox-radius) !important;
}
[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--ox-border) !important; border-radius: var(--ox-radius) !important;
  background: var(--ox-panel); backdrop-filter: blur(12px);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.28);
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {
  box-shadow: none; backdrop-filter: none;
}
[data-testid="stMetric"] {
  background: var(--ox-panel); border: 1px solid var(--ox-border); padding: 0.9rem 1.1rem;
  backdrop-filter: blur(12px); box-shadow: 0 6px 22px rgba(0, 0, 0, 0.25);
  transition: border-color 0.2s ease, transform 0.2s ease;
}
[data-testid="stMetric"]:hover { border-color: var(--ox-border-hover); transform: translateY(-1px); }
[data-testid="stMetricLabel"] { color: var(--ox-muted); text-transform: uppercase;
  font-size: 0.72rem; letter-spacing: 0.12em; }
[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; font-weight: 650;
  font-size: clamp(1.3rem, 2.2vw, 1.9rem); }
[data-testid="stExpander"] { background: var(--ox-panel); border: 1px solid var(--ox-border) !important;
  backdrop-filter: blur(12px); }
[data-testid="stExpander"] details, [data-testid="stExpander"] summary { border-radius: var(--ox-radius); }
[data-testid="stDataFrame"], [data-testid="stPlotlyChart"] {
  background: var(--ox-panel-strong); border: 1px solid var(--ox-border); overflow: hidden; }
[data-testid="stAlert"] { background: var(--ox-panel-strong) !important; border: 1px solid var(--ox-border);
  border-radius: var(--ox-radius-sm); backdrop-filter: blur(10px); }
[data-testid="stCaptionContainer"], .stCaption { color: var(--ox-muted) !important; }
hr { border-color: var(--ox-border) !important; }

/* ---- tabs: pills ---- */
[data-testid="stTabs"] [role="tablist"] { gap: 0.4rem; background: var(--ox-panel); padding: 0.3rem;
  border: 1px solid var(--ox-border); border-radius: 999px; width: fit-content; max-width: 100%;
  overflow-x: auto; backdrop-filter: blur(12px); box-shadow: none; }
[data-testid="stTabs"] [role="tablist"] > div:not([data-testid="stTab"]) { display: none; }
[data-testid="stTab"] { border-radius: 999px; min-height: 2.4rem; padding: 0 1.1rem;
  color: var(--ox-muted); transition: background 0.2s ease, color 0.2s ease; }
[data-testid="stTab"] .react-aria-SelectionIndicator { display: none; }
[data-testid="stTab"]:hover { color: var(--ox-text); background: rgba(56, 189, 248, 0.10); }
[data-testid="stTab"][data-selected="true"], [data-testid="stTab"][aria-selected="true"] {
  color: #04101f; font-weight: 650; background: linear-gradient(90deg, #7dd3fc, var(--ox-accent)); }
[data-testid="stTab"][aria-selected="true"] p { color: #04101f; }
[data-testid="stTabs"] [role="tabpanel"] { padding-top: 1rem; }

/* ---- buttons ---- */
.stButton > button, .stDownloadButton > button {
  min-height: 2.6rem; border-radius: var(--ox-radius-sm); font-weight: 600;
  color: var(--ox-text); background: rgba(56, 189, 248, 0.10);
  border: 1px solid var(--ox-border); transition: all 0.18s ease; }
.stButton > button:hover, .stDownloadButton > button:hover {
  border-color: var(--ox-accent); background: rgba(56, 189, 248, 0.22); color: #fff;
  transform: translateY(-1px); }
.stButton > button:active, .stDownloadButton > button:active { transform: translateY(0);
  background: rgba(56, 189, 248, 0.32); }
.stButton > button:disabled, .stDownloadButton > button:disabled { opacity: 0.45; cursor: not-allowed;
  transform: none; }
.stButton > button p, .stDownloadButton > button p { display: inline-flex; align-items: center;
  gap: 0.4rem; margin: 0; }
.stButton > button { width: 100%; }

/* ---- inputs ---- */
[data-testid="stTextInputRootElement"], [data-testid="stSelectbox"] [role="group"],
[data-testid="stNumberInputContainer"] {
  background: rgba(5, 11, 23, 0.72) !important; border-radius: var(--ox-radius-sm) !important;
  border: 1px solid var(--ox-border) !important; }
[data-testid="stTextInputRootElement"]:hover, [data-testid="stSelectbox"] [role="group"]:hover {
  border-color: var(--ox-border-hover) !important; }
[data-testid="stTextInputRootElement"]:focus-within, [data-testid="stSelectbox"] [role="group"]:focus-within {
  border-color: var(--ox-accent) !important; box-shadow: 0 0 0 1px var(--ox-accent); }
[data-testid="stSidebar"] { background: var(--ox-panel-strong) !important;
  border-right: 1px solid var(--ox-border); backdrop-filter: blur(16px); }
.ox-side-title { font-size: 0.72rem; letter-spacing: 0.22em; text-transform: uppercase;
  color: var(--ox-accent); font-weight: 600; margin-bottom: 0.6rem; }

/* ---- visible keyboard focus everywhere ---- */
button:focus-visible, [role="tab"]:focus-visible, summary:focus-visible, input:focus-visible,
[role="slider"]:focus-visible, a:focus-visible {
  outline: 2px solid var(--ox-accent) !important; outline-offset: 2px !important; }

/* ---- footer ---- */
.ox-footer { color: var(--ox-muted); font-size: 0.8rem; line-height: 1.55; padding: 0.8rem 0 0.2rem; }
.ox-footer a { color: var(--ox-accent); }

@media (max-width: 760px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: 3.2rem; }
  .ox-badge { float: none; margin-top: 0.6rem; }
  [data-testid="stTab"] { padding: 0 0.75rem; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; }
}
"""


def inject_theme() -> None:
    """Add the stylesheet. Call once per run; Streamlit de-duplicates identical elements."""
    with st.container(key="orbitx_css"):
        st.html(f"<style>{CSS}</style>")
