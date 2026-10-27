/** @odoo-module */

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
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
            .filter(line => !line.isDiscountLine && !line.uiState?.isDiscountLine && (typeof line.get_unit_price === "function" ? line.get_unit_price() >= 0 : (line.price_unit >= 0)) && (typeof line.get_product === "function" ? line.get_product() : line.product_id))
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

    get ncPaymentLine() {
        const lines = (
            this.order.payment_ids ||
            this.order.paymentlines ||
            (typeof this.order.get_paymentlines === "function" ? this.order.get_paymentlines() : [])
        ).filter(p => !p.is_change);
        return lines.find(p => {
            const name = (p.payment_method_id?.name || p.name || "").toLowerCase().trim();
            return name.includes("no charge") || name.includes("(nc)") || name === "nc" || !!p.nc_reason;
        });
    },

    get isNcOrder() {
        return Boolean(this.ncPaymentLine || this.order.nc_reason);
    },

    get ncReason() {
        return this.ncPaymentLine?.nc_reason || this.order.nc_reason || "";
    },

    get subtotalAmount() {
        if (this.isNcOrder) {
            return 0;
        }
        return this.receiptLines.reduce((acc, l) => acc + (l.unit_price * l.qty), 0);
    },

    get allOrderlines() {
        if (typeof this.order.getOrderlines === "function") {
            return this.order.getOrderlines();
        }
        if (typeof this.order.get_orderlines === "function") {
            return this.order.get_orderlines();
        }
        return this.order.lines ? [...this.order.lines] : [];
    },

    get discountAmount() {
        let disc = 0;
        const lines = this.allOrderlines;
        for (const l of lines) {
            const qty = typeof l.get_quantity === "function" ? l.get_quantity() : (l.qty || 1);
            const unitPrice = typeof l.get_unit_price === "function" ? l.get_unit_price() : (l.price_unit || 0);
            if (l.discount && l.discount > 0) {
                disc += (unitPrice * qty * l.discount) / 100;
            }
            if (l.isDiscountLine || l.uiState?.isDiscountLine || (unitPrice < 0)) {
                disc += Math.abs(unitPrice * qty);
            }
        }
        if (disc === 0 && typeof this.order.getTotalDiscount === "function") {
            disc = this.order.getTotalDiscount() || 0;
        }
        return Math.round(disc * 100) / 100;
    },

    get discountReason() {
        if (this.order.uiState?.discount_reason || this.order.discount_reason) {
            return this.order.uiState?.discount_reason || this.order.discount_reason;
        }
        const lines = this.allOrderlines;
        const globalDiscLine = lines.find(l => 
            l.isDiscountLine || 
            l.uiState?.isDiscountLine || 
            (typeof l.get_unit_price === "function" ? l.get_unit_price() < 0 : (l.price_unit < 0))
        );
        if (globalDiscLine) {
            if (globalDiscLine.uiState?.discount_reason || globalDiscLine.discount_reason) {
                return globalDiscLine.uiState?.discount_reason || globalDiscLine.discount_reason;
            }
            const note = globalDiscLine.customer_note || globalDiscLine.note || "";
            const m = note.match(/-\s*(.+)$/);
            if (m) {
                return m[1].trim();
            }
        }
        return "";
    },

    get discountLabelFormatted() {
        const lines = this.allOrderlines;
        let label = "Discount";
        const reason = this.discountReason;
        
        // 1. Stored discount percentage on order
        const storedPct = this.order.uiState?.discount_percentage || this.order.discount_percentage;
        if (storedPct) {
            const p = Number(storedPct);
            const pct = p % 1 === 0 ? p.toFixed(0) : p.toFixed(2);
            label = `Discount ${pct}%`;
        } else {
            // 2. Line-level discount percentage
            const discLine = lines.find(l => l.discount > 0);
            if (discLine && discLine.discount) {
                const pct = Number(discLine.discount) % 1 === 0 ? Number(discLine.discount).toFixed(0) : Number(discLine.discount).toFixed(2);
                label = `Discount ${pct}%`;
            } else {
                // 3. Global discount line note
                const globalDiscLine = lines.find(l => l.isDiscountLine || l.uiState?.isDiscountLine || (typeof l.get_unit_price === "function" ? l.get_unit_price() < 0 : (l.price_unit < 0)));
                let pctFound = false;
                if (globalDiscLine) {
                    const note = globalDiscLine.customer_note || globalDiscLine.note || "";
                    const pctMatch = note.match(/(\d+(?:\.\d+)?)\s*%/);
                    if (pctMatch) {
                        label = `Discount ${pctMatch[1]}%`;
                        pctFound = true;
                    } else if (/fixed/i.test(note)) {
                        label = `Discount ${this.formatAmount(this.discountAmount)}`;
                        pctFound = true;
                    }
                }
                
                // 4. Fallback: Compute percentage directly from discountAmount vs subtotalAmount
                if (!pctFound && this.subtotalAmount > 0 && this.discountAmount > 0) {
                    const calculatedPct = (this.discountAmount / this.subtotalAmount) * 100;
                    if (Math.abs(calculatedPct - Math.round(calculatedPct)) < 0.01) {
                        label = `Discount ${Math.round(calculatedPct)}%`;
                    } else {
                        label = `Discount ${this.formatAmount(this.discountAmount)}`;
                    }
                }
            }
        }

        if (reason) {
            return `${label} (${reason})`;
        }
        return label;
    },

    get taxAmount() {
        if (this.isNcOrder) {
            return 0;
        }
        // 5% Tax calculated on Sub Total (discount does not reduce tax)
        return Math.round(this.subtotalAmount * 0.05 * 100) / 100;
    },

    get sgstAmount() {
        if (this.isNcOrder) {
            return 0;
        }
        return Math.round(this.subtotalAmount * 0.025 * 100) / 100;
    },

    get cgstAmount() {
        if (this.isNcOrder) {
            return 0;
        }
        return Math.round((this.taxAmount - this.sgstAmount) * 100) / 100;
    },

    get grossPayableAmount() {
        if (this.isNcOrder) {
            return 0;
        }
        return Math.max(0, this.subtotalAmount - this.discountAmount) + this.taxAmount;
    },

    get roundingAmount() {
        if (this.isNcOrder) {
            return 0;
        }
        if (this.order.appliedRounding !== undefined && this.order.appliedRounding !== null && this.order.appliedRounding !== 0) {
            return this.order.appliedRounding;
        }
        // Match thermal receipt standard integer rounding
        const rounded = Math.round(this.grossPayableAmount);
        return Math.round((rounded - this.grossPayableAmount) * 100) / 100;
    },

    get payableAmount() {
        if (this.isNcOrder) {
            return 0;
        }
        return Math.round((this.grossPayableAmount + this.roundingAmount) * 100) / 100;
    },

    get paymentMethodsFormatted() {
        const paymentLines = (
            this.order.payment_ids ||
            this.order.paymentlines ||
            (typeof this.order.get_paymentlines === "function" ? this.order.get_paymentlines() : [])
        ).filter(p => !p.is_change);
        if (!paymentLines.length) {
            return [];
        }
        let remainingToCover = this.payableAmount;
        return paymentLines.map(p => {
            const rawName = p.payment_method_id?.name || p.name || "Payment";
            const isNc = rawName.toLowerCase().includes("no charge") || rawName.toLowerCase().includes("(nc)") || rawName.toLowerCase() === "nc" || !!p.nc_reason;
            const isCash = Boolean(p.payment_method_id?.is_cash_count || rawName.toLowerCase().includes("cash"));
            const reason = p.nc_reason || (isNc ? this.ncReason : "");
            
            let amount = 0;
            if (isNc) {
                amount = 0;
            } else {
                const lineAmount = typeof p.getAmount === "function" ? p.getAmount() : (p.amount || 0);
                if (isCash) {
                    amount = lineAmount;
                } else {
                    // For non-cash payment methods (UPI, Card), amount on bill should not exceed payable amount
                    amount = Math.min(lineAmount, remainingToCover);
                    remainingToCover = Math.max(0, remainingToCover - amount);
                }
            }

            return {
                name: rawName,
                reason: reason,
                amount: amount,
                isNc: isNc,
            };
        });
    },

    get changeAmount() {
        if (this.isNcOrder) {
            return 0;
        }
        // Change is only applicable if cash was used and paid cash exceeds payableAmount
        const cashPayment = (this.order.payment_ids || []).find(p => !p.is_change && (p.payment_method_id?.is_cash_count || (p.payment_method_id?.name || p.name || "").toLowerCase().includes("cash")));
        if (!cashPayment) {
            return 0;
        }
        return typeof this.order.get_change === "function" ? this.order.get_change() : (this.order.change || 0);
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

patch(ReceiptScreen.prototype, {
    get isNcOrder() {
        const order = this.currentOrder;
        if (!order) {
            return false;
        }
        if (order.nc_reason) {
            return true;
        }
        const paymentLines = (
            order.payment_ids ||
            order.paymentlines ||
            (typeof order.get_paymentlines === "function" ? order.get_paymentlines() : [])
        ).filter(p => !p.is_change);
        return Boolean(paymentLines.find(p => {
            const name = (p.payment_method_id?.name || p.name || "").toLowerCase().trim();
            return name.includes("no charge") || name.includes("(nc)") || name === "nc" || !!p.nc_reason;
        }));
    },

    get orderAmountPlusTip() {
        if (this.isNcOrder) {
            return this.env.utils.formatCurrency(0);
        }
        return super.orderAmountPlusTip;
    },
});
