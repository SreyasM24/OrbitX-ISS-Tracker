"""Mission guides must exist, follow the contract in missions.py and reference real files."""

import ast
import re
import textwrap

import pytest

from orbitx import config
from orbitx.missions import MISSIONS, REQUIRED_SECTIONS, Mission

ROOT = config.PROJECT_ROOT
EXPECTED_FILES = ["mission-1.md", "mission-2.md", "mission-3.md", "mission-4.md", "final-challenge.md"]
# Functions that the missions ask participants to *write*, so they must not exist yet.
TASK_FUNCTIONS = {"format_altitude", "footprint_radius_km", "best_pass", "evening_passes"}
FILE_REF = re.compile(r"`((?:src/orbitx/\w+\.py)|(?:app\.py)|(?:scripts/[\w.]+))`")


def headings(text: str) -> list[str]:
    return re.findall(r"^## (.+?)\s*$", text, flags=re.MULTILINE)


def repo_source() -> str:
    files = [ROOT / "app.py", *(ROOT / "src" / "orbitx").glob("*.py")]
    return "\n".join(p.read_text(encoding="utf-8") for p in files)


def test_registry_matches_expected_files_in_order():
    assert [m.filename for m in MISSIONS] == EXPECTED_FILES


def test_durations_fit_the_workshop_schedule():
    assert [m.minutes for m in MISSIONS] == [20, 20, 25, 15, 10]
    assert sum(m.minutes for m in MISSIONS) == 90


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
def test_functions_named_in_ai_prompt_exist_or_are_the_task(mission):
    prompt = mission.read().split("## AI prompt")[1].split("\n## ")[0]
    source = repo_source()
    for name in re.findall(r"`(\w+)\(", prompt):
        if name in TASK_FUNCTIONS:
            assert f"def {name}" not in source, f"{name} is the participant's task but already exists"
        else:
            assert f"def {name}" in source or hasattr(config, name) or f"{name}(" in source, name


@pytest.mark.parametrize("mission", MISSIONS, ids=lambda m: m.filename)
def test_python_code_blocks_are_valid_syntax(mission):
    for block in re.findall(r"```python\n(.*?)```", mission.read(), flags=re.DOTALL):
        ast.parse(textwrap.dedent(block))


@pytest.mark.parametrize("mission", MISSIONS, ids=lambda m: m.filename)
def test_missions_do_not_ask_for_secrets_or_paid_services(mission):
    text = mission.read().lower()
    assert "api key" not in text and "password" not in text


def test_starter_snippet_names_exist():
    import orbitx.orbital_engine as eng
    import orbitx.pass_predictor as pp
    import orbitx.tle_service as ts

    assert all(hasattr(eng, n) for n in ("build_satellite", "compute_position"))
    assert all(hasattr(pp, n) for n in ("make_observer", "find_passes"))
    assert all(hasattr(ts, n) for n in ("get_orbital_data", "tle_age_days"))


def test_missing_mission_file_gives_friendly_text(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MISSIONS_DIR", tmp_path)
    assert "was not found" in Mission("9", "x", 1, "nope.md").read()
