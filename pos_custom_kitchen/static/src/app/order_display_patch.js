/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { FloorScreen } from "@pos_restaurant/app/screens/floor_screen/floor_screen";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(OrderDisplay.prototype, {
    get comboSortedLines() {
        const lines = super.comboSortedLines;
        return lines.filter(line => !line.isDiscountLine);
    }
});

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals);
        this.bill_printed = Boolean(vals.bill_printed);
    },

    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        data.bill_printed = Boolean(this.bill_printed);
        return data;
    },
});

patch(ControlButtons.prototype, {
    async clickPrintBill() {
        if (this.currentOrder) {
            this.currentOrder.bill_printed = true;
            if (this.currentOrder.isSynced) {
                this.pos.data.write("pos.order", [this.currentOrder.id], { bill_printed: true });
            }
        }
        return await super.clickPrintBill(...arguments);
    },
});

patch(PosStore.prototype, {
    async printReceipt({ order = this.getOrder(), printBillActionTriggered = false } = {}) {
        if (printBillActionTriggered && order) {
            order.bill_printed = true;
            if (order.isSynced) {
                this.data.write("pos.order", [order.id], { bill_printed: true });
            }
        }
        return await super.printReceipt(...arguments);
    },

    async addLineToOrder(vals, order, opts = {}, configure = true) {
        if (!order?.preset_id?.is_return && vals && vals.qty < 0 && !opts.force) {
            this.dialog.add(AlertDialog, {
                title: _t("Negative quantity not allowed"),
                body: _t("The quantity of the product cannot be negative."),
            });
            return;
        }
        if (order && order.bill_printed) {
            order.bill_printed = false;
            if (order.isSynced) {
                this.data.write("pos.order", [order.id], { bill_printed: false });
            }
        }
        return await super.addLineToOrder(...arguments);
    },
});

patch(FloorScreen.prototype, {
    getTableOrders(table) {
        if (!table) {
            return [];
        }
        const activeOrders = [];
        if (typeof table.getOrder === "function") {
            const singleOrder = table.getOrder();
            if (singleOrder && !singleOrder.finalized) {
                activeOrders.push(singleOrder);
            }
        }
        if (typeof table.getOrders === "function") {
            const multiOrders = table.getOrders().filter((o) => !o.finalized);
            for (const o of multiOrders) {
                if (!activeOrders.includes(o)) {
                    activeOrders.push(o);
                }
            }
        }
        return activeOrders;
    },

    getTableStatus(table) {
        const orders = this.getTableOrders(table);
        if (!orders || orders.length === 0) {
            return "available"; // Colour - Green: Available Table
        }
        const anyBillPrinted = orders.some((o) => o.bill_printed);
        if (anyBillPrinted) {
            return "bill_printed"; // Colour - Yellow: Bill Printed
        }
        return "occupied"; // Colour - Blue: On use Table
    },

    getTableStatusClass(table) {
        const status = this.getTableStatus(table);
        if (status === "bill_printed") {
            return "table-bill-printed";
        } else if (status === "occupied") {
            return "table-in-use";
        }
        return "table-available";
    },

    getTableColor(table) {
        const status = this.getTableStatus(table);
        if (status === "available") {
            return "#22c55e"; // Green for Available Table
        } else if (status === "bill_printed") {
            return "#eab308"; // Yellow for Bill Printed
        }
        return "#2563eb"; // Blue for On use Table
    },

    getTableBg(table) {
        return "#ffffff";
    },

    getTableTextColor(table) {
        return "#0f172a";
    },

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
