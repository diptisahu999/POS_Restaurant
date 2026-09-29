# -*- coding: utf-8 -*-
from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    nc_reason = fields.Char(
        string='No Charge (NC) Reason',
        help='Reason recorded when paying with No Charge (NC)'
    )

    @api.model
    def _process_order(self, order, existing_order):
        order_id = super()._process_order(order, existing_order)
        if order.get('nc_reason'):
            pos_order = self.browse(order_id)
            if pos_order.exists() and pos_order.nc_reason != order['nc_reason']:
                pos_order.write({'nc_reason': order['nc_reason']})
        return order_id


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    nc_reason = fields.Char(
        string='NC Reason',
        help='Reason recorded for No Charge (NC) payment'
    )
