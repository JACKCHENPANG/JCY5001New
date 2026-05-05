
import json, sqlite3, time, urllib.request
BASE='http://127.0.0.1:5000'

def req(method, path, data=None, timeout=20):
    body = None if data is None else json.dumps(data).encode('utf-8')
    r = urllib.request.Request(BASE+path, data=body, method=method)
    r.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8', errors='ignore'))

def db_scalar(sql):
    conn=sqlite3.connect(r"D:\JCY5001_clean\JCY5001AS_Clean_Source\data\test_results.db")
    cur=conn.cursor()
    v=cur.execute(sql).fetchone()[0]
    conn.close()
    return v

print('BASE_MAX_ID', db_scalar('select coalesce(max(id),0) from test_results'))
print('BASE_BATCH', db_scalar('select coalesce(max(batch_id),0) from test_results'))
print('STATUS0', req('GET','/status', timeout=10))
print('CFG', req('POST','/config', {'updates': {
    'enabled_channels': [1,2,3,5,6,7,8],
    'test.enabled_channels': [1,2,3,5,6,7,8],
    'battery_detection.enabled': False,
    'auto_detect': False,
    'test.auto_detect': False,
    'test.use_parallel_staggered_mode': True,
    'test.critical_frequency': 10.0,
}}, timeout=30))
try:
    print('STOP_BD', req('POST','/battery_detection/stop', {'disable': True}, timeout=10))
except Exception as e:
    print('STOP_BD_ERR', repr(e))
start = time.time()
print('START', req('POST','/start_test', {}, timeout=20))
last=None
for i in range(260):
    st=req('GET','/status', timeout=10)
    d=st.get('data', {})
    tup=(d.get('is_testing'), d.get('test_state'), d.get('connected_device'))
    if tup != last or i % 5 == 0:
        print('POLL', i, round(time.time()-start,1), tup)
        last=tup
    if not d.get('is_testing') and i > 2:
        break
    time.sleep(1)
print('ELAPSED', round(time.time()-start,2))
print('FINAL', req('GET','/status', timeout=10))
print('AFTER_MAX_ID', db_scalar('select coalesce(max(id),0) from test_results'))
print('AFTER_BATCH', db_scalar('select coalesce(max(batch_id),0) from test_results'))
conn=sqlite3.connect(r"D:\JCY5001_clean\JCY5001AS_Clean_Source\data\test_results.db")
conn.row_factory=sqlite3.Row
cur=conn.cursor()
rows=cur.execute('select id,batch_id,channel_id,rs,rct,created_at from test_results order by id desc limit 12').fetchall()
for r in rows:
    print(dict(r))
conn.close()
