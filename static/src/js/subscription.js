/** @odoo-module **/

import publicWidget from 'web.public.widget';
import 'web.dom_ready';

// Enhanced portal counter widget with null checks and debugging
publicWidget.registry.PortalHomeCounters.include({
    
    /**
     * Override the _updateCounters method to add null checks and debugging
     */
    async _updateCounters(elem) {
        console.log('SubscriptionPlans: Portal counters update started');
        
        try {
            const numberRpc = 3;
            const counterElements = this.el.querySelectorAll('[data-placeholder_count]');
            console.log('SubscriptionPlans: Found counter elements:', counterElements.length);
            
            if (counterElements.length === 0) {
                console.log('SubscriptionPlans: No counter elements found, skipping counter update');
                return;
            }
            
            const needed = Array.from(counterElements).map(documentsCounterEl => {
                const placeholderCount = documentsCounterEl.dataset['placeholder_count'];
                console.log('SubscriptionPlans: Processing counter element for:', placeholderCount);
                return placeholderCount;
            });
            
            const counterByRpc = Math.ceil(needed.length / numberRpc);
            const countersAlwaysDisplayed = this._getCountersAlwaysDisplayed();
            
            const proms = [...Array(Math.min(numberRpc, needed.length)).keys()].map(async i => {
                try {
                    console.log('SubscriptionPlans: Making RPC call for counters:', needed.slice(i * counterByRpc, (i + 1) * counterByRpc));
                    
                    const documentsCountersData = await this._rpc({
                        route: "/my/counters",
                        params: {
                            counters: needed.slice(i * counterByRpc, (i + 1) * counterByRpc)
                        },
                    });
                    
                    console.log('SubscriptionPlans: Received counter data:', documentsCountersData);
                    
                    Object.keys(documentsCountersData).forEach(counterName => {
                        console.log('SubscriptionPlans: Updating counter:', counterName, 'with value:', documentsCountersData[counterName]);
                        
                        const documentsCounterEl = this.el.querySelector(`[data-placeholder_count='${counterName}']`);
                        
                        if (!documentsCounterEl) {
                            console.warn('SubscriptionPlans: Counter element not found for:', counterName);
                            return;
                        }
                        
                        console.log('SubscriptionPlans: Setting textContent for:', counterName);
                        
                        // Add null check before setting textContent
                        if (documentsCounterEl && typeof documentsCounterEl.textContent !== 'undefined') {
                            documentsCounterEl.textContent = documentsCountersData[counterName];
                            
                            if (documentsCountersData[counterName] !== 0 || countersAlwaysDisplayed.includes(counterName)) {
                                if (documentsCounterEl.parentElement) {
                                    documentsCounterEl.parentElement.classList.remove('d-none');
                                }
                            }
                        } else {
                            console.error('SubscriptionPlans: Element is null or textContent property not available for:', counterName);
                        }
                    });
                    
                    return documentsCountersData;
                } catch (error) {
                    console.error('SubscriptionPlans: Error in RPC call:', error);
                    return {};
                }
            });
            
            return Promise.all(proms).then((results) => {
                console.log('SubscriptionPlans: All counter RPC calls completed');
                
                const counters = results.reduce((prev, current) => Object.assign({
                    ...prev,
                    ...current
                }), {});
                
                console.log('SubscriptionPlans: Final counter values:', counters);
                
                // Add null check for spinner element
                const spinnerElement = this.el.querySelector('.o_portal_doc_spinner');
                if (spinnerElement) {
                    spinnerElement.remove();
                    console.log('SubscriptionPlans: Removed spinner element');
                } else {
                    console.log('SubscriptionPlans: Spinner element not found, skipping removal');
                }
                
                if (!countersAlwaysDisplayed.length && !Object.values(counters).filter((val) => val > 0).length) {
                    const noDocElement = this.el.querySelector('.o_portal_no_doc_message');
                    if (noDocElement) {
                        noDocElement.classList.remove('d-none');
                        console.log('SubscriptionPlans: Showed no documents message');
                    } else {
                        console.log('SubscriptionPlans: No documents message element not found');
                    }
                }
                
                console.log('SubscriptionPlans: Portal counters update completed successfully');
            });
            
        } catch (error) {
            console.error('SubscriptionPlans: Error in _updateCounters:', error);
            // Don't throw the error, just log it to prevent breaking the page
        }
    },
});

// Enhanced Subscription Page Widget
publicWidget.registry.SubscriptionPage = publicWidget.Widget.extend({
    selector: '.subscription_page_wrap',
    events: {
        'click .quick_nav .nav-link': '_onNavClick',
        'click .subscription_btn': '_onPlanSelect',
        'mouseenter .subscription_plan_card': '_onCardHover',
        'mouseleave .subscription_plan_card': '_onCardLeave',
        'click .comparison_table tbody tr': '_onComparisonRowClick',
    },

    /**
     * Initialize the widget
     */
    start: function () {
        this._super.apply(this, arguments);
        this._initScrollSpy();
        this._initAnimations();
        this._initComparisonTable();
        return Promise.resolve();
    },

    /**
     * Initialize scroll spy for navigation
     */
    _initScrollSpy: function () {
        const $navLinks = this.$('.quick_nav .nav-link');
        const sections = ['plans-overview', 'detailed-comparison', 'subscription-faq', 'testimonials'];
        
        $(window).on('scroll', () => {
            const scrollPos = $(window).scrollTop() + 200;
            
            sections.forEach(sectionId => {
                const $section = $(`#${sectionId}`);
                if ($section.length) {
                    const sectionTop = $section.offset().top;
                    const sectionBottom = sectionTop + $section.outerHeight();
                    
                    if (scrollPos >= sectionTop && scrollPos < sectionBottom) {
                        $navLinks.removeClass('active');
                        $(`.quick_nav .nav-link[href="#${sectionId}"]`).addClass('active');
                    }
                }
            });
        });
    },

    /**
     * Handle navigation click
     */
    _onNavClick: function (ev) {
        ev.preventDefault();
        const target = $(ev.currentTarget).attr('href');
        const $target = $(target);
        
        if ($target.length) {
            $('html, body').animate({
                scrollTop: $target.offset().top - 100
            }, 800, 'easeInOutQuart');
        }
    },

    /**
     * Initialize comparison table interactions
     */
    _initComparisonTable: function () {
        // Add hover effects to comparison rows
        this.$('.comparison_table tbody tr').hover(
            function() {
                $(this).addClass('table-active');
            },
            function() {
                $(this).removeClass('table-active');
            }
        );

        // Add click to highlight feature
        this.$('.comparison_table .feature_name').click(function() {
            const $row = $(this).closest('tr');
            $row.toggleClass('highlighted-row');
            
            // Auto-remove highlight after 3 seconds
            setTimeout(() => {
                $row.removeClass('highlighted-row');
            }, 3000);
        });
    },

    /**
     * Handle comparison row click
     */
    _onComparisonRowClick: function (ev) {
        const $row = $(ev.currentTarget);
        if (!$row.hasClass('action_row')) {
            $row.addClass('pulse-row');
            setTimeout(() => {
                $row.removeClass('pulse-row');
            }, 1000);
        }
    },

    /**
     * Initialize card animations
     */
    _initAnimations: function () {
        // Animate cards on scroll
        if (typeof IntersectionObserver !== 'undefined') {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('animate-in');
                    }
                });
            }, {
                threshold: 0.1
            });

            this.$('.subscription_plan_card, .testimonial_card, .stat_item').each(function() {
                observer.observe(this);
            });
        }
    },

    /**
     * Handle plan selection
     */
    _onPlanSelect: function (ev) {
        const $btn = $(ev.currentTarget);
        const originalText = $btn.html();
        
        // Add loading state
        $btn.addClass('subscription_loading');
        $btn.html('<i class="fas fa-spinner fa-spin me-2"></i>Processing...');
        
        // Disable other buttons temporarily
        this.$('.subscription_btn').not($btn).prop('disabled', true);
        
        // Let the normal link behavior continue
        setTimeout(() => {
            if ($btn.length) {
                $btn.removeClass('subscription_loading');
                $btn.html(originalText);
                this.$('.subscription_btn').prop('disabled', false);
            }
        }, 2000);
    },

    /**
     * Handle card hover effects
     */
    _onCardHover: function (ev) {
        const $card = $(ev.currentTarget);
        $card.find('.plan_icon').addClass('pulse-animation');
        $card.addClass('card-hover-effect');
    },

    /**
     * Handle card leave effects
     */
    _onCardLeave: function (ev) {
        const $card = $(ev.currentTarget);
        $card.find('.plan_icon').removeClass('pulse-animation');
        $card.removeClass('card-hover-effect');
    },
});

// Subscription Plans Interactive Widget (existing)
publicWidget.registry.SubscriptionPlans = publicWidget.Widget.extend({
    selector: '.subscription_plans_wrap',
    events: {
        'click .subscription_btn': '_onPlanSelect',
        'mouseenter .subscription_plan_card': '_onCardHover',
        'mouseleave .subscription_plan_card': '_onCardLeave',
        'click .plan_navigation a': '_onNavigationClick',
    },

    /**
     * Initialize the widget
     */
    start: function () {
        this._super.apply(this, arguments);
        this._initAnimations();
        this._initComparisonTable();
        return Promise.resolve();
    },

    /**
     * Handle navigation clicks
     */
    _onNavigationClick: function (ev) {
        ev.preventDefault();
        const target = $(ev.currentTarget).attr('href');
        const $target = $(target);
        
        if ($target.length) {
            $('html, body').animate({
                scrollTop: $target.offset().top - 100
            }, 800, 'easeInOutQuart');
        }
    },

    /**
     * Initialize comparison table
     */
    _initComparisonTable: function () {
        // Add interactive features to comparison table
        this.$('.comparison_table tbody tr').hover(
            function() {
                $(this).addClass('table-active');
            },
            function() {
                $(this).removeClass('table-active');
            }
        );
    },

    /**
     * Initialize card animations
     */
    _initAnimations: function () {
        // Animate cards on scroll
        if (typeof IntersectionObserver !== 'undefined') {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('animate-in');
                    }
                });
            }, {
                threshold: 0.1
            });

            this.$('.subscription_plan_card').each(function() {
                observer.observe(this);
            });
        }
    },

    /**
     * Handle plan selection
     */
    _onPlanSelect: function (ev) {
        const $btn = $(ev.currentTarget);
        const planId = $btn.closest('.subscription_plan_card').data('plan-id');
        
        // Add loading state
        $btn.addClass('subscription_loading');
        $btn.html('<i class="fas fa-spinner fa-spin me-2"></i>Processing...');
        
        // Disable other buttons temporarily
        this.$('.subscription_btn').not($btn).prop('disabled', true);
        
        // Let the normal link behavior continue
        setTimeout(() => {
            if ($btn.length) {
                $btn.removeClass('subscription_loading');
                this.$('.subscription_btn').prop('disabled', false);
            }
        }, 2000);
    },

    /**
     * Handle card hover effects
     */
    _onCardHover: function (ev) {
        const $card = $(ev.currentTarget);
        $card.find('.plan_icon').addClass('pulse-animation');
    },

    /**
     * Handle card leave effects
     */
    _onCardLeave: function (ev) {
        const $card = $(ev.currentTarget);
        $card.find('.plan_icon').removeClass('pulse-animation');
    },
});

// Payment Form Widget
publicWidget.registry.PaymentForm = publicWidget.Widget.extend({
    selector: '.payment_wrap',
    events: {
        'submit form': '_onFormSubmit',
        'click .btn-link': '_onBackClick',
    },

    /**
     * Handle form submission
     */
    _onFormSubmit: function (ev) {
        const $form = $(ev.currentTarget);
        const $submitBtn = $form.find('button[type="submit"]');
        
        // Add loading state
        $submitBtn.addClass('subscription_loading');
        $submitBtn.html('<i class="fas fa-spinner fa-spin me-2"></i>Processing Payment...');
        $submitBtn.prop('disabled', true);
        
        // Show processing message
        const $alert = $('<div class="alert alert-info mt-3">' +
            '<i class="fas fa-clock me-2"></i>Processing your payment, please wait...' +
            '</div>');
        $form.append($alert);
        
        // Continue with normal form submission
        return true;
    },

    /**
     * Handle back button click
     */
    _onBackClick: function (ev) {
        // Add a slight delay for better UX
        ev.preventDefault();
        const href = $(ev.currentTarget).attr('href');
        setTimeout(() => {
            window.location.href = href;
        }, 300);
    },
});

// Success Page Widget
publicWidget.registry.SuccessPage = publicWidget.Widget.extend({
    selector: '.success_wrap',

    /**
     * Initialize success page
     */
    start: function () {
        this._super.apply(this, arguments);
        this._initSuccessAnimation();
        return Promise.resolve();
    },

    /**
     * Initialize success animations
     */
    _initSuccessAnimation: function () {
        // Confetti effect (simple version)
        this._showConfetti();
        
        // Auto-redirect after 10 seconds (optional)
        setTimeout(() => {
            if (confirm('Would you like to start playing now?')) {
                window.location.href = '/decks';
            }
        }, 10000);
    },

    /**
     * Simple confetti effect
     */
    _showConfetti: function () {
        // Create simple falling elements animation
        for (let i = 0; i < 20; i++) {
            setTimeout(() => {
                const $confetti = $('<div class="confetti-piece"></div>');
                $confetti.css({
                    position: 'fixed',
                    top: '-10px',
                    left: Math.random() * window.innerWidth + 'px',
                    width: '10px',
                    height: '10px',
                    backgroundColor: ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7'][Math.floor(Math.random() * 5)],
                    zIndex: 9999,
                    borderRadius: '50%',
                });
                
                $('body').append($confetti);
                
                $confetti.animate({
                    top: window.innerHeight + 'px',
                    left: '+=' + (Math.random() * 200 - 100) + 'px'
                }, 3000, function() {
                    $(this).remove();
                });
            }, i * 100);
        }
    },
});

// My Subscription Widget
publicWidget.registry.MySubscription = publicWidget.Widget.extend({
    selector: '.my_subscription_wrap',
    events: {
        'click .btn[href*="upgrade"]': '_onUpgradeClick',
    },

    /**
     * Handle upgrade button click
     */
    _onUpgradeClick: function (ev) {
        const $btn = $(ev.currentTarget);
        $btn.html('<i class="fas fa-spinner fa-spin me-2"></i>Loading...');
    },
});

// Add custom CSS animations and easing
$(document).ready(function() {
    // Add easing function for smooth animations
    $.easing.easeInOutQuart = function (x, t, b, c, d) {
        if ((t/=d/2) < 1) return c/2*t*t*t*t + b;
        return -c/2 * ((t-=2)*t*t*t - 2) + b;
    };

    // Add custom styles for animations
    const customCSS = `
        <style>
        .animate-in {
            animation: slideInUp 0.6s ease-out;
        }
        
        @keyframes slideInUp {
            from {
                transform: translateY(30px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        
        .pulse-animation {
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        .pulse-row {
            animation: pulseRow 1s ease-out;
        }
        
        @keyframes pulseRow {
            0% { background-color: transparent; }
            50% { background-color: rgba(102, 126, 234, 0.1); }
            100% { background-color: transparent; }
        }
        
        .highlighted-row {
            background-color: rgba(255, 193, 7, 0.1) !important;
            border-left: 4px solid #ffc107;
        }
        
        .card-hover-effect {
            box-shadow: 0 20px 40px rgba(0,0,0,0.2) !important;
        }
        
        .confetti-piece {
            animation: confetti-fall 3s linear forwards;
        }
        
        @keyframes confetti-fall {
            to {
                transform: translateY(100vh) rotate(360deg);
            }
        }
        
        /* Smooth scrolling for better UX */
        html {
            scroll-behavior: smooth;
        }
        
        /* Enhanced table interactions */
        .comparison_table tbody tr {
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .comparison_table tbody tr:hover {
            background-color: rgba(102, 126, 234, 0.05);
        }
        
        .feature_name {
            cursor: pointer;
        }
        
        .feature_name:hover {
            background-color: rgba(102, 126, 234, 0.1) !important;
        }
        </style>
    `;
    
    $('head').append(customCSS);
});