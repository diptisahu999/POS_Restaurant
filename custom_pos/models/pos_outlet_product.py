# -*- coding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import api, fields, models
# pyrefly: ignore [missing-import]
from odoo.osv.expression import AND


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pos_config_ids = fields.Many2many(
        'pos.config',
        'pos_config_product_template_rel',
        'product_tmpl_id',
        'pos_config_id',
        string='Allowed PoS Outlets',
        help='Specify which Point of Sale outlets can sell this product. Leave empty to allow in all PoS outlets.'
    )

    @api.model
    def _load_pos_data_domain(self, data, config):
        domain = super()._load_pos_data_domain(data, config)
        config_id = config.id if hasattr(config, 'id') else config
        if config_id:
            domain = AND([domain, ['|', ('pos_config_ids', '=', False), ('pos_config_ids', 'in', [config_id])]])
        return domain

    @api.model
    def load_product_from_pos(self, config_id, domain, offset=0, limit=0):
        if config_id:
            pos_domain = ['|', ('pos_config_ids', '=', False), ('pos_config_ids', 'in', [config_id])]
            domain = AND([domain or [], pos_domain])
        return super().load_product_from_pos(config_id, domain, offset=offset, limit=limit)

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        if 'pos_config_ids' not in fields_list:
            fields_list.append('pos_config_ids')
        return fields_list

    def _unrelevant_records(self, config):
        unrelevant_record_ids = super()._unrelevant_records(config)
        config_id = config.id if hasattr(config, 'id') else config
        if config_id:
            for record in self:
                if record.pos_config_ids and config_id not in record.pos_config_ids.ids:
                    unrelevant_record_ids.append(record.id)
        return unrelevant_record_ids


class ProductProduct(models.Model):
    _inherit = 'product.product'

    pos_config_ids = fields.Many2many(
        related='product_tmpl_id.pos_config_ids',
        readonly=False,
        string='Allowed PoS Outlets',
        help='Specify which Point of Sale outlets can sell this product. Leave empty to allow in all PoS outlets.'
    )

    @api.model
    def _load_pos_data_domain(self, data, config):
        domain = super()._load_pos_data_domain(data, config)
        config_id = config.id if hasattr(config, 'id') else config
        if config_id:
            domain = AND([domain, ['|', ('pos_config_ids', '=', False), ('pos_config_ids', 'in', [config_id])]])
        return domain

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super()._load_pos_data_fields(config)
        if 'pos_config_ids' not in fields_list:
            fields_list.append('pos_config_ids')
        return fields_list

    def _unrelevant_records(self, config):
        unrelevant_record_ids = super()._unrelevant_records(config)
        config_id = config.id if hasattr(config, 'id') else config
        if config_id:
            for record in self:
                if record.pos_config_ids and config_id not in record.pos_config_ids.ids:
                    unrelevant_record_ids.append(record.id)
        return unrelevant_record_ids
