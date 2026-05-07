from __future__ import annotations

from pathlib import Path

import pandas as pd

SYNTHESIS_TABLE_ORDER = (
    "CCN_depthseries.csv",
    "CCN_cores.csv",
    "CCN_sites.csv",
    "CCN_methods.csv",
    "CCN_impacts.csv",
    "CCN_species.csv",
    "CCN_study_citations.csv",
)

SYNTHESIS_TABLE_LABELS = {
    "depthseries": "Depth Series",
    "cores": "Cores",
    "sites": "Sites",
    "methods": "Methods",
    "impacts": "Impacts",
    "species": "Species",
    "study_citations": "Study Citations",
}

ID_COLUMNS = ("study_id", "site_id", "core_id", "method_id")


def table_label(table_key: str) -> str:
    return SYNTHESIS_TABLE_LABELS.get(table_key, table_key.replace("_", " ").title())


def table_key_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    if stem.startswith("CCN_"):
        stem = stem.removeprefix("CCN_")
    return stem.lower()


def resolve_synthesis_root_from_inventory(
    inventory: pd.DataFrame,
    synthesis_root: Path | str | None = None,
) -> Path | None:
    if synthesis_root is not None:
        return Path(synthesis_root).expanduser().resolve()

    if not inventory.empty and {"filename", "path"}.issubset(inventory.columns):
        synthesis_rows = inventory[inventory["filename"].astype(str).str.startswith("CCN_")]
        if not synthesis_rows.empty:
            return Path(str(synthesis_rows.iloc[0]["path"])).expanduser().resolve().parent

    try:
        from dashboard.utils.inventory_io import resolve_inventory_synthesis_root

        return resolve_inventory_synthesis_root(required=False, auto_fetch=True)
    except (ImportError, RuntimeError):
        return None


def load_synthesis_tables(
    inventory: pd.DataFrame,
    *,
    synthesis_root: Path | str | None = None,
) -> dict[str, pd.DataFrame]:
    root = resolve_synthesis_root_from_inventory(inventory, synthesis_root)
    if root is None or not root.exists():
        return {}

    ordered_paths = [root / filename for filename in SYNTHESIS_TABLE_ORDER]
    ordered_names = {path.name for path in ordered_paths}
    extra_paths = sorted(path for path in root.glob("CCN_*.csv") if path.name not in ordered_names)

    tables: dict[str, pd.DataFrame] = {}
    for table_path in [*ordered_paths, *extra_paths]:
        if not table_path.exists() or not table_path.is_file():
            continue
        table_key = table_key_from_filename(table_path.name)
        try:
            tables[table_key] = pd.read_csv(table_path, on_bad_lines="skip", low_memory=False)
        except (OSError, ValueError):
            continue
    return tables


def build_synthesis_table_summary(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    records = []
    cores = tables.get("cores", pd.DataFrame())
    for table_key, dataframe in tables.items():
        id_columns = [column for column in ID_COLUMNS if column in dataframe.columns]
        key_completeness = (
            _mask_percent(_non_missing_mask(dataframe, id_columns), len(dataframe)) if id_columns else None
        )
        join_coverage = _core_or_site_join_coverage(table_key, dataframe, cores)
        records.append(
            {
                "Table": table_label(table_key),
                "Rows": len(dataframe),
                "Columns": len(dataframe.columns),
                "Studies": _nunique(dataframe, "study_id"),
                "Sites": _unique_key_count(dataframe, ["study_id", "site_id"]),
                "Cores": _unique_key_count(dataframe, ["study_id", "site_id", "core_id"]),
                "Key Completeness (%)": key_completeness,
                "Core/Site Join (%)": join_coverage,
            }
        )
    return pd.DataFrame(records)


def build_measurement_coverage(depthseries: pd.DataFrame) -> pd.DataFrame:
    measurement_specs = (
        ("Core soil properties", "Dry Bulk Density", ["dry_bulk_density"]),
        ("Core soil properties", "Fraction Carbon", ["fraction_carbon"]),
        (
            "Core soil properties",
            "Fraction Organic Matter",
            ["fraction_organic_matter"],
        ),
        (
            "Paired measurements",
            "Fraction Carbon + Bulk Density",
            ["fraction_carbon", "dry_bulk_density"],
        ),
        (
            "Paired measurements",
            "Fraction Organic Matter + Bulk Density",
            ["fraction_organic_matter", "dry_bulk_density"],
        ),
        ("Depth and age", "Depth Interval", ["depth_min", "depth_max"]),
        ("Depth and age", "Modeled Age", ["age"]),
        ("Depth and age", "Carbon-14 Age", ["c14_age"]),
        ("Depth and age", "Marker Date", ["marker_date"]),
        ("Radionuclides", "Cesium-137 Activity", ["cs137_activity"]),
        ("Radionuclides", "Excess Pb-210 Activity", ["excess_pb210_activity"]),
        ("Radionuclides", "Total Pb-210 Activity", ["total_pb210_activity"]),
        ("Radionuclides", "Radium-226 Activity", ["ra226_activity"]),
        ("Sample condition", "Compaction Fraction", ["compaction_fraction"]),
    )
    records = []
    for category, measurement, columns in measurement_specs:
        mask = _non_missing_mask(depthseries, columns)
        records.append(
            {
                "Category": category,
                "Measurement": measurement,
                "Records": int(mask.sum()),
                "Percent": _mask_percent(mask, len(depthseries)),
                "Studies": _nunique_when(depthseries, "study_id", mask),
                "Cores": _unique_key_count(depthseries, ["study_id", "site_id", "core_id"], mask),
            }
        )
    return pd.DataFrame(records)


def build_study_measurement_summary(depthseries: pd.DataFrame, cores: pd.DataFrame | None = None) -> pd.DataFrame:
    if depthseries.empty or "study_id" not in depthseries.columns:
        return pd.DataFrame(
            columns=[
                "Study",
                "Depth Rows",
                "Cores",
                "Sites",
                "Countries",
                "Habitats",
                "Carbon + BD Records",
                "OM + BD Records",
                "Age Records",
                "Max Depth",
                "Median Fraction Carbon",
                "Median Bulk Density",
            ]
        )

    cores = cores if cores is not None else pd.DataFrame()
    records = []
    for study_id, study_depth in depthseries.groupby("study_id", dropna=True):
        study_cores = cores[cores["study_id"] == study_id] if "study_id" in cores.columns else pd.DataFrame()
        carbon_bulk_density = _non_missing_mask(study_depth, ["fraction_carbon", "dry_bulk_density"])
        organic_matter_bulk_density = _non_missing_mask(study_depth, ["fraction_organic_matter", "dry_bulk_density"])
        age_mask = _any_non_missing_mask(
            study_depth,
            [
                "age",
                "c14_age",
                "marker_date",
                "cs137_activity",
                "excess_pb210_activity",
                "total_pb210_activity",
            ],
        )
        records.append(
            {
                "Study": study_id,
                "Depth Rows": len(study_depth),
                "Cores": _unique_key_count(study_cores, ["study_id", "site_id", "core_id"]),
                "Sites": _unique_key_count(study_cores, ["study_id", "site_id"]),
                "Countries": _nunique(study_cores, "country"),
                "Habitats": _nunique(study_cores, "habitat"),
                "Carbon + BD Records": int(carbon_bulk_density.sum()),
                "OM + BD Records": int(organic_matter_bulk_density.sum()),
                "Age Records": int(age_mask.sum()),
                "Max Depth": _max_numeric(study_depth, ["depth_max", "representative_depth_max"]),
                "Median Fraction Carbon": _median_numeric(study_depth, "fraction_carbon"),
                "Median Bulk Density": _median_numeric(study_depth, "dry_bulk_density"),
            }
        )
    summary = pd.DataFrame(records)
    return summary.sort_values("Depth Rows", ascending=False, ignore_index=True)


def build_depth_bin_summary(depthseries: pd.DataFrame) -> pd.DataFrame:
    depth_position = _representative_depth(depthseries)
    if depth_position.dropna().empty:
        return pd.DataFrame(
            columns=[
                "Depth Bin",
                "Records",
                "Percent",
                "Studies",
                "Cores",
                "Median Fraction Carbon",
                "Median Bulk Density",
            ]
        )

    bins = (
        ("0-10 cm", 0.0, 10.0),
        ("10-30 cm", 10.0, 30.0),
        ("30-100 cm", 30.0, 100.0),
        (">=100 cm", 100.0, None),
    )
    records = []
    for label, lower_bound, upper_bound in bins:
        mask = depth_position.ge(lower_bound)
        if upper_bound is not None:
            mask &= depth_position.lt(upper_bound)
        records.append(
            {
                "Depth Bin": label,
                "Records": int(mask.sum()),
                "Percent": _mask_percent(mask, len(depthseries)),
                "Studies": _nunique_when(depthseries, "study_id", mask),
                "Cores": _unique_key_count(depthseries, ["study_id", "site_id", "core_id"], mask),
                "Median Fraction Carbon": _median_numeric(depthseries.loc[mask], "fraction_carbon"),
                "Median Bulk Density": _median_numeric(depthseries.loc[mask], "dry_bulk_density"),
            }
        )
    return pd.DataFrame(records)


def build_quality_summary(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    records = []
    depthseries = tables.get("depthseries", pd.DataFrame())
    cores = tables.get("cores", pd.DataFrame())
    methods = tables.get("methods", pd.DataFrame())
    citations = tables.get("study_citations", pd.DataFrame())

    _add_quality_item(
        records,
        "Depth Series",
        "Missing depth interval",
        depthseries,
        ~_non_missing_mask(depthseries, ["depth_min", "depth_max"]),
    )
    _add_quality_item(
        records,
        "Depth Series",
        "Missing dry bulk density",
        depthseries,
        ~_non_missing_mask(depthseries, ["dry_bulk_density"]),
    )
    _add_quality_item(
        records,
        "Depth Series",
        "Missing fraction carbon",
        depthseries,
        ~_non_missing_mask(depthseries, ["fraction_carbon"]),
    )
    _add_quality_item(
        records,
        "Depth Series",
        "Missing fraction organic matter",
        depthseries,
        ~_non_missing_mask(depthseries, ["fraction_organic_matter"]),
    )
    _add_quality_item(
        records,
        "Depth Series",
        "Nonpositive dry bulk density",
        depthseries,
        _numeric_mask(depthseries, "dry_bulk_density", lambda series: series <= 0),
    )
    _add_quality_item(
        records,
        "Depth Series",
        "Fraction carbon outside 0-1",
        depthseries,
        _numeric_mask(depthseries, "fraction_carbon", lambda series: ~series.between(0, 1)),
    )
    _add_quality_item(
        records,
        "Depth Series",
        "Organic matter outside 0-1",
        depthseries,
        _numeric_mask(depthseries, "fraction_organic_matter", lambda series: ~series.between(0, 1)),
    )
    if {"fraction_carbon", "fraction_organic_matter"}.issubset(depthseries.columns):
        fraction_carbon = pd.to_numeric(depthseries["fraction_carbon"], errors="coerce")
        fraction_organic_matter = pd.to_numeric(depthseries["fraction_organic_matter"], errors="coerce")
        carbon_greater_than_organic_matter = (
            fraction_carbon.notna() & fraction_organic_matter.notna() & (fraction_carbon > fraction_organic_matter)
        )
        _add_quality_item(
            records,
            "Depth Series",
            "Carbon greater than organic matter",
            depthseries,
            carbon_greater_than_organic_matter,
        )

    _add_quality_item(
        records,
        "Cores",
        "Missing coordinates",
        cores,
        ~_non_missing_mask(cores, ["latitude", "longitude"]),
    )
    _add_quality_item(
        records,
        "Cores",
        "Missing country",
        cores,
        ~_non_missing_mask(cores, ["country"]),
    )
    _add_quality_item(
        records,
        "Cores",
        "Missing habitat",
        cores,
        ~_non_missing_mask(cores, ["habitat"]),
    )
    _add_quality_item(
        records,
        "Cores",
        "Missing collection year",
        cores,
        ~_non_missing_mask(cores, ["year"]),
    )
    _add_quality_item(
        records,
        "Cores",
        "Missing max depth",
        cores,
        ~_non_missing_mask(cores, ["max_depth"]),
    )

    _add_quality_item(
        records,
        "Methods",
        "Missing coring method",
        methods,
        ~_non_missing_mask(methods, ["coring_method"]),
    )
    _add_quality_item(
        records,
        "Methods",
        "Missing fraction carbon method",
        methods,
        ~_non_missing_mask(methods, ["fraction_carbon_method"]),
    )
    _add_quality_item(
        records,
        "Citations",
        "Missing DOI and URL",
        citations,
        ~_any_non_missing_mask(citations, ["doi", "url"]),
    )
    return pd.DataFrame(records)


def build_categorical_summary(tables: dict[str, pd.DataFrame], *, limit_per_variable: int = 12) -> pd.DataFrame:
    specs = (
        ("methods", "Coring Method", "coring_method"),
        ("methods", "Roots Flag", "roots_flag"),
        ("methods", "Sieved Flag", "sediment_sieved_flag"),
        ("methods", "Compaction Flag", "compaction_flag"),
        ("methods", "Carbon Source", "carbon_measured_or_modeled"),
        ("methods", "Fraction Carbon Method", "fraction_carbon_method"),
        ("methods", "Carbonates Removed", "carbonates_removed"),
        ("cores", "Country", "country"),
        ("cores", "Habitat", "habitat"),
        ("cores", "Salinity Class", "salinity_class"),
        ("cores", "Vegetation Class", "vegetation_class"),
        ("cores", "Inundation Class", "inundation_class"),
        ("cores", "Stocks Quality Code", "stocks_qual_code"),
        ("cores", "Position Method", "position_method"),
        ("sites", "Site Salinity Class", "salinity_class"),
        ("sites", "Site Vegetation Class", "vegetation_class"),
        ("sites", "Site Inundation Class", "inundation_class"),
        ("impacts", "Impact Class", "impact_class"),
        ("species", "Species", "species_code"),
        ("species", "Species Code Type", "code_type"),
        ("study_citations", "Publication Type", "publication_type"),
        ("study_citations", "Publication Year", "year"),
    )
    records = []
    for table_key, variable, column in specs:
        dataframe = tables.get(table_key, pd.DataFrame())
        if dataframe.empty or column not in dataframe.columns:
            continue
        values = _clean_series(dataframe[column])
        if values.empty:
            continue
        counts = values.value_counts()
        for value, count in counts.head(limit_per_variable).items():
            value_mask = dataframe[column].astype(str).str.strip() == str(value)
            records.append(
                {
                    "Table": table_label(table_key),
                    "Variable": variable,
                    "Value": value,
                    "Records": int(count),
                    "Studies": _nunique_when(dataframe, "study_id", value_mask),
                }
            )
        if len(counts) > limit_per_variable:
            records.append(
                {
                    "Table": table_label(table_key),
                    "Variable": variable,
                    "Value": "Other values",
                    "Records": int(counts.iloc[limit_per_variable:].sum()),
                    "Studies": None,
                }
            )
    return pd.DataFrame(records)


def _clean_series(series: pd.Series) -> pd.Series:
    clean = series.dropna().astype(str).str.strip()
    clean = clean[clean != ""]
    return clean[~clean.str.lower().isin({"na", "nan", "none"})]


def _non_missing_mask(dataframe: pd.DataFrame, columns: list[str]) -> pd.Series:
    if dataframe.empty:
        return pd.Series(False, index=dataframe.index)
    if not columns or any(column not in dataframe.columns for column in columns):
        return pd.Series(False, index=dataframe.index)

    mask = pd.Series(True, index=dataframe.index)
    for column in columns:
        series = dataframe[column]
        column_mask = series.notna()
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            clean = series.astype(str).str.strip().str.lower()
            column_mask &= ~clean.isin({"", "na", "nan", "none"})
        mask &= column_mask
    return mask.fillna(False)


def _any_non_missing_mask(dataframe: pd.DataFrame, columns: list[str]) -> pd.Series:
    if dataframe.empty:
        return pd.Series(False, index=dataframe.index)
    present_columns = [column for column in columns if column in dataframe.columns]
    if not present_columns:
        return pd.Series(False, index=dataframe.index)
    mask = pd.Series(False, index=dataframe.index)
    for column in present_columns:
        mask |= _non_missing_mask(dataframe, [column])
    return mask.fillna(False)


def _nunique(dataframe: pd.DataFrame, column: str) -> int:
    if dataframe.empty or column not in dataframe.columns:
        return 0
    return int(_clean_series(dataframe[column]).nunique())


def _nunique_when(dataframe: pd.DataFrame, column: str, mask: pd.Series) -> int:
    if dataframe.empty or column not in dataframe.columns:
        return 0
    aligned_mask = mask.reindex(dataframe.index, fill_value=False)
    return int(_clean_series(dataframe.loc[aligned_mask, column]).nunique())


def _unique_key_count(dataframe: pd.DataFrame, keys: list[str], mask: pd.Series | None = None) -> int:
    if dataframe.empty or not set(keys).issubset(dataframe.columns):
        return 0
    subset = dataframe[keys]
    if mask is not None:
        subset = subset.loc[mask.reindex(dataframe.index, fill_value=False)]
    subset = subset.dropna().drop_duplicates()
    if subset.empty:
        return 0
    return len(subset)


def _mask_percent(mask: pd.Series, total: int) -> float | None:
    if total <= 0:
        return None
    return round(float(mask.sum()) / float(total) * 100.0, 1)


def _core_or_site_join_coverage(table_key: str, dataframe: pd.DataFrame, cores: pd.DataFrame) -> float | None:
    if dataframe.empty or cores.empty:
        return None
    if table_key == "cores":
        return 100.0

    key_candidates = (["study_id", "site_id", "core_id"], ["study_id", "site_id"])
    for keys in key_candidates:
        if not set(keys).issubset(dataframe.columns) or not set(keys).issubset(cores.columns):
            continue
        source_keys = dataframe[keys].dropna().drop_duplicates()
        core_keys = cores[keys].dropna().drop_duplicates().assign(_matched_core_key=True)
        if source_keys.empty or core_keys.empty:
            continue
        joined = source_keys.merge(core_keys, on=keys, how="left")
        matched_count = int(joined["_matched_core_key"].notna().sum())
        return round(
            float(matched_count) / float(len(source_keys)) * 100.0,
            1,
        )
    return None


def _max_numeric(dataframe: pd.DataFrame, columns: list[str]) -> float | None:
    values = []
    for column in columns:
        if column in dataframe.columns:
            values.append(pd.to_numeric(dataframe[column], errors="coerce"))
    if not values:
        return None
    combined = pd.concat(values, ignore_index=True).dropna()
    if combined.empty:
        return None
    return round(float(combined.max()), 2)


def _median_numeric(dataframe: pd.DataFrame, column: str) -> float | None:
    if dataframe.empty or column not in dataframe.columns:
        return None
    values = pd.to_numeric(dataframe[column], errors="coerce").dropna()
    if values.empty:
        return None
    return round(float(values.median()), 4)


def _representative_depth(depthseries: pd.DataFrame) -> pd.Series:
    if depthseries.empty:
        return pd.Series(dtype=float)
    depth_min = _numeric_series(depthseries, "depth_min")
    depth_max = _numeric_series(depthseries, "depth_max")
    rep_min = _numeric_series(depthseries, "representative_depth_min")
    rep_max = _numeric_series(depthseries, "representative_depth_max")

    interval_midpoint = (depth_min + depth_max) / 2.0
    representative_midpoint = (rep_min + rep_max) / 2.0
    return representative_midpoint.combine_first(interval_midpoint).combine_first(depth_min).combine_first(depth_max)


def _numeric_series(dataframe: pd.DataFrame, column: str) -> pd.Series:
    if column not in dataframe.columns:
        return pd.Series(index=dataframe.index, dtype=float)
    return pd.to_numeric(dataframe[column], errors="coerce")


def _numeric_mask(dataframe: pd.DataFrame, column: str, predicate) -> pd.Series:
    if dataframe.empty or column not in dataframe.columns:
        return pd.Series(False, index=dataframe.index)
    values = pd.to_numeric(dataframe[column], errors="coerce")
    return values.notna() & predicate(values)


def _add_quality_item(
    records: list[dict],
    table: str,
    item: str,
    dataframe: pd.DataFrame,
    issue_mask: pd.Series,
) -> None:
    total = len(dataframe)
    records.append(
        {
            "Table": table,
            "Inventory Item": item,
            "Records": (int(issue_mask.reindex(dataframe.index, fill_value=False).sum()) if total else 0),
            "Percent": _mask_percent(issue_mask, total),
        }
    )
