# Mission 1 · Where Is the ISS?

## Learning objective

Read the ISS's position from real orbital data, and judge how much to trust it by checking how old that data is.

## Estimated duration

20 minutes (3:25 – 3:45 PM IST)

## Concept

The ISS does not broadcast its position to this app. Instead we download a **TLE** (two-line element set): a short text record from CelesTrak that describes the ISS's orbit at one moment, called the **epoch**. A mathematical model (**SGP4**, run through the **Skyfield** library) rolls that orbit forward or backward to any time we ask about.

- **Latitude / longitude**: the point on Earth directly beneath the ISS (the *sub-satellite point*). Latitude is north/south of the equator, longitude is east/west of Greenwich.
- **Altitude**: height above Earth's surface. Skyfield's WGS84 model treats Earth as a slightly squashed sphere, so we measure above that surface.
- **Orbital speed**: how fast the ISS moves relative to Earth's centre, about 7.7 km/s, roughly 27,600 km/h.
- **Freshness**: the model drifts as the TLE ages. A one-day-old TLE is good. A two-week-old one is only illustrative. The app labels data as **LIVE**, **CACHED** or **SAMPLE** so it never pretends.

## Source files

| File | What it does |
| --- | --- |
| `frontend/app.py` | Starts the dashboard and connects the pieces |
| `frontend/components.py` | Draws the header, status panel and the four metric cards (you will edit this one too) |
| `backend/tle_service.py` | Downloads, validates and caches TLEs; `get_orbital_data()`, `tle_age_days()` |
| `backend/orbital_engine.py` | `build_satellite()` and `compute_position()` |
| `backend/formatting.py` | Small text-formatting helpers (you will edit this one) |

## Instructions

1. Launch the app (`.\scripts\run.ps1`) and look at the top of the page. Write down: the **data source** badge, the **epoch** and its **age**, and the **freshness** badge.
2. Read the four numbers under "Calculated position": latitude, longitude, altitude, speed. Press **R** in the browser to rerun and watch them change.
3. Open the sidebar and press **Re-download orbital elements** once (only once, many people share one network). Did the data source change?
4. In the repository folder, create `scratch_mission1.py` (it is git-ignored) with this content, and run it with `python scratch_mission1.py` in your activated terminal:

```python
from backend import orbital_engine, tle_service
from backend.validation import utcnow

data = tle_service.get_orbital_data()
now = utcnow()
print("source :", data.source.value)
print("epoch  :", data.tle.epoch_utc)
print("age (d):", round(tle_service.tle_age_days(data.tle, now), 2))

satellite = orbital_engine.build_satellite(data.tle)
position = orbital_engine.compute_position(satellite, now)
print("lat/lon:", round(position.latitude_deg, 2), round(position.longitude_deg, 2))
print("alt km :", round(position.altitude_km), " speed km/s:", round(position.speed_km_s, 2))
```

5. Compare the script's numbers with the dashboard. They should agree to within a little movement, because time passed between the two.

## Your task

Space-news headlines often quote miles. Add a function `format_altitude(km)` to `backend/formatting.py` that returns text like `420 km (261 mi)` (1 km = 0.621371 mi), then use it for the **Altitude** metric in `frontend/components.py` (look for `c3.metric("Altitude"` in `render_telemetry()`).

Keep the change small: one new function and one edited line. Do not touch the orbital calculations.

## AI prompt

Copy this into your AI coding assistant, then **read the answer before applying it**:

> I'm working in a Python project called OrbitX. Open `backend/formatting.py` and look at how `format_age` and `format_latitude` are written. Add a new function `format_altitude(altitude_km: float) -> str` in the same style that returns a string like `"420 km (261 mi)"`, using 1 km = 0.621371 miles, rounded to whole numbers. Then show me the single line in `frontend/components.py` (the `c3.metric("Altitude", ...)` call) that should use it. Change nothing else. Explain what each line does.

Check that the suggestion matches the existing style and that it only edits those two places.

## Expected outcome

- The dashboard's Altitude card reads something like `423 km (263 mi)` (the value is whatever the ISS is doing now; typically 400 – 440 km).
- Your terminal script prints `source`, `epoch`, `age`, `lat/lon`, `alt` and `speed` lines with plausible values: latitude within ±52°, longitude within ±180°, speed near 7.66 km/s.

## Verify

Run in the terminal:

```powershell
python -c "from backend.formatting import format_altitude; print(format_altitude(420))"
```

It must print `420 km (261 mi)`. Then refresh the browser and check the dashboard. If you can, ask yourself: *is the age the app reports consistent with the epoch it shows?*

## Common errors

- **`ModuleNotFoundError: No module named 'backend'`**: your terminal is not using the project environment. Run `.\scripts\setup.ps1` again, or `pip install -e .` in the activated venv.
- **`NameError: format_altitude`** in the browser: add it to `formatting.py` *and* import it in `frontend/components.py` (the `from backend.formatting import (...)` block).
- **The page does not change**: save both files, then click **Rerun** in the browser's top-right menu.
- **Data source says SAMPLE**: you are offline or the download failed. This is expected and honest. Continue; the maths is the same, only the data is older.
- Something broke badly? `git checkout -- backend/formatting.py frontend/components.py` restores the originals.

## Optional extension

Also show the speed in km/h (multiply by 3600) next to km/s. Then work out how many times the ISS orbits Earth per day: Earth's circumference at that altitude is roughly 2π(6371 + altitude) km. Divide by the speed to get the orbital period in minutes. (About 92.)
