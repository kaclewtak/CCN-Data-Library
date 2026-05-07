from __future__ import annotations

import pandas as pd
import polars as pl


# Helper Functions
def _normalize(name: str) -> str:
    """Normalize a string by lowercasing alphanumeric characters and replacing non-alphanumeric with underscores."""
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized


def _tokens(name: str) -> list[str]:
    """Split a normalized name into tokens."""
    normalized = _normalize(name)
    return [tok for tok in normalized.split("_") if tok]


def _is_lat_candidate(name: str) -> bool:
    """Check if a column name is a latitude candidate."""
    token_set = set(_tokens(name))
    if token_set.intersection({"lat", "latitude"}):
        return True
    normalized = _normalize(name)
    return normalized.endswith("latitude") or normalized.endswith("_lat") or normalized == "lat"


def _is_lon_candidate(name: str) -> bool:
    """Check if a column name is a longitude candidate."""
    token_set = set(_tokens(name))
    if token_set.intersection({"lon", "lng", "long", "longitude"}):
        return True
    normalized = _normalize(name)
    return (
        normalized.endswith("longitude")
        or normalized.endswith("_lon")
        or normalized.endswith("_lng")
        or normalized == "lon"
        or normalized == "lng"
    )


def _stem(name: str, axis: str) -> str:
    """Extract the stem of a coordinate column name by removing coordinate-specific tokens."""
    lat_terms = {"lat", "latitude"}
    lon_terms = {"lon", "lng", "long", "longitude"}
    remove = lat_terms if axis == "lat" else lon_terms
    stem_tokens = [tok for tok in _tokens(name) if tok not in remove]
    return "_".join(stem_tokens)


# Primary geo utility functions
def find_lat_lon_columns(columns: list[str]) -> tuple[str, str] | None:
    """Find latitude and longitude column names from a list of column names.

    Attempts to match latitude and longitude columns by analyzing column names.
    Returns the best matching pair based on naming conventions and stem similarity.

    Args:
        columns: List of column names to search through.

    Returns:
        A tuple of (latitude_column, longitude_column) if found, None otherwise.
    """
    lat_matches = [(idx, col) for idx, col in enumerate(columns) if _is_lat_candidate(col)]
    lon_matches = [(idx, col) for idx, col in enumerate(columns) if _is_lon_candidate(col)]

    if not lat_matches or not lon_matches:
        return None

    best_pair: tuple[str, str] | None = None
    best_score = -1
    best_order = (10**9, 10**9)

    for lat_idx, lat_col in lat_matches:
        lat_stem = _stem(lat_col, "lat")
        for lon_idx, lon_col in lon_matches:
            lon_stem = _stem(lon_col, "lon")

            score = 0
            if lat_stem and lon_stem and lat_stem == lon_stem:
                score += 3
            if _normalize(lat_col) in {"lat", "latitude"}:
                score += 2
            if _normalize(lon_col) in {"lon", "lng", "longitude"}:
                score += 2

            order = (lat_idx, lon_idx)
            if score > best_score or (score == best_score and order < best_order):
                best_score = score
                best_order = order
                best_pair = (lat_col, lon_col)

    return best_pair


def dataframe_to_geo_points(
    df: pl.DataFrame | None,
    lat_lon_cols: tuple[str, str] | None,
) -> pd.DataFrame:
    if df is None or lat_lon_cols is None:
        return pd.DataFrame(columns=["latitude", "longitude"])

    lat_col, lon_col = lat_lon_cols
    try:
        points = df.select([lat_col, lon_col]).to_pandas()
    except ModuleNotFoundError:
        points = pd.DataFrame(df.select([lat_col, lon_col]).to_dicts())
    points = points.rename(columns={lat_col: "latitude", lon_col: "longitude"})
    points["latitude"] = pd.to_numeric(points["latitude"], errors="coerce")
    points["longitude"] = pd.to_numeric(points["longitude"], errors="coerce")
    points = points.dropna(subset=["latitude", "longitude"])
    return points
