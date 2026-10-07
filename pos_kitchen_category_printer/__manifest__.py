{
    'name': 'POS Kitchen Category Printer & Display',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Separate kitchen tickets and display category-wise for multi-station kitchen printers',
    'description': 'Splits POS kitchen orders by product category when sending to kitchen, enabling multi-printer station printing and categorized kitchen display.',
    'depends': ['point_of_sale', 'pos_restaurant', 'pos_custom_kitchen'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_category_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_kitchen_category_printer/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
