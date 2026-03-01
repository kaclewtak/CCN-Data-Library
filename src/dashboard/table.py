from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl
from shiny import module, reactive, render, ui

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
# Helpers
# ---------------------------
def _excel_sheet_names(path: str) -> list[str]:
    """
    Get the sheet names from an Excel file.

    Args:
        path: Path to the Excel file.

    Returns:
        A list of sheet names.
    """
    try:
        xl = pd.ExcelFile(path)
        return xl.sheet_names or []
    except Exception:
        return []


def _coerce_value(raw_value: Any, dtype: pl.DataType) -> Any:
    """
    Coerce a raw value to the specified Polars data type.

    Args:
        raw_value: The value to coerce (from the editable grid).
        dtype: The target Polars data type.

    Returns:
        The coerced value in the appropriate Python type for the Polars dtype.
    """
    # Empty string -> null
    if raw_value in ("", None):
        return None

    try:
        if dtype in (pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64):
            return int(raw_value)
        if dtype in (pl.Float32, pl.Float64):
            return float(raw_value)
        if dtype == pl.Boolean:
            s = str(raw_value).strip().lower()
            if s in {"true", "1", "yes", "y"}:
                return True
            if s in {"false", "0", "no", "n"}:
                return False
            raise ValueError("Invalid boolean value")
        if dtype == pl.Date:
            return pd.to_datetime(raw_value).date()
        if dtype == pl.Datetime:
            return pd.to_datetime(raw_value).to_pydatetime()
        if dtype == pl.Time:
            return pd.to_datetime(raw_value).time()
        # Utf8, categorical, etc.
        return str(raw_value)
    except Exception as e:
        raise ValueError(f"Cannot convert '{raw_value}' to {dtype}") from e


def _set_cell_value(df: pl.DataFrame, row_idx: int, col_name: str, new_value: Any) -> pl.DataFrame:
    """
    Update a single cell in a Polars DataFrame while preserving the schema/dtype.

    Args:
        df: The Polars DataFrame.
        row_idx: The index of the row to update.
        col_name: The name of the column to update.
        new_value: The new value to set.

    Returns:
        A new Polars DataFrame with the updated cell.
    """
    # Update a single cell while preserving schema/dtype
    dtype = df.schema[col_name]
    coerced = _coerce_value(new_value, dtype)

    updated = (
        df.with_row_index("__rowid")
        .with_columns(
            pl.when(pl.col("__rowid") == row_idx)
            .then(pl.lit(coerced, dtype=dtype))
            .otherwise(pl.col(col_name))
            .alias(col_name)
        )
        .drop("__rowid")
    )
    return updated


def _polars_to_pandas(df: pl.DataFrame) -> pd.DataFrame:
    """
    Convert a Polars DataFrame to a Pandas DataFrame.

    Args:
        df: The Polars DataFrame.

    Returns:
        A Pandas DataFrame.
    """
    try:
        return df.to_pandas()
    except ModuleNotFoundError:
        return pd.DataFrame(df.to_dicts())


def _find_lat_lon_columns(columns: list[str]) -> tuple[str, str] | None:
    def _normalize(name: str) -> str:
        normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
        while "__" in normalized:
            normalized = normalized.replace("__", "_")
        return normalized

    def _tokens(name: str) -> list[str]:
        normalized = _normalize(name)
        return [tok for tok in normalized.split("_") if tok]

    def _is_lat_candidate(name: str) -> bool:
        token_set = set(_tokens(name))
        if token_set.intersection({"lat", "latitude"}):
            return True
        normalized = _normalize(name)
        return normalized.endswith("latitude") or normalized.endswith("_lat") or normalized == "lat"

    def _is_lon_candidate(name: str) -> bool:
        token_set = set(_tokens(name))
        if token_set.intersection({"lon", "lng", "long", "longitude"}):
            return True
        normalized = _normalize(name)
        return (
            normalized.endswith("longitude")
            or normalized.endswith("_lon")
            or normalized.endswith("_lng")
            or normalized == "lon"
            or normalized == "lng"
        )

    def _stem(name: str, axis: str) -> str:
        lat_terms = {"lat", "latitude"}
        lon_terms = {"lon", "lng", "long", "longitude"}
        remove = lat_terms if axis == "lat" else lon_terms
        stem_tokens = [tok for tok in _tokens(name) if tok not in remove]
        return "_".join(stem_tokens)

    lat_matches = [(idx, col) for idx, col in enumerate(columns) if _is_lat_candidate(col)]
    lon_matches = [(idx, col) for idx, col in enumerate(columns) if _is_lon_candidate(col)]

    if not lat_matches or not lon_matches:
        return None

    best_pair: tuple[str, str] | None = None
    best_score = -1
    best_order = (10**9, 10**9)

    for lat_idx, lat_col in lat_matches:
        lat_stem = _stem(lat_col, "lat")
        for lon_idx, lon_col in lon_matches:
            lon_stem = _stem(lon_col, "lon")

            score = 0
            if lat_stem and lon_stem and lat_stem == lon_stem:
                score += 3
            if _normalize(lat_col) in {"lat", "latitude"}:
                score += 2
            if _normalize(lon_col) in {"lon", "lng", "longitude"}:
                score += 2

            order = (lat_idx, lon_idx)
            if score > best_score or (score == best_score and order < best_order):
                best_score = score
                best_order = order
                best_pair = (lat_col, lon_col)

    return best_pair


def _coerce_new_column_default(raw_value: str, dtype_name: str) -> Any:
    if raw_value == "":
        return None

    normalized = dtype_name.strip().lower()
    if normalized == "string":
        return str(raw_value)
    if normalized == "int":
        return int(raw_value)
    if normalized == "float":
        return float(raw_value)
    if normalized == "bool":
        s = str(raw_value).strip().lower()
        if s in {"true", "1", "yes", "y"}:
            return True
        if s in {"false", "0", "no", "n"}:
            return False
        raise ValueError("Default bool value must be true/false, 1/0, yes/no, y/n")

    raise ValueError(f"Unsupported column type: {dtype_name}")


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
            sheets = _excel_sheet_names(f["datapath"])
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
            return

        f = files[0]
        path = f["datapath"]
        name = f["name"].lower()

        try:
            if name.endswith(".csv"):
                sep = input.csv_sep() or ","
                df = pl.read_csv(path, separator=sep)
            elif name.endswith((".xlsx", ".xls")):
                sheet = input.sheet_name()
                if sheet == "(first sheet)":
                    # read first sheet (default)
                    df = pl.read_excel(path)
                else:
                    # Polars currently supports sheet_name in recent versions
                    # fallback to pandas for compatibility if needed.
                    try:
                        df = pl.read_excel(path, sheet_name=sheet)
                    except TypeError:
                        pdf = pd.read_excel(path, sheet_name=sheet)
                        df = pl.from_pandas(pdf)
            else:
                status_msg.set("Unsupported file type. Use .csv/.xlsx/.xls")
                data_pl.set(None)
                return

            data_pl.set(df)
            lat_lon_cols.set(_find_lat_lon_columns(df.columns))
            use_points_on_map.set(False)
            highlighted_new_row.set(None)
            highlighted_new_col.set(None)
            status_msg.set(f"Loaded {f['name']} | rows={df.height}, cols={df.width}")
        except Exception as e:
            data_pl.set(None)
            lat_lon_cols.set(None)
            use_points_on_map.set(False)
            highlighted_new_row.set(None)
            highlighted_new_col.set(None)
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
        df = data_pl.get()
        if df is None:
            status_msg.set("Add row failed: no data loaded.")
            return

        new_row = {col: None for col in df.columns}
        row_df = pl.DataFrame([new_row], schema=df.schema)
        updated = pl.concat([df, row_df], how="vertical_relaxed")
        data_pl.set(updated)
        highlighted_new_row.set(updated.height - 1)
        status_msg.set(f"Added row. rows={updated.height}, cols={updated.width}")

    @reactive.effect
    @reactive.event(input.remove_row)
    def _remove_row():
        df = data_pl.get()
        if df is None:
            status_msg.set("Remove row failed: no data loaded.")
            return

        row_idx = int(input.remove_row_index() or 0)
        if row_idx < 0 or row_idx >= df.height:
            status_msg.set(f"Remove row failed: index {row_idx} out of range [0, {max(df.height - 1, 0)}].")
            return

        marked_row = highlighted_new_row.get()
        if marked_row is not None:
            if row_idx == marked_row:
                highlighted_new_row.set(None)
            elif row_idx < marked_row:
                highlighted_new_row.set(marked_row - 1)

        updated = df.filter(pl.int_range(0, df.height) != row_idx)
        data_pl.set(updated)
        status_msg.set(f"Removed row {row_idx}. rows={updated.height}, cols={updated.width}")

    @reactive.effect
    @reactive.event(input.add_col)
    def _add_column():
        df = data_pl.get()
        if df is None:
            status_msg.set("Add column failed: no data loaded.")
            return

        col_name = (input.new_col_name() or "").strip()
        if not col_name:
            status_msg.set("Add column failed: column name is required.")
            return
        if col_name in df.columns:
            status_msg.set(f"Add column failed: '{col_name}' already exists.")
            return

        dtype_name = input.new_col_type()
        dtype_map: dict[str, pl.DataType] = {
            "string": pl.Utf8,
            "int": pl.Int64,
            "float": pl.Float64,
            "bool": pl.Boolean,
        }

        try:
            if dtype_name not in dtype_map:
                raise ValueError(f"Unsupported column type: {dtype_name}")

            default_value = _coerce_new_column_default(input.new_col_default() or "", dtype_name)
            series = pl.Series(col_name, [default_value] * df.height, dtype=dtype_map[dtype_name])
            updated = df.with_columns(series)
            data_pl.set(updated)
            highlighted_new_col.set(col_name)
            status_msg.set(f"Added column '{col_name}'. rows={updated.height}, cols={updated.width}")
        except Exception as e:
            status_msg.set(f"Add column failed: {e}")

    @reactive.effect
    @reactive.event(input.remove_col)
    def _remove_column():
        df = data_pl.get()
        if df is None:
            status_msg.set("Remove column failed: no data loaded.")
            return

        if df.width <= 1:
            status_msg.set("Remove column failed: cannot remove the last remaining column.")
            return

        col_name = input.drop_col_name()
        if not col_name or col_name not in df.columns:
            status_msg.set("Remove column failed: select a valid column.")
            return

        if highlighted_new_col.get() == col_name:
            highlighted_new_col.set(None)

        updated = df.drop(col_name)
        data_pl.set(updated)
        status_msg.set(f"Removed column '{col_name}'. rows={updated.height}, cols={updated.width}")

    @reactive.effect
    def _clear_highlight_when_no_longer_blank():
        df = data_pl.get()
        if df is None:
            highlighted_new_row.set(None)
            highlighted_new_col.set(None)
            return

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

    @render.data_frame
    def table():
        df = data_pl.get()
        if df is None:
            return render.DataGrid(pd.DataFrame({"Info": ["Upload and load a file to begin editing."]}))

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

        return render.DataGrid(
            _polars_to_pandas(df),
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
        updated = _set_cell_value(df, row, col_name, value)
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
        points = _polars_to_pandas(df.select([lat_col, lon_col]))
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
