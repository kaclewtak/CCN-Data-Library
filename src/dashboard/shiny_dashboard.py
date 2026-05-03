import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from panels.carbon_modeling import carbon_modeling_ui
from panels.data_inventory import data_inventory_server, data_inventory_ui
from panels.eo_panel import eo_server, eo_ui
from panels.metadata_panel import metadata_ui
from panels.pygwalker_page import pygwalker_server, pygwalker_ui
from panels.qa_panel import qa_server, qa_ui
from shiny import App, ui

DASHBOARD_DIR = Path(__file__).resolve().parent


def _dashboard_runtime_dependencies():
    try:
        from ccn_dashboard.data_provider import ensure_synthesis_data_dir
        from ccn_dashboard.pygwalker_assets import validate_pygwalker_assets
    except ModuleNotFoundError:
        src_root = Path(__file__).resolve().parents[1]
        if str(src_root) not in sys.path:
            sys.path.insert(0, str(src_root))
        from ccn_dashboard.data_provider import ensure_synthesis_data_dir
        from ccn_dashboard.pygwalker_assets import validate_pygwalker_assets
    return ensure_synthesis_data_dir, validate_pygwalker_assets


@lru_cache(maxsize=1)
def ensure_dashboard_runtime() -> None:
    ensure_synthesis_data_dir, validate_pygwalker_assets = _dashboard_runtime_dependencies()
    validate_pygwalker_assets()
    ensure_synthesis_data_dir(required=True, timeout=120.0)


def _call_module_ui(module_ui: Any, module_id: str) -> Any:
    return module_ui(module_id)


def _call_module_server(module_server: Any, module_id: str, /, **kwargs: Any) -> Any:
    return module_server(module_id, **kwargs)


app_ui = ui.page_fluid(
    ui.head_content(
        ui.tags.title("CCN Data Library Dashboard"),
        ui.tags.script(src="https://cdn.plot.ly/plotly-2.35.2.min.js"),
        ui.tags.style("""
            :root {
                --ccn-serc-navy: #002c5f;
                --ccn-serc-teal: #006c6f;
                --ccn-serc-teal-soft: #eef8f7;
                --ccn-serc-gold: #c8912f;
                --ccn-serc-ink: #17212b;
                --ccn-serc-muted: #657385;
                --ccn-serc-line: #d7e0e7;
                --ccn-serc-bg: #e8eef2;
                --ccn-serc-paper: #f7fafb;
                --ccn-serc-panel: #ffffff;
            }
            html,
            body {
                height: 100%;
            }
            body {
                color: var(--ccn-serc-ink);
                background: var(--ccn-serc-bg);
            }
            body > .container-fluid {
                min-height: 100vh;
                max-width: none;
                padding: 0;
                display: flex;
                flex-direction: column;
                background: var(--ccn-serc-bg);
            }
            .ccn-serc-topbar {
                min-height: 38px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                padding: 0 22px;
                color: #ffffff;
                background: var(--ccn-serc-navy);
                font-size: 0.78rem;
                font-weight: 700;
            }
            .ccn-dashboard-body {
                flex: 1 1 auto;
                min-height: 0;
                display: flex;
                padding: 18px 22px 22px;
                background: var(--ccn-serc-paper);
            }
            .ccn-main-content {
                flex: 1 1 auto;
                min-width: 0;
                min-height: 0;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .ccn-workspace-header {
                display: flex;
                align-items: flex-end;
                justify-content: space-between;
                gap: 1rem;
            }
            .ccn-workspace-title {
                margin: 0;
                color: #18324a;
                font-size: 1.32rem;
                font-weight: 750;
                line-height: 1.15;
            }
            .ccn-workspace-subtitle {
                margin: 4px 0 0;
                color: var(--ccn-serc-muted);
                font-size: 0.84rem;
            }
            .ccn-status-chip {
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                min-height: 24px;
                padding: 4px 8px;
                border: 1px solid rgba(15, 23, 42, 0.1);
                border-radius: 999px;
                color: #344054;
                background: #edf4f6;
                font-size: 0.72rem;
                font-weight: 700;
                white-space: nowrap;
            }
            .ccn-status-dot {
                width: 8px;
                height: 8px;
                border-radius: 999px;
                background: #2f8a62;
                box-shadow: 0 0 0 4px rgba(47, 138, 98, 0.14);
            }
            .ccn-main-content > .nav {
                flex: 0 0 auto;
                gap: 2px;
                padding: 0 0 0 0;
                border-bottom: 1px solid var(--ccn-serc-line);
                background: #eef4f7;
                overflow-x: auto;
            }
            .ccn-main-content > .nav > .nav-item > .nav-link {
                min-height: 42px;
                display: flex;
                align-items: center;
                border: 0;
                border-bottom: 3px solid transparent;
                border-radius: 0;
                color: #334155;
                font-size: 0.86rem;
                font-weight: 700;
                white-space: nowrap;
            }
            .ccn-main-content > .nav > .nav-item > .nav-link.active {
                color: var(--ccn-serc-teal);
                background: #ffffff;
                border-bottom-color: var(--ccn-serc-teal);
            }
            .ccn-main-content > .tab-content {
                flex: 1 1 auto;
                min-height: 0;
                display: flex;
                flex-direction: column;
                background: transparent;
            }
            .ccn-main-content > .tab-content > .tab-pane {
                min-height: 0;
            }
            .ccn-main-content > .tab-content > .tab-pane.active {
                display: flex;
                flex: 1 1 auto;
                flex-direction: column;
            }
            .ccn-main-content .card {
                border-color: var(--ccn-serc-line);
                border-radius: 8px;
                box-shadow: none;
            }
            .ccn-main-content .card-header {
                background: #ffffff;
                border-bottom-color: #edf2f5;
                font-weight: 700;
            }
            .pygwalker-page {
                flex: 1 1 auto;
                height: calc(100vh - 172px);
                min-height: 720px;
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
            @media (max-width: 1180px) {
                .pygwalker-page {
                    height: calc(100vh - 164px);
                }
            }
            @media (max-width: 760px) {
                .ccn-serc-topbar,
                .ccn-workspace-header {
                    align-items: stretch;
                    flex-direction: column;
                }
                .ccn-dashboard-body {
                    padding: 12px;
                }
                .pygwalker-page {
                    min-height: 640px;
                }
            }
        """),
    ),
    ui.div(
        ui.span("Smithsonian Environmental Research Center"),
        ui.span("CCN Data Library"),
        class_="ccn-serc-topbar",
    ),
    ui.div(
        ui.div(
            ui.div(
                ui.div(
                    ui.h2("CCN Data Library Dashboard", class_="ccn-workspace-title"),
                    ui.p(
                        "Import, explore, validate, and route CCN data through the dashboard workflow.",
                        class_="ccn-workspace-subtitle",
                    ),
                ),
                ui.span(
                    ui.span(class_="ccn-status-dot"),
                    "Dashboard ready",
                    class_="ccn-status-chip",
                ),
                class_="ccn-workspace-header",
            ),
            ui.navset_tab(
                ui.nav_panel(
                    "Data Explorer",
                    _call_module_ui(pygwalker_ui, "pygwalker_explorer"),
                ),
                ui.nav_panel(
                    "QA Dashboard",
                    _call_module_ui(qa_ui, "qa_dashboard"),
                ),
                ui.nav_panel(
                    "Satellite Search",
                    _call_module_ui(eo_ui, "eo_search"),
                ),
                ui.nav_panel(
                    "Carbon Modeling",
                    _call_module_ui(carbon_modeling_ui, "carbon_modeling"),
                ),
                ui.nav_panel(
                    "Data Inventory",
                    _call_module_ui(data_inventory_ui, "inventory"),
                ),
                ui.nav_panel(
                    "Metadata",
                    _call_module_ui(metadata_ui, "metadata"),
                ),
            ),
            class_="ccn-main-content",
        ),
        class_="ccn-dashboard-body",
    ),
    ui.tags.script("""
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
    """),
)


def server(_input, _output, _session):
    ensure_dashboard_runtime()
    explorer_state = _call_module_server(pygwalker_server, "pygwalker_explorer")
    _call_module_server(
        eo_server,
        "eo_search",
        table_points_getter=explorer_state["all_geo_points"],
    )
    _call_module_server(data_inventory_server, "inventory")
    _call_module_server(qa_server, "qa_dashboard", data_getter=explorer_state["data"])


app = App(app_ui, server, static_assets={"/images": DASHBOARD_DIR / "images"})
