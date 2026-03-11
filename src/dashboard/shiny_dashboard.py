from map_panel import map_server, map_ui
from pygwalker_page import pygwalker_server, pygwalker_ui
from shiny import App, ui
from table import table_server, table_ui

# UI
app_ui = ui.page_fluid(
    ui.panel_title("CCN Data Library Dashboard"),
    ui.navset_tab(
        ui.nav_panel(
            "Table & Map",
            ui.layout_columns(
                ui.div(
                    table_ui("data_editor"),
                    style="height: 88vh; overflow: auto; border: 1px solid #ddd; border-radius: 8px; padding: 8px;",
                ),
                ui.div(
                    map_ui("map_viewer"),
                    style="height: 88vh; overflow: auto; border: 1px solid #ddd; border-radius: 8px; padding: 8px;",
                ),
                col_widths=[6, 6],
            ),
        ),
        ui.nav_panel(
            "Data Explorer",
            pygwalker_ui("pygwalker_explorer"),
        ),
    ),
)


# Server
def server(input, output, session):
    table_state = table_server("data_editor")
    map_server("map_viewer", table_points_getter=table_state["map_points"])
    pygwalker_server("pygwalker_explorer", data_getter=table_state["data"])


app = App(app_ui, server)
