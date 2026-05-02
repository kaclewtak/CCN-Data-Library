from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from typing import Sequence

from .data_provider import SynthesisDataError, ensure_synthesis_data_dir
from .launcher import find_available_port
from .pygwalker_assets import PygwalkerAssetError, validate_pygwalker_assets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the CCN standalone dashboard.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument(
        "--port",
        default=8000,
        type=int,
        help="Preferred port. Use 0 for any available port.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the dashboard in a browser.",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Require already-installed synthesis data.",
    )
    parser.add_argument(
        "--force-data-refresh",
        action="store_true",
        help="Redownload synthesis data into files/.",
    )
    parser.add_argument("--log-level", default="info", help="Uvicorn log level.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        validate_pygwalker_assets()
        if args.no_fetch:
            from .data_provider import resolve_synthesis_data_dir

            data_location = resolve_synthesis_data_dir(required=True)
        else:
            data_location = ensure_synthesis_data_dir(required=True, force=args.force_data_refresh)
    except (PygwalkerAssetError, SynthesisDataError) as exc:
        print(f"Unable to launch CCN dashboard: {exc}", file=sys.stderr)
        return 1

    selected_port = find_available_port(args.host, args.port)
    url = f"http://{args.host}:{selected_port}"
    print(data_location.message)
    print(f"Launching CCN dashboard at {url}")
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    import uvicorn

    from .app import get_app

    uvicorn.run(get_app(), host=args.host, port=selected_port, log_level=args.log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
