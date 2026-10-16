"""Background-video helpers: copying to static/, graceful absence, and the generated HTML."""

from __future__ import annotations

from orbitx.ui import background


def test_missing_video_gives_gradient_only_layer(tmp_path):
    assert background.sync_video(tmp_path / "nope.mp4", tmp_path / "static") is None
    html = background.background_html(None)
    assert "<video" not in html and "<script" not in html and "orbitx-bg__shade" in html


def test_empty_video_file_is_ignored(tmp_path):
    empty = tmp_path / "empty.mp4"
    empty.write_bytes(b"")
    assert background.sync_video(empty, tmp_path / "static") is None


def test_video_is_copied_once_and_reused(tmp_path):
    src = tmp_path / "clip.mp4"
    src.write_bytes(b"not-really-video")
    static = tmp_path / "static"
    assert background.sync_video(src, static) == "clip.mp4"
    copied = static / "clip.mp4"
    assert copied.read_bytes() == b"not-really-video"
    first = copied.stat().st_mtime_ns
    assert background.sync_video(src, static) == "clip.mp4"
    assert copied.stat().st_mtime_ns == first  # identical file: not copied again


def test_video_html_is_muted_inline_and_inert():
    html = background.background_html("clip.mp4")
    assert html.count("<video") == 2  # two copies for the crossfade
    for needle in ("muted", "playsinline", "autoplay", 'aria-hidden="true"', "app/static/clip.mp4"):
        assert needle in html
    assert "controls" not in html
    assert "<script>" in html
    assert "<script" not in background.background_html("clip.mp4", with_script=False)
