from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SynthesisArchiveManifest:
    version: str
    cache_version: str
    release_tag: str
    archive_name: str
    url: str
    sha256: str
    archive_root: str
    required_files: tuple[str, ...]


DEFAULT_SYNTHESIS_MANIFEST = SynthesisArchiveManifest(
    version="1.7.0",
    cache_version="current",
    release_tag="ccn-synthesis-v1.7.0",
    archive_name="ccn-synthesis-v1.7.0.zip",
    url=(
        "https://github.com/kaclewtak/CCN-Data-Library/releases/download/"
        "ccn-synthesis-v1.7.0/ccn-synthesis-v1.7.0.zip"
    ),
    sha256="8d82fdb9412424ea376c4ab4081c1945dd90096539f2fb574cc405eb406058b8",
    archive_root="CCN_synthesis",
    required_files=("CCN_depthseries.csv", "CCN_cores.csv"),
)
