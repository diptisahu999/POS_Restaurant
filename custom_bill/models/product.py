# -*- coding: utf-8 -*-
# pyrefly: ignore[missing-import]
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    hsn_code = fields.Char(
        string='HSN / SAC Code',
        default='0202',
        help='Harmonized System of Nomenclature / Services Accounting Code'
    )

class ProductProduct(models.Model):
    _inherit = 'product.product'

    hsn_code = fields.Char(
        related='product_tmpl_id.hsn_code',
        readonly=False,
        string='HSN / SAC Code'
    )
