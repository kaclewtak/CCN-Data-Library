from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .data_manifest import DEFAULT_SYNTHESIS_MANIFEST, SynthesisDatasetManifest

CCN_DATA_DIR_ENV = "CCN_DATA_DIR"
CCN_DATA_CACHE_DIR_ENV = "CCN_DATA_CACHE_DIR"
DEFAULT_CACHE_VERSION = "current"
REQUIRED_SYNTHESIS_FILES = DEFAULT_SYNTHESIS_MANIFEST.required_files


class SynthesisDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class SynthesisDataLocation:
    path: Path
    source: str
    message: str


def _resolve_path(path: str | os.PathLike[str]) -> Path:
    return Path(path).expanduser().resolve()


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _contains_required_files(path: Path, required_files: tuple[str, ...] = REQUIRED_SYNTHESIS_FILES) -> bool:
    return path.is_dir() and all((path / file_name).is_file() for file_name in required_files)


def as_synthesis_dir(
    path: str | os.PathLike[str],
    required_files: tuple[str, ...] = REQUIRED_SYNTHESIS_FILES,
) -> Path | None:
    resolved = _resolve_path(path)
    if _contains_required_files(resolved, required_files):
        return resolved
    nested = resolved / "CCN_synthesis"
    if _contains_required_files(nested, required_files):
        return nested
    return None


def default_cache_root() -> Path:
    env_cache = os.environ.get(CCN_DATA_CACHE_DIR_ENV)
    if env_cache:
        return _resolve_path(env_cache)
    return project_root() / "files"


def _candidate_roots(
    cache_root: Path | None = None, version: str = DEFAULT_CACHE_VERSION
) -> Iterable[tuple[Path, str]]:
    env_data = os.environ.get(CCN_DATA_DIR_ENV)
    if env_data:
        yield _resolve_path(env_data), CCN_DATA_DIR_ENV

    root = _resolve_path(cache_root) if cache_root is not None else default_cache_root()
    cache_source = CCN_DATA_CACHE_DIR_ENV if os.environ.get(CCN_DATA_CACHE_DIR_ENV) else "files"
    yield root / version / "CCN_synthesis", f"{cache_source}:{version}"
    yield root / "CCN_synthesis", f"{cache_source}:legacy"


def resolve_synthesis_data_dir(
    *,
    required: bool = True,
    cache_root: Path | None = None,
    version: str = DEFAULT_CACHE_VERSION,
    required_files: tuple[str, ...] = REQUIRED_SYNTHESIS_FILES,
) -> SynthesisDataLocation | None:
    checked: list[str] = []
    for candidate, source in _candidate_roots(cache_root=cache_root, version=version):
        checked.append(str(candidate))
        synthesis_dir = as_synthesis_dir(candidate, required_files=required_files)
        if synthesis_dir is not None:
            return SynthesisDataLocation(
                path=synthesis_dir,
                source=source,
                message=f"Using CCN synthesis data from {synthesis_dir}",
            )

    if not required:
        return None

    required_list = ", ".join(required_files)
    checked_list = "\n".join(f"- {path}" for path in checked)
    raise SynthesisDataError(
        "Cannot find CCN synthesis reference data. Set CCN_DATA_DIR to a folder containing "
        f"{required_list}, or place those files in the app cache at {default_cache_root() / version / 'CCN_synthesis'}.\n"
        f"Checked:\n{checked_list}"
    )


def ensure_synthesis_data_dir(
    *,
    required: bool = True,
    cache_root: Path | None = None,
    version: str = DEFAULT_CACHE_VERSION,
    required_files: tuple[str, ...] = REQUIRED_SYNTHESIS_FILES,
    manifest: SynthesisDatasetManifest = DEFAULT_SYNTHESIS_MANIFEST,
    force: bool = False,
    timeout: float = 60.0,
) -> SynthesisDataLocation | None:
    existing = resolve_synthesis_data_dir(
        required=False,
        cache_root=cache_root,
        version=version,
        required_files=required_files,
    )
    if existing is not None and (existing.source == CCN_DATA_DIR_ENV or not force):
        return existing

    if not required and not force:
        return None

    root = _resolve_path(cache_root) if cache_root is not None else default_cache_root()
    try:
        from .data_fetcher import SynthesisFetchError, fetch_synthesis_data

        synthesis_dir = fetch_synthesis_data(
            cache_root=root,
            version=version,
            manifest=manifest,
            force=force,
            timeout=timeout,
        )
    except SynthesisFetchError as exc:
        if required:
            raise SynthesisDataError(str(exc)) from exc
        return None

    if not _contains_required_files(synthesis_dir, required_files):
        required_list = ", ".join(required_files)
        raise SynthesisDataError(f"Downloaded synthesis data is missing required files: {required_list}")

    return SynthesisDataLocation(
        path=synthesis_dir,
        source=f"download:{manifest.version}",
        message=f"Using CCN synthesis data from {synthesis_dir}",
    )
