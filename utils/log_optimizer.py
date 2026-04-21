#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志优化器

负责优化日志输出，减少不必要的日志记录，特别是序列号相关的大量日志

Author: Jack
Date: 2025-06-20
"""

import logging
from typing import Dict, Any, Optional, Set
from PyQt5.QtCore import QObject, pyqtSignal


class LogOptimizer(QObject):
    """日志优化器"""
    
    # 信号定义
    optimization_applied = pyqtSignal(str)  # 优化应用信号
    
    def __init__(self, config_manager=None):
        """
        初始化日志优化器
        
        Args:
            config_manager: 配置管理器实例
        """
        super().__init__()
        
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 序列号相关的日志抑制计数器
        self._serial_log_counters = {
            'load_count': 0,
            'save_count': 0,
            'generate_count': 0,
            'register_count': 0
        }
        
        # 日志抑制阈值
        self._log_suppression_thresholds = {
            'serial_operations': 10,  # 序列号操作日志抑制阈值
            'batch_operations': 5,   # 批量操作日志抑制阈值
        }
        
        # 已抑制的日志类型
        self._suppressed_log_types: Set[str] = set()
        
        self.logger.debug("日志优化器初始化完成")
    
    def should_suppress_serial_log(self, operation_type: str) -> bool:
        """
        检查是否应该抑制序列号相关的日志
        
        Args:
            operation_type: 操作类型 (load/save/generate/register)
            
        Returns:
            是否应该抑制日志
        """
        try:
            # 获取调试模式状态
            debug_mode = self.config_manager.get('logging.debug_mode', True) if self.config_manager else True
            
            # 调试模式下不抑制日志
            if debug_mode:
                return False
            
            # 检查操作计数
            counter_key = f"{operation_type}_count"
            if counter_key in self._serial_log_counters:
                self._serial_log_counters[counter_key] += 1
                
                # 超过阈值时开始抑制
                threshold = self._log_suppression_thresholds.get('serial_operations', 10)
                if self._serial_log_counters[counter_key] > threshold:
                    if operation_type not in self._suppressed_log_types:
                        self._suppressed_log_types.add(operation_type)
                        self.logger.info(f"🔇 序列号{operation_type}操作日志已优化，减少重复输出")
                        self.optimization_applied.emit(f"serial_{operation_type}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查日志抑制状态失败: {e}")
            return False
    
    def should_suppress_batch_log(self, batch_size: int) -> bool:
        """
        检查是否应该抑制批量操作的日志
        
        Args:
            batch_size: 批量操作大小
            
        Returns:
            是否应该抑制日志
        """
        try:
            # 获取调试模式状态
            debug_mode = self.config_manager.get('logging.debug_mode', True) if self.config_manager else True
            
            # 调试模式下不抑制日志
            if debug_mode:
                return False
            
            # 大批量操作时抑制详细日志
            threshold = self._log_suppression_thresholds.get('batch_operations', 5)
            return batch_size > threshold
            
        except Exception as e:
            self.logger.error(f"检查批量日志抑制状态失败: {e}")
            return False
    
    def optimize_serial_number_logging(self) -> Dict[str, Any]:
        """
        优化序列号相关的日志记录
        
        Returns:
            优化结果
        """
        try:
            if not self.config_manager:
                return {'status': 'error', 'message': '配置管理器未设置'}
            
            # 获取当前序列号数量
            serial_count = len(self.config_manager.get('serial_numbers.used_list', []))
            
            # 获取调试模式状态
            debug_mode = self.config_manager.get('logging.debug_mode', True)
            
            optimizations = []
            
            # 根据序列号数量和调试模式决定优化策略
            if serial_count > 1000 and not debug_mode:
                # 大量序列号且非调试模式：启用日志抑制
                optimizations.append("启用序列号操作日志抑制")
                
                # 降低日志级别阈值
                self._log_suppression_thresholds['serial_operations'] = 5
                optimizations.append("降低序列号日志抑制阈值")
                
            elif serial_count > 500 and not debug_mode:
                # 中等数量序列号且非调试模式：适度抑制
                self._log_suppression_thresholds['serial_operations'] = 10
                optimizations.append("设置适度的序列号日志抑制")
                
            elif debug_mode:
                # 调试模式：重置抑制状态
                self._serial_log_counters = {key: 0 for key in self._serial_log_counters}
                self._suppressed_log_types.clear()
                optimizations.append("调试模式：重置日志抑制状态")
            
            # 应用优化
            if optimizations:
                self.optimization_applied.emit("serial_logging")
            
            return {
                'status': 'success',
                'serial_count': serial_count,
                'debug_mode': debug_mode,
                'optimizations': optimizations,
                'suppressed_types': list(self._suppressed_log_types)
            }
            
        except Exception as e:
            self.logger.error(f"优化序列号日志记录失败: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """
        获取优化状态
        
        Returns:
            优化状态信息
        """
        try:
            return {
                'log_counters': self._serial_log_counters.copy(),
                'suppression_thresholds': self._log_suppression_thresholds.copy(),
                'suppressed_types': list(self._suppressed_log_types),
                'debug_mode': self.config_manager.get('logging.debug_mode', True) if self.config_manager else True
            }
        except Exception as e:
            self.logger.error(f"获取优化状态失败: {e}")
            return {}
    
    def reset_optimization(self):
        """重置优化状态"""
        try:
            self._serial_log_counters = {key: 0 for key in self._serial_log_counters}
            self._suppressed_log_types.clear()
            
            # 重置阈值为默认值
            self._log_suppression_thresholds = {
                'serial_operations': 10,
                'batch_operations': 5,
            }
            
            self.logger.info("🔄 日志优化状态已重置")
            self.optimization_applied.emit("reset")
            
        except Exception as e:
            self.logger.error(f"重置优化状态失败: {e}")
    
    def apply_smart_logging_rules(self):
        """应用智能日志规则"""
        try:
            if not self.config_manager:
                return
            
            # 获取系统状态
            serial_count = len(self.config_manager.get('serial_numbers.used_list', []))
            debug_mode = self.config_manager.get('logging.debug_mode', True)
            
            # 智能规则1: 大量序列号时自动优化
            if serial_count > 2000:
                if debug_mode:
                    self.logger.warning(f"⚠️ 检测到大量序列号({serial_count}个)，建议关闭调试模式以优化性能")
                else:
                    # 自动应用激进的日志优化
                    self._log_suppression_thresholds['serial_operations'] = 3
                    self.logger.info(f"🚀 自动应用激进日志优化 (序列号数量: {serial_count})")
            
            # 智能规则2: 根据时间段调整日志级别
            from datetime import datetime
            current_hour = datetime.now().hour
            
            # 夜间时段(22:00-06:00)自动降低日志级别
            if (current_hour >= 22 or current_hour <= 6) and not debug_mode:
                self._log_suppression_thresholds['serial_operations'] = 5
                if 'night_mode' not in self._suppressed_log_types:
                    self._suppressed_log_types.add('night_mode')
                    self.logger.info("🌙 夜间模式：自动优化日志输出")
            
            self.optimization_applied.emit("smart_rules")
            
        except Exception as e:
            self.logger.error(f"应用智能日志规则失败: {e}")


# 全局日志优化器实例
_log_optimizer: Optional[LogOptimizer] = None


def get_log_optimizer() -> Optional[LogOptimizer]:
    """获取全局日志优化器实例"""
    return _log_optimizer


def initialize_log_optimizer(config_manager) -> LogOptimizer:
    """
    初始化全局日志优化器
    
    Args:
        config_manager: 配置管理器实例
        
    Returns:
        日志优化器实例
    """
    global _log_optimizer
    
    if _log_optimizer is None:
        _log_optimizer = LogOptimizer(config_manager)
        
        # 应用初始优化
        _log_optimizer.optimize_serial_number_logging()
        _log_optimizer.apply_smart_logging_rules()
        
        logger = logging.getLogger(__name__)
        logger.debug("✅ 全局日志优化器初始化完成")
    
    return _log_optimizer


def should_suppress_serial_log(operation_type: str) -> bool:
    """
    检查是否应该抑制序列号日志的便捷函数
    
    Args:
        operation_type: 操作类型
        
    Returns:
        是否应该抑制日志
    """
    optimizer = get_log_optimizer()
    if optimizer:
        return optimizer.should_suppress_serial_log(operation_type)
    return False


def should_suppress_batch_log(batch_size: int) -> bool:
    """
    检查是否应该抑制批量日志的便捷函数
    
    Args:
        batch_size: 批量大小
        
    Returns:
        是否应该抑制日志
    """
    optimizer = get_log_optimizer()
    if optimizer:
        return optimizer.should_suppress_batch_log(batch_size)
    return False
