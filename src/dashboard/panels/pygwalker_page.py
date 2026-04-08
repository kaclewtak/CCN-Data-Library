from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import polars as pl
from shiny import module, render, ui

# ---------------------------------------------------------------------------
# Inlined from pygwalker_utils/render_utils.py
# ---------------------------------------------------------------------------

_local_pygwalker = Path(__file__).resolve().parents[3] / "interactive_dash"
if _local_pygwalker.is_dir() and str(_local_pygwalker) not in sys.path:
    sys.path.insert(0, str(_local_pygwalker))

import pygwalker as pyg  # noqa: E402


def get_pygwalker_html(df: pl.DataFrame) -> str:
    return pyg.to_html(df, spec="", **{"width": "100%", "height": "100%"})


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
