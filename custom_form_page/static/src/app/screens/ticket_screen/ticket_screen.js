/** @odoo-module **/

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { SelectionPopup } from "@point_of_sale/app/components/popups/selection_popup/selection_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    activeOrderFilter(o) {
        if (o.isEmpty() && !o.isSynced && (o.isDirectSale || !o.table_id)) {
            return false;
        }
        return super.activeOrderFilter(o);
    },

    getOrderStatus(order) {
        if (!order) return "pending";
        if (order.state === "paid" || order.state === "done") {
            return order.order_status || "done";
        }
        return order.order_status || "pending";
    },

    async onCycleOrderStatus(order) {
        const current = this.getOrderStatus(order);
        const selectedStatus = await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("Change Order Status"),
            list: [
                {
                    id: "pending",
                    label: _t("Pending"),
                    isSelected: current === "pending",
                    item: "pending",
                },
                {
                    id: "preparing",
                    label: _t("Preparing"),
                    isSelected: current === "preparing",
                    item: "preparing",
                },
                {
                    id: "done",
                    label: _t("Done"),
                    isSelected: current === "done",
                    item: "done",
                },
            ],
        });

        if (selectedStatus) {
            order.order_status = selectedStatus;
            if (typeof order.update === "function") {
                order.update({ order_status: selectedStatus });
            }
            if (this.pos?.data && order.isSynced && order.id) {
                await this.pos.data.ormWrite("pos.order", [order.id], {
                    order_status: selectedStatus,
                });
            }
        }
    },
});
