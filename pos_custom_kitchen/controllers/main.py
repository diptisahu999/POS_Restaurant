# pyrefly: ignore [missing-import]
from odoo import http
from odoo.http import request

class PosKitchenController(http.Controller):

    @http.route('/pos_kitchen/toggle_round_ready', type='json', auth='user', methods=['POST'])
    def toggle_round_ready(self, round_id, **kw):
        round_rec = request.env['pos.kitchen.round'].browse(int(round_id))
        if round_rec.exists():
            round_rec.is_ready = not round_rec.is_ready
            round_rec.order_id._compute_kitchen_order_lines_summary()
            return {
                'success': True,
                'is_ready': round_rec.is_ready,
            }
        return {'success': False, 'error': 'Round not found'}
