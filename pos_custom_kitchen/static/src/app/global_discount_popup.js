/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class GlobalDiscountPopup extends Component {
    static template = "pos_custom_kitchen.GlobalDiscountPopup";
    static components = { Dialog };
    static props = ["close", "getPayload", "startingValue", "subtotal"];

    setup() {
        super.setup();
        this.state = useState({
            discountType: "percentage", // "percentage" or "fixed"
            percentage: this.props.startingValue || "",
            fixedAmount: "",
            reason: "",
            quickReasons: [
                "Complimentary",
                "Manager Approval",
                "Staff Meal",
                "VIP / Owner Guest"
            ]
        });
    }

    setDiscountType(type) {
        this.state.discountType = type;
    }

    onPercentageInput(ev) {
        this.state.percentage = ev.target.value;
    }

    onFixedAmountInput(ev) {
        this.state.fixedAmount = ev.target.value;
    }

    onReasonInput(ev) {
        this.state.reason = ev.target.value;
    }

    setQuickReason(reason) {
        this.state.reason = reason;
    }

    confirm() {
        const type = this.state.discountType;
        let value = 0;
        
        if (type === "percentage") {
            value = parseFloat(this.state.percentage) || 0;
        } else {
            value = parseFloat(this.state.fixedAmount) || 0;
        }

        this.props.getPayload({
            type: type,
            value: value,
            reason: this.state.reason
        });
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
