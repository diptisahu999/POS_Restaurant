# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ForceDeleteOrderWizard(models.TransientModel):
    _name = 'custom.pos.order.force.delete.wizard'
    _description = 'Force Delete POS Order Wizard'

    order_ids = fields.Many2many('pos.order', string='Orders to Delete')
    order_names = fields.Char(string='Order Names', compute='_compute_order_names')
    count = fields.Integer(string='Count', compute='_compute_order_names')

    @api.depends('order_ids')
    def _compute_order_names(self):
        for rec in self:
            if rec.order_ids:
                names = rec.order_ids.mapped('name')
                rec.count = len(rec.order_ids)
                rec.order_names = ", ".join(names)
            else:
                rec.count = 0
                rec.order_names = ""

    def action_confirm_force_delete(self):
        self.ensure_one()
        if not self.order_ids:
            return

        self.order_ids.sudo().with_context(force_delete=True).unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Deleted'),
                'message': _('POS Order(s) force deleted successfully.'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'pos.order',
                    'view_mode': 'list,form',
                    'views': [(False, 'list'), (False, 'form')],
                }
            }
        }
