from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl
from shiny import module, reactive, render, ui
from table_helpers import (
    coerce_new_column_default,
    excel_sheet_names,
    find_lat_lon_columns,
    polars_to_pandas,
    set_cell_value,
)

# filepath: /home/klewtak/NASA/CCN-Data-Library/scripts/4_capstone/src/dashboard/dashboard_table.py


# ---------------------------
# UI
# ---------------------------
@module.ui
def table_ui():
    """
    UI for the table loader and cell editor module.
        - File upload for CSV/Excel with options
        - Display editable data grid
        - Show load status and current schema
        - Download edited data as CSV
    """
    return ui.TagList(
        ui.panel_title("Table Loader + Cell Editor"),
        ui.card(
            ui.card_header(
                ui.div(
                    ui.tags.strong("Editable Data"),
                    ui.div(
                        ui.input_action_button(
                            "show_load_controls",
                            "Load",
                            class_="btn-outline-secondary btn-sm",
                            title="Upload CSV/Excel and load options",
                        ),
                        ui.input_action_button(
                            "show_download_controls",
                            "Download",
                            class_="btn-outline-secondary btn-sm",
                            title="Download the currently edited table as CSV",
                        ),
                        ui.input_action_button(
                            "show_schema_controls",
                            "Schema",
                            class_="btn-outline-secondary btn-sm",
                            title="View detected dataframe schema",
                        ),
                        ui.input_action_button(
                            "show_status_controls",
                            "Status",
                            class_="btn-outline-secondary btn-sm",
                            title="View file load and validation status",
                        ),
                        ui.input_action_button(
                            "show_map_controls",
                            "Map",
                            class_="btn-outline-secondary btn-sm",
                            title="Enable/disable plotting detected lat/lon points",
                        ),
                        class_="d-flex flex-wrap gap-1",
                    ),
                    class_="d-flex justify-content-between align-items-center flex-wrap gap-2",
                )
            ),
            ui.output_ui("compact_controls_panel"),
            ui.div(
                ui.tags.style(
                    """
                    .table-controls-panel {
                        border: 1px solid #d9d9d9;
                        border-radius: 6px;
                        background: #f8f9fa;
                        padding: 0.5rem;
                        margin-bottom: 0.6rem;
                    }
                    .table-controls-panel .shiny-input-container {
                        margin-bottom: 0.45rem;
                    }
                    .load-controls-panel,
                    .load-controls-panel .bslib-grid,
                    .load-controls-panel .bslib-grid > * {
                        overflow: visible;
                    }
                    .load-controls-panel .shiny-file-input-progress,
                    .load-controls-panel .progress.shiny-file-input-progress {
                        margin-top: 0.35rem;
                        margin-bottom: 0.35rem;
                        min-height: 2.0rem;
                    }
                    .excel-toolbar {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 0.4rem;
                        align-items: center;
                        padding: 0.45rem;
                        margin-bottom: 0.6rem;
                        border: 1px solid #d9d9d9;
                        border-radius: 6px;
                        background: #f8f9fa;
                    }
                    .excel-toolbar .shiny-input-container {
                        margin-bottom: 0;
                    }
                    .excel-toolbar .control-label,
                    .excel-toolbar .form-label {
                        display: none;
                    }
                    .excel-toolbar .form-control,
                    .excel-toolbar .form-select {
                        height: 30px;
                        min-height: 30px;
                        padding: 0.2rem 0.45rem;
                        font-size: 0.82rem;
                    }
                    .excel-toolbar .btn.excel-btn {
                        padding: 0.2rem 0.5rem;
                        font-size: 0.78rem;
                        line-height: 1.2;
                    }
                    """
                ),
                ui.div(
                    ui.input_action_button("add_row", "+ Row", class_="btn-outline-secondary btn-sm excel-btn"),
                    ui.input_numeric("remove_row_index", "", value=0, min=0, step=1, width="96px"),
                    ui.input_action_button("remove_row", "- Row", class_="btn-outline-secondary btn-sm excel-btn"),
                    ui.input_text("new_col_name", "", value="", placeholder="Column name", width="150px"),
                    ui.input_select(
                        "new_col_type",
                        "",
                        choices=["string", "int", "float", "bool"],
                        selected="string",
                        width="110px",
                    ),
                    ui.input_text("new_col_default", "", value="", placeholder="Default", width="120px"),
                    ui.input_action_button("add_col", "+ Col", class_="btn-outline-secondary btn-sm excel-btn"),
                    ui.input_select("drop_col_name", "", choices=[], width="160px"),
                    ui.input_action_button("remove_col", "- Col", class_="btn-outline-secondary btn-sm excel-btn"),
                    class_="excel-toolbar",
                ),
            ),
            ui.output_data_frame("table"),
        ),
    )


# ---------------------------
# Server
# ---------------------------
@module.server
def table_server(input, output, session):
    data_pl = reactive.Value(None)  # type: ignore[var-annotated]
    status_msg = reactive.Value("Waiting for file upload.")
    source_name = reactive.Value("edited_data")
    lat_lon_cols = reactive.Value(None)  # type: ignore[var-annotated]
    use_points_on_map = reactive.Value(False)
    active_compact_panel = reactive.Value(None)  # type: ignore[var-annotated]
    highlighted_new_row = reactive.Value(None)  # type: ignore[var-annotated]
    highlighted_new_col = reactive.Value(None)  # type: ignore[var-annotated]

    def _is_blank_value(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        return False

    def _toggle_panel(panel_name: str) -> None:
        current = active_compact_panel.get()
        active_compact_panel.set(None if current == panel_name else panel_name)

    def _clear_highlights() -> None:
        highlighted_new_row.set(None)
        highlighted_new_col.set(None)

    def _require_df(action_name: str) -> pl.DataFrame | None:
        df = data_pl.get()
        if df is None:
            status_msg.set(f"{action_name} failed: no data loaded.")
            return None
        return df

    def _build_compact_controls(panel_name: str):
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
                    ui.input_action_button("load", "Load file", class_="btn-primary btn-sm"),
                    col_widths=[4, 3, 3, 2],
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

    def _read_uploaded_dataframe(file_info: dict[str, Any]) -> pl.DataFrame:
        path = file_info["datapath"]
        name = file_info["name"].lower()

        if name.endswith(".csv"):
            sep = input.csv_sep() or ","
            return pl.read_csv(path, separator=sep)

        if name.endswith((".xlsx", ".xls")):
            sheet = input.sheet_name()
            if sheet == "(first sheet)":
                return pl.read_excel(path)
            try:
                return pl.read_excel(path, sheet_name=sheet)
            except TypeError:
                pdf = pd.read_excel(path, sheet_name=sheet)
                return pl.from_pandas(pdf)

        raise ValueError("Unsupported file type. Use .csv/.xlsx/.xls")

    def _append_blank_row(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
        new_row = {col: None for col in df.columns}
        row_df = pl.DataFrame([new_row], schema=df.schema)
        updated = pl.concat([df, row_df], how="vertical_relaxed")
        return updated, updated.height - 1

    def _remove_row_from_bottom(df: pl.DataFrame, bottom_offset: int) -> tuple[pl.DataFrame, int]:
        if bottom_offset < 0 or bottom_offset >= df.height:
            raise ValueError(f"bottom offset {bottom_offset} out of range [0, {max(df.height - 1, 0)}].")

        row_idx = df.height - 1 - bottom_offset
        updated = df.filter(pl.int_range(0, df.height) != row_idx)
        return updated, row_idx

    def _add_column_with_default(
        df: pl.DataFrame,
        col_name: str,
        dtype_name: str,
        default_raw: str,
    ) -> pl.DataFrame:
        if not col_name:
            raise ValueError("column name is required.")
        if col_name in df.columns:
            raise ValueError(f"'{col_name}' already exists.")

        dtype_map: dict[str, pl.DataType] = {
            "string": pl.Utf8,
            "int": pl.Int64,
            "float": pl.Float64,
            "bool": pl.Boolean,
        }
        if dtype_name not in dtype_map:
            raise ValueError(f"Unsupported column type: {dtype_name}")

        default_value = coerce_new_column_default(default_raw, dtype_name)
        series = pl.Series(col_name, [default_value] * df.height, dtype=dtype_map[dtype_name])
        return df.with_columns(series)

    def _remove_existing_column(df: pl.DataFrame, col_name: str) -> pl.DataFrame:
        if df.width <= 1:
            raise ValueError("cannot remove the last remaining column.")
        if not col_name or col_name not in df.columns:
            raise ValueError("select a valid column.")
        return df.drop(col_name)

    def _sync_row_highlight_after_remove(removed_row_idx: int) -> None:
        marked_row = highlighted_new_row.get()
        if marked_row is None:
            return
        if removed_row_idx == marked_row:
            highlighted_new_row.set(None)
            return
        if removed_row_idx < marked_row:
            highlighted_new_row.set(marked_row - 1)

    def _clear_highlight_when_filled(df: pl.DataFrame) -> None:
        marked_row = highlighted_new_row.get()
        if marked_row is not None:
            if marked_row < 0 or marked_row >= df.height:
                highlighted_new_row.set(None)
            else:
                row_values = df.row(marked_row)
                if any(not _is_blank_value(value) for value in row_values):
                    highlighted_new_row.set(None)

        marked_col = highlighted_new_col.get()
        if marked_col is not None:
            if marked_col not in df.columns:
                highlighted_new_col.set(None)
            else:
                col_values = df.get_column(marked_col).to_list()
                if any(not _is_blank_value(value) for value in col_values):
                    highlighted_new_col.set(None)

    def _table_styles(df: pl.DataFrame) -> list[render.StyleInfo]:
        styles: list[render.StyleInfo] = []

        marked_row = highlighted_new_row.get()
        if marked_row is not None and 0 <= marked_row < df.height:
            styles.append(
                {
                    "rows": [marked_row],
                    "style": {
                        "paddingTop": "11px",
                        "paddingBottom": "11px",
                        "fontStyle": "italic",
                    },
                }
            )

        marked_col = highlighted_new_col.get()
        if marked_col is not None and marked_col in df.columns:
            styles.append(
                {
                    "cols": [marked_col],
                    "style": {
                        "minWidth": "150px",
                        "paddingTop": "8px",
                        "paddingBottom": "8px",
                        "fontStyle": "italic",
                    },
                }
            )
        return styles

    @reactive.effect
    @reactive.event(input.show_load_controls)
    def _toggle_load_controls():
        _toggle_panel("load")

    @reactive.effect
    @reactive.event(input.show_download_controls)
    def _toggle_download_controls():
        _toggle_panel("download")

    @reactive.effect
    @reactive.event(input.show_schema_controls)
    def _toggle_schema_controls():
        _toggle_panel("schema")

    @reactive.effect
    @reactive.event(input.show_status_controls)
    def _toggle_status_controls():
        _toggle_panel("status")

    @reactive.effect
    @reactive.event(input.show_map_controls)
    def _toggle_map_controls():
        _toggle_panel("map")

    @render.ui
    def compact_controls_panel():
        panel_name = active_compact_panel.get()
        if panel_name is None:
            return ui.div()
        return _build_compact_controls(panel_name)

    @reactive.effect
    def _sync_drop_column_choices():
        df = data_pl.get()
        choices = [] if df is None else df.columns
        selected = choices[0] if choices else None
        ui.update_select("drop_col_name", choices=choices, selected=selected)

    @reactive.effect
    @reactive.event(input.file)
    def _update_sheet_choices():
        files = input.file()
        if not files:
            ui.update_select("sheet_name", choices=["(first sheet)"], selected="(first sheet)")
            return

        f = files[0]
        source_name.set(Path(f["name"]).stem)
        name = f["name"].lower()

        if name.endswith((".xlsx", ".xls")):
            sheets = excel_sheet_names(f["datapath"])
            choices = sheets if sheets else ["(first sheet)"]
            ui.update_select("sheet_name", choices=choices, selected=choices[0])
        else:
            ui.update_select("sheet_name", choices=["(first sheet)"], selected="(first sheet)")

    @reactive.effect
    @reactive.event(input.load)
    def _load_file():
        files = input.file()
        if not files:
            status_msg.set("No file selected.")
            data_pl.set(None)
            _clear_highlights()
            return

        f = files[0]

        try:
            df = _read_uploaded_dataframe(f)

            data_pl.set(df)
            lat_lon_cols.set(find_lat_lon_columns(df.columns))
            use_points_on_map.set(False)
            _clear_highlights()
            status_msg.set(f"Loaded {f['name']} | rows={df.height}, cols={df.width}")
        except Exception as e:
            data_pl.set(None)
            lat_lon_cols.set(None)
            use_points_on_map.set(False)
            _clear_highlights()
            status_msg.set(f"Load failed: {e}")

    @render.ui
    def lat_lon_prompt():
        cols = lat_lon_cols.get()
        if cols is None:
            return ui.p("No latitude/longitude columns detected.")

        lat_col, lon_col = cols
        return ui.TagList(
            ui.p(f"Detected '{lat_col}' and '{lon_col}'. Do you want to display these points on the map?"),
            ui.input_switch("use_map_points", "Plot table points on map", value=False),
        )

    @reactive.effect
    def _sync_use_points_on_map():
        cols = lat_lon_cols.get()
        if cols is None:
            use_points_on_map.set(False)
            return
        use_points_on_map.set(bool(input.use_map_points()))

    @reactive.effect
    @reactive.event(input.add_row)
    def _add_row():
        df = _require_df("Add row")
        if df is None:
            return

        updated, added_row_idx = _append_blank_row(df)
        data_pl.set(updated)
        highlighted_new_row.set(added_row_idx)
        status_msg.set(f"Added row. rows={updated.height}, cols={updated.width}")

    @reactive.effect
    @reactive.event(input.remove_row)
    def _remove_row():
        df = _require_df("Remove row")
        if df is None:
            return

        bottom_offset = int(input.remove_row_index() or 0)
        try:
            updated, row_idx = _remove_row_from_bottom(df, bottom_offset)
            _sync_row_highlight_after_remove(row_idx)
            data_pl.set(updated)
            status_msg.set(
                f"Removed row from bottom offset {bottom_offset} (actual row index {row_idx}). "
                f"rows={updated.height}, cols={updated.width}"
            )
        except ValueError as e:
            status_msg.set(f"Remove row failed: {e}")

    @reactive.effect
    @reactive.event(input.add_col)
    def _add_column():
        df = _require_df("Add column")
        if df is None:
            return

        col_name = (input.new_col_name() or "").strip()
        try:
            updated = _add_column_with_default(
                df=df,
                col_name=col_name,
                dtype_name=input.new_col_type(),
                default_raw=input.new_col_default() or "",
            )
            data_pl.set(updated)
            highlighted_new_col.set(col_name)
            status_msg.set(f"Added column '{col_name}'. rows={updated.height}, cols={updated.width}")
        except ValueError as e:
            status_msg.set(f"Add column failed: {e}")

    @reactive.effect
    @reactive.event(input.remove_col)
    def _remove_column():
        df = _require_df("Remove column")
        if df is None:
            return

        col_name = input.drop_col_name()
        try:
            updated = _remove_existing_column(df, col_name)
            if highlighted_new_col.get() == col_name:
                highlighted_new_col.set(None)
            data_pl.set(updated)
            status_msg.set(f"Removed column '{col_name}'. rows={updated.height}, cols={updated.width}")
        except ValueError as e:
            status_msg.set(f"Remove column failed: {e}")

    @reactive.effect
    def _clear_highlight_when_no_longer_blank():
        df = data_pl.get()
        if df is None:
            _clear_highlights()
            return
        _clear_highlight_when_filled(df)

    @render.data_frame
    def table():
        df = data_pl.get()
        if df is None:
            return render.DataGrid(pd.DataFrame({"Info": ["Upload and load a file to begin editing."]}))
        styles = _table_styles(df)

        return render.DataGrid(
            polars_to_pandas(df),
            editable=True,
            selection_mode="none",
            styles=styles or None,
        )

    @table.set_patch_fn
    def _apply_patch(patch):
        df = data_pl.get()
        if df is None:
            raise ValueError("No data loaded.")

        # patch interface fields from Shiny
        row = int(patch["row_index"])
        col = int(patch["column_index"])
        value = patch["value"]

        col_name = df.columns[col]
        updated = set_cell_value(df, row, col_name, value)
        data_pl.set(updated)

        # returned value is what the client displays in edited cell
        return str(updated[row, col_name]) if updated[row, col_name] is not None else ""

    @render.text
    def status():
        return status_msg.get()

    @render.text
    def schema_text():
        df = data_pl.get()
        if df is None:
            return "No dataframe loaded."
        return "\n".join(f"{k}: {v}" for k, v in df.schema.items())

    @reactive.calc
    def map_points() -> pd.DataFrame:
        df = data_pl.get()
        cols = lat_lon_cols.get()

        if df is None or cols is None or not use_points_on_map.get():
            return pd.DataFrame(columns=["latitude", "longitude"])

        lat_col, lon_col = cols
        points = polars_to_pandas(df.select([lat_col, lon_col]))
        points = points.rename(columns={lat_col: "latitude", lon_col: "longitude"})
        points["latitude"] = pd.to_numeric(points["latitude"], errors="coerce")
        points["longitude"] = pd.to_numeric(points["longitude"], errors="coerce")
        points = points.dropna(subset=["latitude", "longitude"])
        return points

    @render.download(filename=lambda: f"{source_name.get()}_edited.csv")
    def download_csv():
        df = data_pl.get()
        if df is None:
            yield "No data loaded.\n"
            return
        yield df.write_csv()

    return {
        "map_points": map_points,
    }
