# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _check_force_delete_access(self):
        return (
            self.env.user.has_group('custom_pos_orders_force_delete.group_allow_force_delete_pos_orders')
            or self.env.is_superuser
            or self.env.user.has_group('base.group_system')
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_forbid_parts_of_chain(self):
        """
        Bypass sequence chain gap restriction when force delete is performed.
        """
        if self.env.context.get('force_delete') or self._check_force_delete_access():
            return
        return super()._unlink_forbid_parts_of_chain()

    @api.ondelete(at_uninstall=False)
    def _unlink_account_audit_trail_except_once_post(self):
        """
        Bypass audit trail deletion restriction when force delete is performed.
        """
        if self.env.context.get('force_delete') or self._check_force_delete_access():
            return
        return super()._unlink_account_audit_trail_except_once_post()

    def action_force_delete(self):
        """Open the Force Delete confirmation wizard for Customer Invoices / Account Moves"""
        if not self._check_force_delete_access():
            raise UserError(_(
                "You do not have permission to force delete Invoices. "
                "Please enable 'Allow Force Delete POS Orders/Sessions/Payments/Customers/Invoices' "
                "in your user settings."
            ))
        return {
            'name': _('Force Delete Invoice(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.account.move.force.delete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_ids': [(6, 0, self.ids)],
            },
        }

    def unlink(self):
        if self.env.context.get('force_delete') or self._check_force_delete_access():
            for move in self:
                # 1. Detach from linked pos.order
                self.env['pos.order'].sudo().search([('account_move', '=', move.id)]).write({'account_move': False})
                # 2. Detach from linked pos.payment
                self.env['pos.payment'].sudo().search([('account_move_id', '=', move.id)]).write({'account_move_id': False})
                # 3. Detach from pos.session
                self.env['pos.session'].sudo().search([('move_id', '=', move.id)]).write({'move_id': False})
                # 4. Remove reconciliations
                reconciled_lines = move.line_ids.filtered('reconciled')
                if reconciled_lines:
                    reconciled_lines.sudo().remove_move_reconcile()
                # 5. Reset to draft if posted
                if move.state == 'posted':
                    move.sudo().button_draft()
            return super(AccountMove, self.sudo().with_context(force_delete=True, dynamic_unlink=True)).unlink()
        return super().unlink()
