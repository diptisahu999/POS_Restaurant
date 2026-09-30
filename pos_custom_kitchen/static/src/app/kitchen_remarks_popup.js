/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class KitchenRemarksPopup extends Component {
    static template = "pos_custom_kitchen.KitchenRemarksPopup";
    static components = { Dialog };
    // Use array-style props like native Odoo 19 POS popups to avoid type validation issues
    static props = ["close", "getPayload", "orderlines"];

    setup() {
        super.setup();
        const initialNotes = {};
        for (const line of (this.props.orderlines || [])) {
            const key = this._getKey(line);
            let existingNote = "";
            try {
                if (typeof line.get_customer_note === "function") {
                    existingNote = line.get_customer_note() || "";
                } else {
                    existingNote = line.customer_note || line.note || "";
                }
            } catch (e) {
                existingNote = "";
            }
            initialNotes[key] = existingNote;
        }
        this.state = useState({ notes: initialNotes });
    }

    _getKey(line) {
        return String(line.uuid || line.id || line.cid || "line_" + Math.random());
    }

    getLineDisplayName(line) {
        try {
            if (typeof line.get_full_product_name === "function") {
                return line.get_full_product_name();
            }
            if (line.product_id) {
                return line.product_id.display_name || line.product_id.name || "Item";
            }
        } catch (e) {}
        return "Item";
    }

    getLineQuantity(line) {
        try {
            if (typeof line.get_quantity === "function") {
                return line.get_quantity();
            }
            return line.qty || 1;
        } catch (e) {
            return 1;
        }
    }

    onNoteInput(key, ev) {
        this.state.notes[key] = ev.target.value;
    }

    confirm() {
        this.props.getPayload(this.state.notes);
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
