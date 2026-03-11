from __future__ import annotations

from pathlib import Path

import pandas as pd
import polars as pl
from shiny import module, reactive, render, ui
from table_utils.assets_utils import TABLE_SCROLL_PERSISTENCE_SCRIPT
from table_utils.dataframe_utils import (
    add_column_with_default,
    append_blank_row,
    is_blank_value,
    polars_to_pandas,
    remove_existing_column,
    remove_row_from_bottom,
    set_cell_value,
    sync_row_highlight_after_remove,
)
from table_utils.geo_utils import (
    dataframe_to_map_points,
    find_lat_lon_columns,
    row_has_complete_lat_lon,
)
from table_utils.io_utils import (
    autosave_file_path,
    excel_sheet_names,
    file_modified_time,
    latest_autosave_file,
    read_autosave_csv,
    read_uploaded_dataframe,
    write_autosave_csv,
)
from table_utils.style_utils import table_styles
from table_utils.ui_utils import build_compact_controls

# filepath: /home/klewtak/NASA/CCN-Data-Library/scripts/4_capstone/src/dashboard/dashboard_table.py


# ---------------------------
# UI
# ---------------------------
@module.ui
def table_ui():
    """
    UI for the table editor module.
        - File upload for CSV/Excel with options
        - Display editable data grid
        - Show load status and current schema
        - Download edited data as CSV
    """
    return ui.TagList(
        ui.panel_title("Table Editor"),
        ui.card(
            ui.card_header(
                ui.div(
                    ui.tags.strong("Editable Data"),
                    ui.div(
                        ui.input_action_button(
                            "show_load_controls",
                            "Import",
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
            ui.tags.script(TABLE_SCROLL_PERSISTENCE_SCRIPT),
        ),
    )


# ---------------------------
# Server
# ---------------------------
@module.server
def table_server(input, output, session):
    data_pl = reactive.Value(None)  # type: ignore[var-annotated]
    map_points_cache = reactive.Value(pd.DataFrame(columns=["latitude", "longitude"]))
    status_msg = reactive.Value("Waiting for file upload.")
    source_name = reactive.Value("edited_data")
    autosave_session_token = str(id(session))
    autosave_path = reactive.Value(autosave_file_path("edited_data", autosave_session_token))
    has_unsaved_changes = reactive.Value(False)
    pending_load_context = reactive.Value(None)  # type: ignore[var-annotated]
    lat_lon_cols = reactive.Value(None)  # type: ignore[var-annotated]
    use_points_on_map = reactive.Value(False)
    active_compact_panel = reactive.Value(None)  # type: ignore[var-annotated]
    highlighted_new_row = reactive.Value(None)  # type: ignore[var-annotated]
    highlighted_new_col = reactive.Value(None)  # type: ignore[var-annotated]

    # --- Helper: Compact panel controls ----------------------------------------
    def _toggle_panel(panel_name: str) -> None:
        current = active_compact_panel.get()
        active_compact_panel.set(None if current == panel_name else panel_name)

    def _register_panel_toggle(toggle_input, panel_name: str) -> None:
        @reactive.effect
        @reactive.event(toggle_input)
        def _toggle_panel_effect():
            _toggle_panel(panel_name)

    # --- Helper: DataFrame load/edit operations --------------------------------
    def _clear_highlights() -> None:
        highlighted_new_row.set(None)
        highlighted_new_col.set(None)

    def _require_df(action_name: str) -> pl.DataFrame | None:
        df = data_pl.get()
        if df is None:
            status_msg.set(f"{action_name} failed: no data loaded.")
            return None
        return df

    def _refresh_map_points() -> None:
        map_points_cache.set(
            dataframe_to_map_points(
                df=data_pl.get(),
                lat_lon_cols=lat_lon_cols.get(),
                enabled=bool(use_points_on_map.get()),
            )
        )

    def _reset_autosave_target() -> None:
        autosave_path.set(autosave_file_path(source_name.get(), autosave_session_token))
        has_unsaved_changes.set(False)

    def _mark_table_dirty() -> None:
        has_unsaved_changes.set(True)

    def _persist_autosave(force: bool = False) -> None:
        if not force and not has_unsaved_changes.get():
            return

        df = data_pl.get()
        path = autosave_path.get()
        if df is None or path is None:
            return

        try:
            write_autosave_csv(df, path)
            has_unsaved_changes.set(False)
        except Exception as e:
            status_msg.set(f"Autosave failed: {e}")

    def _apply_loaded_dataframe(df: pl.DataFrame, source_stem: str, loaded_label: str) -> None:
        source_name.set(source_stem)
        data_pl.set(df)
        lat_lon_cols.set(find_lat_lon_columns(df.columns))
        use_points_on_map.set(False)
        _clear_highlights()
        _reset_autosave_target()
        _refresh_map_points()
        status_msg.set(f"{loaded_label} | rows={df.height}, cols={df.width}")

    def _prompt_newer_autosave(source_stem: str, autosave_candidate: Path, uploaded_name: str) -> None:
        pending_load_context.set(
            {
                "file": input.file()[0] if input.file() else None,
                "sheet": input.sheet_name(),
                "sep": input.csv_sep(),
                "source_stem": source_stem,
                "uploaded_name": uploaded_name,
                "autosave_path": autosave_candidate,
            }
        )

        ui.modal_show(
            ui.modal(
                ui.p(
                    f"A newer autosave was found for '{source_stem}'. "
                    f"Do you want to use the newer autosave instead of '{uploaded_name}'?"
                ),
                ui.p(f"Autosave file: {autosave_candidate}"),
                title="Use newer autosave?",
                easy_close=False,
                footer=ui.div(
                    ui.input_action_button("open_selected_file", "Open selected file", class_="btn-secondary"),
                    ui.input_action_button("use_newer_autosave", "Use newer autosave", class_="btn-primary"),
                    class_="d-flex gap-2 justify-content-end",
                ),
            )
        )

    # --- Helper: Highlight + style state ---------------------------------------
    def _clear_highlight_when_filled(df: pl.DataFrame) -> None:
        marked_row = highlighted_new_row.get()
        if marked_row is not None:
            if marked_row < 0 or marked_row >= df.height:
                highlighted_new_row.set(None)
            else:
                row_values = df.row(marked_row)
                if any(not is_blank_value(value) for value in row_values):
                    highlighted_new_row.set(None)

        marked_col = highlighted_new_col.get()
        if marked_col is not None:
            if marked_col not in df.columns:
                highlighted_new_col.set(None)
            else:
                col_values = df.get_column(marked_col).to_list()
                if any(not is_blank_value(value) for value in col_values):
                    highlighted_new_col.set(None)

    # --- Reactive events: Compact panel toggles --------------------------------
    _register_panel_toggle(input.show_load_controls, "load")
    _register_panel_toggle(input.show_download_controls, "download")
    _register_panel_toggle(input.show_schema_controls, "schema")
    _register_panel_toggle(input.show_status_controls, "status")
    _register_panel_toggle(input.show_map_controls, "map")

    # --- Render: Compact panel body --------------------------------------------
    @render.ui
    def compact_controls_panel():
        panel_name = active_compact_panel.get()
        if panel_name is None:
            return ui.div()
        return build_compact_controls(panel_name)

    # --- Reactive events: File load + map toggle state -------------------------
    @reactive.effect
    def _sync_drop_column_choices():
        df = data_pl.get()
        choices = [] if df is None else df.columns
        selected = choices[0] if choices else None
        ui.update_select("drop_col_name", choices=choices, selected=selected)

    @reactive.effect
    def _autosave_every_30_seconds():
        reactive.invalidate_later(30)
        _persist_autosave(force=False)

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
    @reactive.event(input.file, input.sheet_name, input.csv_sep)
    def _load_file():
        files = input.file()
        if not files:
            status_msg.set("No file selected.")
            data_pl.set(None)
            lat_lon_cols.set(None)
            use_points_on_map.set(False)
            _clear_highlights()
            _reset_autosave_target()
            _refresh_map_points()
            return

        f = files[0]
        source_stem = Path(f["name"]).stem

        try:
            autosave_candidate = latest_autosave_file(source_stem)
            if autosave_candidate is not None:
                autosave_mtime = file_modified_time(autosave_candidate)
                uploaded_mtime = file_modified_time(Path(f["datapath"]))
                if autosave_mtime > uploaded_mtime:
                    _prompt_newer_autosave(source_stem, autosave_candidate, f["name"])
                    return
        except Exception:
            pass

        try:
            df = read_uploaded_dataframe(
                file_info=f,
                sheet_name=input.sheet_name(),
                csv_sep=input.csv_sep(),
            )
            _apply_loaded_dataframe(df, source_stem=source_stem, loaded_label=f"Loaded {f['name']}")
        except Exception as e:
            data_pl.set(None)
            lat_lon_cols.set(None)
            use_points_on_map.set(False)
            _clear_highlights()
            _reset_autosave_target()
            _refresh_map_points()
            status_msg.set(f"Load failed: {e}")

    @reactive.effect
    @reactive.event(input.use_newer_autosave)
    def _use_newer_autosave_for_load():
        ctx = pending_load_context.get()
        if not ctx:
            return

        autosave_candidate = ctx.get("autosave_path")
        source_stem = ctx.get("source_stem") or "edited_data"
        uploaded_name = ctx.get("uploaded_name") or "selected file"
        try:
            if autosave_candidate is None or not autosave_candidate.exists():
                raise ValueError("Autosave file was not found.")

            df = pl.read_csv(autosave_candidate)
            _apply_loaded_dataframe(
                df,
                source_stem=source_stem,
                loaded_label=f"Loaded newer autosave instead of {uploaded_name}",
            )
        except Exception as e:
            status_msg.set(f"Load failed: {e}")
        finally:
            pending_load_context.set(None)
            ui.modal_remove()

    @reactive.effect
    @reactive.event(input.open_selected_file)
    def _use_selected_file_for_load():
        ctx = pending_load_context.get()
        if not ctx:
            return

        file_info = ctx.get("file")
        source_stem = ctx.get("source_stem") or "edited_data"
        uploaded_name = ctx.get("uploaded_name") or "selected file"
        try:
            if file_info is None:
                raise ValueError("Selected file is no longer available.")

            df = read_uploaded_dataframe(
                file_info=file_info,
                sheet_name=ctx.get("sheet") or "(first sheet)",
                csv_sep=ctx.get("sep"),
            )
            _apply_loaded_dataframe(df, source_stem=source_stem, loaded_label=f"Loaded {uploaded_name}")
        except Exception as e:
            status_msg.set(f"Load failed: {e}")
        finally:
            pending_load_context.set(None)
            ui.modal_remove()

    @render.ui
    def lat_lon_prompt():
        cols = lat_lon_cols.get()
        if cols is None:
            return ui.p("No latitude/longitude columns detected.")

        lat_col, lon_col = cols
        return ui.TagList(
            ui.p(f"Detected '{lat_col}' and '{lon_col}'. Do you want to display these points on the map?"),
            ui.input_switch(
                "use_map_points",
                "Plot table points on map",
                value=bool(use_points_on_map.get()),
            ),
        )

    @reactive.effect
    @reactive.event(input.use_map_points)
    def _sync_use_points_on_map():
        cols = lat_lon_cols.get()
        if cols is None:
            use_points_on_map.set(False)
            _refresh_map_points()
            return

        switch_value = input.use_map_points()
        if switch_value is None:
            return

        use_points_on_map.set(bool(switch_value))
        _refresh_map_points()

    # --- Reactive events: Row/column edit actions ------------------------------
    @reactive.effect
    @reactive.event(input.add_row)
    def _add_row():
        df = _require_df("Add row")
        if df is None:
            return

        updated, added_row_idx = append_blank_row(df)
        data_pl.set(updated)
        highlighted_new_row.set(added_row_idx)
        _mark_table_dirty()
        status_msg.set(f"Added row. rows={updated.height}, cols={updated.width}")

    @reactive.effect
    @reactive.event(input.remove_row)
    def _remove_row():
        df = _require_df("Remove row")
        if df is None:
            return

        bottom_offset = int(input.remove_row_index() or 0)
        try:
            updated, row_idx = remove_row_from_bottom(df, bottom_offset)
            highlighted_new_row.set(sync_row_highlight_after_remove(highlighted_new_row.get(), row_idx))
            data_pl.set(updated)
            _refresh_map_points()
            _mark_table_dirty()
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
            updated = add_column_with_default(
                df=df,
                col_name=col_name,
                dtype_name=input.new_col_type(),
                default_raw=input.new_col_default() or "",
            )
            data_pl.set(updated)
            lat_lon_cols.set(find_lat_lon_columns(updated.columns))
            highlighted_new_col.set(col_name)
            _refresh_map_points()
            _mark_table_dirty()
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
            updated = remove_existing_column(df, col_name)
            if highlighted_new_col.get() == col_name:
                highlighted_new_col.set(None)
            data_pl.set(updated)
            lat_lon_cols.set(find_lat_lon_columns(updated.columns))
            _refresh_map_points()
            _mark_table_dirty()
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

    # --- Render + calc outputs --------------------------------------------------
    @render.data_frame
    def table():
        df = data_pl.get()
        if df is None:
            return render.DataGrid(pd.DataFrame({"Info": ["Upload and load a file to begin editing."]}))
        styles = table_styles(df, highlighted_new_row.get(), highlighted_new_col.get())

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
        detected_cols = lat_lon_cols.get()
        is_lat_lon_edit = False
        before_complete_pair = False
        if detected_cols is not None:
            lat_col, lon_col = detected_cols
            is_lat_lon_edit = col_name in {lat_col, lon_col}
            if is_lat_lon_edit:
                before_complete_pair = row_has_complete_lat_lon(df, row, lat_col, lon_col)

        updated = set_cell_value(df, row, col_name, value)
        data_pl.set(updated)
        _mark_table_dirty()

        if detected_cols is not None and is_lat_lon_edit:
            lat_col, lon_col = detected_cols
            after_complete_pair = row_has_complete_lat_lon(updated, row, lat_col, lon_col)
            if before_complete_pair or after_complete_pair:
                _refresh_map_points()

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
        return map_points_cache.get()

    @reactive.calc
    def data() -> pl.DataFrame | None:
        return data_pl.get()

    @render.download(filename=lambda: f"{source_name.get()}_edited.csv")
    def download_csv():
        df = data_pl.get()
        if df is None:
            yield "No data loaded.\n"
            return

        _persist_autosave(force=True)
        path = autosave_path.get()
        if path is not None and path.exists():
            yield read_autosave_csv(path)
            return

        yield df.write_csv()

    return {
        "map_points": map_points,
        "data": data,
    }
