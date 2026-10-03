{
    'name': 'Product Price Approval',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Require approval for product price changes',
    'depends': ['product', 'mail', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/product_price_approval_views.xml',
        'views/product_template_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
