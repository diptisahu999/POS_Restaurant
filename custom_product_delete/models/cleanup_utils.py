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
    if 'pos.order.line' in env and variant_ids:
        try:
            with env.cr.savepoint():
                pos_lines = env['pos.order.line'].sudo().search([('product_id', 'in', variant_ids)])
                if pos_lines:
                    pos_lines.unlink()
        except Exception as e:
            _logger.warning(f"Error unlinking pos.order.line via ORM: {e}")
            try:
                with env.cr.savepoint():
                    v_tuple = tuple(variant_ids)
                    env.cr.execute("DELETE FROM pos_pack_operation_lot WHERE pos_order_line_id IN (SELECT id FROM pos_order_line WHERE product_id IN %s)", (v_tuple,))
                    env.cr.execute("DELETE FROM pos_order_line WHERE product_id IN %s", (v_tuple,))
            except Exception as sql_e:
                _logger.warning(f"SQL delete pos_order_line error: {sql_e}")

    # 4. Clean Stock Quants
    if 'stock.quant' in env and variant_ids:
        try:
            with env.cr.savepoint():
                quants = env['stock.quant'].sudo().search([('product_id', 'in', variant_ids)])
                if quants:
                    quants.unlink()
        except Exception as e:
            _logger.warning(f"Error unlinking stock.quant: {e}")

    # 5. Clean Stock Moves and Move Lines
    if 'stock.move.line' in env and variant_ids:
        try:
            with env.cr.savepoint():
                sml = env['stock.move.line'].sudo().search([('product_id', 'in', variant_ids)])
                if sml:
                    sml.unlink()
        except Exception as e:
            _logger.warning(f"Error unlinking stock.move.line: {e}")

    if 'stock.move' in env and variant_ids:
        try:
            with env.cr.savepoint():
                sm = env['stock.move'].sudo().search([('product_id', 'in', variant_ids)])
                if sm:
                    sm.unlink()
        except Exception as e:
            _logger.warning(f"Error unlinking stock.move: {e}")

    # 6. Clean Pricelist items
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

    # 7. Clean Supplier Info
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

    # 8. Clean Packaging
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
