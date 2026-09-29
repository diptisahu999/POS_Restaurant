/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    async addNewPaymentLine(paymentMethod) {
        const name = (paymentMethod?.name || "").toLowerCase().trim();
        const isNcMethod = name.includes("no charge") || name.includes("(nc)") || name === "nc" || paymentMethod?.id === 6;

        if (isNcMethod) {
            const buttons = [
                { label: _t("Complimentary") },
                { label: _t("Manager Approval") },
                { label: _t("Staff Meal") },
                { label: _t("VIP / Owner Guest") },
                { label: _t("Food Quality Issue") },
            ];

            const reason = await makeAwaitable(this.dialog, TextInputPopup, {
                title: _t("No Charge (NC) - Reason Required"),
                placeholder: _t("Select a quick reason above or enter reason here..."),
                buttons,
                rows: 3,
            });

            // If user closed or cancelled the dialog without entering a reason
            if (!reason || !reason.trim()) {
                return false;
            }

            const cleanReason = reason.trim();
            const res = await super.addNewPaymentLine(paymentMethod);
            if (res) {
                this.currentOrder.nc_reason = cleanReason;
                const newPaymentLine = this.paymentLines.at(-1);
                if (newPaymentLine) {
                    newPaymentLine.nc_reason = cleanReason;
                }
            }
            return res;
        }

        return super.addNewPaymentLine(paymentMethod);
    },
});
