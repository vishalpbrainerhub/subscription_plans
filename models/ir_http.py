# -*- coding: utf-8 -*-

from odoo import api, models


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @api.model
    def _add_public_key_to_session_info(self, session_info):
        """Override to prevent built-in reCAPTCHA from using our v2 keys"""
        # Don't add recaptcha_public_key to session_info to prevent v3 conflicts
        # Our subscription_plans module handles reCAPTCHA v2 separately
        return session_info
