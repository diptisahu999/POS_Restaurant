# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ForceDeleteCustomerWizard(models.TransientModel):
    _name = 'custom.pos.customer.force.delete.wizard'
    _description = 'Force Delete POS Customer Wizard'

    customer_ids = fields.Many2many('res.partner', string='Customers to Delete')
    customer_names = fields.Char(string='Customer Names', compute='_compute_customer_names')
    count = fields.Integer(string='Count', compute='_compute_customer_names')

    @api.depends('customer_ids')
    def _compute_customer_names(self):
        for rec in self:
            if rec.customer_ids:
                names = rec.customer_ids.mapped('name')
                rec.count = len(rec.customer_ids)
                rec.customer_names = ", ".join(names)
            else:
                rec.count = 0
                rec.customer_names = ""

    def action_confirm_force_delete(self):
        self.ensure_one()
        if not self.customer_ids:
            return

        self.customer_ids.sudo().with_context(force_delete_pos_customer=True).unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Deleted'),
                'message': _('POS Customer(s) force deleted successfully.'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'res.partner',
                    'view_mode': 'list,form',
                    'views': [(False, 'list'), (False, 'form')],
                }
            }
        }
