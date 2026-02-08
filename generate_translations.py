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
PLACEHOLDER_PREFIX = "[TODO] "

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

def update_file(filename, dict_start_regex, new_lines):
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
    # We assume the regex ends right before the content of the dict, e.g. at '{'
    # But match.end() is after '{'.
    # We need to start searching for closing brace from there.
    
    # Actually, let's verify if regex includes '{'. Yes it does in definitions above.
    
    end_idx = find_closing_brace_index(content, start_idx)
    
    if end_idx == -1:
        print(f"  ❌ Could not find closing brace in {filename}")
        return

    # Determine indentation
    if filename == 'gui_translations.py':
        item_indent = "        "
    else:
        item_indent = "    "

    insertion_str = "\n"
    for line in new_lines:
        insertion_str += item_indent + line + "\n"
    
    # Ensure previous item has a comma
    prev_char_idx = end_idx - 1
    while prev_char_idx > start_idx and content[prev_char_idx].isspace():
        prev_char_idx -= 1
    
    if prev_char_idx > start_idx and content[prev_char_idx] not in [',', '{']:
        content = content[:prev_char_idx+1] + "," + content[prev_char_idx+1:]
        end_idx += 1

    new_content = content[:end_idx] + insertion_str + content[end_idx:]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"  💾 Updated {filename}")

def generate_translations():
    print("--- Generating Missing Translations ---")
    
    base_data = TRANSLATIONS[BASE_LANG]
    base_keys = set(base_data.keys())

    for lang, info in LANG_FILES.items():
        if lang not in TRANSLATIONS: continue

        current_keys = set(TRANSLATIONS[lang].keys())
        missing_keys = base_keys - current_keys

        if not missing_keys:
            print(f"✅ {lang}: Up to date.")
            continue

        print(f"🛠️ {lang}: Generating {len(missing_keys)} missing keys...")
        new_lines = []
        for key in sorted(missing_keys):
            safe_text = base_data[key].replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            new_lines.append(f'"{key}": "{PLACEHOLDER_PREFIX}{safe_text}",')

        update_file(info['file'], info['dict_start'], new_lines)

if __name__ == "__main__":
    generate_translations()