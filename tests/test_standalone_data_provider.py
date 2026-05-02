from __future__ import annotations

import sys
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


def _write_required_files(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for file_name in REQUIRED_SYNTHESIS_FILES:
        (path / file_name).write_text("study_id,site_id,core_id\n", encoding="utf-8")


def test_as_synthesis_dir_accepts_direct_synthesis_folder(tmp_path: Path) -> None:
    _write_required_files(tmp_path)

    assert as_synthesis_dir(tmp_path) == tmp_path.resolve()


def test_as_synthesis_dir_accepts_parent_folder(tmp_path: Path) -> None:
    synthesis_dir = tmp_path / "CCN_synthesis"
    _write_required_files(synthesis_dir)

    assert as_synthesis_dir(tmp_path) == synthesis_dir.resolve()


def test_resolve_synthesis_data_dir_prefers_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_resolve_synthesis_data_dir_uses_versioned_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache_root = tmp_path / "cache"
    cache_dir = cache_root / "current" / "CCN_synthesis"
    _write_required_files(cache_dir)
    monkeypatch.delenv(CCN_DATA_DIR_ENV, raising=False)
    monkeypatch.setenv(CCN_DATA_CACHE_DIR_ENV, str(cache_root))

    location = resolve_synthesis_data_dir()

    assert location is not None
    assert location.path == cache_dir.resolve()


def test_resolve_synthesis_data_dir_can_be_optional(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(CCN_DATA_DIR_ENV, raising=False)
    monkeypatch.setenv(CCN_DATA_CACHE_DIR_ENV, str(tmp_path / "empty-cache"))

    assert resolve_synthesis_data_dir(required=False) is None


def test_resolve_synthesis_data_dir_error_is_actionable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(CCN_DATA_DIR_ENV, raising=False)
    monkeypatch.setenv(CCN_DATA_CACHE_DIR_ENV, str(tmp_path / "empty-cache"))

    with pytest.raises(SynthesisDataError) as exc_info:
        resolve_synthesis_data_dir(required=True)

    message = str(exc_info.value)
    assert CCN_DATA_DIR_ENV in message
    assert "CCN_depthseries.csv" in message
    assert "CCN_cores.csv" in message
    assert str(default_cache_root()) in message
