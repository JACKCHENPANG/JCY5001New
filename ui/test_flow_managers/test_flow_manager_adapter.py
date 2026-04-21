# -*- coding: utf-8 -*-
"""
测试流程管理器适配器
将重构后的6个管理器组合成与原TestFlowManager兼容的接口

这个适配器类的作用：
1. 保持与原TestFlowManager相同的接口
2. 内部使用重构后的6个管理器
3. 确保向后兼容性
4. 提供平滑的迁移路径

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import List, Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QMetaObject, Qt
from PyQt5.QtWidgets import QMessageBox

from ui.battery_code_manager import BatteryCodeManager
from .test_flow_controller import TestFlowController
from .test_precheck_manager import TestPreCheckManager
from .test_configuration_manager import TestConfigurationManager
from .test_statistics_manager import TestStatisticsManager
from .test_ui_update_manager import TestUIUpdateManager
from .test_error_handler import TestErrorHandler

logger = logging.getLogger(__name__)


class TestFlowManagerAdapter(QObject):
    """
    测试流程管理器适配器
    
    将重构后的6个管理器组合成与原TestFlowManager兼容的接口
    """
    
    # 信号定义（保持与原TestFlowManager相同）
    test_started = pyqtSignal()  # 测试开始
    test_stopped = pyqtSignal()  # 测试停止
    test_progress_updated = pyqtSignal(int, dict)  # 测试进度更新
    test_completed = pyqtSignal(dict)  # 测试完成
    test_failed = pyqtSignal(str)  # 测试失败
    channel_test_completed = pyqtSignal(int, dict)  # 通道测试完成
    show_continuous_report = pyqtSignal(int, int, dict)  # 显示连续测试报告信号
    delayed_reset_requested = pyqtSignal()  # 延迟重置请求信号
    
    def __init__(self, main_window, config_manager, comm_manager, device_connection_manager):
        """
        初始化测试流程管理器适配器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
            comm_manager: 通信管理器
            device_connection_manager: 设备连接管理器
        """
        super().__init__()

        self.main_window = main_window
        self.config_manager = config_manager
        self.comm_manager = comm_manager
        self.device_connection_manager = device_connection_manager
        
        # 兼容性属性
        self.is_testing = False
        self.test_flow_controller = None
        self.test_engine = None  # 测试引擎实例

        # 修复：添加停止操作锁，防止递归调用
        import threading
        self._adapter_stop_in_progress = False
        self._adapter_stop_lock = threading.Lock()

        # 修复初始化数据上传管理器引用
        self._data_upload_manager = None
        self._pending_upload_manager = None
        
        # 初始化重构后的6个管理器
        self._init_refactored_managers()
        
        # 电池码管理器（保持原有功能）
        self.battery_code_manager = BatteryCodeManager(config_manager, main_window)
        self._init_battery_code_manager_connections()
        
        # 设置延迟重试定时器（防止初始化时序问题）
        # 优化不立即尝试设置，直接使用延迟设置避免初始化警告
        self._setup_channels_container_timer = QTimer()
        self._setup_channels_container_timer.setSingleShot(True)
        self._setup_channels_container_timer.timeout.connect(self._setup_channels_container)
        self._setup_channels_container_timer.start(1000)  # 1秒后设置，避免初始化时序问题
        
        # 连接连续测试报告信号
        self.show_continuous_report.connect(self._do_show_continuous_test_report_signal)

        # 连接延迟重置信号
        self.delayed_reset_requested.connect(self._handle_delayed_reset)

        logger.debug("测试流程管理器适配器初始化完成")

    def set_data_upload_manager(self, upload_manager):
        """
        设置数据上传管理器

        Args:
            upload_manager: 数据上传管理器实例
        """
        try:
            # 修复永久保存数据上传管理器引用，不要清除
            self._data_upload_manager = upload_manager
            self._pending_upload_manager = upload_manager

            # 尝试立即设置到流程控制器的测试结果管理器
            if hasattr(self.flow_controller, 'test_result_manager') and self.flow_controller.test_result_manager:
                self.flow_controller.test_result_manager.set_data_upload_manager(upload_manager)
                logger.info("✅ 数据上传管理器已设置到测试结果管理器")
                # 修复不要清除引用，保持用于后续测试
                # self._pending_upload_manager = None  # 不清除，保持引用
            else:
                logger.debug("⚠️ 测试结果管理器未找到，将在测试引擎初始化后重试")
        except Exception as e:
            logger.error(f"❌ 设置数据上传管理器失败: {e}")

    def _setup_pending_upload_manager(self):
        """设置待处理的数据上传管理器"""
        # 修复使用永久保存的数据上传管理器引用
        upload_manager = getattr(self, '_data_upload_manager', None) or getattr(self, '_pending_upload_manager', None)

        if upload_manager:
            try:
                logger.debug(f" [适配器] 开始设置数据上传管理器到新的测试引擎: {upload_manager is not None}")

                # 检查测试引擎是否已初始化
                if hasattr(self, 'test_engine') and self.test_engine:
                    # 获取测试引擎中的测试流程控制器
                    if hasattr(self.test_engine, 'test_flow_controller') and self.test_engine.test_flow_controller:
                        # 直接设置到测试流程控制器
                        self.test_engine.test_flow_controller.set_data_upload_manager(upload_manager)
                        logger.info("✅ 延迟设置数据上传管理器成功")
                        # 修复不清除引用，保持用于后续测试
                        # self._pending_upload_manager = None
                        return True

                    # 兼容旧版本：尝试直接访问flow_controller
                    elif hasattr(self.test_engine, 'flow_controller') and self.test_engine.flow_controller:
                        if hasattr(self.test_engine.flow_controller, 'set_data_upload_manager'):
                            self.test_engine.flow_controller.set_data_upload_manager(upload_manager)
                            logger.info("✅ 延迟设置数据上传管理器成功（兼容模式）")
                            # 修复不清除引用，保持用于后续测试
                            # self._pending_upload_manager = None
                            return True
                        elif hasattr(self.test_engine.flow_controller, 'test_result_manager'):
                            test_result_manager = self.test_engine.flow_controller.test_result_manager
                            if test_result_manager:
                                test_result_manager.set_data_upload_manager(upload_manager)
                                logger.info("✅ 延迟设置数据上传管理器成功（直接模式）")
                                # 修复不清除引用，保持用于后续测试
                                # self._pending_upload_manager = None
                                return True

                logger.warning("⚠️ 测试流程控制器仍未找到，继续等待")
                return False
            except Exception as e:
                logger.error(f"❌ 延迟设置数据上传管理器失败: {e}")
                return False
        else:
            logger.warning("⚠️ 没有找到待设置的数据上传管理器")
        return True

    def _init_refactored_managers(self):
        """初始化重构后的6个管理器"""
        try:
            
            # 1. 创建核心流程控制器
            self.flow_controller = TestFlowController(self.config_manager, self.comm_manager)

            # 🔥 设置主窗口引用（用于自动打印）
            self.flow_controller.main_window = self.main_window
            
            # 2. 创建预检查管理器
            self.precheck_manager = TestPreCheckManager(
                self.main_window, self.config_manager, 
                self.comm_manager, self.device_connection_manager
            )
            
            # 3. 创建配置管理器
            self.configuration_manager = TestConfigurationManager(
                self.config_manager, self.comm_manager
            )
            
            # 4. 创建统计管理器
            self.statistics_manager = TestStatisticsManager(self.config_manager)
            
            # 5. 创建UI更新管理器
            self.ui_update_manager = TestUIUpdateManager(self.main_window, self.config_manager)
            
            # 6. 创建错误处理器
            self.error_handler = TestErrorHandler(self.main_window, self.config_manager)
            
            # 设置管理器之间的依赖关系
            self.flow_controller.set_managers(
                self.precheck_manager,
                self.configuration_manager,
                self.statistics_manager,
                self.ui_update_manager,
                self.error_handler
            )
            
            # 连接信号
            self._connect_manager_signals()
            
            logger.debug("✅ 重构后的管理器初始化完成")
            
        except Exception as e:
            logger.error(f"❌ 初始化重构管理器失败: {e}")
            raise
    
    def _connect_manager_signals(self):
        """连接管理器信号"""
        try:
            # 连接流程控制器信号
            self.flow_controller.test_started.connect(self.test_started)
            self.flow_controller.test_stopped.connect(self.test_stopped)
            
            # 连接统计管理器信号
            self.statistics_manager.test_completed.connect(self.test_completed)
            
            # 连接错误处理器信号
            self.error_handler.error_occurred.connect(self._on_error_occurred)
            
            logger.debug("管理器信号连接完成")
            
        except Exception as e:
            logger.error(f"连接管理器信号失败: {e}")
    
    def _init_battery_code_manager_connections(self):
        """初始化电池码管理器信号连接"""
        try:
            self.battery_code_manager.codes_ready.connect(self._on_battery_codes_ready)
            self.battery_code_manager.error_occurred.connect(self._on_battery_code_error)
            logger.debug("电池码管理器信号连接完成")
            
        except Exception as e:
            logger.error(f"初始化电池码管理器连接失败: {e}")
    
    def _setup_channels_container(self):
        """设置通道容器组件"""
        try:
            # 检查电池码管理器是否已有通道容器
            if self.battery_code_manager.channels_container is not None:
                logger.debug("通道容器已设置，跳过重复设置")
                return
            
            # 从主界面获取通道容器组件
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                channels_container = ui_manager.get_component('channels_container')
                
                if channels_container:
                    self.battery_code_manager.set_channels_container(channels_container)
                    logger.info("✅ 通道容器组件已设置到电池码管理器")
                    
                    # 验证设置是否成功
                    if hasattr(channels_container, 'set_channel_battery_code'):
                        logger.info("✅ 通道容器支持电池码设置功能")
                    else:
                        logger.warning("⚠️ 通道容器不支持电池码设置功能")
                    
                    # 停止重试定时器
                    if hasattr(self, '_setup_channels_container_timer'):
                        self._setup_channels_container_timer.stop()
                
                else:
                    logger.debug("通道容器组件尚未创建，等待UI初始化完成")
            else:
                logger.debug("UI组件管理器尚未初始化，等待主界面初始化完成")
                
        except Exception as e:
            logger.error(f"❌ 设置通道容器组件失败: {e}")
    
    # ===== 兼容性接口方法 =====

    def _get_main_window(self):
        """获取主窗口实例"""
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'unified_test_controller'):
                        return widget
            return None
        except Exception as e:
            logger.error(f"获取主窗口失败: {e}")
            return None

    def start_test(self) -> bool:
        """
        开始测试（兼容性接口）

        Returns:
            是否启动成功
        """
        try:
            # 修复检查是否已经使用统一测试控制器启动
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, 'unified_test_controller') and main_window.unified_test_controller:
                if hasattr(main_window.unified_test_controller, '_current_state') and main_window.unified_test_controller._current_state == 'running':
                    logger.info("🔄 统一测试控制器已在运行，跳过测试流程管理器适配器启动")
                    return True  # 返回True表示测试已经在运行

            # 使用流程控制器启动测试
            success = self.flow_controller.start_test()

            if success:
                self.is_testing = True
                # 获取电池码（扫码或自动生成）
                if not self._get_battery_codes():
                    self.flow_controller.stop_test()
                    self.is_testing = False
                    return False

            return success

        except Exception as e:
            logger.error(f"启动测试失败: {e}")
            return False
    
    def stop_test(self):
        """停止测试（兼容性接口）"""
        # 修复：使用线程锁防止重复执行
        with self._adapter_stop_lock:
            if self._adapter_stop_in_progress:
                logger.warning("🛑 测试流程管理器适配器停止操作已在进行中，跳过重复调用")
                return

            self._adapter_stop_in_progress = True

        try:
            logger.info("🛑 测试流程管理器适配器开始停止测试...")

            # 修复1立即设置停止标志，防止新的测试启动
            self.is_testing = False

            # 修复2立即停止设备测试（最高优先级）
            self._stop_device_immediately()

            # 修复3停止测试引擎（包含设备停止指令）
            if hasattr(self, 'test_engine') and self.test_engine:
                logger.info("🛑 正在停止测试引擎...")
                self.test_engine.stop_test()
                logger.info("✅ 测试引擎停止完成")
            else:
                logger.warning("⚠️ 测试引擎不存在，跳过测试引擎停止")

            # 修复4停止流程控制器
            logger.info("🛑 正在停止流程控制器...")
            self.flow_controller.stop_test()
            logger.info("✅ 流程控制器停止完成")

            # 修复5停止电池码管理器
            if hasattr(self, 'battery_code_manager') and self.battery_code_manager:
                try:
                    if hasattr(self.battery_code_manager, 'stop_scanning'):
                        self.battery_code_manager.stop_scanning()
                        logger.info("✅ 电池码扫描已停止")
                except Exception as e:
                    logger.error(f"停止电池码管理器失败: {e}")

            # 修复6清理UI状态，重置通道显示
            logger.info("🛑 正在清理UI状态...")
            self._cleanup_ui_state()

            # 修复7发送测试停止信号
            self.test_stopped.emit()
            logger.info("✅ 测试停止信号已发送")

            logger.info("🎉 测试流程管理器适配器停止测试完成")

        except Exception as e:
            logger.error(f"❌ 停止测试失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

            # 确保状态重置
            self.is_testing = False
        finally:
            # 修复：确保停止标志被重置
            with self._adapter_stop_lock:
                self._adapter_stop_in_progress = False

    def _stop_device_immediately(self):
        """立即停止设备测试（最高优先级）"""
        try:
            logger.info("🛑 立即停止设备测试...")

            if hasattr(self, 'comm_manager') and self.comm_manager:
                # 停止所有通道的测试
                all_channels = list(range(8))  # 0-7对应通道1-8
                stop_success = self.comm_manager.stop_impedance_measurement(all_channels)
                if stop_success:
                    logger.info("✅ 设备测试已成功停止")
                else:
                    logger.warning("⚠️ 设备测试停止失败，但停止信号已发送")
            else:
                logger.warning("⚠️ 通信管理器不可用，无法停止设备")

        except Exception as e:
            logger.error(f"停止设备测试失败: {e}")
    
    def _get_battery_codes(self) -> bool:
        """获取电池码（扫码或自动生成）"""
        try:
            
            # 获取启用的通道
            enabled_channels = self.configuration_manager.get_enabled_channels()
            
            if not enabled_channels:
                logger.warning("没有启用的通道")
                return True  # 没有通道也算成功
            
            # 显示模式信息
            mode_desc = self.battery_code_manager.get_mode_description()
            logger.info(f"电池码获取模式: {mode_desc}")
            
            # 启动电池码获取（异步操作）
            success = self.battery_code_manager.get_battery_codes(enabled_channels)
            
            if not success:
                logger.error("启动电池码获取失败")
                return False
            
            # 异步操作，返回True表示启动成功
            # 实际结果通过信号回调处理
            return True
            
        except Exception as e:
            logger.error(f"获取电池码失败: {e}")
            return False
    
    # ===== 信号回调方法 =====
    
    def _on_battery_codes_ready(self, battery_codes: List[str]):
        """电池码准备就绪回调"""
        try:
            logger.info(f"✅ 电池码获取完成: {battery_codes}")

            # 关键修复立即启动实际的测试引擎
            self._start_actual_test(battery_codes)

        except Exception as e:
            logger.error(f"处理电池码就绪回调失败: {e}")
            # 如果处理失败，停止测试
            self.flow_controller.stop_test()

    def _start_actual_test(self, battery_codes: List[str]):
        """启动实际的测试流程"""
        try:
            logger.info("🚀 启动实际测试流程...")

            # 获取启用的通道
            enabled_channels = self.configuration_manager.get_enabled_channels()

            # 设置批次信息
            batch_info = {
                'battery_codes': battery_codes,
                'enabled_channels': enabled_channels,
                'test_start_time': self.statistics_manager.get_statistics().get('test_start_time')
            }
            self.set_batch_info(batch_info)

            # 启动测试引擎
            success = self._start_test_engine(batch_info, battery_codes)

            if success:
                # 发送测试开始信号
                self.test_started.emit()
                logger.info("✅ 实际测试流程启动完成")
                # 显示状态消息
                self.ui_update_manager.show_test_status_message("测试已开始，电池码获取完成", "success")
            else:
                logger.error("❌ 测试引擎启动失败")
                self.error_handler.handle_error("启动测试引擎失败", "测试引擎无法启动", "test")
                self.flow_controller.stop_test()

        except Exception as e:
            logger.error(f"启动实际测试流程失败: {e}")
            self.error_handler.handle_error("启动测试失败", str(e), "test")
            self.flow_controller.stop_test()

    def _start_test_engine(self, batch_info: Dict[str, Any], battery_codes: List[str]) -> bool:
        """启动测试引擎（异步方式避免UI卡死）"""
        try:

            # 修复使用QTimer异步启动，避免UI卡死
            from PyQt5.QtCore import QTimer

            def async_start_test():
                try:
                    # 创建TestEngineAdapter实例
                    from backend.test_engine_adapter import TestEngineAdapter
                    from data.database_manager import DatabaseManager

                    # 获取数据库路径
                    db_path = self.config_manager.get('database.path', 'data/test_results.db')
                    logger.debug(f"数据库路径: {db_path}")

                    # 创建数据库管理器
                    db_manager = DatabaseManager(db_path)

                    # 创建测试引擎适配器
                    self.test_engine = TestEngineAdapter(
                        config_manager=self.config_manager,
                        db_manager=db_manager,
                        comm_manager=self.comm_manager
                    )

                    # 设置回调函数
                    self.test_engine.set_status_callback(self._on_test_engine_status)
                    self.test_engine.set_progress_callback(self._on_test_engine_progress)
                    self.test_engine.set_result_callback(self._on_test_engine_result)

                    # 修复设置连续测试状态回调
                    if hasattr(self.test_engine, 'test_flow_controller') and self.test_engine.test_flow_controller:
                        if hasattr(self.test_engine.test_flow_controller, 'test_executor'):
                            test_executor = self.test_engine.test_flow_controller.test_executor
                            if hasattr(test_executor, 'set_status_callback'):
                                test_executor.set_status_callback(self._on_continuous_test_status)
                                logger.info("✅ 连续测试状态回调已设置")

                    # 新增设置待处理的数据上传管理器
                    self._setup_pending_upload_manager()

                    # 修复使用线程启动批次测试，避免阻塞
                    import threading

                    # 保存引用避免线程中访问问题
                    test_engine_ref = self.test_engine

                    def run_test():
                        try:
                            success = test_engine_ref.start_batch_test(batch_info, battery_codes)
                            if success:
                                logger.info("✅ 测试引擎启动成功")
                            else:
                                logger.error("❌ 测试引擎启动失败")
                        except Exception as e:
                            logger.error(f"线程中启动测试失败: {e}")

                    test_thread = threading.Thread(target=run_test, daemon=True)
                    test_thread.start()

                    logger.info("✅ 测试引擎异步启动完成")

                except Exception as e:
                    logger.error(f"异步启动测试引擎失败: {e}")
                    import traceback
                    logger.error(f"详细错误信息: {traceback.format_exc()}")

            # 使用QTimer延迟执行，确保UI响应
            QTimer.singleShot(100, async_start_test)

            # 立即返回True，表示启动请求已接受
            return True

        except Exception as e:
            logger.error(f"启动测试引擎失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False

    def _on_test_engine_status(self, is_testing: bool):
        """测试引擎状态回调"""
        try:
            logger.debug(f"测试引擎状态: {'测试中' if is_testing else '空闲'}")
            self.ui_update_manager.update_test_control_status(is_testing)

            # 关键修复当测试完成时，通知测试流程控制器重置状态
            if not is_testing and self.test_flow_controller:
                logger.debug(f" 测试完成，通知测试流程控制器重置状态")
                self.test_flow_controller.stop_test()
                logger.debug("✅ 测试流程控制器状态已重置")

        except Exception as e:
            logger.error(f"处理测试引擎状态回调失败: {e}")

    def _on_continuous_test_status(self, status_data: dict):
        """连续测试状态回调"""
        try:
            action = status_data.get('action', '')

            if action == 'continuous_test_completed':
                self._handle_continuous_test_completed(status_data)
            elif action == 'continuous_test_stopped':
                self._handle_continuous_test_stopped(status_data)
            elif action == 'continuous_test_count_updated':
                self._handle_continuous_test_count_updated(status_data)
            elif action == 'continuous_test_started':
                self._handle_continuous_test_started(status_data)
            elif action == 'test_completed':
                # 关键修复处理单次测试完成状态
                self._handle_single_test_completed(status_data)
            else:
                logger.debug(f"未处理的连续测试状态: {action}")

        except Exception as e:
            logger.error(f"处理连续测试状态回调失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _handle_single_test_completed(self, status_data: dict):
        """处理单次测试完成"""
        try:
            logger.debug(f" 单次测试完成，通知测试流程控制器重置状态")

            # 关键修复使用信号槽机制确保在主线程中重置状态
            # 发射延迟重置信号，由主线程处理
            self.delayed_reset_requested.emit()
            logger.debug("✅ 已发射延迟重置信号，将在主线程中处理")

            # 发送测试完成信号
            self.test_completed.emit(status_data)
            logger.debug("✅ 测试完成信号已发送")

        except Exception as e:
            logger.error(f"处理单次测试完成失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _handle_delayed_reset(self):
        """处理延迟重置请求（在主线程中执行）"""
        try:

            # 1. 重置UI层的测试流程控制器
            if hasattr(self, 'flow_controller') and self.flow_controller:
                self.flow_controller.stop_test()
                logger.debug("✅ 延迟重置：UI层测试流程控制器状态已重置")
            else:
                logger.warning("⚠️ 延迟重置：UI层测试流程控制器未找到")

            # 2. 重置后端的测试流程控制器
            if hasattr(self, 'test_engine') and self.test_engine:
                if hasattr(self.test_engine, 'test_flow_controller') and self.test_engine.test_flow_controller:
                    self.test_engine.test_flow_controller.stop_test()
                    logger.debug("✅ 延迟重置：后端测试流程控制器状态已重置")
                else:
                    logger.warning("⚠️ 延迟重置：后端测试引擎中没有测试流程控制器")
            else:
                logger.warning("⚠️ 延迟重置：测试引擎未初始化")


        except Exception as e:
            logger.error(f"主线程延迟重置失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _handle_continuous_test_completed(self, status_data: dict):
        """处理连续测试完成"""
        try:
            count = status_data.get('count', 0)
            max_count = status_data.get('max_count', 0)
            statistics = status_data.get('statistics', {})

            logger.info(f"连续测试已完成: 总共{count}次，达到最大限制{max_count}次")

            # 显示详细的连续测试报告
            self._show_continuous_test_report(count, max_count, statistics)

        except Exception as e:
            logger.error(f"处理连续测试完成失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _handle_continuous_test_stopped(self, status_data: dict):
        """处理连续测试停止"""
        try:
            count = status_data.get('count', 0)
            statistics = status_data.get('statistics', {})

            logger.info(f"连续测试已停止: 总共完成{count}次")

            # 如果连续测试有数据，也显示报告
            if count > 0 and statistics.get('test_results'):
                self._show_continuous_test_report(count, 0, statistics)
            else:
                logger.info("连续测试停止，无测试数据生成报告")

        except Exception as e:
            logger.error(f"处理连续测试停止失败: {e}")

    def _handle_continuous_test_count_updated(self, status_data: dict):
        """处理连续测试计数更新"""
        try:
            count = status_data.get('count', 0)
            max_count = status_data.get('max_count', 0)

            logger.info(f"连续测试计数更新: {count}/{max_count}")
            # 这里可以更新UI显示

        except Exception as e:
            logger.error(f"处理连续测试计数更新失败: {e}")

    def _handle_continuous_test_started(self, status_data: dict):
        """处理连续测试启动"""
        try:
            count = status_data.get('count', 0)
            max_count = status_data.get('max_count', 0)

            logger.info(f"连续测试已启动: 当前{count}次，最大{max_count}次")
            # 这里可以更新UI显示

        except Exception as e:
            logger.error(f"处理连续测试启动失败: {e}")

    def _show_continuous_test_report(self, count: int, max_count: int, statistics: dict):
        """显示连续测试报告（使用信号机制）"""
        try:

            # 使用信号机制确保在主线程中执行
            self.show_continuous_report.emit(count, max_count, statistics)

        except Exception as e:
            logger.error(f"显示连续测试报告失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _do_show_continuous_test_report_signal(self, count: int, max_count: int, statistics: dict):
        """实际显示连续测试报告（信号槽方法）"""
        try:

            # 准备报告数据
            report_data = {
                'total_cycles': count,
                'max_count': max_count,
                'start_time': statistics.get('start_time', ''),
                'end_time': statistics.get('end_time', ''),
                'cycle_times': statistics.get('cycle_times', []),
                'test_results': statistics.get('test_results', [])
            }


            try:
                from ui.continuous_test_report_dialog import ContinuousTestReportDialog

                # 在主线程中创建并显示报告对话框
                report_dialog = ContinuousTestReportDialog(self.main_window, report_data)
                report_dialog.exec_()

                logger.info("连续测试报告对话框已显示")

            except ImportError as e:
                logger.error(f"导入连续测试报告对话框失败: {e}")
                # 显示简单的消息框作为备选方案
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(
                    self.main_window,
                    "连续测试完成",
                    f"连续测试已完成！\n总轮数: {count}\n开始时间: {statistics.get('start_time', '')}\n结束时间: {statistics.get('end_time', '')}"
                )
            except Exception as e:
                logger.error(f"显示连续测试报告对话框失败: {e}")
                import traceback
                logger.error(f"详细错误信息: {traceback.format_exc()}")

                # 显示错误消息
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self.main_window,
                    "报告显示失败",
                    f"连续测试已完成，但报告显示失败:\n{str(e)}"
                )

        except Exception as e:
            logger.error(f"显示连续测试报告失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _on_test_engine_progress(self, channel_num: int, progress_data: Dict[str, Any]):
        """测试引擎进度回调（线程安全）"""
        try:
            logger.debug(f"通道{channel_num}进度更新: {progress_data}")

            # 使用Qt的线程安全信号机制来更新UI
            # 这样可以确保UI更新在主线程中执行
            self.test_progress_updated.emit(channel_num, progress_data)

            # 🔥 新的打印机制：打印处理已移至测试结果保存时直接触发，此处不再需要复杂的信号处理

        except Exception as e:
            logger.error(f"处理测试引擎进度回调失败: {e}")

    def _on_test_engine_result(self, channel_num: int, result_data: Dict[str, Any]):
        """测试引擎结果回调（线程安全）"""
        try:
            logger.info(f"通道{channel_num}测试完成: {result_data}")

            # 修复禁用TestStatisticsManager的统计更新，避免与UI组件管理器重复
            # self.statistics_manager.add_test_result(channel_num, result_data)

            # 使用Qt的线程安全信号机制来更新UI
            # 这样可以确保UI更新在主线程中执行
            self.channel_test_completed.emit(channel_num, result_data)

        except Exception as e:
            logger.error(f"处理测试引擎结果回调失败: {e}")
    
    def _on_battery_code_error(self, error_message: str):
        """电池码获取错误回调"""
        try:
            logger.error(f"❌ 电池码获取失败: {error_message}")
            self.error_handler.handle_error("电池码获取失败", error_message, "test")
            
        except Exception as e:
            logger.error(f"处理电池码错误回调失败: {e}")
    
    def _on_error_occurred(self, title: str, message: str):
        """错误发生回调"""
        try:
            logger.error(f"测试流程错误: {title} - {message}")
            self.test_failed.emit(f"{title}: {message}")

        except Exception as e:
            logger.error(f"处理错误回调失败: {e}")

    def _cleanup_ui_state(self):
        """清理UI状态，重置通道显示"""
        try:
            logger.info("🧹 开始清理UI状态...")

            # 1. 停止所有通道的UI显示
            if hasattr(self, 'ui_update_manager') and self.ui_update_manager:
                logger.info("🛑 停止所有通道测试显示...")
                # 重置所有通道显示状态
                self.ui_update_manager.reset_all_channels_display()

            # 2. 重置测试控制按钮状态
            if hasattr(self, 'ui_update_manager') and self.ui_update_manager:
                logger.info("🔄 重置测试控制按钮状态...")
                self.ui_update_manager.update_test_control_status(False)

            # 3. 清理统计数据显示
            if hasattr(self, 'statistics_manager') and self.statistics_manager:
                # 不清理统计数据，只更新UI显示状态
                pass

            logger.info("✅ UI状态清理完成")

        except Exception as e:
            logger.error(f"❌ 清理UI状态失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    

    
    # ===== 获取器方法（兼容性） =====
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.statistics_manager.get_statistics()
    
    def get_enabled_channels(self) -> List[int]:
        """获取启用的通道"""
        return self.configuration_manager.get_enabled_channels()
    
    def get_test_parameters(self) -> Dict[str, Any]:
        """获取测试参数"""
        return self.configuration_manager.get_test_parameters()

    def is_test_running(self) -> bool:
        """检查测试是否正在运行"""
        return self.flow_controller.is_test_running()

    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计"""
        return self.error_handler.get_error_statistics()

    def clear_statistics(self):
        """清空统计数据"""
        self.statistics_manager.clear_statistics()

    def reset_all_channels_display(self):
        """重置所有通道显示"""
        self.ui_update_manager.reset_all_channels_display()

    def update_channel_progress(self, channel_num: int, progress_data: Dict[str, Any]):
        """更新通道进度"""
        self.ui_update_manager.update_channel_progress(channel_num, progress_data)
        self.test_progress_updated.emit(channel_num, progress_data)

    def mark_channel_as_abnormal(self, channel: int, error_desc: str, error_code: str):
        """标记通道为异常状态"""
        self.ui_update_manager.mark_channel_as_abnormal(channel, error_desc, error_code)

    def add_test_result(self, channel_num: int, test_result: Dict[str, Any]):
        """添加测试结果"""
        # 修复禁用TestStatisticsManager的统计更新，避免与UI组件管理器重复
        # self.statistics_manager.add_test_result(channel_num, test_result)
        self.ui_update_manager.update_channel_test_result(channel_num, test_result)
        self.channel_test_completed.emit(channel_num, test_result)

    def set_batch_info(self, batch_info: Dict[str, Any]):
        """设置批次信息"""
        self.statistics_manager.set_batch_info(batch_info)
        self.ui_update_manager.update_batch_info_display(batch_info)

    def show_error_message(self, title: str, message: str):
        """显示错误消息"""
        self.error_handler.handle_error(title, message, "general", show_dialog=True)

    def get_yield_rate(self) -> float:
        """获取良率"""
        return self.statistics_manager.get_yield_rate()

    def validate_test_parameters(self) -> bool:
        """验证测试参数"""
        return self.configuration_manager.validate_test_parameters()

    def get_manager(self, manager_name: str):
        """
        获取指定的管理器实例

        Args:
            manager_name: 管理器名称

        Returns:
            管理器实例或None
        """
        managers = {
            'flow_controller': self.flow_controller,
            'precheck': self.precheck_manager,
            'configuration': self.configuration_manager,
            'statistics': self.statistics_manager,
            'ui_update': self.ui_update_manager,
            'error_handler': self.error_handler,
            'battery_code': self.battery_code_manager
        }
        return managers.get(manager_name)

    def cleanup(self):
        """清理资源"""
        try:
            # 停止所有定时器
            if hasattr(self, '_setup_channels_container_timer'):
                self._setup_channels_container_timer.stop()

            # 清理管理器资源
            if hasattr(self.statistics_manager, 'cleanup'):
                self.statistics_manager.cleanup()

            if hasattr(self.ui_update_manager, 'cleanup'):
                self.ui_update_manager.cleanup()

            logger.info("测试流程管理器适配器资源已清理")

        except Exception as e:
            logger.error(f"清理适配器资源失败: {e}")
