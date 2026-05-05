
from pathlib import Path
lines = Path(r"D:\JCY5001_clean\JCY5001AS_Clean_Source\logs\app.log").read_text(encoding='utf-8', errors='ignore').splitlines()
for i, ln in enumerate(lines):
    if '2026-05-05 19:46:33,958' in ln:
        start=max(0,i-25); end=min(len(lines),i+60)
        for j in range(start,end):
            print(f"{j+1}:" + lines[j].encode('ascii','backslashreplace').decode('ascii'))
        break
