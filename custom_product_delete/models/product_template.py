# pyrefly: ignore [missing-import]
from odoo import models, api, _
from odoo.exceptions import UserError
from .cleanup_utils import force_clean_product_references

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_force_delete(self):
        """Open the Force Delete confirmation wizard"""
        if not self.env.user.has_group('custom_product_delete.group_allow_force_delete_product'):
            raise UserError(_("You do not have permission to force delete products. Please enable 'Allow Force Delete Products' in your user settings."))

        return {
            'name': _('Force Delete Product'),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.product.force.delete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_tmpl_ids': [(6, 0, self.ids)],
            },
        }

    def unlink(self):
        is_allowed = (
            self.env.context.get('force_delete')
            or self.env.is_superuser
            or self.env.user.has_group('custom_product_delete.group_allow_force_delete_product')
            or self.env.user.has_group('base.group_system')
        )
        if is_allowed:
            variants = self.mapped('product_variant_ids')
            variant_ids = variants.ids if variants else []
            tmpl_ids = self.ids

            # Clean all foreign key references (Stock moves, Journal items, POS order lines, quants, etc.)
            force_clean_product_references(self.env, variant_ids=variant_ids, tmpl_ids=tmpl_ids)

            # Bypass POS session check
            self.sudo().write({'available_in_pos': False})
            if variants:
                variants.sudo().write({'available_in_pos': False})

        return super().unlink()


