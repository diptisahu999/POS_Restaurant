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
        help='Network IP address OR full URL of the printer.\n'
             'Examples:\n'
             '  IP:  192.168.1.232\n'
             '  IP+Port:  192.168.1.232:9100\n'
             '  Cloudflare:  https://abc-xyz.trycloudflare.com/print\n'
             '  Local Agent:  http://localhost:5000/print'
    )
    printer_name = fields.Char(
        string='Printer Name / Station',
        help='Name of the printer or station (e.g. Kitchen, Bar, Grill, Bakery)'
    )

    def _is_http_url(self):
        """Return True if printer_url is an HTTP/HTTPS URL (not a raw IP)."""
        self.ensure_one()
        raw = (self.printer_url or '').strip()
        return raw.startswith('http://') or raw.startswith('https://')

    def parse_printer_ip_port(self):
        """Extract IP and Port from printer_url field (only for raw IP entries)."""
        self.ensure_one()
        raw = (self.printer_url or '').strip()
        if not raw:
            return None, None
        if raw.startswith('http://') or raw.startswith('https://'):
            cleaned = re.sub(r'^https?://', '', raw).split('/')[0].strip()
            match = re.match(r'^([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})(?::([0-9]+))?$', cleaned)
            if match:
                ip = match.group(1)
                port = int(match.group(2)) if match.group(2) else 9100
                return ip, port
            return None, None
        cleaned = raw.split('/')[0].strip()
        match = re.search(r'^([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})(?::([0-9]+))?', cleaned)
        if match:
            ip = match.group(1)
            port = int(match.group(2)) if match.group(2) else 9100
            return ip, port
        return None, None

    def action_test_printer(self):
        """Test the configured printer - supports both IP (TCP) and URL (HTTP) modes."""
        self.ensure_one()
        raw = (self.printer_url or '').strip()
        if not raw:
            raise UserError(
                "Please enter a Printer IP or URL first!\n\n"
                "Examples:\n"
                "  IP address:  192.168.1.232\n"
                "  Cloudflare:  https://abc-xyz.trycloudflare.com/print"
            )
        if self._is_http_url():
            return self._test_via_http_url(raw)
        ip, port = self.parse_printer_ip_port()
        if not ip:
            raise UserError(
                "Invalid printer address!\n\n"
                "Please enter either:\n"
                "  An IP address: 192.168.1.232\n"
                "  A full URL:    https://abc-xyz.trycloudflare.com/print"
            )
        return self._test_via_tcp(ip, port)

    def _test_via_http_url(self, url):
        """Test printer via HTTP POST to a print agent URL (Cloudflare / localhost)."""
        import urllib.request
        import json as json_lib

        test_url = url.rstrip('/')
        if not test_url.endswith('/print'):
            test_url = test_url + '/print'

        now_str = fields.Datetime.context_timestamp(self, fields.Datetime.now()).strftime('%d-%m-%Y %I:%M %p')
        payload = {
            "category": self.name or "TEST",
            "station": self.printer_name or self.name or "TEST",
            "round": "TEST PRINT",
            "table": "Test Table",
            "order": "TEST-001",
            "time": now_str,
            "items": [
                {"qty": 1, "name": "Test Item - KOT Print OK", "note": ""},
                {"qty": 1, "name": "Category: " + (self.name or ""), "note": ""},
            ],
        }
        data = json_lib.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            test_url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                resp.read()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Test Print Sent!',
                    'message': 'KOT test ticket sent to print agent at: ' + test_url,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(
                "Could not reach print agent at:\n" + test_url + "\n\n"
                "Error: " + str(e) + "\n\n"
                "Tips:\n"
                "  Make sure START_AGENT.bat is running\n"
                "  Make sure Cloudflare tunnel is active\n"
                "  URL should end with /print"
            )

    def _test_via_tcp(self, ip, port):
        """Test printer via direct TCP socket (for raw IP addresses)."""
        PAGE_WIDTH = 48
        DIVIDER = "=" * PAGE_WIDTH

        now_str = fields.Datetime.context_timestamp(self, fields.Datetime.now()).strftime('%d-%m-%Y %I:%M %p')
        lines = [
            "\r\n",
            DIVIDER + "\r\n",
            "        KITCHEN ORDER TICKET\r\n",
            "          *** TEST PRINT ***\r\n",
            DIVIDER + "\r\n",
            "Category : " + (self.name or "") + "\r\n",
            "Station  : " + (self.printer_name or self.name or "") + "\r\n",
            "Printer  : " + str(ip) + ":" + str(port) + "\r\n",
            "Time     : " + now_str + "\r\n",
            DIVIDER + "\r\n",
            "     STATUS: CONNECTED & OK!\r\n",
            "\r\n\r\n\r\n",
        ]
        payload = "".join(lines).encode('ascii', errors='replace')

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
                    'message': 'KOT test ticket sent to printer at ' + str(ip) + ':' + str(port),
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
            raise UserError(
                "Could not connect to printer at " + str(ip) + ":" + str(port) + "\n\n"
                "Error: " + str(e) + "\n\n"
                "Tip: Ensure the printer is ON and reachable on the network."
            )
