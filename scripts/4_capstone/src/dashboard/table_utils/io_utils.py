from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pandas as pd
import polars as pl


def excel_sheet_names(path: str) -> list[str]:
    try:
        xl = pd.ExcelFile(path)
        return xl.sheet_names or []
    except Exception:
        return []


def read_uploaded_dataframe(file_info: dict[str, str], sheet_name: str, csv_sep: str | None) -> pl.DataFrame:
    path = file_info["datapath"]
    name = file_info["name"].lower()

    if name.endswith(".csv"):
        sep = csv_sep or ","
        return pl.read_csv(path, separator=sep)

    if name.endswith((".xlsx", ".xls")):
        if sheet_name == "(first sheet)":
            return pl.read_excel(path)
        try:
            return pl.read_excel(path, sheet_name=sheet_name)
        except TypeError:
            pdf = pd.read_excel(path, sheet_name=sheet_name)
            return pl.from_pandas(pdf)

    raise ValueError("Unsupported file type. Use .csv/.xlsx/.xls")


def autosave_file_path(source_name: str, session_token: str) -> Path:
    safe_source = re.sub(r"[^a-zA-Z0-9._-]+", "_", source_name).strip("._") or "edited_data"
    autosave_dir = Path(tempfile.gettempdir()) / "ccn_dashboard_autosaves"
    autosave_dir.mkdir(parents=True, exist_ok=True)
    return autosave_dir / f"{safe_source}_{session_token}_autosave.csv"


def latest_autosave_file(source_name: str) -> Path | None:
    safe_source = re.sub(r"[^a-zA-Z0-9._-]+", "_", source_name).strip("._") or "edited_data"
    autosave_dir = Path(tempfile.gettempdir()) / "ccn_dashboard_autosaves"
    if not autosave_dir.exists():
        return None

    pattern = f"{safe_source}_*_autosave.csv"
    candidates = [path for path in autosave_dir.glob(pattern) if path.is_file()]
    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_mtime)


def file_modified_time(file_path: Path) -> float:
    return file_path.stat().st_mtime


def write_autosave_csv(df: pl.DataFrame, file_path: Path) -> None:
    df.write_csv(file_path)


def read_autosave_csv(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")
