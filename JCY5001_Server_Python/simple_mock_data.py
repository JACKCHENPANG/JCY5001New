#!/usr/bin/env python3
"""
直接向数据库插入模拟测试数据
"""

import sqlite3
import random
import math
from datetime import datetime, timedelta

def create_simple_test_data():
    """创建简单的测试数据"""
    # 连接数据库
    conn = sqlite3.connect('instance/battery_impedance.db')
    cursor = conn.cursor()
    
    print("开始创建模拟测试数据...")
    
    # 获取管理员用户ID
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    admin_user = cursor.fetchone()
    if not admin_user:
        print("错误：找不到管理员用户")
        return
    
    admin_user_id = admin_user[0]
    print(f"找到管理员用户ID: {admin_user_id}")
    
    # 创建设备（如果不存在）
    devices_data = [
        ('JCY5001A_001', '生产线A-测试台1'),
        ('JCY5001A_002', '生产线A-测试台2'),
        ('JCY5001A_003', '生产线B-测试台1'),
    ]
    
    device_ids = []
    for device_id, name in devices_data:
        cursor.execute("SELECT id FROM devices WHERE device_id = ?", (device_id,))
        existing = cursor.fetchone()
        if not existing:
            cursor.execute("""
                INSERT INTO devices (device_id, user_id, name, model, status, created_at, updated_at)
                VALUES (?, ?, ?, 'JCY5001', 'active', ?, ?)
            """, (device_id, admin_user_id, name, datetime.now(), datetime.now()))
            device_db_id = cursor.lastrowid
        else:
            device_db_id = existing[0]
        device_ids.append((device_db_id, device_id))
    
    print(f"创建了 {len(device_ids)} 个设备")
    
    # 创建电池
    cell_types = ['LFP', 'NMC', 'LCO']
    battery_ids = []
    
    for i, cell_type in enumerate(cell_types):
        for j in range(5):  # 每种类型5个电池
            battery_id = f"BAT_{cell_type}_{i+1:03d}_{j+1:02d}"
            batch_number = f"BATCH_{cell_type}_{i+1:03d}"
            
            cursor.execute("SELECT id FROM batteries WHERE battery_id = ?", (battery_id,))
            existing = cursor.fetchone()
            if not existing:
                cursor.execute("""
                    INSERT INTO batteries (battery_id, batch_number, cell_type, nominal_capacity, 
                                         nominal_voltage, manufacturer, production_date, created_at)
                    VALUES (?, ?, ?, ?, 3.7, ?, ?, ?)
                """, (battery_id, batch_number, cell_type, random.uniform(2800, 3200),
                     f"厂商{i+1}", (datetime.now() - timedelta(days=random.randint(1, 30))).date(),
                     datetime.now()))
                battery_db_id = cursor.lastrowid
            else:
                battery_db_id = existing[0]
            battery_ids.append(battery_db_id)
    
    print(f"创建了 {len(battery_ids)} 个电池")
    
    # 创建测试批次
    test_batch_ids = []
    for device_db_id, device_id in device_ids:
        for j in range(3):  # 每个设备3个批次
            batch_id = f"BATCH_{device_id}_{j+1:03d}"
            start_time = datetime.now() - timedelta(days=random.randint(1, 7), hours=random.randint(0, 23))
            
            cursor.execute("SELECT id FROM test_batches WHERE batch_id = ?", (batch_id,))
            existing = cursor.fetchone()
            if not existing:
                cursor.execute("""
                    INSERT INTO test_batches (batch_id, device_id, user_id, start_time, 
                                            end_time, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 'completed', ?, ?)
                """, (batch_id, device_db_id, admin_user_id, start_time,
                     start_time + timedelta(hours=random.randint(1, 8)),
                     datetime.now(), datetime.now()))
                batch_db_id = cursor.lastrowid
            else:
                batch_db_id = existing[0]
            test_batch_ids.append(batch_db_id)
    
    print(f"创建了 {len(test_batch_ids)} 个测试批次")
    
    # 创建测试结果
    test_results_count = 0
    impedance_details_count = 0
    
    for batch_db_id in test_batch_ids:
        # 每个批次创建多个测试结果
        num_tests = random.randint(5, 15)
        
        for i in range(num_tests):
            # 随机选择电池
            battery_db_id = random.choice(battery_ids)
            
            # 生成阻抗数据
            rs_value = random.uniform(10, 25)
            rct_value = random.uniform(15, 35)
            
            # 创建测试结果
            test_id = f"TEST_{batch_db_id}_{i+1:03d}"
            test_time = datetime.now() - timedelta(minutes=random.randint(0, 480))
            
            # 判断测试结果
            is_pass = rs_value < 20 and rct_value < 30 and random.random() > 0.1  # 90%合格率
            
            cursor.execute("""
                INSERT INTO test_results (test_id, batch_id, battery_id, channel_number, test_time,
                                        voltage, rs_value, rct_value, capacity, thickness, temperature,
                                        test_result, error_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (test_id, batch_db_id, battery_db_id, random.randint(1, 8), test_time,
                 random.uniform(3.2, 4.2), rs_value, rct_value, random.uniform(2800, 3200),
                 random.uniform(5.0, 8.0), random.uniform(20, 30),
                 'pass' if is_pass else 'fail',
                 None if is_pass else f"ERR_{random.randint(100, 999)}",
                 datetime.now()))
            
            test_result_db_id = cursor.lastrowid
            test_results_count += 1
            
            # 创建阻抗明细数据
            frequencies = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 7800]
            
            # 添加一些随机变化
            rs = rs_value + random.uniform(-1, 1)
            rct = rct_value + random.uniform(-2, 2)
            c = random.uniform(0.8e-3, 1.2e-3)  # 电容约1mF
            
            for freq in frequencies:
                omega = 2 * math.pi * freq
                
                # 简化的Randles等效电路模型：Rs + Rct/(1 + j*w*Rct*C)
                z_rct = rct / (1 + 1j * omega * rct * c)
                z_total = rs + z_rct
                
                real_part = z_total.real
                imag_part = z_total.imag
                magnitude = abs(z_total)
                phase = math.degrees(math.atan2(imag_part, real_part))
                
                cursor.execute("""
                    INSERT INTO impedance_details (test_id, frequency, z_real, z_imag, 
                                                  z_magnitude, phase_angle, measurement_time, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (test_result_db_id, freq, real_part, imag_part, magnitude, phase, test_time, datetime.now()))
                
                impedance_details_count += 1
    
    # 提交事务
    conn.commit()
    conn.close()
    
    print(f"创建了 {test_results_count} 个测试结果")
    print(f"创建了 {impedance_details_count} 个阻抗明细数据点")
    print("模拟数据创建完成！")

if __name__ == '__main__':
    create_simple_test_data()
