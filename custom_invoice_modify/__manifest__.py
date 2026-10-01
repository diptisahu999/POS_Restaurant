# pyrefly: ignore [missing-import]
{
    'name': 'Custom Invoice Modify',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Allow specific users to modify paid invoices',
    'depends': ['account'],
    'data': [
        'security/invoice_security.xml',
        'views/account_move_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
