# -*- coding: utf-8 -*-
import socket
import time
import logging
# pyrefly: ignore [missing-import]
from odoo import models, fields, api
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PosPrinter(models.Model):
    _inherit = 'pos.printer'

    printer_type = fields.Selection(
        selection_add=[('network_tcp', 'Direct Network Printer (TVS / ESC-POS / TCP)')],
        ondelete={'network_tcp': 'set default'}
    )
    network_printer_ip = fields.Char(
        string='Printer IP Address',
        help='Enter the local IP address of your TVS printer (e.g. 192.168.1.101)'
    )
    network_printer_port = fields.Integer(
        string='Port',
        default=9100,
        help='Port for thermal ESC/POS network printers (default is 9100)'
    )
    ticket_log_ids = fields.One2many(
        'pos.kitchen.printer.log',
        'printer_id',
        string='Kitchen Tickets & Orders'
    )
    order_count = fields.Integer(
        string='Total Orders',
        compute='_compute_printer_order_count'
    )

    @api.depends('ticket_log_ids')
    def _compute_printer_order_count(self):
        for printer in self:
            printer.order_count = len(printer.ticket_log_ids)

    @api.depends('name', 'network_printer_ip', 'printer_type')
    def _compute_display_name(self):
        for printer in self:
            if printer.printer_type == 'network_tcp' and printer.network_printer_ip:
                printer.display_name = f"{printer.name} [{printer.network_printer_ip}]"
            else:
                printer.display_name = printer.name or "Printer"

    def action_view_printer_orders(self):
        self.ensure_one()
        return {
            'name': f'Orders - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'pos.kitchen.printer.log',
            'view_mode': 'kanban,list,form',
            'domain': [('printer_id', '=', self.id)],
            'context': {'default_printer_id': self.id},
        }

    def action_test_network_print(self):
        self.ensure_one()
        if not self.network_printer_ip:
            raise UserError("Please enter the Printer IP Address first!")

        now_dt = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        date_str = now_dt.strftime('%d-%m-%Y')
        time_str = now_dt.strftime('%I:%M %p')
        test_text = (
            "================================\r\n"
            f"     {self.name.upper()} TEST\r\n"
            "================================\r\n"
            f"IP: {self.network_printer_ip}:{self.network_printer_port}\r\n"
            f"Date: {date_str}\r\n"
            f"Time: {time_str}\r\n"
            "Status: CONNECTED SUCCESSFULLY!\r\n"
            "TVS RP 3200 LITE / ESC-POS OK\r\n"
            "================================\r\n"
        )
        success, error = self._send_escpos_data(self.network_printer_ip, self.network_printer_port, test_text)
        if not success:
            raise UserError(
                f"Could not connect to {self.network_printer_ip}:{self.network_printer_port}!\n\n"
                f"Details: {error}\n\n"
                "Tip: Ensure the printer is ON, LAN cable is connected, and your server can reach this IP."
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Test Print Successful!',
                'message': f'Test receipt printed on {self.name} ({self.network_printer_ip})',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def _send_escpos_data(self, ip, port, text):
        """Sends clean ESC/POS commands to network thermal printer on TCP port."""
        ESC_INIT = b'\x1b\x40'            # Initialize printer
        ESC_ALIGN_LEFT = b'\x1b\x61\x00'   # Align left
        TXT_BOLD_ON = b'\x1b\x45\x01'     # Bold text
        TXT_BOLD_OFF = b'\x1b\x45\x00'    # Normal text
        FEED_LINES = b'\r\n\r\n\r\n\r\n'  # Feed paper
        PAPER_CUT = b'\x1d\x56\x00'       # Full cut command

        # Format text with standard CRLF line endings
        # Replace non-standard unicode symbols that break thermal printer firmware
        safe_text = text.replace('\r\n', '\n').replace('\r', '\n')
        safe_text = safe_text.replace('↳', '->').replace('–', '-').replace('—', '-')
        formatted_lines = [line + '\r\n' for line in safe_text.split('\n')]
        clean_text = "".join(formatted_lines)

        payload = ESC_INIT + ESC_ALIGN_LEFT + clean_text.encode('ascii', errors='replace') + FEED_LINES + PAPER_CUT

        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((ip, int(port or 9100)))
            sock.sendall(payload)
            # Give printer micro-controller time to ingest the packet
            time.sleep(0.3)
            try:
                sock.shutdown(socket.SHUT_WR)
            except Exception:
                pass
            sock.close()
            return True, None
        except Exception as e:
            _logger.error("Failed to print to printer %s:%s - %s", ip, port, e)
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
            return False, str(e)
