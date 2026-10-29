/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class KitchenRemarksPopup extends Component {
    static template = "pos_custom_kitchen.KitchenRemarksPopup";
    static components = { Dialog };
    // Use array-style props like native Odoo 19 POS popups to avoid type validation issues
    static props = ["close", "getPayload", "orderlines", "existingRounds?", "order?"];

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

        // Also populate any notes from existing rounds for past items
        for (const round of (this.props.existingRounds || [])) {
            const rlines = round.lines || [];
            for (let idx = 0; idx < rlines.length; idx++) {
                const l = rlines[idx];
                const itemKey = `past_${round.id}_${l.id || idx}`;
                if (l.note) {
                    initialNotes[itemKey] = l.note;
                }
            }
        }

        const sectionsData = this._buildSections(
            this.props.orderlines || [],
            this.props.existingRounds || []
        );

        this.state = useState({
            notes: initialNotes,
            activeTab: "all",
            sections: sectionsData.sections,
            tabs: sectionsData.tabs,
            currentRoundTitle: sectionsData.currentRoundTitle,
        });
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

    _buildSections(orderlines, existingRounds) {
        const sections = [];
        const tabs = [];

        // If no previous rounds were recorded at all, this entire batch is the initial "Order"
        if (!existingRounds || existingRounds.length === 0) {
            const initialLines = orderlines.map((line) => {
                const key = this._getKey(line);
                return {
                    key: key,
                    name: this.getLineDisplayName(line),
                    qty: this.getLineQuantity(line),
                    note: line.customer_note || line.note || "",
                    isCurrent: true,
                    isReorder: false,
                    isAdditionalQty: false,
                    lineRef: line,
                };
            });

            const orderSection = {
                id: "round_order",
                title: "Order",
                round_type: "order",
                badgeText: "Initial Order",
                badgeClass: "badge text-bg-danger",
                isCurrent: true,
                lines: initialLines,
            };
            sections.push(orderSection);

            tabs.push({
                id: "all",
                label: "All Items",
                count: initialLines.length,
                isCurrent: true,
            });
            tabs.push({
                id: "round_order",
                label: "📋 Order",
                count: initialLines.length,
                isCurrent: true,
            });

            return {
                sections,
                tabs,
                currentRoundTitle: "Order",
            };
        }

        // We have past rounds recorded!
        // Calculate total sent quantity per product in all previous rounds
        const sentQtyByProduct = {};
        for (const round of existingRounds) {
            for (const rline of (round.lines || [])) {
                const pId = rline.product_id;
                sentQtyByProduct[pId] = (sentQtyByProduct[pId] || 0) + (rline.qty || 0);
            }
        }

        // Create a section for each past round (marked isCurrent: false, uneditable)
        for (const round of existingRounds) {
            const roundLines = (round.lines || []).map((l, idx) => {
                const itemKey = `past_${round.id}_${l.id || idx}`;
                const matchingLine = orderlines.find(
                    (ol) => (ol.product_id?.id || ol.product_id) === l.product_id
                );
                return {
                    key: itemKey,
                    name: l.product_name,
                    qty: l.qty,
                    note: l.note || "",
                    isCurrent: false,
                    isReorder: round.round_type === "reorder",
                    isAdditionalQty: false,
                    lineRef: matchingLine || null,
                };
            });

            const isFirst = round.sequence === 0 || round.round_type === "order";
            sections.push({
                id: `past_round_${round.id}`,
                roundId: round.id,
                title: round.title || (isFirst ? "Order" : `Reorder ${round.sequence}`),
                round_type: round.round_type,
                badgeText: round.time ? `Sent at ${round.time}` : "Sent",
                badgeClass: "badge bg-dark text-white fw-bold",
                isCurrent: false,
                lines: roundLines,
            });
        }

        // Now calculate delta / new items in the cart that were NOT in previous rounds or have extra quantity
        const remainingSentByProduct = { ...sentQtyByProduct };
        const deltaItems = [];

        for (const line of orderlines) {
            const pId = line.product_id?.id || line.product_id;
            const currentQty = this.getLineQuantity(line);
            const sentQty = remainingSentByProduct[pId] || 0;

            if (currentQty > sentQty) {
                const extraQty = currentQty - sentQty;
                remainingSentByProduct[pId] = 0; // consumed all sent
                deltaItems.push({
                    key: this._getKey(line),
                    name: this.getLineDisplayName(line),
                    qty: extraQty,
                    totalQty: currentQty,
                    note: line.is_sent_to_kitchen ? "" : (line.customer_note || ""),
                    isCurrent: true,
                    isReorder: true,
                    isAdditionalQty: sentQty > 0,
                    lineRef: line,
                });
            } else {
                remainingSentByProduct[pId] = sentQty - currentQty;
            }
        }

        // Next reorder sequence number
        const pastReorders = existingRounds.filter(
            (r) => r.round_type === "reorder" || r.sequence > 0
        );
        const nextReorderNumber = pastReorders.length + 1;
        const currentRoundTitle = `Reorder ${nextReorderNumber}`;

        if (deltaItems.length > 0) {
            sections.push({
                id: "current_reorder",
                roundId: null,
                title: currentRoundTitle,
                round_type: "reorder",
                badgeText: "⭐ New / To Send",
                badgeClass: "badge text-bg-danger",
                isCurrent: true,
                lines: deltaItems,
            });
        }

        // Build navigation tabs
        const totalItemsCount = sections.reduce((acc, s) => acc + s.lines.length, 0);
        tabs.push({
            id: "all",
            label: "All Items",
            count: totalItemsCount,
            isCurrent: false,
        });

        for (const s of sections) {
            const icon = (s.round_type === "order" || s.title === "Order") ? "📋" : "🔁";
            tabs.push({
                id: s.id,
                label: `${icon} ${s.title}`,
                count: s.lines.length,
                isCurrent: s.isCurrent,
            });
        }

        return {
            sections,
            tabs,
            currentRoundTitle: deltaItems.length > 0 ? currentRoundTitle : null,
            hasCurrentReorder: Boolean(deltaItems.length > 0),
        };
    }

    get displayedSections() {
        if (!this.state.activeTab || this.state.activeTab === "all") {
            return this.state.sections;
        }
        return this.state.sections.filter((s) => s.id === this.state.activeTab);
    }

    selectTab(tabId) {
        this.state.activeTab = tabId;
    }

    get currentButtonInfo() {
        const activeTab = this.state.activeTab;
        const currentRoundTitle = this.state.currentRoundTitle;

        if (!activeTab || activeTab === "all") {
            if (currentRoundTitle) {
                const isInitial = currentRoundTitle === "Order" && (!this.props.existingRounds || !this.props.existingRounds.length);
                return {
                    label: isInitial ? "Confirm & Send to Kitchen" : `Confirm & Send to Kitchen (${currentRoundTitle})`,
                    isResend: false,
                    targetRoundId: null,
                };
            } else {
                return {
                    label: "Resend to Kitchen",
                    isResend: true,
                    targetRoundId: null,
                };
            }
        }

        const activeSection = this.state.sections.find((s) => s.id === activeTab);
        if (activeSection) {
            if (activeSection.isCurrent) {
                const isInitial = activeSection.title === "Order" && (!this.props.existingRounds || !this.props.existingRounds.length);
                return {
                    label: isInitial ? "Confirm & Send to Kitchen" : `Confirm & Send to Kitchen (${activeSection.title})`,
                    isResend: false,
                    targetRoundId: null,
                };
            } else {
                return {
                    label: `Resend to Kitchen (${activeSection.title})`,
                    isResend: true,
                    targetRoundId: activeSection.roundId || null,
                };
            }
        }

        if (currentRoundTitle) {
            return {
                label: `Confirm & Send to Kitchen (${currentRoundTitle})`,
                isResend: false,
                targetRoundId: null,
            };
        }
        return {
            label: "Resend to Kitchen",
            isResend: true,
            targetRoundId: null,
        };
    }

    onNoteInput(key, item, ev) {
        // Uneditable protection: Never allow changes to past sent items
        if (!item || !item.isCurrent) {
            return;
        }
        this.state.notes[key] = ev.target.value;
    }

    confirm() {
        const btnInfo = this.currentButtonInfo;
        const currentNotes = {};
        for (const section of this.state.sections) {
            if (section.isCurrent) {
                for (const item of section.lines) {
                    if (item.isCurrent && this.state.notes[item.key] !== undefined) {
                        currentNotes[item.key] = this.state.notes[item.key];
                    }
                }
            }
        }
        this.props.getPayload({
            notes: currentNotes,
            isResend: btnInfo.isResend,
            targetRoundId: btnInfo.targetRoundId,
            targetTitle: btnInfo.label,
        });
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}

