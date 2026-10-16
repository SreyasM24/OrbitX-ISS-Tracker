# Mission 2 · Put the ISS on a Map

## Learning objective

Understand what the map shows (the ground track), why the track "jumps" at the edge of the map, and how far around the ISS the sky can see it.

## Estimated duration

20 minutes (3:45 – 4:05 PM IST)

## Concept

The ISS orbits Earth in about 92 minutes while Earth turns beneath it. Mark the point directly below the ISS every minute and you get the **ground track**, a wavy line that shifts westward on each orbit. Because the orbit is tilted **51.6°** to the equator, the ISS never gets farther north or south than about 51.6° latitude.

Maps are flat but longitude wraps around: going east past +180° puts you at -180°. If you naively join the dots, a line is drawn all the way across the map. OrbitX avoids this in `split_track_segments()` by cutting the line at the edge and continuing on the other side.

The ISS is also *high up*: from about 420 km, the **horizon** is far away. Geometry gives the surface distance to the horizon as

`d = R × arccos( R / (R + h) )`  with R = 6371 km (Earth's radius), h = ISS altitude.

Inside that circle (the **footprint**), the ISS is above the horizon, at least geometrically.

## Source files

| File | What it does |
| --- | --- |
| `src/orbitx/map_view.py` | `build_map()` builds the Folium map (you will edit this one) |
| `src/orbitx/orbital_engine.py` | `predict_track()` and `split_track_segments()` |
| `app.py` | Calls `build_map()` in the **Map** tab |

## Instructions

1. Open the **Map** tab. Find the orange ISS dot, the blue ground track, and the green marker for your observer location (Visakhapatnam by default).
2. Use the sidebar's **Prediction length** slider: 60, 180, then 720 minutes. How many separate orbits can you see at 720? Where does the line shift on each orbit, east or west?
3. Zoom in at the left and right edges of the map. Where does the track end and restart? That is the antimeridian cut.
4. Open `src/orbitx/map_view.py` and read `build_map()` top to bottom. Find where the ISS marker is created.

## Your task

**Warm-up (2 min):** change the colour constants at the top of `map_view.py` (`ISS_COLOR`, `TRACK_COLOR`) to something you like, and refresh.

**Main task:** draw the ISS **footprint** on the map.

1. In `map_view.py`, add `import math` and a helper:

   ```python
   EARTH_RADIUS_KM = 6371.0


   def footprint_radius_km(altitude_km: float) -> float:
       """Surface distance to the geometric horizon, from a given altitude."""
       ...
   ```

   Fill in the body using the formula above (`math.acos`).
2. In `build_map()`, after the ISS marker is added, draw a `folium.Circle` centred on `position.latitude_deg, position.longitude_deg` with `radius=` the footprint **in metres** (Folium wants metres, your function returns km), a thin outline, and a very light fill.

## AI prompt

> I'm editing `src/orbitx/map_view.py` in the OrbitX project. `build_map(position, track_segments, observer, illustrative)` already returns a `folium.Map`. Add a function `footprint_radius_km(altitude_km)` that returns `6371 * acos(6371 / (6371 + altitude_km))`, and inside `build_map()` add a `folium.Circle` around the ISS position using `position.altitude_km`. Folium's radius is in **metres**. Use `ISS_COLOR` for the outline with `weight=1`, a very low `fill_opacity`, and a tooltip saying "Area where the ISS is above the horizon". Show me only the changed parts, and tell me where each goes.

Check: did it convert km to metres? Did it reuse `ISS_COLOR` rather than inventing a new one?

## Expected outcome

- A translucent circle around the orange dot that moves with it. For the ISS at about 420 km its radius is **about 2,250 km** (the circle is distorted by the map projection near the poles, that is normal).
- Changing the colour constants recolours the dot and the track.

## Verify

```powershell
python -c "from orbitx.map_view import footprint_radius_km; print(round(footprint_radius_km(420)))"
```

This should print a number between **2200 and 2300**. Then check the map: at the centre of the circle the ISS is overhead; at its edge the ISS is on the horizon.

## Common errors

- **`NameError: math`**: add `import math` at the top of the file.
- **A huge circle covering the whole map**: you passed kilometres where Folium expects metres. Multiply by 1000.
- **The circle does not move when you rerun**: make sure you used `position.latitude_deg` and `position.longitude_deg`, not fixed numbers.
- **Colour unchanged**: the constants must be valid CSS colours like `"#ff00aa"` or `"red"`.
- Restore the original: `git checkout -- src/orbitx/map_view.py`.

## Optional extension

Make a second, smaller circle for a stricter rule: the ISS is **10° above** the horizon. The central angle then becomes `arccos( R·cos(e) / (R+h) ) − e` with e = 10° in radians, and `d = R × that angle`. Compare the two circle sizes. Which is the more useful area for spotting the ISS?
