/** @odoo-module */

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { patch } from "@web/core/utils/patch";
import { generateQRCodeDataUrl } from "@point_of_sale/utils";

// Prevent duplicate unstyled tableName in ReceiptHeader since we render a prominent dedicated badge
patch(ReceiptHeader.prototype, {
    get tableName() {
        return "";
    },
});

patch(OrderReceipt.prototype, {
    get hasTableInfo() {
        const table = this.order.table_id || this.order.self_ordering_table_id;
        return Boolean(table);
    },

    get tableNumberFormatted() {
        const table = this.order.table_id || this.order.self_ordering_table_id;
        if (!table) {
            return "";
        }
        if (table.table_number !== undefined && table.table_number !== null && table.table_number !== "") {
            return String(table.table_number);
        }
        return table.name || "";
    },

    get floorNameFormatted() {
        const table = this.order.table_id || this.order.self_ordering_table_id;
        return table?.floor_id?.name || "";
    },

    get guestsCount() {
        return this.order.customer_count || (this.order.getCustomerCount ? this.order.getCustomerCount() : 1);
    },

    get isPaidWithUPI() {
        if (!this.paymentLines || !this.paymentLines.length) {
            return false;
        }
        return this.paymentLines.some((line) => {
            const name = (line.payment_method_id?.name || "").toLowerCase();
            return name.includes("upi") || name.includes("online");
        });
    },

    get showUpiQr() {
        if (!this.order.config?.show_upi_qr_on_bill || !this.order.config?.upi_id) {
            return false;
        }
        // Always show on unpaid / pro forma bill printed at table so customer can scan & pay
        if (!this.order.finalized) {
            return true;
        }
        // On finalized receipt, show if payment was made via UPI / Online
        return this.isPaidWithUPI;
    },

    get upiQrCode() {
        const upiId = this.order.config?.upi_id;
        if (!upiId) {
            return false;
        }
        const amount = this.order.roundedPriceIncl || this.order.priceIncl || 0;
        if (amount <= 0) {
            return false;
        }
        const companyName = this.order.company?.name || "Restaurant";
        const tableStr = this.tableNumberFormatted ? `Table_${this.tableNumberFormatted}` : "Order";
        const ref = this.order.pos_reference || this.order.name || "";
        const note = `${companyName} ${tableStr} ${ref}`.trim();
        const upiUrl = `upi://pay?pa=${encodeURIComponent(upiId)}&pn=${encodeURIComponent(companyName)}&am=${amount.toFixed(2)}&cu=INR&tn=${encodeURIComponent(note)}`;
        try {
            return generateQRCodeDataUrl(upiUrl, { width: 140, height: 140 });
        } catch (err) {
            console.error("Failed to generate UPI QR code:", err);
            return false;
        }
    },
});
