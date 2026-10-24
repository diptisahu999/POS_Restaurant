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

        let lines = typeof order.getOrderlines === "function" ? order.getOrderlines() : (typeof order.get_orderlines === "function" ? order.get_orderlines() : [...(order.lines || [])]);

        // Calculate gross subtotal of food/beverage items (excluding any discount lines or negative lines)
        const productLines = lines.filter(l => 
            !l.isDiscountLine && 
            !l.uiState?.isDiscountLine &&
            (typeof l.get_unit_price === "function" ? l.get_unit_price() >= 0 : (l.price_unit >= 0)) &&
            (!discountProductId || (l.product_id?.id !== discountProductId && l.product?.id !== discountProductId))
        );

        const subtotal = productLines.reduce((acc, l) => {
            const qty = typeof l.get_quantity === "function" ? l.get_quantity() : (l.qty || 1);
            const unitPrice = typeof l.get_unit_price === "function" ? l.get_unit_price() : (l.price_unit || 0);
            return acc + (unitPrice * qty);
        }, 0);

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

        // Re-fetch current orderlines
        lines = typeof order.getOrderlines === "function" ? order.getOrderlines() : (typeof order.get_orderlines === "function" ? order.get_orderlines() : [...(order.lines || [])]);

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
            (discountProductId && ((l.product && l.product.id === discountProductId) || (l.product_id && l.product_id.id === discountProductId))) || 
            l.isDiscountLine ||
            l.uiState?.isDiscountLine ||
            (typeof l.get_unit_price === "function" ? l.get_unit_price() < 0 : (l.price_unit < 0))
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
                discountAmt = - Math.round((subtotal * value / 100.0) * 100) / 100;
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
            const newDiscountLine = newLines.find(l => 
                (l.product_id && l.product_id.id === discountProductId) ||
                (l.product && l.product.id === discountProductId) ||
                l.isDiscountLine ||
                (l.price_unit < 0)
            );
            
            if (payload.reason) {
                if (order.uiState) {
                    order.uiState.discount_reason = payload.reason;
                }
                try {
                    order.discount_reason = payload.reason;
                } catch (e) {
                    // ignore
                }
            }
            if (payload.value && discountType === "percentage") {
                if (order.uiState) {
                    order.uiState.discount_percentage = payload.value;
                }
                try {
                    order.discount_percentage = payload.value;
                } catch (e) {
                    // ignore
                }
            }

            if (newDiscountLine) {
                // Ensure the line is marked correctly for the UI
                if (newDiscountLine.uiState) {
                    newDiscountLine.uiState.isDiscountLine = true;
                    if (payload.reason) {
                        newDiscountLine.uiState.discount_reason = payload.reason;
                    }
                }
                try {
                    newDiscountLine.isDiscountLine = true;
                } catch (e) {
                    // ignore
                }
                if (payload.reason) {
                    try {
                        newDiscountLine.discount_reason = payload.reason;
                    } catch (e) {
                        // ignore
                    }
                }
                
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
                    else {
                        try {
                            newDiscountLine.customer_note = note;
                        } catch (e) {
                            // ignore
                        }
                    }
                }
            }

            // If order already has a single non-cash payment line (like UPI or Card), sync its amount to new total
            if (order.payment_ids && order.payment_ids.length === 1) {
                const p = order.payment_ids[0];
                const isCash = p.payment_method_id?.is_cash_count;
                if (!isCash && order.totalDue > 0) {
                    p.setAmount(order.totalDue);
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
