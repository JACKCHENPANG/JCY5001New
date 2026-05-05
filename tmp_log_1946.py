
from pathlib import Path
text = Path(r"D:\JCY5001_clean\JCY5001AS_Clean_Source\logs\app.log").read_text(encoding='utf-8', errors='ignore')
for ln in text.splitlines():
    if '2026-05-05 19:46:' in ln:
        print(ln.encode('ascii', 'backslashreplace').decode('ascii'))
