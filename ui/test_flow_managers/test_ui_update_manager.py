# -*- coding: utf-8 -*-
"""
测试UI更新管理器
负责测试过程中的UI状态更新和显示

从TestFlowManager中提取的UI更新功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class TestUIUpdateManager(QObject):
    """
    测试UI更新管理器
    
    职责：
    - 通道状态UI更新
    - 测试进度UI更新
    - 错误状态UI显示
    - 统计信息UI更新
    """
    
    # 信号定义
    ui_update_requested = pyqtSignal(str, dict)  # UI更新请求
    channel_status_updated = pyqtSignal(int, dict)  # 通道状态更新
    
    def __init__(self, main_window, config_manager):
        """
        初始化测试UI更新管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
        """
        super().__init__()
        
        self.main_window = main_window
        self.config_manager = config_manager
        
        logger.debug("测试UI更新管理器初始化完成")
    
    def mark_channel_as_abnormal(self, channel: int, error_desc: str, error_code: str):
        """
        在UI中标记通道为异常状态
        
        Args:
            channel: 通道号
            error_desc: 错误描述
            error_code: 错误代码
        """
        try:
            # 获取通道显示组件
            ui_manager = getattr(self.main_window, 'ui_component_manager', None)
            if ui_manager:
                channels_container = ui_manager.get_component('channels_container')
                if channels_container and hasattr(channels_container, 'get_channel_widget'):
                    channel_widget = channels_container.get_channel_widget(channel)
                    if channel_widget and hasattr(channel_widget, 'set_error_status'):
                        # 设置错误状态
                        channel_widget.set_error_status(error_desc, error_code)
                        logger.info(f"通道{channel}UI已标记为异常: {error_desc}")
                        
                        # 发送状态更新信号
                        self.channel_status_updated.emit(channel, {
                            'status': 'error',
                            'error_desc': error_desc,
                            'error_code': error_code
                        })
                        return
            
            logger.warning(f"无法在UI中标记通道{channel}为异常状态")
            
        except Exception as e:
            logger.error(f"标记通道{channel}异常状态失败: {e}")
    
    def update_channel_progress(self, channel: int, progress_data: Dict[str, Any]):
        """
        更新通道测试进度
        
        Args:
            channel: 通道号
            progress_data: 进度数据
        """
        try:
            ui_manager = getattr(self.main_window, 'ui_component_manager', None)
            if ui_manager:
                channels_container = ui_manager.get_component('channels_container')
                if channels_container and hasattr(channels_container, 'update_channel_progress'):
                    channels_container.update_channel_progress(channel, progress_data)
                    
                    # 发送状态更新信号
                    self.channel_status_updated.emit(channel, {
                        'status': 'progress_update',
                        'progress_data': progress_data
                    })
                    
                    logger.debug(f"通道{channel}进度UI已更新: {progress_data.get('state', 'unknown')}")
                else:
                    logger.warning("通道容器组件未找到或不支持进度更新")
            else:
                logger.warning("UI组件管理器未找到")
                
        except Exception as e:
            logger.error(f"更新通道{channel}进度失败: {e}")
    
    def update_channel_test_result(self, channel: int, test_result: Dict[str, Any]):
        """
        更新通道测试结果
        
        Args:
            channel: 通道号
            test_result: 测试结果
        """
        try:
            ui_manager = getattr(self.main_window, 'ui_component_manager', None)
            if ui_manager:
                channels_container = ui_manager.get_component('channels_container')
                if channels_container and hasattr(channels_container, 'update_channel_test_result'):
                    channels_container.update_channel_test_result(channel, test_result)
                    
                    # 发送状态更新信号
                    self.channel_status_updated.emit(channel, {
                        'status': 'test_completed',
                        'test_result': test_result
                    })
                    
                    logger.info(f"通道{channel}测试结果UI已更新: {'通过' if test_result.get('is_pass') else '失败'}")
                else:
                    logger.warning("通道容器组件未找到或不支持结果更新")
            else:
                logger.warning("UI组件管理器未找到")
                
        except Exception as e:
            logger.error(f"更新通道{channel}测试结果失败: {e}")
    
    def update_statistics_display(self, statistics: Dict[str, Any]):
        """
        更新统计信息显示
        
        Args:
            statistics: 统计数据
        """
        try:
            ui_manager = getattr(self.main_window, 'ui_component_manager', None)
            if ui_manager:
                statistics_widget = ui_manager.get_component('statistics')
                if statistics_widget and hasattr(statistics_widget, 'update_statistics'):
                    statistics_widget.update_statistics(statistics)
                    
                    # 发送UI更新信号
                    self.ui_update_requested.emit('statistics', statistics)
                    
                    logger.debug("统计信息UI已更新")
                else:
                    logger.warning("统计组件未找到或不支持统计更新")
            else:
                logger.warning("UI组件管理器未找到")
                
        except Exception as e:
            logger.error(f"更新统计信息显示失败: {e}")
    
    def update_test_control_status(self, is_testing: bool):
        """
        更新测试控制按钮状态
        
        Args:
            is_testing: 是否正在测试
        """
        try:
            ui_manager = getattr(self.main_window, 'ui_component_manager', None)
            if ui_manager:
                test_control = ui_manager.get_component('test_control')
                if test_control and hasattr(test_control, 'set_testing_state'):
                    test_control.set_testing_state(is_testing)
                    
                    # 发送UI更新信号
                    self.ui_update_requested.emit('test_control', {'is_testing': is_testing})
                    
                    logger.debug(f"测试控制状态UI已更新: {'测试中' if is_testing else '空闲'}")
                else:
                    logger.warning("测试控制组件未找到或不支持状态更新")
            else:
                logger.warning("UI组件管理器未找到")
                
        except Exception as e:
            logger.error(f"更新测试控制状态失败: {e}")
    
    def reset_all_channels_display(self):
        """重置所有通道显示状态"""
        try:
            ui_manager = getattr(self.main_window, 'ui_component_manager', None)
            if ui_manager:
                channels_container = ui_manager.get_component('channels_container')
                if channels_container and hasattr(channels_container, 'reset_all_channels'):
                    channels_container.reset_all_channels()
                    
                    # 发送UI更新信号
                    self.ui_update_requested.emit('channels_reset', {})
                    
                    logger.info("所有通道显示状态已重置")
                else:
                    logger.warning("通道容器组件未找到或不支持重置")
            else:
                logger.warning("UI组件管理器未找到")
                
        except Exception as e:
            logger.error(f"重置通道显示状态失败: {e}")
    
    def update_batch_info_display(self, batch_info: Dict[str, Any]):
        """
        更新批次信息显示
        
        Args:
            batch_info: 批次信息
        """
        try:
            ui_manager = getattr(self.main_window, 'ui_component_manager', None)
            if ui_manager:
                batch_info_widget = ui_manager.get_component('batch_info')
                if batch_info_widget:
                    # 使用正确的方法名refresh_display而不是update_batch_info
                    if hasattr(batch_info_widget, 'refresh_display'):
                        batch_info_widget.refresh_display()
                        logger.debug("批次信息UI已刷新")

                    # 根据批次信息内容进行具体更新
                    if 'batch_number' in batch_info and hasattr(batch_info_widget, 'set_batch_number'):
                        batch_info_widget.set_batch_number(str(batch_info['batch_number']))
                    if 'operator' in batch_info and hasattr(batch_info_widget, 'set_operator'):
                        batch_info_widget.set_operator(str(batch_info['operator']))
                    if 'cell_type' in batch_info and hasattr(batch_info_widget, 'set_cell_type'):
                        batch_info_widget.set_cell_type(str(batch_info['cell_type']))
                    if 'cell_spec' in batch_info and hasattr(batch_info_widget, 'set_cell_spec'):
                        batch_info_widget.set_cell_spec(str(batch_info['cell_spec']))

                    # 发送UI更新信号
                    self.ui_update_requested.emit('batch_info', batch_info)

                    logger.debug("批次信息UI已更新")
                else:
                    logger.warning("批次信息组件未找到")
            else:
                logger.warning("UI组件管理器未找到")
                
        except Exception as e:
            logger.error(f"更新批次信息显示失败: {e}")
    
    def show_test_status_message(self, message: str, status_type: str = "info"):
        """
        显示测试状态消息
        
        Args:
            message: 状态消息
            status_type: 状态类型 (info, warning, error, success)
        """
        try:
            ui_manager = getattr(self.main_window, 'ui_component_manager', None)
            if ui_manager:
                status_bar = ui_manager.get_component('status_bar')
                if status_bar and hasattr(status_bar, 'set_system_status'):
                    status_bar.set_system_status(message, status_type)
                    
                    # 发送UI更新信号
                    self.ui_update_requested.emit('status_message', {
                        'message': message,
                        'type': status_type
                    })
                    
                    logger.debug(f"状态消息已显示: {message} ({status_type})")
                else:
                    logger.warning("状态栏组件未找到或不支持状态更新")
            else:
                logger.warning("UI组件管理器未找到")
                
        except Exception as e:
            logger.error(f"显示状态消息失败: {e}")
    
    def update_outlier_rate_display(self, channel: int, outlier_result: str, baseline_filename: str = "", frequency_deviations: Dict = None, is_final: bool = False):
        """已移除：更新离群率显示（功能已完全移除）"""
        # 离群率功能已完全移除，不执行任何操作
        pass
    
    def get_ui_component(self, component_name: str):
        """获取UI组件"""
        try:
            ui_manager = getattr(self.main_window, 'ui_component_manager', None)
            if ui_manager:
                return ui_manager.get_component(component_name)
            return None
            
        except Exception as e:
            logger.error(f"获取UI组件{component_name}失败: {e}")
            return None
