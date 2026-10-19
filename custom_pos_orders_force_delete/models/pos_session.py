# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _check_force_delete_access(self):
        return (
            self.env.user.has_group('custom_pos_orders_force_delete.group_allow_force_delete_pos_orders')
            or self.env.is_superuser
            or self.env.user.has_group('base.group_system')
        )

    def action_force_delete(self):
        """Open the Force Delete confirmation wizard for POS Sessions"""
        if not self._check_force_delete_access():
            raise UserError(_(
                "You do not have permission to force delete POS Sessions. "
                "Please enable 'Allow Force Delete POS Orders/Sessions/Payments/Customers' "
                "in your user settings."
            ))
        return {
            'name': _('Force Delete POS Session(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.pos.session.force.delete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_ids': [(6, 0, self.ids)],
            },
        }

    def unlink(self):
        if self.env.context.get('force_delete') or self._check_force_delete_access():
            for session in self:
                # Force close any open session first
                if session.state not in ('closed',):
                    try:
                        session.sudo().write({'state': 'closed'})
                    except Exception:
                        pass
                # Unlink all orders in the session
                orders = self.env['pos.order'].sudo().search([('session_id', '=', session.id)])
                if orders:
                    orders.sudo().with_context(force_delete=True).unlink()
                # Unlink all statement lines
                if hasattr(session, 'statement_line_ids') and session.statement_line_ids:
                    session.statement_line_ids.sudo().with_context(force_delete=True).unlink()
            return super(PosSession, self.sudo().with_context(force_delete=True)).unlink()
        return super().unlink()
