from __future__ import annotations

import json

from dashboard_shared_dataset import (
    SharedDatasetState,
    build_explorer_bootstrap_frame,
    build_startup_dataset_fingerprint,
)
from panels.pygwalker_persistence import (
    build_pygwalker_html_with_config,
    data_fingerprint,
)
from shiny import module, reactive, ui


# ---------------------------------------------------------------------------
# JavaScript handler for persistent PyGWalker rendering
# ---------------------------------------------------------------------------
# This script is injected once into the page.  It accepts custom messages
# from the server and updates the PyGWalker host <div> **only** when the
# data fingerprint actually changes, keeping the iframe (and all user
# chart settings inside it) alive across Shiny tab switches.
# ---------------------------------------------------------------------------
def _build_pygwalker_render_script(host_id: str, placeholder_id: str, dataset_sync_input_id: str) -> str:
    host_id_json = json.dumps(host_id)
    placeholder_id_json = json.dumps(placeholder_id)
    dataset_sync_input_id_json = json.dumps(dataset_sync_input_id)

    return f"""\
(function() {{
    if (window.__ccnPygwalkerHandlerRegistered) return;
    window.__ccnPygwalkerHandlerRegistered = true;

    Shiny.addCustomMessageHandler("ccn_pygwalker_render", function(msg) {{
        var host = document.getElementById({host_id_json});
        var placeholder = document.getElementById({placeholder_id_json});
        if (!host) return;

        if (msg.action === "clear") {{
            host.innerHTML = "";
            host.removeAttribute("data-ccn-fp");
            host.removeAttribute("data-ccn-bridge-id");
            if (placeholder) placeholder.style.display = "";
            return;
        }}

        // Skip if the same data fingerprint is already rendered — this is
        // what keeps the iframe (and all user chart settings) alive when
        // the user simply switches Shiny tabs.
        if (host.getAttribute("data-ccn-fp") === msg.fingerprint) return;

        if (placeholder) placeholder.style.display = "none";
        host.setAttribute("data-ccn-fp", msg.fingerprint);
        if (msg.bridgeId) {{
            host.setAttribute("data-ccn-bridge-id", msg.bridgeId);
        }}
        host.innerHTML = msg.html;
    }});

    window.addEventListener("message", function(event) {{
        var host = document.getElementById({host_id_json});
        if (!host) return;

        var iframe = host.querySelector("iframe");
        if (!iframe || event.source !== iframe.contentWindow) return;

        var payload = event.data;
        if (!payload || payload.type !== "ccn:shared-dataset-sync") return;

        var expectedBridgeId = host.getAttribute("data-ccn-bridge-id");
        if (expectedBridgeId && payload.bridgeId !== expectedBridgeId) return;

        Shiny.setInputValue({dataset_sync_input_id_json}, payload, {{ priority: "event" }});
    }});
}})();
"""


_PYGWALKER_RENDER_SCRIPT = _build_pygwalker_render_script(
    "ccn_pygwalker_host",
    "ccn_pygwalker_placeholder",
    "ccn_pygwalker_dataset_sync",
)


@module.ui
def pygwalker_ui():
    host_id = "ccn_pygwalker_host"
    placeholder_id = "ccn_pygwalker_placeholder"
    dataset_sync_input_id = module.resolve_id("dataset_sync")

    return ui.div(
        ui.div(
            ui.div(
                ui.p("Loading Data Explorer..."),
                style="padding: 2rem; color: #666;",
                id=placeholder_id,
            ),
            ui.div(id=host_id),
            ui.tags.script(_build_pygwalker_render_script(host_id, placeholder_id, dataset_sync_input_id)),
            class_="pygwalker-container",
        ),
        class_="pygwalker-page",
    )


@module.server
def pygwalker_server(
    input_,
    _output,
    session,
):
    # Mutable (non-reactive) state — keeps track of what is already
    # rendered so we only push new HTML when data genuinely changes.
    _state: dict = {"hash": "", "rendered": False}
    _stable_gid = f"ccn-pgw-{id(session)}"
    _bridge_id = f"ccn-pgw-bridge-{id(session)}"
    _shared_dataset = SharedDatasetState()
    _boot_df = build_explorer_bootstrap_frame()
    _boot_fp = data_fingerprint(_boot_df)
    _startup_dataset_fingerprint = build_startup_dataset_fingerprint(_stable_gid)

    @reactive.effect
    async def _render_pygwalker_bootstrap():
        if _state["rendered"]:
            return

        _state["rendered"] = True
        _state["hash"] = _boot_fp
        html = build_pygwalker_html_with_config(
            _boot_df,
            _stable_gid,
            spreadsheet_dataset_fingerprint=_startup_dataset_fingerprint,
            bridge_config={
                "enabled": True,
                "bridgeId": _bridge_id,
                "targetOrigin": "*",
            },
        )
        await session.send_custom_message(
            "ccn_pygwalker_render",
            {"html": html, "fingerprint": _boot_fp, "bridgeId": _bridge_id},
        )

    @reactive.effect
    @reactive.event(input_.dataset_sync)
    def _sync_shared_dataset():
        payload = input_.dataset_sync()
        _shared_dataset.update_from_payload(payload)

    return {
        "data": _shared_dataset.data,
        "all_geo_points": _shared_dataset.geo_points,
        "metadata": _shared_dataset.metadata,
    }
