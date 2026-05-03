import sqlite3
import json
import sys
import os

# Add the project backend to path
sys.path.insert(0, r'D:\JCY5001_clean\JCY5001AS_Clean_Source')

conn = sqlite3.connect(r'D:\JCY5001_clean\JCY5001AS_Clean_Source\data\test_results.db')
conn.row_factory = sqlite3.Row

# Get test #73 full raw_data
c = conn.execute('SELECT * FROM test_results WHERE id = 73')
row = c.fetchone()

if not row:
    print("ERROR: No test with id=73 found")
    sys.exit(1)

print(f"=== Test #73 ===")
print(f"Battery: {row['battery_code']}")
print(f"Voltage: {row['voltage']} V")
print(f"Test time: {row['test_start_time']}")

raw_data_str = row['raw_data']
print(f"\nraw_data length: {len(raw_data_str)} chars")

# Parse raw_data
raw_data = json.loads(raw_data_str)
print(f"raw_data keys: {list(raw_data.keys())}")

if 'impedance_data' in raw_data:
    imp_data = raw_data['impedance_data']
    freqs = imp_data['frequencies']
    reals = imp_data['real_parts']
    imags = imp_data['imag_parts']
    print(f"EIS data points: {len(freqs)}")
    print(f"Frequency range: {min(freqs):.3f} - {max(freqs):.3f} Hz")
elif 'frequencies' in raw_data:
    freqs = raw_data['frequencies']
    reals = raw_data['real_parts']
    imags = raw_data['imag_parts']
else:
    print(f"Unknown raw_data format. Keys: {list(raw_data.keys())}")
    # Try to dump raw_data
    print(f"raw_data content: {json.dumps(raw_data, indent=2)[:2000]}")
    sys.exit(1)

print(f"\n=== EIS Sweep Data ===")
for i in range(len(freqs)):
    print(f"  {freqs[i]:8.3f} Hz | {reals[i]:10.3f} m\u03A9 | {imags[i]:10.3f} m\u03A9")

# Now import and run the analyzer
print("\n\n=== Running EIS Analysis ===")
from backend.eis_analyzer import EISAnalyzer

analyzer = EISAnalyzer()

# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')
analyzer.logger.setLevel(logging.DEBUG)

result = analyzer.calculate_rs_rct_enhanced(freqs, reals, imags, cell_id=row['battery_code'])

print("\n\n========== EIS ANALYSIS RESULTS ==========")
print(f"Test ID: 73")
print(f"Battery: {row['battery_code']}")
print(f"Voltage: {row['voltage']} V")
print(f"Data points: {result.get('data_points', len(freqs))}")
print(f"Frequency range: {result.get('frequency_range', [min(freqs), max(freqs)])}")
print()

# Rs - Zero crossing method
rs_value = result.get('rs_value', 0)
print(f"--- Rs (零交叉法/虚部过零点) ---")
print(f"  Rs = {rs_value:.4f} m\u03A9")
print()

# Rct - Peak method  
rct_value = result.get('rct_value', 0)
print(f"--- Rct (2\u00d7正虚部峰值法) ---")
print(f"  Rct = {rct_value:.4f} m\u03A9")
print()

# Analysis method & circuit model
print(f"--- 分析方法 ---")
print(f"  方法: {result.get('analysis_method', 'N/A')}")
print(f"  电路模型: {result.get('circuit_model', 'N/A')}")
print(f"  拟合误差: {result.get('fit_error', 0):.6f}")
print()

# Circuit params detail
circuit_params = result.get('circuit_params', {})
if circuit_params.get('c_model'):
    cm = circuit_params['c_model']
    print(f"--- C模型拟合 (Rs + Rct//C) ---")
    print(f"  Rs  = {cm['rs']:.4f} m\u03A9")
    print(f"  Rct = {cm['rct']:.4f} m\u03A9")
    print(f"  C   = {cm['c']:.6e} F")
    print(f"  残差 = {cm['residual']:.6e}")
    print()

if circuit_params.get('cpe_model'):
    cpe = circuit_params['cpe_model']
    print(f"--- CPE模型拟合 (Rs + Rct//CPE) ---")
    print(f"  Rs    = {cpe['rs']:.4f} m\u03A9")
    print(f"  Rct   = {cpe['rct']:.4f} m\u03A9")
    print(f"  Q     = {cpe['q']:.6e}")
    print(f"  \u03B1    = {cpe['alpha']:.4f}")
    print(f"  残差   = {cpe['residual']:.6e}")
    print()

# Other parameters
print(f"--- 其他参数 ---")
print(f"  Rsei = {result.get('rsei_value', 0):.4f} m\u03A9")
print(f"  W阻抗 = {result.get('w_impedance', 0):.4f} m\u03A9")
print(f"  特征频率 = {result.get('characteristic_frequency', 0):.3f} Hz")
print(f"  最大相位角 = {result.get('max_phase_angle', 0):.2f} deg")
print()

# Compare with original DB values
print(f"--- 与数据库原始值对比 ---")
print(f"  数据库 Rs  = {row['rs_value']:.4f} m\u03A9")
print(f"  数据库 Rct = {row['rct_value']:.4f} m\u03A9")
print(f"  新分析 Rs  = {rs_value:.4f} m\u03A9")
print(f"  新分析 Rct = {rct_value:.4f} m\u03A9")
print()

# Summary
print("========== SUMMARY (单位: m\u03A9) ==========")
print(f"Rs  (零交叉法):       {rs_value:.4f}")
print(f"Rct (2\u00d7峰值法):     {rct_value:.4f}")
if circuit_params.get('c_model'):
    print(f"Rs  (C模型拟合):     {circuit_params['c_model']['rs']:.4f}")
    print(f"Rct (C模型拟合):     {circuit_params['c_model']['rct']:.4f}")
if circuit_params.get('cpe_model'):
    print(f"Rs  (CPE模型拟合):   {circuit_params['cpe_model']['rs']:.4f}")
    print(f"Rct (CPE模型拟合):   {circuit_params['cpe_model']['rct']:.4f}")
print(f"最佳电路模型:         {result.get('circuit_model', 'N/A')}")
print(f"拟合误差:             {result.get('fit_error', 0):.6f}")

conn.close()
