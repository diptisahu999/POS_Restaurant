/** @odoo-module **/

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async sendOrderInPreparation(order, opts = {}) {
        const result = await super.sendOrderInPreparation(...arguments);
        if (order && !opts.cancelled && order.order_status === "pending") {
            if (typeof order.set_order_status === "function") {
                order.set_order_status("preparing");
            } else {
                order.order_status = "preparing";
            }
        }
        return result;
    },

    async afterOrderValidation(order, ...args) {
        if (order) {
            if (typeof order.set_order_status === "function") {
                order.set_order_status("done");
            } else {
                order.order_status = "done";
            }
        }
        return await super.afterOrderValidation(order, ...args);
    },

    clickSaveOrder() {
        if (this.config.module_pos_restaurant && !this.getOrder()?.table_id) {
            return;
        }
        return super.clickSaveOrder(...arguments);
    },
});
