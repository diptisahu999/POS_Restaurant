# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_force_delete_pos_outlet_access = fields.Boolean(
        string='Allow Force Delete POS Outlets',
        compute='_compute_has_force_delete_pos_outlet_access',
        inverse='_set_has_force_delete_pos_outlet_access',
        store=False,
    )

    def _compute_has_force_delete_pos_outlet_access(self):
        group = self.env.ref('custom_pos_outlet_delete.group_allow_force_delete_pos_outlet', raise_if_not_found=False)
        for user in self:
            user.has_force_delete_pos_outlet_access = group in user.group_ids if group else False

    def _set_has_force_delete_pos_outlet_access(self):
        group = self.env.ref('custom_pos_outlet_delete.group_allow_force_delete_pos_outlet', raise_if_not_found=False)
        if not group:
            return
        for user in self:
            if user.has_force_delete_pos_outlet_access:
                user.group_ids = [(4, group.id)]
            else:
                user.group_ids = [(3, group.id)]
