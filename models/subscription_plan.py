# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SubscriptionPlan(models.Model):
    _name = 'subscription.plan'
    _description = 'Subscription Plan'
    _order = 'sequence, id'

    name = fields.Char(string='Plan Name', required=True, translate=True)
    code = fields.Char(string='Plan Code', required=True, help='Unique identifier for the plan')
    sequence = fields.Integer(string='Sequence', default=10, help='Order of display')
    description = fields.Text(string='Description', translate=True)
    short_description = fields.Char(string='Short Description', translate=True)
    
    # Plan Type
    plan_type = fields.Selection([
        ('try_out', 'Try Out'),
        ('free', 'Free'),
        ('premium', 'Premium')
    ], string='Plan Type', required=True, default='free')
    
    # Pricing
    price = fields.Float(string='Price', digits='Product Price')
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                  default=lambda self: self.env.company.currency_id)
    
    # Features and Limitations
    max_private_decks = fields.Integer(string='Max Private Decks', default=0,
                                       help='Maximum number of private decks allowed (0 = unlimited)')
    max_cards_per_deck = fields.Integer(string='Max Cards Per Deck', default=0,
                                        help='Maximum cards per deck (0 = unlimited)')
    
    # Access Rights
    can_create_decks = fields.Boolean(string='Can Create Decks', default=False)
    can_access_public_decks = fields.Boolean(string='Can Access Public Decks', default=True)
    can_access_premium_content = fields.Boolean(string='Can Access Premium Content', default=False)
    can_use_ai_generation = fields.Boolean(string='Can Use AI Generation', default=False)
    requires_registration = fields.Boolean(string='Requires Registration', default=True)
    
    # Display and Status
    is_active = fields.Boolean(string='Active', default=True)
    is_popular = fields.Boolean(string='Popular Plan', default=False, help='Mark as popular for highlighting')
    color = fields.Char(string='Color Code', help='Hex color code for UI styling')
    icon = fields.Char(string='Icon Class', help='Font Awesome icon class')
    
    # Features List
    feature_ids = fields.One2many('subscription.plan.feature', 'plan_id', string='Features')
    
    @api.model
    def get_default_plan(self):
        """Get the default plan for new users"""
        return self.search([('plan_type', '=', 'free'), ('is_active', '=', True)], limit=1)
    
    @api.model
    def get_try_out_plan(self):
        """Get the try out plan for unregistered users"""
        return self.search([('plan_type', '=', 'try_out'), ('is_active', '=', True)], limit=1)


class SubscriptionPlanFeature(models.Model):
    _name = 'subscription.plan.feature'
    _description = 'Subscription Plan Feature'
    _order = 'sequence, id'

    name = fields.Char(string='Feature', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_highlighted = fields.Boolean(string='Highlighted', default=False,
                                    help='Show this feature prominently')
    icon = fields.Char(string='Icon Class', help='Font Awesome icon class')
    plan_id = fields.Many2one('subscription.plan', string='Plan', required=True, ondelete='cascade') 