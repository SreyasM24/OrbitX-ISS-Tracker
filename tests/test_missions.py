"""Mission guides must exist, follow the contract in missions.py and reference real files."""

import ast
import re
import textwrap

import pytest

from backend import config
from backend.missions import MISSIONS, REQUIRED_SECTIONS, Mission

ROOT = config.PROJECT_ROOT
EXPECTED_FILES = ["mission-1.md", "mission-2.md", "mission-3.md"]
# Functions that the missions ask participants to *write*, so they must not exist yet.
TASK_FUNCTIONS = {"format_altitude", "footprint_radius_km", "best_pass", "evening_passes"}
FILE_REF = re.compile(r"`((?:(?:backend|frontend)/\w+\.py)|(?:scripts/[\w.]+))`")


def headings(text: str) -> list[str]:
    return re.findall(r"^## (.+?)\s*$", text, flags=re.MULTILINE)


def repo_source() -> str:
    files = [*(ROOT / "backend").glob("*.py"), *(ROOT / "frontend").glob("*.py")]
    return "\n".join(p.read_text(encoding="utf-8") for p in files)


def test_registry_matches_expected_files_in_order():
    assert [m.filename for m in MISSIONS] == EXPECTED_FILES


def test_durations_fit_the_workshop_schedule():
    assert [m.minutes for m in MISSIONS] == [15, 15, 10]
    assert sum(m.minutes for m in MISSIONS) == 40


@pytest.mark.parametrize("mission", MISSIONS, ids=lambda m: m.filename)
def test_file_exists_and_has_every_required_section(mission):
    assert mission.path.is_file(), f"missing {mission.path}"
    missing = [s for s in REQUIRED_SECTIONS if s not in headings(mission.read())]
    assert not missing, f"{mission.filename} lacks sections: {missing}"


@pytest.mark.parametrize("mission", MISSIONS, ids=lambda m: m.filename)
def test_title_and_duration_are_consistent(mission):
    text = mission.read()
    assert text.splitlines()[0] == f"# {mission.title}"
    section = text.split("## Estimated duration")[1].split("\n## ")[0]
    assert f"{mission.minutes} minutes" in section


@pytest.mark.parametrize("mission", MISSIONS, ids=lambda m: m.filename)
def test_referenced_repository_files_exist(mission):
    refs = set(FILE_REF.findall(mission.read()))
    assert refs, "a mission should name the source files it uses"
    for ref in refs:
        assert (ROOT / ref).is_file(), f"{mission.filename} refers to missing {ref}"


@pytest.mark.parametrize("mission", MISSIONS, ids=lambda m: m.filename)
def test_python_code_blocks_are_valid_syntax(mission):
    for block in re.findall(r"```python\n(.*?)```", mission.read(), flags=re.DOTALL):
        ast.parse(textwrap.dedent(block))


@pytest.mark.parametrize("mission", MISSIONS, ids=lambda m: m.filename)
def test_missions_do_not_ask_for_secrets_or_paid_services(mission):
    text = mission.read().lower()
    assert "api key" not in text and "password" not in text


def test_starter_snippet_names_exist():
    import backend.orbital_engine as eng
    import backend.pass_predictor as pp
    import backend.tle_service as ts

    assert all(hasattr(eng, n) for n in ("build_satellite", "compute_position"))
    assert all(hasattr(pp, n) for n in ("make_observer", "find_passes"))
    assert all(hasattr(ts, n) for n in ("get_orbital_data", "tle_age_days"))


def test_missing_mission_file_gives_friendly_text(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MISSIONS_DIR", tmp_path)
    assert "was not found" in Mission("9", "x", 1, "nope.md").read()
