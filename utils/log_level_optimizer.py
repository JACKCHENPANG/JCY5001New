#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志级别优化器

根据运行环境和配置动态调整日志级别，减少不必要的日志输出

Author: Jack
Date: 2025-08-03
"""

import logging
import time
from typing import Dict, List, Optional
from PyQt5.QtCore import QObject, QTimer, pyqtSignal


class LogLevelOptimizer(QObject):
    """日志级别优化器"""
    
    # 信号定义
    level_changed = pyqtSignal(str, str)  # 模块名, 新级别
    
    def __init__(self, config_manager=None):
        """
        初始化日志级别优化器
        
        Args:
            config_manager: 配置管理器实例
        """
        super().__init__()
        
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 优化模块化日志级别控制
        self.module_configs = {
            'voltage_reading': {
                'loggers': [
                    'backend.data_read_manager',
                    'backend.voltage_based_battery_detection_manager'
                ],
                'production_level': 'WARNING',  # 生产环境只记录警告以上
                'debug_level': 'DEBUG',
                'enabled_in_production': False
            },
            'serial_communication': {
                'loggers': [
                    'backend.serial_connection_manager',
                    'backend.device_communication_manager'
                ],
                'production_level': 'WARNING',
                'debug_level': 'DEBUG',
                'enabled_in_production': True
            },
            'ui_updates': {
                'loggers': [
                    'ui.main_window',
                    'ui.components',
                    'ui.battery_code_manager'
                ],
                'production_level': 'WARNING',
                'debug_level': 'DEBUG',
                'enabled_in_production': False
            },
            'network_operations': {
                'loggers': [
                    'backend.heartbeat_manager',
                    'urllib3.connectionpool',
                    'requests'
                ],
                'production_level': 'ERROR',  # 网络问题只记录错误
                'debug_level': 'DEBUG',
                'enabled_in_production': True
            },
            'test_execution': {
                'loggers': [
                    'backend.test_executor',
                    'backend.test_flow_manager',
                    'backend.continuous_test_manager'
                ],
                'production_level': 'WARNING',
                'debug_level': 'DEBUG',
                'enabled_in_production': True
            },
            'data_processing': {
                'loggers': [
                    'backend.data_processor',
                    'backend.eis_analyzer',
                    'algorithms'
                ],
                'production_level': 'WARNING',
                'debug_level': 'DEBUG',
                'enabled_in_production': True
            },
            'initialization': {
                'loggers': [
                    'utils',
                    'data.database_manager'
                ],
                'production_level': 'WARNING',  # 初始化信息在生产环境中减少
                'debug_level': 'DEBUG',
                'enabled_in_production': False
            }
        }
        
        # 当前应用的配置
        self.current_config = {}
        
        # 定时器用于动态调整
        self.adjustment_timer = QTimer()
        self.adjustment_timer.timeout.connect(self._periodic_adjustment)
        
        self.logger.info("✅ 日志级别优化器初始化完成")
    
    def apply_optimized_levels(self):
        """应用优化的日志级别"""
        try:
            # 获取当前运行模式
            debug_mode = self._get_debug_mode()
            
            
            for module_name, config in self.module_configs.items():
                # 确定目标级别
                if debug_mode:
                    target_level = config['debug_level']
                else:
                    # 生产模式
                    if config['enabled_in_production']:
                        target_level = config['production_level']
                    else:
                        target_level = 'ERROR'  # 完全禁用非关键模块
                
                # 应用到所有相关的日志记录器
                for logger_name in config['loggers']:
                    self._set_logger_level(logger_name, target_level)
                
                self.current_config[module_name] = target_level
                self.level_changed.emit(module_name, target_level)
            
            # 特殊处理第三方库日志级别
            self._optimize_third_party_loggers(debug_mode)
            
            self.logger.info("✅ 日志级别优化应用完成")
            
        except Exception as e:
            self.logger.error(f"❌ 应用日志级别优化失败: {e}")
    
    def _get_debug_mode(self) -> bool:
        """获取当前调试模式状态"""
        if self.config_manager:
            return self.config_manager.get('logging.debug_mode', False)
        return False
    
    def _set_logger_level(self, logger_name: str, level: str):
        """设置指定日志记录器的级别"""
        try:
            logger = logging.getLogger(logger_name)
            numeric_level = getattr(logging, level.upper(), logging.INFO)
            logger.setLevel(numeric_level)
            
            # 同时设置所有处理器的级别
            for handler in logger.handlers:
                handler.setLevel(numeric_level)
            
            self.logger.debug(f"🔧 设置日志级别: {logger_name} -> {level}")
            
        except Exception as e:
            self.logger.warning(f"⚠️ 设置日志级别失败 {logger_name}: {e}")
    
    def _optimize_third_party_loggers(self, debug_mode: bool):
        """优化第三方库的日志级别"""
        third_party_configs = {
            'urllib3': 'DEBUG' if debug_mode else 'ERROR',
            'requests': 'DEBUG' if debug_mode else 'WARNING',
            'matplotlib': 'WARNING',  # matplotlib日志通常很冗余
            'PIL': 'WARNING',  # PIL日志通常很冗余
            'PyQt5': 'WARNING' if debug_mode else 'ERROR'
        }
        
        for lib_name, level in third_party_configs.items():
            self._set_logger_level(lib_name, level)
    
    def start_dynamic_adjustment(self, interval_minutes: int = 5):
        """
        启动动态调整
        
        Args:
            interval_minutes: 调整间隔（分钟）
        """
        if interval_minutes > 0:
            self.adjustment_timer.start(interval_minutes * 60 * 1000)  # 转换为毫秒
            self.logger.info(f"🔄 启动动态日志级别调整 (间隔: {interval_minutes}分钟)")
    
    def stop_dynamic_adjustment(self):
        """停止动态调整"""
        self.adjustment_timer.stop()
        self.logger.info("🛑 停止动态日志级别调整")
    
    def _periodic_adjustment(self):
        """定期调整日志级别"""
        try:
            # 检查配置是否有变化
            current_debug_mode = self._get_debug_mode()
            
            # 如果调试模式发生变化，重新应用配置
            needs_update = False
            for module_name, config in self.module_configs.items():
                expected_level = config['debug_level'] if current_debug_mode else config['production_level']
                if self.current_config.get(module_name) != expected_level:
                    needs_update = True
                    break
            
            if needs_update:
                self.logger.info("🔄 检测到配置变化，重新应用日志级别优化")
                self.apply_optimized_levels()
            
        except Exception as e:
            self.logger.error(f"❌ 定期日志级别调整失败: {e}")
    
    def enable_module_logging(self, module_name: str, temporary: bool = False):
        """
        临时启用某个模块的日志
        
        Args:
            module_name: 模块名称
            temporary: 是否为临时启用（5分钟后自动恢复）
        """
        if module_name in self.module_configs:
            config = self.module_configs[module_name]
            
            # 启用调试级别
            for logger_name in config['loggers']:
                self._set_logger_level(logger_name, 'DEBUG')
            
            self.logger.debug(f" 临时启用模块日志: {module_name}")
            
            if temporary:
                # 5分钟后恢复
                QTimer.singleShot(5 * 60 * 1000, lambda: self._restore_module_level(module_name))
    
    def _restore_module_level(self, module_name: str):
        """恢复模块的正常日志级别"""
        if module_name in self.module_configs:
            debug_mode = self._get_debug_mode()
            config = self.module_configs[module_name]
            
            target_level = config['debug_level'] if debug_mode else config['production_level']
            
            for logger_name in config['loggers']:
                self._set_logger_level(logger_name, target_level)
            
            self.logger.info(f"🔄 恢复模块日志级别: {module_name} -> {target_level}")
    
    def get_current_config(self) -> Dict[str, str]:
        """获取当前日志级别配置"""
        return self.current_config.copy()
    
    def get_optimization_stats(self) -> Dict:
        """获取优化统计信息"""
        stats = {
            'total_modules': len(self.module_configs),
            'debug_mode': self._get_debug_mode(),
            'current_config': self.current_config,
            'dynamic_adjustment_active': self.adjustment_timer.isActive()
        }
        
        # 统计各级别的模块数量
        level_counts = {}
        for level in self.current_config.values():
            level_counts[level] = level_counts.get(level, 0) + 1
        
        stats['level_distribution'] = level_counts
        
        return stats


# 全局优化器实例
_log_level_optimizer: Optional[LogLevelOptimizer] = None


def get_log_level_optimizer() -> Optional[LogLevelOptimizer]:
    """获取全局日志级别优化器实例"""
    return _log_level_optimizer


def initialize_log_level_optimizer(config_manager=None) -> LogLevelOptimizer:
    """
    初始化全局日志级别优化器
    
    Args:
        config_manager: 配置管理器实例
        
    Returns:
        日志级别优化器实例
    """
    global _log_level_optimizer
    
    if _log_level_optimizer is None:
        _log_level_optimizer = LogLevelOptimizer(config_manager)
        
        # 立即应用优化配置
        _log_level_optimizer.apply_optimized_levels()
        
        # 启动动态调整（每5分钟检查一次）
        _log_level_optimizer.start_dynamic_adjustment(5)
        
        logger = logging.getLogger(__name__)
        logger.info("✅ 全局日志级别优化器初始化完成")
    
    return _log_level_optimizer


def apply_production_logging():
    """应用生产环境日志配置的便捷函数"""
    optimizer = get_log_level_optimizer()
    if optimizer:
        optimizer.apply_optimized_levels()


def enable_debug_logging_for_module(module_name: str, temporary: bool = True):
    """为指定模块临时启用调试日志的便捷函数"""
    optimizer = get_log_level_optimizer()
    if optimizer:
        optimizer.enable_module_logging(module_name, temporary)