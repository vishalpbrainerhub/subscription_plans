/**
 * Deck Translation JavaScript
 * Handles dynamic translation of deck content based on selected language
 */

odoo.define('subscription_plans.deck_translation', function (require) {
    'use strict';

    var core = require('web.core');
    var rpc = require('web.rpc');

    var _t = core._t;

    var DeckTranslation = {

        /**
         * Initialize deck translation functionality
         */
        init: function() {
            this.bindLanguageChange();
            this.setupTranslations();
        },

        /**
         * Bind to language change events
         */
        bindLanguageChange: function() {
            var self = this;
            
            // Listen for language selector changes
            $(document).on('click', 'a[href*="/website/lang/"]', function(e) {
                var langHref = $(this).attr('href');
                if (langHref) {
                    var langCode = self.extractLanguageFromUrl(langHref);
                    setTimeout(function() {
                        self.translateDecks(langCode);
                    }, 1000); // Wait for page reload/redirect
                }
            });

            // Listen for manual language change events
            $(document).on('change', 'select[name="lang"]', function() {
                var selectedLang = $(this).val();
                self.translateDecks(selectedLang);
            });
        },

        /**
         * Setup initial translations based on current language
         */
        setupTranslations: function() {
            var self = this;
            
            // Detect current language from URL or body classes
            var currentLang = this.detectCurrentLanguage();
            if (currentLang && currentLang !== 'en') {
                this.translateDecks(currentLang);
            }
        },

        /**
         * Extract language code from URL
         */
        extractLanguageFromUrl: function(url) {
            var match = url.match(/\/website\/lang\/([^\/]+)/);
            return match ? match[1] : 'en';
        },

        /**
         * Detect current language from page elements
         */
        detectCurrentLanguage: function() {
            // Check body classes first
            var bodyClass = $('body').attr('class');
            if (bodyClass) {
                var bodyClassMatch = bodyClass.match(/language-([a-z]{2})/);
                if (bodyClassMatch) {
                    return bodyClassMatch[1];
                }
            }

            // Check URL path
            var pathMatch = window.location.pathname.match(/\/([a-z]{2})\//);
            if (pathMatch) {
                return pathMatch[1];
            }

            // Check html lang attribute
            var htmlLang = $('html').attr('lang');
            if (htmlLang) {
                return htmlLang.split('_')[0];
            }

            return 'en';
        },

        /**
         * Translate deck content
         */
        translateDecks: function(langCode) {
            var self = this;
            
            if (langCode === 'en') {
                self.revertToOriginal();
                return;
            }

            // Show loading indicator
            this.showTranslationLoader();

            // Make AJAX call to translate decks
            $.ajax({
                url: '/decks/translate',
                type: 'POST',
                data: JSON.stringify({
                    lang_code: langCode
                }),
                contentType: 'application/json',
                headers: {
                    'Content-Type': 'application/json'
                }
            }).done(function(result) {
                if (result.success) {
                    self.applyDeckTranslations(result.decks);
                } else {
                    console.warn('Translation failed:', result.error);
                }
                self.hideTranslationLoader();
            }).fail(function(error) {
                console.error('Translation error:', error);
                self.hideTranslationLoader();
            });
        },

        /**
         * Apply translations to deck elements
         */
        applyDeckTranslations: function(deckTranslations) {
            var self = this;
            
            // Store original content before applying translations
            this.storeOriginalContent();
            
            // Apply translations to each deck card
            $('.card').each(function() {
                var $card = $(this);
                var deckId = self.extractDeckIdFromCard($card);
                
                if (deckId && deckTranslations[deckId]) {
                    var translation = deckTranslations[deckId];
                    
                    // Update deck name
                    if (translation.name) {
                        $card.find('.card-title').text(translation.name);
                    }
                    
                    // Update deck description
                    if (translation.description) {
                        $card.find('.card-description').text(translation.description);
                    }
                }
            });
            
            // Also update deck names in the simple card grid format
            $('.card .card-header .card-title').each(function() {
                var $title = $(this);
                var $card = $title.closest('.card');
                var deckId = self.extractDeckIdFromCard($card);
                
                if (deckId && deckTranslations[deckId] && deckTranslations[deckId].name) {
                    $title.text(deckTranslations[deckId].name);
                }
            });
            
            $('.card .card-description').each(function() {
                var $desc = $(this);
                var $card = $desc.closest('.card');
                var deckId = self.extractDeckIdFromCard($card);
                
                if (deckId && deckTranslations[deckId] && deckTranslations[deckId].description) {
                    $desc.text(deckTranslations[deckId].description);
                }
            });
        },

        /**
         * Extract deck ID from card element
         */
        extractDeckIdFromCard: function($card) {
            // Try to find deck ID from play button href
            var $playButton = $card.find('a[href*="/game/new?deck_id="], a[href*="/deck/"][href*="/play"]');
            if ($playButton.length > 0) {
                var href = $playButton.attr('href');
                
                // Extract from /game/new?deck_id=X format
                var deckIdMatch = href.match(/deck_id=(\d+)/);
                if (deckIdMatch) {
                    return deckIdMatch[1];
                }
                
                // Extract from /deck/X/play format
                var deckPathMatch = href.match(/\/deck\/(\d+)/);
                if (deckPathMatch) {
                    return deckPathMatch[1];
                }
            }
            
            // Try to find from data attributes
            var deckId = $card.data('deck-id');
            if (deckId) {
                return deckId.toString();
            }
            
            return null;
        },

        /**
         * Store original content for reversion
         */
        storeOriginalContent: function() {
            $('.card-title').each(function() {
                if (!$(this).data('original-text')) {
                    $(this).data('original-text', $(this).text());
                }
            });
            
            $('.card-description').each(function() {
                if (!$(this).data('original-text')) {
                    $(this).data('original-text', $(this).text());
                }
            });
        },

        /**
         * Revert to original language content
         */
        revertToOriginal: function() {
            $('.card-title').each(function() {
                var originalText = $(this).data('original-text');
                if (originalText) {
                    $(this).text(originalText);
                }
            });
            
            $('.card-description').each(function() {
                var originalText = $(this).data('original-text');
                if (originalText) {
                    $(this).text(originalText);
                }
            });
        },

        /**
         * Show translation loading indicator
         */
        showTranslationLoader: function() {
            var loader = '<div id="deck-translation-loader" style="position: fixed; top: 20px; right: 20px; background: #007bff; color: white; padding: 10px 20px; border-radius: 5px; z-index: 9999;">Translating decks...</div>';
            $('body').append(loader);
        },

        /**
         * Hide translation loading indicator
         */
        hideTranslationLoader: function() {
            $('#deck-translation-loader').remove();
        },

        /**
         * Translate specific deck by ID
         */
        translateSingleDeck: function(deckId, langCode) {
            var self = this;
            
            if (langCode === 'en') {
                return;
            }

            $.ajax({
                url: '/api/decks/translate',
                type: 'POST',
                data: JSON.stringify({
                    lang_code: langCode,
                    deck_ids: [deckId]
                }),
                contentType: 'application/json',
                headers: {
                    'Content-Type': 'application/json'
                }
            }).done(function(result) {
                if (result.success && result.decks.length > 0) {
                    var deck = result.decks[0];
                    var deckData = {};
                    deckData[deckId] = deck;
                    self.applyDeckTranslations(deckData);
                }
            }).fail(function(error) {
                console.error('Single deck translation error:', error);
            });
        }
    };

    // Initialize when document is ready
    $(document).ready(function() {
        if ($('.card-grid').length > 0 || $('.deck-card').length > 0) {
            DeckTranslation.init();
        }
    });

    return DeckTranslation;
});
