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
    def get_latest_kitchen_round_for_print(self, order_identifier):
        """
        Fetch the newest kitchen round for printing station KOT tickets.
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
                    'items': [],
                }
            category_map[cat_name]['items'].append({
                'name': line.product_name or (line.product_id and line.product_id.display_name) or "Item",
                'qty': int(line.qty) if line.qty.is_integer() else line.qty,
                'note': line.note or '',
            })

        table_name = (order.table_id and (order.table_id.table_number or order.table_id.name)) or "Takeaway"
        order_name = order.pos_reference or order.name or "Order"

        return {
            'round_id': latest_round.id,
            'round_title': round_title,
            'table_name': str(table_name),
            'order_name': str(order_name),
            'category_map': category_map,
        }

