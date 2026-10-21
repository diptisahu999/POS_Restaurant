# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import AccessError


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    def _get_action_dict(self):
        self.ensure_one()
        if not self.env.is_superuser():
            is_apps_action = (
                self.path == 'apps'
                or self.res_model == 'ir.module.module'
                or (self == self.env.ref('base.open_module_tree', raise_if_not_found=False))
            )
            if is_apps_action and not self.env.user.has_group('custom_apps_access.group_apps_access'):
                raise AccessError(_("You do not have permission to access the Apps module."))

        return super()._get_action_dict()
