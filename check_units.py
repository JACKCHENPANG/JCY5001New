import sqlite3
import json
import sys

conn = sqlite3.connect(r'D:\JCY5001_clean\JCY5001AS_Clean_Source\data\test_results.db')
conn.row_factory = sqlite3.Row

# Get test #73
c = conn.execute('SELECT * FROM test_results WHERE id = 73')
row = c.fetchone()

# Parse raw_data to see actual units
raw_data = json.loads(row['raw_data'])
imp_data = raw_data['impedance_data']
freqs = imp_data['frequencies']
reals = imp_data['real_parts']
imags = imp_data['imag_parts']

# Get impedance_details for this batch/channel
c = conn.execute('''
    SELECT * FROM impedance_details 
    WHERE batch_id = ? AND channel_number = ? AND battery_code = ?
    ORDER BY frequency
''', (row['batch_id'], row['channel_number'], row['battery_code']))
details = c.fetchall()

print(f"=== raw_data vs impedance_details comparison ===")
print(f"raw_data has {len(freqs)} points, impedance_details has {len(details)} points")
print()

if len(details) > 0:
    print(f"{'Freq(Hz)':>10} | {'raw_real':>10} | {'raw_imag':>10} | {'det_real':>10} | {'det_imag':>10} | {'det_z':>10}")
    print("-" * 70)
    
    # Create lookup from details
    det_lookup = {}
    for d in details:
        det_lookup[d['frequency']] = d
    
    for i in range(min(len(freqs), 30)):
        f = freqs[i]
        rr = reals[i]
        ri = imags[i]
        if f in det_lookup:
            d = det_lookup[f]
            print(f"{f:>10.3f} | {rr:>10.3f} | {ri:>10.3f} | {d['impedance_real']:>10.3f} | {d['impedance_imag']:>10.3f} | {d['z_value'] if d['z_value'] else 0:>10.3f}")
        else:
            print(f"{f:>10.3f} | {rr:>10.3f} | {ri:>10.3f} | {'N/A':>10} | {'N/A':>10} | {'N/A':>10}")
else:
    print("No impedance_details found")
    print(f"\nraw_data real_parts range: {min(reals):.3f} - {max(reals):.3f}")
    print(f"raw_data imag_parts range: {min(imags):.3f} - {max(imags):.3f}")
    
    # Check if they seem to be in uOhm or mOhm
    print(f"\nDatabase stored rs_value: {row['rs_value']} mOhm")
    print(f"Database stored rct_value: {row['rct_value']} mOhm")
    
    # If raw_data is in uOhm, convert: 6100 uOhm = 6.1 mOhm
    print(f"\nIf raw_data is in uOhm:")
    print(f"  First real: {reals[0]:.3f} uOhm = {reals[0]/1000:.3f} mOhm")
    print(f"  Last real: {reals[-1]:.3f} uOhm = {reals[-1]/1000:.3f} mOhm")
    print(f"  Estimated Rs (highest freq): {reals[0]/1000:.3f} mOhm")
    print(f"  Database Rs: {row['rs_value']:.3f} mOhm")
    
    print(f"\nIf raw_data is in mOhm:")
    print(f"  First real: {reals[0]:.3f} mOhm")
    print(f"  Database Rs would be: {row['rs_value']:.3f} mOhm") 
    print(f"  These don't match unless raw_data unit is different")

# Also check the test_config
if 'test_config' in raw_data:
    print(f"\ntest_config: {json.dumps(raw_data['test_config'], indent=2)}")

conn.close()
