#!/usr/bin/env python3
"""
通过API创建模拟测试数据
"""

import requests
import json
import random
import math
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5002"

def login():
    """登录获取token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "Admin123!"
    })
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"登录失败: {response.text}")
        return None

def create_test_data(token):
    """创建测试数据"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 创建一些测试结果
    devices = ["JCY5001A_001", "JCY5001A_002", "JCY5001A_003"]
    cell_types = ["LFP", "NMC", "LCO"]
    
    for i in range(20):  # 创建20条测试记录
        # 生成随机测试数据
        device_id = random.choice(devices)
        cell_type = random.choice(cell_types)
        channel = random.randint(1, 8)
        
        # 生成阻抗数据
        rs_value = random.uniform(10, 25)
        rct_value = random.uniform(15, 35)
        rsei_value = random.uniform(5, 15)
        
        # 判断测试结果
        is_pass = rs_value < 20 and rct_value < 30
        
        test_data = {
            "test_id": f"TEST_{device_id}_{i+1:03d}",
            "device_id": device_id,
            "batch_id": f"BATCH_{device_id}_{(i//5)+1:03d}",
            "channel_number": channel,
            "voltage": round(random.uniform(3.2, 4.2), 3),
            "rs_value": round(rs_value, 3),
            "rct_value": round(rct_value, 3),
            "rsei": round(rsei_value, 3),
            "capacity": round(random.uniform(2800, 3200), 1),
            "thickness": round(random.uniform(5.0, 8.0), 2),
            "temperature": round(random.uniform(20, 30), 1),
            "test_result": "pass" if is_pass else "fail",
            "error_code": None if is_pass else f"ERR_{random.randint(100, 999)}",
            "cell_type": cell_type,
            "test_time": (datetime.now() - timedelta(days=random.randint(0, 7), hours=random.randint(0, 23))).isoformat()
        }
        
        # 发送测试结果
        response = requests.post(f"{BASE_URL}/api/test-results", json=test_data, headers=headers)
        if response.status_code == 201:
            print(f"创建测试结果 {i+1}/20: {test_data['test_id']}")
            
            # 为这个测试结果创建阻抗明细数据
            test_result_id = response.json()['result']['id']
            create_impedance_details(token, test_result_id, rs_value, rct_value)
        else:
            print(f"创建测试结果失败 {i+1}: {response.text}")

def create_impedance_details(token, test_result_id, rs_base, rct_base):
    """为测试结果创建阻抗明细数据"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 生成频率点数据
    frequencies = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 7800]
    
    # 添加一些随机变化
    rs = rs_base + random.uniform(-1, 1)
    rct = rct_base + random.uniform(-2, 2)
    c = random.uniform(0.8e-3, 1.2e-3)  # 电容约1mF
    
    impedance_details = []
    
    for freq in frequencies:
        omega = 2 * math.pi * freq
        
        # 简化的Randles等效电路模型：Rs + Rct/(1 + j*w*Rct*C)
        z_rct = rct / (1 + 1j * omega * rct * c)
        z_total = rs + z_rct
        
        real_part = z_total.real
        imag_part = z_total.imag
        magnitude = abs(z_total)
        phase = math.degrees(math.atan2(imag_part, real_part))
        
        detail_data = {
            "test_result_id": test_result_id,
            "frequency": freq,
            "z_real": round(real_part, 6),
            "z_imag": round(imag_part, 6),
            "z_magnitude": round(magnitude, 6),
            "phase_angle": round(phase, 4),
            "measurement_time": datetime.now().isoformat()
        }
        
        impedance_details.append(detail_data)
    
    # 批量创建阻抗明细数据
    response = requests.post(f"{BASE_URL}/api/impedance-details/batch", 
                           json={"details": impedance_details}, 
                           headers=headers)
    
    if response.status_code == 201:
        print(f"  -> 创建了 {len(impedance_details)} 个阻抗明细数据点")
    else:
        print(f"  -> 创建阻抗明细数据失败: {response.text}")

def main():
    print("开始通过API创建模拟测试数据...")
    
    # 登录
    token = login()
    if not token:
        print("登录失败，退出")
        return
    
    print("登录成功，开始创建测试数据...")
    
    # 创建测试数据
    create_test_data(token)
    
    print("模拟数据创建完成！")

if __name__ == '__main__':
    main()
