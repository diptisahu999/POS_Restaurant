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
                            if (productTmpl?.pos_categ_ids?.length && !productVariant.pos_categ_ids?.length) {
                                productVariant.pos_categ_ids = productTmpl.pos_categ_ids;
                            }
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
                default_is_one_time: true,
                ...(this.selectedCategory?.id ? { default_pos_categ_ids: [this.selectedCategory.id] } : {}),
            },
        });
    },

    _isProductAllowedInPos(p, configId) {
        if (!configId) {
            return true;
        }
        let configIds = p.pos_config_ids;
        if ((!configIds || (Array.isArray(configIds) && configIds.length === 0)) && p.product_tmpl_id) {
            configIds = p.product_tmpl_id.pos_config_ids;
        }
        if ((!configIds || (Array.isArray(configIds) && configIds.length === 0)) && p.raw?.pos_config_ids) {
            configIds = p.raw.pos_config_ids;
        }

        if (!configIds) {
            return true;
        }

        let ids = [];
        if (Array.isArray(configIds)) {
            ids = configIds.map((item) => (typeof item === "object" && item !== null ? item.id : item));
        } else if (typeof configIds === "object" && configIds !== null) {
            if (configIds.id !== undefined) {
                ids = [configIds.id];
            } else if (Symbol.iterator in configIds) {
                ids = [...configIds].map((item) => (typeof item === "object" && item !== null ? item.id : item));
            }
        } else if (typeof configIds === "number") {
            ids = [configIds];
        }

        if (ids.length === 0) {
            return true;
        }

        return ids.includes(configId);
    },

    filterExcludedProducts(products) {
        const filteredList = [];
        const excludedProductIds = new Set(this.getExcludedProductIds());
        const availableCateg = new Set(
            (this.config.iface_available_categ_ids || []).map((c) => c.id)
        );
        const configId = this.config?.id;

        for (const p of products) {
            if (filteredList.length >= 100) {
                break;
            }

            if (p.is_one_time || p.available_in_pos === false) {
                continue;
            }

            if (!this._isProductAllowedInPos(p, configId)) {
                continue;
            }

            if (excludedProductIds.has(p.id) || !p.canBeDisplayed) {
                continue;
            }

            if (
                availableCateg.size &&
                !this.config._pos_special_display_products_ids?.includes(p.id) &&
                !p.pos_categ_ids?.some((c) => availableCateg.has(c.id))
            ) {
                continue;
            }

            filteredList.push(p);
        }
        return filteredList;
    },
});
