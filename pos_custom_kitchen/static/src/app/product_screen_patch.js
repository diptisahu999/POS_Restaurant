/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { KitchenRemarksPopup } from "@pos_custom_kitchen/app/kitchen_remarks_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { SWITCHSIGN } from "@point_of_sale/app/components/numpad/numpad";


patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.showNumpad = true;

        // Restore saved left pane width or use default (380px)
        let initialWidth = 380;
        try {
            const savedWidth = localStorage.getItem("pos_leftpane_width");
            if (savedWidth) {
                const parsed = parseInt(savedWidth, 10);
                if (parsed >= 280 && parsed <= 850) {
                    initialWidth = parsed;
                }
            }
        } catch (e) {
            console.warn("Unable to read localStorage for pos_leftpane_width:", e);
        }
        this.state.leftPaneWidth = initialWidth;
    },
    toggleNumpad() {
        this.state.showNumpad = !this.state.showNumpad;
    },
    onResizerPointerDown(event) {
        if (event.button !== 0) return; // Only respond to primary button (left click)
        const resizer = event.currentTarget;
        const screenEl = resizer.closest(".product-screen");
        if (!screenEl) return;
        const leftPane = screenEl.querySelector(".leftpane");
        if (!leftPane) return;

        const startX = event.clientX;
        const startWidth = leftPane.getBoundingClientRect().width;

        try {
            resizer.setPointerCapture(event.pointerId);
        } catch (err) {}

        resizer.classList.add("is-dragging");
        document.body.style.userSelect = "none";
        document.body.style.cursor = "col-resize";

        const onPointerMove = (e) => {
            const deltaX = e.clientX - startX;
            let newWidth = Math.round(startWidth + deltaX);
            const minWidth = 280;
            const maxWidth = Math.min(Math.round(window.innerWidth * 0.65), 750);
            newWidth = Math.max(minWidth, Math.min(newWidth, maxWidth));

            // Instant responsive CSS variable update
            screenEl.style.setProperty("--pos-leftpane-width", `${newWidth}px`);
            this.state.leftPaneWidth = newWidth;
        };

        const onPointerUp = (e) => {
            try {
                resizer.releasePointerCapture(event.pointerId);
            } catch (err) {}

            resizer.classList.remove("is-dragging");
            document.body.style.userSelect = "";
            document.body.style.cursor = "";

            window.removeEventListener("pointermove", onPointerMove);
            window.removeEventListener("pointerup", onPointerUp);
            window.removeEventListener("pointercancel", onPointerUp);

            try {
                localStorage.setItem("pos_leftpane_width", String(this.state.leftPaneWidth));
            } catch (err) {
                console.warn("Could not save leftpane width:", err);
            }
        };

        window.addEventListener("pointermove", onPointerMove);
        window.addEventListener("pointerup", onPointerUp);
        window.addEventListener("pointercancel", onPointerUp);
    },
    onResizerDblClick() {
        const defaultWidth = 380;
        const screenEl = document.querySelector(".product-screen");
        if (screenEl) {
            screenEl.style.setProperty("--pos-leftpane-width", `${defaultWidth}px`);
        }
        this.state.leftPaneWidth = defaultWidth;
        try {
            localStorage.removeItem("pos_leftpane_width");
        } catch (err) {
            console.warn("Could not clear leftpane width:", err);
        }
    },
    async customSendToKitchen() {
        const order = this.currentOrder;
        if (!order || order.isEmpty()) {
            return;
        }

        // Get order lines - support both Odoo 17 and 18/19 API
        let lines = [];
        if (typeof order.get_orderlines === "function") {
            lines = order.get_orderlines();
        } else if (order.lines) {
            lines = [...order.lines];
        }

        if (!lines || lines.length === 0) {
            return;
        }

        // Filter out discount lines so they don't appear in the kitchen remarks wizard
        lines = lines.filter(line => !line.isDiscountLine);

        if (lines.length === 0) {
            return;
        }

        // Open the remarks wizard — user enters per-item notes
        const payload = await makeAwaitable(this.dialog, KitchenRemarksPopup, {
            orderlines: lines,
        });

        // payload is undefined if user cancelled
        if (!payload) {
            return;
        }

        // Apply remarks to each order line
        for (const line of lines) {
            const key = String(line.uuid || line.id || line.cid || "");
            const note = (payload && payload[key]) || "";
            if (typeof line.setCustomerNote === "function") {
                line.setCustomerNote(note);
            } else if (typeof line.set_customer_note === "function") {
                line.set_customer_note(note);
            } else {
                line.customer_note = note;
            }
        }

        // Sync to server so kitchen display shows updated notes and quantities
        try {
            await this.pos.syncAllOrders({ orders: [order], force: true });
        } catch (e) {
            console.warn("Kitchen sync failed:", e);
        }

        // Show immediate notification that printing has started
        this.env.services.notification.add(
            "Sending order to Kitchen Printers...",
            { type: "info" }
        );

        // Trigger direct network kitchen printer
        try {
            const printResult = await this.pos.data.call("pos.order", "action_print_kitchen_order", [order.uuid]);
            if (printResult && printResult.success) {
                const printerNames = (printResult.printers && printResult.printers.length)
                    ? printResult.printers.join(", ")
                    : "Kitchen Printer";
                this.env.services.notification.add(
                    `Printing Order: Sent to ${printerNames}!`,
                    { type: "success" }
                );
            } else if (printResult && !printResult.success) {
                this.env.services.notification.add(
                    `Printer Warning: ${printResult.message || 'No ticket printed'}`,
                    { type: "warning" }
                );
            }
        } catch (e) {
            console.error("Network kitchen print call failed:", e);
            this.env.services.notification.add(
                "Printer Error: " + (e.message || "Failed to reach printer"),
                { type: "danger" }
            );
        }
    },

    getNumpadButtons() {
        const buttons = super.getNumpadButtons();
        if (this.pos.numpadMode === "quantity") {
            return buttons.map((b) => {
                if (b.value === "-" || b.value === "+/-" || (SWITCHSIGN && b.value === SWITCHSIGN.value)) {
                    return { ...b, disabled: true };
                }
                return b;
            });
        }
        return buttons;
    },

    onNumpadClick(buttonValue) {
        if ((buttonValue === "-" || buttonValue === "+/-" || (SWITCHSIGN && buttonValue === SWITCHSIGN.value)) && this.pos.numpadMode === "quantity") {
            return this.dialog.add(AlertDialog, {
                title: _t("Negative quantity not allowed"),
                body: _t("The quantity of the product cannot be negative."),
            });
        }
        return super.onNumpadClick(...arguments);
    },
});

