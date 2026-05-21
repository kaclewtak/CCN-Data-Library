# CCN Standalone Dashboard

Standalone Shiny for Python dashboard for exploring, validating, and visualizing Coastal Carbon Network soil carbon datasets.

The dashboard starts with an empty working session in **Data Explorer**. Users can import a table, edit and verify it, compare matched fields against CCN reference distributions, search for matching NASA satellite observations, and review saved carbon-modeling results.

## Quick Start

Install [uv](https://github.com/astral-sh/uv), then sync the project from the repository root:

```bash
uv sync
```

When working from source, build the customized Data Explorer frontend assets before launching:

```bash
cd src/interactive_dash/app
npm install --legacy-peer-deps
npm run build
cd ../../..
```

### CLI dashboard launch:

```bash
uv run ccn-dashboard
```

The launcher validates the local Data Explorer bundle, chooses an available port, opens a browser by default, and downloads CCN synthesis reference data on first launch if needed.

Useful launch options:

```bash
uv run ccn-dashboard --no-browser
uv run ccn-dashboard --port 8050
uv run ccn-dashboard --no-fetch
uv run ccn-dashboard --force-data-refresh
```

### Notebook dashboard launch

There is a premade notebook which can be used to run the Dashboard. It is located in:

```
src/dashboard/Python_Shiny.ipynb
```

Likewise, notebook or async Python sessions can launch the same app with:

```python
from ccn_dashboard import launch_dashboard

handle = await launch_dashboard(require_data=True, open_browser=True)
# await handle.stop()
```

## Dashboard Workflow

1. Open **Data Explorer** first.
2. Import a CSV, JSON, XLS, XLSX, or XLSM file, or build a sheet directly in the embedded spreadsheet.
3. Use clear coordinate names such as `latitude`, `longitude`, `lat`, `lon`, or `lng` if you need maps or satellite search.
4. Use **QA Dashboard** to match fields, review validation warnings, and compare against CCN reference data.
5. Use **Satellite Search** for datasets with coordinates, then **Data Inventory**, **Carbon Modeling**, and **Metadata** for reference context.

The Data Explorer table is the session source of truth. Spreadsheet edits are mirrored to Shiny and reused by downstream panels without replacing the embedded explorer iframe.

## Feature Guide

### Data Explorer

Loads and edits the working dataset with a customized PyGWalker / Graphic Walker interface. It supports spreadsheet import/export, browser-local sheet saves, row and column editing, undo/redo, CCN column verification, and visual exploration.

### QA Dashboard

Matches common user fields for carbon fraction, organic matter fraction, dry bulk density, depth ranges, identifiers, latitude, and longitude. It provides QA charts, statistical comparisons, row-level validation warnings, exportable validation output, and a map overlay of user and CCN core locations.

### Satellite Search

Uses imported latitude and longitude columns to build a buffered bounding box, query earth-observation sources for regional products, and list matching items with available time ranges, data links, metadata links, preview imagery when available, cloud cover where available, and coverage maps. Result footprints are overlaid only for rows checked in the Map column, with the first result selected after each search; the map now renders CMR polygon footprints as well as STAC geometry/bounding boxes. Model-relevant sources are prioritized from the modeling notebooks: EMIT L2A Reflectance is queried through NASA CMR, while Sentinel-2 L2A Surface Reflectance and Sentinel-1 RTC Backscatter are queried through Planetary Computer STAC for NDVI and VV/VH backscatter source discovery with each initial load capped at 100 items. Sentinel data links are signed on click through the Planetary Computer API because the underlying Azure Blob assets are not publicly accessible without a SAS token. The current PACE OCI L2 Ocean Color and Inherent Optical Properties CMR collections remain available for continuity. This panel needs internet access and availability of NASA CMR or the Planetary Computer STAC API.

### Data Inventory

Loads app-managed CCN synthesis data for library-level context. It summarizes synthesis table rows, measurement coverage, quality flags, methods, habitat classes, species, impacts, SOM and bulk density distributions, correlations, density contours, geographic coverage, and gap hints.

### Carbon Modeling

Shows saved notebook figures and findings; it does not retrain models inside the dashboard. The current panel compares the clean reduced cohort with the expanded North American run: expansion increases coverage from 676 to 1,432 filtered cores, but pooled within-study skill weakens while MAE stays near 0.067. Fraction carbon remains the more defensible target, and SOC stock remains weak as a prediction product.

### Metadata

Provides citation, stewardship, data-use, service-source, and software acknowledgement information for report-ready attribution.

## Reference Data Cache

The dashboard does not track synthesis CSVs in git. On first launch, it downloads the Coastal Carbon Library files from Smithsonian Figshare and installs them under:

```text
files/current/CCN_synthesis/
```

The `files/` directory is ignored. Later launches reuse the cache unless `--force-data-refresh` is used. QA Dashboard and Data Inventory require at least `CCN_depthseries.csv` and `CCN_cores.csv`.

Current data source:

- Version: `1.7.0`
- Figshare article: `https://smithsonian.figshare.com/articles/dataset/Database_Coastal_Carbon_Library_Version_1_0_0_/21565671`
- DOI: `doi.org/10.25573/serc.21565671.v9`
- API metadata: `https://api.figshare.com/v2/articles/21565671`

Each downloaded file is validated against the MD5 checksum published by Figshare before the cache is activated.

Advanced data overrides:

- `CCN_DATA_DIR`: use a custom folder containing the required synthesis CSV files; this prevents downloads.
- `CCN_DATA_CACHE_DIR`: redirect the app-managed cache root away from repo-local `files/`.

## Development

Key files:

- [src/ccn_dashboard/cli.py](src/ccn_dashboard/cli.py) defines the `ccn-dashboard` CLI.
- [src/ccn_dashboard/launcher.py](src/ccn_dashboard/launcher.py) provides notebook-friendly launch helpers and port selection.
- [src/ccn_dashboard/data_manifest.py](src/ccn_dashboard/data_manifest.py) tracks the synthesis download manifest.
- [src/dashboard/shiny_dashboard.py](src/dashboard/shiny_dashboard.py) composes the Shiny app and tab order.
- [src/dashboard/dashboard_shared_dataset.py](src/dashboard/dashboard_shared_dataset.py) stores the session dataset mirrored from Data Explorer.
- [src/dashboard/panels](src/dashboard/panels) contains the main dashboard tabs.
- [src/dashboard/utils](src/dashboard/utils) contains reference-data, QA, inventory, and geographic helpers.
- [src/interactive_dash/app/src](src/interactive_dash/app/src) contains the customized Data Explorer frontend.
- [src/interactive_dash/pygwalker/services/render.py](src/interactive_dash/pygwalker/services/render.py) serves the packaged PyGWalker frontend bundle used by the dashboard.

Verification commands:

```bash
uv run pytest -q
cd src/interactive_dash/app && npm run test:unit
cd src/interactive_dash/app && npm run build
```

The frontend build writes runtime assets into `src/interactive_dash/pygwalker/templates/dist/`. Those generated files are ignored in source control, but releases must include or regenerate them before launch.

## VS Code Setup

Open this repository root as the workspace folder. Recommended extensions are Python (`ms-python.python`), Ruff (`charliermarsh.ruff`), Black Formatter (`ms-python.black-formatter`), and Isort (`ms-python.isort`). Workspace settings format Python files and sort imports on save.

## Citation And Data Use

The dashboard uses CCN synthesis reference data curated by the Coastal Carbon Network. Users should cite both the CCN database version and any original source datasets used in their analysis.

Recommended database citation:

Coastal Carbon Network (2023). Database: Coastal Carbon Library (Version 1.7.0). Smithsonian Environmental Research Center. Dataset. https://doi.org/10.25573/serc.21565671. Accessed YYYY-MM-DD.
