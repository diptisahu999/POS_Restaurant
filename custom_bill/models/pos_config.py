    # -*- coding: utf-8 -*-
import base64
# pyrefly: ignore [missing-import]
from odoo import api, fields, models

# Clean SVG icons encoded in base64 for payment buttons
UPI_ICON_SVG = base64.b64encode(b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <rect width="100" height="100" rx="20" fill="#097939"/>
  <path d="M25 35 L45 65 L40 75 L20 45 Z" fill="#ffffff"/>
  <path d="M45 25 L75 25 L55 75 L25 75 Z" fill="#f37021"/>
  <text x="50" y="90" font-family="Arial,sans-serif" font-size="16" font-weight="bold" fill="#ffffff" text-anchor="middle">UPI</text>
</svg>''').decode('ascii')

GC_ICON_SVG = base64.b64encode(b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <rect width="100" height="100" rx="20" fill="#6A1B9A"/>
  <rect x="20" y="28" width="60" height="44" rx="8" fill="#ffffff" stroke="#e0e0e0" stroke-width="2"/>
  <rect x="20" y="38" width="60" height="10" fill="#8E24AA"/>
  <circle cx="34" cy="58" r="4" fill="#FFD700"/>
  <text x="62" y="62" font-family="Arial,sans-serif" font-size="12" font-weight="bold" fill="#4A148C">GIFT</text>
</svg>''').decode('ascii')


def _setup_custom_bill_payment_methods(env):
    """Creates default payment methods and assigns them to POS configs."""
    company = env.company
    bank_journal = env['account.journal'].search([
        ('type', '=', 'bank'),
        ('company_id', '=', company.id)
    ], limit=1)
    if not bank_journal:
        bank_journal = env['account.journal'].search([('type', '=', 'bank')], limit=1)

    PaymentMethod = env['pos.payment.method']

    # 1. UPI / Online
    upi_pm = PaymentMethod.search([
        ('name', '=', 'UPI / Online'),
        ('company_id', '=', company.id)
    ], limit=1)
    if not upi_pm:
        upi_pm = PaymentMethod.create({
            'name': 'UPI / Online',
            'journal_id': bank_journal.id if bank_journal else False,
            'company_id': company.id,
            'payment_method_type': 'none',
            'image': UPI_ICON_SVG,
        })

    # 2. Gift Card (GC)
    gc_pm = PaymentMethod.search([
        ('name', '=', 'Gift Card (GC)'),
        ('company_id', '=', company.id)
    ], limit=1)
    if not gc_pm:
        gc_pm = PaymentMethod.create({
            'name': 'Gift Card (GC)',
            'journal_id': bank_journal.id if bank_journal else False,
            'company_id': company.id,
            'payment_method_type': 'none',
            'image': GC_ICON_SVG,
        })

    # Link both to all active pos configs
    pos_configs = env['pos.config'].search([])
    for config in pos_configs:
        commands = []
        if upi_pm.id not in config.payment_method_ids.ids:
            commands.append((4, upi_pm.id))
        if gc_pm.id not in config.payment_method_ids.ids:
            commands.append((4, gc_pm.id))
        if commands:
            config.with_context(bypass_payment_method_ids_forbidden_change=True).write({
                'payment_method_ids': commands
            })


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _is_write_forbidden(self, fields):
        # Whitelist 'image' so UI icon can be updated without session restart
        return super()._is_write_forbidden(fields - {'image'})


class PosConfig(models.Model):
    _inherit = 'pos.config'

    upi_id = fields.Char(
        string='UPI ID / VPA',
        default='merchant@upi',
        help='UPI Virtual Payment Address for customer QR payments (e.g. restaurant@upi, 9876543210@paytm)'
    )
    show_upi_qr_on_bill = fields.Boolean(
        string='Show UPI QR Code on Bill',
        default=True,
        help='Display a dynamic UPI QR Code on restaurant bills and receipts for instant scanning and payment'
    )

