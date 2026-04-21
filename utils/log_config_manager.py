#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置管理器
负责根据调试模式动态调整日志级别

功能：
1. 根据debug_mode配置动态调整日志级别
2. 当debug_mode=false时，设置日志级别为INFO或更高
3. 当debug_mode=true时，保持DEBUG级别输出
4. 提供日志级别切换的接口

作者：Jack
日期：2025-01-31
"""

import logging
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal


class LogConfigManager(QObject):
    """日志配置管理器"""
    
    # 信号定义
    log_level_changed = pyqtSignal(str)  # 日志级别变更信号
    
    def __init__(self, config_manager=None):
        """
        初始化日志配置管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        super().__init__()
        
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 日志级别映射
        self.level_mapping = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        # 连接配置变更信号
        if self.config_manager:
            self.config_manager.config_changed.connect(self._on_config_changed)
        
        self.logger.debug("日志配置管理器初始化完成")
    
    def apply_debug_mode_settings(self):
        """应用调试模式设置"""
        try:
            if not self.config_manager:
                self.logger.warning("配置管理器未设置，无法应用调试模式设置")
                return

            # 获取调试模式设置
            debug_mode = self.config_manager.get('logging.debug_mode', True)
            log_level = self.config_manager.get('logging.level', 'DEBUG')

            # 根据调试模式确定实际日志级别
            if debug_mode:
                # 调试模式开启：使用配置的日志级别
                actual_level = log_level
                # 启用日志输出
                self._enable_logging(True)
                self._set_log_level(actual_level)
            else:
                # 调试模式关闭：完全禁用日志输出
                actual_level = 'DISABLED'
                # 禁用日志输出
                self._enable_logging(False)

            # 发送信号
            self.log_level_changed.emit(actual_level if debug_mode else 'DISABLED')

        except Exception as e:
            self.logger.error(f"应用调试模式设置失败: {e}")
    
    def _set_log_level(self, level: str):
        """设置日志级别"""
        try:
            if level not in self.level_mapping:
                self.logger.error(f"无效的日志级别: {level}")
                return

            log_level = self.level_mapping[level]

            # 设置根日志记录器级别
            root_logger = logging.getLogger()
            root_logger.setLevel(log_level)

            # 设置所有处理器的级别
            for handler in root_logger.handlers:
                handler.setLevel(log_level)

            self.logger.info(f"✅ 日志级别已设置为: {level}")

        except Exception as e:
            self.logger.error(f"设置日志级别失败: {e}")

    def _enable_logging(self, enabled: bool):
        """启用或禁用日志输出"""
        try:
            root_logger = logging.getLogger()

            if enabled:
                # 启用日志：恢复正常的日志级别
                # 这里不需要做特殊处理，_set_log_level会处理
                pass
            else:
                # 禁用日志：设置为最高级别，完全禁用输出
                disable_level = logging.CRITICAL + 10  # 比CRITICAL高很多，确保不会输出
                root_logger.setLevel(disable_level)

                # 设置所有处理器为禁用级别
                for handler in root_logger.handlers:
                    handler.setLevel(disable_level)

                # 优化对于文件处理器，完全禁用
                for handler in root_logger.handlers:
                    if hasattr(handler, 'stream') and hasattr(handler.stream, 'name'):
                        # 这是文件处理器，设置为禁用级别
                        handler.setLevel(disable_level)

        except Exception as e:
            # 这里不能用self.logger，因为可能正在禁用日志
            print(f"设置日志启用状态失败: {e}")
    
    def set_debug_mode(self, enabled: bool):
        """
        设置调试模式
        
        Args:
            enabled: 是否启用调试模式
        """
        try:
            if not self.config_manager:
                self.logger.warning("配置管理器未设置，无法设置调试模式")
                return
            
            # 更新配置
            self.config_manager.set('logging.debug_mode', enabled)
            
            # 应用设置
            self.apply_debug_mode_settings()
            
            
        except Exception as e:
            self.logger.error(f"设置调试模式失败: {e}")
    
    def set_log_level(self, level: str):
        """
        设置日志级别
        
        Args:
            level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        """
        try:
            if not self.config_manager:
                self.logger.warning("配置管理器未设置，无法设置日志级别")
                return
            
            if level not in self.level_mapping:
                self.logger.error(f"无效的日志级别: {level}")
                return
            
            # 更新配置
            self.config_manager.set('logging.level', level)
            
            # 应用设置
            self.apply_debug_mode_settings()
            
        except Exception as e:
            self.logger.error(f"设置日志级别失败: {e}")
    
    def get_debug_mode(self) -> bool:
        """
        获取调试模式状态
        
        Returns:
            调试模式是否启用
        """
        if not self.config_manager:
            return True  # 默认启用调试模式
        
        return self.config_manager.get('logging.debug_mode', True)
    
    def get_log_level(self) -> str:
        """
        获取当前日志级别
        
        Returns:
            当前日志级别
        """
        if not self.config_manager:
            return 'DEBUG'  # 默认DEBUG级别
        
        return self.config_manager.get('logging.level', 'DEBUG')
    
    def get_effective_log_level(self) -> str:
        """
        获取有效的日志级别（考虑调试模式）

        Returns:
            有效的日志级别
        """
        debug_mode = self.get_debug_mode()
        log_level = self.get_log_level()

        if debug_mode:
            return log_level
        else:
            # 调试模式关闭时，完全禁用日志输出
            return 'DISABLED'
    
    def _on_config_changed(self, key: str, value: Any):
        """配置变更处理"""
        try:
            # 监听日志相关配置变更
            if key.startswith('logging.'):
                self.logger.debug(f"检测到日志配置变更: {key} = {value}")
                
                # 重新应用调试模式设置
                self.apply_debug_mode_settings()
                
        except Exception as e:
            self.logger.error(f"处理配置变更失败: {e}")
    
    def get_log_config_info(self) -> Dict[str, Any]:
        """
        获取日志配置信息
        
        Returns:
            日志配置信息字典
        """
        try:
            return {
                'debug_mode': self.get_debug_mode(),
                'configured_level': self.get_log_level(),
                'effective_level': self.get_effective_log_level(),
                'system_log_enabled': self.config_manager.get('logging.enable_system_log', True) if self.config_manager else True,
                'communication_log_enabled': self.config_manager.get('communication.enable_logging', False) if self.config_manager else False
            }
        except Exception as e:
            self.logger.error(f"获取日志配置信息失败: {e}")
            return {}
    
    def reset_to_default(self):
        """重置为默认日志配置"""
        try:
            if not self.config_manager:
                self.logger.warning("配置管理器未设置，无法重置日志配置")
                return
            
            # 重置为默认值
            self.config_manager.set('logging.debug_mode', True)
            self.config_manager.set('logging.level', 'DEBUG')
            self.config_manager.set('logging.enable_system_log', True)
            
            # 应用设置
            self.apply_debug_mode_settings()
            
            self.logger.info("✅ 日志配置已重置为默认值")
            
        except Exception as e:
            self.logger.error(f"重置日志配置失败: {e}")


# 全局日志配置管理器实例
_log_config_manager: Optional[LogConfigManager] = None


def get_log_config_manager() -> Optional[LogConfigManager]:
    """获取全局日志配置管理器实例"""
    return _log_config_manager


def initialize_log_config_manager(config_manager) -> LogConfigManager:
    """
    初始化全局日志配置管理器
    
    Args:
        config_manager: 配置管理器实例
        
    Returns:
        日志配置管理器实例
    """
    global _log_config_manager
    
    if _log_config_manager is None:
        _log_config_manager = LogConfigManager(config_manager)

        # 应用初始设置
        _log_config_manager.apply_debug_mode_settings()

        # 新增集成日志级别优化器
        try:
            from utils.log_level_optimizer import initialize_log_level_optimizer
            log_level_optimizer = initialize_log_level_optimizer(config_manager)
            logger = logging.getLogger(__name__)
            logger.debug("✅ 日志级别优化器已集成")
        except ImportError:
            logger = logging.getLogger(__name__)
            logger.debug("⚠️ 日志级别优化器不可用")

        logger = logging.getLogger(__name__)
        logger.debug("✅ 全局日志配置管理器初始化完成")
    
    return _log_config_manager


def apply_debug_mode_from_config(config_manager):
    """
    从配置应用调试模式（便捷函数）
    
    Args:
        config_manager: 配置管理器实例
    """
    log_manager = initialize_log_config_manager(config_manager)
    log_manager.apply_debug_mode_settings()
