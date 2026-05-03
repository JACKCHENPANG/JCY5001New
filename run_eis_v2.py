import sqlite3
import json
import sys
import os
import logging
import math

sys.path.insert(0, r'D:\JCY5001_clean\JCY5001AS_Clean_Source')

conn = sqlite3.connect(r'D:\JCY5001_clean\JCY5001AS_Clean_Source\data\test_results.db')
conn.row_factory = sqlite3.Row

c = conn.execute('SELECT * FROM test_results WHERE id = 73')
row = c.fetchone()

print(f"=== Test #73 Info ===")
print(f"Battery: {row['battery_code']}")
print(f"Voltage: {row['voltage']} V")
print(f"Test started: {row['test_start_time']}")
print(f"Database stored Rs:  {row['rs_value']:.4f} m\u03A9")
print(f"Database stored Rct: {row['rct_value']:.4f} m\u03A9")
print()

# Parse raw_data
raw_data = json.loads(row['raw_data'])
imp_data = raw_data['impedance_data']
freqs_raw = imp_data['frequencies']
reals_raw = imp_data['real_parts']  # in uOhm
imags_raw = imp_data['imag_parts']  # in uOhm

print(f"Raw data: {len(freqs_raw)} data points")
print(f"Raw data unit: \u03bc\u03A9 (micro-ohm)")
print(f"  First real: {reals_raw[0]:.3f} \u03bc\u03A9 = {reals_raw[0]/1000:.3f} m\u03A9")
print(f"  Last real:  {reals_raw[-1]:.3f} \u03bc\u03A9 = {reals_raw[-1]/1000:.3f} m\u03A9")
print()

# Convert from uOhm to mOhm for the analyzer
freqs = [float(f) for f in freqs_raw]
reals = [float(r) / 1000.0 for r in reals_raw]   # uOhm -> mOhm
imags = [float(i) / 1000.0 for i in imags_raw]   # uOhm -> mOhm

print(f"Converted to m\u03A9 for analysis:")
print(f"  Freq(Hz)     | Real(m\u03A9)   | Imag(m\u03A9)")
print("-" * 50)
for i in range(len(freqs)):
    print(f"  {freqs[i]:8.3f}   | {reals[i]:8.4f} | {imags[i]:8.4f}")
print()

# ====== Run EIS Analysis ======
print(f"{'='*60}")
print(f"  EIS ANALYSIS - Test #73 ({row['battery_code']})")
print(f"{'='*60}")
print()

from backend.eis_analyzer import EISAnalyzer

analyzer = EISAnalyzer()
analyzer.logger.setLevel(logging.INFO)

# Add a stream handler for output
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('  [%(levelname)s] %(message)s')
ch.setFormatter(formatter)
analyzer.logger.addHandler(ch)

result = analyzer.calculate_rs_rct_enhanced(freqs, reals, imags, cell_id=row['battery_code'])

print()
print(f"{'='*60}")
print(f"  RESULTS")
print(f"{'='*60}")
print()

# 1) Rs from zero-crossing (the _calculate_rs_zero_crossing method)
rs_value = result.get('rs_value', 0)

# 2) Rct from 2x peak method
rct_value = result.get('rct_value', 0)

print(f"  Rs (\u96f6\u4ea4\u53c9\u6cd5/\u865a\u90e8\u8fc7\u96f6\u70b9):")
print(f"    Rs = {rs_value:.4f} m\u03A9")
print()

print(f"  Rct (2\u00d7\u6b63\u865a\u90e8\u5cf0\u503c\u6cd5):")
print(f"    Rct = {rct_value:.4f} m\u03A9")
print()

# 3) Hybrid circuit fit results
hybrid_result = result.get('circuit_params', {})
print(f"  \u6df7\u5408\u7eaf\u5408\u7ed3\u679c:")
print(f"    \u65b9\u6cd5: {result.get('analysis_method', 'N/A')}")
print(f"    \u7ebf\u8def\u6a21\u578b: {result.get('circuit_model', 'N/A')}")
print(f"    \u8bef\u5dee: {result.get('fit_error', 0):.6f}")

if hybrid_result.get('c_model'):
    cm = hybrid_result['c_model']
    print(f"\n    C\u6a21\u578b (Rs + Rct//C):")
    print(f"      Rs  = {cm['rs']:.4f} m\u03A9")
    print(f"      Rct = {cm['rct']:.4f} m\u03A9")
    print(f"      C   = {cm['c']:.4e} F")
    print(f"      \u6b8b\u5dee = {cm['residual']:.4e}")

if hybrid_result.get('cpe_model'):
    cpe = hybrid_result['cpe_model']
    print(f"\n    CPE\u6a21\u578b (Rs + Rct//CPE):")
    print(f"      Rs    = {cpe['rs']:.4f} m\u03A9")
    print(f"      Rct   = {cpe['rct']:.4f} m\u03A9")
    print(f"      Q     = {cpe['q']:.4e}")
    print(f"      \u03b1    = {cpe['alpha']:.4f}")
    print(f"      \u6b8b\u5dee   = {cpe['residual']:.4e}")

print()
print(f"  \u5176\u4ed6\u53c2\u6570:")
print(f"    Rsei     = {result.get('rsei_value', 0):.4f} m\u03A9")
print(f"    W\u963b\u6297    = {result.get('w_impedance', 0):.4f} m\u03A9")
print(f"    \u7279\u5f81\u9891\u7387 = {result.get('characteristic_frequency', 0):.3f} Hz")
print(f"    \u6700\u5927\u76f8\u4f4d\u89d2 = {result.get('max_phase_angle', 0):.2f}\u00b0")

# Compare with DB
print()
print(f"  \u5bf9\u6bd4\u6570\u636e\u5e93:")
print(f"    DB Rs  = {row['rs_value']:.4f} m\u03A9")
print(f"    DB Rct = {row['rct_value']:.4f} m\u03A9")
print(f"    New Rs = {rs_value:.4f} m\u03A9")
print(f"    New Rct = {rct_value:.4f} m\u03A9")
rs_match = "✓" if abs(rs_value - row['rs_value']) < 0.1 else "Δ"
rct_match = "✓" if abs(rct_value - row['rct_value']) < 0.1 else "Δ"
print(f"    Match: Rs {rs_match}, Rct {rct_match}")

print()
print(f"{'='*60}")
print(f"  SUMMARY (all values in m\u03A9)")
print(f"{'='*60}")
print(f"  Rs  (\u96f6\u4ea4\u53c9\u6cd5):        {rs_value:.4f} m\u03A9")
print(f"  Rct (2\u00d7\u5cf0\u503c\u6cd5):        {rct_value:.4f} m\u03A9")
if hybrid_result.get('c_model'):
    print(f"  Rs  (C\u6a21\u578b\u7ecf\u5408):    {hybrid_result['c_model']['rs']:.4f} m\u03A9")
    print(f"  Rct (C\u6a21\u578b\u7ecf\u5408):    {hybrid_result['c_model']['rct']:.4f} m\u03A9")
if hybrid_result.get('cpe_model'):
    print(f"  Rs  (CPE\u6a21\u578b\u7ecf\u5408):  {hybrid_result['cpe_model']['rs']:.4f} m\u03A9")
    print(f"  Rct (CPE\u6a21\u578b\u7ecf\u5408):  {hybrid_result['cpe_model']['rct']:.4f} m\u03A9")
print(f"  \u6700\u4f73\u6a21\u578b:              {result.get('circuit_model', 'N/A')}")
print(f"  \u7ecf\u5408\u8bef\u5dee:              {result.get('fit_error', 0):.6f}")
print(f"{'='*60}")

conn.close()
