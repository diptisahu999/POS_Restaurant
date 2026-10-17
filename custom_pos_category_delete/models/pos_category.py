# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError
from .cleanup_utils import force_clean_pos_category_references

class PosCategory(models.Model):
    _inherit = 'pos.category'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_session_open(self):
        is_allowed = (
            self.env.context.get('force_delete')
            or self.env.is_superuser
            or self.env.user.has_group('custom_pos_category_delete.group_allow_force_delete_pos_category')
            or self.env.user.has_group('base.group_system')
        )
        if is_allowed:
            return
        return super()._unlink_except_session_open()

    def action_force_delete(self):
        """Open the Force Delete confirmation wizard"""
        if not (self.env.user.has_group('custom_pos_category_delete.group_allow_force_delete_pos_category') or self.env.is_superuser):
            raise UserError(_("You do not have permission to force delete POS categories. Please enable 'Allow Force Delete POS Categories' in your user settings."))

        return {
            'name': _('Force Delete POS Category'),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.pos.category.force.delete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_category_ids': [(6, 0, self.ids)],
            },
        }

    def unlink(self):
        is_allowed = (
            self.env.context.get('force_delete')
            or self.env.is_superuser
            or self.env.user.has_group('custom_pos_category_delete.group_allow_force_delete_pos_category')
            or self.env.user.has_group('base.group_system')
        )
        if is_allowed:
            force_clean_pos_category_references(self.env, category_ids=self.ids)
            return super(PosCategory, self.with_context(force_delete=True)).unlink()

        return super().unlink()
