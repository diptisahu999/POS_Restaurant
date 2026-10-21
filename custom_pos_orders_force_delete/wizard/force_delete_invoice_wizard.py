# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ForceDeleteInvoiceWizard(models.TransientModel):
    _name = 'custom.account.move.force.delete.wizard'
    _description = 'Force Delete Invoice Wizard'

    invoice_ids = fields.Many2many('account.move', string='Invoices to Delete')
    invoice_names = fields.Char(string='Invoice Numbers', compute='_compute_invoice_names')
    count = fields.Integer(string='Count', compute='_compute_invoice_names')

    @api.depends('invoice_ids')
    def _compute_invoice_names(self):
        for rec in self:
            if rec.invoice_ids:
                names = rec.invoice_ids.mapped('name')
                rec.count = len(rec.invoice_ids)
                rec.invoice_names = ", ".join(names)
            else:
                rec.count = 0
                rec.invoice_names = ""

    def action_confirm_force_delete(self):
        self.ensure_one()
        if not self.invoice_ids:
            return

        self.invoice_ids.sudo().with_context(force_delete=True, dynamic_unlink=True).unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Deleted'),
                'message': _('Invoice(s) force deleted successfully.'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'view_mode': 'list,form',
                    'views': [(False, 'list'), (False, 'form')],
                }
            }
        }
