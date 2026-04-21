# -*- coding: utf-8 -*-
"""
重构后的主窗口类 - 第二版
使用新的管理器架构，将1221行的上帝类拆分为多个专门的管理器

重构说明：
- 原1221行的MainWindow已拆分为5个专门管理器
- 使用组合模式保持向后兼容性
- 遵循单一职责原则

重构后的管理器：
1. WindowLayoutManager - 窗口布局管理
2. ComponentInitializer - 组件初始化管理
3. SettingsLoader - 设置加载管理
4. EventCoordinator - 事件协调管理
5. AuthorizationManager - 授权管理

Author: Jack
Date: 2025-01-30
Version: 重构版本 - 拆分为5个专门管理器
"""

import logging
import os
import time
from datetime import datetime
from typing import Optional
from PyQt5.QtWidgets import QMainWindow, QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

logger = logging.getLogger(__name__)

# 导入重构后的管理器
from ui.main_window_managers import (
    WindowLayoutManager,
    ComponentInitializer,
    SettingsLoader,
    EventCoordinator,
    AuthorizationManager
)

# 导入统一的失败结果显示工具类
from ui.utils.fail_result_display_utils import FailResultDisplayUtils


class MainWindow(QMainWindow):
    """
    重构后的主窗口类 - 第二版

    职责：
    - 各个管理器的协调和集成
    - 统一的事件处理接口
    - 兼容性保证

    重构说明：
    - 原1221行的上帝类已拆分为5个专门管理器
    - 使用组合模式保持向后兼容性
    - 遵循单一职责原则
    """

    # 信号定义
    config_changed = pyqtSignal(str, object)  # 配置变更信号
    test_started = pyqtSignal()  # 测试开始信号
    test_stopped = pyqtSignal()  # 测试停止信号

    def __init__(self, config_manager, database_manager=None, parent=None):
        """
        初始化重构后的主窗口

        Args:
            config_manager: 配置管理器
            database_manager: 数据库管理器
            parent: 父窗口
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.database_manager = database_manager
        self.is_testing = False

        # 修复：添加主窗口停止操作锁，防止递归调用
        import threading
        self._main_window_stop_in_progress = False
        self._main_window_stop_lock = threading.Lock()

        # 🚀 阶段3优化：初始化统一服务架构
        self._initialize_unified_services()

        # 初始化重构后的5个管理器
        self._initialize_refactored_managers()

        # 初始化通信管理器
        self.component_initializer.initialize_communication_manager()

        # 初始化其他管理器
        self.component_initializer.initialize_ui_managers()
        self.component_initializer.initialize_device_managers()
        self.component_initializer.initialize_printer_managers()

        # 🔥 初始化新的自动打印管理器（将被统一打印服务替代）
        self._initialize_auto_print_manager()

        # 初始化数据上传管理器（不立即启动服务）
        self.component_initializer.initialize_data_upload_manager()

        # 初始化心跳管理器（不立即启动服务）
        self.component_initializer.initialize_heartbeat_manager()

        # 将数据上传管理器设置到测试流程管理器
        self._setup_data_upload_integration()

        # 🚀 性能优化：延迟启动网络服务，避免初始化时卡顿
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, self._start_network_services_delayed)  # 减少到2秒，加快启动

        # 初始化设置同步管理器
        self._initialize_settings_sync_manager()

        # 设置电池检测回调
        self._setup_battery_detection_callbacks()

        # 初始化界面
        self._init_ui()

        # 加载启动设置
        self.settings_loader.load_startup_settings()

        # 尝试自动连接设备
        self._try_auto_connect()

        logger.debug("重构后的主窗口初始化完成")

        # 标记初始化完成，允许处理电池插入事件
        self._initialization_complete = True

        # 添加电池检测模式状态管理
        self._battery_detection_active = False  # 电池检测模式是否已激活（首次手动启动后）
        self._battery_detection_test_completed = False  # 测试是否已完成
        self._waiting_for_battery_removal = False  # 等待电池移除状态
        self._all_batteries_removed = False  # 所有电池都已移除
        self._user_manual_stop_battery_detection = False  # 用户是否手动停止了电池侦测模式

        print("🎯 主窗口初始化完成，准备显示窗口...")

        # 延迟检查授权状态（确保UI组件已完全初始化）
        QTimer.singleShot(1000, self.authorization_manager.check_license_on_startup)

        #
        self._init_window_monitor()

    def _start_network_services_delayed(self):
        """🚀 延迟启动网络服务（性能优化）"""
        try:
            logger.info("🚀 开始延迟启动网络服务...")

            # 启动数据上传服务
            if hasattr(self, 'data_upload_manager') and self.data_upload_manager:
                self.data_upload_manager.start_services_delayed()

            # 启动心跳服务（如果需要且数据上传已启用）
            if hasattr(self, 'heartbeat_manager') and self.heartbeat_manager:
                heartbeat_config = self.heartbeat_manager.heartbeat_config
                data_upload_enabled = self.config_manager.get('data_upload.enabled', False)
                if heartbeat_config.get('enabled', False) and data_upload_enabled:
                    self.heartbeat_manager.start()
                    logger.info("✅ 心跳服务已启动")
                else:
                    logger.info("心跳服务未启动：数据上传功能已禁用")

            logger.info("✅ 网络服务延迟启动完成")

        except Exception as e:
            logger.error(f"延迟启动网络服务失败: {e}")

    def _init_window_monitor(self):
        """初始化窗口状态监控定时器"""
        try:
            # 创建定时器监控窗口状态
            self.window_monitor_timer = QTimer()
            self.window_monitor_timer.timeout.connect(self._check_window_status)
            self.window_monitor_timer.start(5000)  # 每5秒检查一次
            logger.info("✅ 窗口状态监控定时器已启动")
        except Exception as e:
            logger.error(f"❌ 初始化窗口监控失败: {e}")

    def _check_window_status(self):
        """检查窗口状态"""
        try:
            # 在应用程序关闭时不进行窗口状态检查
            if hasattr(self, '_is_closing') and self._is_closing:
                return

            # 只在窗口意外隐藏时才恢复（排除最小化的正常情况）
            if self.isHidden() and not self.isMinimized():
                logger.warning(f"⚠️ 检测到窗口异常状态: hidden={self.isHidden()}, minimized={self.isMinimized()}")
                # 强制显示窗口
                self.showMaximized()
                self.raise_()
                self.activateWindow()
                logger.info(f"✅ 窗口已强制恢复显示")
        except Exception as e:
            logger.error(f"❌ 检查窗口状态失败: {e}")

    # ===== 兼容性方法 - 保持向后兼容 =====

    def _initialize_managers(self):
        """初始化各个管理器（兼容性方法 - 已重构为新的管理器架构）"""
        logger.warning("调用了已重构的_initialize_managers方法，请使用新的管理器架构")
        # 新的管理器已在__init__中初始化，此方法保留用于兼容性

    def _initialize_unified_services(self):
        """
        🚀 阶段3优化：初始化统一服务架构

        替代原有的多个重复组件，提供统一的服务接口
        """
        try:
            logger.info("🚀 开始初始化统一服务架构...")

            # 导入统一服务
            from services import (
                get_print_service, get_channel_service, get_test_controller
            )
            from core import get_event_bus, get_state_manager, get_resource_pool

            # 初始化核心服务
            self.event_bus = get_event_bus()
            self.state_manager = get_state_manager()
            self.resource_pool = get_resource_pool()

            logger.debug("✅ 核心服务初始化完成")

            # 初始化统一服务
            self.unified_print_service = get_print_service(self)
            self.unified_channel_service = get_channel_service(self)
            self.unified_test_controller = get_test_controller(self)

            logger.debug("✅ 统一服务初始化完成")

            # 设置回调函数
            if self.unified_test_controller:
                self.unified_test_controller.set_callbacks(
                    progress_callback=self._on_unified_test_progress,
                    status_callback=self._on_unified_test_status
                )

            logger.info("✅ 统一服务架构初始化完成")

        except Exception as e:
            logger.error(f"❌ 初始化统一服务架构失败: {e}")
            # 不抛出异常，允许系统继续使用原有架构
            self.unified_print_service = None
            self.unified_channel_service = None
            self.unified_test_controller = None

    def _initialize_refactored_managers(self):
        """初始化重构后的5个管理器"""
        try:

            # 1. 窗口布局管理器
            self.window_layout_manager = WindowLayoutManager(self, self.config_manager)

            # 2. 组件初始化管理器
            self.component_initializer = ComponentInitializer(self, self.config_manager, self.database_manager)

            # 3. 设置加载管理器
            self.settings_loader = SettingsLoader(self, self.config_manager)

            # 4. 事件协调器
            self.event_coordinator = EventCoordinator(self, self.config_manager)

            # 5. 授权管理器
            self.authorization_manager = AuthorizationManager(self, self.config_manager)

            logger.debug("✅ 重构后的管理器初始化完成")

        except Exception as e:
            logger.error(f"❌ 初始化重构管理器失败: {e}")
            raise

    def _initialize_auto_print_manager(self):
        """初始化新的自动打印管理器"""
        try:
            # 🔥 创建简单的自动打印管理器
            class SimpleAutoPrintManager:
                def __init__(self, main_window):
                    self.main_window = main_window
                    self._printed_test_ids = set()
                    logger.info("✅ 简单自动打印管理器初始化完成")

                def trigger_print_for_test_result(self, test_result_data):
                    """为单个测试结果触发打印"""
                    try:
                        test_id = test_result_data.get('id')
                        channel_num = test_result_data.get('channel_number')

                        logger.debug(f"🖨️ [自动打印] 收到打印请求: CH={channel_num}, ID={test_id}")

                        if not test_id or not channel_num:
                            logger.warning(f"测试结果数据不完整，跳过打印: ID={test_id}, 通道={channel_num}")
                            return

                        # Jack要求检查测试是否被停止，如果停止则不打印
                        if hasattr(self.main_window, 'test_executor') and self.main_window.test_executor:
                            if hasattr(self.main_window.test_executor, 'stop_event') and self.main_window.test_executor.stop_event.is_set():
                                logger.warning(f"🛑 通道{channel_num}测试已被停止，跳过打印，避免打印脏数据")
                                return

                        if test_id in self._printed_test_ids:
                            logger.warning(f"🖨️ [自动打印] 通道{channel_num}测试结果(ID:{test_id})已打印过，跳过")
                            return

                        # 检查是否启用自动打印
                        auto_print_enabled = self._is_auto_print_enabled()
                        logger.debug(f"🖨️ [自动打印] 通道{channel_num}自动打印启用状态: {auto_print_enabled}")
                        if not auto_print_enabled:
                            logger.warning(f"🖨️ [自动打印] 通道{channel_num}自动打印未启用，跳过")
                            return

                        # 检查打印机是否就绪
                        printer_ready = self._is_printer_ready()
                        logger.debug(f"🖨️ [自动打印] 通道{channel_num}打印机就绪状态: {printer_ready}")
                        if not printer_ready:
                            logger.warning(f"🖨️ [自动打印] 通道{channel_num}打印机未就绪，跳过打印")
                            return

                        # 检查取样测试模式
                        sampling_test = self.main_window.config_manager.get('test.sampling_test', False)
                        if sampling_test:
                            logger.info(f"🎯 通道{channel_num}取样测试模式：跳过打印")
                            return

                        # 准备打印数据
                        print_data = self._prepare_print_data(test_result_data)
                        if not print_data:
                            logger.warning(f"通道{channel_num}打印数据准备失败")
                            return

                        # 执行打印
                        logger.info(f"🖨️ [自动打印] 准备提交打印: CH={channel_num}, 数据摘要={{'V': {print_data.get('voltage', 0):.3f}V, 'Rs': {print_data.get('rs_value', 0):.3f}mΩ, 'Rct': {print_data.get('rct_value', 0):.3f}mΩ}}")
                        job_id = self.main_window.label_print_manager.print_test_result(print_data)

                        if job_id:
                            self._printed_test_ids.add(test_id)
                            logger.info(f"✅ 通道{channel_num}打印成功: Rs={print_data.get('rs_value', 0):.3f}mΩ, Rct={print_data.get('rct_value', 0):.3f}mΩ, 任务ID={job_id}")
                        else:
                            logger.error(f"❌ 通道{channel_num}打印失败")

                    except Exception as e:
                        logger.error(f"触发通道{test_result_data.get('channel_number', '?')}打印失败: {e}")

                def _is_auto_print_enabled(self):
                    """检查是否启用自动打印"""
                    try:
                        return self.main_window.label_print_manager.is_auto_print_enabled()
                    except Exception as e:
                        logger.error(f"检查自动打印状态失败: {e}")
                        return False

                def _is_printer_ready(self):
                    """检查打印机是否就绪"""
                    try:
                        return self.main_window.label_print_manager.is_printer_ready()
                    except Exception as e:
                        logger.error(f"检查打印机状态失败: {e}")
                        return False

                def _prepare_print_data(self, test_result_data):
                    """准备打印数据"""
                    try:
                        channel_num = test_result_data.get('channel_number')
                        rs_value = test_result_data.get('rs_value', 0)
                        rct_value = test_result_data.get('rct_value', 0)

                        if rs_value == 0 and rct_value == 0:
                            logger.warning(f"通道{channel_num}测试数据异常: Rs={rs_value}, Rct={rct_value}")
                            return None

                        print_data = {
                            'channel_number': channel_num,
                            'rs_value': rs_value,
                            'rct_value': rct_value,
                            'voltage': test_result_data.get('voltage', 0),
                            'rs_grade': test_result_data.get('rs_grade', 0),
                            'rct_grade': test_result_data.get('rct_grade', 0),
                            'is_pass': test_result_data.get('is_pass', False),
                            'fail_reason': test_result_data.get('fail_reason', ''),
                            'battery_code': test_result_data.get('battery_code', ''),
                            'test_time': test_result_data.get('test_time', ''),
                            'impedance_ratio': test_result_data.get('impedance_ratio', 0),
                        }

                        logger.debug(f"通道{channel_num}打印数据准备完成: Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")
                        return print_data

                    except Exception as e:
                        logger.error(f"准备通道{test_result_data.get('channel_number', '?')}打印数据失败: {e}")
                        return None

                def reset_printed_records(self):
                    """重置已打印记录"""
                    self._printed_test_ids.clear()
                    logger.info("🔄 已打印记录已重置")

                def reset_for_new_session(self):
                    """开始新的测试会话时重置自动打印去重集合"""
                    try:
                        old = len(self._printed_test_ids)
                        self._printed_test_ids.clear()
                        logger.info(f"🆕 自动打印会话已重置，清空已打印ID: {old} 个")
                    except Exception as e:
                        logger.error(f"重置自动打印会话失败: {e}")

            self.auto_print_manager = SimpleAutoPrintManager(self)
            logger.info("✅ 自动打印管理器初始化完成")
        except Exception as e:
            logger.error(f"自动打印管理器初始化失败: {e}")

    def _init_communication_manager(self):
        """初始化通信管理器"""
        try:
            from backend.communication_manager import CommunicationManager

            # 获取通信配置
            comm_config = {
                'port': self.config_manager.get('device.connection.port', 'COM16'),
                'baudrate': self.config_manager.get('device.connection.baudrate', 115200),
                'device_address': self.config_manager.get('device.connection.device_address', 1),
                'timeout': self.config_manager.get('device.connection.timeout', 2.0)
            }

            self.comm_manager = CommunicationManager(comm_config)

        except Exception as e:
            logger.error(f"初始化通信管理器失败: {e}")

    # 旧的_initialize_managers方法已被重构为新的管理器架构
    # 保留此注释以说明重构过程

    # 旧的_setup_manager_connections方法已被重构为新的管理器架构
    # 信号连接现在在component_initializer.setup_signal_connections()中处理

    def _init_ui(self):
        """初始化用户界面（使用重构后的管理器）"""
        try:
            # 1. 设置窗口属性
            self.window_layout_manager.setup_window_properties()

            # 2. 创建主布局
            main_layout = self.window_layout_manager.create_main_layout()

            # 3. 创建UI组件
            self.component_initializer.create_ui_components(main_layout)

            # 4. 创建菜单栏（需要先获取菜单管理器）
            if hasattr(self, 'menu_manager'):
                self.menu_manager.create_menu_bar()

            # 5. 应用样式
            self.window_layout_manager.apply_styles()

            # 6. 设置信号连接
            self.component_initializer.setup_signal_connections()

            # 7. 打印状态面板已移除，设备连接信息已集成到底部状态栏
            logger.debug("打印状态面板已取消，设备信息显示在底部状态栏")

            logger.debug("用户界面初始化完成")

        except Exception as e:
            logger.error(f"初始化用户界面失败: {e}")

    def _create_ui_components(self, main_layout):
        """创建UI组件"""
        try:
            # 创建精确比例布局容器
            containers = self.window_layout_manager.create_proportional_layout(main_layout)

            if not containers:
                logger.error("创建比例布局失败")
                return

            # 创建顶部标题栏（在header容器中）
            header_container = containers['header']
            self.ui_component_manager.create_header_widget_in_container(header_container)

            # 创建上层区域组件（在upper容器中）
            upper_container = containers['upper']
            upper_layout = self.window_layout_manager.create_upper_layout(upper_container)
            self.ui_component_manager.create_upper_widgets(upper_layout)

            # 设置上层区域比例
            batch_widget = self.ui_component_manager.get_component('batch_info')
            statistics_widget = self.ui_component_manager.get_component('statistics')
            control_widget = self.ui_component_manager.get_component('test_control')

            if all([batch_widget, statistics_widget, control_widget]):
                self.window_layout_manager.setup_upper_widget_proportions(
                    upper_layout, batch_widget, statistics_widget, control_widget
                )

            # 创建通道容器（分为两行）
            channels_row1_container = containers['channels_row1']
            channels_row2_container = containers['channels_row2']
            self.ui_component_manager.create_split_channels_container(
                channels_row1_container, channels_row2_container
            )

            # 创建状态栏
            self.ui_component_manager.create_status_bar()

            # 设置信号连接
            self.ui_component_manager.setup_signal_connections()

        except Exception as e:
            logger.error(f"创建UI组件失败: {e}")

    def _setup_battery_detection_callbacks(self):
        """设置电池检测回调函数"""
        try:
            # 修复：无论是否启用自动侦测模式，都设置回调函数，以便动态切换
            logger.debug("🔧 开始设置电池检测回调函数...")

            # 设置电池检测回调函数
            if hasattr(self, 'battery_detection_manager'):
                self.battery_detection_manager.set_callbacks(
                    battery_removed_callback=self._on_battery_removed,
                    new_battery_detected_callback=self._on_new_battery_detected,
                    status_update_callback=self._on_battery_status_updated
                )
                logger.info("✅ 电池检测回调函数设置完成")

                # 检查是否启用自动侦测模式，如果启用则启动检测
                auto_detect = self.config_manager.get('test.auto_detect', False)
                if auto_detect:
                    logger.info("🔋 自动侦测模式已启用，准备启动电池检测")
                else:
                    logger.info("🔋 自动侦测模式未启用，回调函数已设置但检测未启动")
            else:
                logger.warning("⚠️ 电池检测管理器未找到，跳过回调设置")
        except Exception as e:
            logger.error(f"❌ 电池检测回调设置处理失败: {e}")

    def _initialize_settings_sync_manager(self):
        """初始化设置同步管理器"""
        try:

            # 导入设置同步管理器
            from ui.main_window_settings_sync import MainWindowSettingsSync

            # 创建设置同步管理器实例
            self.settings_sync_manager = MainWindowSettingsSync(
                main_window=self,
                config_manager=self.config_manager,
                parent=self
            )

            # 连接同步完成和失败信号
            self.settings_sync_manager.sync_completed.connect(self._on_settings_sync_completed)
            self.settings_sync_manager.sync_failed.connect(self._on_settings_sync_failed)

            logger.debug("✅ 设置同步管理器初始化完成")

        except Exception as e:
            logger.error(f"❌ 初始化设置同步管理器失败: {e}")
            # 不抛出异常，避免影响主窗口初始化

    def _on_settings_sync_completed(self, message: str):
        """设置同步完成处理"""
        try:
            logger.debug(f"设置同步完成: {message}")
        except Exception as e:
            logger.error(f"处理设置同步完成失败: {e}")

    def _on_settings_sync_failed(self, sync_type: str, error_message: str):
        """设置同步失败处理"""
        try:
            logger.warning(f"设置同步失败 [{sync_type}]: {error_message}")
        except Exception as e:
            logger.error(f"处理设置同步失败失败: {e}")

    def _try_auto_connect(self):
        """尝试自动连接设备"""
        try:
            self.device_connection_manager.auto_connect()
        except Exception as e:
            logger.error(f"自动连接设备失败: {e}")

    def _load_startup_settings(self):
        """
        软件启动时加载所有设置（修复：启动时设置读取）
        """
        try:
            logger.info("开始加载启动设置...")

            # 1. 加载通道使能状态
            self._load_channel_enable_settings()

            # 2. 加载产品信息设置
            self._load_product_info_settings()

            # 3. 加载测试参数设置
            self._load_test_parameter_settings()

            # 4. 加载界面显示设置
            self._load_ui_display_settings()

            # 5. 加载离群检测设置
            self._load_outlier_detection_settings()

            # 6. 延迟初始化打印机状态显示（确保UI完全初始化后）
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self._initialize_printer_status)

            # 7. 加载历史统计数据
            self._load_historical_statistics()

            logger.info("启动设置加载完成")

        except Exception as e:
            logger.error(f"加载启动设置失败: {e}")

    def _load_channel_enable_settings(self):
        """加载通道使能状态设置"""
        try:
            # 获取启用的通道列表
            enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))

            # 更新通道容器的使能状态
            channels_container = self.ui_component_manager.get_component('channels_container')
            if channels_container:
                for channel_num in range(1, 9):
                    is_enabled = channel_num in enabled_channels
                    if hasattr(channels_container, 'set_channel_enabled'):
                        channels_container.set_channel_enabled(channel_num, is_enabled)

                logger.info(f"通道使能状态已加载: {enabled_channels}")
            else:
                logger.warning("通道容器组件未找到，无法设置通道使能状态")

        except Exception as e:
            logger.error(f"加载通道使能设置失败: {e}")

    def _load_product_info_settings(self):
        """加载产品信息设置"""
        try:
            # 更新批次信息组件
            batch_info = self.ui_component_manager.get_component('batch_info')
            if batch_info and hasattr(batch_info, 'load_settings'):
                batch_info.load_settings()
                logger.info("产品信息设置已加载")
            else:
                logger.warning("批次信息组件未找到或不支持设置加载")

        except Exception as e:
            logger.error(f"加载产品信息设置失败: {e}")

    def _load_test_parameter_settings(self):
        """加载测试参数设置"""
        try:
            # 这里可以添加测试参数的加载逻辑
            # 例如：频率设置、阻抗范围、档位配置等
            logger.debug("测试参数设置加载完成")

        except Exception as e:
            logger.error(f"加载测试参数设置失败: {e}")

    def _load_ui_display_settings(self):
        """加载界面显示设置"""
        try:
            # 这里可以添加界面显示相关的设置加载
            # 例如：主题、字体、布局等
            logger.debug("界面显示设置加载完成")

        except Exception as e:
            logger.error(f"加载界面显示设置失败: {e}")

    def _load_outlier_detection_settings(self):
        """加载离群检测设置（避免不必要的管理器创建）"""
        try:
            # 先检查配置文件，避免创建管理器实例
            outlier_enabled_in_config = self.config_manager.get('outlier_is_enabled', False)

            if not outlier_enabled_in_config:
                # 配置中已禁用，直接设置UI为禁用状态
                channels_container = self.ui_component_manager.get_component('channels_container')
                if channels_container and hasattr(channels_container, 'update_all_outlier_detection_status'):
                    channels_container.update_all_outlier_detection_status(False)
                    logger.info("离群检测设置已加载: 禁用")
                return

            # 🚫 离群检测功能已删除

        except Exception as e:
            logger.error(f"加载离群检测设置失败: {e}")

    def _initialize_printer_status(self):
        """初始化打印机状态显示"""
        try:
            # 手动触发一次打印机状态检查和UI更新
            if hasattr(self, 'printer_manager'):
                # 🔧 修复：使用同步刷新，确保状态检查完成后再更新UI
                self.printer_manager.refresh_status_sync()

                # 获取当前打印机状态
                current_status = self.printer_manager.get_current_status()
                printer_info = self.printer_manager.get_printer_status()

                # 更新UI显示
                self.ui_component_manager.update_printer_status(current_status, printer_info)

                # 🔧 修复：强制发送状态信号，确保所有UI组件都能收到状态更新
                self.printer_manager.force_emit_current_status()

                logger.info(f"✅ 打印机状态初始化完成: {'已连接' if current_status else '未连接'}")
            else:
                logger.warning("打印机管理器未找到，无法初始化打印机状态")

        except Exception as e:
            logger.error(f"初始化打印机状态失败: {e}")

    def _load_historical_statistics(self):
        """加载历史统计数据"""
        try:

            # 获取统计组件
            statistics_widget = self.ui_component_manager.get_component('statistics')
            if statistics_widget and hasattr(statistics_widget, 'refresh_statistics'):
                statistics_widget.refresh_statistics()
                logger.info("✅ 历史统计数据加载完成")
            else:
                logger.warning("⚠️ 统计组件未找到或不支持刷新功能")

        except Exception as e:
            logger.error(f"❌ 加载历史统计数据失败: {e}")

    # ===== 事件处理方法（使用事件协调器） =====

    def _on_device_connection_changed(self, connected: bool):
        """设备连接状态变更处理"""
        self.event_coordinator.handle_device_connection_changed(connected)

        # 设备连接状态变更处理
        if connected:
            # 启动电池检测（如果启用自动侦测模式）
            self._start_battery_detection_on_connection()
            self._start_heartbeat_on_connection()
        else:
            # 停止电池检测
            self._stop_battery_detection_on_disconnection()
            self._stop_heartbeat_on_disconnection()

    def _start_battery_detection_on_connection(self):
        """设备连接后启动电池检测"""
        # 检查是否启用自动侦测模式
        auto_detect = self.config_manager.get('test.auto_detect', False)
        if not auto_detect:
            logger.info("自动侦测模式未启用，跳过电池检测启动")
            return

        # 延迟启动电池检测，确保设备连接稳定
        QTimer.singleShot(3000, self._do_start_battery_detection)

    def _initialize_print_status_panel(self):
        """打印状态面板已移除，设备连接信息已集成到底部状态栏"""
        logger.info("打印状态面板功能已取消，设备连接信息显示在底部状态栏中")



    def _do_start_battery_detection(self):
        """实际启动电池检测"""
        try:
            # 检查是否启用自动侦测模式
            auto_detect = self.config_manager.get('test.auto_detect', False)
            if not auto_detect:
                logger.info("自动侦测模式未启用，跳过电池检测启动")
                return

            # 启动电池检测
            if hasattr(self, 'battery_detection_manager'):
                enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))
                self.battery_detection_manager.start_detection(enabled_channels)
                logger.info(f"✅ 设备连接后电池检测已启动，监控通道: {enabled_channels}")
            else:
                logger.warning("⚠️ 电池检测管理器未找到")

        except Exception as e:
            logger.error(f"电池检测启动处理失败: {e}")

    def _stop_battery_detection_on_disconnection(self):
        """设备断开连接后停止电池检测"""
        try:
            # 停止电池检测
            if hasattr(self, 'battery_detection_manager'):
                self.battery_detection_manager.stop_detection()
                logger.info("✅ 设备断开连接，电池检测已停止")
            else:
                logger.warning("⚠️ 电池检测管理器未找到")

        except Exception as e:
            logger.error(f"电池检测停止处理失败: {e}")

    def _start_heartbeat_on_connection(self):
        """设备连接后启动心跳服务"""
        try:
            if hasattr(self, 'heartbeat_manager') and self.heartbeat_manager:
                # 检查数据上传功能是否启用
                data_upload_enabled = self.config_manager.get('data_upload.enabled', False)
                heartbeat_enabled = self.heartbeat_manager.heartbeat_config.get('enabled', False)

                if data_upload_enabled and heartbeat_enabled:
                    # 更新设备状态为在线
                    self.heartbeat_manager.update_status('online', '设备已连接')
                    # 启动心跳服务
                    self.heartbeat_manager.start()
                    logger.info("✅ 设备连接后心跳服务已启动")
                else:
                    logger.info("设备连接后心跳服务未启动：数据上传功能已禁用")
            else:
                logger.warning("⚠️ 心跳管理器未找到")

        except Exception as e:
            logger.error(f"设备连接后启动心跳服务失败: {e}")

    def _stop_heartbeat_on_disconnection(self):
        """设备断开连接后停止心跳服务"""
        try:
            if hasattr(self, 'heartbeat_manager') and self.heartbeat_manager:
                # 更新设备状态为离线
                self.heartbeat_manager.update_status('offline', '设备已断开连接')
                logger.info("✅ 设备断开连接，心跳状态已更新为离线")

        except Exception as e:
            logger.error(f"停止心跳服务失败: {e}")

    def _on_device_info_updated(self, device_info: dict):
        """设备信息更新处理"""
        self.event_coordinator.handle_device_info_updated(device_info)

    def _on_test_started(self):
        """测试开始处理"""
        self.event_coordinator.handle_test_started()

        # 修复清理旧的打印完成标记，生成新的测试ID
        import time
        self._current_test_id = int(time.time() * 1000)  # 毫秒级时间戳
        self._test_completion_flags = set()  # 清空旧的完成标记
        logger.debug(f"测试开始，生成新的测试ID: {self._current_test_id}")

        # 🚀 阶段3优化：使用统一打印服务
        if hasattr(self, 'unified_print_service') and self.unified_print_service:
            self.unified_print_service.start_new_test_session(self._current_test_id)
        else:
            # 兼容性：使用原有的标签打印管理器
            if hasattr(self, 'label_print_manager') and self.label_print_manager:
                self.label_print_manager.start_new_test_session(self._current_test_id)

        # 同步重置自动打印会话的去重集合
        try:
            if hasattr(self, 'auto_print_manager') and self.auto_print_manager:
                self.auto_print_manager.reset_for_new_session()
        except Exception as e:
            logger.warning(f"自动打印会话重置失败: {e}")

        # 修复：只有在数据上传启用时才更新心跳状态
        data_upload_enabled = self.config_manager.get('data_upload.enabled', False)
        if (hasattr(self, 'heartbeat_manager') and self.heartbeat_manager and
            data_upload_enabled):
            self.heartbeat_manager.update_status('online', '正在进行测试')
        else:
            logger.debug("数据上传功能已禁用，跳过心跳状态更新")

    def _on_test_stopped(self):
        """测试停止处理"""
        # 修复：防止重复调用
        if hasattr(self, '_test_stop_processing') and self._test_stop_processing:
            logger.debug("测试停止处理已在进行中，跳过重复调用")
            return

        self._test_stop_processing = True

        try:
            # 修复记录测试停止时间，用于宽限期判断
            import time
            self._test_stop_time = time.time()
            logger.debug(f"记录测试停止时间: {self._test_stop_time}")

            self.event_coordinator.handle_test_stopped()

            # 修复：只有在心跳功能启用且数据上传启用时才更新心跳状态
            data_upload_enabled = self.config_manager.get('data_upload.enabled', False)
            if (hasattr(self, 'heartbeat_manager') and self.heartbeat_manager and
                data_upload_enabled and self.heartbeat_manager.heartbeat_config.get('enabled', False)):
                # 使用异步方式更新心跳状态，避免阻塞界面
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(100, lambda: self._update_heartbeat_status_async('online', '测试已停止，系统就绪'))
            else:
                logger.debug("心跳功能已禁用，跳过心跳状态更新")

        finally:
            # 延迟重置处理标志
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(2000, lambda: setattr(self, '_test_stop_processing', False))

    def _update_heartbeat_status_async(self, status: str, message: str):
        """异步更新心跳状态，避免阻塞界面"""
        try:
            # 再次检查数据上传是否启用
            data_upload_enabled = self.config_manager.get('data_upload.enabled', False)
            if not data_upload_enabled:
                logger.debug("数据上传功能已禁用，跳过异步心跳状态更新")
                return

            if hasattr(self, 'heartbeat_manager') and self.heartbeat_manager:
                self.heartbeat_manager.update_status(status, message)
        except Exception as e:
            logger.debug(f"异步更新心跳状态失败: {e}")

    def _on_test_progress_updated(self, channel_num: int, progress_data: dict):
        """测试进度更新处理"""
        self.event_coordinator.handle_test_progress_updated(channel_num, progress_data)

    def _on_test_failed(self, error_message: str):
        """测试失败处理"""
        self.event_coordinator.handle_test_failed(error_message)

    def _on_component_ready(self, component_name: str):
        """组件就绪处理"""
        self.event_coordinator.handle_component_ready(component_name)

    # ===== 🚀 阶段3优化：统一服务回调方法 =====

    def _on_unified_test_progress(self, progress_data: dict):
        """
        统一测试控制器进度回调

        Args:
            progress_data: 进度数据
        """
        try:
            channel_num = progress_data.get('channel_num')
            progress = progress_data.get('progress', 0)
            status = progress_data.get('status', '')

            logger.debug(f"🔄 统一测试进度更新: 通道{channel_num}, 进度{progress}%, 状态: {status}")

            # 更新UI显示
            if hasattr(self, 'test_control_widget') and self.test_control_widget:
                # 这里可以更新测试控制组件的进度显示
                pass

        except Exception as e:
            logger.error(f"❌ 处理统一测试进度回调失败: {e}")

    def _on_unified_test_status(self, status_data: dict):
        """
        统一测试控制器状态回调

        Args:
            status_data: 状态数据
        """
        try:
            test_state = status_data.get('test_state', 'unknown')
            message = status_data.get('message', '')

            logger.info(f"🔄 [统一测试状态] 收到状态更新: {test_state} - {message}")
            logger.info(f"🔋 [统一测试状态] 当前电池侦测状态: _battery_detection_active={getattr(self, '_battery_detection_active', 'NOT_SET')}")

            # 更新主窗口测试状态
            if test_state in ['running', 'preparing']:
                self.is_testing = True
            elif test_state in ['idle', 'completed', 'failed', 'error']:
                # 🔧 [关键修复] 在设置is_testing=False之前记录测试停止时间，确保宽限期逻辑正常工作
                if self.is_testing and test_state == 'completed':
                    import time
                    self._test_stop_time = time.time()
                    logger.info(f"🔧 [测试完成] 记录测试停止时间: {self._test_stop_time}，允许5秒宽限期完成数据保存")

                self.is_testing = False

                # 🔋 关键修复：测试完成时启动电池移除监控
                if test_state == 'completed':
                    logger.info("🔋 [统一测试状态] 统一测试控制器测试完成，检查是否需要启动电池移除监控")

                    # 检查是否为自动侦测模式
                    auto_detect = self.config_manager.get('test.auto_detect', False)
                    continuous_mode = self.config_manager.get('test.continuous_mode', False)
                    battery_detection_active = getattr(self, '_battery_detection_active', False)

                    logger.info(f"🔋 [统一测试状态] 配置检查: auto_detect={auto_detect}, continuous_mode={continuous_mode}, _battery_detection_active={battery_detection_active}")

                    if auto_detect and not continuous_mode and battery_detection_active:
                        logger.info("✅ [统一测试状态] 自动侦测模式：测试完成，延迟执行完整测试重置（确保打印完成）")
                        # 🔧 Jack修复：延迟执行自动侦测模式重置，给打印流程足够时间完成
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(3000, self._complete_auto_detect_test_reset_delayed)
                        logger.info("✅ [统一测试状态] 自动侦测模式：已安排延迟重置（3秒后执行），确保打印流程完成")
                    else:
                        logger.info(f"ℹ️ [统一测试状态] 跳过电池移除监控启动 - auto_detect={auto_detect}, continuous_mode={continuous_mode}, battery_detection_active={battery_detection_active}")

            # 更新UI状态
            if hasattr(self, 'test_control_widget') and self.test_control_widget:
                # 这里可以更新测试控制组件的状态显示
                pass

        except Exception as e:
            logger.error(f"❌ 处理统一测试状态回调失败: {e}")

    def _on_component_error(self, component_name: str, error_msg: str):
        """组件错误处理"""
        self.event_coordinator.handle_component_error(component_name, error_msg)

    # ===== 兼容性方法 =====

    def _on_start_test(self):
        """开始测试（兼容性方法）"""
        # 修复检查是否已经使用统一测试控制器启动
        if hasattr(self, 'unified_test_controller') and self.unified_test_controller:
            if hasattr(self.unified_test_controller, '_current_state') and self.unified_test_controller._current_state == 'running':
                logger.info("🔄 统一测试控制器已在运行，跳过原有流程启动")
                return

        # 开始新测试会话，清理打印缓存
        if hasattr(self, 'label_print_manager') and self.label_print_manager:
            self.label_print_manager.start_new_test_session()

        # 清理测试完成标志，允许新测试的打印触发
        if hasattr(self, '_test_completion_flags'):
            self._test_completion_flags.clear()

        logger.info("🔄 使用原有测试流程（兼容性方法）")

        # Jack修复启动进度监控
        sampling_test = self.config_manager.get('test.sampling_test', False)
        if sampling_test:
            logger.info("🎯 采样测试模式：启动进度监控")
            self._start_progress_monitoring()

        self.test_flow_manager.start_test()

    def _on_stop_test(self):
        """停止测试（增强版）"""
        # 修复：使用线程锁防止重复执行
        with self._main_window_stop_lock:
            if self._main_window_stop_in_progress:
                logger.warning("🛑 主窗口停止操作已在进行中，跳过重复调用")
                return

            self._main_window_stop_in_progress = True

        try:
            logger.info("🛑 [增强版] 主窗口开始停止测试流程...")

            # 1. 立即设置主窗口状态
            self.is_testing = False

            # Jack修复停止进度监控
            self._stop_progress_monitoring()

            # 2. 强制停止测试流程管理器
            if hasattr(self, 'test_flow_manager') and self.test_flow_manager:
                try:
                    self.test_flow_manager.stop_test()
                    logger.info("✅ 测试流程管理器已停止")
                except Exception as e:
                    logger.error(f"停止测试流程管理器失败: {e}")

            # 3. 强制停止测试引擎（如果存在）
            if hasattr(self, 'test_engine') and self.test_engine:
                try:
                    self.test_engine.stop_test()
                    logger.info("✅ 测试引擎已停止")
                except Exception as e:
                    logger.error(f"停止测试引擎失败: {e}")

            # 4. 强制停止通信管理器的测试
            if hasattr(self, 'comm_manager') and self.comm_manager:
                try:
                    all_channels = list(range(8))
                    self.comm_manager.stop_impedance_measurement(all_channels)
                    logger.info("✅ 通信管理器测试已停止")
                except Exception as e:
                    logger.error(f"停止通信管理器测试失败: {e}")

            # 修复：停止标签打印队列，避免打印脏数据
            if hasattr(self, 'label_print_manager') and self.label_print_manager:
                try:
                    self.label_print_manager.handle_test_stopped()
                    logger.info("✅ 标签打印队列已清理")
                except Exception as e:
                    logger.error(f"清理标签打印队列失败: {e}")

            # 5. 更新UI状态
            try:
                # 新增强制重置通道显示状态
                if hasattr(self, 'ui_component_manager'):
                    channels_container = self.ui_component_manager.get_component('channels_container')
                    if channels_container:
                        # 先停止所有测试
                        if hasattr(channels_container, 'stop_all_tests'):
                            channels_container.stop_all_tests()
                            logger.info("✅ 所有通道测试已停止")

                        # 然后重置所有通道
                        if hasattr(channels_container, 'reset_all_channels'):
                            channels_container.reset_all_channels()
                            logger.info("✅ 通道显示已重置")

                        # 新增强制刷新UI显示
                        if hasattr(channels_container, 'channels'):
                            for channel in channels_container.channels:
                                if hasattr(channel, 'update'):
                                    channel.update()  # 强制刷新UI
                            logger.info("✅ 通道UI已强制刷新")

                        # 新增延迟强制重置UI状态，确保所有停止流程完成后再更新
                        from PyQt5.QtCore import QTimer
                        def force_reset_ui():
                            try:
                                if hasattr(channels_container, 'channels'):
                                    for channel in channels_container.channels:
                                        # 强制重置每个通道的UI状态
                                        if hasattr(channel, 'result_label'):
                                            channel.result_label.setText("待测试")
                                            channel.result_label.setObjectName("resultWaiting")
                                            channel.result_label.setStyleSheet("")
                                        if hasattr(channel, 'test_time_label'):
                                            channel.test_time_label.setText("00:00:00")
                                        if hasattr(channel, 'update'):
                                            channel.update()
                                    logger.info("✅ 延迟UI强制重置完成")
                            except Exception as e:
                                logger.error(f"延迟UI强制重置失败: {e}")

                        QTimer.singleShot(500, force_reset_ui)  # 500ms后强制重置UI

                # 更新状态栏
                status_bar = self.ui_component_manager.get_component('status_bar')
                if status_bar and hasattr(status_bar, 'set_system_status'):
                    status_bar.set_system_status("测试已停止", "warning")

            except Exception as e:
                logger.error(f"更新UI状态失败: {e}")

            # Jack修复检查是否为采样测试模式，如果是则触发参数建议对话框
            sampling_test = self.config_manager.get('test.sampling_test', False)
            if sampling_test:
                logger.info("🎯 采样测试模式：测试停止后检查是否需要显示参数建议对话框")
                # 延迟2秒后检查，确保停止流程完成
                QTimer.singleShot(2000, self._check_sampling_test_after_stop)

            logger.info("✅ [增强版] 主窗口停止测试流程完成")

        except Exception as e:
            logger.error(f"❌ [增强版] 主窗口停止测试失败: {e}")
        finally:
            # 修复：确保停止标志被重置
            with self._main_window_stop_lock:
                self._main_window_stop_in_progress = False

    def _check_sampling_test_after_stop(self):
        """测试停止后检查采样测试是否需要显示参数建议"""
        try:
            logger.debug(f" 检查采样测试停止后是否需要显示参数建议对话框...")

            # 检查是否为采样测试模式
            sampling_test = self.config_manager.get('test.sampling_test', False)
            if not sampling_test:
                logger.debug(f" 非采样测试模式，跳过参数建议检查")
                return

            # 获取采样测试集成管理器
            sampling_integration_manager = self._get_sampling_integration_manager()
            if not sampling_integration_manager:
                logger.warning("⚠️ 无法获取采样测试集成管理器，显示简单完成消息")
                self._show_simple_sampling_completion_message()
                return

            # 获取采样测试管理器
            sampling_manager = sampling_integration_manager.sampling_manager
            if not sampling_manager:
                logger.warning("⚠️ 无法获取采样测试管理器，显示简单完成消息")
                self._show_simple_sampling_completion_message()
                return

            # 检查是否有测试数据
            current_count, valid_count, target_count = sampling_manager.get_progress_info()
            logger.debug(f" 采样测试停止后检查: {valid_count}/{target_count} (总测试: {current_count})")

            # 修复：只有达到设定测试次数才触发采样完成流程
            if current_count >= target_count:
                logger.info(f"🎉 检测到已达到设定测试次数({current_count}/{target_count})，触发最终确认流程")

                # 强制设置为完成状态
                if valid_count < target_count:
                    sampling_manager.valid_sample_count = min(current_count, target_count)
                    logger.debug(f" 强制设置有效样本数为: {sampling_manager.valid_sample_count}")

                # 修复：获取最后一次测试的数据，显示采样结果确认对话框
                try:
                    # 获取最后一次测试的数据
                    last_test_data = sampling_manager.get_last_test_data()
                    if last_test_data:
                        test_id = last_test_data.get('test_id')
                        channel_data = last_test_data.get('channel_data', {})

                        # 获取统计数据和进度信息
                        statistics_data = sampling_manager.get_current_statistics()
                        progress_info = sampling_manager.get_progress_info()

                        logger.info("📋 显示最终采样结果确认对话框，用户确认后将显示参数建议")

                        # 显示结果确认对话框，用户确认后会自动显示参数建议对话框
                        sampling_integration_manager._show_result_confirmation_dialog(
                            test_id, channel_data, statistics_data, progress_info
                        )
                    else:
                        logger.warning("⚠️ 无法获取最后一次测试数据，直接显示参数建议对话框")
                        sampling_integration_manager._handle_sampling_completion()

                except Exception as e:
                    logger.error(f"❌ 显示最终确认对话框失败: {e}")
                    # 如果出错，直接显示参数建议对话框
                    sampling_integration_manager._handle_sampling_completion()
            else:
                logger.debug(f" 未达到设定测试次数({current_count}/{target_count})，不触发采样完成流程")

        except Exception as e:
            logger.error(f"❌ 检查采样测试停止后状态失败: {e}")
            # 如果检查失败，也尝试显示参数建议对话框
            try:
                self._force_show_parameter_suggestion_dialog()
            except Exception as force_error:
                logger.error(f"❌ 强制显示参数建议对话框也失败: {force_error}")

    def _check_sampling_test_completion_after_channel_complete(self, completed_channel_num: int):
        """通道完成后检查采样测试是否全部完成"""
        try:
            logger.debug(f" 通道{completed_channel_num}完成，检查采样测试是否全部完成...")

            # 检查是否为采样测试模式
            sampling_test = self.config_manager.get('test.sampling_test', False)
            if not sampling_test:
                logger.debug("🔧 非采样测试模式，跳过检查")
                return

            # 延迟检查，确保所有通道状态都已更新
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(2000, self._delayed_check_all_channels_sampling_completion)

        except Exception as e:
            logger.error(f"❌ 检查采样测试完成失败: {e}")

    def _delayed_check_all_channels_sampling_completion(self):
        """延迟检查所有通道的采样测试完成状态"""
        try:
            logger.debug(f" 延迟检查所有通道的采样测试完成状态...")

            # 检查是否为采样测试模式
            sampling_test = self.config_manager.get('test.sampling_test', False)
            if not sampling_test:
                logger.debug("🔧 非采样测试模式，跳过检查")
                return

            # 检查测试是否还在进行中
            if self.is_testing:
                logger.debug(f" 测试仍在进行中，跳过采样完成检查")
                return

            # 检查是否有测试数据
            from data.database_manager import DatabaseManager
            from datetime import datetime, timedelta
            db_manager = DatabaseManager()

            # 获取最近的测试结果（最近5分钟内的）
            end_date = datetime.now().date()
            start_date = end_date  # 只查询今天的数据

            recent_results = db_manager.get_test_results(
                start_date=start_date,
                end_date=end_date,
                limit=10
            )
            if not recent_results:
                logger.debug(f" 没有找到最近的测试结果，跳过采样完成检查")
                return

            logger.info(f"🎉 检测到 {len(recent_results)} 条最近的测试结果，采样测试完成")
            # 移除小的参数建议窗体，只保留大的取样测试结果窗体

        except Exception as e:
            logger.error(f"❌ 延迟检查采样测试完成失败: {e}")
            # 移除小的参数建议窗体调用

    def _on_clear_statistics(self):
        """清空统计（兼容性方法）"""
        self.ui_component_manager.clear_test_data()

    def _on_export_data(self):
        """导出数据（兼容性方法）"""
        self.menu_manager._on_export_data()

    def _on_open_settings(self):
        """打开设置（兼容性方法）"""
        self.menu_manager._on_open_settings()

    def _on_channel_test_completed(self, channel_num: int, result_data: dict):
        """通道测试完成处理（防重复触发）"""
        try:
            # 修复允许在测试停止后的短时间内继续处理通道完成（用于打印）
            # 检查是否在测试停止的宽限期内
            import time
            current_time = time.time()
            test_stop_time = getattr(self, '_test_stop_time', None)
            grace_period = 5.0  # 5秒宽限期

            if not self.is_testing:
                # 🔧 [修复] 检查是否在测试完成的数据保存阶段
                # 如果测试刚刚完成，允许短时间内继续处理通道完成（用于数据保存）
                if test_stop_time and (current_time - test_stop_time) <= grace_period:
                    logger.info(f"🔧 测试停止后宽限期内，允许通道{channel_num}完成数据保存")
                else:
                    # Jack要求测试停止后不应该处理任何结果，不计算Rs/Rct，不打印，不存数据库
                    logger.warning(f"🛑 测试已被停止，跳过通道{channel_num}的测试完成处理，避免处理脏数据")
                    return

            # 🎯 取样测试模式：正常更新UI显示，但不执行打印处理
            sampling_test = self.config_manager.get('test.sampling_test', False)
            if sampling_test:
                logger.info(f"🎯 通道{channel_num}取样测试模式：正常更新UI，跳过打印处理")
                # 继续执行UI更新，但在打印处理时返回

            # 修复放宽数据验证，允许测试失败的情况也进行打印
            # 检查是否有测试数据（不要求数值必须大于0）
            has_test_data = (
                result_data.get('rs_value') is not None or
                result_data.get('rct_value') is not None or
                result_data.get('rs') is not None or
                result_data.get('rct') is not None or
                result_data.get('is_pass') is not None or
                result_data.get('rs_grade') is not None or
                result_data.get('rct_grade') is not None
            )

            # 只有完全没有测试数据时才跳过
            if not has_test_data:
                logger.warning(f"[主窗口] 通道{channel_num}完全没有测试数据，跳过打印")
                return

            # 记录数据状态，允许0值的情况
            rs_val = result_data.get('rs_value', result_data.get('rs', 0))
            rct_val = result_data.get('rct_value', result_data.get('rct', 0))
            is_pass = result_data.get('is_pass', False)
            rs_grade = result_data.get('rs_grade', 'N/A')
            rct_grade = result_data.get('rct_grade', 'N/A')

            logger.info(f"[主窗口] 通道{channel_num}准备打印: Rs={rs_val:.3f}mΩ, Rct={rct_val:.3f}mΩ, 档位={rs_grade}-{rct_grade}, 结果={'合格' if is_pass else '不合格'}")

            # 修复使用测试轮次标识进行重复检查，避免跨测试轮次的误判
            current_test_id = getattr(self, '_current_test_id', None)
            if current_test_id is None:
                # 生成新的测试ID
                import time
                self._current_test_id = int(time.time() * 1000)  # 毫秒级时间戳
                current_test_id = self._current_test_id
                logger.debug(f"生成新的测试ID: {current_test_id}")

            completion_key = f"test_{current_test_id}_ch{channel_num}_completed"
            if hasattr(self, '_test_completion_flags'):
                if completion_key in self._test_completion_flags:
                    logger.debug(f"通道{channel_num}在当前测试轮次({current_test_id})已完成打印，跳过")
                    return
            else:
                self._test_completion_flags = set()

            # 标记该通道在当前测试轮次已完成
            self._test_completion_flags.add(completion_key)
            logger.debug(f"标记通道{channel_num}在测试轮次({current_test_id})已完成打印")

            # 🎯 取样测试模式：跳过打印处理，但检查是否所有通道都完成
            if sampling_test:
                logger.info(f"🎯 通道{channel_num}取样测试模式：跳过标签打印")

                # Jack修复检查是否所有通道都完成了采样测试
                self._check_sampling_test_completion_after_channel_complete(channel_num)
                return

            # 🔥 新的打印机制：直接通过自动打印管理器处理
            # 打印处理已移至测试结果保存时直接触发，此处不再需要

        except Exception as e:
            logger.error(f"处理通道{channel_num}测试完成失败: {e}")

    def _trigger_label_print(self, channel_num: int, result_data: dict):
        """触发标签打印（兼容性方法，现在使用新的自动打印管理器）"""
        try:
            # 🔥 使用新的自动打印管理器
            if hasattr(self, 'auto_print_manager'):
                self.auto_print_manager.trigger_print_for_test_result(result_data)
            else:
                logger.warning("自动打印管理器未初始化")

        except Exception as e:
            logger.error(f"触发通道{channel_num}标签打印失败: {e}")

    def _prepare_print_data(self, channel_num: int, result_data: dict) -> dict:
        """准备打印数据（优先获取最新测试结果）"""
        try:
            logger.debug(f" [打印数据] 通道{channel_num}开始准备打印数据")

            # 🔧 修复：直接从数据库获取最新测试结果，避免重复计算
            latest_data = None
            try:
                # 从数据库获取该通道的最新测试结果
                latest_data = self._get_latest_test_result_from_database(channel_num)
                if latest_data:
                    logger.info(f"✅ [打印数据] 通道{channel_num}从数据库获取到最新测试结果: Rs={latest_data.get('rs_value', 0):.3f}mΩ, Rct={latest_data.get('rct_value', 0):.3f}mΩ")
                else:
                    logger.warning(f"⚠️ [打印数据] 通道{channel_num}数据库中未找到测试结果")
            except Exception as e:
                logger.error(f"❌ [打印数据] 通道{channel_num}从数据库获取测试结果失败: {e}")

            # 选择数据源优先使用最新数据，备用传入数据
            if latest_data and latest_data.get('rs_value', 0) > 0 and latest_data.get('rct_value', 0) > 0:
                # 使用最新的测试结果数据
                source_data = latest_data
                data_source = "最新测试结果"
                logger.info(f"🎯 [打印数据] 通道{channel_num}使用最新测试结果数据")
            else:
                # 使用传入的回调数据作为备用
                source_data = result_data
                data_source = "回调传入数据"
                logger.warning(f"⚠️ [打印数据] 通道{channel_num}使用回调传入数据（备用）")

            # 从选定的数据源提取信息
            rs_grade = source_data.get('rs_grade')
            rct_grade = source_data.get('rct_grade')
            is_pass = source_data.get('is_pass', False)

            # 验证数据有效性
            if (rs_grade is not None and rct_grade is not None and
                source_data.get('rs_value', 0) > 0 and source_data.get('rct_value', 0) > 0):

                logger.info(f"✅ [打印数据] 通道{channel_num}使用{data_source}: Rs={source_data.get('rs_value', 0):.3f}mΩ, Rct={source_data.get('rct_value', 0):.3f}mΩ, 档位={rs_grade}-{rct_grade}")

                # 构建完整的打印数据
                print_data = {
                    'channel_number': channel_num,
                    'battery_code': source_data.get('battery_code', f'BAT{channel_num:03d}'),
                    'voltage': source_data.get('voltage', 0),
                    'rs': source_data.get('rs_value', source_data.get('rs', 0)),
                    'rct': source_data.get('rct_value', source_data.get('rct', 0)),
                    'rs_value': source_data.get('rs_value', source_data.get('rs', 0)),
                    'rct_value': source_data.get('rct_value', source_data.get('rct', 0)),
                    'rs_grade': rs_grade,
                    'rct_grade': rct_grade,
                    'is_pass': is_pass,
                    'timestamp': datetime.now(),
                    'outlier_result': source_data.get('outlier_result', 'PASS'),
                    'outlier_rate': source_data.get('outlier_rate', 'PASS'),
                    'frequency_deviations': source_data.get('frequency_deviations', {}),
                    'max_deviation_percent': source_data.get('max_deviation_percent', 0.0),
                    'baseline_filename': source_data.get('baseline_filename', ''),
                    'baseline_id': source_data.get('baseline_id', None)
                }

                return print_data
            else:
                logger.warning(f"⚠️ [打印数据] 通道{channel_num}{data_source}无效: Rs档位={rs_grade}, Rct档位={rct_grade}, Rs值={source_data.get('rs_value', 0)}, Rct值={source_data.get('rct_value', 0)}")

            # 备用数据处理如果所有数据源都无效，使用传入数据构建基础打印数据
            logger.warning(f"⚠️ [打印数据] 通道{channel_num}所有数据源都无效，使用传入数据构建基础打印数据")

            # 获取电池码
            battery_code = result_data.get('battery_code', f'CH{channel_num}-{int(time.time())}')

            # 如果没有电池码，尝试从其他地方获取
            if not battery_code or battery_code.startswith('CH'):
                # 尝试从测试流程管理器获取
                if hasattr(self, 'test_flow_manager') and hasattr(self.test_flow_manager, 'battery_codes'):
                    battery_codes = getattr(self.test_flow_manager, 'battery_codes', {})
                    battery_code = battery_codes.get(channel_num, f'AUTO-{channel_num}-{int(time.time())}')

            # 准备标签打印数据，正确处理档位信息
            rs_grade = result_data.get('rs_grade')
            rct_grade = result_data.get('rct_grade')
            is_pass = result_data.get('is_pass', False)

            # 根据测试结果正确设置档位显示
            if is_pass and rs_grade is not None and rct_grade is not None:
                grade_result = f"{rs_grade}-{rct_grade}"  # 合格时显示档位
            else:
                grade_result = "不合格"  # 不合格时显示不合格
                if not is_pass:
                    rs_grade = "--"
                    rct_grade = "--"

            # 获取时间戳（支持多种字段名）
            timestamp = result_data.get('timestamp')
            if not timestamp:
                # 如果没有timestamp，尝试从test_time获取
                test_time = result_data.get('test_time')
                if test_time:
                    # 如果test_time是ISO格式字符串，转换为datetime对象
                    if isinstance(test_time, str):
                        try:
                            timestamp = datetime.fromisoformat(test_time.replace('Z', '+00:00'))
                        except ValueError:
                            timestamp = datetime.now()
                    else:
                        timestamp = test_time
                else:
                    timestamp = datetime.now()

            # 正确获取Rs和Rct值，处理字段名不匹配问题
            rs_value = result_data.get('rs_value', result_data.get('rs', 0.0))
            rct_value = result_data.get('rct_value', result_data.get('rct', 0.0))
            voltage = result_data.get('voltage', 0.0)

            # 获取离群率相关数据
            outlier_result = result_data.get('outlier_result', '')
            baseline_filename = result_data.get('baseline_filename', '')
            baseline_id = result_data.get('baseline_id', '')
            max_deviation_percent = result_data.get('max_deviation_percent', 0.0)
            frequency_deviations = result_data.get('frequency_deviations', {})


            # 如果仍然获取不到值，尝试从通道组件直接获取当前值
            if rs_value == 0.0 or rct_value == 0.0 or not outlier_result:
                try:
                    channels_container = self.ui_component_manager.get_component('channels_container')
                    if channels_container:
                        channel_widget = channels_container.get_channel(channel_num)
                        if channel_widget:
                            # 优先从通道组件的test_result获取完整数据
                            if hasattr(channel_widget, 'test_result') and channel_widget.test_result:
                                test_result = channel_widget.test_result

                                # 获取Rs/Rct值
                                if rs_value == 0.0:
                                    rs_value = test_result.get('rs_value', test_result.get('rs', 0.0))
                                if rct_value == 0.0:
                                    rct_value = test_result.get('rct_value', test_result.get('rct', 0.0))
                                if voltage == 0.0:
                                    voltage = test_result.get('voltage', 0.0)

                                # 获取离群率数据
                                if not outlier_result:
                                    outlier_result = test_result.get('outlier_result', test_result.get('outlier_rate', ''))
                                    frequency_deviations = test_result.get('frequency_deviations', {})
                                    max_deviation_percent = test_result.get('max_deviation_percent', 0.0)


                            # 如果test_result中还是没有数据，尝试从通道组件属性获取
                            if rs_value == 0.0 or rct_value == 0.0:
                                current_rs = getattr(channel_widget, 'rs_value', 0.0)
                                current_rct = getattr(channel_widget, 'rct_value', 0.0)
                                current_voltage = getattr(channel_widget, 'voltage', 0.0)
                                current_outlier = getattr(channel_widget, 'outlier_rate_result', '')

                                # 优先使用非零值
                                if current_rs > 0:
                                    rs_value = current_rs
                                if current_rct > 0:
                                    rct_value = current_rct
                                if current_voltage > 0:
                                    voltage = current_voltage
                                if current_outlier and not outlier_result:
                                    outlier_result = current_outlier


                except Exception as e:
                    logger.warning(f"从通道{channel_num}组件获取值失败: {e}")
                    import traceback
                    logger.debug(f"详细错误信息: {traceback.format_exc()}")

            # 获取测试结果状态，处理不合格原因
            is_pass = result_data.get('is_pass', False)
            fail_reason = result_data.get('fail_reason', '')

            # 完善失败原因处理，使用与UI显示一致的组合逻辑
            if not is_pass and not fail_reason:
                fail_items = result_data.get('fail_items', [])
                if fail_items:
                    # 使用与UI显示一致的组合失败原因逻辑
                    fail_reason = self._generate_combined_fail_reason(fail_items)
                else:
                    # 如果没有fail_items但有离群率结果，检查离群率是否不合格
                    if outlier_result and outlier_result not in ["PASS", "已禁用", "无数据", ""]:
                        fail_reason = '不合格-离群率'
                    else:
                        fail_reason = '不合格'

            print_data = {
                'channel_number': channel_num,
                'battery_code': battery_code,
                'voltage': voltage,
                'rs_value': rs_value,
                'rct_value': rct_value,
                'rs_grade': rs_grade,
                'rct_grade': rct_grade,
                'grade_result': grade_result,
                'is_pass': is_pass,
                'fail_reason': fail_reason,
                'test_duration': result_data.get('test_duration', 0),
                'timestamp': timestamp,
                # 离群率相关数据
                'outlier_rate': outlier_result,
                'outlier_result': outlier_result,
                'baseline_filename': baseline_filename,
                'baseline_id': baseline_id,
                'max_deviation_percent': max_deviation_percent,
                'frequency_deviations': frequency_deviations
            }

            logger.info(f"通道{channel_num}打印数据准备完成: {battery_code} "
                        f"Rs={rs_value:.3f}mΩ Rct={rct_value:.3f}mΩ 档位={rs_grade}-{rct_grade} "
                        f"离群率={outlier_result} 结果={'合格' if is_pass else fail_reason}")

            return print_data

        except Exception as e:
            logger.error(f"准备通道{channel_num}打印数据失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            # 返回基本数据
            return {
                'channel_number': channel_num,
                'battery_code': f'ERROR-{channel_num}',
                'voltage': 0.0,
                'rs_value': 0.0,
                'rct_value': 0.0,
                'rs_grade': 1,
                'rct_grade': 1,
                'grade_result': '1-1',
                'is_pass': False,
                'timestamp': datetime.now()
            }

    def _get_latest_test_result_from_database(self, channel_num: int) -> dict:
        """
        从数据库获取指定通道的最新测试结果

        Args:
            channel_num: 通道号

        Returns:
            测试结果数据字典，如果没有找到则返回None
        """
        try:
            # 获取数据库管理器
            db_manager = None
            if hasattr(self, 'test_executor') and hasattr(self.test_executor, 'test_result_manager'):
                db_manager = self.test_executor.test_result_manager.db_manager

            if not db_manager:
                # 创建临时数据库管理器
                from data.database_manager import DatabaseManager
                db_manager = DatabaseManager()

            # 查询该通道的最新测试结果
            query = """
                SELECT channel_number, battery_code, voltage, rs_value, rct_value,
                       rs_grade, rct_grade, is_pass, fail_reason, test_start_time
                FROM test_results
                WHERE channel_number = ?
                ORDER BY test_start_time DESC
                LIMIT 1
            """

            result = db_manager.execute_query(query, (channel_num,))

            if result and len(result) > 0:
                row = result[0]
                # 构建测试结果数据
                test_data = {
                    'channel_number': row[0],
                    'battery_code': row[1],
                    'voltage': row[2],
                    'rs_value': row[3],
                    'rct_value': row[4],
                    'rs_grade': row[5],
                    'rct_grade': row[6],
                    'is_pass': bool(row[7]),
                    'fail_reason': row[8] or '',
                    'test_start_time': row[9]
                }

                # 🔧 解析fail_reason生成fail_items
                fail_reason = test_data.get('fail_reason', '')
                fail_items = []
                if fail_reason and not test_data['is_pass']:
                    # 从详细失败原因中提取失败项目
                    if '电压超标' in fail_reason:
                        fail_items.append('电压')
                    if 'Rs超标' in fail_reason:
                        fail_items.append('Rs')
                    if 'Rct超标' in fail_reason:
                        fail_items.append('Rct')
                    if '离群率' in fail_reason:
                        fail_items.append('离群率')

                test_data['fail_items'] = fail_items

                logger.debug(f"✅ 从数据库获取通道{channel_num}最新测试结果: Rs={test_data['rs_value']:.3f}mΩ, Rct={test_data['rct_value']:.3f}mΩ, 合格={test_data['is_pass']}")
                return test_data
            else:
                logger.warning(f"⚠️ 数据库中未找到通道{channel_num}的测试结果")
                return None

        except Exception as e:
            logger.error(f"❌ 从数据库获取通道{channel_num}测试结果失败: {e}")
            return None

    def _generate_combined_fail_reason(self, fail_items: list) -> str:
        """
        生成组合失败原因文本（统一使用失败结果显示工具类）

        Args:
            fail_items: 失败项目列表，如 ["电压", "离群率", "Rs"]

        Returns:
            组合失败原因文本，如 "不合格-电压/离群率/Rs"
        """
        try:
            # 🔧 统一使用失败结果显示工具类
            return FailResultDisplayUtils.generate_combined_fail_reason(fail_items)
        except Exception as e:
            logger.error(f"生成组合失败原因失败: {e}")
            return "不合格"

    def _on_channel_battery_code_changed(self, channel_num: int, battery_code: str):
        """通道电池码变更（兼容性方法）"""
        # 通道电池码设置 - 运行时不输出日志
        pass

    def _on_all_channels_ready(self):
        """所有通道就绪处理"""
        try:
            logger.info("🎯 _on_all_channels_ready方法被调用")

            # 修复采样测试模式下不使用重复调用检查，确保每次都能处理
            sampling_test = self.config_manager.get('test.sampling_test', False)

            if not sampling_test:
                # 非采样测试模式：使用重复调用检查
                if hasattr(self, '_all_channels_ready_processed') and self._all_channels_ready_processed:
                    logger.debug("所有通道就绪已处理过，跳过重复处理")
                    return
                self._all_channels_ready_processed = True

            logger.info("所有通道测试完成")

            # 更新状态栏显示
            status_bar = self.ui_component_manager.get_component('status_bar')
            if status_bar and hasattr(status_bar, 'set_system_status'):
                status_bar.set_system_status("所有通道测试完成", "success")

            if sampling_test:
                # 取样测试模式：先处理取样数据，然后执行停止流程
                logger.info("🎯 取样测试模式：先处理取样数据，避免状态丢失")

                # 修复先处理取样测试完成，确保对话框能正常显示
                self._handle_sampling_test_completion()

                # 新增检查采样测试是否应该完成并显示参数建议对话框
                self._check_and_handle_sampling_completion()

                # 然后执行停止流程
                self._handle_test_completion_stop()

                # 采样测试模式延迟设置处理标志，避免阻塞当前处理
                QTimer.singleShot(1000, lambda: setattr(self, '_all_channels_ready_processed', True))
            else:
                # 非取样测试模式：执行正常的测试完成处理
                # 检查当前测试模式，如果是手动模式则重置按钮状态
                self._handle_manual_mode_completion()

                # 检查是否需要停止测试（只有在非连续测试模式下才停止）
                self._handle_test_completion_stop()

            # 延长重置时间，避免短时间内的重复调用
            QTimer.singleShot(10000, self._reset_all_channels_ready_flag)

        except Exception as e:
            logger.error(f"处理所有通道就绪失败: {e}")
            # Jack修复如果采样测试模式下出现异常，尝试强制完成
            sampling_test = self.config_manager.get('test.sampling_test', False)
            if sampling_test:
                logger.debug(f" 采样测试模式异常，尝试强制完成...")
                try:
                    self._force_show_parameter_suggestion_dialog()
                except Exception as force_error:
                    logger.error(f"❌ 强制完成也失败: {force_error}")

            # 确保重置标志，避免卡住
            if hasattr(self, '_all_channels_ready_processed'):
                self._all_channels_ready_processed = False
            # 修复确保在异常情况下也能重置标志
            try:
                QTimer.singleShot(10000, self._reset_all_channels_ready_flag)
            except:
                # 如果QTimer也失败，直接重置
                self._reset_all_channels_ready_flag()

    def _reset_all_channels_ready_flag(self):
        """重置所有通道就绪标志"""
        try:
            self._all_channels_ready_processed = False
            logger.debug("所有通道就绪标志已重置，允许下次测试处理")
        except Exception as e:
            logger.error(f"重置所有通道就绪标志失败: {e}")

    def _get_current_test_mode_info(self):
        """获取当前测试模式信息（统一判断逻辑）"""
        try:
            # 获取所有相关配置
            continuous_mode = self.config_manager.get('test.continuous_mode', False)
            auto_detect = self.config_manager.get('test.auto_detect', False)
            sampling_test = self.config_manager.get('test.sampling_test', False)

            # 统一判断逻辑
            is_manual_mode = not continuous_mode and not auto_detect and not sampling_test

            return {
                'continuous_mode': continuous_mode,
                'auto_detect': auto_detect,
                'sampling_test': sampling_test,
                'is_manual_mode': is_manual_mode
            }
        except Exception as e:
            logger.error(f"获取测试模式信息失败: {e}")
            return {
                'continuous_mode': False,
                'auto_detect': True,
                'sampling_test': False,
                'is_manual_mode': True
            }

    def _handle_manual_mode_completion(self):
        """处理测试完成后的UI状态管理"""
        try:
            # 统一使用测试模式判断逻辑
            mode_info = self._get_current_test_mode_info()

            logger.debug(f" 测试完成状态检查: 手动模式={mode_info['is_manual_mode']}, 连续测试={mode_info['continuous_mode']}, 自动侦测={mode_info['auto_detect']}, 取样测试={mode_info['sampling_test']}")

            # 修复：只在真正的手动模式和取样测试模式下重置按钮状态
            should_reset_button = (
                mode_info['is_manual_mode'] or  # 手动模式
                mode_info['sampling_test']      # 取样测试模式
                # 移除自动侦测模式的按钮重置，因为自动侦测应该保持测试状态
            )

            if should_reset_button:
                logger.info("✅ 检测到需要重置按钮状态的测试模式")

                # 通知测试控制组件测试完成
                test_control = self.ui_component_manager.get_component('test_control')
                if test_control and hasattr(test_control, 'on_test_completed'):
                    logger.info("🔄 调用测试控制组件的on_test_completed方法")
                    test_control.on_test_completed()
                    logger.info("✅ 已通知测试控制组件重置按钮状态")
                else:
                    logger.warning("❌ 无法获取测试控制组件或组件没有on_test_completed方法")

                # 新增确保测试结果正确显示在UI上
                self._ensure_test_results_displayed()

            else:
                logger.info(f"ℹ️ 连续测试模式，保持测试状态（连续测试: {mode_info['continuous_mode']}）")

        except Exception as e:
            logger.error(f"处理测试完成状态管理失败: {e}")

    def _ensure_test_results_displayed(self):
        """确保测试结果正确显示在UI界面上"""
        try:
            logger.debug(f" 确保测试结果正确显示在UI界面")

            # 获取通道容器组件
            channels_container = self.ui_component_manager.get_component('channels_container')
            if not channels_container:
                logger.warning("未找到通道容器组件")
                return

            # 获取启用的通道
            enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))

            # 检查每个通道的测试结果显示状态
            for channel_num in enabled_channels:
                try:
                    channel_widget = getattr(channels_container, f'channel_{channel_num}', None)
                    if channel_widget:
                        # 检查通道是否有测试结果显示
                        if hasattr(channel_widget, 'test_completion_manager'):
                            completion_manager = channel_widget.test_completion_manager
                            if hasattr(completion_manager, 'test_result') and completion_manager.test_result:
                                logger.debug(f"通道{channel_num}测试结果已正确显示")
                            else:
                                logger.warning(f"通道{channel_num}测试结果显示可能不完整")
                        else:
                            logger.debug(f"通道{channel_num}没有测试完成管理器")
                    else:
                        logger.warning(f"未找到通道{channel_num}组件")

                except Exception as e:
                    logger.error(f"检查通道{channel_num}测试结果显示失败: {e}")

            logger.info("✅ 测试结果显示状态检查完成")

        except Exception as e:
            logger.error(f"确保测试结果显示失败: {e}")

    def _handle_test_completion_stop(self):
        """处理测试完成后的停止逻辑"""
        try:
            # 统一使用测试模式判断逻辑
            mode_info = self._get_current_test_mode_info()

            logger.debug(f" 检查是否需要停止测试: 连续测试={mode_info['continuous_mode']}, 自动侦测={mode_info['auto_detect']}, 取样测试={mode_info['sampling_test']}, 手动模式={mode_info['is_manual_mode']}")

            if mode_info['sampling_test']:
                # 🎯 取样测试模式：使用完整的停止流程，确保UI正确重置
                logger.info("🎯 取样测试模式：使用完整停止流程，确保UI正确重置")

                # 关键修复调用完整的停止测试方法，确保UI也被重置
                self._on_stop_test()  # 使用完整的停止流程，包含UI重置

                logger.info("✅ 取样测试：完整停止流程已执行，UI应已重置")

            elif mode_info['is_manual_mode']:
                logger.info("✅ 检测到手动模式，但按钮状态已在on_test_completed中处理，只需停止测试流程")
                # 手动模式下，按钮状态已经在 on_test_completed 中正确设置
                # 这里只需要停止测试流程，不要再调用 _on_stop_test() 避免重复设置按钮状态
                if self.is_testing:
                    # 修复确保状态完全重置，避免下次启动时状态冲突
                    logger.info("🔄 手动模式：开始完整状态重置")

                    # 1. 记录测试停止时间，允许数据保存宽限期（必须在设置is_testing=False之前）
                    import time
                    self._test_stop_time = time.time()
                    logger.info(f"🔧 [提前记录] 测试停止时间: {self._test_stop_time}，允许5秒宽限期完成数据保存")

                    # 2. 直接更新主窗口测试状态
                    self.is_testing = False

                    # 2. 通过测试流程管理器停止测试
                    self.test_flow_manager.stop_test()

                    # 3. 确保测试流程管理器状态完全重置
                    if hasattr(self.test_flow_manager, 'is_testing'):
                        self.test_flow_manager.is_testing = False
                        logger.debug("✅ 测试流程管理器状态已强制重置")

                    # 4. 确保测试控制组件状态同步
                    test_control = self.ui_component_manager.get_component('test_control')
                    if test_control and hasattr(test_control, 'is_testing'):
                        test_control.is_testing = False
                        logger.debug("✅ 测试控制组件状态已同步重置")

                    # 5. 🔧 关键修复：重置电池检测管理器状态，解决第二次测试无法启动的问题
                    self._mark_battery_detection_test_completed()
                    logger.debug("✅ 电池检测管理器状态已重置")

                    logger.info("✅ 手动模式：测试流程已停止，所有状态已重置")
            else:
                logger.info(f"ℹ️ 连续测试或自动侦测模式，不停止测试（连续测试: {mode_info['continuous_mode']}, 自动侦测: {mode_info['auto_detect']}）")

                # 修复：在自动侦测模式下，延迟执行完整的测试重置，确保打印完成
                if mode_info['auto_detect'] and not mode_info['continuous_mode']:
                    logger.info("✅ 自动侦测模式：测试完成，延迟执行完整测试重置（确保打印完成）")

                    # 🔧 Jack修复：检查当前打印状态并记录
                    try:
                        if hasattr(self, 'label_print_manager') and self.label_print_manager:
                            queue_size = self.label_print_manager.get_queue_size()
                            current_job = self.label_print_manager.current_job
                            logger.info(f"🖨️ [测试完成] 当前打印状态: 队列大小={queue_size}, 当前任务={'有' if current_job else '无'}")
                    except Exception as e:
                        logger.warning(f"🖨️ [测试完成] 检查打印状态失败: {e}")

                    # 延迟执行自动侦测模式重置，给打印流程足够时间完成
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(3000, self._complete_auto_detect_test_reset_delayed)
                    logger.info("✅ 自动侦测模式：已安排延迟重置（3秒后执行），确保打印流程完成")

        except Exception as e:
            logger.error(f"处理测试完成停止逻辑失败: {e}")

    def _complete_auto_detect_test_reset(self):
        """自动侦测模式下的完整测试重置"""
        try:
            logger.info("🔄 自动侦测模式：开始完整测试重置...")

            # 1. 重置主窗口测试状态
            self.is_testing = False

            # 2. 清理自动测试启动标志
            if hasattr(self, '_auto_test_starting'):
                self._auto_test_starting = False
                logger.debug("已清理自动测试启动标志")

            # 3. 重置测试流程管理器状态
            if hasattr(self, 'test_flow_manager') and self.test_flow_manager:
                try:
                    # 确保测试流程管理器停止
                    self.test_flow_manager.stop_test()

                    # 重置测试流程管理器状态
                    if hasattr(self.test_flow_manager, 'is_testing'):
                        self.test_flow_manager.is_testing = False

                    # 重置测试流程管理器内部状态
                    self._reset_test_flow_manager_state()

                    logger.debug("测试流程管理器状态已重置")
                except Exception as e:
                    logger.error(f"重置测试流程管理器状态失败: {e}")

            # 4. 执行状态清理
            self._clean_test_states_for_auto_detect()

            # 标记电池检测管理器中的测试完成状态
            self._mark_battery_detection_test_completed()

            # 电池检测模式下不自动重启电池检测，但保持激活状态
            # 测试完成后应该等待用户移除电池，然后检测到电池移除事件后才进入下一轮检测

            # 更新状态栏提示用户移除电池
            try:
                status_bar = self.ui_component_manager.get_component('status_bar')
                if status_bar and hasattr(status_bar, 'set_system_status'):
                    if self._battery_detection_active:
                        status_bar.set_system_status("测试完成，请移除电池后插入新电池", "success")
                    else:
                        status_bar.set_system_status("测试完成，请移除电池", "success")
            except Exception as e:
                logger.error(f"更新状态栏提示失败: {e}")

            # 🎯 启动电池移除监控，等待所有电池移除后自动弹出新一轮测试引导
            logger.info(f"🔋 检查电池侦测模式状态: _battery_detection_active={self._battery_detection_active}")
            if self._battery_detection_active:
                logger.info("🔋 电池侦测模式已激活，启动电池移除监控")
                self._start_battery_removal_monitoring()
            else:
                logger.info("🔋 电池侦测模式未激活，跳过电池移除监控")

            logger.info("✅ 自动侦测模式完整测试重置完成")

        except Exception as e:
            logger.error(f"自动侦测模式完整测试重置失败: {e}")

    def _complete_auto_detect_test_reset_delayed(self):
        """延迟执行的自动侦测模式完整测试重置"""
        try:
            logger.info("🔄 [延迟重置] 自动侦测模式：开始延迟完整测试重置...")

            # 检查是否仍在自动侦测模式
            auto_detect = self.config_manager.get('test.auto_detect', False)
            if not auto_detect:
                logger.info("🔄 [延迟重置] 自动侦测模式已关闭，跳过延迟重置")
                return

            # 🔧 Jack修复：添加超时保护，避免无限等待
            if not hasattr(self, '_reset_delay_start_time'):
                self._reset_delay_start_time = time.time()

            elapsed_time = time.time() - self._reset_delay_start_time
            max_wait_time = 30.0  # 最大等待30秒

            if elapsed_time > max_wait_time:
                logger.warning(f"🔄 [延迟重置] 等待打印完成超时({max_wait_time}秒)，强制执行重置")
                # 清理超时标记
                if hasattr(self, '_reset_delay_start_time'):
                    delattr(self, '_reset_delay_start_time')
                # 强制执行重置
                self._complete_auto_detect_test_reset()
                return

            # 检查打印队列状态，确保打印完成
            print_queue_empty = True
            current_job_active = False
            try:
                if hasattr(self, 'label_print_manager') and self.label_print_manager:
                    # 使用标准方法检查打印队列大小
                    queue_size = self.label_print_manager.get_queue_size()
                    print_queue_empty = (queue_size == 0)

                    # 检查是否有当前正在处理的任务
                    current_job_active = (self.label_print_manager.current_job is not None)

                    logger.info(f"🔄 [延迟重置] 打印状态检查: 队列大小={queue_size}, 队列为空={print_queue_empty}, 当前任务活跃={current_job_active}")
                else:
                    logger.debug("🔄 [延迟重置] 打印管理器不存在，假设打印已完成")
            except Exception as e:
                logger.warning(f"🔄 [延迟重置] 检查打印状态失败: {e}")

            if not print_queue_empty or current_job_active:
                logger.info(f"🔄 [延迟重置] 打印未完成（队列非空={not print_queue_empty}, 当前任务活跃={current_job_active}），再次延迟重置")
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(2000, self._complete_auto_detect_test_reset_delayed)
                return

            logger.info("🔄 [延迟重置] 所有打印任务已完成，执行完整重置")

            # 清理延迟开始时间标记
            if hasattr(self, '_reset_delay_start_time'):
                delattr(self, '_reset_delay_start_time')

            # 执行完整的自动侦测模式重置
            self._complete_auto_detect_test_reset()

        except Exception as e:
            logger.error(f"延迟自动侦测模式重置失败: {e}")

    def _handle_sampling_test_completion(self):
        """处理取样测试完成"""
        try:
            logger.info("🎯 取样测试模式：测试完成，处理取样数据")

            # 重要不要在这里停止测试，让正常的停止流程处理
            # 1. 收集测试数据（在测试停止前收集）
            channel_data = self._collect_test_data_for_sampling()
            logger.debug(f" 收集到的测试数据: {len(channel_data) if channel_data else 0}个通道")

            # 修复详细记录收集到的数据
            if channel_data:
                for ch_num, data in channel_data.items():
                    logger.debug(f" 通道{ch_num}数据: V={data.get('voltage', 0):.3f}V, Rs={data.get('rs_value', 0):.3f}mΩ, Rct={data.get('rct_value', 0):.3f}mΩ")

            # 2. 获取取样测试集成管理器（在测试停止前获取）
            sampling_integration_manager = self._get_sampling_integration_manager()
            logger.debug(f" 取样测试集成管理器状态: {'已获取' if sampling_integration_manager else '未获取'}")

            if sampling_integration_manager and channel_data:
                # 3. 处理取样测试完成事件
                logger.debug(f" 准备调用handle_test_completion...")
                sampling_integration_manager.handle_test_completion(channel_data)
                logger.info("✅ 取样测试数据已提交处理")

                # 4. 标记取样测试处理完成，避免后续重复处理
                self._sampling_test_processed = True

            else:
                if not sampling_integration_manager:
                    logger.error("❌ 无法获取取样测试集成管理器")
                if not channel_data:
                    logger.error("❌ 无法收集测试数据")
                logger.error("❌ 无法处理取样测试完成：缺少集成管理器或测试数据")

            # 注意不在这里重置按钮状态，让正常的测试完成流程处理

        except Exception as e:
            logger.error(f"❌ 处理取样测试完成失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _handle_sampling_test_completion_delayed(self):
        """延迟处理取样测试完成（避免阻塞停止流程）"""
        try:
            logger.info("🎯 延迟处理取样测试完成")

            # 修复移除取样测试模式检查，确保对话框能正常显示
            # 即使取样测试模式已退出，也要处理最后一次测试的结果
            logger.info("🎯 执行取样测试完成处理，不检查模式状态")

            # 执行原来的取样测试完成处理
            self._handle_sampling_test_completion()

        except Exception as e:
            logger.error(f"❌ 延迟处理取样测试完成失败: {e}")

    def _force_check_sampling_completion(self):
        """强制检查采样测试完成状态（调试用）"""
        try:
            logger.debug(f" 强制检查采样测试完成状态...")

            # 检查是否在采样测试模式
            sampling_test = self.config_manager.get('test.sampling_test', False)
            if not sampling_test:
                logger.warning("⚠️ 当前不在采样测试模式")
                return

            # 获取采样测试集成管理器
            sampling_integration_manager = self._get_sampling_integration_manager()
            if not sampling_integration_manager:
                logger.error("❌ 无法获取采样测试集成管理器")
                return

            # 获取采样测试管理器
            sampling_manager = sampling_integration_manager.sampling_manager
            if not sampling_manager:
                logger.error("❌ 无法获取采样测试管理器")
                return

            # 获取当前进度
            current_count, valid_count, target_count = sampling_manager.get_progress_info()
            logger.debug(f" 当前采样测试进度: {valid_count}/{target_count} (总测试: {current_count})")

            # 检查是否应该完成
            if current_count >= target_count:
                logger.info("🎉 检测到采样测试应该完成，强制触发完成处理")

                # 强制设置有效样本数为目标数量
                sampling_manager.valid_sample_count = target_count
                logger.debug(f" 强制设置有效样本数为: {target_count}")

                # 触发完成处理
                sampling_integration_manager._handle_sampling_completion()
                logger.info("✅ 强制触发采样测试完成成功")
            else:
                logger.info(f"📊 采样测试尚未完成: 总测试{current_count} < 目标{target_count}")

        except Exception as e:
            logger.error(f"❌ 强制检查采样测试完成失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

    def force_show_parameter_suggestion_dialog(self):
        """强制显示参数建议对话框（调试用）"""
        try:
            logger.debug(f" 强制显示参数建议对话框...")

            # 导入必要的模块
            from ui.dialogs.parameter_suggestion_dialog import ParameterSuggestionDialog
            from PyQt5.QtWidgets import QMessageBox

            # 创建模拟的参数建议数据
            suggestions = {
                'voltage': {
                    'mean': 3.923,
                    'std': 0.05,
                    'min_range': 3.873,
                    'max_range': 3.973,
                    'count': 30
                },
                'rs_value': {
                    'mean': 14.426,
                    'std': 0.169,
                    'min_range': 13.919,
                    'max_range': 14.934,
                    'count': 30
                },
                'rct_value': {
                    'mean': 3.889,
                    'std': 0.604,
                    'min_range': 2.983,
                    'max_range': 4.796,
                    'count': 30
                }
            }

            statistics_data = {
                'total_samples': 30,
                'valid_samples': 30,
                'voltage_stats': suggestions['voltage'],
                'rs_stats': suggestions['rs_value'],
                'rct_stats': suggestions['rct_value']
            }

            logger.info("✅ 模拟参数建议数据创建完成")

            # 创建并显示对话框
            dialog = ParameterSuggestionDialog(
                suggestions=suggestions,
                statistics_data=statistics_data,
                sample_count=30,
                parent=self
            )

            logger.info("✅ 参数建议对话框创建成功")

            # 显示对话框
            result = dialog.exec_()
            logger.info(f"✅ 参数建议对话框显示完成，结果: {result}")

            # 显示成功消息
            QMessageBox.information(
                self,
                "强制显示完成",
                f"参数建议对话框强制显示完成！\n\n"
                f"对话框结果: {'确定' if result == 1 else '取消'}\n\n"
                f"这证明对话框本身功能正常。"
            )

        except Exception as e:
            logger.error(f"❌ 强制显示参数建议对话框失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

            # 显示错误消息
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "强制显示失败",
                f"强制显示参数建议对话框失败：\n\n{str(e)}\n\n"
                f"请检查日志获取详细错误信息。"
            )

    def _check_and_handle_sampling_completion(self):
        """检查并处理采样测试完成"""
        try:
            logger.debug(f" 检查采样测试是否应该完成...")

            # 获取采样测试集成管理器
            sampling_integration_manager = self._get_sampling_integration_manager()
            if not sampling_integration_manager:
                logger.warning("⚠️ 无法获取采样测试集成管理器")
                return

            # 获取采样测试管理器
            sampling_manager = sampling_integration_manager.sampling_manager
            if not sampling_manager:
                logger.warning("⚠️ 无法获取采样测试管理器")
                return

            # 获取进度信息
            current_count, valid_count, target_count = sampling_manager.get_progress_info()
            logger.debug(f" 采样测试进度检查: {valid_count}/{target_count} (总测试: {current_count})")

            # 修复基于总测试次数而不是有效样本数来判断是否完成
            # 因为在采样测试模式下，每次测试都应该被计入，不需要用户确认
            should_complete = False

            if sampling_manager.is_sampling_complete():
                logger.info("🎉 检测到采样测试已完成（基于有效样本数）")
                should_complete = True
            elif current_count >= target_count:
                logger.info(f"🎉 检测到采样测试应该完成（基于总测试次数: {current_count} >= {target_count}）")
                # 强制设置有效样本数为目标数量
                sampling_manager.valid_sample_count = target_count
                logger.debug(f" 强制设置有效样本数为: {target_count}")
                should_complete = True
            else:
                logger.info(f"📊 采样测试尚未完成: 总测试{current_count} < 目标{target_count}")

                # 检查是否有异常情况
                if current_count > target_count * 1.5:  # 如果测试次数超过目标的1.5倍
                    logger.warning(f"⚠️ 检测到可能的异常：测试次数({current_count})超过目标({target_count})的1.5倍")
                    # 自动完成，不询问用户
                    sampling_manager.valid_sample_count = target_count
                    logger.debug(f" 自动设置有效样本数为: {target_count}")
                    should_complete = True

            if should_complete:
                logger.info("🎉 触发采样测试完成处理")
                # Jack修复添加超时保护，防止采样完成处理卡住
                try:
                    from PyQt5.QtCore import QTimer

                    # 设置超时保护
                    timeout_timer = QTimer()
                    timeout_timer.setSingleShot(True)
                    timeout_timer.timeout.connect(lambda: self._handle_sampling_completion_timeout())
                    timeout_timer.start(10000)  # 10秒超时

                    # 执行采样完成处理
                    sampling_integration_manager._handle_sampling_completion()

                    # 如果成功完成，停止超时定时器
                    timeout_timer.stop()

                except Exception as completion_error:
                    logger.error(f"❌ 采样完成处理失败: {completion_error}")
                    # 强制显示参数建议对话框
                    self._force_show_parameter_suggestion_dialog()

        except Exception as e:
            logger.error(f"❌ 检查采样测试完成失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

            # Jack修复如果检查失败，尝试强制完成
            try:
                logger.debug(f" 尝试强制完成采样测试...")
                self._force_show_parameter_suggestion_dialog()
            except Exception as force_error:
                logger.error(f"❌ 强制完成也失败: {force_error}")

    def _on_sampling_completed(self, completion_data: dict):
        """处理取样测试完成信号"""
        try:
            logger.info("🎉 收到取样测试完成信号")

            valid_count = completion_data.get('valid_count', 0)
            suggestions = completion_data.get('suggestions', {})
            statistics = completion_data.get('statistics', {})

            logger.info(f"📊 取样测试完成：有效样本数 {valid_count}")

            # 确保测试已停止
            if self.is_testing:
                logger.info("🛑 取样测试完成，确保停止测试")
                self._on_stop_test()

            # 可以在这里添加其他取样完成后的处理逻辑

        except Exception as e:
            logger.error(f"❌ 处理取样测试完成信号失败: {e}")

    def _handle_sampling_completion_timeout(self):
        """处理采样完成超时"""
        try:
            logger.warning("⚠️ 采样测试完成处理超时")
            # 移除小的参数建议窗体调用
        except Exception as e:
            logger.error(f"❌ 处理采样完成超时失败: {e}")

    def _force_show_parameter_suggestion_dialog(self):
        """强制显示参数建议对话框"""
        try:
            logger.debug(f" 强制显示参数建议对话框...")

            # 移除小的参数建议窗体调用
            logger.debug("移除小的参数建议窗体，只保留大的取样测试结果窗体")

            # 获取采样测试集成管理器
            sampling_integration_manager = self._get_sampling_integration_manager()
            if not sampling_integration_manager:
                logger.warning("⚠️ 无法获取采样测试集成管理器，显示简单完成消息")
                self._show_simple_sampling_completion_message()
                return

            # 获取采样测试管理器
            sampling_manager = sampling_integration_manager.sampling_manager
            if not sampling_manager:
                logger.warning("⚠️ 无法获取采样测试管理器，显示简单完成消息")
                self._show_simple_sampling_completion_message()
                return

            # 尝试获取建议参数
            try:
                suggestions = sampling_manager.get_suggested_parameters()
                statistics_data = sampling_manager.get_current_statistics()
                valid_count = sampling_manager.valid_sample_count

                logger.debug(f" 强制获取参数建议: {len(suggestions) if suggestions else 0}个参数")

                # 如果有参数建议，显示参数建议对话框
                if suggestions:
                    sampling_integration_manager._show_parameter_suggestion_dialog(suggestions, statistics_data, valid_count)
                else:
                    logger.warning("⚠️ 无参数建议数据，显示简单完成消息")
                    self._show_simple_sampling_completion_message()

            except Exception as suggestion_error:
                logger.error(f"❌ 获取参数建议失败: {suggestion_error}")
                self._show_simple_sampling_completion_message()

        except Exception as e:
            logger.error(f"❌ 强制显示参数建议对话框失败: {e}")
            self._show_simple_sampling_completion_message()

    def _show_simple_sampling_completion_message(self):
        """显示简单的采样完成消息"""
        try:
            from PyQt5.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                "采样测试完成",
                "采样测试已完成！\n\n"
                "由于技术原因，无法显示参数建议对话框。\n"
                "请手动检查测试结果并调整参数设置。\n\n"
                "系统已切换到手动模式。"
            )
            logger.info("✅ 简单采样完成消息已显示")

        except Exception as e:
            logger.error(f"❌ 显示简单采样完成消息失败: {e}")

    # 移除：小的参数建议窗体方法已被移除，只保留大的取样测试结果窗体
    # def _show_direct_parameter_suggestion_dialog(self):
    #     """已移除：直接显示参数建议对话框（小窗体）"""
    #     pass

    # 移除：小的参数建议窗体方法已被移除，只保留大的取样测试结果窗体
    # def _show_parameter_suggestion_dialog_direct(self, suggestions, sample_count):
    #     """已移除：直接显示参数建议对话框（小窗体）"""
    #     pass

    # def _apply_suggested_parameters(self, dialog):
    #     """已移除：应用建议的参数（小窗体相关）"""
    #     pass

    def keyPressEvent(self, event):
        """处理按键事件"""
        try:
            # Jack修复添加快捷键 Ctrl+F 来强制触发采样测试完成
            if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                sampling_test = self.config_manager.get('test.sampling_test', False)
                if sampling_test:
                    logger.debug(f" 用户按下Ctrl+F，强制触发采样测试完成")
                    self._force_completion_check()
                else:
                    logger.debug(f" 用户按下Ctrl+F，但当前不是采样测试模式")
                return

            # 移除快捷键 Ctrl+Alt+P 的小参数建议窗体调用
            if event.key() == Qt.Key_P and event.modifiers() == (Qt.ControlModifier | Qt.AltModifier):
                sampling_test = self.config_manager.get('test.sampling_test', False)
                if sampling_test:
                    logger.debug(f" 用户按下Ctrl+Alt+P，但小参数建议窗体已移除")
                else:
                    logger.debug(f" 用户按下Ctrl+Alt+P，但当前不是采样测试模式")
                return

            # Jack修复添加快捷键 Ctrl+Q 来强制停止测试并显示结果
            if event.key() == Qt.Key_Q and event.modifiers() == Qt.ControlModifier:
                logger.debug(f" 用户按下Ctrl+Q，强制停止测试")
                try:
                    # 停止测试
                    self._on_stop_test()

                    # 如果是采样测试模式，显示参数建议对话框
                    sampling_test = self.config_manager.get('test.sampling_test', False)
                    if sampling_test:
                        QTimer.singleShot(2000, self._force_show_parameter_suggestion_dialog)
                except Exception as stop_error:
                    logger.error(f"❌ 强制停止测试失败: {stop_error}")
                return

            # 调用父类的按键处理
            super().keyPressEvent(event)

        except Exception as e:
            logger.error(f"❌ 处理按键事件失败: {e}")
            super().keyPressEvent(event)

    def _start_progress_monitoring(self):
        """启动进度监控（用于检测卡住的测试）"""
        try:
            # Jack修复添加进度监控，防止测试卡在97%
            if not hasattr(self, '_progress_monitor_timer'):
                from PyQt5.QtCore import QTimer
                self._progress_monitor_timer = QTimer()
                self._progress_monitor_timer.timeout.connect(self._check_progress_stuck)

            # 初始化监控状态
            self._last_progress_check = {}
            self._progress_stuck_count = {}

            # 每5秒检查一次进度
            self._progress_monitor_timer.start(5000)
            logger.info("✅ 进度监控已启动")

        except Exception as e:
            logger.error(f"❌ 启动进度监控失败: {e}")

    def _stop_progress_monitoring(self):
        """停止进度监控"""
        try:
            if hasattr(self, '_progress_monitor_timer') and self._progress_monitor_timer:
                self._progress_monitor_timer.stop()
                logger.info("✅ 进度监控已停止")
        except Exception as e:
            logger.error(f"❌ 停止进度监控失败: {e}")

    def _check_progress_stuck(self):
        """检查进度是否卡住"""
        try:
            # 只在采样测试模式下检查
            sampling_test = self.config_manager.get('test.sampling_test', False)
            if not sampling_test:
                return

            # 检查是否正在测试
            if not self.is_testing:
                return

            # 获取通道进度
            channels_container = self.ui_component_manager.get_component('channels_container')
            if not channels_container:
                return

            high_progress_channels = 0
            stuck_channels = 0
            completed_channels = 0

            for channel_num in range(1, 9):
                try:
                    # 获取通道进度
                    channel_widget = getattr(channels_container, f'channel_{channel_num}', None)
                    if not channel_widget:
                        continue

                    # 获取进度值
                    progress_value = getattr(channel_widget, 'current_progress', 0)

                    # Jack修复检查通道状态
                    channel_state = getattr(channel_widget, 'current_state', '')

                    # 检查完成状态
                    if progress_value == 100 or channel_state == 'sampling_completed':
                        completed_channels += 1

                    # 检查高进度通道
                    if progress_value >= 97:
                        high_progress_channels += 1

                        # 检查是否卡住
                        last_progress = self._last_progress_check.get(channel_num, 0)
                        if progress_value == last_progress:
                            stuck_count = self._progress_stuck_count.get(channel_num, 0) + 1
                            self._progress_stuck_count[channel_num] = stuck_count

                            if stuck_count >= 6:  # 30秒没有变化
                                stuck_channels += 1
                        else:
                            self._progress_stuck_count[channel_num] = 0

                        self._last_progress_check[channel_num] = progress_value

                except Exception as channel_error:
                    logger.debug(f"检查通道{channel_num}进度失败: {channel_error}")

            logger.debug(f"🔍 进度监控: 完成{completed_channels}个, 高进度{high_progress_channels}个, 卡住{stuck_channels}个")

            # Jack修复如果所有通道都完成了，立即触发完成处理
            if completed_channels >= 8:
                logger.warning(f"🎉 检测到所有通道都已完成: {completed_channels}/8")
                logger.debug(f" 立即触发采样测试完成处理...")

                # 停止监控，避免重复触发
                self._stop_progress_monitoring()

                # 立即触发完成检查
                self._force_completion_check()
                return

            # 如果有多个通道卡在高进度，触发强制完成
            if high_progress_channels >= 4 and stuck_channels >= 2:
                logger.warning(f"⚠️ 检测到测试可能卡住: {high_progress_channels}个高进度通道, {stuck_channels}个卡住通道")
                logger.debug(f" 触发强制完成检查...")

                # 停止监控，避免重复触发
                self._stop_progress_monitoring()

                # 强制触发完成检查
                QTimer.singleShot(1000, self._force_completion_check)

        except Exception as e:
            logger.error(f"❌ 检查进度卡住失败: {e}")

    def _force_completion_check(self):
        """强制完成检查"""
        try:
            logger.debug(f" 执行强制完成检查...")

            # 检查是否为采样测试模式
            sampling_test = self.config_manager.get('test.sampling_test', False)
            if sampling_test:
                logger.info("🎯 采样测试模式：强制触发完成处理")

                # Jack修复直接处理采样测试完成，跳过可能有问题的检测机制
                try:
                    # 1. 先尝试正常流程
                    logger.debug(f" 步骤1：尝试正常的所有通道就绪流程")
                    self._on_all_channels_ready()

                    # 2. 等待2秒后检查是否成功
                    QTimer.singleShot(2000, self._check_and_force_sampling_completion)

                except Exception as normal_error:
                    logger.error(f"❌ 正常流程失败: {normal_error}")
                    # 直接跳到强制完成
                    self._check_and_force_sampling_completion()
            else:
                logger.info("🎯 非采样测试模式：强制停止测试")
                self._on_stop_test()

        except Exception as e:
            logger.error(f"❌ 强制完成检查失败: {e}")

    def _check_and_force_sampling_completion(self):
        """检查并强制采样测试完成"""
        try:
            logger.debug(f" 步骤2：检查采样测试是否已完成，如未完成则强制完成")

            # 获取采样测试集成管理器
            sampling_integration_manager = self._get_sampling_integration_manager()
            if not sampling_integration_manager:
                logger.warning("⚠️ 无法获取采样测试集成管理器，直接显示简单完成消息")
                self._show_simple_sampling_completion_message()
                return

            # 获取采样测试管理器
            sampling_manager = sampling_integration_manager.sampling_manager
            if not sampling_manager:
                logger.warning("⚠️ 无法获取采样测试管理器，直接显示简单完成消息")
                self._show_simple_sampling_completion_message()
                return

            # 检查是否已经完成
            current_count, valid_count, target_count = sampling_manager.get_progress_info()
            logger.debug(f" 当前采样进度: {valid_count}/{target_count} (总测试: {current_count})")

            if valid_count >= target_count:
                logger.info("✅ 采样测试已完成，触发参数建议对话框")
                sampling_integration_manager._handle_sampling_completion()
            elif current_count >= target_count:
                logger.info(f"✅ 采样测试达到目标次数({current_count}/{target_count})，强制设置为完成状态")

                # 强制设置为完成状态
                sampling_manager.valid_sample_count = target_count
                logger.debug(f" 强制设置有效样本数为: {target_count}")

                # 触发完成处理
                sampling_integration_manager._handle_sampling_completion()
            else:
                logger.debug(f" 采样测试未达到目标次数({current_count}/{target_count})，不触发完成处理")

        except Exception as e:
            logger.error(f"❌ 检查并强制采样测试完成失败: {e}")
            # 最后的备用方案
            self._force_show_parameter_suggestion_dialog()

    def force_sampling_test_completion(self):
        """强制完成采样测试（调试用）"""
        try:
            logger.debug(f" 强制完成采样测试...")

            # 检查是否在采样测试模式
            sampling_test = self.config_manager.get('test.sampling_test', False)
            if not sampling_test:
                logger.warning("⚠️ 当前不在采样测试模式")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "提示", "当前不在采样测试模式")
                return

            # 获取采样测试集成管理器
            sampling_integration_manager = self._get_sampling_integration_manager()
            if not sampling_integration_manager:
                logger.error("❌ 无法获取采样测试集成管理器")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "错误", "无法获取采样测试集成管理器")
                return

            # 获取采样测试管理器
            sampling_manager = sampling_integration_manager.sampling_manager
            if not sampling_manager:
                logger.error("❌ 无法获取采样测试管理器")
                return

            # 获取当前进度
            current_count, valid_count, target_count = sampling_manager.get_progress_info()
            logger.debug(f" 当前采样测试进度: {valid_count}/{target_count} (总测试: {current_count})")

            # 询问用户确认
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "强制完成采样测试",
                f"当前采样测试进度：\n\n"
                f"总测试次数: {current_count}\n"
                f"有效样本数: {valid_count}\n"
                f"目标样本数: {target_count}\n\n"
                f"是否强制完成采样测试并显示参数建议？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                logger.debug(f" 用户确认强制完成采样测试")

                # 如果有效样本数不足，设置为目标数量
                if valid_count < target_count:
                    sampling_manager.valid_sample_count = target_count
                    logger.debug(f" 强制设置有效样本数为目标数量: {target_count}")

                # 触发采样完成处理
                sampling_integration_manager._handle_sampling_completion()
                logger.info("✅ 强制完成采样测试成功")
            else:
                logger.debug(f" 用户取消强制完成采样测试")

        except Exception as e:
            logger.error(f"❌ 强制完成采样测试失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

    def _force_stop_sampling_test(self):
        """强制停止取样测试（多重停止机制）"""
        try:
            logger.info("🛑 开始强制停止取样测试...")

            # 1. 立即设置主窗口测试状态为False
            self.is_testing = False
            logger.info("✅ 主窗口测试状态已设置为False")

            # 2. 停止测试流程管理器
            if hasattr(self, 'test_flow_manager') and self.test_flow_manager:
                try:
                    self.test_flow_manager.stop_test()
                    logger.info("✅ 测试流程管理器已停止")
                except Exception as e:
                    logger.error(f"停止测试流程管理器失败: {e}")

            # 3. 直接停止测试引擎（如果存在）
            if hasattr(self, 'test_engine') and self.test_engine:
                try:
                    self.test_engine.stop_test()
                    logger.info("✅ 测试引擎已停止")
                except Exception as e:
                    logger.error(f"停止测试引擎失败: {e}")

            # 4. 停止设备通信（如果存在）
            if hasattr(self, 'comm_manager') and self.comm_manager:
                try:
                    # 停止所有通道的测试
                    all_channels = list(range(8))  # 0-7对应通道1-8
                    stop_success = self.comm_manager.stop_impedance_measurement(all_channels)
                    if stop_success:
                        logger.info("✅ 设备测试已强制停止")
                    else:
                        logger.warning("⚠️ 设备测试停止失败，但软件停止信号已发送")
                except Exception as e:
                    logger.error(f"停止设备通信失败: {e}")

            # 5. 🔧 关键修复：强制重置UI显示状态
            try:
                logger.debug(f" 开始强制重置UI显示状态...")

                # 重置通道显示状态
                if hasattr(self, 'ui_component_manager'):
                    logger.debug(f" 开始重置通道显示状态...")
                    channels_container = self.ui_component_manager.get_component('channels_container')
                    if channels_container:
                        logger.debug(f" 找到通道容器组件: {type(channels_container).__name__}")

                        # 停止所有通道测试
                        if hasattr(channels_container, 'stop_all_tests'):
                            logger.debug(f" 调用 stop_all_tests()...")
                            channels_container.stop_all_tests()
                            logger.info("✅ 所有通道测试已停止")
                        else:
                            logger.warning("⚠️ 通道容器没有 stop_all_tests 方法")

                        # 重置所有通道显示
                        if hasattr(channels_container, 'reset_all_channels'):
                            logger.debug(f" 调用 reset_all_channels()...")
                            channels_container.reset_all_channels()
                            logger.info("✅ 通道显示已重置")
                        else:
                            logger.warning("⚠️ 通道容器没有 reset_all_channels 方法")

                        # 强制刷新UI显示
                        if hasattr(channels_container, 'channels'):
                            for channel in channels_container.channels:
                                if hasattr(channel, 'update'):
                                    channel.update()  # 强制刷新UI
                            logger.info("✅ 通道UI已强制刷新")

                        # 延迟强制重置UI状态，确保显示正确
                        from PyQt5.QtCore import QTimer
                        def force_reset_ui():
                            try:
                                logger.debug(f" 开始延迟强制重置UI状态...")
                                if hasattr(channels_container, 'channels'):
                                    logger.debug(f" 找到 {len(channels_container.channels)} 个通道组件")
                                    for i, channel in enumerate(channels_container.channels):
                                        channel_num = i + 1
                                        logger.debug(f" 重置通道{channel_num}UI状态...")

                                        # 🎯 使用统一显示管理器强制重置UI状态（按照第一次运行时的标准模式）
                                        if hasattr(channel, 'grade_label') and hasattr(channel, 'result_label'):
                                            from utils.unified_display_manager import reset_channel_display_unified

                                            old_grade = channel.grade_label.text()
                                            old_result = channel.result_label.text()

                                            success = reset_channel_display_unified(channel.grade_label, channel.result_label)
                                            if success:
                                                logger.info(f"  ✅ 通道{channel_num}统一重置: 档位'{old_grade}'->'--' 结果'{old_result}'->'待测试'")
                                            else:
                                                logger.warning(f"  ⚠️ 通道{channel_num}统一重置失败")

                                        if hasattr(channel, 'test_time_label'):
                                            old_time = channel.test_time_label.text()
                                            channel.test_time_label.setText("00:00:00")
                                            logger.info(f"  通道{channel_num}时间标签: '{old_time}' -> '00:00:00'")

                                        if hasattr(channel, 'progress_bar'):
                                            old_value = channel.progress_bar.value()
                                            channel.progress_bar.setValue(0)
                                            logger.info(f"  通道{channel_num}进度条: {old_value}% -> 0%")

                                        if hasattr(channel, 'update'):
                                            channel.update()
                                            logger.info(f"  通道{channel_num}UI已刷新")

                                    logger.info("✅ 延迟UI强制重置完成")
                                else:
                                    logger.error("❌ 通道容器没有 channels 属性")
                            except Exception as e:
                                logger.error(f"❌ 延迟UI强制重置失败: {e}")
                                import traceback
                                logger.error(f"详细错误: {traceback.format_exc()}")

                        QTimer.singleShot(300, force_reset_ui)  # 300ms后强制重置UI
                    else:
                        logger.error("❌ 无法获取通道容器组件")
                else:
                    logger.error("❌ 无法获取UI组件管理器")

                # 重置测试统计
                if hasattr(self, '_reset_test_statistics'):
                    self._reset_test_statistics()

                # 清理测试状态标志
                if hasattr(self, '_all_channels_ready_processed'):
                    self._all_channels_ready_processed = False

                logger.info("✅ 测试状态和UI显示已强制重置")

            except Exception as e:
                logger.error(f"重置测试状态和UI失败: {e}")

            logger.info("✅ 强制停止取样测试完成（包含UI重置）")

        except Exception as e:
            logger.error(f"❌ 强制停止取样测试失败: {e}")
            # 确保至少主窗口状态被重置
            self.is_testing = False

    def _collect_test_data_for_sampling(self) -> dict:
        """收集测试数据用于取样测试"""
        try:
            channel_data = {}

            # 优先从测试结果处理管理器获取数据
            try:
                if hasattr(self.test_flow_manager, 'test_flow_controller') and \
                   hasattr(self.test_flow_manager.test_flow_controller, 'test_executor') and \
                   hasattr(self.test_flow_manager.test_flow_controller.test_executor, 'test_result_processing_manager'):

                    result_processing_manager = self.test_flow_manager.test_flow_controller.test_executor.test_result_processing_manager

                    # 获取启用的通道
                    enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))

                    for channel_num in enabled_channels:
                        try:
                            # 从测试结果处理管理器获取通道数据
                            test_data = result_processing_manager._get_channel_test_data_from_result_manager(channel_num)

                            if test_data and (test_data.get('voltage', 0) > 0 or test_data.get('rs_value', 0) > 0 or test_data.get('rct_value', 0) > 0):
                                channel_data[channel_num] = {
                                    'voltage': test_data.get('voltage', 0.0),
                                    'rs_value': test_data.get('rs_value', 0.0),
                                    'rct_value': test_data.get('rct_value', 0.0),
                                    'w_impedance': 0.0,  # 取样测试暂不使用W阻抗
                                    'is_pass': None,  # 取样测试不判断合格性
                                    'grade': 'Sampling',
                                    'impedance_data': test_data.get('impedance_data', {}),
                                    'frequency_data': test_data.get('frequency_data', {})
                                }
                                logger.debug(f"✅ 从测试结果管理器收集通道{channel_num}数据: 电压={test_data.get('voltage', 0):.3f}V, Rs={test_data.get('rs_value', 0):.3f}mΩ, Rct={test_data.get('rct_value', 0):.3f}mΩ")
                            else:
                                logger.debug(f"⚠️ 通道{channel_num}从测试结果管理器获取的数据无效，跳过")

                        except Exception as e:
                            logger.error(f"❌ 从测试结果管理器收集通道{channel_num}数据失败: {e}")

                    if channel_data:
                        logger.info(f"📊 从测试结果管理器收集取样测试数据完成，通道数量: {len(channel_data)}")
                        return channel_data
                    else:
                        logger.warning("⚠️ 从测试结果管理器未获取到有效数据，尝试从UI组件获取")

            except Exception as e:
                logger.error(f"❌ 从测试结果管理器收集数据失败: {e}")

            # 备用方案从UI组件获取数据
            channel_display = self.ui_component_manager.get_component('channel_display')
            if not channel_display or not hasattr(channel_display, 'channel_widgets'):
                logger.warning("⚠️ 无法获取通道显示组件，尝试从数据库获取最新测试结果")
                # 最后备用方案从数据库获取最新测试结果
                return self._get_latest_test_results_from_database()

            # 遍历所有通道收集数据
            for channel_num, channel_widget in channel_display.channel_widgets.items():
                try:
                    # 直接从通道组件属性获取数据（更可靠）
                    voltage = getattr(channel_widget, 'voltage', 0.0)
                    rs_value = getattr(channel_widget, 'rs_value', 0.0)
                    rct_value = getattr(channel_widget, 'rct_value', 0.0)

                    # 检查是否有有效数据
                    if voltage > 0 or rs_value > 0 or rct_value > 0:
                        channel_data[channel_num] = {
                            'voltage': voltage,
                            'rs_value': rs_value,
                            'rct_value': rct_value,
                            'w_impedance': 0.0,  # 取样测试暂不使用W阻抗
                            'is_pass': None,  # 取样测试不判断合格性
                            'grade': 'Sampling'
                        }
                        logger.debug(f"✅ 从UI组件收集通道{channel_num}数据: 电压={voltage:.3f}V, Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")
                    else:
                        logger.debug(f"⚠️ 通道{channel_num}无有效数据，跳过")

                except Exception as e:
                    logger.error(f"❌ 收集通道{channel_num}数据失败: {e}")

            logger.info(f"📊 取样测试数据收集完成，通道数量: {len(channel_data)}")
            return channel_data

        except Exception as e:
            logger.error(f"❌ 收集取样测试数据失败: {e}")
            return {}

    def _get_latest_test_results_from_database(self) -> dict:
        """从数据库获取最新的测试结果"""
        try:
            logger.debug(f" 尝试从数据库获取最新测试结果")

            # 优先从测试流程管理器获取数据库管理器
            database_manager = None

            # 方法1：从测试流程管理器获取
            if hasattr(self, 'test_flow_manager') and self.test_flow_manager and \
               hasattr(self.test_flow_manager, 'test_flow_controller') and \
               self.test_flow_manager.test_flow_controller and \
               hasattr(self.test_flow_manager.test_flow_controller, 'test_executor') and \
               self.test_flow_manager.test_flow_controller.test_executor and \
               hasattr(self.test_flow_manager.test_flow_controller.test_executor, 'test_result_manager') and \
               hasattr(self.test_flow_manager.test_flow_controller.test_executor.test_result_manager, 'database_manager'):
                database_manager = self.test_flow_manager.test_flow_controller.test_executor.test_result_manager.database_manager
                logger.debug(f" 从测试流程管理器获取数据库管理器")

            # 方法2：从主窗口获取
            elif hasattr(self, 'database_manager') and self.database_manager:
                database_manager = self.database_manager
                logger.debug(f" 从主窗口获取数据库管理器")

            # 方法3：尝试创建数据库管理器实例
            else:
                try:
                    from data.database_manager import DatabaseManager
                    database_manager = DatabaseManager()
                    logger.debug(f" 从data路径创建数据库管理器实例")
                except Exception as e:
                    logger.error(f"❌ 从data路径创建数据库管理器失败: {e}")
                    # 方法4：尝试从其他路径创建
                    try:
                        from backend.database_manager import DatabaseManager
                        database_manager = DatabaseManager()
                        logger.debug(f" 从backend路径创建数据库管理器实例")
                    except Exception as e2:
                        logger.error(f"❌ 从backend路径创建数据库管理器也失败: {e2}")
                        # 方法5：最后尝试utils路径
                        try:
                            from utils.database_manager import DatabaseManager
                            database_manager = DatabaseManager()
                            logger.debug(f" 从utils路径创建数据库管理器实例")
                        except Exception as e3:
                            logger.error(f"❌ 从utils路径创建数据库管理器也失败: {e3}")

            if not database_manager:
                logger.error("❌ 无法获取数据库管理器")
                return {}

            # 获取启用的通道
            enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))
            channel_data = {}

            # 为每个启用的通道获取最新测试结果
            for channel_num in enabled_channels:
                try:
                    # 使用数据库管理器的get_test_results方法获取最新测试结果
                    # 获取该通道的最新测试结果（默认按时间倒序排列）
                    test_results = database_manager.get_test_results(
                        channel_number=channel_num,
                        limit=1
                    )

                    if test_results and len(test_results) > 0:
                        result = test_results[0]
                        # 修复详细记录数据库中的原始数据，处理None值
                        voltage = result.get('voltage', 0.0) or 0.0
                        rs_value = result.get('rs_value', 0.0) or 0.0
                        rct_value = result.get('rct_value', 0.0) or 0.0
                        w_impedance = result.get('w_impedance', 0.0) or 0.0

                        logger.debug(f" 通道{channel_num}数据库原始数据: 电压={voltage:.3f}V, Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ, W={w_impedance:.3f}mΩ")

                        channel_data[channel_num] = {
                            'voltage': voltage,
                            'rs_value': rs_value,
                            'rct_value': rct_value,
                            'w_impedance': w_impedance,
                            'is_pass': None,  # 取样测试不判断合格性
                            'grade': 'Sampling'
                        }
                        logger.debug(f"✅ 从数据库获取通道{channel_num}数据: 电压={voltage:.3f}V, Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")
                    else:
                        logger.debug(f"⚠️ 通道{channel_num}在数据库中无最新测试结果")

                except Exception as e:
                    logger.error(f"❌ 从数据库获取通道{channel_num}数据失败: {e}")
                    import traceback
                    logger.error(f"详细错误: {traceback.format_exc()}")

            logger.info(f"📊 从数据库获取取样测试数据完成，通道数量: {len(channel_data)}")
            return channel_data

        except Exception as e:
            logger.error(f"❌ 从数据库获取最新测试结果失败: {e}")
            return {}

    def _get_sampling_integration_manager(self):
        """获取取样测试集成管理器"""
        try:
            # 检查是否已存在集成管理器
            if hasattr(self, '_sampling_integration_manager') and self._sampling_integration_manager:
                logger.debug(f" 使用已存在的取样测试集成管理器")
                return self._sampling_integration_manager

            # 优先尝试从测试流程管理器获取测试流程控制器
            test_flow_controller = None

            # 方法1：从测试流程管理器获取
            if hasattr(self, 'test_flow_manager') and self.test_flow_manager and \
               hasattr(self.test_flow_manager, 'test_flow_controller') and \
               self.test_flow_manager.test_flow_controller:
                test_flow_controller = self.test_flow_manager.test_flow_controller
                logger.debug(f" 从测试流程管理器获取测试流程控制器")

            # 方法2：尝试从其他路径获取
            elif hasattr(self, 'test_flow_manager') and self.test_flow_manager:
                # 检查是否有其他属性可以获取控制器
                for attr_name in ['controller', 'flow_controller', 'test_controller']:
                    if hasattr(self.test_flow_manager, attr_name):
                        controller = getattr(self.test_flow_manager, attr_name)
                        if controller:
                            test_flow_controller = controller
                            logger.debug(f" 从测试流程管理器的{attr_name}属性获取控制器")
                            break

            if not test_flow_controller:
                logger.error("❌ 无法创建取样测试集成管理器：缺少测试流程控制器")
                # 尝试创建一个简化的集成管理器，只用于显示结果确认对话框
                try:
                    from backend.sampling_test_integration_manager import SamplingTestIntegrationManager

                    # 创建简化版本，不依赖测试流程控制器
                    self._sampling_integration_manager = SamplingTestIntegrationManager(
                        config_manager=self.config_manager,
                        test_flow_controller=None,  # 传入None，让管理器内部处理
                        parent=self
                    )

                    # 连接取样完成信号
                    self._sampling_integration_manager.sampling_completed.connect(self._on_sampling_completed)
                    logger.info("✅ 取样完成信号已连接")

                    logger.info("✅ 创建简化版取样测试集成管理器成功")
                    return self._sampling_integration_manager

                except Exception as simple_error:
                    logger.error(f"❌ 创建简化版取样测试集成管理器失败: {simple_error}")
                    return None

            # 创建取样测试集成管理器
            try:
                from backend.sampling_test_integration_manager import SamplingTestIntegrationManager

                self._sampling_integration_manager = SamplingTestIntegrationManager(
                    config_manager=self.config_manager,
                    test_flow_controller=test_flow_controller,
                    parent=self
                )

                # 连接取样完成信号
                self._sampling_integration_manager.sampling_completed.connect(self._on_sampling_completed)
                logger.info("✅ 取样完成信号已连接")

                logger.info("✅ 取样测试集成管理器创建成功")
                return self._sampling_integration_manager

            except Exception as create_error:
                logger.error(f"❌ 创建取样测试集成管理器失败: {create_error}")
                import traceback
                logger.error(f"创建错误详情: {traceback.format_exc()}")
                return None

        except Exception as e:
            logger.error(f"❌ 获取取样测试集成管理器失败: {e}")
            import traceback
            logger.error(f"获取错误详情: {traceback.format_exc()}")
            return None

    def _clean_test_states_for_auto_detect(self):
        """为自动侦测模式清理测试状态"""
        try:
            logger.debug("🧹 开始清理测试状态...")

            # 获取通道组件
            channel_widgets = []
            if hasattr(self, 'ui_component_manager'):
                channel_display = self.ui_component_manager.get_component('channel_display')
                if channel_display and hasattr(channel_display, 'channel_widgets'):
                    channel_widgets = list(channel_display.channel_widgets.values())

            # 使用测试状态清理器
            if channel_widgets:
                try:
                    from backend.test_state_cleaner import TestStateCleaner
                    cleaner = TestStateCleaner()
                    success = cleaner.clean_all_test_states(channel_widgets)
                    if success:
                        logger.debug("✅ 测试状态清理成功")
                    else:
                        logger.warning("⚠️ 测试状态清理部分失败")
                except Exception as e:
                    logger.error(f"使用测试状态清理器失败: {e}")

        except Exception as e:
            logger.error(f"清理测试状态失败: {e}")

    def _reset_test_flow_manager_state(self):
        """重置测试流程管理器的内部状态"""
        try:
            logger.debug("🔄 重置测试流程管理器内部状态...")

            # 重置测试流程控制器状态
            if hasattr(self.test_flow_manager, 'test_flow_controller') and self.test_flow_manager.test_flow_controller:
                controller = self.test_flow_manager.test_flow_controller

                # 重置控制器状态
                if hasattr(controller, 'is_testing'):
                    controller.is_testing = False
                if hasattr(controller, 'current_state'):
                    controller.current_state = 'idle'  # 使用字符串而不是枚举
                if hasattr(controller, 'stop_event'):
                    controller.stop_event.clear()

                # 清理测试状态
                if hasattr(controller, '_cleanup_test_state'):
                    controller._cleanup_test_state()

                logger.debug("测试流程控制器状态已重置")

            # 重置其他可能的状态标志
            if hasattr(self.test_flow_manager, '_test_state'):
                self.test_flow_manager._test_state = 'idle'

            # 清理可能的测试线程引用
            if hasattr(self.test_flow_manager, 'test_thread'):
                self.test_flow_manager.test_thread = None

            logger.debug("✅ 测试流程管理器内部状态重置完成")

        except Exception as e:
            logger.error(f"重置测试流程管理器内部状态失败: {e}")

    def _start_battery_removal_monitoring(self):
        """启动电池移除监控"""
        try:
            logger.info("🔋 启动电池移除监控，等待所有电池移除后自动弹出新一轮测试引导")

            # 设置状态
            self._waiting_for_battery_removal = True
            self._all_batteries_removed = False

            # 启动定时器定期检查电池状态（每2秒检查一次）
            if not hasattr(self, '_battery_removal_timer'):
                self._battery_removal_timer = QTimer()
                self._battery_removal_timer.timeout.connect(self._check_all_batteries_removed)

            self._battery_removal_timer.start(2000)  # 每2秒检查一次
            logger.info("🔋 电池移除监控定时器已启动（每2秒检查一次）")

            # 立即检查当前电池状态
            self._check_all_batteries_removed()

        except Exception as e:
            logger.error(f"启动电池移除监控失败: {e}")

    def _check_all_batteries_removed(self):
        """检查所有使能通道的电池是否都已移除"""
        try:
            if not self._waiting_for_battery_removal:
                logger.debug("🔋 未在等待电池移除状态，跳过检查")
                return

            # 获取使能通道
            enabled_channels = self.config_manager.get('test.enabled_channels', [1, 2, 3, 4, 5, 6, 7, 8])
            logger.debug(f"🔋 检查电池移除状态，使能通道: {enabled_channels}")

            # 检查所有使能通道是否都没有电池
            all_removed = True
            connected_channels = []

            if self.battery_detection_manager:
                for channel in enabled_channels:
                    is_connected = self._is_battery_connected_in_channel(channel)
                    logger.debug(f"🔋 通道{channel}电池连接状态: {is_connected}")

                    if is_connected:
                        all_removed = False
                        connected_channels.append(channel)
            else:
                logger.warning("🔋 电池检测管理器不可用")
                return

            logger.info(f"🔋 电池移除检查结果: 全部移除={all_removed}, 仍连接的通道={connected_channels}")

            if all_removed and not self._all_batteries_removed:
                logger.info("🔋 检测到所有电池已移除，准备弹出新一轮测试引导界面")
                self._all_batteries_removed = True
                self._waiting_for_battery_removal = False

                # 停止电池移除监控定时器
                if hasattr(self, '_battery_removal_timer') and self._battery_removal_timer.isActive():
                    self._battery_removal_timer.stop()
                    logger.info("🔋 电池移除监控定时器已停止")

                # 延迟1秒后弹出新一轮测试引导界面
                QTimer.singleShot(1000, self._show_next_round_test_guide)
            else:
                logger.debug(f"🔋 还有{len(connected_channels)}个通道连接电池，继续等待")

        except Exception as e:
            logger.error(f"检查所有电池移除状态失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

    def _is_battery_connected_in_channel(self, channel):
        """检查指定通道是否连接了电池"""
        try:
            if not self.battery_detection_manager:
                logger.debug(f"🔋 通道{channel}: 电池检测管理器不可用")
                return False

            # 方法1：使用get_channel_state方法（推荐）
            if hasattr(self.battery_detection_manager, 'get_channel_state'):
                channel_state = self.battery_detection_manager.get_channel_state(channel)
                if channel_state:
                    battery_state = channel_state.get('battery_state', 'unknown')
                    voltage = channel_state.get('last_voltage', 0.0)
                    logger.debug(f"🔋 通道{channel}: 状态={battery_state}, 电压={voltage:.3f}V")
                    return battery_state == 'connected'
                else:
                    logger.debug(f"🔋 通道{channel}: 无法获取通道状态")
                    return False

            # 方法2：直接访问channels属性
            elif hasattr(self.battery_detection_manager, 'channels'):
                channel_info = self.battery_detection_manager.channels.get(channel)
                if channel_info:
                    # 检查电池状态
                    if hasattr(channel_info, 'battery_state'):
                        state_value = channel_info.battery_state.value
                        voltage = getattr(channel_info, 'last_voltage', 0.0)
                        logger.debug(f"🔋 通道{channel}: 状态={state_value}, 电压={voltage:.3f}V")
                        return state_value == 'connected'
                    # 备用：检查电压范围（不推荐，但作为后备）
                    elif hasattr(channel_info, 'last_voltage'):
                        voltage = channel_info.last_voltage
                        is_connected = 2.5 <= voltage <= 4.0  # 正常电池电压范围
                        logger.debug(f"🔋 通道{channel}: 仅电压判断，电压={voltage:.3f}V, 连接={is_connected}")
                        return is_connected
                else:
                    logger.debug(f"🔋 通道{channel}: 通道信息不存在")
                    return False
            else:
                logger.debug(f"🔋 通道{channel}: 电池检测管理器API不兼容")
                return False

        except Exception as e:
            logger.error(f"检查通道{channel}电池连接状态失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False

    def _show_next_round_test_guide(self):
        """显示新一轮测试引导界面"""
        try:
            logger.info("🔋 显示新一轮电池侦测模式测试引导界面")

            # 更新状态栏
            try:
                status_bar = self.ui_component_manager.get_component('status_bar')
                if status_bar and hasattr(status_bar, 'set_system_status'):
                    status_bar.set_system_status("准备新一轮测试，请插入电池", "info")
            except Exception as e:
                logger.error(f"更新状态栏失败: {e}")

            # 获取测试控制组件并显示引导界面
            test_control = self.ui_component_manager.get_component('test_control')
            if test_control and hasattr(test_control, '_show_battery_detection_guide'):
                test_control._show_battery_detection_guide()
            else:
                logger.error("无法找到测试控制组件或引导方法")

        except Exception as e:
            logger.error(f"显示新一轮测试引导界面失败: {e}")

    def _mark_battery_detection_test_completed(self):
        """标记电池检测管理器中的测试完成状态"""
        try:
            if hasattr(self, 'battery_detection_manager') and self.battery_detection_manager:
                # 获取启用的通道
                enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))

                # 标记所有启用通道的测试完成
                for channel_num in enabled_channels:
                    self.battery_detection_manager.mark_test_completed(channel_num)

                logger.info(f"已标记通道{enabled_channels}测试完成，等待电池移除")
            else:
                logger.debug("电池检测管理器未找到，跳过测试完成标记")
        except Exception as e:
            logger.error(f"标记电池检测测试完成失败: {e}")

    def _restart_battery_detection_after_test(self):
        """测试完成后重新启动电池检测（兼容性方法）"""
        try:
            logger.info("🔄 测试完成，重新启动电池检测...")

            # 延迟重启电池检测，给系统一些时间完成清理
            QTimer.singleShot(2000, self._do_restart_battery_detection)

        except Exception as e:
            logger.error(f"重新启动电池检测失败: {e}")

    def _do_restart_battery_detection(self):
        """实际执行电池检测重启"""
        try:
            if hasattr(self, 'battery_detection_manager'):
                # 先停止当前的电池检测
                try:
                    self.battery_detection_manager.stop_detection()
                    logger.debug("已停止当前电池检测")
                except Exception as e:
                    logger.debug(f"停止电池检测时出现异常（可能已停止）: {e}")

                # 短暂延迟确保停止完成
                import time
                time.sleep(0.1)

                # 获取启用的通道
                enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))

                # 重新启动电池检测
                self.battery_detection_manager.start_detection(enabled_channels)
                logger.info(f"✅ 电池检测已重新启动，监控通道: {enabled_channels}")
            else:
                logger.warning("⚠️ 电池检测管理器未找到，无法重新启动")

        except Exception as e:
            logger.error(f"执行电池检测重启失败: {e}")

    def _on_device_status_changed(self, connected: bool):
        """设备状态变更（兼容性方法）"""
        logger.debug(f"设备状态: {'已连接' if connected else '未连接'}")

    # ===== 电池检测回调方法 =====

    def _on_battery_removed(self, channel_num: int, voltage: float):
        """电池移除回调处理"""
        try:
            # 检查是否启用自动侦测模式
            auto_detect = self.config_manager.get('test.auto_detect', False)
            if not auto_detect:
                logger.debug(f"自动侦测模式未启用，忽略通道{channel_num}电池移除事件（电压={voltage:.3f}V）")
                return

            logger.info(f"🔋 主窗口收到电池移除事件: 通道{channel_num}, 电压{voltage:.3f}V")

            # 使用Qt的线程安全机制调用主线程方法
            if not self._is_main_thread():
                QTimer.singleShot(0, lambda: self._on_battery_removed_main_thread(channel_num, voltage))
                return

            self._on_battery_removed_main_thread(channel_num, voltage)

        except Exception as e:
            logger.error(f"电池移除事件处理失败: {e}")

    def _on_battery_removed_main_thread(self, channel_num: int, voltage: float):
        """在主线程中处理电池移除事件"""
        try:
            logger.debug(f"在主线程中处理电池移除: 通道{channel_num}, 电压{voltage:.3f}V")

            # 通知通道显示组件更新状态
            try:
                channels_container = self.ui_component_manager.get_component('channels_container')
                if channels_container:
                    channel_widget = channels_container.get_channel(channel_num)
                    if channel_widget and hasattr(channel_widget, 'on_battery_removed'):
                        channel_widget.on_battery_removed()
                        logger.debug(f"通道{channel_num}电池移除UI更新成功")
                    else:
                        logger.debug(f"通道{channel_num}组件不存在或无on_battery_removed方法")
                else:
                    logger.debug("通道容器组件未找到")
            except Exception as ui_error:
                logger.error(f"更新通道{channel_num}电池移除UI失败: {ui_error}")
                import traceback
                logger.error(f"UI更新详细错误: {traceback.format_exc()}")
                # 不重新抛出异常，避免闪退

            # 🎯 检查是否所有电池都已移除，如果是则弹出新一轮测试引导
            if self._waiting_for_battery_removal:
                self._check_all_batteries_removed()

        except Exception as e:
            logger.error(f"主线程处理电池移除事件失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _on_new_battery_detected(self, channel_num: int, voltage: float):
        """新电池检测回调处理"""
        try:
            # 检查是否启用自动侦测模式
            auto_detect = self.config_manager.get('test.auto_detect', False)
            if not auto_detect:
                logger.debug(f"自动侦测模式未启用，忽略通道{channel_num}新电池检测事件（电压={voltage:.3f}V）")
                return

            logger.info(f"🔋 通道{channel_num}检测到新电池插入，电压: {voltage:.3f}V")

            # 使用Qt的线程安全机制调用主线程方法
            if not self._is_main_thread():
                QTimer.singleShot(0, lambda: self._on_new_battery_detected_main_thread(channel_num, voltage))
                return

            self._on_new_battery_detected_main_thread(channel_num, voltage)

        except Exception as e:
            logger.error(f"新电池检测事件处理失败: {e}")

    def _on_new_battery_detected_main_thread(self, channel_num: int, voltage: float):
        """在主线程中处理新电池检测事件"""
        try:
            # 改为INFO级别，确保能看到日志
            logger.info(f"📱 在主线程中处理新电池检测: 通道{channel_num}, 电压{voltage:.3f}V")

            # 检查是否启用自动侦测模式
            auto_detect = self.config_manager.get('test.auto_detect', False)
            if not auto_detect:
                logger.info("自动侦测模式未启用，跳过自动测试启动")
                return

            # 检查当前是否正在测试
            if self.is_testing:
                logger.info("当前正在测试中，跳过自动测试启动")
                return

            # 🎯 如果正在等待电池移除，重置状态
            if self._waiting_for_battery_removal:
                logger.info("🔋 检测到新电池插入，重置电池移除等待状态")
                self._waiting_for_battery_removal = False
                self._all_batteries_removed = False

                # 停止电池移除监控定时器
                if hasattr(self, '_battery_removal_timer') and self._battery_removal_timer.isActive():
                    self._battery_removal_timer.stop()
                    logger.info("🔋 电池移除监控定时器已停止（检测到新电池插入）")

            # 电池检测模式智能启动逻辑
            logger.info(f"🔋 电池检测模式：检测到通道{channel_num}新电池插入")

            # 更新电池状态显示
            try:
                # 更新通道显示组件中的电池状态
                channels_container = self.ui_component_manager.get_component('channels_container')
                if channels_container:
                    channel_widget = channels_container.get_channel(channel_num)
                    if channel_widget:
                        # 优先使用电池状态更新方法
                        if hasattr(channel_widget, 'update_battery_status'):
                            channel_widget.update_battery_status('connected', voltage)
                            logger.info(f"✅ 已更新通道{channel_num}电池状态显示: connected ({voltage:.3f}V)")
                        elif hasattr(channel_widget, 'on_new_battery_detected'):
                            channel_widget.on_new_battery_detected()
                            logger.info(f"✅ 已调用通道{channel_num}新电池检测方法")
                    else:
                        logger.warning(f"⚠️ 通道{channel_num}组件未找到")
                else:
                    logger.warning("⚠️ 通道容器组件未找到")

                # 更新状态栏显示
                status_bar = self.ui_component_manager.get_component('status_bar')
                if status_bar and hasattr(status_bar, 'set_battery_status'):
                    status_bar.set_battery_status(channel_num, 'connected', voltage)
                    logger.info(f"✅ 已更新状态栏电池状态显示")

            except Exception as ui_error:
                logger.error(f"更新UI状态失败: {ui_error}")
                import traceback
                logger.error(f"UI更新详细错误: {traceback.format_exc()}")

            # 🎯 电池侦测模式核心逻辑：检查所有启用通道是否都已插入电池
            if self._check_all_enabled_channels_have_batteries():
                logger.info("🚀 所有启用通道都已检测到电池，准备自动启动全通道错频测试")
                try:
                    status_bar = self.ui_component_manager.get_component('status_bar')
                    if status_bar and hasattr(status_bar, 'set_system_status'):
                        status_bar.set_system_status("所有通道电池就绪，自动启动错频测试", "info")

                    # 延迟启动测试，确保UI更新完成和避免同频干扰（参数化）
                    try:
                        initial_delay_ms = self.config_manager.get('test.auto_detect.print_wait.initial_delay_ms', 1000)
                    except Exception:
                        initial_delay_ms = 1000
                    QTimer.singleShot(int(initial_delay_ms), self._auto_start_test_for_battery_detection_guarded)
                    logger.info(f"✅ 已安排延迟启动全通道错频测试（延迟 {initial_delay_ms} ms）")
                except Exception as timer_error:
                    logger.error(f"安排延迟测试启动失败: {timer_error}")
            else:
                # 还有通道未插入电池，等待
                enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))
                ready_count = self._count_ready_batteries()
                total_count = len(enabled_channels)
                logger.info(f"⏳ 通道{channel_num}电池已就绪，等待其他启用通道插入电池... ({ready_count}/{total_count})")

                try:
                    status_bar = self.ui_component_manager.get_component('status_bar')
                    if status_bar and hasattr(status_bar, 'set_system_status'):
                        status_bar.set_system_status(f"等待电池插入: {ready_count}/{total_count} 通道就绪", "info")
                except Exception as e:
                    logger.error(f"更新状态栏提示失败: {e}")

        except Exception as e:
            logger.error(f"主线程处理新电池检测事件失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _check_all_enabled_channels_have_batteries(self) -> bool:
        """检查所有启用通道是否都已插入电池"""
        try:
            # 获取启用的通道列表
            enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))

            # 检查电池检测管理器是否可用
            if not hasattr(self, 'battery_detection_manager'):
                logger.warning("电池检测管理器未找到，无法检查电池状态")
                return False

            # 检查每个启用通道的电池状态
            for channel_num in enabled_channels:
                if hasattr(self.battery_detection_manager, 'channels'):
                    channel_state = self.battery_detection_manager.channels.get(channel_num)
                    if not channel_state or channel_state.battery_state.value != 'connected':
                        logger.debug(f"通道{channel_num}电池未就绪")
                        return False
                else:
                    # 备用方法：通过电压检查
                    try:
                        voltage = self._get_channel_voltage(channel_num)
                        if voltage < 2.0:  # 电压阈值
                            logger.debug(f"通道{channel_num}电压过低: {voltage:.3f}V")
                            return False
                    except Exception as e:
                        logger.debug(f"检查通道{channel_num}电压失败: {e}")
                        return False

            logger.info(f"✅ 所有启用通道({enabled_channels})都已检测到电池")
            return True

        except Exception as e:
            logger.error(f"检查电池状态失败: {e}")
            return False

    def _count_ready_batteries(self) -> int:
        """统计已就绪的电池数量"""
        try:
            enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))
            ready_count = 0

            for channel_num in enabled_channels:
                if hasattr(self, 'battery_detection_manager') and hasattr(self.battery_detection_manager, 'channels'):
                    channel_state = self.battery_detection_manager.channels.get(channel_num)
                    if channel_state and channel_state.battery_state.value == 'connected':
                        ready_count += 1
                else:
                    # 备用方法：通过电压检查
                    try:
                        voltage = self._get_channel_voltage(channel_num)
                        if voltage >= 2.0:
                            ready_count += 1
                    except:
                        pass

            return ready_count

        except Exception as e:
            logger.error(f"统计电池数量失败: {e}")
            return 0

    def _get_channel_voltage(self, channel_num: int) -> float:
        """获取指定通道的电压"""
        try:
            if hasattr(self, 'comm_manager') and self.comm_manager.is_connected:
                # 这里应该调用通信管理器获取电压
                # 暂时返回模拟值，实际应该从设备读取
                return 3.7  # 模拟电压值
            return 0.0
        except Exception as e:
            logger.error(f"获取通道{channel_num}电压失败: {e}")
            return 0.0

    def _auto_start_test_for_battery_detection_guarded(self):
        """带打印完成守卫的自动启动测试（电池侦测模式）"""
        try:
            # 如果存在打印管理器，则检查打印状态
            if hasattr(self, 'label_print_manager') and self.label_print_manager:
                try:
                    queue_size = self.label_print_manager.get_queue_size()
                    current_job_active = (self.label_print_manager.current_job is not None)
                    if queue_size > 0 or current_job_active:
                        logger.info(f"🖨️ [电池侦测] 打印未完成（队列={queue_size}, 当前任务活跃={current_job_active}），准备等待后重试")
                        # 参数化等待间隔并提示状态栏
                        try:
                            retry_delay_ms = self.config_manager.get('test.auto_detect.print_wait.retry_delay_ms', 2000)
                            hint_enabled = self.config_manager.get('test.auto_detect.print_wait.show_hint', True)
                        except Exception:
                            retry_delay_ms = 2000
                            hint_enabled = True
                        # 状态栏提示
                        try:
                            if hint_enabled:
                                status_bar = self.ui_component_manager.get_component('status_bar')
                                if status_bar and hasattr(status_bar, 'set_system_status'):
                                    status_bar.set_system_status("打印进行中，等待完成后自动开始下一轮", "info")
                        except Exception:
                            pass
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(int(retry_delay_ms), self._auto_start_test_for_battery_detection_guarded)
                        return
                except Exception as e:
                    logger.warning(f"检查打印状态失败，继续按常规流程启动: {e}")

            # 打印已完成或无打印管理器，按常规流程启动
            self._auto_start_test_for_battery_detection()
        except Exception as e:
            logger.error(f"守卫式自动启动失败: {e}")

    def _auto_start_test_for_battery_detection(self):
        """电池侦测模式自动启动测试"""
        try:
            logger.info("🚀 电池侦测模式：自动启动全通道错频测试")

            # 检查是否正在测试
            if self.is_testing:
                logger.warning("当前正在测试中，跳过自动启动")
                return

            # 模拟点击开始测试按钮
            test_control = self.ui_component_manager.get_component('test_control')
            if test_control and hasattr(test_control, 'start_test_clicked'):
                logger.info("✅ 通过测试控制组件自动启动测试")
                test_control.start_test_clicked()
            else:
                logger.warning("测试控制组件未找到，无法自动启动测试")

        except Exception as e:
            logger.error(f"电池侦测模式自动启动测试失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _handle_battery_detection_mode_change(self, enabled: bool = None):
        """处理电池侦测模式变更"""
        try:
            if enabled is None:
                enabled = self.config_manager.get('test.auto_detect', False)

            if enabled:
                logger.info("🔋 电池侦测模式已启用，重新设置回调函数")
                # 重新设置电池检测回调函数
                self._setup_battery_detection_callbacks()

                # 如果设备已连接，启动电池检测
                if hasattr(self, 'comm_manager') and self.comm_manager.is_connected:
                    self._do_start_battery_detection()

                # 更新测试模式显示
                test_control = self.ui_component_manager.get_component('test_control')
                if test_control and hasattr(test_control, 'update_test_mode_display'):
                    test_control.update_test_mode_display()

            else:
                logger.info("🔋 电池侦测模式已禁用，停止电池检测")
                # 停止电池检测
                if hasattr(self, 'battery_detection_manager'):
                    self.battery_detection_manager.stop_detection()

                # 更新测试模式显示
                test_control = self.ui_component_manager.get_component('test_control')
                if test_control and hasattr(test_control, 'update_test_mode_display'):
                    test_control.update_test_mode_display()

        except Exception as e:
            logger.error(f"处理电池侦测模式变更失败: {e}")

    def _on_battery_status_updated(self, channel_num: int, status: str, voltage: float):
        """电池状态更新回调处理"""
        try:
            logger.info(f"🔋 [回调] 收到通道{channel_num}电池状态更新: {status}, 电压{voltage:.3f}V")

            # 检查是否启用自动侦测模式
            auto_detect = self.config_manager.get('test.auto_detect', False)
            if not auto_detect:
                logger.debug(f"自动侦测模式未启用，忽略通道{channel_num}状态更新（状态={status}, 电压={voltage:.3f}V）")
                return

            logger.info(f"🔋 [回调] 自动侦测模式已启用，处理通道{channel_num}状态更新: {status}, 电压{voltage:.3f}V")

            # 使用Qt的线程安全机制调用主线程方法
            if not self._is_main_thread():
                logger.debug(f"🔋 [回调] 非主线程，使用QTimer调用主线程方法")
                # 修复：使用functools.partial避免lambda闭包问题
                from functools import partial
                QTimer.singleShot(0, partial(self._on_battery_status_updated_main_thread, channel_num, status, voltage))
                return

            logger.debug(f"🔋 [回调] 主线程，直接调用处理方法")
            self._on_battery_status_updated_main_thread(channel_num, status, voltage)

        except Exception as e:
            logger.error(f"电池状态更新事件处理失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _on_battery_status_updated_main_thread(self, channel_num: int, status: str, voltage: float):
        """在主线程中处理电池状态更新"""
        try:
            logger.info(f"🔋 在主线程中更新通道{channel_num}电池状态: {status}, 电压{voltage:.3f}V")

            # 更新通道卡片的电池状态显示，增强错误处理和备用方案
            ui_update_success = False
            try:
                channels_container = self.ui_component_manager.get_component('channels_container')
                if channels_container:
                    channel_widget = channels_container.get_channel(channel_num)
                    if channel_widget and hasattr(channel_widget, 'update_battery_status'):
                        channel_widget.update_battery_status(status, voltage)
                        logger.info(f"✅ 通道{channel_num}状态UI更新成功: {status}")
                        ui_update_success = True
                    else:
                        logger.warning(f"⚠️ 通道{channel_num}组件不存在或无update_battery_status方法")
                else:
                    logger.warning("⚠️ 通道容器组件未找到")
            except Exception as ui_error:
                logger.error(f"❌ 更新通道{channel_num}电池状态UI失败: {ui_error}")
                import traceback
                logger.error(f"UI更新详细错误: {traceback.format_exc()}")

            # 如果主要方法失败，尝试备用更新方法
            if not ui_update_success:
                self._fallback_update_channel_status(channel_num, status, voltage)

            # 更新状态栏显示
            try:
                status_bar = self.ui_component_manager.get_component('status_bar')
                if status_bar and hasattr(status_bar, 'set_battery_status'):
                    status_bar.set_battery_status(channel_num, status, voltage)
                    logger.debug(f"✅ 状态栏电池状态更新成功")
            except Exception as status_error:
                logger.error(f"❌ 更新状态栏电池状态失败: {status_error}")

        except Exception as e:
            logger.error(f"❌ 主线程处理电池状态更新失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _fallback_update_channel_status(self, channel_num: int, status: str, voltage: float):
        """备用的通道状态更新方法"""
        try:

            # 尝试直接查找通道组件
            for widget in self.findChildren(QWidget):
                if hasattr(widget, 'channel_number') and widget.channel_number == channel_num:
                    if hasattr(widget, 'update_battery_status'):
                        widget.update_battery_status(status, voltage)
                        logger.info(f"✅ 备用方法成功更新通道{channel_num}状态")
                        return

            logger.warning(f"⚠️ 备用方法也无法找到通道{channel_num}组件")

        except Exception as e:
            logger.error(f"❌ 备用状态更新方法失败: {e}")

    def _start_auto_test_for_new_battery(self):
        """为新电池启动自动测试（保留兼容性）"""
        self._start_auto_test_for_new_battery_safe()

    def _start_auto_test_for_new_battery_safe(self):
        """为新电池启动自动测试（安全版本）"""
        try:
            logger.info("🚀 检测到新电池，启动自动测试...")

            # 确保在主线程中执行
            if not self._is_main_thread():
                logger.debug("非主线程调用，转发到主线程")
                QTimer.singleShot(0, self._start_auto_test_for_new_battery_safe)
                return

            # 添加状态检查，防止重复启动
            if hasattr(self, '_auto_test_starting') and self._auto_test_starting:
                logger.info("自动测试启动中，跳过重复请求")
                return

            self._auto_test_starting = True

            try:
                # 1. 检查设备连接状态
                if not self.device_connection_manager.get_connection_status():
                    logger.warning("设备未连接，无法启动自动测试")
                    return

                # 2. 检查主窗口测试状态
                if self.is_testing:
                    logger.info("当前正在测试中，跳过自动测试启动")
                    return

                # 3. 检查测试流程管理器状态
                if not hasattr(self, 'test_flow_manager') or not self.test_flow_manager:
                    logger.error("测试流程管理器未初始化")
                    return

                # 4. 检查测试流程管理器内部状态
                if hasattr(self.test_flow_manager, 'is_testing') and self.test_flow_manager.is_testing:
                    logger.warning("测试流程管理器显示正在测试中，跳过自动测试启动")
                    return

                # 5. 检查自动侦测配置
                auto_detect = self.config_manager.get('test.auto_detect', False)
                if not auto_detect:
                    logger.info("自动侦测已禁用，跳过自动测试启动")
                    return

                # 6. 额外的状态验证
                if not self._validate_auto_test_conditions():
                    logger.warning("自动测试条件验证失败，跳过启动")
                    return

                # 启动测试
                logger.info("🎯 所有条件满足，准备启动测试流程...")
                success = self.test_flow_manager.start_test()

                if success:
                    logger.info("✅ 新电池自动测试启动成功")
                    # 更新主窗口状态
                    self.is_testing = True
                else:
                    logger.warning("⚠️ 新电池自动测试启动失败")

            finally:
                # 确保清理启动标志
                self._auto_test_starting = False

        except Exception as e:
            logger.error(f"启动新电池自动测试失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            # 确保清理启动标志
            if hasattr(self, '_auto_test_starting'):
                self._auto_test_starting = False

    def _validate_auto_test_conditions(self) -> bool:
        """验证自动测试启动条件"""
        try:
            # 检查测试模式
            continuous_mode = self.config_manager.get('test.continuous_mode', False)
            sampling_test = self.config_manager.get('test.sampling_test', False)

            if continuous_mode:
                logger.debug("连续测试模式已启用，跳过自动测试")
                return False

            if sampling_test:
                logger.debug("取样测试模式已启用，跳过自动测试")
                return False

            # 检查测试控制组件状态
            try:
                test_control = self.ui_component_manager.get_component('test_control')
                if test_control and hasattr(test_control, 'is_testing') and test_control.is_testing:
                    logger.debug("测试控制组件显示正在测试中")
                    return False
            except Exception as e:
                logger.debug(f"检查测试控制组件状态失败: {e}")

            # 检查是否有通道启用
            enabled_channels = self.config_manager.get('test.enabled_channels', [])
            if not enabled_channels:
                logger.debug("没有启用的测试通道")
                return False

            logger.debug("自动测试条件验证通过")
            return True

        except Exception as e:
            logger.error(f"验证自动测试条件失败: {e}")
            return False

    def _is_main_thread(self) -> bool:
        """检查当前是否在主线程中"""
        try:
            from PyQt5.QtCore import QThread
            return QThread.currentThread() == self.thread()
        except Exception:
            return True  # 如果检查失败，假设在主线程中

    def _on_printer_status_changed(self, connected: bool, printer_info: Optional[dict] = None):
        """打印机状态变更处理"""
        self.event_coordinator.handle_printer_status_changed(connected, printer_info)

    def _on_label_print_started(self, print_job_info: dict):
        """标签打印开始处理"""
        self.event_coordinator.handle_label_print_started(print_job_info)

    def _on_label_print_completed(self, print_result: dict):
        """标签打印完成处理"""
        self.event_coordinator.handle_label_print_completed(print_result)

    def _on_print_queue_updated(self, queue_info: dict):
        """打印队列更新处理"""
        self.event_coordinator.handle_print_queue_updated(queue_info)

    def _on_config_changed(self, key: str, value):
        """配置变更处理（使用事件协调器）"""
        self.event_coordinator.handle_config_changed(key, value)

        # 特殊处理电池侦测模式变更
        if key == 'test.auto_detect':
            self._handle_battery_detection_mode_change(value)

    def _on_label_template_config_changed(self, key: str, value):
        """标签模板配置变更处理"""
        try:
            logger.info(f"标签模板配置变更: {key} = {value}")

            # 重新加载标签打印管理器的模板配置
            if hasattr(self, 'label_print_manager'):
                self.label_print_manager.reload_template_config()
                logger.info("标签打印管理器模板配置已重新加载")

        except Exception as e:
            logger.error(f"处理标签模板配置变更失败: {e}")

    def _on_grade_settings_changed(self, key: str, value):
        """档位设置变更处理"""
        try:
            logger.info(f"档位设置已变更: {key} = {value}")

            # 更新统计组件的档位范围显示
            if hasattr(self, 'ui_component_manager'):
                ui_manager = self.ui_component_manager
                statistics_widget = ui_manager.get_component('statistics')
                if statistics_widget and hasattr(statistics_widget, 'update_grade_settings'):
                    statistics_widget.update_grade_settings()
                    logger.debug("已更新统计组件的档位范围显示")

            # 更新通道显示组件的档位设置
            channels_container = ui_manager.get_component('channels_container')
            if channels_container and hasattr(channels_container, 'update_grade_settings'):
                channels_container.update_grade_settings()
                logger.debug("已更新通道容器的档位设置")

        except Exception as e:
            logger.error(f"处理档位设置变更失败: {e}")

    def _on_product_info_changed(self, key: str, value):
        """产品信息设置变更处理（修复：产品信息实时更新）"""
        try:
            logger.info(f"产品信息设置已变更: {key} = {value}")

            # 更新批次信息组件显示
            batch_info = self.ui_component_manager.get_component('batch_info')
            if batch_info:
                if hasattr(batch_info, 'refresh_display'):
                    batch_info.refresh_display()
                    logger.debug("批次信息显示已刷新")

                # 根据具体的配置键进行特定更新
                if key.endswith('.batch_number'):
                    if hasattr(batch_info, 'set_batch_number'):
                        batch_info.set_batch_number(str(value))
                elif key.endswith('.operator'):
                    if hasattr(batch_info, 'set_operator'):
                        batch_info.set_operator(str(value))
                elif key.endswith('.battery_type'):
                    if hasattr(batch_info, 'set_cell_type'):
                        batch_info.set_cell_type(str(value))
                elif key.endswith('.battery_spec'):
                    if hasattr(batch_info, 'refresh_battery_spec_from_product'):
                        batch_info.refresh_battery_spec_from_product()

        except Exception as e:
            logger.error(f"处理产品信息设置变更失败: {e}")

    def _on_general_settings_changed(self, value):
        """通用设置变更处理（修复：设置实时更新）"""
        try:
            logger.info(f"通用设置已变更，刷新所有设置: {value}")

            # 重新加载所有启动设置（使用新的设置加载管理器）
            self.settings_loader.load_startup_settings()

        except Exception as e:
            logger.error(f"处理通用设置变更失败: {e}")

    def _on_channel_enable_changed(self, enabled_channels):
        """通道使能设置变更处理"""
        try:
            logger.info(f"通道使能设置已变更: {enabled_channels}")

            # 更新测试引擎的通道使能状态
            if hasattr(self, 'test_engine') and self.test_engine:
                self.test_engine._update_channel_enable_status(enabled_channels)

            # 更新UI显示
            if hasattr(self, 'ui_component_manager'):
                ui_manager = self.ui_component_manager

                # 更新通道容器的使能状态
                channels_container = ui_manager.get_component('channels_container')
                if channels_container and hasattr(channels_container, 'update_channel_enable_status'):
                    channels_container.update_channel_enable_status(enabled_channels)
                    logger.debug("已更新通道容器的使能状态")

        except Exception as e:
            logger.error(f"处理通道使能设置变更失败: {e}")

    def _on_probe_pin_settings_changed(self, key: str, value):
        """顶针寿命设置变更处理"""
        try:
            logger.debug(f"顶针寿命设置已变更: {key} = {value}")

            # 刷新顶针寿命显示
            if hasattr(self, 'ui_component_manager'):
                ui_manager = self.ui_component_manager

                # 通过通道容器刷新测试计数显示
                channels_container = ui_manager.get_component('channels_container')
                if channels_container:
                    # 刷新所有通道的测试计数显示
                    for channel_num in range(1, 9):
                        count = self.config_manager.get(f'test_count.channel_{channel_num}', 0)
                        if hasattr(channels_container, 'update_channel_test_count'):
                            channels_container.update_channel_test_count(channel_num, count)
                    logger.debug("已刷新所有通道的测试计数显示")

        except Exception as e:
            logger.error(f"处理顶针寿命设置变更失败: {e}")

    def _on_outlier_detection_config_changed(self, key: str, value):
        """离群检测配置变更处理"""
        try:
            logger.debug(f"离群检测配置已变更: {key} = {value}")

            # 获取离群检测状态
            if key == 'outlier_detection.is_enabled':
                enabled = bool(value)

                # 更新所有通道的离群检测状态
                if hasattr(self, 'ui_component_manager'):
                    ui_manager = self.ui_component_manager
                    channels_container = ui_manager.get_component('channels_container')
                    if channels_container and hasattr(channels_container, 'update_all_outlier_detection_status'):
                        channels_container.update_all_outlier_detection_status(enabled)
                        logger.info(f"已更新所有通道离群检测状态: {'启用' if enabled else '禁用'}")

        except Exception as e:
            logger.error(f"处理离群检测配置变更失败: {e}")

    def _on_test_count_changed(self, key: str, value):
        """测试计数变更处理"""
        try:
            # 提取通道号
            if 'channel_' in key:
                channel_num_str = key.split('channel_')[1]
                try:
                    channel_num = int(channel_num_str)
                    logger.debug(f"通道{channel_num}测试计数已变更: {value}")

                    # 更新通道显示组件的测试计数
                    if hasattr(self, 'ui_component_manager'):
                        ui_manager = self.ui_component_manager

                        channels_container = ui_manager.get_component('channels_container')
                        if channels_container and hasattr(channels_container, 'update_channel_test_count'):
                            channels_container.update_channel_test_count(channel_num, value)
                            logger.debug(f"已更新通道{channel_num}的测试计数显示")

                except ValueError:
                    logger.warning(f"无法解析通道号: {key}")

        except Exception as e:
            logger.error(f"处理测试计数变更失败: {e}")

    def _on_test_mode_config_changed(self, key: str, value):
        """测试模式配置变更处理"""
        try:
            logger.debug(f"测试模式配置已变更: {key} = {value}")

            # 获取测试控制组件并重新加载设置
            if hasattr(self, 'ui_component_manager'):
                ui_manager = self.ui_component_manager
                test_control = ui_manager.get_component('test_control')

                if test_control and hasattr(test_control, 'load_settings'):
                    test_control.load_settings()
                    logger.debug("已刷新测试控制组件的设置")
                else:
                    logger.warning("测试控制组件未找到或不支持设置加载")

        except Exception as e:
            logger.error(f"处理测试模式配置变更失败: {e}")

    # ===== 窗口事件 =====

    def keyPressEvent(self, event):
        """键盘事件处理"""
        try:
            # 检查隐藏的调试功能组合键 Ctrl+Shift+T
            if (event.key() == Qt.Key.Key_T and  # 使用正确的Qt常量
                event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
                logger.debug("检测到Ctrl+Shift+T组合键，触发调试功能")
                self._show_debug_dialog()
                return

            # 新增检查强制完成采样测试组合键 Ctrl+Shift+S
            if (event.key() == Qt.Key.Key_S and  # 使用正确的Qt常量
                event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
                logger.debug("检测到Ctrl+Shift+S组合键，触发强制完成采样测试")
                self.force_sampling_test_completion()
                return

            # 新增检查强制显示参数建议对话框组合键 Ctrl+Shift+P
            if (event.key() == Qt.Key.Key_P and  # 使用正确的Qt常量
                event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
                logger.debug("检测到Ctrl+Shift+P组合键，触发强制显示参数建议对话框")
                self.force_show_parameter_suggestion_dialog()
                return

            # F11键或ESC键切换/退出全屏
            if event.key() == Qt.Key.Key_F11:  # 使用正确的Qt常量
                self._toggle_fullscreen()
            elif event.key() == Qt.Key.Key_Escape and self.isFullScreen():  # 使用正确的Qt常量
                self._exit_fullscreen()
            else:
                super().keyPressEvent(event)

        except Exception as e:
            logger.error(f"处理键盘事件失败: {e}")
            super().keyPressEvent(event)

    def _toggle_fullscreen(self):
        """切换全屏模式"""
        try:
            if self.isFullScreen():
                self._exit_fullscreen()
            else:
                self._enter_fullscreen()
        except Exception as e:
            logger.error(f"切换全屏模式失败: {e}")

    def _enter_fullscreen(self):
        """进入全屏模式"""
        try:
            self.showFullScreen()
            logger.info("进入全屏模式")
        except Exception as e:
            logger.error(f"进入全屏模式失败: {e}")

    def _exit_fullscreen(self):
        """退出全屏模式"""
        try:
            self.showNormal()
            logger.info("退出全屏模式")
        except Exception as e:
            logger.error(f"退出全屏模式失败: {e}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 设置关闭标志，停止窗口状态监控
            self._is_closing = True
            if hasattr(self, 'window_monitor_timer'):
                self.window_monitor_timer.stop()

            # 保存窗口设置
            if hasattr(self, 'window_layout_manager'):
                self.window_layout_manager.save_window_settings()

            # 保存配置
            self.config_manager.save_config()

            # 清理资源
            self._cleanup_resources()

            logger.info("应用程序正在关闭")
            event.accept()

        except Exception as e:
            logger.error(f"关闭窗口失败: {e}")
            event.accept()

    def _cleanup_resources(self):
        """清理资源"""
        try:
            # 修复优先停止网络相关服务，避免退出卡顿
            logger.info("开始清理网络相关资源...")

            # 停止心跳服务（防御式检查）
            hb = getattr(self, 'heartbeat_manager', None)
            if hb and callable(getattr(hb, 'stop', None)):
                try:
                    hb.stop()
                except Exception as e:
                    logger.debug(f"停止心跳服务异常: {e}")

            # 停止数据上传管理器（防御式检查）
            du = getattr(self, 'data_upload_manager', None)
            if du and callable(getattr(du, 'stop', None)):
                try:
                    du.stop()
                except Exception as e:
                    logger.debug(f"停止数据上传管理器异常: {e}")

            # 停止数据库同步管理器（兼容不同命名）
            ds = getattr(self, 'database_sync_manager', None)
            if ds:
                try:
                    if callable(getattr(ds, 'stop_sync_service', None)):
                        ds.stop_sync_service()
                    elif callable(getattr(ds, 'stop', None)):
                        ds.stop()
                except Exception as e:
                    logger.debug(f"停止数据库同步管理器异常: {e}")

            logger.info("网络相关资源清理完成，开始清理其他资源...")

            # 清理定时器
            wl = getattr(self, 'window_layout_manager', None)
            if wl and callable(getattr(wl, 'cleanup_timers', None)):
                try:
                    wl.cleanup_timers()
                except Exception as e:
                    logger.debug(f"清理窗口定时器异常: {e}")

            # 清理测试流程
            tf = getattr(self, 'test_flow_manager', None)
            if tf and callable(getattr(tf, 'cleanup', None)):
                try:
                    tf.cleanup()
                except Exception as e:
                    logger.debug(f"清理测试流程异常: {e}")

            # 清理设备连接
            dc = getattr(self, 'device_connection_manager', None)
            if dc and callable(getattr(dc, 'cleanup', None)):
                try:
                    dc.cleanup()
                except Exception as e:
                    logger.debug(f"清理设备连接异常: {e}")

            # 清理UI组件
            ui = getattr(self, 'ui_component_manager', None)
            if ui and callable(getattr(ui, 'cleanup', None)):
                try:
                    ui.cleanup()
                except Exception as e:
                    logger.debug(f"清理UI组件异常: {e}")

        except Exception as e:
            logger.error(f"清理资源失败: {e}")

    # ===== 管理器访问接口 =====

    def get_manager(self, manager_name: str):
        """
        获取指定的管理器实例

        Args:
            manager_name: 管理器名称

        Returns:
            管理器实例或None
        """
        managers = {
            'window': getattr(self, 'window_layout_manager', None),
            'menu': getattr(self, 'menu_manager', None),
            'device_connection': getattr(self, 'device_connection_manager', None),
            'test_flow': getattr(self, 'test_flow_manager', None),
            'ui_component': getattr(self, 'ui_component_manager', None)
        }
        return managers.get(manager_name)

    def get_status_info(self) -> dict:
        """
        获取状态信息

        Returns:
            状态信息字典
        """
        status_info = {
            'is_testing': self.is_testing,
        }

        # 安全地获取各管理器的状态信息
        if hasattr(self, 'window_layout_manager'):
            status_info['window_info'] = getattr(self.window_layout_manager, 'get_window_info', lambda: {})()

        if hasattr(self, 'device_connection_manager'):
            status_info['device_status'] = getattr(self.device_connection_manager, 'get_manager_info', lambda: {})()

        if hasattr(self, 'test_flow_manager'):
            status_info['test_status'] = getattr(self.test_flow_manager, 'get_test_status', lambda: {})()

        if hasattr(self, 'ui_component_manager'):
            status_info['components_info'] = getattr(self.ui_component_manager, 'get_components_info', lambda: {})()

        return status_info

    # ===== 授权管理相关方法 =====

    def _on_trial_expired(self):
        """处理试用期到期"""
        try:
            logger.warning("试用期已到期")

            # 获取header组件的授权管理器
            header = self.ui_component_manager.get_component('header')
            if header and hasattr(header, 'get_license_manager'):
                license_manager = header.get_license_manager()
                if license_manager and not license_manager.is_authorized():
                    # 显示试用期到期提示
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(
                        self,
                        "试用期到期",
                        "软件试用期已到期！\n\n请点击右上角的\"解锁\"按钮输入解锁码以继续使用软件。\n\n如需购买授权，请联系软件供应商。",
                        QMessageBox.Ok
                    )

        except Exception as e:
            logger.error(f"处理试用期到期失败: {e}")

    def _on_unlock_requested(self):
        """处理解锁请求"""
        try:
            logger.info("用户请求解锁软件")

            # 获取header组件的授权管理器
            header = self.ui_component_manager.get_component('header')
            if header and hasattr(header, 'get_license_manager'):
                license_manager = header.get_license_manager()
                if license_manager:
                    self._show_unlock_dialog(license_manager)
                else:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.critical(self, "错误", "授权管理器未初始化")
            else:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(self, "错误", "无法获取授权管理器")

        except Exception as e:
            logger.error(f"处理解锁请求失败: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"处理解锁请求时发生错误：\n\n{e}")

    def _show_unlock_dialog(self, license_manager):
        """显示解锁对话框"""
        try:
            from ui.dialogs.unlock_dialog import UnlockDialog

            dialog = UnlockDialog(license_manager, self)
            dialog.unlock_successful.connect(self._on_unlock_successful)

            # 显示对话框
            dialog.exec_()

        except Exception as e:
            logger.error(f"显示解锁对话框失败: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"显示解锁对话框时发生错误：\n\n{e}")

    def _on_unlock_successful(self):
        """处理解锁成功"""
        try:
            logger.info("软件解锁成功")

            # 刷新header组件的授权状态显示
            header = self.ui_component_manager.get_component('header')
            if header and hasattr(header, 'refresh_license_status'):
                header.refresh_license_status()

            # 显示成功消息
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "解锁成功",
                "恭喜！软件已成功解锁。\n\n您现在可以无限制使用本软件的所有功能。"
            )

        except Exception as e:
            logger.error(f"处理解锁成功失败: {e}")

    def check_license_on_startup(self):
        """启动时检查授权状态"""
        try:
            header = self.ui_component_manager.get_component('header')
            if header and hasattr(header, 'get_license_manager'):
                license_manager = header.get_license_manager()
                if license_manager:
                    status = license_manager.get_license_status()

                    if status['is_licensed']:
                        logger.info("软件已授权，可正常使用")
                    elif not status['is_trial_expired']:
                        remaining_days = status['remaining_days']
                        logger.info(f"软件在试用期内，剩余{remaining_days}天")

                        # 如果剩余天数较少，显示提醒
                        if remaining_days <= 7:
                            from PyQt5.QtWidgets import QMessageBox
                            QMessageBox.information(
                                self,
                                "试用期提醒",
                                f"软件试用期剩余 {remaining_days} 天。\n\n如需继续使用，请及时联系供应商获取解锁码。"
                            )
                    else:
                        logger.warning("软件试用期已到期")
                        # 试用期到期的处理在_on_trial_expired中进行
                else:
                    logger.error("授权管理器未初始化")
            else:
                logger.error("无法获取授权管理器")

        except Exception as e:
            logger.error(f"启动时检查授权状态失败: {e}")










    def _show_debug_dialog(self):
        """显示授权调试对话框（隐藏功能）"""
        try:

            # 检查调试模式文件是否存在
            debug_file = os.path.join(os.path.dirname(__file__), '..', '.debug_mode')
            if not os.path.exists(debug_file):
                logger.warning("调试模式文件不存在，调试功能被禁用")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "调试功能不可用",
                    "调试功能仅在开发环境中可用。\n\n生产环境中此功能已禁用。"
                )
                return

            logger.info(f"✅ 调试模式文件存在: {debug_file}")

            # 导入调试对话框
            from ui.dialogs.license_debug_dialog import LicenseDebugDialog

            # 创建并显示调试对话框
            debug_dialog = LicenseDebugDialog(self.config_manager, self)

            # 连接状态变更信号
            debug_dialog.license_status_changed.connect(self._on_license_status_changed)

            # 显示对话框
            debug_dialog.exec_()

        except Exception as e:
            logger.error(f"❌ 显示授权调试对话框失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "调试功能错误",
                f"无法启动授权调试功能：\n\n{e}\n\n请检查调试功能是否已正确配置。"
            )

    def _on_license_status_changed(self):
        """处理授权状态变更"""
        try:
            logger.info("授权状态已变更，刷新相关组件")

            # 刷新header组件的授权状态显示
            header = self.ui_component_manager.get_component('header')
            if header and hasattr(header, 'refresh_license_status'):
                header.refresh_license_status()

            # 可以在这里添加其他需要响应授权状态变更的逻辑

        except Exception as e:
            logger.error(f"处理授权状态变更失败: {e}")

    def _setup_data_upload_integration(self):
        """设置数据上传功能集成"""
        try:

            # 检查数据上传管理器是否已初始化
            has_upload_manager = hasattr(self, 'data_upload_manager')
            upload_manager_exists = self.data_upload_manager if has_upload_manager else None


            if not has_upload_manager or not self.data_upload_manager:
                logger.warning("⚠️ 数据上传管理器未初始化，跳过集成")
                return

            # 检查测试流程管理器状态
            has_flow_manager = hasattr(self, 'test_flow_manager')
            flow_manager_exists = self.test_flow_manager if has_flow_manager else None


            # 将数据上传管理器设置到测试流程管理器
            if has_flow_manager and self.test_flow_manager:
                if hasattr(self.test_flow_manager, 'set_data_upload_manager'):
                    self.test_flow_manager.set_data_upload_manager(self.data_upload_manager)
                    logger.info("✅ 数据上传管理器已集成到测试流程")
                else:
                    logger.warning("⚠️ 测试流程管理器不支持数据上传功能")
            else:
                logger.warning("⚠️ 测试流程管理器未初始化")

            # 获取上传配置状态
            upload_config = self.config_manager.get('data_upload', {})
            if upload_config.get('enabled', False):
                logger.info("✅ 数据上传功能已启用")
                logger.info(f"   服务器地址: {upload_config.get('server_url', 'N/A')}")
                logger.info(f"   自动认证: {upload_config.get('auto_auth', False)}")
            else:
                logger.info("ℹ️ 数据上传功能已禁用")

        except Exception as e:
            logger.error(f"❌ 设置数据上传功能集成失败: {e}")
            # 数据上传集成失败不应影响主程序运行
