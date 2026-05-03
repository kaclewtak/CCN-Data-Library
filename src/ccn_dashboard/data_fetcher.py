from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .data_manifest import DEFAULT_SYNTHESIS_MANIFEST, SynthesisDatasetManifest

DownloadFunction = Callable[[str, Path, float], None]
INSTALL_METADATA_FILE = ".ccn_synthesis_source.json"


class SynthesisFetchError(RuntimeError):
    pass


def _contains_required_files(path: Path, required_files: tuple[str, ...]) -> bool:
    return path.is_dir() and all((path / file_name).is_file() for file_name in required_files)


def _md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_file(url: str, destination: Path, timeout: float) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "ccn-dashboard-data-fetcher"})
    with (
        urllib.request.urlopen(request, timeout=timeout) as response,
        destination.open("wb") as handle,
    ):
        shutil.copyfileobj(response, handle)


def _file_metadata(manifest: SynthesisDatasetManifest) -> list[dict[str, object]]:
    return [asdict(file_manifest) for file_manifest in manifest.files]


def _metadata_matches(target_dir: Path, manifest: SynthesisDatasetManifest) -> bool:
    metadata_path = target_dir / INSTALL_METADATA_FILE
    if not _contains_required_files(target_dir, manifest.required_files) or not metadata_path.is_file():
        return False
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return (
        metadata.get("source_url") == manifest.source_url
        and metadata.get("version") == manifest.version
        and metadata.get("article_version") == manifest.article_version
        and metadata.get("files") == _file_metadata(manifest)
    )


def _write_metadata(target_dir: Path, manifest: SynthesisDatasetManifest) -> None:
    metadata = {
        "source": "figshare",
        "source_name": manifest.source_name,
        "source_url": manifest.source_url,
        "api_url": manifest.api_url,
        "version": manifest.version,
        "article_id": manifest.article_id,
        "article_version": manifest.article_version,
        "doi": manifest.doi,
        "citation": manifest.citation,
        "files": _file_metadata(manifest),
        "installed_at": datetime.now(timezone.utc).isoformat(),
    }
    (target_dir / INSTALL_METADATA_FILE).write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _destination_for_file(staging_dir: Path, file_name: str) -> Path:
    relative_path = Path(file_name)
    if relative_path.name != file_name or file_name in {"", ".", ".."}:
        raise SynthesisFetchError(f"Unsafe synthesis file name: {file_name}")
    return staging_dir / file_name


def _download_manifest_files(
    staging_dir: Path,
    manifest: SynthesisDatasetManifest,
    timeout: float,
    downloader: DownloadFunction,
) -> None:
    seen_names: set[str] = set()
    for source_file in manifest.files:
        if source_file.name in seen_names:
            raise SynthesisFetchError(f"Duplicate synthesis file in manifest: {source_file.name}")
        seen_names.add(source_file.name)
        destination = _destination_for_file(staging_dir, source_file.name)
        try:
            downloader(source_file.url, destination, timeout)
        except Exception as exc:  # noqa: BLE001 - preserve network/library details in the message.
            raise SynthesisFetchError(f"Failed to download {source_file.name} from {source_file.url}: {exc}") from exc

        observed_md5 = _md5(destination)
        if observed_md5.lower() != source_file.md5.lower():
            raise SynthesisFetchError(
                "Downloaded CCN synthesis file failed checksum validation. "
                f"File {source_file.name} expected MD5 {source_file.md5}, "
                f"observed {observed_md5}."
            )


def _install_synthesis_files(
    target_dir: Path,
    manifest: SynthesisDatasetManifest,
    timeout: float,
    downloader: DownloadFunction,
) -> Path:
    target_parent = target_dir.parent
    target_parent.mkdir(parents=True, exist_ok=True)
    staging_dir = target_parent / f".{target_dir.name}.installing"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir()
    try:
        _download_manifest_files(staging_dir, manifest, timeout, downloader)
        if not _contains_required_files(staging_dir, manifest.required_files):
            required = ", ".join(manifest.required_files)
            raise SynthesisFetchError(f"Downloaded synthesis data does not contain required files: {required}")
        _write_metadata(staging_dir, manifest)
        if target_dir.exists():
            shutil.rmtree(target_dir)
        staging_dir.rename(target_dir)
    except (OSError, SynthesisFetchError):
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        raise
    return target_dir


def fetch_synthesis_data(
    *,
    cache_root: Path,
    version: str,
    manifest: SynthesisDatasetManifest = DEFAULT_SYNTHESIS_MANIFEST,
    force: bool = False,
    timeout: float = 60.0,
    downloader: DownloadFunction | None = None,
) -> Path:
    """Download and cache the requested CCN synthesis dataset when needed."""
    target_dir = cache_root / version / "CCN_synthesis"
    if not force and _metadata_matches(target_dir, manifest):
        return target_dir

    cache_root.mkdir(parents=True, exist_ok=True)
    download = downloader or _download_file
    return _install_synthesis_files(target_dir, manifest, timeout, download)
