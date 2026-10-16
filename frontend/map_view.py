"""Folium map of the ISS sub-satellite point, ground track and optional observer."""

from __future__ import annotations

import folium

from backend.formatting import format_latitude, format_longitude, format_utc
from backend.models import Observer, SatellitePosition

TRACK_COLOR = "#38bdf8"
ISS_COLOR = "#f97316"
OBSERVER_COLOR = "#a3e635"


def build_map(
    position: SatellitePosition,
    track_segments: list[list[tuple[float, float]]],
    observer: Observer | None = None,
    illustrative: bool = False,
) -> folium.Map:
    """Build the map. ``illustrative`` relabels the marker when elements are expired."""
    fmap = folium.Map(
        location=[position.latitude_deg, position.longitude_deg],
        zoom_start=2,
        min_zoom=1,
        tiles="OpenStreetMap",  # key-free; folium warns CartoDB tiles now need an API key
        world_copy_jump=True,
        control_scale=True,
    )

    track_group = folium.FeatureGroup(name="Predicted ground track", show=True)
    for segment in track_segments:
        if len(segment) >= 2:
            folium.PolyLine(segment, color=TRACK_COLOR, weight=2, opacity=0.85).add_to(track_group)
    track_group.add_to(fmap)

    label = "ISS (illustrative position)" if illustrative else "ISS"
    popup = (
        f"<b>{label}</b><br>{format_utc(position.time_utc)}<br>"
        f"{format_latitude(position.latitude_deg)}, {format_longitude(position.longitude_deg)}<br>"
        f"Altitude {position.altitude_km:.0f} km"
    )
    folium.CircleMarker(
        [position.latitude_deg, position.longitude_deg],
        radius=9, color="#ffffff", weight=2, fill=True, fill_color=ISS_COLOR, fill_opacity=1,
        tooltip=label, popup=folium.Popup(popup, max_width=260),
    ).add_to(fmap)

    if observer is not None:
        folium.Marker(
            [observer.latitude_deg, observer.longitude_deg],
            tooltip=observer.name,
            icon=folium.Icon(color="green", icon="user", prefix="fa"),
        ).add_to(fmap)

    folium.LayerControl(collapsed=True).add_to(fmap)
    return fmap
