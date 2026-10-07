# pyrefly: ignore [missing-import]
from odoo import models, fields, api

class PosKitchenRoundLine(models.Model):
    _inherit = 'pos.kitchen.round.line'

    pos_category_id = fields.Many2one('pos.category', string='POS Category')
    category_name = fields.Char(string='Category Name')


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.depends(
        'lines', 'lines.qty', 'lines.full_product_name', 'lines.product_id',
        'lines.customer_note', 'lines.is_reorder', 'lines.reorder_qty', 'lines.reorder_note',
        'kitchen_round_ids', 'kitchen_round_ids.sequence', 'kitchen_round_ids.round_type',
        'kitchen_round_ids.is_ready',
        'kitchen_round_ids.line_ids', 'kitchen_round_ids.line_ids.qty',
        'kitchen_round_ids.line_ids.product_name', 'kitchen_round_ids.line_ids.note',
        'kitchen_round_ids.line_ids.category_name'
    )
    def _compute_kitchen_order_lines_summary(self):
        for order in self:
            rounds = order.kitchen_round_ids.sorted(key=lambda r: (r.sequence, r.id))
            if not rounds:
                super(PosOrder, order)._compute_kitchen_order_lines_summary()
                continue

            first_round_id = rounds[0].id if rounds else None
            reorder_counter = 0
            rounds_html = []

            for round_rec in rounds:
                if not round_rec.line_ids:
                    continue

                is_first = (round_rec.id == first_round_id) or (round_rec.sequence == 0 and round_rec.round_type == 'order')
                if is_first:
                    header_title = "--------- ORDER ---------"
                    header_color = "#495057"
                    bg_color = "transparent"
                else:
                    reorder_counter += 1
                    header_title = f"-------- REORDER {reorder_counter} --------"
                    header_color = "#dc3545"
                    bg_color = "rgba(220, 53, 69, 0.04)"

                is_ready = bool(round_rec.is_ready)
                btn_class = "btn-success" if is_ready else "btn-danger"
                btn_label = "✅ Ready" if is_ready else "🔴 Pending"

                # Group lines by category
                lines_by_cat = {}
                for line in round_rec.line_ids:
                    cat = line.category_name or "General"
                    if cat not in lines_by_cat:
                        lines_by_cat[cat] = []
                    lines_by_cat[cat].append(line)

                category_blocks = []
                for cat_name, cat_lines in lines_by_cat.items():
                    cat_items_html = []
                    for line in cat_lines:
                        name = line.product_name or (line.product_id and line.product_id.display_name) or ''
                        qty = int(line.qty) if line.qty.is_integer() else line.qty

                        if qty < 0:
                            item_display = f"""
                                <span style="font-size: 14px; font-weight: 600; color: #dc3545; text-decoration: line-through;">
                                    {abs(qty)}x {name} (Cancelled)
                                </span>
                            """
                        else:
                            item_display = f"""
                                <span style="font-size: 15px; font-weight: 600; color: #111;">
                                    {qty}x {name}
                                </span>
                            """

                        note_html = ""
                        if line.note:
                            note_html = f"""<div style="color: #dc3545; font-size: 13px; font-weight: 600; margin-left: 16px; font-style: italic;">
                                ↳ Remark: {line.note}
                            </div>"""

                        cat_items_html.append(f"""
                            <div style="margin-bottom: 6px;">
                                {item_display}
                                {note_html}
                            </div>
                        """)

                    category_blocks.append(f"""
                        <div class="mb-2">
                            <div class="badge text-bg-secondary mb-1" style="font-size: 11px; padding: 3px 8px; text-transform: uppercase;">
                                📂 {cat_name}
                            </div>
                            <div class="ps-2">
                                {''.join(cat_items_html)}
                            </div>
                        </div>
                    """)

                rounds_html.append(f"""
                    <div class="mb-3 p-2 rounded" style="background-color: {bg_color}; border: 1px solid rgba(0,0,0,0.06);">
                        <div class="d-flex align-items-center justify-content-between mb-2 pb-1 border-bottom">
                            <span class="fw-bold" style="color: {header_color}; font-size: 13px; letter-spacing: 0.5px;">
                                {header_title}
                            </span>
                            <button type="button" 
                                    class="btn btn-sm round-status-btn {btn_class}" 
                                    data-round-id="{round_rec.id}"
                                    style="font-size: 11px; font-weight: 700; padding: 2px 10px; border-radius: 12px; cursor: pointer; box-shadow: 0 1px 2px rgba(0,0,0,0.15);">
                                {btn_label}
                            </button>
                        </div>
                        <div class="ps-1">
                            {''.join(category_blocks)}
                        </div>
                    </div>
                """)

            order.kitchen_order_lines_summary = "".join(rounds_html)

    def _get_product_category_name(self, product):
        if product and product.pos_categ_ids:
            return product.pos_categ_ids[0].name
        return "General"

    @api.model
    def _send_escpos_kot_to_printer(self, ip, port, category_name, printer_name, items, round_title, table_name, order_name, time_str):
        """
        Sends raw ESC/POS commands directly to TVS RP 3200 LITE / Network thermal printer via TCP socket.
        """
        import socket
        import time
        import logging
        _log = logging.getLogger(__name__)

        ESC_INIT = b'\x1b\x40'              # Initialize printer
        ESC_ALIGN_CENTER = b'\x1b\x61\x01'  # Center align
        ESC_ALIGN_LEFT = b'\x1b\x61\x00'    # Left align
        TXT_BOLD_ON = b'\x1b\x45\x01'       # Bold on
        TXT_BOLD_OFF = b'\x1b\x45\x00'      # Bold off
        TXT_DOUBLE_SIZE = b'\x1b\x21\x30'   # Double width and height
        TXT_NORMAL = b'\x1b\x21\x00'        # Normal
        FEED_AND_CUT = b'\r\n\r\n\r\n\r\n\x1d\x56\x00' # Feed lines & Full paper cut

        lines = [
            "================================\r\n",
            "      KITCHEN ORDER TICKET      \r\n",
        ]
        if printer_name and printer_name != category_name:
            lines.append(f"       [{printer_name}]       \r\n")
        lines.extend([
            f"     *** [ {round_title} ] ***    \r\n",
            "================================\r\n",
            f"Table: {table_name}\r\n",
            f"Order: {order_name}\r\n",
            f"Time:  {time_str}\r\n",
            "--------------------------------\r\n",
            f"STATION: {category_name.upper()}\r\n",
            "--------------------------------\r\n",
        ])

        for itm in items:
            qty = itm.get('qty', 1)
            name = itm.get('name', '')
            note = itm.get('note', '')
            lines.append(f"{qty}x {name}\r\n")
            if note:
                lines.append(f"   -> Note: {note}\r\n")

        lines.extend([
            "--------------------------------\r\n",
            f"--- STATION: {category_name.upper()} ---\r\n",
            "================================\r\n",
        ])

        raw_text = "".join(lines)
        safe_text = raw_text.replace('↳', '->').replace('–', '-').replace('—', '-')
        payload = ESC_INIT + ESC_ALIGN_LEFT + safe_text.encode('ascii', errors='replace') + FEED_AND_CUT

        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((ip, int(port or 9100)))
            sock.sendall(payload)
            time.sleep(0.2)
            try:
                sock.shutdown(socket.SHUT_WR)
            except Exception:
                pass
            sock.close()
            _log.info("Direct ESC/POS ticket printed successfully to %s:%s for %s", ip, port, category_name)
            return True, None
        except Exception as e:
            _log.warning("Direct ESC/POS socket print failed for %s:%s - %s", ip, port, e)
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
            return False, str(e)

    @api.model
    def get_latest_kitchen_round_for_print(self, order_identifier):
        """
        Fetch the newest kitchen round for printing station KOT tickets.
        Directly dispatches ESC/POS tickets to configured printer IPs.
        """
        if not order_identifier:
            return None

        domain = ['|', '|',
            ('uuid', '=', str(order_identifier)),
            ('pos_reference', '=', str(order_identifier)),
            ('name', '=', str(order_identifier))
        ]
        if str(order_identifier).isdigit():
            domain = ['|'] + domain + [('id', '=', int(order_identifier))]

        order = self.search(domain, limit=1)
        if not order or not order.kitchen_round_ids:
            return None

        rounds = order.kitchen_round_ids.sorted(key=lambda r: (r.sequence, r.id))
        if not rounds:
            return None

        latest_round = rounds[-1]
        first_round_id = rounds[0].id

        is_first = (latest_round.id == first_round_id) or (latest_round.sequence == 0 and latest_round.round_type == 'order')
        if is_first:
            round_title = "ORDER"
        else:
            reorders = [r for r in rounds if not ((r.id == first_round_id) or (r.sequence == 0 and r.round_type == 'order'))]
            reorder_index = reorders.index(latest_round) + 1 if latest_round in reorders else len(reorders)
            round_title = f"REORDER {reorder_index}"

        table_name = (order.table_id and (order.table_id.table_number or order.table_id.name)) or "Takeaway"
        order_name = order.pos_reference or order.name or "Order"
        time_str = fields.Datetime.context_timestamp(self, fields.Datetime.now()).strftime('%I:%M %p')

        category_map = {}
        for line in latest_round.line_ids:
            if line.qty <= 0:
                continue

            pos_cat = line.pos_category_id
            if not pos_cat and line.product_id and line.product_id.pos_categ_ids:
                pos_cat = line.product_id.pos_categ_ids[0]

            cat_name = line.category_name or (pos_cat and pos_cat.name) or "General"
            printer_url = pos_cat.printer_url.strip() if pos_cat and pos_cat.printer_url else ""
            printer_name = pos_cat.printer_name.strip() if pos_cat and pos_cat.printer_name else ""

            if cat_name not in category_map:
                category_map[cat_name] = {
                    'category_name': cat_name,
                    'printer_url': printer_url,
                    'printer_name': printer_name,
                    'pos_category_id': pos_cat.id if pos_cat else False,
                    'items': [],
                    'direct_printed': False,
                }
            category_map[cat_name]['items'].append({
                'name': line.product_name or (line.product_id and line.product_id.display_name) or "Item",
                'qty': int(line.qty) if line.qty.is_integer() else line.qty,
                'note': line.note or '',
            })

        # Attempt direct ESC/POS socket printing to printer IPs
        default_ip, default_port = None, None
        configured_cat = self.env['pos.category'].search([('printer_url', '!=', False), ('printer_url', '!=', '')], limit=1)
        if configured_cat:
            default_ip, default_port = configured_cat.parse_printer_ip_port()

        for cat_name, cat_data in category_map.items():
            pos_cat_id = cat_data.get('pos_category_id')
            pos_cat = self.env['pos.category'].browse(pos_cat_id) if pos_cat_id else None
            ip, port = (pos_cat.parse_printer_ip_port() if pos_cat else (None, None))
            if not ip and cat_data.get('printer_url'):
                import re
                cleaned = re.sub(r'^https?:\/\/', '', cat_data['printer_url']).split('/')[0].strip()
                m = re.search(r'^([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})(?::([0-9]+))?', cleaned)
                if m:
                    ip = m.group(1)
                    port = int(m.group(2)) if m.group(2) else 9100

            # Fallback to default kitchen printer IP if this category doesn't have its own IP
            if not ip and default_ip:
                ip = default_ip
                port = default_port

            if ip:
                cat_data['printer_ip'] = ip
                cat_data['printer_port'] = port
                ok, err = self._send_escpos_kot_to_printer(
                    ip, port, cat_name, cat_data['printer_name'],
                    cat_data['items'], round_title, str(table_name), str(order_name), time_str
                )
                if ok:
                    cat_data['direct_printed'] = True
                else:
                    cat_data['direct_error'] = err

        return {
            'round_id': latest_round.id,
            'round_title': round_title,
            'table_name': str(table_name),
            'order_name': str(order_name),
            'category_map': category_map,
        }

