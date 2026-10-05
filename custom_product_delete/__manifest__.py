{
    'name': 'Custom Product Force Delete',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Allows force deleting products even when POS sessions are open',
    'description': 'Adds a Force Delete action in the Actions menu to safely and permanently delete products bypassing open POS session restrictions.',
    'depends': ['product', 'point_of_sale'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'wizard/force_delete_wizard_views.xml',
        'views/product_actions.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
