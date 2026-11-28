/** @odoo-module */

import { Domain } from "@web/core/domain";
import { patch } from "@web/core/utils/patch";
import { SearchModel } from "@web/search/search_model";

const PRODUCT_MODELS = new Set(["product.template", "product.product"]);

patch(SearchModel.prototype, {
    _getFilterDomain(excludedFilterId) {
        if (!PRODUCT_MODELS.has(this.resModel)) {
            return super._getFilterDomain(...arguments);
        }
        const subDomains = [];

        const addCondition = (fieldName, valueMap) => {
            const ids = [];
            for (const [valueId, value] of valueMap) {
                if (value.checked) {
                    ids.push(valueId);
                }
            }
            if (!ids.length) {
                return;
            }
            if (fieldName === "pos_config_ids") {
                subDomains.push(
                    new Domain(["|", [fieldName, "=", false], [fieldName, "in", ids]])
                );
            } else {
                subDomains.push(new Domain([[fieldName, "in", ids]]));
            }
        };

        for (const filter of this.filters) {
            if (filter.id === excludedFilterId) {
                continue;
            }
            const { fieldName, groups, values } = filter;
            if (groups) {
                for (const group of groups.values()) {
                    addCondition(fieldName, group.values);
                }
            } else {
                addCondition(fieldName, values);
            }
        }
        return subDomains.length ? Domain.and(subDomains).toList() : [];
    },

    async _reloadSections() {
        const catSection = PRODUCT_MODELS.has(this.resModel)
            ? [...(this.sections?.values() || [])].find(
                  (s) => s.type === "filter" && s.fieldName === "pos_categ_ids"
              )
            : null;
        const prevChecked = catSection
            ? [...catSection.values.entries()].filter(([, v]) => v.checked).map(([id]) => id)
            : [];

        await super._reloadSections(...arguments);

        if (catSection && prevChecked.length && this.sectionsPromise) {
            await this.sectionsPromise;
            const dropped = prevChecked.some((id) => !catSection.values.has(id));
            if (dropped) {
                this._reset();
            }
        }
    },
});
