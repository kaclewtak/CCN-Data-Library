from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path

REQUIRED_PYGWALKER_DIST_ASSETS = (
    "pygwalker-app.iife.js",
    "pygwalker-app.es.js",
    "dsl-to-workflow.umd.js",
    "vega-to-dsl.umd.js",
)


class PygwalkerAssetError(FileNotFoundError):
    pass


def _source_tree_pygwalker_root() -> Path | None:
    candidate = Path(__file__).resolve().parents[1] / "interactive_dash" / "pygwalker"
    return candidate if candidate.is_dir() else None


def _installed_pygwalker_root() -> Path | None:
    spec = find_spec("pygwalker")
    if spec is None or not spec.submodule_search_locations:
        return None
    candidate = Path(next(iter(spec.submodule_search_locations)))
    return candidate if candidate.is_dir() else None


def pygwalker_root() -> Path:
    root = _source_tree_pygwalker_root() or _installed_pygwalker_root()
    if root is None:
        raise PygwalkerAssetError("Cannot find the local customized pygwalker package.")
    return root


def pygwalker_dist_dir() -> Path:
    return pygwalker_root() / "templates" / "dist"


def validate_pygwalker_assets(
    required_assets: tuple[str, ...] = REQUIRED_PYGWALKER_DIST_ASSETS,
) -> tuple[Path, ...]:
    dist_dir = pygwalker_dist_dir()
    missing = [asset for asset in required_assets if not (dist_dir / asset).is_file()]
    if missing:
        missing_list = ", ".join(missing)
        raise PygwalkerAssetError(
            "Missing customized Data Explorer frontend assets in "
            f"{dist_dir}: {missing_list}. Maintainers should build the bundle before packaging."
        )
    return tuple(dist_dir / asset for asset in required_assets)
