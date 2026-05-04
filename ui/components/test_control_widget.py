# -*- coding: utf-8 -*-
"""
测试控制组件
包含开始/停止按钮、统计清理、导出数据、设置等控制功能

Author: Jack
Date: 2025-01-27
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QGroupBox, QMessageBox, QFrame, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
import logging

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager
from ui.dialogs.battery_detection_guide_dialog import BatteryDetectionGuideDialog


class TestControlWidget(QWidget):
    """测试控制组件"""

    # 信号定义
    start_test = pyqtSignal()  # 开始测试信号
    stop_test = pyqtSignal()  # 停止测试信号
    clear_statistics = pyqtSignal()  # 清理统计信号
    export_data = pyqtSignal()  # 导出数据信号
    open_settings = pyqtSignal()  # 打开设置信号

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        初始化测试控制组件

        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.is_testing = False

        # 初始化界面
        self._init_ui()

        logger.debug("测试控制组件初始化完成")

    def _init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 创建分组框
        group_box = QGroupBox("测试控制")
        group_box.setObjectName("controlGroup")
        main_layout.addWidget(group_box)

        # 创建内容布局
        content_layout = QVBoxLayout(group_box)
        content_layout.setContentsMargins(10, 15, 10, 10)
        content_layout.setSpacing(10)

        # 创建测试模式状态显示框
        self._create_test_mode_status_display(content_layout)

        # 创建连续测试状态指示器
        self._create_continuous_status_indicator(content_layout)

        # 创建控制按钮
        self._create_control_buttons(content_layout)

        # 设置组件样式
        self._apply_styles()

    def _create_test_mode_status_display(self, layout):
        """创建测试模式状态显示框（简洁版）"""

        # 测试模式状态容器（简洁版）
        mode_status_container = QFrame()
        mode_status_container.setObjectName("testModeStatusContainer")

        mode_status_layout = QHBoxLayout(mode_status_container)
        mode_status_layout.setContentsMargins(6, 4, 6, 4)  # 减小边距
        mode_status_layout.setSpacing(6)  # 减小间距

        # 测试模式状态显示（简洁版，不显示"当前模式:"标题）
        self.test_mode_status_label = QLabel("手动模式")
        self.test_mode_status_label.setObjectName("testModeStatusLabel")
        mode_status_layout.addWidget(self.test_mode_status_label)

        # 分隔符
        separator = QLabel("|")
        separator.setStyleSheet("color: #999; font-weight: bold;")
        mode_status_layout.addWidget(separator)

        # 频点数量显示
        self.frequency_count_label = QLabel("频点: 20")
        self.frequency_count_label.setObjectName("frequencyCountLabel")
        self.frequency_count_label.setStyleSheet("color: #666; font-size: 11px;")
        mode_status_layout.addWidget(self.frequency_count_label)

        # 弹性空间
        mode_status_layout.addStretch()

        layout.addWidget(mode_status_container)

        # 保存引用
        self.test_mode_status_container = mode_status_container

        # 初始化状态显示
        self._update_test_mode_status()

    def _create_continuous_status_indicator(self, layout):
        """创建连续测试状态指示器"""

        # 连续测试状态容器
        status_container = QFrame()
        status_container.setObjectName("continuousStatusContainer")
        status_container.setVisible(False)  # 默认隐藏

        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(8, 6, 8, 6)
        status_layout.setSpacing(8)

        # 状态指示器
        self.continuous_status_label = QLabel("🔄 连续测试模式")
        self.continuous_status_label.setObjectName("continuousStatusLabel")
        status_layout.addWidget(self.continuous_status_label)

        # 测试计数显示
        self.test_count_label = QLabel("当前: 0 次")
        self.test_count_label.setObjectName("testCountLabel")
        status_layout.addWidget(self.test_count_label)

        # 弹性空间
        status_layout.addStretch()

        # 停止连续测试按钮
        self.stop_continuous_button = QPushButton("停止连续测试")
        self.stop_continuous_button.setObjectName("stopContinuousButton")
        self.stop_continuous_button.setMinimumHeight(20)  # 减少最小高度以适配14%布局空间
        self.stop_continuous_button.clicked.connect(self._on_stop_continuous_clicked)
        status_layout.addWidget(self.stop_continuous_button)

        layout.addWidget(status_container)

        # 保存引用
        self.continuous_status_container = status_container

    def _create_control_buttons(self, layout):
        """创建控制按钮"""
        # 第一行按钮：开始测试 + 统计清理 水平并排
        first_row_layout = QHBoxLayout()
        first_row_layout.setSpacing(8)  # 设置按钮间距

        # 开始/停止测试按钮
        self.start_stop_button = QPushButton("开始测试")
        self.start_stop_button.setObjectName("startButton")
        self.start_stop_button.setMinimumHeight(35)  # 减少最小高度以适配12%布局空间
        self.start_stop_button.clicked.connect(self._on_start_stop_clicked)
        first_row_layout.addWidget(self.start_stop_button)

        # 统计清理按钮
        self.clear_button = QPushButton("统计清理")
        self.clear_button.setObjectName("warningButton")
        self.clear_button.setMinimumHeight(35)  # 与开始测试按钮保持相同高度
        self.clear_button.clicked.connect(self._on_clear_clicked)
        first_row_layout.addWidget(self.clear_button)

        # 将第一行按钮布局添加到主布局
        first_row_widget = QWidget()
        first_row_widget.setLayout(first_row_layout)
        layout.addWidget(first_row_widget)

        # 第二行按钮：数据分析 + 设置 水平并排
        second_row_layout = QHBoxLayout()
        second_row_layout.setSpacing(8)  # 设置按钮间距

        # 数据分析按钮
        self.export_button = QPushButton("数据分析")
        self.export_button.setMinimumHeight(28)  # 减少最小高度以适配12%布局空间
        self.export_button.clicked.connect(self._on_export_clicked)
        second_row_layout.addWidget(self.export_button)

        # 设置按钮
        self.settings_button = QPushButton("设置")
        self.settings_button.setMinimumHeight(28)  # 减少最小高度以适配12%布局空间
        self.settings_button.clicked.connect(self._on_settings_clicked)
        second_row_layout.addWidget(self.settings_button)

        # 将第二行按钮布局添加到主布局
        second_row_widget = QWidget()
        second_row_widget.setLayout(second_row_layout)
        layout.addWidget(second_row_widget)

        # 添加弹性空间
        layout.addStretch()

    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QGroupBox#controlGroup {
                font-weight: bold;
                border: 2px solid #e74c3c;
                border-radius: 5px;
                margin-top: 0.2ex;  /* 进一步压缩优化：从1ex减少到0.2ex */
                padding-top: 2px;   /* 进一步压缩优化：从10px减少到2px */
                background-color: white;
            }

            QGroupBox#controlGroup::title {
                subcontrol-origin: margin;
                left: 5px;          /* 进一步压缩优化：从10px减少到5px */
                padding: 0 3px 0 3px;  /* 进一步压缩优化：从8px减少到3px */
                color: #e74c3c;
                font-size: 9pt;     /* 进一步压缩优化：从11pt减少到9pt */
            }

            QPushButton {
                background-color: #3498db;
                border: none;
                color: white;
                padding: 6px 12px;  /* 进一步压缩优化：从8px 16px减少到6px 12px */
                border-radius: 4px;  /* 进一步压缩优化：从6px减少到4px */
                font-weight: bold;
                font-size: 12pt;    /* 保持12pt字体大小不变 */
                min-width: 90px;    /* 进一步压缩优化：从100px减少到90px */
            }

            QPushButton:hover {
                background-color: #2980b9;
            }

            QPushButton:pressed {
                background-color: #21618c;
            }

            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }

            QPushButton#startButton {
                background-color: #27ae60;
                font-size: 12pt;
            }

            QPushButton#startButton:hover {
                background-color: #229954;
            }

            QPushButton#startButton:pressed {
                background-color: #1e8449;
            }

            QPushButton#stopButton {
                background-color: #e74c3c;
                font-size: 12pt;
            }

            QPushButton#stopButton:hover {
                background-color: #c0392b;
            }

            QPushButton#stopButton:pressed {
                background-color: #a93226;
            }

            QPushButton#warningButton {
                background-color: #f39c12;
            }

            QPushButton#warningButton:hover {
                background-color: #e67e22;
            }

            QPushButton#warningButton:pressed {
                background-color: #d35400;
            }

            QFrame {
                color: #bdc3c7;
            }

            QFrame#continuousStatusContainer {
                background-color: #e8f5e8;
                border: 2px solid #27ae60;
                border-radius: 6px;
                margin: 2px;
                min-height: 40px;
                max-height: 60px;
            }

            QLabel#continuousStatusLabel {
                color: #27ae60;
                font-weight: bold;
                font-size: 11pt;
            }

            QLabel#testCountLabel {
                color: #2c3e50;
                font-weight: bold;
                font-size: 10pt;
            }

            QPushButton#stopContinuousButton {
                background-color: #e74c3c;
                font-size: 12pt;
                min-width: 80px;
                padding: 4px 8px;
            }

            QPushButton#stopContinuousButton:hover {
                background-color: #c0392b;
            }

            QPushButton#stopContinuousButton:pressed {
                background-color: #a93226;
            }

            QFrame#testModeStatusContainer {
                background-color: #f0f8ff;
                border: 1px solid #87ceeb;
                border-radius: 4px;
                margin: 1px;
                min-height: 24px;
                max-height: 32px;
            }

            QLabel#testModeStatusLabel {
                color: #1e90ff;
                font-weight: normal;
                font-size: 12pt;
                padding: 2px 4px;
            }
        """)

    def _on_start_stop_clicked(self):
        """开始/停止按钮点击处理"""
        try:
            # 修复在处理点击前先检查和同步状态
            self._sync_testing_state()
            
            # 检查主窗口状态
            main_window = self._get_main_window()
            if main_window:
                
                # 检查测试流程管理器状态
                if hasattr(main_window, 'test_flow_manager') and main_window.test_flow_manager:
                    
                    # 检查测试引擎状态
                    if hasattr(main_window.test_flow_manager, 'test_engine') and main_window.test_flow_manager.test_engine:
                        test_engine = main_window.test_flow_manager.test_engine
                        if hasattr(test_engine, 'test_flow_controller') and test_engine.test_flow_controller:
                            controller = test_engine.test_flow_controller

            # 处理开始/停止按钮点击
            logger.debug(f"开始/停止按钮点击: is_testing={self.is_testing}")

            # 🔋 检查是否为电池侦测模式下的停止操作
            auto_detect = self.config_manager.get('test.auto_detect', False)
            continuous_test = self.config_manager.get('test.continuous_mode', False)
            main_window = self._get_main_window()
            battery_detection_active = (main_window and
                                      hasattr(main_window, '_battery_detection_active') and
                                      main_window._battery_detection_active)

            if not self.is_testing:
                # 开始测试
                logger.info("用户点击开始测试")
                self._start_test()
            else:
                # 停止测试
                logger.info("🛑 用户点击停止测试")

                # 🔋 如果是电池侦测模式，需要停止电池侦测工作
                if auto_detect and not continuous_test and battery_detection_active:
                    logger.info("🔋 电池侦测模式：用户主动停止，将停止电池侦测工作")
                    # 🔧 设置用户手动停止标记
                    if main_window:
                        main_window._user_manual_stop_battery_detection = True
                        main_window._battery_detection_active = False
                        logger.info("🔋 电池侦测模式已停用，设置用户手动停止标记")

                        # 停止电池移除监控定时器
                        if hasattr(main_window, '_battery_removal_timer') and main_window._battery_removal_timer:
                            main_window._battery_removal_timer.stop()
                            logger.info("🔋 电池移除监控定时器已停止")

                self._stop_test()

        except Exception as e:
            logger.error(f"开始/停止测试失败: {e}")
            QMessageBox.critical(self, "错误", f"操作失败: {e}")

    def _start_test(self):
        """开始测试（增强版）"""
        try:
            # 修复确保状态完全重置，避免状态冲突
            logger.info(f"🚀 开始测试，当前状态: is_testing={self.is_testing}")

            # 检查授权状态
            if not self._check_authorization():
                return

            # 检查配置
            if not self._validate_test_config():
                return

            # 检查是否为电池侦测模式
            auto_detect = self.config_manager.get('test.auto_detect', False)
            if auto_detect:
                # 🔧 检查是否为用户手动停止后的重新启动
                main_window = self._get_main_window()
                user_manual_stop = (main_window and
                                  hasattr(main_window, '_user_manual_stop_battery_detection') and
                                  main_window._user_manual_stop_battery_detection)

                if user_manual_stop:
                    logger.info("🔋 电池侦测模式：用户手动停止后重新启动，跳过引导对话框")
                    # 清除手动停止标记
                    main_window._user_manual_stop_battery_detection = False
                    # 重新激活电池侦测模式
                    main_window._battery_detection_active = True
                    logger.info("🔋 电池侦测模式已重新激活")
                else:
                    logger.info("🔋 电池侦测模式：显示启动引导对话框")
                    self._show_battery_detection_guide()
                    return

            # 新增自动下发设备参数
            if not self._auto_configure_device_parameters():
                return

            # 新增清理上一次测试的状态数据
            self._prepare_for_new_test()

            # 🚀 阶段3优化：优先使用统一测试控制器
            main_window = self._get_main_window()
            if main_window:
                # 尝试使用统一测试控制器
                if hasattr(main_window, 'unified_test_controller') and main_window.unified_test_controller:
                    logger.info("🚀 使用统一测试控制器启动测试")

                    # 使用统一测试控制器启动
                    if main_window.unified_test_controller.start_test():
                        logger.info("✅ 统一测试控制器启动成功")
                        # 更新主窗口状态
                        main_window.is_testing = True
                    else:
                        logger.error("❌ 统一测试控制器启动失败，回退到原有流程")
                        # 回退到原有流程
                        self._start_test_legacy(main_window)
                        return
                else:
                    logger.info("🔄 统一测试控制器不可用，使用原有流程")
                    # 使用原有流程
                    self._start_test_legacy(main_window)

            # 更新状态
            self.is_testing = True
            self.start_stop_button.setText("停止测试")
            self.start_stop_button.setObjectName("stopButton")
            self.start_stop_button.setStyleSheet("")  # 重新应用样式

            # 禁用其他按钮
            self.clear_button.setEnabled(False)
            self.settings_button.setEnabled(False)

            # 更新测试模式状态显示
            self._update_test_mode_status()

            # 检查连续测试模式并显示状态指示器
            continuous_mode = self.config_manager.get('test.continuous_mode', False)
            if continuous_mode:
                self.set_continuous_test_status(True, 0)
                logger.info("连续测试模式已启用，显示状态指示器")

            # 🚫 电池检测功能已屏蔽，跳过激活逻辑
            auto_detect = False  # 强制设置为False，屏蔽功能
            logger.debug("电池检测功能已屏蔽，跳过激活逻辑")

            # 🚀 优化：异步清除之前的测试结果，避免启动卡顿
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(50, self._clear_previous_test_results)

            # 发送开始测试信号
            self.start_test.emit()

            logger.info("✅ 测试已开始，状态同步完成")

        except Exception as e:
            logger.error(f"开始测试失败: {e}")
            # 修复出错时重置状态
            self.is_testing = False
            self.start_stop_button.setText("开始测试")
            self.start_stop_button.setObjectName("startButton")
            self.start_stop_button.setStyleSheet("")
            raise

    def _clear_previous_test_results(self):
        """清除之前的测试结果显示（仅在测试开始时调用）"""
        try:
            logger.info("🧹 测试开始：清除之前的测试结果显示")

            # 获取主窗口
            main_window = self._get_main_window()
            if not main_window:
                logger.warning("无法获取主窗口，跳过清除之前的测试结果")
                return

            # 获取通道容器组件
            if hasattr(main_window, 'ui_component_manager'):
                channels_container = main_window.ui_component_manager.get_component('channels_container')
                if channels_container and hasattr(channels_container, 'channels'):
                    # 只清除测试结果显示，不重置整个通道状态
                    for channel_widget in channels_container.channels:
                        if hasattr(channel_widget, 'clear_previous_results'):
                            channel_widget.clear_previous_results()

                    logger.info("✅ 已清除所有通道的之前测试结果显示")
                else:
                    logger.warning("无法获取通道容器组件")
            else:
                logger.warning("无法获取UI组件管理器")

        except Exception as e:
            logger.error(f"清除之前测试结果失败: {e}")

    def _get_main_window(self):
        """获取主窗口引用"""
        try:
            # 修复增强主窗口查找逻辑
            main_window = self.parent()
            search_depth = 0
            max_depth = 10  # 防止无限循环

            while main_window and search_depth < max_depth:

                # 检查是否是主窗口（通过类名或属性判断）
                if (hasattr(main_window, '_battery_detection_active') or
                    type(main_window).__name__ == 'MainWindow' or
                    hasattr(main_window, 'battery_detection_manager')):
                    logger.debug(f"✅ 找到主窗口: {type(main_window).__name__}")
                    return main_window

                main_window = main_window.parent()
                search_depth += 1

            logger.warning(f"⚠️ 未找到主窗口，搜索深度: {search_depth}")
            return None

        except Exception as e:
            logger.error(f"获取主窗口失败: {e}")
            return None

    def _check_authorization(self) -> bool:
        """检查授权状态"""
        try:
            # 获取主窗口的授权管理器
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'authorization_manager'):
                main_window = main_window.parent()

            if main_window and hasattr(main_window, 'authorization_manager'):
                auth_manager = main_window.authorization_manager
                license_status = auth_manager.get_license_status()

                # 检查授权是否有效
                if not license_status.get('is_valid', False):
                    # 试用期已到期且未授权
                    if license_status.get('is_expired', True):
                        QMessageBox.warning(
                            self,
                            "软件试用期已到期",
                            "软件试用期已到期，测试功能已被禁用。\n\n请点击右上角的\"解锁\"按钮输入解锁码以继续使用测试功能。\n\n如需购买授权，请联系软件供应商。"
                        )

                        # 触发解锁对话框
                        auth_manager.handle_unlock_requested()
                        return False
                    else:
                        QMessageBox.warning(
                            self,
                            "软件授权无效",
                            "软件授权验证失败，无法使用测试功能。\n\n请联系软件供应商获取有效授权。"
                        )
                        return False

                # 检查测试功能是否启用
                enabled_features = license_status.get('enabled_features', [])
                if 'basic_test' not in enabled_features:
                    QMessageBox.warning(
                        self,
                        "测试功能未授权",
                        "当前授权不包含测试功能。\n\n请联系软件供应商升级授权。"
                    )
                    return False

                return True
            else:
                # 未找到授权管理器，允许测试（向后兼容）
                return True

        except Exception as e:
            logger.error(f"检查授权状态失败: {e}")
            QMessageBox.critical(
                self,
                "授权检查失败",
                f"无法验证软件授权状态：{str(e)}\n\n请重启软件后重试。"
            )
            return False

    def set_test_buttons_enabled(self, enabled: bool):
        """设置测试按钮启用状态（用于授权控制）"""
        try:
            self.start_stop_button.setEnabled(enabled)
            if not enabled:
                self.start_stop_button.setText("测试已禁用")
                self.start_stop_button.setToolTip("软件试用期已到期，请解锁后使用测试功能")
            else:
                self.start_stop_button.setText("开始测试" if not self.is_testing else "停止测试")
                self.start_stop_button.setToolTip("")

        except Exception as e:
            logger.error(f"设置测试按钮状态失败: {e}")

    def _stop_test(self):
        """停止测试（增强版）"""
        try:
            logger.info("🛑 [增强版] UI测试控制组件开始停止...")

            # 🚀 阶段3优化：优先使用统一测试控制器
            if self._stop_test_unified():
                logger.info("✅ 使用统一测试控制器停止成功")
            else:
                logger.info("🔄 回退到原有停止流程")

            # 1. 发送停止测试信号（优先级最高）
            self.stop_test.emit()

            # 2. 设置停止中状态，避免立即重置按钮
            self.start_stop_button.setText("停止中...")
            self.start_stop_button.setEnabled(False)  # 暂时禁用按钮，防止重复点击

            # 3. 延迟重置按钮状态，等待测试真正停止
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1500, self._delayed_button_reset)  # 1.5秒后重置

            # 4. 强制刷新UI显示
            self.update()
            self.repaint()

            # 5. 处理连续测试状态
            continuous_mode = self.config_manager.get('test.continuous_mode', False)

            if continuous_mode:
                logger.info("连续测试模式仍启用，保持状态指示器显示")
            else:
                self.set_continuous_test_status(False)
                logger.info("连续测试模式已关闭，隐藏状态指示器")

            # 🚫 电池检测功能已屏蔽，跳过处理逻辑
            logger.debug("电池检测功能已屏蔽，跳过停止处理")

            logger.info("✅ [增强版] UI测试控制组件停止完成")

        except Exception as e:
            logger.error(f"❌ [增强版] UI停止测试失败: {e}")
            # 如果停止失败，立即重置按钮状态
            self._delayed_button_reset()
            raise

    def _delayed_button_reset(self):
        """延迟重置按钮状态"""
        try:
            # 🔋 检查是否为电池侦测模式
            auto_detect = self.config_manager.get('test.auto_detect', False)
            continuous_test = self.config_manager.get('test.continuous_mode', False)

            # 检查电池侦测模式是否激活
            main_window = self._get_main_window()
            battery_detection_active = (main_window and
                                      hasattr(main_window, '_battery_detection_active') and
                                      main_window._battery_detection_active)

            # 🔧 修复：检查是否为用户手动停止（通过标记判断）
            user_manual_stop = (main_window and
                              hasattr(main_window, '_user_manual_stop_battery_detection') and
                              main_window._user_manual_stop_battery_detection)

            if auto_detect and not continuous_test and battery_detection_active and not user_manual_stop:
                # 🔋 电池侦测模式下，且非用户手动停止，保持"停止测试"状态，不重置按钮
                logger.info("🔋 电池侦测模式：保持'停止测试'状态，跳过按钮重置")

                # 只重置内部状态，但保持按钮为"停止测试"
                self.is_testing = False

                # 确保按钮显示为"停止测试"
                self.start_stop_button.setText("停止测试")
                self.start_stop_button.setObjectName("stopButton")
                self.start_stop_button.setStyleSheet("")  # 重新应用样式
                self.start_stop_button.setEnabled(True)  # 重新启用按钮

                # 保持其他按钮禁用状态，表示系统仍在工作
                self.clear_button.setEnabled(False)
                self.settings_button.setEnabled(False)

                logger.info("✅ 电池侦测模式：按钮状态已保持为'停止测试'")
                return

            # 🔧 如果是用户手动停止，清除标记
            if user_manual_stop and main_window:
                main_window._user_manual_stop_battery_detection = False
                logger.info("🔋 用户手动停止电池侦测模式：清除停止标记，重置按钮状态")

            # 重置内部状态
            self.is_testing = False

            # 重置按钮状态
            self.start_stop_button.setText("开始测试")
            self.start_stop_button.setObjectName("startButton")
            self.start_stop_button.setStyleSheet("")  # 重新应用样式
            self.start_stop_button.setEnabled(True)  # 重新启用按钮

            # 启用其他按钮
            self.clear_button.setEnabled(True)
            self.settings_button.setEnabled(True)

            logger.info("✅ 按钮状态已延迟重置")

        except Exception as e:
            logger.error(f"延迟重置按钮状态失败: {e}")

    def _on_stop_continuous_clicked(self):
        """停止连续测试按钮点击处理"""
        try:
            # 修复停止连续测试逻辑：关闭连续测试模式而不是直接隐藏状态指示器
            # 1. 关闭连续测试模式配置
            self.config_manager.set('test.continuous_mode', False)

            # 2. 隐藏连续测试状态指示器
            self.set_continuous_test_status(False)

            # 3. 更新测试模式状态显示
            self._update_test_mode_status()

            # 4. 停止当前测试
            if self.is_testing:
                self._stop_test()

            logger.info("用户手动停止连续测试模式")

        except Exception as e:
            logger.error(f"停止连续测试失败: {e}")

    def _validate_test_config(self) -> bool:
        """
        验证测试配置

        Returns:
            配置是否有效
        """
        try:
            # 检查批次信息
            batch_number = self.config_manager.get('batch_info.batch_number', '')
            if not batch_number or batch_number == "未设置":
                QMessageBox.warning(
                    self, "配置检查",
                    "请先在设置中配置批次号！"
                )
                return False

            # 检查操作员
            operator = self.config_manager.get('batch_info.operator', '')
            if not operator or operator == "未设置":
                QMessageBox.warning(
                    self, "配置检查",
                    "请先在设置中配置操作员信息！"
                )
                return False

            # 检查设备连接（这里暂时跳过，后续集成时实现）
            # device_connected = self.config_manager.get('device.connected', False)
            # if not device_connected:
            # QMessageBox.warning(
            # self, "设备检查",
            # "设备未连接，请检查设备连接状态！"
            # )
            # return False

            return True

        except Exception as e:
            logger.error(f"验证测试配置失败: {e}")
            QMessageBox.critical(self, "错误", f"配置验证失败: {e}")
            return False

    def _show_battery_detection_guide(self):
        """显示电池侦测模式启动引导对话框"""
        try:
            logger.info("🔋 显示电池侦测模式启动引导对话框")

            # 获取主窗口和电池检测管理器
            main_window = self._get_main_window()
            battery_detection_manager = None

            if main_window and hasattr(main_window, 'battery_detection_manager'):
                battery_detection_manager = main_window.battery_detection_manager

            # 创建对话框
            dialog = BatteryDetectionGuideDialog(
                parent=self,
                config_manager=self.config_manager,
                battery_detection_manager=battery_detection_manager
            )

            # 连接信号
            dialog.start_test_requested.connect(self._on_battery_detection_start_test)
            dialog.dialog_cancelled.connect(self._on_battery_detection_cancelled)

            # 显示对话框
            result = dialog.exec_()

            if result == dialog.Accepted:
                logger.info("✅ 电池侦测模式启动引导完成")
            else:
                logger.info("❌ 电池侦测模式启动引导被取消")

        except Exception as e:
            logger.error(f"显示电池侦测模式启动引导对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"启动引导失败: {e}")

    def _on_battery_detection_start_test(self):
        """电池侦测模式对话框确认开始测试"""
        try:
            logger.info("🚀 电池侦测模式：用户确认开始测试")

            # 继续执行正常的测试启动流程（跳过电池侦测检查）
            self._start_test_after_battery_detection()

        except Exception as e:
            logger.error(f"电池侦测模式开始测试失败: {e}")

    def _on_battery_detection_cancelled(self):
        """电池侦测模式对话框被取消"""
        try:
            logger.info("❌ 电池侦测模式启动被用户取消")
            # 不需要特殊处理，保持当前状态

        except Exception as e:
            logger.error(f"处理电池侦测模式取消失败: {e}")

    def _start_test_after_battery_detection(self):
        """电池侦测模式确认后继续启动测试"""
        try:
            logger.info("🚀 电池侦测模式确认后继续启动测试")

            # 🔋 关键修复：标记电池侦测模式已激活，用于测试完成后启动电池移除监控
            main_window = self._get_main_window()
            if main_window:
                main_window._battery_detection_active = True
                logger.info("🔋 电池侦测模式已激活，测试完成后将启动电池移除监控")

            # 新增自动下发设备参数
            if not self._auto_configure_device_parameters():
                return

            # 新增清理上一次测试的状态数据
            self._prepare_for_new_test()

            # 🚀 阶段3优化：优先使用统一测试控制器
            if main_window:
                # 尝试使用统一测试控制器
                if hasattr(main_window, 'unified_test_controller') and main_window.unified_test_controller:
                    logger.info("🚀 使用统一测试控制器启动测试")

                    # 使用统一测试控制器启动
                    if main_window.unified_test_controller.start_test():
                        logger.info("✅ 统一测试控制器启动成功")
                        # 更新主窗口状态
                        main_window.is_testing = True
                    else:
                        logger.error("❌ 统一测试控制器启动失败，回退到原有流程")
                        # 回退到原有流程
                        self._start_test_legacy(main_window)
                        return
                else:
                    logger.info("🔄 统一测试控制器不可用，使用原有流程")
                    # 使用原有流程
                    self._start_test_legacy(main_window)

            # 更新状态
            self.is_testing = True
            self.start_stop_button.setText("停止测试")
            self.start_stop_button.setObjectName("stopButton")
            self.start_stop_button.setStyleSheet("")  # 重新应用样式

            # 禁用其他按钮
            self.clear_button.setEnabled(False)
            self.settings_button.setEnabled(False)

            # 更新测试模式状态显示
            self._update_test_mode_status()

            # 检查连续测试模式并显示状态指示器
            continuous_mode = self.config_manager.get('test.continuous_mode', False)
            if continuous_mode:
                self.set_continuous_test_status(True, 0)
                logger.info("连续测试模式已启用，显示状态指示器")

            # 🚀 优化：异步清除之前的测试结果，避免启动卡顿
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(50, self._clear_previous_test_results)

            # 发送开始测试信号
            self.start_test.emit()

            logger.info("✅ 电池侦测模式测试已开始，状态同步完成")

        except Exception as e:
            logger.error(f"电池侦测模式启动测试失败: {e}")
            # 修复出错时重置状态
            self.is_testing = False
            self.start_stop_button.setText("开始测试")
            self.start_stop_button.setObjectName("startButton")
            self.start_stop_button.setStyleSheet("")
            raise

    def _auto_configure_device_parameters(self) -> bool:
        """
        自动下发参数配置（电阻档位、增益、平均次数）
        
        Returns:
            是否配置成功
        """
        try:
            
            # 修复直接从参数配置读取并下发，不使用设备配置管理器
            # 构建参数配置
            params_config = self._build_params_config()
            
            
            # 这里可以添加实际的参数下发逻辑
            # 目前只是记录日志，实际下发由其他组件处理
            logger.info("✅ 参数配置已准备完成，等待下发")
            
            return True
                
        except Exception as e:
            logger.error(f"自动下发参数配置失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            QMessageBox.critical(self, "配置错误", f"参数配置过程中发生错误：\n{e}")
            return False
    
    def _build_params_config(self) -> dict:
        """
        构建参数配置（电阻档位、增益、平均次数）
        
        Returns:
            参数配置字典
        """
        try:
            # 修复从正确的配置路径读取参数配置
            # 增益配置 - 从test_params节点读取
            gain = self.config_manager.get('test_params.gain', '1')
            if gain == 'auto':
                gain = '1'  # 自动模式默认为1倍增益
            
            # 平均次数配置 - 从test_params节点读取
            average_times = self.config_manager.get('test_params.average_times', 1)
            
            # 修复电阻档位配置 - 直接从test_params.resistance_range读取
            resistance_range = self.config_manager.get('test_params.resistance_range', '5R')
            
            params_config = {
                'gain': gain,
                'average_times': average_times,
                'resistance_range': resistance_range
            }
            
            return params_config
            
        except Exception as e:
            logger.error(f"构建参数配置失败: {e}")
            # 返回默认配置
            return {
                'gain': '1',
                'average_times': 1,
                'resistance_range': '5R'
            }

    def _build_test_config_for_device(self) -> dict:
        """
        构建用于设备配置的测试配置（已废弃，保留用于兼容性）
        
        Returns:
            测试配置字典
        """
        try:
            # 修复从正确的配置路径读取设备参数（根据实际配置文件结构）
            # 增益配置 - 从test_params节点读取
            gain = self.config_manager.get('test_params.gain', '1')
            if gain == 'auto':
                gain = '1'  # 自动模式默认为1倍增益
            
            # 平均次数配置 - 从test_params节点读取
            average_times = self.config_manager.get('test_params.average_times', 1)
            
            # 电阻档位配置 - 从test_params节点读取
            resistance_range = self.config_manager.get('test_params.resistance_range', '5R')
            
            # 频率配置 - 多频点模式，优先从list读取，备选custom_list
            frequencies = self.config_manager.get('frequency.list', [])
            if not frequencies:
                frequencies = self.config_manager.get('frequency.multi_freq.custom_list', [])
            
            # 启用的通道 - 从test节点读取
            enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))
            
            test_config = {
                'gain': gain,
                'average_times': average_times,
                'resistance_range': resistance_range,
                'frequencies': frequencies,
                'enabled_channels': enabled_channels
            }
            
            return test_config
            
        except Exception as e:
            logger.error(f"构建测试配置失败: {e}")
            # 返回默认配置
            return {
                'gain': '1',
                'average_times': 1,
                'resistance_range': '5R',
                'frequencies': [],
                'enabled_channels': list(range(1, 9))
            }
    
    def _get_resistance_range_from_battery_range(self) -> str:
        """
        根据电池档位配置获取设备电阻档位
        
        Returns:
            设备电阻档位字符串
        """
        try:
            battery_range = self.config_manager.get('test_params.battery_range', '10mΩ以下')
            
            # 定义映射关系
            battery_to_device_map = {
                '1mΩ以下': '1R',   # 1mΩ以内 → 1R档位
                '10mΩ以下': '5R',  # 10mΩ以内 → 5R档位
                '100mΩ以下': '10R' # 100mΩ以内 → 10R档位
            }
            
            resistance_range = battery_to_device_map.get(battery_range, '5R')
            
            return resistance_range
            
        except Exception as e:
            logger.error(f"获取电阻档位失败: {e}")
            return '5R'  # 默认5R档位
    
    def _get_enabled_channels(self) -> list:
        """
        获取启用的通道列表
        
        Returns:
            启用的通道列表
        """
        try:
            # 从配置中获取启用的通道
            enabled_channels = []
            for i in range(1, 9):  # 通道1-8
                if self.config_manager.get(f'channels.channel_{i}.enabled', True):
                    enabled_channels.append(i)
            
            if not enabled_channels:
                # 如果没有启用的通道，默认启用所有通道
                enabled_channels = list(range(1, 9))
                logger.warning("⚠️ 没有启用的通道，默认启用所有通道")
            
            return enabled_channels
            
        except Exception as e:
            logger.error(f"获取启用通道失败: {e}")
            return list(range(1, 9))  # 默认所有通道

    def _on_clear_clicked(self):
        """统计清理按钮点击处理"""
        try:
            # 确认对话框
            reply = QMessageBox.question(
                self, '确认清理',
                '确定要清理所有统计数据吗？\n此操作不可撤销。',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 发送清理统计信号
                self.clear_statistics.emit()
                logger.info("用户确认清理统计数据")

        except Exception as e:
            logger.error(f"清理统计数据失败: {e}")
            QMessageBox.critical(self, "错误", f"清理失败: {e}")

    def _on_export_clicked(self):
        """导出数据按钮点击处理"""
        try:
            # 发送导出数据信号
            self.export_data.emit()
            logger.info("用户请求导出数据")

        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            QMessageBox.critical(self, "错误", f"导出失败: {e}")

    def _on_settings_clicked(self):
        """设置按钮点击处理"""
        try:
            # 发送打开设置信号
            self.open_settings.emit()
            logger.info("用户请求打开设置")

        except Exception as e:
            logger.error(f"打开设置失败: {e}")
            QMessageBox.critical(self, "错误", f"打开设置失败: {e}")



    def set_testing_state(self, is_testing: bool):
        """
        设置测试状态（外部调用）

        Args:
            is_testing: 是否正在测试
        """
        # 修复在特殊测试模式下的状态处理
        continuous_mode = self.config_manager.get('test.continuous_mode', False)
        sampling_test = self.config_manager.get('test.sampling_test', False)

        if is_testing and not self.is_testing:
            self._start_test()
        elif not is_testing and self.is_testing:
            if continuous_mode:
                # 连续测试模式下，只更新UI状态，不发送停止信号
                # 只更新按钮显示，不调用_stop_test()
                self.is_testing = False
                self.start_stop_button.setText("停止测试")
                self.start_stop_button.setObjectName("stopButton")
                self.start_stop_button.setStyleSheet("")  # 重新应用样式
            elif sampling_test:
                # 取样测试模式下，重置按钮为"开始测试"，等待用户手动开始下一次测试
                self.is_testing = False
                self.start_stop_button.setText("开始测试")
                self.start_stop_button.setObjectName("startButton")
                self.start_stop_button.setStyleSheet("")  # 重新应用样式

                # 启用其他按钮
                self.clear_button.setEnabled(True)
                self.settings_button.setEnabled(True)

                logger.info("✅ 取样测试：按钮状态已重置为'开始测试'，等待下一次测试")
            else:
                # 非特殊测试模式，正常停止
                self._stop_test()

    def reset_button_state_for_continuous_test(self):
        """重置连续测试完成后的按钮状态（外部调用）"""
        try:

            # 重置按钮状态为开始测试
            self.is_testing = False
            self.start_stop_button.setText("开始测试")
            self.start_stop_button.setObjectName("startButton")
            self.start_stop_button.setStyleSheet("")  # 重新应用样式

            # 启用其他按钮
            self.clear_button.setEnabled(True)
            self.settings_button.setEnabled(True)

            # 隐藏连续测试状态指示器
            self.set_continuous_test_status(False)

            logger.info("✅ 连续测试完成：按钮状态已重置")

        except Exception as e:
            logger.error(f"重置连续测试按钮状态失败: {e}")

    def get_testing_state(self) -> bool:
        """
        获取当前测试状态

        Returns:
            是否正在测试
        """
        return self.is_testing

    def on_test_completed(self):
        """测试完成处理（增强版）"""
        try:
            logger.info("🎯 测试控制组件：收到测试完成通知")

            # 获取当前测试模式（与main_window保持一致）
            continuous_test = self.config_manager.get('test.continuous_mode', False)
            auto_detect = self.config_manager.get('test.auto_detect', False)  # 修复：默认值改为False，与屏蔽状态一致
            sampling_test = self.config_manager.get('test.sampling_test', False)

            # 判断是否为手动模式
            is_manual_mode = not continuous_test and not auto_detect and not sampling_test

            logger.debug(f" 测试模式检查: 手动模式={is_manual_mode}, 连续测试={continuous_test}, 自动侦测={auto_detect}, 取样测试={sampling_test}")

            if is_manual_mode:
                logger.info("✅ 测试控制组件：手动模式，开始重置按钮状态")
                self._reset_to_start_state("手动模式测试完成")
            elif sampling_test:
                logger.info("✅ 测试控制组件：取样测试模式，重置按钮状态")
                self._reset_to_start_state("取样测试完成")
            elif auto_detect and not continuous_test:
                logger.info("✅ 测试控制组件：自动侦测模式，保持测试状态等待下一轮")
                # 🔋 电池侦测模式下，测试完成后保持"停止测试"状态，等待用户取下电池后重新插入
                logger.info("🔋 电池侦测模式：测试完成，保持测试状态，等待电池移除后重新插入")

                # 🔋 确保按钮状态为"停止测试"
                self.is_testing = False  # 内部状态设为false，但按钮保持停止状态
                self.start_stop_button.setText("停止测试")
                self.start_stop_button.setObjectName("stopButton")
                self.start_stop_button.setStyleSheet("")  # 重新应用样式
                self.start_stop_button.setEnabled(True)  # 确保按钮可点击

                # 保持其他按钮禁用状态，表示系统仍在工作
                self.clear_button.setEnabled(False)
                self.settings_button.setEnabled(False)

                logger.info("🔋 电池侦测模式：按钮状态已设置为'停止测试'，等待用户主动停止")
            else:
                logger.info(f"ℹ️ 测试控制组件：连续测试模式，保持测试状态（连续测试: {continuous_test}）")
                # 连续测试模式下，保持"停止测试"状态，等待下一轮测试

        except Exception as e:
            logger.error(f"测试完成处理失败: {e}")

    def _reset_to_start_state(self, reason: str = "测试完成"):
        """重置到开始测试状态"""
        try:
            logger.info(f"🔄 重置按钮状态: {reason}")

            # 修复确保内部状态完全重置
            self.is_testing = False

            # 更新按钮显示
            self.start_stop_button.setText("开始测试")
            self.start_stop_button.setObjectName("startButton")
            self.start_stop_button.setStyleSheet("")  # 重新应用样式

            # 启用其他按钮
            self.clear_button.setEnabled(True)
            self.settings_button.setEnabled(True)

            # 修复确保测试流程管理器状态同步
            main_window = self._get_main_window()
            if main_window:
                # 🔧 [关键修复] 在设置is_testing=False之前记录测试停止时间，确保宽限期逻辑正常工作
                if main_window.is_testing and reason == "手动模式测试完成":
                    import time
                    main_window._test_stop_time = time.time()
                    logger.info(f"🔧 [测试控制组件] 记录测试停止时间: {main_window._test_stop_time}，允许5秒宽限期完成数据保存")

                # 同步主窗口的测试状态
                main_window.is_testing = False
                logger.debug("✅ 主窗口测试状态已同步重置")

                # 关键修复确保所有测试流程管理器状态正确重置
                if hasattr(main_window, 'test_flow_manager') and main_window.test_flow_manager:
                    # 重置测试流程管理器适配器状态
                    if main_window.test_flow_manager.is_testing:
                        logger.debug("⚠️ 测试流程管理器状态不一致，强制重置")
                        main_window.test_flow_manager.is_testing = False
                        logger.debug("✅ 测试流程管理器状态已强制重置")

                    # 新增重置测试引擎中的测试流程控制器状态
                    if hasattr(main_window.test_flow_manager, 'test_engine') and main_window.test_flow_manager.test_engine:
                        test_engine = main_window.test_flow_manager.test_engine
                        if hasattr(test_engine, 'test_flow_controller') and test_engine.test_flow_controller:
                            test_flow_controller = test_engine.test_flow_controller

                            # 重置测试流程控制器的各种状态
                            if hasattr(test_flow_controller, 'is_testing'):
                                test_flow_controller.is_testing = False
                                logger.debug("✅ 测试引擎中的测试流程控制器is_testing状态已重置")

                            if hasattr(test_flow_controller, 'current_state'):
                                test_flow_controller.current_state = 'idle'
                                logger.debug("✅ 测试引擎中的测试流程控制器current_state已重置为idle")

                            if hasattr(test_flow_controller, '_test_state'):
                                test_flow_controller._test_state = 'idle'
                                logger.debug("✅ 测试引擎中的测试流程控制器_test_state已重置为idle")

                            logger.info("✅ 测试引擎中的测试流程控制器状态已完全重置")

                    # 新增重置测试流程管理器适配器中的测试流程控制器
                    if hasattr(main_window.test_flow_manager, 'test_flow_controller') and main_window.test_flow_manager.test_flow_controller:
                        adapter_controller = main_window.test_flow_manager.test_flow_controller
                        if hasattr(adapter_controller, 'is_testing'):
                            adapter_controller.is_testing = False
                            logger.debug("✅ 适配器中的测试流程控制器状态已重置")
                        if hasattr(adapter_controller, 'current_state'):
                            adapter_controller.current_state = 'idle'
                            logger.debug("✅ 适配器中的测试流程控制器状态已重置为idle")

            # 强制刷新UI显示
            self.update()
            self.repaint()

            logger.info(f"✅ 按钮状态已重置为'开始测试': {reason}")

        except Exception as e:
            logger.error(f"重置按钮状态失败: {e}")

    def _sync_testing_state(self):
        """同步测试状态，确保各组件状态一致"""
        try:
            main_window = self._get_main_window()
            if not main_window:
                return

            # 修复获取所有相关组件的测试状态
            main_window_testing = getattr(main_window, 'is_testing', False)
            flow_manager_testing = False
            test_flow_controller_testing = False

            # 检查测试流程管理器状态
            if hasattr(main_window, 'test_flow_manager') and main_window.test_flow_manager:
                flow_manager_testing = getattr(main_window.test_flow_manager, 'is_testing', False)

                # 新增检查测试引擎中的测试流程控制器状态
                if hasattr(main_window.test_flow_manager, 'test_engine') and main_window.test_flow_manager.test_engine:
                    test_engine = main_window.test_flow_manager.test_engine
                    if hasattr(test_engine, 'test_flow_controller') and test_engine.test_flow_controller:
                        test_flow_controller = test_engine.test_flow_controller
                        if hasattr(test_flow_controller, 'is_testing'):
                            test_flow_controller_testing = test_flow_controller.is_testing
                        elif hasattr(test_flow_controller, 'current_state'):
                            # 如果没有is_testing属性，根据current_state判断
                            test_flow_controller_testing = (test_flow_controller.current_state != 'idle')

            # 检查状态是否一致
            states_consistent = (self.is_testing == main_window_testing == flow_manager_testing == test_flow_controller_testing)

            if not states_consistent:
                logger.warning(f"⚠️ 检测到状态不一致: UI控件={self.is_testing}, 主窗口={main_window_testing}, 流程管理器={flow_manager_testing}, 测试流程控制器={test_flow_controller_testing}")

                # 修复以按钮文本为准进行状态同步
                button_text = self.start_stop_button.text()
                should_be_testing = (button_text == "停止测试")

                logger.info(f"🔄 以按钮状态为准同步: 按钮文本='{button_text}', 应该测试中={should_be_testing}")

                # 修复同步所有组件状态
                self.is_testing = should_be_testing
                if hasattr(main_window, 'is_testing'):
                    main_window.is_testing = should_be_testing

                # 同步测试流程管理器状态
                if hasattr(main_window, 'test_flow_manager') and main_window.test_flow_manager:
                    if hasattr(main_window.test_flow_manager, 'is_testing'):
                        main_window.test_flow_manager.is_testing = should_be_testing

                    # 新增同步测试引擎中的测试流程控制器状态
                    if hasattr(main_window.test_flow_manager, 'test_engine') and main_window.test_flow_manager.test_engine:
                        test_engine = main_window.test_flow_manager.test_engine
                        if hasattr(test_engine, 'test_flow_controller') and test_engine.test_flow_controller:
                            test_flow_controller = test_engine.test_flow_controller

                            if hasattr(test_flow_controller, 'is_testing'):
                                test_flow_controller.is_testing = should_be_testing
                                logger.debug(f"✅ 测试引擎中的测试流程控制器is_testing已同步为: {should_be_testing}")

                            if hasattr(test_flow_controller, 'current_state'):
                                new_state = 'testing' if should_be_testing else 'idle'
                                test_flow_controller.current_state = new_state
                                logger.debug(f"✅ 测试引擎中的测试流程控制器current_state已同步为: {new_state}")

                logger.info("✅ 状态同步完成")
            else:
                logger.debug(f"✅ 状态一致: is_testing={self.is_testing}")

        except Exception as e:
            logger.error(f"同步测试状态失败: {e}")

    def _prepare_for_new_test(self):
        """准备新测试：清理上一次测试的状态数据和UI显示"""
        try:
            logger.info("🔄 准备新测试：开始清理上一次测试状态")

            # 获取主窗口引用
            main_window = self._get_main_window()
            if not main_window:
                logger.warning("无法获取主窗口引用，跳过状态清理")
                return

            # 1. 重置主窗口的测试完成标志
            if hasattr(main_window, '_all_channels_ready_processed'):
                main_window._all_channels_ready_processed = False
                logger.debug("已重置主窗口测试完成标志")

            # 2. 清理通道测试完成标志
            if hasattr(main_window, '_test_completion_flags'):
                main_window._test_completion_flags.clear()
                logger.debug("已清理通道测试完成标志")

            # 3. 重置通道UI显示状态
            self._reset_channels_ui_state(main_window)

            # 4. 重置测试流程管理器状态
            if hasattr(main_window, 'test_flow_manager') and main_window.test_flow_manager:
                if hasattr(main_window.test_flow_manager, 'reset_test_state'):
                    main_window.test_flow_manager.reset_test_state()
                    logger.debug("已重置测试流程管理器状态")

            # 5. 🚀 优化：跳过电池检测状态重置，避免启动卡顿
            # 注释：这个方法应该在测试完成后调用，而不是在测试开始前调用
            # 移除此调用可以显著提升测试启动速度
            logger.debug("✅ 跳过电池检测状态重置，提升启动速度")

            logger.info("✅ 新测试准备完成：状态清理成功")

        except Exception as e:
            logger.error(f"准备新测试失败: {e}")

    def _reset_channels_ui_state(self, main_window):
        """重置所有通道的UI显示状态"""
        try:
            # 获取通道容器组件
            if hasattr(main_window, 'ui_component_manager'):
                channels_container = main_window.ui_component_manager.get_component('channels_container')
                if channels_container and hasattr(channels_container, 'channels'):
                    # 修复只重置进度，不重置测试结果显示
                    for channel_widget in channels_container.channels:
                        if hasattr(channel_widget, 'reset_progress'):
                            channel_widget.reset_progress()
                        # 注释掉完整重置，避免隐藏测试结果
                        # elif hasattr(channel_widget, 'reset_test_state'):
                        # channel_widget.reset_test_state()

                    logger.debug("已重置所有通道进度状态")
                else:
                    logger.debug("未找到通道容器组件")
            else:
                logger.debug("未找到UI组件管理器")

        except Exception as e:
            logger.error(f"重置通道UI状态失败: {e}")

    def set_continuous_test_status(self, is_continuous: bool, test_count: int = 0, max_count: int = 0, interval: float = 0):
        """
        设置连续测试状态（增强版）

        Args:
            is_continuous: 是否为连续测试模式
            test_count: 已完成的测试次数
            max_count: 最大测试次数（0表示无限制）
            interval: 测试间隔时间（秒）
        """
        try:

            if is_continuous:
                # 修复确保连续测试状态指示器存在
                if not hasattr(self, 'continuous_status_container'):
                    logger.error("❌ continuous_status_container 不存在，无法显示连续测试状态")
                    return

                if not hasattr(self, 'test_count_label'):
                    logger.error("❌ test_count_label 不存在，无法更新计数显示")
                    return

                # 显示连续测试状态指示器
                self.continuous_status_container.setVisible(True)
                self.continuous_status_container.show()  # 强制显示
                logger.info(f"✅ 连续测试状态指示器已显示")

                # 更新连续测试状态标签
                self.continuous_status_label.setText("🔄 连续测试模式")

                # 修复更新测试计数显示，始终显示当前次数
                if max_count > 0:
                    count_text = f"当前 {test_count}/{max_count} 次"
                else:
                    count_text = f"当前 {test_count} 次"

                self.test_count_label.setText(count_text)

                # 修复强制刷新UI显示
                self.test_count_label.update()
                self.continuous_status_container.update()

                logger.info(f"✅ 连续测试计数已更新: {count_text}")

                # 更新间隔时间显示（如果有间隔信息）
                if interval > 0:
                    if hasattr(self, 'interval_label'):
                        self.interval_label.setText(f"间隔: {interval:.1f}秒")

            else:
                # 隐藏连续测试状态指示器
                if hasattr(self, 'continuous_status_container'):
                    self.continuous_status_container.setVisible(False)
                else:
                    logger.warning("⚠️ continuous_status_container 不存在，无法隐藏")

        except Exception as e:
            logger.error(f"设置连续测试状态失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _update_test_mode_status(self):
        """更新测试模式状态显示"""
        try:
            # 修复检查UI组件是否已初始化
            if not hasattr(self, 'start_stop_button') or not hasattr(self, 'test_mode_status_label'):
                logger.debug("UI组件未完全初始化，跳过测试模式状态更新")
                return

            # 获取配置（与main_window保持一致）
            continuous_test = self.config_manager.get('test.continuous_mode', False)
            auto_detect = self.config_manager.get('test.auto_detect', False)
            sampling_test = self.config_manager.get('test.sampling_test', False)

            # 调试日志：显示当前配置状态
            logger.debug(f"🔧 测试模式配置状态: continuous={continuous_test}, auto_detect={auto_detect}, sampling={sampling_test}")

            # 确定当前测试模式（简洁版显示）
            if sampling_test and not continuous_test and not auto_detect:
                # 取样测试模式
                sampling_count = self.config_manager.get('test.sampling_count', 30)

                # 获取取样进度（如果有测试流程控制器）
                main_window = self._get_main_window()
                if main_window and hasattr(main_window, 'test_flow_controller'):
                    try:
                        _, valid_count, target_count = main_window.test_flow_controller.get_sampling_progress()
                        # 确保显示正确的计数（重置后应该显示0/目标数）
                        mode_text = f"取样测试 {valid_count}/{target_count}"
                    except Exception as e:
                        logger.debug(f"获取取样进度失败: {e}")
                        mode_text = f"取样测试 (目标:{sampling_count}次)"
                else:
                    mode_text = f"取样测试 (目标:{sampling_count}次)"

            elif continuous_test and not auto_detect and not sampling_test:
                # 连续测试模式（简洁显示）
                continuous_delay = self.config_manager.get('test.continuous_mode_delay', 2.0)
                count_limit_enabled = self.config_manager.get('test.count_limit_enabled', False)
                max_count = self.config_manager.get('test.max_count', 100)

                if count_limit_enabled:
                    mode_text = f"连续测试 ({continuous_delay:.1f}s, {max_count}次)"
                else:
                    mode_text = f"连续测试 ({continuous_delay:.1f}s)"

            elif auto_detect and not continuous_test and not sampling_test:
                # 自动侦测模式
                mode_text = "自动侦测模式"

            elif not continuous_test and not auto_detect and not sampling_test:
                # 手动模式（简洁显示）
                mode_text = "手动模式"

                # 修复确保在手动模式下按钮状态正确
                if not self.is_testing:
                    self.start_stop_button.setText("开始测试")
                    self.start_stop_button.setObjectName("startButton")
                    self.start_stop_button.setStyleSheet("")  # 重新应用样式
                    logger.info("✅ 手动模式：按钮状态已同步为'开始测试'")

            else:
                # 配置冲突（理论上不应该发生）
                mode_text = "配置冲突"
                logger.warning("检测到测试模式配置冲突")

            # 更新显示
            self.test_mode_status_label.setText(mode_text)

            # 更新频点数量显示
            if hasattr(self, 'frequency_count_label'):
                frequencies = self.config_manager.get('frequency.list', [])
                freq_count = len(frequencies) if frequencies else 0
                self.frequency_count_label.setText(f"频点: {freq_count}")
            logger.debug(f"测试模式状态更新: {mode_text}")

        except Exception as e:
            logger.error(f"更新测试模式状态失败: {e}")
            if hasattr(self, 'test_mode_status_label'):
                self.test_mode_status_label.setText("状态获取失败")

    def update_continuous_test_info(self, count: int, max_count: int = 0, status: str = ""):
        """
        更新连续测试信息显示

        Args:
            count: 当前测试次数
            max_count: 最大测试次数
            status: 当前状态描述
        """
        try:
            # 更新计数显示
            if max_count > 0:
                self.test_count_label.setText(f"已完成: {count}/{max_count} 次")
            else:
                self.test_count_label.setText(f"已完成: {count} 次")

            # 更新状态显示（如果有状态标签）
            if hasattr(self, 'status_label') and status:
                self.status_label.setText(status)

            logger.debug(f"连续测试信息更新: {count}次, 状态: {status}")

        except Exception as e:
            logger.error(f"更新连续测试信息失败: {e}")

    def update_test_count(self, count: int):
        """
        更新测试计数显示

        Args:
            count: 测试次数
        """
        try:
            self.test_count_label.setText(f"已完成: {count} 次")

        except Exception as e:
            logger.error(f"更新测试计数失败: {e}")

    def update_continuous_test_count(self, current_count: int, max_count: int = 0):
        """
        更新连续测试计数显示（修复版）

        Args:
            current_count: 当前测试次数（正在进行的轮次）
            max_count: 最大测试次数（0表示无限制）
        """
        try:
            logger.debug(f" update_continuous_test_count 被调用: current_count={current_count}, max_count={max_count}")

            # 修复放宽连续测试模式检查，允许强制更新
            continuous_test = self.config_manager.get('test.continuous_mode', False)
            if not continuous_test:
                logger.warning(f"⚠️ 不是连续测试模式，但仍然尝试更新计数显示")
                # 不再直接返回，而是继续执行更新

            # 修复检查UI组件是否存在
            if not hasattr(self, 'test_count_label') or self.test_count_label is None:
                logger.error(f"❌ test_count_label 不存在，无法更新计数")
                return

            if not hasattr(self, 'continuous_status_container') or self.continuous_status_container is None:
                logger.error(f"❌ continuous_status_container 不存在，无法显示状态")
                return

            # 修复强制确保连续测试状态指示器可见
            if not self.continuous_status_container.isVisible():
                logger.debug(f" 连续测试状态指示器不可见，强制设置为可见")
                self.continuous_status_container.setVisible(True)
                self.continuous_status_container.show()  # 强制显示

            # 修复生成正确的计数显示文本，始终显示当前次数
            if max_count > 0:
                count_text = f"当前 {current_count}/{max_count} 次"
            else:
                count_text = f"当前 {current_count} 次"

            # 修复更新连续测试状态标签
            if hasattr(self, 'continuous_status_label'):
                if current_count > 0:
                    self.continuous_status_label.setText(f"🔄 连续测试 - 第{current_count}轮")
                else:
                    self.continuous_status_label.setText("🔄 连续测试模式")

            # 更新计数标签文本
            old_text = self.test_count_label.text()
            self.test_count_label.setText(count_text)

            # 修复增强UI刷新机制
            self.test_count_label.update()
            self.test_count_label.repaint()  # 强制重绘
            self.continuous_status_container.update()
            self.continuous_status_container.repaint()  # 强制重绘

            # 修复确保样式正确应用
            self.test_count_label.setStyleSheet("")  # 重新应用样式

            # 强制刷新整个组件
            self.update()
            self.repaint()  # 强制重绘整个组件

            logger.info(f"✅ 连续测试计数显示已更新: '{old_text}' -> '{count_text}'")

            # 更新测试模式状态显示
            self._update_test_mode_status()


        except Exception as e:
            logger.error(f"更新连续测试计数失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def reset_continuous_test_count_display(self):
        """重置连续测试计数显示"""
        try:

            # 检查UI组件是否存在
            if hasattr(self, 'test_count_label') and self.test_count_label is not None:
                self.test_count_label.setText("当前: 0 次")
                self.test_count_label.update()

            if hasattr(self, 'continuous_status_label') and self.continuous_status_label is not None:
                self.continuous_status_label.setText("🔄 连续测试模式")

            # 隐藏连续测试状态指示器
            if hasattr(self, 'continuous_status_container') and self.continuous_status_container is not None:
                self.continuous_status_container.setVisible(False)

            logger.info("✅ 连续测试计数显示已重置")

        except Exception as e:
            logger.error(f"重置连续测试计数显示失败: {e}")

    def reset_sampling_test_display(self):
        """重置取样测试显示"""
        try:
            logger.info("🔄 重置取样测试UI显示")

            # 强制更新测试模式状态显示
            self._update_test_mode_status()

            # 强制刷新整个组件
            self.update()

            logger.info("✅ 取样测试显示已重置")

        except Exception as e:
            logger.error(f"重置取样测试显示失败: {e}")

    def show_continuous_test_status(self, show: bool = True):
        """显示或隐藏连续测试状态指示器"""
        try:
            if hasattr(self, 'continuous_status_container') and self.continuous_status_container is not None:
                self.continuous_status_container.setVisible(show)
                if show:
                    self.continuous_status_container.show()
                    logger.info("✅ 连续测试状态指示器已显示")
                else:
                    self.continuous_status_container.hide()
                    logger.info("✅ 连续测试状态指示器已隐藏")
        except Exception as e:
            logger.error(f"显示/隐藏连续测试状态指示器失败: {e}")

    def update_test_mode_display(self):
        """公共方法：强制更新测试模式显示"""
        try:
            logger.info("🔄 强制更新测试模式显示")
            self._update_test_mode_status()
            logger.info("✅ 测试模式显示更新完成")
        except Exception as e:
            logger.error(f"强制更新测试模式显示失败: {e}")

    def load_settings(self):
        """重新加载设置"""
        try:
            # 更新测试模式状态显示
            self._update_test_mode_status()

            # 检查连续测试模式设置
            continuous_mode = self.config_manager.get('test.continuous_mode', False)
            if continuous_mode:
                # 如果启用了连续测试模式，显示状态指示器
                # 获取相关配置信息
                delay = self.config_manager.get('test.continuous_mode_delay', 2.0)
                count_limit_enabled = self.config_manager.get('test.count_limit_enabled', False)
                max_count = self.config_manager.get('test.max_count', 100)

                # 显示连续测试状态指示器
                if count_limit_enabled:
                    self.set_continuous_test_status(True, 0, max_count, delay)
                else:
                    self.set_continuous_test_status(True, 0, 0, delay)
                logger.info("连续测试模式已启用，显示状态指示器")
            else:
                # 连续测试模式已关闭，隐藏状态指示器
                self.set_continuous_test_status(False)
                logger.info("连续测试模式已关闭，隐藏状态指示器")

        except Exception as e:
            logger.error(f"加载设置失败: {e}")

    # ===== 🚀 阶段3优化：原有流程兼容性方法 =====

    def _start_test_legacy(self, main_window):
        """
        原有的测试启动流程（兼容性方法）

        Args:
            main_window: 主窗口实例
        """
        try:
            logger.info("🔄 使用原有测试启动流程")

            # 确保主窗口状态正确
            main_window.is_testing = True
            logger.debug("✅ 主窗口测试状态已设置为True")

            # 修复实际启动原有的测试流程
            if hasattr(main_window, 'test_flow_manager') and main_window.test_flow_manager:
                # 确保测试流程管理器状态正确
                if main_window.test_flow_manager.is_testing:
                    logger.warning("⚠️ 测试流程管理器状态异常，强制重置后重新开始")
                    main_window.test_flow_manager.is_testing = False

                # 启动原有测试流程
                logger.info("🚀 启动原有测试流程管理器")
                success = main_window.test_flow_manager.start_test()
                if success:
                    logger.info("✅ 原有测试流程启动成功")
                else:
                    logger.error("❌ 原有测试流程启动失败")
            else:
                logger.error("❌ 测试流程管理器不可用")

        except Exception as e:
            logger.error(f"❌ 原有测试启动流程失败: {e}")

    def _stop_test_unified(self):
        """
        🚀 阶段3优化：使用统一测试控制器停止测试

        Returns:
            是否停止成功
        """
        try:
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, 'unified_test_controller') and main_window.unified_test_controller:
                logger.info("🛑 使用统一测试控制器停止测试")

                if main_window.unified_test_controller.stop_test():
                    logger.info("✅ 统一测试控制器停止成功")
                    # 更新主窗口状态
                    main_window.is_testing = False
                    return True
                else:
                    logger.error("❌ 统一测试控制器停止失败")
                    return False
            else:
                logger.info("🔄 统一测试控制器不可用，使用原有停止流程")
                return False

        except Exception as e:
            logger.error(f"❌ 统一测试控制器停止失败: {e}")
            return False
