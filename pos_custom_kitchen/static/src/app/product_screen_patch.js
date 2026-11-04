/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { KitchenRemarksPopup } from "@pos_custom_kitchen/app/kitchen_remarks_popup";
import { CancelItemPopup } from "@pos_custom_kitchen/app/cancel_item_popup";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { SWITCHSIGN } from "@point_of_sale/app/components/numpad/numpad";


patch(ProductScreen.prototype, {
    get canCancelKitchenItems() {
        const order = this.currentOrder;
        if (!order || order.state === "cancel" || order.uiState?.cancelled || order._is_cancelled) {
            return false;
        }
        let allLines = [];
        if (typeof order.get_orderlines === "function") {
            allLines = order.get_orderlines();
        } else if (order.lines) {
            allLines = [...order.lines];
        }
        return allLines.some(l =>
            l.is_sent_to_kitchen &&
            !l.isDiscountLine &&
            (typeof l.get_quantity === "function" ? l.get_quantity() > 0 : (l.qty > 0))
        );
    },

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
        if (event.button !== 0) return;
        const resizer = event.currentTarget;
        const screenEl = resizer.closest(".product-screen");
        if (!screenEl) return;
        const leftPane = screenEl.querySelector(".leftpane");
        if (!leftPane) return;

        const startX = event.clientX;
        const startWidth = leftPane.getBoundingClientRect().width;

        try { resizer.setPointerCapture(event.pointerId); } catch (err) {}

        resizer.classList.add("is-dragging");
        document.body.style.userSelect = "none";
        document.body.style.cursor = "col-resize";

        const onPointerMove = (e) => {
            const deltaX = e.clientX - startX;
            let newWidth = Math.round(startWidth + deltaX);
            const minWidth = 280;
            const maxWidth = Math.min(Math.round(window.innerWidth * 0.65), 750);
            newWidth = Math.max(minWidth, Math.min(newWidth, maxWidth));
            screenEl.style.setProperty("--pos-leftpane-width", `${newWidth}px`);
            this.state.leftPaneWidth = newWidth;
        };

        const onPointerUp = (e) => {
            try { resizer.releasePointerCapture(event.pointerId); } catch (err) {}
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
        try { localStorage.removeItem("pos_leftpane_width"); } catch (err) {
            console.warn("Could not clear leftpane width:", err);
        }
    },

    // ─────────────────────────────────────────────────────────────────────────
    //  SEND TO KITCHEN
    // ─────────────────────────────────────────────────────────────────────────
    async customSendToKitchen() {
        const order = this.currentOrder;
        if (!order || order.isEmpty()) return;

        let lines = [];
        if (typeof order.get_orderlines === "function") {
            lines = order.get_orderlines();
        } else if (order.lines) {
            lines = [...order.lines];
        }

        if (!lines || lines.length === 0) return;

        // Filter out discount lines
        lines = lines.filter(line => !line.isDiscountLine);
        if (lines.length === 0) return;

        // Fetch existing rounds from backend or local cache
        const identifier = order.uuid || order.server_id || order.id || order.name || order.pos_reference;
        let existingRounds = [];
        try {
            const orm = this.env?.services?.orm || this.pos?.orm;
            if (orm && identifier) {
                existingRounds = await orm.call("pos.order", "get_order_kitchen_rounds", [identifier]);
            }
        } catch (e) {
            console.warn("Could not fetch kitchen rounds via RPC:", e);
        }
        if (!existingRounds || !Array.isArray(existingRounds) || existingRounds.length === 0) {
            existingRounds = order._kitchen_rounds_local || [];
        }

        const payload = await makeAwaitable(this.dialog, KitchenRemarksPopup, {
            orderlines: lines,
            existingRounds: existingRounds,
            order: order,
        });

        if (!payload) return;

        const isResend = Boolean(payload.isResend);
        const targetRoundId = payload.targetRoundId;
        const notes = payload.notes || payload;

        if (isResend) {
            this.env.services.notification.add("Resending order to Kitchen Printers...", { type: "info" });
            try {
                const printResult = await this.pos.data.call("pos.order", "action_print_kitchen_order", [order.uuid, targetRoundId]);
                if (printResult && printResult.success) {
                    const printerNames = (printResult.printers && printResult.printers.length)
                        ? printResult.printers.join(", ")
                        : "Kitchen Printer";
                    this.env.services.notification.add(`Resent to ${printerNames}!`, { type: "success" });
                } else if (printResult && !printResult.success) {
                    this.env.services.notification.add(
                        `Printer Warning: ${printResult.message || 'No ticket printed'}`, { type: "warning" }
                    );
                }
            } catch (e) {
                console.error("Network kitchen print call failed:", e);
                this.env.services.notification.add("Printer Error: " + (e.message || "Failed to reach printer"), { type: "danger" });
            }
            return;
        }

        // Apply updated quantities if modified in remarks popup
        const lineQuantities = payload.lineQuantities;
        if (lineQuantities) {
            for (const line of lines) {
                const key = String(line.uuid || line.id || line.cid || "");
                if (lineQuantities[key] !== undefined) {
                    const newQty = lineQuantities[key];
                    if (newQty <= 0) {
                        if (typeof order.removeOrderline === "function") {
                            order.removeOrderline(line);
                        } else if (typeof line.delete === "function") {
                            line.delete();
                        } else if (typeof order.remove_orderline === "function") {
                            order.remove_orderline(line);
                        }
                    } else {
                        if (typeof line.setQuantity === "function") {
                            line.setQuantity(newQty);
                        } else if (typeof line.set_quantity === "function") {
                            line.set_quantity(newQty);
                        } else {
                            line.qty = newQty;
                        }
                    }
                }
            }
            lines = (typeof order.get_orderlines === "function" ? order.get_orderlines() : (order.lines ? [...order.lines] : [])).filter(l => !l.isDiscountLine);
            if (!lines || lines.length === 0) {
                this.env.services.notification.add("All items removed. Nothing to send to kitchen.", { type: "info" });
                return;
            }
        }

        // Determine round sequence and title
        const prevRounds = Array.isArray(order._kitchen_rounds_local) ? [...order._kitchen_rounds_local] : [];
        const isInitialOrder = prevRounds.length === 0;
        const pastReorders = prevRounds.filter(r => r.round_type === 'reorder' || r.sequence > 0);
        const nextSequence = isInitialOrder ? 0 : pastReorders.length + 1;
        const roundTitle = isInitialOrder ? "Order" : `Reorder ${nextSequence}`;
        const roundType = isInitialOrder ? "order" : "reorder";

        // Apply remarks & round sequence to each order line (only for unsent / new items)
        for (const line of lines) {
            if (line.is_sent_to_kitchen) continue;
            const key = String(line.uuid || line.id || line.cid || "");
            const note = (notes && notes[key]) !== undefined ? notes[key] : (line.customer_note || "");
            if (typeof line.setCustomerNote === "function") {
                line.setCustomerNote(note);
            } else if (typeof line.set_customer_note === "function") {
                line.set_customer_note(note);
            } else {
                line.customer_note = note;
            }
            line.kitchen_round_seq = nextSequence;
            line.kitchen_round_title = roundTitle;
        }

        for (const line of lines) { line.is_sent_to_kitchen = true; }
        order.is_sent_to_kitchen = true;

        const sentQtyByProduct = {};
        for (const r of prevRounds) {
            for (const rl of (r.lines || [])) {
                sentQtyByProduct[rl.product_id] = (sentQtyByProduct[rl.product_id] || 0) + (rl.qty || 0);
            }
        }

        const deltaRoundLines = [];
        for (const l of lines) {
            const pId = l.product_id?.id || l.product_id;
            const qty = typeof l.get_quantity === "function" ? l.get_quantity() : (l.qty || 0);
            const prevSent = sentQtyByProduct[pId] || 0;
            if (qty > prevSent) {
                const diff = qty - prevSent;
                sentQtyByProduct[pId] = qty;
                deltaRoundLines.push({
                    id: `local_${Date.now()}_${pId}`,
                    product_id: pId,
                    product_name: typeof l.get_full_product_name === "function" ? l.get_full_product_name() : (l.full_product_name || l.product_id?.display_name || "Item"),
                    category_name: l.product_id?.pos_categ_ids?.[0]?.name || "General",
                    qty: diff,
                    note: l.customer_note || "",
                });
            }
        }

        if (deltaRoundLines.length > 0) {
            prevRounds.push({
                id: `local_${Date.now()}`,
                sequence: nextSequence,
                round_type: roundType,
                title: roundTitle,
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                lines: deltaRoundLines,
            });
            order._kitchen_rounds_local = prevRounds;
        }

        try {
            await this.pos.syncAllOrders({ orders: [order], force: true });
            try {
                const orm = this.env?.services?.orm || this.pos?.orm;
                if (orm && identifier) {
                    const serverRounds = await orm.call("pos.order", "get_order_kitchen_rounds", [identifier]);
                    if (serverRounds && Array.isArray(serverRounds) && serverRounds.length > 0) {
                        order._kitchen_rounds_local = serverRounds;
                    }
                }
            } catch (err) {}
        } catch (e) {
            console.warn("Kitchen sync failed:", e);
        }

        this.env.services.notification.add("Sending order to Kitchen Printers...", { type: "info" });

        try {
            const printResult = await this.pos.data.call("pos.order", "action_print_kitchen_order", [order.uuid]);
            if (printResult && printResult.success) {
                const printerNames = (printResult.printers && printResult.printers.length)
                    ? printResult.printers.join(", ")
                    : "Kitchen Printer";
                this.env.services.notification.add(`Printing Order: Sent to ${printerNames}!`, { type: "success" });
            } else if (printResult && !printResult.success) {
                this.env.services.notification.add(
                    `Printer Warning: ${printResult.message || 'No ticket printed'}`, { type: "warning" }
                );
            }
        } catch (e) {
            console.error("Network kitchen print call failed:", e);
            this.env.services.notification.add("Printer Error: " + (e.message || "Failed to reach printer"), { type: "danger" });
        }
    },

    // ─────────────────────────────────────────────────────────────────────────
    //  CANCEL KITCHEN ITEMS  (NEW)
    // ─────────────────────────────────────────────────────────────────────────
    async cancelKitchenItems(targetLine = null) {
        const order = this.currentOrder;
        if (!order) return;

        // Block cancellation if order is already cancelled
        if (order.state === "cancel" || order.uiState?.cancelled || order._is_cancelled) {
            await makeAwaitable(this.dialog, AlertDialog, {
                title: _t("Order Already Cancelled"),
                body: _t("This order has already been cancelled and cannot be cancelled again."),
            });
            if (this.pos.config.module_pos_restaurant) {
                this.pos.showScreen("FloorScreen");
            }
            return;
        }

        // Collect only sent-to-kitchen lines with quantity > 0 (excluding discount lines)
        let allLines = [];
        if (typeof order.get_orderlines === "function") {
            allLines = order.get_orderlines();
        } else if (order.lines) {
            allLines = [...order.lines];
        }
        const sentLines = allLines.filter(l =>
            l.is_sent_to_kitchen &&
            !l.isDiscountLine &&
            (typeof l.get_quantity === "function" ? l.get_quantity() > 0 : (l.qty > 0))
        );

        if (sentLines.length === 0) {
            this.dialog.add(AlertDialog, {
                title: _t("No Sent Items"),
                body: _t("There are no active kitchen-sent items on this order to cancel."),
            });
            return;
        }

        // Fetch existing rounds from server or local cache
        const identifier = order.uuid || order.server_id || order.id || order.name || order.pos_reference;
        let existingRounds = [];
        try {
            const orm = this.env?.services?.orm || this.pos?.orm;
            if (orm && identifier) {
                existingRounds = await orm.call("pos.order", "get_order_kitchen_rounds", [identifier]);
            }
        } catch (e) {
            console.warn("Could not fetch kitchen rounds via RPC:", e);
        }
        if (!existingRounds || !Array.isArray(existingRounds) || existingRounds.length === 0) {
            existingRounds = order._kitchen_rounds_local || [];
        }

        // Open Cancel popup with rounds and target line
        const payload = await makeAwaitable(this.dialog, CancelItemPopup, {
            orderlines: sentLines,
            existingRounds: existingRounds,
            order: order,
            targetLine: targetLine,
        });

        if (!payload || !payload.cancelledItems || payload.cancelledItems.length === 0) return;

        const { cancelledItems, printCancelKot, globalReason, isFullOrderCancel } = payload;

        // Build items list for backend cancellation
        const cancelData = cancelledItems.map(ci => {
            const line = ci.lineRef;
            const p = line?.product_id || line?.product;
            const pId = (typeof p === "object" && p !== null)
                ? (p.id || (Array.isArray(p) ? p[0] : null))
                : (typeof p === "number" ? p : null);
            const resolvedPId = pId || (typeof line?.getProduct === "function" ? line.getProduct()?.id : null);

            let catId = null;
            if (p && typeof p === "object") {
                if (Array.isArray(p.pos_categ_ids) && p.pos_categ_ids.length > 0) {
                    catId = typeof p.pos_categ_ids[0] === "object" ? p.pos_categ_ids[0].id : p.pos_categ_ids[0];
                }
            }
            if (!catId && line?.pos_category_id) {
                catId = typeof line.pos_category_id === "object" ? line.pos_category_id.id : line.pos_category_id;
            }

            return {
                product_id: resolvedPId,
                product_name: ci.name,
                cancel_qty: ci.cancelQty,
                reason: ci.reason || globalReason || "",
                line_uuid: line?.uuid || null,
                line_id: line?.id || null,
                round_title: ci.roundTitle || "",
                round_seq: ci.roundSeq !== undefined ? ci.roundSeq : null,
                pos_category_id: catId,
            };
        });

        this.env.services.notification.add(
            _t("Processing cancellation..."),
            { type: "info" }
        );

        try {
            // Call backend to record cancel round and adjust lines
            const orm = this.env?.services?.orm || this.pos?.orm;
            let result = null;
            if (orm && order.uuid) {
                result = await orm.call(
                    "pos.order",
                    "action_cancel_kitchen_items",
                    [order.uuid, cancelData, printCancelKot]
                );
            }

            // Update local POS order lines cleanly
            order._allow_kitchen_cancel = true;
            for (const ci of cancelledItems) {
                const line = ci.lineRef;
                if (!line) continue;
                line._allow_kitchen_cancel = true;
                const currentQty = typeof line.get_quantity === "function" ? line.get_quantity() : (line.qty || 0);
                if (ci.cancelQty >= currentQty) {
                    // Line fully cancelled -> remove from order
                    if (typeof order.removeOrderline === "function") {
                        order.removeOrderline(line);
                    } else if (typeof line.delete === "function") {
                        line.delete();
                    }
                } else {
                    // Partial cancellation -> decrease quantity
                    const newQty = currentQty - ci.cancelQty;
                    if (typeof line.setQuantity === "function") {
                        line.setQuantity(newQty);
                    } else if (typeof line.set_quantity === "function") {
                        line.set_quantity(newQty);
                    } else {
                        line.qty = newQty;
                    }
                }
                line._allow_kitchen_cancel = false;
            }
            order._allow_kitchen_cancel = false;

            // Check if entire order is empty or cancelled
            const remainingLines = order.get_orderlines
                ? order.get_orderlines().filter(l => !l.isDiscountLine)
                : (order.lines ? [...order.lines].filter(l => !l.isDiscountLine) : []);

            const isOrderEmpty = remainingLines.length === 0 || isFullOrderCancel || Boolean(result?.order_cancelled);

            // Build clear confirmation message for popup
            const popupTitle = isOrderEmpty
                ? _t("Order Successfully Cancelled")
                : _t("Item(s) Successfully Cancelled");

            let popupBody = isOrderEmpty
                ? _t("The order has been successfully cancelled and the table has been released.")
                : _t("The selected item(s) have been successfully cancelled.");

            if (printCancelKot) {
                if (result?.printers && result.printers.length > 0) {
                    popupBody += "\n\n" + _t("Cancel slip printed on corresponding printer(s):") + "\n• " + result.printers.join("\n• ");
                } else if (result?.print_message) {
                    popupBody += "\n\n" + _t("Printer Status:") + " " + result.print_message;
                } else if (result?.print_success) {
                    popupBody += "\n\n" + _t("Cancel slip sent to corresponding kitchen printer.");
                } else {
                    popupBody += "\n\n" + _t("Notice: No kitchen printer was reached or configured for these items.");
                }
            }

            // SHOW POPUP CONFIRMATION MODAL
            await makeAwaitable(this.dialog, AlertDialog, {
                title: popupTitle,
                body: popupBody,
            });

            if (result?.already_cancelled) {
                order.state = "cancel";
                if (!order.uiState) order.uiState = {};
                order.uiState.cancelled = true;
                order._is_cancelled = true;
                if (typeof this.pos.removeOrder === "function") {
                    this.pos.removeOrder(order, false);
                }
                if (this.pos.config.module_pos_restaurant) {
                    this.pos.showScreen("FloorScreen");
                }
                return;
            }

            if (isOrderEmpty) {
                order.state = "cancel";
                if (!order.uiState) order.uiState = {};
                order.uiState.cancelled = true;
                order._is_cancelled = true;

                if (order.table_id && typeof order.table_id.removeOrder === "function") {
                    order.table_id.removeOrder(order);
                }

                if (typeof this.pos.deleteOrders === "function") {
                    try {
                        await this.pos.deleteOrders([order], [], true);
                    } catch (_) {
                        if (typeof this.pos.removeOrder === "function") {
                            this.pos.removeOrder(order, false);
                        }
                    }
                } else if (typeof this.pos.removeOrder === "function") {
                    this.pos.removeOrder(order, false);
                }

                if (typeof this.pos.syncAllOrders === "function") {
                    try {
                        await this.pos.syncAllOrders({ force: true });
                    } catch (_) {}
                }

                if (this.pos.config.module_pos_restaurant) {
                    this.pos.showScreen("FloorScreen");
                }
                return;
            }

            // Refresh local kitchen rounds cache & sync order
            try {
                if (orm && order.uuid) {
                    const serverRounds = await orm.call("pos.order", "get_order_kitchen_rounds", [order.uuid]);
                    if (serverRounds && Array.isArray(serverRounds)) {
                        order._kitchen_rounds_local = serverRounds;
                    }
                }
                await this.pos.syncAllOrders({ orders: [order], force: true });
            } catch (_) {}
        } catch (e) {
            console.error("Cancel kitchen items error:", e);
            await makeAwaitable(this.dialog, AlertDialog, {
                title: _t("Cancellation Error"),
                body: _t("Failed to process cancellation:\n") + (e.message || String(e)),
            });
        }
    },

    // ─────────────────────────────────────────────────────────────────────────
    //  NUMPAD overrides
    // ─────────────────────────────────────────────────────────────────────────
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
        const selectedLine = this.currentOrder?.getSelectedOrderline();
        if (selectedLine && selectedLine.is_sent_to_kitchen) {
            if (buttonValue === "Backspace" || buttonValue === "c" || buttonValue === "0") {
                return this.dialog.add(ConfirmationDialog, {
                    title: _t("Item Already Sent to Kitchen"),
                    body: _t("This item has already been sent to the kitchen. Would you like to cancel it?"),
                    confirmLabel: _t("Cancel This Item"),
                    cancelLabel: _t("Keep Item"),
                    confirm: () => {
                        this.cancelKitchenItems(selectedLine);
                    },
                });
            }
            return this.dialog.add(AlertDialog, {
                title: _t("Item Locked"),
                body: _t("This item has already been sent to the kitchen and cannot be modified. To order more, select the item from the catalog. To cancel, click 'Cancel Order / Reorder Items'."),
            });
        }
        if ((buttonValue === "-" || buttonValue === "+/-" || (SWITCHSIGN && buttonValue === SWITCHSIGN.value)) && this.pos.numpadMode === "quantity") {
            return this.dialog.add(AlertDialog, {
                title: _t("Negative quantity not allowed"),
                body: _t("The quantity of the product cannot be negative."),
            });
        }
        return super.onNumpadClick(...arguments);
    },
});
