# Mission 2 — Orbit Explorer: How Does OrbitX Track the ISS?

## Learning objective

Understand the end-to-end technical pipeline that turns raw two-line orbital elements into real-time sub-satellite coordinates, instantaneous velocity vectors, and interactive ground tracks.

## Estimated duration

15 minutes (Hands-on Workshop Phase 2)

## Concept

Many people assume satellite tracking apps receive a live, continuous GPS stream directly from the spacecraft. In reality, OrbitX uses **mathematical propagation**:

$$\text{Orbital Elements (TLE)} \longrightarrow \text{Orbital Propagation (SGP4)} \longrightarrow \text{State Vector } (\vec{r}, \vec{v}) \longrightarrow \text{Geodetic Coordinates (WGS84)} \longrightarrow \text{Dashboard \& Map}$$

### Key Technical Concepts:
- **SGP4 (Simplified General Perturbations 4):** A mathematical model developed by NORAD and NASA that predicts the trajectory of satellites in Low Earth Orbit. SGP4 accounts for Earth's non-spherical shape (gravitational oblateness terms $J_2, J_3, J_4$), solar and lunar gravitational pulls, and atmospheric drag.
- **State Vector:** At any given UTC instant, SGP4 computes the satellite's 3D position vector ($\vec{r}$) and velocity vector ($\vec{v}$) in an inertial coordinate frame (GCRS — Geocentric Celestial Reference System).
- **Geodetic Coordinates (WGS84):** Earth is not a flat disk or a perfect sphere; it is an oblate ellipsoid. Skyfield projects the 3D position vector down to Earth's surface to calculate:
  - **Sub-satellite Latitude & Longitude:** The geographic coordinate directly under the station.
  - **Altitude:** The true height in kilometers above the WGS84 ellipsoid surface (approx. 415–430 km).
  - **Orbital Speed:** The magnitude of the inertial velocity relative to Earth's center ($\|\vec{v}\| \approx 7.66\text{ km/s} \approx 27,600\text{ km/h}$). This is distinct from ground speed ($\sim 7.2\text{ km/s}$) because Earth rotates beneath the orbit.
- **Ground Track:** The path traced across Earth's surface over time. Because the ISS has an orbital inclination of **51.6°** to the equator, its ground track forms a sinusoidal wave that never travels north of 51.6° N or south of 51.6° S.

## Source files

| File | Primary Responsibility |
|---|---|
| [`frontend/app.py`](frontend/app.py) | Application entry point: connects the data provider, orbital engine, and UI components. |
| [`backend/orbital_engine.py`](backend/orbital_engine.py) | Pure astrodynamics: initializes `EarthSatellite`, calls SGP4, computes positions and predicts ground tracks. |
| [`frontend/components.py`](frontend/components.py) | Telemetry rendering: formats and displays headline metric cards (`Latitude`, `Longitude`, `Altitude`, `Orbital speed`). |
| [`frontend/map_view.py`](frontend/map_view.py) | Cartography: renders the interactive Leaflet/Folium map, antimeridian line splitting, and markers. |

## Guided code exploration

Open the project files in your editor to trace how data flows through the application:

### 1. Where Calculation Begins: `frontend/app.py`
Open [`frontend/app.py`](frontend/app.py) and look at lines 75–86:
```python
@st.fragment(run_every=run_every)
def render_live_dashboard() -> None:
    current_time = utcnow()
    start = current_time.replace(second=0, microsecond=0)
    try:
        satellite = build_satellite(tle)
        position = compute_position(satellite, current_time)
        track = cached_track(tle.name, tle.line1, tle.line2, start,
                             controls.track_minutes, controls.step_s)
    except (PredictionError, ValidationError) as exc:
        st.error(f"Could not calculate the ISS position: {exc}")
        return
```
- Notice that every time this Streamlit fragment runs (configured by the refresh slider in the sidebar), it gets the current UTC instant: `current_time = utcnow()`.
- It builds an `EarthSatellite` object from the TLE and passes it to `compute_position()`.

### 2. The Astrodynamics Engine: `backend/orbital_engine.py`
Open [`backend/orbital_engine.py`](backend/orbital_engine.py) and examine `compute_position()`:
```python
def compute_position(satellite: EarthSatellite, when_utc: datetime) -> SatellitePosition:
    when = ensure_utc(when_utc)
    geocentric = satellite.at(get_timescale().from_datetime(when))
    subpoint = wgs84.subpoint_of(geocentric)
    speed = float(np.linalg.norm(geocentric.velocity.km_per_s))
    lat = subpoint.latitude.degrees
    lon = subpoint.longitude.degrees
    alt = wgs84.height_of(geocentric).km
    return SatellitePosition(when, lat, lon, alt, speed)
```
- Notice how `satellite.at()` invokes SGP4.
- Notice that `subpoint.latitude.degrees` and `subpoint.longitude.degrees` are extracted directly from the WGS84 model.
- Notice that `speed` is the norm of the velocity vector: `np.linalg.norm(geocentric.velocity.km_per_s)`.
- **Zero HTTP requests happen in this file.** It is pure, local numerical mathematics.

### 3. Displaying Telemetry: `frontend/components.py`
Open [`frontend/components.py`](frontend/components.py) and locate `render_telemetry()`:
- Notice how `position.latitude_deg`, `position.longitude_deg`, `position.altitude_km`, and `position.speed_km_s` are passed to `c1.metric`, `c2.metric`, `c3.metric`, and `c4.metric`.
- If the data is from an expired TLE or sample file, the header transparently says `"Illustrative position"` instead of `"Calculated position"`.

## Interactive investigation

Switch to the running OrbitX web dashboard:

1. **Observe the Ground Track on the Map:**
   - In the sidebar under **Mission controls**, find the **Ground track** section.
   - Adjust the **Prediction length (minutes)** slider: test **60 min**, **180 min**, and **720 min**.
   - Watch the blue track on the map:
     - At 60 minutes, you see less than one full orbit (one orbit takes $\approx 92.8$ minutes).
     - At 180 minutes, you see roughly two complete orbits.
     - At 720 minutes, you see the track weave across the globe. Notice how each successive orbit is shifted **westward** by roughly 23° of longitude. Why? Because Earth rotated east underneath the space station while it completed that orbit!
2. **Observe the Antimeridian Cut ($\pm 180^\circ$):**
   - Look at where the blue ground track hits the eastern and western edges of the map.
   - Does a continuous line streak all the way across the Pacific Ocean from left to right?
   - In [`backend/orbital_engine.py`](backend/orbital_engine.py), look at `split_track_segments()`: notice how OrbitX detects when longitude jumps from $+180^\circ$ to $-180^\circ$ and cuts the line so it renders cleanly.

> **Important Distinction:** The **Prediction length** slider controls how far into the future OrbitX calculates the *ground track path*. It does **not** change the current position timestamp of the ISS now, which is always computed for the current UTC moment.

## Investigation questions

Discuss these questions with your partner:

1. **What role does a TLE play in calculating the ISS's position?**
2. **What does the SGP4 algorithm do with a TLE and a timestamp?**
3. **How does OrbitX convert a 3D coordinate in space into a latitude and longitude on a map?**
4. **Why is the ISS ground track bounded between 51.6° N and 51.6° S? Could the ISS ever fly directly over the North Pole?**
5. **Why does each successive orbit shift westward on the world map?**
6. **How does OrbitX's calculated position differ from direct real-time GPS telemetry?**

## Deliverable

Each pair must report:
1. The four key files in the pipeline and what each file does (`app.py`, `orbital_engine.py`, `components.py`, `map_view.py`).
2. An explanation of why the orbital speed is reported as $\approx 7.66\text{ km/s}$ while ground speed is $\sim 7.2\text{ km/s}$.
3. One observation from the ground track slider investigation (e.g. how many orbits fit in 720 minutes, and why the path shifts westward).

---
*Learning Outcome: You understand the mathematical propagation pipeline from TLE orbital elements to live map tracks and coordinates.*
