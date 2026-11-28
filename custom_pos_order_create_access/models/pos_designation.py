# -*- coding: utf-8 -*-
from odoo import models, fields


class PosDesignation(models.Model):
    _name = 'pos.designation'
    _description = 'POS User Designation'
    _order = 'name'

    name = fields.Char(string='Designation Name', required=True)
    allow_create_pos_order = fields.Boolean(
        string='Allow Create POS Orders by Default',
        default=False,
        help='If enabled, selecting this designation will automatically turn ON POS Order creation for the user.'
    )
