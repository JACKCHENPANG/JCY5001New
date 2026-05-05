
import sqlite3
from pathlib import Path

db = r"D:\JCY5001_clean\JCY5001AS_Clean_Source\data\test_results.db"
conn = sqlite3.connect(db)
cur = conn.cursor()
print('SCHEMA')
for row in cur.execute("PRAGMA table_info(test_results)"):
    print(row)
print('LATEST')
cols = [r[1] for r in cur.execute("PRAGMA table_info(test_results)").fetchall()]
sel = ', '.join(cols[:12])
for row in cur.execute(f"select {sel} from test_results order by id desc limit 20"):
    print(row)
conn.close()

log_path = Path(r"D:\JCY5001_clean\JCY5001AS_Clean_Source\logs\app.log")
text = log_path.read_text(encoding='utf-8', errors='ignore')
print('LOG_1946')
for ln in text.splitlines():
    if '2026-05-05 19:46:' in ln:
        print(ln)
