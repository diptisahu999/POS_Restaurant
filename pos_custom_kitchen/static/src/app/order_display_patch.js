/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { FloorScreen } from "@pos_restaurant/app/screens/floor_screen/floor_screen";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
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

patch(PosOrderline.prototype, {
    setup(vals) {
        super.setup(...arguments);
        this.is_sent_to_kitchen = Boolean(vals.is_sent_to_kitchen);
    },

    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        data.is_sent_to_kitchen = Boolean(this.is_sent_to_kitchen);
        return data;
    },

    canBeMergedWith(orderline) {
        // Items sent to kitchen cannot be merged into by new reorder items
        if (this.is_sent_to_kitchen || orderline.is_sent_to_kitchen) {
            return false;
        }
        return super.canBeMergedWith(...arguments);
    },

    setQuantity(quantity, keep_price) {
        if (this.is_sent_to_kitchen && this.qty !== undefined && this.qty !== 0) {
            const quant = typeof quantity === "number" ? quantity : parseFloat("" + (quantity ? quantity : 0));
            if (quant !== this.qty) {
                return false;
            }
        }
        return super.setQuantity(...arguments);
    },

    setUnitPrice(price) {
        if (this.is_sent_to_kitchen && this.price_unit !== undefined) {
            return false;
        }
        return super.setUnitPrice(...arguments);
    },

    setDiscount(discount) {
        if (this.is_sent_to_kitchen && this.discount !== undefined) {
            return false;
        }
        return super.setDiscount(...arguments);
    },

    delete() {
        if (this.is_sent_to_kitchen && this.order_id && !this.order_id.finalized) {
            return false;
        }
        return super.delete(...arguments);
    },
});

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals);
        this.bill_printed = Boolean(vals.bill_printed);
        this.is_sent_to_kitchen = Boolean(vals.is_sent_to_kitchen);
    },

    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        data.bill_printed = Boolean(this.bill_printed);
        data.is_sent_to_kitchen = Boolean(this.is_sent_to_kitchen);
        return data;
    },

    removeOrderline(line) {
        if (line && line.is_sent_to_kitchen) {
            this.env?.services?.dialog?.add(AlertDialog, {
                title: _t("Item Locked"),
                body: _t("This item has already been sent to the kitchen and cannot be deleted."),
            });
            return false;
        }
        return super.removeOrderline(...arguments);
    },
});

patch(OrderSummary.prototype, {
    _setValue(val) {
        const selectedLine = this.currentOrder?.getSelectedOrderline();
        if (selectedLine && selectedLine.is_sent_to_kitchen) {
            this.dialog.add(AlertDialog, {
                title: _t("Item Locked"),
                body: _t("This item has already been sent to the kitchen and cannot be modified or deleted. To order more, please select the item from the catalog to add a new reorder."),
            });
            this.numberBuffer.reset();
            return;
        }
        return super._setValue(...arguments);
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
        return this.getTableColor(table);
    },

    getTableTextColor(table) {
        const status = this.getTableStatus(table);
        if (status === "occupied") {
            return "#ffffff";
        }
        return "#000000";
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
