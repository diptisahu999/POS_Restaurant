# -*- coding: utf-8 -*-
from odoo import fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    # table_id and customer_count are inherited from pos_restaurant.
    # We add a clean table name helper if needed for backend reporting.
