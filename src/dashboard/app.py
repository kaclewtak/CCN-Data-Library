# ============================================================
# CCN Data Library — QA Dashboard
# ============================================================
#
# Hey Kacper! This is the QA dashboard for sanity-checking new
# field data against the existing CCN synthesis. The whole idea:
# load the CCN reference distributions once at startup, then let
# users upload (or hand-type) their new data and instantly see
# how it compares — outliers pop right out.
#
# THE BIG PICTURE:
#   1. On startup, we load ~117K depthseries rows and ~16K cores
#      from the CCN synthesis CSVs. These become the "reference."
#   2. The QA Charts tab shows those reference distributions
#      immediately — no upload needed. Users see the CCN world.
#   3. Users go to the Data Editor tab, upload their CSV (or
#      click "New Empty Table" to type values from scratch).
#   4. The app auto-detects which of their columns match CCN
#      schema names (e.g., "dbd" -> dry_bulk_density). It does
#      this with a token-based scoring system + synonym maps.
#   5. Their data points appear as red diamonds overlaid on the
#      blue CCN distributions. Outliers are immediately obvious.
#   6. The Validation panel auto-flags common mistakes (fractions
#      entered as percentages, negative densities, etc.).
#   7. The Map tab shows where their cores sit relative to the
#      existing CCN network.
#
# TECH STACK:
#   - Shiny for Python: the reactive web framework (like R Shiny
#     but in Python). Handles the UI, server, reactivity.
#   - Pandas: all data manipulation. User data is small so we
#     don't need Polars here (the main dashboard uses Polars).
#   - Plotly: interactive charts with hover tooltips. Way better
#     than static matplotlib for QA — you can hover any point
#     to see its exact value, study, core, etc.
#   - Folium: the map. Renders as static HTML but has clustering
#     and layer toggling. No need for ipyleaflet/shinywidgets.
#
# HOW SHINY WORKS (quick crash course, Kacper):
#   - The app has two halves: UI (what the user sees) and Server
#     (the logic that responds to user actions).
#   - reactive.Value: a box that holds data. When you .set() it,
#     anything that reads from it automatically re-runs.
#   - @reactive.calc: a derived value. It re-computes whenever
#     any reactive thing it reads changes. Like a spreadsheet
#     formula that updates itself.
#   - @reactive.effect: runs side effects when inputs change
#     (e.g., updating dropdown choices after a file upload).
#   - @render.ui / @render.data_frame: functions that produce
#     output for the browser. They re-run when their reactive
#     dependencies change.
#   - input.something(): reads a UI widget's current value.
#     Also creates a reactive dependency — if the user changes
#     that widget, anything reading it re-runs.
#
# SETUP (Anaconda PowerShell):
#   1. Open "Anaconda PowerShell Prompt"
#   2. cd C:\Users\user\Desktop\CCN-Data-Library-main
#   3. conda create -n qa_dashboard python=3.11 -y
#      conda activate qa_dashboard
#   4. pip install -r qa_dashboard\requirements.txt
#   5. shiny run qa_dashboard\app.py --launch-browser
#   6. Opens at http://localhost:8000  — Ctrl+C to stop.
# ============================================================

from __future__ import annotations

import os
from pathlib import Path

import folium
import folium.plugins
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from shiny import App, reactive, render, ui

# ============================================================
# 1. REFERENCE DATA LOADING
# ============================================================
# Kacper, this whole section runs ONCE when the app starts up.
# It's at module level (outside any function), so it executes
# during import. The data stays in memory for the entire session.
#
# We only load the columns we actually need (usecols) to keep
# memory reasonable — the full depthseries has 49 columns but
# we only care about ~8 for QA charts.
#
# The merge at the end attaches habitat labels from the cores
# table onto the depthseries rows, so we can color point clouds
# by habitat and let users filter distributions by ecosystem.
# ============================================================

def _find_data_dir() -> Path:
    """Hunt for the CCN_synthesis folder. Tries a few relative
    paths so the app works whether you run from the project root
    or from inside qa_dashboard/. You can also override with the
    CCN_DATA_DIR environment variable."""
    env = os.environ.get("CCN_DATA_DIR")
    if env and Path(env).is_dir():
        return Path(env)

    app_dir = Path(__file__).resolve().parent
    candidates = [
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


DATA_DIR = _find_data_dir()

# Only grab the columns we need for QA — keeps memory ~50-80MB
# instead of ~300MB if we loaded everything.
_DS_COLS = [
    "study_id", "site_id", "core_id",
    "depth_min", "depth_max",
    "dry_bulk_density", "fraction_organic_matter", "fraction_carbon",
]
_CORE_COLS = [
    "study_id", "site_id", "core_id",
    "latitude", "longitude",
    "habitat", "vegetation_class", "salinity_class",
]

print(f"[QA Dashboard] Loading reference data from {DATA_DIR} ...")

REF_DS = pd.read_csv(
    DATA_DIR / "CCN_depthseries.csv",
    usecols=_DS_COLS, na_values=["NA", "N/A", ""], low_memory=False,
)
REF_CORES = pd.read_csv(
    DATA_DIR / "CCN_cores.csv",
    usecols=_CORE_COLS, na_values=["NA", "N/A", ""], low_memory=False,
)

# Force numeric types — some values come in as strings because
# the CSVs use "NA" for missing (not empty cells).
for c in ["depth_min", "depth_max", "dry_bulk_density",
          "fraction_organic_matter", "fraction_carbon"]:
    REF_DS[c] = pd.to_numeric(REF_DS[c], errors="coerce")
for c in ["latitude", "longitude"]:
    REF_CORES[c] = pd.to_numeric(REF_CORES[c], errors="coerce")

# Join habitat onto depthseries so we can color charts by ecosystem.
# Left join means depthseries rows without a matching core keep NaN habitat.
REF_MERGED = REF_DS.merge(
    REF_CORES[["study_id", "site_id", "core_id", "habitat"]],
    on=["study_id", "site_id", "core_id"], how="left",
)
REF_CORES_VALID = REF_CORES.dropna(subset=["latitude", "longitude"])
HABITAT_CHOICES = sorted(REF_CORES["habitat"].dropna().unique().tolist())

print(
    f"[QA Dashboard] Loaded: {len(REF_DS):,} depthseries rows, "
    f"{len(REF_CORES):,} cores, {len(HABITAT_CHOICES)} habitat types."
)

# ============================================================
# 2. COLUMN AUTO-MATCHING UTILITIES
# ============================================================
# Kacper, this is the secret sauce for usability. When someone
# uploads a CSV with columns like "dbd" or "frac_c" or "LOI",
# we want to automatically figure out that those map to
# "dry_bulk_density", "fraction_carbon", "fraction_organic_matter".
#
# The approach: normalize column names (lowercase, strip special
# chars), tokenize them, then score each user column against each
# canonical CCN column name. Exact match = 10 points, synonym
# match = 8, token overlap = 3+. Highest score wins.
#
# This is adapted from the geo_utils.py find_lat_lon_columns()
# function in the main dashboard, but generalized to handle all
# CCN schema columns, not just lat/lon.
# ============================================================

# These are all the CCN columns we know how to QA-check.
# Each one has a unit (for chart labels) and a set of synonyms
# (alternative names people might use in their own CSVs).
QA_NUMERIC_COLS = {
    "dry_bulk_density": {"unit": "g/cm\u00b3", "synonyms": {"dbd", "bulk_density", "dry_density", "bulk_dens"}},
    "fraction_carbon": {"unit": "fraction", "synonyms": {"frac_c", "oc_fraction", "carbon_fraction", "foc", "organic_carbon"}},
    "fraction_organic_matter": {"unit": "fraction", "synonyms": {"frac_om", "om_fraction", "loi", "organic_matter", "loss_on_ignition"}},
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

# Merge them all into one dict for iteration
ALL_CANONICAL = {**{k: v for k, v in QA_NUMERIC_COLS.items()},
                 **{k: v for k, v in QA_GEO_COLS.items()},
                 **{k: v for k, v in QA_ID_COLS.items()}}


def _normalize(name: str) -> str:
    """Lowercase, replace non-alphanumeric with _, collapse doubles.
    'Core Latitude (WGS84)' -> 'core_latitude_wgs84'"""
    n = "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")
    while "__" in n:
        n = n.replace("__", "_")
    return n


def _tokenize(name: str) -> set[str]:
    """Split normalized name into a set of tokens.
    'core_latitude' -> {'core', 'latitude'}"""
    return {t for t in _normalize(name).split("_") if t}


def auto_match_columns(user_columns: list[str]) -> dict[str, str | None]:
    """Score each user column against each canonical CCN column.
    Returns {canonical_name: best_matching_user_column_or_None}.

    Scoring:
      - Exact normalized match:     10 pts  (e.g., "dry_bulk_density" == "dry_bulk_density")
      - Synonym match:               8 pts  (e.g., "dbd" matches dry_bulk_density)
      - Token overlap:            3+ pts  (e.g., "bulk_density_gcm3" shares tokens with dry_bulk_density)
      - Minimum threshold:           3 pts  (below this, no match)

    Once a user column is matched, it's removed from the pool so
    we don't double-assign (e.g., "lat" can't match both latitude
    and something else)."""
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


# ============================================================
# 3. VALIDATION UTILITIES
# ============================================================
# Kacper, this runs automatically every time user_data changes.
# It checks every cell against known physical/logical constraints
# and returns a DataFrame of warnings.
#
# The rules come straight from the R QA functions in
# scripts/1_data_formatting/qa_functions.R — things like
# fractionNotPercent(), testNumericCols(), etc. We're basically
# doing the same checks but live in the browser as you type.
# ============================================================

def run_validation(df: pd.DataFrame, col_map: dict[str, str | None]) -> pd.DataFrame:
    """Run all validation rules against user data.
    Returns a DataFrame with columns: Row, Column, Value, Issue."""
    warnings: list[dict] = []

    def _get(canonical: str) -> str | None:
        """Look up the user's actual column name for a canonical CCN name."""
        c = col_map.get(canonical)
        return c if c and c in df.columns else None

    def _flag(row_idx: int, col: str, value, issue: str):
        warnings.append({"Row": row_idx + 1, "Column": col, "Value": value, "Issue": issue})

    # ---- Per-column range checks ----
    # Each rule: (canonical_col, min_allowed, max_allowed, error_message)
    # None means "no bound on that side"
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

    # ---- Cross-column: depth_max must be > depth_min ----
    dmin_col = _get("depth_min")
    dmax_col = _get("depth_max")
    if dmin_col and dmax_col:
        dmin = pd.to_numeric(df[dmin_col], errors="coerce")
        dmax = pd.to_numeric(df[dmax_col], errors="coerce")
        for idx in range(len(df)):
            if pd.notna(dmin.iloc[idx]) and pd.notna(dmax.iloc[idx]):
                if dmax.iloc[idx] <= dmin.iloc[idx]:
                    _flag(idx, dmax_col, df[dmax_col].iloc[idx],
                          f"depth_max must be > depth_min ({df[dmin_col].iloc[idx]})")

    # ---- Cross-column: carbon can't exceed organic matter ----
    # (Carbon is a subset of organic matter, so this is a physics check)
    fc_col = _get("fraction_carbon")
    fom_col = _get("fraction_organic_matter")
    if fc_col and fom_col:
        fc = pd.to_numeric(df[fc_col], errors="coerce")
        fom = pd.to_numeric(df[fom_col], errors="coerce")
        for idx in range(len(df)):
            if pd.notna(fc.iloc[idx]) and pd.notna(fom.iloc[idx]):
                if fc.iloc[idx] > fom.iloc[idx]:
                    _flag(idx, fc_col, df[fc_col].iloc[idx],
                          "fraction_carbon should be \u2264 fraction_organic_matter")

    # ---- Non-numeric values in columns that should be numbers ----
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


# ============================================================
# 4. CHART UTILITIES  (plotly — interactive with hover)
# ============================================================
# Kacper, the charts are built with Plotly, which renders as
# interactive HTML. Users can hover any point/bar to see details,
# zoom, pan, lasso-select, etc.
#
# Key design choices:
#   - We load plotly.js ONCE in the page <head> (see app_ui),
#     then every chart uses include_plotlyjs=False so it just
#     emits a <div> + inline JS. This way chart type swapping
#     is instant — no re-downloading the 3MB plotly library.
#   - Point Cloud uses go.Scattergl (WebGL) for performance.
#     Regular go.Scatter would choke on 6000 points.
#   - User data is always red diamonds — stands out clearly
#     against the blue reference, and the diamond shape means
#     you can tell them apart even in monochrome.
# ============================================================

def _user_hover_texts(
    user_series: pd.Series,
    user_df: pd.DataFrame | None,
    col_map: dict[str, str | None],
) -> list[str]:
    """Build rich hover text for each user data point.
    Shows the value, row number, and any ID columns (study_id,
    site_id, core_id) if they exist in the user's data."""
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


# Cap reference points in Point Cloud mode so the browser
# doesn't melt. 6000 WebGL points render smoothly; 100K would not.
POINT_CLOUD_MAX = 6000


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
    """Build a single-variable QA chart. Returns plotly HTML string.

    This is the main chart builder. It handles all 4 chart types:
      - Histogram + Strip: classic binned distribution
      - Point Cloud: every data point as a dot, colored by habitat
      - Violin + Strip: KDE-shaped density outline
      - Box + Strip: box-and-whisker summary

    In all modes, user data appears as red diamond markers.
    The 5th-95th percentile band and median lines give context."""
    fig = go.Figure()
    ref_clean = ref_values.dropna()

    if len(ref_clean) == 0:
        fig.add_annotation(text="No reference data for this variable.",
                           x=0.5, y=0.5, xref="paper", yref="paper",
                           showarrow=False, font=dict(size=16))
        return fig.to_html(full_html=False, include_plotlyjs=False)

    # ---- 5th-95th percentile band ----
    # This shaded region shows where 90% of CCN values fall.
    # Points outside this band are unusual (not necessarily wrong).
    p5, p95 = float(np.nanpercentile(ref_clean, 5)), float(np.nanpercentile(ref_clean, 95))
    fig.add_vrect(x0=p5, x1=p95, fillcolor="#4C72B0", opacity=0.08, line_width=0,
                  annotation_text="5th-95th pctl", annotation_position="top left",
                  annotation_font_size=10, annotation_font_color="#4C72B0")

    n_ref = len(ref_clean)

    # ---- Point Cloud: individual dots colored by habitat ----
    # Kacper, this is the pretty one. Each CCN data point is a dot
    # with slight y-jitter so they spread into a cloud. Color = habitat.
    # Uses Scattergl (WebGL) so the browser can handle thousands of points.
    if chart_type == "Point Cloud":
        rng = np.random.default_rng(42)
        # Sample if too large for smooth rendering
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

        # Random y-jitter spreads points vertically so they don't stack
        y_jitter = rng.uniform(-0.4, 0.4, len(rc))

        if rh is not None and rh.notna().any():
            # One trace per habitat = one color per habitat in the legend
            for hab in sorted(rh.dropna().unique()):
                mask = (rh == hab).values
                hover_parts = []
                for xi, si in zip(rc[mask].values, (rs[mask] if rs is not None else [None] * mask.sum())):
                    parts = [f"<b>{variable_name}: {xi:.4f}</b>", f"Habitat: {hab}"]
                    if si is not None and pd.notna(si):
                        parts.append(f"Study: {si}")
                    hover_parts.append("<br>".join(parts))
                fig.add_trace(go.Scattergl(
                    x=rc[mask].values, y=y_jitter[mask],
                    mode="markers",
                    marker=dict(size=4, opacity=0.6),
                    name=hab,
                    hovertemplate="%{text}<extra></extra>",
                    text=hover_parts,
                ))
        else:
            fig.add_trace(go.Scattergl(
                x=rc.values, y=y_jitter,
                mode="markers",
                marker=dict(size=4, color="rgba(76, 114, 176, 0.5)"),
                name=f"CCN Reference{sample_note}",
                hovertemplate=f"<b>{variable_name}: %{{x:.4f}}</b><extra></extra>",
            ))

    # ---- Histogram ----
    elif chart_type == "Histogram + Strip":
        fig.add_trace(go.Histogram(
            x=ref_clean, nbinsx=80, histnorm="probability density",
            marker_color="rgba(76, 114, 176, 0.35)",
            name=f"CCN Reference (n={n_ref:,})",
            hovertemplate="Bin: %{x:.4f}<br>Density: %{y:.4f}<extra></extra>",
        ))

    # ---- Violin ----
    elif chart_type == "Violin + Strip":
        fig.add_trace(go.Violin(
            x=ref_clean, line_color="#4C72B0", fillcolor="rgba(76, 114, 176, 0.25)",
            name=f"CCN Reference (n={n_ref:,})", side="positive",
            meanline_visible=True, hoveron="kde", hoverinfo="x",
        ))

    # ---- Box ----
    elif chart_type == "Box + Strip":
        fig.add_trace(go.Box(
            x=ref_clean, marker_color="#4C72B0", fillcolor="rgba(76, 114, 176, 0.25)",
            name=f"CCN Reference (n={n_ref:,})",
            boxmean=True, boxpoints=False,
        ))

    # ---- Reference median line ----
    ref_med = float(ref_clean.median())
    fig.add_vline(x=ref_med, line_dash="dash", line_color="#4C72B0", line_width=1.5,
                  annotation_text=f"CCN median: {ref_med:.4g}",
                  annotation_font_color="#4C72B0", annotation_font_size=10)

    # ---- User data overlay (always red diamonds) ----
    # These sit on top of whatever chart type is selected.
    # In Point Cloud mode they're placed at y=0.55 so they float
    # above the jittered reference cloud and really stand out.
    if user_values is not None:
        user_clean = pd.to_numeric(user_values, errors="coerce").dropna()
        if len(user_clean) > 0:
            hover = _user_hover_texts(user_clean, user_df, col_map or {})
            y_user = [0] * len(user_clean)
            if chart_type == "Point Cloud":
                y_user = [0.55] * len(user_clean)
            fig.add_trace(go.Scatter(
                x=user_clean.values, y=y_user,
                mode="markers",
                marker=dict(symbol="diamond", size=13, color="#E74C3C",
                            line=dict(color="black", width=1.2)),
                name=f"Your Data (n={len(user_clean)})",
                hovertemplate="%{text}<extra></extra>",
                text=hover,
            ))
            user_med = float(user_clean.median())
            fig.add_vline(x=user_med, line_dash="dash", line_color="#E74C3C", line_width=1.5,
                          annotation_text=f"Your median: {user_med:.4g}",
                          annotation_font_color="#E74C3C", annotation_font_size=10,
                          annotation_position="bottom right")

    is_cloud = chart_type == "Point Cloud"
    fig.update_layout(
        title=dict(text=f"QA Distribution: {variable_name}", font_size=15),
        xaxis_title=f"{variable_name} ({unit})",
        yaxis_title="" if is_cloud or chart_type == "Box + Strip" else "Density",
        yaxis=dict(showticklabels=not is_cloud, showgrid=not is_cloud),
        height=500 if is_cloud else 460,
        template="plotly_white",
        legend=dict(yanchor="top", y=0.98, xanchor="right", x=0.98, font_size=10),
        margin=dict(t=60, b=50),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_stats_html(ref_values: pd.Series, user_values: pd.Series | None, variable_name: str) -> str:
    """Build an HTML stats comparison table (n, mean, median, std, min, max)
    showing CCN reference vs user data side by side."""
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
        f'<thead><tr><th>{variable_name}</th><th>n</th><th>Mean</th>'
        f'<th>Median</th><th>Std</th><th>Min</th><th>Max</th></tr></thead><tbody>'
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
    """Build an interactive grid showing ALL QA variables at once.

    Kacper, this is the "All Variables" landing view. It creates a
    2-row x 3-col plotly subplot grid, one panel per variable.
    Each panel shows the CCN reference distribution + user data
    diamonds (if any data is loaded).

    Point Cloud is too heavy for 5 subplots (would be 30K WebGL
    points total), so it falls back to Histogram in grid mode.
    The app shows a note telling the user to select a single
    variable for the full point cloud experience."""
    ref = ref_merged.copy()
    if habitats:
        ref = ref[ref["habitat"].isin(habitats)]

    # Point Cloud too heavy for subplots — fall back to histogram in grid
    grid_type = chart_type if chart_type != "Point Cloud" else "Histogram + Strip"

    variables = list(QA_NUMERIC_COLS.keys())
    n = len(variables)
    n_cols = 3
    n_rows = (n + n_cols - 1) // n_cols

    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        subplot_titles=[f"{v} ({QA_NUMERIC_COLS[v]['unit']})" for v in variables],
        horizontal_spacing=0.08, vertical_spacing=0.12,
    )

    for i, var in enumerate(variables):
        r = i // n_cols + 1
        c = i % n_cols + 1
        ref_vals = pd.to_numeric(ref.get(var, pd.Series(dtype=float)), errors="coerce").dropna()

        if len(ref_vals) > 0:
            if grid_type == "Histogram + Strip":
                fig.add_trace(go.Histogram(
                    x=ref_vals, nbinsx=60, histnorm="probability density",
                    marker_color="rgba(76, 114, 176, 0.35)",
                    name=var, showlegend=False,
                    hovertemplate=f"<b>{var}</b><br>Bin: %{{x:.4f}}<br>Density: %{{y:.4f}}<extra></extra>",
                ), row=r, col=c)
            elif grid_type == "Violin + Strip":
                fig.add_trace(go.Violin(
                    x=ref_vals, line_color="#4C72B0",
                    fillcolor="rgba(76, 114, 176, 0.25)",
                    name=var, showlegend=False,
                    meanline_visible=True, hoveron="kde", hoverinfo="x",
                ), row=r, col=c)
            elif grid_type == "Box + Strip":
                fig.add_trace(go.Box(
                    x=ref_vals, marker_color="#4C72B0",
                    fillcolor="rgba(76, 114, 176, 0.25)",
                    name=var, showlegend=False,
                    boxmean=True, boxpoints=False,
                ), row=r, col=c)

        # User overlay — same red diamonds as the single-variable charts
        ucol = col_map.get(var) if col_map else None
        if user_df is not None and ucol and ucol in user_df.columns:
            user_vals = pd.to_numeric(user_df[ucol], errors="coerce").dropna()
            if len(user_vals) > 0:
                hover = _user_hover_texts(user_vals, user_df, col_map or {})
                fig.add_trace(go.Scatter(
                    x=user_vals.values, y=[0] * len(user_vals),
                    mode="markers",
                    marker=dict(symbol="diamond", size=10, color="#E74C3C",
                                line=dict(color="black", width=0.8)),
                    name="Your data", showlegend=False,
                    hovertemplate="%{text}<extra></extra>",
                    text=hover,
                ), row=r, col=c)

    title_suffix = " (Point Cloud: select a single variable)" if chart_type == "Point Cloud" else ""
    fig.update_layout(
        height=340 * n_rows,
        title_text=f"CCN Reference Distributions vs Your Data{title_suffix}",
        template="plotly_white", showlegend=False,
        margin=dict(t=80, b=40),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


# ============================================================
# 5. MAP UTILITIES
# ============================================================
# The map uses Folium, which generates a self-contained HTML map.
# We render it into the Shiny page via ui.HTML(map._repr_html_()).
#
# Reference cores use MarkerCluster so the browser doesn't choke
# on 16K markers — they cluster at low zoom and expand when you
# zoom in. User points are individual red circles, no clustering.
#
# Kacper, if you ever want to switch this to ipyleaflet (like the
# main dashboard), you'd need to add shinywidgets to requirements
# and use output_widget/render_widget. Folium is simpler but
# less interactive (no click-to-select-row linking).
# ============================================================

MAX_REF_MAP_POINTS = 8000


def build_map_html(
    ref_cores: pd.DataFrame,
    user_df: pd.DataFrame | None,
    lat_col: str | None,
    lon_col: str | None,
    show_ref: bool,
    show_user: bool,
    habitat_filter: list[str],
) -> str:
    """Build a folium map with reference cores (blue, clustered)
    and user data points (red, individual). Returns (html, ref_count, user_count)."""
    m = folium.Map(location=[20, -40], zoom_start=3, tiles="CartoDB positron")

    # Satellite layer as an option — toggle via the layer control
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Satellite", overlay=False,
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

        # MarkerCluster groups nearby points at low zoom — essential
        # for performance with thousands of markers
        cluster = folium.plugins.MarkerCluster(name="CCN Reference Cores", show=True)
        for _, row in ref.iterrows():
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=3, color="#4C72B0", fill=True, fill_opacity=0.5, weight=1,
                popup=f"{row.get('study_id','')} / {row.get('core_id','')}<br>"
                      f"Habitat: {row.get('habitat','-')}",
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
                radius=7, color="#E74C3C", fill=True, fill_color="#E74C3C",
                fill_opacity=0.9, weight=2,
                popup=f"Your data row {idx + 1}",
            ).add_to(user_group)
            user_count += 1
        user_group.add_to(m)

    folium.LayerControl().add_to(m)

    return m._repr_html_(), ref_count, user_count


# ============================================================
# 6. UI DEFINITION
# ============================================================
# Kacper, this is the layout of the entire app. Shiny uses a
# declarative UI — you describe what widgets and panels exist,
# and Shiny handles rendering them in the browser.
#
# The app has 4 tabs:
#   1. QA Charts (landing) — shows CCN distributions immediately
#   2. Data Editor — upload/edit your data
#   3. Map — geographic view
#   4. Export — download CSVs
#
# Every ui.output_*() here connects to a @render.* function in
# the server (below). For example, ui.output_ui("qa_chart")
# renders whatever the server's qa_chart() function returns.
#
# Every ui.input_*() creates a widget the server can read via
# input.widget_id(). Changing the widget automatically triggers
# any reactive function that reads it.
# ============================================================

VARIABLE_CHOICES = {"__all__": "All Variables (overview)"}
VARIABLE_CHOICES.update({k: f"{k}  ({v['unit']})" for k, v in QA_NUMERIC_COLS.items()})

# These are the columns pre-filled when you click "New Empty Table"
CCN_TEMPLATE_COLS = [
    "study_id", "site_id", "core_id",
    "depth_min", "depth_max",
    "dry_bulk_density", "fraction_organic_matter", "fraction_carbon",
    "latitude", "longitude",
]

app_ui = ui.page_navbar(
    # Load plotly.js once in the page head — all charts reference
    # this single copy instead of each embedding their own.
    # This is why chart type swapping is instant.
    ui.head_content(
        ui.tags.script(src="https://cdn.plot.ly/plotly-2.35.2.min.js"),
    ),

    # ---- Tab 1: QA Charts (landing page) ----
    # This is the first thing users see. The CCN distributions
    # render immediately from the reference data loaded at startup.
    # No upload needed — the blue charts are always there.
    ui.nav_panel(
        "QA Charts",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_select("chart_var", "Variable",
                                choices=VARIABLE_CHOICES, selected="__all__"),
                ui.input_radio_buttons("chart_type", "Chart Style",
                                       choices=["Histogram + Strip", "Point Cloud", "Violin + Strip", "Box + Strip"],
                                       selected="Histogram + Strip"),
                ui.input_selectize("chart_habitat", "Filter CCN by Habitat",
                                   choices=HABITAT_CHOICES, multiple=True),
                ui.hr(),
                ui.p("Blue = CCN reference distributions", style="color:#4C72B0;font-size:0.85em;margin:0"),
                ui.p("Red diamonds = your uploaded data", style="color:#E74C3C;font-size:0.85em;margin:0"),
                width=280,
            ),
            ui.output_ui("qa_chart"),
            ui.output_ui("stats_panel"),
        ),
    ),

    # ---- Tab 2: Data Editor ----
    # Upload a CSV/Excel, or start with an empty CCN-formatted table.
    # The column mapping panel auto-detects matches and lets you
    # manually override any mapping via dropdowns.
    ui.nav_panel(
        "Data Editor",
        ui.layout_columns(
            ui.card(
                ui.card_header("Import"),
                ui.input_file("file", "Upload CSV / Excel", accept=[".csv", ".xlsx", ".xls"]),
                ui.layout_columns(
                    ui.input_select("sheet_name", "Sheet", choices=["(first sheet)"]),
                    ui.input_text("csv_sep", "CSV sep", value=","),
                    col_widths=[8, 4],
                ),
                ui.input_action_button("load_btn", "Load File", class_="btn-primary btn-sm w-100"),
                ui.hr(),
                ui.p("Or start from scratch:", style="font-size:0.85em;margin-bottom:4px"),
                ui.input_action_button("new_empty", "New Empty Table (CCN columns)",
                                       class_="btn-outline-primary btn-sm w-100"),
            ),
            # Column mapping — one dropdown per canonical CCN column.
            # These are static inputs (created at page load), not
            # dynamically generated. The server populates their choices
            # when a file is loaded. This avoids the circular reactive
            # dependency that dynamic UIs can cause in Shiny.
            ui.card(
                ui.card_header("Column Mapping (auto-detected)"),
                ui.div(
                    *[
                        ui.layout_columns(
                            ui.tags.span(canon, style="font-size:0.82em;font-weight:500;padding-top:6px"),
                            ui.input_select(f"map_{canon}", None, choices=["(none)"], width="100%"),
                            col_widths=[5, 7],
                        )
                        for canon in ALL_CANONICAL
                    ],
                    style="max-height:280px;overflow-y:auto;padding:4px",
                ),
            ),
            col_widths=[5, 7],
        ),
        # Row/column toolbar — add/remove rows and columns on the fly
        ui.div(
            ui.input_action_button("add_row", "+ Row", class_="btn-outline-secondary btn-sm"),
            ui.input_action_button("rm_row", "- Last Row", class_="btn-outline-warning btn-sm"),
            ui.tags.span(" | ", style="margin:0 6px"),
            ui.input_text("new_col_name", None, placeholder="new col name",
                          width="130px"),
            ui.input_select("new_col_type", None,
                            choices=["string", "int", "float", "bool"], width="90px"),
            ui.input_action_button("add_col", "+ Col", class_="btn-outline-secondary btn-sm"),
            ui.input_select("rm_col_select", None, choices=[], width="150px"),
            ui.input_action_button("rm_col", "- Col", class_="btn-outline-warning btn-sm"),
            class_="d-flex flex-wrap gap-1 align-items-end mb-2 mt-2",
        ),
        # The editable data grid — double-click any cell to edit.
        # Shiny's DataGrid widget handles this natively.
        ui.output_data_frame("table"),
        # Validation warnings — auto-updates whenever user_data changes
        ui.card(
            ui.card_header(
                ui.div(
                    ui.tags.strong("Validation"),
                    ui.output_text("validation_summary", inline=True),
                    class_="d-flex justify-content-between w-100",
                )
            ),
            ui.output_data_frame("validation_table"),
        ),
        ui.div(
            ui.download_button("download_csv", "Download Edited CSV", class_="btn-primary btn-sm"),
            ui.download_button("download_warnings", "Download Validation Report", class_="btn-outline-secondary btn-sm"),
            class_="d-flex gap-2 mt-2",
        ),
        ui.output_text_verbatim("status_bar"),
    ),

    # ---- Tab 3: Map ----
    ui.nav_panel(
        "Map",
        ui.layout_columns(
            ui.input_checkbox("show_ref", "Show CCN reference cores", value=True),
            ui.input_checkbox("show_user", "Show my data", value=True),
            ui.input_selectize("map_habitat", "Filter CCN by Habitat",
                               choices=HABITAT_CHOICES, multiple=True),
            col_widths=[3, 3, 6],
        ),
        ui.output_ui("map_status"),
        ui.output_ui("map_display"),
    ),

    # ---- Tab 4: Export ----
    ui.nav_panel(
        "Export",
        ui.card(
            ui.card_header("Download Your Data"),
            ui.p("Download the current state of your edited table as CSV."),
            ui.download_button("export_csv", "Download CSV", class_="btn-primary"),
        ),
        ui.card(
            ui.card_header("Download Validation Report"),
            ui.p("Download a CSV listing every flagged issue."),
            ui.download_button("export_warnings", "Download Validation Report",
                               class_="btn-outline-secondary"),
        ),
        ui.card(
            ui.card_header("Reference Data Summary"),
            ui.output_ui("ref_summary"),
        ),
    ),

    title="CCN QA Dashboard",
    id="main_nav",
)


# ============================================================
# 7. SERVER
# ============================================================
# Kacper, the server function runs once per browser session.
# Everything inside it is scoped to that user's session — so
# two people can use the dashboard at the same time without
# interfering with each other.
#
# The reactive flow:
#   user uploads file
#     -> _load_file() fires
#       -> user_data.set(df) updates the reactive value
#         -> table() re-renders (shows the data)
#         -> validation_results() re-computes (checks for issues)
#         -> qa_chart() re-renders (overlays user data on CCN)
#         -> map_display() re-renders (shows user points)
#
# All of this is automatic — you just .set() the reactive value
# and everything downstream updates. That's the magic of Shiny.
# ============================================================

def server(input, output, session):

    # ---- Reactive state ----
    # These are the "boxes" that hold session state.
    # Anything that reads them (.get()) will automatically re-run
    # when they change (.set()).
    user_data: reactive.Value[pd.DataFrame | None] = reactive.Value(None)
    source_name = reactive.Value("new_data")
    status_msg = reactive.Value(
        f"Reference loaded: {len(REF_DS):,} depthseries rows, "
        f"{len(REF_CORES):,} cores. Upload your data to begin."
    )

    # ---- File upload: sheet discovery ----
    # When the user selects an Excel file, we peek at its sheet
    # names and populate the sheet dropdown before they click Load.
    @reactive.effect
    @reactive.event(input.file)
    def _update_sheets():
        files = input.file()
        if not files:
            return
        name = files[0]["name"].lower()
        if name.endswith((".xlsx", ".xls")):
            try:
                xl = pd.ExcelFile(files[0]["datapath"])
                sheets = xl.sheet_names or ["(first sheet)"]
            except Exception:
                sheets = ["(first sheet)"]
        else:
            sheets = ["(first sheet)"]
        ui.update_select("sheet_name", choices=sheets, selected=sheets[0])

    # ---- Load file ----
    # Triggered when user clicks the "Load File" button.
    # Reads the CSV/Excel, stores it in user_data, and runs
    # auto_match_columns to populate the mapping dropdowns.
    @reactive.effect
    @reactive.event(input.load_btn)
    def _load_file():
        files = input.file()
        if not files:
            status_msg.set("No file selected.")
            return

        f = files[0]
        name_lower = f["name"].lower()
        try:
            if name_lower.endswith(".csv"):
                sep = input.csv_sep() or ","
                df = pd.read_csv(f["datapath"], sep=sep, na_values=["NA", "N/A", ""], low_memory=False)
            elif name_lower.endswith((".xlsx", ".xls")):
                sheet = input.sheet_name()
                sheet_arg = 0 if sheet == "(first sheet)" else sheet
                df = pd.read_excel(f["datapath"], sheet_name=sheet_arg,
                                   na_values=["NA", "N/A", ""])
            else:
                status_msg.set("Unsupported file type. Use .csv / .xlsx / .xls")
                return

            df = df.reset_index(drop=True)
            user_data.set(df)
            source_name.set(Path(f["name"]).stem)

            # Auto-match columns and populate mapping dropdowns.
            # This is where the scoring magic happens — see Section 2.
            mapping = auto_match_columns(df.columns.tolist())
            user_cols = ["(none)"] + df.columns.tolist()
            for canonical in ALL_CANONICAL:
                selected = mapping.get(canonical)
                if selected not in df.columns:
                    selected = "(none)"
                ui.update_select(f"map_{canonical}", choices=user_cols, selected=selected)

            ui.update_select("rm_col_select", choices=df.columns.tolist())

            matched = sum(1 for v in mapping.values() if v is not None)
            status_msg.set(
                f"Loaded {f['name']}: {len(df)} rows, {len(df.columns)} cols. "
                f"Auto-matched {matched}/{len(ALL_CANONICAL)} CCN columns."
            )
        except Exception as e:
            status_msg.set(f"Load failed: {e}")

    # ---- New empty table with CCN columns ----
    # Creates a blank DataFrame with standard CCN column names
    # so users can start typing data directly without uploading.
    @reactive.effect
    @reactive.event(input.new_empty)
    def _new_empty():
        df = pd.DataFrame({c: pd.Series(dtype="object") for c in CCN_TEMPLATE_COLS})
        blank = {c: np.nan for c in CCN_TEMPLATE_COLS}
        df = pd.concat([df, pd.DataFrame([blank])], ignore_index=True)
        user_data.set(df)
        source_name.set("new_data")

        # Exact match for all columns since we created them
        user_cols = ["(none)"] + df.columns.tolist()
        for canonical in ALL_CANONICAL:
            selected = canonical if canonical in df.columns else "(none)"
            ui.update_select(f"map_{canonical}", choices=user_cols, selected=selected)
        ui.update_select("rm_col_select", choices=df.columns.tolist())
        status_msg.set(f"New empty table created with {len(CCN_TEMPLATE_COLS)} CCN columns. Add rows and start typing.")

    # ---- Column mapping: read from static selects ----
    # This reactive.calc reads all 12 mapping dropdown values and
    # builds a dict of {canonical_name: user_column_name_or_None}.
    # It re-runs whenever ANY mapping dropdown changes, which means
    # the charts/validation/map automatically update when you
    # manually remap a column.
    @reactive.calc
    def resolved_col_map() -> dict[str, str | None]:
        new_map: dict[str, str | None] = {}
        for canonical in ALL_CANONICAL:
            try:
                val = input[f"map_{canonical}"]()
                new_map[canonical] = val if val != "(none)" else None
            except Exception:
                new_map[canonical] = None
        return new_map

    # ---- Table rendering ----
    # Shiny's DataGrid with editable=True gives us inline cell
    # editing for free. Double-click any cell to edit its value.
    @render.data_frame
    def table():
        df = user_data.get()
        if df is None:
            return render.DataGrid(
                pd.DataFrame({"Info": ["Upload a file and click 'Load File' to begin."]}),
            )
        return render.DataGrid(df, editable=True, selection_mode="row")

    # This function runs when the user edits a cell in the DataGrid.
    # It coerces the new value to the column's dtype (so editing a
    # float column gives you a float, not a string) and updates
    # user_data, which triggers all downstream reactives.
    @table.set_patch_fn
    def _apply_patch(patch):
        df = user_data.get()
        if df is None:
            return ""
        row = int(patch["row_index"])
        col_idx = int(patch["column_index"])
        value = patch["value"]
        col_name = df.columns[col_idx]

        # Type coercion — try to keep the column's dtype
        dtype = df[col_name].dtype
        try:
            if pd.api.types.is_integer_dtype(dtype):
                coerced = int(value) if str(value).strip() else np.nan
            elif pd.api.types.is_float_dtype(dtype):
                coerced = float(value) if str(value).strip() else np.nan
            elif pd.api.types.is_bool_dtype(dtype):
                coerced = str(value).strip().lower() in ("true", "1", "yes")
            else:
                coerced = value
        except (ValueError, TypeError):
            coerced = value

        updated = df.copy()
        updated.iloc[row, col_idx] = coerced
        user_data.set(updated)
        return str(coerced) if coerced is not None else ""

    # ---- Row / Column operations ----
    @reactive.effect
    @reactive.event(input.add_row)
    def _add_row():
        df = user_data.get()
        if df is None:
            return
        new = pd.DataFrame({c: [np.nan] for c in df.columns})
        user_data.set(pd.concat([df, new], ignore_index=True))
        status_msg.set(f"Row added. {len(df) + 1} rows.")

    @reactive.effect
    @reactive.event(input.rm_row)
    def _rm_row():
        df = user_data.get()
        if df is None or len(df) == 0:
            return
        user_data.set(df.iloc[:-1].reset_index(drop=True))
        status_msg.set(f"Last row removed. {len(df) - 1} rows.")

    @reactive.effect
    @reactive.event(input.add_col)
    def _add_col():
        df = user_data.get()
        if df is None:
            return
        name = (input.new_col_name() or "").strip()
        if not name or name in df.columns:
            status_msg.set("Column name is empty or already exists.")
            return
        dtype = input.new_col_type()
        defaults = {"string": "", "int": 0, "float": 0.0, "bool": False}
        updated = df.copy()
        updated[name] = defaults.get(dtype, np.nan)
        user_data.set(updated)
        # Re-run auto-match since the new column might match a CCN name
        user_cols = ["(none)"] + updated.columns.tolist()
        mapping = auto_match_columns(updated.columns.tolist())
        for canon in ALL_CANONICAL:
            sel = mapping.get(canon)
            if sel not in updated.columns:
                sel = "(none)"
            ui.update_select(f"map_{canon}", choices=user_cols, selected=sel)
        ui.update_select("rm_col_select", choices=updated.columns.tolist())
        status_msg.set(f"Column '{name}' added.")

    @reactive.effect
    @reactive.event(input.rm_col)
    def _rm_col():
        df = user_data.get()
        if df is None:
            return
        col = input.rm_col_select()
        if not col or col not in df.columns or len(df.columns) <= 1:
            return
        updated = df.drop(columns=[col])
        user_data.set(updated)
        user_cols = ["(none)"] + updated.columns.tolist()
        mapping = auto_match_columns(updated.columns.tolist())
        for canon in ALL_CANONICAL:
            sel = mapping.get(canon)
            if sel not in updated.columns:
                sel = "(none)"
            ui.update_select(f"map_{canon}", choices=user_cols, selected=sel)
        ui.update_select("rm_col_select", choices=updated.columns.tolist())
        status_msg.set(f"Column '{col}' removed.")

    # ---- Validation ----
    # This reactive.calc re-runs whenever user_data or the column
    # mapping changes. It returns a DataFrame of warnings that
    # feeds both the summary count and the warnings table.
    @reactive.calc
    def validation_results():
        df = user_data.get()
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
                pd.DataFrame({"Status": ["No validation issues."]}),
            )
        return render.DataGrid(w)

    # ---- Downloads ----
    # Shiny's @render.download yields CSV content as a string.
    # The browser handles the actual file save dialog.
    @render.download(filename=lambda: f"{source_name.get()}_edited.csv")
    def download_csv():
        df = user_data.get()
        if df is None:
            yield "No data loaded.\n"
            return
        yield df.to_csv(index=False)

    @render.download(filename=lambda: f"{source_name.get()}_validation.csv")
    def download_warnings():
        w = validation_results()
        if w.empty:
            yield "No validation issues.\n"
            return
        yield w.to_csv(index=False)

    @render.download(filename=lambda: f"{source_name.get()}_edited.csv")
    def export_csv():
        df = user_data.get()
        if df is None:
            yield "No data loaded.\n"
            return
        yield df.to_csv(index=False)

    @render.download(filename=lambda: f"{source_name.get()}_validation.csv")
    def export_warnings():
        w = validation_results()
        if w.empty:
            yield "No validation issues.\n"
            return
        yield w.to_csv(index=False)

    @render.text
    def status_bar():
        return status_msg.get()

    # ---- QA Charts (plotly — interactive) ----
    # This is where the chart magic happens, Kacper. When ANY of
    # these inputs change, the chart re-renders:
    #   - chart_var (which variable)
    #   - chart_type (histogram/cloud/violin/box)
    #   - chart_habitat (habitat filter)
    #   - resolved_col_map() (column mapping)
    #   - user_data (the actual data)
    #
    # The __all__ mode calls build_overview_grid (5 charts in a grid).
    # Single variable mode calls build_qa_chart (one big chart).
    @render.ui
    def qa_chart():
        var = input.chart_var()
        chart_type = input.chart_type()
        habitats = list(input.chart_habitat()) if input.chart_habitat() else []
        mapping = resolved_col_map()
        df = user_data.get()

        # Overview grid mode — all 5 variables at once
        if var == "__all__":
            html = build_overview_grid(REF_MERGED, df, mapping, habitats, chart_type)
            return ui.HTML(html)

        # Single variable mode — one big detailed chart
        ref = REF_MERGED.copy()
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
            ref_values, user_values, var,
            QA_NUMERIC_COLS.get(var, {}).get("unit", ""),
            chart_type, user_df=df, col_map=mapping,
            ref_habitat=ref_habitat, ref_study_id=ref_study,
        )
        return ui.HTML(html)

    @render.ui
    def stats_panel():
        var = input.chart_var()
        if var == "__all__":
            return ui.HTML("")  # overview grid is self-contained
        habitats = list(input.chart_habitat()) if input.chart_habitat() else []

        ref = REF_MERGED.copy()
        if habitats:
            ref = ref[ref["habitat"].isin(habitats)]

        ref_values = pd.to_numeric(ref.get(var, pd.Series(dtype=float)), errors="coerce")

        mapping = resolved_col_map()
        df = user_data.get()
        user_values = None
        if df is not None and mapping.get(var):
            ucol = mapping[var]
            if ucol in df.columns:
                user_values = df[ucol]

        return ui.HTML(build_stats_html(ref_values, user_values, var))

    # ---- Map ----
    @render.ui
    def map_display():
        mapping = resolved_col_map()
        df = user_data.get()
        habitats = list(input.map_habitat()) if input.map_habitat() else []

        lat_c = mapping.get("latitude")
        lon_c = mapping.get("longitude")

        html, ref_n, user_n = build_map_html(
            REF_CORES_VALID, df, lat_c, lon_c,
            show_ref=input.show_ref(),
            show_user=input.show_user(),
            habitat_filter=habitats,
        )
        return ui.HTML(html)

    @render.ui
    def map_status():
        mapping = resolved_col_map()
        df = user_data.get()
        lat_c = mapping.get("latitude")
        lon_c = mapping.get("longitude")

        ref_n = len(REF_CORES_VALID)
        user_n = 0
        if df is not None and lat_c and lon_c and lat_c in df.columns and lon_c in df.columns:
            user_n = df[[lat_c, lon_c]].dropna().shape[0]

        dash = "\u2014"
        lat_label = lat_c or dash
        lon_label = lon_c or dash
        return ui.HTML(
            f'<p style="font-size:0.9em;color:#555">'
            f'Reference cores: {ref_n:,} | Your data points: {user_n} | '
            f'Lat col: {lat_label} | Lon col: {lon_label}</p>'
        )

    # ---- Export tab: reference summary ----
    # Static table showing CCN reference statistics. This doesn't
    # change per session — it's the same for everyone.
    @render.ui
    def ref_summary():
        rows = []
        for var, info in QA_NUMERIC_COLS.items():
            vals = pd.to_numeric(REF_MERGED.get(var, pd.Series(dtype=float)), errors="coerce").dropna()
            if len(vals) == 0:
                continue
            rows.append(
                f"<tr><td><b>{var}</b></td><td>{info['unit']}</td>"
                f"<td>{len(vals):,}</td><td>{vals.mean():.4f}</td>"
                f"<td>{vals.median():.4f}</td><td>{vals.std():.4f}</td>"
                f"<td>{vals.min():.4f}</td><td>{vals.max():.4f}</td></tr>"
            )
        return ui.HTML(
            '<table class="table table-sm table-bordered" style="font-size:0.85em">'
            '<thead><tr><th>Variable</th><th>Unit</th><th>n</th><th>Mean</th>'
            '<th>Median</th><th>Std</th><th>Min</th><th>Max</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>'
        )


# ============================================================
# 8. APP
# ============================================================
# This is the entry point. Shiny's App() wires the UI and server
# together, and the `shiny run` CLI command finds this `app`
# object to start the web server.
# ============================================================

app = App(app_ui, server)
