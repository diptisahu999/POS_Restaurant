from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    kitchen_state = fields.Selection([
        ('pending', 'Waiting'),
        ('preparing', 'Preparing'),
        ('ready_to_serve', 'Ready to Serve'),
        ('done', 'Served')
    ], string='Kitchen Status', default='pending', tracking=True)

    kitchen_order_lines_summary = fields.Html(string='Order Summary', compute='_compute_kitchen_order_lines_summary', sanitize=False)

    @api.depends('lines', 'lines.qty', 'lines.full_product_name', 'lines.product_id', 'lines.customer_note')
    def _compute_kitchen_order_lines_summary(self):
        for order in self:
            items_html = []
            for line in order.lines:
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
