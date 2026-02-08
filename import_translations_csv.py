import sys
import os
import csv
import re

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = 'translations_export.csv'

# Map language codes to their source files and dictionary start regex
# indent: indentation for the dictionary items
LANG_CONFIG = {
    'fr': {'file': 'gui_translations.py', 'dict_start': r"['\"]fr['\"]\s*:\s*\{", 'indent': '        '},
    'en': {'file': 'gui_translations.py', 'dict_start': r"['\"]en['\"]\s*:\s*\{", 'indent': '        '},
    'de': {'file': 'gui_translations.py', 'dict_start': r"['\"]de['\"]\s*:\s*\{", 'indent': '        '},
    'es': {'file': 'gui_translations_es.py', 'dict_start': r"es_translations\s*=\s*\{", 'indent': '    '},
    'uk': {'file': 'gui_translations_uk.py', 'dict_start': r"uk_translations\s*=\s*\{", 'indent': '    '},
    'el': {'file': 'gui_translations_el.py', 'dict_start': r"el_translations\s*=\s*\{", 'indent': '    '},
    'he': {'file': 'gui_translations_he.py', 'dict_start': r"he_translations\s*=\s*\{", 'indent': '    '},
    'ar': {'file': 'gui_translations_ar.py', 'dict_start': r"ar_translations\s*=\s*\{", 'indent': '    '},
}

def find_closing_brace_index(content, start_index):
    """Finds the index of the closing brace matching the one at start_index."""
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

def import_translations():
    print(f"--- Importing Translations from {INPUT_FILE} ---")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ File not found: {INPUT_FILE}")
        sys.exit(1)

    # 1. Read CSV
    translations = {} # {lang: {key: value}}
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            if not reader.fieldnames:
                print("❌ CSV file is empty or invalid.")
                sys.exit(1)
            
            # Initialize dicts for languages present in CSV headers
            for lang in reader.fieldnames:
                if lang != 'key':
                    translations[lang] = {}

            for row in reader:
                key = row['key']
                if not key: continue
                
                for lang in translations:
                    if lang in row:
                        translations[lang][key] = row[lang]
                        
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        sys.exit(1)

    # 2. Update Files
    for lang, data in translations.items():
        if lang not in LANG_CONFIG:
            print(f"⚠️ Skipping unknown language in CSV: {lang}")
            continue
        
        config = LANG_CONFIG[lang]
        filename = config['file']
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        
        if not os.path.exists(filepath):
            print(f"❌ Target file not found for {lang}: {filename}")
            continue

        print(f"🛠️ Updating {lang} in {filename}...")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        match = re.search(config['dict_start'], content)
        if not match:
            print(f"  ❌ Could not find dictionary start for {lang} in {filename}")
            continue

        start_idx = match.end() # This is after the opening '{'
        
        end_idx = find_closing_brace_index(content, start_idx)
        if end_idx == -1:
            print(f"  ❌ Could not find closing brace for {lang} in {filename}")
            continue

        # Generate new content
        new_lines = []
        indent = config['indent']
        
        sorted_keys = sorted(data.keys())
        
        for key in sorted_keys:
            val = data[key]
            # Escape value for Python string
            safe_val = val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            line = f'{indent}"{key}": "{safe_val}",'
            new_lines.append(line)
        
        # Determine closing brace indentation (one level less than items)
        closing_indent = indent[:-4] if len(indent) >= 4 else ""
        
        new_dict_content = "\n" + "\n".join(new_lines) + "\n" + closing_indent

        # Replace content
        new_file_content = content[:start_idx] + new_dict_content + content[end_idx:]
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_file_content)
            print(f"  ✅ Updated {len(data)} keys for {lang}")
        except Exception as e:
            print(f"  ❌ Error writing file {filename}: {e}")

if __name__ == "__main__":
    import_translations()