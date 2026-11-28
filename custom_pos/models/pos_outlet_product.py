# -*- coding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import api, fields, models
# pyrefly: ignore [missing-import]
from odoo.osv.expression import AND


def _search_panel_select_multi_range_pos(recordset, super_call, field_name, **kwargs):
    """Adjust POS outlet & category search panel values and counters.

    - For 'pos_config_ids', include products with empty pos_config_ids ("All PoS Outlets")
      in each outlet's counter so counts match the filtered product list.
    - For 'pos_categ_ids', restrict listed categories to those used by products matching
      the active PoS outlet/filter domain when any outlet filter is active.
    """
    has_extra_domain = bool(kwargs.get('category_domain') or kwargs.get('filter_domain'))

    if field_name == 'pos_config_ids':
        res = super_call(field_name, **kwargs)
        if kwargs.get('enable_counters') and not kwargs.get('group_by') and res.get('values'):
            model_domain = kwargs.get('search_domain', [])
            extra_domain = AND([
                kwargs.get('category_domain', []),
                kwargs.get('filter_domain', []),
            ])
            all_outlets_domain = AND([
                model_domain,
                [('pos_config_ids', '=', False)],
                extra_domain,
            ])
            all_outlets_count = recordset.search_count(all_outlets_domain)
            if all_outlets_count:
                for val in res['values']:
                    val['__count'] = val.get('__count', 0) + all_outlets_count
        return res

    if field_name == 'pos_categ_ids' and has_extra_domain and not kwargs.get('expand'):
        model_domain = kwargs.get('search_domain', [])
        extra_domain = AND([
            kwargs.get('category_domain', []),
            kwargs.get('filter_domain', []),
        ])
        scoped_domain = AND([model_domain, extra_domain])
        domain_image = recordset._search_panel_domain_image(
            field_name, scoped_domain, limit=kwargs.get('limit')
        )
        kwargs = dict(kwargs)
        kwargs['comodel_domain'] = AND([
            kwargs.get('comodel_domain', []),
            [('id', 'in', list(domain_image.keys()))],
        ])

    return super_call(field_name, **kwargs)


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
    def search_panel_select_multi_range(self, field_name, **kwargs):
        return _search_panel_select_multi_range_pos(
            self,
            lambda f, **kw: super(ProductTemplate, self).search_panel_select_multi_range(f, **kw),
            field_name,
            **kwargs,
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
    def search_panel_select_multi_range(self, field_name, **kwargs):
        return _search_panel_select_multi_range_pos(
            self,
            lambda f, **kw: super(ProductProduct, self).search_panel_select_multi_range(f, **kw),
            field_name,
            **kwargs,
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
