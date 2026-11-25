# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta
import pytz
import base64
import io
import xlsxwriter

from odoo import api, fields, models, _


class PosTransactionWizard(models.TransientModel):
    _name = 'pos.transaction.wizard'
    _description = 'POS Transaction & Food Audit Wizard'

    date_preset = fields.Selection([
        ('today', 'Today'),
        ('yesterday', 'Yesterday'),
        ('this_week', 'This Week'),
        ('this_month', 'This Month'),
        ('custom', 'Custom Date Range'),
    ], string='Period Preset', default='today', required=True)

    start_date = fields.Datetime(string='Start Date', required=True, default=fields.Datetime.now)
    end_date = fields.Datetime(string='End Date', required=True, default=fields.Datetime.now)

    pos_config_ids = fields.Many2many(
        'pos.config',
        string='Point of Sale Outlets',
        help='Restrict audit to specific POS outlets (ARECA, Daily Delight Cafe, etc.).'
    )
    payment_method_ids = fields.Many2many(
        'pos.payment.method',
        string='Payment Methods',
        help='Restrict to specific transaction types (Cash, Card, UPI, No Charge, etc.).'
    )
    only_split_payments = fields.Boolean(
        string='Only Split / Multi-Tender Payments',
        default=False,
        help='Filter transactions where the order was paid using multiple payment methods.'
    )
    only_nc_payments = fields.Boolean(
        string='Only No Charge (NC) / Complimentary',
        default=False,
        help='Filter complimentary transactions that have an NC reason.'
    )

    @api.onchange('date_preset')
    def _onchange_date_preset(self):
        user_tz = pytz.timezone(self.env.user.tz or 'Asia/Kolkata')
        now_local = datetime.now(user_tz)
        today = now_local.date()

        if self.date_preset == 'today':
            s_local = user_tz.localize(datetime.combine(today, time.min))
            e_local = user_tz.localize(datetime.combine(today, time.max))
        elif self.date_preset == 'yesterday':
            yesterday = today - timedelta(days=1)
            s_local = user_tz.localize(datetime.combine(yesterday, time.min))
            e_local = user_tz.localize(datetime.combine(yesterday, time.max))
        elif self.date_preset == 'this_week':
            start_week = today - timedelta(days=today.weekday())
            s_local = user_tz.localize(datetime.combine(start_week, time.min))
            e_local = user_tz.localize(datetime.combine(today, time.max))
        elif self.date_preset == 'this_month':
            start_month = today.replace(day=1)
            s_local = user_tz.localize(datetime.combine(start_month, time.min))
            e_local = user_tz.localize(datetime.combine(today, time.max))
        else:
            return

        self.start_date = s_local.astimezone(pytz.utc).replace(tzinfo=None)
        self.end_date = e_local.astimezone(pytz.utc).replace(tzinfo=None)

    def _get_payments_domain(self):
        self.ensure_one()
        domain = [
            ('payment_date', '>=', self.start_date),
            ('payment_date', '<=', self.end_date),
        ]
        if self.pos_config_ids:
            domain.append(('pos_config_id', 'in', self.pos_config_ids.ids))
        if self.payment_method_ids:
            domain.append(('payment_method_id', 'in', self.payment_method_ids.ids))
        if self.only_split_payments:
            domain.append(('is_split_payment', '=', True))
        if self.only_nc_payments:
            domain.append(('is_nc_payment', '=', True))
        return domain

    def action_view_transactions(self):
        self.ensure_one()
        domain = self._get_payments_domain()
        action = self.env.ref('custom_transaction_details.action_pos_transaction_details').read()[0]
        action['domain'] = domain
        action['context'] = {
            'search_default_group_by_payment_method': 1,
            'search_default_group_by_pos_config': 1,
        }
        return action

    def action_export_excel(self):
        self.ensure_one()
        domain = self._get_payments_domain()
        payments = self.env['pos.payment'].search(domain, order='payment_date desc, id desc')

        user_tz = pytz.timezone(self.env.user.tz or 'Asia/Kolkata')
        s_utc = pytz.utc.localize(self.start_date) if self.start_date.tzinfo is None else self.start_date
        e_utc = pytz.utc.localize(self.end_date) if self.end_date.tzinfo is None else self.end_date
        s_local = s_utc.astimezone(user_tz)
        e_local = e_utc.astimezone(user_tz)
        now_local = datetime.now(user_tz)

        period_from = s_local.strftime('%d-%m-%Y %I:%M %p')
        period_to = e_local.strftime('%d-%m-%Y %I:%M %p')
        generated_on = now_local.strftime('%d-%m-%Y %I:%M %p')
        generated_by = self.env.user.name or 'Admin'

        outlets_str = ", ".join(self.pos_config_ids.mapped('name')) if self.pos_config_ids else "All Outlets"

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})

        # Styles
        fmt_title = wb.add_format({'font_name': 'Arial', 'font_size': 14, 'bold': True, 'font_color': '#1F4E78'})
        fmt_meta_lbl = wb.add_format({'font_name': 'Arial', 'font_size': 9, 'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'border_color': '#D9D9D9'})
        fmt_meta_val = wb.add_format({'font_name': 'Arial', 'font_size': 9, 'border': 1, 'border_color': '#D9D9D9'})
        fmt_tbl_hdr_left = wb.add_format({'font_name': 'Arial', 'font_size': 9, 'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#2F5597', 'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color': '#2F5597'})
        fmt_tbl_hdr_center = wb.add_format({'font_name': 'Arial', 'font_size': 9, 'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#2F5597', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#2F5597'})
        fmt_tbl_hdr_right = wb.add_format({'font_name': 'Arial', 'font_size': 9, 'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#2F5597', 'align': 'right', 'valign': 'vcenter', 'border': 1, 'border_color': '#2F5597'})

        fmt_cell_left = wb.add_format({'font_name': 'Arial', 'font_size': 9, 'align': 'left', 'border': 1, 'border_color': '#D9D9D9'})
        fmt_cell_center = wb.add_format({'font_name': 'Arial', 'font_size': 9, 'align': 'center', 'border': 1, 'border_color': '#D9D9D9'})
        fmt_cell_num = wb.add_format({'font_name': 'Arial', 'font_size': 9, 'align': 'right', 'num_format': '#,##0.00', 'border': 1, 'border_color': '#D9D9D9'})
        fmt_cell_pct = wb.add_format({'font_name': 'Arial', 'font_size': 9, 'align': 'right', 'num_format': '0.0%', 'border': 1, 'border_color': '#D9D9D9'})
        fmt_cell_nc = wb.add_format({'font_name': 'Arial', 'font_size': 9, 'bold': True, 'font_color': '#C00000', 'border': 1, 'border_color': '#D9D9D9'})
        fmt_cell_split = wb.add_format({'font_name': 'Arial', 'font_size': 9, 'font_color': '#B25900', 'border': 1, 'border_color': '#D9D9D9'})

        fmt_total_lbl = wb.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'bg_color': '#F2F2F2', 'align': 'left', 'top': 1, 'bottom': 6, 'left': 1, 'right': 1, 'border_color': '#808080'})
        fmt_total_num = wb.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'bg_color': '#F2F2F2', 'align': 'right', 'num_format': '#,##0.00', 'top': 1, 'bottom': 6, 'left': 1, 'right': 1, 'border_color': '#808080'})

        # ---------------------------------------------------------
        # SHEET 1: All Transactions
        # ---------------------------------------------------------
        ws1 = wb.add_worksheet('All Transactions')
        col_widths_1 = {
            'A': 18, 'B': 18, 'C': 16, 'D': 16, 'E': 16, 'F': 12, 'G': 18, 'H': 18,
            'I': 15, 'J': 15, 'K': 12, 'L': 32, 'M': 22, 'N': 35
        }
        for col_let, width in col_widths_1.items():
            ws1.set_column(f'{col_let}:{col_let}', width)

        ws1.write(0, 0, f"{self.env.company.name} - POS PAYMENT DETAILS & FOOD AUDIT", fmt_title)
        ws1.write(2, 0, 'Period From:', fmt_meta_lbl)
        ws1.write(2, 1, period_from, fmt_meta_val)
        ws1.write(2, 2, 'Period To:', fmt_meta_lbl)
        ws1.write(2, 3, period_to, fmt_meta_val)
        ws1.write(2, 4, 'POS Outlets:', fmt_meta_lbl)
        ws1.write(2, 5, outlets_str, fmt_meta_val)
        ws1.write(2, 6, 'Generated On:', fmt_meta_lbl)
        ws1.write(2, 7, generated_on, fmt_meta_val)

        headers_1 = [
            'Transaction Date', 'Payment Method', 'Bill No', 'Order Ref', 'POS Outlet', 'Table',
            'Cashier', 'Customer', 'Trans. Amount', 'Order Total', 'Share %',
            'Split / Other Tenders Involved', 'NC Reason', 'Food Served / Items Ordered'
        ]
        r1 = 4
        for col_idx, h_text in enumerate(headers_1):
            align_fmt = fmt_tbl_hdr_right if col_idx in [8, 9, 10] else (fmt_tbl_hdr_center if col_idx in [0, 2, 3, 5] else fmt_tbl_hdr_left)
            ws1.write(r1, col_idx, h_text, align_fmt)

        row_idx = r1 + 1
        for p in payments:
            dt_str = pytz.utc.localize(p.payment_date).astimezone(user_tz).strftime('%d-%m-%Y %I:%M %p') if p.payment_date else ''
            ws1.write(row_idx, 0, dt_str, fmt_cell_center)
            ws1.write(row_idx, 1, p.payment_method_id.name or '-', fmt_cell_left)
            ws1.write(row_idx, 2, p.bill_number or '-', fmt_cell_center)
            ws1.write(row_idx, 3, p.pos_order_id.name or '-', fmt_cell_center)
            ws1.write(row_idx, 4, p.pos_config_id.name or '-', fmt_cell_left)
            ws1.write(row_idx, 5, p.table_label or '-', fmt_cell_center)
            ws1.write(row_idx, 6, p.cashier_name or '-', fmt_cell_left)
            ws1.write(row_idx, 7, p.partner_id.name or '-', fmt_cell_left)
            ws1.write(row_idx, 8, p.amount, fmt_cell_num)
            ws1.write(row_idx, 9, p.order_amount_total, fmt_cell_num)
            ws1.write(row_idx, 10, (p.payment_ratio / 100.0), fmt_cell_pct)
            ws1.write(row_idx, 11, p.other_payments_display or 'Full Payment', fmt_cell_split if p.is_split_payment else fmt_cell_left)
            ws1.write(row_idx, 12, p.nc_reason or '-', fmt_cell_nc if p.nc_reason else fmt_cell_left)
            ws1.write(row_idx, 13, p.food_served_summary or '-', fmt_cell_left)
            row_idx += 1

        if row_idx > r1 + 1:
            ws1.write(row_idx, 0, 'Total All Transactions', fmt_total_lbl)
            for c in range(1, 8):
                ws1.write(row_idx, c, '', fmt_total_lbl)
            ws1.write_formula(row_idx, 8, f'=SUBTOTAL(9,I{r1+2}:I{row_idx})', fmt_total_num)
            ws1.write(row_idx, 9, '', fmt_total_lbl)
            ws1.write(row_idx, 10, '', fmt_total_lbl)
            ws1.write(row_idx, 11, '', fmt_total_lbl)
            ws1.write(row_idx, 12, '', fmt_total_lbl)
            ws1.write(row_idx, 13, '', fmt_total_lbl)

        # ---------------------------------------------------------
        # SHEET 2: Split Payments Audit
        # ---------------------------------------------------------
        ws2 = wb.add_worksheet('Split Payments Audit')
        col_widths_2 = {'A': 18, 'B': 18, 'C': 16, 'D': 16, 'E': 16, 'F': 12, 'G': 18, 'H': 15, 'I': 15, 'J': 12, 'K': 35}
        for col_let, width in col_widths_2.items():
            ws2.set_column(f'{col_let}:{col_let}', width)

        ws2.write(0, 0, 'SPLIT / MULTI-TENDER PAYMENTS AUDIT', fmt_title)
        headers_2 = ['Transaction Date', 'This Method', 'Bill No', 'Order Ref', 'POS Outlet', 'Table', 'Cashier', 'This Amount', 'Order Total', 'Share %', 'All Tenders Combined']
        for col_idx, h_text in enumerate(headers_2):
            align_fmt = fmt_tbl_hdr_right if col_idx in [7, 8, 9] else (fmt_tbl_hdr_center if col_idx in [0, 2, 3, 5] else fmt_tbl_hdr_left)
            ws2.write(2, col_idx, h_text, align_fmt)

        split_payments = payments.filtered(lambda p: p.is_split_payment)
        r2 = 3
        for sp in split_payments:
            dt_str = pytz.utc.localize(sp.payment_date).astimezone(user_tz).strftime('%d-%m-%Y %I:%M %p') if sp.payment_date else ''
            ws2.write(r2, 0, dt_str, fmt_cell_center)
            ws2.write(r2, 1, sp.payment_method_id.name or '-', fmt_cell_left)
            ws2.write(r2, 2, sp.bill_number or '-', fmt_cell_center)
            ws2.write(r2, 3, sp.pos_order_id.name or '-', fmt_cell_center)
            ws2.write(r2, 4, sp.pos_config_id.name or '-', fmt_cell_left)
            ws2.write(r2, 5, sp.table_label or '-', fmt_cell_center)
            ws2.write(r2, 6, sp.cashier_name or '-', fmt_cell_left)
            ws2.write(r2, 7, sp.amount, fmt_cell_num)
            ws2.write(r2, 8, sp.order_amount_total, fmt_cell_num)
            ws2.write(r2, 9, (sp.payment_ratio / 100.0), fmt_cell_pct)
            ws2.write(r2, 10, sp.other_payments_display or '-', fmt_cell_left)
            r2 += 1

        if r2 > 3:
            ws2.write(r2, 0, 'Total Split Payments', fmt_total_lbl)
            for c in range(1, 7):
                ws2.write(r2, c, '', fmt_total_lbl)
            ws2.write_formula(r2, 7, f'=SUBTOTAL(9,H4:H{r2})', fmt_total_num)
            ws2.write(r2, 8, '', fmt_total_lbl)
            ws2.write(r2, 9, '', fmt_total_lbl)
            ws2.write(r2, 10, '', fmt_total_lbl)
        else:
            ws2.write(3, 0, 'No split payment transactions found in this period.', fmt_cell_left)

        # ---------------------------------------------------------
        # SHEET 3: NC (No Charge) Audit
        # ---------------------------------------------------------
        ws3 = wb.add_worksheet('NC & Complimentary Audit')
        col_widths_3 = {'A': 18, 'B': 16, 'C': 16, 'D': 16, 'E': 12, 'F': 18, 'G': 15, 'H': 25, 'I': 35}
        for col_let, width in col_widths_3.items():
            ws3.set_column(f'{col_let}:{col_let}', width)

        ws3.write(0, 0, 'NO CHARGE (NC) & COMPLIMENTARY TRANSACTIONS AUDIT', fmt_title)
        headers_3 = ['Transaction Date', 'Bill No', 'Order Ref', 'POS Outlet', 'Table', 'Cashier', 'Waived Amount', 'NC / Complimentary Reason', 'Food Served']
        for col_idx, h_text in enumerate(headers_3):
            align_fmt = fmt_tbl_hdr_right if col_idx == 6 else (fmt_tbl_hdr_center if col_idx in [0, 1, 2, 4] else fmt_tbl_hdr_left)
            ws3.write(2, col_idx, h_text, align_fmt)

        nc_payments = payments.filtered(lambda p: p.is_nc_payment or p.nc_reason)
        r3 = 3
        for np in nc_payments:
            dt_str = pytz.utc.localize(np.payment_date).astimezone(user_tz).strftime('%d-%m-%Y %I:%M %p') if np.payment_date else ''
            ws3.write(r3, 0, dt_str, fmt_cell_center)
            ws3.write(r3, 1, np.bill_number or '-', fmt_cell_center)
            ws3.write(r3, 2, np.pos_order_id.name or '-', fmt_cell_center)
            ws3.write(r3, 3, np.pos_config_id.name or '-', fmt_cell_left)
            ws3.write(r3, 4, np.table_label or '-', fmt_cell_center)
            ws3.write(r3, 5, np.cashier_name or '-', fmt_cell_left)
            ws3.write(r3, 6, np.amount, fmt_cell_num)
            ws3.write(r3, 7, np.nc_reason or 'No Reason Specified', fmt_cell_nc)
            ws3.write(r3, 8, np.food_served_summary or '-', fmt_cell_left)
            r3 += 1

        if r3 > 3:
            ws3.write(r3, 0, 'Total Complimentary Waived', fmt_total_lbl)
            for c in range(1, 6):
                ws3.write(r3, c, '', fmt_total_lbl)
            ws3.write_formula(r3, 6, f'=SUBTOTAL(9,G4:G{r3})', fmt_total_num)
            ws3.write(r3, 7, '', fmt_total_lbl)
            ws3.write(r3, 8, '', fmt_total_lbl)
        else:
            ws3.write(3, 0, 'No complimentary / NC transactions found in this period.', fmt_cell_left)

        # ---------------------------------------------------------
        # SHEET 4: Food Served Line Items
        # ---------------------------------------------------------
        ws4 = wb.add_worksheet('Food Line Items')
        col_widths_4 = {'A': 18, 'B': 18, 'C': 16, 'D': 16, 'E': 16, 'F': 12, 'G': 20, 'H': 32, 'I': 10, 'J': 13, 'K': 15, 'L': 15}
        for col_let, width in col_widths_4.items():
            ws4.set_column(f'{col_let}:{col_let}', width)

        ws4.write(0, 0, 'FOOD & BEVERAGE LINE ITEMS BY TRANSACTION', fmt_title)
        headers_4 = ['Transaction Date', 'Payment Method', 'Bill No', 'Order Ref', 'POS Outlet', 'Table', 'Category', 'Product / Food Served', 'Qty', 'Unit Price', 'Subtotal (Excl Tax)', 'Total (Incl Tax)']
        for col_idx, h_text in enumerate(headers_4):
            align_fmt = fmt_tbl_hdr_right if col_idx in [8, 9, 10, 11] else (fmt_tbl_hdr_center if col_idx in [0, 2, 3, 5] else fmt_tbl_hdr_left)
            ws4.write(2, col_idx, h_text, align_fmt)

        r4 = 3
        for p in payments:
            dt_str = pytz.utc.localize(p.payment_date).astimezone(user_tz).strftime('%d-%m-%Y %I:%M %p') if p.payment_date else ''
            order = p.pos_order_id
            if order:
                for line in order.lines:
                    prod_cat = line.product_id.pos_categ_ids[:1] or line.product_id.categ_id
                    cat_name = prod_cat.name if prod_cat else 'Uncategorized'
                    ws4.write(r4, 0, dt_str, fmt_cell_center)
                    ws4.write(r4, 1, p.payment_method_id.name or '-', fmt_cell_left)
                    ws4.write(r4, 2, p.bill_number or '-', fmt_cell_center)
                    ws4.write(r4, 3, order.name or '-', fmt_cell_center)
                    ws4.write(r4, 4, p.pos_config_id.name or '-', fmt_cell_left)
                    ws4.write(r4, 5, p.table_label or '-', fmt_cell_center)
                    ws4.write(r4, 6, cat_name, fmt_cell_left)
                    ws4.write(r4, 7, line.product_id.display_name, fmt_cell_left)
                    ws4.write(r4, 8, line.qty, fmt_cell_num)
                    ws4.write(r4, 9, line.price_unit, fmt_cell_num)
                    ws4.write(r4, 10, line.price_subtotal, fmt_cell_num)
                    ws4.write(r4, 11, line.price_subtotal_incl, fmt_cell_num)
                    r4 += 1

        if r4 > 3:
            ws4.write(r4, 0, 'Total Line Items', fmt_total_lbl)
            for c in range(1, 8):
                ws4.write(r4, c, '', fmt_total_lbl)
            ws4.write_formula(r4, 8, f'=SUBTOTAL(9,I4:I{r4})', fmt_total_num)
            ws4.write(r4, 9, '', fmt_total_lbl)
            ws4.write_formula(r4, 10, f'=SUBTOTAL(9,K4:K{r4})', fmt_total_num)
            ws4.write_formula(r4, 11, f'=SUBTOTAL(9,L4:L{r4})', fmt_total_num)

        wb.close()
        excel_data = output.getvalue()
        output.close()

        filename = f"POS_Transaction_Details_{s_local.strftime('%Y%m%d_%H%M')}_to_{e_local.strftime('%Y%m%d_%H%M')}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_data),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
