/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class GlobalDiscountPopup extends Component {
    static template = "pos_custom_kitchen.GlobalDiscountPopup";
    static components = { Dialog };
    static props = ["close", "getPayload", "startingValue"];

    setup() {
        super.setup();
        this.state = useState({
            percentage: this.props.startingValue || "",
            reason: "",
            quickReasons: [
                "Complimentary",
                "Manager Approval",
                "Staff Meal",
                "VIP / Owner Guest"
            ]
        });
    }

    onPercentageInput(ev) {
        this.state.percentage = ev.target.value;
    }

    onReasonInput(ev) {
        this.state.reason = ev.target.value;
    }

    setQuickReason(reason) {
        this.state.reason = reason;
    }

    confirm() {
        this.props.getPayload({
            percentage: parseFloat(this.state.percentage),
            reason: this.state.reason
        });
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
