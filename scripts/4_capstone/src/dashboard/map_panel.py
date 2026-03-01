from __future__ import annotations

from collections.abc import Callable

import ipyleaflet
import pandas as pd
from map_helpers import (
    build_manual_markers,
    build_table_markers,
    is_valid_coordinate,
    zoom_for_span,
)
from shiny import module, reactive, render, ui
from shinywidgets import output_widget, render_widget


@module.ui
def map_ui():
    return ui.div(
        ui.h4("Map Viewer"),
        ui.layout_columns(
            ui.input_numeric("lat", "Latitude:", value=25.286, step=0.01),
            ui.input_numeric("lng", "Longitude:", value=-81.178, step=0.01),
            ui.input_action_button("go", "Add manual point", class_="btn-primary"),
            col_widths=[4, 4, 4],
        ),
        ui.output_text_verbatim("map_status"),
        output_widget("map", height="84vh"),
    )


@module.server
def map_server(input, output, session, table_points_getter: Callable[[], pd.DataFrame]):
    locations = reactive.Value(pd.DataFrame(columns=["ID", "Latitude", "Longitude"]))
    rendered_marker_count = reactive.Value(0)

    map_center = reactive.Value((25.286, -81.178))
    map_zoom = reactive.Value(13)
    last_imported_view_key: dict[str, tuple[int, float, float, float] | None] = {"value": None}

    @render_widget
    def map():
        manual_df = locations.get()
        table_points = table_points_getter()

        layers = [*build_manual_markers(manual_df), *build_table_markers(table_points)]
        rendered_marker_count.set(len(layers))

        basemap_layer = ipyleaflet.basemap_to_tiles(ipyleaflet.basemaps.Esri.WorldImagery)
        return ipyleaflet.Map(
            basemap=ipyleaflet.basemaps.Esri.WorldImagery,
            center=map_center.get(),
            zoom=map_zoom.get(),
            layers=[basemap_layer] + layers,
        )

    @reactive.effect
    def _focus_map_on_imported_points():
        table_points = table_points_getter()
        if table_points.empty:
            last_imported_view_key["value"] = None
            return

        points = table_points.copy()
        points["latitude"] = pd.to_numeric(points["latitude"], errors="coerce")
        points["longitude"] = pd.to_numeric(points["longitude"], errors="coerce")
        points = points.dropna(subset=["latitude", "longitude"])

        if points.empty:
            last_imported_view_key["value"] = None
            return

        center_lat = float(points["latitude"].mean())
        center_lng = float(points["longitude"].mean())
        lat_span = float(points["latitude"].max() - points["latitude"].min())
        lng_span = float(points["longitude"].max() - points["longitude"].min())
        span = max(lat_span, lng_span)
        zoom = zoom_for_span(span)

        view_key = (len(points), round(center_lat, 5), round(center_lng, 5), round(span, 5))
        if last_imported_view_key["value"] == view_key:
            return

        last_imported_view_key["value"] = view_key
        map_center.set((center_lat, center_lng))
        map_zoom.set(zoom)

    @reactive.Effect
    @reactive.event(input.go)
    def update_locations():
        current_df = locations.get()
        new_id = len(current_df) + 1
        lat = float(input.lat())
        lng = float(input.lng())

        if not is_valid_coordinate(lat, lng):
            ui.notification_show(
                "Invalid coordinates. Latitude must be in [-90, 90] and longitude in [-180, 180].",
                type="error",
                duration=5,
            )
            return

        updated_df = current_df.copy()
        updated_df.loc[len(updated_df)] = {
            "ID": new_id,
            "Latitude": lat,
            "Longitude": lng,
        }
        locations.set(updated_df)

        map_center.set((lat, lng))
        map_zoom.set(15)

    @render.text
    def map_status():
        manual_df = locations.get()
        table_points = table_points_getter()
        return (
            f"Manual points: {len(manual_df)} | "
            f"Table points (enabled + valid): {len(table_points)} | "
            f"Rendered markers: {rendered_marker_count.get()}"
        )
