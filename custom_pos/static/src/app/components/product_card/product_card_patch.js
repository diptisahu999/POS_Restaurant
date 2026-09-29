/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

patch(ProductCard.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },

    getOrderLines() {
        const order = this.pos?.getOrder();
        if (!order || !this.props.productId) {
            return [];
        }
        return order.lines.filter(
            (l) =>
                l.product_id?.product_tmpl_id?.id === this.props.productId ||
                l.product_id?.id === this.props.productId
        );
    },

    get cartQty() {
        const lines = this.getOrderLines();
        if (lines.length > 0) {
            return lines.reduce((sum, l) => sum + (l.qty || 0), 0);
        }
        return this.props.productCartQty || 0;
    },

    get displayPrice() {
        const product = this.props.product;
        if (!product) {
            return "";
        }
        try {
            if (product.displayPriceUnit) {
                return product.displayPriceUnit;
            }
            if (this.env.utils?.formatCurrency && product.lst_price !== undefined) {
                return this.env.utils.formatCurrency(product.lst_price);
            }
        } catch {
            // fallback
        }
        return product.lst_price !== undefined ? `${product.lst_price}` : "";
    },

    onIncreaseQty(ev) {
        if (ev) {
            ev.stopPropagation();
            ev.preventDefault();
        }
        const lines = this.getOrderLines();
        if (lines.length > 0) {
            const lastLine = lines.at(-1);
            lastLine.setQuantity(lastLine.qty + 1);
        } else {
            if (typeof this.props.onClick === "function") {
                this.props.onClick(ev);
            } else if (this.pos) {
                this.pos.addLineToCurrentOrder({ product_tmpl_id: this.props.product });
            }
        }
    },

    onDecreaseQty(ev) {
        if (ev) {
            ev.stopPropagation();
            ev.preventDefault();
        }
        const order = this.pos?.getOrder();
        if (!order) {
            return;
        }
        const lines = this.getOrderLines();
        if (!lines.length) {
            return;
        }
        const lastLine = lines.at(-1);
        if (lastLine.qty > 1) {
            lastLine.setQuantity(lastLine.qty - 1);
        } else {
            order.removeOrderline(lastLine);
        }
    },
});
