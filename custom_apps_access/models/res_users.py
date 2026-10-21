# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_apps_access = fields.Boolean(
        string='Allow Apps Module Access',
        compute='_compute_has_apps_access',
        inverse='_set_has_apps_access',
        store=False,
    )

    def _compute_has_apps_access(self):
        group = self.env.ref('custom_apps_access.group_apps_access', raise_if_not_found=False)
        for user in self:
            user.has_apps_access = bool(group and group in user.group_ids)

    def _set_has_apps_access(self):
        group = self.env.ref('custom_apps_access.group_apps_access', raise_if_not_found=False)
        if not group:
            return
        for user in self:
            if user.has_apps_access:
                user.group_ids = [Command.link(group.id)]
            else:
                user.group_ids = [Command.unlink(group.id)]
