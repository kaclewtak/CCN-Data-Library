import ipyleaflet
import pandas as pd
from ipywidgets import HTML
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget
from table import table_server, table_ui

# UI
app_ui = ui.page_fluid(
    ui.panel_title("Location + Data Editor"),
    ui.div(
        table_ui("data_editor"),
        style="height: 48vh; overflow: auto; border: 1px solid #ddd; border-radius: 8px; padding: 8px;",
    ),
    ui.br(),
    ui.div(
        ui.h4("Map Viewer"),
        ui.layout_columns(
            ui.input_numeric("lat", "Latitude:", value=25.286, step=0.01),
            ui.input_numeric("lng", "Longitude:", value=-81.178, step=0.01),
            ui.input_action_button("go", "Add manual point", class_="btn-primary"),
            col_widths=[4, 4, 4],
        ),
        ui.output_text_verbatim("map_status"),
        output_widget("map", height="38vh"),
        style="height: 48vh; overflow: auto; border: 1px solid #ddd; border-radius: 8px; padding: 8px;",
    ),
)


# Server
def server(input, output, session):
    # Table module outputs
    table_state = table_server("data_editor")

    # Manual location logic
    locations = reactive.Value(pd.DataFrame(columns=["ID", "Latitude", "Longitude"]))
    rendered_marker_count = reactive.Value(0)

    # Track map view state so it persists across redraws
    map_center = reactive.Value((25.286, -81.178))
    map_zoom = reactive.Value(13)

    @render_widget
    def map():
        manual_df = locations.get()
        table_points = table_state["map_points"]()

        layers = []

        for _, row in manual_df.iterrows():
            lat = float(row["Latitude"])
            lng = float(row["Longitude"])
            if not _is_valid_coordinate(lat, lng):
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

        for _, row in table_points.iterrows():
            lat = float(row["latitude"])
            lng = float(row["longitude"])
            if not _is_valid_coordinate(lat, lng):
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

        rendered_marker_count.set(len(layers))

        basemap_layer = ipyleaflet.basemap_to_tiles(ipyleaflet.basemaps.Esri.WorldImagery)
        return ipyleaflet.Map(
            basemap=ipyleaflet.basemaps.Esri.WorldImagery,
            center=map_center.get(),
            zoom=map_zoom.get(),
            layers=[basemap_layer] + layers,
        )

    def _is_valid_coordinate(latitude: float, longitude: float) -> bool:
        return -90 <= latitude <= 90 and -180 <= longitude <= 180

    @reactive.Effect
    @reactive.event(input.go)
    def update_locations():
        # Create new row
        current_df = locations.get()
        new_id = len(current_df) + 1
        lat = float(input.lat())
        lng = float(input.lng())

        if not _is_valid_coordinate(lat, lng):
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

        # Update Map View
        map_center.set((lat, lng))
        map_zoom.set(15)

    @render.text
    def map_status():
        manual_df = locations.get()
        table_points = table_state["map_points"]()
        return (
            f"Manual points: {len(manual_df)} | "
            f"Table points (enabled + valid): {len(table_points)} | "
            f"Rendered markers: {rendered_marker_count.get()}"
        )


app = App(app_ui, server)
