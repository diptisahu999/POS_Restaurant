# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    pos_printer_ids = fields.Many2many(
        'pos.printer',
        'pos_printer_product_rel',
        'product_id',
        'printer_id',
        string='Kitchen Printers'
    )


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pos_printer_ids = fields.Many2many(
        'pos.printer',
        string='Kitchen Printers',
        compute='_compute_pos_printer_ids',
        inverse='_inverse_pos_printer_ids',
        search='_search_pos_printer_ids',
        help='Kitchen printers that will print tickets for this product.'
    )

    @api.depends('product_variant_ids.pos_printer_ids')
    def _compute_pos_printer_ids(self):
        for template in self:
            template.pos_printer_ids = template.product_variant_ids.pos_printer_ids

    def _inverse_pos_printer_ids(self):
        for template in self:
            for variant in template.product_variant_ids:
                variant.pos_printer_ids = template.pos_printer_ids

    def _search_pos_printer_ids(self, operator, value):
        return [('product_variant_ids.pos_printer_ids', operator, value)]
