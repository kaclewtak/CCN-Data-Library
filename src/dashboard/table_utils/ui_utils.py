from __future__ import annotations

from shiny import ui


def build_compact_controls(panel_name: str):
    if panel_name == "load":
        return ui.div(
            ui.layout_columns(
                ui.input_file(
                    "file",
                    "Upload CSV/Excel",
                    accept=[".csv", ".xlsx", ".xls"],
                    multiple=False,
                ),
                ui.input_select(
                    "sheet_name",
                    "Excel sheet",
                    choices=["(first sheet)"],
                    selected="(first sheet)",
                ),
                ui.input_text("csv_sep", "CSV separator", value=","),
                col_widths=[5, 4, 3],
            ),
            class_="table-controls-panel load-controls-panel",
        )

    if panel_name == "download":
        return ui.div(
            ui.download_button("download_csv", "Download edited CSV", class_="btn-sm"),
            class_="table-controls-panel",
        )

    if panel_name == "schema":
        return ui.div(
            ui.output_text_verbatim("schema_text"),
            class_="table-controls-panel",
        )

    if panel_name == "status":
        return ui.div(
            ui.output_text_verbatim("status"),
            class_="table-controls-panel",
        )

    if panel_name == "map":
        return ui.div(
            ui.output_ui("lat_lon_prompt"),
            class_="table-controls-panel",
        )

    return ui.div()
