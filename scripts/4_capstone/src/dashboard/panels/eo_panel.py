from __future__ import annotations

import json
from collections.abc import Callable

import pandas as pd
import requests
from shiny import module, reactive, render, ui

# Satellite earth observation collections

COLLECTIONS = {
    "EMIT L2A Reflectance": {
        "short_name": "EMITL2ARFL",
        "version": "001",
        "provider": "LPCLOUD",
        "file_filter": "EMIT_L2A_RFL",
        "ext": ".nc",
        "color": "#e05c00",
    },
    "PACE OCI L2 Ocean Color (AOP)": {
        "short_name": "PACE_OCI_L2_AOP_NRT",
        "version": "3.1",
        "provider": "OB_CLOUD",
        "file_filter": None,
        "ext": ".nc",
        "color": "#0077bb",
    },
    "PACE OCI L2 Inherent Optical Properties": {
        "short_name": "PACE_OCI_L2_IOP_NRT",
        "version": "3.1",
        "provider": "OB_CLOUD",
        "file_filter": None,
        "ext": ".nc",
        "color": "#009966",
    },
}

CMR_GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"


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


def _search_granules(bbox: tuple, collection: dict) -> list[dict]:
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
            preview_url = ""
            if urls and "lp-prod-protected" in urls[0]:
                preview_url = urls[0].replace("lp-prod-protected", "lp-prod-public").replace(".nc", ".png")
            elif urls and "ob.daac" in urls[0].lower():
                preview_url = urls[0].replace(".nc", ".png")

            all_results.append(
                {
                    "granule_id": e.get("producer_granule_id", e.get("title", "")),
                    "time_start": e.get("time_start", "")[:19].replace("T", " "),
                    "time_end": e.get("time_end", "")[:19].replace("T", " "),
                    "url": urls[0] if urls else "",
                    "preview_url": preview_url,
                    "boxes": e.get("boxes", []),
                }
            )

        # Last page
        if len(entries) < 100:
            break
        params["page_num"] += 1

    return all_results


# Shiny module — UI


@module.ui
def eo_ui():
    return ui.TagList(
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
                    "Search Granules from Uploaded Points",
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
    )


# Shiny module — Server


@module.server
def eo_server(input_, _output, _session, table_points_getter: Callable[[], pd.DataFrame]):
    granules = reactive.Value([])
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
            results = _search_granules(bbox, collection)
            granules.set(results)
            status.set(f"Found {len(results)} granule(s)." if results else "No granules found for this region.")
        except requests.RequestException as e:
            status.set(f"Error: {e}")

    @render.text
    def search_status():
        return status.get()

    # Granule results table

    @render.ui
    def granule_table():
        rows = granules.get()
        if not rows:
            return ui.p("No results yet.", style="padding: 1rem; color: #666;")

        td = 'style="padding: 4px 8px; border-bottom: 1px solid #eee;"'

        rows_html = ""
        for r in rows:
            url = r["url"]
            preview = r.get("preview_url", "")

            link = f'<a href="{url}" target="_blank" title="{url}">Download</a>' if url else "—"

            # Thumbnail with lightbox on click
            thumb = (
                (
                    f'<img src="{preview}" '
                    f'style="height:48px; width:auto; border-radius:3px; cursor:pointer;" '
                    f"onclick=\"showLightbox('{preview}')\" "
                    f"onerror=\"this.style.display='none'\" />"
                )
                if preview
                else "—"
            )

            rows_html += f"""
            <tr>
                <td {td}>{thumb}</td>
                <td {td}>{r["granule_id"]}</td>
                <td {td}>{r["time_start"]}</td>
                <td {td}>{r["time_end"]}</td>
                <td {td}>{link}</td>
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
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') hideLightbox();
        }});
        </script>

        <div style="overflow: auto; max-height: 400px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">
                <thead>
                    <tr style="background: #f5f5f5; text-align: left;">
                        <th style="padding: 6px 8px;">Preview</th>
                        <th style="padding: 6px 8px;">Granule ID</th>
                        <th style="padding: 6px 8px;">Start</th>
                        <th style="padding: 6px 8px;">End</th>
                        <th style="padding: 6px 8px;">Download</th>
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

        boxes_js = json.dumps([r["boxes"] for r in rows if r["boxes"]])
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
        <div id="emit-map" style="height: 400px; width: 100%;"></div>
        <script>
        (function() {{
            var map = L.map('emit-map').setView([20, 0], 2);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors'
            }}).addTo(map);

            var bounds = [];

            // Granule footprints
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
            style="width: 100%; height: 420px; border: none;",
        )
