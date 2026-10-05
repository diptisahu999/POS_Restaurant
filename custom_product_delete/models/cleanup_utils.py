# pyrefly: ignore [missing-import]
import logging

_logger = logging.getLogger(__name__)

def force_clean_product_references(env, variant_ids=None, tmpl_ids=None):
    """
    Cleans up all database foreign key references pointing to the given product variants
    or product templates so they can be deleted cleanly without constraint errors.
    Uses savepoints to ensure transaction integrity.
    """
    variant_ids = list(variant_ids or [])
    tmpl_ids = list(tmpl_ids or [])

    if not variant_ids and not tmpl_ids:
        return

    # 1. Clean POS combo lines
    if 'pos.combo.line' in env and variant_ids:
        try:
            with env.cr.savepoint():
                combo_lines = env['pos.combo.line'].sudo().search([('product_id', 'in', variant_ids)])
                if combo_lines:
                    combo_lines.unlink()
        except Exception as e:
            _logger.warning(f"Error unlinking pos.combo.line: {e}")

    # 2. Clean POS kitchen round lines
    if 'pos.kitchen.round.line' in env and variant_ids:
        try:
            with env.cr.savepoint():
                k_lines = env['pos.kitchen.round.line'].sudo().search([('product_id', 'in', variant_ids)])
                if k_lines:
                    k_lines.unlink()
        except Exception as e:
            _logger.warning(f"Error unlinking pos.kitchen.round.line: {e}")

    # 3. Clean POS order lines
    if variant_ids:
        v_tuple = tuple(variant_ids)
        try:
            with env.cr.savepoint():
                env.cr.execute("DELETE FROM pos_pack_operation_lot WHERE pos_order_line_id IN (SELECT id FROM pos_order_line WHERE product_id IN %s)", (v_tuple,))
                env.cr.execute("DELETE FROM pos_order_line WHERE product_id IN %s", (v_tuple,))
        except Exception as e:
            _logger.warning(f"Error deleting pos_order_line: {e}")

    # 4. Clean Stock Valuation Layer
    if variant_ids:
        v_tuple = tuple(variant_ids)
        try:
            with env.cr.savepoint():
                env.cr.execute("""
                    DELETE FROM stock_valuation_layer 
                    WHERE product_id IN %s 
                       OR stock_move_id IN (SELECT id FROM stock_move WHERE product_id IN %s)
                """, (v_tuple, v_tuple))
        except Exception as e:
            _logger.warning(f"Error deleting stock_valuation_layer: {e}")

    # 5. Clean Stock Quants
    if variant_ids:
        v_tuple = tuple(variant_ids)
        try:
            with env.cr.savepoint():
                env.cr.execute("DELETE FROM stock_quant WHERE product_id IN %s", (v_tuple,))
        except Exception as e:
            _logger.warning(f"Error deleting stock_quant: {e}")

    # 6. Clean Stock Move Lines
    if variant_ids:
        v_tuple = tuple(variant_ids)
        try:
            with env.cr.savepoint():
                env.cr.execute("""
                    DELETE FROM stock_move_line 
                    WHERE product_id IN %s 
                       OR move_id IN (SELECT id FROM stock_move WHERE product_id IN %s)
                """, (v_tuple, v_tuple))
        except Exception as e:
            _logger.warning(f"Error deleting stock_move_line: {e}")

    # 7. Clean Stock Move destination/purchase relations & Stock Moves
    if variant_ids:
        v_tuple = tuple(variant_ids)
        for rel_table in ['stock_move_move_rel', 'stock_move_created_purchase_line_rel', 'stock_move_line_consume_rel']:
            try:
                with env.cr.savepoint():
                    env.cr.execute(f"""
                        DELETE FROM {rel_table} 
                        WHERE move_id IN (SELECT id FROM stock_move WHERE product_id IN %s)
                           OR move_dest_id IN (SELECT id FROM stock_move WHERE product_id IN %s)
                    """, (v_tuple, v_tuple))
            except Exception:
                pass

        try:
            with env.cr.savepoint():
                env.cr.execute("DELETE FROM stock_move WHERE product_id IN %s", (v_tuple,))
        except Exception as e:
            _logger.warning(f"Error deleting stock_move: {e}")

    # 8. Clean Stock Lots / Serial Numbers
    if variant_ids:
        v_tuple = tuple(variant_ids)
        for lot_table in ['stock_lot', 'stock_production_lot']:
            try:
                with env.cr.savepoint():
                    env.cr.execute(f"DELETE FROM {lot_table} WHERE product_id IN %s", (v_tuple,))
            except Exception:
                pass

    # 9. Clean Pricelist items
    if 'product.pricelist.item' in env:
        try:
            with env.cr.savepoint():
                domain = []
                if variant_ids and tmpl_ids:
                    domain = ['|', ('product_id', 'in', variant_ids), ('product_tmpl_id', 'in', tmpl_ids)]
                elif variant_ids:
                    domain = [('product_id', 'in', variant_ids)]
                elif tmpl_ids:
                    domain = [('product_tmpl_id', 'in', tmpl_ids)]
                if domain:
                    pl_items = env['product.pricelist.item'].sudo().search(domain)
                    if pl_items:
                        pl_items.unlink()
        except Exception as e:
            _logger.warning(f"Error unlinking product.pricelist.item: {e}")

    # 10. Clean Supplier Info
    if 'product.supplierinfo' in env:
        try:
            with env.cr.savepoint():
                domain = []
                if variant_ids and tmpl_ids:
                    domain = ['|', ('product_id', 'in', variant_ids), ('product_tmpl_id', 'in', tmpl_ids)]
                elif variant_ids:
                    domain = [('product_id', 'in', variant_ids)]
                elif tmpl_ids:
                    domain = [('product_tmpl_id', 'in', tmpl_ids)]
                if domain:
                    suppliers = env['product.supplierinfo'].sudo().search(domain)
                    if suppliers:
                        suppliers.unlink()
        except Exception as e:
            _logger.warning(f"Error unlinking product.supplierinfo: {e}")

    # 11. Clean Packaging
    if 'product.packaging' in env:
        try:
            with env.cr.savepoint():
                domain = []
                if variant_ids and tmpl_ids:
                    domain = ['|', ('product_id', 'in', variant_ids), ('product_tmpl_id', 'in', tmpl_ids)]
                elif variant_ids:
                    domain = [('product_id', 'in', variant_ids)]
                elif tmpl_ids:
                    domain = [('product_tmpl_id', 'in', tmpl_ids)]
                if domain:
                    packagings = env['product.packaging'].sudo().search(domain)
                    if packagings:
                        packagings.unlink()
        except Exception as e:
            _logger.warning(f"Error unlinking product.packaging: {e}")

    # 12. Clean or detach Account Move Lines (Journal Items)
    if variant_ids:
        try:
            with env.cr.savepoint():
                v_tuple = tuple(variant_ids)
                # Setting product_id = NULL on account_move_line preserves accounting debit/credit balances
                # while allowing the product to be deleted without triggering foreign key constraint errors.
                env.cr.execute("UPDATE account_move_line SET product_id = NULL WHERE product_id IN %s", (v_tuple,))
        except Exception as e:
            _logger.warning(f"Error detaching account.move.line: {e}")

    # 13. Clean or detach Sale Order Lines
    if variant_ids:
        try:
            with env.cr.savepoint():
                v_tuple = tuple(variant_ids)
                env.cr.execute("UPDATE sale_order_line SET product_id = NULL WHERE product_id IN %s", (v_tuple,))
        except Exception as e:
            _logger.warning(f"Error detaching sale.order.line: {e}")

    # 14. Clean or detach Purchase Order Lines
    if variant_ids:
        try:
            with env.cr.savepoint():
                v_tuple = tuple(variant_ids)
                env.cr.execute("UPDATE purchase_order_line SET product_id = NULL WHERE product_id IN %s", (v_tuple,))
        except Exception as e:
            _logger.warning(f"Error detaching purchase.order.line: {e}")

    # 15. Clean MRP BOM lines (if mrp table exists)
    if variant_ids:
        try:
            with env.cr.savepoint():
                v_tuple = tuple(variant_ids)
                env.cr.execute("DELETE FROM mrp_bom_line WHERE product_id IN %s", (v_tuple,))
                if tmpl_ids:
                    t_tuple = tuple(tmpl_ids)
                    env.cr.execute("DELETE FROM mrp_bom WHERE product_tmpl_id IN %s", (t_tuple,))
        except Exception as e:
            pass


