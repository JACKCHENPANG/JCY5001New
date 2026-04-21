# -*- coding: utf-8 -*-
"""
重构后的主窗口类（第三版）
进一步拆分为更多专门的管理器，将主类简化为纯协调器角色

重构说明：
- 在原有5个管理器基础上，新增6个专门管理器
- 主类只负责管理器的初始化和协调
- 所有具体业务逻辑都委托给对应的管理器

新增管理器：
1. WindowManager - 窗口状态管理
2. SettingsSyncManager - 设置同步管理
3. BatteryDetectionCallbackManager - 电池检测回调管理
4. PrintIntegrationManager - 打印集成管理
5. LicenseIntegrationManager - 许可证集成管理
6. ConfigChangeManager - 配置变更管理

Author: Jack
Date: 2025-06-27
Version: 重构版本第三版 - 拆分为11个专门管理器
"""

import logging
from typing import Optional
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)

# 导入所有管理器
from ui.main_window_managers import (
    # 原有的5个管理器
    WindowLayoutManager,
    ComponentInitializer,
    SettingsLoader,
    EventCoordinator,
    AuthorizationManager,
    # 新增的6个管理器
    WindowManager,
    SettingsSyncManager,
    BatteryDetectionCallbackManager,
    PrintIntegrationManager,
    LicenseIntegrationManager,
    ConfigChangeManager
)


class MainWindow(QMainWindow):
    """
    重构后的主窗口类（第三版）- 纯协调器角色

    职责：
    - 管理器的初始化和生命周期管理
    - 管理器之间的协调和通信
    - 统一的事件处理接口
    - 兼容性保证

    重构成果：
    - 原2232行代码拆分为11个专门管理器
    - 主类简化为纯协调器，不包含具体业务逻辑
    - 遵循单一职责原则和开闭原则
    """

    # 信号定义
    config_changed = pyqtSignal(str, object)  # 配置变更信号
    test_started = pyqtSignal()  # 测试开始信号
    test_stopped = pyqtSignal()  # 测试停止信号
    window_ready = pyqtSignal()  # 窗口就绪信号

    def __init__(self, config_manager, parent=None):
        """
        初始化重构后的主窗口

        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.is_testing = False

        # 初始化所有管理器
        self._initialize_all_managers()

        # 初始化通信和其他组件
        self._initialize_components()

        # 初始化界面
        self._init_ui()

        # 加载启动设置
        self._load_startup_settings()

        # 设置管理器之间的协调
        self._setup_manager_coordination()

        # 尝试自动连接设备
        self._try_auto_connect()

        # 标记初始化完成
        self._finalize_initialization()

        logger.debug("重构后的主窗口（第三版）初始化完成")

    def _initialize_all_managers(self):
        """初始化所有11个管理器"""
        try:

            # 原有的5个管理器
            self.window_layout_manager = WindowLayoutManager(self, self.config_manager)
            self.component_initializer = ComponentInitializer(self, self.config_manager)
            self.settings_loader = SettingsLoader(self, self.config_manager)
            self.event_coordinator = EventCoordinator(self, self.config_manager)
            self.authorization_manager = AuthorizationManager(self, self.config_manager)

            # 新增的6个管理器
            self.window_manager = WindowManager(self, self.config_manager, self)
            self.settings_sync_manager = SettingsSyncManager(self, self.config_manager, self)
            self.battery_detection_callback_manager = BatteryDetectionCallbackManager(self, self.config_manager, self)
            self.print_integration_manager = PrintIntegrationManager(self, self.config_manager, self)
            self.license_integration_manager = LicenseIntegrationManager(self, self.config_manager, self)
            self.config_change_manager = ConfigChangeManager(self, self.config_manager, self)

            # 初始化各个管理器
            self.settings_sync_manager.initialize()
            self.print_integration_manager.initialize()
            self.license_integration_manager.initialize()
            self.config_change_manager.initialize()

            logger.debug("✅ 所有11个管理器初始化完成")

        except Exception as e:
            logger.error(f"❌ 初始化管理器失败: {e}")
            raise

    def _initialize_components(self):
        """初始化组件"""
        try:
            # 初始化通信管理器
            self.component_initializer.initialize_communication_manager()

            # 初始化其他管理器
            self.component_initializer.initialize_ui_managers()
            self.component_initializer.initialize_device_managers()
            self.component_initializer.initialize_printer_managers()

            # 初始化数据上传管理器
            self.component_initializer.initialize_data_upload_manager()

            logger.debug("组件初始化完成")

        except Exception as e:
            logger.error(f"组件初始化失败: {e}")

    def _init_ui(self):
        """初始化用户界面"""
        try:
            # 1. 设置窗口属性
            self.window_layout_manager.setup_window_properties()

            # 2. 创建主布局
            main_layout = self.window_layout_manager.create_main_layout()

            # 3. 创建UI组件
            self.component_initializer.create_ui_components(main_layout)

            # 4. 创建菜单栏
            if hasattr(self, 'menu_manager'):
                self.menu_manager.create_menu_bar()

            # 5. 应用样式
            self.window_layout_manager.apply_styles()

            # 6. 设置信号连接
            self.component_initializer.setup_signal_connections()

            logger.debug("用户界面初始化完成")

        except Exception as e:
            logger.error(f"初始化用户界面失败: {e}")

    def _load_startup_settings(self):
        """加载启动设置"""
        try:
            # 使用设置同步管理器加载启动设置
            self.settings_sync_manager.load_startup_settings()

            # 使用设置加载器加载其他设置
            self.settings_loader.load_startup_settings()

        except Exception as e:
            logger.error(f"加载启动设置失败: {e}")

    def _setup_manager_coordination(self):
        """设置管理器之间的协调"""
        try:
            # 设置电池检测回调
            self.battery_detection_callback_manager.setup_battery_detection_callbacks()

            # 连接窗口管理器信号
            self.window_manager.window_closing.connect(self._on_window_closing)
            self.window_manager.fullscreen_toggled.connect(self._on_fullscreen_toggled)

            # 连接设置同步管理器信号
            self.settings_sync_manager.sync_completed.connect(self._on_settings_sync_completed)
            self.settings_sync_manager.sync_failed.connect(self._on_settings_sync_failed)

            # 连接电池检测回调管理器信号
            self.battery_detection_callback_manager.auto_test_requested.connect(self._on_auto_test_requested)

            # 连接打印集成管理器信号
            self.print_integration_manager.print_triggered.connect(self._on_print_triggered)

            # 连接许可证集成管理器信号
            self.license_integration_manager.trial_expired.connect(self._on_trial_expired)
            self.license_integration_manager.unlock_successful.connect(self._on_unlock_successful)

            # 连接配置变更管理器信号
            self.config_change_manager.config_processed.connect(self._on_config_processed)

            logger.info("管理器协调设置完成")

        except Exception as e:
            logger.error(f"设置管理器协调失败: {e}")

    def _try_auto_connect(self):
        """尝试自动连接设备"""
        try:
            # 委托给组件初始化器
            if hasattr(self.component_initializer, 'try_auto_connect'):
                self.component_initializer.try_auto_connect()
        except Exception as e:
            logger.error(f"尝试自动连接设备失败: {e}")

    def _finalize_initialization(self):
        """完成初始化"""
        try:
            # 标记电池检测回调管理器初始化完成
            self.battery_detection_callback_manager.set_initialization_complete(True)

            # 延迟检查授权状态
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1000, self.license_integration_manager.check_license_on_startup)

            # 发送窗口就绪信号
            self.window_ready.emit()

            logger.info("主窗口初始化最终完成")

        except Exception as e:
            logger.error(f"完成初始化失败: {e}")

    # ===== 事件处理方法（委托给管理器） =====

    def keyPressEvent(self, event):
        """键盘事件处理"""
        try:
            # 检查隐藏的调试功能组合键 Ctrl+Shift+T
            if (event.key() == Qt.Key.Key_T and
                event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
                logger.debug("检测到Ctrl+Shift+T组合键，触发调试功能")
                self.license_integration_manager.show_debug_dialog()
                return

            # 委托给窗口管理器处理
            if self.window_manager.handle_key_press_event(event):
                return

            # 如果窗口管理器没有处理，调用父类方法
            super().keyPressEvent(event)

        except Exception as e:
            logger.error(f"处理键盘事件失败: {e}")
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 委托给窗口管理器处理
            if self.window_manager.handle_close_event(event):
                # 保存配置
                self.config_manager.save_config()
                # 清理资源
                self._cleanup_resources()
                event.accept()
            else:
                event.ignore()

        except Exception as e:
            logger.error(f"关闭窗口失败: {e}")
            event.accept()

    # ===== 信号处理方法 =====

    def _on_window_closing(self):
        """窗口关闭信号处理"""
        logger.info("窗口正在关闭")

    def _on_fullscreen_toggled(self, is_fullscreen: bool):
        """全屏切换信号处理"""
        logger.info(f"全屏模式: {'开启' if is_fullscreen else '关闭'}")

    def _on_settings_sync_completed(self, message: str):
        """设置同步完成信号处理"""
        logger.info(f"设置同步完成: {message}")

    def _on_settings_sync_failed(self, sync_type: str, error_message: str):
        """设置同步失败信号处理"""
        logger.error(f"设置同步失败 [{sync_type}]: {error_message}")

    def _on_auto_test_requested(self):
        """自动测试请求信号处理"""
        logger.info("收到自动测试请求")
        # 委托给测试流程管理器
        if hasattr(self, 'test_flow_manager'):
            self.test_flow_manager.start_test()

    def _on_print_triggered(self, channel_num: int, print_data: dict):
        """打印触发信号处理"""
        logger.info(f"通道{channel_num}打印已触发")

    def _on_trial_expired(self):
        """试用期到期信号处理"""
        logger.warning("试用期已到期")

    def _on_unlock_successful(self):
        """解锁成功信号处理"""
        logger.info("软件解锁成功")

    def _on_config_processed(self, key: str, value):
        """配置处理完成信号处理"""
        logger.debug(f"配置处理完成: {key}")

    def _on_start_test(self):
        """开始测试信号处理"""
        logger.info("收到开始测试信号")
        if hasattr(self, 'test_flow_manager'):
            self.test_flow_manager.start_test()

    def _on_stop_test(self):
        """停止测试信号处理"""
        logger.info("收到停止测试信号")
        if hasattr(self, 'test_flow_manager'):
            self.test_flow_manager.stop_test()

    def _on_clear_statistics(self):
        """清除统计信号处理"""
        logger.info("收到清除统计信号")

    def _on_export_data(self):
        """导出数据信号处理"""
        logger.info("收到导出数据信号")

    def _on_open_settings(self):
        """打开设置信号处理"""
        logger.info("收到打开设置信号")

    def _on_device_connection_changed(self, connected: bool):
        """设备连接状态变更处理"""
        logger.info(f"设备连接状态变更: {connected}")
        if hasattr(self, 'event_coordinator'):
            self.event_coordinator.handle_device_connection_changed(connected)

    def _on_device_info_updated(self, device_info: dict):
        """设备信息更新处理"""
        logger.debug(f"设备信息更新: {device_info}")

    def _on_test_started(self):
        """测试开始处理"""
        logger.info("测试已开始")
        self.is_testing = True
        self.test_started.emit()

    def _on_test_stopped(self):
        """测试停止处理"""
        logger.info("测试已停止")
        self.is_testing = False
        self.test_stopped.emit()

    def _on_test_progress_updated(self, channel_num: int, progress_data: dict):
        """测试进度更新处理"""
        logger.debug(f"通道{channel_num}测试进度更新")

    def _on_channel_test_completed(self, channel_num: int, test_result: dict):
        """通道测试完成处理"""
        logger.info(f"通道{channel_num}测试完成")

    def _on_channel_battery_code_changed(self, channel_num: int, battery_code: str):
        """通道电池码变更处理"""
        logger.debug(f"通道{channel_num}电池码变更: {battery_code}")

    def _on_all_channels_ready(self):
        """所有通道就绪处理"""
        logger.info("所有通道已就绪")

    def _on_device_status_changed(self, status: str):
        """设备状态变更处理"""
        logger.debug(f"设备状态变更: {status}")

    def _on_printer_status_changed(self, status: str):
        """打印机状态变更处理"""
        logger.debug(f"打印机状态变更: {status}")

    def _on_unlock_requested(self):
        """解锁请求处理"""
        logger.info("收到解锁请求")
        if hasattr(self, 'license_integration_manager'):
            self.license_integration_manager.handle_unlock_request()

    def _on_test_failed(self, error_message: str):
        """测试失败处理"""
        logger.error(f"测试失败: {error_message}")

    def _on_config_changed(self, key: str, value):
        """配置变更处理"""
        logger.debug(f"配置变更: {key} = {value}")
        self.config_changed.emit(key, value)

    def _on_print_queue_updated(self, queue_info: dict):
        """打印队列更新处理"""
        logger.debug(f"打印队列更新: {queue_info}")

    # ===== 兼容性方法 =====

    def get_manager(self, manager_name: str):
        """获取指定的管理器"""
        return getattr(self, manager_name, None)

    def get_status_info(self) -> dict:
        """获取状态信息"""
        try:
            return {
                'window_info': self.window_manager.get_window_info(),
                'license_status': self.license_integration_manager.get_license_status(),
                'print_status': self.print_integration_manager.get_print_status(),
                'battery_status': self.battery_detection_callback_manager.get_battery_status_summary()
            }
        except Exception as e:
            logger.error(f"获取状态信息失败: {e}")
            return {}

    def _cleanup_resources(self):
        """清理资源"""
        try:
            # 清理各个管理器的资源
            managers = [
                self.window_manager,
                self.settings_sync_manager,
                self.battery_detection_callback_manager,
                self.print_integration_manager,
                self.license_integration_manager,
                self.config_change_manager
            ]

            for manager in managers:
                if hasattr(manager, 'cleanup'):
                    manager.cleanup()

            logger.info("资源清理完成")

        except Exception as e:
            logger.error(f"清理资源失败: {e}")
