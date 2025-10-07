# -*- coding: utf-8 -*-
{
    'name': 'Subscription Plans',
    'version': '16.0.1.0.0',
    'category': 'Website',
    'summary': 'Enhanced subscription plans management with comparison features and dedicated website page',
    'description': """
        Enhanced Subscription Plans Module
        =================================
        This module provides comprehensive subscription plan management for users with three tiers:
        
        Features:
        ---------
        * Try Out plan for unregistered users
        * Free plan for registered users  
        * Premium plan for paid subscribers
        * Beautiful frontend interface for plan selection
        * Enhanced comparison table for easy plan comparison
        * Dedicated subscription page accessible from website menu
        * Interactive testimonials and statistics
        * User subscription tracking and management
        * Smooth scrolling navigation and animations
        
        Plans:
        ------
        1. Try Out - No registration required, limited access
        2. Free - Registration required, basic features
        3. Premium - Payment required, full features access
        
        New Features:
        ------------
        * Dedicated /subscription page with enhanced UI
        * Feature-by-feature comparison table
        * Interactive navigation with scroll spy
        * Testimonials section
        * Statistics display
        * Enhanced animations and user experience
        * Multi-language support (Spanish, French, Portuguese)
    """,
    
    'author': 'Diago Team',
    'website': 'https://www.diago.com',
    'depends': [
        'base',
        'website',
        'portal',
        'auth_signup',
        'carddecks',
    ],
    
    'external_dependencies': {
        'python': ['stripe', 'googletrans'],
    },
    
    'data': [
        'security/ir.model.access.csv',
        'security/carddecks_access.xml',
        'data/subscription_plan_data.xml',
        'data/recaptcha_data.xml',
        'data/cron_jobs.xml',
        'views/subscription_plan_views.xml',
        'views/user_subscription_views.xml',
        'views/subscription_menu.xml',
        'views/deck_views.xml',
        'views/res_config_settings_views.xml',
        # 'views/subscription_templates.xml',
        'views/website_templates.xml',
    ],
    
    'assets': {
        'web.assets_frontend': [
            'subscription_plans/static/src/css/subscription_styles.css',
            'subscription_plans/static/src/css/deck_styles.css',
            'subscription_plans/static/src/css/recaptcha_v2.css',
            'subscription_plans/static/src/css/stripe_payment.css',
            'subscription_plans/static/src/js/subscription.js',
            'subscription_plans/static/src/js/stripe_payment.js',
            'subscription_plans/static/src/js/deck_translation.js',
        ],
        'web.assets_backend': [
            'subscription_plans/static/src/css/subscription_backend.css',
        ],
    },
    
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
} 