from __future__ import annotations

import polars as pl
from shiny import render


def table_styles(
    df: pl.DataFrame,
    highlighted_new_row: int | None,
    highlighted_new_col: str | None,
) -> list[render.StyleInfo]:
    styles: list[render.StyleInfo] = []

    if highlighted_new_row is not None and 0 <= highlighted_new_row < df.height:
        styles.append(
            {
                "rows": [highlighted_new_row],
                "style": {
                    "paddingTop": "11px",
                    "paddingBottom": "11px",
                    "fontStyle": "italic",
                },
            }
        )

    if df.height > 0:
        styles.append(
            {
                "rows": [df.height - 1],
                "style": {
                    "paddingBottom": "22px",
                },
            }
        )

    if highlighted_new_col is not None and highlighted_new_col in df.columns:
        styles.append(
            {
                "cols": [highlighted_new_col],
                "style": {
                    "minWidth": "150px",
                    "paddingTop": "8px",
                    "paddingBottom": "8px",
                    "fontStyle": "italic",
                },
            }
        )

    return styles
