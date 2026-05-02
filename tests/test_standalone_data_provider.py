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

data_provider = import_module("ccn_dashboard.data_provider")

CCN_DATA_CACHE_DIR_ENV = data_provider.CCN_DATA_CACHE_DIR_ENV
CCN_DATA_DIR_ENV = data_provider.CCN_DATA_DIR_ENV
REQUIRED_SYNTHESIS_FILES = data_provider.REQUIRED_SYNTHESIS_FILES
SynthesisDataError = data_provider.SynthesisDataError
as_synthesis_dir = data_provider.as_synthesis_dir
default_cache_root = data_provider.default_cache_root
resolve_synthesis_data_dir = data_provider.resolve_synthesis_data_dir
ensure_synthesis_data_dir = data_provider.ensure_synthesis_data_dir
SynthesisArchiveManifest = import_module(
    "ccn_dashboard.data_manifest"
).SynthesisArchiveManifest


def _write_required_files(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for file_name in REQUIRED_SYNTHESIS_FILES:
        (path / file_name).write_text("study_id,site_id,core_id\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_synthesis_archive(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for file_name in REQUIRED_SYNTHESIS_FILES:
            archive.writestr(f"CCN_synthesis/{file_name}", "study_id,site_id,core_id\n")
        archive.writestr("CCN_synthesis/README.txt", "test synthesis archive\n")
    return path


def test_as_synthesis_dir_accepts_direct_synthesis_folder(tmp_path: Path) -> None:
    _write_required_files(tmp_path)

    assert as_synthesis_dir(tmp_path) == tmp_path.resolve()


def test_as_synthesis_dir_accepts_parent_folder(tmp_path: Path) -> None:
    synthesis_dir = tmp_path / "CCN_synthesis"
    _write_required_files(synthesis_dir)

    assert as_synthesis_dir(tmp_path) == synthesis_dir.resolve()


def test_resolve_synthesis_data_dir_prefers_env_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_dir = tmp_path / "env" / "CCN_synthesis"
    cache_dir = tmp_path / "cache" / "current" / "CCN_synthesis"
    _write_required_files(env_dir)
    _write_required_files(cache_dir)
    monkeypatch.setenv(CCN_DATA_DIR_ENV, str(env_dir))
    monkeypatch.setenv(CCN_DATA_CACHE_DIR_ENV, str(tmp_path / "cache"))

    location = resolve_synthesis_data_dir()

    assert location is not None
    assert location.path == env_dir.resolve()
    assert location.source == CCN_DATA_DIR_ENV


def test_resolve_synthesis_data_dir_uses_versioned_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_root = tmp_path / "cache"
    cache_dir = cache_root / "current" / "CCN_synthesis"
    _write_required_files(cache_dir)
    monkeypatch.delenv(CCN_DATA_DIR_ENV, raising=False)
    monkeypatch.setenv(CCN_DATA_CACHE_DIR_ENV, str(cache_root))

    location = resolve_synthesis_data_dir()

    assert location is not None
    assert location.path == cache_dir.resolve()


def test_resolve_synthesis_data_dir_can_be_optional(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(CCN_DATA_DIR_ENV, raising=False)
    monkeypatch.setenv(CCN_DATA_CACHE_DIR_ENV, str(tmp_path / "empty-cache"))

    assert resolve_synthesis_data_dir(required=False) is None


def test_resolve_synthesis_data_dir_error_is_actionable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(CCN_DATA_DIR_ENV, raising=False)
    monkeypatch.setenv(CCN_DATA_CACHE_DIR_ENV, str(tmp_path / "empty-cache"))

    with pytest.raises(SynthesisDataError) as exc_info:
        resolve_synthesis_data_dir(required=True)

    message = str(exc_info.value)
    assert CCN_DATA_DIR_ENV in message
    assert "CCN_depthseries.csv" in message
    assert "CCN_cores.csv" in message
    assert str(default_cache_root()) in message


def test_default_cache_root_is_repo_local_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(CCN_DATA_CACHE_DIR_ENV, raising=False)

    assert default_cache_root() == Path(__file__).resolve().parents[1] / "files"


def test_ensure_synthesis_data_dir_downloads_once_and_reuses_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path = _write_synthesis_archive(tmp_path / "ccn-synthesis.zip")
    manifest = SynthesisArchiveManifest(
        version="test-version",
        cache_version="current",
        release_tag="test-release",
        archive_name=archive_path.name,
        url="https://example.test/ccn-synthesis.zip",
        sha256=_sha256(archive_path),
        archive_root="CCN_synthesis",
        required_files=REQUIRED_SYNTHESIS_FILES,
    )
    downloads: list[str] = []

    def fake_download(url: str, destination: Path, _timeout: float) -> None:
        downloads.append(url)
        shutil.copyfile(archive_path, destination)

    data_fetcher = import_module("ccn_dashboard.data_fetcher")
    monkeypatch.setattr(data_fetcher, "_download_file", fake_download)
    monkeypatch.delenv(CCN_DATA_DIR_ENV, raising=False)
    cache_root = tmp_path / "files"

    first = ensure_synthesis_data_dir(cache_root=cache_root, manifest=manifest)
    second = ensure_synthesis_data_dir(cache_root=cache_root, manifest=manifest)

    assert first is not None
    assert second is not None
    assert first.path == cache_root / "current" / "CCN_synthesis"
    assert second.path == first.path
    assert downloads == [manifest.url]
    assert (first.path / ".ccn_synthesis_source.json").is_file()


def test_ensure_synthesis_data_dir_env_override_prevents_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_dir = tmp_path / "env" / "CCN_synthesis"
    _write_required_files(env_dir)

    def fail_download(_url: str, _destination: Path, _timeout: float) -> None:
        raise AssertionError("download should not run when CCN_DATA_DIR is valid")

    data_fetcher = import_module("ccn_dashboard.data_fetcher")
    monkeypatch.setattr(data_fetcher, "_download_file", fail_download)
    monkeypatch.setenv(CCN_DATA_DIR_ENV, str(env_dir))

    location = ensure_synthesis_data_dir(cache_root=tmp_path / "files")

    assert location is not None
    assert location.path == env_dir.resolve()
    assert location.source == CCN_DATA_DIR_ENV
