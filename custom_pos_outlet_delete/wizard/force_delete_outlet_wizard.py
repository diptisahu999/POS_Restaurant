# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ForceDeleteOutletWizard(models.TransientModel):
    _name = 'custom.pos.outlet.force.delete.wizard'
    _description = 'Force Delete POS Outlet Wizard'

    config_ids = fields.Many2many('pos.config', string='POS Outlets to Delete')
    config_names = fields.Char(string='POS Outlet Names', compute='_compute_config_details')
    count = fields.Integer(string='Count', compute='_compute_config_details')
    session_count = fields.Integer(string='Linked Sessions', compute='_compute_config_details')
    order_count = fields.Integer(string='Linked Orders', compute='_compute_config_details')

    @api.depends('config_ids')
    def _compute_config_details(self):
        for rec in self:
            if rec.config_ids:
                names = rec.config_ids.mapped('name')
                rec.count = len(rec.config_ids)
                rec.config_names = ", ".join(names)
                rec.session_count = self.env['pos.session'].sudo().search_count([
                    ('config_id', 'in', rec.config_ids.ids)
                ])
                rec.order_count = self.env['pos.order'].sudo().search_count([
                    ('config_id', 'in', rec.config_ids.ids)
                ])
            else:
                rec.count = 0
                rec.config_names = ""
                rec.session_count = 0
                rec.order_count = 0

    def action_confirm_force_delete(self):
        self.ensure_one()
        if not self.config_ids:
            return
        if not (self.env.su or self.config_ids._check_force_delete_access()):
            from odoo.exceptions import UserError
            raise UserError(_(
                "You do not have permission to force delete POS Outlets. "
                "Please enable 'Allow Force Delete POS Outlets' in your user settings."
            ))

        self.config_ids.sudo().with_context(force_delete=True).unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Deleted'),
                'message': _('POS Outlet(s) force deleted successfully.'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'pos.config',
                    'view_mode': 'kanban,list,form',
                    'views': [(False, 'kanban'), (False, 'list'), (False, 'form')],
                }
            }
        }
