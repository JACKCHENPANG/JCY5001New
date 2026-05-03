#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动时资源检查和修复脚本
确保打包后的程序能正常显示设置界面

Author: Jack
Date: 2025-01-27
"""

import sys
import os
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_and_fix_resources():
    """检查并修复资源文件"""
    logger.debug(f" 开始检查资源文件...")
    
    try:
        # 确定基础路径
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        elif hasattr(sys, 'frozen'):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        logger.info(f"基础路径: {base_path}")
        
        # 检查关键目录
        required_dirs = [
            "config",
            "resources",
            "resources/icons",
            "resources/styles"
        ]
        
        for dir_name in required_dirs:
            dir_path = os.path.join(base_path, dir_name)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"✅ 创建目录: {dir_path}")
            else:
                logger.debug(f"✅ 目录存在: {dir_path}")
        
        # 检查关键文件
        required_files = {
            "config/app_config.json": create_default_config,
            "resources/styles/main_style.qss": create_default_style
        }
        
        for file_path, creator_func in required_files.items():
            full_path = os.path.join(base_path, file_path)
            if not os.path.exists(full_path):
                try:
                    creator_func(full_path)
                    logger.info(f"✅ 创建文件: {full_path}")
                except Exception as e:
                    logger.error(f"❌ 创建文件失败: {full_path}, {e}")
            else:
                logger.debug(f"✅ 文件存在: {full_path}")
        
        logger.info("✅ 资源文件检查完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 资源文件检查失败: {e}")
        return False


def create_default_config(file_path):
    """创建默认配置文件"""
    default_config = """{
    "ui": {
        "style": {
            "enabled": true,
            "theme": "default"
        },
        "font": {
            "family": "Microsoft YaHei",
            "size": 9
        }
    },
    "test": {
        "impedance_range": {},
        "gain": {}
    },
    "data_upload": {
        "enabled": false,
        "server_url": "https://ukukukukukukukuk.uk",
        "endpoint": "/api/test-results",
        "timeout": 30
    },
    "printer": {
        "name": "",
        "enabled": false
    }
}"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(default_config)


def create_default_style(file_path):
    """创建默认样式文件"""
    default_style = """/* JCY5001AS 默认样式 - 修复打包后显示问题 */

/* 对话框样式 */
QDialog {
    background-color: #f5f5f5;
    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
    font-size: 9pt;
}

/* 选项卡样式 */
QTabWidget::pane {
    border: 1px solid #d0d0d0;
    background-color: white;
    border-radius: 4px;
}

QTabWidget::tab-bar {
    alignment: left;
}

QTabBar::tab {
    background-color: #e0e0e0;
    border: 1px solid #d0d0d0;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 8px 16px;
    margin-right: 2px;
    min-width: 100px;
    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
    font-size: 9pt;
}

QTabBar::tab:selected {
    background-color: white;
    border-bottom: 1px solid white;
}

QTabBar::tab:hover {
    background-color: #f0f0f0;
}

/* 按钮样式 */
QPushButton {
    background-color: #2196F3;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
    font-size: 9pt;
}

QPushButton:hover {
    background-color: #1976D2;
}

QPushButton:pressed {
    background-color: #0D47A1;
}

QPushButton:disabled {
    background-color: #BDBDBD;
    color: #757575;
}

/* 分组框样式 */
QGroupBox {
    font-weight: bold;
    border: 2px solid #cccccc;
    border-radius: 5px;
    margin-top: 1ex;
    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
    font-size: 9pt;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}

/* 标签样式 */
QLabel {
    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
    font-size: 9pt;
}

/* 输入控件样式 */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    border: 1px solid #ddd;
    border-radius: 3px;
    padding: 5px;
    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
    font-size: 9pt;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #2196F3;
}

/* 复选框样式 */
QCheckBox {
    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
    font-size: 9pt;
}

/* 单选按钮样式 */
QRadioButton {
    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
    font-size: 9pt;
}

/* 列表样式 */
QListWidget {
    border: 1px solid #ddd;
    border-radius: 3px;
    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
    font-size: 9pt;
}

/* 表格样式 */
QTableWidget {
    border: 1px solid #ddd;
    border-radius: 3px;
    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
    font-size: 9pt;
}

QTableWidget::item {
    padding: 5px;
}

QTableWidget::item:selected {
    background-color: #2196F3;
    color: white;
}

/* 滚动条样式 */
QScrollBar:vertical {
    border: none;
    background: #f0f0f0;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #c0c0c0;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #a0a0a0;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(default_style)


def setup_working_directory():
    """设置工作目录"""
    try:
        if hasattr(sys, 'frozen'):
            # 打包后的环境，设置工作目录为可执行文件所在目录
            exe_dir = os.path.dirname(sys.executable)
            os.chdir(exe_dir)
            logger.info(f"✅ 工作目录设置为: {exe_dir}")
        else:
            logger.debug("开发环境，保持当前工作目录")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 设置工作目录失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("🚀 启动资源检查和修复...")
    
    success = True
    
    # 1. 设置工作目录
    if not setup_working_directory():
        success = False
    
    # 2. 检查和修复资源文件
    if not check_and_fix_resources():
        success = False
    
    if success:
        logger.info("✅ 启动资源检查和修复完成")
    else:
        logger.error("❌ 启动资源检查和修复失败")
    
    return success


if __name__ == "__main__":
    main()
