from __future__ import annotations

import asyncio
import sys
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
DASHBOARD_ROOT = SRC_ROOT / "dashboard"


def _path_resolves_to(path_entry: str, expected: Path) -> bool:
    try:
        return Path(path_entry or ".").resolve() == expected.resolve()
    except OSError:
        return False


def _write_required_synthesis_files(path: Path, required_files: tuple[str, ...]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for file_name in required_files:
        (path / file_name).write_text("study_id,site_id,core_id\n", encoding="utf-8")


def test_get_app_loads_when_called_from_outside_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    external_cwd = tmp_path / "external-working-dir"
    external_cwd.mkdir()
    monkeypatch.chdir(external_cwd)

    sanitized_sys_path = [path_entry for path_entry in sys.path if not _path_resolves_to(path_entry, DASHBOARD_ROOT)]
    if str(SRC_ROOT) not in sanitized_sys_path:
        sanitized_sys_path.insert(0, str(SRC_ROOT))
    monkeypatch.setattr(sys, "path", sanitized_sys_path)
    monkeypatch.delitem(sys.modules, "ccn_dashboard.app", raising=False)
    monkeypatch.delitem(sys.modules, "shiny_dashboard", raising=False)
    ccn_package = sys.modules.get("ccn_dashboard")
    if ccn_package is not None:
        ccn_package.__dict__.pop("app", None)

    assert str(DASHBOARD_ROOT) not in sys.path

    app_module = import_module("ccn_dashboard.app")
    app = app_module.get_app()

    assert Path.cwd() == external_cwd
    assert app.__class__.__name__ == "App"
    assert app_module.dashboard_source_dir() == DASHBOARD_ROOT
    assert sys.path[0] == str(DASHBOARD_ROOT)


def test_data_provider_uses_configured_cache_from_outside_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_provider = import_module("ccn_dashboard.data_provider")
    external_cwd = tmp_path / "external-working-dir"
    cache_root = tmp_path / "standalone-cache"
    synthesis_dir = cache_root / "current" / "CCN_synthesis"
    external_cwd.mkdir()
    _write_required_synthesis_files(synthesis_dir, data_provider.REQUIRED_SYNTHESIS_FILES)

    monkeypatch.chdir(external_cwd)
    monkeypatch.delenv(data_provider.CCN_DATA_DIR_ENV, raising=False)
    monkeypatch.setenv(data_provider.CCN_DATA_CACHE_DIR_ENV, str(cache_root))

    location = data_provider.resolve_synthesis_data_dir()

    assert Path.cwd() == external_cwd
    assert location is not None
    assert location.path == synthesis_dir.resolve()


def test_pygwalker_assets_can_validate_installed_package_without_source_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pygwalker_assets = import_module("ccn_dashboard.pygwalker_assets")
    installed_root = tmp_path / "site-packages" / "pygwalker"
    dist_dir = installed_root / "templates" / "dist"
    dist_dir.mkdir(parents=True)
    for asset_name in pygwalker_assets.REQUIRED_PYGWALKER_DIST_ASSETS:
        (dist_dir / asset_name).write_text("// bundled asset\n", encoding="utf-8")

    monkeypatch.setattr(pygwalker_assets, "_source_tree_pygwalker_root", lambda: None)
    monkeypatch.setattr(
        pygwalker_assets,
        "find_spec",
        lambda name: SimpleNamespace(submodule_search_locations=[str(installed_root)]) if name == "pygwalker" else None,
    )

    assets = pygwalker_assets.validate_pygwalker_assets()

    assert {path.name for path in assets} == set(pygwalker_assets.REQUIRED_PYGWALKER_DIST_ASSETS)
    assert all(path.parent == dist_dir for path in assets)


def test_launch_dashboard_accepts_supplied_app_from_outside_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = import_module("ccn_dashboard.launcher")
    external_cwd = tmp_path / "external-working-dir"
    external_cwd.mkdir()
    monkeypatch.chdir(external_cwd)
    monkeypatch.delenv("CCN_DATA_DIR", raising=False)
    monkeypatch.delenv("CCN_DATA_CACHE_DIR", raising=False)
    monkeypatch.setattr(launcher, "validate_pygwalker_assets", lambda: ())

    async def standalone_test_app(scope: dict[str, Any], _receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            return
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})

    async def launch_and_stop() -> None:
        handle = await launcher.launch_dashboard(
            app=standalone_test_app,
            port=0,
            require_data=False,
            log_level="critical",
            startup_timeout=5.0,
        )
        try:
            assert Path.cwd() == external_cwd
            assert handle.url == f"http://127.0.0.1:{handle.port}"
            assert handle.port > 0
            assert handle.data_location is None
        finally:
            await handle.stop()

    asyncio.run(launch_and_stop())
