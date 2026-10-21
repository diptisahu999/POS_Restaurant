# -*- coding: utf-8 -*-
from odoo import models, api


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        visible_ids = super()._visible_menu_ids(debug=debug)
        if self.env.is_superuser():
            return visible_ids

        if not self.env.user.has_group('custom_apps_access.group_apps_access'):
            apps_menu = self.env.ref('base.menu_management', raise_if_not_found=False)
            if apps_menu:
                apps_menus = self.search([('id', 'child_of', apps_menu.id)])
                visible_ids = frozenset(visible_ids - set(apps_menus.ids))

        return visible_ids
