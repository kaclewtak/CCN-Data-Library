from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SynthesisFileManifest:
    name: str
    url: str
    md5: str
    size: int


@dataclass(frozen=True)
class SynthesisDatasetManifest:
    version: str
    cache_version: str
    source_name: str
    source_url: str
    api_url: str
    article_id: str
    article_version: int
    doi: str
    citation: str
    files: tuple[SynthesisFileManifest, ...]
    required_files: tuple[str, ...]


DEFAULT_SYNTHESIS_MANIFEST = SynthesisDatasetManifest(
    version="1.7.0",
    cache_version="current",
    source_name="Database: Coastal Carbon Library (Version 1.7.0)",
    source_url=(
        "https://smithsonian.figshare.com/articles/dataset/" "Database_Coastal_Carbon_Library_Version_1_0_0_/21565671"
    ),
    api_url="https://api.figshare.com/v2/articles/21565671",
    article_id="21565671",
    article_version=9,
    doi="10.25573/serc.21565671.v9",
    citation=(
        "Coastal Carbon Network (2023). Database: Coastal Carbon Library "
        "(Version 1.7.0). Smithsonian Environmental Research Center. Dataset. "
        "https://doi.org/10.25573/serc.21565671.v9"
    ),
    files=(
        SynthesisFileManifest(
            name="README.txt",
            url="https://ndownloader.figshare.com/files/59698892",
            md5="43680d7508ab3f21cd050f5562a5db4e",
            size=4520,
        ),
        SynthesisFileManifest(
            name="CCN_database_structure.html",
            url="https://ndownloader.figshare.com/files/45374731",
            md5="6b1348dcb70f85e2c49b8a631e952e2b",
            size=1414208,
        ),
        SynthesisFileManifest(
            name="CCN_methods.csv",
            url="https://ndownloader.figshare.com/files/59698877",
            md5="239d1f92a117986f0f0ce756d1baaf85",
            size=82613,
        ),
        SynthesisFileManifest(
            name="CCN_sites.csv",
            url="https://ndownloader.figshare.com/files/59698880",
            md5="01c30236173a5ad60f05a4e7a1021874",
            size=139788,
        ),
        SynthesisFileManifest(
            name="CCN_cores.csv",
            url="https://ndownloader.figshare.com/files/59698871",
            md5="3c2072b33925f8d2dcf8e54e8db3904f",
            size=5111526,
        ),
        SynthesisFileManifest(
            name="CCN_depthseries.csv",
            url="https://ndownloader.figshare.com/files/59698883",
            md5="c5304e494ef535c006fba628006dae0f",
            size=30303567,
        ),
        SynthesisFileManifest(
            name="CCN_impacts.csv",
            url="https://ndownloader.figshare.com/files/59698874",
            md5="f9f63a66c215b9fb141a33272efa70df",
            size=155120,
        ),
        SynthesisFileManifest(
            name="CCN_species.csv",
            url="https://ndownloader.figshare.com/files/59698886",
            md5="1897e3da258608a0784d1649b63357a4",
            size=1011350,
        ),
        SynthesisFileManifest(
            name="CCN_study_citations.csv",
            url="https://ndownloader.figshare.com/files/59698889",
            md5="886bc8f087b1666d04387db9e69b3840",
            size=786151,
        ),
        SynthesisFileManifest(
            name="CCN_bibliography.bib",
            url="https://ndownloader.figshare.com/files/59698868",
            md5="7b66a23cd74003f23ed6e9e8fd632003",
            size=298551,
        ),
        SynthesisFileManifest(
            name="version_information.txt",
            url="https://ndownloader.figshare.com/files/59698895",
            md5="2ba1682351294f0d9d8d200cc6881415",
            size=30963,
        ),
    ),
    required_files=("CCN_depthseries.csv", "CCN_cores.csv"),
)

SynthesisArchiveManifest = SynthesisDatasetManifest
