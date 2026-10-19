# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    def _check_force_delete_access(self):
        return (
            self.env.user.has_group('custom_pos_orders_force_delete.group_allow_force_delete_pos_orders')
            or self.env.is_superuser
            or self.env.user.has_group('base.group_system')
        )

    def action_force_delete(self):
        """Open the Force Delete confirmation wizard for POS Payments"""
        if not self._check_force_delete_access():
            raise UserError(_(
                "You do not have permission to force delete POS Payments. "
                "Please enable 'Allow Force Delete POS Orders/Sessions/Payments/Customers' "
                "in your user settings."
            ))
        return {
            'name': _('Force Delete POS Payment(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.pos.payment.force.delete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_ids': [(6, 0, self.ids)],
            },
        }

    def unlink(self):
        if self.env.context.get('force_delete') or self._check_force_delete_access():
            return super(PosPayment, self.sudo().with_context(force_delete=True)).unlink()
        return super().unlink()
