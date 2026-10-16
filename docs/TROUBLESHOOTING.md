# Troubleshooting

## Setup

| Symptom | Fix |
| --- | --- |
| PowerShell: "running scripts is disabled" | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (your user only), or follow the manual steps in the README. |
| `python` not found / opens the Microsoft Store | Install Python 3.10+ from python.org with "Add python.exe to PATH", then open a new terminal. |
| `ModuleNotFoundError: No module named 'orbitx'` | Activate `.venv` and run `pip install -e .`. |
| `pip install` fails | Check internet or proxy settings; re-run `.\scripts\setup.ps1`. `.\scripts\setup.ps1 -Recreate` rebuilds `.venv`. |
| `pip check` reports conflicts | Recreate the environment with `-Recreate` so versions come from `requirements-dev.txt`. |

## Running

| Symptom | Fix |
| --- | --- |
| Port 8501 is busy | `.\scripts\run.ps1 -Port 8502`. To find the owner: `Get-NetTCPConnection -LocalPort 8501 -State Listen` shows its process id; stop it with `Stop-Process -Id <id>`. |
| Stop the app | Press `Ctrl+C` in its terminal. |
| Browser does not open | Open `http://localhost:8501` yourself. |
| Page is stuck on "Running..." | Wait up to about 10 s for the CelesTrak request to time out, or start with `-Offline`. |

## Data

| Symptom | Fix |
| --- | --- |
| **SAMPLE, NOT live** | CelesTrak could not be reached or offline mode is on. Positions are illustrative if the sample is old. |
| **STALE** (3+ days) or **EXPIRED** (14+ days) | Press **Re-download orbital elements** (not repeatedly: CelesTrak asks for at most one request per 2 hours). Offline, the last cache is used, however old. |
| Wrong cached data | Delete the `.orbitx_cache/` folder; it is recreated automatically. |

## Visuals

| Symptom | Fix |
| --- | --- |
| Map is grey | OpenStreetMap tiles need internet. The marker and track still draw. |
| Map area is empty | The map's scripts also load from a CDN. Open **Plain track plot (works without internet)**. |
| No video background | Put a video at `assets/iss-background.mp4` (see `assets/README.md`) and restart. The gradient is the normal fallback when the file is missing. |
| Video does not play | Use an H.264 MP4. Browsers may pause background video on battery saver or with "reduce motion" enabled. |
| Edited code, nothing changed | Save the file, then press **R** in the page or use the menu's **Rerun**. After editing `ui/theme.py`, restart the app. |
