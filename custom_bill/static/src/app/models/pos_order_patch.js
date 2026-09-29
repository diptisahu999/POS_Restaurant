/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals);
        this.nc_reason = vals.nc_reason || "";
    },

    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        if (this.nc_reason) {
            data.nc_reason = this.nc_reason;
        }
        return data;
    },
});
