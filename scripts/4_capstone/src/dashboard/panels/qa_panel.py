"""QA Dashboard panel — compare user data against CCN reference distributions."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import polars as pl
from shiny import module, reactive, render, ui
from utils.qa import (
    ALL_CANONICAL,
    QA_NUMERIC_COLS,
    VARIABLE_CHOICES,
    auto_match_columns,
    build_comparison_results,
    build_map_html,
    build_overview_grid,
    build_qa_chart,
    build_stats_html,
    load_reference_data,
    matched_numeric_variables,
    run_validation,
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
                    ui.input_select("chart_var", "Variable", choices=VARIABLE_CHOICES, selected="__all__"),
                    ui.input_radio_buttons(
                        "chart_type",
                        "Chart Style",
                        choices=["Histogram + Strip", "Point Cloud", "Violin + Strip", "Box + Strip"],
                        selected="Histogram + Strip",
                    ),
                    ui.input_selectize("chart_habitat", "Filter CCN by Habitat", choices=[], multiple=True),
                    ui.hr(),
                    ui.p("Blue = CCN reference distributions", style="color:#4C72B0;font-size:0.85em;margin:0"),
                    ui.p("Red = your current session dataset", style="color:#E74C3C;font-size:0.85em;margin:0"),
                    width=280,
                ),
                ui.output_ui("qa_chart"),
                ui.output_ui("stats_panel"),
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
                    "download_warnings", "Download Validation Report", class_="btn-outline-secondary btn-sm"
                ),
                class_="mt-2",
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
                        choices={"ks": "Kolmogorov-Smirnov", "anderson": "Anderson-Darling"},
                        selected="ks",
                    ),
                    ui.input_selectize("comparison_habitat", "Filter CCN by Habitat", choices=[], multiple=True),
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
        # --- QA Map tab ---
        ui.nav_panel(
            "QA Map",
            ui.layout_columns(
                ui.input_checkbox("show_ref", "Show CCN reference cores", value=True),
                ui.input_checkbox("show_user", "Show my data", value=True),
                ui.input_selectize("map_habitat", "Filter CCN by Habitat", choices=[], multiple=True),
                col_widths=[3, 3, 6],
            ),
            ui.output_ui("map_status"),
            ui.output_ui("map_display"),
        ),
    )


@module.server
def qa_server(module_input, _output, _session, data_getter: Callable[[], pl.DataFrame | None]):
    # Lazy-load reference data on first access
    _ = (_output, _session)
    ref_data = reactive.Value(None)

    @reactive.calc
    def _ensure_ref():
        """Load reference data once, then cache."""
        cached = ref_data.get()
        if cached is not None:
            return cached
        data = load_reference_data()
        ref_data.set(data)
        return data

    @reactive.effect
    def _populate_habitat_choices():
        data = _ensure_ref()
        choices = data["habitat_choices"]
        ui.update_selectize("chart_habitat", choices=choices)
        ui.update_selectize("comparison_habitat", choices=choices)
        ui.update_selectize("map_habitat", choices=choices)

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
        habitats = list(module_input.chart_habitat()) if module_input.chart_habitat() else []
        mapping = resolved_col_map()
        df = user_pandas()

        if var == "__all__":
            html = build_overview_grid(ref_merged, df, mapping, habitats, chart_type)
            return ui.HTML(html)

        ref = ref_merged.copy()
        if habitats:
            ref = ref[ref["habitat"].isin(habitats)]

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

        habitats = list(module_input.chart_habitat()) if module_input.chart_habitat() else []
        ref = ref_merged.copy()
        if habitats:
            ref = ref[ref["habitat"].isin(habitats)]

        ref_values = pd.to_numeric(ref.get(var, pd.Series(dtype=float)), errors="coerce")
        mapping = resolved_col_map()
        df = user_pandas()
        user_values = None
        if df is not None and mapping.get(var):
            ucol = mapping[var]
            if ucol in df.columns:
                user_values = df[ucol]

        return ui.HTML(build_stats_html(ref_values, user_values, var))

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
        w = validation_results()
        if w.empty:
            yield "No validation issues.\n"
            return
        yield w.to_csv(index=False)

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

        habitats = list(module_input.comparison_habitat()) if module_input.comparison_habitat() else []
        results = build_comparison_results(
            data["ref_merged"],
            df,
            resolved_col_map(),
            habitats=habitats,
            variable=module_input.comparison_var(),
            test_name=module_input.comparison_test(),
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
                    ui.tags.td(str(result["n_user"]), style="padding:8px 12px; text-align:right;"),
                    ui.tags.td(str(result["n_ref"]), style="padding:8px 12px; text-align:right;"),
                    ui.tags.td(
                        str(result["statistic"]) if result["statistic"] is not None else "-",
                        style="padding:8px 12px; text-align:right;",
                    ),
                    ui.tags.td(
                        str(p_value) if p_value is not None else "-",
                        style=f"padding:8px 12px; text-align:right; font-weight:600; color:{color};",
                    ),
                    ui.tags.td(result["interpretation"], style=f"padding:8px 12px; color:{color};"),
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
        summary = ui.p(
            f"{test_label.get(module_input.comparison_test(), module_input.comparison_test())} against {habitat_label} reference data.",
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
        habitats = list(module_input.map_habitat()) if module_input.map_habitat() else []

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
