# -*- coding: utf-8 -*-
{
    'name': 'Custom POS Order Create Access',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Control Create (New) button on POS Orders user-wise based on dynamic designation and access rights',
    'author': 'Techvizor',
    'depends': ['base', 'point_of_sale'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/pos_designation_data.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
