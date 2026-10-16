"""The offline-safe track plot: no network, correct antimeridian handling, honest labels."""

from datetime import timedelta

import numpy as np
import pytest

from backend import orbital_engine as engine
from frontend.charts import track_figure
from backend.models import Observer


@pytest.fixture(scope="module")
def track_and_position(sample_tle):
    satellite = engine.build_satellite(sample_tle)
    start = sample_tle.epoch_utc + timedelta(hours=1)
    return engine.predict_track(satellite, start, 600, 60), engine.compute_position(satellite, start)


def test_track_is_split_at_the_antimeridian(track_and_position):
    track, position = track_and_position
    figure = track_figure(track, position)
    lines = [t for t in figure.data if t.mode == "lines"]
    assert len(lines) >= 2, "a 10-hour track must cross +/-180 at least once"
    for line in lines:
        assert np.max(np.abs(np.diff(line.x))) < 180, "a segment sweeps across the whole map"
        assert max(line.x) <= 180 and min(line.x) >= -180


def test_marks_the_iss_and_optional_observer(track_and_position):
    track, position = track_and_position
    figure = track_figure(track, position)
    markers = [t for t in figure.data if t.mode == "markers"]
    assert [m.name for m in markers] == ["ISS now"]
    assert markers[0].x == (position.longitude_deg,) and markers[0].y == (position.latitude_deg,)

    observer = Observer("Test city", 17.6868, 83.2185)
    names = [t.name for t in track_figure(track, position, observer).data if t.mode == "markers"]
    assert names == ["ISS now", "Test city"]


def test_axes_cover_the_globe_and_name_their_units(track_and_position):
    track, position = track_and_position
    layout = track_figure(track, position).layout
    assert tuple(layout.xaxis.range) == (-180, 180) and tuple(layout.yaxis.range) == (-90, 90)
    assert "Longitude" in layout.xaxis.title.text and "Latitude" in layout.yaxis.title.text
