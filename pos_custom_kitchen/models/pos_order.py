from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    kitchen_state = fields.Selection([
        ('pending', 'Waiting'),
        ('preparing', 'Preparing'),
        ('ready_to_serve', 'Ready to Serve'),
        ('done', 'Served')
    ], string='Kitchen Status', default='pending', tracking=True)

    kitchen_remark = fields.Text(string='Kitchen Remark')

    kitchen_order_lines_display = fields.Html(
        string='Kitchen Order Lines',
        compute='_compute_kitchen_order_lines_display'
    )

    @api.depends('lines', 'lines.product_id', 'lines.qty', 'lines.customer_note', 'lines.note', 'kitchen_remark')
    def _compute_kitchen_order_lines_display(self):
        for order in self:
            html_parts = []
            for line in order.lines:
                if line.product_id.type == 'service':
                    continue
                qty = int(line.qty) if line.qty == int(line.qty) else line.qty
                prod_name = line.product_id.display_name or line.full_product_name or 'Item'
                line_html = f'<div style="font-size: 15px; font-weight: 600; color: #212529; margin-top: 4px;">{qty}x {prod_name}</div>'
                
                # Line level note/remark if present
                line_note = getattr(line, 'customer_note', None) or getattr(line, 'note', None) or ''
                if line_note and str(line_note).strip():
                    line_html += f'<div style="color: #dc3545; font-style: italic; font-weight: 600; font-size: 13px; margin-left: 8px;">⚡ Remark: {str(line_note).strip()}</div>'
                
                html_parts.append(line_html)

            # Order level kitchen remark
            if order.kitchen_remark and str(order.kitchen_remark).strip():
                html_parts.append(f'<div style="color: #dc3545; font-style: italic; font-weight: 600; font-size: 13px; margin-top: 4px;">⚡ Remark: {str(order.kitchen_remark).strip()}</div>')
            
            order.kitchen_order_lines_display = "".join(html_parts)

    @api.model
    def _order_fields(self, ui_order):
        fields_dict = super()._order_fields(ui_order)
        if ui_order.get('kitchen_remark'):
            fields_dict['kitchen_remark'] = ui_order['kitchen_remark']
        return fields_dict

    def action_start_preparing(self):
        for order in self:
            order.kitchen_state = 'preparing'

    def action_pos_order_paid(self):
        for order in self:
            if order.kitchen_state != 'done' and any(line.product_id.type != 'service' for line in order.lines):
                from odoo.exceptions import UserError
                raise UserError("You cannot accept payment! The food must be served to the customer first.")
        return super().action_pos_order_paid()

    def action_ready_to_serve(self):
        for order in self:
            order.kitchen_state = 'ready_to_serve'

    def action_mark_done(self):
        for order in self:
            order.kitchen_state = 'done'

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            # When an order comes from the POS, automatically put it in 'pending' state
            if not order.kitchen_state:
                order.kitchen_state = 'pending'
        return orders

