import ipyleaflet
import pandas as pd
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget
from table import table_server, table_ui

# UI
app_ui = ui.page_navbar(
    ui.nav_panel(
        "Location Viewer",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_numeric("lat", "Latitude:", value=25.286, step=0.01),
                ui.input_numeric("lng", "Longitude:", value=-81.178, step=0.01),
                ui.input_action_button("go", "Show on Map", class_="btn-primary"),
            ),
            output_widget("map", height="500px"),
            ui.hr(),
            ui.h4("Saved Locations"),
            ui.output_data_frame("loc_table"),
        ),
    ),
    ui.nav_panel("Data Editor", table_ui("data_editor")),
    title="Dashboard",
    id="tabs",
)


# Server
def server(input, output, session):
    # Location Viewer logic
    locations = reactive.Value(pd.DataFrame(columns=["ID", "Latitude", "Longitude"]))

    # Initialize Map
    m = ipyleaflet.Map(basemap=ipyleaflet.basemaps.Esri.WorldImagery, center=(25.286, -81.178), zoom=13)

    @render_widget
    def map():
        return m

    @reactive.Effect
    @reactive.event(input.go)
    def update_locations():
        # Create new row
        current_df = locations.get()
        new_id = len(current_df) + 1
        lat = input.lat()
        lng = input.lng()

        new_row = pd.DataFrame([[new_id, lat, lng]], columns=["ID", "Latitude", "Longitude"])
        updated_df = pd.concat([current_df, new_row], ignore_index=True)
        locations.set(updated_df)

        # Update Map View
        m.center = (lat, lng)
        m.zoom = 15

        # Re-draw markers
        # Filter out existing CircleMarkers to clear them (keeping other layers like tiles)
        base_layers = [l for l in m.layers if not isinstance(l, ipyleaflet.CircleMarker)]

        new_markers = []
        for idx, row in updated_df.iterrows():
            marker = ipyleaflet.CircleMarker(
                location=(row["Latitude"], row["Longitude"]),
                radius=8,
                color="#ff3333",
                fill_color="#ff3333",
                fill_opacity=0.9,
                weight=2,
                opacity=1,
            )
            # Add popup
            popup_content = f"ID: {row['ID']}<br>Lat: {row['Latitude']}<br>Lng: {row['Longitude']}"
            message = ipyleaflet.HTML()
            message.value = popup_content
            marker.popup = message

            new_markers.append(marker)

        m.layers = tuple(base_layers + new_markers)

    @render.data_frame
    def loc_table():
        return render.DataGrid(locations.get(), selection_mode="none")

    # Data Editor logic
    table_server("data_editor")


app = App(app_ui, server)
