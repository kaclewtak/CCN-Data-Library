from __future__ import annotations

from .data_provider import (
    CCN_DATA_CACHE_DIR_ENV,
    CCN_DATA_DIR_ENV,
    REQUIRED_SYNTHESIS_FILES,
    SynthesisDataError,
    SynthesisDataLocation,
    default_cache_root,
    ensure_synthesis_data_dir,
    resolve_synthesis_data_dir,
)
from .launcher import DashboardLaunch, find_available_port, launch_dashboard

__all__ = [
    "CCN_DATA_CACHE_DIR_ENV",
    "CCN_DATA_DIR_ENV",
    "DashboardLaunch",
    "REQUIRED_SYNTHESIS_FILES",
    "SynthesisDataError",
    "SynthesisDataLocation",
    "app",
    "default_cache_root",
    "ensure_synthesis_data_dir",
    "find_available_port",
    "get_app",
    "launch_dashboard",
    "resolve_synthesis_data_dir",
]


def get_app():
    from .app import get_app as _get_app

    return _get_app()


def __getattr__(name: str):
    if name == "app":
        from .app import app

        return app
    raise AttributeError(f"module 'ccn_dashboard' has no attribute {name!r}")
