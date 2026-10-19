# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _check_force_delete_access(self):
        return (
            self.env.user.has_group('custom_pos_orders_force_delete.group_allow_force_delete_pos_orders')
            or self.env.is_superuser
            or self.env.user.has_group('base.group_system')
        )

    def action_force_delete_pos_customer(self):
        """Open the Force Delete confirmation wizard for POS Customers (res.partner)"""
        if not self._check_force_delete_access():
            raise UserError(_(
                "You do not have permission to force delete POS Customers. "
                "Please enable 'Allow Force Delete POS Orders/Sessions/Payments/Customers' "
                "in your user settings."
            ))
        return {
            'name': _('Force Delete POS Customer(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.pos.customer.force.delete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_customer_ids': [(6, 0, self.ids)],
            },
        }

    def unlink(self):
        if self.env.context.get('force_delete_pos_customer') or self._check_force_delete_access():
            # Detach from POS orders before deletion
            orders = self.env['pos.order'].sudo().search([('partner_id', 'in', self.ids)])
            if orders:
                orders.write({'partner_id': False})
            return super(ResPartner, self.sudo().with_context(force_delete_pos_customer=True)).unlink()
        return super().unlink()
