# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import AccessError


class IrActionsClient(models.Model):
    _inherit = 'ir.actions.client'

    def read(self, fields=None, load='_classic_read'):
        if not self.env.is_superuser() and getattr(self.env.user, 'hide_discuss', False):
            discuss_action = self.env.ref('mail.action_discuss', raise_if_not_found=False)
            for action in self:
                if action.path == 'discuss' or action.tag == 'mail.action_discuss' or (discuss_action and action.id == discuss_action.id):
                    raise AccessError(_("You do not have permission to access Discuss."))
        return super().read(fields=fields, load=load)
