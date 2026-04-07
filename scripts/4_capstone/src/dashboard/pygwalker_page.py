from __future__ import annotations

from collections.abc import Callable

import polars as pl
from pygwalker_utils.render_utils import get_pygwalker_html
from shiny import module, render, ui


@module.ui
def pygwalker_ui():
    return ui.div(
        ui.div(
            ui.output_ui("pygwalker_view"),
            class_="pygwalker-container",
        ),
        class_="pygwalker-page",
    )


@module.server
def pygwalker_server(input, output, session, data_getter: Callable[[], pl.DataFrame | None]):
    @render.ui
    def pygwalker_view():
        df = data_getter()
        if df is None:
            return ui.div(
                ui.p("Upload a file on the Table Editor tab to explore data here."),
                style="padding: 2rem; color: #666;",
            )
        return ui.HTML(get_pygwalker_html(df))
