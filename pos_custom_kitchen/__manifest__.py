{
    'name': 'POS Custom Kitchen Display',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'A Kanban display for Kitchen Orders',
    'description': 'Adds a custom Kanban view to manage kitchen orders from POS.',
    'depends': ['point_of_sale', 'pos_restaurant', 'pos_discount'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_kitchen_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pos_custom_kitchen/static/src/backend/**/*',
        ],
        'point_of_sale._assets_pos': [
            'pos_custom_kitchen/static/src/app/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
