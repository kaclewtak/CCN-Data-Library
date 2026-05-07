from __future__ import annotations

from shiny import module, ui

ComparisonFigure = tuple[str, str, str, str]
ComparisonGroup = tuple[str, str, str, list[ComparisonFigure]]

COMPARISON_GROUPS: list[ComparisonGroup] = [
    (
        "Within-study prediction runs",
        "side-by-side",
        "The within-study runs uses the pre-filter feature matrices: 720 rows across 37 studies "
        "for the reduced clean run and 1,440 rows across 72 studies for the expanded run. Best "
        "within-study R^2 drops from +0.150 to +0.115, showing broader coverage with weaker held-out-study signal.",
        [
            (
                "Reduced clean",
                "carbon_modeling_clean_01_within-study-diagnostic.png",
                "Reduced within-study diagnostic",
                "RF strong is the best within-study model here, with overall R^2 = +0.332, "
                "within-study R^2 = +0.150, within r = +0.394, and 88.9% empirical coverage.",
            ),
            (
                "Expanded",
                "carbon_modeling_01_block-a-data-download-feature-engineering-within-study-modeling.png",
                "Expanded within-study diagnostic",
                "The stacked ensemble becomes the best within-study model, with overall R^2 = +0.201, "
                "within-study R^2 = +0.115, within r = +0.363, and 89.7% empirical coverage.",
            ),
        ],
    ),
    (
        "Model zoo",
        "side-by-side",
        "The clean run includes NOAA tidal features in its later model-zoo matrix, giving 30 features and stronger model-zoo "
        "scores. The expanded run has no NOAA cache in the saved output, so it falls back to 20 features "
        "and loses both overall and within-study skill.",
        [
            (
                "Reduced clean",
                "carbon_modeling_clean_02_model-zoo.png",
                "Reduced model zoo",
                "ExtraTrees leads with within-study R^2 = +0.234 and overall R^2 = +0.374. "
                "Removing tidal features hurts, and adding tidal to a spectral baseline improves within-study R^2 by +0.295.",
            ),
            (
                "Expanded",
                "carbon_modeling_02_block-d-comprehensive-model-zoo-feature-attribution.png",
                "Expanded model zoo",
                "ExtraTrees still leads, but drops to within-study R^2 = +0.138 and overall R^2 = +0.270. "
                "The notebook explicitly skips the tidal test because the NOAA cache is absent.",
            ),
        ],
    ),
    (
        "RF sweep and feature effects",
        "side-by-side",
        "The same model-family diagnostics are easier to compare side-by-side because these panels are less wide. "
        "The reduced run has stronger RF sweep scores, while both runs show that non-spectral context features are needed.",
        [
            (
                "Reduced clean",
                "carbon_modeling_clean_03_rf-sweep-feature-attribution.png",
                "Reduced RF and feature attribution",
                "The best RF sweep setting is unrestricted depth with leaf=1, reaching within-study R^2 = +0.211 "
                "and overall R^2 = +0.351. Tidal, environment, water, and cyclone groups all improve on spectral-only features.",
            ),
            (
                "Expanded",
                "carbon_modeling_03_block-d-comprehensive-model-zoo-feature-attribution.png",
                "Expanded RF and feature attribution",
                "The best RF sweep setting is depth=12 and leaf=5, reaching within-study R^2 = +0.125 "
                "and overall R^2 = +0.233. Water, climate, vegetation, cyclone, and terrain signals still recur.",
            ),
        ],
    ),
    (
        "ExtraTrees tuning and per-study skill",
        "side-by-side",
        "The tuned ExtraTrees model is the clearest reduced-versus-expanded skill drop: within-study R^2 falls "
        "from +0.252 to +0.142, and median per-study Pearson r falls from +0.494 to +0.248. The clean notebook also "
        "has a separate tidal sub-ablation plot that the expanded notebook skips.",
        [
            (
                "Reduced clean",
                "carbon_modeling_clean_04_extratrees-tuning.png",
                "Reduced ExtraTrees tuning",
                "The best run uses 1,200 trees, leaf=1, and max_features=0.75. It reaches within-study R^2 = +0.252, "
                "overall R^2 = +0.382, and within r = +0.503.",
            ),
            (
                "Expanded",
                "carbon_modeling_04_block-e-extratrees-tuning-per-study-breakdown-tidal-sub-ablation.png",
                "Expanded ExtraTrees tuning",
                "The best run uses 1,200 trees, leaf=2, and max_features=sqrt. It reaches within-study R^2 = +0.142, "
                "overall R^2 = +0.274, and within r = +0.387.",
            ),
            (
                "Reduced clean only",
                "carbon_modeling_clean_05_per-study-breakdown-tidal-ablation.png",
                "Reduced per-study and tidal sub-ablation",
                "The clean output reports 31 studies with median per-study r = +0.494 and shows greedy tidal selection "
                "raising spectral-only within-study R^2 from -0.104 to +0.171 before stopping.",
            ),
        ],
    ),
    (
        "Fraction carbon versus organic matter",
        "side-by-side",
        "This sanity-check figure is identical in the clean and expanded notebooks because it uses the same paired "
        "depthseries measurements. It supports the same interpretation in both runs.",
        [
            (
                "Shared clean and expanded output",
                "carbon_modeling_clean_06_fraction-carbon-vs-organic-matter.png",
                "Fraction carbon versus organic matter",
                "Across 11,998 C-OM pairs, Pearson r is +0.923 and the through-zero slope is 0.463. "
                "That aligns with the Craft mangrove reference range of roughly 0.40-0.50.",
            ),
        ],
    ),
    (
        "Data quality and bias diagnostics",
        "side-by-side",
        "The expanded diagnostics cover 1,432 filtered cores instead of 676. The dry-bulk-density sanity check remains "
        "strong in both runs, but shallow-core error becomes more pronounced in the expanded output.",
        [
            (
                "Reduced clean",
                "carbon_modeling_clean_07_data-quality-bias-diagnostics.png",
                "Reduced quality diagnostics",
                "The reduced run has 660 cores with DBD, Pearson r(DBD, C) = -0.713, no high-density high-carbon flags, "
                "and similar MAE for shallow and deeper cores.",
            ),
            (
                "Expanded",
                "carbon_modeling_07_data-quality-bias-diagnostics-find-the-next-rock-removal-issue.png",
                "Expanded quality diagnostics",
                "The expanded run has 1,389 cores with DBD, Pearson r(DBD, C) = -0.668, one high-density high-carbon flag, "
                "and MAE 0.099 on cores with less than 15 cm coverage.",
            ),
        ],
    ),
    (
        "Isotonic recalibration",
        "side-by-side",
        "The reduced run benefits more from isotonic recalibration than the expanded run. Both land near nominal "
        "90% conformal coverage, but the expanded calibration barely changes MAE.",
        [
            (
                "Reduced clean",
                "carbon_modeling_clean_08_isotonic-calibration.png",
                "Reduced isotonic calibration",
                "OOF isotonic calibration improves overall R^2 from +0.390 to +0.398, within-study R^2 from +0.254 "
                "to +0.255, and MAE from 0.0711 to 0.0685.",
            ),
            (
                "Expanded",
                "carbon_modeling_08_isotonic-recalibration-of-loso-predictions.png",
                "Expanded isotonic calibration",
                "OOF isotonic calibration moves overall R^2 from +0.263 to +0.249, within-study R^2 from +0.106 "
                "to +0.110, and MAE only from 0.0674 to 0.0672.",
            ),
        ],
    ),
    (
        "Calibration-method shootout",
        "side-by-side",
        "The best calibrator changes with scope. The reduced run favors per-tier isotonic calibration, while the "
        "expanded run favors a simpler linear stretch and keeps nearly the same MAE.",
        [
            (
                "Reduced clean",
                "carbon_modeling_clean_09_calibration-shootout.png",
                "Reduced calibration shootout",
                "Per-tier isotonic is best, with overall R^2 = +0.407, within-study R^2 = +0.256, "
                "MAE = 0.0673, median absolute error = 0.048, and 51.2% within +/-0.05.",
            ),
            (
                "Expanded",
                "carbon_modeling_09_recalibration-shootout-three-oof-approaches.png",
                "Expanded calibration shootout",
                "Linear stretch is best, with overall R^2 = +0.262, within-study R^2 = +0.124, "
                "MAE = 0.0670, median absolute error = 0.050, and 49.4% within +/-0.05.",
            ),
        ],
    ),
    (
        "Habitat-stratified models",
        "side-by-side",
        "The habitat split changes in opposite directions. Marsh gains many more cores but loses within-study skill, "
        "while mangrove remains small and improves from negative to positive within-study R^2.",
        [
            (
                "Reduced clean",
                "carbon_modeling_clean_10_habitat-stratified.png",
                "Reduced habitat models",
                "Marsh has 437 cores across 14 studies and calibrated within-study R^2 = +0.344. "
                "Mangrove has 103 cores across 11 studies and remains negative at within-study R^2 = -0.104.",
            ),
            (
                "Expanded",
                "carbon_modeling_10_habitat-stratified-models-marsh-vs-mangrove.png",
                "Expanded habitat models",
                "Marsh grows to 1,042 cores across 47 studies but drops to within-study R^2 = +0.169. "
                "Mangrove has 87 cores across 10 studies and improves to within-study R^2 = +0.052.",
            ),
        ],
    ),
    (
        "Pooled feature importance by habitat",
        "side-by-side",
        "The importance story shifts with the expanded scope. Reduced marsh importance centers on precipitation, "
        "inundation, and NDVI, while expanded marsh importance emphasizes cyclone and SWIR signals.",
        [
            (
                "Reduced clean",
                "carbon_modeling_clean_11_pooled-feature-importance.png",
                "Reduced pooled feature importance",
                "Reduced marsh top predictors are precipitation, inundation frequency, NDVI peak greenness, cyclone wind, "
                "and SWIR. Reduced mangrove is led by temperature, inundation observations, SAR VH, elevation, and precipitation.",
            ),
            (
                "Expanded",
                "carbon_modeling_11_feature-importance-bar-plot-pooled-model.png",
                "Expanded pooled feature importance",
                "Expanded marsh is led by cyclone wind, SWIR, temperature, storm count, and NDVI peak greenness. "
                "Expanded mangrove is led by temperature, elevation, EMIT cellulose, inundation observations, and EMIT organic-C.",
            ),
        ],
    ),
    (
        "Per-study top-feature small multiples",
        "side-by-side",
        "Both notebooks show that feature rankings vary by study. The small multiples are paired side-by-side because "
        "their aspect ratios are moderate enough for visual comparison on desktop.",
        [
            (
                "Reduced clean",
                "carbon_modeling_clean_12_per-study-feature-small-multiples.png",
                "Reduced per-study features",
                "The reduced small multiples include 12 studies and show study-specific reliance on the same broad water, climate, "
                "vegetation, and storm feature families.",
            ),
            (
                "Expanded",
                "carbon_modeling_12_feature-importance-bar-plot-pooled-model.png",
                "Expanded per-study features",
                "The expanded small multiples also include 12 studies, but the top-ranked features shift enough that one global "
                "importance story should be treated cautiously.",
            ),
        ],
    ),
    (
        "Marsh feature importance",
        "side-by-side",
        "The marsh-only bars make the predictor shift especially visible: precipitation and inundation lead in the reduced "
        "scope, while cyclone wind and SWIR become dominant in the expanded scope.",
        [
            (
                "Reduced clean",
                "carbon_modeling_clean_13_marsh-feature-importance.png",
                "Reduced marsh feature importance",
                "The reduced marsh run trains on 443 cores. Its top five predictors are precipitation, inundation frequency, "
                "NDVI peak greenness, cyclone wind, and SWIR reflectance.",
            ),
            (
                "Expanded",
                "carbon_modeling_13_feature-importance-bar-plots-one-per-habitat.png",
                "Expanded marsh feature importance",
                "The expanded marsh run trains on 1,053 cores. Its top five predictors are cyclone wind, SWIR reflectance, "
                "temperature, number of historical cyclones, and NDVI peak greenness.",
            ),
        ],
    ),
    (
        "Mangrove feature importance",
        "side-by-side",
        "The mangrove model remains small in both notebooks, so these feature rankings are useful signals but should be "
        "read with more caution than the marsh rankings.",
        [
            (
                "Reduced clean",
                "carbon_modeling_clean_14_mangrove-feature-importance.png",
                "Reduced mangrove feature importance",
                "The reduced mangrove run trains on 106 cores. Its top predictors are temperature, inundation observation count, "
                "SAR VH, elevation, and precipitation.",
            ),
            (
                "Expanded",
                "carbon_modeling_14_feature-importance-bar-plots-one-per-habitat.png",
                "Expanded mangrove feature importance",
                "The expanded mangrove run trains on 92 cores. Its top predictors are temperature, elevation, EMIT cellulose, "
                "inundation observation count, and EMIT organic-C absorption.",
            ),
        ],
    ),
    (
        "Original versus expanded summary",
        "side-by-side",
        "This expanded-notebook panel summarizes the global OOF-isotonic F.2 headline comparison directly: "
        "more filtered cores and studies, weaker aggregate skill, nearly unchanged MAE, and a mangrove model "
        "that improves from negative to positive skill.",
        [
            (
                "Expanded comparison panel",
                "carbon_modeling_15_original-vs-expanded-modeling-comparison.png",
                "Side-by-side summary from the expanded notebook",
                "The filtered cohort grows from 676 to 1,432 cores and from 33 to 70 studies. Using the global "
                "OOF-isotonic headline, pooled within-study R^2 drops from +0.255 to +0.110, while MAE improves "
                "slightly from 0.0685 to 0.0672.",
            ),
        ],
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


def figure_card(run_label: str, file_name: str, title: str, description: str):
    return ui.card(
        ui.tags.img(
            src=f"/images/{file_name}",
            alt=title,
            loading="lazy",
            class_="carbon-modeling-figure-img",
        ),
        ui.div(
            ui.div(run_label, class_="carbon-modeling-run-label"),
            ui.div(title, class_="carbon-modeling-figure-title"),
            ui.p(description, class_="carbon-modeling-figure-description"),
            class_="carbon-modeling-figure-caption",
        ),
        class_="carbon-modeling-figure-card",
    )


def comparison_group(title: str, layout: str, description: str, figures: list[ComparisonFigure]):
    return ui.div(
        ui.div(
            ui.h4(title, class_="carbon-modeling-comparison-title"),
            ui.p(description, class_="carbon-modeling-comparison-description"),
            class_="carbon-modeling-comparison-header",
        ),
        ui.div(
            *[figure_card(*figure) for figure in figures],
            class_=f"carbon-modeling-figure-pair carbon-modeling-figure-pair--{layout}",
        ),
        class_="carbon-modeling-comparison-group",
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
                max-width: 1040px;
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
                margin: 0;
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
            .carbon-modeling-comparison-list {
                display: flex;
                flex-direction: column;
                gap: 18px;
            }
            .carbon-modeling-comparison-group {
                display: flex;
                flex-direction: column;
                gap: 10px;
                padding-top: 14px;
                border-top: 1px solid var(--ccn-serc-line);
            }
            .carbon-modeling-comparison-header {
                display: grid;
                grid-template-columns: minmax(190px, 0.34fr) minmax(300px, 1fr);
                gap: 14px;
                align-items: start;
            }
            .carbon-modeling-comparison-title {
                margin: 0;
                color: #18324a;
                font-size: 0.98rem;
                font-weight: 800;
                line-height: 1.25;
            }
            .carbon-modeling-comparison-description {
                margin: 0;
                color: #4f5f70;
                font-size: 0.85rem;
                line-height: 1.45;
            }
            .carbon-modeling-figure-pair {
                display: grid;
                gap: 12px;
                align-items: start;
            }
            .carbon-modeling-figure-pair--side-by-side {
                grid-template-columns: repeat(auto-fit, minmax(540px, 1fr));
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
                min-height: 132px;
                padding: 11px 12px 12px;
                color: #344054;
                line-height: 1.3;
            }
            .carbon-modeling-run-label {
                display: inline-flex;
                width: fit-content;
                margin-bottom: 7px;
                padding: 2px 7px;
                border: 1px solid #b7d9d0;
                border-radius: 999px;
                color: #23685e;
                background: #eef8f5;
                font-size: 0.68rem;
                font-weight: 800;
                letter-spacing: 0;
                text-transform: uppercase;
            }
            .carbon-modeling-figure-title {
                color: #24364a;
                font-size: 0.86rem;
                font-weight: 800;
                line-height: 1.28;
            }
            .carbon-modeling-figure-description {
                margin: 6px 0 0;
                color: #526273;
                font-size: 0.8rem;
                font-weight: 500;
                line-height: 1.42;
            }
            @media (max-width: 1040px) {
                .carbon-modeling-metric-grid {
                    grid-template-columns: repeat(2, minmax(220px, 1fr));
                }
                .carbon-modeling-comparison-header,
                .carbon-modeling-figure-pair--side-by-side {
                    grid-template-columns: 1fr;
                }
            }
            @media (max-width: 700px) {
                .carbon-modeling-metric-grid {
                    grid-template-columns: 1fr;
                }
                .carbon-modeling-metric-value {
                    font-size: 1.28rem;
                }
                .carbon-modeling-figure-caption {
                    min-height: unset;
                }
            }
            """),
        ui.p(
            "Side-by-side comparison of the clean reduced modeling notebook and the expanded North American run.",
            class_="carbon-modeling-lede",
        ),
        ui.div(
            _metric_card(
                "Reduced clean cohort",
                "676 cores",
                "Filtered headline cohort: 33 studies; pre-filter matrix: 720 rows/37 studies",
            ),
            _metric_card(
                "Expanded cohort",
                "1,432 cores",
                "Filtered headline cohort: 70 studies; pre-filter matrix: 1,440 rows/72 studies",
            ),
            _metric_card(
                "Within-study skill tradeoff",
                "-0.146 R^2",
                "delta in within-study R^2; overall R^2 changes from +0.398 to +0.249; MAE 0.0685 to 0.0672",
                "gold",
            ),
            _metric_card(
                "Operational caution",
                "Stock weak",
                "Direct SOC stock R^2 -0.215 to +0.031; two-stage stock models remain weak",
                "red",
            ),
            class_="carbon-modeling-metric-grid",
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header("High-Level Findings"),
                ui.tags.ul(
                    _finding(
                        "Reduced is smaller but stronger.",
                        "The clean run uses 676 filtered cores and reaches calibrated pooled within-study R^2 = +0.255. "
                        "The expanded run grows to 1,432 filtered cores but drops to within-study R^2 = +0.110.",
                    ),
                    _finding(
                        "The expansion mainly buys coverage.",
                        "The expanded run adds 756 filtered cores and 37 studies. Overall MAE is nearly unchanged "
                        "(0.0685 to 0.0672), but aggregate validation skill weakens.",
                    ),
                    _finding(
                        "Habitat effects move in opposite directions.",
                        "Marsh grows from 437 to 1,042 calibrated cores, but within-study R^2 falls from +0.344 to +0.169. "
                        "Mangrove stays small and improves from -0.104 to +0.052.",
                    ),
                    _finding(
                        "SOC stock remains a weak prediction product.",
                        "The SOC stock target stays much weaker than fraction carbon. Direct calibrated stock R^2 moves from "
                        "-0.215 to +0.031, and the best two-stage stock variants remain weak.",
                    ),
                    class_="carbon-modeling-finding-list",
                ),
            ),
            ui.card(
                ui.card_header("Feature And Data Quality Signals"),
                ui.tags.ul(
                    _finding(
                        "ExtraTrees remains the strongest model family.",
                        "It leads both model zoos, but reduced within-study R^2 = +0.234 is notably stronger than expanded "
                        "within-study R^2 = +0.138 before tuning.",
                    ),
                    _finding(
                        "Calibration changes with scope.",
                        "The reduced run favors per-tier isotonic calibration; the expanded run favors linear stretch. "
                        "Both keep MAE near 0.067.",
                    ),
                    _finding(
                        "Physical QA is stable.",
                        "The C-vs-OM relationship is unchanged across notebooks, and DBD remains strongly negative with carbon "
                        "in both reduced and expanded diagnostics.",
                    ),
                    _finding(
                        "Feature rankings shift with geography.",
                        "Reduced marsh emphasizes precipitation, inundation, and NDVI; expanded marsh emphasizes cyclone wind, "
                        "SWIR, and temperature. Mangrove remains more sample-limited in both runs.",
                    ),
                    class_="carbon-modeling-finding-list",
                ),
            ),
            col_widths=[6, 6],
        ),
        ui.div(
            ui.h3("Notebook Figure Comparisons", class_="carbon-modeling-figure-section-title"),
            ui.p(
                "Each group pairs the clean reduced output with the comparable expanded output when both exist. "
                "Descriptions summarize the relevant printed notebook findings.",
                class_="carbon-modeling-section-note",
            ),
            ui.div(
                *[comparison_group(*group) for group in COMPARISON_GROUPS],
                class_="carbon-modeling-comparison-list",
            ),
        ),
        class_="carbon-modeling-page",
    )
