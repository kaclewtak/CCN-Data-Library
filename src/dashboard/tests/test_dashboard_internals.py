from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import pandas as pd
import pytest
from shiny import reactive
from shiny.types import SilentException

DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

dashboard_shared_dataset = import_module("dashboard_shared_dataset")
carbon_modeling = import_module("panels.carbon_modeling")
data_inventory = import_module("panels.data_inventory")
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


def test_carbon_modeling_comparisons_include_clean_and_expanded_descriptions() -> None:
    groups = carbon_modeling.COMPARISON_GROUPS
    figures = [figure for _, _, _, group_figures in groups for figure in group_figures]
    file_names = [file_name for _, file_name, _, _ in figures]

    assert len(groups) == 14
    assert len(figures) == 27
    assert all(len(group) == 4 for group in groups)
    assert all(len(figure) == 4 for figure in figures)
    assert all(description for _, _, _, description in groups)
    assert all(summary for _, _, _, summary in figures)
    assert all((DASHBOARD_ROOT / "images" / file_name).is_file() for file_name in file_names)

    layouts = {layout for _, layout, _, _ in groups}
    assert layouts == {"side-by-side"}
    assert any(file_name.startswith("carbon_modeling_clean_") for file_name in file_names)
    assert "carbon_modeling_15_original-vs-expanded-modeling-comparison.png" in file_names
    assert not any(file_name.startswith("carbon_modeling_05_") for file_name in file_names)

    extra_trees_group = next(group for group in groups if group[0] == "ExtraTrees tuning and per-study skill")
    assert len(extra_trees_group[3]) == 3
    assert any(figure[0] == "Reduced clean only" for figure in extra_trees_group[3])

    html = str(carbon_modeling.carbon_modeling_ui("carbon_modeling"))
    assert "Reduced clean" in html
    assert "Expanded" in html
    assert "carbon-modeling-figure-pair--side-by-side" in html
    assert "carbon-modeling-figure-pair--stacked" not in html
    assert "carbon-modeling-figure-pair--single" not in html
    assert "All notebook figures use the same side-by-side comparison layout" in html
    assert "best within-study R^2 drops to +0.115" in html


def test_dashboard_runtime_check_validates_assets_and_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict]] = []

    def fake_ensure_synthesis_data_dir(**kwargs):
        calls.append(("data", kwargs))
        return object()

    def fake_validate_pygwalker_assets():
        calls.append(("assets", {}))
        return ()

    monkeypatch.setattr(
        shiny_dashboard,
        "_dashboard_runtime_dependencies",
        lambda: (fake_ensure_synthesis_data_dir, fake_validate_pygwalker_assets),
    )
    shiny_dashboard.ensure_dashboard_runtime.cache_clear()
    try:
        shiny_dashboard.ensure_dashboard_runtime()
        shiny_dashboard.ensure_dashboard_runtime()
    finally:
        shiny_dashboard.ensure_dashboard_runtime.cache_clear()

    assert calls == [
        ("assets", {}),
        ("data", {"required": True, "timeout": 120.0}),
    ]


def test_dashboard_server_wires_explorer_state_to_downstream_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_getter = object()
    geo_getter = object()
    calls: list[tuple[str, dict]] = []
    runtime_calls = 0

    def fake_ensure_dashboard_runtime() -> None:
        nonlocal runtime_calls
        runtime_calls += 1

    def fake_call_module_server(_module_server, module_id: str, /, **kwargs):
        calls.append((module_id, kwargs))
        if module_id == "pygwalker_explorer":
            return {
                "data": data_getter,
                "all_geo_points": geo_getter,
                "metadata": object(),
            }
        return None

    monkeypatch.setattr(shiny_dashboard, "ensure_dashboard_runtime", fake_ensure_dashboard_runtime)
    monkeypatch.setattr(shiny_dashboard, "_call_module_server", fake_call_module_server)

    shiny_dashboard.server(object(), object(), object())

    assert runtime_calls == 1
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


def test_shared_dataset_state_accepts_mapping_shaped_upload_payload_and_metadata() -> None:
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

    assert qa_panel.validation_report_csv(pd.DataFrame(columns=warnings.columns)) == "No validation issues.\n"
    assert qa_panel.validation_report_csv(warnings) == "Row,Column,Value,Issue\n2,Carbon Fraction,1.2,Must be 0-1\n"


def test_qa_input_values_treats_absent_dynamic_inputs_as_empty() -> None:
    class FakeInput:
        def selected(self):
            return ("north america", "europe")

        def scalar(self):
            return "united states"

        def dynamic_missing(self):
            raise SilentException()

    fake_input = FakeInput()
    input_values = getattr(qa_panel, "_input_values")

    assert input_values(fake_input, "selected") == ["north america", "europe"]
    assert input_values(fake_input, "scalar") == ["united states"]
    assert input_values(fake_input, "dynamic_missing") == []
    assert input_values(fake_input, "not_registered") == []


def test_qa_map_controls_render_as_single_compact_row() -> None:
    map_controls = getattr(qa_panel, "_qa_map_controls")
    html = str(map_controls())

    assert "qa-map-control-row" in html
    assert "flex-wrap: nowrap" in html
    assert "width: auto !important" in html
    assert "qa-map-filter-control--optional:empty" in html
    assert "qa-map-filter-control--wide" in html
    assert "col_widths=[3, 3, 3, 3, 6, 6]" not in html


def test_data_inventory_summary_tab_combines_inventory_and_synthesis_context() -> None:
    summary_tab_content = getattr(data_inventory, "_summary_tab_content")
    inventory_metric = getattr(data_inventory, "_inventory_metric")
    html = str(summary_tab_content())
    metric_html = str(inventory_metric("Synthesis Files", "7", "teal"))

    assert "inventory_overview_cards" in html
    assert "inventory-summary-grid" in html
    assert "inventory-summary-card" in metric_html
    assert "inventory-summary-card--teal" in metric_html
    assert "Synthesis Categories" in html
    assert "Top Studies by Synthesis Rows" in html
    assert "SOM Distribution" in html
    assert "Bulk Density Distribution" in html
    assert "inventory_summary_cards" not in html
    assert "synthesis_summary_cards" not in html
    assert "Load Inventory" not in html


def test_data_inventory_counts_use_synthesis_categories_and_studies() -> None:
    category_info = getattr(data_inventory, "_synthesis_category_info")
    study_counts = getattr(data_inventory, "_synthesis_study_counts")
    synthesis = pd.DataFrame(
        {
            "habitat": ["marsh", "mangrove", "marsh", None, ""],
            "source_study": ["study-a", "study-b", "study-a", "study-c", "study-a"],
        }
    )

    category_label, category_values = category_info(synthesis)

    assert category_label == "Habitat Categories"
    assert category_values.value_counts().to_dict() == {"marsh": 2, "mangrove": 1}
    assert study_counts(synthesis, limit=2).to_dict() == {"study-a": 3, "study-b": 1}


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
                                {"href": "https://example.test/EMIT_L2A_RFL_scene.nc.dmrpp"},
                                {"href": "https://lp-prod-protected.example/EMIT_L2A_RFL_scene.nc"},
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


def test_build_inventory_df_reads_flat_synthesis_files(tmp_path: Path) -> None:
    synthesis_root = tmp_path / "data" / "CCN_synthesis"
    synthesis_root.mkdir(parents=True)
    (synthesis_root / "CCN_depthseries.csv").write_text("study_id,core_id\n", encoding="utf-8")
    (synthesis_root / "CCN_cores.csv").write_text("study_id,core_id\n", encoding="utf-8")
    (synthesis_root / "README.txt").write_text("ignored\n", encoding="utf-8")
    inventory = inventory_io.build_inventory_df(synthesis_root=synthesis_root)

    assert set(inventory["filename"]) == {"CCN_depthseries.csv", "CCN_cores.csv"}
    assert set(inventory["study_id"]) == {"CCN_synthesis"}
    assert set(inventory["stage"]) == {"derivative"}


def test_build_synthesis_df_loads_flat_depthseries_and_merges_core_area(
    tmp_path: Path,
) -> None:
    synthesis_root = tmp_path / "CCN_synthesis"
    synthesis_root.mkdir()
    (synthesis_root / "CCN_depthseries.csv").write_text(
        "study_id,site_id,core_id,fraction_carbon,dry_bulk_density\nstudy-a,site-1,core-1,0.12,0.8\n",
        encoding="utf-8",
    )
    (synthesis_root / "CCN_cores.csv").write_text(
        "study_id,site_id,core_id,country,habitat,latitude,longitude\n"
        "study-a,site-1,core-1,united states,marsh,30.0,-90.0\n",
        encoding="utf-8",
    )
    synthesis = synthesis_io.build_synthesis_df(pd.DataFrame(), synthesis_root=synthesis_root)

    assert synthesis.to_dict(orient="records") == [
        {
            "som": 0.12,
            "bulk_density": 0.8,
            "source_study": "study-a",
            "som_source": "fraction_carbon",
            "area": "united states",
            "habitat": "marsh",
            "latitude": 30.0,
            "longitude": -90.0,
        }
    ]
