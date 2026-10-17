# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

def force_clean_pos_category_references(env, category_ids):
    """
    Cleans up all database references pointing to the given POS categories
    so they can be safely and permanently deleted without constraint errors.
    """
    category_ids = list(category_ids or [])
    if not category_ids:
        return

    c_tuple = tuple(category_ids)

    # 1. Re-parent child sub-categories to root
    try:
        with env.cr.savepoint():
            child_cats = env['pos.category'].sudo().search([('parent_id', 'in', category_ids)])
            if child_cats:
                child_cats.write({'parent_id': False})
    except Exception as e:
        _logger.warning(f"Error re-parenting child pos.category: {e}")

    # 2. Unlink from products (product.template Many2many pos_categ_ids)
    if 'pos_categ_ids' in env['product.template']._fields:
        try:
            with env.cr.savepoint():
                products = env['product.template'].sudo().search([('pos_categ_ids', 'in', category_ids)])
                for cat_id in category_ids:
                    products.write({'pos_categ_ids': [(3, cat_id)]})
        except Exception as e:
            _logger.warning(f"Error detaching pos.category from product.template: {e}")

    # 3. Direct DB cleanup of pos_category_product_template_rel if exists
    try:
        with env.cr.savepoint():
            env.cr.execute("""
                DELETE FROM pos_category_product_template_rel 
                WHERE pos_category_id IN %s
            """, (c_tuple,))
    except Exception:
        pass

    # 4. Standard pos_restaurant printer categories (product_categories_ids)
    if 'pos.printer' in env and 'product_categories_ids' in env['pos.printer']._fields:
        try:
            with env.cr.savepoint():
                printers = env['pos.printer'].sudo().search([('product_categories_ids', 'in', category_ids)])
                for cat_id in category_ids:
                    printers.write({'product_categories_ids': [(3, cat_id)]})
        except Exception as e:
            _logger.warning(f"Error detaching pos.category from pos.printer: {e}")

    # 5. Direct DB cleanup of pos_printer_category_rel
    try:
        with env.cr.savepoint():
            env.cr.execute("""
                DELETE FROM pos_printer_category_rel 
                WHERE category_id IN %s
            """, (c_tuple,))
    except Exception:
        pass

    # 6. Custom kitchen printer M2M relation (printer_category_rel)
    try:
        with env.cr.savepoint():
            env.cr.execute("""
                DELETE FROM printer_category_rel 
                WHERE category_id IN %s
            """, (c_tuple,))
    except Exception:
        pass

    # 7. Clean pos.config available categories (iface_available_categ_ids)
    if 'pos.config' in env and 'iface_available_categ_ids' in env['pos.config']._fields:
        try:
            with env.cr.savepoint():
                configs = env['pos.config'].sudo().search([('iface_available_categ_ids', 'in', category_ids)])
                for cat_id in category_ids:
                    configs.write({'iface_available_categ_ids': [(3, cat_id)]})
        except Exception as e:
            _logger.warning(f"Error detaching pos.category from pos.config: {e}")

    # 8. Clean pos.kitchen.round.line pos_category_id
    if 'pos.kitchen.round.line' in env:
        try:
            with env.cr.savepoint():
                lines = env['pos.kitchen.round.line'].sudo().search([('pos_category_id', 'in', category_ids)])
                if lines:
                    lines.write({'pos_category_id': False})
        except Exception as e:
            _logger.warning(f"Error detaching pos.category from pos.kitchen.round.line: {e}")
