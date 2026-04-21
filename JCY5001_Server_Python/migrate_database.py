"""
数据库迁移脚本
更新云端数据库结构以支持完整的数据同步功能
"""

import os
import sys
import logging
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from flask import Flask
from extensions import db
from config import Config

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


def migrate_database():
    """执行数据库迁移"""
    try:
        app = create_app()
        
        with app.app_context():
            logger.info("开始数据库迁移...")
            
            # 导入所有模型以确保表结构正确
            from models.user import User, Device, TestBatch, TestResult, ImpedanceDetail
            
            # 创建所有表
            logger.info("创建/更新数据库表...")
            db.create_all()
            
            # 检查表是否存在
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            expected_tables = ['users', 'devices', 'test_batches', 'test_results', 'impedance_details']
            
            for table in expected_tables:
                if table in tables:
                    logger.info(f"✅ 表 {table} 存在")
                    
                    # 获取表的列信息
                    columns = inspector.get_columns(table)
                    column_names = [col['name'] for col in columns]
                    logger.info(f"   列数: {len(column_names)}")
                    
                    # 显示一些关键列
                    if table == 'test_results':
                        key_columns = ['test_id', 'battery_code', 'rs_value', 'rct_value', 'rsei_value', 
                                     'impedance_ratio', 'test_start_time', 'test_end_time']
                        existing_key_columns = [col for col in key_columns if col in column_names]
                        logger.info(f"   关键列: {existing_key_columns}")
                    
                    elif table == 'impedance_details':
                        key_columns = ['test_id', 'frequency', 'impedance_real', 'impedance_imag', 
                                     'batch_id', 'channel_number', 'battery_code']
                        existing_key_columns = [col for col in key_columns if col in column_names]
                        logger.info(f"   关键列: {existing_key_columns}")
                        
                else:
                    logger.error(f"❌ 表 {table} 不存在")
            
            # 创建测试用户（如果不存在）
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                logger.info("创建管理员用户...")
                admin_user = User(
                    username='admin',
                    email='admin@jcy5001.com',
                    password='Admin123!',
                    company='JCY5001',
                    role='admin'
                )
                db.session.add(admin_user)
                db.session.commit()
                logger.info("✅ 管理员用户创建成功")
            else:
                logger.info("✅ 管理员用户已存在")
            
            # 显示统计信息
            logger.info("数据库统计信息:")
            logger.info(f"  用户数量: {User.query.count()}")
            logger.info(f"  设备数量: {Device.query.count()}")
            logger.info(f"  测试批次数量: {TestBatch.query.count()}")
            logger.info(f"  测试结果数量: {TestResult.query.count()}")
            logger.info(f"  阻抗明细数量: {ImpedanceDetail.query.count()}")
            
            logger.info("🎉 数据库迁移完成！")
            
    except Exception as e:
        logger.error(f"❌ 数据库迁移失败: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")


def test_database_connection():
    """测试数据库连接"""
    try:
        app = create_app()
        
        with app.app_context():
            # 测试数据库连接
            result = db.session.execute(db.text('SELECT 1'))
            logger.info("✅ 数据库连接正常")
            
            # 显示数据库信息
            logger.info(f"数据库URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")


def backup_database():
    """备份数据库（SQLite）"""
    try:
        app = create_app()
        
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            import shutil
            
            # 获取数据库文件路径
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            
            if os.path.exists(db_path):
                # 创建备份文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"{db_path}.backup_{timestamp}"
                
                # 复制数据库文件
                shutil.copy2(db_path, backup_path)
                logger.info(f"✅ 数据库备份完成: {backup_path}")
            else:
                logger.warning(f"⚠️ 数据库文件不存在: {db_path}")
        else:
            logger.info("ℹ️ 非SQLite数据库，跳过备份")
            
    except Exception as e:
        logger.error(f"❌ 数据库备份失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("JCY5001AS 云端数据库迁移工具")
    print("=" * 60)
    
    import argparse
    parser = argparse.ArgumentParser(description='数据库迁移工具')
    parser.add_argument('--test', action='store_true', help='测试数据库连接')
    parser.add_argument('--backup', action='store_true', help='备份数据库')
    parser.add_argument('--migrate', action='store_true', help='执行数据库迁移')
    
    args = parser.parse_args()
    
    if args.test:
        logger.info("测试数据库连接...")
        test_database_connection()
    
    if args.backup:
        logger.info("备份数据库...")
        backup_database()
    
    if args.migrate or not any([args.test, args.backup]):
        logger.info("执行数据库迁移...")
        migrate_database()
    
    print("\n" + "=" * 60)
    print("操作完成！")


if __name__ == '__main__':
    main()
