/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { GlobalDiscountPopup } from "@pos_custom_kitchen/app/global_discount_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(ControlButtons.prototype, {
    async clickDiscount() {
        const order = this.pos.getOrder();
        if (!order) {
            return;
        }
        
        const subtotal = typeof order.get_total_without_tax === "function" ? order.get_total_without_tax() : (order.priceExcl || 0);

        // Open our custom popup
        const payload = await makeAwaitable(this.dialog, GlobalDiscountPopup, {
            startingValue: 10,
            subtotal: subtotal,
        });

        if (!payload) {
            return;
        }

        const discountType = payload.type; // "percentage" or "fixed"
        const value = discountType === "percentage" ? Math.max(0, Math.min(100, payload.value)) : Math.max(0, payload.value);
        
        // Apply discount using the Global Discount Product to avoid reducing tax
        const discountConfig = this.pos.config.discount_product_id;
        const discountProductId = discountConfig ? (discountConfig.id || discountConfig[0] || discountConfig) : false;
        if (!discountProductId) {
            this.env.services.notification.add("Discount product is not configured in POS settings.", { type: "danger" });
            return;
        }

        const discountProduct = this.pos.models["product.product"].get(discountProductId);
        if (!discountProduct) {
            this.env.services.notification.add("Discount product not found in local database.", { type: "danger" });
            return;
        }
        
        let lines = [];
        if (typeof order.getOrderlines === "function") {
            lines = order.getOrderlines();
        } else if (typeof order.get_orderlines === "function") {
            lines = order.get_orderlines();
        } else if (order.lines) {
            lines = [...order.lines];
        }

        // First, reset all line discounts to 0 to clear the previous method
        for (const line of lines) {
            if (line.discount > 0) {
                if (typeof line.set_discount === "function") line.set_discount(0);
                else if (typeof line.setDiscount === "function") line.setDiscount(0);
                else line.discount = 0;
            }
        }

        // Remove any existing Global Discount lines
        const existingDiscounts = lines.filter(l => 
            (l.product && l.product.id === discountProductId) || 
            (l.product_id && l.product_id.id === discountProductId) ||
            l.isDiscountLine
        );
        for (const line of existingDiscounts) {
            if (typeof order.removeOrderline === "function") {
                order.removeOrderline(line);
            } else if (typeof order.remove_orderline === "function") {
                order.remove_orderline(line);
            }
        }

        // Apply new global discount
        if (value > 0) {
            let discountAmt = 0;
            if (discountType === "percentage") {
                discountAmt = - (subtotal * value / 100.0);
            } else {
                discountAmt = - Math.min(subtotal, value); // Cannot discount more than subtotal
            }
            
            await this.pos.addLineToOrder({
                product_id: discountProduct,
                product_tmpl_id: discountProduct.product_tmpl_id,
                price_unit: discountAmt,
                qty: 1,
                tax_ids: [],
                price_manually_set: true,
            }, order, { force: true }, false);

            // Re-fetch lines to find the newly added discount line
            const newLines = typeof order.getOrderlines === "function" ? order.getOrderlines() : (typeof order.get_orderlines === "function" ? order.get_orderlines() : [...order.lines]);
            const newDiscountLine = newLines.find(l => l.product && l.product.id === discountProductId);
            
            if (newDiscountLine) {
                // Ensure the line is marked correctly for the UI
                newDiscountLine.isDiscountLine = true;
                
                // Set note
                if (payload.reason) {
                    let note = "";
                    if (discountType === "percentage") {
                        note = `Discount ${value}% - ${payload.reason}`;
                    } else {
                        note = `Fixed Discount ${this.env.utils.formatCurrency(value)} - ${payload.reason}`;
                    }
                    if (typeof newDiscountLine.setCustomerNote === "function") newDiscountLine.setCustomerNote(note);
                    else if (typeof newDiscountLine.set_customer_note === "function") newDiscountLine.set_customer_note(note);
                    else newDiscountLine.customer_note = note;
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
            value > 0 ? `Discount applied!` : "Discount removed!",
            { type: "success" }
        );
    }
});
