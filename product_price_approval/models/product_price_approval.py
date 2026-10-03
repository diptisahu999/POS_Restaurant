from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProductPriceApproval(models.Model):
    _name = 'product.price.approval'
    _description = 'Product Price Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    product_tmpl_id = fields.Many2one('product.template', string='Product', required=True, readonly=True)
    requester_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, required=True, readonly=True)
    old_price = fields.Float(string='Current Price', required=True, readonly=True)
    new_price = fields.Float(string='Proposed Price', required=True, readonly=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='pending', tracking=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('product.price.approval') or _('New')
        return super().create(vals_list)

    def action_approve(self):
        self.ensure_one()
        if not self.env.user.has_group('product_price_approval.group_price_approval_manager'):
            raise UserError(_("Only Price Approval Managers can approve requests."))
        
        self.product_tmpl_id.with_context(bypass_price_approval=True).list_price = self.new_price
        self.state = 'approved'
        self.message_post(body=_("Price change approved and applied. New price is %s") % self.new_price)
        
        # Notify requester
        self.env['bus.bus']._sendone(
            self.requester_id.partner_id,
            'simple_notification',
            {
                'type': 'success',
                'title': _('Price Approved'),
                'message': _('Your price change request for %s has been approved.') % self.product_tmpl_id.name,
                'sticky': False,
            }
        )

    def action_reject(self):
        self.ensure_one()
        if not self.env.user.has_group('product_price_approval.group_price_approval_manager'):
            raise UserError(_("Only Price Approval Managers can reject requests."))
            
        self.state = 'rejected'
        self.message_post(body=_("Price change request was rejected."))
        
        # Notify requester
        self.env['bus.bus']._sendone(
            self.requester_id.partner_id,
            'simple_notification',
            {
                'type': 'danger',
                'title': _('Price Rejected'),
                'message': _('Your price change request for %s was rejected.') % self.product_tmpl_id.name,
                'sticky': False,
            }
        )
