/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { GlobalDiscountPopup } from "@pos_custom_kitchen/app/global_discount_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(ControlButtons.prototype, {
    async clickDiscount() {
        // Open our custom popup
        const payload = await makeAwaitable(this.dialog, GlobalDiscountPopup, {
            startingValue: 10,
        });

        if (!payload) {
            return;
        }

        const percent = Math.max(0, Math.min(100, payload.percentage));
        const order = this.pos.getOrder();
        if (!order) {
            return;
        }

        // Apply discount directly to each order line — no discount product needed
        let lines = [];
        if (typeof order.getOrderlines === "function") {
            lines = order.getOrderlines();
        } else if (typeof order.get_orderlines === "function") {
            lines = order.get_orderlines();
        } else if (order.lines) {
            lines = [...order.lines];
        }

        // Only apply to real product lines (skip any existing discount lines)
        const productLines = lines.filter(l => !l.isDiscountLine);
        for (const line of productLines) {
            if (typeof line.set_discount === "function") {
                line.set_discount(percent);
            } else if (typeof line.setDiscount === "function") {
                line.setDiscount(percent);
            } else {
                line.discount = percent;
            }

            // Attach the reason as a customer note if provided
            if (payload.reason) {
                const note = `Discount ${percent}% - ${payload.reason}`;
                if (typeof line.setCustomerNote === "function") {
                    line.setCustomerNote(note);
                } else if (typeof line.set_customer_note === "function") {
                    line.set_customer_note(note);
                } else {
                    line.customer_note = note;
                }
            }
        }

        // Sync to server
        try {
            await this.pos.syncAllOrders();
        } catch (e) {
            console.warn("Discount sync failed:", e);
        }

        this.env.services.notification.add(
            `${percent}% discount applied!`,
            { type: "success" }
        );
    }
});
