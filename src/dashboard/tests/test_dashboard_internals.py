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
synthesis_inventory = import_module("utils.synthesis_inventory")


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


def test_eo_gallery_includes_dataset_specific_assets_and_reasoning() -> None:
    groups_by_dataset = eo_panel.EO_DATASET_EXAMPLE_GROUPS

    assert set(groups_by_dataset) == set(eo_panel.COLLECTIONS)

    for collection_name, groups in groups_by_dataset.items():
        figures = [figure for _, _, _, group_figures in groups for figure in group_figures]
        file_names = [file_name for _, file_name, _, _ in figures]
        text = " ".join(
            [collection_name]
            + [title for title, _, _, _ in groups]
            + [description for _, _, description, _ in groups]
            + [" ".join((run_label, title, summary)) for run_label, _, title, summary in figures]
        ).lower()

        assert len(groups) == 2
        assert len(figures) >= 2
        assert all(len(group) == 4 for group in groups)
        assert all(len(figure) == 4 for figure in figures)
        assert all(description for _, _, description, _ in groups)
        assert all(summary for _, _, _, summary in figures)
        assert all(file_name.startswith("eo_dataset_") for file_name in file_names)
        assert all((DASHBOARD_ROOT / "images" / file_name).is_file() for file_name in file_names)
        assert "raw" in text
        assert "derivative" in text

    html = str(eo_panel.eo_ui("eo_search"))
    assert "eo_example_gallery" in html
    assert "eo-example-gallery" in html
    assert "eo_dataset_emit_raw.png" not in html

    sentinel2_html = str(
        getattr(eo_panel, "_eo_example_gallery")(
            "Sentinel-2 L2A Surface Reflectance",
            groups_by_dataset["Sentinel-2 L2A Surface Reflectance"],
        )
    )
    assert "Raw and Derived EO Examples: Sentinel-2 L2A Surface Reflectance" in sentinel2_html
    assert "eo_dataset_sentinel2_raw_tci.png" in sentinel2_html
    assert "eo_dataset_sentinel2_derivatives.png" in sentinel2_html
    assert "eo_dataset_emit_raw.png" not in sentinel2_html
    assert "modeling notebook" in sentinel2_html.lower()


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
    extended_html = "\n".join(
        str(getattr(data_inventory, content_func)())
        for content_func in (
            "_synthesis_tables_tab_content",
            "_measurement_tab_content",
            "_methods_context_tab_content",
            "_geographic_tab_content",
        )
    )
    metric_html = str(inventory_metric("Synthesis Files", "7", "teal"))

    assert "inventory_overview_cards" in html
    assert "inventory-summary-grid" in html
    assert "inventory-summary-card" in metric_html
    assert "inventory-summary-card--teal" in metric_html
    assert "Synthesis Categories" in html
    assert "Top Studies by Synthesis Rows" in html
    assert "SOM Distribution" in html
    assert "Bulk Density Distribution" in html
    assert "Rows by Synthesis Table" in extended_html
    assert "Measurement Availability" in extended_html
    assert "Method Inventory" in extended_html
    assert "Country Contribution" in extended_html
    assert "synthesis_table_grid" in extended_html
    assert "measurement_coverage_grid" in extended_html
    assert "categorical_summary_grid" in extended_html
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
                            "polygons": [["10 -80 10 -79 11 -79 11 -80 10 -80"]],
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
        source_name="EMIT L2A Reflectance",
    )

    assert calls[0]["url"] == eo_panel.CMR_GRANULES_URL
    assert calls[0]["params"]["bounding_box"] == "-80.5,9.5,-78.5,11.5"
    assert "temporal" not in calls[0]["params"]
    assert results == [
        {
            "source": "EMIT L2A Reflectance",
            "granule_id": "EMIT_SCENE_001",
            "time_start": "2025-01-02 03:04:05",
            "time_end": "2025-01-02 03:14:05",
            "url": "https://lp-prod-protected.example/EMIT_L2A_RFL_scene.nc",
            "metadata_url": "",
            "preview_url": "https://lp-prod-public.example/EMIT_L2A_RFL_scene.png",
            "preview_kind": "derived PNG preview",
            "cloud_cover": "",
            "boxes": ["10 -80 11 -79"],
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-80.0, 10.0], [-79.0, 10.0], [-79.0, 11.0], [-80.0, 11.0], [-80.0, 10.0]]],
            },
        }
    ]


def test_cmr_polygons_to_geometry_parses_live_cmr_shape() -> None:
    geometry = getattr(eo_panel, "_cmr_polygons_to_geometry")(
        [
            [
                "26.7522621 -80.4531479 26.2169151 -81.0166702 25.6396103 -80.4682388 26.1749573 -79.9047165 26.7522621 -80.4531479"
            ]
        ]
    )

    assert geometry == {
        "type": "Polygon",
        "coordinates": [
            [
                [-80.4531479, 26.7522621],
                [-81.0166702, 26.2169151],
                [-80.4682388, 25.6396103],
                [-79.9047165, 26.1749573],
                [-80.4531479, 26.7522621],
            ]
        ],
    }


def test_search_stac_items_builds_unfiltered_payload_and_stops_at_initial_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    class FakeResponse:
        def __init__(self, payload: dict) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            if self.payload.get("token") == "next-page":
                return {
                    "features": [
                        {
                            "id": "S2A_002",
                            "bbox": [-80.0, 10.0, -79.0, 11.0],
                            "properties": {"datetime": "2024-06-02T15:30:00Z"},
                            "assets": {
                                "B04": {
                                    "href": "https://example.test/red.tif",
                                    "type": "image/tiff; application=geotiff",
                                }
                            },
                            "links": [{"rel": "self", "href": "https://example.test/item-2.json"}],
                        }
                    ]
                }

            return {
                "features": [
                    {
                        "id": "S2A_001",
                        "bbox": [-80.5, 9.5, -78.5, 11.5],
                        "properties": {
                            "datetime": "2024-06-01T15:30:00Z",
                            "eo:cloud_cover": 12.34,
                        },
                        "assets": {
                            "rendered_preview": {"href": "https://example.test/preview.png"},
                            "visual": {
                                "href": "https://sentinel2l2a01.blob.core.windows.net/path/visual.tif",
                                "type": "image/tiff; application=geotiff",
                            },
                        },
                        "links": [{"rel": "self", "href": "https://example.test/item.json"}],
                    }
                ],
                "links": [{"rel": "next", "href": eo_panel.STAC_SEARCH_URL, "body": {"token": "next-page"}}],
            }

    def fake_post(url: str, *, json: dict, timeout: int) -> FakeResponse:
        calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse(json)

    monkeypatch.setattr(eo_panel.requests, "post", fake_post)

    search_stac_items = getattr(eo_panel, "_search_stac_items")
    results = search_stac_items(
        (-80.5, 9.5, -78.5, 11.5),
        eo_panel.COLLECTIONS["Sentinel-2 L2A Surface Reflectance"],
        source_name="Sentinel-2 L2A Surface Reflectance",
    )

    assert calls[0]["url"] == eo_panel.STAC_SEARCH_URL
    assert calls[0]["json"] == {
        "collections": ["sentinel-2-l2a"],
        "bbox": [-80.5, 9.5, -78.5, 11.5],
        "limit": 100,
    }
    assert len(calls) == 1
    assert results == [
        {
            "source": "Sentinel-2 L2A Surface Reflectance",
            "granule_id": "S2A_001",
            "time_start": "2024-06-01 15:30:00",
            "time_end": "2024-06-01 15:30:00",
            "url": "https://sentinel2l2a01.blob.core.windows.net/path/visual.tif",
            "data_links": [{"label": "Visual", "url": "https://sentinel2l2a01.blob.core.windows.net/path/visual.tif"}],
            "metadata_url": "https://example.test/item.json",
            "preview_url": "https://example.test/preview.png",
            "preview_kind": "STAC rendered preview",
            "cloud_cover": 12.34,
            "boxes": ["9.5 -80.5 11.5 -78.5"],
            "geometry": None,
        },
    ]


def test_search_stac_items_supports_sentinel1_rtc_vv_vh_assets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "features": [
                    {
                        "id": "S1A_RTC_001",
                        "bbox": [-91.0, 29.0, -90.0, 30.0],
                        "properties": {"datetime": "2026-05-16T00:10:27Z"},
                        "assets": {
                            "rendered_preview": {"href": "https://example.test/sentinel-1-preview.png"},
                            "vv": {
                                "href": "https://sentinel1euwestrtc.blob.core.windows.net/path/vv.tif",
                                "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                            },
                            "vh": {
                                "href": "https://sentinel1euwestrtc.blob.core.windows.net/path/vh.tif",
                                "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                            },
                        },
                        "links": [{"rel": "self", "href": "https://example.test/s1-item.json"}],
                    }
                ]
            }

    def fake_post(url: str, *, json: dict, timeout: int) -> FakeResponse:
        calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(eo_panel.requests, "post", fake_post)

    search_stac_items = getattr(eo_panel, "_search_stac_items")
    results = search_stac_items(
        (-91.0, 29.0, -90.0, 30.0),
        eo_panel.COLLECTIONS["Sentinel-1 RTC Backscatter"],
        source_name="Sentinel-1 RTC Backscatter",
    )

    assert calls[0]["json"] == {
        "collections": ["sentinel-1-rtc"],
        "bbox": [-91.0, 29.0, -90.0, 30.0],
        "limit": 100,
    }
    assert results == [
        {
            "source": "Sentinel-1 RTC Backscatter",
            "granule_id": "S1A_RTC_001",
            "time_start": "2026-05-16 00:10:27",
            "time_end": "2026-05-16 00:10:27",
            "url": "https://sentinel1euwestrtc.blob.core.windows.net/path/vv.tif",
            "data_links": [
                {"label": "VV", "url": "https://sentinel1euwestrtc.blob.core.windows.net/path/vv.tif"},
                {"label": "VH", "url": "https://sentinel1euwestrtc.blob.core.windows.net/path/vh.tif"},
            ],
            "metadata_url": "https://example.test/s1-item.json",
            "preview_url": "https://example.test/sentinel-1-preview.png",
            "preview_kind": "STAC rendered preview",
            "cloud_cover": "",
            "boxes": ["29.0 -91.0 30.0 -90.0"],
            "geometry": None,
        }
    ]


def test_links_html_lazy_signs_planetary_computer_data_links() -> None:
    links_html = getattr(eo_panel, "_links_html")(
        "https://sentinel2l2a01.blob.core.windows.net/path/visual.tif",
        "https://example.test/item.json",
    )

    assert 'data-raw-url="https://sentinel2l2a01.blob.core.windows.net/path/visual.tif"' in links_html
    assert "signAndOpenPlanetaryComputerUrl(this)" in links_html
    assert "https://example.test/item.json" in links_html


def test_selected_result_rows_filters_map_overlays_to_checked_rows() -> None:
    parse_selected = getattr(eo_panel, "_parse_selected_row_indexes")
    selected_rows = getattr(eo_panel, "_selected_result_rows")
    rows = [
        {"granule_id": "first", "boxes": ["10 -80 11 -79"]},
        {"granule_id": "second", "boxes": ["11 -80 12 -79"]},
        {"granule_id": "third", "boxes": ["12 -80 13 -79"]},
    ]

    selected_indexes = parse_selected(("1", 1, "bad", 12, -1, "2"), len(rows))

    assert selected_indexes == [1, 2]
    assert parse_selected("0,2", len(rows)) == [0, 2]
    assert selected_rows(rows, selected_indexes) == [rows[1], rows[2]]


def test_eo_map_toggle_uses_closest_container_not_id_selector() -> None:
    panel_source = (DASHBOARD_ROOT / "panels" / "eo_panel.py").read_text(encoding="utf-8")

    assert 'onchange="window.updateSelectedGranuleRows(this)"' in panel_source
    assert "closest('.eo-granule-table-container')" in panel_source
    assert "querySelectorAll('.eo-row-select:checked')" in panel_source
    assert "querySelectorAll('#" not in panel_source
    assert '_session.ns("granule-table-container")' not in panel_source
    assert 'id="{table_container_id}"' not in panel_source
    assert "selected_indexes = set(selected_granule_rows.get())" not in panel_source
    assert 'checked = " checked" if row_index == 0 else ""' in panel_source


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


def test_synthesis_inventory_helpers_summarize_tables() -> None:
    depthseries = pd.DataFrame(
        {
            "study_id": ["study-a", "study-a", "study-b", "study-b"],
            "site_id": ["site-1", "site-1", "site-2", "site-2"],
            "core_id": ["core-1", "core-1", "core-2", "core-3"],
            "method_id": ["method-1", "method-1", "method-2", "method-2"],
            "depth_min": [0, 10, 30, 100],
            "depth_max": [10, 30, 100, 150],
            "dry_bulk_density": [0.8, 0.7, -0.1, 0.5],
            "fraction_carbon": [0.12, None, 1.2, 0.6],
            "fraction_organic_matter": [0.4, 0.3, 0.8, 0.4],
            "age": [5, None, None, None],
            "c14_age": [None, 100, None, None],
        }
    )
    cores = pd.DataFrame(
        {
            "study_id": ["study-a", "study-b", "study-b"],
            "site_id": ["site-1", "site-2", "site-2"],
            "core_id": ["core-1", "core-2", "core-3"],
            "country": ["United States", "", "Belize"],
            "habitat": ["marsh", "mangrove", ""],
            "latitude": [30.0, None, 17.0],
            "longitude": [-90.0, -88.0, -88.2],
            "year": [2020, None, 2021],
            "max_depth": [30, 150, 150],
        }
    )
    methods = pd.DataFrame(
        {
            "study_id": ["study-a", "study-b"],
            "method_id": ["method-1", "method-2"],
            "coring_method": ["push core", None],
            "roots_flag": ["included", ""],
            "fraction_carbon_method": ["elemental analyzer", None],
        }
    )
    tables = {
        "depthseries": depthseries,
        "cores": cores,
        "methods": methods,
        "impacts": pd.DataFrame(
            {
                "study_id": ["study-a", "study-b"],
                "impact_class": ["natural", "restored"],
            }
        ),
        "species": pd.DataFrame(
            {
                "study_id": ["study-a"],
                "species_code": ["Spartina patens"],
                "code_type": ["Species"],
            }
        ),
        "study_citations": pd.DataFrame(
            {
                "study_id": ["study-a", "study-b"],
                "publication_type": ["primary dataset", "journal article"],
                "year": [2023, 2024],
                "doi": [None, "10.example/example"],
                "url": [None, "https://example.test"],
            }
        ),
    }

    table_summary = synthesis_inventory.build_synthesis_table_summary(tables)
    measurement = synthesis_inventory.build_measurement_coverage(depthseries)
    depth_bins = synthesis_inventory.build_depth_bin_summary(depthseries)
    quality = synthesis_inventory.build_quality_summary(tables)
    categorical = synthesis_inventory.build_categorical_summary(tables)
    study_summary = synthesis_inventory.build_study_measurement_summary(depthseries, cores)

    depth_row = table_summary.set_index("Table").loc["Depth Series"]
    assert depth_row["Rows"] == 4
    assert depth_row["Cores"] == 3
    assert depth_row["Core/Site Join (%)"] == 100.0

    measurement_records = measurement.set_index("Measurement")["Records"].to_dict()
    assert measurement_records["Fraction Carbon + Bulk Density"] == 3
    assert measurement_records["Fraction Organic Matter + Bulk Density"] == 4
    assert measurement.set_index("Measurement").loc["Fraction Carbon + Bulk Density", "Percent"] == 75.0

    assert depth_bins.set_index("Depth Bin")["Records"].to_dict() == {
        "0-10 cm": 1,
        "10-30 cm": 1,
        "30-100 cm": 1,
        ">=100 cm": 1,
    }

    quality_counts = quality.set_index("Inventory Item")["Records"].to_dict()
    assert quality_counts["Fraction carbon outside 0-1"] == 1
    assert quality_counts["Carbon greater than organic matter"] == 2
    assert quality_counts["Missing coordinates"] == 1
    assert quality_counts["Missing DOI and URL"] == 1

    categorical_counts = categorical.set_index(["Variable", "Value"])["Records"].to_dict()
    assert categorical_counts[("Coring Method", "push core")] == 1
    assert categorical_counts[("Habitat", "marsh")] == 1
    assert categorical_counts[("Impact Class", "natural")] == 1
    assert categorical_counts[("Species", "Spartina patens")] == 1

    study_rows = study_summary.set_index("Study")
    assert study_rows.loc["study-a", "Depth Rows"] == 2
    assert study_rows.loc["study-a", "Carbon + BD Records"] == 1
    assert study_rows.loc["study-b", "Cores"] == 2
    assert study_rows.loc["study-b", "Carbon + BD Records"] == 2
