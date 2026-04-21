# -*- coding: utf-8 -*-
"""
测试错误处理器
负责测试过程中的错误处理、异常恢复和用户提示

从TestFlowManager中提取的错误处理功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Dict, Any, Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


class TestErrorHandler(QObject):
    """
    测试错误处理器
    
    职责：
    - 错误消息显示
    - 异常状态处理
    - 错误恢复策略
    - 用户交互处理
    """
    
    # 信号定义
    error_occurred = pyqtSignal(str, str)  # 错误发生 (标题, 消息)
    error_resolved = pyqtSignal(str)  # 错误解决
    recovery_requested = pyqtSignal(str, dict)  # 恢复请求
    
    def __init__(self, main_window, config_manager):
        """
        初始化测试错误处理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
        """
        super().__init__()
        
        self.main_window = main_window
        self.config_manager = config_manager
        
        # 错误处理配置
        self.error_config = {
            'show_detailed_errors': self.config_manager.get('debug.show_detailed_errors', True),
            'auto_recovery_enabled': self.config_manager.get('error_handling.auto_recovery', True),
            'max_retry_attempts': self.config_manager.get('error_handling.max_retries', 3),
            'error_log_enabled': self.config_manager.get('error_handling.log_errors', True)
        }
        
        # 错误统计
        self.error_statistics = {
            'total_errors': 0,
            'device_errors': 0,
            'communication_errors': 0,
            'test_errors': 0,
            'ui_errors': 0,
            'last_error_time': None
        }
        
        logger.debug("测试错误处理器初始化完成")
    
    def handle_error(self, title: str, message: str, error_type: str = "general", 
                    show_dialog: bool = True, auto_recovery: bool = False) -> bool:
        """
        处理错误
        
        Args:
            title: 错误标题
            message: 错误消息
            error_type: 错误类型
            show_dialog: 是否显示对话框
            auto_recovery: 是否尝试自动恢复
            
        Returns:
            是否处理成功
        """
        try:
            # 记录错误
            self._log_error(title, message, error_type)
            
            # 更新错误统计
            self._update_error_statistics(error_type)
            
            # 发送错误信号
            self.error_occurred.emit(title, message)
            
            # 显示错误对话框
            if show_dialog:
                self._show_error_dialog(title, message, error_type)
            
            # 尝试自动恢复
            if auto_recovery and self.error_config['auto_recovery_enabled']:
                recovery_success = self._attempt_auto_recovery(error_type, message)
                if recovery_success:
                    self.error_resolved.emit(f"{title} - 自动恢复成功")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"处理错误失败: {e}")
            return False
    
    def handle_device_error(self, error_code: str, error_message: str, channel: Optional[int] = None) -> bool:
        """
        处理设备错误
        
        Args:
            error_code: 错误代码
            error_message: 错误消息
            channel: 相关通道号
            
        Returns:
            是否处理成功
        """
        try:
            title = f"设备错误 ({error_code})"
            if channel:
                title += f" - 通道{channel}"
            
            # 根据错误代码确定处理策略
            recovery_strategy = self._get_device_error_recovery_strategy(error_code)
            
            return self.handle_error(
                title=title,
                message=error_message,
                error_type="device",
                show_dialog=True,
                auto_recovery=recovery_strategy.get('auto_recovery', False)
            )
            
        except Exception as e:
            logger.error(f"处理设备错误失败: {e}")
            return False
    
    def handle_communication_error(self, operation: str, error_message: str) -> bool:
        """
        处理通信错误
        
        Args:
            operation: 操作名称
            error_message: 错误消息
            
        Returns:
            是否处理成功
        """
        try:
            title = f"通信错误 - {operation}"
            
            return self.handle_error(
                title=title,
                message=f"通信操作失败: {error_message}\n\n请检查设备连接和串口配置。",
                error_type="communication",
                show_dialog=True,
                auto_recovery=True
            )
            
        except Exception as e:
            logger.error(f"处理通信错误失败: {e}")
            return False
    
    def handle_test_error(self, test_phase: str, error_message: str, channel: Optional[int] = None) -> bool:
        """
        处理测试错误
        
        Args:
            test_phase: 测试阶段
            error_message: 错误消息
            channel: 相关通道号
            
        Returns:
            是否处理成功
        """
        try:
            title = f"测试错误 - {test_phase}"
            if channel:
                title += f" (通道{channel})"
            
            return self.handle_error(
                title=title,
                message=error_message,
                error_type="test",
                show_dialog=True,
                auto_recovery=False
            )
            
        except Exception as e:
            logger.error(f"处理测试错误失败: {e}")
            return False
    
    def _show_error_dialog(self, title: str, message: str, error_type: str):
        """显示错误对话框"""
        try:
            # 根据错误类型选择图标
            icon_map = {
                "device": QMessageBox.Critical,
                "communication": QMessageBox.Warning,
                "test": QMessageBox.Warning,
                "ui": QMessageBox.Information,
                "general": QMessageBox.Critical
            }
            
            icon = icon_map.get(error_type, QMessageBox.Critical)
            
            # 创建消息框
            msg_box = QMessageBox(self.main_window)
            msg_box.setIcon(icon)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            
            # 添加详细信息（如果启用）
            if self.error_config['show_detailed_errors']:
                detailed_info = self._get_error_details(error_type)
                if detailed_info:
                    msg_box.setDetailedText(detailed_info)
            
            # 添加按钮
            msg_box.setStandardButtons(QMessageBox.Ok)
            if error_type in ["device", "communication"]:
                msg_box.addButton("重试", QMessageBox.ActionRole)
                msg_box.addButton("设置", QMessageBox.ActionRole)
            
            # 显示对话框
            msg_box.exec_()
            
        except Exception as e:
            logger.error(f"显示错误对话框失败: {e}")
    
    def _log_error(self, title: str, message: str, error_type: str):
        """记录错误日志"""
        try:
            if self.error_config['error_log_enabled']:
                logger.error(f"[{error_type.upper()}] {title}: {message}")
                
        except Exception as e:
            logger.error(f"记录错误日志失败: {e}")
    
    def _update_error_statistics(self, error_type: str):
        """更新错误统计"""
        try:
            from datetime import datetime
            
            self.error_statistics['total_errors'] += 1
            self.error_statistics['last_error_time'] = datetime.now()
            
            # 按类型统计
            type_key = f"{error_type}_errors"
            if type_key in self.error_statistics:
                self.error_statistics[type_key] += 1
            
        except Exception as e:
            logger.error(f"更新错误统计失败: {e}")
    
    def _attempt_auto_recovery(self, error_type: str, error_message: str) -> bool:
        """尝试自动恢复"""
        try:
            recovery_strategies = {
                "communication": self._recover_communication_error,
                "device": self._recover_device_error,
                "test": self._recover_test_error
            }
            
            recovery_func = recovery_strategies.get(error_type)
            if recovery_func:
                return recovery_func(error_message)
            
            return False
            
        except Exception as e:
            logger.error(f"自动恢复失败: {e}")
            return False
    
    def _recover_communication_error(self, error_message: str) -> bool:
        """恢复通信错误"""
        try:
            # 尝试重新连接设备
            if hasattr(self.main_window, 'device_connection_manager'):
                device_manager = self.main_window.device_connection_manager
                if device_manager.connect_device():
                    logger.info("通信错误自动恢复成功")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"恢复通信错误失败: {e}")
            return False
    
    def _recover_device_error(self, error_message: str) -> bool:
        """恢复设备错误"""
        try:
            # 设备错误通常需要人工干预
            logger.info("设备错误需要人工处理")
            return False
            
        except Exception as e:
            logger.error(f"恢复设备错误失败: {e}")
            return False
    
    def _recover_test_error(self, error_message: str) -> bool:
        """恢复测试错误"""
        try:
            # 测试错误通常需要重新开始测试
            logger.info("测试错误需要重新开始测试")
            return False
            
        except Exception as e:
            logger.error(f"恢复测试错误失败: {e}")
            return False
    
    def _get_device_error_recovery_strategy(self, error_code: str) -> Dict[str, Any]:
        """获取设备错误恢复策略"""
        strategies = {
            "0003": {"auto_recovery": False, "user_action": "检查电池连接"},
            "0001": {"auto_recovery": True, "user_action": "等待设备就绪"},
            "0002": {"auto_recovery": False, "user_action": "检查参数设置"},
            "0004": {"auto_recovery": True, "user_action": "重试测试"},
            "0005": {"auto_recovery": False, "user_action": "联系技术支持"}
        }
        
        return strategies.get(error_code, {"auto_recovery": False, "user_action": "检查设备状态"})
    
    def _get_error_details(self, error_type: str) -> str:
        """获取错误详细信息"""
        details = {
            "device": "设备相关错误，请检查设备连接和状态",
            "communication": "通信相关错误，请检查串口连接和配置",
            "test": "测试相关错误，请检查测试参数和电池状态",
            "ui": "界面相关错误，请重启应用程序",
            "general": "一般性错误，请查看日志获取更多信息"
        }
        
        return details.get(error_type, "未知错误类型")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        获取错误统计信息
        
        Returns:
            错误统计字典
        """
        return self.error_statistics.copy()
    
    def clear_error_statistics(self):
        """清空错误统计"""
        try:
            self.error_statistics = {
                'total_errors': 0,
                'device_errors': 0,
                'communication_errors': 0,
                'test_errors': 0,
                'ui_errors': 0,
                'last_error_time': None
            }
            
            logger.info("错误统计已清空")
            
        except Exception as e:
            logger.error(f"清空错误统计失败: {e}")
