# pyrefly: ignore [missing-import]
from odoo import models, api, _
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_modify_paid_invoice(self):
        for move in self:
            if not self.env.user.has_group('custom_invoice_modify.group_modify_paid_invoices'):
                raise UserError(_("You do not have access to modify paid invoices."))

            # Remove reconciled payments first if any exist
            if any(line.reconciled for line in move.line_ids):
                move.line_ids.filtered('reconciled').remove_move_reconcile()

            move.button_draft()
