# OrbitX Facilitator Guide

For the organisers of the OrbitX workshop: **90-minute hands-on GAAC workshop**, about 50 students working in about 25 pairs.

The guiding rule: **a working demonstration beats a completed checklist.** If setup or the network eats time, jump to the fallback (section 6) and be honest with the room about which tasks were done live and which were only shown.

## 1. Essential outcomes and optional extras

| Essential (every pair should leave with this) | Optional (faster pairs / at home) |
| --- | --- |
| A running OrbitX app, or the facilitator's projected demo. | Mission 3 code enhancements (e.g. altitude in miles). |
| Can explain what a TLE is, why its age matters, and read the data-source badge. | Investigating antimeridian line splitting or Doppler shift. |
| Has traced TLE $\rightarrow$ SGP4 $\rightarrow$ position and knows why the ground track shifts west. | Reading pass predictions and visibility constraints. |
| Has completed the 6-step engineering review in Mission 3 and proposed one upgrade. | Continuing independent development on their own GitHub fork. |

The hands-on missions prioritize **understanding and engineering discovery**; coding in Mission 3 is encouraged but optional. A pair that completed the audit and proposed an architecture solution has fully achieved the workshop objective.

## 2. Required software and pre-event setup

**Per laptop (Windows 11 assumed):** Python 3.10 or newer, a modern browser, a text editor (VS Code recommended), Git, and optional access to an AI coding assistant.

**Day before (strongly recommended):**

1. **Pre-install:** Participants run `.\scripts\setup.ps1`, then `.\scripts\run.ps1` once, to ensure dependencies are downloaded before arriving at the venue.
2. **Facilitator check:** On the venue network, run the app, check the data-source badge reads `LIVE` or `CACHED`, and run `pytest tests/` (all tests pass).
3. **Avoid 50 simultaneous downloads:** On the facilitator machine, run the app once while online, then copy the resulting `.orbitx_cache` folder to a USB stick. If venue Wi-Fi struggles, distribute this folder so students run `.\scripts\run.ps1 -Offline`.

## 3. Workshop Schedule (90 Minutes Total)

| Time | Block | Duration | Facilitator & Mentor Focus |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:30** | Speaker presentations & demo | 30 min | 5 speakers present astrodynamics fundamentals and demo the live OrbitX app. |
| **0:30 – 0:40** | Setup & environment check | 10 min | Mentors circulate. **Hard stop at 10 min**: anyone not running joins a neighbour. |
| **0:40 – 0:55** | **Mission 1 — Data Detective** | 15 min | Pairs investigate data source, TLE epoch, age, and failover behavior. |
| **0:55 – 1:10** | **Mission 2 — Orbit Explorer** | 15 min | Pairs trace SGP4 pipeline in code and explore ground track horizons. |
| **1:10 – 1:20** | **Mission 3 — Mission Upgrade** | 10 min | Pairs audit the app, identify one limitation or feature, and formulate a proposal. |
| **1:20 – 1:27** | Team showcase | 7 min | 2–3 volunteer pairs project their findings or code enhancements to the room. |
| **1:27 – 1:30** | Wrap-up & next steps | 3 min | Explain GitHub forks, continuing development at home, and GAAC community links. |

Call out the time at each boundary. Keep the pace active and supportive.

## 4. Short demonstration checklist (0:00 – 0:30)

- [ ] Projector shows the app with the data-source badge. Read it aloud: LIVE / CACHED / SAMPLE, and what each means.
- [ ] Point out the element **epoch and age**: "everything you see is calculated from this one record."
- [ ] Show the four metrics, then the Map tab (orange ISS marker, blue ground track, green observer pin).
- [ ] Change the ground track prediction slider (60 $\rightarrow$ 180 $\rightarrow$ 720 min): explain the 92-minute orbit and westward shift.
- [ ] Show the **🎯 Missions** tab inside the app: show where the 3 guided missions sit.
- [ ] Say clearly: **a pass is geometry; seeing the ISS also needs darkness for you, sunlight on it, and clear sky.**

## 5. Expected results for the three missions

| Mission | What a successful pair has | Typical, sensible observations |
| --- | --- | --- |
| **1. Data Detective** | Identified data source, TLE epoch, data age, download timestamp, and provider from UI/config. | Epoch within hours/days of today; age matches epoch; provider is CelesTrak, ARISS, or WhereTheISS.at. |
| **2. Orbit Explorer** | Traced TLE $\rightarrow$ SGP4 $\rightarrow$ `compute_position()` $\rightarrow$ UI; explained why speed is 7.66 km/s; explored 720-min ground track. | Speed is $\approx 7.66\text{ km/s}$ (orbital speed relative to Earth's center); ground track shifts westward $\approx 23^\circ$ per orbit. |
| **3. Mission Upgrade** | Completed the 6-step review; categorized one real finding; proposed or implemented a fix (e.g. altitude in miles). | Identified file(s) to change (e.g. `formatting.py`, `components.py`); recorded proposal for showcase and home development. |

*(Note: Legacy extension guides `missions/mission-4.md` and `missions/final-challenge.md` remain in the repository for students continuing independent exploration at home).*

## 6. Common failures and recovery

**Installation and network**

| Symptom | Quick recovery |
| --- | --- |
| `python` not found | Install Python from python.org (tick *Add to PATH*), open a new terminal. Fallback: pair up with a working laptop. |
| Script blocked by execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (their own choice, no admin needed) or follow the manual steps in the README. |
| `pip install` slow or failing | Use the wheelhouse (section 2) or pair up. |
| Page shows **SAMPLE, NOT live** | Not a bug. Use it to teach: the app refuses to pretend. Continue. |
| CelesTrak unreachable or rate-limiting | Use the copied `.orbitx_cache` and `-Offline`. |
| Map is grey | Tiles need internet; the markers and track still draw. Carry on. |
| Map area is empty | Its scripts need internet too. Open **Plain track plot (works without internet)** under the map. Carry on. |
| Port 8501 busy | `.\scripts\run.ps1 -Port 8502`. |

**A participant broke the code**

1. Read the red error with them. A `SyntaxError` is usually a missing bracket, comma or colon in the file they just edited.
2. `git diff` shows what they changed. `git checkout -- <file>` restores one file (works in a clone; the unzipped folder is not a repository).
3. No Git? Copy the file from a working laptop, or use the reference solutions below.
4. Last resort: a fresh clone/copy of the project in a new folder and `.\scripts\setup.ps1` again; or move the pair to a neighbour's screen. Missions are independent enough that a pair can skip a broken task and keep going.
5. Tell students: *the dashboard works without any mission task*, and the five tasks are independent, so a broken task never blocks the next mission.

**Offline fallback for the whole room:** every laptop runs `.\scripts\run.ps1 -Offline` with the pre-seeded cache. If the cache is missing too, the bundled sample is used and clearly labelled; all missions still work, with the caveat that its predictions are only illustrative as it ages.

**Total fallback:** if laptops will not cooperate, project the facilitator's running app, step through the four metrics, the map, the chart and the pass table, switch city twice, and discuss. Debrief honestly: "we demonstrated, we did not build."

## 7. Mentor responsibilities (about 25 pairs)

Suggested: **1 lead + 4 – 5 mentors**, each owning 5 – 6 pairs seated together.

- **Lead:** timekeeping, projector, final decisions on skipping, handles network trouble centrally.
- **Mentors:** during 3:10 – 3:25 get every pair to a running app; after that, circulate every 5 minutes. Ask questions before giving answers ("what does the error say? which file did you change?"). Check that students *read* AI output and ran the Verify command. Note recurring problems to report in the debrief.
- **Float mentor** (if available): the person who knows `git` and Windows PowerShell policy issues best.
- Everyone: keep a `git`-less fix handy (the reference solutions below).

## 8. Final demonstrations and debrief (4:55 – 5:00)

Pick 2 – 3 volunteer pairs (30 seconds each): their city, its next pass vs Visakhapatnam, and one thing they learned.

Debrief questions: *How old was our data and why did that matter? Why does a pass in the table not guarantee we can see the ISS? What did the AI get wrong or over-complicate, and how did you notice?* Close with what comes next: twilight and sunlight checks for real visibility, more satellites, and deploying a dashboard.

Be accurate about what happened: say which missions most pairs completed and which they only discussed.

## 9. Reference solutions (facilitator only)

Each was applied to a scratch copy of the project and verified with the mission's Verify command before this guide was written.

**Mission 1: `backend/formatting.py`** (add), `frontend/components.py` (import `format_altitude`, use in the Altitude metric in `render_telemetry()`):

```python
def format_altitude(altitude_km: float) -> str:
    """e.g. ``420 km (261 mi)``."""
    return f"{altitude_km:.0f} km ({altitude_km * 0.621371:.0f} mi)"
```

```python
c3.metric("Altitude", format_altitude(position.altitude_km), help="Height above the WGS84 ellipsoid.")
```

**Mission 2: `frontend/map_view.py`** (add `import math`, `EARTH_RADIUS_KM = 6371.0`, then):

```python
def footprint_radius_km(altitude_km: float) -> float:
    """Surface distance to the geometric horizon, from a given altitude."""
    return EARTH_RADIUS_KM * math.acos(EARTH_RADIUS_KM / (EARTH_RADIUS_KM + altitude_km))
```

and inside `build_map()`, before the `if observer is not None:` block:

```python
folium.Circle(
    [position.latitude_deg, position.longitude_deg],
    radius=footprint_radius_km(position.altitude_km) * 1000,
    color=ISS_COLOR, weight=1, fill=True, fill_opacity=0.08,
    tooltip="Area where the ISS is above the horizon",
).add_to(fmap)
```

**Mission 3: `frontend/charts.py`**: add `("speed_km_s", "Speed (km/s)", None),` to `specs`; `rows=3` becomes `rows=4`; the x-axis title line uses `row=4`; `height=620` becomes `height=780`.

**Mission 4: `backend/pass_predictor.py`** (add), plus the import and display in `frontend/tabs.py` (`render_passes_tab()`; add `best_pass` to the `orbitx.pass_predictor` import and `format_utc` to the `orbitx.formatting` import there):

```python
def best_pass(passes: list[SatellitePass]) -> SatellitePass | None:
    """The complete pass with the highest maximum elevation, or None."""
    complete = [item for item in passes if item.is_complete]
    return max(complete, key=lambda item: item.max_elevation_deg, default=None)
```

```python
best = best_pass(passes)
if best is not None:
    st.success(f"Best pass in this window: peaks at {best.max_elevation_deg:.0f}° "
               f"at {format_utc(best.culmination_time_utc)}")
```

(place before `st.dataframe(passes_to_frame(...))` in `render_passes_tab()`.)

**Final challenge: `backend/config.py`**: add a line such as `"Cape Town, South Africa": (-33.9249, 18.4241),` to `EXAMPLE_CITIES`. Any real city works; check the sign of latitude and longitude.

## 10. Known limitations to mention if asked

- Passes are geometric; twilight, sunlight on the ISS and cloud are not computed.
- Predictions degrade with the age of the orbital elements; the app warns, but cannot know about future reboosts.
- Only Windows scripts are provided; macOS/Linux steps exist in the README but have not been tested.
- The UI is covered by Streamlit's headless `AppTest` in the automated suite. During the release review it was also driven by hand-written scripts in headless Edge on the developer's Windows 11 machine. That was not a participant laptop and not a pilot with students. Do one visual dry run on a participant-like laptop before the event.
- The street map needs internet for tiles and scripts. Everything else works offline; see section 11.

## 11. Offline rehearsal (do this the day before)

Goal: know exactly what the room will see if the Wi-Fi fails.

1. **Seed the cache (online).** On the facilitator laptop run `.\scripts\run.ps1`. The badge should say **LIVE**. This writes `.orbitx_cache\iss_tle.json`. Stop the app with Ctrl+C.
2. **Rehearse "cache only".** Switch Wi-Fi off (or enable airplane mode), then run `.\scripts\run.ps1 -Offline`. Expect: badge **CACHED** with the download age; metrics, Telemetry, Passes and Missions all work; the CSV download works.
3. **Rehearse "nothing cached".** Stop the app, rename the `.orbitx_cache` folder to `.orbitx_cache_off`, run `.\scripts\run.ps1 -Offline` again. Expect the red **SAMPLE, NOT live** badge and the sample's age. If the sample is more than 3 days old an orange **STALE** warning also appears: refresh `backend/data/sample_iss.tle` (section 2, step 3). Rename the folder back afterwards.
4. **Check the map.** With Wi-Fi off the Map tab area is empty or grey: this is expected. Open **Plain track plot (works without internet)** and confirm the track, the orange ISS dot and the green observer marker draw.
5. **Prepare the room.** Copy the seeded `.orbitx_cache` to every laptop (section 2, step 4) and tell students: "offline means a cached or sample badge, a plain plot instead of a street map, and the same code to edit."
6. Switch Wi-Fi back on and confirm a normal **LIVE** start still works.

What offline cannot do: install packages (`pip`), download newer orbital elements, show street tiles, or reach AI assistants that run in a browser. AI-assisted steps need internet, so plan the schedule accordingly.
