# Mission 4 · Can We See It?

## Learning objective

Read an observation-pass table, pick the best pass over Visakhapatnam, and explain why a pass in the table is not the same as seeing the ISS.

## Estimated duration

15 minutes (4:30 – 4:45 PM IST)

## Concept

From your location, the ISS **rises** above the horizon, climbs to a highest point (**culmination**, or "peak"), then **sets**. Skyfield's `find_events()` finds those three moments. Two angles describe where to look:

- **Elevation**: degrees above the horizon (0° = horizon, 90° = straight up).
- **Azimuth**: compass direction (0° = north, 90° = east, 180° = south, 270° = west).

A pass that peaks at 60° is a long, bright overhead pass. One that peaks at 12° skims the treetops and may be hidden by buildings, hills and haze. That is why the app lets you choose a **minimum elevation**.

**Seeing the ISS needs more than geometry.** The ISS shines by reflecting sunlight, so it is visible only when *it* is in sunlight and *you* are in darkness: typically within a couple of hours after sunset or before sunrise. At midday the ISS is overhead but invisible against the bright sky. In Earth's shadow it is dark. You also need a clear sky. OrbitX computes the **geometry** only; it does not yet check twilight or cloud. All times in the table are shown in **UTC** and **IST** (IST = UTC + 5 h 30 min). Always check which one a column uses.

## Source files

| File | What it does |
| --- | --- |
| `src/orbitx/pass_predictor.py` | `find_passes()`, `passes_to_frame()`, `assemble_passes()` (you will edit this one) |
| `src/orbitx/models.py` | The `SatellitePass` dataclass |
| `app.py` | The **Passes** tab |

## Instructions

1. Open the **Passes** tab with **Visakhapatnam** selected, a 24-hour window and a 10° minimum elevation.
2. Read the first row aloud to your partner: when does the ISS rise (UTC and IST), in which direction, how high does it get, when does it set, and for how long is it above the horizon?
3. Change the minimum elevation to 30°. Which passes disappear? Why?
4. Set the window to 72 hours. How many passes are there above 10°? Which has the highest peak?
5. For each pass, convert the IST time to local clock time: is it after sunset (sunset is around 17:20 IST in Visakhapatnam in late October) or before sunrise (around 05:50 IST)? Those are the ones that *might* be visible.
6. Read `find_passes()` in `pass_predictor.py`: find the line that calls `satellite.find_events(...)`.

## Your task

Add a helper `best_pass(passes)` to `src/orbitx/pass_predictor.py` that returns the **complete pass with the highest maximum elevation**, or `None` if there is no complete pass. Then use it in `app.py` (in the **Passes** tab, just above the table) to show a green summary line such as:

`Best pass in this window: peaks at 62° at 2026-10-21 13:08:11 UTC`

A *complete* pass has a known rise, peak and set (`SatellitePass.is_complete`).

## AI prompt

> In the OrbitX project, `src/orbitx/models.py` defines a `SatellitePass` dataclass with `max_elevation_deg`, `culmination_time_utc` and an `is_complete` property. In `src/orbitx/pass_predictor.py` add `best_pass(passes: list[SatellitePass]) -> SatellitePass | None` that returns the complete pass with the highest `max_elevation_deg`, or `None` if there is none. Then show me the lines to add to the Passes tab in `app.py`, just above the `st.dataframe(passes_to_frame(...))` call, that display `st.success(...)` with the peak elevation and the UTC time (use `format_utc` from `orbitx.formatting`, already imported). Keep changes minimal and don't change existing function signatures.

Check: does it ignore incomplete passes? Does it handle an empty list without crashing?

## Expected outcome

- A green line appears above the table naming the highest pass in your window; the number matches the largest value in the *Max elevation (deg)* column among complete passes.
- With a very high minimum elevation (for example 60° and a short window), when there is no pass the app shows the "No passes above ..." message and no error.
- Over 24 hours at Visakhapatnam you will typically see **zero to a few** passes above 10°, with peaks anywhere from 10° to 90°. Exact times change every day.

## Verify

```powershell
python -c "from orbitx.pass_predictor import best_pass; print(best_pass([]))"
```

It must print `None`. Then, in the browser, compare the green line with the table by eye. Finally decide: *for the best pass, was the observer in darkness?* Write one sentence about it, using the concept section above.

## Common errors

- **`ValueError: max() arg is an empty sequence`**: you need `default=None` or an explicit empty check.
- **`TypeError` comparing `None` and `float`**: incomplete passes can have `max_elevation_deg = None`; filter on `is_complete` first.
- **The green line shows a time that is not in the table**: you may be showing the *rise* instead of the *peak* time, or the wrong time zone. Check the column label.
- **"Fix the observer location"**: latitude or longitude text is invalid. Press **Reset to default location**.
- **No passes at all**: widen the window or lower the minimum elevation.
- Restore: `git checkout -- src/orbitx/pass_predictor.py app.py`.

## Optional extension

Add a second function `evening_passes(passes)` that keeps only passes whose peak is between 18:00 and 21:00 IST (use `config.IST` and `.astimezone`). How many of the next 72 hours' passes qualify? Compare with the passes you judged "after sunset" in step 5.
