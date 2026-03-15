from __future__ import annotations

import polars as pl
import pygwalker as pyg


def get_pygwalker_html(df: pl.DataFrame) -> str:
    return pyg.to_html(df, height=1400)
