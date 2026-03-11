from __future__ import annotations

TABLE_SCROLL_PERSISTENCE_SCRIPT = """
(() => {
    if (window.__tableScrollPersistenceInit) {
        return;
    }
    window.__tableScrollPersistenceInit = true;

    const state = new Map();

    const isTableOutputId = (id) => {
        if (!id) {
            return false;
        }
        return id === "table" || id.endsWith("-table");
    };

    const findScrollable = (root) => {
        if (!root) {
            return null;
        }

        const candidates = [root, ...root.querySelectorAll("*")];
        for (const el of candidates) {
            const style = window.getComputedStyle(el);
            const yAuto = style.overflowY === "auto" || style.overflowY === "scroll";
            const xAuto = style.overflowX === "auto" || style.overflowX === "scroll";
            const canY = yAuto && el.scrollHeight > el.clientHeight;
            const canX = xAuto && el.scrollWidth > el.clientWidth;
            if (canY || canX) {
                return el;
            }
        }
        return null;
    };

    const save = (id) => {
        const root = document.getElementById(id);
        const scrollable = findScrollable(root);
        if (!scrollable) {
            return;
        }
        state.set(id, {
            top: scrollable.scrollTop,
            left: scrollable.scrollLeft,
        });
    };

    const restore = (id) => {
        const root = document.getElementById(id);
        const scrollable = findScrollable(root);
        const saved = state.get(id);
        if (!scrollable || !saved) {
            return;
        }
        scrollable.scrollTop = saved.top;
        scrollable.scrollLeft = saved.left;
    };

    const attach = (id) => {
        const root = document.getElementById(id);
        if (!root || root.dataset.scrollPersistAttached === "1") {
            return;
        }

        root.dataset.scrollPersistAttached = "1";

        root.addEventListener(
            "scroll",
            () => {
                save(id);
            },
            { passive: true, capture: true }
        );

        const observer = new MutationObserver(() => {
            restore(id);
        });
        observer.observe(root, { childList: true, subtree: true });

        restore(id);
    };

    const scan = () => {
        const nodes = document.querySelectorAll(".shiny-bound-output[id]");
        for (const node of nodes) {
            if (isTableOutputId(node.id)) {
                attach(node.id);
            }
        }
    };

    const bodyObserver = new MutationObserver(() => {
        scan();
    });
    bodyObserver.observe(document.body, { childList: true, subtree: true });

    document.addEventListener(
        "shiny:value",
        (event) => {
            const target = event.target;
            const id = target && target.id ? target.id : null;
            if (!isTableOutputId(id)) {
                return;
            }
            setTimeout(() => restore(id), 0);
            setTimeout(() => restore(id), 80);
        },
        true
    );

    scan();
})();
"""
