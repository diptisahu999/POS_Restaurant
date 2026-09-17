# -*- coding: utf-8 -*-
{
    'name': 'Custom POS Restaurant Menu',
    'version': '1.0.0',
    'summary': 'La Flora Restaurant Menu & Categories for Point of Sale',
    'description': """
        Custom POS Module for La Flora Restaurant:
        - Automatically installs all 8 POS categories (Soups, Salads, Pizza, Pasta, Appetizers, etc.)
        - Automatically loads all 40 restaurant menu products with prices and descriptions
        - Configures default POS settings
    """,
    'category': 'Point of Sale',
    'author': 'La Flora',
    'depends': ['base', 'point_of_sale', 'pos_restaurant'],
    'data': [
        'data/pos_category_data.xml',
        'data/product_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
