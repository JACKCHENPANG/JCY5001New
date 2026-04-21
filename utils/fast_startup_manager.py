#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速启动管理器 - 优化程序启动速度

作者: Jack
版本: V0.91.00
日期: 2025-08-03
"""

import time
import logging
from typing import Dict, List, Callable, Any
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class FastStartupManager(QObject):
    """快速启动管理器"""
    
    startup_completed = pyqtSignal()  # 启动完成信号
    
    def __init__(self, config_manager=None):
        super().__init__()
        self.config_manager = config_manager
        self.startup_time = time.time()
        self.deferred_tasks = []
        self.fast_mode_enabled = True
        
        # 启动阶段计时
        self.stage_times = {}
        self.current_stage = None
        
    def enable_fast_mode(self):
        """启用快速启动模式"""
        self.fast_mode_enabled = True
        logger.info("🚀 快速启动模式已启用")
        
    def disable_fast_mode(self):
        """禁用快速启动模式"""
        self.fast_mode_enabled = False
        logger.info("🔄 快速启动模式已禁用")
        
    def start_stage(self, stage_name: str):
        """开始一个启动阶段"""
        if self.current_stage:
            self.end_stage()
        
        self.current_stage = stage_name
        self.stage_times[stage_name] = {'start': time.time()}
        logger.debug(f"🚀 启动阶段开始: {stage_name}")
        
    def end_stage(self):
        """结束当前启动阶段"""
        if self.current_stage and self.current_stage in self.stage_times:
            end_time = time.time()
            start_time = self.stage_times[self.current_stage]['start']
            duration = end_time - start_time
            self.stage_times[self.current_stage]['duration'] = duration
            logger.debug(f"✅ 启动阶段完成: {self.current_stage} (耗时: {duration:.2f}秒)")
            self.current_stage = None
            
    def defer_task(self, task_func: Callable, delay_ms: int = 1000, *args, **kwargs):
        """延迟执行任务"""
        if self.fast_mode_enabled:
            task_info = {
                'func': task_func,
                'args': args,
                'kwargs': kwargs,
                'delay': delay_ms
            }
            self.deferred_tasks.append(task_info)
            logger.debug(f"📋 任务已延迟: {task_func.__name__} (延迟: {delay_ms}ms)")
        else:
            # 非快速模式下立即执行
            try:
                task_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"立即执行任务失败: {e}")
                
    def execute_deferred_tasks(self):
        """执行所有延迟的任务"""
        if not self.deferred_tasks:
            return
            
        logger.info(f"🔄 开始执行 {len(self.deferred_tasks)} 个延迟任务...")
        
        for i, task_info in enumerate(self.deferred_tasks):
            try:
                # 使用QTimer延迟执行
                QTimer.singleShot(
                    task_info['delay'] + i * 100,  # 错开执行时间
                    lambda t=task_info: self._execute_single_task(t)
                )
            except Exception as e:
                logger.error(f"延迟执行任务失败: {e}")
                
        self.deferred_tasks.clear()
        
    def _execute_single_task(self, task_info: Dict):
        """执行单个延迟任务"""
        try:
            func = task_info['func']
            args = task_info['args']
            kwargs = task_info['kwargs']
            func(*args, **kwargs)
            logger.debug(f"✅ 延迟任务执行完成: {func.__name__}")
        except Exception as e:
            logger.error(f"延迟任务执行失败: {e}")
            
    def optimize_logging_for_startup(self):
        """为启动期间优化日志"""
        if self.fast_mode_enabled:
            # 临时提高日志级别，减少日志输出
            logging.getLogger().setLevel(logging.WARNING)
            logger.info("🔇 启动期间日志级别已提高")
            
    def restore_normal_logging(self):
        """恢复正常日志级别"""
        # 恢复到INFO级别
        logging.getLogger().setLevel(logging.INFO)
        logger.info("🔊 日志级别已恢复正常")
        
    def skip_non_essential_checks(self) -> bool:
        """是否跳过非必要检查"""
        return self.fast_mode_enabled
        
    def get_startup_summary(self) -> Dict[str, Any]:
        """获取启动总结"""
        total_time = time.time() - self.startup_time
        
        summary = {
            'total_time': total_time,
            'fast_mode': self.fast_mode_enabled,
            'stages': self.stage_times.copy(),
            'deferred_tasks_count': len(self.deferred_tasks)
        }
        
        return summary
        
    def print_startup_summary(self):
        """打印启动总结"""
        summary = self.get_startup_summary()
        
        logger.info("=" * 50)
        logger.info("🚀 启动性能总结")
        logger.info("=" * 50)
        logger.info(f"总启动时间: {summary['total_time']:.2f}秒")
        logger.info(f"快速模式: {'启用' if summary['fast_mode'] else '禁用'}")
        logger.info(f"延迟任务数: {summary['deferred_tasks_count']}")
        
        if summary['stages']:
            logger.info("\n各阶段耗时:")
            for stage, times in summary['stages'].items():
                if 'duration' in times:
                    logger.info(f"  {stage}: {times['duration']:.2f}秒")
                    
        logger.info("=" * 50)
        
    def complete_startup(self):
        """完成启动流程"""
        self.end_stage()  # 结束当前阶段
        
        # 执行延迟任务
        self.execute_deferred_tasks()
        
        # 恢复正常日志
        self.restore_normal_logging()
        
        # 打印启动总结
        self.print_startup_summary()
        
        # 发送启动完成信号
        self.startup_completed.emit()
        
        logger.info("✅ 快速启动流程完成")


def create_fast_startup_manager(config_manager=None) -> FastStartupManager:
    """创建快速启动管理器"""
    return FastStartupManager(config_manager)
