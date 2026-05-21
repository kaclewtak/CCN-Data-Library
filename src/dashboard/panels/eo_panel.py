from __future__ import annotations

import json
from collections.abc import Callable
from html import escape

import pandas as pd
import requests
from shiny import module, reactive, render, ui

# Satellite earth observation sources. EMIT and Sentinel products are prioritized
# because they are used directly in the modeling notebooks and can expose previews.

COLLECTIONS = {
    "EMIT L2A Reflectance": {
        "backend": "cmr",
        "short_name": "EMITL2ARFL",
        "version": "001",
        "provider": "LPCLOUD",
        "file_filter": "EMIT_L2A_RFL",
        "ext": ".nc",
        "color": "#e05c00",
        "model_relevance": "EMIT hyperspectral features",
        "previewable": True,
    },
    "Sentinel-2 L2A Surface Reflectance": {
        "backend": "stac",
        "collection": "sentinel-2-l2a",
        "provider": "Planetary Computer",
        "color": "#2f7d32",
        "model_relevance": "Sentinel-2 NDVI features",
        "asset_keys": ["visual", "B08", "B04", "B03", "B02"],
        "asset_labels": {"visual": "Visual", "B08": "B08", "B04": "B04", "B03": "B03", "B02": "B02"},
        "previewable": True,
    },
    "Sentinel-1 RTC Backscatter": {
        "backend": "stac",
        "collection": "sentinel-1-rtc",
        "provider": "Planetary Computer",
        "color": "#8a5a00",
        "model_relevance": "Sentinel-1 VV/VH backscatter features",
        "asset_keys": ["vv", "vh", "hh", "hv"],
        "asset_labels": {"vv": "VV", "vh": "VH", "hh": "HH", "hv": "HV"},
        "previewable": True,
    },
    "PACE OCI L2 Ocean Color (AOP)": {
        "backend": "cmr",
        "short_name": "PACE_OCI_L2_AOP_NRT",
        "version": "3.1",
        "provider": "OB_CLOUD",
        "file_filter": None,
        "ext": ".nc",
        "color": "#0077bb",
        "model_relevance": "Current EO panel source",
        "previewable": True,
    },
    "PACE OCI L2 Inherent Optical Properties": {
        "backend": "cmr",
        "short_name": "PACE_OCI_L2_IOP_NRT",
        "version": "3.1",
        "provider": "OB_CLOUD",
        "file_filter": None,
        "ext": ".nc",
        "color": "#009966",
        "model_relevance": "Current EO panel source",
        "previewable": True,
    },
}

CMR_GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
STAC_SEARCH_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PLANETARY_COMPUTER_SIGN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"

EOExampleFigure = tuple[str, str, str, str]
EOExampleGroup = tuple[str, str, str, list[EOExampleFigure]]

EO_DATASET_EXAMPLE_GROUPS: dict[str, list[EOExampleGroup]] = {
    "EMIT L2A Reflectance": [
        (
            "Raw EMIT reflectance",
            "single",
            "This preview shows the downloaded EMIT L2A reflectance cube before feature engineering.",
            [
                (
                    "Raw data",
                    "eo_dataset_emit_raw.png",
                    "EMIT L2A reflectance preview",
                    "The false-color reflectance view confirms the hyperspectral file is readable and gives spatial "
                    "context for later spectral features.",
                ),
            ],
        ),
        (
            "Derivative examples and modeling relevance",
            "two-up",
            "The modeling notebooks use spectral smoothing, SNV-style normalization, derivatives, and continuum "
            "removal to reduce baseline effects and emphasize absorption-shape information before modeling.",
            [
                (
                    "Spectral derivatives",
                    "eo_dataset_emit_spectral_derivatives.png",
                    "Raw, smoothed, SNV, derivative, and continuum views",
                    "Useful when the model should learn shape and absorption differences rather than raw brightness "
                    "alone; this follows the spectral preprocessing pattern used in the modeling notebooks.",
                ),
                (
                    "Spatial derivatives",
                    "eo_dataset_emit_spatial_derivatives.png",
                    "NDVI, NDWI, SWIR carbon contrast, and red-edge slope",
                    "These map layers translate hyperspectral bands into vegetation, water, SWIR, and red-edge "
                    "contrasts that can be compared with site footprints and carbon covariates.",
                ),
            ],
        ),
    ],
    "Sentinel-2 L2A Surface Reflectance": [
        (
            "Raw Sentinel-2 products",
            "two-up",
            "The raw examples separate the display-oriented true-color image from calibrated optical bands that "
            "support index and derivative products.",
            [
                (
                    "Raw data",
                    "eo_dataset_sentinel2_raw_tci.png",
                    "Sentinel-2 true-color image",
                    "The TCI product gives quick visual context for clouds, water, reefs, and land cover, but it is not "
                    "the best source for calibrated spectral modeling.",
                ),
                (
                    "Raw bands",
                    "eo_dataset_sentinel2_raw_bands.png",
                    "Blue, green, red, and NIR bands",
                    "The individual L2A bands expose calibrated optical channels that feed vegetation indices and "
                    "spectral-derivative features.",
                ),
            ],
        ),
        (
            "Derivative examples and modeling relevance",
            "two-up",
            "The modeling notebooks rely on normalized indices and derivative-style spectral transforms because "
            "they reduce illumination and baseline differences while preserving vegetation and surface contrasts.",
            [
                (
                    "Band derivatives",
                    "eo_dataset_sentinel2_derivatives.png",
                    "NDVI, green NDVI, SNV, and first derivative",
                    "NDVI/GNDVI summarize vegetation vigor, while SNV and first derivatives mirror the modeling "
                    "notebook approach for suppressing brightness shifts before learning.",
                ),
                (
                    "Visual derivatives",
                    "eo_dataset_sentinel2_tci_derivatives.png",
                    "Luminance, excess green, edge, texture, and green-red index",
                    "These are fallback visual-context features when only RGB display imagery is available; texture and "
                    "edges can still describe spatial structure around sample footprints.",
                ),
            ],
        ),
    ],
    "Sentinel-1 RTC Backscatter": [
        (
            "Raw Sentinel-1 RTC backscatter",
            "single",
            "The raw radar examples show the VV and VH backscatter channels in dB after RTC processing.",
            [
                (
                    "Raw data",
                    "eo_dataset_sentinel1_raw.png",
                    "VV and VH backscatter channels",
                    "Radar backscatter complements optical data because it can respond to roughness, structure, and "
                    "moisture even when visible imagery is limited by clouds.",
                ),
            ],
        ),
        (
            "Derivative examples and modeling relevance",
            "single",
            "Radar ratio products compress paired polarizations into interpretable features that can complement "
            "the optical and hyperspectral predictors used by the modeling notebooks.",
            [
                (
                    "Radar derivatives",
                    "eo_dataset_sentinel1_derivatives.png",
                    "VV/VH contrast and radar vegetation index",
                    "VV minus VH and RVI highlight canopy structure, roughness, and moisture-linked radar responses "
                    "that may improve models where optical signals are ambiguous.",
                ),
            ],
        ),
    ],
    "PACE OCI L2 Ocean Color (AOP)": [
        (
            "Raw PACE AOP ocean color",
            "single",
            "This preview shows the downloaded PACE OCI AOP product before deriving spectral or ocean-color ratios.",
            [
                (
                    "Raw data",
                    "eo_dataset_pace_aop_raw.png",
                    "PACE AOP remote-sensing reflectance preview",
                    "The raw reflectance view gives ocean-color context and confirms the NetCDF product can be decoded "
                    "into a spatial image layer.",
                ),
            ],
        ),
        (
            "Derivative examples and modeling relevance",
            "two-up",
            "PACE AOP derivatives convert the spectral ocean-color product into noise-controlled spectra and "
            "bio-optical ratios that are easier to compare with downstream modeling covariates.",
            [
                (
                    "Spectral derivatives",
                    "eo_dataset_pace_aop_spectral_derivatives.png",
                    "Raw, smoothed, SNV, derivative, and continuum views",
                    "This follows the modeling notebook reasoning: smoothing controls noise, SNV normalizes scale, and "
                    "derivatives emphasize shape changes in the spectrum.",
                ),
                (
                    "Spatial derivatives",
                    "eo_dataset_pace_aop_spatial_derivatives.png",
                    "Blue/green Rrs, NDCI, turbidity, and visible slope",
                    "These ratios and slopes are logical ocean-color features for chlorophyll, turbidity, and water-color "
                    "gradients near the sampled region.",
                ),
            ],
        ),
    ],
    "PACE OCI L2 Inherent Optical Properties": [
        (
            "Raw PACE IOP bio-optical product",
            "single",
            "This preview shows the downloaded PACE OCI IOP product before deriving bio-optical ratios.",
            [
                (
                    "Raw data",
                    "eo_dataset_pace_iop_raw.png",
                    "PACE IOP bio-optical preview",
                    "The raw product gives spatial context for absorption, backscatter, and attenuation variables that "
                    "can be summarized into model-friendly derivatives.",
                ),
            ],
        ),
        (
            "Derivative examples and modeling relevance",
            "two-up",
            "PACE IOP derivatives summarize bio-optical shape and ratio information so the model can use relative "
            "water-property contrasts instead of only raw variable magnitudes.",
            [
                (
                    "Spectral derivatives",
                    "eo_dataset_pace_iop_spectral_derivatives.png",
                    "Raw, smoothed, SNV, derivative, and continuum views",
                    "The same modeling notebook preprocessing logic applies here: normalize scale, smooth noise, and "
                    "highlight spectral-shape changes before learning.",
                ),
                (
                    "Spatial derivatives",
                    "eo_dataset_pace_iop_spatial_derivatives.png",
                    "aph, bb, Kd ratios, and absorption slope",
                    "These bio-optical ratios capture phytoplankton absorption, backscatter, attenuation, and spectral "
                    "slope patterns that are more compact than the raw NetCDF variables.",
                ),
            ],
        ),
    ],
}

EO_EXAMPLE_GROUPS = EO_DATASET_EXAMPLE_GROUPS["EMIT L2A Reflectance"]


# Helper functions
def _get_bounding_box(points_df: pd.DataFrame) -> tuple[float, float, float, float] | None:
    """Return (min_lon, min_lat, max_lon, max_lat) with 0.5-degree buffer."""
    if points_df.empty:
        return None
    buf = 0.5
    return (
        points_df["longitude"].min() - buf,
        points_df["latitude"].min() - buf,
        points_df["longitude"].max() + buf,
        points_df["latitude"].max() + buf,
    )


def _format_datetime(value: object) -> str:
    text = str(value or "")
    return text[:19].replace("T", " ")


def _cmr_preview_url(download_url: str) -> str:
    if "lp-prod-protected" in download_url:
        return download_url.replace("lp-prod-protected", "lp-prod-public").replace(".nc", ".png")
    if "ob.daac" in download_url.lower():
        return download_url.replace(".nc", ".png")
    return ""


def _first_link_href(links: list[dict], rels: set[str]) -> str:
    for link in links:
        rel = str(link.get("rel", "")).lower()
        if rel in rels and link.get("href"):
            return str(link["href"])
    return ""


def _bbox_to_cmr_box(bbox: list | tuple | None) -> list[str]:
    if not bbox or len(bbox) < 4:
        return []
    min_lon, min_lat, max_lon, max_lat = bbox[:4]
    return [f"{min_lat} {min_lon} {max_lat} {max_lon}"]


def _cmr_polygon_ring_to_coordinates(raw_ring: object) -> list[list[float]]:
    if not isinstance(raw_ring, str):
        return []

    parts = raw_ring.strip().split()
    if len(parts) < 6 or len(parts) % 2 != 0:
        return []

    coordinates = []
    for idx in range(0, len(parts), 2):
        try:
            lat = float(parts[idx])
            lon = float(parts[idx + 1])
        except ValueError:
            return []
        coordinates.append([lon, lat])

    if coordinates and coordinates[0] != coordinates[-1]:
        coordinates.append(coordinates[0])
    return coordinates


def _cmr_polygons_to_geometry(polygons: object) -> dict | None:
    if not isinstance(polygons, list):
        return None

    polygon_groups = []
    for polygon_group in polygons:
        ring_strings = polygon_group if isinstance(polygon_group, list) else [polygon_group]
        rings = []
        for ring_string in ring_strings:
            ring_coordinates = _cmr_polygon_ring_to_coordinates(ring_string)
            if ring_coordinates:
                rings.append(ring_coordinates)
        if rings:
            polygon_groups.append(rings)

    if not polygon_groups:
        return None
    if len(polygon_groups) == 1:
        return {"type": "Polygon", "coordinates": polygon_groups[0]}
    return {"type": "MultiPolygon", "coordinates": polygon_groups}


def _stac_preview_url(feature: dict) -> str:
    assets = feature.get("assets", {}) or {}
    for key in ("rendered_preview", "thumbnail", "preview", "overview"):
        asset = assets.get(key, {})
        if asset.get("href"):
            return str(asset["href"])

    for link in feature.get("links", []) or []:
        rel = str(link.get("rel", "")).lower()
        title = str(link.get("title", "")).lower()
        media_type = str(link.get("type", "")).lower()
        if link.get("href") and (
            rel in {"preview", "thumbnail"}
            or "preview" in title
            or "thumbnail" in title
            or media_type.startswith("image/")
        ):
            return str(link["href"])
    return ""


def _stac_data_links(feature: dict, source: dict) -> list[dict[str, str]]:
    assets = feature.get("assets", {}) or {}
    labels = source.get("asset_labels", {})
    links = []
    for key in source.get("asset_keys", ("visual", "B08", "B04", "B03", "B02")):
        asset = assets.get(key, {})
        if asset.get("href"):
            links.append({"label": str(labels.get(key, key.upper())), "url": str(asset["href"])})

    if links:
        return links

    for asset in assets.values():
        href = asset.get("href")
        media_type = str(asset.get("type", "")).lower()
        if href and ("geotiff" in media_type or str(href).lower().endswith((".tif", ".tiff"))):
            return [{"label": "Data", "url": str(href)}]
    return []


def _needs_planetary_computer_signing(url: str) -> bool:
    return bool(url and "blob.core.windows.net" in url and "sig=" not in url)


def _normalize_stac_feature(feature: dict, source_name: str, source: dict) -> dict:
    props = feature.get("properties", {}) or {}
    links = feature.get("links", []) or []
    preview_url = _stac_preview_url(feature)
    timestamp = props.get("datetime") or props.get("start_datetime") or ""
    data_links = _stac_data_links(feature, source)
    return {
        "source": source_name,
        "granule_id": feature.get("id", ""),
        "time_start": _format_datetime(timestamp),
        "time_end": _format_datetime(props.get("end_datetime") or timestamp),
        "url": data_links[0]["url"] if data_links else "",
        "data_links": data_links,
        "metadata_url": _first_link_href(links, {"self", "canonical", "parent"}),
        "preview_url": preview_url,
        "preview_kind": "STAC rendered preview" if preview_url else "",
        "cloud_cover": props.get("eo:cloud_cover", ""),
        "boxes": _bbox_to_cmr_box(feature.get("bbox")),
        "geometry": feature.get("geometry"),
    }


def _search_granules(
    bbox: tuple,
    collection: dict,
    source_name: str = "",
) -> list[dict]:
    """Query NASA CMR for granules within bounding box."""
    min_lon, min_lat, max_lon, max_lat = bbox
    params = {
        "short_name": collection["short_name"],
        "version": collection["version"],
        "provider": collection["provider"],
        "bounding_box": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "page_size": 100,
        "page_num": 1,
    }

    all_results = []
    while True:
        resp = requests.get(CMR_GRANULES_URL, params=params, timeout=15)
        resp.raise_for_status()
        entries = resp.json().get("feed", {}).get("entry", [])
        if not entries:
            break

        for e in entries:
            # Get main .nc download link
            file_filter = collection["file_filter"]
            ext = collection["ext"]
            urls = [
                lnk["href"]
                for lnk in e.get("links", [])
                if lnk.get("href", "").endswith(ext)
                and (file_filter is None or file_filter in lnk.get("href", ""))
                and "dmrpp" not in lnk.get("href", "")
            ]

            # Create image preview for EMIT and PACE
            preview_url = _cmr_preview_url(urls[0]) if urls else ""

            result = {
                "source": source_name,
                "granule_id": e.get("producer_granule_id", e.get("title", "")),
                "time_start": _format_datetime(e.get("time_start")),
                "time_end": _format_datetime(e.get("time_end")),
                "url": urls[0] if urls else "",
                "metadata_url": _first_link_href(e.get("links", []) or [], {"self", "via", "alternate"}),
                "preview_url": preview_url,
                "preview_kind": "derived PNG preview" if preview_url else "",
                "cloud_cover": e.get("cloud_cover", ""),
                "boxes": e.get("boxes") or [],
                "geometry": _cmr_polygons_to_geometry(e.get("polygons")),
            }
            all_results.append(result)

        # Last page
        if len(entries) < 100:
            break
        params["page_num"] += 1

    return all_results


def _search_stac_items(
    bbox: tuple,
    source: dict,
    source_name: str = "",
) -> list[dict]:
    """Query the first STAC page of EO items within bounding box."""
    min_lon, min_lat, max_lon, max_lat = bbox
    payload = {
        "collections": [source["collection"]],
        "bbox": [min_lon, min_lat, max_lon, max_lat],
        "limit": 100,
    }

    resp = requests.post(STAC_SEARCH_URL, json=payload, timeout=15)
    resp.raise_for_status()
    features = resp.json().get("features", [])
    return [_normalize_stac_feature(feature, source_name, source) for feature in features]


def _search_source(
    bbox: tuple,
    source_name: str,
    source: dict,
) -> list[dict]:
    if source["backend"] == "cmr":
        return _search_granules(
            bbox,
            source,
            source_name=source_name,
        )
    if source["backend"] == "stac":
        return _search_stac_items(
            bbox,
            source,
            source_name=source_name,
        )
    raise ValueError(f"Unsupported EO source backend: {source['backend']}")


def _links_html(data_url: str, metadata_url: str, data_links: list[dict[str, str]] | None = None) -> str:
    links = []
    source_links = data_links or ([{"label": "Data", "url": data_url}] if data_url else [])
    for data_link in source_links:
        link_url = data_link.get("url", "")
        if not link_url:
            continue
        label = escape(str(data_link.get("label") or "Data"))
        safe_url = escape(link_url, quote=True)
        if _needs_planetary_computer_signing(link_url):
            links.append(
                f'<a href="#" data-raw-url="{safe_url}" '
                'onclick="signAndOpenPlanetaryComputerUrl(this); return false;" '
                f'title="Sign and open {safe_url}">{label}</a>'
            )
        else:
            links.append(f'<a href="{safe_url}" target="_blank" title="{safe_url}">{label}</a>')
    if metadata_url:
        safe_metadata_url = escape(metadata_url, quote=True)
        links.append(f'<a href="{safe_metadata_url}" target="_blank" title="{safe_metadata_url}">Metadata</a>')
    return " | ".join(links) if links else "—"


def _cloud_cover_label(value: object) -> str:
    if value in (None, ""):
        return "—"
    text = str(value)
    try:
        return f"{float(text):.1f}%"
    except (TypeError, ValueError):
        return escape(text)


def _parse_selected_row_indexes(value: object, row_count: int) -> list[int]:
    if isinstance(value, str):
        raw_indexes = value.split(",") if value else []
    elif isinstance(value, (list, tuple, set)):
        raw_indexes = value
    else:
        return []

    selected = []
    for raw_index in raw_indexes:
        try:
            index = int(raw_index)
        except (TypeError, ValueError):
            continue
        if 0 <= index < row_count and index not in selected:
            selected.append(index)
    return selected


def _selected_result_rows(rows: list[dict], selected_indexes: list[int]) -> list[dict]:
    selected = set(selected_indexes)
    return [row for index, row in enumerate(rows) if index in selected]


def _eo_example_figure_card(run_label: str, file_name: str, title: str, description: str):
    return ui.div(
        ui.div(
            ui.tags.img(
                src=f"/images/{file_name}",
                alt=title,
                loading="lazy",
                class_="eo-example-img",
            ),
            class_="eo-example-media",
        ),
        ui.div(
            ui.div(run_label, class_="eo-example-run-label"),
            ui.div(title, class_="eo-example-figure-title"),
            ui.p(description, class_="eo-example-figure-description"),
            class_="eo-example-caption",
        ),
        class_="eo-example-figure-card",
    )


def _eo_example_group(title: str, layout: str, description: str, figures: list[EOExampleFigure]):
    return ui.div(
        ui.div(
            ui.h4(title, class_="eo-example-group-title"),
            ui.p(description, class_="eo-example-group-description"),
            class_="eo-example-group-header",
        ),
        ui.div(
            *[_eo_example_figure_card(*figure) for figure in figures],
            class_=f"eo-example-grid eo-example-grid--{layout}",
        ),
        class_="eo-example-group",
    )


def _eo_example_gallery(collection_name: str, groups: list[EOExampleGroup]):
    return ui.card(
        ui.card_header(f"Raw and Derived EO Examples: {collection_name}"),
        ui.div(
            ui.p(
                "These examples update with the selected dataset. They show what the downloaded raw satellite "
                "product looks like, then show derivative products and why the modeling notebooks use them before "
                "building features.",
                class_="eo-example-lede",
            ),
            *[_eo_example_group(*group) for group in groups],
            class_="eo-example-gallery",
        ),
    )


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
@module.ui
def eo_ui():
    return ui.TagList(
        ui.tags.style("""
            .eo-example-gallery {
                display: flex;
                flex-direction: column;
                gap: 12px;
                padding: 0.2rem 0 0.25rem;
            }
            .eo-example-lede {
                margin: 0;
                max-width: 980px;
                color: var(--ccn-serc-muted);
                font-size: 0.88rem;
                line-height: 1.35;
            }
            .eo-example-group {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .eo-example-group-header {
                display: grid;
                grid-template-columns: minmax(180px, 260px) minmax(0, 1fr);
                gap: 12px;
                align-items: baseline;
                max-width: none;
                padding: 0 2px;
            }
            .eo-example-group-title {
                margin: 0;
                color: #203548;
                font-size: 0.96rem;
                font-weight: 800;
            }
            .eo-example-group-description {
                margin: 0;
                color: #526273;
                font-size: 0.8rem;
                line-height: 1.35;
            }
            .eo-example-grid {
                display: grid;
                gap: 10px;
                align-items: start;
            }
            .eo-example-grid--two-up {
                grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
            }
            .eo-example-grid--three-up {
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            }
            .eo-example-grid--single {
                grid-template-columns: minmax(0, 1fr);
            }
            .eo-example-figure-card {
                overflow: hidden;
                border: 1px solid var(--ccn-serc-line);
                border-radius: 6px;
                background: #fff;
            }
            .eo-example-grid--single .eo-example-figure-card {
                display: grid;
                grid-template-columns: minmax(320px, 0.62fr) minmax(240px, 0.38fr);
            }
            .eo-example-media {
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 220px;
                height: 360px;
                padding: 6px;
                background: #f7f9fa;
                border-bottom: 1px solid var(--ccn-serc-line);
            }
            .eo-example-grid--single .eo-example-media {
                height: 390px;
                border-right: 1px solid var(--ccn-serc-line);
                border-bottom: 0;
            }
            .eo-example-img {
                display: block;
                width: auto;
                height: auto;
                max-width: 100%;
                max-height: 100%;
            }
            .eo-example-caption {
                padding: 9px 10px 10px;
            }
            .eo-example-run-label {
                color: var(--ccn-serc-muted);
                font-size: 0.68rem;
                font-weight: 800;
                text-transform: uppercase;
            }
            .eo-example-figure-title {
                margin-top: 3px;
                color: #203548;
                font-size: 0.88rem;
                font-weight: 800;
                line-height: 1.25;
            }
            .eo-example-figure-description {
                margin: 4px 0 0;
                color: #526273;
                font-size: 0.76rem;
                line-height: 1.32;
            }
            @media (max-width: 900px) {
                .eo-example-group-header,
                .eo-example-grid--single .eo-example-figure-card {
                    grid-template-columns: 1fr;
                }
                .eo-example-grid--single .eo-example-media {
                    height: 330px;
                    border-right: 0;
                    border-bottom: 1px solid var(--ccn-serc-line);
                }
                .eo-example-media {
                    height: 300px;
                }
            }
        """),
        ui.panel_title("Satellite L2 Granule Search"),
        ui.card(
            ui.card_header("Search Controls"),
            ui.div(
                ui.input_select(
                    "collection",
                    "Dataset:",
                    choices=list(COLLECTIONS.keys()),
                    width="350px",
                ),
                ui.input_action_button(
                    "search_eo",
                    "Search from Uploaded Points",
                    class_="btn-primary",
                ),
                ui.output_text("search_status"),
                style="display: flex; align-items: center; gap: 1rem; padding: 0.5rem; flex-wrap: wrap;",
            ),
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header("Matching Granules"),
                ui.output_ui("granule_table"),
            ),
            ui.card(
                ui.card_header("Coverage Map"),
                ui.output_ui("coverage_map"),
            ),
            col_widths=[6, 6],
        ),
        ui.output_ui("eo_example_gallery"),
    )


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
@module.server
def eo_server(input_, _output, _session, table_points_getter: Callable[[], pd.DataFrame]):
    granules = reactive.Value([])
    selected_granule_rows = reactive.Value([])
    status = reactive.Value("Select a dataset and click 'Search'.")
    granule_color = reactive.Value("#e05c00")

    # Search trigger from EO collections

    @reactive.effect
    @reactive.event(input_.search_eo)
    def _do_search():
        points = table_points_getter()
        if points is None or points.empty:
            status.set("No points found. Import a dataset in Data Explorer with latitude/longitude columns first.")
            return

        bbox = _get_bounding_box(points)
        if bbox is None:
            status.set("Could not compute bounding box from points.")
            return

        collection_name = input_.collection()
        collection = COLLECTIONS[collection_name]
        granule_color.set(collection["color"])
        status.set(f"Searching {collection_name}...")

        try:
            results = _search_source(
                bbox,
                collection_name,
                collection,
            )
            selected_granule_rows.set([0] if results else [])
            granules.set(results)
            status.set(f"Found {len(results)} item(s)." if results else "No matching items found for this region.")
        except requests.RequestException as e:
            status.set(f"Error: {e}")
        except ValueError as e:
            status.set(str(e))

    @reactive.effect
    @reactive.event(input_.selected_granule_rows)
    def _update_selected_granule_rows():
        selected_granule_rows.set(_parse_selected_row_indexes(input_.selected_granule_rows(), len(granules.get())))

    @render.text
    def search_status():
        return status.get()

    @render.ui
    def eo_example_gallery():
        collection_name = input_.collection()
        groups = EO_DATASET_EXAMPLE_GROUPS.get(collection_name, [])
        return _eo_example_gallery(collection_name, groups)

    # Granule results table

    @render.ui
    def granule_table():
        rows = granules.get()
        if not rows:
            return ui.p("No results yet.", style="padding: 1rem; color: #666;")

        td = 'style="padding: 4px 8px; border-bottom: 1px solid #eee;"'
        select_td = 'style="padding: 4px 8px; border-bottom: 1px solid #eee; text-align: center;"'
        selected_input_id = json.dumps(_session.ns("selected_granule_rows"))

        rows_html = ""
        for row_index, r in enumerate(rows):
            url = r.get("url", "")
            metadata_url = r.get("metadata_url", "")
            preview = r.get("preview_url", "")

            links = _links_html(url, metadata_url, r.get("data_links"))

            # Thumbnail with lightbox on click
            thumb = (
                (
                    f'<img src="{escape(preview, quote=True)}" '
                    f'style="height:48px; width:auto; border-radius:3px; cursor:pointer;" '
                    f"onclick='showLightbox({json.dumps(preview)})' "
                    f"onerror=\"this.style.display='none'\" />"
                )
                if preview
                else "—"
            )
            checked = " checked" if row_index == 0 else ""
            item_label = escape(str(r.get("granule_id", f"row {row_index + 1}")), quote=True)

            rows_html += f"""
            <tr>
                <td {select_td}>
                    <input type="checkbox" class="eo-row-select" value="{row_index}"
                           aria-label="Show footprint for {item_label}"
                           onchange="window.updateSelectedGranuleRows(this)"{checked} />
                </td>
                <td {td}>{thumb}</td>
                <td {td}>{escape(str(r.get("source", "")))}</td>
                <td {td}>{escape(str(r.get("granule_id", "")))}</td>
                <td {td}>{escape(str(r.get("time_start", "")))}</td>
                <td {td}>{escape(str(r.get("time_end", "")))}</td>
                <td {td}>{_cloud_cover_label(r.get("cloud_cover"))}</td>
                <td {td}>{links}</td>
            </tr>
            """

        table_html = f"""
        <!-- Lightbox overlay — clicking outside image or pressing Escape closes it -->
        <div id="lightbox" onclick="hideLightbox()"
             style="display:none; position:fixed; top:0; left:0; width:100%; height:100%;
                    background:rgba(0,0,0,0.75); z-index:9999;
                    align-items:center; justify-content:center;">
            <div onclick="event.stopPropagation()"
                 style="position:relative; max-width:90vw; max-height:90vh;">
                <button onclick="hideLightbox()"
                        style="position:absolute; top:-36px; right:0; background:white;
                               border:none; border-radius:4px; padding:4px 12px;
                               cursor:pointer; font-size:1rem;">
                    ✕ Close
                </button>
                <img id="lightbox-img" src=""
                     style="max-width:90vw; max-height:85vh; border-radius:6px; display:block;" />
            </div>
        </div>
        <script>
        function showLightbox(src) {{
            document.getElementById('lightbox-img').src = src;
            document.getElementById('lightbox').style.display = 'flex';
        }}
        function hideLightbox() {{
            document.getElementById('lightbox').style.display = 'none';
            document.getElementById('lightbox-img').src = '';
        }}
        window.updateSelectedGranuleRows = function(changedEl) {{
            if (!window.Shiny || !Shiny.setInputValue) return;
            var container = changedEl && changedEl.closest
                ? changedEl.closest('.eo-granule-table-container')
                : null;
            var scope = container || document;
            var selected = Array.from(
                scope.querySelectorAll('.eo-row-select:checked')
            ).map(function(el) {{ return Number(el.value); }});
            Shiny.setInputValue({selected_input_id}, selected, {{ priority: 'event' }});
        }};
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') hideLightbox();
        }});
        async function signAndOpenPlanetaryComputerUrl(linkEl) {{
            var rawUrl = linkEl.getAttribute('data-raw-url');
            var newWindow = window.open('about:blank', '_blank');
            if (!newWindow) {{
                window.alert('Enable pop-ups to open the Sentinel data link.');
                return;
            }}

            var originalText = linkEl.textContent;
            linkEl.textContent = 'Signing...';
            try {{
                var signUrl = {json.dumps(PLANETARY_COMPUTER_SIGN_URL)} + '?href=' + encodeURIComponent(rawUrl);
                var response = await fetch(signUrl);
                if (!response.ok) throw new Error('HTTP ' + response.status);
                var payload = await response.json();
                newWindow.location.href = payload.href || rawUrl;
            }} catch (err) {{
                newWindow.close();
                window.alert('Could not prepare the Sentinel data link. Try rerunning the search. ' + err.message);
            }} finally {{
                linkEl.textContent = originalText || 'Data';
            }}
        }}
        </script>

        <div class="eo-granule-table-container" style="overflow: auto; max-height: 600px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">
                <thead>
                    <tr style="background: #f5f5f5; text-align: left;">
                        <th style="padding: 6px 8px; text-align: center;">Map</th>
                        <th style="padding: 6px 8px;">Preview</th>
                        <th style="padding: 6px 8px;">Source</th>
                        <th style="padding: 6px 8px;">Item ID</th>
                        <th style="padding: 6px 8px;">Start</th>
                        <th style="padding: 6px 8px;">End</th>
                        <th style="padding: 6px 8px;">Cloud</th>
                        <th style="padding: 6px 8px;">Links</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
        """
        return ui.HTML(table_html)

    # Coverage map

    @render.ui
    def coverage_map():
        rows = granules.get()
        points = table_points_getter()

        if not rows and (points is None or points.empty):
            return ui.p("No granules to display.", style="padding: 1rem; color: #666;")

        mapped_rows = _selected_result_rows(rows, selected_granule_rows.get())
        geometry_js = json.dumps([r["geometry"] for r in mapped_rows if r.get("geometry")])
        boxes_js = json.dumps([r["boxes"] for r in mapped_rows if r["boxes"] and not r.get("geometry")])
        color = granule_color.get()

        # Show mapped individual markers
        points_js = "[]"
        if points is not None and not points.empty:
            pts = points[["latitude", "longitude"]].dropna().to_dict(orient="records")
            points_js = json.dumps(pts)

        # Bounding box drawn for EO data
        bbox_js = "null"
        if points is not None and not points.empty:
            bbox = _get_bounding_box(points)
            if bbox:
                min_lon, min_lat, max_lon, max_lat = bbox
                bbox_js = json.dumps([[min_lat, min_lon], [max_lat, max_lon]])

        map_html = f"""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <div id="emit-map" style="height: 600px; width: 100%;"></div>
        <script>
        (function() {{
            var map = L.map('emit-map').setView([20, 0], 2);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors'
            }}).addTo(map);

            var bounds = [];

            // GeoJSON footprints (CMR polygons or STAC geometry)
            var allGeometries = {geometry_js};
            allGeometries.forEach(function(geometry) {{
                var layer = L.geoJSON(geometry, {{
                    style: {{ color: '{color}', weight: 1, fillOpacity: 0.2 }}
                }}).addTo(map);
                var layerBounds = layer.getBounds();
                if (layerBounds && layerBounds.isValid()) {{
                    bounds.push(layerBounds.getSouthWest(), layerBounds.getNorthEast());
                }}
            }});

            // Box footprints when no geometry is available
            var allBoxes = {boxes_js};
            allBoxes.forEach(function(granuleBoxes) {{
                granuleBoxes.forEach(function(box) {{
                    var parts = box.trim().split(/\\s+/).map(Number);
                    var south=parts[0], west=parts[1], north=parts[2], east=parts[3];
                    L.rectangle([[south, west], [north, east]], {{
                        color: '{color}', weight: 1, fillOpacity: 0.2
                    }}).addTo(map);
                    bounds.push([south, west], [north, east]);
                }});
            }});

            // Bounding box from table points
            var bbox = {bbox_js};
            if (bbox) {{
                L.rectangle(bbox, {{
                    color: '#0066cc', weight: 2, fillOpacity: 0.05, dashArray: '6 4'
                }}).addTo(map);
                bounds.push(bbox[0], bbox[1]);
            }}

            // Individual table points
            var tablePoints = {points_js};
            tablePoints.forEach(function(pt) {{
                L.circleMarker([pt.latitude, pt.longitude], {{
                    radius: 5, color: '#6108e8', fillColor: '#6108e8',
                    fillOpacity: 0.8, weight: 1,
                }}).addTo(map);
                bounds.push([pt.latitude, pt.longitude]);
            }});

            if (bounds.length > 0) map.fitBounds(bounds);
        }})();
        </script>
        """
        return ui.tags.iframe(
            srcdoc=map_html,
            style="width: 100%; height: 620px; border: none;",
        )
