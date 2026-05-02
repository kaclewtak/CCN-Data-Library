from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CCN_DATA_DIR_ENV = "CCN_DATA_DIR"
CCN_DATA_CACHE_DIR_ENV = "CCN_DATA_CACHE_DIR"
DEFAULT_CACHE_VERSION = "current"
REQUIRED_SYNTHESIS_FILES = ("CCN_depthseries.csv", "CCN_cores.csv")


class SynthesisDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class SynthesisDataLocation:
    path: Path
    source: str
    message: str


def _resolve_path(path: str | os.PathLike[str]) -> Path:
    return Path(path).expanduser().resolve()


def _contains_required_files(path: Path, required_files: tuple[str, ...] = REQUIRED_SYNTHESIS_FILES) -> bool:
    return path.is_dir() and all((path / file_name).is_file() for file_name in required_files)


def as_synthesis_dir(
    path: str | os.PathLike[str], required_files: tuple[str, ...] = REQUIRED_SYNTHESIS_FILES
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

    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "ccn-dashboard"


def _candidate_roots(
    cache_root: Path | None = None, version: str = DEFAULT_CACHE_VERSION
) -> Iterable[tuple[Path, str]]:
    env_data = os.environ.get(CCN_DATA_DIR_ENV)
    if env_data:
        yield _resolve_path(env_data), CCN_DATA_DIR_ENV

    root = _resolve_path(cache_root) if cache_root is not None else default_cache_root()
    yield root / version / "CCN_synthesis", f"{CCN_DATA_CACHE_DIR_ENV or 'cache'}:{version}"
    yield root / "CCN_synthesis", f"{CCN_DATA_CACHE_DIR_ENV or 'cache'}:legacy"


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
