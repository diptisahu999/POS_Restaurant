# -*- coding: utf-8 -*-
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
        store=True,
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


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    nc_reason = fields.Char(
        string='NC Reason',
        help='Reason recorded for No Charge (NC) payment'
    )
