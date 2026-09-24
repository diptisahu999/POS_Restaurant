/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    onMounted() {
        super.onMounted(...arguments);
        const zeroLines = this.paymentLines.filter((l) => !l.amount || l.amount === 0);
        for (const line of zeroLines) {
            this.currentOrder.removePaymentline(line);
        }
    },

    async addNewPaymentLine(paymentMethod) {
        // If remaining due is already 0 or order is fully covered:
        if (this.currentOrder.remainingDue <= 0 && this.paymentLines.length > 0) {
            const lastLine = this.paymentLines.at(-1);
            // If clicking a DIFFERENT payment method, switch/replace the unpaid line
            if (
                lastLine &&
                !lastLine.is_paid &&
                lastLine.payment_method_id.id !== paymentMethod.id
            ) {
                const prevAmount = lastLine.getAmount();
                this.currentOrder.removePaymentline(lastLine);
                const result = this.currentOrder.addPaymentline(paymentMethod);
                if (result && result.status) {
                    result.data.setAmount(prevAmount);
                    this.numberBuffer.set(prevAmount.toString());
                }
                return true;
            }
            // If already paid / same method clicked, ignore to prevent duplicate 0-amount lines
            return false;
        }

        // Remove any existing 0-amount lines
        const zeroLines = this.paymentLines.filter((l) => !l.amount || l.amount === 0);
        for (const line of zeroLines) {
            this.currentOrder.removePaymentline(line);
        }

        // If there's an existing single unpaid payment line of a different method, replace it
        if (
            this.paymentLines.length === 1 &&
            !this.paymentLines[0].is_paid &&
            this.paymentLines[0].payment_method_id.id !== paymentMethod.id
        ) {
            this.currentOrder.removePaymentline(this.paymentLines[0]);
        }

        return await super.addNewPaymentLine(...arguments);
    },

    updateSelectedPaymentline(amount = false) {
        // Never auto-add default payment lines during buffer updates
        if (!this.selectedPaymentLine) {
            return;
        }
        if (amount === false) {
            if (this.numberBuffer.get() === null) {
                amount = null;
            } else if (this.numberBuffer.get() === "") {
                amount = 0;
            } else {
                amount = this.numberBuffer.getFloat();
            }
        }
        const hasCashPaymentMethod = this.payment_methods_from_config.some(
            (method) => method.type === "cash"
        );
        if (
            !hasCashPaymentMethod &&
            amount > this.currentOrder.remainingDue + this.selectedPaymentLine.amount
        ) {
            this.selectedPaymentLine.setAmount(0);
            this.numberBuffer.set(this.currentOrder.remainingDue.toString());
            amount = this.currentOrder.remainingDue;
        }
        if (amount === null) {
            this.deletePaymentLine(this.selectedPaymentLine.uuid);
        } else {
            this.selectedPaymentLine.setAmount(amount);
        }
    },
});
