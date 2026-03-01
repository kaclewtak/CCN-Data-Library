from __future__ import annotations

from typing import Any

import pandas as pd
import polars as pl


def excel_sheet_names(path: str) -> list[str]:
    """
    Get the sheet names from an Excel file.

    Args:
        path: Path to the Excel file.

    Returns:
        A list of sheet names.
    """
    try:
        xl = pd.ExcelFile(path)
        return xl.sheet_names or []
    except Exception:
        return []


def coerce_value(raw_value: Any, dtype: pl.DataType) -> Any:
    """
    Coerce a raw value to the specified Polars data type.

    Args:
        raw_value: The value to coerce (from the editable grid).
        dtype: The target Polars data type.

    Returns:
        The coerced value in the appropriate Python type for the Polars dtype.
    """
    if raw_value in ("", None):
        return None

    try:
        if dtype in (pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64):
            return int(raw_value)
        if dtype in (pl.Float32, pl.Float64):
            return float(raw_value)
        if dtype == pl.Boolean:
            s = str(raw_value).strip().lower()
            if s in {"true", "1", "yes", "y"}:
                return True
            if s in {"false", "0", "no", "n"}:
                return False
            raise ValueError("Invalid boolean value")
        if dtype == pl.Date:
            return pd.to_datetime(raw_value).date()
        if dtype == pl.Datetime:
            return pd.to_datetime(raw_value).to_pydatetime()
        if dtype == pl.Time:
            return pd.to_datetime(raw_value).time()
        return str(raw_value)
    except Exception as e:
        raise ValueError(f"Cannot convert '{raw_value}' to {dtype}") from e


def set_cell_value(df: pl.DataFrame, row_idx: int, col_name: str, new_value: Any) -> pl.DataFrame:
    """
    Update a single cell in a Polars DataFrame while preserving the schema/dtype.

    Args:
        df: The Polars DataFrame.
        row_idx: The index of the row to update.
        col_name: The name of the column to update.
        new_value: The new value to set.

    Returns:
        A new Polars DataFrame with the updated cell.
    """
    dtype = df.schema[col_name]
    coerced = coerce_value(new_value, dtype)

    updated = (
        df.with_row_index("__rowid")
        .with_columns(
            pl.when(pl.col("__rowid") == row_idx)
            .then(pl.lit(coerced, dtype=dtype))
            .otherwise(pl.col(col_name))
            .alias(col_name)
        )
        .drop("__rowid")
    )
    return updated


def polars_to_pandas(df: pl.DataFrame) -> pd.DataFrame:
    """
    Convert a Polars DataFrame to a Pandas DataFrame.

    Args:
        df: The Polars DataFrame.

    Returns:
        A Pandas DataFrame.
    """
    try:
        return df.to_pandas()
    except ModuleNotFoundError:
        return pd.DataFrame(df.to_dicts())


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


def coerce_new_column_default(raw_value: str, dtype_name: str) -> Any:
    if raw_value == "":
        return None

    normalized = dtype_name.strip().lower()
    if normalized == "string":
        return str(raw_value)
    if normalized == "int":
        return int(raw_value)
    if normalized == "float":
        return float(raw_value)
    if normalized == "bool":
        s = str(raw_value).strip().lower()
        if s in {"true", "1", "yes", "y"}:
            return True
        if s in {"false", "0", "no", "n"}:
            return False
        raise ValueError("Default bool value must be true/false, 1/0, yes/no, y/n")

    raise ValueError(f"Unsupported column type: {dtype_name}")
