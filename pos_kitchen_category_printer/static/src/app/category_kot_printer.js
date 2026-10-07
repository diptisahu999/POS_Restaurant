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

        // 3. Process category print jobs
        for (const [categoryName, catData] of Object.entries(printData.category_map)) {
            const items = catData.items || [];
            if (items.length === 0) {
                continue;
            }

            if (catData.direct_printed) {
                console.log(`[KOT Print] Successfully printed via socket to ${categoryName} station (${catData.printer_ip}:${catData.printer_port || 9100})`);
                continue;
            }

            const printerUrl = (catData.printer_url || "").trim();
            const printerName = catData.printer_name || categoryName;

            // Route to Dynamic HTTP Printer / Proxy if configured
            if (printerUrl && (printerUrl.startsWith("http://") || printerUrl.startsWith("https://"))) {
                this._sendToDynamicPrinterUrl(printerUrl, categoryName, printerName, items, roundTitle, tableName, orderName, now);
            } else {
                // Default / Blank / Browser print: Print directly using browser to Windows Default Printer (Brother DCP-L2540DW)
                this._printViaBrowser(categoryName, printerName, items, roundTitle, tableName, orderName, now);
            }
        }
    },

    _printViaBrowser(categoryName, printerName, items, roundTitle, tableName, orderName, timeStr) {
        const iframe = document.createElement("iframe");
        iframe.style.position = "fixed";
        iframe.style.right = "0";
        iframe.style.bottom = "0";
        iframe.style.width = "0";
        iframe.style.height = "0";
        iframe.style.border = "none";
        document.body.appendChild(iframe);

        const itemsHtml = items.map(it => `
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 15px; font-weight: bold;">
                <span>${it.qty}x ${it.name}</span>
            </div>
            ${it.note ? `<div style="font-size: 13px; color: #d9534f; margin-left: 12px; margin-bottom: 6px; font-style: italic; font-weight: bold;">↳ Note: ${it.note}</div>` : ''}
        `).join("");

        const content = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>KOT - ${categoryName}</title>
                <style>
                    @page { margin: 4mm; size: auto; }
                    body {
                        font-family: 'Courier New', monospace, sans-serif;
                        font-size: 13px;
                        color: #000;
                        margin: 0;
                        padding: 8px;
                        max-width: 320px;
                    }
                    .center { text-align: center; }
                    .bold { font-weight: bold; }
                    .divider { border-top: 1px dashed #000; margin: 8px 0; }
                    .double-divider { border-top: 2px solid #000; margin: 8px 0; }
                    .header-title { font-size: 17px; font-weight: bold; letter-spacing: 1px; }
                    .round-badge { font-size: 14px; font-weight: bold; margin: 4px 0; }
                </style>
            </head>
            <body>
                <div class="center header-title">KITCHEN ORDER TICKET</div>
                ${printerName && printerName !== categoryName ? `<div class="center bold">[${printerName}]</div>` : ''}
                <div class="center round-badge">*** ${roundTitle} ***</div>
                <div class="double-divider"></div>
                <div><span class="bold">Table:</span> ${tableName}</div>
                <div><span class="bold">Order:</span> ${orderName}</div>
                <div><span class="bold">Time:</span> ${timeStr}</div>
                <div class="divider"></div>
                <div class="bold" style="font-size: 14px; text-transform: uppercase;">STATION: ${categoryName}</div>
                <div class="divider"></div>
                <div style="margin: 8px 0;">
                    ${itemsHtml}
                </div>
                <div class="double-divider"></div>
                <div class="center bold" style="font-size: 11px;">--- END OF TICKET ---</div>
            </body>
            </html>
        `;

        iframe.contentWindow.document.open();
        iframe.contentWindow.document.write(content);
        iframe.contentWindow.document.close();

        iframe.contentWindow.focus();
        setTimeout(() => {
            iframe.contentWindow.print();
            setTimeout(() => {
                if (iframe.parentNode) {
                    iframe.parentNode.removeChild(iframe);
                }
            }, 3000);
        }, 300);
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
        };

        try {
            await fetch(printerUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
                mode: "cors",
            });
            console.log(`[KOT Print] Successfully sent print job to ${categoryName} printer at ${printerUrl}`);
        } catch (err) {
            console.warn(`[KOT Print] Network request to ${printerUrl} failed:`, err);
        }
    },
});
