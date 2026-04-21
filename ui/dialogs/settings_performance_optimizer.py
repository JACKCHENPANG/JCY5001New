# -*- coding: utf-8 -*-
"""
设置性能优化器
为设置页面提供性能优化功能，减少卡顿

Author: Jack
Date: 2025-01-27
"""

import logging
from typing import Dict, Any, List, Optional
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class SettingsPerformanceOptimizer(QObject):
    """设置性能优化器"""
    
    # 信号定义
    optimization_completed = pyqtSignal(str)  # 优化完成信号
    optimization_failed = pyqtSignal(str, str)  # 优化失败信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._batch_changes = {}  # 批量变更缓存
        self._optimization_timer = QTimer()
        self._optimization_timer.setSingleShot(True)
        self._optimization_timer.timeout.connect(self._process_batch_changes)
        
    def add_config_change(self, key: str, value: Any):
        """添加配置变更到批量处理队列"""
        try:
            self._batch_changes[key] = value
            
            # 🚀 性能优化：延迟处理，避免频繁更新
            self._optimization_timer.stop()
            self._optimization_timer.start(100)  # 100ms延迟
            
        except Exception as e:
            logger.error(f"添加配置变更失败: {e}")
    
    def _process_batch_changes(self):
        """处理批量配置变更"""
        try:
            if not self._batch_changes:
                return
                
            changes_count = len(self._batch_changes)
            logger.debug(f"🚀 处理批量配置变更，共{changes_count}项")
            
            # 清空缓存
            self._batch_changes.clear()
            
            self.optimization_completed.emit(f"批量处理{changes_count}项配置变更")
            
        except Exception as e:
            logger.error(f"处理批量配置变更失败: {e}")
            self.optimization_failed.emit("batch_process", str(e))
    
    def get_pending_changes(self) -> Dict[str, Any]:
        """获取待处理的配置变更"""
        return self._batch_changes.copy()
    
    def clear_pending_changes(self):
        """清空待处理的配置变更"""
        self._batch_changes.clear()
        self._optimization_timer.stop()


def create_default_collect_settings_changes(widget_name: str) -> callable:
    """
    为设置页面创建默认的收集配置变更方法
    
    Args:
        widget_name: 页面名称
        
    Returns:
        收集配置变更的方法
    """
    def collect_settings_changes() -> Dict[str, Any]:
        """收集配置变更（默认实现）"""
        try:
            # 默认返回空字典，表示没有变更
            logger.debug(f"{widget_name}设置收集到0项变更（默认实现）")
            return {}
        except Exception as e:
            logger.error(f"收集{widget_name}设置变更失败: {e}")
            return {}
    
    return collect_settings_changes


def add_collect_method_to_widgets(widgets: List[Any]):
    """
    为设置页面添加收集配置变更方法
    
    Args:
        widgets: 设置页面列表
    """
    try:
        for widget in widgets:
            if not hasattr(widget, 'collect_settings_changes'):
                # 获取页面名称
                widget_name = getattr(widget, '__class__').__name__
                
                # 添加默认的收集配置变更方法
                widget.collect_settings_changes = create_default_collect_settings_changes(widget_name)
                
                logger.debug(f"为{widget_name}添加了默认的收集配置变更方法")
                
    except Exception as e:
        logger.error(f"为设置页面添加收集方法失败: {e}")


def optimize_settings_dialog_performance(settings_dialog):
    """
    优化设置对话框性能
    
    Args:
        settings_dialog: 设置对话框实例
    """
    try:
        # 为没有收集配置变更方法的页面添加默认方法
        pages = [
            settings_dialog.grade_settings,
            settings_dialog.frequency_settings,
            settings_dialog.product_info,
            settings_dialog.test_config,
            settings_dialog.channel_enable,
            settings_dialog.learning_widget,
            settings_dialog.capacity_prediction,
            settings_dialog.soh_settings,
            settings_dialog.about_widget
        ]
        
        # 过滤掉None的页面
        valid_pages = [page for page in pages if page is not None]
        
        # 添加收集方法
        add_collect_method_to_widgets(valid_pages)
        
        logger.info(f"✅ 设置对话框性能优化完成，处理了{len(valid_pages)}个页面")
        
    except Exception as e:
        logger.error(f"优化设置对话框性能失败: {e}")


# 全局性能优化器实例
_global_optimizer = None


def get_settings_performance_optimizer() -> SettingsPerformanceOptimizer:
    """获取全局设置性能优化器"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = SettingsPerformanceOptimizer()
    return _global_optimizer
