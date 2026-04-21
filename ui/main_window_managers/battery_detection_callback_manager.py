# -*- coding: utf-8 -*-
"""
电池检测回调管理器
负责处理电池检测相关的回调事件，包括电池插入、移除、状态更新等

Author: Jack
Date: 2025-06-27
"""

import logging
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal, QMetaObject, Qt, QThread

logger = logging.getLogger(__name__)


class BatteryDetectionCallbackManager(QObject):
    """电池检测回调管理器"""
    
    # 信号定义
    battery_detected = pyqtSignal(int, float)  # 电池检测信号 (channel, voltage)
    battery_removed = pyqtSignal(int, float)  # 电池移除信号 (channel, voltage)
    battery_status_updated = pyqtSignal(int, str, float)  # 电池状态更新信号 (channel, status, voltage)
    auto_test_requested = pyqtSignal()  # 自动测试请求信号
    
    def __init__(self, main_window, config_manager, parent=None):
        """
        初始化电池检测回调管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
            parent: 父对象
        """
        super().__init__(parent)
        
        self.main_window = main_window
        self.config_manager = config_manager
        
        # 电池检测状态
        self.battery_detection_active = False
        self.initialization_complete = False
        
    def set_initialization_complete(self, complete: bool):
        """设置初始化完成状态"""
        self.initialization_complete = complete
        logger.debug(f"电池检测回调管理器初始化状态: {complete}")

    def set_battery_detection_active(self, active: bool):
        """设置电池检测激活状态"""
        self.battery_detection_active = active
        logger.debug(f"电池检测激活状态: {active}")

    def setup_battery_detection_callbacks(self):
        """设置电池检测回调函数"""
        try:
            # 获取电池检测管理器
            battery_detection_manager = getattr(self.main_window, 'battery_detection_manager', None)
            if not battery_detection_manager:
                logger.warning("电池检测管理器未找到，无法设置回调")
                return
            
            # 设置回调函数
            battery_detection_manager.set_new_battery_callback(self.on_new_battery_detected)
            battery_detection_manager.set_battery_removed_callback(self.on_battery_removed)
            battery_detection_manager.set_battery_status_callback(self.on_battery_status_updated)
            
            logger.info("电池检测回调函数设置完成")
            
        except Exception as e:
            logger.error(f"设置电池检测回调函数失败: {e}")

    def on_battery_removed(self, channel_num: int, voltage: float):
        """电池移除回调处理（线程安全版本）"""
        try:
            if not self.initialization_complete:
                logger.debug(f"初始化未完成，忽略通道{channel_num}电池移除事件")
                return
                
            logger.info(f"🔋 通道{channel_num}电池移除，电压: {voltage:.3f}V")
            
            # 使用Qt的线程安全机制调用主线程方法
            if self._is_main_thread():
                self._on_battery_removed_main_thread(channel_num, voltage)
            else:
                QMetaObject.invokeMethod(
                    self, "_on_battery_removed_main_thread",
                    Qt.ConnectionType.QueuedConnection,
                    channel_num, voltage
                )
                
        except Exception as e:
            logger.error(f"处理通道{channel_num}电池移除回调失败: {e}")

    def _on_battery_removed_main_thread(self, channel_num: int, voltage: float):
        """在主线程中处理电池移除事件"""
        try:
            # 发送电池移除信号
            self.battery_removed.emit(channel_num, voltage)
            
            # 更新通道状态
            self._update_channel_battery_status(channel_num, "disconnected", voltage)
            
            logger.debug(f"通道{channel_num}电池移除事件处理完成")
            
        except Exception as e:
            logger.error(f"在主线程处理通道{channel_num}电池移除事件失败: {e}")

    def on_new_battery_detected(self, channel_num: int, voltage: float):
        """新电池检测回调处理（线程安全版本）"""
        try:
            if not self.initialization_complete:
                logger.debug(f"初始化未完成，忽略通道{channel_num}新电池检测事件")
                return
                
            logger.info(f"🔋 通道{channel_num}检测到新电池，电压: {voltage:.3f}V")
            
            # 使用Qt的线程安全机制调用主线程方法
            if self._is_main_thread():
                self._on_new_battery_detected_main_thread(channel_num, voltage)
            else:
                QMetaObject.invokeMethod(
                    self, "_on_new_battery_detected_main_thread",
                    Qt.ConnectionType.QueuedConnection,
                    channel_num, voltage
                )
                
        except Exception as e:
            logger.error(f"处理通道{channel_num}新电池检测回调失败: {e}")

    def _on_new_battery_detected_main_thread(self, channel_num: int, voltage: float):
        """在主线程中处理新电池检测事件"""
        try:
            # 发送电池检测信号
            self.battery_detected.emit(channel_num, voltage)
            
            # 更新通道状态
            self._update_channel_battery_status(channel_num, "connected", voltage)
            
            # 检查是否需要启动自动测试
            if self._should_start_auto_test():
                self.auto_test_requested.emit()
                
            logger.debug(f"通道{channel_num}新电池检测事件处理完成")
            
        except Exception as e:
            logger.error(f"在主线程处理通道{channel_num}新电池检测事件失败: {e}")

    def on_battery_status_updated(self, channel_num: int, status: str, voltage: float):
        """电池状态更新回调处理（线程安全版本）"""
        try:
            if not self.initialization_complete:
                logger.debug(f"初始化未完成，忽略通道{channel_num}电池状态更新事件")
                return
                
            logger.debug(f"🔋 通道{channel_num}电池状态更新: {status}, 电压: {voltage:.3f}V")
            
            # 使用Qt的线程安全机制调用主线程方法
            if self._is_main_thread():
                self._on_battery_status_updated_main_thread(channel_num, status, voltage)
            else:
                QMetaObject.invokeMethod(
                    self, "_on_battery_status_updated_main_thread",
                    Qt.ConnectionType.QueuedConnection,
                    channel_num, status, voltage
                )
                
        except Exception as e:
            logger.error(f"处理通道{channel_num}电池状态更新回调失败: {e}")

    def _on_battery_status_updated_main_thread(self, channel_num: int, status: str, voltage: float):
        """在主线程中处理电池状态更新"""
        try:
            # 发送电池状态更新信号
            self.battery_status_updated.emit(channel_num, status, voltage)
            
            # 更新通道状态
            self._update_channel_battery_status(channel_num, status, voltage)
            
            logger.debug(f"通道{channel_num}电池状态更新事件处理完成")
            
        except Exception as e:
            logger.error(f"在主线程处理通道{channel_num}电池状态更新事件失败: {e}")

    def _update_channel_battery_status(self, channel_num: int, status: str, voltage: float):
        """更新通道电池状态"""
        try:
            # 更新通道显示组件
            if hasattr(self.main_window, 'channel_display_widget'):
                channel_widget = getattr(self.main_window.channel_display_widget, f'channel_{channel_num}', None)
                if channel_widget and hasattr(channel_widget, 'update_battery_status'):
                    channel_widget.update_battery_status(status, voltage)
                else:
                    # 备用方法
                    self._fallback_update_channel_status(channel_num, status, voltage)
            else:
                logger.warning(f"通道显示组件未找到，无法更新通道{channel_num}状态")
                
        except Exception as e:
            logger.error(f"更新通道{channel_num}电池状态失败: {e}")

    def _fallback_update_channel_status(self, channel_num: int, status: str, voltage: float):
        """备用的通道状态更新方法"""
        try:
            logger.debug(f"使用备用方法更新通道{channel_num}状态: {status}, {voltage:.3f}V")
            # 这里可以添加备用的状态更新逻辑
        except Exception as e:
            logger.error(f"备用通道状态更新失败: {e}")

    def _should_start_auto_test(self) -> bool:
        """检查是否应该启动自动测试"""
        try:
            # 检查是否启用自动测试
            auto_test_enabled = self.config_manager.get('test.auto_start_on_battery_detected', False)
            if not auto_test_enabled:
                return False
            
            # 检查是否在连续测试模式
            continuous_mode = self.config_manager.get('test.continuous_mode', False)
            if not continuous_mode:
                return False
            
            # 检查电池检测是否已激活
            if not self.battery_detection_active:
                return False
            
            # 检查是否有测试正在进行
            if hasattr(self.main_window, 'is_testing') and self.main_window.is_testing:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查自动测试条件失败: {e}")
            return False

    def start_auto_test_for_new_battery(self):
        """为新电池启动自动测试"""
        try:
            if not self._validate_auto_test_conditions():
                return
                
            logger.info("🚀 为新电池启动自动测试")
            
            # 启动测试
            if hasattr(self.main_window, 'test_flow_manager'):
                self.main_window.test_flow_manager.start_test()
            else:
                logger.warning("测试流程管理器未找到，无法启动自动测试")
                
        except Exception as e:
            logger.error(f"为新电池启动自动测试失败: {e}")

    def _validate_auto_test_conditions(self) -> bool:
        """验证自动测试启动条件"""
        try:
            # 检查设备连接状态
            if hasattr(self.main_window, 'communication_manager'):
                if not self.main_window.communication_manager.is_connected:
                    logger.debug("设备未连接，无法启动自动测试")
                    return False
            
            # 检查是否有可用的通道
            enabled_channels = self.config_manager.get('channel_enable.enabled_channels', [])
            if not enabled_channels:
                logger.debug("没有启用的通道，无法启动自动测试")
                return False
            
            # 检查是否有电池连接
            battery_connected = False
            if hasattr(self.main_window, 'battery_detection_manager'):
                for channel_num in enabled_channels:
                    if self.main_window.battery_detection_manager.is_battery_connected(channel_num):
                        battery_connected = True
                        break
            
            if not battery_connected:
                logger.debug("没有电池连接，无法启动自动测试")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证自动测试条件失败: {e}")
            return False

    def _is_main_thread(self) -> bool:
        """检查当前是否在主线程中"""
        try:
            return QThread.currentThread() == self.main_window.thread()
        except Exception as e:
            logger.error(f"检查主线程失败: {e}")
            return False

    def get_battery_status_summary(self) -> dict:
        """获取电池状态摘要"""
        try:
            summary = {
                'detection_active': self.battery_detection_active,
                'initialization_complete': self.initialization_complete,
                'connected_channels': [],
                'disconnected_channels': []
            }
            
            # 检查各通道电池状态
            if hasattr(self.main_window, 'battery_detection_manager'):
                for channel_num in range(1, 9):
                    if self.main_window.battery_detection_manager.is_battery_connected(channel_num):
                        summary['connected_channels'].append(channel_num)
                    else:
                        summary['disconnected_channels'].append(channel_num)
            
            return summary
            
        except Exception as e:
            logger.error(f"获取电池状态摘要失败: {e}")
            return {}

    def cleanup(self):
        """清理资源"""
        try:
            # 清理回调设置
            if hasattr(self.main_window, 'battery_detection_manager'):
                battery_detection_manager = self.main_window.battery_detection_manager
                if hasattr(battery_detection_manager, 'clear_callbacks'):
                    battery_detection_manager.clear_callbacks()
                    
            logger.debug("电池检测回调管理器资源已清理")
            
        except Exception as e:
            logger.error(f"清理电池检测回调管理器资源失败: {e}")
