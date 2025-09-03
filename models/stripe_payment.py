# -*- coding: utf-8 -*-

import logging
import stripe
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StripePayment(models.Model):
    _name = 'stripe.payment'
    _description = 'Stripe Payment Transaction'
    _order = 'create_date desc'

    name = fields.Char(string='Payment Reference', compute='_compute_name', store=True)
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    subscription_id = fields.Many2one('user.subscription', string='Subscription', ondelete='cascade')
    plan_id = fields.Many2one('subscription.plan', string='Plan', required=True)
    
    # Stripe Information
    stripe_payment_intent_id = fields.Char(string='Stripe Payment Intent ID', required=True)
    stripe_payment_method_id = fields.Char(string='Stripe Payment Method ID')
    stripe_customer_id = fields.Char(string='Stripe Customer ID')
    
    # Payment Details
    amount = fields.Float(string='Amount', digits='Product Price', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                  default=lambda self: self.env.company.currency_id)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded')
    ], string='Status', default='draft', required=True)
    
    # Metadata
    stripe_metadata = fields.Text(string='Stripe Metadata')
    payment_date = fields.Datetime(string='Payment Date')
    failure_reason = fields.Text(string='Failure Reason')
    
    @api.depends('user_id', 'plan_id', 'amount')
    def _compute_name(self):
        for payment in self:
            if payment.user_id and payment.plan_id:
                payment.name = f"{payment.user_id.name} - {payment.plan_id.name} - ${payment.amount}"
            else:
                payment.name = "New Payment"
    
    @api.model
    def get_stripe_config(self):
        """Get Stripe configuration from system parameters"""
        config = self.env['ir.config_parameter'].sudo()
        
        publishable_key = config.get_param('subscription_plans.stripe_publishable_key')
        secret_key = config.get_param('subscription_plans.stripe_secret_key')
        webhook_secret = config.get_param('subscription_plans.stripe_webhook_secret')
        test_mode = config.get_param('subscription_plans.stripe_test_mode', 'True') == 'True'
        
        if not secret_key or not publishable_key:
            raise UserError(_("Stripe API keys are not configured. Please configure them in Settings."))
        
        return {
            'publishable_key': publishable_key,
            'secret_key': secret_key,
            'webhook_secret': webhook_secret,
            'test_mode': test_mode
        }
    
    @api.model
    def create_payment_intent(self, user_id, plan_id, amount):
        """Create a Stripe Payment Intent"""
        config = self.get_stripe_config()
        stripe.api_key = config['secret_key']
        
        user = self.env['res.users'].browse(user_id)
        plan = self.env['subscription.plan'].browse(plan_id)
        
        try:
            # Create or get Stripe customer
            customer = self._get_or_create_stripe_customer(user, config)
            
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Stripe expects amount in cents
                currency='usd',
                customer=customer.id,
                metadata={
                    'user_id': user_id,
                    'plan_id': plan_id,
                    'plan_name': plan.name,
                    'odoo_env': self.env.cr.dbname
                },
                automatic_payment_methods={
                    'enabled': True,
                },
            )
            
            # Create payment record
            payment = self.create({
                'user_id': user_id,
                'plan_id': plan_id,
                'stripe_payment_intent_id': intent.id,
                'stripe_customer_id': customer.id,
                'amount': amount,
                'state': 'processing',
                'stripe_metadata': str(intent.metadata)
            })
            
            return {
                'payment_id': payment.id,
                'client_secret': intent.client_secret,
                'publishable_key': config['publishable_key']
            }
            
        except stripe.error.StripeError as e:
            _logger.error(f"Stripe error creating payment intent: {str(e)}")
            raise UserError(_("Payment processing error: %s") % str(e))
    
    def _get_or_create_stripe_customer(self, user, config):
        """Get existing or create new Stripe customer"""
        stripe.api_key = config['secret_key']
        
        # Try to find existing customer by email
        try:
            customers = stripe.Customer.list(email=user.email, limit=1)
            if customers.data:
                return customers.data[0]
        except stripe.error.StripeError:
            pass
        
        # Create new customer
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
                metadata={
                    'user_id': user.id,
                    'odoo_env': self.env.cr.dbname
                }
            )
            return customer
        except stripe.error.StripeError as e:
            _logger.error(f"Error creating Stripe customer: {str(e)}")
            raise UserError(_("Error creating customer: %s") % str(e))
    
    def confirm_payment(self):
        """Confirm successful payment and activate subscription"""
        self.ensure_one()
        
        if self.state != 'succeeded':
            raise UserError(_("Cannot confirm payment that is not successful"))
        
        # Create or update subscription
        if not self.subscription_id:
            subscription = self.env['user.subscription'].sudo().create_subscription(
                self.user_id.id, 
                self.plan_id.id, 
                payment_success=True
            )
            self.subscription_id = subscription.id
        
        # Activate subscription
        self.subscription_id.activate_subscription()
        self.subscription_id.write({
            'payment_status': 'paid',
            'amount_paid': self.amount
        })
        
        return True
    
    def handle_webhook_event(self, event_data):
        """Handle Stripe webhook events"""
        event_type = event_data.get('type')
        payment_intent = event_data.get('data', {}).get('object', {})
        
        payment = self.search([
            ('stripe_payment_intent_id', '=', payment_intent.get('id'))
        ], limit=1)
        
        if not payment:
            _logger.warning(f"Payment not found for Stripe webhook: {payment_intent.get('id')}")
            return False
        
        if event_type == 'payment_intent.succeeded':
            payment.write({
                'state': 'succeeded',
                'payment_date': fields.Datetime.now(),
                'stripe_payment_method_id': payment_intent.get('payment_method')
            })
            payment.confirm_payment()
            
        elif event_type == 'payment_intent.payment_failed':
            failure_reason = payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')
            payment.write({
                'state': 'failed',
                'failure_reason': failure_reason
            })
            
        return True


class UserSubscription(models.Model):
    _inherit = 'user.subscription'
    
    stripe_payment_ids = fields.One2many('stripe.payment', 'subscription_id', string='Stripe Payments')
    stripe_customer_id = fields.Char(string='Stripe Customer ID', 
                                     compute='_compute_stripe_customer_id', store=True)
    
    @api.depends('stripe_payment_ids.stripe_customer_id')
    def _compute_stripe_customer_id(self):
        for subscription in self:
            if subscription.stripe_payment_ids:
                subscription.stripe_customer_id = subscription.stripe_payment_ids[0].stripe_customer_id
            else:
                subscription.stripe_customer_id = False
