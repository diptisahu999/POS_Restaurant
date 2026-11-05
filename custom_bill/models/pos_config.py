# -*- coding: utf-8 -*-
import base64
import re
# pyrefly: ignore [missing-import]
from odoo import api, fields, models

# Clean SVG icons encoded in base64 for payment buttons
UPI_ICON_SVG = base64.b64encode(b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <rect width="100" height="100" rx="20" fill="#097939"/>
  <path d="M25 35 L45 65 L40 75 L20 45 Z" fill="#ffffff"/>
  <path d="M45 25 L75 25 L55 75 L25 75 Z" fill="#f37021"/>
  <text x="50" y="90" font-family="Arial,sans-serif" font-size="16" font-weight="bold" fill="#ffffff" text-anchor="middle">UPI</text>
</svg>''').decode('ascii')

NC_ICON_SVG = base64.b64encode(b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <rect width="100" height="100" rx="20" fill="#D32F2F"/>
  <circle cx="50" cy="50" r="38" fill="none" stroke="#ffffff" stroke-width="4"/>
  <text x="50" y="58" font-family="Arial,sans-serif" font-size="30" font-weight="900" fill="#ffffff" text-anchor="middle">NC</text>
  <text x="50" y="80" font-family="Arial,sans-serif" font-size="10" font-weight="bold" fill="#ffffff" text-anchor="middle" letter-spacing="1">NO CHARGE</text>
</svg>''').decode('ascii')


def _generate_dynamic_bill_prefix(name):
    """Dynamically generates a bill prefix from the POS outlet name without hardcoding."""
    if not name:
        return 'POS'
    clean = name.strip()
    w_lower = clean.lower()
    if w_lower in ('take away', 'takeaway', 'takeout', 'parcel', 'to go'):
        return 'TA'
    if w_lower in ('in room dining', 'room dining', 'room service', 'ird'):
        return 'IRD'
    if w_lower in ('areca', 'arica'):
        return 'ARC'

    words = [w for w in re.findall(r'[A-Za-z0-9]+', clean) if w]
    if len(words) >= 2:
        return ''.join(w[0].upper() for w in words)[:5]
    elif len(words) == 1:
        w = words[0].upper()
        return w[:3] if len(w) >= 3 else w.ljust(3, 'X')
    return 'POS'


def _setup_custom_bill_payment_methods(env):
    """Creates/updates default payment methods and assigns them to POS configs."""
    company = env.company
    bank_journal = env['account.journal'].search([
        ('type', '=', 'bank'),
        ('company_id', '=', company.id)
    ], limit=1)
    if not bank_journal:
        bank_journal = env['account.journal'].search([('type', '=', 'bank')], limit=1)

    cash_journal = env['account.journal'].search([
        ('type', '=', 'cash'),
        ('company_id', '=', company.id)
    ], limit=1)
    if not cash_journal:
        cash_journal = env['account.journal'].search([('type', '=', 'cash')], limit=1)

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
    elif not upi_pm.image:
        upi_pm.write({'image': UPI_ICON_SVG})

    # 2. No Charge (NC)
    nc_pm = PaymentMethod.search([
        ('name', '=', 'No Charge (NC)'),
        ('company_id', '=', company.id)
    ], limit=1)

    if not nc_pm:
        nc_pm = PaymentMethod.create({
            'name': 'No Charge (NC)',
            'journal_id': bank_journal.id if bank_journal else False,
            'company_id': company.id,
            'payment_method_type': 'none',
            'image': NC_ICON_SVG,
        })
    elif not nc_pm.image:
        nc_pm.write({'image': NC_ICON_SVG})

    # Link methods to all active pos configs and ensure each config has a dedicated Cash payment method
    pos_configs = env['pos.config'].search([])
    for config in pos_configs:
        commands = []
        if upi_pm and upi_pm.id not in config.payment_method_ids.ids:
            commands.append((4, upi_pm.id))
        if nc_pm and nc_pm.id not in config.payment_method_ids.ids:
            commands.append((4, nc_pm.id))

        # Ensure dedicated Cash payment method for this shop (Odoo requires 1 Cash PM per POS shop)
        has_cash = config.payment_method_ids.filtered('is_cash_count')
        if not has_cash and cash_journal:
            dedicated_cash = PaymentMethod.search([
                ('company_id', '=', company.id),
                ('is_cash_count', '=', True),
                ('config_ids', '=', False)
            ], limit=1)
            if not dedicated_cash:
                dedicated_cash = PaymentMethod.create({
                    'name': 'Cash',
                    'journal_id': cash_journal.id,
                    'company_id': company.id,
                    'is_cash_count': True,
                    'config_ids': [(4, config.id)],
                })
            else:
                commands.append((4, dedicated_cash.id))

        if commands:
            config.with_context(bypass_payment_method_ids_forbidden_change=True).write({
                'payment_method_ids': commands
            })

        # Set dynamic default bill_prefix if unset
        if not config.bill_prefix and config.name:
            config.write({'bill_prefix': _generate_dynamic_bill_prefix(config.name)})

        env.cr.execute("UPDATE pos_config SET last_data_change = NOW(), write_date = NOW() WHERE id = %s;", (config.id,))


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _is_write_forbidden(self, fields):
        # Whitelist 'image' and 'name' so UI icon and NC name can be updated without session restart
        return super()._is_write_forbidden(fields - {'image', 'name'})


class PosConfig(models.Model):
    _inherit = 'pos.config'

    bill_prefix = fields.Char(
        string='Bill Prefix',
        help='Prefix for bill numbering (e.g. ARC for Areca, DDC for Daily Delight Cafe, TA for Take Away, IRD for In Room Dining, or automatically generated)'
    )
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

    @api.model
    def _generate_bill_prefix(self, name):
        return _generate_dynamic_bill_prefix(name)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('bill_prefix') and vals.get('name'):
                vals['bill_prefix'] = self._generate_bill_prefix(vals['name'])
        records = super().create(vals_list)
        for record in records:
            if not record.payment_method_ids.filtered('is_cash_count'):
                cash_j = self.env['account.journal'].search([
                    ('type', '=', 'cash'),
                    ('company_id', '=', record.company_id.id)
                ], limit=1)
                if cash_j:
                    self.env['pos.payment.method'].create({
                        'name': 'Cash',
                        'journal_id': cash_j.id,
                        'company_id': record.company_id.id,
                        'is_cash_count': True,
                        'config_ids': [(4, record.id)],
                    })
        return records

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super()._load_pos_data_fields(config)
        if fields_list:
            for f in ['bill_prefix', 'upi_id', 'show_upi_qr_on_bill']:
                if f not in fields_list:
                    fields_list.append(f)
        return fields_list
