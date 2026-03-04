from __future__ import annotations

from typing import Callable

import ipyleaflet
import ipywidgets as widgets
import pandas as pd
from ipywidgets import HTML


def is_valid_coordinate(latitude: float, longitude: float) -> bool:
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def delete_manual_marker(marker: ipyleaflet.CircleMarker, manual_df: pd.DataFrame) -> pd.DataFrame:
    lat, lng = marker.location
    updated_df = manual_df[~((manual_df["Latitude"] == lat) & (manual_df["Longitude"] == lng))].reset_index(drop=True)
    return updated_df


def build_manual_markers(
    manual_df: pd.DataFrame, on_delete: Callable[[ipyleaflet.CircleMarker], None] | None = None
) -> list[ipyleaflet.CircleMarker]:
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
        # marker.popup = HTML(value=f"Manual Point<br>Lat: {lat}<br>Lng: {lng}")
        delete_btn = widgets.Button(
            description="Delete",
            button_style="danger",
            layout=widgets.Layout(width="90px", height="28px"),
        )
        info_html = widgets.HTML(value=f"<b>Manual Point</b><br>Lat: {lat}<br>Long: {lng}<br>")
        marker.popup = widgets.VBox([info_html, delete_btn])

        if on_delete:

            def make_handler(m):
                def handle_click(b):
                    on_delete(m)

                return handle_click

            delete_btn.on_click(make_handler(marker))
        layers.append(marker)
    return layers


# def build_manual_markers(manual_df: pd.DataFrame) -> list[ipyleaflet.CircleMarker]:
#     layers: list[ipyleaflet.CircleMarker] = []
#     for _, row in manual_df.iterrows():
#         lat = float(row["Latitude"])
#         lng = float(row["Longitude"])
#         if not is_valid_coordinate(lat, lng):
#             continue
#         marker = ipyleaflet.CircleMarker(
#             location=(lat, lng),
#             radius=9,
#             color="#ff3333",
#             fill_color="#ff3333",
#             fill_opacity=1,
#             weight=3,
#             opacity=1,
#         )
#         marker.popup = HTML(value=f"Manual Point<br>Lat: {lat}<br>Long: {lng}<br> Delete Point: btn")
#         layers.append(marker)
#     return layers


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
