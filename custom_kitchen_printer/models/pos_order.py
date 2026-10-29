# -*- coding: utf-8 -*-
import logging
import pytz
# pyrefly: ignore [missing-import]
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    last_kitchen_print_date = fields.Datetime(string="Last Kitchen Print Date")

    def _print_to_kitchen_network_printers(self, items_to_print=None, is_reorder=False, round_title=None, kot_number=None):
        """Sends only the current round/newly reordered items to designated ESC-POS network printers and logs them."""
        printed_printers = []
        errors = []

        for order in self:
            current_is_reorder = is_reorder
            current_round_title = round_title or ""
            order_items_to_print = items_to_print
            latest_round = None
            current_kot_number = kot_number

            # When items_to_print is not explicitly provided, extract items strictly from the LATEST kitchen round
            if hasattr(order, 'kitchen_round_ids') and order.kitchen_round_ids:
                rounds = order.kitchen_round_ids.sorted(key=lambda r: (r.sequence, r.id))
                if rounds:
                    latest_round = rounds[-1]
                    first_round_id = rounds[0].id
                    is_round_reorder = not ((latest_round.id == first_round_id) or (latest_round.sequence == 0 and latest_round.round_type == 'order'))
                    current_is_reorder = current_is_reorder or is_round_reorder

                    if current_kot_number is None:
                        current_kot_number = rounds.ids.index(latest_round.id) + 1 if latest_round in rounds else len(rounds)

                    if is_round_reorder and not current_round_title:
                        reorders = [r for r in rounds if not ((r.id == first_round_id) or (r.sequence == 0 and r.round_type == 'order'))]
                        reorder_idx = reorders.index(latest_round) + 1 if latest_round in reorders else len(reorders)
                        current_round_title = f"REORDER {reorder_idx}"
                    elif not current_round_title:
                        current_round_title = "ORDER"

                    if order_items_to_print is None:
                        extracted = []
                        for rline in latest_round.line_ids:
                            if rline.qty <= 0:
                                continue
                            prod = rline.product_id
                            prod_cats = set()
                            if rline.pos_category_id:
                                prod_cats.add(rline.pos_category_id.id)
                            if prod:
                                if hasattr(prod, 'pos_categ_ids') and prod.pos_categ_ids:
                                    prod_cats.update(prod.pos_categ_ids.ids)
                                if hasattr(prod, 'product_tmpl_id') and prod.product_tmpl_id and hasattr(prod.product_tmpl_id, 'pos_categ_ids') and prod.product_tmpl_id.pos_categ_ids:
                                    prod_cats.update(prod.product_tmpl_id.pos_categ_ids.ids)
                            extracted.append({
                                'product_id': prod.id if prod else False,
                                'product_name': rline.product_name or (prod and prod.display_name) or 'Item',
                                'qty': int(rline.qty) if rline.qty.is_integer() else rline.qty,
                                'note': rline.note or '',
                                'pos_category_ids': list(prod_cats),
                                'pos_category_id': rline.pos_category_id.id if rline.pos_category_id else False,
                            })
                        order_items_to_print = extracted

            if current_kot_number is None:
                current_kot_number = 1

            # Fallback if no kitchen rounds exist (e.g. direct sale without kitchen rounds)
            if order_items_to_print is None:
                order_items_to_print = []
                for line in order.lines:
                    if line.product_id and order.config_id.module_pos_discount and line.product_id == order.config_id.discount_product_id:
                        continue
                    if current_is_reorder and hasattr(line, 'is_reorder') and not line.is_reorder:
                        continue
                    prod = line.product_id
                    prod_cats = set()
                    if prod:
                        if hasattr(prod, 'pos_categ_ids') and prod.pos_categ_ids:
                            prod_cats.update(prod.pos_categ_ids.ids)
                        if hasattr(prod, 'product_tmpl_id') and prod.product_tmpl_id and hasattr(prod.product_tmpl_id, 'pos_categ_ids') and prod.product_tmpl_id.pos_categ_ids:
                            prod_cats.update(prod.product_tmpl_id.pos_categ_ids.ids)
                    order_items_to_print.append({
                        'product_id': prod.id if prod else False,
                        'product_name': line.full_product_name or prod.display_name,
                        'qty': int(line.qty) if line.qty.is_integer() else line.qty,
                        'note': line.customer_note or '',
                        'pos_category_ids': list(prod_cats),
                    })

            now = fields.Datetime.now()
            if order.last_kitchen_print_date:
                diff_seconds = (now - order.last_kitchen_print_date).total_seconds()
                if diff_seconds < 3:
                    _logger.info("Order %s was printed %.1fs ago, checking for duplicate round.", order.name, diff_seconds)
                    recent_logs = self.env['pos.kitchen.printer.log'].search([
                        ('order_id', '=', order.id),
                        ('status', '=', 'printed')
                    ], limit=5, order='id desc')
                    # If this exact KOT number or round was already logged in the last 3s, skip duplicate
                    kot_match = f"KOT #{current_kot_number:02d}"
                    if recent_logs and any((kot_match in (l.name or '')) or (current_round_title and current_round_title in (l.name or '')) for l in recent_logs):
                        printers_list = [f"{l.printer_id.name} ({l.printer_id.network_printer_ip})" for l in recent_logs if l.printer_id]
                        return {'success': True, 'printers': printers_list or ['Kitchen Printer'], 'message': 'Printed successfully'}

            printers = self.env['pos.printer'].search([
                ('printer_type', '=', 'network_tcp'),
                ('network_printer_ip', '!=', False)
            ])
            if not printers:
                _logger.warning("No active network TCP printers found.")
                return {'success': False, 'message': 'No Network Printers configured with an IP address'}

            for printer in printers:
                printer_product_ids = set(printer.product_ids.ids)
                printer_cat_ids = set()
                if printer.product_categories_ids:
                    printer_cat_ids = set(self.env['pos.category'].search([('id', 'child_of', printer.product_categories_ids.ids)]).ids)
                matching_items = []

                for itm in order_items_to_print:
                    p_id = itm.get('product_id')
                    item_cat_ids = set(itm.get('pos_category_ids', []))
                    if not item_cat_ids and itm.get('pos_category_id'):
                        item_cat_ids = {itm['pos_category_id']}

                    # 1. Primary rule: match by specific mapped items / products
                    if printer_product_ids:
                        if p_id and p_id in printer_product_ids:
                            matching_items.append(itm)
                    # 2. Fallback rule: match by category if no items configured
                    elif printer_cat_ids:
                        if item_cat_ids & printer_cat_ids:
                            matching_items.append(itm)
                    # 3. Default: if neither items nor categories are configured, print all items
                    else:
                        matching_items.append(itm)

                if not matching_items:
                    _logger.info("No matching items for printer %s", printer.name)
                    continue

                table_num = ""
                floor_name = ""
                table_name = "Counter"
                if order.table_id:
                    table_num = str(order.table_id.table_number) if order.table_id.table_number is not False else ""
                    floor_name = order.table_id.floor_id.name if order.table_id.floor_id else ""
                    if table_num:
                        table_name = f"Table {table_num}"
                    else:
                        table_name = order.table_id.display_name or "Table"
                elif order.table_stand_number:
                    table_num = str(order.table_stand_number)
                    table_name = f"Table {table_num}"

                # Extract human-readable Order Number (tracking_number in POS)
                order_num = order.tracking_number or (str(order.sequence_number) if order.sequence_number else '')
                if not order_num and order.pos_reference:
                    parts = order.pos_reference.split('-')
                    order_num = parts[-1] if len(parts) > 1 else order.pos_reference
                if not order_num:
                    order_num = str(order.name or order.id)

                tz_name = (
                    order.env.context.get('tz')
                    or order.user_id.tz
                    or order.env.user.tz
                    or (order.session_id and order.session_id.user_id and order.session_id.user_id.tz)
                    or (order.company_id and order.company_id.partner_id and order.company_id.partner_id.tz)
                    or 'Asia/Kolkata'
                )
                try:
                    user_tz = pytz.timezone(tz_name)
                except Exception:
                    user_tz = pytz.timezone('Asia/Kolkata')

                # Use actual current print timestamp in the local timezone
                import datetime
                dt_obj = datetime.datetime.now(datetime.timezone.utc).astimezone(user_tz)
                date_str = dt_obj.strftime('%d-%m-%Y')
                time_str = dt_obj.strftime('%I:%M %p')

                kot_badge = f"#{current_kot_number:02d}"
                header_title = f"KOT - {printer.name.upper()}"

                # 1. Plain text formatted for ESC/POS thermal printer (32-character line width)
                kot_col = f"KOT NO:   {kot_badge}".ljust(19)
                order_col = f"ORDER: #{order_num}"
                kot_order_line = f"{kot_col}{order_col}"

                ticket_lines = [
                    "================================",
                    header_title.center(32),
                    "================================",
                    kot_order_line,
                    f"TABLE:    {table_name}",
                    f"TIME:     {time_str} ({date_str})",
                    f"REF:      {order.pos_reference or order.name}",
                    "--------------------------------",
                ]
                items_html_list = []
                for item in matching_items:
                    qty = item.get('qty', 1)
                    name = item.get('product_name', '')
                    ticket_lines.append(f"{qty}x  {name}")
                    note_html = ""
                    if item.get('note'):
                        ticket_lines.append(f"   -> Remark: {item['note']}")
                        note_html = f"<div style='color: #dc3545; font-size: 13px; font-weight: 600; margin-left: 12px; font-style: italic;'>↳ Remark: {item['note']}</div>"

                    items_html_list.append(f"""
                        <div style="margin-bottom: 6px;">
                            <span style="font-weight: 700; font-size: 15px; color: #111;">{qty}x {name}</span>
                            {note_html}
                        </div>
                    """)

                ticket_lines.append("================================")
                ticket_text = "\n".join(ticket_lines)

                # Table HTML preview
                if table_num:
                    table_html_badge = f"""
                        <div style="font-size: 14px; font-weight: bold; margin-bottom: 4px;">
                            <strong>TABLE:</strong> <span style="background-color: #ffc107; color: #000; padding: 2px 7px; border-radius: 4px; font-weight: 700;">Table {table_num}</span>
                        </div>
                    """
                else:
                    table_html_badge = f"""
                        <div style="font-size: 14px; margin-bottom: 4px;"><strong>TABLE:</strong> <span class="badge text-bg-warning">{table_name}</span></div>
                    """

                # 2. Rich HTML preview formatted for the Kitchen Printer Kanban/UI Log
                ticket_html = f"""
                    <div style="font-family: monospace; background: #fff; padding: 12px; border: 1px dashed #bbb; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); max-width: 320px;">
                        <div style="text-align: center; font-weight: bold; font-size: 16px; border-bottom: 2px dashed #444; padding-bottom: 6px; margin-bottom: 8px; color: #0d6efd;">
                            {header_title}
                        </div>
                        <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 14px; margin-bottom: 4px;">
                            <span style="color: #6f42c1;">KOT NO: {kot_badge}</span>
                            <span style="color: #d63384;">ORDER: #{order_num}</span>
                        </div>
                        {table_html_badge}
                        <div style="font-size: 12px; color: #333; margin-bottom: 2px;"><strong>TIME:</strong> {time_str} ({date_str})</div>
                        <div style="font-size: 12px; color: #666; margin-bottom: 6px;"><strong>REF:</strong> {order.pos_reference or order.name}</div>
                        <div style="border-top: 1px dashed #ccc; padding-top: 8px; margin-bottom: 8px;">
                            {''.join(items_html_list)}
                        </div>
                        <div style="border-top: 2px dashed #444; margin-top: 8px; text-align: center; font-size: 11px; color: #888; padding-top: 4px;">
                            IP: {printer.network_printer_ip}:{printer.network_printer_port}
                        </div>
                    </div>
                """

                # 3. Send to physical network printer
                _logger.info("Sending kitchen ticket to %s (%s:%s):\n%s", printer.name, printer.network_printer_ip, printer.network_printer_port, ticket_text)
                ok, err = printer._send_escpos_data(printer.network_printer_ip, printer.network_printer_port, ticket_text)

                if ok:
                    printed_printers.append(f"{printer.name} ({printer.network_printer_ip})")
                else:
                    errors.append(f"{printer.name}: {err}")

                # 4. Save to Kitchen Printer Log for UI verification
                try:
                    self.env['pos.kitchen.printer.log'].sudo().create({
                        'name': f"KOT {kot_badge} - Order #{order_num} ({table_name})",
                        'printer_id': printer.id,
                        'order_id': order.id,
                        'order_number': order_num,
                        'table_number': table_num,
                        'floor_name': floor_name,
                        'order_ref': order.pos_reference or order.name,
                        'table_name': table_name,
                        'status': 'printed' if ok else 'failed',
                        'error_message': err if not ok else False,
                        'ticket_text': ticket_text,
                        'ticket_html': ticket_html,
                        'item_count': len(matching_items),
                    })
                except Exception as log_err:
                    _logger.error("Failed to create pos.kitchen.printer.log: %s", log_err)

            if printed_printers:
                try:
                    order.write({'last_kitchen_print_date': fields.Datetime.now()})
                except Exception:
                    pass

        if errors and not printed_printers:
            return {'success': False, 'message': ', '.join(errors), 'printers': []}
        return {'success': True, 'printers': printed_printers, 'message': 'Printed successfully'}

    @api.model
    def action_print_kitchen_order(self, order_uuid, round_id=None):
        """Called directly from frontend popup when 'Confirm & Send to Kitchen' or 'Resend to Kitchen' is clicked."""
        order = self.search([('uuid', '=', order_uuid)], limit=1)
        if order:
            _logger.info("action_print_kitchen_order triggered for order %s (UUID: %s, round_id=%s)", order.name, order_uuid, round_id)
            if round_id and hasattr(order, 'kitchen_round_ids') and order.kitchen_round_ids:
                rounds = order.kitchen_round_ids.sorted(key=lambda r: (r.sequence, r.id))
                target_round = rounds.filtered(lambda r: str(r.id) == str(round_id) or str(r.sequence) == str(round_id))
                if target_round:
                    target_round = target_round[0]
                    first_round_id = rounds[0].id
                    is_reorder = not ((target_round.id == first_round_id) or (target_round.sequence == 0 and target_round.round_type == 'order'))
                    extracted = []
                    for rline in target_round.line_ids:
                        if rline.qty <= 0:
                            continue
                        prod = rline.product_id
                        prod_cats = set()
                        if rline.pos_category_id:
                            prod_cats.add(rline.pos_category_id.id)
                        if prod:
                            if hasattr(prod, 'pos_categ_ids') and prod.pos_categ_ids:
                                prod_cats.update(prod.pos_categ_ids.ids)
                            if hasattr(prod, 'product_tmpl_id') and prod.product_tmpl_id and hasattr(prod.product_tmpl_id, 'pos_categ_ids') and prod.product_tmpl_id.pos_categ_ids:
                                prod_cats.update(prod.product_tmpl_id.pos_categ_ids.ids)
                        extracted.append({
                            'product_id': prod.id if prod else False,
                            'product_name': rline.product_name or (prod and prod.display_name) or 'Item',
                            'qty': int(rline.qty) if rline.qty.is_integer() else rline.qty,
                            'note': rline.note or '',
                            'pos_category_ids': list(prod_cats),
                            'pos_category_id': rline.pos_category_id.id if rline.pos_category_id else False,
                        })
                    reorders = [r for r in rounds if not ((r.id == first_round_id) or (r.sequence == 0 and r.round_type == 'order'))]
                    reorder_idx = reorders.index(target_round) + 1 if target_round in reorders else target_round.sequence
                    title = f"REORDER {reorder_idx} (RESENT)" if is_reorder else "ORDER (RESENT)"
                    kot_num = rounds.ids.index(target_round.id) + 1 if target_round.id in rounds.ids else (target_round.sequence + 1 if target_round.round_type == 'reorder' else 1)
                    return order._print_to_kitchen_network_printers(
                        items_to_print=extracted,
                        is_reorder=is_reorder,
                        round_title=title,
                        kot_number=kot_num
                    )
            return order._print_to_kitchen_network_printers()
        _logger.warning("action_print_kitchen_order could not find order with UUID %s", order_uuid)
        return {'success': False, 'message': f'Order with UUID {order_uuid} not found on server'}

    def action_send_to_kitchen_printers(self):
        """Action button on pos.order to manually send/print to kitchen printers and create logs."""
        for order in self:
            order._print_to_kitchen_network_printers()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Kitchen Printing',
                'message': 'Order dispatched to designated kitchen printers!',
                'type': 'success',
                'sticky': False,
            }
        }

