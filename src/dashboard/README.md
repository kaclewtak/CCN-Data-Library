# Dashboard Module Guide

This folder contains the Python Shiny dashboard used for interactive table editing and map visualization in the CCN Data Library workflow.

The dashboard is organized as two coordinated modules:

- Table module: import/edit/export tabular data and optionally expose latitude/longitude points.
- Map module: render manual and table-driven points, and auto-focus on imported table data.

## High-Level Architecture

- App composition entrypoint: shiny_dashboard.py
- Table feature module: table.py
- Map feature module: map_panel.py
- Table utility package: table_utils/
- Map utility package: map_utils/

Data flow summary:

1. The table module loads CSV/Excel into a Polars DataFrame.
2. The table module exposes reactive map points through table_state["map_points"].
3. The map module consumes that reactive map-point getter.
4. The map module renders both manual points and table points in one map view.

## File-by-File Reference

### shiny_dashboard.py

Purpose:

- Composes the dashboard page layout and wires table + map modules together.

Key responsibilities:

- Defines app_ui with a two-column split (table on left, map on right).
- Creates table module instance and passes table map-point reactive getter into map module.
- Creates App(app_ui, server).

Primary functions:

- server(input, output, session)
	- Initializes table_state = table_server("data_editor").
	- Calls map_server("map_viewer", table_points_getter=table_state["map_points"]).

### table.py

Purpose:

- Implements the editable data-grid workflow and all table-side reactive behavior.

Key responsibilities:

- Compact header controls for Import, Download, Schema, Status, and Map settings.
- Inline toolbar for row/column add/remove operations.
- Auto-import on file selection and option changes.
- Editable DataGrid cell patching with type-preserving writes.
- Selective map-point refresh logic (only when relevant lat/lon events occur).
- CSV download of edited data.

Primary functions:

- table_ui()
	- Builds all visible table UI components.
	- Injects TABLE_SCROLL_PERSISTENCE_SCRIPT to preserve viewport position across re-renders.

- table_server(input, output, session)
	- Owns reactive state for table data, schema/lat-lon detection, toolbar state, and map cache.
	- Registers compact panel toggles via _register_panel_toggle.
	- Handles import, editing, row/column operations, schema/status renderers, and download.
	- Returns a dictionary with map_points reactive calculation.

Important reactive outputs/callbacks:

- compact_controls_panel: renders currently selected compact control panel.
- table (render.data_frame): returns DataGrid with dynamic styles.
- table.set_patch_fn: applies per-cell edits with type coercion and conditional map refresh.
- map_points (reactive.calc): returns cached table points for the map module.

### map_panel.py

Purpose:

- Implements map-side UI and reactive map behavior as an isolated Shiny module.

Key responsibilities:

- Render ipyleaflet map with manual points and table-derived points.
- Allow manual point entry through latitude/longitude controls.
- Auto-focus map viewport on imported table points when appropriate.
- Report map status counts.

Primary functions:

- map_ui()
	- Defines map controls and output container.

- map_server(input, output, session, table_points_getter)
	- Uses table_points_getter to consume table module map points.
	- Maintains map center/zoom and last-imported-view signature.
	- Processes manual point additions and imported-point focusing.

## table_utils Package

The table_utils package contains pure utility code separated by concern.

### table_utils/dataframe_utils.py

Purpose:

- Polars/Pandas conversion, cell coercion, and row/column editing primitives.

Core functions:

- is_blank_value(value)
- coerce_value(raw_value, dtype)
- set_cell_value(df, row_idx, col_name, new_value)
- polars_to_pandas(df)
- coerce_new_column_default(raw_value, dtype_name)
- append_blank_row(df)
- remove_row_from_bottom(df, bottom_offset)
- add_column_with_default(df, col_name, dtype_name, default_raw)
- remove_existing_column(df, col_name)
- sync_row_highlight_after_remove(marked_row, removed_row_idx)

### table_utils/io_utils.py

Purpose:

- File import and sheet-resolution helpers.

Core functions:

- excel_sheet_names(path)
- read_uploaded_dataframe(file_info, sheet_name, csv_sep)

### table_utils/geo_utils.py

Purpose:

- Latitude/longitude detection and transformation to map-ready points.

Core functions:

- find_lat_lon_columns(columns)
- parse_coordinate(value)
- row_has_complete_lat_lon(df, row_idx, lat_col, lon_col)
- dataframe_to_map_points(df, lat_lon_cols, enabled)

Notes:

- find_lat_lon_columns supports flexible naming patterns (for example: core_latitude/core_longitude).
- dataframe_to_map_points always normalizes output columns to latitude and longitude.

### table_utils/style_utils.py

Purpose:

- Encapsulates DataGrid style composition.

Core function:

- table_styles(df, highlighted_new_row, highlighted_new_col)

Styling behavior includes:

- Highlight emphasis for newly added row/column.
- Extra bottom padding for last row to reduce overlap with horizontal scrollbar.

### table_utils/ui_utils.py

Purpose:

- Generates compact panel content based on selected panel type.

Core function:

- build_compact_controls(panel_name)

Supports panel_name values:

- load
- download
- schema
- status
- map

### table_utils/assets_utils.py

Purpose:

- Holds UI asset snippets to keep table.py concise.

Core constant:

- TABLE_SCROLL_PERSISTENCE_SCRIPT

Behavior:

- Persists and restores DataGrid scroll position after output updates/mutations.

## map_utils Package

The map_utils package contains map-focused pure utilities.

### map_utils/marker_utils.py

Purpose:

- Coordinate validation and marker creation.

Core functions:

- is_valid_coordinate(latitude, longitude)
- build_manual_markers(manual_df)
- build_table_markers(table_points)

### map_utils/view_utils.py

Purpose:

- Map viewport calculations for imported points.

Core functions:

- zoom_for_span(span_degrees)
- normalized_table_points(table_points)
- compute_imported_view(table_points)

compute_imported_view returns:

- center tuple (latitude, longitude)
- recommended zoom level
- stable view_key signature for deduplicating repeat map recentering

## Runtime Behaviors and Rules

### Import behavior

- Import is automatic when a file is selected.
- For Excel, changing selected sheet triggers re-read.
- For CSV, changing separator triggers re-read.

### Table edit behavior

- Cell edits are applied through table.set_patch_fn using type-aware coercion.
- Row removal uses bottom offset indexing:
	- 0 means remove last row
	- 1 means remove second-to-last row

### Map refresh behavior from table edits

- Map points are not refreshed for unrelated non-lat/lon cell edits.
- For lat/lon edits, map refresh occurs when:
	- editing an existing complete lat/lon row, or
	- a row becomes complete after edit.

### Map toggle behavior

- Plot toggle state is preserved and used as gate for map-point generation.
- If lat/lon columns are not detected, map-point output is empty.

## Extension Guidance

When adding new functionality, prefer:

- Utility updates in table_utils/map_utils for pure logic.
- Minimal orchestration changes in table.py/map_panel.py.
- Keeping render/event handlers in module files for traceability.

If adding another major feature area, follow the same pattern:

- feature module file (ui + server orchestration)
- feature_utils package for pure transformations and reusable logic

## Quick Start (from this folder)

Typical local run patterns:

- Use the project virtual environment.
- Launch the Shiny app through the jupyter notebook