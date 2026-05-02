"""
PyGWalker persistence helpers
=============================================
Utilities that allow the Shiny "Data Explorer" tab to keep its PyGWalker
iframe alive across tab switches instead of re-rendering from scratch.

Two helpers are provided:

* ``data_fingerprint``  — fast hash that changes only when the underlying
  DataFrame content changes.
* ``build_pygwalker_html`` — thin wrapper around ``pyg.to_html`` that
  accepts a *stable* ``gid`` so the container id stays constant between
  renders.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

import polars as pl

# ── Make the local pygwalker package importable ──────────────────────────
_local_pygwalker = Path(__file__).resolve().parents[2] / "interactive_dash"
if _local_pygwalker.is_dir() and str(_local_pygwalker) not in sys.path:
    sys.path.insert(0, str(_local_pygwalker))

import pygwalker as pyg  # noqa: E402


def data_fingerprint(df: pl.DataFrame) -> str:
    """Return an MD5 hex-digest of *df*'s CSV representation.

    The hash changes if and only if the tabular content (values, columns,
    row order) changes.  It is intentionally fast/cheap — not
    cryptographic — and is used only for *same-session* identity checks.
    """
    return hashlib.md5(df.write_csv().encode("utf-8")).hexdigest()


def build_pygwalker_html(df: pl.DataFrame, gid: str) -> str:
    """Generate PyGWalker HTML with a caller-chosen *gid*.

    Using a stable ``gid`` avoids creating a brand-new container div each
    time, which is the key to keeping the React app alive in the DOM.
    """
    return build_pygwalker_html_with_config(df, gid)


def build_pygwalker_html_with_config(
    df: pl.DataFrame,
    gid: str,
    *,
    spreadsheet_dataset_fingerprint: str | None = None,
    spreadsheet_dataset_label: str = "Uploaded dataset",
    bridge_config: dict[str, Any] | None = None,
) -> str:
    """Generate PyGWalker HTML with CCN spreadsheet and bridge config."""
    fingerprint = data_fingerprint(df)
    extra_config: dict[str, Any] = {
        "ccnSpreadsheet": {
            "enabled": True,
            "datasetFingerprint": spreadsheet_dataset_fingerprint or fingerprint,
            "datasetLabel": spreadsheet_dataset_label,
            "autosaveDebounceMs": 2500,
            "syncDebounceMs": 350,
            "historyLimit": 50,
        }
    }
    if bridge_config:
        extra_config["ccnSharedDatasetBridge"] = bridge_config

    return pyg.to_html(
        df,
        gid=gid,
        spec="",
        width="100%",
        height="100%",
        **extra_config,
    )
