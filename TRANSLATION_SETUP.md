# Translation Setup for Subscription Plans Module

## Overview

This module now includes automatic translation functionality for deck names and descriptions on the `/decks` route, similar to the `carddeck_game` module. The translation system uses Google Translate API via the `googletrans` library and implements parallel processing for optimal performance.

## Features

- **Automatic Language Detection**: Detects user language from URL path, cookies, or Odoo context
- **Parallel Translation Processing**: Translates multiple deck names and descriptions simultaneously using ThreadPoolExecutor
- **Translation Caching**: In-memory cache to avoid repeated API calls for the same text
- **Frontend Dynamic Translation**: JavaScript-based translation that updates content without page reload
- **Multiple API Endpoints**: Various endpoints for different translation needs

## Installation

### 1. Install Required Dependencies

```bash
# Install pip if not available
sudo apt install python3-pip

# Install googletrans library
pip install googletrans==4.0.0rc1

# Or using python3 -m pip
python3 -m pip install googletrans==4.0.0rc1
```

### 2. Restart Odoo Server

After installing the dependencies, restart your Odoo server to load the new libraries.

## How It Works

### Backend Translation

1. **Language Detection**: The system detects the user's preferred language using:
   - URL path prefix (e.g., `/pt/decks`)
   - `frontend_lang` cookie set by Odoo's language selector
   - Odoo context language
   - Defaults to English if none detected

2. **Parallel Processing**: When translating multiple decks:
   - Creates translation tasks for each deck name and description
   - Uses ThreadPoolExecutor with up to 10 concurrent workers
   - Processes all translations simultaneously for maximum speed

3. **Caching**: Implements an in-memory cache to store translations and avoid repeated API calls

### Frontend Translation

1. **Automatic Detection**: JavaScript detects language changes and triggers translation
2. **Dynamic Updates**: Updates deck names and descriptions without page reload
3. **Original Content Preservation**: Stores original text for reverting to English

## API Endpoints

### 1. `/api/decks/translate` (JSON)
Translates specific decks by ID or all accessible decks.

```javascript
// Translate all accessible decks
$.ajax({
    url: '/api/decks/translate',
    type: 'POST',
    data: JSON.stringify({lang_code: 'es'}),
    contentType: 'application/json'
});

// Translate specific decks
$.ajax({
    url: '/api/decks/translate',
    type: 'POST',
    data: JSON.stringify({
        lang_code: 'pt',
        deck_ids: [1, 2, 3]
    }),
    contentType: 'application/json'
});
```

### 2. `/decks/translate` (JSON)
Translates all decks on the deck list page.

```javascript
$.ajax({
    url: '/decks/translate',
    type: 'POST',
    data: JSON.stringify({lang_code: 'fr'}),
    contentType: 'application/json'
});
```

## Supported Languages

The system supports all languages supported by Google Translate, including:
- Spanish (es)
- Portuguese (pt)
- French (fr)
- German (de)
- Italian (it)
- And many more...

## Performance Optimizations

1. **Parallel Processing**: Multiple translations happen simultaneously
2. **Caching**: Prevents duplicate API calls
3. **Cache Management**: Automatically manages cache size (max 1000 entries)
4. **Error Handling**: Graceful fallback to original text if translation fails

## Usage

### Automatic Translation

Translation happens automatically when:
1. User visits `/decks` page with a non-English language selected
2. User changes language using Odoo's language selector
3. URL contains language prefix (e.g., `/pt/decks`)

### Manual Translation

You can trigger translation programmatically:

```javascript
// Initialize translation system
var DeckTranslation = require('subscription_plans.deck_translation');

// Translate to specific language
DeckTranslation.translateDecks('es');

// Translate single deck
DeckTranslation.translateSingleDeck(123, 'pt');
```

## Troubleshooting

### Translation Not Working

1. **Check Dependencies**: Ensure `googletrans==4.0.0rc1` is installed
2. **Check Logs**: Look for translation errors in Odoo logs
3. **Network Issues**: Ensure server can access Google Translate API
4. **Cache Issues**: Restart server to clear translation cache

### Performance Issues

1. **Reduce Concurrent Workers**: Modify `max_workers` in `_translate_deck_content`
2. **Increase Cache Size**: Modify cache limit in `_translate_text`
3. **Network Optimization**: Consider using a local translation service

## Files Modified/Added

### New Files:
- `static/src/js/deck_translation.js` - Frontend translation handling
- `TRANSLATION_SETUP.md` - This documentation

### Modified Files:
- `controllers/deck_controller.py` - Added translation methods and API endpoints
- `__manifest__.py` - Added googletrans dependency and JavaScript asset
- `views/website_templates.xml` - Added translation script and deck ID attributes
- `requirements.txt` - Added googletrans dependency

## Integration with carddeck_game

This implementation follows the same pattern as the `carddeck_game` module:
- Same language detection logic
- Same caching mechanism
- Same parallel processing approach
- Same error handling
- Compatible API structure

The translation system is designed to work seamlessly with the existing `carddeck_game` translation functionality.
