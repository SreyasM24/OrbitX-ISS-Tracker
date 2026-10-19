# Final · New City Challenge (Extension Guide)

> **Self-Paced Extension Guide:** This is an optional post-workshop challenge for students continuing independent exploration at home. The 3 core workshop missions are Mission 1, Mission 2, and Mission 3.

## Learning objective

Change the observer location, and compare what the same ISS orbit means for two places on Earth.

## Estimated duration

10 minutes (4:45 – 4:55 PM IST)

## Concept

The ISS follows one path in space; each observer sees a different slice of it. Latitude matters most: because the orbit is tilted 51.6°, places between about ±50° pass nearly under the track often and get high passes. Far-north cities such as Reykjavik (64°N) only see the ISS low on the horizon, if at all. Longitude changes *when* a pass happens, because the ISS reaches your meridian at different times.

Approximate city coordinates are listed in `EXAMPLE_CITIES` in `backend/config.py`. You do not need a geocoding service: look the coordinates up (any map app shows them) and type them in as decimal degrees (north and east positive, south and west negative).

## Source files

| File | What it does |
| --- | --- |
| `backend/config.py` | `EXAMPLE_CITIES`, `DEFAULT_CITY` (you will edit this one) |
| `backend/pass_predictor.py` | `make_observer()`, `find_passes()` |
| `backend/validation.py` | `validate_latitude()`, `validate_longitude()` |

## Instructions

1. In the sidebar, choose a different city from the **Example city** list and open the **Passes** tab. Note the next complete pass (UTC, IST, peak elevation).
2. Try **Custom location**: type the latitude and longitude of your hometown. Try an invalid value (`91` for latitude) and read the error. Press **Reset to default location**.
3. Open `backend/config.py` and find `EXAMPLE_CITIES`.
4. Create `scratch_compare.py` in the repository folder (it is git-ignored):

```python
from backend import config, orbital_engine, pass_predictor, tle_service
from backend.validation import utcnow

data = tle_service.get_orbital_data()
satellite = orbital_engine.build_satellite(data.tle)
now = utcnow()

for city in (config.DEFAULT_CITY, "Reykjavik, Iceland"):
    lat, lon = config.EXAMPLE_CITIES[city]
    observer = pass_predictor.make_observer(city, lat, lon)
    passes = pass_predictor.find_passes(satellite, observer, now, 24, 10.0)
    peaks = [round(p.max_elevation_deg) for p in passes if p.max_elevation_deg is not None]
    print(f"{city}: {len(passes)} passes in 24 h, peak elevations {peaks}")
```

Run it with `python scratch_compare.py`.

## Your task

Add **your own city** (or any place you care about) to `EXAMPLE_CITIES` in `config.py`, then change the second city in `scratch_compare.py` to yours and compare it with Visakhapatnam. Write down who gets more passes and the higher peak, and your best guess for why.

Do not rename or remove `DEFAULT_CITY`'s entry; the app starts with it.

## AI prompt

> In the OrbitX project, `backend/config.py` has a dictionary `EXAMPLE_CITIES` mapping a name to `(latitude_deg, longitude_deg)`. Add one entry for `<YOUR CITY, COUNTRY>` at the end, keeping the same format and rounding to 4 decimals. Tell me which latitude and longitude you used and how confident you are in them. Then explain, in plain language, why a city at latitude `<YOUR LATITUDE>` would see more or fewer ISS passes than one at 17.7°N, given the ISS orbit is inclined 51.6°. Do not modify any other file.

Do not trust the coordinates blindly: check them against a map before you rely on them.

## Expected outcome

- Your city appears in the sidebar's **Example city** list; selecting it fills in the latitude and longitude boxes.
- The comparison script prints one line per city. The counts and peaks differ between the cities, and are never fixed numbers; they depend on today's orbit. Cities at very high latitude (such as Reykjavik) usually get only low, short passes, or none above 10°.

## Verify

```powershell
python -c "from backend import config; print(len(config.EXAMPLE_CITIES), config.DEFAULT_CITY in config.EXAMPLE_CITIES)"
```

It must print your count (one more than before) and `True`. Then select your city in the app and check that the map shows a green marker where you expect it.

## Common errors

- **`SyntaxError` in `config.py`**: a missing comma after the previous entry or an unclosed parenthesis.
- **`KeyError: 'My City'`** in the script: the name in the script must match the dictionary key exactly.
- **Marker appears in the wrong place (for example the ocean)**: you swapped latitude and longitude, or forgot the minus sign for west/south.
- **City missing from the list**: save `config.py`, then rerun the app. If still missing, stop and restart the app.
- Restore: `git checkout -- backend/config.py`.

## Optional extension

Compare three cities at once and sort them by their best peak elevation. Or compute the number of passes above 30° for every city in `EXAMPLE_CITIES` and print a ranking. Does latitude explain the ranking completely?
