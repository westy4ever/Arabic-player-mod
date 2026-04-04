import os

file_path = r"C:\Users\ammar\.gemini\antigravity\scratch\ArabicPlayer\plugin.py"

with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix Splash screen widget position error
text = text.replace('<widget name="splash_pic" position="center,center"', '<widget name="splash_pic" position="0,0"')

# Fix 8-digit hex colors in skin definitions
hex_replacements = {
    '#CC0D1117': '#0D1117',
    '#B3161B22': '#161B22',
    '#01161B22': '#161B22',
    '#9921262D': '#21262D',
    '#E6161B22': '#161B22',
    '#E61C2333': '#1C2333',
    '#B31C2333': '#1C2333',
    '#CC161B22': '#161B22',
    '#011C2333': '#1C2333'
}

for old, new in hex_replacements.items():
    text = text.replace(old, new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Fixed XML Skin Parsing errors successfully!")
