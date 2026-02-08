import sys
import os
import csv

# Add current directory to path
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

BASE_LANG = 'fr'
OUTPUT_FILE = 'translations_export.csv'

def export_translations():
    print(f"--- Exporting Translations to {OUTPUT_FILE} ---")
    
    # Gather all languages
    languages = {
        'fr': TRANSLATIONS.get('fr', {}),
        'en': TRANSLATIONS.get('en', {}),
        'de': TRANSLATIONS.get('de', {}),
        'es': es_translations,
        'uk': uk_translations,
        'el': el_translations,
        'he': he_translations,
        'ar': ar_translations
    }
    
    # Get all unique keys from all languages
    all_keys = set()
    for lang_data in languages.values():
        all_keys.update(lang_data.keys())
    
    sorted_keys = sorted(list(all_keys))
    
    # Prepare CSV headers
    headers = ['key'] + list(languages.keys())
    
    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for key in sorted_keys:
                row = [key]
                for lang_code in languages.keys():
                    # Get translation or empty string if missing
                    translation = languages[lang_code].get(key, "")
                    row.append(translation)
                writer.writerow(row)
                
        print(f"✅ Successfully exported {len(sorted_keys)} keys to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"❌ Error exporting CSV: {e}")

if __name__ == "__main__":
    export_translations()