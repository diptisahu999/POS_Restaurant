# -*- coding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_upi_id = fields.Char(
        related='pos_config_id.upi_id',
        readonly=False,
        string='Restaurant UPI ID / VPA'
    )
    pos_show_upi_qr_on_bill = fields.Boolean(
        related='pos_config_id.show_upi_qr_on_bill',
        readonly=False,
        string='Show UPI QR Code on Bill'
    )
