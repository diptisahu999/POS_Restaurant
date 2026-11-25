# -*- coding: utf-8 -*-
{
    'name': 'Custom Payment Details - POS Payment & Food Audit',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Detailed POS transaction audit showing connected bill number, order, food served, split payment breakdown, and NC reasons.',
    'description': """
POS payment details & Food Audit
====================================
This module enhances Point of Sale transactions (pos.payment) with complete operational visibility:
- **Connected Bill & Order**: Immediate display of Bill Number, Order Reference, POS Outlet, Table, Customer, and Cashier.
- **Food Served**: Full breakdown of items, quantities, and prices served for each transaction.
- **Split Payment Intelligence**: Automatically identifies split/partial payments and displays the other payments involved on that bill.
- **No Charge (NC) Audit**: Explicit capture and highlighting of complimentary/NC reasons.
- **Dedicated Export Wizard**: Multi-sheet Excel & executive PDF export for transaction audits.
    """,
    'author': 'Techvizor',
    'website': 'https://www.techvizor.com',
    'depends': ['point_of_sale', 'pos_restaurant'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_payment_views.xml',
        'wizard/pos_transaction_wizard_views.xml',
        'views/pos_transaction_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
