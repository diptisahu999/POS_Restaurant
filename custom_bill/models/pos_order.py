# -*- coding: utf-8 -*-
import re
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
    custom_bill_number = fields.Char(
        string='Bill Number',
        compute='_compute_custom_bill_number',
        store=True,
        index=True,
        help='Dynamic outlet-based bill number (e.g. ARC00001, DDC00001, TA001, IRD0001)'
    )

    @api.depends('pos_reference', 'tracking_number', 'sequence_number', 'name', 'config_id', 'config_id.name', 'config_id.bill_prefix', 'table_id')
    def _compute_custom_bill_number(self):
        for order in self:
            config = order.config_id
            config_name = (config.name or '').strip().lower()
            custom_prefix = (getattr(config, 'bill_prefix', '') or '').strip().upper()

            table_name = ''
            floor_name = ''
            if order.table_id:
                table_name = (str(getattr(order.table_id, 'table_number', '')) or str(getattr(order.table_id, 'name', ''))).strip().lower()
                if hasattr(order.table_id, 'floor_id') and order.table_id.floor_id:
                    floor_name = (order.table_id.floor_id.name or '').strip().lower()

            is_take_away = (
                'take away' in config_name or 'takeaway' in config_name or config_name == 'ta'
                or 'take away' in floor_name or 'takeaway' in floor_name
                or table_name.startswith('ta') or 'takeaway' in table_name or 'take away' in table_name
            )
            is_ird = (
                'in room' in config_name or 'room dining' in config_name or 'room service' in config_name or config_name == 'ird'
                or 'room' in floor_name or 'ird' in floor_name
                or table_name.startswith('room') or table_name.startswith('ird')
            )

            if is_take_away:
                prefix = 'TA'
                digits = 3
            elif is_ird:
                prefix = 'IRD'
                digits = 4
            elif custom_prefix:
                prefix = custom_prefix
                digits = 3 if len(prefix) <= 2 else (4 if prefix == 'IRD' else 5)
            else:
                # Dynamically derive prefix from outlet name
                gen_func = getattr(config, '_generate_bill_prefix', None)
                if callable(gen_func):
                    prefix = gen_func(config.name)
                else:
                    words = [w for w in re.findall(r'[A-Za-z0-9]+', config.name or '') if w]
                    if len(words) >= 2:
                        prefix = ''.join(w[0].upper() for w in words)[:5]
                    elif len(words) == 1:
                        w = words[0].upper()
                        prefix = w[:3] if len(w) >= 3 else w.ljust(3, 'X')
                    else:
                        prefix = 'POS'
                digits = 3 if len(prefix) <= 2 else (4 if prefix == 'IRD' else 5)

            # Extract numeric sequence from pos_reference, tracking_number, or name
            ref = order.pos_reference or order.name or ''
            m = re.search(r'(\d+)$', ref)
            num = 1
            if m:
                try:
                    num = int(m.group(1))
                except ValueError:
                    num = 1
            elif order.tracking_number:
                try:
                    num = int(order.tracking_number)
                except ValueError:
                    num = 1
            elif order.sequence_number:
                num = order.sequence_number

            order.custom_bill_number = f"{prefix}{str(num).zfill(digits)}"

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        origins = []
        for order in self:
            bill_ref = order.custom_bill_number or order.pos_reference
            outlet = order.config_id.name or ''
            if bill_ref and outlet:
                origins.append(f"{outlet} - {bill_ref}")
            elif bill_ref:
                origins.append(bill_ref)
        if origins:
            vals['invoice_origin'] = ', '.join(origins)
            if len(self) == 1 and self.custom_bill_number:
                vals['ref'] = f"{self.config_id.name} - {self.custom_bill_number}" if self.config_id.name else self.custom_bill_number
        return vals

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
        if res:
            for f in ['kot_numbers', 'custom_bill_number', 'nc_reason']:
                if f not in res:
                    res.append(f)
        return res

    @api.model
    def _process_order(self, order, existing_order):
        order_id = super()._process_order(order, existing_order)
        updates = {}
        if order.get('nc_reason'):
            updates['nc_reason'] = order['nc_reason']
        if order.get('custom_bill_number'):
            updates['custom_bill_number'] = order['custom_bill_number']

        if updates:
            pos_order = self.browse(order_id)
            if pos_order.exists():
                pos_order.write(updates)
        return order_id


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    nc_reason = fields.Char(
        string='NC Reason',
        help='Reason recorded for No Charge (NC) payment'
    )
