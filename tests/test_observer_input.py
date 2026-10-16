"""Observer location: text parsing, bounds, example cities."""

import math

import pytest

from orbitx import config
from orbitx.pass_predictor import make_observer, observer_from_text
from orbitx.validation import (
    ValidationError,
    validate_latitude,
    validate_longitude,
    validate_min_elevation,
    validate_search_hours,
)


def test_default_city_is_visakhapatnam_and_listed():
    assert config.DEFAULT_CITY == "Visakhapatnam, India"
    assert config.DEFAULT_CITY in config.EXAMPLE_CITIES


def test_all_example_cities_are_valid_and_distinct():
    seen = set()
    for name, (lat, lon) in config.EXAMPLE_CITIES.items():
        obs = make_observer(name, lat, lon)
        assert obs.name == name
        seen.add((lat, lon))
    assert len(seen) == len(config.EXAMPLE_CITIES)


def test_visakhapatnam_coordinates_are_plausible():
    lat, lon = config.EXAMPLE_CITIES["Visakhapatnam, India"]
    assert 17.0 < lat < 18.5 and 82.5 < lon < 84.0


@pytest.mark.parametrize(
    "lat,lon",
    [("17.6868", "83.2185"), (" 17.6868 ", "\t83.2185\n"), ("-90", "180"), ("90", "-180"), ("0", "0")],
)
def test_valid_text_input(lat, lon):
    obs = observer_from_text("Somewhere", lat, lon)
    assert obs.latitude_deg == float(lat) and obs.longitude_deg == float(lon)


@pytest.mark.parametrize(
    "lat,lon,fragment",
    [
        ("", "83", "Latitude is empty"),
        ("17", "", "Longitude is empty"),
        ("   ", "83", "Latitude is empty"),
        (None, "83", "Latitude is empty"),
        ("91", "83", "between -90 and 90"),
        ("-90.0001", "83", "between -90 and 90"),
        ("17", "180.5", "between -180 and 180"),
        ("17", "-181", "between -180 and 180"),
        ("abc", "83", "Latitude must be a number"),
        ("17.", "8,3", "Longitude must be a number"),  # comma decimals are rejected, not guessed
        ("17", "--5", "Longitude must be a number"),
        ("nan", "83", "finite"),
        ("inf", "83", "finite"),
        ("-", "83", "Latitude must be a number"),  # partially typed
    ],
)
def test_invalid_text_input_gives_clear_error(lat, lon, fragment):
    with pytest.raises(ValidationError, match=fragment):
        observer_from_text("x", lat, lon)


def test_observer_name_is_sanitised():
    assert make_observer("", 10, 10).name == "Observer"
    assert make_observer("a\x00b\n", 10, 10).name == "ab"
    assert len(make_observer("n" * 500, 10, 10).name) == 60


def test_bool_is_not_a_coordinate():
    with pytest.raises(ValidationError):
        validate_latitude(True)


@pytest.mark.parametrize("value", [-0.1, 89.1, math.nan])
def test_min_elevation_bounds(value):
    with pytest.raises(ValidationError):
        validate_min_elevation(value)


@pytest.mark.parametrize("value", [0.5, 73])
def test_search_hours_bounds(value):
    with pytest.raises(ValidationError):
        validate_search_hours(value)


def test_longitude_edges_inclusive():
    assert validate_longitude(180) == 180.0 and validate_longitude(-180) == -180.0
