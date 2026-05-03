from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.figure import Figure, SubFigure
from scipy import stats

from dashboard.utils.synthesis_io import (
    BAD_KEYWORDS,
    BD_KEYWORDS,
    SOM_KEYWORDS,
    find_best_column,
)


def find_comparable_columns(user_df: pd.DataFrame, inventory_columns: list[str] | None = None) -> dict[str, str]:
    mapping: dict[str, str] = {}
    cols = list(user_df.columns)
    som_col = find_best_column(
        cols,
        keywords=SOM_KEYWORDS,
        bad_keywords=BAD_KEYWORDS,
        preferred=["fraction_carbon", "fraction carbon", "soil_organic_matter", "soil organic matter", "som", "soc"],
    )
    if som_col:
        mapping[som_col] = "som"
    bd_col = find_best_column(
        cols,
        keywords=BD_KEYWORDS,
        bad_keywords=BAD_KEYWORDS,
        preferred=["bulk_density", "dry_bulk_density"],
    )
    if bd_col:
        mapping[bd_col] = "bulk_density"
    return mapping


def compare_distributions(
    user_series: pd.Series,
    inventory_series: pd.Series,
    test_name: str = "ks",
) -> dict:
    user_clean = pd.to_numeric(user_series, errors="coerce").dropna()
    inv_clean = pd.to_numeric(inventory_series, errors="coerce").dropna()

    if len(user_clean) < 2 or len(inv_clean) < 2:
        return {
            "test": test_name,
            "statistic": None,
            "p_value": None,
            "interpretation": "Insufficient data for comparison.",
        }

    stat: float
    p: float

    if test_name == "anderson":
        try:
            result = stats.anderson_ksamp([user_clean.values, inv_clean.values])
            stat = float(getattr(result, "statistic"))
            p = float(getattr(result, "pvalue"))
        except Exception as exc:
            return {"test": "anderson", "statistic": None, "p_value": None, "interpretation": f"Test failed: {exc}"}
    else:
        result = stats.ks_2samp(user_clean, inv_clean)
        stat = float(getattr(result, "statistic"))
        p = float(getattr(result, "pvalue"))

    if p < 0.01:
        interp = "Distributions are significantly different (p < 0.01)."
    elif p < 0.05:
        interp = "Distributions differ at the 5% significance level."
    else:
        interp = "No significant difference detected between distributions."

    return {
        "test": test_name,
        "statistic": round(stat, 4),
        "p_value": round(p, 4),
        "interpretation": interp,
    }


def build_comparison_plot(
    user_series: pd.Series,
    inventory_series: pd.Series,
    col_name: str,
    ax: Axes | None = None,
) -> Figure:
    user_clean = pd.to_numeric(user_series, errors="coerce").dropna()
    inv_clean = pd.to_numeric(inventory_series, errors="coerce").dropna()

    fig = None
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 4))
    else:
        parent = ax.figure
        fig = parent if isinstance(parent, Figure) else parent.figure

    sns.histplot(x=inv_clean, bins=30, kde=True, stat="density", alpha=0.4, label="Inventory", color="steelblue", ax=ax)
    sns.histplot(x=user_clean, bins=30, kde=True, stat="density", alpha=0.4, label="Uploaded", color="coral", ax=ax)
    ax.set_title(f"Distribution Comparison — {col_name}")
    ax.set_xlabel(col_name)
    ax.legend()
    fig.tight_layout()
    return fig
