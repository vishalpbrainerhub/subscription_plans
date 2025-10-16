# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


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
    duration_months = fields.Integer(string='Duration (Months)', default=1, help='Subscription duration in months')
    is_trial = fields.Boolean(string='Is Trial', default=False)
    
    # Billing Information
    billing_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
    ], string='Billing Period', default='monthly', help='Billing period for this subscription')
    actual_price = fields.Float(string='Actual Price Paid', digits='Product Price', 
                               help='The actual price paid for this subscription period')
    
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
    def create_subscription(self, user_id, plan_id, payment_success=False, billing_period='monthly'):
        """Create a new subscription for a user"""
        plan = self.env['subscription.plan'].browse(plan_id)
        user = self.env['res.users'].browse(user_id)
        
        _logger.info(f"🔄 CREATING SUBSCRIPTION: {user.name} -> {plan.name} ({billing_period}) - Payment: {payment_success}")
        
        # Check for existing active subscription with the same plan
        existing_same_plan = self.search([
            ('user_id', '=', user_id),
            ('plan_id', '=', plan_id),
            ('state', '=', 'active')
        ], limit=1)
        
        # If user already has the same plan active, return existing subscription
        if existing_same_plan:
            _logger.info(f"♻️ EXISTING SUBSCRIPTION: {user.name} already has {plan.name} - returning existing")
            return existing_same_plan
        
        # Check for existing active subscription with the same plan type (prevent duplicates)
        existing_same_type = self.search([
            ('user_id', '=', user_id),
            ('state', '=', 'active'),
            ('plan_id.plan_type', '=', plan.plan_type)
        ], limit=1)
        
        # If user already has an active subscription of the same type, return existing
        if existing_same_type:
            return existing_same_type
        
        # Deactivate existing subscriptions of different types
        existing_subscriptions = self.search([
            ('user_id', '=', user_id),
            ('state', '=', 'active')
        ])
        if existing_subscriptions:
            _logger.info(f"🔄 DEACTIVATING OLD SUBSCRIPTIONS: {len(existing_subscriptions)} for {user.name}")
            existing_subscriptions.write({'state': 'expired'})
        
        # Create new subscription
        vals = {
            'user_id': user_id,
            'plan_id': plan_id,
            'state': 'active',
            'start_date': fields.Datetime.now(),
            'billing_period': billing_period,
        }
        
        # Set payment status based on plan type
        if plan.plan_type == 'premium':
            vals['payment_status'] = 'paid' if payment_success else 'pending'
            
            # Calculate price and duration based on billing period
            if billing_period == 'yearly':
                vals['actual_price'] = plan.yearly_price if plan.yearly_price > 0 else (plan.price * 12)
                vals['amount_paid'] = vals['actual_price'] if payment_success else 0
                vals['duration_months'] = 12
                # Set end date for yearly plans (12 months from now)
                vals['end_date'] = fields.Datetime.now() + timedelta(days=365)
            else:  # monthly
                vals['actual_price'] = plan.price
                vals['amount_paid'] = plan.price if payment_success else 0
                vals['duration_months'] = 1
                # Set end date for monthly plans (1 month from now)
                vals['end_date'] = fields.Datetime.now() + timedelta(days=30)
        else:
            vals['payment_status'] = 'paid'  # Free plans are always "paid"
            vals['amount_paid'] = 0
            vals['actual_price'] = 0
            vals['duration_months'] = 0  # Free plans don't expire
        
        new_subscription = self.create(vals)
        _logger.info(f"✨ NEW SUBSCRIPTION CREATED: ID={new_subscription.id}, {user.name} -> {plan.name} (${vals.get('amount_paid', 0)} {billing_period})")
        
        return new_subscription
    
    def activate_subscription(self):
        """Activate the subscription"""
        self.ensure_one()
        self.state = 'active'
        self.start_date = fields.Datetime.now()
        
        # Set end date based on duration for premium plans
        if self.plan_id.plan_type == 'premium':
            # Calculate end date based on billing period
            if self.billing_period == 'yearly':
                self.end_date = fields.Datetime.now() + timedelta(days=365)
                self.duration_months = 12
            else:  # monthly (default)
                self.end_date = fields.Datetime.now() + timedelta(days=30)
                self.duration_months = 1
    
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
    
    def renew_subscription(self, months=1):
        """Renew subscription for additional months"""
        self.ensure_one()
        if self.state != 'active':
            return False
        
        if self.plan_id.plan_type == 'premium':
            # Extend end date by specified months
            current_end = self.end_date or fields.Datetime.now()
            additional_days = months * 30
            self.end_date = current_end + timedelta(days=additional_days)
            self.duration_months += months
            self.last_activity_date = fields.Datetime.now()
            return True
        return False
    
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
    
    @api.model
    def fix_existing_subscriptions_billing_period(self):
        """Fix existing subscriptions that should be yearly based on amount paid"""
        # Find subscriptions where the amount paid suggests yearly billing
        subscriptions = self.search([
            ('plan_id.plan_type', '=', 'premium'),
            ('billing_period', '=', 'monthly'),  # Currently set as monthly
            ('state', '=', 'active')
        ])
        
        _logger.info(f"Found {len(subscriptions)} premium subscriptions with monthly billing to check")
        
        fixed_count = 0
        for subscription in subscriptions:
            plan = subscription.plan_id
            
            # Check if amount paid suggests yearly billing
            should_be_yearly = False
            
            # If amount paid is >= 1000, assume it's yearly (covers custom pricing)
            if subscription.amount_paid >= 1000:
                should_be_yearly = True
                _logger.info(f"Subscription {subscription.id}: amount_paid {subscription.amount_paid} >= 1000, marking as yearly")
            # Or if amount paid is closer to yearly price than monthly price
            elif plan.yearly_price > 0 and subscription.amount_paid > 0:
                yearly_diff = abs(subscription.amount_paid - plan.yearly_price)
                monthly_diff = abs(subscription.amount_paid - plan.price)
                if yearly_diff < monthly_diff:
                    should_be_yearly = True
                    _logger.info(f"Subscription {subscription.id}: amount_paid {subscription.amount_paid} closer to yearly {plan.yearly_price} than monthly {plan.price}")
            
            if should_be_yearly:
                # This should be a yearly subscription
                _logger.info(f"Fixing subscription {subscription.id} for user {subscription.user_id.name}")
                subscription.write({
                    'billing_period': 'yearly',
                    'actual_price': subscription.amount_paid,  # Keep the actual amount paid
                    'duration_months': 12,
                    'end_date': subscription.start_date + timedelta(days=365) if subscription.start_date else fields.Datetime.now() + timedelta(days=365)
                })
                fixed_count += 1
        
        _logger.info(f"Fixed {fixed_count} subscriptions")        
        return fixed_count


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