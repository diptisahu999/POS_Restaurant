/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

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

