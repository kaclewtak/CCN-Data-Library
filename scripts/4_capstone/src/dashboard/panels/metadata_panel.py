from __future__ import annotations

from shiny import module, ui


def _external_link(label: str, href: str):
    return ui.tags.a(label, href=href, target="_blank", rel="noopener noreferrer")


def _metadata_table(headers: list[str], rows: list[list[object]]):
    return ui.tags.table(
        ui.tags.thead(ui.tags.tr(*[ui.tags.th(header, style="padding:8px 12px;") for header in headers])),
        ui.tags.tbody(
            *[
                ui.tags.tr(*[ui.tags.td(cell, style="padding:8px 12px; vertical-align:top;") for cell in row])
                for row in rows
            ]
        ),
        class_="table table-sm table-hover mb-0",
        style="font-size:0.92rem;",
    )


@module.ui
def metadata_ui():
    return ui.div(
        ui.layout_columns(
            ui.value_box("Data Library", "CCN v1.7.0", theme="primary"),
            ui.value_box("Dashboard", 'Capstone "NASA Team Yellow"', theme="info"),
            ui.value_box("Primary Data Source", "SERC / CCN", theme="success"),
            col_widths=[4, 4, 4],
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header("Recommended Citation"),
                ui.p(
                    "Coastal Carbon Network (2023). Database: Coastal Carbon Library (Version 1.7.0). "
                    "Smithsonian Environmental Research Center. Dataset. ",
                    _external_link(
                        "https://doi.org/10.25573/serc.21565671",
                        "https://doi.org/10.25573/serc.21565671",
                    ),
                    ". Accessed YYYY-MM-DD.",
                    class_="mb-2",
                ),
                ui.p(
                    "Users should also cite original dataset DOIs and credit the original data authors for any "
                    "curated datasets used from the library.",
                    class_="text-muted small mb-0",
                ),
            ),
            ui.card(
                ui.card_header("Project Attribution"),
                _metadata_table(
                    ["Role", "Attribution"],
                    [
                        [
                            "Data library stewardship",
                            "Coastal Carbon Network; Smithsonian Environmental Research Center",
                        ],
                        [
                            "Dashboard implementation",
                            "Kacper Lewtak, Rachel Krasner, Joshua White, Reid Lewis, Delphine Veronese-Milin",
                        ],
                        [
                            "Original QA/QC scripts",
                            "Jaxine Wolfe; CCN contributors; James Holmquist where noted in source comments",
                        ],
                    ],
                ),
            ),
            col_widths=[6, 6],
        ),
        ui.card(
            ui.card_header("Data, Documentation, And Service Sources"),
            _metadata_table(
                ["Source", "Used For", "Reference"],
                [
                    [
                        "CCN Data Library",
                        "Reference soil carbon distributions, core metadata, data inventory context, and QA/QC comparisons.",
                        _external_link(
                            "Repository",
                            "https://github.com/Smithsonian/CCN-Data-Library",
                        ),
                    ],
                    [
                        "CCN Community Resources",
                        "Database structure guidance, data contribution context, and controlled vocabulary documentation.",
                        _external_link(
                            "Community resources",
                            "https://smithsonian.github.io/CCN-Community-Resources/",
                        ),
                    ],
                    [
                        "NASA Common Metadata Repository",
                        "Satellite Search granule discovery for uploaded point locations.",
                        _external_link(
                            "CMR API",
                            "https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html",
                        ),
                    ],
                    [
                        "NASA EMIT and PACE collections",
                        "EO collection metadata and downloadable L2 granule links returned by NASA CMR.",
                        _external_link("NASA Earthdata", "https://www.earthdata.nasa.gov/"),
                    ],
                ],
            ),
        ),
        ui.card(
            ui.card_header("Software Acknowledgements"),
            _metadata_table(
                ["Component", "Dashboard Use"],
                [
                    [
                        "Shiny for Python",
                        "Dashboard application framework and reactive UI.",
                    ],
                    [
                        "PyGWalker / Graphic Walker",
                        "Embedded Data Explorer spreadsheet and visualization interface.",
                    ],
                    ["Plotly", "Interactive QA charts and statistical diagnostics."],
                    ["Folium / Leaflet", "QA and EO map rendering."],
                    [
                        "Pandas, Polars, SciPy, Matplotlib, Seaborn",
                        "Data wrangling, validation, statistics, and inventory plots.",
                    ],
                ],
            ),
        ),
        ui.card(
            ui.card_header("Dashboard Notes"),
            ui.tags.ul(
                ui.tags.li(
                    "The Data Explorer session dataset is mirrored to downstream QA and Satellite Search panels."
                ),
                ui.tags.li(
                    "QA/QC visualizations adapt legacy CCN R QA scripts for an interactive single-session workflow."
                ),
                ui.tags.li(
                    "Satellite Search results depend on NASA CMR availability and the collections selected in the dashboard."
                ),
            ),
            class_="mb-4",
        ),
        style="padding: 0.5rem 0 1.5rem;",
    )
