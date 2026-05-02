from __future__ import annotations

import socket
import sys
from importlib import import_module
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
DASHBOARD_ROOT = SRC_ROOT / "dashboard"
for path in (SRC_ROOT, DASHBOARD_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

app_module = import_module("ccn_dashboard.app")
launcher = import_module("ccn_dashboard.launcher")
pygwalker_assets = import_module("ccn_dashboard.pygwalker_assets")

get_app = app_module.get_app
find_available_port = launcher.find_available_port
REQUIRED_PYGWALKER_DIST_ASSETS = pygwalker_assets.REQUIRED_PYGWALKER_DIST_ASSETS
validate_pygwalker_assets = pygwalker_assets.validate_pygwalker_assets


def test_validate_pygwalker_assets_finds_required_bundle_files() -> None:
    assets = validate_pygwalker_assets()

    assert {path.name for path in assets} == set(REQUIRED_PYGWALKER_DIST_ASSETS)


def test_find_available_port_skips_occupied_preferred_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        occupied_port = int(sock.getsockname()[1])

        selected_port = find_available_port(preferred_port=occupied_port)

    assert selected_port != occupied_port
    assert selected_port > 0


def test_get_app_wraps_existing_dashboard_app() -> None:
    app = get_app()

    assert app is not None
    assert app.__class__.__name__ == "App"
