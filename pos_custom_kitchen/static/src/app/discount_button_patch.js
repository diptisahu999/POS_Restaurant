/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { GlobalDiscountPopup } from "@pos_custom_kitchen/app/global_discount_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(ControlButtons.prototype, {
    async clickDiscount() {
        // Open our custom popup instead of the default NumberPopup
        const payload = await makeAwaitable(this.dialog, GlobalDiscountPopup, {
            startingValue: this.pos.config.discount_pc || 10,
        });

        if (!payload) {
            return;
        }

        const percent = Math.max(0, Math.min(100, payload.percentage));
        await this.pos.applyDiscount(percent);

        // Find the newly added discount line and append the reason
        const order = this.pos.getOrder();
        if (order) {
            // Wait for the discount line to be fully processed by the POS system
            setTimeout(() => {
                const discountLines = order.getOrderlines().filter(l => l.isDiscountLine);
                for (const line of discountLines) {
                    const newNote = payload.reason ? `Reason: ${payload.reason}` : "";
                    if (newNote) {
                        if (typeof line.setCustomerNote === "function") {
                            line.setCustomerNote(newNote);
                        } else if (typeof line.set_customer_note === "function") {
                            line.set_customer_note(newNote);
                        } else {
                            line.customer_note = newNote;
                        }
                    }
                }
            }, 100);
        }
    }
});
