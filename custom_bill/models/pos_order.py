# -*- coding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    nc_reason = fields.Char(
        string='No Charge (NC) Reason',
        help='Reason recorded when paying with No Charge (NC)'
    )
    kot_numbers = fields.Char(
        string='KOT Numbers',
        compute='_compute_kot_numbers',
        store=False,
        help='KOT sequence numbers for this order (e.g. #01, #02)'
    )

    @api.depends('kitchen_round_ids', 'kitchen_round_ids.sequence', 'kitchen_round_ids.round_type', 'lines', 'lines.is_sent_to_kitchen')
    def _compute_kot_numbers(self):
        for order in self:
            badges = []
            if hasattr(order, 'kitchen_round_ids') and order.kitchen_round_ids:
                reorder_idx = 0
                rounds = order.kitchen_round_ids.sorted(key=lambda r: (r.sequence, r.id))
                first_round = rounds[:1]
                for r in rounds:
                    if hasattr(r, 'round_type') and r.round_type == 'cancel':
                        continue
                    is_first = (first_round and r.id == first_round.id) or (r.sequence == 0 and getattr(r, 'round_type', '') == 'order')
                    if is_first:
                        badges.append("#01")
                    else:
                        reorder_idx += 1
                        badges.append(f"#{reorder_idx + 1:02d}")
            elif any(getattr(l, 'is_sent_to_kitchen', False) for l in order.lines):
                seqs = set()
                for l in order.lines:
                    if getattr(l, 'is_sent_to_kitchen', False):
                        seq = getattr(l, 'kitchen_round_seq', 0) or 0
                        seqs.add(seq)
                badges = [f"#{s + 1:02d}" for s in sorted(seqs)]

            if not badges and order.id and 'pos.kitchen.printer.log' in self.env:
                try:
                    import re
                    logs = self.env['pos.kitchen.printer.log'].sudo().search([('order_id', '=', order.id)], order='id asc')
                    for log in logs:
                        if 'CANCEL' in (log.name or ''):
                            continue
                        m = re.search(r'#(\d+)', log.name or '')
                        if m:
                            badge = f"#{int(m.group(1)):02d}"
                            if badge not in badges:
                                badges.append(badge)
                except Exception:
                    pass

            if not badges and getattr(order, 'is_sent_to_kitchen', False):
                badges.append("#01")

            unique_badges = []
            for b in badges:
                if b not in unique_badges:
                    unique_badges.append(b)
            order.kot_numbers = ", ".join(unique_badges) if unique_badges else ""

    @api.model
    def action_print_kitchen_order(self, order_uuid, round_id=None):
        res = super().action_print_kitchen_order(order_uuid, round_id=round_id) if hasattr(super(), 'action_print_kitchen_order') else {'success': True}
        order = self.search([('uuid', '=', order_uuid)], limit=1)
        if order:
            order._compute_kot_numbers()
            if isinstance(res, dict):
                res['kot_numbers'] = order.kot_numbers
        return res

    @api.model
    def _load_pos_data_fields(self, config):
        res = super()._load_pos_data_fields(config)
        # In Odoo 19, PosLoadMixin._load_pos_data_fields returns [] by default for pos.order,
        # which signals records.read([], load=False) to load all fields (including partner_id).
        # Returning a non-empty list restricts read() to only those fields, dropping partner_id.
        if res and 'kot_numbers' not in res:
            res.append('kot_numbers')
        return res

    @api.model
    def _process_order(self, order, existing_order):
        order_id = super()._process_order(order, existing_order)
        if order.get('nc_reason'):
            pos_order = self.browse(order_id)
            if pos_order.exists() and pos_order.nc_reason != order['nc_reason']:
                pos_order.write({'nc_reason': order['nc_reason']})
        return order_id

    def action_print_bill(self):
        """Action button on pos.order to print/download the thermal bill PDF."""
        self.ensure_one()
        if hasattr(self, 'bill_printed'):
            try:
                self.write({'bill_printed': True})
            except Exception:
                pass
        return self.env.ref('custom_bill.action_report_pos_order_bill').report_action(self)

    def _get_bill_number_formatted(self):
        self.ensure_one()
        ref = self.pos_reference or self.name or ""
        import re
        m = re.search(r'(\d+)$', ref)
        if m:
            return f"ARC{m.group(1).zfill(6)}"
        if self.tracking_number:
            return f"ARC{str(self.tracking_number).zfill(6)}"
        return f"ARC{str(self.id).zfill(6)}"

    def _get_order_number_formatted(self):
        self.ensure_one()
        num = self.tracking_number or (str(self.sequence_number) if self.sequence_number else '')
        if not num and self.pos_reference:
            parts = self.pos_reference.split('-')
            num = parts[-1] if len(parts) > 1 else self.pos_reference
        if not num:
            num = str(self.name or self.id)
        import re
        num = re.sub(r'^#+', '', str(num).strip())
        return f"#{num}" if num else ""

    def _get_bill_date_formatted(self):
        self.ensure_one()
        import pytz
        tz_name = self.env.context.get('tz') or self.user_id.tz or self.env.user.tz or 'Asia/Kolkata'
        try:
            user_tz = pytz.timezone(tz_name)
        except Exception:
            user_tz = pytz.timezone('Asia/Kolkata')
        dt = self.date_order or fields.Datetime.now()
        local_dt = pytz.utc.localize(dt).astimezone(user_tz) if dt.tzinfo is None else dt.astimezone(user_tz)
        return local_dt.strftime('%d/%m/%y %I:%M:%S %p').lower()

    def _get_table_number_formatted(self):
        self.ensure_one()
        if self.table_id:
            val = str(self.table_id.table_number) if self.table_id.table_number is not False else (self.table_id.name or '')
            if val.isdigit():
                return f"T-{val.zfill(2)}"
            return val
        if hasattr(self, 'table_stand_number') and self.table_stand_number:
            val = str(self.table_stand_number)
            if val.isdigit():
                return f"T-{val.zfill(2)}"
            return val
        return "COUNTER"

    def _get_amount_in_words(self):
        self.ensure_one()
        num = self.amount_total
        if not num or num <= 0:
            return "RS Zero Only."
        n = abs(float(num))
        int_part = int(n)
        dec_part = int(round((n - int_part) * 100))

        a = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
             "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
        b = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

        def convert_group(val):
            s = ""
            if val >= 100:
                s += a[val // 100] + " Hundred "
                val %= 100
            if val >= 20:
                s += b[val // 10] + (" " + a[val % 10] if val % 10 != 0 else "")
            elif val > 0:
                s += a[val]
            return s.strip()

        words = ""
        rem = int_part
        crore = rem // 10000000
        rem %= 10000000
        lakh = rem // 100000
        rem %= 100000
        thousand = rem // 1000
        rem %= 1000
        hundreds = rem

        if crore > 0: words += convert_group(crore) + " Crore "
        if lakh > 0: words += convert_group(lakh) + " Lakh "
        if thousand > 0: words += convert_group(thousand) + " Thousand "
        if hundreds > 0: words += convert_group(hundreds)

        words = words.strip() or "Zero"
        res = f"RS {words}"
        if dec_part > 0:
            res += f" and {convert_group(dec_part)} Paise"
        return f"{res} Only."

    def _get_bill_data(self):
        self.ensure_one()
        lines_data = []
        subtotal = 0.0
        discount = 0.0

        for l in self.lines:
            if self.config_id.module_pos_discount and l.product_id == self.config_id.discount_product_id:
                discount += abs(l.price_subtotal_incl)
                continue
            if l.price_unit < 0:
                discount += abs(l.price_subtotal_incl)
                continue

            qty_val = int(l.qty) if l.qty.is_integer() else l.qty
            rate_val = l.price_unit
            amt_val = l.price_subtotal

            if l.discount > 0:
                discount += (l.price_unit * l.qty * l.discount) / 100.0

            subtotal += amt_val

            lines_data.append({
                'name': l.full_product_name or (l.product_id and l.product_id.display_name) or 'Item',
                'qty': qty_val,
                'rate': f"{rate_val:.2f}",
                'amount': f"{amt_val:.2f}",
            })

        tax = self.amount_tax
        total = self.amount_total
        calculated = max(0.0, subtotal - discount) + tax
        round_off = round(total - calculated, 2)

        return {
            'lines': lines_data,
            'subtotal': subtotal,
            'discount': discount,
            'discount_label': 'Discount',
            'tax': tax,
            'round_off': round_off,
            'total': total,
            'amount_in_words': self._get_amount_in_words(),
        }


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    nc_reason = fields.Char(
        string='NC Reason',
        help='Reason recorded for No Charge (NC) payment'
    )
