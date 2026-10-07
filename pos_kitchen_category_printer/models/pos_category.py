# pyrefly: ignore [missing-import]
import socket
import time
import re
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PosCategory(models.Model):
    _inherit = 'pos.category'

    printer_url = fields.Char(
        string='Printer IP / URL',
        help='Network IP address or URL of the TVS/ESC-POS printer for this category (e.g., 192.168.1.232 or 192.168.1.232:9100)'
    )
    printer_name = fields.Char(
        string='Printer Name / Station',
        help='Name of the printer or station (e.g. TVS RP3200 Kitchen, Bar, Grill, Bakery)'
    )

    def parse_printer_ip_port(self):
        """Extract IP and Port from printer_url field."""
        self.ensure_one()
        raw = (self.printer_url or '').strip()
        if not raw:
            return None, None
        cleaned = re.sub(r'^https?:\/\/', '', raw).split('/')[0].strip()
        match = re.search(r'^([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})(?::([0-9]+))?', cleaned)
        if match:
            ip = match.group(1)
            port = int(match.group(2)) if match.group(2) else 9100
            return ip, port
        return None, None

    def action_test_printer(self):
        """Test direct ESC/POS print to the configured TVS RP 3200 printer IP."""
        self.ensure_one()
        ip, port = self.parse_printer_ip_port()
        if not ip:
            raise UserError("Please enter a valid Printer IP Address (e.g. 192.168.1.232)!")

        ESC_INIT = b'\x1b\x40'
        ESC_ALIGN_CENTER = b'\x1b\x61\x01'
        ESC_ALIGN_LEFT = b'\x1b\x61\x00'
        FEED_AND_CUT = b'\r\n\r\n\r\n\r\n\x1d\x56\x00'

        now_str = fields.Datetime.context_timestamp(self, fields.Datetime.now()).strftime('%d-%m-%Y %I:%M %p')
        test_msg = (
            "================================\r\n"
            "   TVS RP 3200 LITE TEST PRINT  \r\n"
            "================================\r\n"
            f"Category: {self.name}\r\n"
            f"Station:  {self.printer_name or self.name}\r\n"
            f"Printer:  {ip}:{port}\r\n"
            f"Time:     {now_str}\r\n"
            "--------------------------------\r\n"
            "STATUS: CONNECTED & PRINTING OK!\r\n"
            "================================\r\n"
        )
        payload = ESC_INIT + ESC_ALIGN_LEFT + test_msg.encode('ascii', errors='replace') + FEED_AND_CUT

        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(4.0)
            sock.connect((ip, port))
            sock.sendall(payload)
            time.sleep(0.3)
            try:
                sock.shutdown(socket.SHUT_WR)
            except Exception:
                pass
            sock.close()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Test Print Sent!',
                    'message': f'Test receipt successfully sent to TVS RP 3200 at {ip}:{port}!',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
            raise UserError(f"Could not connect to printer at {ip}:{port}!\n\nError: {e}\n\nTip: Ensure the printer is powered ON and reachable on the network.")
