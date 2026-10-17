"""Data-source honesty: live / cached / sample labelling with every HTTP call mocked."""

from datetime import timedelta
from unittest import mock

import pytest
import requests

from conftest import FakeResponse
from backend import tle_service as ts
from backend.models import DataSource, Freshness, OrbitalData
from frontend import components

pytestmark = pytest.mark.usefixtures("no_network")


def never_called(*args, **kwargs):
    raise AssertionError("network must not be used")


def test_offline_with_nothing_cached_uses_sample_and_says_so(tmp_path):
    data = ts.get_orbital_data(offline=True, cache_path=tmp_path / "c.json", http_get=never_called)
    assert data.source is DataSource.SAMPLE and data.retrieved_at_utc is None
    assert "NOT live" in data.status_message


def test_live_download_is_labelled_live_and_cached(tmp_path, sample_text, sample_tle):
    cache = tmp_path / "c.json"
    now = sample_tle.epoch_utc + timedelta(hours=1)
    data = ts.get_orbital_data(now=now, cache_path=cache, http_get=lambda *a, **k: FakeResponse(sample_text))
    assert data.source is DataSource.LIVE and data.retrieved_at_utc == now
    assert cache.exists()


def test_fresh_cache_is_reused_without_a_request(tmp_path, sample_text, sample_tle):
    cache = tmp_path / "c.json"
    now = sample_tle.epoch_utc + timedelta(hours=1)
    ts.get_orbital_data(now=now, cache_path=cache, http_get=lambda *a, **k: FakeResponse(sample_text))
    again = ts.get_orbital_data(now=now + timedelta(minutes=30), cache_path=cache, http_get=never_called)
    assert again.source is DataSource.CACHED


def test_force_refresh_ignores_fresh_cache(tmp_path, sample_text, sample_tle):
    cache = tmp_path / "c.json"
    now = sample_tle.epoch_utc + timedelta(hours=1)
    ts.get_orbital_data(now=now, cache_path=cache, http_get=lambda *a, **k: FakeResponse(sample_text))
    again = ts.get_orbital_data(
        now=now + timedelta(minutes=5), cache_path=cache, force_refresh=True,
        http_get=lambda *a, **k: FakeResponse(sample_text),
    )
    assert again.source is DataSource.LIVE


def test_offline_prefers_old_cache_over_sample(tmp_path, sample_text, sample_tle):
    cache = tmp_path / "c.json"
    now = sample_tle.epoch_utc + timedelta(hours=1)
    ts.get_orbital_data(now=now, cache_path=cache, http_get=lambda *a, **k: FakeResponse(sample_text))
    data = ts.get_orbital_data(now=now + timedelta(days=1), cache_path=cache, offline=True, http_get=never_called)
    assert data.source is DataSource.CACHED
    assert "Offline mode" in data.status_message


def raise_connection_error(*args, **kwargs):
    raise requests.exceptions.ConnectionError()


def raise_timeout(*args, **kwargs):
    raise requests.exceptions.Timeout()


@pytest.mark.parametrize(
    "getter,reason",
    [
        (raise_connection_error, "no network"),
        (raise_timeout, "timed out"),
        (lambda *a, **k: FakeResponse("Service Unavailable", 503), "HTTP 503"),
        (lambda *a, **k: FakeResponse("<html>Not a TLE</html>"), "No two-line"),
        (lambda *a, **k: FakeResponse(""), "No two-line"),
    ],
)
def test_failed_download_falls_back_to_sample_with_reason(tmp_path, getter, reason):
    data = ts.get_orbital_data(cache_path=tmp_path / "c.json", http_get=getter)
    assert data.source is DataSource.SAMPLE
    assert any("Live download failed" in w and reason in w for w in data.warnings)


def test_failed_download_uses_stale_cache_before_sample(tmp_path, sample_text, sample_tle):
    cache = tmp_path / "c.json"
    now = sample_tle.epoch_utc + timedelta(hours=1)
    ts.get_orbital_data(now=now, cache_path=cache, http_get=lambda *a, **k: FakeResponse(sample_text))
    data = ts.get_orbital_data(now=now + timedelta(hours=5), cache_path=cache, http_get=raise_connection_error)
    assert data.source is DataSource.CACHED
    assert "unavailable" in data.status_message


def test_wrong_satellite_data_is_rejected(tmp_path):
    other = (
        "NOT THE ISS\n"
        "1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753\n"
        "2 00005  34.2682 348.7242 1859667 331.7664  19.3264 10.82419157413667\n"
    )
    data = ts.get_orbital_data(cache_path=tmp_path / "c.json", http_get=lambda *a, **k: FakeResponse(other))
    assert data.source is DataSource.SAMPLE
    assert any("Live download failed" in w for w in data.warnings)


def test_corrupt_cache_is_ignored_with_a_warning(tmp_path):
    cache = tmp_path / "c.json"
    cache.write_text("{not json", encoding="utf-8")
    data = ts.get_orbital_data(offline=True, cache_path=cache)
    assert data.source is DataSource.SAMPLE
    assert any("Ignoring local cache" in w for w in data.warnings)


def test_unwritable_cache_does_not_break_a_good_download(tmp_path, sample_text):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    data = ts.get_orbital_data(cache_path=blocker / "sub" / "c.json", http_get=lambda *a, **k: FakeResponse(sample_text))
    assert data.source is DataSource.LIVE
    assert any("Could not write the local cache" in w for w in data.warnings)


def test_expired_elements_carry_an_illustrative_warning(tmp_path, sample_tle):
    data = ts.get_orbital_data(offline=True, cache_path=tmp_path / "c.json", now=sample_tle.epoch_utc + timedelta(days=30))
    assert any("illustrative" in w for w in data.warnings)


def test_naive_now_is_rejected(tmp_path):
    from datetime import datetime

    from backend.validation import ValidationError

    with pytest.raises(ValidationError):
        ts.get_orbital_data(offline=True, now=datetime(2026, 10, 21), cache_path=tmp_path / "c.json")


def test_primary_url_timeout_falls_back_to_secondary_and_succeeds(tmp_path, sample_text):
    calls = []

    def mock_getter(target_url, **kwargs):
        calls.append(target_url)
        if len(calls) == 1:
            raise requests.exceptions.Timeout("primary timed out")
        return FakeResponse(sample_text)

    tle = ts.fetch_live_tle(http_get=mock_getter)
    assert tle.catalog_number == 25544
    assert len(calls) == 2


def test_multi_satellite_tle_finds_iss_among_others(sample_text):
    # Valid line checksums for a multi-satellite feed fixture:
    # 48274 checksums:
    # Line 1: '1 48274U 21035A   24001.50000000  .00010000  00000-0  10000-3 0  9997'
    # Line 2: '2 48274  41.4700 100.0000 0005000 120.0000 240.0000 15.60000000100009'
    other = (
        "CSS (TIANHE)\n"
        "1 48274U 21035A   24001.50000000  .00010000  00000-0  10000-3 0  9997\n"
        "2 48274  41.4700 100.0000 0005000 120.0000 240.0000 15.60000000100009\n"
    )
    combined = f"{other}\n{sample_text}"
    tle = ts.parse_tle_text(combined)
    assert tle.catalog_number == 25544
    assert "ISS" in tle.name


def test_celestrak_block_falls_back_to_secondary_mirror(tmp_path, sample_text):
    calls = []

    def mock_getter(target_url, **kwargs):
        calls.append(target_url)
        if "celestrak" in target_url:
            raise requests.exceptions.Timeout("celestrak blocked in cloud")
        return FakeResponse(sample_text)

    data = ts.get_orbital_data(cache_path=tmp_path / "c.json", http_get=mock_getter)
    assert data.source is DataSource.LIVE
    assert "ARISS" in data.source_label or "WhereTheISS.at" in data.source_label
    assert len(calls) == 2


def test_celestrak_and_ariss_fail_falls_back_to_wheretheiss(tmp_path, sample_text):
    calls = []

    def mock_getter(target_url, **kwargs):
        calls.append(target_url)
        if "celestrak" in target_url or "ariss" in target_url:
            raise requests.exceptions.Timeout("blocked in cloud")
        return FakeResponse(sample_text)

    data = ts.get_orbital_data(cache_path=tmp_path / "c.json", http_get=mock_getter)
    assert data.source is DataSource.LIVE
    assert "WhereTheISS.at" in data.source_label
    assert len(calls) == 3


def test_cache_preserves_source_url_and_displays_cached_mirror_label(tmp_path, sample_text, sample_tle):
    cache = tmp_path / "c.json"
    now = sample_tle.epoch_utc + timedelta(hours=1)

    def mock_ariss(target_url, **kwargs):
        if "ariss" in target_url:
            return FakeResponse(sample_text)
        raise requests.exceptions.Timeout("timeout")

    data = ts.get_orbital_data(now=now, cache_path=cache, http_get=mock_ariss)
    assert data.source is DataSource.LIVE
    assert "ARISS" in data.source_label

    # Second load within 2-hour window uses cache with truthful ARISS cached label
    cached_data = ts.get_orbital_data(
        now=now + timedelta(minutes=15),
        cache_path=cache,
        http_get=never_called,
    )
    assert cached_data.source is DataSource.CACHED
    assert "ARISS" in cached_data.source_label


def test_primary_malformed_falls_back_to_valid_secondary(tmp_path, sample_text):
    calls = []

    def mock_malformed_primary(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return FakeResponse("Corrupted garbage header\n1 99999 ...\n2 99999 ...")
        return FakeResponse(sample_text)

    tle = ts.fetch_live_tle(http_get=mock_malformed_primary)
    assert tle.catalog_number == 25544
    assert len(calls) == 2


def test_all_endpoints_failing_provides_diagnostic_breakdown(tmp_path):
    def mock_failing(url, **kwargs):
        if "stations" in url:
            return FakeResponse("Bad gateway", status_code=502)
        if "wheretheiss" in url:
            return FakeResponse("Not a TLE")
        raise requests.exceptions.Timeout("timed out")

    data = ts.get_orbital_data(cache_path=tmp_path / "c.json", http_get=mock_failing)
    assert data.source is DataSource.SAMPLE
    warn_text = " ".join(data.warnings)
    assert "Live download failed" in warn_text
    assert "timed out" in warn_text
    assert "HTTP 502" in warn_text


def test_sample_freshness_status_does_not_display_green_fresh(sample_tle):
    import unittest.mock as mock
    from frontend import components
    from backend.models import Freshness, OrbitalData

    data = OrbitalData(
        tle=sample_tle,
        source=DataSource.SAMPLE,
        retrieved_at_utc=None,
        source_label="Bundled sample",
        status_message="Offline sample",
        warnings=(),
    )

    calls = []

    class DummyCol:
        def markdown(self, text): calls.append(("markdown", text))
        def write(self, text): calls.append(("write", text))
        def success(self, text): calls.append(("success", text))
        def warning(self, text): calls.append(("warning", text))
        def error(self, text): calls.append(("error", text))
        def info(self, text): calls.append(("info", text))

    class DummyContainer:
        def __enter__(self): return self
        def __exit__(self, *a): pass

    with mock.patch("streamlit.container", return_value=DummyContainer()), \
         mock.patch("streamlit.expander", return_value=DummyContainer()), \
         mock.patch("streamlit.columns", return_value=(DummyCol(), DummyCol(), DummyCol())), \
         mock.patch("streamlit.caption"), \
         mock.patch("streamlit.markdown"), \
         mock.patch("streamlit.warning"):
        components.render_status(data, sample_tle, age_days=0.5, freshness=Freshness.FRESH)

    success_calls = [text for op, text in calls if op == "success"]
    assert "FRESH" not in success_calls
    warning_calls = [text for op, text in calls if op == "warning"]
    assert any("SAMPLE / NOT LIVE" in t for t in warning_calls)


def test_probe_endpoint_success(sample_text):
    from backend import diagnostics
    res = diagnostics.probe_endpoint("https://example.com/tle", http_get=lambda *a, **k: FakeResponse(sample_text))
    assert res["phase"] == "success"
    assert res["status_code"] == 200
    assert res["catalog_number"] == 25544
    assert res["error"] is None


def test_probe_endpoint_timeout():
    from backend import diagnostics
    res = diagnostics.probe_endpoint("https://example.com/tle", http_get=raise_timeout)
    assert res["phase"] == "networking"
    assert res["status_code"] is None
    assert "timed out" in res["error"]


def test_probe_endpoint_parse_error():
    from backend import diagnostics
    res = diagnostics.probe_endpoint("https://example.com/tle", http_get=lambda *a, **k: FakeResponse("invalid data"))
    assert res["phase"] == "validation"
    assert res["status_code"] == 200
    assert "validation error" in res["error"]


def test_render_status_authoritative_app_version_regression(sample_tle):
    """Regression test: render_status must render canonical APP_VERSION without AttributeError."""
    from backend.version import APP_VERSION
    assert APP_VERSION == "v1.2.1"
    data = OrbitalData(
        sample_tle, DataSource.SAMPLE, None, "Bundled sample",
        "Bundled sample", (), diagnostics=(), cache_used=False,
    )
    calls = []
    class DummyCol:
        def markdown(self, text): calls.append(("markdown", text))
        def write(self, text): calls.append(("write", text))
        def success(self, text): calls.append(("success", text))
        def warning(self, text): calls.append(("warning", text))
        def error(self, text): calls.append(("error", text))
        def info(self, text): calls.append(("info", text))

    class DummyContainer:
        def __enter__(self): return self
        def __exit__(self, *a): pass

    markdown_calls = []
    def fake_markdown(text):
        markdown_calls.append(text)

    with mock.patch("streamlit.container", return_value=DummyContainer()), \
         mock.patch("streamlit.expander", return_value=DummyContainer()), \
         mock.patch("streamlit.columns", return_value=(DummyCol(), DummyCol(), DummyCol())), \
         mock.patch("streamlit.caption"), \
         mock.patch("streamlit.markdown", side_effect=fake_markdown), \
         mock.patch("streamlit.warning"):
        components.render_status(data, sample_tle, age_days=0.5, freshness=Freshness.FRESH)

    version_markdown = [t for t in markdown_calls if "Application Version:" in t]
    assert len(version_markdown) == 1
    assert APP_VERSION in version_markdown[0]


def test_failed_fetch_then_successful_fetch_recovers(tmp_path, sample_text, sample_tle):
    """Verify that a failed fetch does not poison the state: subsequent live request succeeds."""
    cache = tmp_path / "c.json"
    now = sample_tle.epoch_utc + timedelta(hours=1)

    # 1. First fetch fails
    failed_data = ts.get_orbital_data(now=now, cache_path=cache, http_get=raise_connection_error)
    assert failed_data.source is DataSource.SAMPLE

    # 2. Network recovers
    recovered_data = ts.get_orbital_data(
        now=now + timedelta(seconds=10), cache_path=cache,
        http_get=lambda *a, **k: FakeResponse(sample_text),
    )
    assert recovered_data.source is DataSource.LIVE
    assert recovered_data.tle.catalog_number == 25544


def test_csv_export_includes_provenance_column(sample_tle):
    """Verify that track dataframe export includes data_source provenance."""
    import pandas as pd
    from frontend import tabs

    track = pd.DataFrame({
        "time_utc": ["2026-10-17 12:00:00 UTC"],
        "latitude_deg": [15.5],
        "longitude_deg": [45.2],
        "altitude_km": [420.0],
        "speed_km_s": [7.66],
    })

    captured_csv = []
    def fake_download_button(label, data, file_name, mime):
        captured_csv.append(data)

    with mock.patch("streamlit.plotly_chart"), \
         mock.patch("streamlit.caption"), \
         mock.patch("streamlit.expander", return_value=mock.MagicMock()), \
         mock.patch("streamlit.dataframe"), \
         mock.patch("streamlit.download_button", side_effect=fake_download_button):
        tabs.render_charts_tab(track, illustrative=False, source_label="LIVE")

    assert len(captured_csv) == 1
    assert "data_source" in captured_csv[0]
    assert "LIVE" in captured_csv[0]


def test_background_video_and_gradient_fallback():
    """Verify background HTML helper renders gradient when None and video tags when provided."""
    from frontend.background import background_html

    # Fallback gradient when video is missing/None
    gradient_only = background_html(None, with_script=False)
    assert '<div class="orbitx-bg__shade"></div>' in gradient_only
    assert '<video' not in gradient_only

    # Full video layer when video name provided
    video_html = background_html("test.mp4", with_script=False)
    assert '<video' in video_html
    assert "app/static/test.mp4" in video_html


def test_all_production_modules_import_cleanly():
    """Verify all project modules import cleanly without circular dependencies or missing attributes."""
    from backend.version import APP_VERSION as canonical_app_version, __version__ as canonical_version
    from backend.config import APP_VERSION as config_app_version
    from backend import APP_VERSION as pkg_app_version
    from backend import __version__ as pkg_version

    assert canonical_version == "1.2.1"
    assert canonical_app_version == "v1.2.1"
    assert config_app_version == "v1.2.1"
    assert pkg_app_version == "v1.2.1"
    assert pkg_version == "1.2.1"

    import backend
    import backend.version
    import backend.config
    import backend.diagnostics
    import backend.formatting
    import backend.missions
    import backend.models
    import backend.orbital_engine
    import backend.pass_predictor
    import backend.tle_service
    import backend.validation
    import frontend.background
    import frontend.charts
    import frontend.components
    import frontend.data
    import frontend.map_view
    import frontend.sidebar
    import frontend.tabs
    import frontend.theme

    # Verify modules point inside the repository (not an unexpected third-party namespace)
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[1]
    assert Path(backend.__file__).resolve().is_relative_to(repo_root)
    assert Path(backend.version.__file__).resolve().is_relative_to(repo_root)

    assert backend.__version__ == "1.2.1"
    assert backend.config.APP_VERSION == "v1.2.1"
    assert backend.APP_VERSION == "v1.2.1"
    assert hasattr(backend.models, "OrbitalData")
    assert hasattr(backend.tle_service, "get_orbital_data")
    assert hasattr(frontend.components, "APP_VERSION")
    assert frontend.components.APP_VERSION == "v1.2.1"


def test_version_footer_renders_correctly():
    """Verify render_footer displays canonical APP_VERSION and attribution."""
    from backend.version import APP_VERSION

    rendered_markdown = []
    def fake_markdown(text, unsafe_allow_html=False):
        rendered_markdown.append(text)

    with mock.patch("streamlit.markdown", side_effect=fake_markdown):
        components.render_footer()

    assert len(rendered_markdown) == 1
    assert f"OrbitX {APP_VERSION}" in rendered_markdown[0]
    assert "GITAM Aero Astro Club (GAAC)" in rendered_markdown[0]


def test_fresh_subprocess_import_matrix():
    """Verify imports succeed cleanly in fresh, unpolluted Python processes regardless of order."""
    import subprocess
    import sys
    from pathlib import Path

    repo_dir = str(Path(__file__).resolve().parents[1])

    snippets = [
        # Streamlit Cloud load order: frontend components first
        "import sys; sys.path.insert(0, r'%s'); from frontend import components; from backend.config import APP_VERSION; print(APP_VERSION)" % repo_dir,
        # Backend config first then frontend
        "import sys; sys.path.insert(0, r'%s'); from backend.config import APP_VERSION; from frontend import components; print(components.APP_VERSION)" % repo_dir,
        # Canonical version leaf module first
        "import sys; sys.path.insert(0, r'%s'); from backend.version import APP_VERSION; import backend; print(backend.APP_VERSION)" % repo_dir,
        # Frontend app entry module
        "import sys; sys.path.insert(0, r'%s'); import frontend.app; print('Loaded frontend.app successfully')" % repo_dir,
    ]

    for snippet in snippets:
        res = subprocess.run(
            [sys.executable, "-c", snippet],
            capture_output=True,
            text=True,
            check=False,
        )
        assert res.returncode == 0, f"Subprocess failed with stderr:\n{res.stderr}"


def test_app_starts_when_all_endpoints_unavailable(tmp_path):
    """Verify the Streamlit dashboard starts and renders cleanly when all network calls fail."""
    from pathlib import Path
    from streamlit.testing.v1 import AppTest

    app_path = str(Path(__file__).resolve().parents[1] / "frontend" / "app.py")
    app = AppTest.from_file(app_path, default_timeout=20)
    # Block all live downloads so it exercises offline fallback
    with mock.patch("requests.get", side_effect=ConnectionError("Cloud network isolated")):
        app.run()

    assert not app.exception
    # Ensure tabs rendered
    tab_labels = [t.label for t in app.tabs]
    assert len(tab_labels) == 4
