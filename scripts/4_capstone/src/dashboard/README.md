# CCN Data Library Dashboard

Interactive Shiny for Python dashboard for exploring, validating, and visualising CCN Data Library datasets.

## Quick Start

```bash
cd src/dashboard
uvicorn shiny_dashboard:app --reload
```

Or open [Python_Shiny.ipynb](Python_Shiny.ipynb) and run all cells.

## Dashboard Flow

The dashboard is now explorer-first.

1. Open the **Data Explorer** tab first.
2. Import a CSV, JSON, or Excel file from the embedded spreadsheet inside PyGWalker.
3. The imported spreadsheet snapshot becomes the session dataset for the rest of the dashboard.
4. **Satellite Search** consumes detected latitude/longitude columns from that same dataset.
5. **Carbon Modeling** shows the static high-level findings and copied figures from the saved modeling notebook outputs.
6. **QA Dashboard** consumes that same dataset for validation, statistical comparisons, charts, and map overlays.
7. **Data Inventory** remains independent and focuses on repository inventory, synthesis summaries, and coverage diagnostics.

The Data Explorer remains the source of truth after import. Later spreadsheet edits and formula-driven changes are mirrored back to the Shiny session and reused by downstream panels without replacing the embedded iframe.

## File Structure

```text
src/dashboard/
├── shiny_dashboard.py          # App composition and tab wiring
├── dashboard_shared_dataset.py # Session-owned dataset mirrored from Data Explorer
├── Python_Shiny.ipynb          # Notebook launcher for the dashboard
├── README.md
├── panels/
│   ├── carbon_modeling.py       # Static SOC modeling findings and copied notebook figures
│   ├── eo_panel.py             # NASA CMR satellite search
│   ├── pygwalker_page.py       # Explorer page, persistent iframe, parent bridge listener
│   ├── pygwalker_persistence.py# PyGWalker HTML builder and spreadsheet config injection
│   ├── data_inventory.py       # File inventory and distribution analysis
│   └── qa_panel.py             # QA charts, validation, and reference map
├── images/                      # Static dashboard figures copied from modeling notebooks
├── tests/
│   ├── test_dashboard_shared_dataset.py
│   └── test_pygwalker_persistence.py
└── utils/
    ├── geo.py                  # Lat/lon detection and dataframe-to-geo conversion
    ├── qa.py                   # Reference data, matching, validation, and map/chart builders
    ├── distributions.py        # Statistical distribution comparison
    ├── geo_gaps.py             # Geographic gap analysis
    ├── inventory_io.py         # Inventory directory scanning
    └── synthesis_io.py         # Synthesis dataset loading
```

## Architecture

### Data Explorer

- [panels/pygwalker_page.py](panels/pygwalker_page.py) renders a persistent PyGWalker iframe and listens for `postMessage` events from the embedded spreadsheet.
- [panels/pygwalker_persistence.py](panels/pygwalker_persistence.py) still injects the existing `ccnSpreadsheet` config so the spreadsheet editor, formulas, and UI customisations stay intact.
- The explorer boots with the smallest supported placeholder dataframe because the local PyGWalker fork cannot initialize from a truly empty dataframe.

### Shared Dataset State

- [dashboard_shared_dataset.py](dashboard_shared_dataset.py) stores the current session dataset mirrored from the explorer.
- It rebuilds a Polars dataframe in the spreadsheet field order, derives latitude/longitude columns, and exposes normalized geo points for downstream consumers.
- Blank startup is treated as "no uploaded dataset yet" until the user imports a real file from the explorer.

### Downstream Panels

- [panels/eo_panel.py](panels/eo_panel.py) reads geo points from the shared dataset and searches NASA CMR for matching granules.
- [panels/qa_panel.py](panels/qa_panel.py) reads the same shared dataframe and compares it against CCN reference distributions.
- [panels/data_inventory.py](panels/data_inventory.py) stays independent of the explorer-owned session dataset.

## Frontend Bridge

The embedded explorer is served by the local frontend app under [../interactive_dash/app/src](../interactive_dash/app/src).

- [../interactive_dash/app/src/index.tsx](../interactive_dash/app/src/index.tsx) still renders the existing CCN spreadsheet plus GraphicWalker split layout.
- [../interactive_dash/app/src/features/ccnSpreadsheet/useCcnSpreadsheetState.ts](../interactive_dash/app/src/features/ccnSpreadsheet/useCcnSpreadsheetState.ts) now tracks the imported dataset identity and mirrors debounced spreadsheet snapshots to the parent window.
- [../interactive_dash/app/src/features/ccnSpreadsheet/bridge.ts](../interactive_dash/app/src/features/ccnSpreadsheet/bridge.ts) contains the pure helper logic for dataset fingerprints and sync payloads.

Tracked frontend source is the edit surface. The embedded build output is regenerated locally from the app package and is not a manual edit target.

## Verification

Typical local verification steps:

```bash
uv run pytest -q
cd src/interactive_dash/app && npm run test:unit
cd src/interactive_dash/app && npm run build
```

The frontend build writes runtime assets into the ignored `src/interactive_dash/pygwalker/templates/dist` directory. Those files should be regenerated for verification, but not hand-edited.