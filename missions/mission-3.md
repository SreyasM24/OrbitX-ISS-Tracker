# Mission 3 · Where Will It Be?

## Learning objective

Use predicted positions to read the shape of an orbit from charts, estimate the orbital period, and understand why predictions get worse the further you go from the data's epoch.

## Estimated duration

25 minutes (4:05 – 4:30 PM IST)

## Concept

A TLE lets us ask "where will the ISS be at 5:00 PM?" without waiting. `predict_track()` asks the SGP4 model for a position every *step* seconds across a time window. The **Telemetry** tab plots latitude, longitude and altitude against UTC time.

- Latitude goes up and down like a wave between about -51.6° and +51.6°. One full wave is **one orbit**.
- Longitude keeps sweeping from -180° to +180° and wrapping. It sweeps faster than Earth rotates, because the ISS moves west to east.
- Altitude hovers between roughly 400 and 440 km and rises and falls **twice per orbit**. A little of that is the orbit being very slightly non-circular; most of it is that Earth is flattened, so the surface we measure height above (the WGS84 ellipsoid) lies further from Earth's centre at the equator than near the latitude extremes.

**Prediction limits matter.** The model ignores things like atmospheric drag changes and reboosts (when the ISS fires engines to climb back up). So error grows with distance from the TLE's epoch, and the app warns once you are more than 7 days away. The code also *bounds* requests (`validate_track_request` in `backend/validation.py`) so nobody can ask for a million points and freeze the page.

## Source files

| File | What it does |
| --- | --- |
| `frontend/charts.py` | `telemetry_figure()` builds the Plotly charts (you will edit this one) |
| `backend/orbital_engine.py` | `predict_track()` and its output columns, `TRACK_COLUMNS` |
| `backend/validation.py` | `validate_track_request()`: the limits |
| `backend/config.py` | `DEFAULT_TRACK_MINUTES`, `MAX_TRACK_POINTS`, ... |

## Instructions

1. Open the **Telemetry** tab with a 180-minute prediction. Hover over the latitude curve. Find two consecutive peaks (or troughs) and note their times. The difference is the orbital period. (About 92 minutes.)
2. Switch the sidebar to 720 minutes and 120 s steps. How many orbits fit in 12 hours?
3. Try to break the limits on purpose: in the code, `validate_track_request(1440, 10)` raises an error. Run it in Python and read the message.
4. Open `frontend/charts.py` and read `telemetry_figure()`. Find the `specs` list: each entry is one panel `(column, label, axis range)`.
5. Check which columns `predict_track()` returns (`TRACK_COLUMNS` in `orbital_engine.py`). One of them is not plotted yet.

## Your task

Add a **fourth panel** to the telemetry chart: **Speed (km/s)**, using the existing `speed_km_s` column.

1. Add `("speed_km_s", "Speed (km/s)", None)` to the `specs` list.
2. Change `rows=3` to `rows=4`.
3. The x-axis title currently goes on the *bottom* panel (`row=3`), so move it to `row=4`.
4. Increase the figure `height` (for example from 620 to 780) so four panels stay readable.

Only `charts.py` needs to change.

## AI prompt

> Open `frontend/charts.py` in the OrbitX project. The function `telemetry_figure(track)` builds three stacked Plotly panels from the `specs` list. The DataFrame also has a `speed_km_s` column that is not plotted. Modify the function to add a fourth panel for `speed_km_s` titled "Speed (km/s)" with an automatic y-range. Update `rows`, the row number of the x-axis title (it must stay on the bottom panel), and the figure height. Don't change colours, the antimeridian-gap handling or the function signature. Show me a minimal diff and explain each changed line.

Check that the answer keeps `insert_antimeridian_gaps()` in use, and that it doesn't rewrite the whole function.

## Expected outcome

- The **Telemetry** tab shows four stacked panels sharing one UTC time axis: latitude, longitude, altitude, speed.
- Speed looks almost flat at about **7.6 – 7.7 km/s** and varies by well under 0.05 km/s. Altitude swings by roughly 10 km over an orbit. The ISS orbit is close to a circle.
- You can state the orbital period from the latitude chart (about 92 minutes) and the number of orbits in your chosen window.

## Verify

```powershell
python -c "from frontend.charts import telemetry_figure; from backend import orbital_engine as e, tle_service as t; from backend.validation import utcnow; d=t.get_orbital_data(); s=e.build_satellite(d.tle); f=telemetry_figure(e.predict_track(s, utcnow(), 180, 60)); print(len(f.data), 'panels')"
```

It must print `4 panels`. Then check the browser: the bottom panel has the "Time (UTC)" label, and the speed panel's y-axis is in km/s.

## Common errors

- **`4 panels` prints `3`**: you added to `specs` but the loop did not pick it up. Check `rows=4` and the spelling `speed_km_s`.
- **Panels overlap or look squashed**: increase `height`.
- **The x-axis label sits in the middle of the figure**: it is still on `row=3`; move it to `row=4`.
- **`KeyError: 'speed_km_s'`**: the name must match `TRACK_COLUMNS` exactly.
- Restore: `git checkout -- frontend/charts.py`.

## Optional extension

Set `DEFAULT_TRACK_MINUTES` in `backend/config.py` to `270` and check that the slider default changes (the app adds it to the list of choices). Then, in Python, compare `validate_track_request(1440, 10)` with `validate_track_request(1440, 120)`: why does the first fail and the second pass? Find the check in `validate_track_request`.
