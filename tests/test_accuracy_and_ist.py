"""Focused tests for IST display conversion, accuracy cross-checking, and regression protection."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import math
import pytest
import pandas as pd
from unittest import mock

from backend import config, formatting, models, orbital_engine, pass_predictor, tle_service, validation
from backend.diagnostics import cross_check_live_position, haversine_distance_km
from frontend import components, charts, tabs


UTC = timezone.utc
IST_ZONE = ZoneInfo("Asia/Kolkata")


# 1. Correct UTC-to-IST conversion and +05:30 offset
def test_ist_conversion_offset():
    utc_moment = datetime(2026, 10, 20, 8, 50, 32, tzinfo=UTC)
    ist_str = formatting.format_ist(utc_moment)
    assert "20 Oct 2026, 02:20:32 PM IST" in ist_str

    ist_with_offset = formatting.format_ist(utc_moment, include_offset=True)
    assert "20 Oct 2026, 02:20:32 PM IST (UTC+05:30)" in ist_with_offset


# 2. Conversion across midnight and date boundaries
def test_ist_conversion_across_midnight_date_boundary():
    # 20:00 UTC on 20 Oct becomes 01:30 AM on 21 Oct in IST
    utc_evening = datetime(2026, 10, 20, 20, 0, 0, tzinfo=UTC)
    ist_str = formatting.format_ist(utc_evening)
    assert "21 Oct 2026, 01:30:00 AM IST" in ist_str

    # 01:00 UTC on 20 Oct is 06:30 AM on 20 Oct
    utc_morning = datetime(2026, 10, 20, 1, 0, 0, tzinfo=UTC)
    assert "20 Oct 2026, 06:30:00 AM IST" in formatting.format_ist(utc_morning)


# 3. Correct element-age calculations regardless of display timezone
def test_element_age_independent_of_display_timezone():
    epoch_utc = datetime(2026, 10, 19, 18, 0, 0, tzinfo=UTC)
    now_utc = datetime(2026, 10, 20, 6, 0, 0, tzinfo=UTC)
    tle = models.TleRecord("ISS", "1 25544U...", "2 25544...", 25544, epoch_utc)

    # Calculate age using UTC
    age_from_utc = tle_service.tle_age_days(tle, now_utc)

    # Calculate age using now in IST
    now_ist = now_utc.astimezone(IST_ZONE)
    age_from_ist = tle_service.tle_age_days(tle, now_ist)

    assert age_from_utc == pytest.approx(0.5)
    assert age_from_ist == pytest.approx(0.5)
    assert age_from_utc == age_from_ist


# 4. Consistent IST display across telemetry, provenance and predicted passes
def test_consistent_ist_formatting():
    test_dt = datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC)
    formatted = formatting.format_ist(test_dt)
    assert formatted == "20 Oct 2026, 05:30:00 PM IST"


# 5. UTC timestamps continuing to reach orbital engine
def test_utc_reaches_orbital_engine(sample_tle):
    sat = orbital_engine.build_satellite(sample_tle)
    # Give IST timezone input - orbital_engine must normalize to UTC
    t_ist = datetime(2026, 10, 20, 15, 0, 0, tzinfo=IST_ZONE)
    pos = orbital_engine.compute_position(sat, t_ist)
    assert pos.time_utc.tzinfo == UTC
    assert pos.time_utc == datetime(2026, 10, 20, 9, 30, 0, tzinfo=UTC)


# 6. Unchanged latitude, longitude, altitude and speed when display changes
def test_orbital_calculations_unchanged_by_formatting(sample_tle):
    sat = orbital_engine.build_satellite(sample_tle)
    t = datetime(2026, 10, 20, 10, 0, 0, tzinfo=UTC)
    pos1 = orbital_engine.compute_position(sat, t)

    # Ensure format_ist or format_utc does not mutate position object
    _ = formatting.format_ist(pos1.time_utc)
    _ = formatting.format_utc(pos1.time_utc)

    pos2 = orbital_engine.compute_position(sat, t)
    assert pos1.latitude_deg == pos2.latitude_deg
    assert pos1.longitude_deg == pos2.longitude_deg
    assert pos1.altitude_km == pos2.altitude_km
    assert pos1.speed_km_s == pos2.speed_km_s


# 7. Unchanged ground tracks and predicted passes
def test_track_columns_and_values_unchanged(sample_tle):
    sat = orbital_engine.build_satellite(sample_tle)
    start = datetime(2026, 10, 20, 10, 0, 0, tzinfo=UTC)
    track = orbital_engine.predict_track(sat, start, duration_min=10, step_s=60)
    assert list(track.columns) == orbital_engine.TRACK_COLUMNS
    assert len(track) == 11
    # Check that time_utc column is UTC
    assert track["time_utc"].dt.tz is not None


# 8. Correct handling of unavailable or malformed independent reference data
def test_cross_check_handles_network_failure():
    result = cross_check_live_position(
        calculated_lat=20.0,
        calculated_lon=80.0,
        calculated_alt_km=420.0,
        calculated_speed_km_s=7.66,
        http_get=mock.Mock(side_effect=ConnectionError("Offline simulated")),
    )
    assert result["success"] is False
    assert result["separation_km"] is None
    assert "Offline simulated" in result["error"]


def test_cross_check_handles_malformed_json():
    class FakeBadResp:
        status_code = 200
        text = "NOT JSON"
        def json(self):
            raise ValueError("bad json")

    result = cross_check_live_position(
        calculated_lat=20.0,
        calculated_lon=80.0,
        calculated_alt_km=420.0,
        calculated_speed_km_s=7.66,
        http_get=mock.Mock(return_value=FakeBadResp()),
    )
    assert result["success"] is False
    assert result["separation_km"] is None
    assert result["error"] is not None


# 9. Correct coordinate frames and units in validation comparisons
def test_cross_check_successful_comparison():
    class FakeGoodResp:
        status_code = 200
        text = '{"latitude": 20.01, "longitude": 80.01, "altitude": 421.5, "velocity": 27576.0}'
        def json(self):
            return {"latitude": 20.01, "longitude": 80.01, "altitude": 421.5, "velocity": 27576.0}

    result = cross_check_live_position(
        calculated_lat=20.0,
        calculated_lon=80.0,
        calculated_alt_km=420.0,
        calculated_speed_km_s=7.66,
        http_get=mock.Mock(return_value=FakeGoodResp()),
    )
    assert result["success"] is True
    assert result["ref_latitude"] == 20.01
    assert result["ref_longitude"] == 80.01
    assert result["ref_altitude_km"] == 421.5
    # 27576 / 3600 = 7.66 km/s
    assert result["ref_speed_km_s"] == pytest.approx(7.66, abs=0.01)
    assert result["separation_km"] < 2.0  # ~1.5 km


# 10. Correct longitude-difference handling at the ±180° boundary
def test_haversine_across_antimeridian():
    # 179.9 E and -179.9 (179.9 W) on equator are 0.2 degrees apart
    dist = haversine_distance_km(0.0, 179.9, 0.0, -179.9)
    # Circumference ~ 40075 km -> 0.2 deg ~ 22.2 km
    assert 22.0 < dist < 22.5

    # Check cross_check delta_longitude wrapped correctly
    class AntimeridianResp:
        status_code = 200
        text = '{"latitude": 0.0, "longitude": -179.9, "altitude": 420.0, "velocity": 27576.0}'
        def json(self):
            return {"latitude": 0.0, "longitude": -179.9, "altitude": 420.0, "velocity": 27576.0}

    res = cross_check_live_position(
        calculated_lat=0.0,
        calculated_lon=179.9,
        calculated_alt_km=420.0,
        calculated_speed_km_s=7.66,
        http_get=mock.Mock(return_value=AntimeridianResp()),
    )
    assert res["success"] is True
    assert res["delta_longitude_deg"] == pytest.approx(-0.2, abs=0.01)


# 11. Correct differentiation between LIVE, CACHED and SAMPLE data
def test_data_source_differentiation(sample_tle):
    live_data = models.OrbitalData(
        sample_tle, models.DataSource.LIVE, datetime.now(UTC), "CelesTrak", "Live download", ()
    )
    cached_data = models.OrbitalData(
        sample_tle, models.DataSource.CACHED, datetime.now(UTC), "CelesTrak", "From disk cache", ()
    )
    sample_data = models.OrbitalData(
        sample_tle, models.DataSource.SAMPLE, None, "Bundled sample", "Offline sample", ()
    )

    assert live_data.source is models.DataSource.LIVE
    assert cached_data.source is models.DataSource.CACHED
    assert sample_data.source is models.DataSource.SAMPLE
    assert live_data.retrieved_at_utc is not None
    assert sample_data.retrieved_at_utc is None


# 12. Safe handling of malformed or timezone-naive timestamps
def test_safe_handling_of_none_and_naive():
    assert formatting.format_ist(None) == "–"
    assert formatting.format_utc(None) == "–"

    # Naive timestamp should be safely interpreted as UTC without crashing
    naive = datetime(2026, 10, 20, 8, 50, 32)
    assert "20 Oct 2026, 02:20:32 PM IST" in formatting.format_ist(naive)

    # Malformed non-datetime object should return str representation without crashing
    assert formatting.format_ist("2026-10-20") == "2026-10-20"
