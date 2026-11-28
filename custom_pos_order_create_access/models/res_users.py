# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    pos_designation_id = fields.Many2one(
        'pos.designation',
        string='Designation',
        help='User designation. You can select existing or type to create a new one.'
    )
    has_create_pos_order_access = fields.Boolean(
        string='Allow Create POS Orders',
        compute='_compute_has_create_pos_order_access',
        inverse='_set_has_create_pos_order_access',
        store=False,
        help='If checked, the user is allowed to see and use the Create (New) button on POS Orders.'
    )

    def _compute_has_create_pos_order_access(self):
        group = self.env.ref(
            'custom_pos_order_create_access.group_allow_create_pos_order',
            raise_if_not_found=False
        )
        for user in self:
            user.has_create_pos_order_access = group in user.group_ids if group else False

    def _set_has_create_pos_order_access(self):
        group = self.env.ref(
            'custom_pos_order_create_access.group_allow_create_pos_order',
            raise_if_not_found=False
        )
        if not group:
            return
        for user in self:
            if user.has_create_pos_order_access:
                user.group_ids = [(4, group.id)]
            else:
                user.group_ids = [(3, group.id)]

    @api.onchange('pos_designation_id')
    def _onchange_pos_designation_id(self):
        if self.pos_designation_id:
            self.has_create_pos_order_access = self.pos_designation_id.allow_create_pos_order
