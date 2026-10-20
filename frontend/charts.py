"""Plotly charts for predicted telemetry (UTC time on every x-axis)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backend import config
from backend.models import Observer, SatellitePosition
from backend.orbital_engine import insert_antimeridian_gaps, split_track_segments

NAVY = "#0b1426"
PANEL = "#111c33"
CYAN = "#38bdf8"
GRID = "#24324f"
TEXT = "#d6e2f5"


def telemetry_figure(track: pd.DataFrame) -> go.Figure:
    """Latitude, longitude and altitude versus UTC time as three stacked panels.

    Longitude wraps from +180 to -180; lines are broken there instead of drawing a
    misleading vertical sweep.
    """
    plotted = insert_antimeridian_gaps(track)
    specs = [
        ("latitude_deg", "Latitude (°)", [-90, 90]),
        ("longitude_deg", "Longitude (°)", [-180, 180]),
        ("altitude_km", "Altitude (km)", None),
    ]
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
        subplot_titles=[label for _, label, _ in specs],
    )
    time_series = pd.to_datetime(plotted["time_utc"], utc=True)
    times_ist = time_series.dt.tz_convert(config.IST)
    for row, (column, label, axis_range) in enumerate(specs, start=1):
        fig.add_trace(
            go.Scatter(
                x=times_ist, y=plotted[column], mode="lines",
                line={"color": CYAN, "width": 2}, connectgaps=False,
                name=label, showlegend=False,
                hovertemplate="%{x|%d %b %Y, %I:%M:%S %p} IST<br>" + label + ": %{y:.2f}<extra></extra>",
            ),
            row=row, col=1,
        )
        fig.update_yaxes(title_text=label, range=axis_range, row=row, col=1)
    fig.update_xaxes(title_text="Time (IST)", row=3, col=1)
    fig.update_layout(
        height=620, margin={"l": 60, "r": 20, "t": 40, "b": 50},
        paper_bgcolor=NAVY, plot_bgcolor=PANEL, font={"color": TEXT},
    )
    fig.update_xaxes(gridcolor=GRID)
    fig.update_yaxes(gridcolor=GRID)
    for annotation in fig.layout.annotations:  # subplot titles
        annotation.font = {"color": TEXT, "size": 12}
    return fig


def track_figure(
    track: pd.DataFrame,
    position: SatellitePosition,
    observer: Observer | None = None,
) -> go.Figure:
    """Plain latitude/longitude plot of the ground track.

    Unlike the Folium map it needs no internet (no map tiles, no CDN scripts), so it is
    the fallback view when the venue network is down. The track is split at the
    antimeridian exactly as on the map.
    """
    fig = go.Figure()
    for index, segment in enumerate(split_track_segments(track)):
        if len(segment) < 2:
            continue
        fig.add_trace(
            go.Scatter(
                x=[lon for _, lon in segment], y=[lat for lat, _ in segment], mode="lines",
                line={"color": CYAN, "width": 2}, name="Predicted ground track",
                legendgroup="track", showlegend=index == 0, hoverinfo="skip",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=[position.longitude_deg], y=[position.latitude_deg], mode="markers", name="ISS now",
            marker={"color": "#f97316", "size": 12, "line": {"color": "#ffffff", "width": 2}},
        )
    )
    if observer is not None:
        fig.add_trace(
            go.Scatter(
                x=[observer.longitude_deg], y=[observer.latitude_deg], mode="markers",
                name=observer.name, marker={"color": "#a3e635", "size": 10, "symbol": "diamond"},
            )
        )
    fig.update_xaxes(title_text="Longitude (°)", range=[-180, 180], dtick=30, gridcolor=GRID)
    fig.update_yaxes(title_text="Latitude (°)", range=[-90, 90], dtick=30, gridcolor=GRID)
    fig.update_layout(
        height=420, margin={"l": 60, "r": 20, "t": 20, "b": 50},
        paper_bgcolor=NAVY, plot_bgcolor=PANEL, font={"color": TEXT},
        legend={"orientation": "h", "y": -0.2},
    )
    return fig
