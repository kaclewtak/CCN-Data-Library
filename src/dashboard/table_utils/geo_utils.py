from __future__ import annotations

from typing import Any

import pandas as pd
import polars as pl
from table_utils.dataframe_utils import polars_to_pandas


def find_lat_lon_columns(columns: list[str]) -> tuple[str, str] | None:
    def _normalize(name: str) -> str:
        normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
        while "__" in normalized:
            normalized = normalized.replace("__", "_")
        return normalized

    def _tokens(name: str) -> list[str]:
        normalized = _normalize(name)
        return [tok for tok in normalized.split("_") if tok]

    def _is_lat_candidate(name: str) -> bool:
        token_set = set(_tokens(name))
        if token_set.intersection({"lat", "latitude"}):
            return True
        normalized = _normalize(name)
        return normalized.endswith("latitude") or normalized.endswith("_lat") or normalized == "lat"

    def _is_lon_candidate(name: str) -> bool:
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
        lat_terms = {"lat", "latitude"}
        lon_terms = {"lon", "lng", "long", "longitude"}
        remove = lat_terms if axis == "lat" else lon_terms
        stem_tokens = [tok for tok in _tokens(name) if tok not in remove]
        return "_".join(stem_tokens)

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


def parse_coordinate(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    return parsed


def row_has_complete_lat_lon(df: pl.DataFrame, row_idx: int, lat_col: str, lon_col: str) -> bool:
    if row_idx < 0 or row_idx >= df.height:
        return False
    lat_value = parse_coordinate(df[row_idx, lat_col])
    lon_value = parse_coordinate(df[row_idx, lon_col])
    return lat_value is not None and lon_value is not None


def dataframe_to_map_points(
    df: pl.DataFrame | None,
    lat_lon_cols: tuple[str, str] | None,
    enabled: bool,
) -> pd.DataFrame:
    if df is None or lat_lon_cols is None or not enabled:
        return pd.DataFrame(columns=["latitude", "longitude"])

    lat_col, lon_col = lat_lon_cols
    points = polars_to_pandas(df.select([lat_col, lon_col]))
    points = points.rename(columns={lat_col: "latitude", lon_col: "longitude"})
    points["latitude"] = pd.to_numeric(points["latitude"], errors="coerce")
    points["longitude"] = pd.to_numeric(points["longitude"], errors="coerce")
    points = points.dropna(subset=["latitude", "longitude"])
    return points
