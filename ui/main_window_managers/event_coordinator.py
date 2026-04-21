# -*- coding: utf-8 -*-
"""
事件协调器
从MainWindow中提取的事件处理相关功能

职责：
- 事件处理方法
- 信号回调处理
- 状态变更协调
- 错误处理协调

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


class EventCoordinator(QObject):
    """
    事件协调器
    
    职责：
    - 处理各种事件回调
    - 协调不同组件间的状态变更
    - 统一的错误处理
    - 事件流程控制
    """
    
    def __init__(self, main_window, config_manager):
        """
        初始化事件协调器

        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
        """
        super().__init__()

        self.main_window = main_window
        self.config_manager = config_manager

        # 修复连接配置变更信号
        self._connect_config_signals()

        logger.debug("事件协调器初始化完成")

    def _connect_config_signals(self):
        """连接配置变更信号"""
        try:
            # 连接配置变更信号到处理方法
            if hasattr(self.config_manager, 'config_changed'):
                self.config_manager.config_changed.connect(self.handle_config_changed)
                logger.info("✅ 配置变更信号已连接")
            else:
                logger.warning("⚠️ 配置管理器没有 config_changed 信号")

        except Exception as e:
            logger.error(f"❌ 连接配置变更信号失败: {e}")
    
    def handle_device_connection_changed(self, connected: bool):
        """设备连接状态变更处理"""
        try:
            # 如果是连接状态，延迟一点时间再获取端口信息，确保设备信息已更新
            if connected:
                # 使用QTimer延迟100ms后再更新状态栏，确保设备信息已更新
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(100, lambda: self._update_connection_status_with_port(connected))
            else:
                # 断开连接时立即更新
                self._update_connection_status_with_port(connected)

        except Exception as e:
            logger.error(f"处理设备连接状态变更失败: {e}")

    def _update_connection_status_with_port(self, connected: bool):
        """
        更新连接状态和端口信息

        Args:
            connected: 是否连接
        """
        try:
            # 获取当前连接的串口信息
            current_port = ""
            if connected:
                try:
                    # 优先从设备连接管理器获取当前端口
                    if hasattr(self.main_window, 'device_connection_manager'):
                        device_manager = self.main_window.device_connection_manager
                        if hasattr(device_manager, 'current_port') and device_manager.current_port:
                            current_port = device_manager.current_port
                            logger.debug(f"通过设备连接管理器获取串口: {current_port}")
                        elif hasattr(device_manager, 'device_info') and device_manager.device_info:
                            current_port = device_manager.device_info.get('port', '')
                            logger.debug(f"通过设备信息获取串口: {current_port}")

                    # 如果设备连接管理器没有端口信息，尝试从通信管理器获取
                    if not current_port and hasattr(self.main_window, 'comm_manager'):
                        if hasattr(self.main_window.comm_manager, 'port'):
                            current_port = getattr(self.main_window.comm_manager, 'port', '')
                            logger.debug(f"通过通信管理器port属性获取串口: {current_port}")
                        elif hasattr(self.main_window.comm_manager, 'get_actual_port'):
                            current_port = self.main_window.comm_manager.get_actual_port()
                            logger.debug(f"通过get_actual_port获取串口: {current_port}")

                    # 最后尝试从配置获取
                    if not current_port:
                        current_port = self.config_manager.get('device.connection.port', '')
                        logger.debug(f"通过配置获取串口: {current_port}")

                except Exception as e:
                    logger.debug(f"获取串口信息失败: {e}")

            # 修复统一状态栏更新，避免重复调用
            device_info = {}
            if connected and hasattr(self.main_window, 'device_connection_manager'):
                device_info = getattr(self.main_window.device_connection_manager, 'device_info', {})
                if current_port and 'port' not in device_info:
                    device_info['port'] = current_port

            # 统一通过UI组件管理器更新设备状态（包含状态栏更新）
            self.main_window.ui_component_manager.update_device_status(connected, device_info)

            logger.debug(f"设备状态已统一更新: {'已连接' if connected else '未连接'} {current_port}")

            # 更新菜单状态
            self.main_window.menu_manager.update_menu_status(self.main_window.is_testing)

            logger.info(f"设备连接状态已更新: {'已连接' if connected else '未连接'} {current_port}")

        except Exception as e:
            logger.error(f"更新连接状态和端口信息失败: {e}")
    
    def handle_device_info_updated(self, device_info: dict):
        """设备信息更新处理"""
        try:
            self.main_window.ui_component_manager.update_device_status(True, device_info)
        except Exception as e:
            logger.error(f"处理设备信息更新失败: {e}")
    
    def handle_test_started(self):
        """测试开始处理"""
        try:
            self.main_window.is_testing = True
            self.main_window.test_started.emit()
            
            # 更新UI状态
            self.main_window.ui_component_manager.set_component_enabled('test_control', True)
            self.main_window.menu_manager.update_menu_status(True)
            
        except Exception as e:
            logger.error(f"处理测试开始失败: {e}")
    
    def handle_test_stopped(self):
        """测试停止处理"""
        try:
            self.main_window.is_testing = False
            self.main_window.test_stopped.emit()
            
            # 更新UI状态
            self.main_window.ui_component_manager.set_component_enabled('test_control', True)
            self.main_window.menu_manager.update_menu_status(False)
            
        except Exception as e:
            logger.error(f"处理测试停止失败: {e}")
    
    def handle_test_progress_updated(self, channel_num: int, progress_data: dict):
        """测试进度更新处理（修复版 - 防止递归调用并确保采样测试完成）"""
        try:
            # 🔧 新增：检查是否为全局测试完成信号
            if channel_num == 0 and progress_data.get('state') == 'test_completed':
                logger.info("🎯 收到全局测试完成信号，强制重置UI状态")
                self._handle_global_test_completed(progress_data)
                return

            # Jack修复防止递归调用
            if hasattr(self, '_processing_progress') and self._processing_progress:
                logger.debug(f"🔧 [事件协调器] 跳过递归调用: 通道{channel_num}")
                return

            self._processing_progress = True

            try:
                state = progress_data.get('state', 'unknown')
                progress = progress_data.get('progress', 0)
                frequency = progress_data.get('frequency', 'N/A')

                logger.debug(f"🔧 [事件协调器] 收到通道{channel_num}进度更新: 状态={state}, 进度={progress}%, 频率={frequency}Hz")

                # 新增处理通道异常状态
                if progress_data.get('state') == 'exception':
                    self.handle_channel_exception(channel_num, progress_data)
                else:
                    if progress_data.get('state') == 'completed':
                        rs_grade = progress_data.get('rs_grade')
                        rct_grade = progress_data.get('rct_grade')
                        is_pass = progress_data.get('is_pass')

                        # 修复：正确显示档位信息，None值显示为"未知"
                        rs_grade_display = "未知" if rs_grade is None else rs_grade
                        rct_grade_display = "未知" if rct_grade is None else rct_grade
                        result_display = "合格" if is_pass else "不合格" if is_pass is not None else "未判定"

                        logger.debug(f" [事件协调器] 通道{channel_num}测试完成: Rs档位={rs_grade_display}, Rct档位={rct_grade_display}, 结果={result_display}")

                    # 更新UI进度（包括统计更新）
                    self.main_window.ui_component_manager.update_test_progress(channel_num, progress_data)

                    # 关键修复确保所有通道的completed状态都触发打印处理
                    if progress_data.get('state') == 'completed':
                        logger.debug(f" [事件协调器] 通道{channel_num}测试完成，强制触发打印处理")
                        self.handle_channel_test_completed(channel_num, progress_data)

                        # Jack修复检查是否为采样测试模式，如果是则检查是否所有通道都完成
                        sampling_test = getattr(self.main_window.config_manager, 'get', lambda x, y: False)('test.sampling_test', False)
                        if sampling_test:
                            self._check_sampling_test_completion()

            finally:
                self._processing_progress = False

        except Exception as e:
            logger.error(f"处理测试进度更新失败: {e}")
            # 确保重置标志
            self._processing_progress = False

    def handle_channel_exception(self, channel_num: int, exception_data: dict):
        """处理通道异常"""
        try:
            logger.warning(f"🚨 处理通道{channel_num}异常: {exception_data}")

            # 更新UI显示异常状态
            self.main_window.ui_component_manager.update_channel_exception(channel_num, exception_data)

            # 更新状态栏显示
            status_bar = self.main_window.ui_component_manager.get_component('status_bar')
            if status_bar and hasattr(status_bar, 'set_system_status'):
                error_message = exception_data.get('error_message', '通道异常')
                status_bar.set_system_status(f"通道{channel_num}: {error_message}", "warning")

        except Exception as e:
            logger.error(f"处理通道{channel_num}异常失败: {e}")

    def _check_sampling_test_completion(self):
        """检查采样测试是否完成"""
        try:
            # Jack修复检查所有通道是否都已完成
            channels_container = self.main_window.ui_component_manager.get_component('channels_container')
            logger.debug(f" 获取通道容器: {channels_container is not None}")
            if not channels_container:
                logger.error(f"🔧 通道容器获取失败，无法检查采样测试完成状态")
                return

            completed_channels = 0
            total_channels = 8

            # 修复使用正确的方式获取通道组件
            for channel_num in range(1, 9):
                try:
                    # 使用通道容器的get_channel方法获取通道组件
                    channel_widget = channels_container.get_channel(channel_num)
                    if channel_widget:
                        # 检查通道状态 - 使用通道组件的状态管理器
                        state_manager = getattr(channel_widget, 'state_manager', None)
                        current_progress = getattr(channel_widget, 'current_progress', 0)

                        if state_manager:
                            # 使用状态管理器获取状态
                            current_state = state_manager.test_state.value  # TestState枚举的值
                            logger.debug(f" 通道{channel_num}状态检查(状态管理器): state='{current_state}', progress={current_progress}%")

                            # 修复检查采样测试完成状态
                            if current_state in ['sampling_completed', 'completed'] or current_progress == 100:
                                completed_channels += 1
                                logger.debug(f" 通道{channel_num}被计为已完成: state='{current_state}', progress={current_progress}%")
                        else:
                            # 备用方案：直接检查通道属性
                            current_state = getattr(channel_widget, 'test_state', '')
                            logger.debug(f" 通道{channel_num}备用检查: test_state='{current_state}', progress={current_progress}%")

                            if current_state in ['sampling_completed', 'completed'] or current_progress == 100:
                                completed_channels += 1
                                logger.debug(f" 通道{channel_num}被计为已完成(备用): state='{current_state}', progress={current_progress}%")
                    else:
                        logger.warning(f"🔧 通道{channel_num}组件不存在")

                except Exception as channel_error:
                    logger.error(f"检查通道{channel_num}状态失败: {channel_error}")

            logger.debug(f" 采样测试完成检查: {completed_channels}/{total_channels}个通道完成")

            # 如果所有通道都完成了，触发采样测试完成处理
            if completed_channels >= total_channels:
                logger.info(f"🎉 检测到所有通道都已完成采样测试: {completed_channels}/{total_channels}")

                # 延迟触发，避免在事件处理中直接调用
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(1000, self._trigger_sampling_completion)

        except Exception as e:
            logger.error(f"❌ 检查采样测试完成失败: {e}")

    def _trigger_sampling_completion(self):
        """触发采样测试完成处理"""
        try:
            logger.debug(f" 触发采样测试完成处理...")

            # 调用主窗口的采样测试完成检查
            if hasattr(self.main_window, '_check_and_handle_sampling_completion'):
                self.main_window._check_and_handle_sampling_completion()
            else:
                logger.warning("⚠️ 主窗口没有采样测试完成处理方法")

        except Exception as e:
            logger.error(f"❌ 触发采样测试完成处理失败: {e}")

    def handle_test_failed(self, error_message: str):
        """测试失败处理"""
        try:
            logger.error(f"测试失败: {error_message}")

            # 重置测试状态
            self.main_window.is_testing = False

            # 更新UI状态
            self.main_window.ui_component_manager.set_component_enabled('test_control', True)

            # 显示错误消息
            QMessageBox.critical(self.main_window, "测试失败", f"测试过程中发生错误：\n\n{error_message}")

        except Exception as e:
            logger.error(f"处理测试失败失败: {e}")

    def handle_component_ready(self, component_name: str):
        """组件就绪处理"""
        logger.debug(f"组件 {component_name} 已就绪")
    
    def handle_component_error(self, component_name: str, error_msg: str):
        """组件错误处理"""
        logger.error(f"组件 {component_name} 错误: {error_msg}")
    
    def handle_channel_test_completed(self, channel_num: int, result_data: dict):
        """通道测试完成处理"""
        try:

            # 修复调用主窗口的测试完成处理方法（用于打印等功能）
            # 注意：统计更新已在update_test_progress中处理，这里不重复处理
            if hasattr(self.main_window, '_on_channel_test_completed'):
                self.main_window._on_channel_test_completed(channel_num, result_data)
            else:
                logger.warning("主窗口没有_on_channel_test_completed方法")

            # Jack修复检查是否为采样测试模式，如果是则检查是否所有通道都完成
            sampling_test = getattr(self.main_window.config_manager, 'get', lambda x, y: False)('test.sampling_test', False)
            if sampling_test:
                logger.info(f"🎯 采样测试模式：通道{channel_num}完成，检查是否所有通道都完成")
                # 延迟检查，避免在事件处理中直接调用
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(1000, self._check_all_channels_completed_for_sampling)

        except Exception as e:
            logger.error(f"处理通道测试完成失败: {e}")

    def _check_all_channels_completed_for_sampling(self):
        """检查所有通道是否都完成了采样测试"""
        try:
            logger.debug(f" 检查所有通道是否都完成了采样测试...")

            # 检查是否为采样测试模式
            sampling_test = getattr(self.main_window.config_manager, 'get', lambda x, y: False)('test.sampling_test', False)
            if not sampling_test:
                logger.debug(f" 非采样测试模式，跳过检查")
                return

            # Jack修复在采样测试模式下，直接检查通道完成状态，不依赖is_testing
            # 因为采样测试模式下，即使所有通道完成，is_testing可能仍为True
            logger.debug(f" 采样测试模式：直接检查通道完成状态")

            # 检查所有通道是否都完成
            completed_channels = self._count_completed_channels()
            total_channels = 8

            logger.debug(f" 通道完成状态检查: {completed_channels}/{total_channels}个通道完成")

            if completed_channels >= total_channels:
                logger.info("🎉 所有通道都已完成，触发采样测试完成检查")
                # 调用主窗口的采样测试完成检查
                if hasattr(self.main_window, '_check_and_handle_sampling_completion'):
                    self.main_window._check_and_handle_sampling_completion()
                else:
                    logger.warning("⚠️ 主窗口没有_check_and_handle_sampling_completion方法")
            else:
                logger.info(f"📊 还有{total_channels - completed_channels}个通道未完成，继续等待")

        except Exception as e:
            logger.error(f"❌ 检查所有通道完成状态失败: {e}")

    def _handle_global_test_completed(self, progress_data: dict):
        """处理全局测试完成信号"""
        try:
            logger.info("🔄 处理全局测试完成信号，强制重置UI状态...")

            success = progress_data.get('success', True)

            # 1. 强制设置主窗口测试状态为False
            self.main_window.is_testing = False
            logger.info("✅ 主窗口测试状态已重置为False")

            # 2. 强制重置测试控制组件按钮状态
            test_control = self.main_window.ui_component_manager.get_component('test_control')
            if test_control and hasattr(test_control, 'on_test_completed'):
                logger.info("🔄 强制调用测试控制组件的on_test_completed方法")
                test_control.on_test_completed()
                logger.info("✅ 测试控制组件按钮状态已重置")
            else:
                logger.warning("❌ 无法获取测试控制组件或组件没有on_test_completed方法")

            # 3. 强制重置测试流程管理器状态
            if hasattr(self.main_window, 'test_flow_manager') and self.main_window.test_flow_manager:
                if hasattr(self.main_window.test_flow_manager, 'is_testing'):
                    self.main_window.test_flow_manager.is_testing = False
                    logger.info("✅ 测试流程管理器状态已重置")

            # 4. 发送测试停止信号
            self.main_window.test_stopped.emit()
            logger.info("✅ 测试停止信号已发送")

            # 5. 更新状态栏
            status_bar = self.main_window.ui_component_manager.get_component('status_bar')
            if status_bar and hasattr(status_bar, 'set_system_status'):
                status_message = "测试完成" if success else "测试失败"
                status_bar.set_system_status(status_message, "success" if success else "error")
                logger.info(f"✅ 状态栏已更新: {status_message}")

            # 6. 更新菜单状态
            if hasattr(self.main_window, 'menu_manager'):
                self.main_window.menu_manager.update_menu_status(False)
                logger.info("✅ 菜单状态已更新")

            # 🔋 关键修复：通知统一测试控制器测试完成
            if hasattr(self.main_window, 'unified_test_controller') and self.main_window.unified_test_controller:
                try:
                    logger.info("🔋 [全局测试完成] 通知统一测试控制器测试完成")
                    # 调用统一测试控制器的状态回调
                    if hasattr(self.main_window.unified_test_controller, '_on_test_executor_status_changed'):
                        status_data = {
                            'action': 'test_completed',
                            'is_testing': False,
                            'success': success
                        }
                        self.main_window.unified_test_controller._on_test_executor_status_changed(status_data)
                        logger.info("✅ [全局测试完成] 统一测试控制器状态回调已调用")
                    else:
                        logger.warning("⚠️ [全局测试完成] 统一测试控制器没有状态回调方法")
                except Exception as e:
                    logger.error(f"❌ [全局测试完成] 调用统一测试控制器状态回调失败: {e}")

            logger.info("✅ 全局测试完成处理完成，UI状态已强制重置")

        except Exception as e:
            logger.error(f"❌ 处理全局测试完成信号失败: {e}")

    def _count_completed_channels(self):
        """统计已完成的通道数量"""
        try:
            completed_count = 0

            # 获取通道容器
            channels_container = self.main_window.ui_component_manager.get_component('channels_container')
            if not channels_container:
                logger.warning("🔧 无法获取通道容器，返回0")
                return 0

            # 检查每个通道的完成状态
            for channel_num in range(1, 9):
                try:
                    channel_widget = channels_container.get_channel(channel_num)
                    if channel_widget:
                        # 检查通道状态管理器
                        state_manager = getattr(channel_widget, 'state_manager', None)
                        if state_manager:
                            current_state = state_manager.test_state.value
                            if current_state in ['sampling_completed', 'completed']:
                                completed_count += 1
                                logger.debug(f"🔧 通道{channel_num}已完成: {current_state}")
                        else:
                            # 备用检查方法
                            current_progress = getattr(channel_widget, 'current_progress', 0)
                            if current_progress == 100:
                                completed_count += 1
                                logger.debug(f"🔧 通道{channel_num}已完成(进度100%)")
                except Exception as channel_error:
                    logger.debug(f"检查通道{channel_num}状态失败: {channel_error}")

            return completed_count

        except Exception as e:
            logger.error(f"统计完成通道数量失败: {e}")
            return 0
    
    def handle_printer_status_changed(self, connected: bool, printer_info: Optional[dict] = None):
        """打印机状态变更处理"""
        try:
            logger.info(f"打印机状态变更: {'已连接' if connected else '未连接'}")
            
            # 更新UI显示
            self.main_window.ui_component_manager.update_printer_status(connected, printer_info)
            
        except Exception as e:
            logger.error(f"处理打印机状态变更失败: {e}")
    
    def handle_label_print_started(self, print_job_info: dict):
        """标签打印开始处理"""
        try:
            logger.info(f"标签打印开始: {print_job_info}")
            
            # 这里可以添加打印开始的处理逻辑
            
        except Exception as e:
            logger.error(f"处理标签打印开始失败: {e}")
    
    def handle_label_print_completed(self, print_result: dict):
        """标签打印完成处理"""
        try:
            logger.info(f"标签打印完成: {print_result}")
            
            # 这里可以添加打印完成的处理逻辑
            
        except Exception as e:
            logger.error(f"处理标签打印完成失败: {e}")
    
    def handle_print_queue_updated(self, queue_info: dict):
        """打印队列更新处理"""
        try:
            logger.debug(f"打印队列更新: {queue_info}")
            
            # 这里可以添加队列更新的处理逻辑
            
        except Exception as e:
            logger.error(f"处理打印队列更新失败: {e}")
    
    def handle_config_changed(self, config_key: str, new_value: Any):
        """配置变更处理"""
        try:

            # 根据配置类型进行相应处理
            if config_key.startswith('ui.'):
                self._handle_ui_config_changed(config_key, new_value)
            elif config_key.startswith('test.'):
                self._handle_test_config_changed(config_key, new_value)
            elif config_key.startswith('device.'):
                self._handle_device_config_changed(config_key, new_value)
            elif config_key.startswith('batch_info.') or config_key.startswith('product.'):
                self._handle_product_config_changed(config_key, new_value)
            elif config_key.startswith('test_params.'):
                self._handle_test_params_config_changed(config_key, new_value)
            elif config_key.startswith('frequency.'):
                self._handle_frequency_config_changed(config_key, new_value)
            elif config_key.startswith('grade_settings.'):
                self._handle_grade_config_changed(config_key, new_value)
            elif config_key.startswith('outlier_detection.') or config_key.startswith('outlier_'):
                self._handle_outlier_detection_config_changed(config_key, new_value)
            elif config_key == 'settings' and new_value == 'updated':
                # 通用设置更新
                self._handle_general_settings_updated()
            else:
                logger.debug(f"未处理的配置类型: {config_key}")

        except Exception as e:
            logger.error(f"❌ 处理配置变更失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _handle_ui_config_changed(self, config_key: str, new_value: Any):
        """处理UI配置变更"""
        try:
            if 'style' in config_key:
                # 重新应用样式
                if hasattr(self.main_window, 'window_layout_manager'):
                    self.main_window.window_layout_manager.apply_styles()

        except Exception as e:
            logger.error(f"处理UI配置变更失败: {e}")

    def _handle_test_config_changed(self, config_key: str, new_value: Any):
        """处理测试配置变更"""
        try:
            if 'enabled_channels' in config_key:
                # 重新加载通道使能状态
                if hasattr(self.main_window, 'settings_loader'):
                    self.main_window.settings_loader.load_channel_enable_settings()
            elif 'test_count' in config_key:
                # 更新测试次数显示
                if hasattr(self.main_window, 'ui_component_manager'):
                    ui_manager = self.main_window.ui_component_manager
                    channels_container = ui_manager.get_component('channels_container')
                    if channels_container:
                        # 提取通道号
                        if 'channel_' in config_key:
                            channel_num_str = config_key.split('channel_')[1]
                            try:
                                channel_num = int(channel_num_str)
                                # 更新通道的测试计数显示
                                if hasattr(channels_container, 'update_channel_test_count'):
                                    channels_container.update_channel_test_count(channel_num, new_value)
                                    logger.info(f"通道{channel_num}的测试计数显示已更新")
                            except ValueError:
                                logger.warning(f"无法解析通道号: {config_key}")

        except Exception as e:
            logger.error(f"处理测试配置变更失败: {e}")

    def _handle_device_config_changed(self, config_key: str, new_value: Any):
        """处理设备配置变更"""
        try:
            if 'connection' in config_key:
                # 设备连接配置变更，重新连接设备

                # 修复同时更新设备连接管理器和通信管理器
                self._update_communication_managers_config()

                # 重新建立连接
                self._reconnect_device_with_new_config()

                logger.info("✅ 设备配置更新和重新连接完成")

        except Exception as e:
            logger.error(f"❌ 处理设备配置变更失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _update_communication_managers_config(self):
        """更新通信管理器配置"""
        try:
            # 获取最新的通信配置
            new_comm_config = {
                'port': self.config_manager.get('device.connection.port', 'COM16'),
                'baudrate': self.config_manager.get('device.connection.baudrate', 115200),
                'device_address': self.config_manager.get('device.connection.device_address', 1),
                'timeout': self.config_manager.get('device.connection.timeout', 2.0)
            }


            # 更新主窗口的通信管理器配置
            if hasattr(self.main_window, 'comm_manager'):
                comm_manager = self.main_window.comm_manager

                # 更新配置属性
                if hasattr(comm_manager, 'config'):
                    comm_manager.config.update(new_comm_config)

                # 更新直接属性
                for key, value in new_comm_config.items():
                    if hasattr(comm_manager, key):
                        setattr(comm_manager, key, value)
                        logger.debug(f"  更新 comm_manager.{key} = {value}")

                # 如果通信管理器有连接管理器，也要更新
                if hasattr(comm_manager, 'connection_manager'):
                    connection_manager = comm_manager.connection_manager
                    for key, value in new_comm_config.items():
                        if hasattr(connection_manager, key):
                            setattr(connection_manager, key, value)
                            logger.debug(f"  更新 connection_manager.{key} = {value}")

                logger.info("✅ 通信管理器配置已更新")
            else:
                logger.warning("⚠️ 主窗口没有 comm_manager 属性")

        except Exception as e:
            logger.error(f"❌ 更新通信管理器配置失败: {e}")

    def _reconnect_device_with_new_config(self):
        """使用新配置重新连接设备"""
        try:
            # 方法1：优先使用设备连接管理器
            if hasattr(self.main_window, 'device_connection_manager'):
                device_manager = self.main_window.device_connection_manager

                # 如果当前已连接，先断开连接
                if device_manager.is_connected:
                    logger.info("🔌 断开当前设备连接...")
                    device_manager.disconnect_device()

                    # 等待断开完成
                    import time
                    time.sleep(0.5)

                # 重新连接设备
                logger.info("🔌 使用新配置重新连接设备...")
                success = device_manager.connect_device()

                if success:
                    logger.info("✅ 设备重新连接成功")
                else:
                    logger.warning("⚠️ 设备重新连接失败")

                return success

            # 方法2：如果没有设备连接管理器，使用通信管理器
            elif hasattr(self.main_window, 'comm_manager'):
                comm_manager = self.main_window.comm_manager

                # 断开当前连接
                if hasattr(comm_manager, 'is_connected') and comm_manager.is_connected:
                    logger.info("🔌 断开当前通信连接...")
                    comm_manager.disconnect()

                    # 等待断开完成
                    import time
                    time.sleep(0.5)

                # 重新连接
                logger.info("🔌 使用新配置重新建立通信连接...")
                success = comm_manager.connect()

                if success:
                    logger.info("✅ 通信重新连接成功")
                else:
                    logger.warning("⚠️ 通信重新连接失败")

                return success

            else:
                logger.error("❌ 没有找到设备连接管理器或通信管理器")
                return False

        except Exception as e:
            logger.error(f"❌ 重新连接设备失败: {e}")
            return False

    def _handle_product_config_changed(self, config_key: str, new_value: Any):
        """处理产品信息配置变更"""
        try:

            # 更新批次信息组件
            if hasattr(self.main_window, 'ui_component_manager'):
                batch_info = self.main_window.ui_component_manager.get_component('batch_info')
                if batch_info and hasattr(batch_info, 'load_settings'):
                    batch_info.load_settings()
                    logger.info("✅ 批次信息组件已刷新")
                else:
                    logger.warning("⚠️ 批次信息组件未找到或不支持设置加载")

        except Exception as e:
            logger.error(f"❌ 处理产品信息配置变更失败: {e}")

    def _handle_test_params_config_changed(self, config_key: str, new_value: Any):
        """处理测试参数配置变更"""
        try:

            # 更新测试控制组件
            if hasattr(self.main_window, 'ui_component_manager'):
                test_control = self.main_window.ui_component_manager.get_component('test_control')
                if test_control and hasattr(test_control, 'load_settings'):
                    test_control.load_settings()
                    logger.info("✅ 测试控制组件已刷新")
                else:
                    logger.warning("⚠️ 测试控制组件未找到或不支持设置加载")

        except Exception as e:
            logger.error(f"❌ 处理测试参数配置变更失败: {e}")

    def _handle_outlier_detection_config_changed(self, config_key: str, new_value: Any):
        """处理离群检测配置变更"""
        try:

            # 修复重新加载离群检测设置，确保配置立即生效
            if hasattr(self.main_window, 'settings_loader'):
                self.main_window.settings_loader.load_outlier_detection_settings()
                logger.info("✅ 离群检测设置已重新加载")
            else:
                logger.warning("⚠️ 设置加载器未找到，无法重新加载离群检测设置")

            # 新增通知测试结果管理器更新离群检测配置缓存
            try:
                if hasattr(self.main_window, 'test_flow_controller') and self.main_window.test_flow_controller:
                    test_executor = getattr(self.main_window.test_flow_controller, 'test_executor', None)
                    if test_executor and hasattr(test_executor, 'test_result_manager'):
                        test_executor.test_result_manager.update_outlier_config_cache()
                        logger.info("✅ 测试结果管理器的离群检测配置缓存已更新")
                    else:
                        logger.debug("测试执行器或测试结果管理器未找到")
                else:
                    logger.debug("测试流程控制器未找到")
            except Exception as cache_error:
                logger.error(f"更新测试结果管理器配置缓存失败: {cache_error}")

            # 新增强制刷新UI显示，确保立即生效
            try:
                from PyQt5.QtCore import QTimer
                # 使用QTimer确保UI更新在主线程中执行
                QTimer.singleShot(100, self._force_refresh_outlier_ui)
                logger.info("✅ 已安排强制刷新离群率UI显示")
            except Exception as ui_error:
                logger.error(f"安排UI刷新失败: {ui_error}")

        except Exception as e:
            logger.error(f"❌ 处理离群检测配置变更失败: {e}")

    def _force_refresh_outlier_ui(self):
        """🚫 离群检测功能已删除"""
        pass

    def _handle_frequency_config_changed(self, config_key: str, new_value: Any):
        """处理频率配置变更"""
        try:
            # 这里可以添加频率配置变更的处理逻辑
            # 例如：更新频率设置组件、重新计算频率列表等
            logger.debug(f"频率配置变更: {config_key} = {new_value}")

        except Exception as e:
            logger.error(f"❌ 处理频率配置变更失败: {e}")

    def _handle_grade_config_changed(self, config_key: str, new_value: Any):
        """处理档位配置变更"""
        try:

            # 更新统计组件的档位范围显示
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                
                # 更新统计组件
                statistics_widget = ui_manager.get_component('statistics')
                if statistics_widget and hasattr(statistics_widget, 'update_grade_settings'):
                    statistics_widget.update_grade_settings()
                    logger.info("统计组件的档位范围显示已更新")
                
                # 更新通道显示组件
                channels_container = ui_manager.get_component('channels_container')
                if channels_container and hasattr(channels_container, 'update_grade_settings'):
                    channels_container.update_grade_settings()
                    logger.info("通道容器的档位设置已更新")

        except Exception as e:
            logger.error(f"❌ 处理档位配置变更失败: {e}")

    def _handle_general_settings_updated(self):
        """处理通用设置更新"""
        try:

            # 重新加载所有启动设置
            if hasattr(self.main_window, 'settings_loader'):
                self.main_window.settings_loader.load_startup_settings()
                logger.info("✅ 所有启动设置已重新加载")
            else:
                logger.warning("⚠️ 设置加载管理器未找到")

        except Exception as e:
            logger.error(f"❌ 处理通用设置更新失败: {e}")

    def handle_all_channels_ready(self, battery_codes: list):
        """所有通道准备就绪处理"""
        try:
            logger.info(f"所有通道准备就绪，电池码: {battery_codes}")

            # 这里可以添加所有通道就绪后的处理逻辑
            # 例如：自动开始测试、显示确认对话框等

        except Exception as e:
            logger.error(f"处理所有通道就绪失败: {e}")

    def handle_channel_battery_code_changed(self, channel_num: int, battery_code: str):
        """通道电池码变更处理"""
        try:
            logger.debug(f"通道{channel_num}电池码变更: {battery_code}")

            # 这里可以添加电池码变更的处理逻辑

        except Exception as e:
            logger.error(f"处理通道电池码变更失败: {e}")

    def get_event_statistics(self) -> Dict[str, Any]:
        """
        获取事件处理统计

        Returns:
            事件统计字典
        """
        try:
            # 这里可以添加事件统计的实现
            return {
                'total_events_handled': 0,  # 简化实现
                'error_events': 0,
                'success_events': 0,
                'last_event_time': None
            }

        except Exception as e:
            logger.error(f"获取事件统计失败: {e}")
            return {'error': str(e)}