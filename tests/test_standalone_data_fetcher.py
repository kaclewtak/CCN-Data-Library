from __future__ import annotations

import hashlib
import shutil
import sys
import zipfile
from importlib import import_module
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

data_fetcher = import_module("ccn_dashboard.data_fetcher")
data_manifest = import_module("ccn_dashboard.data_manifest")

SynthesisFetchError = data_fetcher.SynthesisFetchError
fetch_synthesis_data = data_fetcher.fetch_synthesis_data
SynthesisArchiveManifest = data_manifest.SynthesisArchiveManifest


REQUIRED_FILES = ("CCN_depthseries.csv", "CCN_cores.csv")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_for(path: Path, *, sha256: str | None = None) -> SynthesisArchiveManifest:
    return SynthesisArchiveManifest(
        version="test-version",
        cache_version="current",
        release_tag="test-release",
        archive_name=path.name,
        url="https://example.test/ccn-synthesis.zip",
        sha256=sha256 or _sha256(path),
        archive_root="CCN_synthesis",
        required_files=REQUIRED_FILES,
    )


def _copy_archive(source: Path):
    def _download(_url: str, destination: Path, _timeout: float) -> None:
        shutil.copyfile(source, destination)

    return _download


def test_fetch_synthesis_data_rejects_checksum_mismatch(tmp_path: Path) -> None:
    archive_path = tmp_path / "bad-checksum.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("CCN_synthesis/CCN_depthseries.csv", "study_id\n")
        archive.writestr("CCN_synthesis/CCN_cores.csv", "study_id\n")

    manifest = _manifest_for(archive_path, sha256="0" * 64)

    with pytest.raises(SynthesisFetchError, match="checksum"):
        fetch_synthesis_data(
            cache_root=tmp_path / "files",
            version="current",
            manifest=manifest,
            downloader=_copy_archive(archive_path),
        )


def test_fetch_synthesis_data_rejects_unsafe_archive_member(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../evil.csv", "nope\n")
        archive.writestr("CCN_synthesis/CCN_depthseries.csv", "study_id\n")
        archive.writestr("CCN_synthesis/CCN_cores.csv", "study_id\n")

    with pytest.raises(SynthesisFetchError, match="escapes extraction"):
        fetch_synthesis_data(
            cache_root=tmp_path / "files",
            version="current",
            manifest=_manifest_for(archive_path),
            downloader=_copy_archive(archive_path),
        )
