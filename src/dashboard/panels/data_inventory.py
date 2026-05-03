from __future__ import annotations

from textwrap import shorten

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.ticker import StrMethodFormatter
from shiny import module, reactive, render, ui

from dashboard.utils.geo_gaps import generate_gap_hints
from dashboard.utils.inventory_io import build_inventory_df
from dashboard.utils.synthesis_io import build_synthesis_df

matplotlib.use("Agg")

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------


@module.ui
def data_inventory_ui():
    return ui.navset_card_tab(
        ui.nav_panel(
            "Summary",
            _summary_tab_content(),
        ),
        ui.nav_panel(
            "Geographic Coverage",
            ui.card(
                ui.card_header("Area Contribution"),
                ui.output_plot("plot_area_bar", height="620px"),
            ),
            ui.card(ui.card_header("Coverage Gap Hints"), ui.output_ui("gap_hints_ui")),
        ),
    )


def _summary_tab_content():
    return ui.TagList(
        ui.tags.style("""
            .inventory-summary-grid {
                display: grid;
                grid-template-columns: repeat(6, minmax(7.25rem, 1fr));
                gap: 0.65rem;
                margin-bottom: 0.8rem;
            }
            .inventory-summary-card {
                min-width: 0;
                min-height: 72px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                gap: 0.18rem;
                padding: 0.72rem 0.82rem;
                border: 1px solid var(--ccn-serc-line, #d7e0e7);
                border-left: 4px solid var(--inventory-summary-accent, #006c6f);
                border-radius: 8px;
                background: #ffffff;
            }
            .inventory-summary-label {
                color: var(--ccn-serc-muted, #657385);
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0;
                line-height: 1.15;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .inventory-summary-value {
                color: var(--ccn-serc-ink, #17212b);
                font-size: 1.28rem;
                font-weight: 750;
                line-height: 1.1;
                overflow-wrap: anywhere;
            }
            .inventory-summary-card--teal {
                --inventory-summary-accent: var(--ccn-serc-teal, #006c6f);
            }
            .inventory-summary-card--navy {
                --inventory-summary-accent: var(--ccn-serc-navy, #002c5f);
            }
            .inventory-summary-card--gold {
                --inventory-summary-accent: var(--ccn-serc-gold, #c8912f);
            }
            @media (max-width: 1200px) {
                .inventory-summary-grid {
                    grid-template-columns: repeat(3, minmax(8rem, 1fr));
                }
            }
            @media (max-width: 760px) {
                .inventory-summary-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }
        """),
        ui.output_ui("inventory_overview_cards"),
        ui.layout_columns(
            ui.card(
                ui.card_header("Synthesis Categories"),
                ui.output_plot("plot_category_dist", height="380px"),
            ),
            ui.card(
                ui.card_header("Top Studies by Synthesis Rows"),
                ui.output_plot("plot_study_counts", height="380px"),
            ),
            col_widths=[6, 6],
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header("SOM Distribution"),
                ui.output_plot("plot_som_hist", height="390px"),
            ),
            ui.card(
                ui.card_header("Bulk Density Distribution"),
                ui.output_plot("plot_bd_hist", height="390px"),
            ),
            col_widths=[6, 6],
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header("SOM vs Bulk Density"),
                ui.output_plot("plot_som_bd_scatter", height="470px"),
            ),
            ui.card(
                ui.card_header("Correlation Heatmap"),
                ui.output_plot("plot_corr_heatmap", height="470px"),
            ),
            col_widths=[6, 6],
        ),
        ui.card(
            ui.card_header("Density Contours (Eligible Studies)"),
            ui.output_plot("plot_kde", height="520px"),
        ),
    )


def _inventory_metric(label: str, value: str, accent: str):
    return ui.div(
        ui.div(label, class_="inventory-summary-label"),
        ui.div(value, class_="inventory-summary-value"),
        class_=f"inventory-summary-card inventory-summary-card--{accent}",
    )


def _clean_label_series(series: pd.Series) -> pd.Series:
    clean = series.dropna().astype(str).str.strip()
    return clean[clean != ""]


def _synthesis_category_info(synthesis: pd.DataFrame) -> tuple[str, pd.Series]:
    for column, label in (
        ("habitat", "Habitat Categories"),
        ("category", "Synthesis Categories"),
        ("som_source", "Measurement Categories"),
    ):
        if column not in synthesis.columns:
            continue
        values = _clean_label_series(synthesis[column])
        if not values.empty:
            return label, values
    return "Synthesis Categories", pd.Series(dtype="object")


def _synthesis_study_counts(synthesis: pd.DataFrame, limit: int) -> pd.Series:
    if "source_study" not in synthesis.columns:
        return pd.Series(dtype="int64")
    return _clean_label_series(synthesis["source_study"]).value_counts().head(limit)


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------


@module.server
def data_inventory_server(_module_input, _output, _session):
    initial_inventory = build_inventory_df()
    inventory_df: reactive.Value[pd.DataFrame | None] = reactive.Value(initial_inventory)
    synthesis_df: reactive.Value[pd.DataFrame | None] = reactive.Value(build_synthesis_df(initial_inventory))

    # ---- Inventory + synthesis summary cards -------------------------------

    @render.ui
    def inventory_overview_cards():
        inv = inventory_df.get()
        if inv is None:
            return ui.p(
                "Loading synthesis inventory...",
                class_="text-muted p-3",
            )
        sdf = synthesis_df.get()
        category_count = "0"
        synthesis_rows = "0"
        study_sources = "0"
        som_mean = "N/A"
        bd_mean = "N/A"
        if sdf is not None and not sdf.empty:
            _, category_values = _synthesis_category_info(sdf)
            category_count = _format_count(category_values.nunique())
            synthesis_rows = _format_count(len(sdf))
            study_sources = _format_count(sdf["source_study"].nunique())
            if not sdf["som"].isna().all():
                som_mean = f"{sdf['som'].mean():.2f}"
            if not sdf["bulk_density"].isna().all():
                bd_mean = f"{sdf['bulk_density'].mean():.2f}"
        return ui.div(
            _inventory_metric("Synthesis Files", _format_count(len(inv)), "teal"),
            _inventory_metric("Categories", category_count, "navy"),
            _inventory_metric(
                "Synthesis Rows",
                synthesis_rows,
                "teal",
            ),
            _inventory_metric(
                "Study Sources",
                study_sources,
                "navy",
            ),
            _inventory_metric("Mean SOM", som_mean, "gold"),
            _inventory_metric("Mean BD", bd_mean, "gold"),
            class_="inventory-summary-grid",
        )

    # ---- Synthesis count plots --------------------------------------------

    @render.plot
    def plot_category_dist():
        sdf = synthesis_df.get()
        if sdf is None or sdf.empty:
            return _empty_fig()
        category_label, category_values = _synthesis_category_info(sdf)
        if category_values.empty:
            return _message_fig("No synthesis categories found")
        counts = _top_counts(category_values, limit=12, other_label="Other categories")
        return _horizontal_count_plot(
            counts,
            title=f"{category_label} by Synthesis Rows",
            xlabel="Synthesis rows",
            label_width=24,
            palette="viridis",
        )

    @render.plot
    def plot_study_counts():
        sdf = synthesis_df.get()
        if sdf is None or sdf.empty:
            return _empty_fig()
        counts = _synthesis_study_counts(sdf, limit=12)
        if counts.empty:
            return _message_fig("No synthesis study identifiers found")
        return _horizontal_count_plot(
            counts,
            title="Top Studies by Synthesis Rows",
            xlabel="Synthesis rows",
            label_width=30,
            palette="mako",
        )

    # ---- Synthesis plots --------------------------------------------------

    @render.plot
    def plot_som_hist():
        sdf = synthesis_df.get()
        if sdf is None or sdf.empty:
            return _empty_fig()
        return _numeric_histogram(
            sdf["som"],
            title="SOM Distribution (Central 99%)",
            xlabel="SOM / Fraction Carbon",
            color="#118ab2",
        )

    @render.plot
    def plot_bd_hist():
        sdf = synthesis_df.get()
        if sdf is None or sdf.empty:
            return _empty_fig()
        return _numeric_histogram(
            sdf["bulk_density"],
            title="Bulk Density Distribution (Central 99%)",
            xlabel="Bulk Density",
            color="#2a9d8f",
        )

    @render.plot
    def plot_som_bd_scatter():
        sdf = synthesis_df.get()
        if sdf is None or sdf.empty:
            return _empty_fig()
        subset = _central_xy(sdf, "bulk_density", "som")
        shown = subset.sample(n=12000, random_state=7) if len(subset) > 12000 else subset
        fig, ax = plt.subplots(figsize=(9, 5))
        sns.scatterplot(
            data=shown,
            x="bulk_density",
            y="som",
            color="#1f77b4",
            alpha=0.28,
            s=14,
            edgecolor=None,
            ax=ax,
        )
        ax.set_title("SOM vs Bulk Density (Central 99%)")
        ax.set_xlabel("Bulk Density")
        ax.set_ylabel("SOM / Fraction Carbon")
        ax.grid(True, alpha=0.3)
        ax.text(
            0.98,
            0.96,
            f"Showing {_format_count(len(shown))} of {_format_count(len(subset))} central records",
            ha="right",
            va="top",
            transform=ax.transAxes,
            fontsize=9,
            color="#555555",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 3},
        )
        fig.tight_layout()
        return fig

    @render.plot
    def plot_corr_heatmap():
        sdf = synthesis_df.get()
        if sdf is None or sdf.empty:
            return _empty_fig()
        corr = sdf[["som", "bulk_density"]].corr()
        fig, ax = plt.subplots(figsize=(4.8, 4))
        sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", ax=ax)
        ax.set_title("SOM vs Bulk Density Correlation")
        fig.tight_layout()
        return fig

    @render.plot
    def plot_kde():
        sdf = synthesis_df.get()
        if sdf is None or sdf.empty:
            return _empty_fig()
        eligible_studies = _eligible_density_studies(sdf, limit=6)
        if not eligible_studies:
            return _message_fig("No studies have enough paired SOM and bulk density records for density contours")
        subset = _central_xy(sdf[sdf["source_study"].isin(eligible_studies)], "bulk_density", "som")
        fig, ax = plt.subplots(figsize=(10, 5.5))
        try:
            sns.kdeplot(
                data=subset,
                x="bulk_density",
                y="som",
                hue="source_study",
                fill=False,
                levels=5,
                linewidths=1.3,
                common_norm=False,
                ax=ax,
            )
            ax.set_title(f"SOM vs Bulk Density Density Contours (Top {len(eligible_studies)} Eligible Studies)")
            sns.move_legend(ax, "upper left", bbox_to_anchor=(1.01, 1), title="Study", frameon=False)
        except (FloatingPointError, ValueError):
            ax.text(
                0.5,
                0.5,
                "Density contours could not be computed for the selected studies",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
        ax.set_xlabel("Bulk Density")
        ax.set_ylabel("SOM / Fraction Carbon")
        ax.set_xlim(max(0, subset["bulk_density"].min()), subset["bulk_density"].max())
        ax.set_ylim(max(0, subset["som"].min()), subset["som"].max())
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        return fig

    # ---- Geographic plots + hints -----------------------------------------

    @render.plot
    def plot_area_bar():
        sdf = synthesis_df.get()
        if sdf is None or sdf.empty:
            return _empty_fig()
        if "area" not in sdf.columns:
            return _message_fig("No area column found in synthesis data")
        area_counts = sdf["area"].value_counts().head(20)
        return _horizontal_count_plot(
            area_counts,
            title="Top Areas by Data Point Contribution",
            xlabel="Data points (log scale)",
            label_width=36,
            palette="crest",
            log_x=True,
        )

    @render.ui
    def gap_hints_ui():
        sdf = synthesis_df.get()
        if sdf is None:
            return ui.p("Synthesis inventory is loading.", class_="text-muted")
        hints = generate_gap_hints(sdf)
        alert_map = {
            "danger": "alert-danger",
            "warning": "alert-warning",
            "info": "alert-info",
        }
        tags = []
        for h in hints:
            css = alert_map.get(h["level"], "alert-secondary")
            tags.append(ui.div(h["text"], class_=f"alert {css}", role="alert"))
        return ui.TagList(*tags)

    # helpers
    def _format_count(value: int) -> str:
        return f"{value:,}"

    def _message_fig(message: str):
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        fig.tight_layout()
        return fig

    def _empty_fig():
        return _message_fig("No data loaded")

    def _top_counts(series: pd.Series, limit: int, other_label: str) -> pd.Series:
        counts = series.value_counts()
        if len(counts) <= limit:
            return counts
        top = counts.head(limit)
        other = pd.Series({other_label: counts.iloc[limit:].sum()})
        return pd.concat([top, other])

    def _display_labels(labels: pd.Index, width: int) -> list[str]:
        return [shorten(str(label).replace("_", " "), width=width, placeholder="...") for label in labels]

    def _horizontal_count_plot(
        counts: pd.Series,
        title: str,
        xlabel: str,
        label_width: int,
        palette: str,
        log_x: bool = False,
    ):
        counts = counts.sort_values(ascending=True)
        fig_height = max(5.2, 0.42 * len(counts) + 1.6)
        fig, ax = plt.subplots(figsize=(10, fig_height))
        labels = _display_labels(counts.index, label_width)
        values = counts.to_numpy(dtype=float)
        colors = sns.color_palette(palette, n_colors=len(counts))
        bars = ax.barh(labels, values, color=colors)
        if values.size:
            right_edge = values.max() * (1.22 if log_x else 1.14)
            if log_x:
                positive_values = values[values > 0]
                left_edge = positive_values.min() * 0.75 if positive_values.size else 0.1
                ax.set_xlim(left=left_edge, right=right_edge)
            else:
                ax.set_xlim(left=0, right=right_edge)
        if log_x:
            ax.set_xscale("log")
        ax.bar_label(
            bars,
            labels=[_format_count(int(value)) for value in values],
            padding=4,
            fontsize=9,
        )
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("")
        ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        ax.grid(True, axis="x", alpha=0.25)
        ax.margins(y=0.08)
        sns.despine(ax=ax, left=True, bottom=False)
        fig.subplots_adjust(left=0.34, right=0.92, top=0.86, bottom=0.19)
        return fig

    def _central_series(series: pd.Series, lower: float = 0.005, upper: float = 0.995) -> pd.Series:
        clean = series.dropna()
        if clean.empty or clean.nunique() < 3:
            return clean
        low, high = clean.quantile([lower, upper])
        if pd.isna(low) or pd.isna(high) or low == high:
            return clean
        return clean[(clean >= low) & (clean <= high)]

    def _numeric_histogram(series: pd.Series, title: str, xlabel: str, color: str):
        clean = _central_series(series)
        if clean.empty:
            return _message_fig("No numeric data available")
        fig, ax = plt.subplots(figsize=(10, 4.6))
        sns.histplot(
            x=clean,
            bins=40,
            kde=True,
            color=color,
            edgecolor="white",
            linewidth=0.5,
            ax=ax,
        )
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Records")
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        ax.grid(True, axis="y", alpha=0.25)
        sns.despine(ax=ax)
        fig.subplots_adjust(left=0.18, right=0.97, top=0.84, bottom=0.18)
        return fig

    def _central_xy(df: pd.DataFrame, x_col: str, y_col: str) -> pd.DataFrame:
        subset = df[[x_col, y_col, "source_study"]].dropna()
        if subset.empty:
            return subset
        x = _central_series(subset[x_col])
        y = _central_series(subset[y_col])
        return subset[subset[x_col].between(x.min(), x.max()) & subset[y_col].between(y.min(), y.max())]

    def _eligible_density_studies(df: pd.DataFrame, limit: int) -> list[str]:
        eligible = []
        for study in df["source_study"].value_counts().index:
            subset = df.loc[df["source_study"] == study, ["bulk_density", "som"]].dropna()
            if len(subset) >= 30 and subset["bulk_density"].nunique() >= 3 and subset["som"].nunique() >= 3:
                eligible.append(study)
            if len(eligible) == limit:
                break
        return eligible
