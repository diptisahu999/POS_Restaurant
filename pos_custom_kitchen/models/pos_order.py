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

    @api.depends('lines', 'lines.qty', 'lines.full_product_name', 'lines.product_id', 'lines.customer_note')
    def _compute_kitchen_order_lines_summary(self):
        for order in self:
            items_html = []
            for line in order.lines:
                # Filter out the global discount line from the kitchen view
                if line.product_id and order.config_id.module_pos_discount and line.product_id == order.config_id.discount_product_id:
                    continue
                
                name = line.full_product_name or (line.product_id and line.product_id.display_name) or ''
                qty = int(line.qty) if line.qty.is_integer() else line.qty
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
        Odoo 19 POS calls sync_from_ui() when 'Send to Kitchen' syncs the order.
        We detect if new lines were added to an existing active kitchen order
        and increment reorder_count.
        """
        # Step 1: snapshot line counts BEFORE saving, for existing active kitchen orders
        # Odoo 19 finds orders by 'uuid', not 'id'
        line_counts_before = {}
        for order_data in orders:
            uuid = order_data.get('uuid')
            if not uuid:
                continue
            existing = self._get_open_order(order_data)
            if not existing:
                continue
            if existing.kitchen_state in ('pending', 'preparing', 'ready_to_serve'):
                line_counts_before[existing.id] = len(existing.lines)

        # Step 2: call the real sync_from_ui (saves everything to DB)
        result = super().sync_from_ui(orders)

        # Step 3: compare line counts AFTER — increment reorder for orders with new items
        orders_to_increment = []
        for order_id, count_before in line_counts_before.items():
            order = self.browse(order_id)
            if len(order.lines) > count_before:
                orders_to_increment.append(order_id)

        if orders_to_increment:
            self.env.cr.execute(
                "UPDATE pos_order SET reorder_count = reorder_count + 1 WHERE id IN %s",
                (tuple(orders_to_increment),)
            )
            self.browse(orders_to_increment).invalidate_recordset(['reorder_count'])

        return result
