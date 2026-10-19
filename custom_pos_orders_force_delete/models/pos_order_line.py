# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_order_state(self):
        """
        Override Odoo's built-in guard that blocks deletion of order lines
        linked to orders in paid/done state.
        When force_delete context is set we skip the check entirely.
        """
        if self.env.context.get('force_delete'):
            return
        # Check permission-based bypass
        if (
            self.env.user.has_group('custom_pos_orders_force_delete.group_allow_force_delete_pos_orders')
            or self.env.is_superuser
            or self.env.user.has_group('base.group_system')
        ):
            return
        # Fall back to original restriction
        if self.filtered(lambda x: x.order_id.state not in ['draft', 'cancel']):
            raise UserError(_(
                "You can only unlink PoS order lines that are related to orders in new or cancelled state."
            ))
