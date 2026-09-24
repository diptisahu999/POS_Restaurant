/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals);
        this.order_status = vals.order_status || "pending";
    },
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        data.order_status = this.order_status || "pending";
        return data;
    },
    set_order_status(status) {
        this.order_status = status;
        if (typeof this.update === "function") {
            this.update({ order_status: status });
        }
        const dataService = this.models?.data || this.models?.["pos.order"]?.data;
        if (dataService && this.isSynced && this.id) {
            dataService.ormWrite("pos.order", [this.id], { order_status: status });
        }
    },
});
