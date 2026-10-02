/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        if (!this.getOrder()) {
            const newOrder = this.addNewOrder();
            if (newOrder) {
                this.setOrder(newOrder);
            }
        }
        return await super.addLineToCurrentOrder(...arguments);
    },

    async editProduct(product) {
        if (product) {
            return super.editProduct(...arguments);
        }

        const orderContainsProduct = false;
        this.action.doAction("point_of_sale.product_template_action_add_pos", {
            props: {
                resId: undefined,
                onSave: async (record) => {
                    const tmplId = record.evalContext?.id || record.resId;
                    const isOneTime = Boolean(record.data?.is_one_time);

                    await this.data.read("product.template", [tmplId]);
                    await this.data.searchRead("product.product", [
                        ["product_tmpl_id", "=", tmplId],
                    ]);

                    this.action.doAction({
                        type: "ir.actions.act_window_close",
                    });

                    const productTmpl = this.models["product.template"].get(tmplId);
                    let productVariant = productTmpl?.product_variant_ids?.[0];
                    if (!productVariant) {
                        productVariant = this.models["product.product"].find(
                            (p) => p.product_tmpl_id?.id === tmplId || p.product_tmpl_id === tmplId
                        );
                    }

                    if (isOneTime || productTmpl?.is_one_time) {
                        if (productTmpl) {
                            productTmpl.is_one_time = true;
                            productTmpl.available_in_pos = false;
                        }
                        if (productVariant) {
                            productVariant.is_one_time = true;
                            productVariant.available_in_pos = false;
                        }

                        let order = this.getOrder();
                        if (!order) {
                            order = this.addNewOrder();
                            if (order) {
                                this.setOrder(order);
                            }
                        }

                        if (order && productTmpl) {
                            const orderVals = {
                                product_tmpl_id: productTmpl,
                            };
                            if (productVariant) {
                                orderVals.product_id = productVariant;
                            }

                            await this.addLineToCurrentOrder(orderVals);
                            this.navigateToOrderScreen(order);
                            this.notification.add(
                                _t(
                                    "One-time product '%s' added to current bill.",
                                    record.data?.name || productTmpl?.name || ""
                                ),
                                { type: "info" }
                            );

                            // Archive the product so it's invisible in ALL product lists
                            // (Inventory, backend, etc.) while the bill still references it.
                            try {
                                await this.env.services.orm.call(
                                    "product.template",
                                    "archive_one_time_product",
                                    [tmplId]
                                );
                            } catch (e) {
                                console.warn("Could not archive one-time product:", e);
                            }
                        }
                    }
                },
            },
            additionalContext: {
                taxes_readonly: orderContainsProduct,
                default_is_storable: false,
            },
        });
    },

    filterExcludedProducts(products) {
        const filtered = super.filterExcludedProducts(products);
        return filtered.filter((p) => !p.is_one_time && p.available_in_pos !== false);
    },
});
