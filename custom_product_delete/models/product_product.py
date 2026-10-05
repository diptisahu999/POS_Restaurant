# pyrefly: ignore [missing-import]
from odoo import models, api, _
from odoo.exceptions import UserError
from .cleanup_utils import force_clean_product_references

class ProductProduct(models.Model):
    _inherit = 'product.product'

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
                'default_product_ids': [(6, 0, self.ids)],
            },
        }

    def unlink(self):
        if self.env.context.get('force_delete'):
            variant_ids = self.ids

            # Clean all foreign key references (POS order lines, combos, quants, moves, etc.)
            force_clean_product_references(self.env, variant_ids=variant_ids)

            # Bypass POS session check
            self.sudo().write({'available_in_pos': False})

        return super().unlink()
