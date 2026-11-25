# -*- coding: utf-8 -*-
{
    'name': 'Custom POS Outlet Force Delete',
    'version': '1.0',
    'category': 'Point of Sale',
    'author': 'Techvizor',
    'summary': 'Allows force deleting POS Outlets (pos.config) even when sessions or orders exist',
    'description': """
        Adds permissions and a safe Force Delete action & wizard for POS Outlets (pos.config):
        - Bypass open POS session and linked order deletion restrictions.
        - Automatically closes/unlinks linked sessions, orders, payments, and settings before unlinking.
        - Adds a Force Delete button on POS Outlet Form, List, Action menu, and Dashboard Kanban card.
        - Adds an authorization toggle under Users Settings (Access Rights).
        - Provides a confirmation wizard showing affected outlet names and linked record counts.
    """,
    'depends': ['point_of_sale'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'wizard/force_delete_outlet_wizard_views.xml',
        'views/pos_config_actions.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
