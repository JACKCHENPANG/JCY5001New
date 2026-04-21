# -*- coding: utf-8 -*-
"""
组件初始化管理器
从MainWindow中提取的组件初始化相关功能

职责：
- UI组件创建
- 管理器初始化
- 信号连接设置
- 组件配置

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Dict, Any
from PyQt5.QtCore import QObject

logger = logging.getLogger(__name__)


class ComponentInitializer(QObject):
    """
    组件初始化管理器
    
    职责：
    - 各种管理器的初始化
    - UI组件的创建和配置
    - 信号连接的建立
    - 组件间依赖关系设置
    """
    
    def __init__(self, main_window, config_manager, database_manager=None):
        """
        初始化组件初始化管理器

        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
            database_manager: 数据库管理器
        """
        super().__init__()

        self.main_window = main_window
        self.config_manager = config_manager
        self.database_manager = database_manager

        logger.debug("组件初始化管理器初始化完成")
    
    def initialize_communication_manager(self):
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
            
            self.main_window.comm_manager = CommunicationManager(comm_config)
            logger.debug("通信管理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化通信管理器失败: {e}")
            raise
    
    def initialize_ui_managers(self):
        """初始化UI相关管理器"""
        try:
            # 1. 窗口管理器（如果还没有创建的话）
            if not hasattr(self.main_window, 'window_layout_manager'):
                from ui.main_window_managers.window_layout_manager import WindowLayoutManager
                self.main_window.window_layout_manager = WindowLayoutManager(
                    self.main_window, self.config_manager
                )

            # 2. 菜单管理器
            from ui.menu_manager import MenuManager
            self.main_window.menu_manager = MenuManager(self.main_window, self.config_manager)

            # 3. UI组件管理器
            from ui.ui_component_manager import UIComponentManager
            self.main_window.ui_component_manager = UIComponentManager(
                self.main_window, self.config_manager
            )

            logger.debug("UI管理器初始化完成")

        except Exception as e:
            logger.error(f"初始化UI管理器失败: {e}")
            raise
    
    def initialize_device_managers(self):
        """初始化设备相关管理器"""
        try:
            # 设备连接管理器
            from ui.device_connection_manager import DeviceConnectionManager
            self.main_window.device_connection_manager = DeviceConnectionManager(
                self.main_window, self.config_manager, self.main_window.comm_manager
            )

            # 电池检测管理器 - 使用新的实时电压检测
            from backend.voltage_based_battery_detection_manager import VoltageBasedBatteryDetectionManager
            self.main_window.battery_detection_manager = VoltageBasedBatteryDetectionManager(
                self.main_window.comm_manager, self.config_manager
            )

            # 测试流程管理器
            from ui.test_flow_manager import TestFlowManager
            self.main_window.test_flow_manager = TestFlowManager(
                self.main_window, self.config_manager,
                self.main_window.comm_manager, self.main_window.device_connection_manager
            )

            logger.debug("设备管理器初始化完成")

        except Exception as e:
            logger.error(f"初始化设备管理器失败: {e}")
            raise
    
    def initialize_printer_managers(self):
        """初始化打印机相关管理器"""
        try:
            # 打印机管理器
            from ui.printer_manager import PrinterManager
            self.main_window.printer_manager = PrinterManager(self.config_manager)

            # 标签打印管理器
            from ui.label_print_manager import LabelPrintManager
            self.main_window.label_print_manager = LabelPrintManager(
                self.config_manager, self.main_window.printer_manager
            )

            logger.debug("打印机管理器初始化完成")

        except Exception as e:
            logger.error(f"初始化打印机管理器失败: {e}")
            raise

    def initialize_data_upload_manager(self):
        """初始化数据上传管理器"""
        try:
            logger.info("🚀 开始初始化数据上传管理器...")
            from backend.data_upload_manager import DataUploadManager

            # 获取数据上传配置
            upload_config = self.config_manager.get('data_upload', {})

            # 新增合并数据库同步配置
            sync_config = self.config_manager.get('database_sync', {})
            if sync_config:
                # 将同步配置合并到上传配置中
                upload_config.update({
                    'enable_database_sync': sync_config.get('enabled', True),
                    'sync_interval': sync_config.get('sync_interval', 300),
                    'incremental_sync': sync_config.get('incremental_sync', True),
                })
                # 如果同步配置中有服务器地址，使用同步配置的
                if sync_config.get('server_url'):
                    upload_config['server_url'] = sync_config['server_url']
                if sync_config.get('username'):
                    upload_config['username'] = sync_config['username']
                if sync_config.get('password'):
                    upload_config['password'] = sync_config['password']
                if sync_config.get('auto_auth') is not None:
                    upload_config['auto_auth'] = sync_config['auto_auth']

                logger.info(f"📋 数据库同步配置已合并: enabled={sync_config.get('enabled', False)}")

            logger.info(f"📋 数据上传配置: enabled={upload_config.get('enabled', False)}")

            # 新增获取数据库管理器用于断点续传
            db_manager = None

            # 优先使用传递进来的数据库管理器
            if self.database_manager:
                db_manager = self.database_manager
                logger.info("✅ 使用传递的数据库管理器")
            elif hasattr(self.main_window, 'database_manager') and self.main_window.database_manager:
                db_manager = self.main_window.database_manager
                logger.info("✅ 从主窗口获取数据库管理器")
            elif hasattr(self.main_window, 'db_manager'):
                db_manager = self.main_window.db_manager
                logger.info("✅ 从主窗口获取db_manager")
            elif hasattr(self.main_window, 'test_flow_manager') and \
                 hasattr(self.main_window.test_flow_manager, 'flow_controller') and \
                 hasattr(self.main_window.test_flow_manager.flow_controller, 'test_result_manager') and \
                 hasattr(self.main_window.test_flow_manager.flow_controller.test_result_manager, 'db_manager'):
                db_manager = self.main_window.test_flow_manager.flow_controller.test_result_manager.db_manager
                logger.info("✅ 从测试流程管理器获取数据库管理器")
            else:
                logger.warning("⚠️ 未找到数据库管理器，将在延迟设置中处理")

            # 创建数据上传管理器（支持断点续传）
            logger.debug(f" 创建数据上传管理器实例...")
            self.main_window.data_upload_manager = DataUploadManager(upload_config, db_manager)

            logger.info("✅ 数据上传管理器初始化完成")
            logger.info(f"   启用状态: {upload_config.get('enabled', False)}")
            logger.info(f"   服务器地址: {upload_config.get('server_url', 'N/A')}")
            logger.info(f"   自动认证: {upload_config.get('auto_auth', False)}")
            logger.info(f"   断点续传: {upload_config.get('enable_resumable', True)}")
            logger.info(f"   数据库同步: {upload_config.get('enable_database_sync', False)}")
            logger.info(f"   同步间隔: {upload_config.get('sync_interval', 300)}秒")
            logger.info(f"   数据库管理器: {'已找到' if db_manager else '未找到'}")

            # 新增显示同步状态
            if hasattr(self.main_window.data_upload_manager, 'is_sync_enabled') and \
               self.main_window.data_upload_manager.is_sync_enabled():
                logger.info("✅ 数据库同步功能已启用并运行")
            else:
                logger.info("ℹ️ 数据库同步功能未启用")

        except Exception as e:
            logger.error(f"❌ 初始化数据上传管理器失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            # 数据上传失败不应影响主程序运行
            self.main_window.data_upload_manager = None

    def initialize_heartbeat_manager(self):
        """初始化心跳管理器"""
        try:
            logger.info("🚀 开始初始化心跳管理器...")
            from backend.heartbeat_manager import HeartbeatManager

            # 获取心跳配置
            heartbeat_config = self.config_manager.get('heartbeat', {})

            # 获取数据上传功能的启用状态
            data_upload_enabled = self.main_window.config_manager.get('data_upload.enabled', False)

            # 修复：如果数据上传功能被禁用，完全跳过心跳管理器初始化
            if not data_upload_enabled:
                logger.info("ℹ️ 数据上传功能已禁用，跳过心跳管理器初始化")
                self.main_window.heartbeat_manager = None
                return

            # 默认配置（联动数据上传功能）
            default_heartbeat_config = {
                'enabled': data_upload_enabled,  # 联动：只有数据上传启用时才启用心跳
                'server_url': 'http://192.168.101.10:5002',
                'heartbeat_interval': 30,  # 30秒间隔
                'auto_auth': True,
                'username': 'admin',
                'password': 'Admin123!',
                'collect_system_info': True
            }

            # 合并配置
            final_config = {**default_heartbeat_config, **heartbeat_config}

            # 强制联动：如果数据上传被禁用，心跳也必须被禁用
            if not data_upload_enabled:
                final_config['enabled'] = False
                logger.info("ℹ️ 数据上传功能已禁用，心跳功能联动禁用")
            
            # 创建心跳管理器
            logger.debug(f" 创建心跳管理器实例...")
            self.main_window.heartbeat_manager = HeartbeatManager(final_config)

            # 设置状态回调
            self.main_window.heartbeat_manager.set_status_callback(self._on_heartbeat_status_changed)

            # 设置数据上传管理器和心跳管理器的联动关系
            if hasattr(self.main_window, 'data_upload_manager') and self.main_window.data_upload_manager:
                self.main_window.data_upload_manager.set_heartbeat_manager(self.main_window.heartbeat_manager)
                logger.info("✅ 数据上传与心跳服务联动关系已建立")
            
            logger.info("✅ 心跳管理器初始化完成")
            logger.info(f"   启用状态: {final_config.get('enabled', False)}")
            logger.info(f"   服务器地址: {final_config.get('server_url', 'N/A')}")
            logger.info(f"   心跳间隔: {final_config.get('heartbeat_interval', 30)}秒")
            logger.info(f"   自动认证: {final_config.get('auto_auth', False)}")
            logger.info(f"   系统信息收集: {final_config.get('collect_system_info', True)}")

        except Exception as e:
            logger.error(f"❌ 初始化心跳管理器失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            # 心跳失败不应影响主程序运行
            self.main_window.heartbeat_manager = None

    def _on_heartbeat_status_changed(self, event_type: str, data: dict):
        """心跳状态变更回调"""
        try:
            if event_type == 'heartbeat_sent':
                logger.debug(f"心跳已发送: {data.get('status', 'unknown')}")
                
                # 更新状态栏显示
                if hasattr(self.main_window, 'ui_component_manager'):
                    status_bar = self.main_window.ui_component_manager.get_component('status_bar')
                    if status_bar and hasattr(status_bar, 'set_heartbeat_status'):
                        status_bar.set_heartbeat_status(data.get('status', 'unknown'))
                        
        except Exception as e:
            logger.error(f"处理心跳状态变更失败: {e}")

    def create_ui_components(self, main_layout):
        """
        创建UI组件

        Args:
            main_layout: 主布局
        """
        try:
            # 创建精确比例布局容器
            containers = self.main_window.window_layout_manager.create_proportional_layout(main_layout)

            if not containers:
                logger.error("创建比例布局失败")
                return

            # 创建顶部标题栏（在header容器中）
            header_container = containers['header']
            self.main_window.ui_component_manager.create_header_widget_in_container(header_container)

            # 创建上层区域组件（在upper容器中）
            upper_container = containers['upper']
            upper_layout = self.main_window.window_layout_manager.create_upper_layout(upper_container)
            self.main_window.ui_component_manager.create_upper_widgets(upper_layout)

            # 设置上层区域比例
            self._setup_upper_widget_proportions(upper_layout)

            # 创建通道容器（分为两行）
            channels_row1_container = containers['channels_row1']
            channels_row2_container = containers['channels_row2']
            self.main_window.ui_component_manager.create_split_channels_container(
                channels_row1_container, channels_row2_container
            )

            # 创建状态栏
            self.main_window.ui_component_manager.create_status_bar()

            logger.info("UI组件创建完成")

        except Exception as e:
            logger.error(f"创建UI组件失败: {e}")
            raise

    def _setup_upper_widget_proportions(self, upper_layout):
        """设置上层区域组件比例"""
        try:
            batch_widget = self.main_window.ui_component_manager.get_component('batch_info')
            statistics_widget = self.main_window.ui_component_manager.get_component('statistics')
            control_widget = self.main_window.ui_component_manager.get_component('test_control')

            if all([batch_widget, statistics_widget, control_widget]):
                self.main_window.window_layout_manager.setup_upper_widget_proportions(
                    upper_layout, batch_widget, statistics_widget, control_widget
                )
            else:
                logger.warning("部分上层组件未找到，无法设置比例")

        except Exception as e:
            logger.error(f"设置上层组件比例失败: {e}")

    def setup_signal_connections(self):
        """设置信号连接"""
        try:
            # UI组件信号连接
            self.main_window.ui_component_manager.setup_signal_connections()

            # 设备连接管理器信号
            self.main_window.device_connection_manager.connection_status_changed.connect(
                self.main_window._on_device_connection_changed
            )
            self.main_window.device_connection_manager.device_info_updated.connect(
                self.main_window._on_device_info_updated
            )

            # 测试流程管理器信号
            self.main_window.test_flow_manager.test_started.connect(self.main_window._on_test_started)
            self.main_window.test_flow_manager.test_stopped.connect(self.main_window._on_test_stopped)
            self.main_window.test_flow_manager.test_progress_updated.connect(
                self.main_window._on_test_progress_updated
            )
            self.main_window.test_flow_manager.test_failed.connect(self.main_window._on_test_failed)
            self.main_window.test_flow_manager.channel_test_completed.connect(
                self.main_window._on_channel_test_completed
            )

            # UI组件管理器信号
            self.main_window.ui_component_manager.component_ready.connect(
                self.main_window._on_component_ready
            )
            self.main_window.ui_component_manager.component_error.connect(
                self.main_window._on_component_error
            )

            # 打印机管理器信号
            self.main_window.printer_manager.printer_status_changed.connect(
                self.main_window._on_printer_status_changed
            )

            # 标签打印管理器信号
            self.main_window.label_print_manager.print_started.connect(
                self.main_window._on_label_print_started
            )
            self.main_window.label_print_manager.print_completed.connect(
                self.main_window._on_label_print_completed
            )
            self.main_window.label_print_manager.print_queue_updated.connect(
                self.main_window._on_print_queue_updated
            )

            # 修复配置变更信号连接
            if hasattr(self.main_window, 'config_changed'):
                self.main_window.config_changed.connect(self.main_window._on_config_changed)
                logger.debug("已连接主窗口配置变更信号")

            # 修复连接配置管理器的配置变更信号
            if hasattr(self.main_window, 'config_manager') and hasattr(self.main_window.config_manager, 'config_changed'):
                self.main_window.config_manager.config_changed.connect(self.main_window._on_config_changed)
                logger.debug("已连接配置管理器配置变更信号")

            logger.info("信号连接设置完成")

        except Exception as e:
            logger.error(f"设置信号连接失败: {e}")

    def get_initialization_status(self) -> Dict[str, Any]:
        """
        获取初始化状态

        Returns:
            初始化状态字典
        """
        try:
            manager_status = {
                'communication_manager': hasattr(self.main_window, 'comm_manager'),
                'window_layout_manager': hasattr(self.main_window, 'window_layout_manager'),
                'menu_manager': hasattr(self.main_window, 'menu_manager'),
                'ui_component_manager': hasattr(self.main_window, 'ui_component_manager'),
                'device_connection_manager': hasattr(self.main_window, 'device_connection_manager'),
                'test_flow_manager': hasattr(self.main_window, 'test_flow_manager'),
                'printer_manager': hasattr(self.main_window, 'printer_manager'),
                'label_print_manager': hasattr(self.main_window, 'label_print_manager'),
                'data_upload_manager': hasattr(self.main_window, 'data_upload_manager'),
                'heartbeat_manager': hasattr(self.main_window, 'heartbeat_manager')
            }

            # 创建结果字典，包含统计信息
            result: Dict[str, Any] = dict(manager_status)  # 复制管理器状态
            result['all_initialized'] = all(manager_status.values())
            result['initialized_count'] = sum(manager_status.values())
            result['total_count'] = len(manager_status)

            return result

        except Exception as e:
            logger.error(f"获取初始化状态失败: {e}")
            return {'error': str(e)}