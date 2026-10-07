# -*- coding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import models, fields

class PosCategory(models.Model):
    _inherit = 'pos.category'

    printer_ids = fields.Many2many(
        'pos.printer',
        'printer_category_rel',
        'category_id',
        'printer_id',
        string='Kitchen Printers',
        help='Select the kitchen printer(s) that should print orders for this food category.',
    )
