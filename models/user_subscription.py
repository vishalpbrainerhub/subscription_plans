# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta


class UserSubscription(models.Model):
    _name = 'user.subscription'
    _description = 'User Subscription'
    _order = 'create_date desc'

    name = fields.Char(string='Subscription Name', compute='_compute_name', store=True)
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    plan_id = fields.Many2one('subscription.plan', string='Subscription Plan', required=True)
    
    # Status and Dates
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True)
    
    start_date = fields.Datetime(string='Start Date', default=fields.Datetime.now)
    end_date = fields.Datetime(string='End Date')
    is_trial = fields.Boolean(string='Is Trial', default=False)
    
    # Payment Information (for future integration)
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded')
    ], string='Payment Status', default='pending')
    
    amount_paid = fields.Float(string='Amount Paid', digits='Product Price')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    
    # Usage Tracking
    private_decks_count = fields.Integer(string='Private Decks Created', default=0)
    last_activity_date = fields.Datetime(string='Last Activity')
    
    # Related fields for easy access
    plan_type = fields.Selection(related='plan_id.plan_type', string='Plan Type', store=True)
    max_private_decks = fields.Integer(related='plan_id.max_private_decks', string='Max Private Decks')
    max_cards_per_deck = fields.Integer(related='plan_id.max_cards_per_deck', string='Max Cards Per Deck')
    
    @api.depends('user_id', 'plan_id')
    def _compute_name(self):
        for subscription in self:
            if subscription.user_id and subscription.plan_id:
                subscription.name = f"{subscription.user_id.name} - {subscription.plan_id.name}"
            else:
                subscription.name = "New Subscription"
    
    @api.model
    def get_user_subscription(self, user_id=None):
        """Get the active subscription for a user"""
        if not user_id:
            user_id = self.env.user.id
        
        subscription = self.search([
            ('user_id', '=', user_id),
            ('state', '=', 'active')
        ], limit=1)
        
        if not subscription:
            # Create a default free subscription for the user
            default_plan = self.env['subscription.plan'].get_default_plan()
            if default_plan:
                subscription = self.create({
                    'user_id': user_id,
                    'plan_id': default_plan.id,
                    'state': 'active',
                    'start_date': fields.Datetime.now(),
                })
        
        return subscription
    
    @api.model
    def create_subscription(self, user_id, plan_id, payment_success=False):
        """Create a new subscription for a user"""
        # Deactivate existing subscriptions
        existing_subscriptions = self.search([
            ('user_id', '=', user_id),
            ('state', '=', 'active')
        ])
        existing_subscriptions.write({'state': 'expired'})
        
        # Create new subscription
        vals = {
            'user_id': user_id,
            'plan_id': plan_id,
            'state': 'active',
            'start_date': fields.Datetime.now(),
        }
        
        # Set payment status based on plan type
        plan = self.env['subscription.plan'].browse(plan_id)
        if plan.plan_type == 'premium':
            vals['payment_status'] = 'paid' if payment_success else 'pending'
            vals['amount_paid'] = plan.price if payment_success else 0
        else:
            vals['payment_status'] = 'paid'  # Free plans are always "paid"
            vals['amount_paid'] = 0
        
        return self.create(vals)
    
    def activate_subscription(self):
        """Activate the subscription"""
        self.ensure_one()
        self.state = 'active'
        self.start_date = fields.Datetime.now()
        
        # Set end date for premium plans (1 year from now)
        if self.plan_id.plan_type == 'premium':
            self.end_date = fields.Datetime.now() + timedelta(days=365)
    
    def can_create_private_deck(self):
        """Check if user can create another private deck"""
        self.ensure_one()
        if self.max_private_decks == 0:  # Unlimited
            return True
        return self.private_decks_count < self.max_private_decks
    
    def increment_deck_count(self):
        """Increment the private deck count"""
        self.ensure_one()
        self.private_decks_count += 1
        self.last_activity_date = fields.Datetime.now()
    
    @api.model
    def check_expired_subscriptions(self):
        """Check and expire subscriptions (called by cron)"""
        expired_subscriptions = self.search([
            ('state', '=', 'active'),
            ('end_date', '!=', False),
            ('end_date', '<', fields.Datetime.now())
        ])
        
        expired_subscriptions.write({'state': 'expired'})
        
        # Optionally notify users about expiration
        for subscription in expired_subscriptions:
            # TODO: Send email notification about expiration
            pass
        
        return len(expired_subscriptions)


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    subscription_ids = fields.One2many('user.subscription', 'user_id', string='Subscriptions')
    current_subscription_id = fields.Many2one('user.subscription', string='Current Subscription',
                                              compute='_compute_current_subscription')
    subscription_plan_type = fields.Selection(related='current_subscription_id.plan_type',
                                              string='Current Plan Type')
    
    @api.depends('subscription_ids.state')
    def _compute_current_subscription(self):
        for user in self:
            subscription = user.subscription_ids.filtered(lambda s: s.state == 'active')
            user.current_subscription_id = subscription[0] if subscription else False 