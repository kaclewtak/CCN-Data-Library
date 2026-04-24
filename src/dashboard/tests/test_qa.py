from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import pandas as pd

DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

qa = import_module("utils.qa")

build_overview_grid = qa.build_overview_grid
build_qa_chart = qa.build_qa_chart
build_comparison_results = qa.build_comparison_results
compare_user_to_reference = qa.compare_user_to_reference
matched_numeric_variables = qa.matched_numeric_variables
classify_us_subregion = qa.classify_us_subregion
apply_geo_filters = qa.apply_geo_filters


def test_matched_numeric_variables_returns_only_available_numeric_matches() -> None:
    user_df = pd.DataFrame(
        {
            "Bulk Density": [1.1, 1.2],
            "Carbon Fraction": [0.1, 0.2],
            "Latitude": [44.0, 45.0],
        }
    )
    col_map = {
        "dry_bulk_density": "Bulk Density",
        "fraction_carbon": "Carbon Fraction",
        "fraction_organic_matter": None,
        "depth_min": None,
        "depth_max": None,
        "latitude": "Latitude",
    }

    matches = matched_numeric_variables(user_df, col_map)

    assert matches == [
        {"variable": "dry_bulk_density", "user_column": "Bulk Density", "unit": "g/cm³"},
        {"variable": "fraction_carbon", "user_column": "Carbon Fraction", "unit": "fraction"},
    ]


def test_compare_user_to_reference_handles_insufficient_data() -> None:
    result = compare_user_to_reference(pd.Series([1.0]), pd.Series([1.0, 1.1]), test_name="ks")

    assert result["statistic"] is None
    assert result["p_value"] is None
    assert result["interpretation"] == "Insufficient data for comparison."
    assert result["n_user"] == 1
    assert result["n_ref"] == 2


def test_build_comparison_results_filters_reference_rows_and_selected_variable() -> None:
    ref_merged = pd.DataFrame(
        {
            "habitat": ["mangrove", "mangrove", "saltmarsh", "saltmarsh"],
            "dry_bulk_density": [1.0, 1.1, 1.8, 1.9],
            "fraction_carbon": [0.10, 0.11, 0.30, 0.31],
            "fraction_organic_matter": [0.20, 0.21, 0.40, 0.41],
            "depth_min": [0, 5, 0, 5],
            "depth_max": [5, 10, 5, 10],
        }
    )
    user_df = pd.DataFrame(
        {
            "Bulk Density": [1.0, 1.1, 1.2],
            "Carbon Fraction": [0.10, 0.11, 0.12],
        }
    )
    col_map = {
        "dry_bulk_density": "Bulk Density",
        "fraction_carbon": "Carbon Fraction",
        "fraction_organic_matter": None,
        "depth_min": None,
        "depth_max": None,
    }

    results = build_comparison_results(
        ref_merged,
        user_df,
        col_map,
        habitats=["mangrove"],
        variable="fraction_carbon",
        test_name="ks",
    )

    assert len(results) == 1
    assert results[0]["variable"] == "fraction_carbon"
    assert results[0]["user_column"] == "Carbon Fraction"
    assert results[0]["n_user"] == 3
    assert results[0]["n_ref"] == 2
    assert results[0]["test"] == "ks"
    assert results[0]["statistic"] is not None
    assert results[0]["p_value"] is not None


def test_build_qa_chart_uses_red_distribution_trace_for_violin() -> None:
    html = build_qa_chart(
        pd.Series([0.1, 0.2, 0.3, 0.4]),
        pd.Series([0.12, 0.22, 0.32]),
        "fraction_carbon",
        "fraction",
        "Violin + Strip",
    )

    assert "Your Data (n=3)" in html
    assert '"type":"violin"' in html
    assert '"side":"both"' in html
    assert '"points":false' in html
    assert '"symbol":"diamond"' not in html


def test_build_overview_grid_uses_red_distribution_trace_for_violin() -> None:
    ref_merged = pd.DataFrame(
        {
            "habitat": ["mangrove", "mangrove", "saltmarsh", "saltmarsh"],
            "dry_bulk_density": [1.0, 1.1, 1.8, 1.9],
            "fraction_carbon": [0.10, 0.11, 0.30, 0.31],
            "fraction_organic_matter": [0.20, 0.21, 0.40, 0.41],
            "depth_min": [0, 5, 0, 5],
            "depth_max": [5, 10, 5, 10],
        }
    )
    user_df = pd.DataFrame(
        {
            "Bulk Density": [1.0, 1.1, 1.2],
            "Carbon Fraction": [0.10, 0.11, 0.12],
            "Organic Matter": [0.20, 0.22, 0.24],
            "Depth Min": [0, 2, 4],
            "Depth Max": [2, 4, 6],
        }
    )
    col_map: dict[str, str | None] = {
        "dry_bulk_density": "Bulk Density",
        "fraction_carbon": "Carbon Fraction",
        "fraction_organic_matter": "Organic Matter",
        "depth_min": "Depth Min",
        "depth_max": "Depth Max",
    }

    html = build_overview_grid(ref_merged, user_df, col_map, [], chart_type="Violin + Strip")

    assert "Your data" in html
    assert '"type":"violin"' in html
    assert '"symbol":"diamond"' not in html


def test_build_overview_grid_supports_point_cloud_rendering() -> None:
    ref_merged = pd.DataFrame(
        {
            "habitat": ["mangrove", "mangrove", "saltmarsh", "saltmarsh"],
            "dry_bulk_density": [1.0, 1.1, 1.8, 1.9],
            "fraction_carbon": [0.10, 0.11, 0.30, 0.31],
            "fraction_organic_matter": [0.20, 0.21, 0.40, 0.41],
            "depth_min": [0, 5, 0, 5],
            "depth_max": [5, 10, 5, 10],
        }
    )
    user_df = pd.DataFrame(
        {
            "Bulk Density": [1.0, 1.1, 1.2],
            "Carbon Fraction": [0.10, 0.11, 0.12],
            "Organic Matter": [0.20, 0.22, 0.24],
            "Depth Min": [0, 2, 4],
            "Depth Max": [2, 4, 6],
        }
    )
    col_map: dict[str, str | None] = {
        "dry_bulk_density": "Bulk Density",
        "fraction_carbon": "Carbon Fraction",
        "fraction_organic_matter": "Organic Matter",
        "depth_min": "Depth Min",
        "depth_max": "Depth Max",
    }

    html = build_overview_grid(ref_merged, user_df, col_map, [], chart_type="Point Cloud")

    assert "CCN Reference Distributions vs Your Data" in html
    assert "Your data" in html
    assert '"type":"scattergl"' in html
    assert "Point Cloud: select a single variable" not in html


# ---------------------------------------------------------------------------
# Geographic region classification & filtering tests
# ---------------------------------------------------------------------------


def test_classify_us_subregion_known_locations() -> None:
    # New York City → Northeast
    assert classify_us_subregion(40.7, -74.0) == "Northeast"
    # Miami → Southeast
    assert classify_us_subregion(25.8, -80.2) == "Southeast"
    # New Orleans → Gulf Coast
    assert classify_us_subregion(30.0, -90.0) == "Gulf Coast"
    # Los Angeles → West Coast
    assert classify_us_subregion(34.0, -118.2) == "West Coast"
    # Honolulu → Pacific Islands
    assert classify_us_subregion(21.3, -157.8) == "Pacific Islands"
    # Anchorage → Alaska
    assert classify_us_subregion(61.2, -149.9) == "Alaska"


def test_classify_us_subregion_fallback() -> None:
    # Middle of nowhere — doesn't match any box
    assert classify_us_subregion(45.0, -100.0) == "Other US"


def _make_geo_df() -> pd.DataFrame:
    """Small reference-like DataFrame with continent/country/us_subregion/habitat."""
    return pd.DataFrame(
        {
            "continent": ["north america", "north america", "europe", "asia"],
            "country": ["united states", "united states", "united kingdom", "india"],
            "us_subregion": ["Southeast", "Northeast", "", ""],
            "habitat": ["mangrove", "saltmarsh", "saltmarsh", "mangrove"],
            "dry_bulk_density": [1.0, 1.2, 1.5, 0.8],
        }
    )


def test_apply_geo_filters_empty_is_noop() -> None:
    df = _make_geo_df()
    assert len(apply_geo_filters(df)) == 4


def test_apply_geo_filters_by_continent() -> None:
    df = _make_geo_df()
    result = apply_geo_filters(df, continents=["north america"])
    assert len(result) == 2
    assert set(result["country"]) == {"united states"}


def test_apply_geo_filters_by_country() -> None:
    df = _make_geo_df()
    result = apply_geo_filters(df, countries=["india"])
    assert len(result) == 1


def test_apply_geo_filters_by_us_subregion() -> None:
    df = _make_geo_df()
    result = apply_geo_filters(df, us_subregions=["Southeast"])
    assert len(result) == 1
    assert result.iloc[0]["habitat"] == "mangrove"


def test_apply_geo_filters_chains_continent_country_habitat() -> None:
    df = _make_geo_df()
    result = apply_geo_filters(
        df,
        continents=["north america"],
        countries=["united states"],
        habitats=["saltmarsh"],
    )
    assert len(result) == 1
    assert result.iloc[0]["us_subregion"] == "Northeast"


def test_build_comparison_results_with_geo_filters() -> None:
    ref_merged = pd.DataFrame(
        {
            "habitat": ["mangrove", "mangrove", "saltmarsh", "saltmarsh"],
            "continent": ["north america", "europe", "north america", "europe"],
            "country": ["united states", "united kingdom", "united states", "united kingdom"],
            "us_subregion": ["Southeast", "", "Northeast", ""],
            "dry_bulk_density": [1.0, 1.1, 1.8, 1.9],
            "fraction_carbon": [0.10, 0.11, 0.30, 0.31],
            "fraction_organic_matter": [0.20, 0.21, 0.40, 0.41],
            "depth_min": [0, 5, 0, 5],
            "depth_max": [5, 10, 5, 10],
        }
    )
    user_df = pd.DataFrame({"Bulk Density": [1.0, 1.1, 1.2]})
    col_map = {
        "dry_bulk_density": "Bulk Density",
        "fraction_carbon": None,
        "fraction_organic_matter": None,
        "depth_min": None,
        "depth_max": None,
    }

    results = build_comparison_results(
        ref_merged,
        user_df,
        col_map,
        continents=["north america"],
        variable="dry_bulk_density",
    )

    assert len(results) == 1
    assert results[0]["n_ref"] == 2  # only the 2 north america rows
