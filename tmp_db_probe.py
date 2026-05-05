
import sqlite3
conn=sqlite3.connect(r"D:\JCY5001_clean\JCY5001AS_Clean_Source\data\test_results.db")
cur=conn.cursor()
print('MAX_ID', cur.execute("select coalesce(max(id),0) from test_results").fetchone()[0])
print('LAST_BATCH', cur.execute("select coalesce(max(batch_id),0) from test_results").fetchone()[0])
conn.close()
