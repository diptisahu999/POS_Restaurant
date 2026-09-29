/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(ProductScreen.prototype, {
    async customSendToKitchen() {
        // Push the draft to the server so it appears in the Kitchen Kanban
        await this.pos.syncAllOrders();
        this.env.services.notification.add("Order sent to kitchen successfully!", { type: "success" });
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
