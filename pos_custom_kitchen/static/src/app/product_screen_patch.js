/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { KitchenRemarksPopup } from "@pos_custom_kitchen/app/kitchen_remarks_popup";

patch(PosStore.prototype, {
    async submitOrder() {
        const order = this.getOrder();
        await super.submitOrder(...arguments);
        if (order) {
            try {
                await this.syncAllOrders({ orders: [order], force: true });
            } catch (e) {
                console.warn("Kitchen sync failed in submitOrder:", e);
            }
        }
    },
});

patch(ProductScreen.prototype, {
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

        this.env.services.notification.add(
            "Order sent to kitchen!",
            { type: "success" }
        );
    },
});
