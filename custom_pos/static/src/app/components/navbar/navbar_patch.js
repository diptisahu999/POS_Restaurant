/** @odoo-module */

import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    get showCreateProductButton() {
        return super.showCreateProductButton && this.pos.router?.state?.current !== "FloorScreen";
    },
});
