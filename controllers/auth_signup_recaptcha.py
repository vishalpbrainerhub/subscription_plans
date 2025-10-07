# -*- coding: utf-8 -*-

import requests
import logging
import werkzeug
from werkzeug.urls import url_encode
from odoo import http, _
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AuthSignupRecaptcha(AuthSignupHome):
    """Extend Odoo's signup controller to add reCAPTCHA v2 validation"""

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        """Override signup to add reCAPTCHA validation"""
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        # Add reCAPTCHA site key to context
        recaptcha_site_key = request.env['ir.config_parameter'].sudo().get_param(
            'subscription_plans.recaptcha_v2_site_key'
        )
        qcontext['recaptcha_site_key'] = recaptcha_site_key
        
        # Debug logging
        _logger.info("reCAPTCHA site key: %s", recaptcha_site_key)

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            # Validate reCAPTCHA first
            if not self._verify_recaptcha_v2():
                qcontext['error'] = _('Please complete the verification and try again.')
            else:
                try:
                    self.do_signup(qcontext)
                    # Send an account creation confirmation email
                    User = request.env['res.users']
                    user_sudo = User.sudo().search(
                        User._get_login_domain(qcontext.get('login')), order=User._get_login_order(), limit=1
                    )
                    template = request.env.ref('auth_signup.mail_template_user_signup_account_created', raise_if_not_found=False)
                    if user_sudo and template:
                        template.sudo().send_mail(user_sudo.id, force_send=True)
                    return self.web_login(*args, **kw)
                except UserError as e:
                    qcontext['error'] = e.args[0]
                except (SignupError, AssertionError) as e:
                    if request.env["res.users"].sudo().search([("login", "=", qcontext.get("login"))]):
                        qcontext["error"] = _("Another user is already registered using this email address.")
                    else:
                        _logger.error("%s", e)
                        qcontext['error'] = _("Could not create a new account.")

        elif 'signup_email' in qcontext:
            user = request.env['res.users'].sudo().search([('email', '=', qcontext.get('signup_email')), ('state', '!=', 'new')], limit=1)
            if user:
                return request.redirect('/web/login?%s' % url_encode({'login': user.login, 'redirect': '/web'}))

        response = request.render('subscription_plans.signup_with_recaptcha', qcontext)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    @http.route('/web/reset_password', type='http', auth='public', website=True, sitemap=False)
    def web_auth_reset_password(self, *args, **kw):
        """Override reset password to add reCAPTCHA validation"""
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('reset_password_enabled'):
            raise werkzeug.exceptions.NotFound()

        # Add reCAPTCHA site key to context
        recaptcha_site_key = request.env['ir.config_parameter'].sudo().get_param(
            'subscription_plans.recaptcha_v2_site_key'
        )
        qcontext['recaptcha_site_key'] = recaptcha_site_key

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            # Validate reCAPTCHA first (only for initial email submission, not token-based reset)
            if not qcontext.get('token') and not self._verify_recaptcha_v2():
                qcontext['error'] = _('Please complete the verification and try again.')
            else:
                try:
                    if qcontext.get('token'):
                        self.do_signup(qcontext)
                        return self.web_login(*args, **kw)
                    else:
                        login = qcontext.get('login')
                        assert login, _("No login provided.")
                        _logger.info(
                            "Password reset attempt for <%s> by user <%s> from %s",
                            login, request.env.user.login, request.httprequest.remote_addr)
                        request.env['res.users'].sudo().reset_password(login)
                        qcontext['message'] = _("Password reset instructions sent to your email")
                except UserError as e:
                    qcontext['error'] = e.args[0]
                except SignupError:
                    qcontext['error'] = _("Could not reset your password")
                    _logger.exception('error when resetting password')
                except Exception as e:
                    qcontext['error'] = str(e)

        elif 'signup_email' in qcontext:
            user = request.env['res.users'].sudo().search([('email', '=', qcontext.get('signup_email')), ('state', '!=', 'new')], limit=1)
            if user:
                return request.redirect('/web/login?%s' % url_encode({'login': user.login, 'redirect': '/web'}))

        response = request.render('subscription_plans.reset_password_with_recaptcha', qcontext)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    def _verify_recaptcha_v2(self):
        """Verify reCAPTCHA v2 response"""
        recaptcha_response = request.params.get('g-recaptcha-response')
        if not recaptcha_response:
            return False
        
        # Get secret key
        secret_key = request.env['ir.config_parameter'].sudo().get_param(
            'subscription_plans.recaptcha_v2_secret_key'
        )
        
        if not secret_key:
            _logger.warning("reCAPTCHA v2 secret key not configured")
            return True  # If not configured, skip validation
        
        # Verify with Google
        try:
            response = requests.post(
                'https://www.google.com/recaptcha/api/siteverify',
                data={
                    'secret': secret_key,
                    'response': recaptcha_response,
                    'remoteip': request.httprequest.remote_addr,
                },
                timeout=5
            )
            
            result = response.json()
            
            if not result.get('success', False):
                _logger.warning("reCAPTCHA v2 verification failed: %s", result.get('error-codes', []))
                return False
            
            return True
            
        except Exception as e:
            _logger.error("reCAPTCHA v2 verification error: %s", e)
            return False
