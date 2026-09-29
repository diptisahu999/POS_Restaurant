# -*- coding: utf-8 -*-
from . import models

def post_init_hook(env):
    """Setup default payment methods (UPI / Online, Gift Card (GC)) and attach to POS configs."""
    models.pos_config._setup_custom_bill_payment_methods(env)
