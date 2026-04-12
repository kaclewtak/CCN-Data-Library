from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import polars as pl
from shiny import reactive

DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

dashboard_shared_dataset = import_module("dashboard_shared_dataset")

SharedDatasetState = dashboard_shared_dataset.SharedDatasetState
build_explorer_bootstrap_frame = dashboard_shared_dataset.build_explorer_bootstrap_frame
build_startup_dataset_fingerprint = dashboard_shared_dataset.build_startup_dataset_fingerprint


def test_build_explorer_bootstrap_frame_returns_single_blank_row() -> None:
    bootstrap = build_explorer_bootstrap_frame()

    assert bootstrap.columns == ["Column 1"]
    assert bootstrap.height == 1
    assert bootstrap.row(0) == (None,)


def test_startup_dataset_fingerprint_is_session_scoped() -> None:
    assert build_startup_dataset_fingerprint("gid-a") == "startup::gid-a"


def test_shared_dataset_state_ignores_blank_startup_payload() -> None:
    state = SharedDatasetState()
    state.update_from_payload({"hasUploadedData": False})

    with reactive.isolate():
        assert state.data() is None
        assert state.geo_points().empty
        assert state.metadata() is None


def test_shared_dataset_state_rebuilds_dataframe_and_geo_points() -> None:
    state = SharedDatasetState()
    state.update_from_payload(
        {
            "hasUploadedData": True,
            "bridgeId": "bridge-123",
            "datasetFingerprint": "dataset::abc",
            "datasetLabel": "Uploaded dataset",
            "sheetName": "uploaded",
            "fields": [
                {"fid": "study_id", "name": "Study ID"},
                {"fid": "latitude", "name": "Latitude"},
                {"fid": "longitude", "name": "Longitude"},
            ],
            "rows": [
                {"study_id": "A1", "latitude": 12.5, "longitude": -91.25},
                {"study_id": "B2", "latitude": None, "longitude": None},
            ],
            "sequence": 4,
        }
    )

    expected = pl.DataFrame(
        {
            "Study ID": ["A1", "B2"],
            "Latitude": [12.5, None],
            "Longitude": [-91.25, None],
        }
    )
    with reactive.isolate():
        assert state.data().equals(expected)
        assert len(state.geo_points()) == 1
        assert state.metadata()["sequence"] == 4


def test_shared_dataset_state_accepts_tuple_payloads_from_shiny() -> None:
    state = SharedDatasetState()
    state.update_from_payload(
        {
            "hasUploadedData": True,
            "datasetFingerprint": "dataset::tuple",
            "datasetLabel": "Uploaded dataset",
            "sheetName": "uploaded",
            "fields": (
                {"fid": "study_id", "name": "Study ID"},
                {"fid": "latitude", "name": "Latitude"},
                {"fid": "longitude", "name": "Longitude"},
            ),
            "rows": (
                {"study_id": "A1", "latitude": 12.5, "longitude": -91.25},
                {"study_id": "B2", "latitude": None, "longitude": None},
            ),
        }
    )

    with reactive.isolate():
        assert state.data() is not None
        assert state.data().columns == ["Study ID", "Latitude", "Longitude"]
        assert state.data().height == 2
        assert len(state.geo_points()) == 1


def test_shared_dataset_state_accepts_mixed_numeric_excel_columns() -> None:
    state = SharedDatasetState()
    state.update_from_payload(
        {
            "hasUploadedData": True,
            "datasetFingerprint": "dataset::excel-mixed-numeric",
            "datasetLabel": "Excel upload",
            "sheetName": "sheet1",
            "fields": [
                {"fid": "depth_cm", "name": "Depth (cm)"},
                {"fid": "latitude", "name": "Latitude"},
                {"fid": "longitude", "name": "Longitude"},
            ],
            "rows": [
                {"depth_cm": 26, "latitude": 12, "longitude": -75},
                {"depth_cm": 26.5, "latitude": 12.5, "longitude": -75.5},
                {"depth_cm": None, "latitude": None, "longitude": None},
            ],
        }
    )

    with reactive.isolate():
        assert state.data() is not None
        assert state.data()["Depth (cm)"].to_list() == [26.0, 26.5, None]
        assert len(state.geo_points()) == 2


def test_shared_dataset_state_preserves_empty_uploaded_dataset_shape() -> None:
    state = SharedDatasetState()
    state.update_from_payload(
        {
            "hasUploadedData": True,
            "datasetFingerprint": "dataset::empty",
            "datasetLabel": "Uploaded dataset",
            "sheetName": "uploaded",
            "fields": [
                {"fid": "latitude", "name": "Latitude"},
                {"fid": "longitude", "name": "Longitude"},
            ],
            "rows": [],
        }
    )

    with reactive.isolate():
        assert state.data() is not None
        assert state.data().columns == ["Latitude", "Longitude"]
        assert state.data().height == 0
        assert state.geo_points().empty
