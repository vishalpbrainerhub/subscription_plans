# -*- coding: utf-8 -*-

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError
import json


class DeckController(http.Controller):

    @http.route(['/decks'], type='http', auth='public', website=True)
    def deck_list(self, **kwargs):
        """Display deck list page based on user subscription with header information"""
        user = request.env.user
        
        # Get user's subscription info and header details
        if user._is_public():
            subscription = None
            plan_type = 'try_out'
            can_create = False
            max_private_decks = 0
            max_cards_per_deck = 0
            user_name = 'Guest User'
            subscription_status = 'No Subscription'
        else:
            subscription = request.env['user.subscription'].sudo().get_user_subscription(user.id)
            plan_type = subscription.plan_type if subscription else 'free'
            can_create = subscription.plan_id.can_create_decks if subscription else False
            max_private_decks = subscription.max_private_decks if subscription else 0
            max_cards_per_deck = subscription.max_cards_per_deck if subscription else 0
            user_name = user.name or user.login
            subscription_status = subscription.plan_id.name if subscription else 'Free Plan'
        
        # Get all accessible decks using original carddecks filtering with subscription overlay
        all_accessible_decks = request.env['carddecks.deck'].get_accessible_decks(user=user, limit=100)
        
        # Separate decks by type for display
        try_out_decks = all_accessible_decks.filtered(lambda d: hasattr(d, 'deck_type') and d.deck_type == 'try_out')
        free_decks = all_accessible_decks.filtered(lambda d: hasattr(d, 'deck_type') and d.deck_type == 'free')
        premium_decks = all_accessible_decks.filtered(lambda d: hasattr(d, 'deck_type') and d.deck_type == 'premium')
        
        # For decks without deck_type (original carddecks), treat them as free decks if they're public
        original_decks = all_accessible_decks.filtered(lambda d: not hasattr(d, 'deck_type') or not d.deck_type)
        if original_decks and not user._is_public():
            free_decks = free_decks + original_decks
        
        # Get user's own decks if logged in
        user_decks = request.env['carddecks.deck'].browse()
        if not user._is_public():
            user_decks = request.env['carddecks.deck'].get_user_decks(user)
        
        values = {
            'try_out_decks': try_out_decks,
            'free_decks': free_decks,
            'premium_decks': premium_decks,
            'user_decks': user_decks,
            'subscription': subscription,
            'plan_type': plan_type,
            'user': user,
            'user_name': user_name,
            'subscription_status': subscription_status,
            'total_accessible': len(all_accessible_decks),
            'can_create': can_create,
            'max_private_decks': max_private_decks,
            'max_cards_per_deck': max_cards_per_deck,
        }
        
        return request.render('subscription_plans.deck_list_page', values)

    @http.route(['/deck/<int:deck_id>'], type='http', auth='public', website=True)
    def deck_detail(self, deck_id, **kwargs):
        """Display deck detail page"""
        deck = request.env['carddecks.deck'].browse(deck_id)
        if not deck.exists():
            return request.not_found()
        
        user = request.env.user
        can_access = deck.can_user_access(user)
        can_play = deck.can_user_play(user)
        
        # Get subscription info
        subscription = None
        if not user._is_public():
            subscription = request.env['user.subscription'].sudo().get_user_subscription(user.id)
        
        values = {
            'deck': deck,
            'can_access': can_access,
            'can_play': can_play,
            'subscription': subscription,
            'user': user,
        }
        
        return request.render('subscription_plans.deck_detail_page', values)

    @http.route(['/deck/<int:deck_id>/play'], type='http', auth='public', website=True)
    def deck_play(self, deck_id, **kwargs):
        """Play a deck"""
        deck = request.env['carddecks.deck'].browse(deck_id)
        if not deck.exists():
            return request.not_found()
        
        user = request.env.user
        
        # Check access permissions
        if not deck.can_user_play(user):
            if user._is_public():
                # Redirect to signup for try-out decks
                if deck.deck_type == 'try_out':
                    return request.redirect('/web/signup?redirect=/deck/%s/play' % deck_id)
                else:
                    return request.redirect('/web/signup?redirect=/subscription')
            else:
                # Show upgrade message for registered users
                return request.redirect('/subscription?upgrade=true&deck_id=%s' % deck_id)
        
        # Increment play count
        deck.increment_play_count()
        
        # Redirect to game controller (assuming carddecks_game module has this)
        return request.redirect('/game/deck/%s' % deck_id)



    @http.route(['/api/decks/accessible'], type='json', auth='public')
    def get_accessible_decks(self, deck_type=None, limit=None, **kwargs):
        """API endpoint to get accessible decks"""
        user = request.env.user
        
        try:
            decks = request.env['carddecks.deck'].get_accessible_decks(
                user=user, 
                deck_type=deck_type, 
                limit=limit
            )
            
            deck_data = []
            for deck in decks:
                deck_data.append({
                    'id': deck.id,
                    'name': deck.name,
                    'description': deck.description,
                    'deck_type': deck.deck_type,
                    'play_count': deck.play_count,
                    'total_cards': deck.total_cards,
                    'can_play': deck.can_user_play(user),
                    'category': deck.category.name if deck.category else '',
                })
            
            return {
                'success': True,
                'decks': deck_data
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(['/api/user/subscription'], type='json', auth='user')
    def get_user_subscription_info(self, **kwargs):
        """API endpoint to get user subscription info"""
        user = request.env.user
        
        try:
            subscription = request.env['user.subscription'].sudo().get_user_subscription(user.id)
            
            if not subscription:
                return {'success': False, 'error': 'No subscription found'}
            
            data = {
                'plan_name': subscription.plan_id.name,
                'plan_type': subscription.plan_type,
                'features': [{
                    'name': feature.name,
                    'description': feature.description,
                    'is_highlighted': feature.is_highlighted,
                    'icon': feature.icon,
                } for feature in subscription.plan_id.feature_ids]
            }
            
            return {
                'success': True,
                'subscription': data
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(['/subscription/upgrade/<int:plan_id>'], type='http', auth='user', website=True)
    def upgrade_subscription(self, plan_id, **kwargs):
        """Handle subscription upgrade"""
        user = request.env.user
        plan = request.env['subscription.plan'].browse(plan_id)
        
        if not plan.exists():
            return request.not_found()
        
        # For now, upgrade immediately without payment processing
        subscription = request.env['user.subscription'].create_subscription(
            user_id=user.id,
            plan_id=plan_id,
            payment_success=True
        )
        
        return request.redirect('/decks?upgraded=true')
