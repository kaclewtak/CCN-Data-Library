from __future__ import annotations

import ipyleaflet
import pandas as pd
from ipywidgets import HTML


def is_valid_coordinate(latitude: float, longitude: float) -> bool:
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def build_manual_markers(manual_df: pd.DataFrame) -> list[ipyleaflet.CircleMarker]:
    layers: list[ipyleaflet.CircleMarker] = []
    for _, row in manual_df.iterrows():
        lat = float(row["Latitude"])
        lng = float(row["Longitude"])
        if not is_valid_coordinate(lat, lng):
            continue
        marker = ipyleaflet.CircleMarker(
            location=(lat, lng),
            radius=9,
            color="#ff3333",
            fill_color="#ff3333",
            fill_opacity=1,
            weight=3,
            opacity=1,
        )
        marker.popup = HTML(value=f"Manual Point<br>Lat: {lat}<br>Lng: {lng}")
        layers.append(marker)
    return layers


def build_table_markers(table_points: pd.DataFrame) -> list[ipyleaflet.CircleMarker]:
    layers: list[ipyleaflet.CircleMarker] = []
    for _, row in table_points.iterrows():
        lat = float(row["latitude"])
        lng = float(row["longitude"])
        if not is_valid_coordinate(lat, lng):
            continue
        marker = ipyleaflet.CircleMarker(
            location=(lat, lng),
            radius=7,
            color="#fdcd3a",
            fill_color="#fdcd3a",
            fill_opacity=0.9,
            weight=2,
            opacity=1,
        )
        marker.popup = HTML(value=f"Table Point<br>Lat: {lat}<br>Lng: {lng}")
        layers.append(marker)
    return layers
