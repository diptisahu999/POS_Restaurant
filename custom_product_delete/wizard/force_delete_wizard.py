# pyrefly: ignore [missing-import]
from odoo import models, fields, api, _
from ..models.cleanup_utils import force_clean_product_references

class ForceDeleteWizard(models.TransientModel):
    _name = 'custom.product.force.delete.wizard'
    _description = 'Force Delete Product Wizard'

    product_tmpl_ids = fields.Many2many('product.template', string='Products to Delete')
    product_ids = fields.Many2many('product.product', string='Product Variants to Delete')
    product_names = fields.Char(string='Product Names', compute='_compute_product_names')
    count = fields.Integer(string='Count', compute='_compute_product_names')

    @api.depends('product_tmpl_ids', 'product_ids')
    def _compute_product_names(self):
        for rec in self:
            names = []
            if rec.product_tmpl_ids:
                names = rec.product_tmpl_ids.mapped('name')
                rec.count = len(rec.product_tmpl_ids)
            elif rec.product_ids:
                names = rec.product_ids.mapped('display_name')
                rec.count = len(rec.product_ids)
            else:
                rec.count = 0
            rec.product_names = ", ".join(names)

    def action_confirm_force_delete(self):
        self.ensure_one()
        all_variant_ids = []
        tmpl_ids = self.product_tmpl_ids.ids if self.product_tmpl_ids else []

        if self.product_tmpl_ids:
            all_variant_ids = self.product_tmpl_ids.mapped('product_variant_ids').ids
        elif self.product_ids:
            all_variant_ids = self.product_ids.ids

        # Clean all foreign key references (POS order lines, combo lines, quants, moves, etc.)
        force_clean_product_references(self.env, variant_ids=all_variant_ids, tmpl_ids=tmpl_ids)

        # Force delete product templates or variants
        if self.product_tmpl_ids:
            self.product_tmpl_ids.with_context(force_delete=True).unlink()
        elif self.product_ids:
            self.product_ids.with_context(force_delete=True).unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Deleted'),
                'message': _('Product(s) force deleted successfully.'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'product.template',
                    'view_mode': 'kanban,list,form',
                    'views': [(False, 'kanban'), (False, 'list'), (False, 'form')],
                }
            }
        }
