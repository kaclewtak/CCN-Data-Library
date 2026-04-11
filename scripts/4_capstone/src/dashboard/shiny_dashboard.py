from typing import Any

from panels.data_inventory import data_inventory_server, data_inventory_ui
from panels.eo_panel import eo_server, eo_ui
from panels.pygwalker_page import pygwalker_server, pygwalker_ui
from panels.qa_panel import qa_server, qa_ui
from shiny import App, ui


def _call_module_ui(module_ui: Any, module_id: str) -> Any:
    return module_ui(module_id)


def _call_module_server(module_server: Any, module_id: str, /, **kwargs: Any) -> Any:
    return module_server(module_id, **kwargs)


app_ui = ui.page_fluid(
    ui.head_content(
        ui.tags.script(src="https://cdn.plot.ly/plotly-2.35.2.min.js"),
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
            /* ---- CCN SOFT-DISABLED START: original .shiny-html-output rules ----
             * The output_ui element no longer exists; replaced by the persistent
             * #ccn_pygwalker_host div.  Restore these if reverting to the original
             * output_ui approach in pygwalker_page.py.
            .pygwalker-container > .shiny-html-output,
            .pygwalker-container > .shiny-html-output > [id^="ifr-pyg-"] {
                display: flex !important;
                flex: 1 1 auto;
                height: 100% !important;
                min-height: 0;
            }
             * ---- CCN SOFT-DISABLED END ---- */

            /* ---- CCN ADDITION START: flex sizing for persistent host div ---- */
            #ccn_pygwalker_host {
                display: flex;
                flex: 1 1 auto;
                height: 100%;
                min-height: 0;
            }
            #ccn_pygwalker_host > [id^="ifr-pyg-"] {
                display: flex !important;
                flex: 1 1 auto;
                height: 100% !important;
                min-height: 0;
            }
            /* ---- CCN ADDITION END ---- */
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
        ),
    ),
    ui.panel_title("CCN Data Library Dashboard"),
    ui.navset_tab(
        ui.nav_panel(
            "Data Explorer",
            _call_module_ui(pygwalker_ui, "pygwalker_explorer"),
        ),
        ui.nav_panel(
            "Satellite Search",
            _call_module_ui(eo_ui, "eo_search"),
        ),
        ui.nav_panel(
            "Data Inventory",
            _call_module_ui(data_inventory_ui, "inventory"),
        ),
        ui.nav_panel(
            "QA Dashboard",
            _call_module_ui(qa_ui, "qa_dashboard"),
        ),
    ),
    ui.tags.script(
        """
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


def server(_input, _output, _session):
    explorer_state = _call_module_server(pygwalker_server, "pygwalker_explorer")
    _call_module_server(
        eo_server,
        "eo_search",
        table_points_getter=explorer_state["all_geo_points"],
    )
    _call_module_server(data_inventory_server, "inventory")
    _call_module_server(qa_server, "qa_dashboard", data_getter=explorer_state["data"])


app = App(app_ui, server)
