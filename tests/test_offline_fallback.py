"""Data-source honesty: live / cached / sample labelling with every HTTP call mocked."""

from datetime import timedelta

import pytest
import requests

from conftest import FakeResponse
from orbitx import tle_service as ts
from orbitx.models import DataSource

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

    from orbitx.validation import ValidationError

    with pytest.raises(ValidationError):
        ts.get_orbital_data(offline=True, now=datetime(2026, 10, 21), cache_path=tmp_path / "c.json")
