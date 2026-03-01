from __future__ import annotations

import ipyleaflet
import pandas as pd
from ipywidgets import HTML


def is_valid_coordinate(latitude: float, longitude: float) -> bool:
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def zoom_for_span(span_degrees: float) -> int:
    if span_degrees <= 0.02:
        return 15
    if span_degrees <= 0.05:
        return 14
    if span_degrees <= 0.1:
        return 13
    if span_degrees <= 0.25:
        return 12
    if span_degrees <= 0.5:
        return 11
    if span_degrees <= 1.0:
        return 10
    if span_degrees <= 2.0:
        return 9
    if span_degrees <= 5.0:
        return 8
    if span_degrees <= 10.0:
        return 7
    if span_degrees <= 20.0:
        return 6
    return 4


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
            color="#1f78b4",
            fill_color="#1f78b4",
            fill_opacity=0.9,
            weight=2,
            opacity=1,
        )
        marker.popup = HTML(value=f"Table Point<br>Lat: {lat}<br>Lng: {lng}")
        layers.append(marker)
    return layers
