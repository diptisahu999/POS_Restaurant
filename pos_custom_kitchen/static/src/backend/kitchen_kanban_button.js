/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

document.addEventListener("click", async (ev) => {
    const btn = ev.target.closest(".round-status-btn");
    if (!btn) {
        return;
    }
    ev.preventDefault();
    ev.stopPropagation();

    const roundId = parseInt(btn.getAttribute("data-round-id"), 10);
    if (!roundId) {
        return;
    }

    // Immediate visual toggle
    const isCurrentlyReady = btn.classList.contains("btn-success");
    if (isCurrentlyReady) {
        btn.classList.remove("btn-success");
        btn.classList.add("btn-danger");
        btn.innerHTML = "🔴 Pending";
    } else {
        btn.classList.remove("btn-danger");
        btn.classList.add("btn-success");
        btn.innerHTML = "✅ Ready";
    }

    try {
        await rpc("/pos_kitchen/toggle_round_ready", { round_id: roundId });
    } catch (e) {
        console.error("Failed to toggle kitchen round status:", e);
    }
}, true);
