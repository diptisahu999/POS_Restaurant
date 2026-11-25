# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _check_force_delete_access(self):
        return self.env.user.has_group('custom_pos_outlet_delete.group_allow_force_delete_pos_outlet')

    def action_force_delete(self):
        """Open the Force Delete confirmation wizard for POS Outlets."""
        if not self._check_force_delete_access():
            raise UserError(_(
                "You do not have permission to force delete POS Outlets. "
                "Please enable 'Allow Force Delete POS Outlets' in your user settings."
            ))
        return {
            'name': _('Force Delete POS Outlet(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.pos.outlet.force.delete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_config_ids': [(6, 0, self.ids)],
            },
        }

    def _force_cleanup_orders(self, orders):
        """Safely detach and unlink POS orders regardless of state."""
        if not orders:
            return
        orders = orders.sudo().with_context(force_delete=True)
        # Unlink payments first
        payments = orders.mapped('payment_ids').sudo().with_context(force_delete=True)
        if payments:
            payments.unlink()
        # Cancel non-draft/cancel orders so standard ondelete guards pass even standalone
        non_deletable = orders.filtered(lambda o: o.state not in ('draft', 'cancel'))
        if non_deletable:
            try:
                non_deletable.write({'state': 'cancel'})
            except Exception:
                pass
        orders.unlink()

    def unlink(self):
        if self.env.context.get('force_delete'):
            if not (self.env.su or self._check_force_delete_access()):
                raise UserError(_(
                    "You do not have permission to force delete POS Outlets. "
                    "Please enable 'Allow Force Delete POS Outlets' in your user settings."
                ))
            for config in self:
                # 1. Clean up orders & sessions belonging to this outlet
                sessions = self.env['pos.session'].sudo().search([('config_id', '=', config.id)])
                orders = self.env['pos.order'].sudo().search([
                    '|', ('config_id', '=', config.id), ('session_id', 'in', sessions.ids)
                ])
                self._force_cleanup_orders(orders)

                # Unlink any remaining payments linked directly to this outlet
                PosPayment = self.env['pos.payment'].sudo()
                if 'pos_config_id' in PosPayment._fields:
                    extra_payments = PosPayment.search([('pos_config_id', '=', config.id)])
                    if extra_payments:
                        extra_payments.with_context(force_delete=True).unlink()

                if sessions:
                    open_sessions = sessions.filtered(lambda s: s.state != 'closed')
                    if open_sessions:
                        try:
                            open_sessions.write({'state': 'closed'})
                        except Exception:
                            pass
                    for session in sessions:
                        if hasattr(session, 'statement_line_ids') and session.statement_line_ids:
                            session.statement_line_ids.sudo().with_context(force_delete=True).unlink()
                    sessions.sudo().with_context(force_delete=True).unlink()

                # 2. Clean up transient settings referencing this outlet
                settings = self.env['res.config.settings'].sudo().search([('pos_config_id', '=', config.id)])
                if settings:
                    settings.unlink()

                # 3. Detach Many2many relations
                vals = {}
                for field_name in ('floor_ids', 'printer_ids', 'payment_method_ids', 'iface_available_categ_ids'):
                    if field_name in config._fields:
                        vals[field_name] = [(5, 0, 0)]
                if vals:
                    config.sudo().write(vals)

            return super(PosConfig, self.sudo().with_context(force_delete=True)).unlink()
        return super().unlink()
