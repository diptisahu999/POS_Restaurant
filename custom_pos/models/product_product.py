# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_one_time = fields.Boolean(
        related='product_tmpl_id.is_one_time',
        string='One-Time Product',
        readonly=True,
    )

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super()._load_pos_data_fields(config)
        if 'is_one_time' not in fields_list:
            fields_list.append('is_one_time')
        return fields_list
