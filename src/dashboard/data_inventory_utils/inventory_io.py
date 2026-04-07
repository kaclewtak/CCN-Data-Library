from __future__ import annotations

from pathlib import Path

import pandas as pd

_REPO_DATA = Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "data"
DATA_ROOT = _REPO_DATA / "primary_studies"
SYNTHESIS_ROOT = _REPO_DATA / "CCN_synthesis"

DATA_EXTENSIONS = {".csv", ".xlsx", ".xls", ".parquet"}
STAGES = {"original", "derivative", "intermediate"}


def parse_file_info(file_path: Path) -> dict | None:
    if file_path.suffix.lower() not in DATA_EXTENSIONS:
        return None

    try:
        relative_path = file_path.relative_to(DATA_ROOT)
        parts = relative_path.parts
        if len(parts) != 3:
            return None
        study_id = parts[0]
        stage = parts[1].lower()
        if stage not in STAGES:
            return None
    except ValueError:
        return None

    clean_name = file_path.stem
    if clean_name.lower().startswith(study_id.lower()):
        category = clean_name[len(study_id) :].lstrip("_").lower()
    else:
        category = "raw_source_file"

    return {
        "path": str(file_path),
        "filename": file_path.name,
        "study_id": study_id,
        "stage": stage,
        "category": category,
        "ext": file_path.suffix,
    }


def _build_inventory_from_primary_studies() -> pd.DataFrame:
    records = []
    for file_path in DATA_ROOT.rglob("*"):
        if not file_path.is_file():
            continue
        info = parse_file_info(file_path)
        if info is not None:
            records.append(info)
    return (
        pd.DataFrame(records)
        if records
        else pd.DataFrame(columns=["path", "filename", "study_id", "stage", "category", "ext"])
    )


def _build_inventory_from_synthesis() -> pd.DataFrame:
    records = []
    for file_path in SYNTHESIS_ROOT.iterdir():
        if not file_path.is_file() or file_path.suffix.lower() not in DATA_EXTENSIONS:
            continue
        stem = file_path.stem
        category = stem.replace("CCN_", "").lower() if stem.startswith("CCN_") else stem.lower()
        records.append(
            {
                "path": str(file_path),
                "filename": file_path.name,
                "study_id": "CCN_synthesis",
                "stage": "derivative",
                "category": category,
                "ext": file_path.suffix,
            }
        )
    return (
        pd.DataFrame(records)
        if records
        else pd.DataFrame(columns=["path", "filename", "study_id", "stage", "category", "ext"])
    )


def build_inventory_df() -> pd.DataFrame:
    if DATA_ROOT.exists():
        return _build_inventory_from_primary_studies()
    if SYNTHESIS_ROOT.exists():
        return _build_inventory_from_synthesis()
    return pd.DataFrame(columns=["path", "filename", "study_id", "stage", "category", "ext"])
