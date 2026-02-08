import sys
import os
import re

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from gui_translations import TRANSLATIONS
except ImportError:
    print("Error: Could not import TRANSLATIONS from gui_translations.py")
    sys.exit(1)

BASE_LANG = 'fr'

# Map language codes to their source files and dictionary names
LANG_FILES = {
    'en': {'file': 'gui_translations.py', 'dict_start': r"'en':\s*\{"},
    'de': {'file': 'gui_translations.py', 'dict_start': r"'de':\s*\{"},
    'es': {'file': 'gui_translations_es.py', 'dict_start': r"es_translations\s*=\s*\{"},
    'uk': {'file': 'gui_translations_uk.py', 'dict_start': r"uk_translations\s*=\s*\{"},
    'el': {'file': 'gui_translations_el.py', 'dict_start': r"el_translations\s*=\s*\{"},
    'he': {'file': 'gui_translations_he.py', 'dict_start': r"he_translations\s*=\s*\{"},
    'ar': {'file': 'gui_translations_ar.py', 'dict_start': r"ar_translations\s*=\s*\{"},
}

def find_closing_brace_index(content, start_index):
    """Finds the index of the closing brace matching the one at start_index, handling strings."""
    open_braces = 1
    in_string = False
    string_char = ''
    escape = False
    
    i = start_index
    while i < len(content) and open_braces > 0:
        char = content[i]
        
        if in_string:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == string_char:
                in_string = False
        else:
            if char == '"' or char == "'":
                in_string = True
                string_char = char
            elif char == '{':
                open_braces += 1
            elif char == '}':
                open_braces -= 1
                
        i += 1
    
    if open_braces == 0:
        return i - 1
    return -1

def cleanup_file(filename, dict_start_regex, unused_keys):
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    if not os.path.exists(filepath):
        print(f"  ❌ File not found: {filename}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(dict_start_regex, content)
    if not match:
        print(f"  ❌ Could not find dictionary start in {filename}")
        return

    start_idx = match.end()
    end_idx = find_closing_brace_index(content, start_idx)
    
    if end_idx == -1:
        print(f"  ❌ Could not find closing brace in {filename}")
        return

    dict_content = content[start_idx:end_idx]
    
    # Remove lines containing unused keys
    # This is a simple regex-based removal. It assumes one key per line.
    # It might fail if keys are split across lines or multiple keys on one line.
    # But given the generated format, it should be fine.
    
    new_dict_content = dict_content
    removed_count = 0
    
    for key in unused_keys:
        # Regex to find the key: "key": ... ,?
        # We look for the key surrounded by quotes, followed by colon, value, and optional comma
        # We also capture the newline before it to remove the whole line cleanly
        pattern = r'\n\s*["\']' + re.escape(key) + r'["\']\s*:.*?(?:,|$)'
        
        # Check if key exists before trying to remove
        if re.search(pattern, new_dict_content):
            new_dict_content = re.sub(pattern, '', new_dict_content)
            removed_count += 1
            
    if removed_count > 0:
        new_content = content[:start_idx] + new_dict_content + content[end_idx:]
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  🧹 Cleaned {removed_count} keys from {filename}")
    else:
        print(f"  ✨ No keys to clean in {filename}")

def cleanup_translations():
    print("--- Cleaning Up Unused Translations ---")
    
    base_data = TRANSLATIONS[BASE_LANG]
    base_keys = set(base_data.keys())

    for lang, info in LANG_FILES.items():
        if lang not in TRANSLATIONS: continue

        current_keys = set(TRANSLATIONS[lang].keys())
        unused_keys = current_keys - base_keys

        if not unused_keys:
            print(f"✅ {lang}: No unused keys.")
            continue

        print(f"🗑️ {lang}: Found {len(unused_keys)} unused keys...")
        cleanup_file(info['file'], info['dict_start'], unused_keys)

if __name__ == "__main__":
    cleanup_translations()