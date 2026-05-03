import sqlite3

conn = sqlite3.connect(r'D:\JCY5001_clean\JCY5001AS_Clean_Source\data\test_results.db')
conn.row_factory = sqlite3.Row

# Schema
c = conn.execute('PRAGMA table_info(test_results)')
print('=== test_results schema ===')
for r in c.fetchall():
    print(dict(r))

c = conn.execute('PRAGMA table_info(impedance_details)')
print('\n=== impedance_details schema ===')
for r in c.fetchall():
    print(dict(r))

# Get test #73
print('\n=== Test #73 (test_results) ===')
c = conn.execute('SELECT * FROM test_results WHERE id = 73')
row = c.fetchone()
if row:
    for k in row.keys():
        val = row[k]
        if val is not None and len(str(val)) > 500:
            print(f'{k}: [len={len(str(val))}] {str(val)[:300]}...')
        else:
            print(f'{k}: {val}')
else:
    print('No test with id=73 found')

# Get impedance_details for test 73
print('\n=== impedance_details for test_id=73 ===')
c = conn.execute('SELECT * FROM impedance_details WHERE test_id = 73')
rows = c.fetchall()
if rows:
    for r in rows:
        for k in r.keys():
            val = r[k]
            if val is not None and len(str(val)) > 500:
                print(f'{k}: [len={len(str(val))}] {str(val)[:300]}...')
            else:
                print(f'{k}: {val}')
        print('---')
else:
    print('No impedance_details found for test_id=73')
    
    # Check for test_id=73 in other tables
    for tbl in ['batches', 'frequency_data']:
        c = conn.execute(f'SELECT * FROM {tbl} WHERE test_id = 73')
        rows = c.fetchall()
        if rows:
            print(f'\n=== Found in {tbl} ===')
            for r in rows:
                for k in r.keys():
                    val = r[k]
                    if val is not None and len(str(val)) > 500:
                        print(f'{k}: [len={len(str(val))}] {str(val)[:300]}...')
                    else:
                        print(f'{k}: {val}')
                print('---')

conn.close()
