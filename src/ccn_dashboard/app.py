from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any


def dashboard_source_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "dashboard"


def ensure_dashboard_on_path() -> Path:
    """Check that the dashboard source directory is on sys.path and return its path."""
    dashboard_dir = dashboard_source_dir()
    if not dashboard_dir.is_dir():
        raise RuntimeError(f"Cannot find dashboard source directory at {dashboard_dir}")
    dashboard_path = str(dashboard_dir)
    if dashboard_path not in sys.path:
        sys.path.insert(0, dashboard_path)
    return dashboard_dir


def get_app() -> Any:
    ensure_dashboard_on_path()
    return importlib.import_module("shiny_dashboard").app


app = get_app()
