# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    hide_discuss = fields.Boolean(
        string='Hide Discuss',
        default=False,
        help='If checked, the Discuss module will be hidden for this user.'
    )
    hide_todo = fields.Boolean(
        string='Hide To-do',
        default=False,
        help='If checked, the To-do module will be hidden for this user.'
    )
    hide_employees = fields.Boolean(
        string='Hide Employees',
        default=False,
        help='If checked, the Employees module and all its submenus will be hidden for this user.'
    )
    hide_link_tracker = fields.Boolean(
        string='Hide Link Tracker',
        default=False,
        help='If checked, the Link Tracker module and UTMs will be hidden for this user.'
    )

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ('hide_discuss', 'hide_todo', 'hide_employees', 'hide_link_tracker')):
            self.env.registry.clear_cache()
        return res
