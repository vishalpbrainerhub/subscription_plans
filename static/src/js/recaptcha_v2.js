/**
 * reCAPTCHA v2 Integration for Subscription Plans
 */
odoo.define('subscription_plans.recaptcha_v2', function (require) {
'use strict';

var core = require('web.core');
var dom = require('web.dom');
var session = require('web.session');

var _t = core._t;

var RecaptchaV2 = {
    
    // Configuration
    siteKey: null,
    loaded: false,
    
    init: function(siteKey) {
        this.siteKey = siteKey;
    },
    
    /**
     * Load the reCAPTCHA v2 script
     */
    loadScript: function() {
        var self = this;
        return new Promise(function(resolve, reject) {
            if (self.loaded) {
                resolve();
                return;
            }
            
            var script = document.createElement('script');
            script.src = 'https://www.google.com/recaptcha/api.js?render=explicit&onload=onRecaptchaLoad';
            script.async = true;
            script.defer = true;
            
            // Global callback for when reCAPTCHA loads
            window.onRecaptchaLoad = function() {
                self.loaded = true;
                resolve();
            };
            
            script.onerror = function() {
                reject(new Error('Failed to load reCAPTCHA script'));
            };
            
            document.head.appendChild(script);
        });
    },
    
    /**
     * Render reCAPTCHA widget
     */
    render: function(elementId, callback) {
        var self = this;
        return this.loadScript().then(function() {
            if (!window.grecaptcha) {
                throw new Error('reCAPTCHA not loaded');
            }
            
            return window.grecaptcha.render(elementId, {
                'sitekey': self.siteKey,
                'callback': callback || function(response) {
                    console.log('reCAPTCHA response:', response);
                },
                'expired-callback': function() {
                    console.log('reCAPTCHA expired');
                }
            });
        });
    },
    
    /**
     * Get reCAPTCHA response
     */
    getResponse: function(widgetId) {
        if (!window.grecaptcha) {
            return null;
        }
        
        if (widgetId !== undefined) {
            return window.grecaptcha.getResponse(widgetId);
        } else {
            return window.grecaptcha.getResponse();
        }
    },
    
    /**
     * Reset reCAPTCHA widget
     */
    reset: function(widgetId) {
        if (!window.grecaptcha) {
            return;
        }
        
        if (widgetId !== undefined) {
            window.grecaptcha.reset(widgetId);
        } else {
            window.grecaptcha.reset();
        }
    },
    
    /**
     * Validate form with reCAPTCHA
     */
    validateForm: function(formElement) {
        var response = this.getResponse();
        if (!response) {
            this.showError(_t('Please complete the reCAPTCHA verification.'));
            return false;
        }
        
        // Add the response to the form
        var input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'g-recaptcha-response';
        input.value = response;
        formElement.appendChild(input);
        
        return true;
    },
    
    /**
     * Show error message
     */
    showError: function(message) {
        var errorDiv = document.querySelector('.recaptcha-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger recaptcha-error';
            var recaptchaDiv = document.querySelector('.recaptcha-container');
            if (recaptchaDiv) {
                recaptchaDiv.appendChild(errorDiv);
            }
        }
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    },
    
    /**
     * Hide error message
     */
    hideError: function() {
        var errorDiv = document.querySelector('.recaptcha-error');
        if (errorDiv) {
            errorDiv.style.display = 'none';
        }
    }
};

// Auto-initialize for signup forms
document.addEventListener('DOMContentLoaded', function() {
    console.log('reCAPTCHA v2 script loaded');
    
    var signupForm = document.querySelector('.oe_signup_form');
    var recaptchaDiv = document.querySelector('#recaptcha-container');
    
    console.log('Signup form found:', !!signupForm);
    console.log('reCAPTCHA container found:', !!recaptchaDiv);
    
    if (signupForm && recaptchaDiv) {
        // Get site key from data attribute
        var siteKey = recaptchaDiv.dataset.sitekey;
        console.log('reCAPTCHA site key:', siteKey);
        
        if (siteKey) {
            RecaptchaV2.init(siteKey);
            
            // Render reCAPTCHA
            RecaptchaV2.render('recaptcha-container', function(response) {
                console.log('reCAPTCHA completed:', response);
                RecaptchaV2.hideError();
            }).catch(function(error) {
                console.error('reCAPTCHA render error:', error);
            });
            
            // Handle form submission
            signupForm.addEventListener('submit', function(e) {
                console.log('Form submission attempted');
                if (!RecaptchaV2.validateForm(signupForm)) {
                    console.log('reCAPTCHA validation failed');
                    e.preventDefault();
                    return false;
                }
                console.log('reCAPTCHA validation passed');
            });
        } else {
            console.warn('No reCAPTCHA site key found');
        }
    } else {
        console.warn('Required elements not found for reCAPTCHA initialization');
    }
});

return RecaptchaV2;

});
