# Contributing to OrbitX

Welcome! This guide is written for students working alone or in pairs. You do not need to be an
expert: small, careful changes are the best kind.

## 1. Clone and install (Windows)

```powershell
git clone https://github.com/SreyasM24/OrbitX-ISS-Tracker.git
cd OrbitX-ISS-Tracker
.\scripts\setup.ps1
.\scripts\run.ps1          # opens http://localhost:8501
```

On macOS/Linux (untested by the authors): `python3 -m venv .venv`, activate it,
`pip install -r requirements-dev.txt`, `pip install -e .`, `streamlit run frontend/app.py`.

## 2. Work on a branch

```powershell
git switch -c my-feature-name
```

Never work directly on `main`.

## 3. Where does my code go?

| You are changing... | Put it in | Rule of thumb |
| --- | --- | --- |
| Looks, layout, CSS, tabs, sidebar | `frontend/` (`theme.py`, `components.py`, `tabs.py`, `sidebar.py`, `map_view.py`, `charts.py`) | Streamlit lives here, and only here (plus `frontend/app.py`). |
| Orbital maths, passes, ground track | `backend/orbital_engine.py`, `backend/pass_predictor.py` | No Streamlit imports. Pure functions that are easy to test. |
| Downloading or caching orbital elements | `backend/tle_service.py` | The only module that touches the network. |
| Constants, limits, example cities | `backend/config.py` | Add a name here instead of a "magic number". |
| Data classes, validation, formatting | `backend/models.py`, `backend/validation.py`, `backend/formatting.py` | Validate every user input. |
| Map and charts | `frontend/map_view.py`, `frontend/charts.py` | Return a Folium/Plotly object; `frontend/tabs.py` displays it. |
| Mission guides | `missions/*.md` + `backend/missions.py` | See below. |
| Tests | `tests/` | One `test_*.py` per topic. |

`frontend/app.py` should stay short: it connects the pieces and nothing more. Read
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) before a bigger change.

## 4. Run the tests

```powershell
.\.venv\Scripts\python -m pytest
```

All tests must pass before you open a pull request. Tests never use the network. If you change
behaviour, add or update a test for it. If you fix a bug, add a test that fails without the fix.

## 5. Add a mission or exercise

1. Copy the structure of an existing guide in `missions/` (for example `mission-1.md`) into a new
   file. It must contain the required sections, which `tests/test_missions.py` checks.
2. Register it in `backend/missions.py`.
3. Run the tests and open the **Missions** tab to check that it renders.

## 6. Code quality expectations

- Match the style of the surrounding code; use type hints and short docstrings that explain *why*.
- Keep scientific honesty: label predictions as predictions, keep the caveats about TLE age and
  pass visibility, and never present sample data as live.
- No secrets, no machine-specific paths, no generated files (`.venv/`, `.orbitx_cache/`, `frontend/static/`).
- Do not add large dependencies or media. Check licences before adding any image, video or data.
- Do not hide warnings just to make output tidy; understand them first.

## 7. Submit a pull request

```powershell
git status
git add <the files you changed>
git commit -m "feat: short description of what changed"
git push -u origin my-feature-name
```

Open a pull request on GitHub against `main`. Describe what you changed, why, and how you tested
it (include a screenshot for visual changes). GitHub Actions runs the test suite automatically;
please wait for it to pass.

## 8. Report a bug

Open a GitHub issue with: what you did, what you expected, what happened, your Python version and
operating system, and any message from the terminal. Mention whether the page said LIVE, CACHED or
SAMPLE. See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) first; it solves most problems.
