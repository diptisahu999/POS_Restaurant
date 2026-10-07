# -*- coding: utf-8 -*-
{
    'name': 'Custom Kitchen Printer',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Direct TCP Network Printing (TVS / ESC-POS) for Kitchen Orders',
    'description': """
        Adds direct network IP printing support for kitchen orders:
        - Direct TCP socket printing to TVS RP 3200 Lite & ESC/POS network thermal printers (port 9100).
        - Test print button on Preparation Printer form.
        - Assign kitchen printers directly on POS Product Category.
        - Automatic ticket splitting by category on Send to Kitchen / Reorders.
    """,
    'depends': ['point_of_sale', 'pos_restaurant'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_printer_views.xml',
        'views/pos_category_views.xml',
        'views/kitchen_printer_log_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
