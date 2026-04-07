from __future__ import annotations

import json
import sys
from pathlib import Path

import polars as pl

# Ensure the local pygwalker copy (src/interactive_dash) is importable
_local_pygwalker = Path(__file__).resolve().parents[3] / "src" / "interactive_dash"
if _local_pygwalker.is_dir() and str(_local_pygwalker) not in sys.path:
    sys.path.insert(0, str(_local_pygwalker))

import pygwalker as pyg

_DEFAULT_SPEC = json.dumps(
    [
        {
            "name": "Chart 1",
            "visId": "vis1",
            "config": {
                "coordSystem": "generic",
                "defaultAggregated": False,
                "geoms": ["auto"],
                "limit": -1,
                "timezoneDisplayOffset": 0,
            },
            "encodings": {
                "dimensions": [],
                "measures": [],
                "rows": [],
                "columns": [],
                "color": [],
                "opacity": [],
                "size": [],
                "shape": [],
                "radius": [],
                "theta": [],
                "longitude": [],
                "latitude": [],
                "geoId": [],
                "details": [],
                "filters": [],
                "text": [],
            },
        }
    ]
)


def get_pygwalker_html(df: pl.DataFrame) -> str:
    return pyg.to_html(df, spec=_DEFAULT_SPEC, **{"width": "100%", "height": "100%"})
