import sys
import os

sys.path.insert(0, r"C:\Project\odoo19\odoo")
import odoo
from odoo.tools import config

config.parse_config(['-c', r'C:\Project\odoo19\POS_Restaurant\odoo.conf', '-d', 'POS_restaurant', '--no-http'])

registry = odoo.modules.registry.Registry('POS_restaurant')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    session = env['pos.session'].search([('state', '=', 'opened')], limit=1)
    if not session:
        session = env['pos.session'].search([], limit=1)
    
    config = session.config_id
    print("POS Config Name:", config.name)
    print("limit_categories:", config.limit_categories)
    print("iface_available_categ_ids:", config.iface_available_categ_ids.mapped('name'))
    
    # Check session loader params
    try:
        # In Odoo 18/19
        loader_data = session._load_pos_data(['product.product'])
        print("Loaded products count from _load_pos_data:", len(loader_data.get('product.product', {}).get('data', [])))
    except Exception as e:
        print("Error calling _load_pos_data:", e)

    try:
        # Let's check products
        pos_products = env['product.product'].search([('available_in_pos', '=', True)])
        print("Total product.product with available_in_pos=True:", len(pos_products))
        for p in pos_products[:10]:
            print(f"Product: {p.name}, POS Categs: {p.pos_categ_ids.mapped('name')}, Active: {p.active}, Sale OK: {p.sale_ok}, Available in POS: {p.available_in_pos}")
    except Exception as e:
        print("Error checking products:", e)
