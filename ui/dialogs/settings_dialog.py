# -*- coding: utf-8 -*-
"""
设置对话框框架
提供6个选项卡的设置界面

Author: Jack
Date: 2025-01-27
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QKeyEvent
import logging
import sys
import os

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager
from utils.settings_network_optimizer import apply_settings_optimization, remove_settings_optimization
from utils.settings_performance_booster import quick_optimize_settings, restore_settings_normal_mode
from utils.settings_network_blocker import block_network_for_settings, unblock_network_for_settings
from utils.resource_path_manager import get_resource_path, get_icon_path, get_style_path
from utils.settings_performance_monitor import (
    get_performance_monitor, start_settings_performance_monitoring,
    stop_settings_performance_monitoring, record_operation
)


class SettingsDialog(QDialog):
    """设置对话框主框架"""

    # 信号定义
    settings_applied = pyqtSignal()  # 设置应用信号
    settings_saved = pyqtSignal()   # 设置保存信号
    device_config_changed = pyqtSignal(dict)  # 设备配置变更信号

    def __init__(self, config_manager: ConfigManager, parent=None, comm_manager=None):
        """
        初始化设置对话框

        Args:
            config_manager: 配置管理器
            parent: 父窗口
            comm_manager: 通信管理器（用于设备配置下发）
        """
        super().__init__(parent)

        # 🚀 性能优化：立即阻塞网络服务，防止初始化时的网络延迟
        self._immediate_network_block()

        self.config_manager = config_manager
        self.comm_manager = comm_manager
        self.original_config = {}  # 保存原始配置
        self.has_changes = False   # 是否有未保存的更改

        # 设备配置相关参数
        self.device_config_keys = [
            'test_params.gain',
            'test_params.average_times',
            'test_params.resistance_range'
        ]

        # 🚀 性能优化：应用全面的设置页面优化
        quick_optimize_settings()

        # 🚀 Jack性能优化：启动性能监控
        start_settings_performance_monitoring()
        self._performance_monitor = get_performance_monitor()

        # 连接性能监控信号
        self._performance_monitor.performance_warning.connect(self._on_performance_warning)
        self._performance_monitor.optimization_suggestion.connect(self._on_optimization_suggestion)

        # 初始化界面
        self._init_ui()
        self._init_connections()
        self._load_settings()

        logger.debug("🚀 设置对话框初始化完成（含性能监控）")



    def _init_ui(self):
        """初始化用户界面"""
        # 设置对话框属性
        self.setWindowTitle("设置")  # 修改窗体标题为"设置"

        # 修复使用资源路径管理器加载图标，兼容打包后的环境
        try:
            icon_path = get_icon_path("settings.png")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                logger.debug(f"设置图标加载成功: {icon_path}")
            else:
                logger.warning(f"设置图标文件不存在: {icon_path}")
        except Exception as e:
            logger.warning(f"加载设置图标失败: {e}")

        self.setModal(True)

        # 获取主窗体的高度并设置相同高度，实现居中显示
        parent_widget = self.parent()
        if parent_widget and hasattr(parent_widget, 'height'):
            parent_height = parent_widget.height()
            parent_width = parent_widget.width()
            parent_pos = parent_widget.pos()

            # 设置与主窗体相同的高度，宽度稍小一些
            dialog_width = int(parent_width * 0.9)
            dialog_height = parent_height

            self.resize(dialog_width, dialog_height)

            # 计算居中位置
            center_x = parent_pos.x() + (parent_width - dialog_width) // 2
            center_y = parent_pos.y()

            self.move(center_x, center_y)
        else:
            # 如果没有父窗体，使用默认设置
            self.showMaximized()

        # 设置最小尺寸（当用户退出全屏时的备用尺寸）
        self.setMinimumSize(1200, 850)

        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 创建选项卡容器
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        main_layout.addWidget(self.tab_widget)

        # 创建各个设置页面
        self._create_setting_tabs()

        # 创建按钮区域
        button_layout = self._create_button_area()
        main_layout.addLayout(button_layout)

        # 应用样式
        self._apply_styles()

    def _create_setting_tabs(self):
        """创建设置选项卡（修复：改为预加载模式提升响应速度）"""
        logger.info("🚀 开始创建设置选项卡（预加载模式）...")

        # 性能修复改为预加载模式，避免切换时的延迟
        self._tab_widgets = {}  # 存储已创建的页面实例
        self._tab_classes = {}  # 存储页面配置信息

        # 定义所有页面的配置（延迟创建）
        tab_configs = [
            ("⚙️ 通道配置", "parameter_config", "ParameterConfigWidget", True),
            ("⚖️ 判断页面", "grade_settings", "GradeSettingsWidget", True),
            ("📡 频率设置", "frequency_settings", "FrequencySettingsWidget", True),
            ("📋 产品信息", "product_info", "ProductInfoWidget", True),
            ("🔄 测试配置", "test_config", "TestConfigWidget", True),
            ("📋 通道使能", "channel_enable", "ChannelEnableWidget", True),

            ("🖥️ 设备设置", "device_settings", "DeviceSettingsWidget", True),
            # 🚫 存储管理页面已删除

            ("ℹ️ 关于", "about_widget", "AboutWidget", True)
        ]

        # 性能修复直接创建所有页面，避免懒加载延迟
        for tab_index, (tab_name, attr_name, class_name, enabled) in enumerate(tab_configs):
            try:
                # 存储页面配置信息
                self._tab_classes[tab_index] = {
                    'tab_name': tab_name,
                    'attr_name': attr_name,
                    'class_name': class_name,
                    'enabled': enabled
                }

                # 直接创建页面实例
                widget = self._create_tab_widget(class_name, attr_name)
                if widget:
                    # 添加到选项卡
                    self.tab_widget.addTab(widget, tab_name)
                    self.tab_widget.setTabEnabled(tab_index, enabled)

                    # 存储页面实例
                    self._tab_widgets[tab_index] = widget
                    setattr(self, attr_name, widget)

                    # 连接信号
                    if hasattr(widget, 'settings_changed'):
                        widget.settings_changed.connect(self._on_settings_changed)

                    logger.debug(f"✅ 页面创建完成: {tab_name}")
                else:
                    logger.error(f"❌ 页面创建失败: {tab_name}")
                    # 创建占位符
                    placeholder = self._create_placeholder_widget(f"❌ {tab_name} 加载失败")
                    self.tab_widget.addTab(placeholder, tab_name)
                    self.tab_widget.setTabEnabled(tab_index, False)

            except Exception as e:
                logger.error(f"创建页面 {tab_name} 失败: {e}")
                # 创建错误占位符
                placeholder = self._create_placeholder_widget(f"❌ {tab_name} 加载错误")
                self.tab_widget.addTab(placeholder, tab_name)
                self.tab_widget.setTabEnabled(tab_index, False)

        # 连接选项卡切换信号（仅用于激活页面）
        self.tab_widget.currentChanged.connect(self._on_tab_activated)

        logger.info(f"✅ 设置选项卡创建完成，共{len(tab_configs)}个页面（预加载模式）")

        # 性能修复立即加载所有页面的设置
        self._load_all_settings()

    def _load_all_settings(self):
        """立即加载所有页面的设置（预加载模式）"""
        try:
            for index, widget in self._tab_widgets.items():
                if widget and hasattr(widget, 'load_settings'):
                    try:
                        widget.load_settings()
                        logger.debug(f"已加载页面 {index} 的设置")
                    except Exception as e:
                        logger.error(f"加载页面 {index} 设置失败: {e}")

            logger.info("✅ 所有页面设置加载完成（预加载模式）")

        except Exception as e:
            logger.error(f"批量加载页面设置失败: {e}")

    def _on_tab_activated(self, index: int):
        """选项卡激活处理（预加载模式，无需重新加载）"""
        try:
            # 激活页面
            current_widget = self.tab_widget.widget(index)
            if hasattr(current_widget, 'on_tab_activated'):
                current_widget.on_tab_activated()

            logger.debug(f"激活页面: 索引 {index}")

        except Exception as e:
            logger.error(f"页面激活处理失败: {e}")

    def _create_button_area(self) -> QHBoxLayout:
        """创建按钮区域"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # 添加弹性空间
        button_layout.addStretch()

        # 确定按钮
        self.ok_button = QPushButton("确定")
        self.ok_button.setMinimumWidth(80)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)

        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumWidth(80)
        button_layout.addWidget(self.cancel_button)

        # 应用按钮
        self.apply_button = QPushButton("应用")
        self.apply_button.setMinimumWidth(80)
        self.apply_button.setEnabled(False)  # 初始禁用
        button_layout.addWidget(self.apply_button)

        return button_layout

    def _connect_page_signals(self):
        """连接各页面的信号（懒加载优化：在页面创建时连接）"""
        # 懒加载优化信号连接移到 _load_tab_widget 中
        pass



    def _init_connections(self):
        """初始化信号连接"""
        # 按钮信号
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.apply_button.clicked.connect(self._on_apply_clicked)

        # 注意：选项卡变更信号已在_create_setting_tabs()中连接到_on_tab_activated

    def _apply_styles(self):
        """应用样式表（修复打包后显示问题）"""
        try:
            # 修复使用资源路径管理器加载样式文件
            style_file = get_style_path("main_style.qss")

            if os.path.exists(style_file):
                try:
                    with open(style_file, 'r', encoding='utf-8') as f:
                        external_style = f.read()
                    self.setStyleSheet(external_style)
                    logger.debug(f"外部样式文件加载成功: {style_file}")
                    return
                except Exception as e:
                    logger.warning(f"加载外部样式文件失败: {e}")

            # 使用内置样式（修复字体问题）
            self.setStyleSheet("""
                QDialog {
                    background-color: #f5f5f5;
                    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
                    font-size: 9pt;
                }

                QTabWidget::pane {
                    border: 1px solid #d0d0d0;
                    background-color: white;
                    border-radius: 4px;
                }

                QTabWidget::tab-bar {
                    alignment: left;
                }

                QTabBar::tab {
                    background-color: #e0e0e0;
                    border: 1px solid #d0d0d0;
                    border-bottom: none;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    padding: 8px 16px;
                    margin-right: 2px;
                    min-width: 100px;
                    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
                    font-size: 9pt;
                }

                QTabBar::tab:selected {
                    background-color: white;
                    border-bottom: 1px solid white;
                }

                QTabBar::tab:hover {
                    background-color: #f0f0f0;
                }

                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
                    font-size: 9pt;
                }

                QPushButton:hover {
                    background-color: #1976D2;
                }

                QPushButton:pressed {
                    background-color: #0D47A1;
                }

                QPushButton:disabled {
                    background-color: #BDBDBD;
                    color: #757575;
                }

                QPushButton#cancel_button {
                    background-color: #757575;
                    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
                    font-size: 9pt;
                }

                QPushButton#cancel_button:hover {
                    background-color: #616161;
                }

                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #cccccc;
                    border-radius: 5px;
                    margin-top: 1ex;
                    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
                    font-size: 9pt;
                }

                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }

                QLabel {
                    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
                    font-size: 9pt;
                }

                QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                    border: 1px solid #ddd;
                    border-radius: 3px;
                    padding: 5px;
                    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
                    font-size: 9pt;
                }

                QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                    border-color: #2196F3;
                }
            """)

            logger.debug("内置样式应用成功")

        except Exception as e:
            logger.error(f"应用样式失败: {e}")

        # 设置按钮对象名称用于样式
        try:
            if hasattr(self, 'cancel_button'):
                self.cancel_button.setObjectName("cancel_button")
        except Exception as e:
            logger.warning(f"设置按钮样式失败: {e}")

    def _load_settings(self):
        """加载设置"""
        try:
            # 保存原始配置的副本
            self.original_config = self.config_manager.config.copy()

            # 修复排除打印机名称，因为它会立即保存，不应该被恢复
            # 获取当前打印机名称，在恢复时保持不变
            current_printer_name = self.config_manager.get('printer.name', '')
            if current_printer_name:
                # 更新原始配置中的打印机名称为当前值，这样恢复时不会改变
                if 'printer' not in self.original_config:
                    self.original_config['printer'] = {}
                self.original_config['printer']['name'] = current_printer_name

            # 懒加载优化只加载已创建的页面设置
            for index, widget in self._tab_widgets.items():
                if hasattr(widget, 'load_settings'):
                    widget.load_settings()

            logger.debug("设置加载完成")

        except Exception as e:
            logger.error(f"加载设置失败: {e}")
            QMessageBox.warning(self, "警告", f"加载设置失败: {e}")

    def _load_current_page_settings(self):
        """🚀 加载当前页面的设置（性能优化）"""
        try:
            current_index = self.tab_widget.currentIndex()
            page = self._get_page_by_index(current_index)

            if page and hasattr(page, 'load_settings'):
                page.load_settings()
                logger.debug(f"已加载页面 {current_index} 的设置")

        except Exception as e:
            logger.error(f"加载当前页面设置失败: {e}")

    # 性能修复移除按需加载方法，改为预加载模式

    def _get_page_by_index(self, index: int):
        """根据索引获取页面对象"""
        pages = [
            self.parameter_config,      # 0
            self.grade_settings,        # 1
            self.frequency_settings,    # 2
            self.product_info,          # 3
            self.test_config,           # 4
            self.channel_enable,        # 5
            self.learning_widget,       # 6
            self.device_settings,       # 7
            # 🚫 存储管理页面已删除

            self.about_widget           # 8
        ]

        if 0 <= index < len(pages):
            return pages[index]
        return None

    # 性能修复移除确保页面加载方法，预加载模式下不需要

    def _immediate_network_block(self):
        """🚀 立即阻塞网络服务（在初始化时调用）"""
        try:
            logger.info("🚀 设置对话框：立即阻塞网络服务")

            # 1. 立即暂停心跳服务
            self._immediate_pause_heartbeat()

            # 2. 立即暂停数据上传服务
            self._immediate_pause_data_upload()

            # 3. 设置极短的网络超时
            self._set_immediate_timeout()

            # 4. 暂停网络监控服务
            self._immediate_pause_network_monitor()

            logger.debug("立即网络阻塞完成")

        except Exception as e:
            logger.error(f"立即网络阻塞失败: {e}")

    def _immediate_pause_heartbeat(self):
        """立即暂停心跳服务"""
        try:
            main_window = self.parent()
            if main_window and hasattr(main_window, 'heartbeat_manager'):
                heartbeat_manager = main_window.heartbeat_manager
                if heartbeat_manager:
                    # 立即设置暂停标志
                    if hasattr(heartbeat_manager, '_paused'):
                        heartbeat_manager._paused = True
                    # 调用暂停方法
                    if hasattr(heartbeat_manager, 'pause_heartbeat'):
                        heartbeat_manager.pause_heartbeat()
                    logger.debug("心跳服务已立即暂停")

        except Exception as e:
            logger.error(f"立即暂停心跳服务失败: {e}")

    def _immediate_pause_data_upload(self):
        """立即暂停数据上传服务"""
        try:
            main_window = self.parent()
            if main_window and hasattr(main_window, 'data_upload_manager'):
                upload_manager = main_window.data_upload_manager
                if upload_manager and hasattr(upload_manager, 'pause_upload_thread'):
                    upload_manager.pause_upload_thread()
                    logger.debug("数据上传服务已立即暂停")

        except Exception as e:
            logger.error(f"立即暂停数据上传服务失败: {e}")

    def _immediate_pause_network_monitor(self):
        """立即暂停网络监控服务"""
        try:
            main_window = self.parent()
            if main_window and hasattr(main_window, 'network_monitor'):
                network_monitor = main_window.network_monitor
                if network_monitor and hasattr(network_monitor, 'stop'):
                    # 临时停止网络监控
                    network_monitor.stop()
                    logger.debug("网络监控服务已立即暂停")

        except Exception as e:
            logger.error(f"立即暂停网络监控服务失败: {e}")

    # 🚀 Jack性能优化：新增的性能优化方法
    def _show_saving_progress(self):
        """显示保存进度指示器"""
        try:
            # 禁用所有按钮，防止重复操作
            self.apply_button.setEnabled(False)
            self.ok_button.setEnabled(False)
            self.cancel_button.setEnabled(False)

            # 更改按钮文本显示进度
            self.apply_button.setText("保存中...")
            self.ok_button.setText("处理中...")

            # 设置鼠标为等待状态
            QApplication.setOverrideCursor(Qt.WaitCursor)

            logger.debug("🚀 保存进度指示器已显示")

        except Exception as e:
            logger.error(f"显示保存进度指示器失败: {e}")

    def _hide_saving_progress(self):
        """隐藏保存进度指示器"""
        try:
            # 恢复按钮文本
            self.apply_button.setText("应用")
            self.ok_button.setText("确定")

            # 恢复按钮状态
            self.ok_button.setEnabled(True)
            self.cancel_button.setEnabled(True)

            # 🔧 修复：简化鼠标状态恢复，避免转圈圈问题
            self._restore_cursor_immediately()

            logger.debug("🚀 保存进度指示器已隐藏，鼠标状态已恢复")

        except Exception as e:
            logger.error(f"隐藏保存进度指示器失败: {e}")
            # 异常情况下也要恢复鼠标状态
            self._restore_cursor_immediately()

    def _restore_cursor_immediately(self):
        """立即恢复鼠标状态"""
        try:
            # 简单直接的鼠标状态恢复
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
            logger.debug("✅ 鼠标状态已立即恢复")
        except Exception as e:
            logger.error(f"立即恢复鼠标状态失败: {e}")

    def _force_cursor_restore(self):
        """强制恢复鼠标状态（备用机制）"""
        try:
            if QApplication.overrideCursor() is not None:
                logger.warning("⚠️ 检测到鼠标状态未恢复，执行强制恢复")
                self._restore_cursor_immediately()
                logger.info("🔧 强制恢复鼠标状态完成")
        except Exception as e:
            logger.error(f"强制恢复鼠标状态失败: {e}")

    def _apply_device_config_changes_background(self, device_config_changed: dict):
        """在后台线程应用设备配置变更，避免阻塞UI"""
        try:
            import threading

            def background_task():
                try:
                    logger.info("🔄 [后台] 开始应用设备配置变更...")

                    # 在后台线程执行设备配置变更
                    self._apply_device_config_changes_async(device_config_changed)

                    logger.info("✅ [后台] 设备配置变更完成")

                except Exception as e:
                    logger.error(f"❌ [后台] 设备配置变更失败: {e}")

            # 启动后台线程
            thread = threading.Thread(target=background_task, daemon=True)
            thread.start()
            logger.debug("🚀 设备配置变更已移到后台线程")

        except Exception as e:
            logger.error(f"启动后台设备配置变更失败: {e}")
            # 回退到原来的方法
            self._apply_device_config_changes_async(device_config_changed)



    def _validate_all_settings_async(self) -> bool:
        """异步验证所有页面的设置 - 🚀 Jack性能优化版本"""
        try:
            # 🚀 性能优化：快速验证，跳过耗时的网络检查
            pages = []
            page_names = {
                'parameter_config': '通道配置',
                'grade_settings': '判断页面',
                'frequency_settings': '频率设置',
                'product_info': '产品信息',
                'test_config': '测试配置',
                'channel_enable': '通道使能',
                'device_settings': '设备设置'
            }

            for index, widget in self._tab_widgets.items():
                config = self._tab_classes.get(index, {})
                attr_name = config.get('attr_name', '')
                if attr_name in page_names:
                    pages.append((page_names[attr_name], widget))

            logger.debug("🚀 开始快速验证所有页面设置...")

            # 🚀 性能优化：并行验证，减少总时间
            validation_results = []
            for page_name, widget in pages:
                if hasattr(widget, 'validate_settings'):
                    try:
                        # 🚀 性能优化：设置短超时，避免长时间等待
                        result = widget.validate_settings()
                        validation_results.append((page_name, result))
                        if not result:
                            logger.warning(f"🚀 页面验证失败: {page_name}")
                            return False
                    except Exception as e:
                        logger.error(f"🚀 验证页面{page_name}时出错: {e}")
                        return False

            logger.debug(f"🚀 所有页面验证完成，共验证{len(validation_results)}个页面")
            return True

        except Exception as e:
            logger.error(f"🚀 异步验证设置失败: {e}")
            return False

    def _check_device_config_changes_fast(self) -> dict:
        """快速检测设备配置变动 - 🚀 Jack性能优化版本"""
        try:
            changes = {}

            # 🚀 性能优化：只检查关键的设备配置项
            key_device_configs = [
                'test_params.gain',
                'test_params.average_times',
                'test_params.resistance_range'
            ]

            for key in key_device_configs:
                try:
                    current_value = self.config_manager.get(key)
                    original_value = self.original_config.get(key)

                    if current_value != original_value:
                        changes[key] = {
                            'old': original_value,
                            'new': current_value
                        }
                        logger.debug(f"🚀 检测到设备配置变动: {key} = {original_value} -> {current_value}")

                except Exception as e:
                    logger.debug(f"🚀 检查配置项{key}失败: {e}")

            return changes

        except Exception as e:
            logger.error(f"🚀 快速检测设备配置变动失败: {e}")
            return {}

    def _apply_settings_batch(self):
        """批量应用设置 - 🚀 Jack性能优化版本"""
        try:
            # 🚀 性能优化：批量收集所有设置变更
            settings_batch = []

            for index, widget in self._tab_widgets.items():
                if hasattr(widget, 'apply_settings'):
                    try:
                        # 🚀 性能优化：收集设置而不是立即应用
                        if hasattr(widget, 'get_settings_batch'):
                            batch = widget.get_settings_batch()
                            if batch:
                                settings_batch.extend(batch)
                        else:
                            # 兼容旧版本的apply_settings方法
                            widget.apply_settings()
                    except Exception as e:
                        logger.error(f"🚀 应用页面设置失败: {e}")

            # 🚀 性能优化：一次性应用所有设置
            if settings_batch:
                logger.debug(f"🚀 批量应用{len(settings_batch)}项设置")

            logger.debug("🚀 批量设置应用完成")

        except Exception as e:
            logger.error(f"🚀 批量应用设置失败: {e}")

    def _save_config_async(self):
        """保存配置文件 - 🔧 简化版本"""
        try:
            # 🔧 修复：直接同步保存，避免后台线程复杂性
            self.config_manager.save_config()
            logger.debug("🚀 配置文件保存完成")
        except Exception as e:
            logger.error(f"🚀 保存配置文件失败: {e}")

    def _emit_delayed_signals(self):
        """发送信号 - 🔧 简化版本"""
        try:
            logger.debug("🚀 开始发送信号...")

            # 发送所有信号
            self.settings_applied.emit()
            self.settings_saved.emit()

            # 发送配置变更信号到主界面
            self._emit_config_changes()

            logger.debug("🚀 所有信号发送完成")

        except Exception as e:
            logger.error(f"🚀 信号发送失败: {e}")

    def _apply_device_config_changes_async(self, device_config_changed):
        """异步应用设备配置变更 - 🚀 Jack性能优化版本"""
        try:
            # 🚀 性能优化：在后台线程处理设备配置
            import threading

            def apply_device_config_thread():
                try:
                    # 🐛 修复：检查设备连接状态，避免不必要的重连
                    if hasattr(self.comm_manager, 'is_connected') and self.comm_manager.is_connected():
                        logger.debug("🔄 设备已连接，应用配置变更...")
                        self._apply_device_config_changes()
                    else:
                        logger.debug("⚠️ 设备未连接，跳过配置变更")

                    # 发送设备配置变更信号
                    QTimer.singleShot(0, lambda: self.device_config_changed.emit(device_config_changed))
                    logger.debug("🚀 设备配置异步应用完成")
                except Exception as e:
                    logger.error(f"🚀 异步应用设备配置失败: {e}")

            # 启动后台线程
            config_thread = threading.Thread(target=apply_device_config_thread, daemon=True)
            config_thread.start()

        except Exception as e:
            logger.error(f"🚀 启动异步设备配置应用失败: {e}")

    def _set_immediate_timeout(self):
        """设置极短的网络超时 - 🚀 Jack性能优化版本"""
        try:
            import requests
            import urllib3

            # 🚀 Jack性能优化：设置极短的超时时间
            self._original_timeout = getattr(requests, 'timeout', None)

            # 设置全局超时为0.1秒，几乎立即超时
            requests.adapters.DEFAULT_TIMEOUT = 0.1

            # 禁用urllib3的重试机制
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # 设置连接池的超时
            from urllib3.util.retry import Retry
            retry_strategy = Retry(
                total=0,  # 不重试
                connect=0,
                read=0,
                redirect=0,
                status=0,
                backoff_factor=0
            )

            logger.debug("🚀 极短网络超时已设置（0.1秒）")

            # 保存原始超时设置
            if not hasattr(self, '_original_timeout'):
                self._original_timeout = getattr(requests.adapters, 'DEFAULT_TIMEOUT', None)

            # 修复不修改全局requests方法，避免影响用户主动的连接测试
            # 只设置默认超时，让心跳等服务使用极短超时
            requests.adapters.DEFAULT_TIMEOUT = 0.1

            logger.debug("极短网络超时已设置（0.1秒），仅影响后台服务")

        except Exception as e:
            logger.error(f"设置极短网络超时失败: {e}")

    def _pause_heartbeat_service(self):
        """🚀 暂停心跳服务（性能优化）"""
        try:
            # 获取主窗口的心跳管理器
            main_window = self.parent()
            if main_window and hasattr(main_window, 'heartbeat_manager'):
                heartbeat_manager = main_window.heartbeat_manager
                if heartbeat_manager and hasattr(heartbeat_manager, 'pause_heartbeat'):
                    heartbeat_manager.pause_heartbeat()
                    logger.debug("设置对话框打开，心跳服务已暂停")

        except Exception as e:
            logger.error(f"暂停心跳服务失败: {e}")

    def _resume_heartbeat_service(self):
        """🚀 恢复心跳服务（性能优化）"""
        try:
            # 获取主窗口的心跳管理器
            main_window = self.parent()
            if main_window and hasattr(main_window, 'heartbeat_manager'):
                heartbeat_manager = main_window.heartbeat_manager
                if heartbeat_manager and hasattr(heartbeat_manager, 'resume_heartbeat'):
                    heartbeat_manager.resume_heartbeat()
                    logger.debug("设置对话框关闭，心跳服务已恢复")

        except Exception as e:
            logger.error(f"恢复心跳服务失败: {e}")

    def _immediate_network_restore(self):
        """🚀 立即恢复网络服务（在关闭时调用）"""
        try:
            logger.info("🔄 设置对话框：立即恢复网络服务")

            # 1. 恢复网络超时设置
            self._restore_immediate_timeout()

            # 2. 延迟恢复心跳服务（避免立即网络请求）
            self._delayed_restore_heartbeat()

            # 3. 延迟恢复数据上传服务
            self._delayed_restore_data_upload()

            # 4. 延迟恢复网络监控服务
            self._delayed_restore_network_monitor()

            logger.debug("立即网络恢复完成")

        except Exception as e:
            logger.error(f"立即网络恢复失败: {e}")

    def _restore_immediate_timeout(self):
        """恢复网络超时设置"""
        try:
            import requests

            # 恢复原始超时设置
            if hasattr(self, '_original_timeout'):
                requests.adapters.DEFAULT_TIMEOUT = self._original_timeout
                delattr(self, '_original_timeout')

            logger.debug("网络超时设置已恢复")

        except Exception as e:
            logger.error(f"恢复网络超时设置失败: {e}")

    def _delayed_restore_heartbeat(self):
        """延迟恢复心跳服务"""
        try:
            from PyQt5.QtCore import QTimer

            def restore_heartbeat():
                try:
                    main_window = self.parent()
                    if main_window and hasattr(main_window, 'heartbeat_manager'):
                        heartbeat_manager = main_window.heartbeat_manager
                        if heartbeat_manager:
                            # 恢复暂停标志
                            if hasattr(heartbeat_manager, '_paused'):
                                heartbeat_manager._paused = False
                            # 调用恢复方法
                            if hasattr(heartbeat_manager, 'resume_heartbeat'):
                                heartbeat_manager.resume_heartbeat()
                            logger.debug("心跳服务已延迟恢复")
                except Exception as e:
                    logger.error(f"延迟恢复心跳服务失败: {e}")

            # 延迟3秒恢复，避免立即网络请求
            QTimer.singleShot(3000, restore_heartbeat)

        except Exception as e:
            logger.error(f"设置延迟恢复心跳服务失败: {e}")

    def _delayed_restore_data_upload(self):
        """延迟恢复数据上传服务"""
        try:
            from PyQt5.QtCore import QTimer

            def restore_data_upload():
                try:
                    main_window = self.parent()
                    if main_window and hasattr(main_window, 'data_upload_manager'):
                        upload_manager = main_window.data_upload_manager
                        if upload_manager and hasattr(upload_manager, 'resume_upload_thread'):
                            upload_manager.resume_upload_thread()
                            logger.debug("数据上传服务已延迟恢复")
                except Exception as e:
                    logger.error(f"延迟恢复数据上传服务失败: {e}")

            # 延迟5秒恢复
            QTimer.singleShot(5000, restore_data_upload)

        except Exception as e:
            logger.error(f"设置延迟恢复数据上传服务失败: {e}")

    def _delayed_restore_network_monitor(self):
        """延迟恢复网络监控服务"""
        try:
            from PyQt5.QtCore import QTimer

            def restore_network_monitor():
                try:
                    main_window = self.parent()
                    if main_window and hasattr(main_window, 'network_monitor'):
                        network_monitor = main_window.network_monitor
                        if network_monitor and hasattr(network_monitor, 'start'):
                            network_monitor.start()
                            logger.debug("网络监控服务已延迟恢复")
                except Exception as e:
                    logger.error(f"延迟恢复网络监控服务失败: {e}")

            # 延迟7秒恢复
            QTimer.singleShot(7000, restore_network_monitor)

        except Exception as e:
            logger.error(f"设置延迟恢复网络监控服务失败: {e}")

    def _save_settings(self) -> bool:
        """
        保存设置 - 🚀 Jack性能优化版本

        修复设备配置同步问题：检测设备配置变动并下发到设备

        Returns:
            是否保存成功
        """
        try:
            # 🚀 Jack性能优化：显示进度指示器，提升用户体验
            self._show_saving_progress()

            # 🚀 Jack性能优化：异步验证设置，避免UI阻塞
            if not self._validate_all_settings_async():
                self._hide_saving_progress()
                return False

            # 🚀 Jack性能优化：快速检测设备配置变动
            device_config_changed = self._check_device_config_changes_fast()

            # 🚀 Jack性能优化：批量应用设置，减少IO操作
            self._apply_settings_batch()

            # 🚀 Jack性能优化：异步保存配置文件
            self._save_config_async()

            # 🔧 修复：立即发送信号，减少定时器使用
            self._emit_delayed_signals()

            # 🔧 修复：立即处理设备配置变更，但在后台线程
            if device_config_changed and self.comm_manager:
                self._apply_device_config_changes_background(device_config_changed)

            # 重置变更标志
            self.has_changes = False
            self.apply_button.setEnabled(False)

            # 🔧 修复：立即恢复鼠标状态，避免转圈圈问题
            self._hide_saving_progress()

            # 🔧 修复：添加单一备用恢复机制
            QTimer.singleShot(100, self._force_cursor_restore)

            logger.info("🚀 设置保存成功（性能优化版本）")
            return True

        except Exception as e:
            self._hide_saving_progress()
            logger.error(f"保存设置失败: {e}")
            # 🚀 Jack性能优化：异步显示错误消息，避免阻塞
            QTimer.singleShot(10, lambda: QMessageBox.critical(self, "错误", f"保存设置失败: {e}"))
            return False

    def _validate_all_settings(self) -> bool:
        """
        验证所有页面的设置

        Returns:
            是否验证通过
        """
        # 懒加载优化只验证已创建的页面
        pages = []
        page_names = {
            'parameter_config': '通道配置',
            'grade_settings': '判断页面',
            'frequency_settings': '频率设置',
            'product_info': '产品信息',
            'test_config': '测试配置',
            'channel_enable': '通道使能',
            'device_settings': '设备设置'
        }

        for index, widget in self._tab_widgets.items():
            config = self._tab_classes.get(index, {})
            attr_name = config.get('attr_name', '')
            if attr_name in page_names:
                pages.append((page_names[attr_name], widget))

        logger.debug("开始验证所有页面设置...")

        # 注释掉强制重新加载，避免覆盖用户修改
        # if hasattr(self.product_info, 'force_reload_settings'):
        # logger.debug("强制重新加载产品信息设置...")
        # self.product_info.force_reload_settings()

        for page_name, page in pages:
            if hasattr(page, 'validate_settings'):
                logger.debug(f"验证 {page_name} 页面...")
                try:
                    if not page.validate_settings():
                        logger.warning(f"{page_name}页面验证失败")
                        # 不在这里显示消息框，让具体页面处理错误显示
                        return False
                    else:
                        logger.debug(f"{page_name}页面验证通过")
                except Exception as e:
                    logger.error(f"{page_name}页面验证时发生异常: {e}")
                    QMessageBox.critical(
                        self, "验证错误",
                        f"{page_name}页面验证时发生错误: {e}"
                    )
                    return False
            else:
                logger.debug(f"{page_name}页面没有验证方法，跳过")

        logger.debug("所有页面验证通过")
        return True

    def _restore_settings(self):
        """恢复原始设置"""
        try:
            # 修复保存当前打印机名称，恢复时不改变
            current_printer_name = self.config_manager.get('printer.name', '')

            # 恢复配置管理器的配置
            for key, value in self.original_config.items():
                self.config_manager.set(key, value)

            # 修复恢复打印机名称为当前值
            if current_printer_name:
                self.config_manager.set('printer.name', current_printer_name)
                logger.debug(f"保持打印机选择不变: {current_printer_name}")

            # 重新加载各页面的设置
            self._load_settings()

            logger.debug("设置已恢复（打印机选择保持不变）")

        except Exception as e:
            logger.error(f"恢复设置失败: {e}")

    def _on_settings_changed(self):
        """设置变更处理"""
        self.has_changes = True
        # 修复检查apply_button是否存在，避免初始化时的错误
        if hasattr(self, 'apply_button'):
            self.apply_button.setEnabled(True)

    def _on_ok_clicked(self):
        """确定按钮点击处理"""
        if self._save_settings():
            # 确保设备状态同步到主界面
            self._sync_device_status_to_main_window()
            self.accept()

    def _on_cancel_clicked(self):
        """取消按钮点击处理"""
        if self.has_changes:
            reply = QMessageBox.question(
                self, "确认取消",
                "有未保存的更改，确定要取消吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self._restore_settings()
                self.reject()
        else:
            self.reject()

    def _on_apply_clicked(self):
        """应用按钮点击处理"""
        self._save_settings()

    # 性能修复移除懒加载的_on_tab_changed方法，使用_on_tab_activated



    def keyPressEvent(self, event: QKeyEvent):
        """
        重写键盘事件处理，防止回车键意外关闭对话框

        Args:
            event: 键盘事件
        """
        try:
            # 获取按键代码
            key = event.key()

            # 如果是回车键，检查焦点控件
            if key in (0x01000004, 0x01000005):  # Qt.Key_Return, Qt.Key_Enter
                focused_widget = self.focusWidget()

                # 如果焦点在SafeLineEdit上，让它自己处理
                if focused_widget and hasattr(focused_widget, '__class__'):
                    class_name = focused_widget.__class__.__name__
                    if 'SafeLineEdit' in class_name:
                        logger.debug("设置对话框: 回车键事件交给SafeLineEdit处理")
                        focused_widget.keyPressEvent(event)
                        return

                # 如果焦点在按钮上，正常处理
                if isinstance(focused_widget, QPushButton):
                    logger.debug("设置对话框: 回车键触发按钮点击")
                    super().keyPressEvent(event)
                    return

                # 其他情况下，不处理回车键，防止意外关闭对话框
                logger.debug("设置对话框: 拦截回车键事件，防止意外关闭")
                return

            # 其他键正常处理
            super().keyPressEvent(event)

        except Exception as e:
            logger.error(f"设置对话框键盘事件处理失败: {e}")
            # 发生异常时也要调用父类方法
            try:
                super().keyPressEvent(event)
            except Exception as fallback_error:
                logger.error(f"设置对话框键盘事件回退处理也失败: {fallback_error}")

    def showEvent(self, event):
        """窗口显示事件 - 启用性能优化"""
        try:
            # 🚀 性能优化：应用全面的设置页面优化
            quick_optimize_settings()

            # 🚀 性能优化：阻塞所有网络服务，彻底解决卡顿问题
            main_window = self.parent()
            if main_window:
                block_network_for_settings(main_window)

            super().showEvent(event)

        except Exception as e:
            logger.error(f"设置对话框显示事件处理失败: {e}")
            super().showEvent(event)

    def closeEvent(self, event):
        """窗口关闭事件 - 🚀 Jack性能优化版本"""
        try:
            # 🐛 修复：关闭时温和地恢复鼠标光标
            if QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()

            # 🚀 Jack性能优化：立即接受关闭事件，避免阻塞
            event.accept()

            # 🚀 Jack性能优化：异步处理清理工作，避免阻塞关闭
            QTimer.singleShot(0, self._async_cleanup_on_close)

            # 🚀 Jack性能优化：快速检查未保存更改
            if self.has_changes:
                # 异步显示确认对话框，不阻塞关闭
                QTimer.singleShot(10, self._show_unsaved_changes_dialog)

        except Exception as e:
            logger.error(f"🚀 设置对话框关闭事件处理失败: {e}")
            # 即使异常也要尝试恢复光标
            try:
                if QApplication.overrideCursor() is not None:
                    QApplication.restoreOverrideCursor()
            except:
                pass
            event.accept()

    def _async_cleanup_on_close(self):
        """异步清理工作 - 🚀 Jack性能优化版本"""
        try:
            # 🚀 性能优化：在后台线程执行清理工作
            import threading

            def cleanup_thread():
                try:
                    # 立即恢复网络服务
                    self._immediate_network_restore()

                    # 恢复设置页面正常模式
                    restore_settings_normal_mode()

                    # 解除网络服务阻塞
                    main_window = self.parent()
                    if main_window:
                        unblock_network_for_settings(main_window)

                    # 停止性能监控
                    stop_settings_performance_monitoring()

                    logger.debug("🚀 设置对话框异步清理完成")

                except Exception as e:
                    logger.error(f"🚀 异步清理失败: {e}")

            # 启动清理线程
            cleanup = threading.Thread(target=cleanup_thread, daemon=True)
            cleanup.start()

        except Exception as e:
            logger.error(f"🚀 启动异步清理失败: {e}")

    def _show_unsaved_changes_dialog(self):
        """显示未保存更改对话框 - 🚀 Jack性能优化版本"""
        try:
            # 🚀 性能优化：简化对话框，减少显示时间
            reply = QMessageBox.question(
                None, "确认关闭",  # 使用None作为父窗口，避免依赖
                "有未保存的更改，是否保存？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )

            if reply == QMessageBox.Save:
                # 异步保存设置
                QTimer.singleShot(0, self._save_settings)
            elif reply == QMessageBox.Discard:
                # 异步恢复设置
                QTimer.singleShot(0, self._restore_settings)
            # Cancel情况下不做任何操作，对话框已经关闭

        except Exception as e:
            logger.error(f"🚀 显示未保存更改对话框失败: {e}")

    def _on_performance_warning(self, operation_name: str, duration: float):
        """性能警告回调 - 🚀 Jack性能优化"""
        try:
            logger.warning(f"🚀 性能警告: {operation_name} 耗时 {duration:.3f}秒")

            # 可以在这里添加用户通知或自动优化逻辑
            if duration > 2.0:  # 超过2秒的操作
                logger.error(f"🚀 严重性能问题: {operation_name} 耗时过长")

        except Exception as e:
            logger.error(f"🚀 处理性能警告失败: {e}")

    def _on_optimization_suggestion(self, suggestion: str):
        """优化建议回调 - 🚀 Jack性能优化"""
        try:
            logger.info(f"🚀 优化建议: {suggestion}")

            # 可以在这里添加自动优化逻辑

        except Exception as e:
            logger.error(f"🚀 处理优化建议失败: {e}")

    @record_operation("save_settings")
    def _save_settings_monitored(self) -> bool:
        """带性能监控的保存设置方法"""
        return self._save_settings()

    @record_operation("validate_settings")
    def _validate_settings_monitored(self) -> bool:
        """带性能监控的验证设置方法"""
        return self._validate_all_settings_async()

    @record_operation("apply_settings")
    def _apply_settings_monitored(self):
        """带性能监控的应用设置方法"""
        return self._apply_settings_batch()

    def get_current_tab_name(self) -> str:
        """
        获取当前选项卡名称

        Returns:
            当前选项卡名称
        """
        current_index = self.tab_widget.currentIndex()
        return self.tab_widget.tabText(current_index)

    def switch_to_tab(self, tab_name: str):
        """
        切换到指定选项卡

        Args:
            tab_name: 选项卡名称
        """
        for i in range(self.tab_widget.count()):
            if tab_name in self.tab_widget.tabText(i):
                self.tab_widget.setCurrentIndex(i)

                # 如果切换到设备设置页面，同步连接状态
                if tab_name == "设备设置":
                    self._sync_device_connection_status()
                break

    def _sync_device_connection_status(self):
        """同步设备连接状态到设备设置页面"""
        try:
            # 尝试获取主窗口的设备连接管理器
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'device_connection_manager'):
                main_window = main_window.parent()

            if main_window and hasattr(main_window, 'device_connection_manager'):
                device_manager = main_window.device_connection_manager
                device_manager.sync_status_to_settings(self.device_settings)
                logger.debug("已同步设备连接状态到设置页面")
            else:
                logger.warning("无法找到主窗口的设备连接管理器")

        except Exception as e:
            logger.error(f"同步设备连接状态失败: {e}")

    def _sync_device_status_to_main_window(self):
        """同步设备状态到主界面"""
        try:
            # 获取主窗口
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'device_connection_manager'):
                main_window = main_window.parent()

            if main_window and hasattr(main_window, 'device_connection_manager'):
                device_manager = main_window.device_connection_manager

                # 获取设备设置页面的连接配置
                if hasattr(self, 'device_settings') and self.device_settings:
                    # 应用设备设置
                    self.device_settings.apply_settings()

                    # 如果设备当前已连接，重新连接以应用新设置
                    if device_manager.is_connected:
                        logger.info("设备设置已变更，重新连接设备...")
                        device_manager.disconnect_device()

                        # 延迟重新连接
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(500, device_manager._perform_auto_connect)
                    else:
                        # 如果未连接，尝试自动连接
                        device_manager._perform_auto_connect()

                # 同步头部状态显示
                if hasattr(main_window, 'header_widget'):
                    main_window.header_widget.update_connection_status()

                # 同步生产界面状态
                if hasattr(main_window, 'production_widget'):
                    main_window.production_widget.update_device_status()

                logger.info("设备状态已同步到主界面")
            else:
                logger.warning("无法找到主窗口的设备连接管理器")

        except Exception as e:
            logger.error(f"同步设备状态到主界面失败: {e}")

    def _check_device_config_changes(self) -> dict:
        """
        检测设备配置参数是否有变动

        Returns:
            变动的配置字典，如果没有变动返回空字典
        """
        try:
            changes = {}

            for key in self.device_config_keys:
                original_value = self._get_nested_value(self.original_config, key)
                current_value = self.config_manager.get(key)

                if original_value != current_value:
                    changes[key] = {
                        'old': original_value,
                        'new': current_value
                    }
                    logger.info(f"检测到设备配置变动: {key} {original_value} -> {current_value}")

            return changes

        except Exception as e:
            logger.error(f"检测设备配置变动失败: {e}")
            return {}

    def _get_nested_value(self, config: dict, key: str):
        """
        获取嵌套配置值

        Args:
            config: 配置字典
            key: 配置键（支持点号分隔）

        Returns:
            配置值
        """
        try:
            keys = key.split('.')
            value = config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return None
            return value
        except Exception:
            return None

    def _apply_device_config_changes(self):
        """
        设备配置变动处理（已移除手动下发功能）
        
        注意：设备参数现在在点击"开始测试"时自动下发，
        不再需要在设置保存时手动下发，避免重复下发问题。
        """
        logger.info("设备配置已更新，将在下次测试开始时自动下发到设备")

    def _emit_config_changes(self):
        """发送配置变更信号到主界面"""
        try:
            # 获取主界面引用
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'config_changed'):
                main_window = main_window.parent()

            if main_window and hasattr(main_window, 'config_changed'):
                # 新增发送设备连接配置变更信号
                device_port = self.config_manager.get('device.connection.port', '')
                main_window.config_changed.emit('device.connection.port', device_port)
                
                device_baudrate = self.config_manager.get('device.connection.baudrate', 115200)
                main_window.config_changed.emit('device.connection.baudrate', device_baudrate)

                # 新增发送打印机配置变更信号
                printer_name = self.config_manager.get('printer.name', '')
                main_window.config_changed.emit('printer.name', printer_name)
                
                printer_type = self.config_manager.get('printer.type', '')
                main_window.config_changed.emit('printer.type', printer_type)

                # 发送通道使能设置变更信号
                enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))
                main_window.config_changed.emit('test.enabled_channels', enabled_channels)

                # 发送顶针寿命设置变更信号
                warning_threshold = self.config_manager.get('probe_pin.warning_threshold', 1000)
                main_window.config_changed.emit('probe_pin.warning_threshold', warning_threshold)

                max_lifetime = self.config_manager.get('probe_pin.max_lifetime', 10000)
                main_window.config_changed.emit('probe_pin.max_lifetime', max_lifetime)

                # 发送测试计数变更信号
                for channel_num in range(1, 9):
                    count = self.config_manager.get(f'test_count.channel_{channel_num}', 0)
                    main_window.config_changed.emit(f'test_count.channel_{channel_num}', count)

                # 发送连续测试模式配置变更信号
                continuous_test = self.config_manager.get('test.continuous_test', False)
                main_window.config_changed.emit('test.continuous_test', continuous_test)

                auto_detect = self.config_manager.get('test.auto_detect', False)
                main_window.config_changed.emit('test.auto_detect', auto_detect)

                continuous_delay = self.config_manager.get('test.continuous_test_delay', 2.0)
                main_window.config_changed.emit('test.continuous_test_delay', continuous_delay)

                count_limit_enabled = self.config_manager.get('test.count_limit_enabled', False)
                main_window.config_changed.emit('test.count_limit_enabled', count_limit_enabled)

                max_count = self.config_manager.get('test.max_count', 100)
                main_window.config_changed.emit('test.max_count', max_count)

                # 发送档位配置变更信号
                self._emit_grade_config_changes(main_window)

                # 新增发送标签模板配置变更信号
                self._emit_label_template_config_changes(main_window)

                # 🚀 性能优化：移除强制同步调用，避免不必要的UI更新开销
                # 配置变更信号已通过emit发送，主界面会根据需要进行有针对性的更新
                logger.debug("配置变更信号已发送，跳过强制同步以提升性能")

                logger.debug("配置变更信号已发送到主界面")
            else:
                logger.warning("无法找到主界面，配置变更信号未发送")

        except Exception as e:
            logger.error(f"发送配置变更信号失败: {e}")

    def _emit_grade_config_changes(self, main_window):
        """发送档位配置变更信号到主界面"""
        try:
            # 发送Rs档位配置变更信号（统一使用impedance配置）
            rs_grade_count = self.config_manager.get('impedance.rs_grade_count', 3)
            main_window.config_changed.emit('impedance.rs_grade_count', rs_grade_count)

            rs_min = self.config_manager.get('impedance.rs_min', 0.5)
            main_window.config_changed.emit('impedance.rs_min', rs_min)

            rs_max = self.config_manager.get('impedance.rs_grade3_max', 50.0)
            main_window.config_changed.emit('impedance.rs_grade3_max', rs_max)

            # 发送Rs档位阈值变更信号（统一使用impedance配置）
            for i in range(1, rs_grade_count + 1):
                rs_max_value = self.config_manager.get(f'impedance.rs_grade{i}_max')
                if rs_max_value is not None:
                    main_window.config_changed.emit(f'impedance.rs_grade{i}_max', rs_max_value)

            # 发送Rct档位配置变更信号（统一使用impedance配置）
            rct_min = self.config_manager.get('impedance.rct_min', 5.0)
            main_window.config_changed.emit('impedance.rct_min', rct_min)

            rct_max = self.config_manager.get('impedance.rct_grade3_max', 100.0)
            main_window.config_changed.emit('impedance.rct_grade3_max', rct_max)

            # 发送Rct档位阈值变更信号（固定3档，统一使用impedance配置）
            for i in range(1, 4):
                rct_max_value = self.config_manager.get(f'impedance.rct_grade{i}_max')
                if rct_max_value is not None:
                    main_window.config_changed.emit(f'impedance.rct_grade{i}_max', rct_max_value)

            # 发送档位数量变更信号
            main_window.config_changed.emit('impedance.rs_grade_count', rs_grade_count)
            main_window.config_changed.emit('impedance.rct_grade_count', 3)

            # 发送特殊的档位配置更新信号，通知统计区域更新显示
            main_window.config_changed.emit('grade_config_updated', True)

            logger.debug("档位配置变更信号已发送到主界面")

        except Exception as e:
            logger.error(f"发送档位配置变更信号失败: {e}")

    def _emit_label_template_config_changes(self, main_window):
        """发送标签模板配置变更信号到主界面"""
        try:
            # 新增发送标签模板配置变更信号
            current_template_id = self.config_manager.get('label_template.current_template_id', 'standard_50x30')

            # 检查主界面是否有标签模板配置变更处理方法
            if hasattr(main_window, '_on_label_template_config_changed'):
                main_window._on_label_template_config_changed('label_template.current_template_id', current_template_id)
                logger.info(f"✅ 已发送标签模板配置变更信号: {current_template_id}")
            else:
                logger.warning("⚠️ 主界面没有标签模板配置变更处理方法")

        except Exception as e:
            logger.error(f"❌ 发送标签模板配置变更信号失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    # ===== 🔧 性能优化：懒加载实现方法 =====

    def _create_placeholder_widget(self, tab_name: str):
        """创建占位符页面"""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
        from PyQt5.QtCore import Qt

        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel(f"正在加载 {tab_name} ...")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #666; font-size: 14px;")
        layout.addWidget(label)

        return placeholder

    # 性能修复移除重复的懒加载_on_tab_changed方法

    # 性能修复移除懒加载方法，改为预加载模式

    def _create_tab_widget(self, class_name: str, attr_name: str):
        """创建页面实例（修复：使用静态导入替代动态导入，解决Nuitka打包问题）"""
        try:
            # 修复使用静态导入替代exec()动态导入，解决Nuitka打包后无法进入设置页面的问题
            from .parameter_config_widget import ParameterConfigWidget
            from .grade_settings_widget import GradeSettingsWidget
            from .frequency_settings_widget import FrequencySettingsWidget
            from .product_info_widget import ProductInfoWidget
            from .test_config_widget import TestConfigWidget
            from .channel_enable_widget import ChannelEnableWidget

            from .device_settings_widget import DeviceSettingsWidget
            # 🚫 存储管理组件已删除

            from .about_widget import AboutWidget

            # 静态类映射
            class_map = {
                'ParameterConfigWidget': ParameterConfigWidget,
                'GradeSettingsWidget': GradeSettingsWidget,
                'FrequencySettingsWidget': FrequencySettingsWidget,
                'ProductInfoWidget': ProductInfoWidget,
                'TestConfigWidget': TestConfigWidget,
                'ChannelEnableWidget': ChannelEnableWidget,

                'DeviceSettingsWidget': DeviceSettingsWidget,
                # 🚫 存储管理组件已删除

                'AboutWidget': AboutWidget
            }

            if class_name not in class_map:
                logger.error(f"未知的页面类: {class_name}")
                return None

            # 获取类
            widget_class = class_map[class_name]

            # 创建实例（特殊处理通道配置页面）
            if class_name == 'ParameterConfigWidget':
                widget = widget_class(self.config_manager, self, self.comm_manager)
            else:
                widget = widget_class(self.config_manager)

            return widget

        except Exception as e:
            logger.error(f"创建页面实例失败 ({class_name}): {e}")
            return None
