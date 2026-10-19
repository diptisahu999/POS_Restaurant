# -*- coding: utf-8 -*-
{
    'name': 'Custom POS Orders Force Delete',
    'version': '1.0',
    'category': 'Point of Sale',
    'author': 'Techvizor',
    'summary': 'Allows force deleting POS Orders, Sessions, Payments and Customers even when sessions are open',
    'description': """
        Adds permissions and a safe Force Delete action & wizard for POS Orders, Sessions, Payments and Customers:
        - Bypass open POS session deletion restrictions.
        - Automatically detaches linked records before unlinking.
        - Adds an authorization toggle under Users Settings (Access Rights).
        - Provides a confirmation wizard showing affected record names.
    """,
    'depends': ['point_of_sale'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'wizard/force_delete_order_wizard_views.xml',
        'wizard/force_delete_session_wizard_views.xml',
        'wizard/force_delete_payment_wizard_views.xml',
        'wizard/force_delete_customer_wizard_views.xml',
        'views/pos_order_actions.xml',
        'views/pos_session_actions.xml',
        'views/pos_payment_actions.xml',
        'views/pos_customer_actions.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
