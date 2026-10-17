# -*- coding: utf-8 -*-
{
    'name': 'Custom POS Category Force Delete',
    'version': '1.0',
    'category': 'Point of Sale',
    'author': 'Techvizor',
    'summary': 'Allows force deleting POS food/product categories even when POS sessions are open',
    'description': """
        Adds permissions and a safe Force Delete action & wizard for POS Product Categories:
        - Bypass open POS session deletion restrictions.
        - Automatically detaches products, printers, and subcategories before unlinking.
        - Adds an authorization toggle under Users Settings (Access Rights).
        - Provides a confirmation wizard showing affected category names.
    """,
    'depends': ['point_of_sale'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'wizard/force_delete_category_wizard_views.xml',
        'views/pos_category_actions.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
