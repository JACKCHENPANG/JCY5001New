# -*- coding: utf-8 -*-
"""
主界面设置同步管理器
负责处理设置修改后的主界面实时更新

当设置中的参数修改后，包括：
1. 设备连接的COM口
2. 打印机修改的设置  
3. 顶针寿命归零后的数据
需要及时更新主界面显示，避免用户疑惑

Author: Jack
Date: 2025-06-21
"""

import logging
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


class MainWindowSettingsSync(QObject):
    """主界面设置同步管理器"""
    
    # 信号定义
    sync_completed = pyqtSignal(str)  # 同步完成信号
    sync_failed = pyqtSignal(str, str)  # 同步失败信号 (类型, 错误信息)
    
    def __init__(self, main_window, config_manager, parent=None):
        """
        初始化设置同步管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
            parent: 父对象
        """
        super().__init__(parent)
        
        self.main_window = main_window
        self.config_manager = config_manager
        
        # 新增初始化顶针寿命管理器引用
        self.probe_pin_manager = None
        self._init_probe_pin_manager()
        
        # 连接配置变更信号
        self._connect_config_signals()
        
        logger.debug("主界面设置同步管理器初始化完成")
    
    def _init_probe_pin_manager(self):
        """初始化顶针寿命管理器"""
        try:
            # 导入顶针寿命管理器
            from utils.probe_pin_manager import ProbePinManager
            
            # 创建顶针寿命管理器实例
            self.probe_pin_manager = ProbePinManager(
                config_manager=self.config_manager,
                parent=self
            )
            
            # 连接顶针寿命管理器的信号
            self.probe_pin_manager.lifetime_reset.connect(self._on_probe_pin_lifetime_reset)
            self.probe_pin_manager.test_count_updated.connect(self._on_probe_pin_test_count_updated)
            
            logger.debug("✅ 顶针寿命管理器初始化完成")
            
        except Exception as e:
            logger.error(f"❌ 初始化顶针寿命管理器失败: {e}")
            # 不抛出异常，避免影响设置同步管理器初始化
    
    def _on_probe_pin_lifetime_reset(self):
        """处理顶针寿命归零信号"""
        try:
            logger.info("🔄 收到顶针寿命归零信号，开始同步主界面")
            
            # 更新所有通道的顶针寿命显示
            self._update_probe_pin_lifetime_display()
            
            # 显示归零通知
            self._show_probe_pin_reset_notification()
            
            # 发送同步完成信号
            self.sync_completed.emit("顶针寿命归零后主界面已更新")
            
        except Exception as e:
            logger.error(f"处理顶针寿命归零信号失败: {e}")
            self.sync_failed.emit("probe_pin_reset", str(e))
    
    def _on_probe_pin_test_count_updated(self, channel_num: int, new_count: int):
        """处理顶针测试计数更新信号"""
        try:
            logger.debug(f"🔢 收到通道{channel_num}测试计数更新信号: {new_count}")
            
            # 更新指定通道的测试计数显示
            self._update_channel_test_count(channel_num, new_count)
            
        except Exception as e:
            logger.error(f"处理通道{channel_num}测试计数更新信号失败: {e}")
    
    def _connect_config_signals(self):
        """连接配置变更信号"""
        try:
            # 连接配置管理器的变更信号
            if hasattr(self.config_manager, 'config_changed'):
                self.config_manager.config_changed.connect(self._on_config_changed)
                logger.debug("已连接配置变更信号")
            else:
                logger.warning("配置管理器没有config_changed信号")
                
        except Exception as e:
            logger.error(f"连接配置变更信号失败: {e}")
    
    def _on_config_changed(self, key: str, value: Any):
        """
        处理配置变更事件
        
        Args:
            key: 配置键
            value: 新值
        """
        try:
            
            # 根据配置键类型进行不同的处理
            if self._is_device_connection_config(key):
                self._sync_device_connection_settings(key, value)
            elif self._is_printer_config(key):
                self._sync_printer_settings(key, value)
            elif self._is_probe_pin_config(key):
                self._sync_probe_pin_settings(key, value)
            elif self._is_test_count_config(key):
                self._sync_test_count_settings(key, value)
            elif self._is_channel_enable_config(key):
                self._sync_channel_enable_settings(key, value)
            elif self._is_general_ui_config(key):
                self._sync_general_ui_settings(key, value)
            else:
                logger.debug(f"配置变更不需要特殊处理: {key}")
                
        except Exception as e:
            logger.error(f"处理配置变更失败: {e}")
            self.sync_failed.emit(key, str(e))
    
    def _is_device_connection_config(self, key: str) -> bool:
        """判断是否为设备连接配置"""
        device_keys = [
            'device.connection.port',
            'device.connection.baudrate', 
            'device.connection.timeout',
            'device.auto_connect',
            'device.auto_reconnect',
            'device.reconnect_interval'
        ]
        return key in device_keys
    
    def _is_printer_config(self, key: str) -> bool:
        """判断是否为打印机配置"""
        printer_keys = [
            'printer.name',
            'printer.type',
            'printer.connection',
            'printer.quality',
            'label_print.auto_print',
            'label_print.print_pass_only',
            'label_print.copies'
        ]
        return key in printer_keys
    
    def _is_probe_pin_config(self, key: str) -> bool:
        """判断是否为顶针寿命配置"""
        return key.startswith('probe_pin.')
    
    def _is_test_count_config(self, key: str) -> bool:
        """判断是否为测试计数配置"""
        return key.startswith('test_count.')
    
    def _is_channel_enable_config(self, key: str) -> bool:
        """判断是否为通道使能配置"""
        return key == 'test.enabled_channels'
    
    def _is_general_ui_config(self, key: str) -> bool:
        """判断是否为通用UI配置"""
        ui_keys = [
            'batch_info.batch_number',
            'batch_info.operator',
            'batch_info.cell_type',
            'batch_info.cell_spec',
            'product.batch_number',
            'product.operator',
            'product.battery_type',
            'product.battery_spec'
        ]
        return key in ui_keys
    
    def _sync_device_connection_settings(self, key: str, value: Any):
        """同步设备连接设置"""
        try:
            logger.info(f"🔌 同步设备连接设置: {key} = {value}")
            
            # 更新设备连接状态显示
            self._update_device_connection_status()
            
            # 如果是端口变更，需要重新连接
            if key == 'device.connection.port':
                self._handle_port_change(value)
            
            # 更新状态栏显示
            self._update_status_bar_device_info()
            
            self.sync_completed.emit(f"设备连接设置已更新: {key}")
            
        except Exception as e:
            logger.error(f"同步设备连接设置失败: {e}")
            self.sync_failed.emit("device_connection", str(e))
    
    def _sync_printer_settings(self, key: str, value: Any):
        """同步打印机设置"""
        try:
            logger.info(f"🖨️ 同步打印机设置: {key} = {value}")
            
            # 更新打印机状态显示
            self._update_printer_status()
            
            # 如果是打印机名称变更，需要重新检测
            if key == 'printer.name':
                self._handle_printer_change(value)
            
            # 更新状态栏显示
            self._update_status_bar_printer_info()
            
            self.sync_completed.emit(f"打印机设置已更新: {key}")
            
        except Exception as e:
            logger.error(f"同步打印机设置失败: {e}")
            self.sync_failed.emit("printer", str(e))
    
    def _sync_probe_pin_settings(self, key: str, value: Any):
        """同步顶针寿命设置"""
        try:
            logger.info(f"📌 同步顶针寿命设置: {key} = {value}")
            
            # 更新所有通道的顶针寿命显示
            self._update_probe_pin_lifetime_display()
            
            # 如果是归零操作，显示提示
            if 'reset' in key.lower() or value == 0:
                self._show_probe_pin_reset_notification()
            
            self.sync_completed.emit(f"顶针寿命设置已更新: {key}")
            
        except Exception as e:
            logger.error(f"同步顶针寿命设置失败: {e}")
            self.sync_failed.emit("probe_pin", str(e))
    
    def _sync_test_count_settings(self, key: str, value: Any):
        """同步测试计数设置"""
        try:
            logger.info(f"🔢 同步测试计数设置: {key} = {value}")
            
            # 提取通道号
            if 'channel_' in key:
                channel_num_str = key.split('channel_')[1]
                try:
                    channel_num = int(channel_num_str)
                    self._update_channel_test_count(channel_num, value)
                except ValueError:
                    logger.warning(f"无法解析通道号: {key}")
            
            self.sync_completed.emit(f"测试计数已更新: {key}")
            
        except Exception as e:
            logger.error(f"同步测试计数设置失败: {e}")
            self.sync_failed.emit("test_count", str(e))
    
    def _sync_channel_enable_settings(self, key: str, value: Any):
        """同步通道使能设置"""
        try:
            logger.info(f"📋 同步通道使能设置: {key} = {value}")
            
            # 更新通道使能状态显示
            self._update_channel_enable_display(value)
            
            self.sync_completed.emit(f"通道使能设置已更新: {key}")
            
        except Exception as e:
            logger.error(f"同步通道使能设置失败: {e}")
            self.sync_failed.emit("channel_enable", str(e))
    
    def _sync_general_ui_settings(self, key: str, value: Any):
        """同步通用UI设置"""
        try:
            logger.info(f"🎨 同步通用UI设置: {key} = {value}")
            
            # 更新批次信息显示
            if key.startswith('batch_info.') or key.startswith('product.'):
                self._update_batch_info_display()
            
            self.sync_completed.emit(f"UI设置已更新: {key}")
            
        except Exception as e:
            logger.error(f"同步通用UI设置失败: {e}")
            self.sync_failed.emit("general_ui", str(e))
    
    def _update_device_connection_status(self):
        """更新设备连接状态显示"""
        try:
            # 获取设备连接管理器
            if hasattr(self.main_window, 'device_connection_manager'):
                device_manager = self.main_window.device_connection_manager
                
                # 获取当前连接状态
                is_connected = getattr(device_manager, 'is_connected', False)
                current_port = getattr(device_manager, 'current_port', '')
                
                # 更新头部状态显示
                self._update_header_device_status(is_connected, current_port)
                
                logger.debug(f"设备连接状态已更新: {is_connected}, 端口: {current_port}")
            else:
                logger.warning("设备连接管理器未找到")
                
        except Exception as e:
            logger.error(f"更新设备连接状态失败: {e}")
    
    def _update_printer_status(self):
        """更新打印机状态显示"""
        try:
            # 获取打印机管理器
            if hasattr(self.main_window, 'printer_manager'):
                printer_manager = self.main_window.printer_manager
                
                # 强制刷新打印机状态
                printer_manager.refresh_status()
                
                # 获取当前状态
                is_connected = printer_manager.get_current_status()
                printer_info = printer_manager.get_printer_status()
                
                # 更新UI显示
                self._update_header_printer_status(is_connected, printer_info)
                
                logger.debug(f"打印机状态已更新: {is_connected}")
            else:
                logger.warning("打印机管理器未找到")
                
        except Exception as e:
            logger.error(f"更新打印机状态失败: {e}")
    
    def _update_probe_pin_lifetime_display(self):
        """更新顶针寿命显示"""
        try:
            # 获取UI组件管理器
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                
                # 获取通道容器
                channels_container = ui_manager.get_component('channels_container')
                if channels_container:
                    # 刷新所有通道的测试计数显示
                    for channel_num in range(1, 9):
                        count = self.config_manager.get(f'test_count.channel_{channel_num}', 0)
                        if hasattr(channels_container, 'update_channel_test_count'):
                            channels_container.update_channel_test_count(channel_num, count)
                    
                    logger.debug("顶针寿命显示已更新")
                else:
                    logger.warning("通道容器组件未找到")
            else:
                logger.warning("UI组件管理器未找到")
                
        except Exception as e:
            logger.error(f"更新顶针寿命显示失败: {e}")
    
    def _update_channel_test_count(self, channel_num: int, count: int):
        """更新指定通道的测试计数显示"""
        try:
            # 获取UI组件管理器
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                
                # 获取通道容器
                channels_container = ui_manager.get_component('channels_container')
                if channels_container and hasattr(channels_container, 'update_channel_test_count'):
                    channels_container.update_channel_test_count(channel_num, count)
                    logger.debug(f"通道{channel_num}测试计数已更新: {count}")
                else:
                    logger.warning("通道容器组件未找到或不支持测试计数更新")
            else:
                logger.warning("UI组件管理器未找到")
                
        except Exception as e:
            logger.error(f"更新通道{channel_num}测试计数失败: {e}")
    
    def _update_channel_enable_display(self, enabled_channels: list):
        """更新通道使能状态显示"""
        try:
            # 获取UI组件管理器
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                
                # 获取通道容器
                channels_container = ui_manager.get_component('channels_container')
                if channels_container:
                    # 更新所有通道的使能状态
                    for channel_num in range(1, 9):
                        is_enabled = channel_num in enabled_channels
                        if hasattr(channels_container, 'set_channel_enabled'):
                            channels_container.set_channel_enabled(channel_num, is_enabled)
                    
                    logger.debug(f"通道使能状态已更新: {enabled_channels}")
                else:
                    logger.warning("通道容器组件未找到")
            else:
                logger.warning("UI组件管理器未找到")
                
        except Exception as e:
            logger.error(f"更新通道使能状态失败: {e}")
    
    def _update_batch_info_display(self):
        """更新批次信息显示"""
        try:
            # 获取UI组件管理器
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                
                # 获取批次信息组件
                batch_info = ui_manager.get_component('batch_info')
                if batch_info and hasattr(batch_info, 'refresh_display'):
                    batch_info.refresh_display()
                    logger.debug("批次信息显示已更新")
                else:
                    logger.warning("批次信息组件未找到或不支持刷新")
            else:
                logger.warning("UI组件管理器未找到")
                
        except Exception as e:
            logger.error(f"更新批次信息显示失败: {e}")
    
    def _handle_port_change(self, new_port: str):
        """处理端口变更"""
        try:
            logger.info(f"🔌 处理端口变更: {new_port}")
            
            # 获取设备连接管理器
            if hasattr(self.main_window, 'device_connection_manager'):
                device_manager = self.main_window.device_connection_manager
                
                # 如果当前已连接，先断开
                if getattr(device_manager, 'is_connected', False):
                    logger.info("端口变更，断开当前连接")
                    device_manager.disconnect_device()
                
                # 延迟重新连接到新端口
                QTimer.singleShot(1000, lambda: self._reconnect_to_new_port(new_port))
            else:
                logger.warning("设备连接管理器未找到")
                
        except Exception as e:
            logger.error(f"处理端口变更失败: {e}")
    
    def _handle_printer_change(self, new_printer: str):
        """处理打印机变更"""
        try:
            logger.info(f"🖨️ 处理打印机变更: {new_printer}")
            
            # 获取打印机管理器
            if hasattr(self.main_window, 'printer_manager'):
                printer_manager = self.main_window.printer_manager
                
                # 更新打印机配置
                if hasattr(printer_manager, 'update_printer_config'):
                    success = printer_manager.update_printer_config(new_printer)
                    if success:
                        logger.info(f"打印机配置更新成功: {new_printer}")
                    else:
                        logger.warning(f"打印机配置更新失败: {new_printer}")
                else:
                    # 强制刷新状态
                    printer_manager.refresh_status()
            else:
                logger.warning("打印机管理器未找到")
                
        except Exception as e:
            logger.error(f"处理打印机变更失败: {e}")
    
    def _reconnect_to_new_port(self, port: str):
        """重新连接到新端口"""
        try:
            logger.info(f"🔄 重新连接到新端口: {port}")
            
            # 获取设备连接管理器
            if hasattr(self.main_window, 'device_connection_manager'):
                device_manager = self.main_window.device_connection_manager
                
                # 尝试自动连接
                if hasattr(device_manager, '_perform_auto_connect'):
                    device_manager._perform_auto_connect()
                elif hasattr(device_manager, 'auto_connect'):
                    device_manager.auto_connect()
                else:
                    logger.warning("设备连接管理器不支持自动连接")
            else:
                logger.warning("设备连接管理器未找到")
                
        except Exception as e:
            logger.error(f"重新连接到新端口失败: {e}")
    
    def _update_header_device_status(self, is_connected: bool, port: str):
        """更新头部设备状态显示"""
        try:
            # 获取头部组件
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                header = ui_manager.get_component('header')
                
                if header and hasattr(header, 'update_device_status'):
                    header.update_device_status(is_connected, port)
                    logger.debug("头部设备状态已更新")
                else:
                    logger.debug("头部组件未找到或不支持设备状态更新")
            
        except Exception as e:
            logger.error(f"更新头部设备状态失败: {e}")
    
    def _update_header_printer_status(self, is_connected: bool, printer_info: dict):
        """更新头部打印机状态显示"""
        try:
            # 获取头部组件
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                header = ui_manager.get_component('header')
                
                if header and hasattr(header, 'update_printer_status'):
                    header.update_printer_status(is_connected, printer_info)
                    logger.debug("头部打印机状态已更新")
                else:
                    logger.debug("头部组件未找到或不支持打印机状态更新")
            
        except Exception as e:
            logger.error(f"更新头部打印机状态失败: {e}")
    
    def _update_status_bar_device_info(self):
        """更新状态栏设备信息"""
        try:
            # 获取状态栏组件
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                status_bar = ui_manager.get_component('status_bar')
                
                if status_bar:
                    # 获取当前设备连接状态
                    is_connected = False
                    current_port = ''
                    
                    # 从设备连接管理器获取实际状态
                    if hasattr(self.main_window, 'device_connection_manager'):
                        device_manager = self.main_window.device_connection_manager
                        is_connected = getattr(device_manager, 'is_connected', False)
                        current_port = getattr(device_manager, 'current_port', '')
                    
                    # 如果没有连接状态，从配置获取端口信息
                    if not current_port:
                        current_port = self.config_manager.get('device.connection.port', '')
                    
                    # 使用状态栏的标准方法更新设备状态
                    if hasattr(status_bar, 'set_device_status'):
                        status_bar.set_device_status(is_connected, current_port)
                        logger.info(f"✅ 状态栏设备信息已更新: 连接={is_connected}, 端口={current_port}")
                    elif hasattr(status_bar, 'set_port_info'):
                        status_bar.set_port_info(current_port)
                        logger.info(f"✅ 状态栏端口信息已更新: {current_port}")
                    else:
                        logger.warning("⚠️ 状态栏组件不支持设备状态更新方法")
                else:
                    logger.warning("⚠️ 状态栏组件未找到")
            
        except Exception as e:
            logger.error(f"❌ 更新状态栏设备信息失败: {e}")
    
    def _update_status_bar_printer_info(self):
        """更新状态栏打印机信息"""
        try:
            # 获取状态栏组件
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                status_bar = ui_manager.get_component('status_bar')
                
                if status_bar:
                    # 获取当前打印机连接状态
                    is_connected = False
                    
                    # 从打印机管理器获取实际状态
                    if hasattr(self.main_window, 'printer_manager'):
                        printer_manager = self.main_window.printer_manager
                        is_connected = printer_manager.get_current_status()
                    
                    # 使用状态栏的标准方法更新打印机状态
                    if hasattr(status_bar, 'set_printer_status'):
                        status_bar.set_printer_status(is_connected)
                        logger.info(f"✅ 状态栏打印机信息已更新: 连接={is_connected}")
                    else:
                        logger.warning("⚠️ 状态栏组件不支持打印机状态更新方法")
                else:
                    logger.warning("⚠️ 状态栏组件未找到")
            
        except Exception as e:
            logger.error(f"❌ 更新状态栏打印机信息失败: {e}")
    
    def _show_probe_pin_reset_notification(self):
        """显示顶针寿命归零通知"""
        try:
            # 获取状态栏组件显示通知
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                status_bar = ui_manager.get_component('status_bar')
                
                if status_bar and hasattr(status_bar, 'set_system_status'):
                    status_bar.set_system_status("顶针寿命已归零，计数器已重置", "success")
                    logger.info("顶针寿命归零通知已显示")
                else:
                    logger.debug("状态栏组件未找到，使用消息框显示通知")
                    # 备用方案：使用消息框
                    QMessageBox.information(
                        self.main_window,
                        "顶针寿命归零",
                        "顶针寿命计数器已成功归零重置！\n\n所有通道的测试计数已清零，可以重新开始计数。"
                    )
            
        except Exception as e:
            logger.error(f"显示顶针寿命归零通知失败: {e}")
    
    def force_sync_all_settings(self):
        """强制同步所有设置到主界面"""
        try:
            logger.info("🔄 开始强制同步所有设置...")
            
            # 同步设备连接设置
            self._update_device_connection_status()
            
            # 同步打印机设置
            self._update_printer_status()
            
            # 同步顶针寿命设置
            self._update_probe_pin_lifetime_display()
            
            # 同步通道使能设置
            enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))
            self._update_channel_enable_display(enabled_channels)
            
            # 同步批次信息设置
            self._update_batch_info_display()
            
            # 更新状态栏信息
            self._update_status_bar_device_info()
            self._update_status_bar_printer_info()
            
            logger.info("✅ 所有设置强制同步完成")
            self.sync_completed.emit("所有设置已强制同步")
            
        except Exception as e:
            logger.error(f"强制同步所有设置失败: {e}")
            self.sync_failed.emit("force_sync_all", str(e))
    
    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态信息"""
        try:
            return {
                'device_connection': {
                    'port': self.config_manager.get('device.connection.port', ''),
                    'connected': getattr(getattr(self.main_window, 'device_connection_manager', None), 'is_connected', False)
                },
                'printer': {
                    'name': self.config_manager.get('printer.name', ''),
                    'connected': getattr(getattr(self.main_window, 'printer_manager', None), 'current_printer_connected', False)
                },
                'probe_pin': {
                    'warning_threshold': self.config_manager.get('probe_pin.warning_threshold', 1000),
                    'max_lifetime': self.config_manager.get('probe_pin.max_lifetime', 10000)
                },
                'enabled_channels': self.config_manager.get('test.enabled_channels', list(range(1, 9)))
            }
            
        except Exception as e:
            logger.error(f"获取同步状态失败: {e}")
            return {}
