/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";

export function isRefundOrReturnOrder(order) {
    if (!order) {
        return false;
    }
    return Boolean(
        order.isRefund ||
        order.preset_id?.is_return ||
        order.lines?.some((l) => Boolean(l.refunded_orderline_id))
    );
}

function isDiscountLineRecord(line, order) {
    if (!line) {
        return false;
    }
    const cfg = order?.config_id || line.config;
    return Boolean(
        line.isDiscountLine ||
        line.uiState?.isDiscountLine ||
        (cfg?.module_pos_discount && line.product_id?.id === cfg?.discount_product_id?.id)
    );
}

function getLineValues(line, order) {
    const qty = typeof line.getQuantity === "function" ? Number(line.getQuantity()) : Number(line.qty ?? 1);
    const price = typeof line.getUnitPrice === "function" ? Number(line.getUnitPrice()) : Number(line.price_unit ?? 0);
    const discount = Number(line.discount || 0);
    const baseAmount = price * qty * (1 - discount / 100);
    const lineIncl = line.priceIncl !== undefined ? Number(line.priceIncl) : baseAmount;
    const isDiscountLine = isDiscountLineRecord(line, order);
    return { qty, price, discount, baseAmount, lineIncl, isDiscountLine };
}

function isLineNegativeIssue(line, order, orderTotal) {
    if (!line || line.refunded_orderline_id) {
        return false;
    }
    const { qty, price, discount, lineIncl, isDiscountLine } = getLineValues(line, order);
    if (qty < 0) {
        return true;
    }
    if (isDiscountLine) {
        return orderTotal < -0.005 && lineIncl < -0.005;
    }
    return price < 0 || lineIncl < -0.005 || discount > 100;
}

export function hasNegativeOrderIssue(order) {
    if (!order || order.isEmpty() || isRefundOrReturnOrder(order)) {
        return false;
    }
    const orderTotal = Number(order.priceIncl ?? 0);
    if (orderTotal < -0.005) {
        return true;
    }
    const lines = typeof order.getOrderlines === "function"
        ? order.getOrderlines()
        : [...(order.lines || [])];
    return lines.some((line) => isLineNegativeIssue(line, order, orderTotal));
}

export class NegativeOrderPopup extends Component {
    static template = "pos_custom_kitchen.NegativeOrderPopup";
    static components = { Dialog };
    static props = ["close", "getPayload", "order", "actionLabel", "pos?"];

    setup() {
        super.setup();
        const order = this.props.order;
        const orderTotal = Number(order?.priceIncl ?? 0);
        const lines = typeof order?.getOrderlines === "function"
            ? order.getOrderlines()
            : [...(order?.lines || [])];

        const draftItems = [];
        for (const line of lines) {
            if (!isLineNegativeIssue(line, order, orderTotal)) {
                continue;
            }
            const { qty, price, discount, baseAmount, lineIncl, isDiscountLine } = getLineValues(line, order);

            // Convert unit price * qty * (1 - disc/100) into tax-included subtotal accurately
            // regardless of whether taxes on this product are price-included or price-excluded.
            let inclRatio = 1;
            if (Math.abs(baseAmount) > 0.0001) {
                inclRatio = lineIncl / baseAmount;
            } else if (line.tax_ids?.length) {
                const exclPctSum = line.tax_ids.reduce(
                    (acc, t) => acc + (!t.price_include && t.amount_type === "percent" ? (t.amount || 0) : 0),
                    0
                );
                inclRatio = 1 + exclPctSum / 100;
            }

            let issueLabel = _t("Negative amount");
            if (isDiscountLine) {
                issueLabel = _t("Discount exceeds bill");
            } else if (qty < 0) {
                issueLabel = _t("Negative quantity");
            } else if (price < 0) {
                issueLabel = _t("Negative price");
            } else if (discount > 100) {
                issueLabel = _t("Discount over 100%");
            }

            draftItems.push({
                uuid: line.uuid || String(line.id || Math.random()),
                lineRef: line,
                name: (typeof line.getFullProductName === "function" ? line.getFullProductName() : line.full_product_name)
                    || line.product_id?.display_name
                    || _t("Item"),
                isDiscountLine,
                isLocked: Boolean(line.is_sent_to_kitchen),
                showQtyInput: qty < 0,
                issueLabel,
                origQty: qty,
                origPrice: price,
                origDiscount: discount,
                origIncl: lineIncl,
                inclRatio,
                qty,
                qtyText: String(qty),
                price,
                priceText: String(price),
                discount,
                discountText: String(discount),
                removed: false,
            });
        }

        this.state = useState({
            items: draftItems,
        });
    }

    get currentTotal() {
        return Number(this.props.order?.priceIncl ?? 0);
    }

    get estimatedTotal() {
        let delta = 0;
        for (const item of this.state.items) {
            const newIncl = this.getItemDraftSubtotal(item);
            delta += newIncl - item.origIncl;
        }
        return Math.round((this.currentTotal + delta) * 100) / 100;
    }

    get isReadyToProceed() {
        if (this.estimatedTotal < -0.005) {
            return false;
        }
        return this.state.items.every((item) => this.isItemFixed(item));
    }

    get hasAnyFixableItem() {
        return this.state.items.some((item) => !item.isLocked && !this.isItemFixed(item));
    }

    formatCurrency(amount) {
        const utils = this.env?.utils;
        if (utils?.formatCurrency) {
            return utils.formatCurrency(amount);
        }
        return `${Number(amount || 0).toFixed(2)}`;
    }

    getItemDraftSubtotal(item) {
        if (item.removed) {
            return 0;
        }
        return item.price * item.qty * (1 - item.discount / 100) * item.inclRatio;
    }

    isItemFixed(item) {
        if (item.removed) {
            return true;
        }
        if (item.isLocked) {
            return false;
        }
        if (item.isDiscountLine) {
            return this.estimatedTotal >= -0.005;
        }
        return (
            item.qty >= 0 &&
            item.price >= 0 &&
            item.discount <= 100 &&
            this.getItemDraftSubtotal(item) >= -0.005
        );
    }

    onQtyInput(item, ev) {
        if (item.isLocked) {
            return;
        }
        item.qtyText = ev.target.value;
        const val = parseFloat(ev.target.value);
        item.qty = Number.isNaN(val) ? 0 : Math.max(0, val);
    }

    onPriceInput(item, ev) {
        if (item.isLocked) {
            return;
        }
        item.priceText = ev.target.value;
        const val = parseFloat(ev.target.value);
        if (item.isDiscountLine) {
            item.price = Number.isNaN(val) ? 0 : -Math.abs(val);
        } else {
            item.price = Number.isNaN(val) ? 0 : Math.max(0, val);
        }
    }

    onDiscountInput(item, ev) {
        if (item.isLocked) {
            return;
        }
        item.discountText = ev.target.value;
        const val = parseFloat(ev.target.value);
        item.discount = Number.isNaN(val) ? 0 : Math.min(100, val);
    }

    fixItemPositive(item) {
        if (item.isLocked) {
            return;
        }
        item.removed = false;
        if (item.isDiscountLine) {
            item.removed = true;
            return;
        }
        if (item.qty < 0) {
            item.qty = Math.abs(item.qty) || 1;
            item.qtyText = String(item.qty);
        }
        if (item.price < 0) {
            item.price = Math.abs(item.price);
            item.priceText = String(item.price);
        }
        if (item.discount > 100) {
            item.discount = 0;
            item.discountText = "0";
        }
    }

    toggleRemoveItem(item) {
        if (item.isLocked) {
            return;
        }
        item.removed = !item.removed;
    }

    fixAllAutomatically() {
        for (const item of this.state.items) {
            if (!item.isLocked && !item.isDiscountLine) {
                this.fixItemPositive(item);
            }
        }
        if (this.estimatedTotal < -0.005) {
            for (const item of this.state.items) {
                if (!item.isLocked && item.isDiscountLine) {
                    item.removed = true;
                }
            }
        }
    }

    cancel() {
        const order = this.props.order;
        const target = this.state.items[0]?.lineRef;
        if (order && target && this.props.pos?.selectOrderLine) {
            this.props.pos.selectOrderLine(order, target);
        }
        this.props.getPayload({ proceed: false });
        this.props.close();
    }

    applyAndContinue() {
        const order = this.props.order;
        for (const item of this.state.items) {
            if (item.isLocked) {
                continue;
            }
            const line = item.lineRef;
            if (!line) {
                continue;
            }
            if (item.removed || (!item.isDiscountLine && item.qty <= 0)) {
                order.removeOrderline(line);
                continue;
            }
            if (item.qty !== item.origQty && typeof line.setQuantity === "function") {
                line.setQuantity(item.qty, true);
            }
            if (item.price !== item.origPrice && typeof line.setUnitPrice === "function") {
                line.price_type = "manual";
                line.setUnitPrice(item.price);
            }
            if (item.discount !== item.origDiscount && typeof line.setDiscount === "function") {
                line.setDiscount(item.discount);
            }
        }
        this.props.getPayload({ proceed: true });
        this.props.close();
    }
}

export async function ensureOrderTotalNonNegative({ order, pos, dialog, actionLabel }) {
    if (!hasNegativeOrderIssue(order)) {
        return true;
    }
    if (!dialog) {
        return false;
    }
    const result = await makeAwaitable(dialog, NegativeOrderPopup, {
        order,
        pos,
        actionLabel: actionLabel || _t("continue"),
    });
    if (!result?.proceed || order.isEmpty()) {
        return false;
    }
    if (hasNegativeOrderIssue(order)) {
        return await ensureOrderTotalNonNegative({ order, pos, dialog, actionLabel });
    }
    return true;
}
