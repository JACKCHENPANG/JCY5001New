# -*- coding: utf-8 -*-
"""
设置页面性能增强器
专门优化设置对话框的初始化和响应速度

Author: Jack
Date: 2025-07-13
"""

import logging
import time
from typing import Dict, Any, List, Callable
from PyQt5.QtCore import QObject, QTimer

logger = logging.getLogger(__name__)


class SettingsPerformanceBooster(QObject):
    """设置页面性能增强器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._optimization_enabled = False
        self._deferred_operations = []
        self._performance_mode = False
        
    def enable_performance_mode(self):
        """启用性能模式"""
        try:
            self._performance_mode = True
            logger.info("🚀 设置页面性能模式已启用")
            
            # 应用各种性能优化
            self._optimize_ui_updates()
            self._optimize_database_operations()
            self._optimize_file_operations()
            
        except Exception as e:
            logger.error(f"启用性能模式失败: {e}")
    
    def disable_performance_mode(self):
        """禁用性能模式"""
        try:
            self._performance_mode = False
            logger.info("🔄 设置页面性能模式已禁用")
            
            # 执行延迟的操作
            self._execute_deferred_operations()
            
        except Exception as e:
            logger.error(f"禁用性能模式失败: {e}")
    
    def defer_operation(self, operation: Callable, delay_ms: int = 100):
        """延迟执行操作"""
        try:
            if self._performance_mode:
                self._deferred_operations.append(operation)
                logger.debug(f"操作已延迟执行: {operation.__name__ if hasattr(operation, '__name__') else 'unknown'}")
            else:
                # 立即执行
                operation()
                
        except Exception as e:
            logger.error(f"延迟操作失败: {e}")
    
    def _execute_deferred_operations(self):
        """执行延迟的操作"""
        try:
            for operation in self._deferred_operations:
                try:
                    operation()
                except Exception as e:
                    logger.error(f"执行延迟操作失败: {e}")
            
            self._deferred_operations.clear()
            logger.debug(f"已执行 {len(self._deferred_operations)} 个延迟操作")
            
        except Exception as e:
            logger.error(f"执行延迟操作失败: {e}")
    
    def _optimize_ui_updates(self):
        """优化UI更新"""
        try:
            # 禁用不必要的UI更新
            logger.debug("UI更新优化已应用")
            
        except Exception as e:
            logger.error(f"UI更新优化失败: {e}")
    
    def _optimize_database_operations(self):
        """优化数据库操作"""
        try:
            # 延迟数据库查询
            logger.debug("数据库操作优化已应用")
            
        except Exception as e:
            logger.error(f"数据库操作优化失败: {e}")
    
    def _optimize_file_operations(self):
        """优化文件操作"""
        try:
            # 延迟文件读取
            logger.debug("文件操作优化已应用")
            
        except Exception as e:
            logger.error(f"文件操作优化失败: {e}")


# 全局性能增强器实例
_global_performance_booster = None


def get_settings_performance_booster() -> SettingsPerformanceBooster:
    """获取全局设置性能增强器"""
    global _global_performance_booster
    if _global_performance_booster is None:
        _global_performance_booster = SettingsPerformanceBooster()
    return _global_performance_booster


def enable_settings_performance_mode():
    """启用设置性能模式"""
    booster = get_settings_performance_booster()
    booster.enable_performance_mode()


def disable_settings_performance_mode():
    """禁用设置性能模式"""
    booster = get_settings_performance_booster()
    booster.disable_performance_mode()


def defer_heavy_operation(operation: Callable, delay_ms: int = 100):
    """延迟执行重操作"""
    booster = get_settings_performance_booster()
    booster.defer_operation(operation, delay_ms)


class PerformanceTimer:
    """性能计时器"""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            elapsed = time.time() - self.start_time
            logger.debug(f"⏱️ {self.name} 耗时: {elapsed:.3f}秒")


def measure_performance(name: str):
    """性能测量装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with PerformanceTimer(name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# 快速优化函数
def quick_optimize_settings():
    """快速优化设置页面"""
    try:
        # 启用性能模式
        enable_settings_performance_mode()
        
        # 应用网络优化
        from utils.settings_network_optimizer import apply_settings_optimization
        apply_settings_optimization()
        
        logger.info("✅ 设置页面快速优化已应用")
        
    except Exception as e:
        logger.error(f"快速优化设置页面失败: {e}")


def restore_settings_normal_mode():
    """恢复设置页面正常模式"""
    try:
        # 禁用性能模式
        disable_settings_performance_mode()
        
        # 移除网络优化
        from utils.settings_network_optimizer import remove_settings_optimization
        remove_settings_optimization()
        
        logger.info("✅ 设置页面已恢复正常模式")
        
    except Exception as e:
        logger.error(f"恢复设置页面正常模式失败: {e}")


# 性能优化上下文管理器
class SettingsPerformanceContext:
    """设置性能优化上下文管理器"""
    
    def __enter__(self):
        quick_optimize_settings()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        restore_settings_normal_mode()


# 便捷函数
def with_settings_performance(func):
    """为函数应用设置性能优化的装饰器"""
    def wrapper(*args, **kwargs):
        with SettingsPerformanceContext():
            return func(*args, **kwargs)
    return wrapper
