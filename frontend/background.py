"""Full-screen cinematic background: a muted looping video behind the dashboard.

How it works
------------
* Streamlit only serves files from ``static/`` (``enableStaticServing`` in
  ``.streamlit/config.toml``; Streamlit looks for ``static/`` next to the main script, i.e. ``frontend/static/``), so :func:`sync_video` copies ``frontend/assets/iss-background.mp4`` there.
* :func:`render_background` writes one fixed, full-viewport layer with ``st.html``. Streamlit
  keeps the same DOM element between script reruns, so the video does not restart when a
  student changes a location, switches tab or downloads a file.
* ``background.js`` crossfades two copies of the video at the loop point, because the footage
  drifts and a plain loop would visibly jump. Without JavaScript the first copy simply uses
  the browser's native ``loop``.
* If the video file is missing (it is not part of the repository) the layer is just a CSS
  gradient, so the rest of the app is unaffected.
"""

from __future__ import annotations

import inspect
import os
import shutil
from pathlib import Path

import streamlit as st

from backend import config

FRONTEND_DIR = Path(__file__).resolve().parent
ASSETS_DIR = FRONTEND_DIR / "assets"  # your local video goes here (git-ignored)
STATIC_DIR = FRONTEND_DIR / "static"  # generated copy that Streamlit serves (git-ignored)
BACKGROUND_VIDEO_PATH = Path(
    os.environ.get("ORBITX_BACKGROUND_VIDEO", str(ASSETS_DIR / "iss-background.mp4"))
)
STATIC_URL_PREFIX = "app/static"  # where Streamlit serves ``static/`` (relative to the page)
_JS_PATH = Path(__file__).with_name("background.js")


def sync_video(source: Path | None = None, static_dir: Path | None = None) -> str | None:
    """Make the background video available to the browser.

    Returns the file name inside ``static/`` or ``None`` when there is no usable video.
    The copy is skipped when an identical file (same size and modification time) is already there.
    """
    src = Path(source) if source is not None else BACKGROUND_VIDEO_PATH
    dest_dir = Path(static_dir) if static_dir is not None else STATIC_DIR
    try:
        dest_filename = src.name if src is not None else "iss-background.mp4"
        dest = dest_dir / dest_filename
        if dest.is_file() and dest.stat().st_size > 0:
            return dest.name

        if not src.is_file() or src.stat().st_size == 0:
            return None
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    except OSError:
        return None
    return src.name


def background_html(video_name: str | None, with_script: bool = True) -> str:
    """HTML for the fixed background layer (gradient only when ``video_name`` is None)."""
    layers = '<div class="orbitx-bg__shade"></div>'
    script = ""
    if video_name:
        url = f"{STATIC_URL_PREFIX}/{video_name}"
        video = (
            '<video id="orbitx-bg-{id}" class="orbitx-bg__video{on}" {extra}muted playsinline '
            'preload="auto" tabindex="-1" aria-hidden="true" disablepictureinpicture '
            'disableremoteplayback src="{url}"></video>'
        )
        layers = (
            video.format(id="a", on=" is-on", extra="autoplay loop ", url=url)
            + video.format(id="b", on="", extra="", url=url)
            + layers
        )
        if with_script:
            script = f"<script>{_JS_PATH.read_text(encoding='utf-8')}</script>"
    return f'<div class="orbitx-bg" aria-hidden="true">{layers}</div>{script}'


def _html_runs_scripts() -> bool:
    """Older Streamlit versions cannot run scripts in ``st.html``; the native loop is used then."""
    return "unsafe_allow_javascript" in inspect.signature(st.html).parameters


def render_background() -> None:
    """Insert the background layer. Call first in the script, on every rerun."""
    video_name = sync_video()
    scripts = bool(video_name) and _html_runs_scripts()
    with st.container(key="orbitx_bg"):
        if scripts:
            st.html(background_html(video_name), unsafe_allow_javascript=True)
        else:
            st.html(background_html(video_name, with_script=False))
