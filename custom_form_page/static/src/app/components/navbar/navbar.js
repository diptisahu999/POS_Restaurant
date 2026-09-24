/** @odoo-module **/

import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    async onClickHomeButton() {
        if (typeof this.canClick === "function" && !this.canClick()) {
            return false;
        }
        await this.pos.closePos();
    },
});
