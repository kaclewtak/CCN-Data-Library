from eo_panel import eo_server, eo_ui
from data_inventory import data_inventory_server, data_inventory_ui
from map_panel import map_server, map_ui
from pygwalker_page import pygwalker_server, pygwalker_ui
from shiny import App, reactive, ui
from table import table_server, table_ui

app_ui = ui.page_fluid(
    ui.head_content(
        ui.tags.style(
            """
            html,
            body {
                height: 100%;
            }
            body > .container-fluid {
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }
            body > .container-fluid > h2,
            body > .container-fluid > .nav {
                flex: 0 0 auto;
            }
            body > .container-fluid > .tab-content {
                flex: 1 1 auto;
                min-height: 0;
                display: flex;
                flex-direction: column;
            }
            body > .container-fluid > .tab-content > .tab-pane {
                min-height: 0;
            }
            body > .container-fluid > .tab-content > .tab-pane.active {
                display: flex;
                flex: 1 1 auto;
                flex-direction: column;
            }
            .pygwalker-page {
                height: 88vh;
                overflow: hidden;
            }
            .pygwalker-container {
                display: flex;
                flex: 1 1 auto;
                height: 100%;
                min-height: 0;
                overflow: hidden !important;
            }
            /* Shiny 1.5+ sets display:contents on .shiny-html-output when it has
               children, which removes it from the box model and breaks height:100%
               resolution for all descendants. Override it here. */
            .pygwalker-container > .shiny-html-output,
            .pygwalker-container > .shiny-html-output > [id^="ifr-pyg-"] {
                display: flex !important;
                flex: 1 1 auto;
                height: 100% !important;
                min-height: 0;
            }
            .pygwalker-container [id^="ifr-pyg-"],
            .pygwalker-container iframe {
                width: 100% !important;
            }
            .pygwalker-container iframe {
                display: block;
                flex: 1 1 auto;
                min-height: 0;
                height: 100% !important;
            }
        """
        )
    ),
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
            "Satellite Search",
            eo_ui("eo_search"),
        ),
        ui.nav_panel(
            "Data Explorer",
            pygwalker_ui("pygwalker_explorer"),
        ),
        ui.nav_panel(
            "Data Inventory",
            data_inventory_ui("inventory"),
        ),
    ),
    # JS handler so table can scroll to a row when map marker is clicked
    ui.tags.script(
        """
        Shiny.addCustomMessageHandler("scroll_to_row", function(rowIndex) {
            setTimeout(function() {
                const grids = document.querySelectorAll(".shiny-data-grid-output, [data-testid='data-grid']");
                grids.forEach(function(grid) {
                    const rows = grid.querySelectorAll("tbody tr");
                    if (rows[rowIndex]) {
                        rows[rowIndex].scrollIntoView({ behavior: "smooth", block: "center" });
                        rows[rowIndex].style.outline = "2px solid #ff3333";
                        setTimeout(() => rows[rowIndex].style.outline = "", 1500);
                    }
                });
            }, 100);
        });

        document.addEventListener("shown.bs.tab", function(event) {
            if (event.target?.getAttribute("data-value") !== "Data Explorer") {
                return;
            }
            setTimeout(function() {
                window.dispatchEvent(new Event("resize"));
                document.querySelectorAll(".pygwalker-container iframe").forEach(function(iframe) {
                    try {
                        if (iframe.contentWindow) {
                            iframe.contentWindow.dispatchEvent(new Event("resize"));
                        }
                    } catch (error) {
                    }
                });
            }, 50);
        });
    """
    ),
)


def server(input, output, session):
    selected_point = reactive.Value(None)

    table_state = table_server(
        "data_editor",
        selected_point=selected_point,
    )
    map_server(
        "map_viewer",
        table_points_getter=table_state["map_points"],
        selected_point=selected_point,
    )
    eo_server(
        "eo_search",
        table_points_getter=table_state["map_points"],
    )
    table_state = table_server("data_editor", selected_point=selected_point)
    map_server("map_viewer", table_points_getter=table_state["map_points"], selected_point=selected_point)
    pygwalker_server("pygwalker_explorer", data_getter=table_state["data"])
    data_inventory_server("inventory")


app = App(app_ui, server)
