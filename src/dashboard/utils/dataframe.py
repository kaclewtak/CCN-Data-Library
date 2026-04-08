from __future__ import annotations

from typing import Any

import pandas as pd
import polars as pl


def is_blank_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def coerce_value(raw_value: Any, dtype: pl.DataType) -> Any:
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
    try:
        return df.to_pandas()
    except ModuleNotFoundError:
        return pd.DataFrame(df.to_dicts())


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


def append_blank_row(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    new_row = {col: None for col in df.columns}
    row_df = pl.DataFrame([new_row], schema=df.schema)
    updated = pl.concat([df, row_df], how="vertical_relaxed")
    return updated, updated.height - 1


def remove_row_from_bottom(df: pl.DataFrame, bottom_offset: int) -> tuple[pl.DataFrame, int]:
    if bottom_offset < 0 or bottom_offset >= df.height:
        raise ValueError(f"bottom offset {bottom_offset} out of range [0, {max(df.height - 1, 0)}].")

    row_idx = df.height - 1 - bottom_offset
    updated = df.filter(pl.int_range(0, df.height) != row_idx)
    return updated, row_idx


def add_column_with_default(
    df: pl.DataFrame,
    col_name: str,
    dtype_name: str,
    default_raw: str,
) -> pl.DataFrame:
    if not col_name:
        raise ValueError("column name is required.")
    if col_name in df.columns:
        raise ValueError(f"'{col_name}' already exists.")

    dtype_map: dict[str, pl.DataType] = {
        "string": pl.Utf8,
        "int": pl.Int64,
        "float": pl.Float64,
        "bool": pl.Boolean,
    }
    if dtype_name not in dtype_map:
        raise ValueError(f"Unsupported column type: {dtype_name}")

    default_value = coerce_new_column_default(default_raw, dtype_name)
    series = pl.Series(col_name, [default_value] * df.height, dtype=dtype_map[dtype_name])
    return df.with_columns(series)


def remove_existing_column(df: pl.DataFrame, col_name: str) -> pl.DataFrame:
    if df.width <= 1:
        raise ValueError("cannot remove the last remaining column.")
    if not col_name or col_name not in df.columns:
        raise ValueError("select a valid column.")
    return df.drop(col_name)


def sync_row_highlight_after_remove(marked_row: int | None, removed_row_idx: int) -> int | None:
    if marked_row is None:
        return None
    if removed_row_idx == marked_row:
        return None
    if removed_row_idx < marked_row:
        return marked_row - 1
    return marked_row
