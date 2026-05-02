from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import pandas as pd
import pytest
from shiny import reactive

DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

dashboard_shared_dataset = import_module("dashboard_shared_dataset")
eo_panel = import_module("panels.eo_panel")
qa_panel = import_module("panels.qa_panel")
shiny_dashboard = import_module("shiny_dashboard")
inventory_io = import_module("utils.inventory_io")
synthesis_io = import_module("utils.synthesis_io")


def test_dashboard_ui_contains_expected_workflow_tabs() -> None:
    html = str(shiny_dashboard.app_ui)

    for label in (
        "Data Explorer",
        "QA Dashboard",
        "Satellite Search",
        "Carbon Modeling",
        "Data Inventory",
        "Metadata",
    ):
        assert label in html
    assert "Dashboard ready" in html


def test_dashboard_server_wires_explorer_state_to_downstream_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_getter = object()
    geo_getter = object()
    calls: list[tuple[str, dict]] = []

    def fake_call_module_server(_module_server, module_id: str, /, **kwargs):
        calls.append((module_id, kwargs))
        if module_id == "pygwalker_explorer":
            return {
                "data": data_getter,
                "all_geo_points": geo_getter,
                "metadata": object(),
            }
        return None

    monkeypatch.setattr(shiny_dashboard, "_call_module_server", fake_call_module_server)

    shiny_dashboard.server(object(), object(), object())

    assert [module_id for module_id, _ in calls] == [
        "pygwalker_explorer",
        "eo_search",
        "inventory",
        "qa_dashboard",
    ]
    assert calls[1][1]["table_points_getter"] is geo_getter
    assert calls[3][1]["data_getter"] is data_getter


def test_spreadsheet_snapshot_to_dataframe_uniquifies_upload_column_labels() -> None:
    dataframe = dashboard_shared_dataset.spreadsheet_snapshot_to_dataframe(
        fields=[
            {"fid": "carbon_a", "name": "Carbon"},
            {"fid": "carbon_b", "name": "Carbon"},
            {"fid": "", "name": ""},
        ],
        rows=[{"carbon_a": 0.12, "carbon_b": 0.14, "column_3": "fallback"}],
    )

    assert dataframe.columns == ["Carbon", "Carbon_2", "column_3"]
    assert dataframe.row(0) == (0.12, 0.14, "fallback")


def test_shared_dataset_state_accepts_mapping_shaped_upload_payload_and_metadata() -> (
    None
):
    state = dashboard_shared_dataset.SharedDatasetState()
    state.update_from_payload(
        {
            "hasUploadedData": True,
            "datasetFingerprint": "dataset::csv-upload",
            "datasetLabel": "Imported CSV",
            "sheetName": "uploaded",
            "fileName": "cores.csv",
            "source": "file-import",
            "worksheetName": "Sheet1",
            "fields": {
                "0": {"fid": "lat", "name": "Latitude"},
                "1": {"fid": "lon", "name": "Longitude"},
            },
            "rows": {
                "1": {"lat": 32.1, "lon": -78.4},
                "0": {"lat": 31.5, "lon": -77.9},
            },
        }
    )

    with reactive.isolate():
        assert state.data().columns == ["Latitude", "Longitude"]
        assert state.data()["Latitude"].to_list() == [31.5, 32.1]
        assert len(state.geo_points()) == 2
        assert state.metadata()["file_name"] == "cores.csv"
        assert state.metadata()["source"] == "file-import"
        assert state.metadata()["worksheet_name"] == "Sheet1"


def test_validation_report_csv_download_content() -> None:
    warnings = pd.DataFrame(
        {
            "Row": [2],
            "Column": ["Carbon Fraction"],
            "Value": [1.2],
            "Issue": ["Must be 0-1"],
        }
    )

    assert (
        qa_panel.validation_report_csv(pd.DataFrame(columns=warnings.columns))
        == "No validation issues.\n"
    )
    assert (
        qa_panel.validation_report_csv(warnings)
        == "Row,Column,Value,Issue\n2,Carbon Fraction,1.2,Must be 0-1\n"
    )


def test_search_granules_extracts_download_and_preview_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "feed": {
                    "entry": [
                        {
                            "producer_granule_id": "EMIT_SCENE_001",
                            "time_start": "2025-01-02T03:04:05Z",
                            "time_end": "2025-01-02T03:14:05Z",
                            "boxes": ["10 -80 11 -79"],
                            "links": [
                                {
                                    "href": "https://example.test/EMIT_L2A_RFL_scene.nc.dmrpp"
                                },
                                {
                                    "href": "https://lp-prod-protected.example/EMIT_L2A_RFL_scene.nc"
                                },
                                {"href": "https://example.test/OTHER_scene.nc"},
                            ],
                        }
                    ]
                }
            }

    def fake_get(url: str, *, params: dict, timeout: int) -> FakeResponse:
        calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(eo_panel.requests, "get", fake_get)

    search_granules = getattr(eo_panel, "_search_granules")
    results = search_granules(
        (-80.5, 9.5, -78.5, 11.5),
        eo_panel.COLLECTIONS["EMIT L2A Reflectance"],
    )

    assert calls[0]["url"] == eo_panel.CMR_GRANULES_URL
    assert calls[0]["params"]["bounding_box"] == "-80.5,9.5,-78.5,11.5"
    assert results == [
        {
            "granule_id": "EMIT_SCENE_001",
            "time_start": "2025-01-02 03:04:05",
            "time_end": "2025-01-02 03:14:05",
            "url": "https://lp-prod-protected.example/EMIT_L2A_RFL_scene.nc",
            "preview_url": "https://lp-prod-public.example/EMIT_L2A_RFL_scene.png",
            "boxes": ["10 -80 11 -79"],
        }
    ]


def test_get_bounding_box_adds_expected_buffer() -> None:
    points = pd.DataFrame({"latitude": [10.0, 11.0], "longitude": [-80.0, -79.0]})
    get_bounding_box = getattr(eo_panel, "_get_bounding_box")

    assert get_bounding_box(points) == (-80.5, 9.5, -78.5, 11.5)


def test_build_inventory_df_reads_flat_synthesis_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    synthesis_root = tmp_path / "data" / "CCN_synthesis"
    synthesis_root.mkdir(parents=True)
    (synthesis_root / "CCN_depthseries.csv").write_text(
        "study_id,core_id\n", encoding="utf-8"
    )
    (synthesis_root / "CCN_cores.csv").write_text(
        "study_id,core_id\n", encoding="utf-8"
    )
    (synthesis_root / "README.txt").write_text("ignored\n", encoding="utf-8")
    inventory = inventory_io.build_inventory_df(synthesis_root=synthesis_root)

    assert set(inventory["filename"]) == {"CCN_depthseries.csv", "CCN_cores.csv"}
    assert set(inventory["study_id"]) == {"CCN_synthesis"}
    assert set(inventory["stage"]) == {"derivative"}


def test_build_synthesis_df_loads_flat_depthseries_and_merges_core_area(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    synthesis_root = tmp_path / "CCN_synthesis"
    synthesis_root.mkdir()
    (synthesis_root / "CCN_depthseries.csv").write_text(
        "study_id,site_id,core_id,fraction_carbon,dry_bulk_density\n"
        "study-a,site-1,core-1,0.12,0.8\n",
        encoding="utf-8",
    )
    (synthesis_root / "CCN_cores.csv").write_text(
        "study_id,site_id,core_id,country,habitat,latitude,longitude\n"
        "study-a,site-1,core-1,united states,marsh,30.0,-90.0\n",
        encoding="utf-8",
    )
    synthesis = synthesis_io.build_synthesis_df(
        pd.DataFrame(), synthesis_root=synthesis_root
    )

    assert synthesis.to_dict(orient="records") == [
        {
            "som": 0.12,
            "bulk_density": 0.8,
            "source_study": "study-a",
            "som_source": "fraction_carbon",
            "area": "united states",
            "latitude": 30.0,
            "longitude": -90.0,
        }
    ]
