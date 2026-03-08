from __future__ import annotations

import ipyleaflet
import pandas as pd
from map_utils.marker_utils import (
    build_manual_markers,
    build_table_markers,
    delete_manual_marker,
    is_valid_coordinate,
)
from map_utils.view_utils import compute_imported_view
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
def map_server(input, output, session, table_points_getter, selected_point):
    # --- State ----------------------------------------------------------------
    locations = reactive.Value(pd.DataFrame(columns=["ID", "Latitude", "Longitude"]))
    rendered_marker_count = reactive.Value(0)
    map_center = reactive.Value((25.286, -81.178))
    map_zoom = reactive.Value(13)
    last_imported_view_key: dict[str, tuple[int, float, float, float] | None] = {"value": None}
    map_widget = reactive.Value(None)
    table_markers_ref: reactive.Value[list[ipyleaflet.CircleMarker]] = reactive.Value([])  # reactive list

    # --- Helpers ---------------------------------------------------------------
    def _set_map_view(center_lat: float, center_lng: float, zoom: int) -> None:
        map_center.set((center_lat, center_lng))
        map_zoom.set(zoom)

    # --- Render outputs --------------------------------------------------------
    @render_widget
    def map():
        manual_df = locations.get()
        table_points = table_points_getter()

        def on_delete(marker):
            updated = delete_manual_marker(marker, locations.get())
            locations.set(updated)

        manual_layers = build_manual_markers(manual_df, on_delete=on_delete)
        new_table_markers = build_table_markers(
            table_points,
            on_select=lambda idx: selected_point.set(idx),
        )
        with reactive.isolate():  # <-- wrap in isolate
            table_markers_ref.set(new_table_markers)

        layers = [*manual_layers, *new_table_markers]
        rendered_marker_count.set(len(layers))

        basemap_layer = ipyleaflet.basemap_to_tiles(ipyleaflet.basemaps.Esri.WorldImagery)
        m = ipyleaflet.Map(
            basemap=ipyleaflet.basemaps.Esri.WorldImagery,
            center=map_center.get(),
            zoom=map_zoom.get(),
            layers=[basemap_layer] + layers,
        )
        map_widget.set(m)
        return m

    # --- Update marker styles in place, no full re-render --------------------
    @reactive.effect
    def _update_selected_marker():
        markers = table_markers_ref.get()
        selected_idx = selected_point.get()

        if not markers or selected_idx is None:
            return

        for i, marker in enumerate(markers):
            is_selected = i == selected_idx
            marker.color = "#ff3369" if is_selected else "#7438cd"
            marker.fill_color = "#ff3369" if is_selected else "#7438cd"
            marker.fill_opacity = 1.0 if is_selected else 0.9
            marker.weight = 3 if is_selected else 2

        # --- Reactive effects: imported points focus ------------------------------
        @reactive.effect
        def _focus_map_on_imported_points():
            table_points = table_points_getter()
            imported_view = compute_imported_view(table_points)
            if imported_view is None:
                last_imported_view_key["value"] = None
                return

            (center_lat, center_lng), zoom, view_key = imported_view
            if last_imported_view_key["value"] == view_key:
                return

            last_imported_view_key["value"] = view_key
            _set_map_view(center_lat, center_lng, zoom)

    # --- Reactive effects: manual point actions -------------------------------
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
        _set_map_view(lat, lng, 15)

    @render.text
    def map_status():
        manual_df = locations.get()
        table_points = table_points_getter()
        return (
            f"Manual points: {len(manual_df)} | "
            f"Table points (enabled + valid): {len(table_points)} | "
            f"Rendered markers: {rendered_marker_count.get()}"
        )
