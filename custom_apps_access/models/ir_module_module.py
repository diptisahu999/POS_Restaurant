# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import AccessError


class IrModule(models.Model):
    _inherit = 'ir.module.module'

    def _check_apps_access(self):
        if not self.env.is_superuser() and not self.env.user.has_group('custom_apps_access.group_apps_access'):
            raise AccessError(_("You do not have permission to manage modules."))

    def button_immediate_install(self):
        self._check_apps_access()
        return super().button_immediate_install()

    def button_immediate_upgrade(self):
        self._check_apps_access()
        return super().button_immediate_upgrade()

    def button_immediate_uninstall(self):
        self._check_apps_access()
        return super().button_immediate_uninstall()

    def button_install(self):
        self._check_apps_access()
        return super().button_install()

    def button_upgrade(self):
        self._check_apps_access()
        return super().button_upgrade()

    def button_uninstall(self):
        self._check_apps_access()
        return super().button_uninstall()

    @api.model_create_multi
    def create(self, vals_list):
        self._check_apps_access()
        return super().create(vals_list)

    def write(self, vals):
        if any(f in vals for f in ('state', 'name', 'author', 'website', 'summary', 'description')):
            self._check_apps_access()
        return super().write(vals)

    def unlink(self):
        self._check_apps_access()
        return super().unlink()
