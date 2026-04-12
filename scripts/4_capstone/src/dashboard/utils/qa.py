"""QA utilities: reference data loading, column matching, validation, charts, map."""

from __future__ import annotations

import os
from pathlib import Path

import folium
import folium.plugins
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

QA_NUMERIC_COLS = {
    "dry_bulk_density": {"unit": "g/cm\u00b3", "synonyms": {"dbd", "bulk_density", "dry_density", "bulk_dens"}},
    "fraction_carbon": {
        "unit": "fraction",
        "synonyms": {"frac_c", "oc_fraction", "carbon_fraction", "foc", "organic_carbon"},
    },
    "fraction_organic_matter": {
        "unit": "fraction",
        "synonyms": {"frac_om", "om_fraction", "loi", "organic_matter", "loss_on_ignition"},
    },
    "depth_min": {"unit": "cm", "synonyms": {"depth_top", "top_depth", "min_depth", "upper_depth"}},
    "depth_max": {"unit": "cm", "synonyms": {"depth_bottom", "bottom_depth", "max_depth", "lower_depth"}},
}

QA_GEO_COLS = {
    "latitude": {"synonyms": {"lat", "y", "core_latitude", "site_latitude"}},
    "longitude": {"synonyms": {"lon", "lng", "long", "x", "core_longitude", "site_longitude"}},
}

QA_ID_COLS = {
    "study_id": {"synonyms": {"study", "study_name", "studyid"}},
    "site_id": {"synonyms": {"site", "site_name", "siteid", "location"}},
    "core_id": {"synonyms": {"core", "core_name", "coreid", "sample", "sample_id"}},
}

ALL_CANONICAL = {**QA_NUMERIC_COLS, **QA_GEO_COLS, **QA_ID_COLS}

VARIABLE_CHOICES = {"__all__": "All Variables (overview)"}
VARIABLE_CHOICES.update({k: f"{k}  ({v['unit']})" for k, v in QA_NUMERIC_COLS.items()})

POINT_CLOUD_MAX = 6000
MAX_REF_MAP_POINTS = 8000

# ---------------------------------------------------------------------------
# Reference data — lazy singleton
# ---------------------------------------------------------------------------

_ref_cache: dict | None = None


def _find_data_dir() -> Path:
    """Hunt for the CCN_synthesis folder."""
    env = os.environ.get("CCN_DATA_DIR")
    if env and Path(env).is_dir():
        return Path(env)

    app_dir = Path(__file__).resolve().parent.parent  # dashboard/
    candidates = [
        # Walk up to the repo root (CCN-Data-Library)
        app_dir.parents[3] / "data" / "CCN_synthesis",
        app_dir.parents[2] / "data" / "CCN_synthesis",
        app_dir.parent / "data" / "CCN_synthesis",
        app_dir / "data" / "CCN_synthesis",
        Path.cwd() / "data" / "CCN_synthesis",
        Path.cwd().parent / "data" / "CCN_synthesis",
    ]
    for c in candidates:
        if (c / "CCN_depthseries.csv").exists():
            return c
    raise FileNotFoundError(
        "Cannot find data/CCN_synthesis/CCN_depthseries.csv. "
        "Run from the CCN-Data-Library-main directory, or set CCN_DATA_DIR."
    )


def load_reference_data() -> dict:
    """Load (and cache) the CCN reference data on first call.

    Returns a dict with keys: ref_merged, ref_cores_valid, habitat_choices.
    """
    global _ref_cache
    if _ref_cache is not None:
        return _ref_cache

    data_dir = _find_data_dir()

    ds_cols = [
        "study_id",
        "site_id",
        "core_id",
        "depth_min",
        "depth_max",
        "dry_bulk_density",
        "fraction_organic_matter",
        "fraction_carbon",
    ]
    core_cols = [
        "study_id",
        "site_id",
        "core_id",
        "latitude",
        "longitude",
        "habitat",
        "vegetation_class",
        "salinity_class",
    ]

    print(f"[QA] Loading reference data from {data_dir} ...")
    ref_ds = pd.read_csv(
        data_dir / "CCN_depthseries.csv",
        usecols=ds_cols,
        na_values=["NA", "N/A", ""],
        low_memory=False,
    )
    ref_cores = pd.read_csv(
        data_dir / "CCN_cores.csv",
        usecols=core_cols,
        na_values=["NA", "N/A", ""],
        low_memory=False,
    )

    for c in ["depth_min", "depth_max", "dry_bulk_density", "fraction_organic_matter", "fraction_carbon"]:
        ref_ds[c] = pd.to_numeric(ref_ds[c], errors="coerce")
    for c in ["latitude", "longitude"]:
        ref_cores[c] = pd.to_numeric(ref_cores[c], errors="coerce")

    ref_merged = ref_ds.merge(
        ref_cores[["study_id", "site_id", "core_id", "habitat"]],
        on=["study_id", "site_id", "core_id"],
        how="left",
    )
    ref_cores_valid = ref_cores.dropna(subset=["latitude", "longitude"])
    habitat_choices = sorted(ref_cores["habitat"].dropna().unique().tolist())

    print(
        f"[QA] Loaded: {len(ref_ds):,} depthseries rows, "
        f"{len(ref_cores):,} cores, {len(habitat_choices)} habitat types."
    )

    _ref_cache = {
        "ref_merged": ref_merged,
        "ref_cores_valid": ref_cores_valid,
        "habitat_choices": habitat_choices,
    }
    return _ref_cache


# ---------------------------------------------------------------------------
# Column auto-matching
# ---------------------------------------------------------------------------


def _normalize(name: str) -> str:
    n = "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")
    while "__" in n:
        n = n.replace("__", "_")
    return n


def _tokenize(name: str) -> set[str]:
    return {t for t in _normalize(name).split("_") if t}


def auto_match_columns(user_columns: list[str]) -> dict[str, str | None]:
    """Score each user column against each canonical CCN column.

    Returns {canonical_name: best_matching_user_column_or_None}.
    """
    matches: dict[str, str | None] = {}
    used: set[str] = set()

    for canonical, info in ALL_CANONICAL.items():
        best_col: str | None = None
        best_score = 0
        synonyms = info.get("synonyms", set())
        canon_norm = _normalize(canonical)
        canon_tokens = _tokenize(canonical)

        for ucol in user_columns:
            if ucol in used:
                continue
            u_norm = _normalize(ucol)
            u_tokens = _tokenize(ucol)
            score = 0

            if u_norm == canon_norm:
                score = 10
            elif u_norm in synonyms:
                score = 8
            elif u_tokens & canon_tokens:
                overlap = len(u_tokens & canon_tokens)
                score = 3 + overlap
            else:
                for syn in synonyms:
                    if _normalize(syn) == u_norm:
                        score = 8
                        break
                    if _tokenize(syn) & u_tokens:
                        score = 4
                        break

            if score > best_score:
                best_score = score
                best_col = ucol

        if best_score >= 3 and best_col is not None:
            matches[canonical] = best_col
            used.add(best_col)
        else:
            matches[canonical] = None

    return matches


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def run_validation(df: pd.DataFrame, col_map: dict[str, str | None]) -> pd.DataFrame:
    """Run all validation rules against user data.

    Returns a DataFrame with columns: Row, Column, Value, Issue.
    """
    warnings: list[dict] = []

    def _get(canonical: str) -> str | None:
        c = col_map.get(canonical)
        return c if c and c in df.columns else None

    def _flag(row_idx: int, col: str, value, issue: str):
        warnings.append({"Row": row_idx + 1, "Column": col, "Value": value, "Issue": issue})

    range_rules: list[tuple[str, float | None, float | None, str]] = [
        ("fraction_carbon", 0.0, 1.0, "Must be 0\u20131 (fraction, not percent)"),
        ("fraction_organic_matter", 0.0, 1.0, "Must be 0\u20131 (fraction, not percent)"),
        ("dry_bulk_density", 0.0, 2.65, "Must be > 0 and \u2264 2.65 g/cm\u00b3"),
        ("depth_min", 0.0, None, "Must be \u2265 0"),
        ("depth_max", 0.0, None, "Must be \u2265 0"),
        ("latitude", -90.0, 90.0, "Must be \u201390 to 90"),
        ("longitude", -180.0, 180.0, "Must be \u2013180 to 180"),
    ]

    for canonical, lo, hi, desc in range_rules:
        ucol = _get(canonical)
        if ucol is None:
            continue
        vals = pd.to_numeric(df[ucol], errors="coerce")
        for idx in range(len(df)):
            v = vals.iloc[idx]
            if pd.isna(v):
                continue
            if lo is not None and v < lo:
                _flag(idx, ucol, df[ucol].iloc[idx], desc)
            elif hi is not None and v > hi:
                _flag(idx, ucol, df[ucol].iloc[idx], desc)

    # Cross-column: depth_max must be > depth_min
    dmin_col = _get("depth_min")
    dmax_col = _get("depth_max")
    if dmin_col and dmax_col:
        dmin = pd.to_numeric(df[dmin_col], errors="coerce")
        dmax = pd.to_numeric(df[dmax_col], errors="coerce")
        for idx in range(len(df)):
            if pd.notna(dmin.iloc[idx]) and pd.notna(dmax.iloc[idx]):
                if dmax.iloc[idx] <= dmin.iloc[idx]:
                    _flag(
                        idx,
                        dmax_col,
                        df[dmax_col].iloc[idx],
                        f"depth_max must be > depth_min ({df[dmin_col].iloc[idx]})",
                    )

    # Cross-column: carbon can't exceed organic matter
    fc_col = _get("fraction_carbon")
    fom_col = _get("fraction_organic_matter")
    if fc_col and fom_col:
        fc = pd.to_numeric(df[fc_col], errors="coerce")
        fom = pd.to_numeric(df[fom_col], errors="coerce")
        for idx in range(len(df)):
            if pd.notna(fc.iloc[idx]) and pd.notna(fom.iloc[idx]):
                if fc.iloc[idx] > fom.iloc[idx]:
                    _flag(idx, fc_col, df[fc_col].iloc[idx], "fraction_carbon should be \u2264 fraction_organic_matter")

    # Non-numeric values in columns that should be numbers
    for canonical in list(QA_NUMERIC_COLS) + list(QA_GEO_COLS):
        ucol = _get(canonical)
        if ucol is None:
            continue
        for idx in range(len(df)):
            raw = df[ucol].iloc[idx]
            if pd.isna(raw) or str(raw).strip() == "":
                continue
            try:
                float(raw)
            except (ValueError, TypeError):
                _flag(idx, ucol, raw, f"Non-numeric value in {ucol}")

    return pd.DataFrame(warnings) if warnings else pd.DataFrame(columns=["Row", "Column", "Value", "Issue"])


def matched_numeric_variables(
    user_df: pd.DataFrame | None,
    col_map: dict[str, str | None],
) -> list[dict[str, str]]:
    """Return matched numeric QA variables in canonical display order."""
    if user_df is None:
        return []

    matches: list[dict[str, str]] = []
    for variable, info in QA_NUMERIC_COLS.items():
        user_column = col_map.get(variable)
        if user_column and user_column in user_df.columns:
            matches.append(
                {
                    "variable": variable,
                    "user_column": user_column,
                    "unit": info["unit"],
                }
            )
    return matches


def compare_user_to_reference(
    user_values: pd.Series,
    ref_values: pd.Series,
    test_name: str = "ks",
) -> dict[str, float | int | str | None]:
    """Compare a user series to the CCN reference series."""
    user_clean = pd.to_numeric(user_values, errors="coerce").dropna()
    ref_clean = pd.to_numeric(ref_values, errors="coerce").dropna()

    result: dict[str, float | int | str | None] = {
        "test": test_name,
        "n_user": len(user_clean),
        "n_ref": len(ref_clean),
        "statistic": None,
        "p_value": None,
        "interpretation": "Insufficient data for comparison.",
    }
    if len(user_clean) < 2 or len(ref_clean) < 2:
        return result

    if test_name == "anderson":
        try:
            comparison = stats.anderson_ksamp([user_clean.values, ref_clean.values])
            statistic = comparison.statistic
            p_value = comparison.pvalue
        except ValueError as exc:
            result["interpretation"] = f"Test failed: {exc}"
            return result
    else:
        statistic, p_value = stats.ks_2samp(user_clean, ref_clean)

    if p_value < 0.01:
        interpretation = "Distributions are significantly different (p < 0.01)."
    elif p_value < 0.05:
        interpretation = "Distributions differ at the 5% significance level."
    else:
        interpretation = "No significant difference detected between distributions."

    result.update(
        {
            "statistic": round(float(statistic), 4),
            "p_value": round(float(p_value), 4),
            "interpretation": interpretation,
        }
    )
    return result


def build_comparison_results(
    ref_merged: pd.DataFrame,
    user_df: pd.DataFrame | None,
    col_map: dict[str, str | None],
    habitats: list[str] | None = None,
    variable: str = "__all__",
    test_name: str = "ks",
) -> list[dict[str, float | int | str | None]]:
    """Build statistical comparison rows for the matched QA variables."""
    matches = matched_numeric_variables(user_df, col_map)
    if user_df is None or not matches:
        return []

    ref = ref_merged.copy()
    if habitats:
        ref = ref[ref["habitat"].isin(habitats)]

    selected_variables = [variable] if variable != "__all__" else [match["variable"] for match in matches]
    results: list[dict[str, float | int | str | None]] = []
    for selected in selected_variables:
        user_column = col_map.get(selected)
        if user_column is None or user_column not in user_df.columns or selected not in ref.columns:
            continue

        comparison = compare_user_to_reference(user_df[user_column], ref[selected], test_name=test_name)
        comparison.update(
            {
                "variable": selected,
                "user_column": user_column,
                "unit": QA_NUMERIC_COLS.get(selected, {}).get("unit", ""),
            }
        )
        results.append(comparison)

    return results


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------


def _user_hover_texts(
    user_series: pd.Series,
    user_df: pd.DataFrame | None,
    col_map: dict[str, str | None],
) -> list[str]:
    texts: list[str] = []
    for idx, val in user_series.items():
        parts = [f"<b>Value: {val:.4f}</b>", f"Row: {int(idx) + 1}"]
        if user_df is not None and col_map:
            for id_col in ("study_id", "site_id", "core_id"):
                mapped = col_map.get(id_col)
                if mapped and mapped in user_df.columns:
                    id_val = user_df[mapped].iloc[int(idx)]
                    if pd.notna(id_val):
                        parts.append(f"{id_col}: {id_val}")
        texts.append("<br>".join(parts))
    return texts


def _user_distribution_trace(
    user_values: pd.Series,
    chart_type: str,
    *,
    name: str,
    hover_text: list[str] | None = None,
    showlegend: bool = True,
    category_label: str | None = None,
):
    if chart_type == "Point Cloud":
        user_y = np.linspace(0.52, 0.68, len(user_values)) if len(user_values) > 1 else [0.6]
        return go.Scattergl(
            x=user_values.values,
            y=user_y,
            mode="markers",
            marker=dict(symbol="diamond-dot", size=5, color="#E74C3C", line=dict(color="black", width=1.2)),
            name=name,
            hovertemplate="%{text}<extra></extra>",
            text=hover_text or [],
            showlegend=showlegend,
        )

    if chart_type == "Histogram + Strip":
        return go.Histogram(
            x=user_values,
            nbinsx=80,
            histnorm="probability density",
            marker_color="rgba(231, 76, 60, 0.35)",
            name=name,
            hovertemplate="Bin: %{x:.4f}<br>Density: %{y:.4f}<extra></extra>",
            showlegend=showlegend,
        )

    if chart_type == "Violin + Strip":
        y_values = [category_label] * len(user_values) if category_label is not None else None
        return go.Violin(
            x=user_values,
            y=y_values,
            orientation="h",
            line_color="#E74C3C",
            fillcolor="rgba(231, 76, 60, 0.25)",
            name=name,
            side="both",
            meanline_visible=True,
            hoveron="kde",
            hoverinfo="x",
            points=False,
            showlegend=showlegend,
        )

    return go.Box(
        x=user_values,
        line_color="#E74C3C",
        fillcolor="rgba(231, 76, 60, 0.2)",
        marker_color="#E74C3C",
        name=name,
        boxmean=True,
        boxpoints=False,
        showlegend=showlegend,
    )


def build_qa_chart(
    ref_values: pd.Series,
    user_values: pd.Series | None,
    variable_name: str,
    unit: str,
    chart_type: str,
    user_df: pd.DataFrame | None = None,
    col_map: dict[str, str | None] | None = None,
    ref_habitat: pd.Series | None = None,
    ref_study_id: pd.Series | None = None,
) -> str:
    """Build a single-variable QA chart. Returns plotly HTML string."""
    fig = go.Figure()
    ref_clean = ref_values.dropna()

    if len(ref_clean) == 0:
        fig.add_annotation(
            text="No reference data for this variable.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=16),
        )
        return fig.to_html(full_html=False, include_plotlyjs=False)

    p5, p95 = float(np.nanpercentile(ref_clean, 5)), float(np.nanpercentile(ref_clean, 95))
    fig.add_vrect(
        x0=p5,
        x1=p95,
        fillcolor="#4C72B0",
        opacity=0.08,
        line_width=0,
        annotation_text="5th-95th pctl",
        annotation_position="top left",
        annotation_font_size=10,
        annotation_font_color="#4C72B0",
    )

    n_ref = len(ref_clean)

    if chart_type == "Point Cloud":
        rng = np.random.default_rng(42)
        if n_ref > POINT_CLOUD_MAX:
            sample_idx = rng.choice(ref_clean.index, POINT_CLOUD_MAX, replace=False)
            rc = ref_clean.loc[sample_idx]
            rh = ref_habitat.loc[sample_idx] if ref_habitat is not None else None
            rs = ref_study_id.loc[sample_idx] if ref_study_id is not None else None
            sample_note = f" (showing {POINT_CLOUD_MAX:,}/{n_ref:,})"
        else:
            rc = ref_clean
            rh = ref_habitat
            rs = ref_study_id
            sample_note = ""

        y_jitter = rng.uniform(-0.4, 0.4, len(rc))

        if rh is not None and rh.notna().any():
            for hab in sorted(rh.dropna().unique()):
                mask = (rh == hab).values
                hover_parts = []
                for xi, si in zip(rc[mask].values, (rs[mask] if rs is not None else [None] * mask.sum())):
                    parts = [f"<b>{variable_name}: {xi:.4f}</b>", f"Habitat: {hab}"]
                    if si is not None and pd.notna(si):
                        parts.append(f"Study: {si}")
                    hover_parts.append("<br>".join(parts))
                fig.add_trace(
                    go.Scattergl(
                        x=rc[mask].values,
                        y=y_jitter[mask],
                        mode="markers",
                        marker=dict(size=4, opacity=0.6),
                        name=hab,
                        hovertemplate="%{text}<extra></extra>",
                        text=hover_parts,
                    )
                )
        else:
            fig.add_trace(
                go.Scattergl(
                    x=rc.values,
                    y=y_jitter,
                    mode="markers",
                    marker=dict(size=4, color="rgba(76, 114, 176, 0.5)"),
                    name=f"CCN Reference{sample_note}",
                    hovertemplate=f"<b>{variable_name}: %{{x:.4f}}</b><extra></extra>",
                )
            )

    elif chart_type == "Histogram + Strip":
        fig.add_trace(
            go.Histogram(
                x=ref_clean,
                nbinsx=80,
                histnorm="probability density",
                marker_color="rgba(76, 114, 176, 0.35)",
                name=f"CCN Reference (n={n_ref:,})",
                hovertemplate="Bin: %{x:.4f}<br>Density: %{y:.4f}<extra></extra>",
            )
        )

    elif chart_type == "Violin + Strip":
        fig.add_trace(
            go.Violin(
                x=ref_clean,
                y=[variable_name] * len(ref_clean),
                orientation="h",
                line_color="#4C72B0",
                fillcolor="rgba(76, 114, 176, 0.25)",
                name=f"CCN Reference (n={n_ref:,})",
                side="both",
                meanline_visible=True,
                hoveron="kde",
                hoverinfo="x",
                points=False,
            )
        )

    elif chart_type == "Box + Strip":
        fig.add_trace(
            go.Box(
                x=ref_clean,
                marker_color="#4C72B0",
                fillcolor="rgba(76, 114, 176, 0.25)",
                name=f"CCN Reference (n={n_ref:,})",
                boxmean=True,
                boxpoints=False,
            )
        )

    ref_med = float(ref_clean.median())
    fig.add_vline(
        x=ref_med,
        line_dash="dash",
        line_color="#4C72B0",
        line_width=1.5,
        annotation_text=f"CCN median: {ref_med:.4g}",
        annotation_font_color="#4C72B0",
        annotation_font_size=10,
    )

    if user_values is not None:
        user_clean = pd.to_numeric(user_values, errors="coerce").dropna()
        if len(user_clean) > 0:
            hover = _user_hover_texts(user_clean, user_df, col_map or {})
            fig.add_trace(
                _user_distribution_trace(
                    user_clean,
                    chart_type,
                    name=f"Your Data (n={len(user_clean)})",
                    hover_text=hover,
                    category_label=variable_name,
                )
            )
            user_med = float(user_clean.median())
            fig.add_vline(
                x=user_med,
                line_dash="dash",
                line_color="#E74C3C",
                line_width=1.5,
                annotation_text=f"Your median: {user_med:.4g}",
                annotation_font_color="#E74C3C",
                annotation_font_size=10,
                annotation_position="bottom right",
            )

    is_cloud = chart_type == "Point Cloud"
    layout_updates = {}
    if chart_type == "Histogram + Strip":
        layout_updates["barmode"] = "overlay"
    elif chart_type == "Violin + Strip":
        layout_updates["violinmode"] = "overlay"
    elif chart_type == "Box + Strip":
        layout_updates["boxmode"] = "overlay"

    fig.update_layout(
        title=dict(text=f"QA Distribution: {variable_name}", font_size=15),
        xaxis_title=f"{variable_name} ({unit})",
        yaxis_title="" if is_cloud or chart_type == "Box + Strip" else "Density",
        yaxis=dict(showticklabels=not is_cloud, showgrid=not is_cloud),
        height=500 if is_cloud else 460,
        template="plotly_white",
        legend=dict(yanchor="top", y=0.98, xanchor="right", x=0.98, font_size=10),
        margin=dict(t=60, b=50),
        **layout_updates,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_stats_html(ref_values: pd.Series, user_values: pd.Series | None, variable_name: str) -> str:
    """Build an HTML stats comparison table."""
    ref_clean = ref_values.dropna()

    def _row(label: str, vals: pd.Series) -> str:
        if len(vals) == 0:
            return f"<tr><td>{label}</td>" + "<td>-</td>" * 6 + "</tr>"
        return (
            f"<tr><td><b>{label}</b></td>"
            f"<td>{len(vals):,}</td>"
            f"<td>{vals.mean():.4f}</td>"
            f"<td>{vals.median():.4f}</td>"
            f"<td>{vals.std():.4f}</td>"
            f"<td>{vals.min():.4f}</td>"
            f"<td>{vals.max():.4f}</td></tr>"
        )

    html = (
        f'<table class="table table-sm table-bordered" style="font-size:0.85em">'
        f"<thead><tr><th>{variable_name}</th><th>n</th><th>Mean</th>"
        f"<th>Median</th><th>Std</th><th>Min</th><th>Max</th></tr></thead><tbody>"
    )
    html += _row("CCN Reference", ref_clean)
    if user_values is not None:
        user_clean = pd.to_numeric(user_values, errors="coerce").dropna()
        html += _row("Your Data", user_clean)
    html += "</tbody></table>"
    return html


def build_overview_grid(
    ref_merged: pd.DataFrame,
    user_df: pd.DataFrame | None,
    col_map: dict[str, str | None],
    habitats: list[str],
    chart_type: str = "Histogram + Strip",
) -> str:
    """Build a 2x3 subplot grid showing all QA variables at once."""
    ref = ref_merged.copy()
    if habitats:
        ref = ref[ref["habitat"].isin(habitats)]

    grid_type = chart_type

    variables = list(QA_NUMERIC_COLS.keys())
    n = len(variables)
    n_cols = 3
    n_rows = (n + n_cols - 1) // n_cols

    fig = make_subplots(
        rows=n_rows,
        cols=n_cols,
        subplot_titles=[f"{v} ({QA_NUMERIC_COLS[v]['unit']})" for v in variables],
        horizontal_spacing=0.08,
        vertical_spacing=0.12,
    )

    for i, var in enumerate(variables):
        r = i // n_cols + 1
        c = i % n_cols + 1
        ref_vals = pd.to_numeric(ref.get(var, pd.Series(dtype=float)), errors="coerce").dropna()

        if len(ref_vals) > 0:
            if grid_type == "Point Cloud":
                rng = np.random.default_rng(42 + i)
                ref_sample = ref_vals
                if len(ref_sample) > POINT_CLOUD_MAX:
                    sample_idx = rng.choice(ref_sample.index, POINT_CLOUD_MAX, replace=False)
                    ref_sample = ref_sample.loc[sample_idx]
                fig.add_trace(
                    go.Scattergl(
                        x=ref_sample.values,
                        y=rng.uniform(-0.35, 0.35, len(ref_sample)),
                        mode="markers",
                        marker=dict(size=4, color="rgba(76, 114, 176, 0.6)"),
                        name=var,
                        showlegend=False,
                        hovertemplate=f"<b>{var}: %{{x:.4f}}</b><extra></extra>",
                    ),
                    row=r,
                    col=c,
                )
            elif grid_type == "Histogram + Strip":
                fig.add_trace(
                    go.Histogram(
                        x=ref_vals,
                        nbinsx=60,
                        histnorm="probability density",
                        marker_color="rgba(76, 114, 176, 0.35)",
                        name=var,
                        showlegend=False,
                        hovertemplate=f"<b>{var}</b><br>Bin: %{{x:.4f}}<br>Density: %{{y:.4f}}<extra></extra>",
                    ),
                    row=r,
                    col=c,
                )
            elif grid_type == "Violin + Strip":
                fig.add_trace(
                    go.Violin(
                        x=ref_vals,
                        y=[var] * len(ref_vals),
                        orientation="h",
                        line_color="#4C72B0",
                        fillcolor="rgba(76, 114, 176, 0.25)",
                        name=var,
                        showlegend=False,
                        side="both",
                        meanline_visible=True,
                        hoveron="kde",
                        hoverinfo="x",
                        points=False,
                    ),
                    row=r,
                    col=c,
                )
            elif grid_type == "Box + Strip":
                fig.add_trace(
                    go.Box(
                        x=ref_vals,
                        marker_color="#4C72B0",
                        fillcolor="rgba(76, 114, 176, 0.25)",
                        name=var,
                        showlegend=False,
                        boxmean=True,
                        boxpoints=False,
                    ),
                    row=r,
                    col=c,
                )

        ucol = col_map.get(var) if col_map else None
        if user_df is not None and ucol and ucol in user_df.columns:
            user_vals = pd.to_numeric(user_df[ucol], errors="coerce").dropna()
            if len(user_vals) > 0:
                fig.add_trace(
                    _user_distribution_trace(
                        user_vals,
                        grid_type,
                        name="Your data",
                        showlegend=False,
                        hover_text=None,
                        category_label=var,
                    ),
                    row=r,
                    col=c,
                )

    title_suffix = ""
    layout_updates = {}
    if grid_type == "Point Cloud":
        fig.update_yaxes(showticklabels=False, showgrid=False)
    elif grid_type == "Histogram + Strip":
        layout_updates["barmode"] = "overlay"
    elif grid_type == "Violin + Strip":
        layout_updates["violinmode"] = "overlay"
    elif grid_type == "Box + Strip":
        layout_updates["boxmode"] = "overlay"

    fig.update_layout(
        height=340 * n_rows,
        title_text=f"CCN Reference Distributions vs Your Data{title_suffix}",
        template="plotly_white",
        showlegend=False,
        margin=dict(t=80, b=40),
        **layout_updates,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


# ---------------------------------------------------------------------------
# Folium QA map
# ---------------------------------------------------------------------------


def build_map_html(
    ref_cores: pd.DataFrame,
    user_df: pd.DataFrame | None,
    lat_col: str | None,
    lon_col: str | None,
    show_ref: bool,
    show_user: bool,
    habitat_filter: list[str],
) -> tuple[str, int, int]:
    """Build a folium map with reference cores (blue, clustered)
    and user data points (red, individual). Returns (html, ref_count, user_count)."""
    m = folium.Map(location=[20, -40], zoom_start=3, tiles="CartoDB positron")

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite",
        overlay=False,
    ).add_to(m)

    ref_count = 0
    user_count = 0

    if show_ref:
        ref = ref_cores.copy()
        if habitat_filter:
            ref = ref[ref["habitat"].isin(habitat_filter)]
        ref = ref.dropna(subset=["latitude", "longitude"])
        if len(ref) > MAX_REF_MAP_POINTS:
            ref = ref.sample(n=MAX_REF_MAP_POINTS, random_state=42)
        ref_count = len(ref)

        cluster = folium.plugins.MarkerCluster(name="CCN Reference Cores", show=True)
        for _, row in ref.iterrows():
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=3,
                color="#4C72B0",
                fill=True,
                fill_opacity=0.5,
                weight=1,
                popup=f"{row.get('study_id','')} / {row.get('core_id','')}<br>" f"Habitat: {row.get('habitat','-')}",
            ).add_to(cluster)
        cluster.add_to(m)

    if show_user and user_df is not None and lat_col and lon_col:
        user_group = folium.FeatureGroup(name="Your Data")
        for idx, row in user_df.iterrows():
            try:
                lat = float(row[lat_col])
                lon = float(row[lon_col])
            except (ValueError, TypeError):
                continue
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            folium.CircleMarker(
                location=[lat, lon],
                radius=7,
                color="#E74C3C",
                fill=True,
                fill_color="#E74C3C",
                fill_opacity=0.9,
                weight=2,
                popup=f"Your data row {idx + 1}",
            ).add_to(user_group)
            user_count += 1
        user_group.add_to(m)

    folium.LayerControl().add_to(m)

    return m._repr_html_(), ref_count, user_count
