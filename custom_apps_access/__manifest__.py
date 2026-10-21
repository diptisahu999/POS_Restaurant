# -*- coding: utf-8 -*-
{
    'name': 'Custom Apps Access Management',
    'version': '1.0',
    'category': 'Administration',
    'summary': 'User-wise access control for Apps module and menu',
    'description': """
        Custom Apps Access Control:
        - Allows controlling access to the Apps module and menu on a user-by-user basis.
        - Provides a toggle in Users settings under Access Rights.
        - Dynamically hides the Apps menu and sidebar icon for unauthorized users.
        - Blocks direct URL access (/odoo/apps) and action execution.
        - Protects module installation, upgrade, and uninstallation actions.
    """,
    'author': 'Custom',
    'depends': ['base'],
    'data': [
        'security/groups.xml',
        'security/menu_security.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
