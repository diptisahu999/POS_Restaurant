# -*- coding: utf-8 -*-
from odoo import models, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        if view_type in ('list', 'tree', 'form', 'kanban'):
            user = self.env.user
            if not self.env.is_superuser() and not user.has_group('custom_pos_order_create_access.group_allow_create_pos_order'):
                arch.attrib['create'] = 'false'
        return arch, view
