#!/usr/bin/env python3
"""
数据库初始化脚本
创建默认管理员用户和示例数据
"""

import os
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import create_app
from src.extensions import db
from src.models.user import User, Device

def init_database():
    """初始化数据库"""
    app = create_app()
    
    with app.app_context():
        try:
            # 删除所有表（如果存在）
            db.drop_all()
            print("已删除所有现有表")
            
            # 创建所有表
            db.create_all()
            print("已创建所有数据库表")
            
            # 检查是否已存在管理员用户
            admin_user = User.query.filter_by(username='admin').first()
            if admin_user:
                print("管理员用户已存在")
                return
            
            # 创建默认管理员用户
            admin_user = User(
                username='admin',
                email='admin@jcytest.com',
                password='Admin123!',  # 这会自动进行哈希处理
                company='JCY Technology',
                role='admin'
            )
            
            db.session.add(admin_user)
            db.session.flush()  # 获取用户ID
            
            print(f"创建管理员用户: {admin_user.username}")
            print(f"用户ID: {admin_user.id}")
            print(f"邮箱: {admin_user.email}")
            print(f"角色: {admin_user.role}")
            
            # 创建示例设备
            sample_device = Device(
                device_id='JCY5001-001',
                user_id=admin_user.id,
                name='JCY5001测试设备',
                model='JCY5001',
                firmware_version='1.0.0'
            )
            
            db.session.add(sample_device)
            
            # 提交所有更改
            db.session.commit()
            
            print("✅ 数据库初始化完成")
            print("管理员账号: admin")
            print("管理员密码: Admin123!")
            
            # 验证用户创建
            test_user = User.query.filter_by(username='admin').first()
            if test_user:
                print(f"✅ 用户验证成功: {test_user.username}")
                if test_user.check_password('Admin123!'):
                    print("✅ 密码验证成功")
                else:
                    print("❌ 密码验证失败")
            else:
                print("❌ 用户创建失败")
                
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    init_database()
