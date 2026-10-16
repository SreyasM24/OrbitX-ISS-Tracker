"""Streamlit AppTest smoke tests. No network; time is frozen relative to the sample TLE epoch.

AppTest runs the script headlessly (no browser). It checks that the app executes and which
elements it produces, not how they look.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
import requests
import streamlit as st
from streamlit.testing.v1 import AppTest

from conftest import FakeResponse
from orbitx import config, tle_service
from orbitx import validation
from orbitx.missions import MISSIONS

APP = str(Path(__file__).resolve().parents[1] / "app.py")
REAL_GET_ORBITAL_DATA = tle_service.get_orbital_data


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path, sample_tle):
    """Frozen clock one hour after the sample epoch, tmp cache, no real network."""
    st.cache_data.clear()
    st.cache_resource.clear()
    monkeypatch.setattr(validation, "utcnow", lambda: sample_tle.epoch_utc + timedelta(hours=1))
    monkeypatch.setattr(requests, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))

    def offline_data(**kwargs):
        kwargs.update(offline=True, cache_path=tmp_path / "cache.json", now=validation.utcnow())
        return REAL_GET_ORBITAL_DATA(**kwargs)

    monkeypatch.setattr(tle_service, "get_orbital_data", offline_data)
    yield
    st.cache_data.clear()


def run(timeout: int = 90) -> AppTest:
    return AppTest.from_file(APP, default_timeout=timeout).run()


def test_app_runs_without_exception_and_shows_structure():
    at = run()
    assert not at.exception
    assert "OrbitX" in at.title[0].value
    assert [t.label for t in at.tabs] == ["🗺️ Map", "📈 Telemetry", "🔭 Passes", "🎯 Missions"]
    labels = {m.label for m in at.metric}
    assert {"Latitude", "Longitude", "Altitude", "Orbital speed"} <= labels


def test_metrics_are_computed_not_hardcoded_and_plausible():
    at = run()
    values = {m.label: m.value for m in at.metric}
    assert values["Latitude"].endswith(("N", "S")) and values["Longitude"].endswith(("E", "W"))
    altitude = float(values["Altitude"].split()[0])
    speed = float(values["Orbital speed"].split()[0])
    assert 300 < altitude < 500 and 7.0 < speed < 8.0
    # Same frozen clock => same numbers on a second run: deterministic, not live telemetry.
    assert {m.label: m.value for m in run().metric if m.label in values} == {
        k: v for k, v in values.items()
    }


def test_sample_data_is_labelled_not_live():
    at = run()
    assert any("SAMPLE" in e.value and "NOT live" in e.value for e in at.error)
    assert not any(s.value.startswith("LIVE") for s in at.success)


def test_live_label_when_download_succeeds(monkeypatch, tmp_path, sample_text):
    def live_data(**kwargs):
        kwargs.update(cache_path=tmp_path / "live.json", now=validation.utcnow(),
                      http_get=lambda *a, **k: FakeResponse(sample_text))
        return REAL_GET_ORBITAL_DATA(**kwargs)

    monkeypatch.setattr(tle_service, "get_orbital_data", live_data)
    at = run()
    assert not at.exception
    assert any(s.value.startswith("LIVE") for s in at.success)


def test_failed_download_shows_warning_and_sample(monkeypatch, tmp_path):
    def failing(**kwargs):
        def boom(*a, **k):
            raise requests.exceptions.ConnectionError()

        kwargs.update(cache_path=tmp_path / "x.json", now=validation.utcnow(), http_get=boom)
        return REAL_GET_ORBITAL_DATA(**kwargs)

    monkeypatch.setattr(tle_service, "get_orbital_data", failing)
    at = run()
    assert not at.exception
    assert any("Live download failed" in w.value for w in at.warning)
    assert any("SAMPLE" in e.value for e in at.error)


def test_expired_elements_warn_and_position_is_illustrative(monkeypatch, sample_tle):
    monkeypatch.setattr(validation, "utcnow", lambda: sample_tle.epoch_utc + timedelta(days=20))
    at = run()
    assert not at.exception
    assert any("illustrative" in w.value.lower() for w in at.warning)
    assert any("Illustrative position" in s.value for s in at.subheader)
    assert any(e.value == "EXPIRED" for e in at.error)


def test_default_observer_is_visakhapatnam():
    at = run()
    assert at.selectbox(key="city").value == config.DEFAULT_CITY
    lat, lon = config.EXAMPLE_CITIES[config.DEFAULT_CITY]
    assert at.text_input(key="lat_text").value == f"{lat:.4f}"
    assert at.text_input(key="lon_text").value == f"{lon:.4f}"


def test_choosing_a_city_fills_coordinates():
    at = run()
    at.selectbox(key="city").select("London, United Kingdom").run()
    assert not at.exception
    assert at.text_input(key="lat_text").value == "51.5074"
    assert at.text_input(key="lon_text").value == "-0.1278"


def test_editing_coordinates_switches_to_custom_and_persists_across_reruns():
    at = run()
    at.text_input(key="lat_text").input("12.5").run()
    assert at.selectbox(key="city").value == "Custom location"
    at.selectbox(key="city").select("Custom location")  # unrelated rerun
    at.run()
    assert at.text_input(key="lat_text").value == "12.5"
    assert not at.exception


@pytest.mark.parametrize(
    "key,bad,fragment",
    [("lat_text", "91", "between -90 and 90"), ("lon_text", "", "Longitude is empty"), ("lat_text", "12.", None)],
)
def test_invalid_coordinates_show_errors_without_crashing(key, bad, fragment):
    at = run()
    at.text_input(key=key).input(bad).run()
    assert not at.exception
    if fragment:
        assert any(fragment in e.value for e in at.sidebar.error)
        assert any("Fix the observer location" in w.value for w in at.warning)
    # The map, charts and metrics still work with a bad observer.
    assert {m.label for m in at.metric} >= {"Latitude", "Altitude"}


def test_reset_restores_default_location():
    at = run()
    at.selectbox(key="city").select("Tokyo, Japan").run()
    reset = next(b for b in at.sidebar.button if "Reset" in b.label)
    reset.click().run()
    assert at.selectbox(key="city").value == config.DEFAULT_CITY
    assert at.text_input(key="lat_text").value == "17.6868"


def test_pass_table_is_shown_with_explicit_time_zones():
    at = run()
    assert not at.exception
    frames = [d.value for d in at.dataframe if "Rise (UTC)" in d.value.columns]
    assert frames, "expected a pass table for the default 24 h window"
    assert {"Rise (IST)", "Peak (UTC)", "Set (IST)", "Duration (min)"} <= set(frames[0].columns)


def test_no_pass_state_is_friendly():
    at = run()
    at.sidebar.slider[0].set_value(1)  # 1 h window
    at.sidebar.slider[1].set_value(60)  # 60 deg minimum elevation
    at.run()
    assert not at.exception
    assert any("No passes above 60" in i.value for i in at.info)


def test_utc_only_hides_ist_columns():
    at = run()
    at.sidebar.radio[0].set_value("UTC only").run()
    frames = [d.value for d in at.dataframe if "Rise (UTC)" in d.value.columns]
    assert frames and not any("IST" in c for c in frames[0].columns)


def test_missions_tab_renders_every_guide():
    at = run()
    radio = next(r for r in at.radio if r.label == "Mission")
    for mission in MISSIONS:
        radio.set_value(mission.key).run()
        assert not at.exception
        assert any(mission.title in m.value and "Learning objective" in m.value for m in at.markdown)


def test_no_prediction_length_crashes_the_app():
    at = run()
    slider = next(s for s in at.select_slider if "Prediction length" in s.label)
    for minutes in slider.options:
        slider.set_value(minutes).run()
        assert not at.exception


def test_map_tab_offers_a_plot_that_needs_no_internet():
    at = run()
    assert not at.exception
    assert any("without internet" in e.label for e in at.expander)
