
import os
log_file = 'logs/app.log'
if os.path.exists(log_file):
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    # 搜索包含 COM 或 connect 的行
    for line in lines[-200:]:
        if 'COM' in line or 'connect' in line.lower():
            print(line.strip())
