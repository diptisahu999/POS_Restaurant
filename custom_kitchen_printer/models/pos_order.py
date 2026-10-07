# -*- coding: utf-8 -*-
import logging
# pyrefly: ignore [missing-import]
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    last_kitchen_print_date = fields.Datetime(string="Last Kitchen Print Date")

    def _print_to_kitchen_network_printers(self, items_to_print=None, is_reorder=False):
        """Sends order items to their designated ESC-POS network printers and logs them."""
        printed_printers = []
        errors = []

        for order in self:
            now = fields.Datetime.now()
            if order.last_kitchen_print_date and not items_to_print:
                diff_seconds = (now - order.last_kitchen_print_date).total_seconds()
                if diff_seconds < 4:
                    _logger.info("Order %s was already printed %.1fs ago, skipping duplicate.", order.name, diff_seconds)
                    recent_logs = self.env['pos.kitchen.printer.log'].search([
                        ('order_id', '=', order.id),
                        ('status', '=', 'printed')
                    ], limit=5)
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
                printer_cat_ids = set()
                if printer.product_categories_ids:
                    printer_cat_ids = set(self.env['pos.category'].search([('id', 'child_of', printer.product_categories_ids.ids)]).ids)
                matching_items = []

                if items_to_print:
                    for itm in items_to_print:
                        item_cat_ids = set(itm.get('pos_category_ids', []))
                        if not item_cat_ids and itm.get('pos_category_id'):
                            item_cat_ids = {itm['pos_category_id']}
                        if not printer_cat_ids or (item_cat_ids & printer_cat_ids):
                            matching_items.append(itm)
                else:
                    for line in order.lines:
                        if line.product_id and order.config_id.module_pos_discount and line.product_id == order.config_id.discount_product_id:
                            continue
                        prod = line.product_id
                        prod_cats = set()
                        if prod:
                            if hasattr(prod, 'pos_categ_ids') and prod.pos_categ_ids:
                                prod_cats.update(prod.pos_categ_ids.ids)
                            if hasattr(prod, 'product_tmpl_id') and prod.product_tmpl_id and hasattr(prod.product_tmpl_id, 'pos_categ_ids') and prod.product_tmpl_id.pos_categ_ids:
                                prod_cats.update(prod.product_tmpl_id.pos_categ_ids.ids)
                        if not printer_cat_ids or (prod_cats & printer_cat_ids):
                            matching_items.append({
                                'product_name': line.full_product_name or prod.display_name,
                                'qty': int(line.qty) if line.qty.is_integer() else line.qty,
                                'note': line.customer_note or '',
                            })

                if not matching_items:
                    _logger.info("No matching items for printer %s", printer.name)
                    continue

                table_num = ""
                floor_name = ""
                table_name = "Counter"
                if order.table_id:
                    table_num = str(order.table_id.table_number) if order.table_id.table_number is not False else ""
                    floor_name = order.table_id.floor_id.name if order.table_id.floor_id else ""
                    if table_num and floor_name:
                        table_name = f"Table {table_num} ({floor_name})"
                    elif table_num:
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

                dt_obj = fields.Datetime.context_timestamp(order, order.date_order or fields.Datetime.now())
                date_str = dt_obj.strftime('%d-%m-%Y')
                time_str = dt_obj.strftime('%I:%M %p')
                title_badge = f"{printer.name.upper()} - REORDER" if is_reorder else f"{printer.name.upper()}"

                # 1. Plain text formatted for ESC/POS thermal printer
                ticket_lines = [
                    "================================",
                    f"       {title_badge}",
                    f"Order No: #{order_num}",
                ]
                if table_num:
                    if floor_name:
                        ticket_lines.append(f"Table No: Table {table_num} ({floor_name})")
                    else:
                        ticket_lines.append(f"Table No: Table {table_num}")
                else:
                    ticket_lines.append(f"Table:    {table_name}")

                ticket_lines.extend([
                    f"Ref:      {order.pos_reference or order.name}",
                    f"Date:     {date_str}",
                    f"Time:     {time_str}",
                    "--------------------------------",
                ])
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
                    floor_badge = f"<span style='font-size: 13px; color: #555; font-weight: normal; margin-left: 4px;'>({floor_name})</span>" if floor_name else ""
                    table_html_badge = f"""
                        <div style="font-size: 15px; font-weight: bold; color: #198754; margin-bottom: 4px;">
                            Table No: <span style="background-color: #ffc107; color: #000; padding: 2px 7px; border-radius: 4px; font-weight: 700;">Table {table_num}</span>{floor_badge}
                        </div>
                    """
                else:
                    table_html_badge = f"""
                        <div style="font-size: 14px; margin-bottom: 4px;"><strong>Table:</strong> <span class="badge text-bg-warning">{table_name}</span></div>
                    """

                # 2. Rich HTML preview formatted for the Kitchen Printer Kanban/UI Log
                ticket_html = f"""
                    <div style="font-family: monospace; background: #fff; padding: 12px; border: 1px dashed #bbb; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);">
                        <div style="text-align: center; font-weight: bold; font-size: 16px; border-bottom: 2px dashed #444; padding-bottom: 6px; margin-bottom: 8px; color: #0d6efd;">
                            {title_badge}
                        </div>
                        <div style="font-size: 16px; font-weight: bold; color: #d63384; margin-bottom: 4px;">
                            Order No: #{order_num}
                        </div>
                        {table_html_badge}
                        <div style="font-size: 12px; color: #666; margin-bottom: 2px;"><strong>Ref:</strong> {order.pos_reference or order.name}</div>
                        <div style="font-size: 12px; color: #666; margin-bottom: 2px;"><strong>Date:</strong> {date_str}</div>
                        <div style="font-size: 12px; color: #666; margin-bottom: 8px;"><strong>Time:</strong> {time_str}</div>
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
                        'name': f"Order #{order_num} ({table_name})",
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
    def action_print_kitchen_order(self, order_uuid):
        """Called directly from frontend popup when 'Confirm & Send to Kitchen' is clicked."""
        order = self.search([('uuid', '=', order_uuid)], limit=1)
        if order:
            _logger.info("action_print_kitchen_order triggered for order %s (UUID: %s)", order.name, order_uuid)
            return order._print_to_kitchen_network_printers(is_reorder=False)
        _logger.warning("action_print_kitchen_order could not find order with UUID %s", order_uuid)
        return {'success': False, 'message': f'Order with UUID {order_uuid} not found on server'}

    def action_send_to_kitchen_printers(self):
        """Action button on pos.order to manually send/print to kitchen printers and create logs."""
        for order in self:
            order._print_to_kitchen_network_printers(is_reorder=False)
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

