# -*- coding: utf-8 -*-
{
    'name': 'Custom Other Modules Hide',
    'version': '1.0',
    'category': 'Administration',
    'summary': 'User-wise visibility control to hide Discuss, To-do, Employees, and Link Tracker',
    'description': """
        Custom Other Modules Hide:
        - Allows hiding Discuss, To-do, Employees, and Link Tracker modules per user.
        - Adds toggle switches in Users settings under Access Rights.
        - Dynamically hides the sidebar icons and navigation menus for unauthorized users.
        - Blocks direct action access for hidden modules.
    """,
    'author': 'Custom',
    'depends': ['base'],
    'data': [
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
