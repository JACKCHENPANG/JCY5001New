#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移管理器
提供完整的数据库版本控制和迁移功能

Author: Jack
Date: 2025-07-08
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from flask import Flask
from extensions import db
from models.user import User, Device, TestBatch, TestResult, ImpedanceDetail

logger = logging.getLogger(__name__)


class DatabaseMigration:
    """数据库迁移管理器"""
    
    # 数据库版本号
    CURRENT_VERSION = "1.2.0"
    
    def __init__(self, app: Flask):
        self.app = app
        self.db_path = self._get_db_path()
        
    def _get_db_path(self) -> str:
        """获取数据库文件路径"""
        db_uri = self.app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if db_uri.startswith('sqlite:///'):
            path = db_uri.replace('sqlite:///', '')
            # 如果是相对路径，转换为绝对路径
            if not os.path.isabs(path):
                # 从Flask应用的根目录开始
                app_root = os.path.dirname(os.path.abspath(__file__))
                path = os.path.join(app_root, path)
            return path
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'battery_impedance.db')
    
    def get_current_version(self) -> Optional[str]:
        """获取当前数据库版本"""
        try:
            if not os.path.exists(self.db_path):
                return None
                
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查版本表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='database_version'
            """)
            
            if not cursor.fetchone():
                conn.close()
                return None
            
            # 获取版本号
            cursor.execute("SELECT version FROM database_version ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"获取数据库版本失败: {e}")
            return None
    
    def create_version_table(self):
        """创建版本管理表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS database_version (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    description TEXT,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("版本管理表创建成功")
            
        except Exception as e:
            logger.error(f"创建版本管理表失败: {e}")
            raise
    
    def set_version(self, version: str, description: str = ""):
        """设置数据库版本"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO database_version (version, description)
                VALUES (?, ?)
            """, (version, description))
            
            conn.commit()
            conn.close()
            logger.info(f"数据库版本设置为: {version}")
            
        except Exception as e:
            logger.error(f"设置数据库版本失败: {e}")
            raise
    
    def backup_database(self) -> str:
        """备份数据库"""
        try:
            if not os.path.exists(self.db_path):
                logger.warning("数据库文件不存在，跳过备份")
                return ""
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{self.db_path}.backup_{timestamp}"
            
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"数据库备份完成: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            raise
    
    def get_table_info(self, table_name: str) -> List[Tuple]:
        """获取表结构信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            conn.close()
            return columns
            
        except Exception as e:
            logger.error(f"获取表{table_name}信息失败: {e}")
            return []
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (table_name,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"检查表{table_name}是否存在失败: {e}")
            return False
    
    def column_exists(self, table_name: str, column_name: str) -> bool:
        """检查列是否存在"""
        columns = self.get_table_info(table_name)
        column_names = [col[1] for col in columns]
        return column_name in column_names
    
    def add_column(self, table_name: str, column_name: str, column_type: str, default_value: str = None):
        """添加列"""
        try:
            if self.column_exists(table_name, column_name):
                logger.info(f"列 {table_name}.{column_name} 已存在")
                return
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            if default_value:
                sql += f" DEFAULT {default_value}"
            
            cursor.execute(sql)
            conn.commit()
            conn.close()
            
            logger.info(f"添加列: {table_name}.{column_name}")
            
        except Exception as e:
            logger.error(f"添加列{table_name}.{column_name}失败: {e}")
            raise
    
    def migrate_to_v1_0_0(self):
        """迁移到版本1.0.0 - 基础表结构"""
        logger.info("执行迁移: v1.0.0 - 基础表结构")
        
        with self.app.app_context():
            # 创建所有基础表
            db.create_all()
            logger.info("基础表结构创建完成")
    
    def migrate_to_v1_1_0(self):
        """迁移到版本1.1.0 - 添加firmware_version字段"""
        logger.info("执行迁移: v1.1.0 - 添加firmware_version字段")
        
        # 确保devices表存在firmware_version字段
        if self.table_exists('devices'):
            self.add_column('devices', 'firmware_version', 'TEXT')
        
        # 添加其他可能缺失的字段
        if self.table_exists('test_results'):
            self.add_column('test_results', 'rsei_value', 'NUMERIC(8,4)')
            self.add_column('test_results', 'w_impedance', 'NUMERIC(8,4)')
        
        if self.table_exists('impedance_details'):
            self.add_column('impedance_details', 'z_value', 'NUMERIC(10,6)')
            self.add_column('impedance_details', 'baseline_z_value', 'NUMERIC(10,6)')
            self.add_column('impedance_details', 'deviation_percent', 'NUMERIC(8,4)')
    
    def migrate_to_v1_2_0(self):
        """迁移到版本1.2.0 - 完善数据结构"""
        logger.info("执行迁移: v1.2.0 - 完善数据结构")
        
        # 确保所有表都有正确的索引
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 为关键字段添加索引
            indexes = [
                ("idx_devices_device_id", "devices", "device_id"),
                ("idx_test_results_test_id", "test_results", "test_id"),
                ("idx_test_results_batch_id", "test_results", "batch_id"),
                ("idx_test_results_start_time", "test_results", "test_start_time"),
                ("idx_impedance_details_test_id", "impedance_details", "test_id"),
                ("idx_impedance_details_frequency", "impedance_details", "frequency"),
            ]
            
            for index_name, table_name, column_name in indexes:
                try:
                    cursor.execute(f"""
                        CREATE INDEX IF NOT EXISTS {index_name} 
                        ON {table_name} ({column_name})
                    """)
                    logger.info(f"创建索引: {index_name}")
                except Exception as e:
                    logger.warning(f"创建索引{index_name}失败: {e}")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"创建索引失败: {e}")
    
    def run_migration(self) -> bool:
        """执行数据库迁移"""
        try:
            logger.info("开始数据库迁移...")
            
            # 获取当前版本
            current_version = self.get_current_version()
            logger.info(f"当前数据库版本: {current_version}")
            logger.info(f"目标版本: {self.CURRENT_VERSION}")
            
            # 如果数据库不存在，创建新数据库
            if not os.path.exists(self.db_path):
                logger.info("数据库不存在，创建新数据库")
                self.create_fresh_database()
                return True
            
            # 创建版本管理表
            self.create_version_table()
            
            # 如果没有版本信息，说明是旧数据库
            if current_version is None:
                logger.info("检测到旧数据库，开始迁移")
                self.backup_database()
                current_version = "0.0.0"
            
            # 执行迁移
            if self._version_compare(current_version, "1.0.0") < 0:
                self.migrate_to_v1_0_0()
                self.set_version("1.0.0", "基础表结构")
            
            if self._version_compare(current_version, "1.1.0") < 0:
                self.migrate_to_v1_1_0()
                self.set_version("1.1.0", "添加firmware_version字段")
            
            if self._version_compare(current_version, "1.2.0") < 0:
                self.migrate_to_v1_2_0()
                self.set_version("1.2.0", "完善数据结构")
            
            logger.info("数据库迁移完成")
            return True
            
        except Exception as e:
            logger.error(f"数据库迁移失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False
    
    def create_fresh_database(self):
        """创建全新数据库"""
        logger.info("创建全新数据库")
        
        with self.app.app_context():
            # 创建所有表
            db.create_all()
            
            # 创建版本管理表
            self.create_version_table()
            
            # 设置当前版本
            self.set_version(self.CURRENT_VERSION, "全新数据库")
            
            # 创建默认管理员用户
            self.create_default_admin()
            
            logger.info("全新数据库创建完成")
    
    def create_default_admin(self):
        """创建默认管理员用户"""
        try:
            with self.app.app_context():
                admin_user = User.query.filter_by(username='admin').first()
                if not admin_user:
                    admin_user = User(
                        username='admin',
                        email='admin@jcytest.com',
                        password='Admin123!',
                        company='JCY Technology',
                        role='admin'
                    )
                    db.session.add(admin_user)
                    db.session.flush()
                    
                    # 创建示例设备
                    sample_device = Device(
                        device_id='JCY5001-001',
                        user_id=admin_user.id,
                        name='JCY5001测试设备',
                        model='JCY5001',
                        firmware_version='1.0.0'
                    )
                    db.session.add(sample_device)
                    
                    db.session.commit()
                    logger.info("默认管理员用户创建成功")
                else:
                    logger.info("管理员用户已存在")
                    
        except Exception as e:
            logger.error(f"创建默认管理员用户失败: {e}")
            db.session.rollback()
    
    def _version_compare(self, version1: str, version2: str) -> int:
        """比较版本号"""
        def version_tuple(v):
            return tuple(map(int, v.split('.')))
        
        v1 = version_tuple(version1)
        v2 = version_tuple(version2)
        
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0
    
    def get_migration_status(self) -> Dict:
        """获取迁移状态"""
        return {
            'current_version': self.get_current_version(),
            'target_version': self.CURRENT_VERSION,
            'database_exists': os.path.exists(self.db_path),
            'database_path': self.db_path
        }


def init_database_with_migration(app: Flask) -> bool:
    """使用迁移机制初始化数据库"""
    try:
        migration = DatabaseMigration(app)
        return migration.run_migration()
    except Exception as e:
        logger.error(f"数据库迁移初始化失败: {e}")
        return False
