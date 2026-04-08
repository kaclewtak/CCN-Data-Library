# CCN Data Library Dashboard

Interactive Shiny for Python dashboard for exploring, validating, and visualising CCN Data Library datasets.

## Quick Start

```bash
cd src/dashboard
uvicorn shiny_dashboard:app --reload
```

Or from the Jupyter notebook: open **Python_Shiny.ipynb** and run all cells.

## File Structure

```
src/dashboard/
├── shiny_dashboard.py        # App composition & tab wiring
├── Python_Shiny.ipynb        # Notebook launcher for the dashboard
├── README.md
├── panels/                   # One Shiny module per tab
│   ├── table.py              # Editable data table (import/edit/export)
│   ├── map_panel.py          # Interactive ipyleaflet map
│   ├── eo_panel.py           # NASA CMR satellite search
│   ├── pygwalker_page.py     # PyGWalker data explorer
│   ├── data_inventory.py     # File inventory & distribution analysis
│   └── qa_panel.py           # QA charts, validation & reference map
└── utils/                    # Shared helpers (no Shiny imports)
    ├── qa.py                 # Reference data, column matching, validation, chart & map builders
    ├── dataframe.py          # Column parsing, type coercion, schema detection
    ├── geo.py                # Lat/lon detection & point extraction
    ├── io.py                 # CSV/Excel import & autosave
    ├── markers.py            # ipyleaflet marker factories
    ├── distributions.py      # Statistical distribution comparison
    ├── geo_gaps.py           # Geographic gap analysis
    ├── inventory_io.py       # Inventory directory scanning
    └── synthesis_io.py       # Synthesis dataset loading
```

## Architecture

### Data Flow

1. **Table** (`panels/table.py`) loads CSV/Excel into a Polars DataFrame and exposes three reactive getters: `map_points`, `all_geo_points`, and `data`.
2. **Map** (`panels/map_panel.py`) consumes `map_points` to render table-driven markers alongside manual points.
3. **Satellite Search** (`panels/eo_panel.py`) uses `all_geo_points` to query the NASA CMR API.
4. **Data Explorer** (`panels/pygwalker_page.py`) receives `data` for interactive visual exploration.
5. **QA Dashboard** (`panels/qa_panel.py`) receives `data`, converts to Pandas, and overlays user data on CCN reference distributions.

### Tab Overview

| Tab | Module | Purpose |
|-----|--------|---------|
| Table & Map | `table` + `map_panel` | Side-by-side editable grid and map with click-to-select |
| Satellite Search | `eo_panel` | Search NASA CMR for imagery over user points |
| Data Explorer | `pygwalker_page` | Drag-and-drop visual analytics via PyGWalker |
| Data Inventory | `data_inventory` | Browse file inventory, compare distributions, find geographic gaps |
| QA Dashboard | `qa_panel` | Compare user data to ~117K CCN reference samples, validate ranges, view reference map |

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