from __future__ import annotations

import hashlib
import shutil
import sys
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
SynthesisDatasetManifest = data_manifest.SynthesisDatasetManifest
SynthesisFileManifest = data_manifest.SynthesisFileManifest


REQUIRED_FILES = ("CCN_depthseries.csv", "CCN_cores.csv")


def _md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_file(source_dir: Path, name: str, text: str) -> Path:
    path = source_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _manifest_for(
    source_files: tuple[Path, ...], *, md5_overrides: dict[str, str] | None = None
) -> SynthesisDatasetManifest:
    overrides = md5_overrides or {}
    files = tuple(
        SynthesisFileManifest(
            name=path.name,
            url=f"https://example.test/{path.name}",
            md5=overrides.get(path.name, _md5(path)),
            size=path.stat().st_size,
        )
        for path in source_files
    )
    return SynthesisDatasetManifest(
        version="test-version",
        cache_version="current",
        source_name="Test Figshare dataset",
        source_url="https://example.test/articles/1",
        api_url="https://api.example.test/articles/1",
        article_id="1",
        article_version=1,
        doi="10.example/test",
        citation="Test Figshare dataset",
        files=files,
        required_files=REQUIRED_FILES,
    )


def _copy_sources(source_files: tuple[Path, ...]):
    source_by_url = {f"https://example.test/{source_file.name}": source_file for source_file in source_files}

    def _download(_url: str, destination: Path, _timeout: float) -> None:
        shutil.copyfile(source_by_url[_url], destination)

    return _download


def test_fetch_synthesis_data_installs_figshare_files(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    sources = (
        _source_file(source_dir, "CCN_depthseries.csv", "study_id\n"),
        _source_file(source_dir, "CCN_cores.csv", "study_id\n"),
    )
    manifest = _manifest_for(sources)

    result = fetch_synthesis_data(
        cache_root=tmp_path / "files",
        version="current",
        manifest=manifest,
        downloader=_copy_sources(sources),
    )

    assert result == tmp_path / "files" / "current" / "CCN_synthesis"
    assert (result / "CCN_depthseries.csv").read_text(encoding="utf-8") == "study_id\n"
    assert (result / ".ccn_synthesis_source.json").is_file()


def test_fetch_synthesis_data_rejects_checksum_mismatch(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    sources = (
        _source_file(source_dir, "CCN_depthseries.csv", "study_id\n"),
        _source_file(source_dir, "CCN_cores.csv", "study_id\n"),
    )
    manifest = _manifest_for(sources, md5_overrides={"CCN_depthseries.csv": "0" * 32})

    with pytest.raises(SynthesisFetchError, match="checksum"):
        fetch_synthesis_data(
            cache_root=tmp_path / "files",
            version="current",
            manifest=manifest,
            downloader=_copy_sources(sources),
        )


def test_fetch_synthesis_data_rejects_unsafe_file_name(tmp_path: Path) -> None:
    manifest = SynthesisDatasetManifest(
        version="test-version",
        cache_version="current",
        source_name="Test Figshare dataset",
        source_url="https://example.test/articles/1",
        api_url="https://api.example.test/articles/1",
        article_id="1",
        article_version=1,
        doi="10.example/test",
        citation="Test Figshare dataset",
        files=(
            SynthesisFileManifest(
                name="../evil.csv",
                url="https://example.test/evil.csv",
                md5="0" * 32,
                size=0,
            ),
        ),
        required_files=(),
    )

    def fail_download(_url: str, _destination: Path, _timeout: float) -> None:
        raise AssertionError("unsafe file name should fail before download")

    with pytest.raises(SynthesisFetchError, match="Unsafe synthesis file name"):
        fetch_synthesis_data(
            cache_root=tmp_path / "files",
            version="current",
            manifest=manifest,
            downloader=fail_download,
        )
