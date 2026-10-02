# pyrefly: ignore [missing-import]
from odoo import models, fields, api

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
        default=0,
        help='How many times the order was modified after being sent to kitchen',
    )

    kitchen_order_lines_summary = fields.Html(string='Order Summary', compute='_compute_kitchen_order_lines_summary', sanitize=False)

    @api.depends(
        'lines', 'lines.qty', 'lines.full_product_name', 'lines.product_id',
        'lines.customer_note', 'lines.is_reorder', 'lines.reorder_qty', 'lines.reorder_note'
    )
    def _compute_kitchen_order_lines_summary(self):
        for order in self:
            items_html = []
            for line in order.lines:
                # Filter out the global discount line from the kitchen view
                if line.product_id and order.config_id.module_pos_discount and line.product_id == order.config_id.discount_product_id:
                    continue
                
                name = line.full_product_name or (line.product_id and line.product_id.display_name) or ''
                qty = int(line.qty) if line.qty.is_integer() else line.qty

                badge_html = ""
                if line.is_reorder:
                    if line.reorder_note:
                        badge_text = f"🔁 {line.reorder_note}"
                    elif line.reorder_qty > 0 and line.reorder_qty < line.qty:
                        r_qty = int(line.reorder_qty) if line.reorder_qty.is_integer() else line.reorder_qty
                        badge_text = f"🔁 +{r_qty} Reordered"
                    else:
                        badge_text = "🔁 Reordered"

                    badge_html = f"""<span class="badge rounded-pill text-bg-danger ms-2" style="font-size: 12px; padding: 4px 8px; font-weight: 700; vertical-align: middle;">
                        {badge_text}
                    </span>"""

                note_html = ""
                if line.customer_note:
                    note_html = f"""<div style="color: #dc3545; font-size: 14px; font-weight: bold; margin-left: 20px; font-style: italic;">
                        ↳ Remark: {line.customer_note}
                    </div>"""
                items_html.append(f"""
                    <div style="margin-bottom: 8px;">
                        <span style="font-size: 16px; font-weight: 600; color: #111;">
                            {qty}x {name}
                        </span>
                        {badge_html}
                        {note_html}
                    </div>
                """)
            order.kitchen_order_lines_summary = "".join(items_html)

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
            # When an order comes from the POS, automatically put it in 'pending' state
            order.kitchen_state = 'pending'
        return orders

    @api.model
    def sync_from_ui(self, orders):
        """
        Odoo 19 POS calls sync_from_ui() when orders are synced.
        Detects if new lines were added, quantities modified, or items changed,
        increments reorder_count, marks the reordered lines, and updates kitchen_state.
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
            # Track any active order (not cancelled or paid)
            if existing.state not in ('cancel', 'paid'):
                line_data_before[existing.id] = {
                    'kitchen_state': existing.kitchen_state,
                    'lines': {line.id: line.qty for line in existing.lines}
                }

        # Step 2: Call the real sync_from_ui (saves everything to DB)
        result = super().sync_from_ui(orders)

        # Step 3: Compare line data AFTER — detect new items or quantity changes
        orders_to_increment = []
        for order_id, before_info in line_data_before.items():
            order = self.browse(order_id)
            old_lines = before_info['lines']
            old_kitchen_state = before_info['kitchen_state']
            is_reorder = False

            # If previous round of food was already ready to serve or served,
            # clear previous reorder badges so only current round changes are highlighted.
            if old_kitchen_state in ('ready_to_serve', 'done'):
                order.lines.write({'is_reorder': False, 'reorder_qty': 0.0, 'reorder_note': ''})

            current_line_ids = []
            for line in order.lines:
                current_line_ids.append(line.id)
                # Ignore global discount line
                if line.product_id and order.config_id.module_pos_discount and line.product_id == order.config_id.discount_product_id:
                    continue

                if line.id not in old_lines:
                    # New product added to the order
                    is_reorder = True
                    line.write({
                        'is_reorder': True,
                        'reorder_qty': line.qty,
                        'reorder_note': 'New Item',
                    })
                elif line.qty > old_lines[line.id]:
                    # Quantity increased (number of product changed)
                    is_reorder = True
                    added_qty = line.qty - old_lines[line.id]
                    line.write({
                        'is_reorder': True,
                        'reorder_qty': added_qty,
                        'reorder_note': f"+{int(added_qty) if added_qty.is_integer() else added_qty} Reordered",
                    })
                elif line.qty < old_lines[line.id]:
                    # Quantity reduced
                    is_reorder = True
                    old_q = int(old_lines[line.id]) if old_lines[line.id].is_integer() else old_lines[line.id]
                    new_q = int(line.qty) if line.qty.is_integer() else line.qty
                    line.write({
                        'is_reorder': True,
                        'reorder_qty': line.qty,
                        'reorder_note': f"Qty {old_q} ➔ {new_q}",
                    })

            if not is_reorder:
                for old_id in old_lines:
                    if old_id not in current_line_ids:
                        is_reorder = True
                        break

            if is_reorder:
                orders_to_increment.append(order_id)

        if orders_to_increment:
            for ro_order in self.browse(orders_to_increment):
                ro_order.write({
                    'reorder_count': ro_order.reorder_count + 1,
                    'kitchen_state': 'pending',
                })
            self.browse(orders_to_increment).invalidate_recordset(['reorder_count', 'kitchen_state', 'kitchen_order_lines_summary'])

        return result


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    is_reorder = fields.Boolean(string='Is Reorder', default=False)
    reorder_qty = fields.Float(string='Reordered Quantity', default=0.0)
    reorder_note = fields.Char(string='Reorder Note', default='')
