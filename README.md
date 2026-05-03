# CCN Standalone Dashboard

Standalone Shiny for Python dashboard for exploring, validating, and visualizing Coastal Carbon Network soil carbon datasets.

The dashboard starts as an empty working session in Data Explorer. Users can import CSV, JSON, or Excel files, inspect and edit the table, compare matched fields against CCN reference distributions, search for matching NASA satellite observations, and review the capstone carbon-modeling summary.

## Quick Start

Install [uv](https://github.com/astral-sh/uv), then sync the project from the repository root:

```bash
uv sync
```

Build the customized Data Explorer frontend assets when working from source:

```bash
cd src/interactive_dash/app
npm install --legacy-peer-deps
npm run build
cd ../../..
```

Launch the dashboard:

```bash
uv run ccn-dashboard
```

The command chooses an available local port, opens the dashboard in a browser by default, and downloads CCN synthesis reference data on first launch if it is not already installed.

Useful launch options:

```bash
uv run ccn-dashboard --no-browser
uv run ccn-dashboard --port 8050
uv run ccn-dashboard --no-fetch
uv run ccn-dashboard --force-data-refresh
```

## Reference Data Cache

The standalone dashboard does not track synthesis CSVs in git. On first launch, it downloads the versioned Coastal Carbon Library files from Smithsonian Figshare and installs them under:

```text
files/current/CCN_synthesis/
```

The `files/` directory is intentionally ignored by git. A second launch reuses the installed files and does not download again unless `--force-data-refresh` is used.

Current data source:

- Version: `1.7.0`
- Figshare article: `https://smithsonian.figshare.com/articles/dataset/Database_Coastal_Carbon_Library_Version_1_0_0_/21565671`
- DOI: `10.25573/serc.21565671.v9`
- API metadata: `https://api.figshare.com/v2/articles/21565671`

Each downloaded file is validated against the MD5 checksum published by Figshare before the cache is activated.

Advanced data overrides:

- `CCN_DATA_DIR`: use a custom folder containing `CCN_depthseries.csv` and `CCN_cores.csv`; this prevents downloads.
- `CCN_DATA_CACHE_DIR`: redirect the app-managed cache root away from repo-local `files/`.

## Development Commands

```bash
uv run pytest -q
cd src/interactive_dash/app && npm run test:unit
cd src/interactive_dash/app && npm run build
```

The frontend build writes runtime assets into `src/interactive_dash/pygwalker/templates/dist/`. Those generated files are ignored in source control, but releases must include or regenerate them before launch.

## VS Code Setup

Open this repository root as the workspace folder. Recommended extensions are:

- Python (`ms-python.python`)
- Ruff (`charliermarsh.ruff`)
- Black Formatter (`ms-python.black-formatter`)
- Isort (`ms-python.isort`)

The workspace settings format Python files and sort imports on save.

## Citation And Data Use

The dashboard uses CCN synthesis reference data curated by the Coastal Carbon Network. Users should cite both the CCN database version and any original source datasets used in their analysis.

Recommended database citation:

Coastal Carbon Network (2023). Database: Coastal Carbon Library (Version 1.7.0). Smithsonian Environmental Research Center. Dataset. https://doi.org/10.25573/serc.21565671. Accessed YYYY-MM-DD.
