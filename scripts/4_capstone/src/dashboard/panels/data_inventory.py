from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from shiny import module, reactive, render, ui
from utils.distributions import compare_distributions, find_comparable_columns
from utils.geo_gaps import generate_gap_hints
from utils.inventory_io import build_inventory_df
from utils.synthesis_io import build_synthesis_df

matplotlib.use("Agg")

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------


@module.ui
def data_inventory_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.h5("Inventory Controls"),
            ui.input_action_button("load_inventory", "Load Inventory", class_="btn-primary w-100 mb-3"),
            ui.hr(),
            ui.h6("Distribution Comparison"),
            ui.input_file("user_file", "Upload your dataset (.csv/.xlsx)", accept=[".csv", ".xlsx", ".xls"]),
            ui.output_ui("column_selectors"),
            ui.input_select(
                "test_type", "Statistical Test", choices={"ks": "Kolmogorov–Smirnov", "anderson": "Anderson–Darling"}
            ),
            ui.input_action_button("run_comparison", "Run Comparison", class_="btn-outline-primary w-100"),
            width=300,
        ),
        # main area
        ui.navset_card_tab(
            ui.nav_panel(
                "File Inventory",
                ui.output_ui("inventory_summary_cards"),
                ui.layout_columns(
                    ui.card(ui.card_header("Category Distribution"), ui.output_plot("plot_category_dist")),
                    ui.card(ui.card_header("Top Studies by File Count"), ui.output_plot("plot_study_counts")),
                    col_widths=[6, 6],
                ),
            ),
            ui.nav_panel(
                "Synthesis Summary",
                ui.output_ui("synthesis_summary_cards"),
                ui.layout_columns(
                    ui.card(ui.card_header("SOM Distribution"), ui.output_plot("plot_som_hist")),
                    ui.card(ui.card_header("Bulk Density Distribution"), ui.output_plot("plot_bd_hist")),
                    col_widths=[6, 6],
                ),
                ui.layout_columns(
                    ui.card(ui.card_header("SOM vs Bulk Density"), ui.output_plot("plot_som_bd_scatter")),
                    ui.card(ui.card_header("Correlation Heatmap"), ui.output_plot("plot_corr_heatmap")),
                    col_widths=[6, 6],
                ),
                ui.card(ui.card_header("Bivariate KDE (Top 6 Studies)"), ui.output_plot("plot_kde")),
            ),
            ui.nav_panel(
                "Geographic Coverage",
                ui.card(ui.card_header("Area Contribution"), ui.output_plot("plot_area_bar")),
                ui.card(ui.card_header("Coverage Gap Hints"), ui.output_ui("gap_hints_ui")),
            ),
            ui.nav_panel(
                "Distribution Comparison",
                ui.output_ui("comparison_results_ui"),
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------


@module.server
def data_inventory_server(input, output, session):
    inventory_df: reactive.Value[pd.DataFrame | None] = reactive.Value(None)
    synthesis_df: reactive.Value[pd.DataFrame | None] = reactive.Value(None)
    user_df: reactive.Value[pd.DataFrame | None] = reactive.Value(None)
    comparison_results: reactive.Value[list | None] = reactive.Value(None)

    # ---- Load inventory on button click (cached) -------------------------

    @reactive.effect
    @reactive.event(input.load_inventory)
    def _load():
        inv = build_inventory_df()
        inventory_df.set(inv)
        syn = build_synthesis_df(inv)
        synthesis_df.set(syn)

    # ---- User file upload -------------------------------------------------

    @reactive.effect
    @reactive.event(input.user_file)
    def _upload():
        file_infos = input.user_file()
        if not file_infos:
            return
        info = file_infos[0]
        path = info["datapath"]
        name = info["name"].lower()
        try:
            if name.endswith(".csv"):
                df = pd.read_csv(path, on_bad_lines="skip", low_memory=False)
            elif name.endswith((".xlsx", ".xls")):
                df = pd.read_excel(path)
            else:
                return
            user_df.set(df)
        except Exception:
            user_df.set(None)

    # ---- Dynamic column selectors after upload ----------------------------

    @render.ui
    def column_selectors():
        df = user_df.get()
        if df is None:
            return ui.TagList()
        mapping = find_comparable_columns(df)
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not num_cols:
            return ui.TagList(
                ui.div(
                    "No numeric columns found in the uploaded file. "
                    "Distribution comparison requires a depthseries or cores CSV "
                    "with numeric columns such as fraction_carbon, "
                    "soil_organic_matter, or bulk_density.",
                    class_="alert alert-warning",
                    role="alert",
                )
            )

        som_default = next((k for k, v in mapping.items() if v == "som"), num_cols[0])
        bd_default = next((k for k, v in mapping.items() if v == "bulk_density"), num_cols[0])
        choices = {c: c for c in num_cols}

        hint = None
        if not mapping:
            hint = ui.div(
                "No SOM or bulk density columns were auto-detected. "
                "This file may not be a depthseries or cores dataset. "
                "Please verify the correct file is uploaded, or manually "
                "select the appropriate columns below.",
                class_="alert alert-warning",
                role="alert",
            )

        return ui.TagList(
            hint,
            ui.input_select("user_som_col", "Column to compare with SOM", choices=choices, selected=som_default),
            ui.input_select("user_bd_col", "Column to compare with Bulk Density", choices=choices, selected=bd_default),
        )

    # ---- Run comparison ---------------------------------------------------

    @reactive.effect
    @reactive.event(input.run_comparison)
    def _compare():
        udf = user_df.get()
        sdf = synthesis_df.get()
        if udf is None:
            ui.notification_show(
                "Please upload a dataset first.",
                type="warning",
            )
            return
        if sdf is None or sdf.empty:
            ui.notification_show(
                "Please click 'Load Inventory' before running a comparison.",
                type="warning",
            )
            return

        som_col = input.user_som_col()
        bd_col = input.user_bd_col()
        test = input.test_type()

        # Guard: verify selected columns exist in the uploaded file
        missing = []
        if som_col and som_col not in udf.columns:
            missing.append(som_col)
        if bd_col and bd_col not in udf.columns:
            missing.append(bd_col)
        if missing:
            ui.notification_show(
                f"Column(s) {', '.join(missing)} not found in the uploaded file. "
                "Please upload a depthseries or cores CSV that contains "
                "soil organic matter and/or bulk density measurements.",
                type="error",
                duration=8,
            )
            return

        results = []
        if som_col and "som" in sdf.columns:
            res = compare_distributions(udf[som_col], sdf["som"], test_name=test)
            res["user_col"] = som_col
            res["inventory_col"] = "som"
            results.append(res)
        if bd_col and "bulk_density" in sdf.columns:
            res = compare_distributions(udf[bd_col], sdf["bulk_density"], test_name=test)
            res["user_col"] = bd_col
            res["inventory_col"] = "bulk_density"
            results.append(res)

        if not results:
            ui.notification_show(
                "No comparable columns found. Ensure the uploaded file has " "numeric columns for SOM or bulk density.",
                type="warning",
            )
            return

        comparison_results.set(results)

    # ---- Inventory summary cards ------------------------------------------

    @render.ui
    def inventory_summary_cards():
        inv = inventory_df.get()
        if inv is None:
            return ui.p("Click 'Load Inventory' to scan the data repository.", class_="text-muted p-3")
        n_files = len(inv)
        n_studies = inv["study_id"].nunique()
        n_cats = inv["category"].nunique()
        return ui.layout_columns(
            ui.value_box("Total Files", str(n_files), theme="primary"),
            ui.value_box("Studies", str(n_studies), theme="info"),
            ui.value_box("Categories", str(n_cats), theme="success"),
            col_widths=[4, 4, 4],
        )

    # ---- Inventory plots --------------------------------------------------

    @render.plot
    def plot_category_dist():
        inv = inventory_df.get()
        if inv is None or inv.empty:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No data loaded", ha="center", va="center", transform=ax.transAxes)
            return fig
        fig, ax = plt.subplots(figsize=(10, max(4, len(inv["category"].unique()) * 0.35)))
        order = inv["category"].value_counts().index
        sns.countplot(y="category", data=inv, order=order, hue="category", palette="viridis", legend=False, ax=ax)
        ax.set_title("Distribution of File Categories")
        fig.tight_layout()
        return fig

    @render.plot
    def plot_study_counts():
        inv = inventory_df.get()
        if inv is None or inv.empty:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No data loaded", ha="center", va="center", transform=ax.transAxes)
            return fig
        counts = inv["study_id"].value_counts().head(20)
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.barplot(x=counts.index, y=counts.values, hue=counts.index, palette="mako", legend=False, ax=ax)
        ax.set_title("Top Studies by File Count")
        ax.set_ylabel("Files")
        plt.xticks(rotation=45, ha="right")
        fig.tight_layout()
        return fig

    # ---- Synthesis summary cards ------------------------------------------

    @render.ui
    def synthesis_summary_cards():
        sdf = synthesis_df.get()
        if sdf is None:
            return ui.p("Click 'Load Inventory' first.", class_="text-muted p-3")
        if sdf.empty:
            return ui.p("No studies with both SOM and Bulk Density columns were found.", class_="text-warning p-3")
        n_records = len(sdf)
        n_studies = sdf["source_study"].nunique()
        som_mean = f"{sdf['som'].mean():.2f}" if not sdf["som"].isna().all() else "N/A"
        bd_mean = f"{sdf['bulk_density'].mean():.2f}" if not sdf["bulk_density"].isna().all() else "N/A"
        return ui.layout_columns(
            ui.value_box("Records", str(n_records), theme="primary"),
            ui.value_box("Studies Merged", str(n_studies), theme="info"),
            ui.value_box("Mean SOM", som_mean, theme="success"),
            ui.value_box("Mean Bulk Density", bd_mean, theme="warning"),
            col_widths=[3, 3, 3, 3],
        )

    # ---- Synthesis plots --------------------------------------------------

    @render.plot
    def plot_som_hist():
        sdf = synthesis_df.get()
        if sdf is None or sdf.empty:
            return _empty_fig()
        fig, ax = plt.subplots(figsize=(8, 4))
        sns.histplot(sdf["som"].dropna(), bins=30, kde=True, ax=ax)
        ax.set_title("SOM Distribution")
        fig.tight_layout()
        return fig

    @render.plot
    def plot_bd_hist():
        sdf = synthesis_df.get()
        if sdf is None or sdf.empty:
            return _empty_fig()
        fig, ax = plt.subplots(figsize=(8, 4))
        sns.histplot(sdf["bulk_density"].dropna(), bins=30, kde=True, ax=ax)
        ax.set_title("Bulk Density Distribution")
        fig.tight_layout()
        return fig

    @render.plot
    def plot_som_bd_scatter():
        sdf = synthesis_df.get()
        if sdf is None or sdf.empty:
            return _empty_fig()
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.scatterplot(data=sdf, x="bulk_density", y="som", hue="source_study", alpha=0.5, legend=False, ax=ax)
        ax.set_title("SOM vs Bulk Density (All Studies)")
        ax.set_xlabel("Bulk Density")
        ax.set_ylabel("SOM / Fraction Carbon")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return fig

    @render.plot
    def plot_corr_heatmap():
        sdf = synthesis_df.get()
        if sdf is None or sdf.empty:
            return _empty_fig()
        corr = sdf[["som", "bulk_density"]].corr()
        fig, ax = plt.subplots(figsize=(4, 3))
        sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", ax=ax)
        ax.set_title("SOM vs Bulk Density Correlation")
        fig.tight_layout()
        return fig

    @render.plot
    def plot_kde():
        sdf = synthesis_df.get()
        if sdf is None or sdf.empty:
            return _empty_fig()
        top = sdf["source_study"].value_counts().head(6).index.tolist()
        subset = sdf[sdf["source_study"].isin(top)]
        fig, ax = plt.subplots(figsize=(10, 6))
        try:
            sns.kdeplot(data=subset, x="bulk_density", y="som", hue="source_study", fill=True, alpha=0.3, ax=ax)
            ax.set_title("SOM vs Bulk Density KDE (Top 6 Studies)")
        except FloatingPointError:
            ax.text(
                0.5,
                0.5,
                "KDE computation failed (numerical underflow)",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
        fig.tight_layout()
        return fig

    # ---- Geographic plots + hints -----------------------------------------

    @render.plot
    def plot_area_bar():
        sdf = synthesis_df.get()
        if sdf is None or sdf.empty:
            return _empty_fig()
        if "area" not in sdf.columns:
            fig, ax = plt.subplots()
            ax.text(
                0.5, 0.5, "No area column found in synthesis data", ha="center", va="center", transform=ax.transAxes
            )
            return fig
        area_counts = sdf["area"].value_counts().head(20)
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.barplot(
            x=area_counts.index, y=area_counts.values, hue=area_counts.index, palette="mako", legend=False, ax=ax
        )
        ax.set_title("Top Areas by Data Point Contribution")
        ax.set_ylabel("Data Points")
        plt.xticks(rotation=45, ha="right")
        fig.tight_layout()
        return fig

    @render.ui
    def gap_hints_ui():
        sdf = synthesis_df.get()
        if sdf is None:
            return ui.p("Load inventory first.", class_="text-muted")
        hints = generate_gap_hints(sdf)
        alert_map = {"danger": "alert-danger", "warning": "alert-warning", "info": "alert-info"}
        tags = []
        for h in hints:
            css = alert_map.get(h["level"], "alert-secondary")
            tags.append(ui.div(h["text"], class_=f"alert {css}", role="alert"))
        return ui.TagList(*tags)

    # ---- Distribution comparison results ----------------------------------

    @render.ui
    def comparison_results_ui():
        results = comparison_results.get()
        if results is None:
            return ui.p("Upload a dataset and click 'Run Comparison' to see results.", class_="text-muted p-3")

        test_label = {"ks": "Kolmogorov–Smirnov", "anderson": "Anderson–Darling"}
        test_name = test_label.get(results[0]["test"], results[0]["test"].upper()) if results else ""

        def _p_color(p):
            if p is None:
                return "#6c757d"  # grey – inconclusive
            if p >= 0.05:
                return "#198754"  # green – not significant
            if p >= 0.01:
                return "#ffc107"  # amber – significant at 5%
            return "#dc3545"  # red – highly significant

        # Build table rows
        rows = []
        for r in results:
            color = _p_color(r["p_value"])
            rows.append(
                ui.tags.tr(
                    ui.tags.td(
                        f"{r['user_col']}  →  {r['inventory_col']}",
                        style="padding:8px 12px;",
                    ),
                    ui.tags.td(
                        str(r["statistic"]) if r["statistic"] is not None else "—",
                        style="padding:8px 12px; text-align:right;",
                    ),
                    ui.tags.td(
                        str(r["p_value"]) if r["p_value"] is not None else "—",
                        style=f"padding:8px 12px; text-align:right; font-weight:600; color:{color};",
                    ),
                    ui.tags.td(
                        r["interpretation"],
                        style=f"padding:8px 12px; color:{color};",
                    ),
                )
            )

        table = ui.tags.table(
            ui.tags.thead(
                ui.tags.tr(
                    ui.tags.th("Comparison", style="padding:8px 12px;"),
                    ui.tags.th("Statistic", style="padding:8px 12px; text-align:right;"),
                    ui.tags.th("p-value", style="padding:8px 12px; text-align:right;"),
                    ui.tags.th("Interpretation", style="padding:8px 12px;"),
                ),
                style="border-bottom:2px solid #dee2e6;",
            ),
            ui.tags.tbody(*rows),
            class_="table table-hover",
            style="width:100%;",
        )

        # Legend
        legend = ui.div(
            ui.tags.span("■ ", style="color:#198754;"),
            "p ≥ 0.05 — not significantly different   ",
            ui.tags.span("■ ", style="color:#ffc107;"),
            "p < 0.05 — significantly different   ",
            ui.tags.span("■ ", style="color:#dc3545;"),
            "p < 0.01 — extremely different",
            style="font-size:0.85rem; padding:6px 0; color:#6c757d;",
        )

        return ui.card(
            ui.card_header(f"Results — {test_name} test"),
            table,
            legend,
        )

    # helper
    def _empty_fig():
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data loaded", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
