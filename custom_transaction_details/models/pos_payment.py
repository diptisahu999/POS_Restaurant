# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    order_number = fields.Char(
        string='Order Number',
        compute='_compute_order_number',
        store=True,
        help='POS Order Number (e.g. ticket reference or sequence).'
    )
    bill_number = fields.Char(
        string='Bill No',
        compute='_compute_bill_number',
        store=True,
        help='Formatted bill number or invoice reference connected to this transaction.'
    )
    pos_config_id = fields.Many2one(
        'pos.config',
        string='Point of Sale',
        related='pos_order_id.config_id',
        store=True,
        readonly=True,
        help='Point of Sale outlet where this transaction occurred.'
    )
    table_id = fields.Many2one(
        'restaurant.table',
        string='Table',
        related='pos_order_id.table_id',
        store=True,
        readonly=True,
    )
    table_label = fields.Char(
        string='Table No',
        compute='_compute_table_label',
        help='Formatted table designation.'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='pos_order_id.partner_id',
        store=True,
        readonly=True,
    )
    cashier_name = fields.Char(
        string='Cashier / Steward',
        compute='_compute_cashier_name',
        help='Cashier or salesperson who processed this order.'
    )
    order_amount_untaxed = fields.Monetary(
        string='Product Value (Excl Tax)',
        compute='_compute_order_totals',
        currency_field='currency_id',
        help='Net value of products/food items excluding taxes.'
    )
    order_amount_tax = fields.Monetary(
        string='Taxes on Order',
        compute='_compute_order_totals',
        currency_field='currency_id',
        help='Total tax amount on connected order.'
    )
    order_amount_total = fields.Monetary(
        string='Total Products Value (Incl Tax)',
        related='pos_order_id.amount_total',
        currency_field='currency_id',
        readonly=True,
        help='Total value of products including taxes.'
    )
    order_line_ids = fields.Many2many(
        'pos.order.line',
        string='Food Served / Ordered Items',
        compute='_compute_order_lines',
        help='Full breakdown of food and beverage items served on this order.'
    )
    food_served_summary = fields.Text(
        string='Food Served',
        compute='_compute_food_served_summary',
        help='Summary of items served corresponding to this transaction.'
    )
    is_split_payment = fields.Boolean(
        string='Is Split Payment',
        compute='_compute_split_details',
        store=True,
        help='Indicates whether this order was paid using multiple payment methods / split tenders.'
    )
    other_payment_ids = fields.Many2many(
        'pos.payment',
        compute='_compute_split_details',
        string='Other Payments on Order',
        help='Other payment transactions involved in settling this order.'
    )
    other_payments_display = fields.Char(
        string='Split Payment Details',
        compute='_compute_split_details',
        help='Readable breakdown of all other payments involved in this order.'
    )
    payment_ratio = fields.Float(
        string='Payment Share %',
        compute='_compute_split_details',
        help='Percentage of the total bill covered by this specific transaction (0.0 to 1.0).'
    )
    is_nc_payment = fields.Boolean(
        string='Is No Charge (NC)',
        compute='_compute_nc_details',
        store=True,
        help='Indicates whether this is a No Charge / Complimentary settlement.'
    )
    nc_reason = fields.Char(
        string='NC / Complimentary Reason',
        compute='_compute_nc_details',
        store=True,
        readonly=False,
        help='Operational reason why this bill was settled under No Charge (NC).'
    )

    @api.depends('pos_order_id', 'pos_order_id.pos_reference', 'pos_order_id.tracking_number', 'pos_order_id.sequence_number')
    def _compute_order_number(self):
        for payment in self:
            order = payment.pos_order_id
            if order:
                num = order.pos_reference or (f"Order #{order.sequence_number}" if order.sequence_number else f"Order #{order.id}")
                payment.order_number = num
            else:
                payment.order_number = '-'

    @api.depends('pos_order_id', 'pos_order_id.name', 'pos_order_id.pos_reference', 'pos_order_id.tracking_number')
    def _compute_bill_number(self):
        for payment in self:
            order = payment.pos_order_id
            if order:
                bill = order.name if (order.name and order.name != '/') else (
                    order.pos_reference or order.tracking_number or f"Order #{order.id}"
                )
                payment.bill_number = bill
            else:
                payment.bill_number = '-'

    @api.depends('pos_order_id', 'pos_order_id.amount_tax', 'pos_order_id.amount_total')
    def _compute_order_totals(self):
        for payment in self:
            order = payment.pos_order_id
            if order:
                payment.order_amount_tax = order.amount_tax
                payment.order_amount_untaxed = order.amount_total - order.amount_tax
            else:
                payment.order_amount_tax = 0.0
                payment.order_amount_untaxed = 0.0

    @api.depends('table_id', 'pos_order_id.table_id')
    def _compute_table_label(self):
        for payment in self:
            tbl = payment.table_id or (payment.pos_order_id.table_id if payment.pos_order_id else False)
            if tbl:
                payment.table_label = f"Table {tbl.table_number}" if getattr(tbl, 'table_number', False) else (tbl.name or '-')
            else:
                payment.table_label = '-'

    @api.depends('pos_order_id', 'pos_order_id.user_id')
    def _compute_cashier_name(self):
        for payment in self:
            order = payment.pos_order_id
            payment.cashier_name = order.user_id.name if order and order.user_id else '-'

    @api.depends('pos_order_id', 'pos_order_id.lines')
    def _compute_order_lines(self):
        for payment in self:
            payment.order_line_ids = payment.pos_order_id.lines if payment.pos_order_id else False

    @api.depends('pos_order_id', 'pos_order_id.lines', 'pos_order_id.lines.product_id', 'pos_order_id.lines.qty')
    def _compute_food_served_summary(self):
        for payment in self:
            order = payment.pos_order_id
            if order and order.lines:
                items = []
                for line in order.lines:
                    qty_val = int(line.qty) if line.qty.is_integer() else f"{line.qty:.1f}"
                    items.append(f"{qty_val}x {line.product_id.display_name}")
                payment.food_served_summary = ", ".join(items)
            else:
                payment.food_served_summary = "No items recorded"

    @api.depends('pos_order_id', 'pos_order_id.payment_ids', 'pos_order_id.payment_ids.amount', 'amount')
    def _compute_split_details(self):
        for payment in self:
            order = payment.pos_order_id
            if order and order.payment_ids:
                all_payments = order.payment_ids
                other_payments = all_payments - payment
                total_order = order.amount_total or sum(all_payments.mapped('amount')) or 1.0
                ratio = (payment.amount / total_order) if total_order else 1.0
                payment.payment_ratio = ratio

                if len(all_payments) > 1:
                    payment.is_split_payment = True
                    payment.other_payment_ids = other_payments
                    sym = payment.currency_id.symbol or '₹'
                    other_parts = []
                    for op in other_payments:
                        other_parts.append(f"{op.payment_method_id.name or 'Other'}: {sym} {op.amount:,.2f}")
                    payment.other_payments_display = f"Split ({(ratio * 100.0):.1f}%) | Other Tenders: {', '.join(other_parts)}"
                else:
                    payment.is_split_payment = False
                    payment.other_payment_ids = False
                    payment.other_payments_display = f"Full Payment (100%)"
            else:
                payment.is_split_payment = False
                payment.other_payment_ids = False
                payment.other_payments_display = '-'
                payment.payment_ratio = 1.0

    @api.depends('payment_method_id', 'payment_method_id.name', 'pos_order_id')
    def _compute_nc_details(self):
        for payment in self:
            pm_name = payment.payment_method_id.name.lower() if payment.payment_method_id and payment.payment_method_id.name else ''
            is_nc = ('no charge' in pm_name or 'nc' in pm_name or 'complimentary' in pm_name)
            payment.is_nc_payment = is_nc

            # Preserve existing nc_reason or sync from order
            if not payment.nc_reason:
                order_nc = getattr(payment.pos_order_id, 'nc_reason', False) if payment.pos_order_id else False
                if order_nc:
                    payment.nc_reason = order_nc
                elif is_nc:
                    payment.nc_reason = 'Complimentary / No Charge'
