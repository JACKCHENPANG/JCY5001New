import os

files_to_update = [
    'ui/window_manager.py',
    'ui/menu_manager.py',
    'config/app_config.json'
]

for filepath in files_to_update:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace('V0.92.53', 'V0.92.54')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated: {filepath}")
    else:
        print(f"Not found: {filepath}")

print("Version updated to V0.92.54")
