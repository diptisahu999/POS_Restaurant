# pyrefly: ignore [missing-import]
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    allow_modify_invoices = fields.Boolean(
        string='Modify Paid Invoices',
        compute='_compute_allow_modify_invoices',
        inverse='_set_allow_modify_invoices',
        store=False,
    )

    def _compute_allow_modify_invoices(self):
        group = self.env.ref('custom_invoice_modify.group_modify_paid_invoices', raise_if_not_found=False)
        for user in self:
            user.allow_modify_invoices = group in user.group_ids if group else False

    def _set_allow_modify_invoices(self):
        group = self.env.ref('custom_invoice_modify.group_modify_paid_invoices', raise_if_not_found=False)
        if not group:
            return
        for user in self:
            if user.allow_modify_invoices:
                user.group_ids = [(4, group.id)]
            else:
                user.group_ids = [(3, group.id)]
