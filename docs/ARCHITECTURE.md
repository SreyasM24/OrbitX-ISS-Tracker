# OrbitX architecture

OrbitX is a single Streamlit application split into two code categories: `backend/` (orbital maths, data, validation; no Streamlit) and `frontend/` (everything the user sees). The frontend imports the backend; the backend never imports the frontend. Streamlit re-runs `frontend/app.py` from top to bottom on every
interaction, so the design keeps the scientific parts in plain Python modules and caches their
results.

## Flow

```
CelesTrak (network)                      backend/data/sample_iss.tle (bundled)
        |                                          |
        v                                          v
  tle_service.get_orbital_data()  -- cache (.orbitx_cache, 2 h) --> OrbitalData(source, tle, warnings)
        |      LIVE -> CACHED -> SAMPLE fallback chain; every result says where it came from
        v
  orbital_engine.build_satellite(tle)         (Skyfield / SGP4)
        |
        +--> compute_position(now)                 latitude, longitude, WGS84 altitude, orbital speed
        +--> predict_track(start, minutes, step)   -> pandas DataFrame (also the CSV export)
        +--> pass_predictor.find_passes(observer)  -> rise / peak / set / max elevation
        |
        v
  map_view.build_map (Folium)   charts.telemetry_figure / track_figure (Plotly)   passes_to_frame
        |
        v
  frontend/ : theme (CSS), background (video), sidebar, components (header, status, metrics), tabs
        |
        v
  frontend/app.py wires it together and Streamlit renders it in the browser
```

## Modules

| Module | Responsibility | Imports Streamlit? |
| --- | --- | --- |
| `backend/config.py` | Constants, thresholds, paths, environment overrides | no |
| `backend/models.py` | Dataclasses: `TleRecord`, `Observer`, `SatellitePosition`, `SatellitePass`, enums | no |
| `backend/validation.py` | Input validation, UTC helpers, TLE checksums | no |
| `backend/tle_service.py` | Download, parse, cache, freshness, offline fallback | no |
| `backend/orbital_engine.py` | Propagation, coordinates, ground track, antimeridian splitting | no |
| `backend/pass_predictor.py` | Passes for an observer and the pass table | no |
| `backend/formatting.py`, `backend/missions.py` | Display strings, mission guide registry | no |
| `frontend/map_view.py`, `frontend/charts.py` | Build Folium / Plotly figures | no (pure figure builders) |
| `frontend/data.py` | `st.cache_data` wrappers around the backend functions | yes |
| `frontend/theme.py` | The stylesheet | yes |
| `frontend/background.py` (+ `.js`) | Background video layer | yes |
| `frontend/sidebar.py`, `frontend/components.py`, `frontend/tabs.py` | Widgets and sections | yes |
| `frontend/app.py` | Entry point | yes |

Rule: `backend/` never imports `streamlit` or `frontend`, so it can be tested and reused on its own.

## Caching

- `tle_service` stores the last successful download on disk (2-hour courtesy window for CelesTrak).
- `frontend/data.py` uses `st.cache_data` with plain, hashable arguments, so changing a widget does not
  recompute the orbit unless its inputs changed. Times are rounded to whole minutes for stable keys.

## Background video

Streamlit serves only a `static/` folder next to the main script, i.e. `frontend/static/` (enabled in `.streamlit/config.toml`), so `frontend/background.py` copies
`frontend/assets/iss-background.mp4` there. It renders one fixed full-screen layer with `st.html`. Streamlit
keeps the same DOM node between reruns, which is why the video does not restart when a student
switches tabs or changes a location. `background.js` crossfades two copies of the clip at the loop
point. If the file is missing, a CSS gradient is used. The video is not distributed with the
repository; see `frontend/assets/README.md`.

## Scientific caveats built into the design

Positions are computed from orbital elements, not onboard telemetry; accuracy degrades with TLE
age; a predicted pass is not a visibility guarantee; map tiles need internet (the Plotly track plot
is the offline fallback).
