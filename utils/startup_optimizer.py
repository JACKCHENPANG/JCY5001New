# -*- coding: utf-8 -*-
"""
启动性能优化器
负责优化应用程序启动速度和用户体验

Author: Jack
Date: 2025-06-10
"""

import logging
import time
from typing import Dict, Any, Callable, Optional
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class StartupOptimizer(QObject):
    """启动性能优化器"""
    
    # 信号定义
    stage_completed = pyqtSignal(str, float)  # 阶段名称, 耗时
    optimization_completed = pyqtSignal(float)  # 总耗时
    
    def __init__(self):
        super().__init__()
        
        self.start_time = None
        self.stage_times = {}
        self.current_stage = None
        self.deferred_tasks = []
        
        logger.debug("🚀 启动性能优化器初始化完成")
    
    def start_optimization(self):
        """开始启动优化"""
        self.start_time = time.time()
        logger.info("🚀 启动性能优化开始")
    
    def start_stage(self, stage_name: str):
        """开始一个启动阶段"""
        current_time = time.time()
        
        # 结束上一个阶段
        if self.current_stage:
            elapsed = current_time - self.stage_times[self.current_stage]
            logger.info(f"✅ 阶段完成: {self.current_stage} ({elapsed:.3f}s)")
            self.stage_completed.emit(self.current_stage, elapsed)
        
        # 开始新阶段
        self.current_stage = stage_name
        self.stage_times[stage_name] = current_time
        logger.info(f"🔄 开始阶段: {stage_name}")
    
    def defer_task(self, task_name: str, task_func: Callable, delay_ms: int = 1000):
        """延迟执行任务"""
        self.deferred_tasks.append({
            'name': task_name,
            'func': task_func,
            'delay': delay_ms
        })
        logger.info(f"⏰ 任务已延迟: {task_name} (延迟{delay_ms}ms)")
    
    def execute_deferred_tasks(self):
        """执行延迟任务"""
        for task in self.deferred_tasks:
            QTimer.singleShot(task['delay'], lambda t=task: self._execute_task(t))
        
        logger.info(f"🔄 已安排{len(self.deferred_tasks)}个延迟任务")
    
    def _execute_task(self, task: Dict[str, Any]):
        """执行单个延迟任务"""
        try:
            logger.info(f"🔄 执行延迟任务: {task['name']}")
            task['func']()
            logger.info(f"✅ 延迟任务完成: {task['name']}")
        except Exception as e:
            logger.error(f"❌ 延迟任务失败: {task['name']} - {e}")
    
    def finish_optimization(self):
        """完成启动优化"""
        if self.start_time:
            total_time = time.time() - self.start_time
            
            # 结束最后一个阶段
            if self.current_stage:
                elapsed = time.time() - self.stage_times[self.current_stage]
                logger.info(f"✅ 阶段完成: {self.current_stage} ({elapsed:.3f}s)")
                self.stage_completed.emit(self.current_stage, elapsed)
            
            logger.info(f"🎯 启动优化完成，总耗时: {total_time:.3f}s")
            self.optimization_completed.emit(total_time)
            
            # 执行延迟任务
            self.execute_deferred_tasks()
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        if not self.start_time:
            return {'error': '优化未开始'}
        
        total_time = time.time() - self.start_time
        
        # 计算各阶段耗时
        stage_durations = {}
        stage_names = list(self.stage_times.keys())
        
        for i, stage in enumerate(stage_names):
            if i < len(stage_names) - 1:
                next_stage_time = self.stage_times[stage_names[i + 1]]
                duration = next_stage_time - self.stage_times[stage]
            else:
                duration = time.time() - self.stage_times[stage]
            
            stage_durations[stage] = duration
        
        return {
            'total_time': total_time,
            'stage_durations': stage_durations,
            'deferred_tasks_count': len(self.deferred_tasks),
            'optimization_ratio': self._calculate_optimization_ratio()
        }
    
    def _calculate_optimization_ratio(self) -> float:
        """计算优化比例"""
        # 这里可以基于历史数据计算优化效果
        # 暂时返回估算值
        return 0.3  # 假设优化了30%的启动时间


class FastStartupManager:
    """快速启动管理器"""

    def __init__(self, config_manager, startup_optimizer=None):
        self.config_manager = config_manager
        self.optimizer = startup_optimizer or get_startup_optimizer()

        # 启动配置
        self.fast_startup_enabled = config_manager.get('startup.fast_mode', True)
        self.defer_non_critical = config_manager.get('startup.defer_non_critical', True)
        self.show_splash = config_manager.get('startup.show_splash', True)

        logger.debug("⚡ 快速启动管理器初始化完成")
    
    def should_defer_component(self, component_name: str) -> bool:
        """判断组件是否应该延迟初始化"""
        if not self.defer_non_critical:
            return False
        
        # 定义非关键组件列表
        non_critical_components = [
            'storage_monitor',
            'data_cleanup_manager',
            'performance_monitor',
            'statistics_counter',
            'outlier_detection',
            'learning_analyzer'
        ]
        
        return component_name in non_critical_components
    
    def get_component_priority(self, component_name: str) -> int:
        """获取组件初始化优先级（数字越小优先级越高）"""
        priority_map = {
            # 核心组件 - 最高优先级
            'config_manager': 1,
            'log_config_manager': 2,
            'database_manager': 3,
            'license_manager': 4,
            
            # UI组件 - 高优先级
            'main_window': 5,
            'window_layout_manager': 6,
            'ui_component_manager': 7,
            'menu_manager': 8,
            
            # 设备组件 - 中等优先级
            'communication_manager': 9,
            'device_connection_manager': 10,
            'battery_detection_manager': 11,
            
            # 功能组件 - 低优先级
            'printer_manager': 12,
            'label_print_manager': 13,
            'test_flow_manager': 14,
            
            # 非关键组件 - 最低优先级（可延迟）
            'storage_monitor': 15,
            'data_cleanup_manager': 16,
            'performance_monitor': 17,
            'statistics_counter': 18,
            'outlier_detection': 19,
            'learning_analyzer': 20
        }
        
        return priority_map.get(component_name, 99)
    
    def optimize_logging_for_startup(self):
        """为启动优化日志配置"""
        if self.fast_startup_enabled:
            # 临时降低日志级别，减少启动时的日志输出
            logging.getLogger().setLevel(logging.WARNING)
            logger.debug("启动期间日志级别已临时降低")
    
    def restore_normal_logging(self):
        """恢复正常日志配置"""
        # 恢复正常日志级别
        debug_mode = self.config_manager.get('logging.debug_mode', True)
        if debug_mode:
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)
        
        logger.debug("日志级别已恢复正常")


# 全局启动优化器实例
_startup_optimizer: Optional[StartupOptimizer] = None
_fast_startup_manager: Optional[FastStartupManager] = None


def get_startup_optimizer() -> Optional[StartupOptimizer]:
    """获取全局启动优化器实例"""
    global _startup_optimizer
    if _startup_optimizer is None:
        _startup_optimizer = StartupOptimizer()
    return _startup_optimizer


def get_fast_startup_manager() -> Optional[FastStartupManager]:
    """获取全局快速启动管理器实例"""
    return _fast_startup_manager


def initialize_startup_optimization(config_manager) -> tuple:
    """
    初始化启动优化

    Returns:
        (StartupOptimizer, FastStartupManager)
    """
    global _startup_optimizer, _fast_startup_manager

    if _startup_optimizer is None:
        _startup_optimizer = StartupOptimizer()
        # 日志已在StartupOptimizer.__init__中输出，避免重复

    if _fast_startup_manager is None:
        _fast_startup_manager = FastStartupManager(config_manager, _startup_optimizer)

    return _startup_optimizer, _fast_startup_manager
