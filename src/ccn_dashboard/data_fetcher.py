from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from .data_manifest import DEFAULT_SYNTHESIS_MANIFEST, SynthesisArchiveManifest

DownloadFunction = Callable[[str, Path, float], None]
INSTALL_METADATA_FILE = ".ccn_synthesis_source.json"


class SynthesisFetchError(RuntimeError):
    pass


def _contains_required_files(path: Path, required_files: tuple[str, ...]) -> bool:
    return path.is_dir() and all(
        (path / file_name).is_file() for file_name in required_files
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_file(url: str, destination: Path, timeout: float) -> None:
    request = urllib.request.Request(
        url, headers={"User-Agent": "ccn-dashboard-data-fetcher"}
    )
    with (
        urllib.request.urlopen(request, timeout=timeout) as response,
        destination.open("wb") as handle,
    ):
        shutil.copyfileobj(response, handle)


def _validate_archive_members(zip_file: zipfile.ZipFile, destination: Path) -> None:
    destination_root = destination.resolve()
    for member in zip_file.infolist():
        member_path = (destination / member.filename).resolve()
        if not member_path.is_relative_to(destination_root):
            raise SynthesisFetchError(
                f"Archive member escapes extraction directory: {member.filename}"
            )


def _extract_archive(archive_path: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(archive_path) as zip_file:
            _validate_archive_members(zip_file, destination)
            zip_file.extractall(destination)
    except zipfile.BadZipFile as exc:
        raise SynthesisFetchError(
            f"Downloaded synthesis archive is not a valid zip file: {archive_path}"
        ) from exc


def _find_synthesis_dir(extract_dir: Path, manifest: SynthesisArchiveManifest) -> Path:
    candidates = []
    if manifest.archive_root:
        candidates.append(extract_dir / manifest.archive_root)
    candidates.extend([extract_dir, extract_dir / "CCN_synthesis"])

    for candidate in candidates:
        if _contains_required_files(candidate, manifest.required_files):
            return candidate

    required = ", ".join(manifest.required_files)
    raise SynthesisFetchError(
        f"Downloaded synthesis archive does not contain required files: {required}"
    )


def _metadata_matches(target_dir: Path, manifest: SynthesisArchiveManifest) -> bool:
    metadata_path = target_dir / INSTALL_METADATA_FILE
    if (
        not _contains_required_files(target_dir, manifest.required_files)
        or not metadata_path.is_file()
    ):
        return False
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return (
        metadata.get("url") == manifest.url
        and metadata.get("version") == manifest.version
        and metadata.get("sha256") == manifest.sha256
    )


def _write_metadata(target_dir: Path, manifest: SynthesisArchiveManifest) -> None:
    metadata = {
        "url": manifest.url,
        "version": manifest.version,
        "release_tag": manifest.release_tag,
        "archive_name": manifest.archive_name,
        "sha256": manifest.sha256,
        "installed_at": datetime.now(timezone.utc).isoformat(),
    }
    (target_dir / INSTALL_METADATA_FILE).write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _install_synthesis_dir(
    source_dir: Path, target_dir: Path, manifest: SynthesisArchiveManifest
) -> Path:
    target_parent = target_dir.parent
    target_parent.mkdir(parents=True, exist_ok=True)
    staging_dir = target_parent / f".{target_dir.name}.installing"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    shutil.copytree(source_dir, staging_dir)
    _write_metadata(staging_dir, manifest)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    staging_dir.rename(target_dir)
    return target_dir


def fetch_synthesis_data(
    *,
    cache_root: Path,
    version: str,
    manifest: SynthesisArchiveManifest = DEFAULT_SYNTHESIS_MANIFEST,
    force: bool = False,
    timeout: float = 60.0,
    downloader: DownloadFunction | None = None,
) -> Path:
    target_dir = cache_root / version / "CCN_synthesis"
    if not force and _metadata_matches(target_dir, manifest):
        return target_dir

    cache_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".ccn-download-", dir=cache_root
    ) as temporary_dir_name:
        temporary_dir = Path(temporary_dir_name)
        archive_path = temporary_dir / manifest.archive_name
        extract_dir = temporary_dir / "extract"
        extract_dir.mkdir()
        download = downloader or _download_file

        try:
            download(manifest.url, archive_path, timeout)
        except Exception as exc:  # noqa: BLE001 - preserve network/library details in the message.
            raise SynthesisFetchError(
                f"Failed to download CCN synthesis data from {manifest.url}: {exc}"
            ) from exc

        observed_sha = _sha256(archive_path)
        if observed_sha.lower() != manifest.sha256.lower():
            raise SynthesisFetchError(
                "Downloaded CCN synthesis archive failed checksum validation. "
                f"Expected {manifest.sha256}, observed {observed_sha}."
            )

        _extract_archive(archive_path, extract_dir)
        synthesis_dir = _find_synthesis_dir(extract_dir, manifest)
        return _install_synthesis_dir(synthesis_dir, target_dir, manifest)
