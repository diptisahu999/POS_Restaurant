# -*- coding: utf-8 -*-
from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    order_status = fields.Selection([
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('done', 'Done'),
    ], string='Order Status', default='pending', index=True, copy=False)

    def _process_order(self, order, existing_order):
        order_id = super()._process_order(order, existing_order)
        if order.get('order_status'):
            pos_order = self.browse(order_id)
            if pos_order.exists() and pos_order.order_status != order['order_status']:
                pos_order.write({'order_status': order['order_status']})
        return order_id
