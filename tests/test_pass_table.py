"""Pass-table formatting, UTC/IST conversion and truncated-pass handling."""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from orbitx import config
from orbitx.formatting import compass_point
from orbitx.models import SatellitePass
from orbitx.pass_predictor import (
    CULMINATE,
    RISE,
    SET,
    PassEvent,
    assemble_passes,
    passes_to_frame,
)

UTC = timezone.utc
T0 = datetime(2026, 10, 21, 9, 30, 0, tzinfo=UTC)


def full_pass() -> SatellitePass:
    return SatellitePass(T0, T0 + timedelta(minutes=3), T0 + timedelta(minutes=6), 62.34, 315.0, 135.0)


def test_ist_is_utc_plus_5_30():
    row = passes_to_frame([full_pass()]).iloc[0]
    assert row["Rise (UTC)"] == "2026-10-21 09:30:00"
    assert row["Rise (IST)"] == "2026-10-21 15:00:00"
    assert row["Peak (IST)"] == "2026-10-21 15:03:00"
    assert row["Set (IST)"] == "2026-10-21 15:06:00"


def test_ist_conversion_crosses_midnight():
    late = SatellitePass(datetime(2026, 10, 21, 19, 0, tzinfo=UTC), None, None, None)
    assert passes_to_frame([late]).iloc[0]["Rise (IST)"] == "2026-10-22 00:30:00"


def test_non_utc_input_is_normalised():
    ist_time = datetime(2026, 10, 21, 15, 0, tzinfo=config.IST)  # same instant as 09:30 UTC
    item = SatellitePass(ist_time, ist_time, ist_time, 30.0)
    assert passes_to_frame([item]).iloc[0]["Rise (UTC)"] == "2026-10-21 09:30:00"


def test_every_time_column_names_its_zone():
    frame = passes_to_frame([full_pass()])
    time_cols = [c for c in frame.columns if c.startswith(("Rise (", "Peak (", "Set ("))]
    assert len(time_cols) == 6 and all(c.endswith(("(UTC)", "(IST)")) for c in time_cols)


@pytest.mark.parametrize("zones,absent", [(("UTC",), "IST"), (("IST",), "UTC")])
def test_zone_subsets(zones, absent):
    frame = passes_to_frame([full_pass()], zones)
    assert not any(absent in c for c in frame.columns)


@pytest.mark.parametrize("zones", [(), ("PST",), ("UTC", "GMT")])
def test_bad_zones_rejected(zones):
    with pytest.raises(ValueError):
        passes_to_frame([full_pass()], zones)


def test_values_duration_and_directions():
    row = passes_to_frame([full_pass()]).iloc[0]
    assert row["Duration (min)"] == 6.0
    assert row["Max elevation (deg)"] == 62.3
    assert row["Rises toward"] == "NW (315°)" and row["Sets toward"] == "SE (135°)"
    assert row["Note"] == ""


def test_empty_pass_list_gives_empty_frame():
    assert passes_to_frame([]).empty


def test_truncated_passes_have_blank_cells_and_notes():
    started = SatellitePass(None, T0, T0 + timedelta(minutes=2), 45.0, None, 90.0)
    unfinished = SatellitePass(T0, T0 + timedelta(minutes=3), None, 20.0, 200.0, None)
    frame = passes_to_frame([started, unfinished])
    assert pd.isna(frame.iloc[0]["Rise (UTC)"]) and pd.isna(frame.iloc[0]["Duration (min)"])
    assert "in progress" in frame.iloc[0]["Note"]
    assert pd.isna(frame.iloc[1]["Set (UTC)"]) and "Continues" in frame.iloc[1]["Note"]
    assert frame.iloc[0]["Rises toward"] == compass_point(None)


def test_assemble_regular_pass():
    ev = [
        PassEvent(T0, RISE, 10, 300),
        PassEvent(T0 + timedelta(minutes=3), CULMINATE, 50, 20),
        PassEvent(T0 + timedelta(minutes=6), SET, 10, 100),
    ]
    (p,) = assemble_passes(ev, 10.0)
    assert p.is_complete and p.max_elevation_deg == 50 and p.duration_s == 360


def test_assemble_window_starts_mid_pass_and_ends_mid_pass():
    ev = [
        PassEvent(T0, CULMINATE, 40, 0),
        PassEvent(T0 + timedelta(minutes=2), SET, 10, 90),
        PassEvent(T0 + timedelta(hours=1), RISE, 10, 300),
        PassEvent(T0 + timedelta(hours=1, minutes=3), CULMINATE, 55, 0),
    ]
    first, second = assemble_passes(ev, 10.0)
    assert first.rise_time_utc is None and first.set_time_utc is not None and not first.is_complete
    assert second.set_time_utc is None and second.rise_time_utc is not None and second.duration_s is None


def test_assemble_ignores_low_stray_culmination_and_unsorted_input():
    ev = [
        PassEvent(T0 + timedelta(minutes=6), SET, 10, 100),
        PassEvent(T0 + timedelta(hours=2), RISE, 10, 300),
        PassEvent(T0 + timedelta(minutes=3), CULMINATE, 50, 20),
        PassEvent(T0 - timedelta(minutes=30), CULMINATE, 3, 0),  # below threshold, outside a pass
        PassEvent(T0, RISE, 10, 300),
    ]
    result = assemble_passes(ev, 10.0)
    assert [p.is_complete for p in result] == [True, False]


def test_assemble_empty():
    assert assemble_passes([], 10.0) == []


@pytest.mark.parametrize(
    "azimuth,expected",
    [(0, "N (0°)"), (359.9, "N (360°)"), (90, "E (90°)"), (225, "SW (225°)"), (-90, "W (270°)"), (450, "E (90°)")],
)
def test_compass_point(azimuth, expected):
    assert compass_point(azimuth) == expected


def test_compass_point_unknown_is_dash():
    assert compass_point(None) == "–"
