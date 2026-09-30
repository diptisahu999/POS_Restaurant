env = env(user=1)
product = env['product.product'].search([('name', '=', 'Global Discount')], limit=1)
if not product:
    product = env['product.product'].create({
        'name': 'Global Discount',
        'type': 'service',
        'available_in_pos': True,
        'taxes_id': False,
        'supplier_taxes_id': False,
        'sale_ok': True,
        'purchase_ok': False,
    })
else:
    product.write({'available_in_pos': True, 'type': 'service'})

configs = env['pos.config'].search([])
configs.write({
    'module_pos_discount': True,
    'discount_product_id': product.id,
    'discount_pc': 10,
})
env.cr.commit()
print("Setup successful!")
