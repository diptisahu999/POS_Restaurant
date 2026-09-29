# -*- coding: utf-8 -*-
{
    'name': 'Custom Restaurant Bill & Payments',
    'version': '1.0.0',
    'summary': 'Prominent Table Number badge, UPI QR Code on restaurant bills, UPI / Online and Gift Card (GC) payment methods',
    'category': 'Point of Sale',
    'author': 'Techvizor',
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'pos_restaurant'],
    'data': [
        'views/pos_config_views.xml',
        'views/pos_order_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_bill/static/src/**/*',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
