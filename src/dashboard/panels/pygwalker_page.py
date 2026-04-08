from __future__ import annotations

from collections.abc import Callable

import polars as pl
from shiny import module, reactive, ui

from panels.pygwalker_persistence import build_pygwalker_html, data_fingerprint

# ---------------------------------------------------------------------------
# CCN ADDITION — JavaScript handler for persistent PyGWalker rendering
# ---------------------------------------------------------------------------
# This script is injected once into the page.  It accepts custom messages
# from the server and updates the PyGWalker host <div> **only** when the
# data fingerprint actually changes, keeping the iframe (and all user
# chart settings inside it) alive across Shiny tab switches.
# ---------------------------------------------------------------------------
_PYGWALKER_RENDER_SCRIPT = """\
(function() {
    if (window.__ccnPygwalkerHandlerRegistered) return;
    window.__ccnPygwalkerHandlerRegistered = true;

    Shiny.addCustomMessageHandler("ccn_pygwalker_render", function(msg) {
        var host = document.getElementById("ccn-pygwalker-host");
        var placeholder = document.getElementById("ccn-pygwalker-placeholder");
        if (!host) return;

        if (msg.action === "clear") {
            host.innerHTML = "";
            host.removeAttribute("data-ccn-fp");
            if (placeholder) placeholder.style.display = "";
            return;
        }

        // Skip if the same data fingerprint is already rendered — this is
        // what keeps the iframe (and all user chart settings) alive when
        // the user simply switches Shiny tabs.
        if (host.getAttribute("data-ccn-fp") === msg.fingerprint) return;

        if (placeholder) placeholder.style.display = "none";
        host.setAttribute("data-ccn-fp", msg.fingerprint);
        host.innerHTML = msg.html;
    });
})();
"""


@module.ui
def pygwalker_ui():
    return ui.div(
        ui.div(
            # ------ CCN ADDITION START: persistent container ------
            # The host div is NOT a Shiny output — its content is managed
            # entirely via the "ccn_pygwalker_render" custom-message
            # handler so that the PyGWalker iframe survives Shiny tab
            # switches unchanged.
            ui.div(
                ui.p("Upload a file on the Table Editor tab to explore data here."),
                style="padding: 2rem; color: #666;",
                id="ccn-pygwalker-placeholder",
            ),
            ui.div(id="ccn-pygwalker-host"),
            ui.tags.script(_PYGWALKER_RENDER_SCRIPT),
            # ------ CCN ADDITION END ------
            # ------ CCN SOFT-DISABLED START: original Shiny output_ui ------
            # Replaced by the persistent container + custom-message pattern
            # above.  The output_ui approach regenerated the entire PyGWalker
            # iframe each time data_getter() invalidated or the user changed
            # tabs, which destroyed all user chart settings.
            #
            # ui.output_ui("pygwalker_view"),
            # ------ CCN SOFT-DISABLED END ------
            class_="pygwalker-container",
        ),
        class_="pygwalker-page",
    )


@module.server
def pygwalker_server(
    input,
    output,
    session,
    data_getter: Callable[[], pl.DataFrame | None],
):
    # Mutable (non-reactive) state — keeps track of what is already
    # rendered so we only push new HTML when data genuinely changes.
    _state: dict = {"hash": ""}
    _stable_gid = f"ccn-pgw-{id(session)}"

    @reactive.effect
    async def _push_pygwalker():
        """Push PyGWalker HTML only when the underlying data changes.

        The JS-side handler skips replacement when the fingerprint matches
        what is already rendered, so Shiny tab switches are free.
        """
        df = data_getter()

        if df is None:
            if _state["hash"]:
                _state["hash"] = ""
                await session.send_custom_message("ccn_pygwalker_render", {"action": "clear"})
            return

        fp = data_fingerprint(df)
        if fp == _state["hash"]:
            return  # data unchanged — keep the existing iframe alive

        _state["hash"] = fp
        html = build_pygwalker_html(df, _stable_gid)
        await session.send_custom_message(
            "ccn_pygwalker_render",
            {"html": html, "fingerprint": fp},
        )

    # ------ CCN SOFT-DISABLED START: original @render.ui ------
    # The @render.ui / pygwalker_view pattern has been replaced by the
    # @reactive.effect / custom-message approach above.  The original
    # code regenerated the entire PyGWalker iframe whenever data_getter()
    # changed (or the tab became visible), destroying all user chart
    # settings.
    #
    # @render.ui
    # def pygwalker_view():
    #     df = data_getter()
    #     if df is None:
    #         return ui.div(
    #             ui.p("Upload a file on the Table Editor tab ..."),
    #             style="padding: 2rem; color: #666;",
    #         )
    #     return ui.HTML(get_pygwalker_html(df))
    # ------ CCN SOFT-DISABLED END ------
