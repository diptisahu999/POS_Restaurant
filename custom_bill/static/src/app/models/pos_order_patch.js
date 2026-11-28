/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { parseFloat as oParseFloat } from "@web/views/fields/parsers";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

function isRefundOrReturnOrder(order) {
    if (!order) {
        return false;
    }
    return Boolean(
        order.isRefund ||
        order.preset_id?.is_return ||
        order.lines?.some((l) => Boolean(l.refunded_orderline_id))
    );
}

function isNegativeQtyInput(val) {
    if (typeof val === "number") {
        return val < 0 || Object.is(val, -0);
    }
    const raw = String(val ?? "").trim();
    if (raw.startsWith("-")) {
        return true;
    }
    let parsed;
    try {
        parsed = oParseFloat(raw);
    } catch {
        parsed = Number.parseFloat(raw);
    }
    return typeof parsed === "number" && !Number.isNaN(parsed) && (parsed < 0 || Object.is(parsed, -0));
}

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals);
        this.nc_reason = vals.nc_reason || "";
        this.discount_reason = vals.discount_reason || "";
        this.discount_percentage = vals.discount_percentage || 0;
        this.kot_numbers = vals.kot_numbers || "";
    },

    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        if (this.nc_reason) {
            data.nc_reason = this.nc_reason;
        }
        return data;
    },
});

patch(PosOrderline.prototype, {
    setup(vals) {
        super.setup(vals);
        this.discount_reason = vals.discount_reason || "";
    },

    setQuantity(quantity, keep_price) {
        const isRefundLine = Boolean(this.refunded_orderline_id || isRefundOrReturnOrder(this.order_id));
        if (!isRefundLine && isNegativeQtyInput(quantity)) {
            return {
                title: _t("Negative quantity not allowed"),
                body: _t("The quantity of the product cannot be negative."),
            };
        }
        return super.setQuantity(...arguments);
    },

    get isDiscountLine() {
        return (
            Boolean(this.uiState?.isDiscountLine) ||
            Boolean(super.isDiscountLine) ||
            Boolean(this.config?.module_pos_discount && this.product_id?.id === this.config?.discount_product_id?.id)
        );
    },

    set isDiscountLine(val) {
        if (!this.uiState) {
            this.uiState = {};
        }
        this.uiState.isDiscountLine = Boolean(val);
    },
});

patch(OrderPaymentValidation.prototype, {
    async isOrderValid(isForceValidate) {
        const order = this.order;
        if (order && !isRefundOrReturnOrder(order)) {
            const lines = typeof order.getOrderlines === "function" ? order.getOrderlines() : [...(order.lines || [])];
            for (const line of lines) {
                const qty = typeof line.getQuantity === "function" ? line.getQuantity() : (line.qty ?? 0);
                if (!line.refunded_orderline_id && qty < 0) {
                    this.pos.dialog.add(AlertDialog, {
                        title: _t("Negative quantity not allowed"),
                        body: _t(
                            "Product '%s' has a negative quantity. Please correct it before payment.",
                            line.full_product_name || line.product_id?.display_name || "Item"
                        ),
                    });
                    return false;
                }
            }
            if ((order.priceIncl ?? 0) < -0.01) {
                this.pos.dialog.add(AlertDialog, {
                    title: _t("Negative bill amount not allowed"),
                    body: _t("The total bill amount cannot be negative for a non-refund order."),
                });
                return false;
            }
        }
        return await super.isOrderValid(...arguments);
    },
});
