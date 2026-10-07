# pyrefly: ignore [missing-import]
from odoo import models, fields

class PosCategory(models.Model):
    _inherit = 'pos.category'

    printer_url = fields.Char(
        string='Printer URL / IP',
        help='Network URL or IP of the KOT printer for this category (e.g., http://192.168.1.201:8069 or http://192.168.1.201:5000/print)'
    )
    printer_name = fields.Char(
        string='Printer Name / Station',
        help='Name of the printer or station (e.g. TVS RP3200 Kitchen, Bar, Grill, Bakery)'
    )
