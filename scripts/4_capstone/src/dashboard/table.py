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
        ui.layout_sidebar(
            ui.sidebar(
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
                ui.input_action_button("load", "Load file", class_="btn-primary"),
                ui.hr(),
                ui.download_button("download_csv", "Download edited CSV"),
                ui.hr(),
                ui.h5("Load / validation status"),
                ui.output_text_verbatim("status"),
                ui.hr(),
                ui.h5("Map integration"),
                ui.output_ui("lat_lon_prompt"),
                width=350,
            ),
            ui.card(
                ui.card_header("Editable Data"),
                ui.output_data_frame("table"),
            ),
        ),
        ui.hr(),
        ui.h5("Current schema (polars)"),
        ui.output_text_verbatim("schema_text"),
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
    normalized_to_original = {col.strip().lower(): col for col in columns}

    lat_candidates = ["latitude", "lat"]
    lon_candidates = ["longitude", "lng", "lon"]

    lat_col = next((normalized_to_original[c] for c in lat_candidates if c in normalized_to_original), None)
    lon_col = next((normalized_to_original[c] for c in lon_candidates if c in normalized_to_original), None)

    if lat_col is None or lon_col is None:
        return None
    return lat_col, lon_col


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
            status_msg.set(f"Loaded {f['name']} | rows={df.height}, cols={df.width}")
        except Exception as e:
            data_pl.set(None)
            lat_lon_cols.set(None)
            use_points_on_map.set(False)
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

    @render.data_frame
    def table():
        df = data_pl.get()
        if df is None:
            return render.DataGrid(pd.DataFrame({"Info": ["Upload and load a file to begin editing."]}))
        return render.DataGrid(_polars_to_pandas(df), editable=True, selection_mode="none")

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
