# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _check_force_delete_access(self):
        return (
            self.env.user.has_group('custom_pos_orders_force_delete.group_allow_force_delete_pos_orders')
            or self.env.is_superuser
            or self.env.user.has_group('base.group_system')
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        """
        Override Odoo's built-in guard that blocks deletion of orders
        not in draft/cancel state. Skip the restriction when force_delete
        context is set or user has the permission group.
        """
        if self.env.context.get('force_delete'):
            return
        if self._check_force_delete_access():
            return
        # Fall back to original restriction
        for pos_order in self:
            if pos_order.state not in ['draft', 'cancel']:
                raise UserError(_('In order to delete a sale, it must be new or cancelled.'))

    def action_force_delete(self):
        """Open the Force Delete confirmation wizard for POS Orders"""
        if not self._check_force_delete_access():
            raise UserError(_(
                "You do not have permission to force delete POS Orders. "
                "Please enable 'Allow Force Delete POS Orders/Sessions/Payments/Customers' "
                "in your user settings."
            ))
        return {
            'name': _('Force Delete POS Order(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.pos.order.force.delete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_ids': [(6, 0, self.ids)],
            },
        }

    def unlink(self):
        if self.env.context.get('force_delete') or self._check_force_delete_access():
            # Use sudo + force_delete context so all child ondelete guards are bypassed
            return super(PosOrder, self.sudo().with_context(force_delete=True)).unlink()
        return super().unlink()

