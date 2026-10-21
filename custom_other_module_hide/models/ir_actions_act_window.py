# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import AccessError


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    def _get_action_dict(self):
        self.ensure_one()
        if not self.env.is_superuser():
            user = self.env.user
            if getattr(user, 'hide_todo', False):
                todo_act = self.env.ref('project_todo.action_todo_todos', raise_if_not_found=False)
                if self.path == 'to-do' or (todo_act and self.id == todo_act.id):
                    raise AccessError(_("You do not have permission to access To-do."))

            if getattr(user, 'hide_employees', False):
                if self.path == 'employees' or self == self.env.ref('hr.open_view_employee_list_my', raise_if_not_found=False):
                    raise AccessError(_("You do not have permission to access Employees."))

            if getattr(user, 'hide_link_tracker', False):
                if self.path == 'link_tracker' or self == self.env.ref('link_tracker.link_tracker_action', raise_if_not_found=False):
                    raise AccessError(_("You do not have permission to access Link Tracker."))

        return super()._get_action_dict()
