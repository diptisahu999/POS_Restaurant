/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    async customSendToKitchen() {
        const order = this.currentOrder;
        if (!order || order.isEmpty()) {
            return;
        }

        // 1. Call parent customSendToKitchen to handle remarks popup and server sync
        await super.customSendToKitchen(...arguments);

        // 2. Fetch the latest kitchen round (delta items + category printer URLs) from backend
        const identifier = order.uuid || order.server_id || order.id || order.name || order.pos_reference;
        let printData = null;
        try {
            const orm = this.env?.services?.orm || this.pos?.orm;
            if (orm && identifier) {
                printData = await orm.call(
                    "pos.order",
                    "get_latest_kitchen_round_for_print",
                    [identifier]
                );
            }
        } catch (e) {
            console.warn("Could not fetch latest kitchen round via RPC for KOT print:", e);
        }

        if (!printData || !printData.category_map || Object.keys(printData.category_map).length === 0) {
            return;
        }

        // Avoid printing the exact same round multiple times
        if (printData.round_id) {
            if (!order._printed_round_ids) {
                order._printed_round_ids = new Set();
            }
            if (order._printed_round_ids.has(printData.round_id)) {
                return;
            }
            order._printed_round_ids.add(printData.round_id);
        }

        const tableName = printData.table_name || ((order.table_id && (order.table_id.table_number || order.table_id.name)) || (order.table && (order.table.table_number || order.table.name)) || "Takeaway");
        const orderName = printData.order_name || order.name || order.pos_reference || "Order";
        const roundTitle = printData.round_title || "ORDER";
        const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // 3. Print separate KOT tickets for each category to its configured dynamic Printer URL / Station
        for (const [categoryName, catData] of Object.entries(printData.category_map)) {
            const items = catData.items || [];
            if (items.length === 0) {
                continue;
            }

            const printerUrl = (catData.printer_url || "").trim();
            const printerName = catData.printer_name || categoryName;

            // Route to Dynamic Printer URL if configured
            if (printerUrl) {
                this._sendToDynamicPrinterUrl(printerUrl, categoryName, printerName, items, roundTitle, tableName, orderName, now);
            } else {
                // Fallback to browser slip print
                this._printCategoryKOT(categoryName, printerName, items, roundTitle, tableName, orderName, now);
            }
        }
    },

    async _sendToDynamicPrinterUrl(printerUrl, categoryName, printerName, items, roundTitle, tableName, orderName, timeStr) {
        const payload = {
            station: printerName || categoryName,
            category: categoryName,
            round: roundTitle,
            table: tableName,
            order: orderName,
            time: timeStr,
            items: items.map(it => ({
                name: it.name,
                qty: it.qty,
                note: it.note || '',
            })),
            html: this._getKOTReceiptHtml(categoryName, printerName, items, roundTitle, tableName, orderName, timeStr),
        };

        try {
            // Direct POST call to dynamic category printer URL / proxy
            await fetch(printerUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
                mode: "cors",
            });
            console.log(`[KOT Print] Successfully sent print job to ${categoryName} printer at ${printerUrl}`);
        } catch (err) {
            console.warn(`[KOT Print] Failed to send direct network request to ${printerUrl}. Falling back to browser slip:`, err);
            // Fallback to browser slip print if network request is blocked/unreachable
            this._printCategoryKOT(categoryName, printerName, items, roundTitle, tableName, orderName, timeStr);
        }
    },

    _getKOTReceiptHtml(categoryName, printerName, items, roundTitle, tableName, orderName, timeStr) {
        let itemsHtml = "";
        for (const item of items) {
            let noteHtml = "";
            if (item.note) {
                noteHtml = `<div style="font-size: 13px; font-weight: bold; font-style: italic; margin-left: 15px; color: #333;">↳ Note: ${item.note}</div>`;
            }

            itemsHtml += `
                <div style="display: flex; justify-content: space-between; font-size: 16px; font-weight: bold; margin-bottom: 6px; border-bottom: 1px dashed #ddd; padding-bottom: 4px;">
                    <span>${item.qty}x ${item.name}</span>
                </div>
                ${noteHtml}
            `;
        }

        return `
            <!DOCTYPE html>
            <html>
            <head>
                <title>KOT - ${categoryName}</title>
                <style>
                    body { font-family: monospace, sans-serif; width: 280px; margin: 0 auto; padding: 10px; color: #000; }
                    .header { text-align: center; border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 8px; }
                    .round-badge { background: #000; color: #fff; text-align: center; font-size: 16px; font-weight: 900; padding: 4px; margin: 6px 0; letter-spacing: 1px; }
                    .cat-title { background: #eee; border: 2px solid #000; color: #000; text-align: center; font-size: 17px; font-weight: 900; padding: 6px; margin: 6px 0; }
                    .meta { font-size: 14px; font-weight: bold; margin-bottom: 8px; }
                    .footer { text-align: center; border-top: 2px solid #000; margin-top: 12px; padding-top: 6px; font-size: 12px; font-weight: bold; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h2 style="margin: 0; font-size: 20px;">KITCHEN ORDER TICKET</h2>
                    ${printerName && printerName !== categoryName ? `<div style="font-size: 13px; font-weight: bold;">[ ${printerName} ]</div>` : ''}
                </div>
                <div class="round-badge">
                    *** [ ${roundTitle} ] ***
                </div>
                <div class="meta">
                    <div><strong>Table:</strong> ${tableName}</div>
                    <div><strong>Order:</strong> ${orderName}</div>
                    <div><strong>Time:</strong> ${timeStr}</div>
                </div>
                <div class="cat-title">
                    STATION: ${categoryName.toUpperCase()}
                </div>
                <div style="margin-top: 10px;">
                    ${itemsHtml}
                </div>
                <div class="footer">
                    --- STATION PRINT: ${categoryName.toUpperCase()} ---
                </div>
            </body>
            </html>
        `;
    },

    _printCategoryKOT(categoryName, printerName, items, roundTitle, tableName, orderName, timeStr) {
        const receiptHtml = this._getKOTReceiptHtml(categoryName, printerName, items, roundTitle, tableName, orderName, timeStr);

        // Create invisible iframe to trigger print for this category printer
        const iframe = document.createElement("iframe");
        iframe.style.position = "absolute";
        iframe.style.width = "0px";
        iframe.style.height = "0px";
        iframe.style.border = "none";
        document.body.appendChild(iframe);

        const doc = iframe.contentWindow.document;
        doc.open();
        doc.write(receiptHtml);
        doc.close();

        iframe.contentWindow.focus();
        setTimeout(() => {
            iframe.contentWindow.print();
            setTimeout(() => {
                document.body.removeChild(iframe);
            }, 1000);
        }, 500);
    },
});
