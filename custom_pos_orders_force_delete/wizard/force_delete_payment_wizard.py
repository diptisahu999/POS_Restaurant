# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ForceDeletePaymentWizard(models.TransientModel):
    _name = 'custom.pos.payment.force.delete.wizard'
    _description = 'Force Delete POS Payment Wizard'

    payment_ids = fields.Many2many('pos.payment', string='Payments to Delete')
    payment_names = fields.Char(string='Payment Names', compute='_compute_payment_names')
    count = fields.Integer(string='Count', compute='_compute_payment_names')

    @api.depends('payment_ids')
    def _compute_payment_names(self):
        for rec in self:
            if rec.payment_ids:
                names = [str(p.id) for p in rec.payment_ids]
                rec.count = len(rec.payment_ids)
                rec.payment_names = ", ".join(names)
            else:
                rec.count = 0
                rec.payment_names = ""

    def action_confirm_force_delete(self):
        self.ensure_one()
        if not self.payment_ids:
            return

        self.payment_ids.sudo().with_context(force_delete=True).unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Deleted'),
                'message': _('POS Payment(s) force deleted successfully.'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'pos.payment',
                    'view_mode': 'list,form',
                    'views': [(False, 'list'), (False, 'form')],
                }
            }
        }
