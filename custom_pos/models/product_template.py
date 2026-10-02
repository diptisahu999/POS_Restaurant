# -*- coding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_one_time = fields.Boolean(
        string='One-Time Product',
        default=False,
        help="If enabled, this product is created for a single order/bill only and will not be displayed in the POS product catalog."
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_one_time'):
                vals['available_in_pos'] = False
                vals['is_storable'] = False
                vals['type'] = 'service'
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('is_one_time'):
            vals['available_in_pos'] = False
            vals['is_storable'] = False
            vals['type'] = 'service'
        return super().write(vals)

    @api.model
    def _load_pos_data_domain(self, data, config):
        domain = super()._load_pos_data_domain(data, config)
        domain.append(('is_one_time', '=', False))
        return domain

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        if 'is_one_time' not in fields_list:
            fields_list.append('is_one_time')
        return fields_list

    @api.model
    def archive_one_time_product(self, template_id):
        """Archive a one-time product after it has been added to an order.
        Archived products are invisible in all product lists but the order line
        still references them for bill printing purposes.
        """
        product = self.with_context(active_test=False).browse(template_id)
        if product.exists() and product.is_one_time:
            product.write({'active': False})
        return True
