from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

# Ensure the local pygwalker copy (src/interactive_dash) is importable
_local_pygwalker = Path(__file__).resolve().parents[3] / "src" / "interactive_dash"
if _local_pygwalker.is_dir() and str(_local_pygwalker) not in sys.path:
    sys.path.insert(0, str(_local_pygwalker))

import pygwalker as pyg


def get_pygwalker_html(df: pl.DataFrame) -> str:
    return pyg.to_html(df)
