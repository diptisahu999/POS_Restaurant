from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    kitchen_state = fields.Selection([
        ('pending', 'Waiting'),
        ('preparing', 'Preparing'),
        ('ready_to_serve', 'Ready to Serve'),
        ('done', 'Served')
    ], string='Kitchen Status', default='pending', tracking=True)

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
