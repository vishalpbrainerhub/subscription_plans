# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    recaptcha_v2_site_key = fields.Char(
        string="reCAPTCHA v2 Site Key",
        config_parameter='subscription_plans.recaptcha_v2_site_key',
        help="Your reCAPTCHA v2 site key from Google reCAPTCHA admin console"
    )
    
    recaptcha_v2_secret_key = fields.Char(
        string="reCAPTCHA v2 Secret Key",
        config_parameter='subscription_plans.recaptcha_v2_secret_key',
        help="Your reCAPTCHA v2 secret key from Google reCAPTCHA admin console"
    )
    
    # Stripe Configuration
    stripe_publishable_key = fields.Char(
        string="Stripe Publishable Key",
        config_parameter='subscription_plans.stripe_publishable_key',
        help="Your Stripe publishable key (pk_test_... for test mode, pk_live_... for live mode)"
    )
    
    stripe_secret_key = fields.Char(
        string="Stripe Secret Key",
        config_parameter='subscription_plans.stripe_secret_key',
        help="Your Stripe secret key (sk_test_... for test mode, sk_live_... for live mode)"
    )
    
    stripe_webhook_secret = fields.Char(
        string="Stripe Webhook Secret",
        config_parameter='subscription_plans.stripe_webhook_secret',
        help="Your Stripe webhook endpoint secret for payment confirmations"
    )
    
    stripe_test_mode = fields.Boolean(
        string="Stripe Test Mode",
        config_parameter='subscription_plans.stripe_test_mode',
        default=True,
        help="Enable to use test mode for Stripe payments"
    )