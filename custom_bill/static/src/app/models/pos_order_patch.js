/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals);
        this.nc_reason = vals.nc_reason || "";
        this.discount_reason = vals.discount_reason || "";
        this.discount_percentage = vals.discount_percentage || 0;
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
        const quant = typeof quantity === "number" ? quantity : parseFloat("" + (quantity ? quantity : 0));
        if (!this.order_id?.preset_id?.is_return && !this.refunded_orderline_id && (quant < 0 || quantity === "-")) {
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


