# -*- coding: utf-8 -*-
"""
重构验证测试
验证重构后的主窗口管理器是否正常工作

Author: Jack
Date: 2025-01-30
"""

import logging
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger(__name__)


def test_manager_imports():
    """测试管理器导入"""
    try:
        from ui.main_window_managers import (
            WindowLayoutManager,
            ComponentInitializer,
            SettingsLoader,
            EventCoordinator,
            AuthorizationManager
        )
        
        print("✅ 所有管理器导入成功")
        return True
        
    except ImportError as e:
        print(f"❌ 管理器导入失败: {e}")
        return False


def test_manager_initialization():
    """测试管理器初始化"""
    try:
        # 模拟配置管理器
        class MockConfigManager:
            def get(self, key, default=None):
                return default
        
        # 模拟主窗口
        class MockMainWindow:
            def __init__(self):
                self.config_manager = MockConfigManager()
        
        main_window = MockMainWindow()
        config_manager = MockConfigManager()
        
        # 测试各个管理器的初始化
        from ui.main_window_managers import (
            WindowLayoutManager,
            ComponentInitializer,
            SettingsLoader,
            EventCoordinator,
            AuthorizationManager
        )
        
        window_layout_manager = WindowLayoutManager(main_window, config_manager)
        component_initializer = ComponentInitializer(main_window, config_manager)
        settings_loader = SettingsLoader(main_window, config_manager)
        event_coordinator = EventCoordinator(main_window, config_manager)
        authorization_manager = AuthorizationManager(main_window, config_manager)
        
        print("✅ 所有管理器初始化成功")
        return True
        
    except Exception as e:
        print(f"❌ 管理器初始化失败: {e}")
        return False


def test_manager_methods():
    """测试管理器方法"""
    try:
        # 模拟配置管理器
        class MockConfigManager:
            def get(self, key, default=None):
                return default
        
        # 模拟主窗口
        class MockMainWindow:
            def __init__(self):
                self.config_manager = MockConfigManager()
        
        main_window = MockMainWindow()
        config_manager = MockConfigManager()
        
        from ui.main_window_managers import EventCoordinator
        
        event_coordinator = EventCoordinator(main_window, config_manager)
        
        # 测试事件处理方法
        event_coordinator.handle_device_connection_changed(True)
        event_coordinator.handle_test_started()
        event_coordinator.handle_test_stopped()
        
        print("✅ 管理器方法测试成功")
        return True
        
    except Exception as e:
        print(f"❌ 管理器方法测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🔧 开始重构验证测试...")
    
    tests = [
        ("管理器导入测试", test_manager_imports),
        ("管理器初始化测试", test_manager_initialization),
        ("管理器方法测试", test_manager_methods)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} 失败")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 重构验证成功！所有管理器工作正常")
        return True
    else:
        print("⚠️ 重构验证失败，需要修复问题")
        return False


if __name__ == "__main__":
    main()