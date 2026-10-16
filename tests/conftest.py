"""Shared fixtures. Nothing here touches the network or depends on today's ISS position."""

from __future__ import annotations

import pytest
import requests

from orbitx import config, tle_service


class FakeResponse:
    """Minimal stand-in for ``requests.Response`` used to mock CelesTrak."""

    def __init__(self, text: str = "", status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(response=self)


@pytest.fixture(scope="session")
def sample_text() -> str:
    return config.SAMPLE_TLE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def sample_tle():
    return tle_service.load_sample_tle()


@pytest.fixture
def no_network(monkeypatch):
    """Fail loudly if any code path tries a real HTTP request."""

    def blocked(*args, **kwargs):
        raise AssertionError("A test attempted a real network request.")

    monkeypatch.setattr(requests, "get", blocked)
    monkeypatch.setattr(requests.sessions.Session, "request", blocked)
