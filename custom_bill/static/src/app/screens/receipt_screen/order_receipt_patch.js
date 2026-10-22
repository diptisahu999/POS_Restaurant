/** @odoo-module */

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { patch } from "@web/core/utils/patch";

// Helper to convert number to Indian Currency Words
function numberToIndianWords(num) {
    if (num === undefined || num === null || isNaN(num) || num <= 0) {
        return "RS Zero Only.";
    }
    const n = Math.abs(Number(num));
    const intPart = Math.floor(n);
    const decPart = Math.round((n - intPart) * 100);

    const a = [
        "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"
    ];
    const b = [
        "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"
    ];

    function convertGroup(val) {
        let str = "";
        if (val >= 100) {
            str += a[Math.floor(val / 100)] + " Hundred ";
            val %= 100;
        }
        if (val >= 20) {
            str += b[Math.floor(val / 10)] + (val % 10 !== 0 ? " " + a[val % 10] : "");
        } else if (val > 0) {
            str += a[val];
        }
        return str.trim();
    }

    let words = "";
    let rem = intPart;

    const crore = Math.floor(rem / 10000000);
    rem %= 10000000;
    const lakh = Math.floor(rem / 100000);
    rem %= 100000;
    const thousand = Math.floor(rem / 1000);
    rem %= 1000;
    const hundreds = rem;

    if (crore > 0) words += convertGroup(crore) + " Crore ";
    if (lakh > 0) words += convertGroup(lakh) + " Lakh ";
    if (thousand > 0) words += convertGroup(thousand) + " Thousand ";
    if (hundreds > 0) words += convertGroup(hundreds);

    words = words.trim();
    if (!words) words = "Zero";

    let result = `RS ${words}`;
    if (decPart > 0) {
        result += ` and ${convertGroup(decPart)} Paise`;
    }
    result += " Only.";
    return result;
}

// Suppress unstyled elements in standard header
patch(ReceiptHeader.prototype, {
    get tableName() {
        return "";
    },
});

patch(OrderReceipt.prototype, {
    get hasTableInfo() {
        return true;
    },

    get tableNumberFormatted() {
        const table = this.order.table_id || this.order.self_ordering_table_id || this.order.table;
        if (!table) {
            return "TA15";
        }
        const val = table.table_number !== undefined && table.table_number !== null && table.table_number !== ""
            ? String(table.table_number).trim()
            : String(table.name || "").trim();

        if (/^\d+$/.test(val)) {
            return `T-${val.padStart(2, "0")}`;
        }
        return val || "TA15";
    },

    get stewardNameFormatted() {
        const waiter = this.order.server || this.order.waiter || this.order.employee;
        if (waiter && waiter.name) {
            return waiter.name;
        }
        return this.cashierNameFormatted || "ADMIN";
    },

    get guestsCount() {
        return this.order.customer_count || (this.order.getCustomerCount ? this.order.getCustomerCount() : 1);
    },

    get billNumberFormatted() {
        const ref = this.order.pos_reference || this.order.name || "";
        const m = ref.match(/(\d+)$/);
        if (m) {
            return `ARC${m[1].padStart(3, "0")}`;
        }
        if (this.order.tracking_number) {
            return `ARC${String(this.order.tracking_number).padStart(3, "0")}`;
        }
        return "ARC001";
    },

    get billDateFormatted() {
        const date = this.order.date_order ? new Date(this.order.date_order) : new Date();
        const dd = String(date.getDate()).padStart(2, "0");
        const mm = String(date.getMonth() + 1).padStart(2, "0");
        const yy = String(date.getFullYear()).slice(-2);
        let hours = date.getHours();
        const ampm = hours >= 12 ? "pm" : "am";
        hours = hours % 12 || 12;
        const hh = String(hours).padStart(2, "0");
        const min = String(date.getMinutes()).padStart(2, "0");
        const ss = String(date.getSeconds()).padStart(2, "0");
        return `${dd}/${mm}/${yy}   ${hh}:${min}:${ss} ${ampm}`;
    },

    get kotNumbersFormatted() {
        if (this.order._printed_round_ids && this.order._printed_round_ids.size) {
            return Array.from(this.order._printed_round_ids).join(", ");
        }
        if (this.order.kitchen_round_ids && this.order.kitchen_round_ids.length) {
            return this.order.kitchen_round_ids.map(r => r.id || r.sequence || r).join(", ");
        }
        return "";
    },

    get receiptLines() {
        const lines = typeof this.order.get_orderlines === "function"
            ? this.order.get_orderlines()
            : (this.order.lines ? [...this.order.lines] : []);

        return lines
            .filter(line => !line.isDiscountLine && (typeof line.get_product === "function" ? line.get_product() : line.product_id))
            .map(line => {
                const prod = (typeof line.get_product === "function" ? line.get_product() : line.product_id) || {};
                const name = (typeof line.get_full_product_name === "function" ? line.get_full_product_name() : line.full_product_name) || prod.display_name || prod.name || "Item";
                const qty = typeof line.get_quantity === "function" ? line.get_quantity() : (line.qty || 1);
                const unitPrice = typeof line.get_unit_price === "function" ? line.get_unit_price() : (line.price_unit || 0);
                const subtotal = typeof line.get_price_without_tax === "function" ? line.get_price_without_tax() : (line.price_subtotal !== undefined ? line.price_subtotal : (unitPrice * qty));

                return {
                    uuid: line.uuid || line.id || line.cid,
                    product_name: name,
                    qty: Number(qty) % 1 === 0 ? Number(qty).toFixed(0) : Number(qty).toFixed(2),
                    unit_price: unitPrice,
                    price_subtotal: subtotal,
                    discount: line.discount || 0,
                };
            });
    },

    get subtotalAmount() {
        return this.receiptLines.reduce((acc, l) => acc + (l.unit_price * l.qty), 0);
    },

    get discountAmount() {
        let disc = 0;
        const lines = typeof this.order.get_orderlines === "function" ? this.order.get_orderlines() : (this.order.lines || []);
        for (const l of lines) {
            const qty = typeof l.get_quantity === "function" ? l.get_quantity() : (l.qty || 1);
            const unitPrice = typeof l.get_unit_price === "function" ? l.get_unit_price() : (l.price_unit || 0);
            if (l.discount && l.discount > 0) {
                disc += (unitPrice * qty * l.discount) / 100;
            }
            if (l.isDiscountLine || (unitPrice < 0)) {
                disc += Math.abs(unitPrice * qty);
            }
        }
        if (disc === 0 && typeof this.order.getTotalDiscount === "function") {
            disc = this.order.getTotalDiscount() || 0;
        }
        return Math.round(disc * 100) / 100;
    },

    get discountLabelFormatted() {
        const lines = typeof this.order.get_orderlines === "function" ? this.order.get_orderlines() : (this.order.lines || []);
        const discLine = lines.find(l => l.discount > 0);
        if (discLine && discLine.discount) {
            return `Discount(FD-${discLine.discount}%)`;
        }
        return "Discount";
    },

    get netTaxableAmount() {
        return Math.max(0, this.subtotalAmount - this.discountAmount);
    },

    get taxAmount() {
        // Enforce 5% Tax on net taxable amount
        return Math.round(this.netTaxableAmount * 0.05 * 100) / 100;
    },

    get sgstAmount() {
        // 2.5% SGST
        return Math.round(this.netTaxableAmount * 0.025 * 100) / 100;
    },

    get cgstAmount() {
        // 2.5% CGST (total 5% minus SGST to prevent 1 paise rounding discrepancy)
        return Math.round((this.taxAmount - this.sgstAmount) * 100) / 100;
    },

    get grossPayableAmount() {
        return this.netTaxableAmount + this.taxAmount;
    },

    get roundingAmount() {
        if (this.order.appliedRounding !== undefined && this.order.appliedRounding !== null && this.order.appliedRounding !== 0) {
            return this.order.appliedRounding;
        }
        // Match thermal receipt standard integer rounding
        const rounded = Math.round(this.grossPayableAmount);
        return Math.round((rounded - this.grossPayableAmount) * 100) / 100;
    },

    get payableAmount() {
        return Math.round((this.grossPayableAmount + this.roundingAmount) * 100) / 100;
    },

    get amountInWordsFormatted() {
        return numberToIndianWords(this.payableAmount);
    },

    get cashierNameFormatted() {
        return (typeof this.order.getCashierName === "function" ? this.order.getCashierName() : (this.order.cashier?.name || "Mitchell Admin"));
    },

    formatAmount(val) {
        if (val === undefined || val === null || isNaN(val)) {
            return "0.00";
        }
        return Number(val).toFixed(2);
    },
});
