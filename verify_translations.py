import sys
import os

# Add current directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from gui_translations import TRANSLATIONS
    from gui_translations_es import es_translations
    from gui_translations_uk import uk_translations
    from gui_translations_el import el_translations
    from gui_translations_he import he_translations
    from gui_translations_ar import ar_translations
except ImportError as e:
    print(f"Error importing translation files: {e}")
    sys.exit(1)

def verify_translations():
    print("--- Verifying Translations ---")
    
    # Base language (French) is the reference
    base_lang = 'fr'
    if base_lang not in TRANSLATIONS:
        print(f"Error: Base language '{base_lang}' not found in TRANSLATIONS.")
        sys.exit(1)
        
    base_keys = set(TRANSLATIONS[base_lang].keys())
    print(f"Base language ({base_lang}) has {len(base_keys)} keys.")
    
    # Map of language codes to their translation dictionaries
    # Note: 'en' and 'de' are inside gui_translations.py, others are imported
    languages = {
        'en': TRANSLATIONS.get('en', {}),
        'de': TRANSLATIONS.get('de', {}),
        'es': es_translations,
        'uk': uk_translations,
        'el': el_translations,
        'he': he_translations,
        'ar': ar_translations
    }
    
    all_valid = True
    
    for lang_code, translations in languages.items():
        current_keys = set(translations.keys())
        missing_keys = base_keys - current_keys
        extra_keys = current_keys - base_keys
        
        if missing_keys:
            print(f"\n❌ Language '{lang_code}' is missing {len(missing_keys)} keys:")
            for key in sorted(missing_keys):
                print(f"   - {key}")
            all_valid = False
        
        if extra_keys:
            print(f"\n⚠️ Language '{lang_code}' has {len(extra_keys)} extra keys (not in base):")
            for key in sorted(extra_keys):
                print(f"   + {key}")
            # Extra keys are not necessarily an error, but good to know
            
        if not missing_keys and not extra_keys:
            print(f"✅ Language '{lang_code}' is complete and matches base.")
            
    print("\n--- Summary ---")
    if all_valid:
        print("🎉 All translation files are complete!")
        sys.exit(0)
    else:
        print("🛑 Some languages are missing translations.")
        sys.exit(1)

if __name__ == "__main__":
    verify_translations()