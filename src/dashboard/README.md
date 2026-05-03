# CCN Data Library Dashboard

Interactive Shiny for Python dashboard for exploring, validating, and visualizing Coastal Carbon Network soil carbon datasets.

The dashboard is organized around one main workflow: import or build a working dataset in **Data Explorer**, then use the rest of the dashboard to check quality, compare against CCN reference distributions, search for matching satellite observations, and review modeling and metadata context.

## Quick Start

From this repository:

```bash
uv run ccn-dashboard
```

The standalone wrapper under [../ccn_dashboard](../ccn_dashboard) validates the local Data Explorer bundle, resolves or installs CCN synthesis data, and exposes both the `ccn-dashboard` CLI and a notebook-friendly `launch_dashboard()` helper.

## Typical Workflow
1. Open **Data Explorer** first.
2. Import a CSV, JSON, or Excel file in the embedded spreadsheet.
3. Confirm the imported table has the fields you expect, especially latitude and longitude if you want maps or satellite search.
4. Use **QA Dashboard** to compare your data against CCN reference distributions and review validation warnings.
5. Use **Satellite Search** if your dataset has geographic coordinates.
6. Use **Data Inventory** for library-wide context and **Carbon Modeling** for the modeling-phase summary.
7. Use **Metadata** for citation, source, and software attribution.

The Data Explorer table is the source of truth for the session. Edits made in the spreadsheet are mirrored to Shiny and reused by QA Dashboard and Satellite Search without replacing the embedded explorer iframe.

## Feature Guide

### Data Explorer
Use this tab to load and inspect your working dataset. The embedded PyGWalker/Graphic Walker view includes a spreadsheet for import and editing plus visual exploration tools for charts and map-like views.

Common uses:

- Import CSV, JSON, or Excel data.
- Edit spreadsheet values and formulas before downstream checks.
- Explore fields visually before deciding which QA views matter.
- Keep the current session dataset synchronized with QA Dashboard and Satellite Search.

Tips:

- Use recognizable coordinate names such as `latitude`, `longitude`, `lat`, `lon`, or similar names so downstream map tools can detect them.
- A blank startup sheet is expected. Downstream panels treat it as no uploaded dataset until you import real data.
- If Data Explorer does not load, the local customized PyGWalker bundle is the first thing to check.

### QA Dashboard
Use this tab to evaluate the current Data Explorer dataset against CCN reference data.

Main views:

- **QA Charts** compares matched user columns against CCN reference distributions, with filters for geography and habitat.
- **Statistical Tests** runs distribution comparisons for matched variables.
- **Validation** lists row-level warnings and can export a validation report.
- **QA Map** overlays user locations with reference CCN core locations.

The QA tools automatically match common field names for carbon fraction, organic matter fraction, dry bulk density, depth ranges, identifiers, latitude, and longitude. Check the matched-column output before interpreting statistical results.

### Satellite Search
Use this tab after importing a dataset with latitude and longitude columns. The dashboard computes a bounding box around your points, queries NASA CMR, and lists matching L2 granules for the selected collection.

Current collections include EMIT L2A Reflectance, PACE OCI Ocean Color, and PACE OCI Inherent Optical Properties. Results include granule IDs, time ranges, download links when available, preview images when available, and a coverage map.

Satellite Search depends on NASA CMR availability and an internet connection.

### Carbon Modeling
Use this tab for a report-ready summary of the capstone modeling phase. It does not rerun models inside the dashboard. Instead, it presents copied notebook figures, metric cards, and high-level findings from the saved modeling workflow.

Use it when you need to review model scope, performance, caveats, feature-importance signals, and the main conclusion that fraction carbon is a more defensible prediction target than SOC stock in the current workflow.

### Data Inventory
Use this tab for library-level context rather than session-dataset QA. It loads the app-managed synthesis data automatically, then shows synthesis-backed category counts, top studies by row contribution, SOM and bulk density distributions, correlations, density contours, and geographic coverage hints.

Inventory utilities use the standalone synthesis data provider. By default, they read the app-managed `files/current/CCN_synthesis` cache or fetch it on first use.

### Metadata
Use this tab for citation, stewardship, data-use, service-source, and software acknowledgement information. It includes the recommended CCN Data Library citation and reminders that users should also cite original dataset contributors where appropriate.

## Data Requirements

QA Dashboard and Data Inventory need CCN synthesis reference files, especially `CCN_depthseries.csv` and `CCN_cores.csv`.

Current supported paths:

- Set `CCN_DATA_DIR` to a folder containing the CCN synthesis CSV files.
- Let the standalone launcher download and install the Smithsonian Figshare files into `files/current/CCN_synthesis`.
- Set `CCN_DATA_CACHE_DIR` to redirect the app-managed cache root.

The download manifest is tracked in [../ccn_dashboard/data_manifest.py](../ccn_dashboard/data_manifest.py). First launch downloads once; later launches reuse the local cache unless a force refresh is requested.

## Maintainer Notes

Important dashboard files:

- [shiny_dashboard.py](shiny_dashboard.py) composes the Shiny app and tab order.
- [dashboard_shared_dataset.py](dashboard_shared_dataset.py) stores the session dataset mirrored from Data Explorer.
- [panels/pygwalker_page.py](panels/pygwalker_page.py) renders the persistent Data Explorer iframe and handles spreadsheet sync messages.
- [panels/pygwalker_persistence.py](panels/pygwalker_persistence.py) injects the CCN spreadsheet and bridge config into PyGWalker HTML.
- [panels/qa_panel.py](panels/qa_panel.py), [panels/eo_panel.py](panels/eo_panel.py), [panels/data_inventory.py](panels/data_inventory.py), [panels/carbon_modeling.py](panels/carbon_modeling.py), and [panels/metadata_panel.py](panels/metadata_panel.py) define the major dashboard tabs.
- [utils/qa.py](utils/qa.py), [utils/inventory_io.py](utils/inventory_io.py), [utils/synthesis_io.py](utils/synthesis_io.py), and [utils/geo.py](utils/geo.py) contain the main reference-data and matching helpers.
- [../interactive_dash/app/src](../interactive_dash/app/src) contains the customized frontend source for the embedded Data Explorer.

Verification commands:

```bash
uv run pytest -q
cd src/interactive_dash/app && npm run test:unit
cd src/interactive_dash/app && npm run build
```

The frontend build writes runtime assets into the ignored [../interactive_dash/pygwalker/templates/dist](../interactive_dash/pygwalker/templates/dist) directory. Those files should be regenerated for verification and packaged for standalone use, but not hand-edited.

## Appendix A: PyGWalker And Data Explorer References

External documentation and source references:

- PyGWalker homepage: https://kanaries.net/pygwalker
- PyGWalker repository: https://github.com/Kanaries/pygwalker
- PyGWalker documentation portal: https://docs.kanaries.net
- PyGWalker package page: https://pypi.org/project/pygwalker
- Graphic Walker package used by the local frontend: `@kanaries/graphic-walker` version `0.5.0-alpha.2`

Local CCN customization references:

- [../interactive_dash/README.md](../interactive_dash/README.md) identifies this as the local PyGWalker copy used by the dashboard.
- [../interactive_dash/app/src/index.tsx](../interactive_dash/app/src/index.tsx) renders the split spreadsheet plus Graphic Walker interface.
- [../interactive_dash/app/src/features/ccnSpreadsheet](../interactive_dash/app/src/features/ccnSpreadsheet) contains import, spreadsheet, persistence, and shared-dataset bridge logic.
- [../interactive_dash/pygwalker/services/render.py](../interactive_dash/pygwalker/services/render.py) reads the packaged PyGWalker frontend bundle used by `pyg.to_html`.
- [panels/pygwalker_persistence.py](panels/pygwalker_persistence.py) is the Shiny-side integration point for stable Data Explorer HTML generation.

## Appendix B: Modeling Phase Key Findings

The Carbon Modeling tab summarizes saved notebook outputs rather than rerunning models. Key findings shown in the dashboard are:

- The pooled modeling cohort contains 676 cores from 33 studies after the rock-screening pass.
- Fraction carbon is the most defensible prediction target. The calibrated pooled ExtraTrees workflow predicts 0-30 cm `fraction_carbon` with overall R^2 = +0.406, within-study R^2 = +0.256, MAE = 0.067, and 51.2% of predictions within +/-0.05 fraction carbon.
- Study-level validation matters. On the N>=10 cohort, median per-study Pearson r was +0.530, and 69% of studies had r > 0.3.
- Calibration improved usability but did not solve the high-carbon tail. Per-tier isotonic calibration had MAE = 0.0673, median absolute error = 0.0483, and 89.1% empirical coverage for nominal 90% intervals.
- Habitat-specific signal was uneven. Marsh-only modeling improved within-study structure with within R^2 = +0.344 and within r = +0.587, while mangrove-only modeling remained underpowered with 103 cores across 11 studies.
- Direct SOC stock prediction is not ready as a prediction product. Calibrated SOC stock modeling had overall R^2 = -0.215 and MAE = 39.2 Mg C/ha; the two-stage carbon by dry bulk density approach was worse after calibration.
- ExtraTrees was the strongest model family in the tested model zoo, reaching within-study R^2 = +0.252 before filtering and calibration.
- Recurring feature signals included water, climate, vegetation, and terrain variables. Marsh predictors included mean annual precipitation, inundation frequency, NDVI peak greenness, cyclone wind, and SWIR reflectance. Mangrove predictors included temperature, inundation observations, SAR VH, elevation, and precipitation.
- Rock screening was useful QA but not a major skill cure. The C-vs-OM check flagged 44 suspicious high-carbon, low-organic-matter cores and 72 carbon-greater-than-organic-matter violations; removing suspicious cores barely changed within-study R^2.
- Regression to the mean remained the main error pattern, with low-carbon deciles over-predicted and high-carbon deciles under-predicted.