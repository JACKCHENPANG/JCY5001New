#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移工具
独立的数据库迁移和管理工具

Author: Jack
Date: 2025-07-08
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flask import Flask
from config import Config
from extensions import db
from database_migration import DatabaseMigration

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 初始化数据库
    db.init_app(app)
    
    return app


def show_status():
    """显示数据库状态"""
    app = create_app()
    migration = DatabaseMigration(app)
    
    status = migration.get_migration_status()
    
    print("=" * 60)
    print("数据库状态")
    print("=" * 60)
    print(f"数据库路径: {status['database_path']}")
    print(f"数据库存在: {'是' if status['database_exists'] else '否'}")
    print(f"当前版本: {status['current_version'] or '未知'}")
    print(f"目标版本: {status['target_version']}")
    
    if status['database_exists']:
        # 显示表信息
        print("\n表结构信息:")
        tables = ['users', 'devices', 'test_batches', 'test_results', 'impedance_details']
        
        for table in tables:
            if migration.table_exists(table):
                columns = migration.get_table_info(table)
                print(f"  {table}: {len(columns)} 列")
                for col in columns[:5]:  # 只显示前5列
                    print(f"    - {col[1]} ({col[2]})")
                if len(columns) > 5:
                    print(f"    ... 还有 {len(columns) - 5} 列")
            else:
                print(f"  {table}: 不存在")


def run_migration():
    """执行数据库迁移"""
    print("=" * 60)
    print("执行数据库迁移")
    print("=" * 60)
    
    app = create_app()
    migration = DatabaseMigration(app)
    
    success = migration.run_migration()
    
    if success:
        print("\n✅ 数据库迁移成功完成！")
    else:
        print("\n❌ 数据库迁移失败！")
        sys.exit(1)


def backup_database():
    """备份数据库"""
    print("=" * 60)
    print("备份数据库")
    print("=" * 60)
    
    app = create_app()
    migration = DatabaseMigration(app)
    
    try:
        backup_path = migration.backup_database()
        if backup_path:
            print(f"✅ 数据库备份成功: {backup_path}")
        else:
            print("⚠️ 数据库不存在，跳过备份")
    except Exception as e:
        print(f"❌ 数据库备份失败: {e}")
        sys.exit(1)


def reset_database():
    """重置数据库"""
    print("=" * 60)
    print("重置数据库")
    print("=" * 60)
    
    app = create_app()
    migration = DatabaseMigration(app)
    
    # 确认操作
    confirm = input("⚠️ 这将删除所有数据！确认重置数据库？(输入 'YES' 确认): ")
    if confirm != 'YES':
        print("操作已取消")
        return
    
    try:
        # 备份现有数据库
        if os.path.exists(migration.db_path):
            backup_path = migration.backup_database()
            print(f"已备份现有数据库: {backup_path}")
            
            # 删除数据库文件
            os.remove(migration.db_path)
            print("已删除现有数据库文件")
        
        # 创建新数据库
        migration.create_fresh_database()
        print("✅ 数据库重置完成！")
        
    except Exception as e:
        print(f"❌ 数据库重置失败: {e}")
        sys.exit(1)


def test_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("测试数据库连接")
    print("=" * 60)
    
    try:
        app = create_app()
        
        with app.app_context():
            # 测试数据库连接
            result = db.session.execute(db.text('SELECT 1'))
            print("✅ 数据库连接正常")
            
            # 显示数据库信息
            print(f"数据库URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            # 测试查询
            from models.user import User
            user_count = User.query.count()
            print(f"用户数量: {user_count}")
            
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        sys.exit(1)


def validate_schema():
    """验证数据库模式"""
    print("=" * 60)
    print("验证数据库模式")
    print("=" * 60)
    
    app = create_app()
    migration = DatabaseMigration(app)
    
    # 检查关键表和字段
    checks = [
        ('users', ['id', 'username', 'email', 'password_hash', 'role']),
        ('devices', ['id', 'device_id', 'user_id', 'name', 'model', 'firmware_version']),
        ('test_results', ['id', 'test_id', 'batch_id', 'channel_number', 'battery_code']),
        ('impedance_details', ['id', 'test_id', 'frequency', 'impedance_real', 'impedance_imag'])
    ]
    
    all_valid = True
    
    for table_name, required_columns in checks:
        print(f"\n检查表: {table_name}")
        
        if not migration.table_exists(table_name):
            print(f"  ❌ 表不存在")
            all_valid = False
            continue
        
        columns = migration.get_table_info(table_name)
        column_names = [col[1] for col in columns]
        
        for required_col in required_columns:
            if required_col in column_names:
                print(f"  ✅ {required_col}")
            else:
                print(f"  ❌ {required_col} (缺失)")
                all_valid = False
    
    if all_valid:
        print("\n✅ 数据库模式验证通过")
    else:
        print("\n❌ 数据库模式验证失败")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='JCY5001AS 数据库迁移工具')
    parser.add_argument('--status', action='store_true', help='显示数据库状态')
    parser.add_argument('--migrate', action='store_true', help='执行数据库迁移')
    parser.add_argument('--backup', action='store_true', help='备份数据库')
    parser.add_argument('--reset', action='store_true', help='重置数据库')
    parser.add_argument('--test', action='store_true', help='测试数据库连接')
    parser.add_argument('--validate', action='store_true', help='验证数据库模式')
    
    args = parser.parse_args()
    
    # 如果没有指定参数，显示帮助
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    print("JCY5001AS 数据库迁移工具")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        if args.status:
            show_status()
        
        if args.backup:
            backup_database()
        
        if args.test:
            test_connection()
        
        if args.validate:
            validate_schema()
        
        if args.reset:
            reset_database()
        
        if args.migrate:
            run_migration()
        
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"操作失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == '__main__':
    main()
