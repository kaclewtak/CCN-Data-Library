from __future__ import annotations

import asyncio
import socket
import webbrowser
from dataclasses import dataclass
from typing import Any

from .data_provider import (
    SynthesisDataError,
    SynthesisDataLocation,
    resolve_synthesis_data_dir,
)
from .pygwalker_assets import validate_pygwalker_assets


@dataclass
class DashboardLaunch:
    url: str
    host: str
    port: int
    data_location: SynthesisDataLocation | None
    warnings: tuple[str, ...]
    server: Any
    task: asyncio.Task

    async def stop(self, timeout: float = 5.0) -> None:
        self.server.should_exit = True
        try:
            await asyncio.wait_for(self.task, timeout=timeout)
        except asyncio.TimeoutError:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)


def _can_bind(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def find_available_port(host: str = "127.0.0.1", preferred_port: int = 8000) -> int:
    if preferred_port > 0 and _can_bind(host, preferred_port):
        return preferred_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _resolve_optional_data(require_data: bool) -> tuple[SynthesisDataLocation | None, tuple[str, ...]]:
    try:
        return resolve_synthesis_data_dir(required=require_data), ()
    except SynthesisDataError as exc:
        if require_data:
            raise
        return None, (str(exc),)


async def launch_dashboard(
    *,
    app: Any | None = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    require_data: bool = False,
    open_browser: bool = False,
    log_level: str = "info",
    startup_timeout: float = 10.0,
) -> DashboardLaunch:
    import uvicorn

    validate_pygwalker_assets()
    data_location, warnings = _resolve_optional_data(require_data)
    selected_port = find_available_port(host, port)

    if app is None:
        from .app import get_app

        app = get_app()

    config = uvicorn.Config(app, host=host, port=selected_port, log_level=log_level)
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())

    loop = asyncio.get_running_loop()
    deadline = loop.time() + startup_timeout
    while not server.started and not task.done() and loop.time() < deadline:
        await asyncio.sleep(0.05)

    if task.done():
        task.result()

    url = f"http://{host}:{selected_port}"
    if open_browser:
        webbrowser.open(url)

    return DashboardLaunch(
        url=url,
        host=host,
        port=selected_port,
        data_location=data_location,
        warnings=warnings,
        server=server,
        task=task,
    )


def launch_dashboard_sync(**kwargs: Any) -> DashboardLaunch:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(launch_dashboard(**kwargs))
    if loop.is_running():
        raise RuntimeError("Use `await launch_dashboard(...)` when running inside Jupyter or marimo.")
    return loop.run_until_complete(launch_dashboard(**kwargs))
        return asyncio.run(launch_dashboard(**kwargs))
    if loop.is_running():
        raise RuntimeError("Use `await launch_dashboard(...)` when running inside Jupyter or marimo.")
    return loop.run_until_complete(launch_dashboard(**kwargs))
