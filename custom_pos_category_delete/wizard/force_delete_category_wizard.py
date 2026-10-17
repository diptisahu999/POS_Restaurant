# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from ..models.cleanup_utils import force_clean_pos_category_references

class ForceDeleteCategoryWizard(models.TransientModel):
    _name = 'custom.pos.category.force.delete.wizard'
    _description = 'Force Delete POS Category Wizard'

    category_ids = fields.Many2many('pos.category', string='Categories to Delete')
    category_names = fields.Char(string='Category Names', compute='_compute_category_names')
    count = fields.Integer(string='Count', compute='_compute_category_names')

    @api.depends('category_ids')
    def _compute_category_names(self):
        for rec in self:
            if rec.category_ids:
                names = rec.category_ids.mapped('display_name')
                rec.count = len(rec.category_ids)
                rec.category_names = ", ".join(names)
            else:
                rec.count = 0
                rec.category_names = ""

    def action_confirm_force_delete(self):
        self.ensure_one()
        if not self.category_ids:
            return

        cat_ids = self.category_ids.ids

        # Clean all foreign key and M2M references
        force_clean_pos_category_references(self.env, category_ids=cat_ids)

        # Force delete categories bypassing open session checks
        self.category_ids.with_context(force_delete=True).unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Deleted'),
                'message': _('POS Category/Categories force deleted successfully.'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'pos.category',
                    'view_mode': 'list,kanban,form',
                    'views': [(False, 'list'), (False, 'kanban'), (False, 'form')],
                }
            }
        }
