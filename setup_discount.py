import xmlrpc.client

url = "http://localhost:7676"
db = "laflora"
username = "laflora001@gmail.com"
password = "admin"

try:
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

    # Check if a discount product exists
    product_ids = models.execute_kw(db, uid, password, 'product.product', 'search', [[('name', '=', 'Global Discount')]])
    if not product_ids:
        print("Creating Global Discount product...")
        product_id = models.execute_kw(db, uid, password, 'product.product', 'create', [{
            'name': 'Global Discount',
            'type': 'service',
            'available_in_pos': True,
            'taxes_id': [],
            'supplier_taxes_id': [],
            'sale_ok': True,
            'purchase_ok': False,
        }])
    else:
        product_id = product_ids[0]
        # Ensure it is available in POS
        models.execute_kw(db, uid, password, 'product.product', 'write', [[product_id], {'available_in_pos': True, 'type': 'service'}])

    print(f"Discount Product ID: {product_id}")

    # Update POS configs
    config_ids = models.execute_kw(db, uid, password, 'pos.config', 'search', [[]])
    models.execute_kw(db, uid, password, 'pos.config', 'write', [config_ids, {
        'module_pos_discount': True,
        'discount_product_id': product_id,
        'discount_pc': 10,
    }])
    print("POS configs updated successfully!")

except Exception as e:
    print(f"Error: {e}")
