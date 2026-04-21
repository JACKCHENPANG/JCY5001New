#!/usr/bin/env python3
"""
创建模拟测试数据脚本
用于演示数据分析页面功能
"""

import sys
import os
import random
import math
from datetime import datetime, timedelta

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from extensions import db
from models.user import User, Device, Battery, TestBatch, TestResult, ImpedanceDetail
from main import create_app

def generate_impedance_data(rs_base=15.0, rct_base=25.0):
    """生成模拟阻抗数据"""
    frequencies = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 7800]
    impedance_data = []
    
    # 添加一些随机变化
    rs = rs_base + random.uniform(-2, 2)
    rct = rct_base + random.uniform(-5, 5)
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
        
        impedance_data.append({
            'frequency': freq,
            'z_real': real_part,
            'z_imag': imag_part,
            'z_magnitude': magnitude,
            'phase_angle': phase
        })
    
    return impedance_data, rs, rct

def create_mock_data():
    """创建模拟测试数据"""
    app = create_app()

    with app.app_context():
        print("开始创建模拟测试数据...")

        # 确保数据库表存在
        try:
            db.create_all()
            print("数据库表检查完成")
        except Exception as e:
            print(f"数据库表创建失败: {e}")
            return

        # 获取管理员用户
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("错误：找不到管理员用户")
            return
        
        # 创建设备（如果不存在）
        devices_data = [
            {'device_id': 'JCY5001A_001', 'name': '生产线A-测试台1'},
            {'device_id': 'JCY5001A_002', 'name': '生产线A-测试台2'},
            {'device_id': 'JCY5001A_003', 'name': '生产线B-测试台1'},
        ]
        
        devices = []
        for device_data in devices_data:
            device = Device.query.filter_by(device_id=device_data['device_id']).first()
            if not device:
                device = Device(
                    device_id=device_data['device_id'],
                    user_id=admin_user.id,
                    name=device_data['name'],
                    model='JCY5001'
                )
                db.session.add(device)
            devices.append(device)
        
        db.session.commit()
        print(f"创建了 {len(devices)} 个设备")
        
        # 创建电池类型
        cell_types = ['LFP', 'NMC', 'LCO']
        batteries = []
        
        for i, cell_type in enumerate(cell_types):
            for j in range(5):  # 每种类型5个电池
                battery_id = f"BAT_{cell_type}_{i+1:03d}_{j+1:02d}"
                battery = Battery.query.filter_by(battery_id=battery_id).first()
                if not battery:
                    battery = Battery(
                        battery_id=battery_id,
                        batch_number=f"BATCH_{cell_type}_{i+1:03d}",
                        cell_type=cell_type,
                        nominal_capacity=random.uniform(2800, 3200),
                        nominal_voltage=3.7,
                        manufacturer=f"厂商{i+1}",
                        production_date=datetime.now().date() - timedelta(days=random.randint(1, 30))
                    )
                    db.session.add(battery)
                batteries.append(battery)
        
        db.session.commit()
        print(f"创建了 {len(batteries)} 个电池")
        
        # 创建测试批次
        test_batches = []
        for i, device in enumerate(devices):
            for j in range(3):  # 每个设备3个批次
                batch_id = f"BATCH_{device.device_id}_{j+1:03d}"
                test_batch = TestBatch.query.filter_by(batch_id=batch_id).first()
                if not test_batch:
                    start_time = datetime.now() - timedelta(days=random.randint(1, 7), hours=random.randint(0, 23))
                    test_batch = TestBatch(
                        batch_id=batch_id,
                        device_id=device.id,
                        user_id=admin_user.id,
                        start_time=start_time,
                        end_time=start_time + timedelta(hours=random.randint(1, 8)),
                        status='completed'
                    )
                    db.session.add(test_batch)
                test_batches.append(test_batch)
        
        db.session.commit()
        print(f"创建了 {len(test_batches)} 个测试批次")
        
        # 创建测试结果和阻抗明细
        test_results_count = 0
        impedance_details_count = 0
        
        for test_batch in test_batches:
            # 每个批次创建多个测试结果
            num_tests = random.randint(5, 15)
            
            for i in range(num_tests):
                # 随机选择电池
                battery = random.choice(batteries)
                
                # 生成阻抗数据
                impedance_data, rs_value, rct_value = generate_impedance_data()
                
                # 创建测试结果
                test_id = f"TEST_{test_batch.batch_id}_{i+1:03d}"
                test_time = test_batch.start_time + timedelta(minutes=random.randint(0, 480))
                
                # 判断测试结果
                is_pass = rs_value < 20 and rct_value < 30 and random.random() > 0.1  # 90%合格率
                
                test_result = TestResult(
                    test_id=test_id,
                    batch_id=test_batch.id,
                    battery_id=battery.id,
                    channel_number=random.randint(1, 8),
                    test_time=test_time,
                    voltage=random.uniform(3.2, 4.2),
                    rs_value=rs_value,
                    rct_value=rct_value,
                    capacity=random.uniform(2800, 3200),
                    thickness=random.uniform(5.0, 8.0),
                    temperature=random.uniform(20, 30),
                    test_result='pass' if is_pass else 'fail',
                    error_code=None if is_pass else f"ERR_{random.randint(100, 999)}"
                )
                
                db.session.add(test_result)
                db.session.flush()  # 获取test_result.id
                
                test_results_count += 1
                
                # 创建阻抗明细数据
                for impedance_point in impedance_data:
                    impedance_detail = ImpedanceDetail(
                        test_id=test_result.id,
                        frequency=impedance_point['frequency'],
                        measurement_time=test_time,
                        z_real=impedance_point['z_real'],
                        z_imag=impedance_point['z_imag'],
                        z_magnitude=impedance_point['z_magnitude'],
                        phase_angle=impedance_point['phase_angle']
                    )
                    db.session.add(impedance_detail)
                    impedance_details_count += 1
        
        # 更新测试批次统计
        for test_batch in test_batches:
            test_batch.update_statistics()
        
        db.session.commit()
        
        print(f"创建了 {test_results_count} 个测试结果")
        print(f"创建了 {impedance_details_count} 个阻抗明细数据点")
        print("模拟数据创建完成！")

if __name__ == '__main__':
    create_mock_data()
