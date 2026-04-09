from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import polars as pl

DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

pygwalker_page = import_module("panels.pygwalker_page")
pygwalker_persistence = import_module("panels.pygwalker_persistence")

_PYGWALKER_RENDER_SCRIPT = getattr(pygwalker_page, "_PYGWALKER_RENDER_SCRIPT")
build_pygwalker_html = pygwalker_persistence.build_pygwalker_html
data_fingerprint = pygwalker_persistence.data_fingerprint


def _sample_df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "study_id": ["A1", "B2"],
            "depth_cm": [10, 25],
        }
    )


def test_data_fingerprint_is_deterministic() -> None:
    df = _sample_df()

    assert data_fingerprint(df) == data_fingerprint(df)


def test_data_fingerprint_changes_when_data_changes() -> None:
    original = _sample_df()
    changed = original.with_columns(pl.Series("depth_cm", [10, 30]))

    assert data_fingerprint(original) != data_fingerprint(changed)


def test_build_pygwalker_html_includes_ccn_spreadsheet_config(monkeypatch) -> None:
    df = _sample_df()
    captured: dict[str, object] = {}

    def fake_to_html(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "<div>mock-html</div>"

    monkeypatch.setattr(pygwalker_persistence.pyg, "to_html", fake_to_html)

    html = build_pygwalker_html(df, "ccn-test-gid")

    assert html == "<div>mock-html</div>"
    assert captured["args"] == (df,)
    assert captured["kwargs"]["gid"] == "ccn-test-gid"
    assert captured["kwargs"]["width"] == "100%"
    assert captured["kwargs"]["height"] == "100%"

    ccn_config = captured["kwargs"]["ccnSpreadsheet"]
    assert ccn_config["enabled"] is True
    assert ccn_config["datasetFingerprint"] == data_fingerprint(df)
    assert ccn_config["datasetLabel"] == "Uploaded dataset"


def test_render_script_uses_persistent_message_handler() -> None:
    assert "ccn_pygwalker_render" in _PYGWALKER_RENDER_SCRIPT
    assert "data-ccn-fp" in _PYGWALKER_RENDER_SCRIPT
