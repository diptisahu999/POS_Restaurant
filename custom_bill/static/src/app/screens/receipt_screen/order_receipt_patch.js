/** @odoo-module */

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { patch } from "@web/core/utils/patch";

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

    get ncAmount() {
        if (!this.paymentLines || !this.paymentLines.length) {
            return 0;
        }
        let totalNc = 0;
        for (const line of this.paymentLines) {
            const name = (line.payment_method_id?.name || "").toLowerCase().trim();
            const isNc = name.includes("no charge") || name.includes("(nc)") || name === "nc" || line.payment_method_id?.id === 6 || Boolean(line.nc_reason);
            if (isNc) {
                totalNc += typeof line.getAmount === "function" ? line.getAmount() : (line.amount || 0);
            }
        }
        return totalNc;
    },

    get ncAmountFormatted() {
        return this.formatCurrency(this.ncAmount);
    },

    get payableAmount() {
        const total = this.order.roundedPriceIncl !== undefined && this.order.roundedPriceIncl !== null
            ? this.order.roundedPriceIncl
            : (this.order.priceIncl || 0);
        return Math.max(0, total - this.ncAmount);
    },

    get payableAmountFormatted() {
        return this.formatCurrency(this.payableAmount);
    },

    get hasNcPayment() {
        return this.ncAmount > 0 || Boolean(this.order.nc_reason);
    },

    get ncReason() {
        if (this.order.nc_reason) {
            return this.order.nc_reason;
        }
        if (this.paymentLines) {
            const ncLine = this.paymentLines.find((line) => line.nc_reason);
            if (ncLine && ncLine.nc_reason) {
                return ncLine.nc_reason;
            }
        }
        return "";
    },
});
