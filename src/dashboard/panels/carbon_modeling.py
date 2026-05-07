from __future__ import annotations

from shiny import module, ui

FIGURES = [
    (
        "carbon_modeling_01_block-a-data-download-feature-engineering-within-study-modeling.png",
        "Modeled cohort and engineered EO feature space",
    ),
    (
        "carbon_modeling_02_block-d-comprehensive-model-zoo-feature-attribution.png",
        "Expanded model zoo results",
    ),
    (
        "carbon_modeling_03_block-d-comprehensive-model-zoo-feature-attribution.png",
        "Feature-group attribution and add-back diagnostics",
    ),
    (
        "carbon_modeling_04_block-e-extratrees-tuning-per-study-breakdown-tidal-sub-ablation.png",
        "ExtraTrees hyperparameter tuning",
    ),
    (
        "carbon_modeling_05_block-e-extratrees-tuning-per-study-breakdown-tidal-sub-ablation.png",
        "Per-study skill and tidal sub-ablation",
    ),
    (
        "carbon_modeling_06_sanity-check-fraction-carbon-vs-fraction-organic-matter.png",
        "Fraction carbon versus organic matter sanity check",
    ),
    (
        "carbon_modeling_07_data-quality-bias-diagnostics-find-the-next-rock-removal-issue.png",
        "Data-quality and residual-bias diagnostics",
    ),
    (
        "carbon_modeling_08_isotonic-recalibration-of-loso-predictions.png",
        "Isotonic recalibration diagnostics",
    ),
    (
        "carbon_modeling_09_recalibration-shootout-three-oof-approaches.png",
        "Calibration-method comparison",
    ),
    (
        "carbon_modeling_10_habitat-stratified-models-marsh-vs-mangrove.png",
        "Habitat-stratified model comparison",
    ),
    (
        "carbon_modeling_11_feature-importance-bar-plot-pooled-model.png",
        "Pooled feature importance by habitat",
    ),
    (
        "carbon_modeling_12_feature-importance-bar-plot-pooled-model.png",
        "Per-study top feature small multiples",
    ),
    (
        "carbon_modeling_13_feature-importance-bar-plots-one-per-habitat.png",
        "Marsh feature-importance bars",
    ),
    (
        "carbon_modeling_14_feature-importance-bar-plots-one-per-habitat.png",
        "Mangrove feature-importance bars",
    ),
]


# Helper functions
def _metric_card(label: str, value: str, detail: str, tone: str = "teal"):
    return ui.div(
        ui.div(label, class_="carbon-modeling-metric-label"),
        ui.div(value, class_="carbon-modeling-metric-value"),
        ui.div(detail, class_="carbon-modeling-metric-detail"),
        class_=f"carbon-modeling-metric carbon-modeling-metric-{tone}",
    )


def _finding(title: str, body: str):
    return ui.tags.li(
        ui.tags.strong(title),
        ui.span(f" {body}"),
        class_="carbon-modeling-finding",
    )


def _figure_card(file_name: str, caption: str):
    return ui.card(
        ui.tags.img(
            src=f"/images/{file_name}",
            alt=caption,
            loading="lazy",
            class_="carbon-modeling-figure-img",
        ),
        ui.div(caption, class_="carbon-modeling-figure-caption"),
        class_="carbon-modeling-figure-card",
    )


@module.ui
def carbon_modeling_ui():
    return ui.div(
        ui.tags.style("""
            .carbon-modeling-page {
                display: flex;
                flex-direction: column;
                gap: 14px;
                padding: 0.5rem 0 1.5rem;
            }
            .carbon-modeling-lede {
                margin: 0;
                max-width: 980px;
                color: var(--ccn-serc-muted);
                font-size: 0.94rem;
                line-height: 1.48;
            }
            .carbon-modeling-metric-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(160px, 1fr));
                gap: 10px;
            }
            .carbon-modeling-metric {
                min-height: 112px;
                padding: 14px 16px;
                border: 1px solid var(--ccn-serc-line);
                border-top: 4px solid var(--ccn-serc-teal);
                border-radius: 8px;
                background: #ffffff;
            }
            .carbon-modeling-metric-gold {
                border-top-color: var(--ccn-serc-gold);
            }
            .carbon-modeling-metric-red {
                border-top-color: #b94a48;
            }
            .carbon-modeling-metric-label {
                color: var(--ccn-serc-muted);
                font-size: 0.76rem;
                font-weight: 750;
                text-transform: uppercase;
            }
            .carbon-modeling-metric-value {
                margin-top: 8px;
                color: #18324a;
                font-size: 1.48rem;
                font-weight: 800;
                line-height: 1.1;
            }
            .carbon-modeling-metric-detail {
                margin-top: 7px;
                color: #526273;
                font-size: 0.82rem;
                line-height: 1.35;
            }
            .carbon-modeling-finding-list {
                margin: 0;
                padding-left: 1.1rem;
            }
            .carbon-modeling-finding {
                margin: 0.5rem 0;
                color: #263545;
                line-height: 1.45;
            }
            .carbon-modeling-section-note {
                color: var(--ccn-serc-muted);
                font-size: 0.88rem;
                line-height: 1.45;
            }
            .carbon-modeling-figure-section-title {
                margin: 4px 0 0;
                color: #18324a;
                font-size: 1.08rem;
                font-weight: 800;
                line-height: 1.2;
            }
            .carbon-modeling-figure-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(280px, 1fr));
                gap: 12px;
            }
            .carbon-modeling-figure-card {
                overflow: hidden;
            }
            .carbon-modeling-figure-img {
                display: block;
                width: 100%;
                height: auto;
                border-bottom: 1px solid var(--ccn-serc-line);
                background: #ffffff;
            }
            .carbon-modeling-figure-caption {
                min-height: 42px;
                padding: 10px 12px;
                color: #344054;
                font-size: 0.84rem;
                font-weight: 700;
                line-height: 1.3;
            }
            @media (max-width: 1040px) {
                .carbon-modeling-metric-grid,
                .carbon-modeling-figure-grid {
                    grid-template-columns: repeat(2, minmax(220px, 1fr));
                }
            }
            @media (max-width: 700px) {
                .carbon-modeling-metric-grid,
                .carbon-modeling-figure-grid {
                    grid-template-columns: 1fr;
                }
                .carbon-modeling-metric-value {
                    font-size: 1.28rem;
                }
            }
            """),
        ui.p(
            "Summary of the Modeling Notebook. We display " "the produced figures and report-ready findings.",
            class_="carbon-modeling-lede",
        ),
        ui.div(
            _metric_card("Pooled cohort", "676 cores", "33 studies after the rock-screening pass"),
            _metric_card(
                "Calibrated pooled model",
                "+0.406 R^2",
                "overall R^2; within-study R^2 = +0.256",
            ),
            _metric_card(
                "Typical fraction-carbon error",
                "MAE 0.067",
                "median absolute error = 0.048",
            ),
            _metric_card(
                "Operational caution",
                "SOC stock weak",
                "single-stage stock R^2 = -0.215",
                "red",
            ),
            class_="carbon-modeling-metric-grid",
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header("High-Level Findings"),
                ui.tags.ul(
                    _finding(
                        "Fraction carbon is the defendable target.",
                        "The calibrated pooled ExtraTrees workflow predicts 0-30 cm fraction_carbon with moderate "
                        "leave-one-study-out skill: overall R^2 = +0.406, within-study R^2 = +0.256, MAE = 0.067, "
                        "and 51.2% of predictions within +/-0.05 fraction_carbon.",
                    ),
                    _finding(
                        "Study-level validation matters.",
                        "On the N>=10 cohort, median per-study Pearson r was +0.530 and 69% of studies had r > 0.3, "
                        "showing useful skill only when small-study noise is separated from the reportable subset.",
                    ),
                    _finding(
                        "Calibration improves usability, not the whole tail problem.",
                        "Per-tier isotonic calibration produced the best balance among tested calibrators: MAE = 0.0673, "
                        "median absolute error = 0.0483, and 89.1% empirical coverage for nominal 90% intervals.",
                    ),
                    _finding(
                        "Habitat-specific signal is uneven.",
                        "Marsh-only modeling improved within-study structure (within R^2 = +0.344, within r = +0.587), "
                        "while mangrove-only modeling remained underpowered and unstable with 103 cores across 11 studies.",
                    ),
                    _finding(
                        "SOC stock is not ready as a prediction product.",
                        "Direct SOC stock prediction was worse than fraction_carbon, with calibrated overall R^2 = -0.215 "
                        "and MAE = 39.2 Mg C/ha; the two-stage C x DBD approach was worse still after calibration.",
                    ),
                    class_="carbon-modeling-finding-list",
                ),
            ),
            ui.card(
                ui.card_header("Feature And Data Quality Signals"),
                ui.tags.ul(
                    _finding(
                        "ExtraTrees was the strongest model family.",
                        "The tuned ExtraTrees run reached within-study R^2 = +0.252 before filtering and calibration, "
                        "outperforming random forests, gradient boosting variants, linear models, and KNN in the model zoo.",
                    ),
                    _finding(
                        "Water, climate, vegetation, and terrain signals recur.",
                        "Top marsh predictors included mean annual precipitation, inundation frequency, NDVI peak greenness, "
                        "cyclone wind, and SWIR reflectance; top mangrove predictors included temperature, inundation observations, "
                        "SAR VH, elevation, and precipitation.",
                    ),
                    _finding(
                        "Rock screening is useful QA but not a skill cure.",
                        "The C-vs-OM check flagged 44 suspicious high-C, low-OM cores and 72 C>OM violations; removing the "
                        "suspicious cores barely changed within-study R^2 (+0.2520 to +0.2537).",
                    ),
                    _finding(
                        "Regression to the mean remains the main error pattern.",
                        "Low-carbon deciles were over-predicted and high-carbon deciles were under-predicted; calibration reduced "
                        "central errors but did not fully correct the high-carbon tail.",
                    ),
                    class_="carbon-modeling-finding-list",
                ),
            ),
            col_widths=[6, 6],
        ),
        ui.div(
            ui.h3("Copied Notebook Figures", class_="carbon-modeling-figure-section-title"),
            ui.p(
                "These figures are copied from the saved notebook outputs into the dashboard images folder.",
                class_="carbon-modeling-section-note",
            ),
            ui.div(
                *[_figure_card(file_name, caption) for file_name, caption in FIGURES],
                class_="carbon-modeling-figure-grid",
            ),
        ),
        class_="carbon-modeling-page",
    )
