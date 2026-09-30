/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

export class KitchenRemarkDialog extends Component {
    static template = "pos_custom_kitchen.KitchenRemarkDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        confirm: Function,
        defaultRemark: { type: String, optional: true },
    };

    setup() {
        this.state = useState({
            remark: this.props.defaultRemark || "",
        });
    }

    addQuickRemark(text) {
        if (!this.state.remark || this.state.remark.trim() === "") {
            this.state.remark = text;
        } else {
            this.state.remark += ", " + text;
        }
    }

    async onConfirm() {
        await this.props.confirm(this.state.remark);
        this.props.close();
    }

    onCancel() {
        this.props.close();
    }
}

// Track kitchen_remark on PosOrder model in POS
if (PosOrder && PosOrder.prototype) {
    patch(PosOrder.prototype, {
        setup() {
            super.setup(...arguments);
            if (this.kitchen_remark === undefined) {
                this.kitchen_remark = "";
            }
        },
        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            json.kitchen_remark = this.kitchen_remark || "";
            return json;
        },
        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.kitchen_remark = json.kitchen_remark || "";
        },
    });
}

patch(ProductScreen.prototype, {
    async customSendToKitchen() {
        const order = this.currentOrder;
        if (!order || order.isEmpty()) {
            return;
        }

        this.env.services.dialog.add(KitchenRemarkDialog, {
            defaultRemark: order.kitchen_remark || "",
            confirm: async (remark) => {
                order.kitchen_remark = remark;
                if (typeof order.set_order_note === "function") {
                    order.set_order_note(remark);
                }

                // Sync draft / order to server so it appears in Kitchen Kanban
                await this.pos.syncAllOrders();

                // If order already has backend database ID, write kitchen_remark directly
                if (Number.isInteger(order.id)) {
                    await this.env.services.orm.write("pos.order", [order.id], {
                        kitchen_remark: remark,
                    });
                }

                const msg = remark
                    ? `Order sent to kitchen with remark: "${remark}"`
                    : "Order sent to kitchen successfully!";
                this.env.services.notification.add(msg, { type: "success" });
            },
        });
    }
});

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate = false) {
        // First sync to ensure the backend has the order created and the id fetched
        await this.pos.syncAllOrders();

        const order = this.currentOrder;

        // In Odoo 18+, if order is synced and has a database ID, order.id is an integer
        if (Number.isInteger(order.id)) {
            const serverState = await this.env.services.orm.searchRead("pos.order", [["id", "=", order.id]], ["kitchen_state"]);
            if (serverState.length > 0 && serverState[0].kitchen_state !== "done") {
                this.env.services.dialog.add(ConfirmationDialog, {
                    title: "Wait! Food Not Served Yet",
                    body: "You cannot accept the payment yet because the food has not been fully served to the customer. Please wait for the kitchen/waiter to mark it as 'Served' before completing the payment.",
                    confirmLabel: "Ok, I will wait",
                    cancelLabel: "Cancel"
                });
                return;
            }
        }

        return super.validateOrder(isForceValidate);
    }
});

