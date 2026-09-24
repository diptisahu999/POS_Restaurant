# -*- coding: utf-8 -*-
{
    'name': 'Custom Form Page',
    'version': '1.0.0',
    'category': 'Point of Sale',
    'summary': 'Add Home button and Order Status updates (Pending -> Preparing -> Done)',
    'description': """
        Custom POS Module:
        - Adds a 'Home' button to the POS navbar next to Orders
        - Adds Order Status lifecycle (Pending -> Preparing -> Done)
        - Seamless status tracking in POS Orders list and backend views
    """,
    'author': 'Techvizor',
    'depends': ['point_of_sale', 'pos_restaurant'],
    'data': [
        'views/pos_order_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_form_page/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
