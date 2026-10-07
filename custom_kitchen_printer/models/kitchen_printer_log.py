# -*- coding: utf-8 -*-
import logging
# pyrefly: ignore [missing-import]
from odoo import models, fields, api
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PosKitchenPrinterLog(models.Model):
    _name = 'pos.kitchen.printer.log'
    _description = 'Kitchen Printer Ticket Log'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Ticket Title', required=True)
    printer_id = fields.Many2one(
        'pos.printer', 
        string='Kitchen Printer', 
        required=True, 
        index=True,
        group_expand='_read_group_printer_ids'
    )
    printer_name = fields.Char(string='Printer Name', related='printer_id.name', store=True)
    order_id = fields.Many2one('pos.order', string='Order', ondelete='cascade', index=True)

    @api.model
    def _read_group_printer_ids(self, printers, domain):
        """Dynamically return all kitchen network printers so their columns always appear on the kanban board."""
        all_printers = self.env['pos.printer'].search([('printer_type', '=', 'network_tcp')])
        if not all_printers:
            all_printers = self.env['pos.printer'].search([])
        return all_printers
    order_number = fields.Char(string='Order Number')
    order_ref = fields.Char(string='Order Reference')
    table_number = fields.Char(string='Table Number')
    floor_name = fields.Char(string='Floor')
    table_name = fields.Char(string='Table', default='Counter')
    status = fields.Selection([
        ('printed', 'Printed'),
        ('failed', 'Failed'),
    ], string='Status', default='printed')
    error_message = fields.Text(string='Error')
    ticket_text = fields.Text(string='Raw Ticket Text')
    ticket_html = fields.Html(string='Ticket Slip Preview', sanitize=False)
    item_count = fields.Integer(string='Items Count', default=0)

    def action_reprint(self):
        for rec in self:
            if not rec.printer_id:
                raise UserError("No printer is assigned to this ticket log!")
            if not rec.printer_id.network_printer_ip:
                raise UserError("The printer has no IP address configured!")

            ok, err = rec.printer_id._send_escpos_data(
                rec.printer_id.network_printer_ip,
                rec.printer_id.network_printer_port,
                rec.ticket_text or ''
            )
            if ok:
                rec.write({'status': 'printed', 'error_message': False})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Reprint Successful!',
                        'message': f'Ticket sent to {rec.printer_id.name} ({rec.printer_id.network_printer_ip})',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                rec.write({'status': 'failed', 'error_message': err})
                raise UserError(f"Reprint failed: {err}")
