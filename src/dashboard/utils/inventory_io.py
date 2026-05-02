from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    from ccn_dashboard.data_provider import (
        ensure_synthesis_data_dir,
        resolve_synthesis_data_dir,
    )
except ModuleNotFoundError:  # Supports direct development runs from src/dashboard.
    import sys

    src_root = Path(__file__).resolve().parents[2]
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    from ccn_dashboard.data_provider import (
        ensure_synthesis_data_dir,
        resolve_synthesis_data_dir,
    )

DATA_EXTENSIONS = {".csv", ".xlsx", ".xls", ".parquet"}
STAGES = {"original", "derivative", "intermediate"}


def parse_file_info(file_path: Path, data_root: Path) -> dict | None:
    if file_path.suffix.lower() not in DATA_EXTENSIONS:
        return None

    try:
        relative_path = file_path.relative_to(data_root)
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


def _empty_inventory_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["path", "filename", "study_id", "stage", "category", "ext"]
    )


def _build_inventory_from_primary_studies(data_root: Path) -> pd.DataFrame:
    records = []
    for file_path in data_root.rglob("*"):
        if not file_path.is_file():
            continue
        info = parse_file_info(file_path, data_root)
        if info is not None:
            records.append(info)
    return pd.DataFrame(records) if records else _empty_inventory_df()


def _build_inventory_from_synthesis(synthesis_root: Path) -> pd.DataFrame:
    records = []
    for file_path in synthesis_root.iterdir():
        if not file_path.is_file() or file_path.suffix.lower() not in DATA_EXTENSIONS:
            continue
        stem = file_path.stem
        category = (
            stem.replace("CCN_", "").lower()
            if stem.startswith("CCN_")
            else stem.lower()
        )
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
    return pd.DataFrame(records) if records else _empty_inventory_df()


def resolve_inventory_synthesis_root(
    *, required: bool = False, auto_fetch: bool = False
) -> Path | None:
    location = (
        ensure_synthesis_data_dir(required=required)
        if auto_fetch
        else resolve_synthesis_data_dir(required=required)
    )
    return location.path if location is not None else None


def build_inventory_df(
    *,
    synthesis_root: Path | str | None = None,
    primary_studies_root: Path | str | None = None,
    auto_fetch: bool = True,
) -> pd.DataFrame:
    if primary_studies_root is not None:
        data_root = Path(primary_studies_root).expanduser().resolve()
        if data_root.exists():
            return _build_inventory_from_primary_studies(data_root)

    resolved_synthesis_root = (
        Path(synthesis_root).expanduser().resolve()
        if synthesis_root is not None
        else resolve_inventory_synthesis_root(required=False, auto_fetch=auto_fetch)
    )
    if resolved_synthesis_root is not None and resolved_synthesis_root.exists():
        return _build_inventory_from_synthesis(resolved_synthesis_root)

    return _empty_inventory_df()
