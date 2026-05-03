"""QA Dashboard panel — compare user data against CCN reference distributions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd
import polars as pl
from shiny import module, reactive, render, ui
from shiny.types import SilentException
from utils.qa import (
    ALL_CANONICAL,
    QA_NUMERIC_COLS,
    VARIABLE_CHOICES,
    apply_geo_filters,
    auto_match_columns,
    build_comparison_results,
    build_depth_profile_html,
    build_duplicate_diagnostics_html,
    build_map_html,
    build_overview_grid,
    build_qa_chart,
    build_qaqc_summary_html,
    build_relationship_diagnostics_html,
    build_stats_html,
    load_reference_data,
    matched_numeric_variables,
    run_validation,
)


def validation_report_csv(warnings: pd.DataFrame) -> str:
    if warnings.empty:
        return "No validation issues.\n"
    return warnings.to_csv(index=False)


def _input_values(module_input: Any, input_id: str) -> list:
    value_getter = getattr(module_input, input_id, None)
    if value_getter is None:
        return []
    try:
        value = value_getter()
    except SilentException:
        return []
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return list(value)


def _qa_map_controls():
    return ui.div(
        ui.tags.style("""
            .qa-map-control-row {
                display: flex;
                flex-wrap: nowrap;
                gap: 0.75rem;
                align-items: flex-end;
                overflow-x: auto;
                padding-bottom: 0.25rem;
            }
            .qa-map-control-row .form-group,
            .qa-map-control-row .form-check,
            .qa-map-control-row .selectize-control {
                margin-bottom: 0;
            }
            .qa-map-toggle-control {
                flex: 0 0 auto;
                min-width: 8.5rem;
                padding-bottom: 0.45rem;
                white-space: nowrap;
            }
            .qa-map-toggle-control .shiny-input-container {
                width: auto !important;
            }
            .qa-map-filter-control {
                flex: 1 0 9.5rem;
                min-width: 9.5rem;
            }
            .qa-map-filter-control--optional:empty {
                display: none;
            }
            .qa-map-filter-control .shiny-input-container {
                width: 100% !important;
            }
            .qa-map-filter-control--wide {
                flex-basis: 11rem;
            }
            """),
        ui.div(
            ui.div(
                ui.input_checkbox("show_ref", "Show CCN reference cores", value=True),
                class_="qa-map-toggle-control",
            ),
            ui.div(
                ui.input_checkbox("show_user", "Show my data", value=True),
                class_="qa-map-toggle-control",
            ),
            ui.div(
                ui.input_selectize("map_continent", "Continent", choices=[], multiple=True),
                class_="qa-map-filter-control",
            ),
            ui.div(
                ui.input_selectize("map_country", "Country", choices=[], multiple=True),
                class_="qa-map-filter-control",
            ),
            ui.output_ui(
                "map_us_subregion_ui",
                class_="qa-map-filter-control qa-map-filter-control--optional",
            ),
            ui.div(
                ui.input_selectize("map_habitat", "Filter CCN by Habitat", choices=[], multiple=True),
                class_="qa-map-filter-control qa-map-filter-control--wide",
            ),
            class_="qa-map-control-row",
        ),
        class_="qa-map-controls mb-2",
    )


@module.ui
def qa_ui():
    comparison_choices = {"__all__": "All matched variables"}
    comparison_choices.update({k: f"{k}  ({v['unit']})" for k, v in QA_NUMERIC_COLS.items()})

    return ui.navset_tab(
        # --- QA Charts tab ---
        ui.nav_panel(
            "QA Charts",
            ui.layout_sidebar(
                ui.sidebar(
                    ui.input_select(
                        "chart_var",
                        "Variable",
                        choices=VARIABLE_CHOICES,
                        selected="__all__",
                    ),
                    ui.input_radio_buttons(
                        "chart_type",
                        "Chart Style",
                        choices=[
                            "Histogram + Strip",
                            "Point Cloud",
                            "Violin + Strip",
                            "Box + Strip",
                        ],
                        selected="Histogram + Strip",
                    ),
                    ui.hr(),
                    ui.tags.small("Geographic Filters", class_="text-muted fw-bold"),
                    ui.input_selectize("chart_continent", "Continent", choices=[], multiple=True),
                    ui.input_selectize("chart_country", "Country", choices=[], multiple=True),
                    ui.output_ui("chart_us_subregion_ui"),
                    ui.input_selectize(
                        "chart_habitat",
                        "Filter CCN by Habitat",
                        choices=[],
                        multiple=True,
                    ),
                    ui.hr(),
                    ui.p(
                        "Blue = CCN reference distributions",
                        style="color:#4C72B0;font-size:0.85em;margin:0",
                    ),
                    ui.p(
                        "Red = your current session dataset",
                        style="color:#E74C3C;font-size:0.85em;margin:0",
                    ),
                    width=280,
                ),
                ui.output_ui("qa_chart"),
                ui.output_ui("stats_panel"),
                ui.output_ui("qaqc_summary_panel"),
                ui.output_ui("relationship_diagnostics_panel"),
                ui.output_ui("depth_profile_panel"),
                ui.output_ui("duplicate_diagnostics_panel"),
            ),
        ),
        # --- Statistical Tests tab ---
        ui.nav_panel(
            "Statistical Tests",
            ui.layout_sidebar(
                ui.sidebar(
                    ui.input_select(
                        "comparison_var",
                        "Variable",
                        choices=comparison_choices,
                        selected="__all__",
                    ),
                    ui.input_select(
                        "comparison_test",
                        "Statistical Test",
                        choices={
                            "ks": "Kolmogorov-Smirnov",
                            "anderson": "Anderson-Darling",
                        },
                        selected="ks",
                    ),
                    ui.input_selectize(
                        "comparison_habitat",
                        "Filter CCN by Habitat",
                        choices=[],
                        multiple=True,
                    ),
                    ui.hr(),
                    ui.tags.small("Geographic Filters", class_="text-muted fw-bold"),
                    ui.input_selectize("comparison_continent", "Continent", choices=[], multiple=True),
                    ui.input_selectize("comparison_country", "Country", choices=[], multiple=True),
                    ui.output_ui("comparison_us_subregion_ui"),
                    ui.hr(),
                    ui.p(
                        "Comparisons use the current session dataset from the Data Explorer tab.",
                        class_="text-muted small",
                    ),
                    width=300,
                ),
                ui.card(
                    ui.card_header("Matched Dataset Columns"),
                    ui.output_ui("comparison_mapping"),
                ),
                ui.card(
                    ui.card_header("Statistical Comparison Results"),
                    ui.output_ui("comparison_results_ui"),
                ),
            ),
        ),
        # --- Validation tab ---
        ui.nav_panel(
            "Validation",
            ui.card(
                ui.card_header(
                    ui.div(
                        ui.tags.strong("Validation Warnings"),
                        ui.output_text("validation_summary", inline=True),
                        class_="d-flex justify-content-between w-100",
                    )
                ),
                ui.output_data_frame("validation_table"),
            ),
            ui.div(
                ui.download_button(
                    "download_warnings",
                    "Download Validation Report",
                    class_="btn-outline-secondary btn-sm",
                ),
                class_="mt-2",
            ),
        ),
        # --- QA Map tab ---
        ui.nav_panel(
            "QA Map",
            _qa_map_controls(),
            ui.output_ui("map_status"),
            ui.output_ui("map_display"),
        ),
    )


@module.server
def qa_server(module_input, _output, _session, data_getter: Callable[[], pl.DataFrame | None]):
    # Lazy-load reference data on first access
    _ = (_output, _session)
    ref_data: reactive.Value[dict[str, Any] | None] = reactive.Value(None)

    @reactive.calc
    def _ensure_ref() -> dict[str, Any]:
        """Load reference data once, then cache."""
        cached = ref_data.get()
        if cached is not None:
            return cached
        data = load_reference_data()
        ref_data.set(data)
        return data

    @reactive.effect
    def _populate_initial_choices():
        data = _ensure_ref()
        for prefix in ("chart", "comparison", "map"):
            ui.update_selectize(f"{prefix}_continent", choices=data["continent_choices"])
            ui.update_selectize(f"{prefix}_country", choices=data["country_choices"])
            ui.update_selectize(f"{prefix}_habitat", choices=data["habitat_choices"])

    # --- Cascading geo filter helpers (one set per tab prefix) ---

    def _read_geo_inputs(prefix: str):
        """Return (continents, countries, us_subregions, habitats) lists for a tab."""
        continents = _input_values(module_input, f"{prefix}_continent")
        countries = _input_values(module_input, f"{prefix}_country")
        us_subs = _input_values(module_input, f"{prefix}_us_subregion")
        habitats = _input_values(module_input, f"{prefix}_habitat")
        return continents, countries, us_subs, habitats

    def _cascade_for(prefix: str):
        """Wire cascading updates for continent→country→us_subregion→habitat."""
        data = _ensure_ref()
        ref = data["ref_merged"]

        continents = list(getattr(module_input, f"{prefix}_continent")() or [])
        countries_input = list(getattr(module_input, f"{prefix}_country")() or [])

        # Narrow country choices by continent
        subset = ref.copy()
        if continents:
            subset = subset[subset["continent"].isin(continents)]
        avail_countries = sorted(subset["country"].replace("", pd.NA).dropna().unique().tolist())
        ui.update_selectize(
            f"{prefix}_country",
            choices=avail_countries,
            selected=[c for c in countries_input if c in avail_countries],
        )

        # Narrow habitat choices by continent + country
        if countries_input:
            subset = subset[subset["country"].isin(countries_input)]
        avail_habitats = sorted(subset["habitat"].dropna().unique().tolist())
        current_habitats = list(getattr(module_input, f"{prefix}_habitat")() or [])
        ui.update_selectize(
            f"{prefix}_habitat",
            choices=avail_habitats,
            selected=[h for h in current_habitats if h in avail_habitats],
        )

    @reactive.effect
    def _cascade_chart():
        _cascade_for("chart")

    @reactive.effect
    def _cascade_comparison():
        _cascade_for("comparison")

    @reactive.effect
    def _cascade_map():
        _cascade_for("map")

    # Conditionally render US sub-region input (only when US data is in scope)

    def _us_subregion_ui_for(prefix: str):
        data = _ensure_ref()
        continents = list(getattr(module_input, f"{prefix}_continent")() or [])
        countries = list(getattr(module_input, f"{prefix}_country")() or [])
        # Show if US is explicitly selected OR no country filter but North America continent selected
        show = "united states" in countries or (not countries and "north america" in continents)
        if not show:
            return ui.TagList()
        choices = data["us_subregion_choices"]
        return ui.input_selectize(f"{prefix}_us_subregion", "US Sub-region", choices=choices, multiple=True)

    @render.ui
    def chart_us_subregion_ui():
        return _us_subregion_ui_for("chart")

    @render.ui
    def comparison_us_subregion_ui():
        return _us_subregion_ui_for("comparison")

    @render.ui
    def map_us_subregion_ui():
        return _us_subregion_ui_for("map")

    # --- User data (Polars -> Pandas) + auto column matching ---

    @reactive.calc
    def user_pandas() -> pd.DataFrame | None:
        df = data_getter()
        if df is None:
            return None
        return df.to_pandas()

    @reactive.calc
    def resolved_col_map() -> dict[str, str | None]:
        df = user_pandas()
        if df is None:
            return {k: None for k in ALL_CANONICAL}
        return auto_match_columns(df.columns.tolist())

    # --- QA Charts ---

    @render.ui
    def qa_chart():
        data = _ensure_ref()
        ref_merged = data["ref_merged"]
        var = module_input.chart_var()
        chart_type = module_input.chart_type()
        continents, countries, us_subs, habitats = _read_geo_inputs("chart")
        mapping = resolved_col_map()
        df = user_pandas()

        if var == "__all__":
            html = build_overview_grid(
                ref_merged,
                df,
                mapping,
                habitats,
                chart_type,
                continents=continents,
                countries=countries,
                us_subregions=us_subs,
            )
            return ui.HTML(html)

        ref = apply_geo_filters(ref_merged.copy(), continents, countries, us_subs, habitats)

        if var not in ref.columns:
            return ui.p(f"'{var}' not found in reference data.")

        ref_values = pd.to_numeric(ref[var], errors="coerce")
        ref_habitat = ref["habitat"] if "habitat" in ref.columns else None
        ref_study = ref["study_id"] if "study_id" in ref.columns else None

        user_values = None
        if df is not None and mapping.get(var):
            ucol = mapping[var]
            if ucol in df.columns:
                user_values = df[ucol]

        html = build_qa_chart(
            ref_values,
            user_values,
            var,
            QA_NUMERIC_COLS.get(var, {}).get("unit", ""),
            chart_type,
            user_df=df,
            col_map=mapping,
            ref_habitat=ref_habitat,
            ref_study_id=ref_study,
        )
        return ui.HTML(html)

    @render.ui
    def stats_panel():
        data = _ensure_ref()
        ref_merged = data["ref_merged"]
        var = module_input.chart_var()
        if var == "__all__":
            return ui.HTML("")

        continents, countries, us_subs, habitats = _read_geo_inputs("chart")
        ref = apply_geo_filters(ref_merged.copy(), continents, countries, us_subs, habitats)

        ref_series = ref[var] if var in ref.columns else pd.Series(dtype=float)
        ref_values = pd.to_numeric(ref_series, errors="coerce")
        mapping = resolved_col_map()
        df = user_pandas()
        user_values = None
        if df is not None and mapping.get(var):
            ucol = mapping[var]
            if ucol in df.columns:
                user_values = df[ucol]

        return ui.HTML(build_stats_html(ref_values, user_values, var))

    @render.ui
    def qaqc_summary_panel():
        return ui.HTML(build_qaqc_summary_html(user_pandas(), resolved_col_map(), validation_results()))

    @render.ui
    def relationship_diagnostics_panel():
        data = _ensure_ref()
        continents, countries, us_subs, habitats = _read_geo_inputs("chart")
        return ui.HTML(
            build_relationship_diagnostics_html(
                data["ref_merged"],
                user_pandas(),
                resolved_col_map(),
                habitats=habitats,
                continents=continents,
                countries=countries,
                us_subregions=us_subs,
            )
        )

    @render.ui
    def depth_profile_panel():
        return ui.HTML(build_depth_profile_html(user_pandas(), resolved_col_map()))

    @render.ui
    def duplicate_diagnostics_panel():
        return ui.HTML(build_duplicate_diagnostics_html(user_pandas(), resolved_col_map()))

    # --- Validation ---

    @reactive.calc
    def validation_results():
        df = user_pandas()
        if df is None:
            return pd.DataFrame(columns=["Row", "Column", "Value", "Issue"])
        return run_validation(df, resolved_col_map())

    @render.text
    def validation_summary():
        w = validation_results()
        if w.empty:
            return "  No issues found."
        return f"  {len(w)} issue(s) found"

    @render.data_frame
    def validation_table():
        w = validation_results()
        if w.empty:
            return render.DataGrid(
                pd.DataFrame({"Status": ["No validation issues. Import or edit data in the Data Explorer tab."]}),
            )
        return render.DataGrid(w)

    @render.download(filename="validation_report.csv")
    def download_warnings():
        yield validation_report_csv(validation_results())

    # --- Statistical Tests ---

    @render.ui
    def comparison_mapping():
        df = user_pandas()
        if df is None:
            return ui.p(
                "Import or edit data in the Data Explorer tab to compare your session dataset against CCN reference data.",
                class_="text-muted p-3",
            )

        matches = matched_numeric_variables(df, resolved_col_map())
        if not matches:
            return ui.div(
                "No comparable QA variables were auto-matched. Add or rename numeric columns so they resemble CCN fields such as dry_bulk_density, fraction_carbon, or fraction_organic_matter.",
                class_="alert alert-warning m-3",
                role="alert",
            )

        rows = [
            ui.tags.tr(
                ui.tags.td(match["variable"], style="padding:8px 12px;"),
                ui.tags.td(match["user_column"], style="padding:8px 12px;"),
                ui.tags.td(match["unit"], style="padding:8px 12px;"),
            )
            for match in matches
        ]
        table = ui.tags.table(
            ui.tags.thead(
                ui.tags.tr(
                    ui.tags.th("CCN variable", style="padding:8px 12px;"),
                    ui.tags.th("Your column", style="padding:8px 12px;"),
                    ui.tags.th("Unit", style="padding:8px 12px;"),
                )
            ),
            ui.tags.tbody(*rows),
            class_="table table-sm table-hover mb-0",
        )
        return ui.TagList(
            ui.p(
                "These are the session-dataset columns QA can benchmark against CCN reference distributions.",
                class_="text-muted px-3 pt-3 pb-0 mb-2",
            ),
            table,
        )

    @render.ui
    def comparison_results_ui():
        data = _ensure_ref()
        df = user_pandas()
        if df is None:
            return ui.p(
                "Import or edit data in the Data Explorer tab to generate statistical comparisons.",
                class_="text-muted p-3",
            )

        continents, countries, us_subs, habitats = _read_geo_inputs("comparison")
        results = build_comparison_results(
            data["ref_merged"],
            df,
            resolved_col_map(),
            habitats=habitats,
            variable=module_input.comparison_var(),
            test_name=module_input.comparison_test(),
            continents=continents,
            countries=countries,
            us_subregions=us_subs,
        )
        if not results:
            return ui.div(
                "No statistical comparisons are available for the current dataset and filters.",
                class_="alert alert-warning m-3",
                role="alert",
            )

        test_label = {
            "ks": "Kolmogorov-Smirnov",
            "anderson": "Anderson-Darling",
        }

        def _p_color(p_value: float | None) -> str:
            if p_value is None:
                return "#6c757d"
            if p_value >= 0.05:
                return "#198754"
            if p_value >= 0.01:
                return "#ffc107"
            return "#dc3545"

        rows = []
        for result in results:
            p_value = result["p_value"]
            color = _p_color(p_value if isinstance(p_value, float) else None)
            rows.append(
                ui.tags.tr(
                    ui.tags.td(result["variable"], style="padding:8px 12px;"),
                    ui.tags.td(result["user_column"], style="padding:8px 12px;"),
                    ui.tags.td(
                        str(result["n_user"]),
                        style="padding:8px 12px; text-align:right;",
                    ),
                    ui.tags.td(
                        str(result["n_ref"]),
                        style="padding:8px 12px; text-align:right;",
                    ),
                    ui.tags.td(
                        (str(result["statistic"]) if result["statistic"] is not None else "-"),
                        style="padding:8px 12px; text-align:right;",
                    ),
                    ui.tags.td(
                        str(p_value) if p_value is not None else "-",
                        style=f"padding:8px 12px; text-align:right; font-weight:600; color:{color};",
                    ),
                    ui.tags.td(
                        result["interpretation"],
                        style=f"padding:8px 12px; color:{color};",
                    ),
                )
            )

        table = ui.tags.table(
            ui.tags.thead(
                ui.tags.tr(
                    ui.tags.th("Variable", style="padding:8px 12px;"),
                    ui.tags.th("Your column", style="padding:8px 12px;"),
                    ui.tags.th("n (you)", style="padding:8px 12px; text-align:right;"),
                    ui.tags.th("n (CCN)", style="padding:8px 12px; text-align:right;"),
                    ui.tags.th("Statistic", style="padding:8px 12px; text-align:right;"),
                    ui.tags.th("p-value", style="padding:8px 12px; text-align:right;"),
                    ui.tags.th("Interpretation", style="padding:8px 12px;"),
                ),
                style="border-bottom:2px solid #dee2e6;",
            ),
            ui.tags.tbody(*rows),
            class_="table table-hover mb-0",
            style="width:100%;",
        )

        habitat_label = ", ".join(habitats) if habitats else "All habitats"
        geo_parts = []
        if continents:
            geo_parts.append(", ".join(continents))
        if countries:
            geo_parts.append(", ".join(countries))
        if us_subs:
            geo_parts.append(", ".join(us_subs))
        geo_label = " — ".join(geo_parts) if geo_parts else "All regions"
        summary = ui.p(
            f"{test_label.get(module_input.comparison_test(), module_input.comparison_test())} against {habitat_label} / {geo_label} reference data.",
            class_="text-muted px-3 pt-3 pb-0 mb-2",
        )
        legend = ui.div(
            ui.tags.span("■ ", style="color:#198754;"),
            "p ≥ 0.05 — not significantly different   ",
            ui.tags.span("■ ", style="color:#ffc107;"),
            "p < 0.05 — significantly different   ",
            ui.tags.span("■ ", style="color:#dc3545;"),
            "p < 0.01 — extremely different",
            style="font-size:0.85rem; padding:6px 16px 12px; color:#6c757d;",
        )
        return ui.TagList(summary, table, legend)

    # --- QA Map ---

    @render.ui
    def map_display():
        data = _ensure_ref()
        mapping = resolved_col_map()
        df = user_pandas()
        continents, countries, us_subs, habitats = _read_geo_inputs("map")

        lat_c = mapping.get("latitude")
        lon_c = mapping.get("longitude")

        map_result = build_map_html(
            data["ref_cores_valid"],
            df,
            lat_c,
            lon_c,
            show_ref=module_input.show_ref(),
            show_user=module_input.show_user(),
            habitat_filter=habitats,
            continents=continents,
            countries=countries,
            us_subregions=us_subs,
        )
        return ui.HTML(map_result[0])

    @render.ui
    def map_status():
        data = _ensure_ref()
        mapping = resolved_col_map()
        df = user_pandas()
        lat_c = mapping.get("latitude")
        lon_c = mapping.get("longitude")

        ref_n = len(data["ref_cores_valid"])
        user_n = 0
        if df is not None and lat_c and lon_c and lat_c in df.columns and lon_c in df.columns:
            user_n = df[[lat_c, lon_c]].dropna().shape[0]

        dash = "\u2014"
        return ui.HTML(
            f'<p style="font-size:0.9em;color:#555">'
            f"Reference cores: {ref_n:,} | Your data points: {user_n} | "
            f"Lat col: {lat_c or dash} | Lon col: {lon_c or dash}</p>"
        )
