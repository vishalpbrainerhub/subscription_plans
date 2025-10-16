# -*- coding: utf-8 -*-

import json
import logging
import stripe
from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SubscriptionController(http.Controller):

    @http.route('/subscription/signup/<int:plan_id>', type='http', auth='public', website=True)
    def subscription_signup(self, plan_id, **kwargs):
        """Store plan info and redirect to standard Odoo signup"""
        plan = request.env['subscription.plan'].sudo().browse(plan_id)
        
        if not plan.exists():
            return request.not_found()
        
        # Store selected plan in session for after registration
        request.session['selected_plan_id'] = plan_id
        request.session['selected_plan_name'] = plan.name
        
        # Redirect to Odoo's standard signup page with redirect parameter
        return request.redirect('/web/signup?redirect=/subscription/activate')

    @http.route('/subscription', type='http', auth='public', website=True)
    def subscription_page(self, **kwargs):
        """Display the main subscription page with enhanced comparison features"""
        plans = request.env['subscription.plan'].sudo().search([
            ('is_active', '=', True)
        ], order='sequence, id')
        
        # Get current user's subscription if authenticated
        current_subscription = None
        if request.env.user and not request.env.user._is_public():
            user_subscription_model = request.env['user.subscription'].sudo()
            current_subscription = user_subscription_model.get_user_subscription(request.env.user.id)
        
        values = {
            'plans': plans,
            'current_subscription': current_subscription,
            'page_name': 'subscription',
        }
        
        return request.render('subscription_plans.subscription_page_new', values)

    @http.route('/subscription/plans', type='http', auth='public', website=True)
    def subscription_plans(self, **kwargs):
        """Display subscription plans page"""
        plans = request.env['subscription.plan'].sudo().search([
            ('is_active', '=', True)
        ], order='sequence, id')
        
        values = {
            'plans': plans,
            'page_name': 'subscription_plans',
        }
        
        return request.render('subscription_plans.subscription_plans_page', values)

    @http.route('/subscription/select/<int:plan_id>', type='http', auth='public', website=True)
    def select_plan(self, plan_id, billing_period='monthly', **kwargs):
        """Handle plan selection"""
        plan = request.env['subscription.plan'].sudo().browse(plan_id)
        
        if not plan.exists():
            return request.not_found()
        
        _logger.info(f"🎯 PLAN SELECTED: {plan.name} ({billing_period}) by user: {request.env.user.name if not request.env.user._is_public() else 'Anonymous'}")
        
        # Handle Try Out plan (no registration required)
        if plan.plan_type == 'try_out':
            # Set session variable for try out mode
            request.session['try_out_mode'] = True
            _logger.info(f"🆓 TRY OUT MODE: User accessing try out plan")
            return request.redirect('/decks')
        
        # For other plans, check if user is logged in
        if not request.env.user or request.env.user._is_public():
            # Store billing period in session for after registration
            request.session['selected_billing_period'] = billing_period
            # Redirect to custom signup route with reCAPTCHA v2
            return request.redirect(f'/subscription/signup/{plan_id}')
        
        # User is logged in, proceed with plan selection
        return self._process_plan_selection(plan, billing_period)

    def _process_plan_selection(self, plan, billing_period='monthly'):
        """Process the plan selection for logged in users"""
        user = request.env.user
        
        if plan.plan_type == 'free':
            # Create free subscription immediately
            subscription = request.env['user.subscription'].sudo().create_subscription(
                user.id, plan.id, payment_success=True, billing_period=billing_period
            )
            
            # Check if this is an existing subscription (duplicate prevention)
            if subscription:
                subscription.activate_subscription()
                # Add a parameter to indicate if it's a new or existing subscription
                existing = request.env['user.subscription'].sudo().search_count([
                    ('user_id', '=', user.id),
                    ('plan_id', '=', plan.id),
                    ('state', '=', 'active')
                ]) > 0
                redirect_url = '/subscription/success?plan=free'
                if existing:
                    redirect_url += '&existing=true'
                return request.redirect(redirect_url)
            
            return request.redirect('/subscription/error?plan=free')
            
        elif plan.plan_type == 'premium':
            # Redirect to payment page with billing period
            return request.redirect(f'/subscription/payment/{plan.id}?billing_period={billing_period}')
        
        return request.redirect('/subscription/plans')

    @http.route('/subscription/payment/<int:plan_id>', type='http', auth='user', website=True)
    def payment_page(self, plan_id, billing_period='monthly', **kwargs):
        """Display Stripe payment page for premium plans"""
        plan = request.env['subscription.plan'].sudo().browse(plan_id)
        
        if not plan.exists() or plan.plan_type != 'premium':
            return request.not_found()
        
        _logger.info(f"💰 PAYMENT PAGE: {request.env.user.name} accessing payment for {plan.name} - billing_period={billing_period}")
        
        # Check if Stripe is configured
        try:
            stripe_config = request.env['stripe.payment'].sudo().get_stripe_config()
        except UserError as e:
            return request.render('subscription_plans.stripe_config_error', {
                'error_message': str(e),
                'plan': plan,
                'billing_period': billing_period
            })
        
        # Calculate the actual price based on billing period
        if billing_period == 'yearly':
            actual_price = plan.yearly_price if plan.yearly_price > 0 else (plan.price * 12)
        else:
            actual_price = plan.price
        
        _logger.info(f"💰 PAYMENT CALCULATION: {plan.name} - {billing_period} = ${actual_price}")
        
        values = {
            'plan': plan,
            'billing_period': billing_period,
            'actual_price': actual_price,
            'page_name': 'payment',
            'stripe_publishable_key': stripe_config['publishable_key'],
            'test_mode': stripe_config['test_mode']
        }
        
        _logger.info(f"💰 TEMPLATE VALUES: billing_period={billing_period}, actual_price={actual_price}")
        
        return request.render('subscription_plans.stripe_payment_page', values)

    @http.route('/subscription/payment/create-intent', type='json', auth='user', methods=['POST'])
    def create_payment_intent(self, plan_id, billing_period='monthly', **kwargs):
        """Create Stripe Payment Intent"""
        _logger.info(f"🔧 CREATE INTENT REQUEST: plan_id={plan_id}, billing_period={billing_period}, kwargs={kwargs}")
        
        try:
            plan = request.env['subscription.plan'].sudo().browse(int(plan_id))
            user = request.env.user
            
            if not plan.exists() or plan.plan_type != 'premium':
                return {'error': 'Invalid plan'}
            
            # Calculate the actual price based on billing period
            if billing_period == 'yearly':
                actual_price = plan.yearly_price if plan.yearly_price > 0 else (plan.price * 12)
            else:
                actual_price = plan.price
            
            _logger.info(f"🔧 INTENT CALCULATION: {plan.name} {billing_period} = ${actual_price}")
            
            # Create payment intent
            result = request.env['stripe.payment'].sudo().create_payment_intent(
                user.id, plan.id, actual_price, billing_period=billing_period
            )
            
            return {
                'success': True,
                'client_secret': result['client_secret'],
                'payment_id': result['payment_id']
            }
            
        except Exception as e:
            _logger.error(f"Error creating payment intent: {str(e)}")
            return {'error': str(e)}
    
    @http.route('/subscription/payment/confirm', type='json', auth='user', methods=['POST'])
    def confirm_payment(self, payment_intent_id, **kwargs):
        """Confirm payment success and activate subscription"""
        try:
            # Find the payment record
            payment = request.env['stripe.payment'].sudo().search([
                ('stripe_payment_intent_id', '=', payment_intent_id),
                ('user_id', '=', request.env.user.id)
            ], limit=1)
            
            if not payment:
                return {'error': 'Payment not found'}
            
            # Verify with Stripe
            config = request.env['stripe.payment'].sudo().get_stripe_config()
            stripe.api_key = config['secret_key']
            
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status == 'succeeded':
                payment.write({
                    'state': 'succeeded',
                    'payment_date': fields.Datetime.now(),
                    'stripe_payment_method_id': intent.payment_method
                })
                payment.confirm_payment()
                
                return {
                    'success': True,
                    'redirect_url': '/subscription/success?plan=premium'
                }
            else:
                return {'error': f'Payment not completed: {intent.status}'}
                
        except Exception as e:
            _logger.error(f"Error confirming payment: {str(e)}")
            return {'error': str(e)}
    
    @http.route('/subscription/stripe/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def stripe_webhook(self, **kwargs):
        """Handle Stripe webhooks"""
        try:
            payload = request.httprequest.data
            sig_header = request.httprequest.headers.get('Stripe-Signature')
            
            config = request.env['stripe.payment'].sudo().get_stripe_config()
            
            if not config.get('webhook_secret'):
                _logger.warning("Stripe webhook secret not configured")
                return request.make_response('Webhook secret not configured', status=400)
            
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, config['webhook_secret']
                )
            except ValueError:
                _logger.error("Invalid payload in Stripe webhook")
                return request.make_response('Invalid payload', status=400)
            except stripe.error.SignatureVerificationError:
                _logger.error("Invalid signature in Stripe webhook")
                return request.make_response('Invalid signature', status=400)
            
            # Handle the event
            if event['type'] in ['payment_intent.succeeded', 'payment_intent.payment_failed']:
                request.env['stripe.payment'].sudo().handle_webhook_event(event)
            
            return request.make_response('Success', status=200)
            
        except Exception as e:
            _logger.error(f"Error processing Stripe webhook: {str(e)}")
            return request.make_response('Error', status=500)

    @http.route('/subscription/success', type='http', auth='user', website=True)
    def subscription_success(self, **kwargs):
        """Display subscription success page"""
        plan_type = kwargs.get('plan', 'free')
        existing = kwargs.get('existing', 'false') == 'true'
        
        values = {
            'plan_type': plan_type,
            'existing_subscription': existing,
            'page_name': 'success',
        }
        
        return request.render('subscription_plans.subscription_success_page', values)
    
    @http.route('/subscription/error', type='http', auth='user', website=True)
    def subscription_error(self, **kwargs):
        """Display subscription error page"""
        plan_type = kwargs.get('plan', 'unknown')
        
        values = {
            'plan_type': plan_type,
            'page_name': 'error',
        }
        
        return request.render('subscription_plans.subscription_error_page', values)

    @http.route('/subscription/my', type='http', auth='user', website=True)
    def my_subscription(self, **kwargs):
        """Display user's current subscription details"""
        user = request.env.user
        subscription = request.env['user.subscription'].sudo().get_user_subscription(user.id)
        
        values = {
            'subscription': subscription,
            'page_name': 'my_subscription',
        }
        
        return request.render('subscription_plans.my_subscription_page', values)

    @http.route('/subscription/activate', type='http', auth='user', website=True)
    def activate_plan_after_signup(self, **kwargs):
        """Activate plan after user registration"""
        plan_id = request.session.get('selected_plan_id')
        plan_name = request.session.get('selected_plan_name', 'your selected plan')
        billing_period = request.session.get('selected_billing_period', 'monthly')
        
        if plan_id:
            # Clear the session variables
            request.session.pop('selected_plan_id', None)
            request.session.pop('selected_plan_name', None)
            request.session.pop('selected_billing_period', None)
            
            # Get the plan and process selection
            plan = request.env['subscription.plan'].sudo().browse(int(plan_id))
            if plan.exists():
                return self._process_plan_selection(plan, billing_period)
        
        # If no plan in session, show message and redirect to plans page
        return request.render('subscription_plans.activation_message', {
            'message': 'Welcome! Please select a subscription plan to get started.',
            'redirect_url': '/subscription'
        })

    @http.route('/subscription/upgrade/<int:plan_id>', type='http', auth='user', website=True)
    def upgrade_subscription(self, plan_id, **kwargs):
        """Handle subscription upgrade"""
        plan = request.env['subscription.plan'].sudo().browse(plan_id)
        user = request.env.user
        
        if not plan.exists():
            return request.not_found()
        
        current_subscription = request.env['user.subscription'].sudo().get_user_subscription(user.id)
        
        # Check if it's actually an upgrade
        if current_subscription and current_subscription.plan_id.sequence >= plan.sequence:
            return request.redirect('/subscription/my?error=not_upgrade')
        
        # Process the upgrade
        return self._process_plan_selection(plan)

    @http.route('/test/recaptcha', type='http', auth='public', website=True)
    def test_recaptcha(self, **kwargs):
        """Test page for reCAPTCHA v2"""
        return request.render('subscription_plans.test_recaptcha_page')




class PortalSubscription(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        """Add subscription info to portal home"""
        values = super()._prepare_home_portal_values(counters)
        
        if request.env.user and not request.env.user._is_public():
            subscription = request.env['user.subscription'].sudo().get_user_subscription()
            values['subscription'] = subscription
            
            if 'subscription_count' in counters:
                subscription_count = request.env['user.subscription'].search_count([
                    ('user_id', '=', request.env.user.id)
                ])
                values['subscription_count'] = subscription_count
            
        return values
    
    @http.route(['/my/subscription', '/my/subscription/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_subscription(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        user = request.env.user
        domain = [('user_id', '=', user.id)]

        searchbar_sortings = {
            'date': {'label': 'Newest', 'order': 'create_date desc'},
            'name': {'label': 'Name', 'order': 'name'},
            'state': {'label': 'Status', 'order': 'state'},
        }
        
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Count for pager
        subscription_count = request.env['user.subscription'].search_count(domain)
        # Pager
        pager = portal_pager(
            url="/my/subscription",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=subscription_count,
            page=page,
            step=self._items_per_page
        )

        # Content according to pager and archive selected
        subscriptions = request.env['user.subscription'].search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_subscription_history'] = subscriptions.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'subscriptions': subscriptions,
            'page_name': 'subscription',
            'archive_groups': [],
            'default_url': '/my/subscription',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("subscription_plans.portal_my_subscription", values) 