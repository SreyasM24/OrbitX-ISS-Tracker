"""Phase 1 baseline tests: the existing modules import and behave sensibly offline."""

from datetime import datetime, timedelta, timezone

import pytest

from orbitx import config, orbital_engine as eng, pass_predictor as pp, tle_service as tle
from orbitx.models import DataSource
from orbitx.validation import ValidationError, ensure_utc, tle_checksum_ok


@pytest.fixture(scope="module")
def sample():
    return tle.load_sample_tle()


@pytest.fixture(scope="module")
def satellite(sample):
    return eng.build_satellite(sample)


def test_sample_tle_parses_and_checksums(sample):
    assert sample.catalog_number == config.ISS_NORAD_ID
    assert tle_checksum_ok(sample.line1) and tle_checksum_ok(sample.line2)
    assert sample.epoch_utc.tzinfo is not None


def test_corrupted_tle_rejected(sample):
    bad = sample.line1[:-1] + str((int(sample.line1[-1]) + 1) % 10)
    with pytest.raises(tle.TleParseError):
        tle.parse_tle_text(f"ISS (ZARYA)\n{bad}\n{sample.line2}")


def test_wrong_satellite_rejected(sample):
    with pytest.raises(tle.TleParseError):
        tle.parse_tle_text(f"ISS (ZARYA)\n{sample.line1}\n{sample.line2}", expected_catalog_number=1)


def test_naive_datetime_rejected():
    with pytest.raises(ValidationError):
        ensure_utc(datetime(2026, 10, 21, 9, 30))


def test_position_is_physically_plausible(satellite, sample):
    pos = eng.compute_position(satellite, sample.epoch_utc + timedelta(minutes=30))
    assert -52.0 <= pos.latitude_deg <= 52.0  # bounded by orbital inclination (51.6 deg)
    assert -180.0 <= pos.longitude_deg <= 180.0
    assert 380.0 < pos.altitude_km < 460.0  # regression: used to be 0.0 (subpoint elevation)
    assert 7.5 < pos.speed_km_s < 7.8


def test_track_shape_and_altitude(satellite, sample):
    df = eng.predict_track(satellite, sample.epoch_utc, 180, 60)
    assert list(df.columns) == eng.TRACK_COLUMNS
    assert len(df) == 181
    assert df["altitude_km"].between(380, 460).all()


def test_track_request_bounds(satellite, sample):
    with pytest.raises(ValidationError):
        eng.predict_track(satellite, sample.epoch_utc, 24 * 60, 10)  # too many points


def test_antimeridian_segments_do_not_span_the_globe(satellite, sample):
    df = eng.predict_track(satellite, sample.epoch_utc, 180, 60)
    for segment in eng.split_track_segments(df):
        lons = [lon for _, lon in segment]
        assert all(abs(b - a) < 180.0 for a, b in zip(lons, lons[1:]))


def test_find_passes_vizag(satellite, sample):
    lat, lon = config.EXAMPLE_CITIES[config.DEFAULT_CITY]
    observer = pp.make_observer("Vizag", lat, lon)
    passes = pp.find_passes(satellite, observer, sample.epoch_utc, 48, 10.0)
    assert passes, "ISS should pass over India at least once in 48 h"
    for p in passes:
        if p.is_complete:
            assert p.rise_time_utc < p.culmination_time_utc < p.set_time_utc
            assert p.max_elevation_deg >= 10.0 - 1e-6
            assert p.duration_s < 20 * 60


def test_offline_orbital_data_is_labelled_sample(tmp_path):
    data = tle.get_orbital_data(offline=True, cache_path=tmp_path / "none.json")
    assert data.source is DataSource.SAMPLE
    assert "NOT live" in data.status_message


def test_failed_download_falls_back_honestly(tmp_path):
    def boom(*a, **k):
        raise tle.requests.exceptions.ConnectionError()

    data = tle.get_orbital_data(http_get=boom, cache_path=tmp_path / "none.json")
    assert data.source is DataSource.SAMPLE
    assert any("Live download failed" in w for w in data.warnings)


def test_stale_elements_warn(sample):
    later = sample.epoch_utc + timedelta(days=20)
    assert "illustrative" in tle.freshness_warning(sample, later)


def test_ist_is_display_only_offset():
    assert config.IST.utcoffset(None) == timedelta(hours=5, minutes=30)
    assert datetime(2026, 10, 21, 9, 30, tzinfo=timezone.utc).astimezone(config.IST).hour == 15
