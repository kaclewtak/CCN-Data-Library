from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import pandas as pd
import polars as pl
from shiny import reactive
from utils.geo import dataframe_to_geo_points, find_lat_lon_columns

_BOOTSTRAP_COLUMN_NAME = "Column 1"


def build_explorer_bootstrap_frame() -> pl.DataFrame:
    """Return the smallest dataframe that boots the embedded explorer."""
    return pl.DataFrame({_BOOTSTRAP_COLUMN_NAME: [None]})


def build_startup_dataset_fingerprint(gid: str) -> str:
    """Return a session-scoped fingerprint for the blank startup sheet."""
    return f"startup::{gid}"


def empty_geo_points() -> pd.DataFrame:
    return pd.DataFrame(columns=["latitude", "longitude"])


def _normalize_column_label(raw_label: Any, fallback: str) -> str:
    label = str(raw_label).strip() if raw_label is not None else ""
    return label or fallback


def _unique_column_labels(fields: Iterable[dict[str, Any]]) -> list[tuple[str, str]]:
    used_labels: dict[str, int] = {}
    resolved: list[tuple[str, str]] = []

    for index, field in enumerate(fields, start=1):
        field_id = str(field.get("fid") or f"column_{index}")
        base_label = _normalize_column_label(field.get("name"), field_id)
        next_count = used_labels.get(base_label, 0)
        used_labels[base_label] = next_count + 1
        label = base_label if next_count == 0 else f"{base_label}_{next_count + 1}"
        resolved.append((field_id, label))

    return resolved


def _coerce_snapshot_records(raw_records: Any) -> list[dict[str, Any]]:
    if raw_records is None:
        return []

    if isinstance(raw_records, Mapping):
        if all(str(key).isdigit() for key in raw_records):
            ordered_keys = sorted(raw_records, key=lambda key: int(str(key)))
            items = [raw_records[key] for key in ordered_keys]
        else:
            items = [raw_records]
    elif isinstance(raw_records, Sequence) and not isinstance(raw_records, (str, bytes, bytearray)):
        items = list(raw_records)
    else:
        return []

    normalized: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, Mapping):
            normalized.append(dict(item))

    return normalized


def spreadsheet_snapshot_to_dataframe(
    fields: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> pl.DataFrame:
    """Convert the frontend spreadsheet snapshot into a column-ordered dataframe."""
    if not fields:
        return pl.DataFrame()

    field_labels = _unique_column_labels(fields)
    if not rows:
        return pl.DataFrame({label: [] for _, label in field_labels})

    column_data = {label: [row.get(field_id) for row in rows] for field_id, label in field_labels}
    return pl.DataFrame(column_data, strict=False)


class SharedDatasetState:
    """Session-scoped dataset state mirrored from the Data Explorer iframe."""

    def __init__(self) -> None:
        self._data = reactive.Value(None)
        self._geo_points = reactive.Value(empty_geo_points())
        self._lat_lon_cols = reactive.Value(None)
        self._metadata = reactive.Value(None)

    def reset(self) -> None:
        self._data.set(None)
        self._geo_points.set(empty_geo_points())
        self._lat_lon_cols.set(None)
        self._metadata.set(None)

    def update_from_payload(self, payload: dict[str, Any] | None) -> None:
        if not isinstance(payload, dict) or not payload.get("hasUploadedData"):
            self.reset()
            return

        fields = _coerce_snapshot_records(payload.get("fields"))
        rows = _coerce_snapshot_records(payload.get("rows"))
        if payload.get("fields") is not None and not fields:
            print("[Data Explorer] Ignoring malformed fields payload during dataset sync.", flush=True)
            self.reset()
            return
        if payload.get("rows") is not None and not rows and payload.get("rows") not in ([], (), {}):
            print("[Data Explorer] Ignoring malformed rows payload during dataset sync.", flush=True)
            self.reset()
            return

        dataframe = spreadsheet_snapshot_to_dataframe(fields, rows)
        lat_lon_cols = find_lat_lon_columns(dataframe.columns)

        self._data.set(dataframe)
        self._lat_lon_cols.set(lat_lon_cols)
        self._geo_points.set(dataframe_to_geo_points(dataframe, lat_lon_cols))
        self._metadata.set(
            {
                "bridge_id": payload.get("bridgeId"),
                "dataset_fingerprint": payload.get("datasetFingerprint"),
                "dataset_label": payload.get("datasetLabel"),
                "sheet_name": payload.get("sheetName"),
                "file_name": payload.get("fileName"),
                "source": payload.get("source"),
                "worksheet_name": payload.get("worksheetName"),
                "sequence": payload.get("sequence"),
            }
        )

    def data(self) -> pl.DataFrame | None:
        return self._data.get()

    def geo_points(self) -> pd.DataFrame:
        return self._geo_points.get()

    def lat_lon_cols(self) -> tuple[str, str] | None:
        return self._lat_lon_cols.get()

    def metadata(self) -> dict[str, Any] | None:
        return self._metadata.get()
