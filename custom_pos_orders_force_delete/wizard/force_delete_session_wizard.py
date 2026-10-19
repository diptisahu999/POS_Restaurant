# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ForceDeleteSessionWizard(models.TransientModel):
    _name = 'custom.pos.session.force.delete.wizard'
    _description = 'Force Delete POS Session Wizard'

    session_ids = fields.Many2many('pos.session', string='Sessions to Delete')
    session_names = fields.Char(string='Session Names', compute='_compute_session_names')
    count = fields.Integer(string='Count', compute='_compute_session_names')

    @api.depends('session_ids')
    def _compute_session_names(self):
        for rec in self:
            if rec.session_ids:
                names = rec.session_ids.mapped('name')
                rec.count = len(rec.session_ids)
                rec.session_names = ", ".join(names)
            else:
                rec.count = 0
                rec.session_names = ""

    def action_confirm_force_delete(self):
        self.ensure_one()
        if not self.session_ids:
            return

        self.session_ids.sudo().with_context(force_delete=True).unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Deleted'),
                'message': _('POS Session(s) force deleted successfully.'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'pos.session',
                    'view_mode': 'list,form',
                    'views': [(False, 'list'), (False, 'form')],
                }
            }
        }
