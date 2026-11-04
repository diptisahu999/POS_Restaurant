/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export const SUGGESTED_CANCEL_REASONS = [
    { id: "mind", label: "Customer changed mind", icon: "fa-undo" },
    // { id: "delay", label: "Order delayed / Taking too long", icon: "fa-clock-o" },
    { id: "wrong", label: "Wrong item ordered", icon: "fa-times-circle" },
    // { id: "stock", label: "Kitchen out of stock", icon: "fa-cutlery" },
    { id: "left", label: "Customer left / Table cancelled", icon: "fa-sign-out" },
    { id: "duplicate", label: "Duplicate reorder / Entry error", icon: "fa-files-o" },
    // { id: "quality", label: "Food quality / Special request", icon: "fa-heartbeat" },
    // { id: "guest_request", label: "Customer request to cancel", icon: "fa-user-times" },
];

/**
 * CancelItemPopup – lets the cashier select which sent-to-kitchen items,
 * reorders, or entire orders to cancel with suggested quick reasons
 * and ESC/POS kitchen printer slip generation.
 */
export class CancelItemPopup extends Component {
    static template = "pos_custom_kitchen.CancelItemPopup";
    static components = { Dialog };
    static props = ["close", "getPayload", "orderlines", "existingRounds?", "order?", "targetLine?"];

    setup() {
        super.setup();

        const targetLine = this.props.targetLine;

        // Build items from sent orderlines
        const items = (this.props.orderlines || []).map((line) => {
            const qty = this._getLineQty(line);
            const roundSeq = line.kitchen_round_seq !== undefined
                ? line.kitchen_round_seq
                : (line.is_reorder ? 1 : 0);
            const roundTitle = line.kitchen_round_title
                || (roundSeq === 0 ? "Order" : `Reorder ${roundSeq}`);
            const category = line.product_id?.pos_categ_ids?.[0]?.name || "";

            const isPreselected = Boolean(targetLine && (
                line === targetLine ||
                (targetLine.uuid && line.uuid === targetLine.uuid) ||
                (targetLine.id && line.id === targetLine.id)
            ));

            return {
                key: String(line.uuid || line.id || line.cid || "item_" + Math.random()),
                lineRef: line,
                name: this._getLineName(line),
                qty: qty,
                roundSeq: roundSeq,
                roundTitle: roundTitle,
                category: category,
                selected: isPreselected,
                cancelQty: qty,
                reason: "",
            };
        });

        // Build navigation tabs based on items and existing rounds
        const tabs = this._buildTabs(items, this.props.existingRounds || []);

        // Initial active tab
        let initialTab = "all";
        if (targetLine) {
            const preselectedItem = items.find((i) => i.selected);
            if (preselectedItem) {
                initialTab = `round_${preselectedItem.roundSeq}`;
            }
        }

        this.suggestedReasons = SUGGESTED_CANCEL_REASONS;

        this.state = useState({
            items,
            tabs,
            activeTab: initialTab,
            printCancelKot: true,
            globalReason: "",
        });
    }

    _buildTabs(items, existingRounds) {
        const tabs = [];
        tabs.push({
            id: "all",
            label: "All Items",
            count: items.length,
            roundSeq: null,
            roundTitle: "All Items",
        });

        // Collect unique round sequences from items
        const roundMap = new Map();
        for (const item of items) {
            if (!roundMap.has(item.roundSeq)) {
                roundMap.set(item.roundSeq, {
                    roundSeq: item.roundSeq,
                    roundTitle: item.roundTitle,
                    count: 0,
                });
            }
            roundMap.get(item.roundSeq).count += 1;
        }

        // Sort by round sequence (0 = Order, 1 = Reorder 1, etc.)
        const sortedRounds = Array.from(roundMap.values()).sort((a, b) => a.roundSeq - b.roundSeq);

        for (const r of sortedRounds) {
            const isFirst = r.roundSeq === 0 || r.roundTitle.toLowerCase() === "order";
            const icon = isFirst ? "📋" : "🔁";
            tabs.push({
                id: `round_${r.roundSeq}`,
                label: `${icon} ${r.roundTitle}`,
                count: r.count,
                roundSeq: r.roundSeq,
                roundTitle: r.roundTitle,
                isReorder: !isFirst,
            });
        }

        return tabs;
    }

    _getLineName(line) {
        try {
            if (typeof line.get_full_product_name === "function") return line.get_full_product_name();
            return line.product_id?.display_name || line.product_id?.name || "Item";
        } catch (_) {
            return "Item";
        }
    }

    _getLineQty(line) {
        try {
            if (typeof line.get_quantity === "function") return line.get_quantity();
            return line.qty || 1;
        } catch (_) {
            return 1;
        }
    }

    // ─── computed getters ───────────────────────────────────────────────────

    get displayedItems() {
        if (!this.state.activeTab || this.state.activeTab === "all") {
            return this.state.items;
        }
        const activeTabObj = this.state.tabs.find((t) => t.id === this.state.activeTab);
        if (!activeTabObj || activeTabObj.roundSeq === null) {
            return this.state.items;
        }
        return this.state.items.filter((i) => i.roundSeq === activeTabObj.roundSeq);
    }

    get selectedItems() {
        return this.state.items.filter((i) => i.selected);
    }

    get hasSelection() {
        return this.selectedItems.length > 0;
    }

    get totalCancelQty() {
        return this.selectedItems.reduce((acc, i) => acc + (parseFloat(i.cancelQty) || 0), 0);
    }

    get activeRoundTab() {
        return this.state.tabs.find((t) => t.id === this.state.activeTab) || this.state.tabs[0];
    }

    get orderTableDisplay() {
        const order = this.props.order;
        if (!order) return "";
        let info = "";
        if (order.table_id) {
            info = `Table ${order.table_id.table_number || order.table_id.display_name || ""}`;
        } else if (order.table_stand_number) {
            info = `Table ${order.table_stand_number}`;
        }
        const ref = order.pos_reference || order.name || "";
        return info ? `${info} (${ref})` : ref;
    }

    // ─── tab & selection handlers ───────────────────────────────────────────

    selectTab(tabId) {
        this.state.activeTab = tabId;
    }

    toggleItem(item) {
        item.selected = !item.selected;
        if (item.selected && (!item.cancelQty || item.cancelQty <= 0)) {
            item.cancelQty = item.qty;
        }
    }

    selectAllInCurrentTab() {
        const currentItems = this.displayedItems;
        for (const item of currentItems) {
            item.selected = true;
            if (!item.cancelQty || item.cancelQty <= 0) {
                item.cancelQty = item.qty;
            }
        }
    }

    clearAllInCurrentTab() {
        const currentItems = this.displayedItems;
        for (const item of currentItems) {
            item.selected = false;
        }
    }

    cancelEntireCurrentRound() {
        const currentItems = this.displayedItems;
        for (const item of currentItems) {
            item.selected = true;
            item.cancelQty = item.qty; // full cancel
        }
        const tab = this.activeRoundTab;
        if (!this.state.globalReason) {
            if (tab.id === "all") {
                this.state.globalReason = "Order cancelled";
            } else {
                this.state.globalReason = `${tab.roundTitle} cancelled`;
            }
        }
    }

    cancelEntireOrder() {
        for (const item of this.state.items) {
            item.selected = true;
            item.cancelQty = item.qty;
        }
        if (!this.state.globalReason) {
            this.state.globalReason = "Customer left / Table cancelled";
        }
    }

    // ─── quantity controls ──────────────────────────────────────────────────

    incQty(item, ev) {
        if (ev) ev.stopPropagation();
        if (item.cancelQty < item.qty) {
            item.cancelQty = Math.min(item.qty, item.cancelQty + 1);
        }
    }

    decQty(item, ev) {
        if (ev) ev.stopPropagation();
        if (item.cancelQty > 1) {
            item.cancelQty = Math.max(1, item.cancelQty - 1);
        }
    }

    setMaxQty(item, ev) {
        if (ev) ev.stopPropagation();
        item.cancelQty = item.qty;
    }

    onCancelQtyChange(item, ev) {
        const parsed = parseFloat(ev.target.value);
        if (!isNaN(parsed) && parsed > 0 && parsed <= item.qty) {
            item.cancelQty = parsed;
        } else {
            ev.target.value = item.cancelQty;
        }
    }

    // ─── reason controls ────────────────────────────────────────────────────

    selectSuggestedReason(text) {
        if (this.state.globalReason === text) {
            this.state.globalReason = ""; // toggle off
        } else {
            this.state.globalReason = text;
        }
    }

    onReasonChange(item, ev) {
        item.reason = ev.target.value;
    }

    onGlobalReasonChange(ev) {
        this.state.globalReason = ev.target.value;
    }

    clearGlobalReason() {
        this.state.globalReason = "";
    }

    togglePrintKot() {
        this.state.printCancelKot = !this.state.printCancelKot;
    }

    // ─── confirm / cancel ───────────────────────────────────────────────────

    confirm() {
        if (!this.hasSelection) return;

        const isFullOrderCancel =
            this.selectedItems.length === this.state.items.length &&
            this.selectedItems.every((i) => i.cancelQty >= i.qty);

        const payload = {
            cancelledItems: this.selectedItems.map((i) => ({
                key: i.key,
                lineRef: i.lineRef,
                name: i.name,
                cancelQty: i.cancelQty,
                reason: i.reason || this.state.globalReason || "Cancelled by cashier",
                roundTitle: i.roundTitle,
                roundSeq: i.roundSeq,
            })),
            printCancelKot: this.state.printCancelKot,
            globalReason: this.state.globalReason,
            isFullOrderCancel: isFullOrderCancel,
        };

        this.props.getPayload(payload);
        this.props.close();
    }

    cancelDialog() {
        this.props.close();
    }
}
