# pyrefly: ignore [missing-import]
from odoo import models, fields, _
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, vals):
        if 'list_price' in vals and not self.env.context.get('bypass_price_approval'):
            if not self.env.user.has_group('product_price_approval.group_price_approval_manager'):
                # Check if price actually changed
                for record in self:
                    if record.list_price != vals['list_price']:
                        raise UserError(_(
                            "You do not have permission to change the sales price directly.\n"
                            "Please use the 'Request Price Approval' button to propose a new price."
                        ))
        return super().write(vals)

class RequestPriceApprovalWizard(models.TransientModel):
    _name = 'product.price.approval.wizard'
    _description = 'Request Price Approval Wizard'

    product_tmpl_id = fields.Many2one('product.template', string='Product', required=True)
    old_price = fields.Float(string='Current Price', related='product_tmpl_id.list_price', readonly=True)
    new_price = fields.Float(string='Proposed Price', required=True)

    def action_request_approval(self):
        self.ensure_one()
        if self.new_price <= 0:
            raise UserError(_("Proposed price must be greater than 0."))
        
        # Create approval request
        approval = self.env['product.price.approval'].create({
            'product_tmpl_id': self.product_tmpl_id.id,
            'old_price': self.old_price,
            'new_price': self.new_price,
        })

        # Notify managers
        manager_group = self.env.ref('product_price_approval.group_price_approval_manager')
        managers = manager_group.all_user_ids
        for manager in managers:
            self.env['bus.bus']._sendone(
                manager.partner_id,
                'simple_notification',
                {
                    'type': 'warning',
                    'title': _('New Price Approval Request'),
                    'message': _('%s has requested a price change for %s (%.2f -> %.2f).') % (
                        self.env.user.name, self.product_tmpl_id.name, self.old_price, self.new_price
                    ),
                    'sticky': True,
                }
            )

        # Notify requester
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'type': 'success',
                'title': _('Approval Requested'),
                'message': _('Your price change request has been submitted for approval.'),
                'sticky': False,
            }
        )

        return {'type': 'ir.actions.act_window_close'}
