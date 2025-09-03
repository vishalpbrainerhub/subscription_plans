// Simple reCAPTCHA v2 integration without Odoo module system
(function() {
    'use strict';

    console.log('Simple reCAPTCHA script loaded');

    // reCAPTCHA functionality
    var RecaptchaSimple = {
        loaded: false,
        siteKey: null,
        widgetId: null,

        init: function(siteKey) {
            this.siteKey = siteKey;
            console.log('reCAPTCHA initialized with key:', siteKey);
        },

        loadScript: function() {
            var self = this;
            return new Promise(function(resolve, reject) {
                if (self.loaded || window.grecaptcha) {
                    resolve();
                    return;
                }

                var script = document.createElement('script');
                script.src = 'https://www.google.com/recaptcha/api.js?render=explicit&onload=onRecaptchaLoad';
                script.async = true;
                script.defer = true;

                window.onRecaptchaLoad = function() {
                    console.log('Google reCAPTCHA API loaded');
                    self.loaded = true;
                    resolve();
                };

                script.onerror = function() {
                    console.error('Failed to load reCAPTCHA script');
                    reject(new Error('Failed to load reCAPTCHA script'));
                };

                document.head.appendChild(script);
            });
        },

        render: function(elementId) {
            var self = this;
            return this.loadScript().then(function() {
                if (!window.grecaptcha) {
                    throw new Error('reCAPTCHA not loaded');
                }

                console.log('Rendering reCAPTCHA on element:', elementId);
                self.widgetId = window.grecaptcha.render(elementId, {
                    'sitekey': self.siteKey,
                    'callback': function(response) {
                        console.log('reCAPTCHA completed:', response);
                    },
                    'expired-callback': function() {
                        console.log('reCAPTCHA expired');
                    }
                });
                
                console.log('reCAPTCHA widget ID:', self.widgetId);
                return self.widgetId;
            });
        },

        getResponse: function() {
            if (!window.grecaptcha) {
                return null;
            }
            return window.grecaptcha.getResponse(this.widgetId);
        }
    };

    // Auto-initialize when DOM is ready
    function initRecaptcha() {
        console.log('Initializing reCAPTCHA...');
        
        var recaptchaDiv = document.querySelector('#recaptcha-container');
        if (!recaptchaDiv) {
            console.log('reCAPTCHA container not found');
            return;
        }

        var siteKey = recaptchaDiv.getAttribute('data-sitekey');
        if (!siteKey) {
            console.log('reCAPTCHA site key not found');
            return;
        }

        console.log('Found reCAPTCHA container with site key:', siteKey);
        
        RecaptchaSimple.init(siteKey);
        RecaptchaSimple.render('recaptcha-container').then(function() {
            console.log('reCAPTCHA rendered successfully');
        }).catch(function(error) {
            console.error('reCAPTCHA render failed:', error);
        });

        // Handle form submission
        var forms = document.querySelectorAll('.oe_signup_form');
        forms.forEach(function(form) {
            form.addEventListener('submit', function(e) {
                var response = RecaptchaSimple.getResponse();
                console.log('Form submit - reCAPTCHA response:', response);
                
                if (!response) {
                    // Simple validation - just prevent submit, user will see the unchecked reCAPTCHA
                    e.preventDefault();
                    return false;
                }
            });
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initRecaptcha);
    } else {
        initRecaptcha();
    }

    // Make it globally available for debugging
    window.RecaptchaSimple = RecaptchaSimple;
})();
