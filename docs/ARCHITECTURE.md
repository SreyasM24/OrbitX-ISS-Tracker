# OrbitX architecture

OrbitX is a single Streamlit application. Streamlit re-runs `app.py` from top to bottom on every
interaction, so the design keeps the scientific parts in plain Python modules and caches their
results.

## Flow

```
CelesTrak (network)                      data/sample_iss.tle (bundled)
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
  ui/ : theme (CSS), background (video), sidebar, components (header, status, metrics), tabs
        |
        v
  app.py wires it together and Streamlit renders it in the browser
```

## Modules

| Module | Responsibility | Imports Streamlit? |
| --- | --- | --- |
| `config.py` | Constants, thresholds, paths, environment overrides | no |
| `models.py` | Dataclasses: `TleRecord`, `Observer`, `SatellitePosition`, `SatellitePass`, enums | no |
| `validation.py` | Input validation, UTC helpers, TLE checksums | no |
| `tle_service.py` | Download, parse, cache, freshness, offline fallback | no |
| `orbital_engine.py` | Propagation, coordinates, ground track, antimeridian splitting | no |
| `pass_predictor.py` | Passes for an observer and the pass table | no |
| `map_view.py`, `charts.py` | Build Folium / Plotly figures | no |
| `formatting.py`, `missions.py` | Display strings, mission guide registry | no |
| `ui/data.py` | `st.cache_data` wrappers around the scientific functions | yes |
| `ui/theme.py` | The stylesheet | yes |
| `ui/background.py` (+ `.js`) | Background video layer | yes |
| `ui/sidebar.py`, `ui/components.py`, `ui/tabs.py` | Widgets and sections | yes |

Rule: scientific modules never import `streamlit`, so they can be tested and reused on their own.

## Caching

- `tle_service` stores the last successful download on disk (2-hour courtesy window for CelesTrak).
- `ui/data.py` uses `st.cache_data` with plain, hashable arguments, so changing a widget does not
  recompute the orbit unless its inputs changed. Times are rounded to whole minutes for stable keys.

## Background video

Streamlit serves only `static/` (enabled in `.streamlit/config.toml`), so `ui/background.py` copies
`assets/iss-background.mp4` there. It renders one fixed full-screen layer with `st.html`. Streamlit
keeps the same DOM node between reruns, which is why the video does not restart when a student
switches tabs or changes a location. `background.js` crossfades two copies of the clip at the loop
point. If the file is missing, a CSS gradient is used. The video is not distributed with the
repository; see `assets/README.md`.

## Scientific caveats built into the design

Positions are computed from orbital elements, not onboard telemetry; accuracy degrades with TLE
age; a predicted pass is not a visibility guarantee; map tiles need internet (the Plotly track plot
is the offline fallback).
