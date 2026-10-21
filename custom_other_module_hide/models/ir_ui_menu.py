# -*- coding: utf-8 -*-
from odoo import models, api


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        visible_ids = super()._visible_menu_ids(debug=debug)
        if self.env.is_superuser():
            return visible_ids

        user = self.env.user
        to_hide_roots = []
        if getattr(user, 'hide_discuss', False):
            to_hide_roots.append('mail.menu_root_discuss')
        if getattr(user, 'hide_todo', False):
            to_hide_roots.append('project_todo.menu_todo_todos')
        if getattr(user, 'hide_employees', False):
            to_hide_roots.append('hr.menu_hr_root')
        if getattr(user, 'hide_link_tracker', False):
            to_hide_roots.append('utm.menu_link_tracker_root')

        if to_hide_roots:
            menus_to_remove = set()
            for xmlid in to_hide_roots:
                root = self.env.ref(xmlid, raise_if_not_found=False)
                if root:
                    children = self.search([('id', 'child_of', root.id)])
                    menus_to_remove.update(children.ids)
            if menus_to_remove:
                visible_ids = frozenset(visible_ids - menus_to_remove)

        return visible_ids
