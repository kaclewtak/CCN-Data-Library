from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

SOM_KEYWORDS = ["soil", "organic", "matter", "carbon", "som", "soc", "fraction"]
BD_KEYWORDS = ["bulk_density", "bd", "dry_bulk"]
AREA_CANDIDATES = [
    "area",
    "region",
    "site",
    "location",
    "loc",
    "state",
    "province",
    "country",
    "biome",
]
CATEGORY_CANDIDATES = ["habitat", "habitat_type", "ecosystem", "wetland_type", "biome"]
BAD_KEYWORDS = [
    "method",
    "flag",
    "qc",
    "unit",
    "note",
    "comment",
    "id",
    "type",
    "carbonate",
    "carbonates",
    "inorganic",
]


def normalize_col(col: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(col).lower()).strip("_")


def score_column(
    name: str,
    keywords: list[str],
    bad_keywords: list[str] | None = None,
    preferred: list[str] | None = None,
) -> float:
    n = normalize_col(name)
    score: float = 0
    for kw in keywords:
        if kw in n:
            score += 1
    if preferred:
        for p in preferred:
            if normalize_col(p) == n:
                score += 5
    if bad_keywords:
        for bk in bad_keywords:
            if bk in n:
                score -= 3
    score -= len(n) * 0.001
    return score


def find_best_column(
    columns: list[str],
    candidates: list[str] | None = None,
    keywords: list[str] | None = None,
    bad_keywords: list[str] | None = None,
    preferred: list[str] | None = None,
) -> str | None:
    if candidates:
        normalized = {c: normalize_col(c) for c in columns}
        for cand in candidates:
            cand_n = normalize_col(cand)
            for raw, norm in normalized.items():
                if cand_n == norm or cand_n in norm:
                    return raw

    if preferred:
        pref_norm = [normalize_col(p) for p in preferred]
        for c in columns:
            if normalize_col(c) in pref_norm:
                return c

    if keywords:
        scored = [
            (
                c,
                score_column(c, keywords, bad_keywords=bad_keywords, preferred=preferred),
            )
            for c in columns
        ]
        scored = [s for s in scored if s[1] > 0]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0] if scored else None

    return None


def _read_file(path: str) -> pd.DataFrame | None:
    try:
        if path.endswith(".csv"):
            return pd.read_csv(path, on_bad_lines="skip", low_memory=False)
        if path.endswith((".xlsx", ".xls")):
            return pd.read_excel(path)
        if path.endswith(".parquet"):
            return pd.read_parquet(path)
    except (ImportError, OSError, ValueError):
        pass
    return None


def _detect_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    cols = list(df.columns)
    som_col = find_best_column(
        cols,
        keywords=SOM_KEYWORDS,
        bad_keywords=BAD_KEYWORDS,
        preferred=[
            "fraction_carbon",
            "fraction carbon",
            "soil_organic_matter",
            "soil organic matter",
            "som",
            "soc",
        ],
    )
    bd_col = find_best_column(
        cols,
        keywords=BD_KEYWORDS,
        bad_keywords=BAD_KEYWORDS,
        preferred=["bulk_density", "dry_bulk_density"],
    )
    return som_col, bd_col


def _read_header(path: str) -> list[str] | None:
    try:
        if path.endswith(".csv"):
            return pd.read_csv(path, nrows=0).columns.tolist()
        if path.endswith((".xlsx", ".xls")):
            return pd.read_excel(path, nrows=0).columns.tolist()
        if path.endswith(".parquet"):
            return pd.read_parquet(path).columns.tolist()
    except (ImportError, OSError, ValueError):
        pass
    return None


def find_candidate_studies(df_inv: pd.DataFrame) -> pd.DataFrame:
    derivative = df_inv[df_inv["stage"] == "derivative"]
    records = []
    for _, row in derivative.iterrows():
        cols = _read_header(row["path"])
        if cols is None:
            continue
        som_col, bd_col = _detect_columns(pd.DataFrame(columns=cols))
        if som_col and bd_col:
            records.append(
                {
                    "path": row["path"],
                    "study_id": row["study_id"],
                    "som_col": som_col,
                    "bd_col": bd_col,
                }
            )
    return pd.DataFrame(records) if records else pd.DataFrame(columns=["path", "study_id", "som_col", "bd_col"])


def load_som_bd_from_file(path: str, som_col: str, bd_col: str, study_id: str) -> pd.DataFrame | None:
    df = _read_file(path)
    if df is None:
        return None

    som_label = str(som_col)
    df = df.rename(columns={som_col: "som", bd_col: "bulk_density"})
    df["som"] = pd.to_numeric(df["som"], errors="coerce")
    df["bulk_density"] = pd.to_numeric(df["bulk_density"], errors="coerce")
    df["som_source"] = som_label
    df["source_study"] = study_id

    area_col = find_best_column(list(df.columns), candidates=AREA_CANDIDATES)
    if area_col and area_col not in {"som", "bulk_density"}:
        df["area"] = df[area_col]

    category_col = find_best_column(list(df.columns), candidates=CATEGORY_CANDIDATES)
    if category_col and category_col not in {"som", "bulk_density"}:
        df["category"] = df[category_col]

    cols = ["som", "bulk_density", "source_study", "som_source"]
    if "area" in df.columns:
        cols.append("area")
    if "category" in df.columns:
        cols.append("category")
    return df[cols]


def _synthesis_root_from_inventory(df_inv: pd.DataFrame) -> Path | None:
    if df_inv.empty or "filename" not in df_inv.columns or "path" not in df_inv.columns:
        return None
    depthseries_rows = df_inv[df_inv["filename"] == "CCN_depthseries.csv"]
    if depthseries_rows.empty:
        return None
    return Path(str(depthseries_rows.iloc[0]["path"])).expanduser().resolve().parent


def _resolve_synthesis_root(df_inv: pd.DataFrame, synthesis_root: Path | str | None) -> Path | None:
    if synthesis_root is not None:
        return Path(synthesis_root).expanduser().resolve()
    inventory_root = _synthesis_root_from_inventory(df_inv)
    if inventory_root is not None:
        return inventory_root
    try:
        from utils.inventory_io import resolve_inventory_synthesis_root

        return resolve_inventory_synthesis_root(required=False, auto_fetch=True)
    except (ImportError, RuntimeError):
        return None


def build_synthesis_df(df_inv: pd.DataFrame, *, synthesis_root: Path | str | None = None) -> pd.DataFrame:
    # Fast path: if inventory came from CCN_synthesis flat files, load depthseries directly.
    resolved_synthesis_root = _resolve_synthesis_root(df_inv, synthesis_root)
    depthseries_path = resolved_synthesis_root / "CCN_depthseries.csv" if resolved_synthesis_root is not None else None
    cores_path = resolved_synthesis_root / "CCN_cores.csv" if resolved_synthesis_root is not None else None
    if depthseries_path is not None and depthseries_path.exists():
        return _build_synthesis_from_flat(depthseries_path, cores_path)

    # Slow path: scan individual study files for SOM + BD columns.
    candidates = find_candidate_studies(df_inv)
    if candidates.empty:
        return pd.DataFrame(columns=["som", "bulk_density", "source_study", "som_source"])

    frames = []
    for _, row in candidates.iterrows():
        part = load_som_bd_from_file(row["path"], row["som_col"], row["bd_col"], row["study_id"])
        if part is not None and not part.empty:
            frames.append(part)

    if not frames:
        return pd.DataFrame(columns=["som", "bulk_density", "source_study", "som_source"])

    return pd.concat(frames, ignore_index=True)


def _build_synthesis_from_flat(depthseries_path, cores_path) -> pd.DataFrame:
    ds = pd.read_csv(depthseries_path, on_bad_lines="skip", low_memory=False)
    som_col, bd_col = _detect_columns(ds)
    if not som_col or not bd_col:
        return pd.DataFrame(columns=["som", "bulk_density", "source_study", "som_source"])

    som_label = str(som_col)
    ds = ds.rename(columns={som_col: "som", bd_col: "bulk_density"})
    ds["som"] = pd.to_numeric(ds["som"], errors="coerce")
    ds["bulk_density"] = pd.to_numeric(ds["bulk_density"], errors="coerce")
    ds["som_source"] = som_label
    ds["source_study"] = ds.get("study_id", "CCN_synthesis")

    # Merge area info from cores (country + habitat)
    if cores_path.exists():
        cores = pd.read_csv(cores_path, on_bad_lines="skip", low_memory=False)
        merge_keys = [k for k in ["study_id", "site_id", "core_id"] if k in ds.columns and k in cores.columns]
        if merge_keys:
            area_cols = merge_keys + [c for c in ["country", "habitat", "latitude", "longitude"] if c in cores.columns]
            cores_sub = cores[area_cols].drop_duplicates(subset=merge_keys)
            ds = ds.merge(cores_sub, on=merge_keys, how="left")
            if "country" in ds.columns:
                ds["area"] = ds["country"]

    cols = ["som", "bulk_density", "source_study", "som_source"]
    for extra in ("area", "habitat", "latitude", "longitude"):
        if extra in ds.columns:
            cols.append(extra)
    return ds[cols]
