# pyrefly: ignore [missing-import]
from odoo import models, fields, api

class PosKitchenRound(models.Model):
    _name = 'pos.kitchen.round'
    _description = 'POS Kitchen Order Round'
    _order = 'sequence asc, id asc'

    order_id = fields.Many2one('pos.order', string='POS Order', ondelete='cascade', required=True, index=True)
    sequence = fields.Integer(string='Round Number', default=0)
    round_type = fields.Selection([
        ('order', 'Order'),
        ('reorder', 'Reorder')
    ], string='Round Type', default='order')
    is_ready = fields.Boolean(string='Is Ready', default=False)
    line_ids = fields.One2many('pos.kitchen.round.line', 'round_id', string='Lines')

    def action_toggle_ready(self):
        for rec in self:
            rec.is_ready = not rec.is_ready
            rec.order_id._compute_kitchen_order_lines_summary()
        return True


class PosKitchenRoundLine(models.Model):
    _name = 'pos.kitchen.round.line'
    _description = 'POS Kitchen Order Round Line'

    round_id = fields.Many2one('pos.kitchen.round', string='Kitchen Round', ondelete='cascade', required=True, index=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_name = fields.Char(string='Product Name')
    pos_category_id = fields.Many2one('pos.category', string='POS Category')
    category_name = fields.Char(string='Category Name')
    qty = fields.Float(string='Quantity', default=1.0)
    note = fields.Char(string='Customer Note')


class PosOrder(models.Model):
    _inherit = 'pos.order'

    kitchen_state = fields.Selection([
        ('pending', 'Waiting'),
        ('preparing', 'Preparing'),
        ('ready_to_serve', 'Ready to Serve'),
        ('done', 'Served')
    ], string='Kitchen Status', default='pending', tracking=True)

    reorder_count = fields.Integer(
        string='Reorder Count',
        compute='_compute_reorder_count',
        store=True,
        help='How many times the order was modified after being sent to kitchen',
    )

    kitchen_round_ids = fields.One2many(
        'pos.kitchen.round',
        'order_id',
        string='Kitchen Rounds'
    )

    kitchen_order_lines_summary = fields.Html(
        string='Order Summary',
        compute='_compute_kitchen_order_lines_summary',
        sanitize=False
    )

    @api.depends('kitchen_round_ids', 'kitchen_round_ids.sequence', 'kitchen_round_ids.round_type')
    def _compute_reorder_count(self):
        for order in self:
            rounds = order.kitchen_round_ids
            if not rounds or len(rounds) <= 1:
                order.reorder_count = 0
            else:
                # Number of reorders is the number of rounds beyond the initial order round
                reorders = rounds.filtered(lambda r: r.sequence > 0 or r.round_type == 'reorder')
                if len(reorders) == len(rounds) and len(rounds) > 1:
                    # In legacy test orders where all rounds were recorded as reorder, first is order
                    order.reorder_count = len(rounds) - 1
                else:
                    order.reorder_count = len(reorders)

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

            # Fallback for orders that don't have rounds recorded yet
            if not rounds:
                round_html = []
                order_items_html = []
                for line in order.lines:
                    if line.product_id and order.config_id.module_pos_discount and line.product_id == order.config_id.discount_product_id:
                        continue
                    name = line.full_product_name or (line.product_id and line.product_id.display_name) or ''
                    qty = int(line.qty) if line.qty.is_integer() else line.qty
                    note_html = f"""<div style="color: #dc3545; font-size: 13px; font-weight: 600; margin-left: 16px; font-style: italic;">
                        ↳ Remark: {line.customer_note}
                    </div>""" if line.customer_note else ""
                    order_items_html.append(f"""
                        <div style="margin-bottom: 6px;">
                            <span style="font-size: 15px; font-weight: 600; color: #111;">
                                {qty}x {name}
                            </span>
                            {note_html}
                        </div>
                    """)

                if order_items_html:
                    round_html.append(f"""
                        <div class="mb-2">
                            <div class="d-flex align-items-center justify-content-between mb-2 pb-1 border-bottom">
                                <span class="fw-bold text-muted" style="font-size: 13px; letter-spacing: 0.5px;">
                                    --------- ORDER ---------
                                </span>
                            </div>
                            <div class="ps-1">
                                {''.join(order_items_html)}
                            </div>
                        </div>
                    """)
                order.kitchen_order_lines_summary = "".join(round_html)
                continue

            # Render structured rounds (Initial Order, Reorder 1, Reorder 2...)
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

                # Group lines by Category
                lines_by_cat = {}
                for line in round_rec.line_ids:
                    cat = line.category_name or (line.product_id and line.product_id.pos_categ_ids and line.product_id.pos_categ_ids[0].name) or "General"
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

    def action_start_preparing(self):
        for order in self:
            order.kitchen_state = 'preparing'

    def action_pos_order_paid(self):
        for order in self:
            if order.kitchen_state != 'done' and any(line.product_id.type != 'service' for line in order.lines):
                # pyrefly: ignore [missing-import]
                from odoo.exceptions import UserError
                raise UserError("You cannot accept payment! The food must be served to the customer first.")
        return super().action_pos_order_paid()

    def action_ready_to_serve(self):
        for order in self:
            order.kitchen_state = 'ready_to_serve'

    def action_mark_done(self):
        for order in self:
            order.kitchen_state = 'done'

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            order.kitchen_state = 'pending'

            # Initialize Round 0 ("Order") if not already created
            if not order.kitchen_round_ids and order.lines:
                round_lines = []
                for line in order.lines:
                    if line.product_id and order.config_id.module_pos_discount and line.product_id == order.config_id.discount_product_id:
                        continue
                    prod = line.product_id
                    cat_id = prod.pos_categ_ids[0].id if prod and prod.pos_categ_ids else False
                    cat_name = prod.pos_categ_ids[0].name if prod and prod.pos_categ_ids else "General"
                    round_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_name': line.full_product_name or (line.product_id and line.product_id.display_name) or '',
                        'pos_category_id': cat_id,
                        'category_name': cat_name,
                        'qty': line.qty,
                        'note': line.customer_note or '',
                    }))
                if round_lines:
                    self.env['pos.kitchen.round'].create({
                        'order_id': order.id,
                        'sequence': 0,
                        'round_type': 'order',
                        'line_ids': round_lines,
                    })
        return orders

    @api.model
    def sync_from_ui(self, orders):
        """
        Odoo 19 POS calls sync_from_ui() when orders are synced.
        Tracks initial batch under 'Order' (Round 0) and subsequent delta batches under
        'Reorder 1', 'Reorder 2', etc., with category information.
        """
        import logging
        _logger = logging.getLogger(__name__)

        # Step 1: Snapshot line counts and state BEFORE saving
        line_data_before = {}
        for order_data in orders:
            uuid = order_data.get('uuid')
            if not uuid:
                continue
            existing = self._get_open_order(order_data)
            if not existing:
                continue
            if existing.state not in ('cancel', 'paid'):
                line_data_before[existing.id] = {
                    'kitchen_state': existing.kitchen_state,
                    'has_rounds': bool(existing.kitchen_round_ids),
                    'lines': {
                        line.id: {
                            'product_id': line.product_id.id,
                            'product_name': line.full_product_name or (line.product_id and line.product_id.display_name) or '',
                            'qty': line.qty,
                            'note': line.customer_note or '',
                        }
                        for line in existing.lines
                        if not (line.product_id and existing.config_id.module_pos_discount and line.product_id == existing.config_id.discount_product_id)
                    }
                }

        # Step 2: Call the real sync_from_ui (saves everything to DB)
        result = super().sync_from_ui(orders)

        # Step 3: Compare line data AFTER — record initial order or new reorder rounds
        orders_to_increment = []
        for order_id, before_info in line_data_before.items():
            order = self.browse(order_id)
            old_lines = before_info['lines']
            has_rounds = bool(order.kitchen_round_ids)

            # Case A: Order has NO rounds yet at all -> this sync is the INITIAL ORDER
            if not has_rounds:
                initial_round_lines = []
                for line in order.lines:
                    if line.product_id and order.config_id.module_pos_discount and line.product_id == order.config_id.discount_product_id:
                        continue
                    prod = line.product_id
                    cat_id = prod.pos_categ_ids[0].id if prod and prod.pos_categ_ids else False
                    cat_name = prod.pos_categ_ids[0].name if prod and prod.pos_categ_ids else "General"
                    prod_name = line.full_product_name or (line.product_id and line.product_id.display_name) or ''
                    initial_round_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_name': prod_name,
                        'pos_category_id': cat_id,
                        'category_name': cat_name,
                        'qty': line.qty,
                        'note': line.customer_note or '',
                    }))
                if initial_round_lines:
                    self.env['pos.kitchen.round'].create({
                        'order_id': order.id,
                        'sequence': 0,
                        'round_type': 'order',
                        'line_ids': initial_round_lines,
                    })
                    order.write({
                        'kitchen_state': 'pending',
                    })
                    orders_to_increment.append(order_id)
                continue

            # Case B: Order ALREADY has rounds -> detect delta and create REORDER round
            new_round_lines = []
            for line in order.lines:
                # Ignore global discount line
                if line.product_id and order.config_id.module_pos_discount and line.product_id == order.config_id.discount_product_id:
                    continue

                prod = line.product_id
                cat_id = prod.pos_categ_ids[0].id if prod and prod.pos_categ_ids else False
                cat_name = prod.pos_categ_ids[0].name if prod and prod.pos_categ_ids else "General"
                prod_name = line.full_product_name or (line.product_id and line.product_id.display_name) or ''

                if line.id not in old_lines:
                    # New product added to the order
                    new_round_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_name': prod_name,
                        'pos_category_id': cat_id,
                        'category_name': cat_name,
                        'qty': line.qty,
                        'note': line.customer_note or '',
                    }))
                    line.write({
                        'is_reorder': True,
                        'reorder_qty': line.qty,
                        'reorder_note': 'New Item',
                    })
                else:
                    old_info = old_lines[line.id]
                    old_qty = old_info['qty']
                    if line.qty > old_qty:
                        added_qty = line.qty - old_qty
                        new_round_lines.append((0, 0, {
                            'product_id': line.product_id.id,
                            'product_name': prod_name,
                            'pos_category_id': cat_id,
                            'category_name': cat_name,
                            'qty': added_qty,
                            'note': line.customer_note or '',
                        }))
                        line.write({
                            'is_reorder': True,
                            'reorder_qty': added_qty,
                            'reorder_note': f"+{int(added_qty) if added_qty.is_integer() else added_qty} Reordered",
                        })
                    elif line.qty < old_qty:
                        reduced_qty = line.qty - old_qty
                        new_round_lines.append((0, 0, {
                            'product_id': line.product_id.id,
                            'product_name': prod_name,
                            'pos_category_id': cat_id,
                            'category_name': cat_name,
                            'qty': reduced_qty,
                            'note': f"Reduced by {int(abs(reduced_qty)) if reduced_qty.is_integer() else abs(reduced_qty)}",
                        }))
                        line.write({
                            'is_reorder': True,
                            'reorder_qty': line.qty,
                            'reorder_note': f"Qty {int(old_qty) if old_qty.is_integer() else old_qty} ➔ {int(line.qty) if line.qty.is_integer() else line.qty}",
                        })

            if new_round_lines:
                existing_reorders = order.kitchen_round_ids.filtered(lambda r: r.round_type == 'reorder' or r.sequence > 0)
                next_seq = len(existing_reorders) + 1
                self.env['pos.kitchen.round'].create({
                    'order_id': order.id,
                    'sequence': next_seq,
                    'round_type': 'reorder',
                    'line_ids': new_round_lines,
                })
                order.write({
                    'kitchen_state': 'pending',
                })
                orders_to_increment.append(order_id)

        if orders_to_increment:
            self.browse(orders_to_increment).invalidate_recordset(['reorder_count', 'kitchen_state', 'kitchen_order_lines_summary', 'kitchen_round_ids'])

        return result


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    is_reorder = fields.Boolean(string='Is Reorder', default=False)
    reorder_qty = fields.Float(string='Reordered Quantity', default=0.0)
    reorder_note = fields.Char(string='Reorder Note', default='')
