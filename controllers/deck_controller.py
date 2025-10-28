# -*- coding: utf-8 -*-

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from googletrans import Translator
except ImportError:
    Translator = None

_logger = logging.getLogger(__name__)

# Simple in-memory cache for translations (cleared on server restart)
_translation_cache = {}


class DeckController(http.Controller):

    def _get_user_language(self):
        """Get current user's language code"""
        # Priority 1: Check URL path for language prefix (e.g., /pt/decks)
        path_parts = request.httprequest.path.split('/')
        if len(path_parts) > 1 and len(path_parts[1]) == 2:
            lang_code = path_parts[1]
            _logger.info(f"Language from URL path: {lang_code}")
            return lang_code
        
        # Priority 2: Check frontend_lang cookie (set by Odoo website language selector)
        frontend_lang_cookie = request.httprequest.cookies.get('frontend_lang', None)
        if frontend_lang_cookie:
            lang_code = frontend_lang_cookie.split('_')[0] if '_' in frontend_lang_cookie else frontend_lang_cookie
            _logger.info(f"Language from frontend_lang cookie: {frontend_lang_cookie} -> {lang_code}")
            return lang_code
        
        # Priority 3: Check Odoo context language
        context_lang = request.env.context.get('lang', None)
        if context_lang:
            lang_code = context_lang.split('_')[0] if '_' in context_lang else context_lang
            _logger.info(f"Language from context: {context_lang} -> {lang_code}")
            return lang_code
        
        # Default: English
        _logger.info("No language detected, defaulting to English")
        return 'en'

    def _translate_text(self, text, target_lang):
        """Single text translation worker function with caching"""
        if not text or not text.strip():
            return text
        
        # Check cache first
        cache_key = f"{target_lang}:{text}"
        if cache_key in _translation_cache:
            return _translation_cache[cache_key]
        
        # Translate if not in cache
        try:
            translator = Translator()
            result = translator.translate(text, dest=target_lang)
            translated_text = result.text
            
            # Store in cache
            _translation_cache[cache_key] = translated_text
            
            # Limit cache size to 1000 entries to avoid memory issues
            if len(_translation_cache) > 1000:
                # Remove oldest 200 entries
                keys_to_remove = list(_translation_cache.keys())[:200]
                for key in keys_to_remove:
                    del _translation_cache[key]
            
            return translated_text
        except Exception:
            return text

    def _translate_deck_content(self, decks, target_lang):
        """Translate deck content including names and descriptions - FAST parallel version"""
        try:
            # Only translate if Translator is available and target language is not English
            if not Translator or target_lang == 'en':
                _logger.info(f"No translation needed: Translator={Translator is not None}, target_lang={target_lang}")
                return decks
            
            _logger.info(f"Translating {len(decks)} decks to {target_lang} (parallel mode)")
            
            # Prepare all translation tasks
            translation_tasks = []
            deck_map = {}  # Map task index to deck and field
            
            for deck in decks:
                # Task for deck name
                if deck.name:
                    task_id = len(translation_tasks)
                    translation_tasks.append(deck.name)
                    deck_map[task_id] = (deck, 'name')
                
                # Task for deck description
                if deck.description:
                    task_id = len(translation_tasks)
                    translation_tasks.append(deck.description)
                    deck_map[task_id] = (deck, 'description')
            
            # Execute all translations in parallel using ThreadPoolExecutor
            translations = {}
            if translation_tasks:
                with ThreadPoolExecutor(max_workers=min(10, len(translation_tasks))) as executor:
                    # Submit all translation tasks
                    future_to_task = {
                        executor.submit(self._translate_text, text, target_lang): idx
                        for idx, text in enumerate(translation_tasks)
                    }
                    
                    # Collect results as they complete
                    for future in as_completed(future_to_task):
                        task_idx = future_to_task[future]
                        try:
                            translations[task_idx] = future.result()
                        except Exception as e:
                            _logger.warning(f"Translation failed for task {task_idx}: {e}")
                            # Keep original text if translation fails
                            translations[task_idx] = translation_tasks[task_idx]
            
            # Apply translations using wrappers
            translated_decks = []
            for deck in decks:
                # Create wrapper for each deck
                class DeckWrapper:
                    def __init__(self, original_deck):
                        self._original_deck = original_deck
                        # Copy all attributes from original deck
                        for attr in dir(original_deck):
                            if not attr.startswith('_') and not callable(getattr(original_deck, attr)):
                                try:
                                    setattr(self, attr, getattr(original_deck, attr))
                                except:
                                    pass
                    
                    def __getattr__(self, name):
                        # Delegate to original deck for any attribute not explicitly set
                        return getattr(self._original_deck, name)
                
                wrapped_deck = DeckWrapper(deck)
                
                # Apply translations for this deck
                for task_idx, (task_deck, field) in deck_map.items():
                    if task_deck.id == deck.id and task_idx in translations:
                        setattr(wrapped_deck, field, translations[task_idx])
                        _logger.info(f"Deck {deck.id} {field}: {getattr(deck, field)[:50]}... -> {translations[task_idx][:50]}...")
                
                translated_decks.append(wrapped_deck)
            
            return translated_decks
            
        except Exception as e:
            _logger.error(f"Deck translation failed: {str(e)}", exc_info=True)
            # Return original decks if translation fails
            return decks

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
        
        # Get user's current language for translation
        user_lang = self._get_user_language()
        cookies = request.httprequest.cookies
        _logger.info(f"Decks request - Detected language: {user_lang}, Path: {request.httprequest.path}, Context lang: {request.env.context.get('lang')}, Cookies: frontend_lang={cookies.get('frontend_lang', 'NOT SET')}")
        
        # Translate deck content if not English and googletrans is available
        translated_try_out_decks = self._translate_deck_content(try_out_decks, user_lang)
        translated_free_decks = self._translate_deck_content(free_decks, user_lang)
        translated_premium_decks = self._translate_deck_content(premium_decks, user_lang)
        translated_user_decks = self._translate_deck_content(user_decks, user_lang)
        
        values = {
            'try_out_decks': translated_try_out_decks,
            'free_decks': translated_free_decks,
            'premium_decks': translated_premium_decks,
            'user_decks': translated_user_decks,
            'subscription': subscription,
            'plan_type': plan_type,
            'user': user,
            'user_name': user_name,
            'subscription_status': subscription_status,
            'total_accessible': len(all_accessible_decks),
            'can_create': can_create,
            'max_private_decks': max_private_decks,
            'max_cards_per_deck': max_cards_per_deck,
            'user_language': user_lang,  # Add language info for frontend
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
        
        # Increment play count (use sudo to allow public users to increment)
        try:
            deck.sudo().increment_play_count()
        except Exception as e:
            # Log the error but don't block the user from playing
            _logger.warning(f"Failed to increment play count for deck {deck_id}: {str(e)}")
        
        # Redirect to game controller (assuming carddecks_game module has this)
        return request.redirect('/game/new?deck_id=%s' % deck_id)



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

    @http.route(['/api/decks/translate'], type='json', auth='public', website=True)
    def translate_decks(self, lang_code=None, deck_ids=None, **kwargs):
        """JSON endpoint to translate deck content"""
        if not Translator:
            return {'error': 'googletrans library not available'}
        
        user_lang = lang_code or self._get_user_language()
        if user_lang == 'en':
            return {'message': 'No translation needed for English'}
        
        try:
            user = request.env.user
            
            # Get decks to translate
            if deck_ids:
                decks = request.env['carddecks.deck'].browse(deck_ids)
            else:
                # Get all accessible decks
                decks = request.env['carddecks.deck'].get_accessible_decks(user=user, limit=100)
            
            # Translate deck content
            translated_decks = self._translate_deck_content(decks, user_lang)
            
            # Prepare response data
            deck_translations = []
            for deck in translated_decks:
                deck_translations.append({
                    'id': deck.id,
                    'name': deck.name,
                    'description': deck.description,
                })
            
            return {
                'success': True,
                'target_language': user_lang,
                'decks': deck_translations
            }
            
        except Exception as e:
            return {'error': f'Translation failed: {str(e)}'}

    @http.route(['/decks/translate'], type='json', auth='public', website=True)
    def translate_deck_page(self, lang_code=None, **kwargs):
        """JSON endpoint to get translated deck page content"""
        if not Translator:
            return {'error': 'googletrans library not available'}
        
        user_lang = lang_code or self._get_user_language()
        if user_lang == 'en':
            return {'message': 'No translation needed for English'}
        
        try:
            user = request.env.user
            
            # Get all accessible decks
            all_accessible_decks = request.env['carddecks.deck'].get_accessible_decks(user=user, limit=100)
            
            # Separate decks by type
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
            
            # Translate all deck collections in parallel
            all_decks = try_out_decks + free_decks + premium_decks + user_decks
            translated_decks = self._translate_deck_content(all_decks, user_lang)
            
            # Prepare response data
            deck_data = {}
            for deck in translated_decks:
                deck_data[str(deck.id)] = {
                    'name': deck.name,
                    'description': deck.description,
                }
            
            return {
                'success': True,
                'target_language': user_lang,
                'decks': deck_data
            }
            
        except Exception as e:
            return {'error': f'Translation failed: {str(e)}'}
