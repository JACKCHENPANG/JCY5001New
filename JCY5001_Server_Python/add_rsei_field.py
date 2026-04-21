#!/usr/bin/env python3
"""
数据库迁移脚本：添加rsei_value字段到test_results表
"""

import os
import sys
import sqlite3

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def add_rsei_field():
    """添加rsei_value字段到test_results表"""
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'battery_impedance.db')
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查rsei_value字段是否已存在
        cursor.execute("PRAGMA table_info(test_results)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'rsei_value' in columns:
            print("rsei_value字段已存在，无需添加")
            conn.close()
            return True
        
        # 添加rsei_value字段
        cursor.execute("ALTER TABLE test_results ADD COLUMN rsei_value NUMERIC(8, 4)")
        conn.commit()
        
        print("✅ 成功添加rsei_value字段到test_results表")
        
        # 验证字段是否添加成功
        cursor.execute("PRAGMA table_info(test_results)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'rsei_value' in columns:
            print("✅ 字段添加验证成功")
        else:
            print("❌ 字段添加验证失败")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 添加rsei_value字段失败: {e}")
        return False

if __name__ == "__main__":
    print("开始添加rsei_value字段...")
    success = add_rsei_field()
    
    if success:
        print("🎉 数据库迁移完成")
    else:
        print("💥 数据库迁移失败")
        sys.exit(1)
