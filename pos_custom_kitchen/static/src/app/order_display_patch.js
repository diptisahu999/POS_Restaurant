/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { FloorScreen } from "@pos_restaurant/app/screens/floor_screen/floor_screen";

patch(OrderDisplay.prototype, {
    get comboSortedLines() {
        const lines = super.comboSortedLines;
        return lines.filter(line => !line.isDiscountLine);
    }
});

patch(FloorScreen.prototype, {
    async onClickTable(table, ev) {
        await super.onClickTable(...arguments);
        
        // If we are not in edit mode or transfer mode, and we just selected a table
        if (!this.pos.isEditMode && !this.pos.isOrderTransferMode && !table.parent_id) {
            const order = this.pos.getOrder();
            if (order && order.table_id && order.table_id.id === table.id) {
                // Instantly open the guest wizard
                await this.pos.setCustomerCount(order, false);
            }
        }
    }
});
