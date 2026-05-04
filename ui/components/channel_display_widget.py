# -*- coding: utf-8 -*-
"""
单通道显示组件
显示单个通道的测试结果，包括通道号、测试用时、电池码、电压、Rs、Rct、进度条和测试结果

Author: Jack
Date: 2025-01-27
"""

import os
import time
from datetime import datetime, timedelta
from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QProgressBar, QFrame,
    QLineEdit, QPushButton, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
import logging

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager
# 安全QPainter导入移除: 暂时移除安全QPainter导入，避免绘图冲突
# from utils.safe_painter import safe_update, install_paint_filter

# 导入重构后的管理器类
from .channel_data_manager import ChannelDataManager
from .channel_timer_manager import ChannelTimerManager
from .channel_state_manager import ChannelStateManager, TestState
from .channel_ui_updater import ChannelUIUpdater
from .channel_event_handler import ChannelEventHandler
from .channel_ui_layout_manager import ChannelUILayoutManager
from .channel_style_manager import ChannelStyleManager

from .channel_config_manager import ChannelConfigManager

# 导入后端判断逻辑
from backend.test_result_manager import TestResultManager

# 导入统一的失败结果显示工具类
from ui.utils.fail_result_display_utils import FailResultDisplayUtils


class ChannelDisplayWidget(QWidget):
    """单通道显示组件"""

    # 信号定义
    battery_code_changed = pyqtSignal(int, str)  # 电池码变更信号 (channel, code)
    test_completed = pyqtSignal(int, dict)  # 测试完成信号 (channel, result)
    statistics_update_requested = pyqtSignal(bool, int, int)  # 统计更新信号 (is_pass, rs_grade, rct_grade)
    judgment_ready = pyqtSignal(int, bool, int, int, list)  # 判断结果准备信号 (channel, is_pass, rs_grade, rct_grade, fail_items)

    def __init__(self, channel_number: int, config_manager: ConfigManager, parent=None):
        """
        初始化单通道显示组件

        Args:
            channel_number: 通道号 (1-8)
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)

        self.channel_number = channel_number
        self.config_manager = config_manager

        # 初始化数据管理器（第二阶段集成）
        self.data_manager = ChannelDataManager(channel_number)

        # 保留原始数据属性作为兼容性接口（逐步迁移）
        self.test_start_time = None
        self.test_end_time = None  # 测试结束时间，用于独立计时

        # 修复添加进度状态管理，防止进度回退
        self.current_progress = 0
        self.max_progress_reached = 0

        # 容量预测相关
        self.capacity_prediction_algorithm = None
        self.predicted_capacity = None
        self.rct_coefficient_of_variation = 0.0

        # EIS参数相关

        # 频点测试数据
        self.current_frequency = 0.0
        self.frequency_index = 0
        self.total_frequencies = 0
        self.frequency_status = "waiting"
        # 重置频点进度标签
        if hasattr(self, 'frequency_progress_label') and self.frequency_progress_label:
            self.frequency_progress_label.setText("频点: 0/0")  # waiting, testing, completed

        # 频点更新状态跟踪
        self._last_frequency_update = None

        # 测试计数跟踪（第三阶段重构：使用配置管理器）
        self.test_count = 0  # 将在后面通过配置管理器加载

        # 通道状态管理 - 修复通道状态显示问题（第二阶段集成：添加回退属性）
        self._is_enabled = True  # 通道是否启用（回退属性）
        self._test_state = "idle"  # idle, testing, completed, failed, disabled（回退属性）

        # 已移除离群检测相关数据（功能已完全移除）

        # 初始化UI布局管理器（第三阶段重构）
        self.ui_layout_manager = ChannelUILayoutManager(channel_number, self)

        # 关键修复保存config_manager实例，确保取样测试模式检测正常工作
        self.config_manager = config_manager

        # 使用后端测试结果管理器进行判断
        self.test_result_manager = TestResultManager(config_manager, None)

        # 初始化样式管理器（第三阶段重构）
        self.style_manager = ChannelStyleManager(channel_number, self)



        # 初始化配置管理器（第三阶段重构）
        self.channel_config_manager = ChannelConfigManager(channel_number, config_manager)

        # 初始化界面
        self._init_ui()
        self._init_timer()

        # 加载测试计数（第三阶段重构：使用配置管理器）
        self.test_count = self.channel_config_manager.load_test_count()

        # 初始化测试计数显示
        self._update_test_count_display()

        # 初始化计时器管理器（第二阶段集成）
        self.timer_manager = ChannelTimerManager(channel_number)
        self.timer_manager.timer_updated.connect(self._on_timer_updated)

        # 初始化状态管理器（第二阶段集成）
        self.state_manager = ChannelStateManager(channel_number)
        self.state_manager.add_state_change_callback(self._on_state_changed)

        # 修复UI更新器初始化移到UI创建之后
        # self._init_ui_updater()  # 移到_init_ui方法末尾

        # 初始化事件处理器（第二阶段集成）
        self._init_event_handler()

        # 初始化容量预测功能
        self._init_capacity_prediction()

        # 安全QPainter导入移除: 暂时移除绘图保护安装
        # install_paint_filter(self)

        logger.debug(f"通道{channel_number}显示组件初始化完成")

    # ===== 数据管理器兼容性属性（第二阶段集成） =====

    @property
    def test_progress(self) -> int:
        """测试进度（兼容性属性）"""
        return self.data_manager.test_data.test_progress

    @test_progress.setter
    def test_progress(self, value: int):
        """设置测试进度（兼容性属性）"""
        self.data_manager.update_progress(value)

    @property
    def test_result(self):
        """测试结果（兼容性属性）"""
        return self.data_manager.test_result

    @test_result.setter
    def test_result(self, value):
        """设置测试结果（兼容性属性）"""
        self.data_manager.test_result = value

    @property
    def battery_code(self) -> str:
        """电池码（兼容性属性）"""
        return self.data_manager.test_data.battery_code

    @battery_code.setter
    def battery_code(self, value: str):
        """设置电池码（兼容性属性）"""
        self.data_manager.update_battery_code(value)

    @property
    def voltage(self) -> float:
        """电压（兼容性属性）"""
        return self.data_manager.test_data.voltage

    @voltage.setter
    def voltage(self, value: float):
        """设置电压（兼容性属性）"""
        self.data_manager.update_voltage(value)

    @property
    def rs_value(self) -> float:
        """Rs值（兼容性属性）"""
        return self.data_manager.test_data.rs_value

    @rs_value.setter
    def rs_value(self, value: float):
        """设置Rs值（兼容性属性）"""
        current_rct = self.data_manager.test_data.rct_value
        self.data_manager.update_impedance(value, current_rct)

    @property
    def rct_value(self) -> float:
        """Rct值（兼容性属性）"""
        return self.data_manager.test_data.rct_value

    @rct_value.setter
    def rct_value(self, value: float):
        """设置Rct值（兼容性属性）"""
        current_rs = self.data_manager.test_data.rs_value
        self.data_manager.update_impedance(current_rs, value)

    # ===== 状态管理器兼容性属性（第二阶段集成） =====

    @property
    def is_enabled(self) -> bool:
        """是否启用（兼容性属性）"""
        if hasattr(self, 'state_manager') and self.state_manager:
            return self.state_manager.is_enabled
        # 回退到原始属性
        return getattr(self, '_is_enabled', True)

    @is_enabled.setter
    def is_enabled(self, value: bool):
        """设置是否启用（兼容性属性）"""
        if hasattr(self, 'state_manager') and self.state_manager:
            self.state_manager.set_enable_state(value)
        else:
            # 回退到原始属性
            self._is_enabled = value

    @property
    def test_state(self) -> str:
        """测试状态（兼容性属性）"""
        if hasattr(self, 'state_manager') and self.state_manager:
            return self.state_manager.test_state.value
        # 回退到原始属性
        return getattr(self, '_test_state', 'idle')

    @test_state.setter
    def test_state(self, value: str):
        """设置测试状态（兼容性属性）"""
        try:
            if hasattr(self, 'state_manager') and self.state_manager:
                if hasattr(TestState, value.upper()):
                    test_state = TestState(value)
                    self.state_manager.set_test_state(test_state)
                else:
                    logger.warning(f"通道{self.channel_number}未知测试状态: {value}")
            else:
                # 回退到原始属性
                self._test_state = value
        except Exception as e:
            logger.error(f"通道{self.channel_number}设置测试状态失败: {e}")

    def set_testing_state_compat(self, is_testing: bool):
        """设置测试中状态（兼容性方法）"""
        if hasattr(self, 'state_manager') and self.state_manager:
            self.state_manager.set_testing_state(is_testing)

    def is_testing_compat(self) -> bool:
        """获取是否正在测试（兼容性方法）"""
        if hasattr(self, 'state_manager') and self.state_manager:
            return self.state_manager.is_testing
        return False

    def set_test_state_compat(self, state: str):
        """设置测试状态（兼容性方法）"""
        self.test_state = state

    def _on_timer_updated(self, channel_number: int, elapsed_time: float):
        """计时器更新回调（第二阶段集成）"""
        try:
            # 格式化时间显示
            hours, remainder = divmod(int(elapsed_time), 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            # 更新时间标签
            if hasattr(self, 'test_time_label'):
                self.test_time_label.setText(time_str)

        except Exception as e:
            logger.error(f"通道{self.channel_number}计时器更新回调失败: {e}")

    def _on_state_changed(self, event):
        """状态变化回调（第二阶段集成）"""
        try:
            from .channel_state_manager import StateChangeEvent

            # 根据状态变化更新UI
            if event.new_state == TestState.TESTING:
                # 开始测试时启动计时器（确保在主线程中执行）
                if not self.timer_manager.is_running:
                    from PyQt5.QtCore import QTimer
                    def start_timer_safe():
                        self.timer_manager.start_timer()
                    QTimer.singleShot(0, start_timer_safe)

            elif event.old_state == TestState.TESTING:
                # 结束测试时停止计时器
                if self.timer_manager.is_running:
                    self.timer_manager.stop_timer()

            logger.debug(f"通道{self.channel_number}状态变化: {event.old_state.value} -> {event.new_state.value}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}状态变化回调失败: {e}")

    def _init_ui_updater(self):
        """初始化UI更新器（第二阶段集成）"""
        try:
            # 收集UI元素引用
            ui_elements = {
                'voltage_label': getattr(self, 'voltage_label', None),
                'rs_label': getattr(self, 'rs_label', None),
                'rct_label': getattr(self, 'rct_label', None),
                # 保持移除继续隐藏阻抗比标签引用
                # 'impedance_ratio_label': getattr(self, 'impedance_ratio_label', None),
                'progress_bar': getattr(self, 'progress_bar', None),
                'result_label': getattr(self, 'result_label', None),
                'grade_label': getattr(self, 'grade_label', None)
            }

            # 初始化UI更新器
            self.ui_updater = ChannelUIUpdater(self.channel_number, ui_elements)
            logger.debug(f"通道{self.channel_number}UI更新器初始化完成")

        except Exception as e:
            logger.error(f"通道{self.channel_number}UI更新器初始化失败: {e}")

    def _init_event_handler(self):
        """初始化事件处理器（第二阶段集成）"""
        try:
            # 初始化事件处理器
            self.event_handler = ChannelEventHandler(self.channel_number, self)

            # 连接信号
            self.event_handler.channel_clicked.connect(self._on_channel_clicked)
            self.event_handler.channel_double_clicked.connect(self._on_channel_double_clicked)

            logger.debug(f"通道{self.channel_number}事件处理器初始化完成")

        except Exception as e:
            logger.error(f"通道{self.channel_number}事件处理器初始化失败: {e}")

    def _on_channel_clicked(self, channel_number: int):
        """通道点击事件处理"""
        logger.debug(f"通道{channel_number}被点击")

    def _on_channel_double_clicked(self, channel_number: int):
        """通道双击事件处理"""
        logger.debug(f"通道{channel_number}被双击")



    def _init_ui(self):
        """初始化用户界面（第三阶段重构：使用UI布局管理器）"""
        try:
            # 使用UI布局管理器创建布局
            main_layout = self.ui_layout_manager.create_main_layout()

            if main_layout is None:
                logger.error(f"通道{self.channel_number}UI布局创建失败")
                return

            # 获取UI元素引用
            ui_elements = self.ui_layout_manager.get_all_ui_elements()

            # 设置UI元素引用到当前对象（保持兼容性）
            for name, element in ui_elements.items():
                setattr(self, name, element)

            # 连接信号
            if hasattr(self, 'battery_code_edit'):
                self.battery_code_edit.textChanged.connect(self._on_battery_code_changed)

            # 应用样式
            self.style_manager.apply_default_styles()

            # 修复在UI创建完成后初始化UI更新器
            self._init_ui_updater()

            logger.debug(f"通道{self.channel_number}UI初始化完成")

        except Exception as e:
            logger.error(f"通道{self.channel_number}UI初始化失败: {e}")
            # 回退到原始UI创建方法
            self._init_ui_fallback()

    def _init_ui_fallback(self):
        """回退的UI初始化方法（保持兼容性）"""
        try:
            # 创建主布局
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(2, 2, 2, 2)
            main_layout.setSpacing(2)

            # 创建分组框
            group_box = QGroupBox(f"通道 {self.channel_number}")
            group_box.setObjectName("channelGroup")
            main_layout.addWidget(group_box)

            # 创建内容布局
            content_layout = QVBoxLayout(group_box)
            content_layout.setContentsMargins(6, 8, 6, 6)
            content_layout.setSpacing(3)

            # 创建显示区域
            self._create_display_areas(content_layout)

            # 设置组件样式
            self._apply_styles()

            # 修复在回退UI创建完成后也初始化UI更新器
            self._init_ui_updater()

            logger.debug(f"通道{self.channel_number}回退UI初始化完成")

        except Exception as e:
            logger.error(f"通道{self.channel_number}回退UI初始化失败: {e}")

    def _create_display_areas(self, layout):
        """创建显示区域 - 紧凑2列布局"""
        # 创建各个区域
        self._create_main_content_area(layout)
        self._create_progress_area(layout)
        self._create_result_area(layout)

    def _create_main_content_area(self, layout):
        """创建主内容区域 - 🔧 1920*1080优化：调整布局比例和间距"""
        # 创建主内容容器
        main_container = QFrame()
        main_container.setObjectName("mainContentContainer")
        main_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main_layout = QHBoxLayout(main_container)
        main_layout.setSpacing(4)  # 1920*1080深度优化进一步减小间距
        main_layout.setContentsMargins(4, 4, 4, 4)  # 1920*1080深度优化进一步减小边距

        # 左列：基本信息 - 🔧 1920*1080优化：调整权重比例
        left_column = self._create_left_column()
        main_layout.addLayout(left_column, 4)  # 1920*1080终极优化调整为4:6比例，给右列更多空间

        # 右列：阻抗值显示 - 🔧 1920*1080终极优化：增加权重，确保阻抗值完整显示
        right_column = self._create_right_column()
        main_layout.addLayout(right_column, 6)  # 1920*1080终极优化增加到6份权重，确保阻抗值有足够显示空间

        layout.addWidget(main_container)

    def _create_left_column(self):
        """创建左列 - 基本信息显示"""
        left_column = QVBoxLayout()
        left_column.setSpacing(4)

        # 测试计数和测试时间区域（第一行）
        self._create_count_time_area(left_column)

        # 电池码输入区域（第二行）
        self._create_battery_code_area(left_column)

        # 电压显示区域（第三行）
        self._create_voltage_area(left_column)

        # 移除离群率显示区域（用户要求不再显示）
        # self._create_outlier_rate_area(left_column)

        # 减少弹性空间，为结果区域留出更多垂直空间
        left_column.addStretch(1)

        return left_column

    def _create_count_time_area(self, layout):
        """创建测试计数和测试时间区域"""
        count_time_layout = QHBoxLayout()
        count_time_layout.setSpacing(8)
        count_time_layout.setContentsMargins(0, 0, 0, 2)

        # 测试计数显示
        count_label = QLabel("测试计数:")
        count_label.setStyleSheet("font-size: 14pt; color: #7f8c8d; font-weight: bold;")  # 精确调整从12pt增大到14pt (+2pt)
        count_time_layout.addWidget(count_label)

        self.test_count_label = QLabel("0")
        self.test_count_label.setObjectName("countLabel")
        self.test_count_label.setStyleSheet("font-size: 15pt; color: #27ae60; font-weight: bold;")  # 精确调整从13pt增大到15pt (+2pt)
        count_time_layout.addWidget(self.test_count_label)

        # 分隔符
        count_time_layout.addWidget(QLabel("|"))

        # 测试时间显示
        time_label = QLabel("测试用时:")
        time_label.setStyleSheet("font-size: 14pt; color: #7f8c8d; font-weight: bold;")  # 精确调整从12pt增大到14pt (+2pt)
        count_time_layout.addWidget(time_label)

        self.test_time_label = QLabel("00:00:00")
        self.test_time_label.setObjectName("timeLabel")
        count_time_layout.addWidget(self.test_time_label)

        count_time_layout.addStretch()
        layout.addLayout(count_time_layout)

    def _create_battery_code_area(self, layout):
        """创建电池码输入区域 - 合理优化电池码显示"""
        battery_layout = QHBoxLayout()
        battery_layout.setSpacing(6)

        battery_label = QLabel("电池码:")
        battery_label.setStyleSheet("font-size: 14pt; color: #7f8c8d; font-weight: bold;")
        battery_label.setMinimumWidth(55)  # 合理优化最小宽度确保标签显示，不过度占用空间
        battery_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        battery_layout.addWidget(battery_label)

        self.battery_code_edit = QLineEdit()
        self.battery_code_edit.setObjectName("batteryCodeEdit")
        self.battery_code_edit.setPlaceholderText("扫码或输入")
        self.battery_code_edit.textChanged.connect(self._on_battery_code_changed)
        # 合理优化设置合适的最小宽度，确保电池码完整显示但不过度占用空间
        self.battery_code_edit.setMinimumWidth(160)
        self.battery_code_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        battery_layout.addWidget(self.battery_code_edit)

        layout.addLayout(battery_layout)

    def _create_voltage_area(self, layout):
        """创建电压显示区域"""
        voltage_layout = QHBoxLayout()
        voltage_layout.setSpacing(4)

        voltage_label = QLabel("电压(V):")
        voltage_label.setStyleSheet("font-size: 14pt; color: #7f8c8d; font-weight: bold;")  # 精确调整从12pt增大到14pt (+2pt)
        voltage_layout.addWidget(voltage_label)

        self.voltage_label = QLabel("0.000")
        self.voltage_label.setObjectName("dataLabel")
        voltage_layout.addWidget(self.voltage_label)

        # 频点进度标签
        self.frequency_progress_label = QLabel("频点: 0/0")
        self.frequency_progress_label.setObjectName("frequencyProgressLabel")
        voltage_layout.addWidget(self.frequency_progress_label)

        voltage_layout.addStretch()

        layout.addLayout(voltage_layout)

    def _create_right_column(self):
        """创建右列 - 🔧 1920*1080优化：阻抗值显示（紧凑格式）"""
        right_column = QVBoxLayout()
        right_column.setSpacing(1)  # 1920*1080深度优化进一步减小垂直间距
        right_column.setContentsMargins(0, 0, 0, 0)

        # 创建Rs显示区域（紧凑单行格式）
        self._create_compact_impedance_area(right_column, "Rs(mΩ)", "rs")

        # 创建Rct显示区域（紧凑单行格式）
        self._create_compact_impedance_area(right_column, "Rct(mΩ)", "rct")

        # Jack要求移除Rsei显示，只显示Rs和Rct
        # self._create_compact_impedance_area(right_column, "Rsei(mΩ)", "rsei")

        # 保持移除继续隐藏Rp/Rs阻抗比显示
        # self._create_compact_impedance_area(right_column, "Rp/Rs", "impedance_ratio")

        # 1920*1080优化减少弹性空间，为阻抗值显示留出更多空间
        right_column.addStretch(1)

        return right_column

    def _create_compact_impedance_area(self, layout, title: str, object_name: str):
        """
        创建紧凑的阻抗值显示区域 - 优化1920*1080分辨率显示

        Args:
            layout: 父布局
            title: 显示标题
            object_name: 对象名称前缀
        """
        impedance_layout = QHBoxLayout()
        impedance_layout.setSpacing(2)  # 1920*1080深度优化进一步减小间距

        # 标题标签 - 🔧 1920*1080终极优化：极限紧凑的标题设计
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 6pt; color: #7f8c8d; font-weight: bold;")  # 终极优化极限减小字体
        title_label.setMinimumWidth(38)  # 终极优化极限减小宽度
        title_label.setMaximumWidth(38)  # 终极优化固定极限小宽度
        title_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        impedance_layout.addWidget(title_label)

        # 数值标签 - 🔧 1920*1080优化：调整字体和尺寸
        value_label = QLabel("0.000")
        value_label.setObjectName(f"{object_name}Value")
        value_label.setWordWrap(True)  # 启用自动换行
        value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)  # 左对齐，更紧凑

        # 1920*1080终极优化极限缩小字体和高度，确保完全不被截取
        value_label.setStyleSheet("font-size: 7pt; font-weight: bold; color: #2c3e50; padding: 1px;")
        value_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        value_label.setMinimumHeight(16)  # 终极优化极限减小最小高度
        value_label.setMaximumHeight(18)  # 终极优化极限限制最大高度

        impedance_layout.addWidget(value_label)

        # 保存数值标签引用
        if object_name == "rs":
            self.rs_label = value_label
        elif object_name == "rct":
            self.rct_label = value_label
        # 保持移除继续隐藏阻抗比标签引用
        # elif object_name == "impedance_ratio":
        # self.impedance_ratio_label = value_label

        layout.addLayout(impedance_layout)

    def _create_outlier_rate_area(self, layout):
        """🔧 已移除：离群率显示区域（用户要求不再显示）"""
        # 离群率功能已完全移除，不再创建任何UI元素
        # 这样可以为阻抗值显示腾出更多空间
        pass

    def _create_progress_area(self, layout):
        """创建进度条区域 - 🔧 1920*1080优化：减小高度"""
        # 1920*1080优化减小分隔空间
        layout.addSpacing(4)

        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("testProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(8)  # 1920*1080优化从12px减小到8px
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.progress_bar)

    def _create_result_area(self, layout):
        """创建测试结果显示区域（档位+判定双区域格式）- 🔧 1920*1080优化：减小高度"""
        # 1920*1080优化减小分隔空间
        layout.addSpacing(4)  # 减小间距，为上方阻抗值腾出更多空间

        # 创建水平布局容器
        result_container = QHBoxLayout()
        result_container.setSpacing(4)  # 1920*1080优化减小间距，节省空间
        result_container.setContentsMargins(0, 0, 0, 0)

        # 第一个区域：档位显示 (1/3宽度) - 🔧 1920*1080优化：进一步减小高度
        self.grade_label = QLabel("--")
        self.grade_label.setObjectName("gradeDisplay")
        self.grade_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grade_label.setFixedHeight(50)  # 1920*1080优化从80px减小到50px，给上方阻抗值更多空间
        self.grade_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        result_container.addWidget(self.grade_label, 1)  # 占1份权重

        # 第二个区域：测试结果判定 (2/3宽度) - 🔧 1920*1080优化：进一步减小高度
        self.result_label = QLabel("待测试")
        self.result_label.setObjectName("resultWaiting")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setFixedHeight(50)  # 1920*1080优化从80px减小到50px，给上方阻抗值更多空间
        self.result_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        result_container.addWidget(self.result_label, 2)  # 占2份权重

        # 将水平布局添加到主布局
        result_widget = QWidget()
        result_widget.setLayout(result_container)
        layout.addWidget(result_widget)





    def _apply_styles(self):
        """应用工业设计风格+苹果设计语言样式"""
        self.setStyleSheet("""
            /* 工业设计风格通道组框 */
            QGroupBox#channelGroup {
                font-weight: bold;
                border: 1px solid #d1d5db;  /* 更细的边框，符合现代设计 */
                border-radius: 12px;  /* 增加圆角，符合苹果设计语言 */
                margin-top: 12px;
                padding-top: 8px;
                background-color: #ffffff;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);  /* 添加阴影，增强层次感 */
            }

            QGroupBox#channelGroup::title {
                subcontrol-origin: margin;
                left: 8px;  /* 减小左边距：12px→8px */
                padding: 0 8px 0 8px;  /* 减小内边距：12px→8px */
                color: #1f2937;  /* 更深的文字颜色，提升对比度 */
                font-size: 12pt;  /* 进一步减小字体：15pt→12pt，给Rs/Rct更多空间 */
                font-weight: 600;  /* 🔧 精确调整：进一步减轻字重，从700减小到600 */
                background-color: #ffffff;
            }

            QLabel#timeLabel {
                font-size: 15pt;  /* 🔧 精确调整：从13pt增大到15pt (+2pt) */
                font-weight: bold;
                color: #3498db;
                background-color: #ebf3fd;
                border: 1px solid #3498db;
                border-radius: 2px;
                padding: 1px 4px;
                max-height: 18px;  /* 字体优化：适应更大字体的高度 */
            }

            QLineEdit#batteryCodeEdit {
                border: 1px solid #bdc3c7 !important;
                border-radius: 3px !important;
                padding: 2px 4px !important;
                background-color: white !important;
                font-size: 14pt !important;  /* 🔧 精确调整：从12pt增大到14pt (+2pt) */
                max-height: 32px !important;  /* 🔧 精确调整：适应更大字体，从28px增加到32px */
                color: #2c3e50 !important;
                min-height: 30px !important;  /* 🔧 精确调整：适应更大字体，从26px增加到30px */
            }

            QLineEdit#batteryCodeEdit:focus {
                border-color: #3498db !important;
                background-color: #f8f9fa !important;
            }

            /* 🔧 已移除：离群率显示样式（功能已完全移除） */

            /* 工业设计风格数据标签 */
            QLabel#dataLabel {
                font-size: 17pt;  /* 🔧 精确调整：从15pt增大到17pt (+2pt) */
                font-weight: 600;  /* 中等粗细 */
                color: #1f2937;
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 6px;  /* 增加圆角 */
                padding: 6px 8px;  /* 增加内边距 */
                min-width: 70px;  /* 稍微增加宽度 */
                max-height: 40px;  /* 🔧 精确调整：适应更大字体，从36px增加到40px */
            }

            /* 主内容容器样式 */
            QFrame#mainContentContainer {
                background-color: transparent;
                border: none;
            }

            /* 🔧 1920*1080终极优化：阻抗值显示样式 - 极限紧凑设计 */
            QLabel#rsValue {
                font-size: 7pt;  /* 🔧 终极优化：极限缩小字体到7pt */
                font-weight: bold;
                color: #065f46;
                background-color: #ecfdf5;
                border: 1px solid #10b981;
                border-radius: 2px;  /* 极致减小圆角 */
                padding: 1px 2px;  /* 极限减小内边距 */
                margin: 0px;
                min-width: 50px;  /* 🔧 终极优化：极限减小最小宽度 */
                min-height: 16px;  /* 🔧 终极优化：极限减小高度 */
                max-width: 140px;  /* 🔧 终极优化：进一步增加最大宽度 */
                max-height: 18px;  /* 🔧 终极优化：极限限制最大高度 */
            }

            QLabel#rctValue {
                font-size: 7pt;  /* 🔧 终极优化：极限缩小字体到7pt */
                font-weight: bold;
                color: #1e40af;
                background-color: #eff6ff;
                border: 1px solid #3b82f6;
                border-radius: 2px;  /* 极致减小圆角 */
                padding: 1px 2px;  /* 极限减小内边距 */
                margin: 0px;
                min-width: 50px;  /* 🔧 终极优化：极限减小最小宽度 */
                min-height: 16px;  /* 🔧 终极优化：极限减小高度 */
                max-width: 140px;  /* 🔧 终极优化：进一步增加最大宽度 */
                max-height: 18px;  /* 🔧 终极优化：极限限制最大高度 */
            }


                color: #7c2d12;  /* 棕色系，区别于Rs和Rct */
                background-color: #fef7ed;
                border: 1px solid #ea580c;
                border-radius: 2px;  /* 极致减小圆角 */
                padding: 1px 2px;  /* 极限减小内边距 */
                margin: 0px;
                min-width: 50px;  /* 🔧 终极优化：极限减小最小宽度 */
                min-height: 16px;  /* 🔧 终极优化：极限减小高度 */
                max-width: 140px;  /* 🔧 终极优化：进一步增加最大宽度 */
                max-height: 18px;  /* 🔧 终极优化：极限限制最大高度 */
            }

            QLabel#impedance_ratioValue {
                font-size: 7pt;  /* 🔧 终极优化：极限缩小字体到7pt */
                font-weight: bold;
                color: #6b21a8;  /* 紫色系，区别于其他参数 */
                background-color: #faf5ff;
                border: 1px solid #9333ea;
                border-radius: 2px;  /* 极致减小圆角 */
                padding: 1px 2px;  /* 极限减小内边距 */
                margin: 0px;
                min-width: 50px;  /* 🔧 终极优化：极限减小最小宽度 */
                min-height: 16px;  /* 🔧 终极优化：极限减小高度 */
                max-width: 140px;  /* 🔧 终极优化：进一步增加最大宽度 */
                max-height: 18px;  /* 🔧 终极优化：极限限制最大高度 */
            }

            /* 工业设计风格进度条 */
            QProgressBar#testProgress {
                border: 1px solid #e5e7eb;
                border-radius: 8px;  /* 增加圆角 */
                text-align: center;
                background-color: #f9fafb;
                color: #374151;
                font-weight: 500;  /* 中等粗细 */
                font-size: 9pt;  /* 稍微增大字体 */
                max-height: 16px;  /* 增加高度 */
                min-height: 16px;
            }

            QProgressBar#testProgress::chunk {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #60a5fa, stop:1 #3b82f6);  /* 渐变色，符合苹果设计语言 */
                border-radius: 7px;  /* 内部圆角 */
            }

            /* 工业设计风格档位显示 - 紧凑优化 */
            QLabel#gradeDisplay {
                background-color: #f0f9ff;
                border: 1px solid #0ea5e9;
                border-radius: 8px;  /* 增加圆角 */
                color: #0c4a6e;
                font-weight: 900;  /* 超粗体，提升视觉重要性 */
                font-size: 32pt;  /* 调整字体大小适应80px高度 */
                padding: 8px;  /* 减小内边距适应新高度 */
                min-height: 80px;  /* 紧凑高度，给上方数据更多空间 */
                max-height: 80px;
                text-align: center;
            }

            QLabel#gradePass {
                background-color: #d5f4e6;
                border: 2px solid #27ae60;
                border-radius: 6px;  /* 🔧 1920*1080优化：减小圆角适应新高度 */
                color: #27ae60;
                font-weight: 900;  /* 超粗体 */
                font-size: 24pt;  /* 🔧 1920*1080优化：从32pt减小到24pt适应50px高度 */
                padding: 4px;  /* 🔧 1920*1080优化：减小内边距适应新高度 */
                min-height: 50px;  /* 🔧 1920*1080优化：从80px减小到50px，给上方阻抗值更多空间 */
                max-height: 50px;
                text-align: center;
            }

            QLabel#gradeFail {
                background-color: #fadbd8;
                border: 2px solid #e74c3c;
                border-radius: 6px;  /* 🔧 1920*1080优化：减小圆角适应新高度 */
                color: #e74c3c;
                font-weight: 900;  /* 超粗体 */
                font-size: 24pt;  /* 🔧 1920*1080优化：从32pt减小到24pt适应50px高度 */
                padding: 4px;  /* 🔧 1920*1080优化：减小内边距适应新高度 */
                min-height: 50px;  /* 🔧 1920*1080优化：从80px减小到50px，给上方阻抗值更多空间 */
                max-height: 50px;
                text-align: center;
            }

            /* 工业设计风格结果显示 - 等待状态 - 🔧 1920*1080优化：进一步减小高度 */
            QLabel#resultWaiting {
                background-color: #f9fafb;
                border: 1px solid #d1d5db;
                border-radius: 6px;  /* 🔧 1920*1080优化：减小圆角适应新高度 */
                color: #6b7280;
                font-weight: 900;  /* 超粗体，提升视觉重要性 */
                font-size: 24pt;  /* 🔧 1920*1080优化：从32pt减小到24pt适应50px高度 */
                padding: 4px;  /* 🔧 1920*1080优化：减小内边距适应新高度 */
                min-height: 50px;  /* 🔧 1920*1080优化：从80px减小到50px，给上方阻抗值更多空间 */
                max-height: 50px;
                text-align: center;
            }

            /* 工业设计风格结果显示 - 测试中状态 - 🔧 1920*1080优化：进一步减小高度 */
            QLabel#resultTesting {
                background-color: #fef3c7;
                border: 1px solid #f59e0b;
                border-radius: 6px;  /* 🔧 1920*1080优化：减小圆角适应新高度 */
                color: #92400e;
                font-weight: 900;  /* 超粗体，提升视觉重要性 */
                font-size: 24pt;  /* 🔧 1920*1080优化：从32pt减小到24pt适应50px高度 */
                padding: 4px;  /* 🔧 1920*1080优化：减小内边距适应新高度 */
                min-height: 50px;  /* 🔧 1920*1080优化：从80px减小到50px，给上方阻抗值更多空间 */
                max-height: 50px;
                text-align: center;
            }

            /* 工业设计风格结果显示 - 通过状态 - 🔧 1920*1080优化：进一步减小高度 */
            QLabel#resultPass {
                background-color: #ecfdf5;
                border: 1px solid #10b981;
                border-radius: 6px;  /* 🔧 1920*1080优化：减小圆角适应新高度 */
                color: #047857;
                font-weight: 900;  /* 超粗体，提升视觉重要性 */
                font-size: 24pt;  /* 🔧 1920*1080优化：从32pt减小到24pt适应50px高度 */
                padding: 4px;  /* 🔧 1920*1080优化：减小内边距适应新高度 */
                min-height: 50px;  /* 🔧 1920*1080优化：从80px减小到50px，给上方阻抗值更多空间 */
                max-height: 50px;
                text-align: center;
            }

            QLabel#resultFailV {
                background-color: #fadbd8;
                border: 2px solid #e74c3c;
                border-radius: 6px;  /* 🔧 1920*1080优化：减小圆角适应新高度 */
                color: #e74c3c;
                font-weight: 900;  /* 超粗体 */
                font-size: 24pt;  /* 🔧 1920*1080优化：从32pt减小到24pt适应50px高度 */
                padding: 4px;  /* 🔧 1920*1080优化：减小内边距适应新高度 */
                min-height: 50px;  /* 🔧 1920*1080优化：从80px减小到50px，给上方阻抗值更多空间 */
                max-height: 50px;
                text-align: center;
            }

            QLabel#resultFailRs {
                background-color: #fef9e7;
                border: 2px solid #f39c12;
                border-radius: 6px;  /* 🔧 1920*1080优化：减小圆角适应新高度 */
                color: #f39c12;
                font-weight: 900;  /* 超粗体 */
                font-size: 24pt;  /* 🔧 1920*1080优化：从32pt减小到24pt适应50px高度 */
                padding: 4px;  /* 🔧 1920*1080优化：减小内边距适应新高度 */
                min-height: 50px;  /* 🔧 1920*1080优化：从80px减小到50px，给上方阻抗值更多空间 */
                max-height: 50px;
                text-align: center;
            }

            QLabel#resultFailRct {
                background-color: #fadbd8;
                border: 2px solid #e74c3c;
                border-radius: 6px;  /* 🔧 1920*1080优化：减小圆角适应新高度 */
                color: #e74c3c;
                font-weight: 900;  /* 超粗体 */
                font-size: 24pt;  /* 🔧 1920*1080优化：从32pt减小到24pt适应50px高度 */
                padding: 4px;  /* 🔧 1920*1080优化：减小内边距适应新高度 */
                min-height: 50px;  /* 🔧 1920*1080优化：从80px减小到50px，给上方阻抗值更多空间 */
                max-height: 50px;
                text-align: center;
            }

            QLabel#resultFail {
                background-color: #fadbd8;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                color: #e74c3c;
                font-weight: 900;  /* 超粗体 */
                font-size: 32pt;  /* 调整字体大小适应80px高度 */
                padding: 8px;  /* 减小内边距适应新高度 */
                min-height: 80px;  /* 紧凑高度，给上方数据更多空间 */
                max-height: 80px;
                text-align: center;
            }

            QLabel#resultFailOutlier {
                background-color: #fef9e7;
                border: 2px solid #f39c12;
                border-radius: 8px;
                color: #f39c12;
                font-weight: 900;  /* 超粗体 */
                font-size: 32pt;  /* 调整字体大小适应80px高度 */
                padding: 8px;  /* 减小内边距适应新高度 */
                min-height: 80px;  /* 紧凑高度，给上方数据更多空间 */
                max-height: 80px;
                text-align: center;
            }

            /* 频点显示样式 */
            QLabel#frequencyValue {
                font-size: 10pt;
                font-weight: bold;
                color: #2c3e50;
                background-color: #e8f4fd;
                border: 1px solid #3498db;
                border-radius: 3px;
                padding: 2px 6px;
                min-width: 60px;
                max-height: 20px;
            }

            QLabel#frequencyProgress {
                font-size: 8pt;
                color: #7f8c8d;
                font-weight: bold;
                padding: 2px 4px;
                max-height: 20px;
            }

            QLabel#frequencyStatusWaiting {
                font-size: 12pt;
                color: #95a5a6;
                font-weight: bold;
                max-width: 16px;
                max-height: 20px;
            }

            QLabel#frequencyStatusTesting {
                font-size: 12pt;
                color: #3498db;
                font-weight: bold;
                max-width: 16px;
                max-height: 20px;
            }

            QLabel#frequencyStatusCompleted {
                font-size: 12pt;
                color: #27ae60;
                font-weight: bold;
                max-width: 16px;
                max-height: 20px;
            }

            /* 频点进度标签样式 */
            QLabel#frequencyProgressLabel {
                font-size: 11pt;
                color: #e67e22;
                font-weight: bold;
                padding: 2px 6px;
                border: 1px solid #f0c27a;
                border-radius: 3px;
                background-color: #fef5e7;
            }
        """)

    def _init_timer(self):
        """初始化定时器"""
        # 测试时间更新定时器
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self._update_test_time)
        self.time_timer.start(1000)  # 每秒更新一次
        # 当控件销毁时停止定时器，避免退出时触发回调导致中断
        try:
            self.destroyed.connect(self._stop_time_timer)
        except Exception:
            pass

    def _update_test_time(self):
        """更新测试时间显示 - 独立计时逻辑"""
        try:
            if self.test_start_time:
                # 如果测试已完成，显示最终测试用时并停止更新
                if self.test_end_time:
                    duration = self.test_end_time - self.test_start_time
                    hours, remainder = divmod(int(duration.total_seconds()), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    self.test_time_label.setText(time_str)
                    # 测试完成后不再更新时间显示
                    return

                # 测试进行中，实时更新时间
                duration = datetime.now() - self.test_start_time
                hours, remainder = divmod(int(duration.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                self.test_time_label.setText(time_str)

        except KeyboardInterrupt:
            logger.info(f"通道{self.channel_number}测试时间更新被中断，停止定时器")
            try:
                if hasattr(self, 'time_timer'):
                    self.time_timer.stop()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新测试时间失败: {e}")

    def _stop_time_timer(self, *args, **kwargs):
        try:
            if hasattr(self, 'time_timer') and self.time_timer.isActive():
                self.time_timer.stop()
                logger.debug(f"通道{self.channel_number}时间定时器已停止（控件销毁）")
        except Exception:
            pass

    def _on_battery_code_changed(self, text: str):
        """电池码变更处理"""
        self.battery_code = text
        self.battery_code_changed.emit(self.channel_number, text)

    def update_outlier_detection_status(self, enabled: bool):
        """
        🔧 已移除：离群检测状态更新（功能已完全移除）
        """
        # 离群率功能已完全移除，不执行任何操作
        pass

    def update_outlier_rate_result(self, result: str, baseline_filename: str = "", frequency_deviations: Optional[dict] = None, is_final: bool = False):
        """
        🔧 已移除：离群率结果更新（功能已完全移除）
        """
        # 离群率功能已完全移除，不执行任何操作
        pass

    def _format_outlier_rate_display(self, result: str, is_final: bool) -> str:
        """
        🔧 已移除：格式化离群率显示文本（功能已完全移除）
        """
        # 离群率功能已完全移除，返回空字符串
        return ""

    def start_test(self, battery_code: str = ""):
        """
        开始测试

        Args:
            battery_code: 电池码
        """
        try:
            # 修复连续测试状态清理 - 在开始新测试前进行全面重置
            logger.debug(f"通道{self.channel_number}开始测试前进行全面状态重置")

            # 测试结果保持逻辑优化: 开始新测试时清除之前的结果
            self.clear_previous_results()

            # 修复重置所有测试数据和状态变量
            self.voltage = 0.0
            self.rs_value = 0.0
            self.rct_value = 0.0
            self.test_progress = 0
            self.test_result = None

            # 修复重置测试完成标志，允许新的测试完成事件
            self._test_completed = False

            # 修复重置进度状态管理
            self.current_progress = 0
            self.max_progress_reached = 0
            logger.debug(f"🎯 [进度管理] 通道{self.channel_number}测试开始，重置进度状态")

            # 重置计时器状态 - 使用新的计时器管理器（第二阶段集成）
            self.timer_manager.reset_timer()
            # 使用QTimer.singleShot确保在主线程中启动计时器
            from PyQt5.QtCore import QTimer
            def start_timer_safe():
                self.timer_manager.start_timer()
            QTimer.singleShot(0, start_timer_safe)

            # 保留原始计时逻辑作为备份
            self.test_start_time = datetime.now()
            self.test_end_time = None  # 清除结束时间，重新开始计时

            if battery_code:
                self.battery_code_edit.setText(battery_code)

            # 修复强制重置所有UI显示元素
            # 重置测试用时显示
            self.test_time_label.setText("00:00:00")

            # 修复强制重置进度条为0%
            self.progress_bar.setValue(0)

            # 修复强制重置结果显示
            self.result_label.setText("测试中...")
            self.result_label.setObjectName("resultWaiting")
            self.result_label.setStyleSheet("")  # 重新应用样式

            # 修复强制重置档位显示（连续测试关键修复）
            self.grade_label.setText("--")
            self.grade_label.setObjectName("")  # 清除之前的对象名
            self.grade_label.setStyleSheet("")

            # 修复强制重置测试数据显示
            self.voltage_label.setText("0.000")
            self.rs_label.setText("0.000")
            self.rct_label.setText("0.000")

            # Jack要求移除Rsei显示相关逻辑
            # 修复重置Rsei显示（SEI膜电阻）- 已移除
            # if hasattr(self, 'rsei_label') and self.rsei_label is not None:
            #     self.rsei_label.setText("--")  # 显示为--而不是0.000
            #     logger.debug(f"通道{self.channel_number}Rsei标签已重置为--")
            # else:
            #     logger.warning(f"通道{self.channel_number}Rsei标签不存在或为None，无法重置")

            # 新增重置Rsei计算状态，清除超时标记 - 已移除
            # if hasattr(self, 'ui_updater') and self.ui_updater:
            #     # 清除UI更新器中的Rsei计算状态
            #     if hasattr(self.ui_updater, '_rsei_calculation_start_time'):
            #         delattr(self.ui_updater, '_rsei_calculation_start_time')
            #     if hasattr(self.ui_updater, '_rsei_calculation_timeout'):
            #         self.ui_updater._rsei_calculation_timeout = False
            #     logger.debug(f"通道{self.channel_number}Rsei计算状态已重置")

            # 修复强制刷新UI组件，确保第二次测试时能正常更新
            self.result_label.update()
            self.grade_label.update()
            self.progress_bar.update()

            # 修复强制清空频点信息，确保新测试时频点能正常更新（频点显示功能已移除）
            # 频点显示功能已移除，跳过清空频点信息
            logger.debug(f"通道{self.channel_number}频点显示功能已移除，跳过清空")

            # 重置离群率显示
            self.outlier_rate_result = "--"
            if self.outlier_detection_enabled:
                self.outlier_rate_label.setText("等待")

            # 修复强制刷新UI显示
            self.update()

            logger.info(f"通道{self.channel_number}开始测试，所有状态已重置")

        except Exception as e:
            logger.error(f"通道{self.channel_number}开始测试失败: {e}")

    def stop_test(self, clear_results=None):
        """
        停止测试

        Args:
            clear_results: 是否清除测试结果，None时根据配置决定
        """
        try:
            # 测试结果保持逻辑优化: 根据配置决定是否清除结果
            if clear_results is None:
                # 根据自动侦测配置决定是否清除结果
                auto_detect = self.config_manager.get('test_config.auto_detect', True)
                clear_results = not auto_detect  # 如果启用自动侦测，则不清除结果

            # 新增强制重置状态管理器
            if hasattr(self, 'state_manager') and self.state_manager:
                from .channel_state_manager import TestState
                self.state_manager.set_test_state(TestState.IDLE, "测试停止")
                logger.info(f"✅ 通道{self.channel_number}状态管理器已重置为IDLE")

            # 新增强制停止计时器（不依赖状态管理器回调）
            if hasattr(self, 'timer_manager') and self.timer_manager:
                if self.timer_manager.is_running:
                    self.timer_manager.stop_timer()
                    logger.info(f"✅ 通道{self.channel_number}计时器已强制停止")

            # 重置计时器状态 - 使用新的计时器管理器（第二阶段集成）
            if clear_results:
                self.timer_manager.stop_timer()
                self.timer_manager.reset_timer()

                # 保留原始计时逻辑作为备份
                self.test_start_time = None
                self.test_end_time = None  # 清除结束时间
                self.test_progress = 0
                self.test_result = None  # 清除测试结果

                # 修复强化进度状态管理重置
                self.current_progress = 0
                self.max_progress_reached = 0
                self.test_progress = 0  # 确保内部进度也重置
                logger.debug(f"🎯 [进度管理] 通道{self.channel_number}测试停止，完全重置进度状态")

                # 强化确保进度条重置
                if hasattr(self, 'progress_bar') and self.progress_bar:
                    self.progress_bar.setValue(0)
                    logger.debug(f"🎯 [进度管理] 通道{self.channel_number}进度条已重置为0")

                # 更新界面状态
                self.result_label.setText("待测试")
                self.result_label.setObjectName("resultWaiting")
                self.result_label.setStyleSheet("")  # 重新应用样式
                self.test_time_label.setText("00:00:00")

                # 重置档位显示
                self.grade_label.setText("--")
                self.grade_label.setStyleSheet("")

                # 新增强制刷新UI显示
                self.result_label.update()
                self.test_time_label.update()
                self.grade_label.update()
                self.update()  # 强制刷新整个widget

                logger.info(f"通道{self.channel_number}停止测试，结果已清除")
            else:
                # 保持测试结果，只重置进行中的状态
                if self.is_testing():
                    # 如果正在测试中被停止，重置进度但保持结果
                    self.test_progress = 0
                    self.progress_bar.setValue(0)

                logger.info(f"通道{self.channel_number}停止测试，结果已保持")

            # 清空频点信息（频点显示功能已移除）
            # 频点显示功能已移除，跳过清空频点信息

            # 启用扫码按钮（如果存在）
            if hasattr(self, 'scan_button'):
                self.scan_button.setEnabled(True)

        except Exception as e:
            logger.error(f"通道{self.channel_number}停止测试失败: {e}")

    def reset_progress_state(self, force_reset: bool = False):
        """
        重置进度状态（新增方法，专门用于进度管理）

        Args:
            force_reset: 是否强制重置，忽略当前状态
        """
        try:
            # 强化完全重置进度状态
            old_progress = getattr(self, 'current_progress', 0)
            old_max = getattr(self, 'max_progress_reached', 0)

            self.current_progress = 0
            self.max_progress_reached = 0
            self.test_progress = 0

            # 强化确保UI进度条也重置
            if hasattr(self, 'progress_bar') and self.progress_bar:
                self.progress_bar.setValue(0)

            # 修复重置测试完成标记，确保新测试时能正常接收后端判断结果
            if hasattr(self, '_test_completed'):
                self._test_completed = False
                logger.debug(f"通道{self.channel_number}重置测试完成标记（进度重置）")

            logger.info(f"🎯 [进度管理] 通道{self.channel_number}进度状态重置: {old_progress}%/{old_max}% -> 0%/0%")

        except Exception as e:
            logger.error(f"通道{self.channel_number}重置进度状态失败: {e}")

    def update_test_data(self, voltage: float, rs: float, rct: float, progress: int):
        """
        更新测试数据 - Jack的简化版本

        Args:
            voltage: 电压值 (V)
            rs: Rs值 (mΩ)
            rct: Rct值 (mΩ) - 总极化阻抗，包含原Rsei+Rct
            progress: 测试进度 (0-100)
        """
        try:
            # Jack的简化版本: 移除数据变化检查，确保UI始终更新
            # 这样可以确保EIS计算的新值能够正确同步到UI显示
            logger.debug(f"通道{self.channel_number}更新数据: V={voltage:.3f}, Rs={rs:.3f}, Rct={rct:.3f}, 进度={progress}%")

            # 修复简化进度管理逻辑，确保实时进度能够正常显示
            original_progress = progress

            # 新增检测测试开始，自动重置进度状态
            if (progress > 0 and self.current_progress == 0 and
                self.max_progress_reached == 0 and not self.is_testing()):
                logger.info(f"🎯 [进度管理] 通道{self.channel_number}检测到新测试开始，重置进度状态")
                self.reset_progress_state(force_reset=True)

            # 修复简化进度更新逻辑，允许实时进度显示
            # 检测测试重新开始的情况
            if (self.current_progress > 40 and progress < 10):
                logger.info(f"🔄 [进度管理] 通道{self.channel_number}检测到测试重新开始，重置进度状态: {self.current_progress}% -> {progress}%")
                self.reset_progress_state(force_reset=True)

            # 关键修复直接更新当前进度，确保UI能够实时显示
            self.current_progress = progress
            if progress > self.max_progress_reached:
                self.max_progress_reached = progress
                logger.debug(f"🎯 [进度管理] 通道{self.channel_number}进度递增: {progress}% (新最高进度)")
            else:
                logger.debug(f"🎯 [进度管理] 通道{self.channel_number}进度更新: {progress}%")

            # 修复更新内部数据，确保数据能够正确保存
            self.voltage = voltage
            # 使用强制更新确保Rs和Rct值能够保存，绕过验证限制
            if hasattr(self, 'data_manager') and self.data_manager:
                self.data_manager.force_update_impedance(rs, rct)

            # 修复同时更新所有相关属性，确保数据一致性
            # 重要修复恢复正数检查，因为算法已经修复了负数Rs问题
            # Rs和Rct在物理上必须为正数，但单频点测试时Rct=0是正常的
            if rs > 0 and rct >= 0:  # 修改：允许Rct=0（单频点测试）
                self.rs_value = rs
                self.rct_value = rct
                self.current_rs = rs
                self.current_rct = rct
                # 修复如果正在等待有效数据，现在收到了，清除等待标志
                if getattr(self, '_waiting_for_valid_data', False):
                    self._waiting_for_valid_data = False

                # 单频点测试检测和日志
                if rct == 0.0:
                    logger.info(f"通道{self.channel_number}检测到单频点测试结果: Rs={rs:.3f}mΩ, Rct=0.000mΩ")

            # Jack要求移除Rsei处理，只保留Rs和Rct
            # Rct现在包含总极化阻抗（原Rsei+Rct）

            if voltage > 0:
                self.voltage = voltage
                self.current_voltage = voltage

            self.test_progress = progress


            # 强制更新UI，确保EIS计算值能够显示
            self._safe_update_ui_data(voltage, rs, rct, progress)

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新测试数据失败: {e}")

    def update_battery_status(self, status: str, voltage: float):
        """更新电池状态显示"""
        try:
            logger.info(f"🔋 通道{self.channel_number}更新电池状态: {status} ({voltage:.2f}V)")

            # 🆕 实时更新电压显示（无论电池状态如何，始终显示当前电压）
            if hasattr(self, 'voltage_label') and self.voltage_label:
                self.voltage_label.setText(f"{voltage:.3f}")

            # 获取电池状态指示器 - 修复：增强调试和多种获取方式
            indicator = None

            # 方法1：尝试从UI布局管理器获取电池状态指示器
            if hasattr(self, 'ui_layout_manager') and self.ui_layout_manager:
                ui_elements = self.ui_layout_manager.get_all_ui_elements()
                indicator = ui_elements.get('battery_status_indicator')
                logger.debug(f"通道{self.channel_number}方法1获取指示器: {'成功' if indicator else '失败'}")

            # 方法2：备用方案：直接从属性获取
            if not indicator and hasattr(self, 'battery_status_indicator'):
                indicator = self.battery_status_indicator
                logger.debug(f"通道{self.channel_number}方法2获取指示器: 成功")

            # 方法3：通过对象名称查找
            if not indicator:
                indicator = self.findChild(QLabel, "batteryStatusIndicator")
                logger.debug(f"通道{self.channel_number}方法3获取指示器: {'成功' if indicator else '失败'}")

            # 方法4：遍历所有QLabel查找
            if not indicator:
                for child in self.findChildren(QLabel):
                    if child.objectName() == "batteryStatusIndicator":
                        indicator = child
                        logger.debug(f"通道{self.channel_number}方法4获取指示器: 成功")
                        break
                if not indicator:
                    logger.debug(f"通道{self.channel_number}方法4获取指示器: 失败")

            if indicator:
                # 根据状态设置指示器样式和文本
                if status == "connected":
                    indicator.setText("●")
                    indicator.setStyleSheet("""
                        QLabel {
                            font-size: 18pt;
                            font-weight: bold;
                            color: #27ae60;
                            min-width: 28px;
                            min-height: 28px;
                            text-align: center;
                            border-radius: 14px;
                            padding: 2px;
                        }
                    """)
                    indicator.setToolTip(f"电池状态：已连接 ({voltage:.2f}V)")
                elif status == "removed":
                    indicator.setText("○")
                    indicator.setStyleSheet("""
                        QLabel {
                            font-size: 18pt;
                            font-weight: bold;
                            color: #e74c3c;
                            min-width: 28px;
                            min-height: 28px;
                            text-align: center;
                            border-radius: 14px;
                            padding: 2px;
                        }
                    """)
                    indicator.setToolTip(f"电池状态：已移除 ({voltage:.2f}V)")
                else:  # unknown
                    indicator.setText("")
                    indicator.setStyleSheet("""
                        QLabel {
                            font-size: 18pt;
                            font-weight: bold;
                            color: #f39c12;
                            min-width: 28px;
                            min-height: 28px;
                            text-align: center;
                            border-radius: 14px;
                            padding: 2px;
                        }
                    """)
                    indicator.setToolTip(f"电池状态：未知 ({voltage:.2f}V)")

                logger.info(f"✅ 通道{self.channel_number}电池状态更新成功: {status} ({voltage:.2f}V)")
            else:
                logger.warning(f"⚠️ 通道{self.channel_number}电池状态指示器未找到，尝试调试信息")
                # 调试信息
                logger.debug(f"  - hasattr ui_layout_manager: {hasattr(self, 'ui_layout_manager')}")
                logger.debug(f"  - hasattr battery_status_indicator: {hasattr(self, 'battery_status_indicator')}")
                if hasattr(self, 'ui_layout_manager') and self.ui_layout_manager:
                    ui_elements = self.ui_layout_manager.get_all_ui_elements()
                    logger.debug(f"  - UI元素列表: {list(ui_elements.keys())}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新电池状态失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            # 确保异常不会导致程序闪退

    def update_test_progress(self, progress_data: dict):
        """
        更新测试进度（新增方法，用于与通道容器兼容）

        Args:
            progress_data: 进度数据字典，包含以下字段：
                - state: 测试状态 ('testing', 'completed', 'failed', etc.)
                - progress: 测试进度 (0-100)
                - voltage: 电压值 (V)
                - rs_value: Rs值 (mΩ)
                - rct_value: Rct值 (mΩ)
                - frequency: 当前频率 (Hz)
                - is_pass: 是否合格 (仅在completed状态时有效)
                - rs_grade: Rs档位 (仅在completed状态时有效)
                - rct_grade: Rct档位 (仅在completed状态时有效)
                - fail_reason: 失败原因 (仅在不合格时有效)
        """
        try:
            state = progress_data.get('state', 'unknown')
            progress = progress_data.get('progress', 0)
            voltage = progress_data.get('voltage', 0.0)
            rs_value = progress_data.get('rs_value', 0.0)
            rct_value = progress_data.get('rct_value', 0.0)

            frequency = progress_data.get('frequency', 0.0)
            rct_cv = progress_data.get('rct_coefficient_of_variation', 0.0)

            logger.debug(f"通道{self.channel_number}进度更新: 状态={state}, 进度={progress}%, V={voltage:.3f}V, Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")

            # 根据状态进行不同的处理
            if state == 'testing':
                # 修复测试开始时启动计时器和重置进度
                if not self.is_testing():
                    # 新增测试开始时重置进度状态
                    if progress <= 5:  # 如果是测试开始阶段的低进度，重置状态
                        self.reset_progress_state(force_reset=True)
                        logger.debug(f"通道{self.channel_number}测试开始，重置进度状态")

                    self.set_testing_state(True)
                    logger.debug(f"通道{self.channel_number}开始测试，启动计时器")

                # 测试进行中，更新数据和进度
                self.update_test_data(voltage, rs_value, rct_value, progress)

                # 更新Rct变异系数
                if rct_cv > 0:
                    self.rct_coefficient_of_variation = rct_cv

                # 修复频率显示参数使用正确的频点索引和总数
                if frequency > 0:
                    # 修复使用后端传递的正确键名获取频点信息
                    current_index = progress_data.get('frequency_index', progress_data.get('current_frequency_index', 1))
                    total_count = progress_data.get('total_frequencies', progress_data.get('total_frequency_count', 2))  # 修复：默认值改为2

                    # 修复移除错误的推算逻辑，直接使用后端提供的准确信息
                    # 如果后端没有提供频点信息，使用保守的默认值
                    if current_index <= 0:
                        current_index = 1
                    if total_count <= 0:
                        total_count = 2  # 使用实际的频点数量作为默认值

                    logger.debug(f"通道{self.channel_number}更新频点显示: {frequency}Hz ({current_index}/{total_count}) testing")
                    # 更新频点进度标签
                    if hasattr(self, 'frequency_progress_label') and self.frequency_progress_label:
                        self.frequency_progress_label.setText(f"频点: {current_index}/{total_count}")

            elif state == 'completed':
                # 修复测试完成时停止计时器
                if self.is_testing():
                    self.set_testing_state(False)
                    logger.debug(f"通道{self.channel_number}测试完成，停止计时器")

                # 修复只有在接收到有效数据时才保存，避免0值覆盖正确数据
                # 单频点测试时Rct=0是正常的
                if rs_value > 0 and rct_value >= 0:
                    # 保存测试数据到实例属性
                    self.rs_value = rs_value
                    self.rct_value = rct_value
                    self.voltage = voltage
                    # 修复同时更新current_rs和current_rct属性，确保set_test_completed能获取到正确值
                    self.current_rs = rs_value
                    self.current_rct = rct_value
                    self.current_voltage = voltage

                    # 测试完成，更新最终数据和结果
                    self.update_test_data(voltage, rs_value, rct_value, 100)
                else:
                    # 修复如果接收到0值，使用之前保存的有效值
                    stored_rs = getattr(self, 'current_rs', 0) or getattr(self, 'rs_value', 0)
                    stored_rct = getattr(self, 'current_rct', 0) or getattr(self, 'rct_value', 0)
                    stored_voltage = getattr(self, 'current_voltage', 0) or getattr(self, 'voltage', 0)

                    if stored_rs > 0 and stored_rct >= 0:  # 允许单频点测试Rct=0
                        logger.debug(f"通道{self.channel_number}接收到0值，使用存储的有效值: Rs={stored_rs:.3f}mΩ, Rct={stored_rct:.3f}mΩ, V={stored_voltage:.3f}V")
                        # 使用存储的有效值
                        rs_value = stored_rs
                        rct_value = stored_rct
                        if voltage <= 0 and stored_voltage > 0:
                            voltage = stored_voltage
                        # 更新最终数据
                        self.update_test_data(voltage, rs_value, rct_value, 100)
                    else:
                        # 如果没有存储的有效值，延迟处理，等待后端数据
                        logger.debug(f"通道{self.channel_number}接收到0值且没有存储的有效值，延迟处理等待后端数据: Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")
                        # 设置一个标志，表示正在等待有效数据
                        self._waiting_for_valid_data = True
                        # 修复红色异常问题不再使用延迟检查，直接更新进度但不设置异常
                        self.update_test_data(voltage, 0, 0, 100)
                        logger.debug(f" 通道{self.channel_number}测试完成但数据为0，跳过延迟检查避免红色异常误判")

                # 更新Rct变异系数
                if rct_cv > 0:
                    self.rct_coefficient_of_variation = rct_cv

                # 修复处理离群率检测结果显示
                outlier_result = progress_data.get('outlier_result')
                frequency_deviations = progress_data.get('frequency_deviations', {})

                logger.debug(f"通道{self.channel_number}收到离群率数据: outlier_result={outlier_result}, frequency_deviations={frequency_deviations}")

                # 已移除离群率结果同步（功能已完全移除）

                # 如果接收到0值，直接跳过，等待后端发送正确数据
                if rs_value == 0.0 and rct_value == 0.0:
                    return  # 直接返回，不处理0值数据

                # 修复直接使用后端传来的判断结果，避免重复判断
                if 'is_pass' in progress_data and 'fail_items' in progress_data:
                    # 使用后端判断结果
                    is_pass = progress_data.get('is_pass', True)
                    fail_items = progress_data.get('fail_items', [])

                    # 修复从后端数据中提取档位信息
                    rs_grade = progress_data.get('rs_grade')
                    rct_grade = progress_data.get('rct_grade')

                    # 如果后端没有提供档位，则计算档位
                    if rs_grade is None or rct_grade is None:
                        rs_grade, rct_grade = self.test_result_manager.calculate_grades(rs_value, rct_value)


                    # 重复判断修复UI层只负责显示，不重复计算或判断

                    # 直接设置测试完成状态，不进行任何重复计算
                    self.set_test_completed(is_pass, rs_grade, rct_grade, fail_items)
                else:
                    # 修复如果后端没有传判断结果，等待后端数据或使用后端判断逻辑
                    logger.warning(f"🔧 [修复] 通道{self.channel_number} 后端未传判断结果，检查数据有效性")

                    # 修复检查是否有存储的正确值
                    stored_rs = getattr(self, 'current_rs', 0) or getattr(self, 'rs_value', 0)
                    stored_rct = getattr(self, 'current_rct', 0) or getattr(self, 'rct_value', 0)
                    stored_voltage = getattr(self, 'current_voltage', 0) or getattr(self, 'voltage', 0)

                    # 如果progress_data中的值为0，但存储的值有效，使用存储的值
                    # 单频点测试时Rct=0是正常的
                    if (rs_value <= 0 or rct_value < 0) and (stored_rs > 0 and stored_rct >= 0):
                        rs_value = stored_rs
                        rct_value = stored_rct
                        if voltage <= 0 and stored_voltage > 0:
                            voltage = stored_voltage

                    # 修复如果正在等待有效数据，且现在收到了有效数据，清除等待标志
                    # 单频点测试时Rct=0是正常的
                    if getattr(self, '_waiting_for_valid_data', False) and rs_value > 0 and rct_value >= 0:
                        self._waiting_for_valid_data = False

                    # 只有在所有值都无效且不在等待状态时才标记为异常
                    # 🔧 [单频点修复] 单频点测试时Rct=0是正常的，不应标记为异常
                    is_single_freq_test = (rct_value == 0.0 and rs_value > 0)
                    if (rs_value <= 0 or (rct_value < 0)) and not getattr(self, '_waiting_for_valid_data', False) and not is_single_freq_test:
                        # 🎯 取样测试模式：即使数据无效也不显示异常，保持空白
                        if hasattr(self, 'config_manager'):
                            sampling_test = self.config_manager.get('test.sampling_test', False)
                            if sampling_test:
                                logger.info(f"🎯 通道{self.channel_number}取样测试模式：数据无效但不显示异常，保持空白")
                                return

                        logger.error(f"🔧 [修复] 通道{self.channel_number} Rs/Rct值无效: Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")
                        # 标记为测试异常
                        self._set_test_exception("数据计算失败", f"Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")
                        return
                    else:
                        # 修复Rs/Rct值正常但缺少判断结果，使用后端测试结果管理器进行判断
                        logger.warning(f"🔧 [修复] 通道{self.channel_number} Rs/Rct值正常但缺少判断结果，使用后端判断逻辑")

                        # 计算档位
                        rs_grade, rct_grade = self.test_result_manager.calculate_grades(rs_value, rct_value)

                        # Jack要求：完全禁用UI层的判断逻辑，测试结果由数据库保存后直接传递
                        logger.info(f"🚫 [禁用UI判断] 通道{self.channel_number} UI层判断已禁用，等待数据库保存后直接传递结果")
                        # 不再进行任何判断，测试结果将由test_result_manager保存数据库后直接传递给UI
                        return

                # 修复频率显示为完成状态使用正确的频点信息
                if frequency > 0:
                    # 从进度数据中获取频点信息
                    current_index = progress_data.get('current_frequency_index', 20)  # 默认最后一个频点
                    total_count = progress_data.get('total_frequency_count', 20)

                    logger.debug(f"通道{self.channel_number}测试完成频点显示: {frequency}Hz ({current_index}/{total_count}) completed")
                    # 更新频点进度标签（测试完成）
                    if hasattr(self, 'frequency_progress_label') and self.frequency_progress_label:
                        self.frequency_progress_label.setText(f"频点: {current_index}/{total_count}")

            elif state == 'sampling_completed':
                # 关键修复处理取样测试完成状态
                logger.info(f"🎯 通道{self.channel_number}收到取样测试完成信号")

                # 停止计时器
                if self.is_testing():
                    self.set_testing_state(False)
                    logger.debug(f"通道{self.channel_number}取样测试完成，停止计时器")

                # 调用取样测试完成方法，设置结束时间并发射信号
                # 单频点测试时Rct=0是正常的
                if rs_value > 0 and rct_value >= 0:
                    self.set_test_completed_for_sampling(voltage, rs_value, rct_value)
                    logger.info(f"🎯 通道{self.channel_number}取样测试完成处理成功")
                else:
                    logger.warning(f"🎯 通道{self.channel_number}取样测试完成但数据无效: Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")

            elif state == 'failed':
                # 修复测试失败时也要停止计时器
                if self.is_testing():
                    self.set_testing_state(False)
                    logger.debug(f"通道{self.channel_number}测试失败，停止计时器")

                # 测试失败
                fail_reason = progress_data.get('fail_reason', '测试失败')
                self.set_test_result("测试失败", False, None, None, [fail_reason])
            elif state == 'frequency_error':
                # 新增处理频点错误状态
                if self.is_testing():
                    self.set_testing_state(False)
                    logger.debug(f"通道{self.channel_number}频点错误，停止计时器")

                # 频点错误
                error_message = progress_data.get('message', '频点出错')
                failed_frequencies = progress_data.get('failed_frequencies', [])
                self.set_exception_state('frequency_error', error_message, 0.0)
                logger.warning(f"通道{self.channel_number}频点错误: {error_message}, 失败频点: {failed_frequencies}")
            elif state == 'skipped':
                # 新增处理跳过测试状态
                if self.is_testing():
                    self.set_testing_state(False)
                    logger.debug(f"通道{self.channel_number}跳过测试，停止计时器")

                # 设置跳过测试状态
                self.set_test_state("skipped")
                logger.debug(f"通道{self.channel_number}设置为跳过测试状态")

            elif state == 'reset':
                # 新增处理重置状态
                if self.is_testing():
                    self.set_testing_state(False)
                    logger.debug(f"通道{self.channel_number}重置状态，停止计时器")

                # 重置通道状态
                self.reset_test_data()
                logger.debug(f"通道{self.channel_number}重置测试数据")

            elif state == 'voltage_update':
                # 新增处理电压更新状态
                if voltage > 0:
                    self.update_test_data(voltage, rs_value, rct_value, progress)
                    logger.debug(f"通道{self.channel_number}电压更新: {voltage:.3f}V")

            else:
                # 其他状态，仅更新数据
                if voltage > 0 or rs_value > 0 or rct_value > 0:
                    self.update_test_data(voltage, rs_value, rct_value, progress)

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新测试进度失败: {e}")

    def _check_delayed_data_completion(self):
        """检查延迟的数据完成情况"""
        try:
            # 检查是否还在等待有效数据
            if not getattr(self, '_waiting_for_valid_data', False):
                return

            # 检查是否现在有有效数据了
            stored_rs = getattr(self, 'current_rs', 0) or getattr(self, 'rs_value', 0)
            stored_rct = getattr(self, 'current_rct', 0) or getattr(self, 'rct_value', 0)
            stored_voltage = getattr(self, 'current_voltage', 0) or getattr(self, 'voltage', 0)

            if stored_rs > 0 and stored_rct >= 0:  # 允许单频点测试Rct=0
                # 清除等待标志
                self._waiting_for_valid_data = False
                # 更新最终数据
                self.update_test_data(stored_voltage, stored_rs, stored_rct, 100)
            else:
                # 🎯 取样测试模式：即使延迟检查无效数据也不显示异常，保持空白
                if hasattr(self, 'config_manager'):
                    sampling_test = self.config_manager.get('test.sampling_test', False)
                    if sampling_test:
                        logger.info(f"🎯 通道{self.channel_number}取样测试模式：延迟检查无效数据但不显示异常，保持空白")
                        # 清除等待标志
                        self._waiting_for_valid_data = False
                        return

                # 修复红色异常问题不再设置异常状态，避免红色异常误判
                logger.debug(f" 通道{self.channel_number}延迟检查仍无有效数据，但跳过异常设置: Rs={stored_rs:.3f}mΩ, Rct={stored_rct:.3f}mΩ")
                # 清除等待标志
                self._waiting_for_valid_data = False
                # 不设置异常状态，等待真正的测试完成数据

        except Exception as e:
            logger.error(f"通道{self.channel_number}延迟数据检查失败: {e}")

    def _check_delayed_data_completion_backup(self):
        """
        备用延迟数据完成检查
        如果第一次延迟检查失败，这是第二次机会
        """
        try:
            # 如果已经不在等待状态，说明数据已经到达，直接返回
            if not getattr(self, '_waiting_for_valid_data', False):
                return

            # 检查是否现在有有效数据了
            stored_rs = getattr(self, 'current_rs', 0) or getattr(self, 'rs_value', 0)
            stored_rct = getattr(self, 'current_rct', 0) or getattr(self, 'rct_value', 0)
            stored_voltage = getattr(self, 'current_voltage', 0) or getattr(self, 'voltage', 0)

            if stored_rs > 0 and stored_rct >= 0:  # 允许单频点测试Rct=0
                logger.debug(f" 通道{self.channel_number}备用检查发现有效数据: Rs={stored_rs:.3f}mΩ, Rct={stored_rct:.3f}mΩ")
                # 清除等待标志
                self._waiting_for_valid_data = False
                # 更新最终数据
                self.update_test_data(stored_voltage, stored_rs, stored_rct, 100)
            else:
                logger.warning(f"🔧 通道{self.channel_number}备用检查仍无有效数据，但不设置异常状态，继续等待")
                # 不设置异常状态，给后端更多时间

        except Exception as e:
            logger.error(f"通道{self.channel_number}备用延迟数据检查失败: {e}")

    def _check_delayed_judgment_completion(self, voltage: float, rs_value: float, rct_value: float):
        """检查延迟的判断完成情况"""
        try:

            # 再次尝试使用后端判断逻辑
            try:
                is_pass, fail_items = self.test_result_manager.judge_test_result(
                    voltage, rs_value, rct_value, channel_num=self.channel_number
                )
                rs_grade, rct_grade = self.test_result_manager.calculate_grades(rs_value, rct_value)

                self.set_test_completed(is_pass, rs_grade, rct_grade, fail_items)

            except Exception as e:
                # 🎯 取样测试模式：即使延迟判断失败也不显示异常，保持空白
                if hasattr(self, 'config_manager'):
                    sampling_test = self.config_manager.get('test.sampling_test', False)
                    if sampling_test:
                        logger.info(f"🎯 通道{self.channel_number}取样测试模式：延迟判断失败但不显示异常，保持空白")
                        return

                logger.error(f"🔧 通道{self.channel_number}延迟判断仍然失败: {e}")
                # 最后的备用方案：标记为异常
                self._set_test_exception("判断逻辑失败", f"Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")

        except Exception as e:
            logger.error(f"通道{self.channel_number}延迟判断完成检查失败: {e}")

    def _safe_update_ui_data(self, voltage: float, rs: float, rct: float, progress: int):
        """
        安全的UI数据更新方法 - Jack的简化版本

        Args:
            voltage: 电压值 (V)
            rs: Rs值 (mΩ)
            rct: Rct值 (mΩ) - 总极化阻抗，包含原Rsei+Rct
            progress: 测试进度 (0-100)
        """
        try:
            # 修复确保进度值在有效范围内，使用传入的实时进度值
            safe_progress = max(0, min(100, progress))

            # 第二阶段集成：优先使用UI更新器
            if hasattr(self, 'ui_updater') and self.ui_updater:
                # 使用UI更新器批量更新
                success = True
                success &= self.ui_updater.update_voltage_display(voltage)
                success &= self.ui_updater.update_impedance_display(rs, rct)
                success &= self.ui_updater.update_progress_display(safe_progress)

                if success:
                    logger.debug(f"通道{self.channel_number}UI数据更新完成(使用UI更新器): V={voltage:.3f}, Rs={rs:.3f}, Rct={rct:.3f}, 进度={safe_progress}%")
                    return
                else:
                    logger.warning(f"通道{self.channel_number}UI更新器更新失败，回退到直接更新")

            # 回退到直接更新UI元素
            # 更新电压显示
            if hasattr(self, 'voltage_label') and self.voltage_label is not None:
                self.voltage_label.setText(f"{voltage:.3f}")

            # 更新Rs显示
            if hasattr(self, 'rs_label') and self.rs_label is not None:
                self.rs_label.setText(f"{rs:.3f}")

            # 更新Rct显示
            if hasattr(self, 'rct_label') and self.rct_label is not None:
                self.rct_label.setText(f"{rct:.3f}")

            # Jack要求移除Rsei显示，界面只显示Rs和Rct
            # if hasattr(self, 'rsei_label') and self.rsei_label is not None:
            # self.rsei_label.setText("--")  # 不再显示Rsei

            # 保持移除继续隐藏阻抗比更新逻辑
            # if hasattr(self, 'impedance_ratio_label') and self.impedance_ratio_label is not None:
            # if rs > 0:
            # rp_value = rsei + rct
            # impedance_ratio = rp_value / rs
            # self.impedance_ratio_label.setText(f"{impedance_ratio:.3f}")
            # else:
            # self.impedance_ratio_label.setText("--")

            # 更新进度条 - 使用安全的进度值
            if hasattr(self, 'progress_bar') and self.progress_bar is not None:
                self.progress_bar.setValue(safe_progress)

            logger.debug(f"通道{self.channel_number}UI数据更新完成(直接更新): V={voltage:.3f}, Rs={rs:.3f}, Rct={rct:.3f}, 进度={safe_progress}%")

        except Exception as e:
            logger.debug(f"通道{self.channel_number}UI数据更新异常: {e}")










    def set_channel_enabled(self, enabled: bool):
        """
        设置通道使能状态 - 修复通道状态显示问题

        Args:
            enabled: 是否启用通道
        """
        try:
            self.is_enabled = enabled

            if enabled:
                # 恢复正常状态
                if self.test_state == "disabled":
                    self.test_state = "idle"
                    self.set_test_state("idle")
            else:
                # 设置为禁用状态
                self.test_state = "disabled"
                self.set_test_state("disabled")

            logger.debug(f"通道{self.channel_number}使能状态更新: {'启用' if enabled else '禁用'}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}设置使能状态失败: {e}")

    def set_channel_status_error(self, status_code: int, description: str, severity: str = "error"):
        """
        设置通道状态码异常

        Args:
            status_code: 状态码
            description: 状态描述
            severity: 严重程度 ("error", "warning", "critical")
        """
        try:
            # 根据状态码设置对应的状态
            if status_code == 0x0003:  # 电池电压低或未安装
                self.set_test_state("battery_error")
                self.grade_label.setText("电池异常")
                self.grade_label.setObjectName("gradeBatteryError")
            elif status_code == 0x0005:  # 硬件错误/ADC错误
                self.set_test_state("hardware_error")
                self.grade_label.setText("硬件异常")
                self.grade_label.setObjectName("gradeHardwareError")
            elif status_code == 0x0004:  # 设置错误
                self.set_test_state("channel_error")
                self.grade_label.setText("设置异常")
                self.grade_label.setObjectName("gradeChannelError")
            elif status_code == 0x0002:  # 平衡功能运行中
                self.set_test_state("skipped")
                self.grade_label.setText("平衡中")
                self.grade_label.setObjectName("gradeSkipped")
            else:
                self.set_test_state("channel_error")
                self.grade_label.setText("状态异常")
                self.grade_label.setObjectName("gradeChannelError")

            # 清除测试数据
            self.voltage = 0.0
            self.rs_value = 0.0
            self.rct_value = 0.0
            self.test_progress = 0

            # 更新显示
            self.voltage_label.setText("0.000V")
            self.rs_label.setText("0.000mΩ")
            self.rct_label.setText("0.000mΩ")
            self.progress_bar.setValue(0)

            # 重新应用样式
            self.result_label.setStyleSheet("")
            self.grade_label.setStyleSheet("")

            logger.warning(f"通道{self.channel_number}状态异常: 0x{status_code:04X} - {description}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}设置状态异常失败: {e}")

    def clear_channel_error(self):
        """清除通道错误状态"""
        try:
            if self.test_state in ["channel_error", "battery_error", "hardware_error", "skipped"]:
                if self.is_enabled:
                    self.set_test_state("idle")
                else:
                    self.set_test_state("disabled")

                logger.debug(f"通道{self.channel_number}错误状态已清除")

        except Exception as e:
            logger.error(f"通道{self.channel_number}清除错误状态失败: {e}")



    def set_test_state(self, state: str):
        """
        设置测试状态 - 修复通道状态显示问题

        Args:
            state: 测试状态 (idle, testing, completed, failed, disabled, channel_error, battery_error, hardware_error, skipped)
        """
        try:
            self.test_state = state

            # 根据状态更新结果标签显示
            if state == "idle":
                if self.is_enabled:
                    self.result_label.setText("等待测试")
                    self.result_label.setObjectName("resultWaiting")
                else:
                    self.result_label.setText("未启用")
                    self.result_label.setObjectName("resultDisabled")
            elif state == "testing":
                self.result_label.setText("测试中")
                self.result_label.setObjectName("resultTesting")
            elif state == "completed":
                # 修复保持现有的测试结果显示，不清除
                # 在completed状态下，测试结果应该持续显示直到下次测试开始
                logger.debug(f"通道{self.channel_number}保持completed状态，测试结果继续显示")
                pass
            elif state == "failed":
                self.result_label.setText("测试失败")
                self.result_label.setObjectName("resultFailed")
            elif state == "disabled":
                self.result_label.setText("未启用")
                self.result_label.setObjectName("resultDisabled")
            elif state == "channel_error":
                self.result_label.setText("通道异常")
                self.result_label.setObjectName("resultChannelError")
            elif state == "battery_error":
                self.result_label.setText("电池异常")
                self.result_label.setObjectName("resultBatteryError")
            elif state == "hardware_error":
                self.result_label.setText("硬件异常")
                self.result_label.setObjectName("resultHardwareError")
            elif state == "skipped":
                self.result_label.setText("跳过测试")
                self.result_label.setObjectName("resultSkipped")

            # 更新样式
            self._update_result_label_style()

            logger.debug(f"通道{self.channel_number}测试状态更新: {state}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}设置测试状态失败: {e}")

    def _update_result_label_style(self):
        """更新结果标签样式"""
        try:
            # 根据对象名称应用不同样式
            object_name = self.result_label.objectName()

            if object_name == "resultWaiting":
                style = "background-color: #f8f9fa; color: #6c757d; border: 1px solid #dee2e6;"
            elif object_name == "resultTesting":
                style = "background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7;"
            elif object_name == "resultDisabled":
                style = "background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;"
            elif object_name == "resultFailed":
                style = "background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;"
            else:
                # 保持现有样式
                return

            self.result_label.setStyleSheet(f"""
                font-size: 32pt;  /* 统一字体：11pt→32pt，与等待测试状态一致 */
                font-weight: 900;  /* 统一字重：bold→900，与等待测试状态一致 */
                border-radius: 8px;  /* 统一圆角：4px→8px，与等待测试状态一致 */
                padding: 8px;  /* 统一内边距：4px 8px→8px，与等待测试状态一致 */
                text-align: center;
                min-height: 80px;  /* 统一高度：与等待测试状态一致 */
                max-height: 80px;
                {style}
            """)

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新结果标签样式失败: {e}")

    def _update_grade_label_style(self, object_name: str):
        """
        更新档位标签样式，确保字体大小与结果标签一致

        Args:
            object_name: 样式对象名
        """
        try:
            # 根据对象名设置样式
            if object_name == "gradePass":
                style = "background-color: #d5f4e6; color: #27ae60; border: 1px solid #27ae60;"
            elif object_name == "gradeFail":
                style = "background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;"
            elif object_name == "gradeDisplay":
                style = "background-color: #f0f9ff; color: #0c4a6e; border: 1px solid #0ea5e9;"
            else:
                # 默认样式
                style = "background-color: #f0f9ff; color: #0c4a6e; border: 1px solid #0ea5e9;"

            # 修复设置与结果标签相同的字体大小（32pt）
            self.grade_label.setStyleSheet(f"""
                font-size: 32pt;  /* 统一字体：24pt→32pt，与测试结果状态一致 */
                font-weight: 900;  /* 统一字重：bold→900，与测试结果状态一致 */
                border-radius: 8px;  /* 统一圆角：4px→8px，与测试结果状态一致 */
                padding: 8px;  /* 统一内边距：4px 8px→8px，与测试结果状态一致 */
                text-align: center;
                min-height: 80px;  /* 统一高度：与测试结果状态一致 */
                max-height: 80px;
                {style}
            """)

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新档位标签样式失败: {e}")

    def set_test_result(self, result: str, is_pass: bool = True, rs_grade: Optional[int] = None, rct_grade: Optional[int] = None, fail_items: Optional[list] = None):
        """
        设置测试结果

        Args:
            result: 测试结果文本
            is_pass: 是否合格
            rs_grade: Rs档位（可选）
            rct_grade: Rct档位（可选）
            fail_items: 不合格项目列表（可选）
        """
        try:
            # 修复防止重复设置测试结果，但允许数据更完整的调用覆盖不完整的调用
            if hasattr(self, '_test_result_set') and self._test_result_set:
                # 检查当前调用是否有更完整的数据
                current_has_fail_items = fail_items and len(fail_items) > 0
                current_has_complete_data = (self.rs_value > 0 or self.rct_value > 0) and current_has_fail_items

                # 如果当前调用没有更完整的数据，则跳过
                if not current_has_complete_data:
                    logger.debug(f"通道{self.channel_number}测试结果已设置且当前数据不完整，跳过重复设置")
                    return
                else:
                    # 重置标记，允许设置更完整的结果
                    self._test_result_set = False

            # 独立计时逻辑: 测试完成时停止计时
            test_duration = None
            if self.test_start_time and not self.test_end_time:
                self.test_end_time = datetime.now()
                test_duration = self.test_end_time - self.test_start_time
                logger.info(f"通道{self.channel_number}测试用时: {test_duration.total_seconds():.1f}秒")
            elif self.test_start_time and self.test_end_time:
                # 如果已经有结束时间，计算持续时间
                test_duration = self.test_end_time - self.test_start_time

            # 修正显示逻辑左侧显示档位/状态，右侧显示测试结果
            if is_pass:
                # 合格时：左侧显示档位，右侧显示"合格"
                if rs_grade is not None and rct_grade is not None:
                    grade_text = f"{rs_grade}-{rct_grade}"
                    # 🐛 修复：添加档位来源调试日志
                    logger.debug(f"🔍 [档位调试] 通道{self.channel_number} 使用传入档位: Rs={rs_grade}, Rct={rct_grade}")
                else:
                    # 🐛 修复：UI不应该重复计算档位，应该使用后端传递的数据
                    logger.warning(f"⚠️ [档位警告] 通道{self.channel_number} 没有传入档位数据，这不应该发生!")
                    logger.warning(f"   当前Rs值: {getattr(self, 'rs_value', 'N/A')}")
                    logger.warning(f"   当前Rct值: {getattr(self, 'rct_value', 'N/A')}")
                    # 使用默认档位而不是重新计算
                    rs_grade, rct_grade = 1, 1
                    grade_text = f"{rs_grade}-{rct_grade}"
                    logger.warning(f"   使用默认档位: {grade_text}")

                # 第二阶段集成：使用UI更新器更新结果显示
                if hasattr(self, 'ui_updater') and self.ui_updater:
                    self.ui_updater.update_grade_display(grade_text, "gradeDisplay")
                    self.ui_updater.update_result_display("合格", "resultPass")
                else:
                    # 回退到直接更新
                    self.grade_label.setText(grade_text)
                    self.result_label.setText("合格")  # 右侧固定显示"合格"
                    self.result_label.setObjectName("resultPass")
            else:
                # 不合格时：左侧显示"不合格"，右侧显示失败原因
                rs_grade, rct_grade = None, None  # 不合格电池不分档位

                # 右侧显示详细的不合格原因
                if fail_items:
                    result_text, result_style = self._get_fail_result_display(fail_items)
                else:
                    result_text = "不合格"
                    result_style = "resultFail"

                # 第二阶段集成：使用UI更新器更新结果显示
                if hasattr(self, 'ui_updater') and self.ui_updater:
                    self.ui_updater.update_grade_display("不合格", "gradeDisplay")
                    self.ui_updater.update_result_display(result_text, result_style)
                else:
                    # 回退到直接更新
                    self.grade_label.setText("不合格")
                    self.result_label.setText(result_text)
                    self.result_label.setObjectName(result_style)

            # 重新应用样式
            if hasattr(self, 'result_label'):
                self.result_label.setStyleSheet("")

            # 修复获取实际显示的文本用于日志和数据存储
            actual_grade_text = self.grade_label.text()
            actual_result_text = self.result_label.text()

            # 修复确保test_result包含正确的字段名，同时兼容新旧字段名
            # 修复确保使用最新的测试数据值
            current_voltage = getattr(self, 'voltage', voltage if 'voltage' in locals() else 0.0)
            current_rs = getattr(self, 'rs_value', 0.0)
            current_rct = getattr(self, 'rct_value', 0.0)

            # 修复如果当前值为0，尝试从其他属性获取
            if current_rs == 0.0:
                current_rs = getattr(self, 'current_rs', 0.0)
            if current_rct == 0.0:
                current_rct = getattr(self, 'current_rct', 0.0)


            self.test_result = {
                'result': actual_result_text,
                'is_pass': is_pass,
                'voltage': current_voltage,
                'rs': current_rs,  # 保持原有字段名
                'rct': current_rct,  # 保持原有字段名
                'rs_value': current_rs,  # 修复兼容打印模块的字段名
                'rct_value': current_rct,  # 修复兼容打印模块的字段名
                'rs_grade': rs_grade,
                'rct_grade': rct_grade,
                'fail_items': fail_items or [],
                'battery_code': self.battery_code,
                'channel_number': self.channel_number,  # 新增通道号
                'test_time': datetime.now().isoformat() if self.test_start_time else None,
                'test_duration': test_duration.total_seconds() if test_duration else None,
                # 修复离群率相关数据
                'outlier_result': getattr(self, 'outlier_rate_result', '--'),
                'outlier_rate': getattr(self, 'outlier_rate_result', '--'),  # 兼容字段名
                'frequency_deviations': getattr(self, 'frequency_deviations', {}),
                'max_deviation_percent': getattr(self, 'max_deviation_percent', 0.0),
                'baseline_filename': getattr(self, 'baseline_filename', ''),
                'baseline_id': getattr(self, 'baseline_id', None)
            }

            # 设置进度为100%（第二阶段集成：使用UI更新器）
            if hasattr(self, 'ui_updater') and self.ui_updater:
                self.ui_updater.update_progress_display(100)
            else:
                self.progress_bar.setValue(100)

            # 启用扫码按钮（如果存在）
            if hasattr(self, 'scan_button'):
                self.scan_button.setEnabled(True)

            # 修复只增加一次测试计数
            if not hasattr(self, '_test_count_incremented') or not self._test_count_incremented:
                self.increment_test_count()
                self._test_count_incremented = True

            # 修复只发送一次测试完成信号
            if not hasattr(self, '_test_completed_emitted') or not self._test_completed_emitted:
                self.test_completed.emit(self.channel_number, self.test_result)
                self._test_completed_emitted = True

            # 修复只有在数据完整时才标记测试结果已设置
            has_complete_data = (self.rs_value > 0 or self.rct_value > 0) and (is_pass or (fail_items and len(fail_items) > 0))
            if has_complete_data:
                self._test_result_set = True
            else:
                logger.debug(f"通道{self.channel_number}测试数据不完整，等待更多数据")

            logger.info(f"通道{self.channel_number}测试完成: 档位{actual_grade_text}, 结果{actual_result_text}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}设置测试结果失败: {e}")

    def get_test_result(self) -> dict:
        """
        获取测试结果

        Returns:
            测试结果字典，如果没有结果则返回空字典
        """
        if self.test_result and hasattr(self.test_result, '__dict__'):
            return self.test_result.__dict__.copy()
        return {}

    def is_testing(self) -> bool:
        """
        检查是否正在测试

        Returns:
            是否正在测试
        """
        # 独立计时逻辑: 只有开始时间存在且结束时间不存在时才算正在测试
        return self.test_start_time is not None and self.test_end_time is None

    def reset(self):
        """重置通道状态"""
        # 新增首先强制重置状态管理器
        if hasattr(self, 'state_manager') and self.state_manager:
            from .channel_state_manager import TestState
            self.state_manager.set_test_state(TestState.IDLE, "通道重置")
            logger.info(f"✅ 通道{self.channel_number}状态管理器已强制重置为IDLE")

        # 新增强制停止计时器
        if hasattr(self, 'timer_manager') and self.timer_manager:
            self.timer_manager.stop_timer()
            self.timer_manager.reset_timer()
            logger.info(f"✅ 通道{self.channel_number}计时器已强制停止")

        self.stop_test(clear_results=True)  # 强制清除结果
        self.battery_code_edit.clear()
        self.voltage_label.setText("0.000")
        self.rs_label.setText("0.000")
        self.rct_label.setText("0.000")

        # 🎯 使用统一显示管理器重置（按照第一次运行时的标准模式）
        from utils.unified_display_manager import reset_channel_display_unified

        success = reset_channel_display_unified(self.grade_label, self.result_label)
        if success:
            logger.debug(f"✅ 通道{self.channel_number}使用统一显示管理器重置成功")
        else:
            logger.warning(f"⚠️ 通道{self.channel_number}统一显示管理器重置失败，使用备用方案")
            # 备用方案：按照第一次运行时的标准模式
            self.grade_label.setText("--")
            self.grade_label.setObjectName("gradeDisplay")
            self.grade_label.setStyleSheet("")

            self.result_label.setText("待测试")
            self.result_label.setObjectName("resultWaiting")
            self.result_label.setStyleSheet("")

        self.test_time_label.setText("00:00:00")

        # 强制刷新UI
        self.result_label.update()
        self.grade_label.update()
        self.test_time_label.update()
        self.update()  # 强制刷新整个widget

        logger.info(f"✅ 通道{self.channel_number}状态已完全重置")
        # 频点显示功能已移除，跳过清空频点信息

    def clear_previous_results(self):
        """清除之前的测试结果（用于开始新测试时）"""
        try:
            # 清除之前的测试结果和时间
            self.test_result = None

            # 修复强制重置结果和档位显示状态
            self.result_label.setText("待测试")
            self.result_label.setObjectName("resultWaiting")
            self.result_label.setStyleSheet("")

            self.grade_label.setText("--")
            self.grade_label.setObjectName("")
            self.grade_label.setStyleSheet("")

            # 重置显示
            self.voltage_label.setText("0.000")
            self.rs_label.setText("0.000")
            self.rct_label.setText("0.000")

            # 修复强制重置进度条
            if hasattr(self, 'progress_bar') and self.progress_bar:
                self.progress_bar.setValue(0)

            # 修复重置防重复操作的标记，确保第二次测试时能正常更新UI
            if hasattr(self, '_test_count_incremented'):
                self._test_count_incremented = False
            if hasattr(self, '_test_completed_emitted'):
                self._test_completed_emitted = False
            if hasattr(self, '_test_result_set'):
                self._test_result_set = False

            logger.debug(f"通道{self.channel_number}清除之前的测试结果")

        except Exception as e:
            logger.error(f"通道{self.channel_number}清除之前结果失败: {e}")

    def reset_test_data(self):
        """重置测试数据（更全面的清理）"""
        try:
            # 🧹 全面清理：调用原有的清理方法
            self.clear_previous_results()

            # 🧹 基础清理：重置测试数据
            self.voltage = 0.0
            self.rs_value = 0.0
            self.rct_value = 0.0
            self.test_progress = 0

            # 🧹 基础清理：重置UI显示
            self.voltage_label.setText("0.000")
            self.rs_label.setText("0.000")
            self.rct_label.setText("0.000")
            self.progress_bar.setValue(0)

            # 🧹 额外清理：重置测试时间
            self.test_start_time = None
            self.test_end_time = None
            self.test_time_label.setText("00:00:00")

            # 🧹 额外清理：重置进度状态
            self.current_progress = 0
            self.max_progress_reached = 0
            self.test_progress = 0

            # 🧹 额外清理：重置状态管理器
            if hasattr(self, 'state_manager') and self.state_manager:
                if hasattr(self.state_manager, 'reset_state'):
                    self.state_manager.reset_state()
                if hasattr(self.state_manager, 'clear_error_state'):
                    self.state_manager.clear_error_state()

            # 🧹 额外清理：重置计时器
            if hasattr(self, 'timer_manager') and self.timer_manager:
                self.timer_manager.stop_timer()
                self.timer_manager.reset_timer()

            # 🧹 额外清理：清除频点信息（频点显示功能已移除）
            # 频点显示功能已移除，跳过清空频点信息

            # 已移除重置离群率（功能已完全移除）

            # 🧹 额外清理：清除数据缓存
            if hasattr(self, 'test_data_cache'):
                if hasattr(self.test_data_cache, 'clear'):
                    self.test_data_cache.clear()
                else:
                    self.test_data_cache = {}

            # 🧹 额外清理：重置计数器
            if hasattr(self, 'test_count'):
                pass  # 不重置测试计数，保持累计
            if hasattr(self, 'measurement_count'):
                self.measurement_count = 0

            # 🧹 额外清理：重置结果和档位显示
            self.result_label.setText("待测试")
            self.result_label.setObjectName("resultWaiting")
            self.result_label.setStyleSheet("")

            self.grade_label.setText("--")
            self.grade_label.setStyleSheet("")

            # 🧹 额外清理：重置进度条
            self.progress_bar.setValue(0)

            # 修复重置防重复操作的标记，确保第二次测试时能正常更新UI
            if hasattr(self, '_test_count_incremented'):
                self._test_count_incremented = False
                logger.debug(f"通道{self.channel_number}重置测试计数增量标记")

            if hasattr(self, '_test_completed_emitted'):
                self._test_completed_emitted = False
                logger.debug(f"通道{self.channel_number}重置测试完成信号标记")

            if hasattr(self, '_test_result_set'):
                self._test_result_set = False
                logger.debug(f"通道{self.channel_number}重置测试结果设置标记")

            # 修复重置测试完成标记，确保第二次测试时能正常接收后端判断结果
            if hasattr(self, '_test_completed'):
                self._test_completed = False
                logger.debug(f"通道{self.channel_number}重置测试完成标记")

            # 🧹 基础清理：重置结果显示状态
            if self.is_enabled:
                self.set_test_state("idle")
            else:
                self.set_test_state("disabled")

            logger.debug(f"通道{self.channel_number}重置测试数据完成")

        except Exception as e:
            logger.error(f"通道{self.channel_number}重置测试数据失败: {e}")

    def on_new_battery_detected(self):
        """检测到新电池时的处理（用于自动侦测模式）"""
        try:
            auto_detect = self.config_manager.get('test_config.auto_detect', True)
            if auto_detect:
                # 修复检测到新电池时不立即清除测试数据显示，只更新状态标签
                # 保留之前的测试数据显示，避免界面信息"消失"

                # 只更新结果状态，不清除测试数据
                self.result_label.setText("待测试")
                self.result_label.setObjectName("resultWaiting")
                self.result_label.setStyleSheet("")

                # 重置计时器显示
                self.test_time_label.setText("00:00:00")

                # 重置档位显示为待测试状态
                self.grade_label.setText("--")
                self.grade_label.setStyleSheet("")

                # 重置进度条
                if hasattr(self, 'progress_bar') and self.progress_bar:
                    self.progress_bar.setValue(0)

                logger.info(f"通道{self.channel_number}检测到新电池，状态已更新为待测试（保留之前数据显示）")

        except Exception as e:
            logger.error(f"通道{self.channel_number}新电池检测处理失败: {e}")

    def on_battery_removed(self):
        """电池移除时的处理（用于自动侦测模式）- 增强异常捕获"""
        try:

            auto_detect = self.config_manager.get('test_config.auto_detect', True)

            if auto_detect:
                # 自动侦测模式下，电池移除时显示移除状态
                if hasattr(self, 'result_label') and self.result_label:
                    self.result_label.setText("电池已移除")
                    self.result_label.setObjectName("resultRemoved")
                    self.result_label.setStyleSheet("")
                    logger.debug(f"✅ 通道{self.channel_number}结果标签更新完成")
                else:
                    logger.warning(f"⚠️ 通道{self.channel_number}结果标签不存在")

                # 重置进度条
                if hasattr(self, 'progress_bar') and self.progress_bar:
                    self.progress_bar.setValue(0)
                    logger.debug(f"✅ 通道{self.channel_number}进度条重置完成")

                # 停止计时器
                if hasattr(self, 'timer_manager') and self.timer_manager:
                    self.timer_manager.stop_timer()
                    logger.debug(f"✅ 通道{self.channel_number}计时器停止完成")

                logger.info(f"✅ 通道{self.channel_number}检测到电池移除，状态已更新")

        except Exception as e:
            logger.error(f"❌ 通道{self.channel_number}电池移除处理失败: {e}")
            logger.error(f"❌ 异常类型: {type(e).__name__}")
            logger.error(f"❌ 异常详情: {e}", exc_info=True)



    def _save_test_count(self):
        """保存测试计数（第三阶段重构：使用配置管理器）"""
        try:
            self.channel_config_manager.save_test_count(self.test_count)
            logger.debug(f"通道{self.channel_number}测试计数已保存: {self.test_count}")
        except Exception as e:
            logger.error(f"通道{self.channel_number}保存测试计数失败: {e}")

    def increment_test_count(self):
        """增加测试计数（第三阶段重构：使用配置管理器）"""
        try:
            self.test_count += 1
            self._save_test_count()
            self._update_test_count_display()
            logger.info(f"通道{self.channel_number}测试计数增加: {self.test_count}")
        except Exception as e:
            logger.error(f"通道{self.channel_number}增加测试计数失败: {e}")

    def reset_test_count(self):
        """重置测试计数（第三阶段重构：使用配置管理器）"""
        try:
            self.test_count = 0
            self._save_test_count()
            self._update_test_count_display()
            logger.info(f"通道{self.channel_number}测试计数已重置")
        except Exception as e:
            logger.error(f"通道{self.channel_number}重置测试计数失败: {e}")

    def _update_test_count_display(self):
        """更新测试计数显示"""
        try:
            if hasattr(self, 'test_count_label') and self.test_count_label is not None:
                self.test_count_label.setText(str(self.test_count))

                # 修复根据测试计数更新颜色
                self._update_test_count_color()

                # 修复强制刷新UI显示
                self.test_count_label.update()
                self.update()

                logger.debug(f"通道{self.channel_number}测试计数显示已更新: {self.test_count}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新测试计数显示失败: {e}")

    def _update_test_count_color(self):
        """
        根据测试计数更新颜色显示
        """
        try:
            if not hasattr(self, 'test_count_label') or self.test_count_label is None:
                return

            # 获取颜色阈值配置
            warning_threshold = self.config_manager.get('test_count.warning_threshold', 1000)
            max_lifetime = self.config_manager.get('test_count.max_lifetime', 2000)

            # 根据测试计数设置颜色
            if self.test_count >= max_lifetime:
                # 超过最大寿命 - 红色
                self.test_count_label.setStyleSheet("""
                    QLabel {
                        color: white;
                        background-color: #e74c3c;
                        border: 1px solid #c0392b;
                        border-radius: 3px;
                        padding: 2px 4px;
                        font-weight: bold;
                    }
                """)
            elif self.test_count >= warning_threshold:
                # 超过警告阈值 - 橙色
                self.test_count_label.setStyleSheet("""
                    QLabel {
                        color: white;
                        background-color: #f39c12;
                        border: 1px solid #e67e22;
                        border-radius: 3px;
                        padding: 2px 4px;
                        font-weight: bold;
                    }
                """)
            else:
                # 正常 - 绿色
                self.test_count_label.setStyleSheet("""
                    QLabel {
                        color: #27ae60;
                        font-weight: bold;
                        font-size: 11pt;  /* 字体优化：从10pt增加到11pt */
                    }
                """)

            logger.debug(f"通道{self.channel_number}测试计数颜色已更新: {self.test_count}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新测试计数颜色失败: {e}")

    def get_test_count(self) -> int:
        """
        获取测试计数

        Returns:
            测试计数
        """
        return self.test_count

    def update_test_count(self, count: int):
        """
        更新测试计数显示

        Args:
            count: 新的测试计数值
        """
        try:
            self.test_count = count
            self._update_test_count_display()
            logger.debug(f"通道{self.channel_number}测试计数已更新: {count}")
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新测试计数失败: {e}")

    def set_test_count(self, count: int):
        """
        设置测试计数（别名方法，与update_test_count功能相同）

        Args:
            count: 新的测试计数值
        """
        self.update_test_count(count)

    def set_enabled(self, enabled: bool):
        """
        设置通道启用状态

        Args:
            enabled: 是否启用
        """
        try:
            self.is_enabled = enabled
            self.update_enable_status(enabled)
            logger.debug(f"通道{self.channel_number}启用状态设置: {'启用' if enabled else '禁用'}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}设置启用状态失败: {e}")

    def update_enable_status(self, enabled: bool):
        """
        更新通道启用状态的视觉显示

        Args:
            enabled: 是否启用
        """
        try:
            # 更新通道标题的视觉状态
            if hasattr(self, 'channel_title'):
                if enabled:
                    self.channel_title.setStyleSheet("""
                        QLabel {
                            background-color: #3498db;
                            color: white;
                            font-size: 10pt;
                            font-weight: bold;
                            padding: 4px;
                            border-radius: 4px;
                            text-align: center;
                        }
                    """)
                else:
                    self.channel_title.setStyleSheet("""
                        QLabel {
                            background-color: #95a5a6;
                            color: #7f8c8d;
                            font-size: 10pt;
                            font-weight: bold;
                            padding: 4px;
                            border-radius: 4px;
                            text-align: center;
                        }
                    """)

            # 更新整个组件的启用状态
            self.setEnabled(enabled)

            # 如果禁用，清除测试状态
            if not enabled:
                self.test_state = "disabled"
                if hasattr(self, 'progress_bar'):
                    self.progress_bar.setValue(0)
                if hasattr(self, 'result_label'):
                    self.result_label.setText("禁用")
                    self.result_label.setStyleSheet("color: #95a5a6; font-weight: bold;")
            else:
                self.test_state = "idle"
                if hasattr(self, 'result_label'):
                    self.result_label.setText("等待测试")
                    self.result_label.setStyleSheet("color: #3498db; font-weight: bold;")

            logger.debug(f"通道{self.channel_number}视觉状态更新: {'启用' if enabled else '禁用'}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新视觉状态失败: {e}")

    def _get_grades_from_database(self) -> tuple:
        """
        从数据库获取最新的档位数据

        Returns:
            (rs_grade, rct_grade, is_pass) 或 (None, None, None) 如果没有数据
        """
        try:
            # 🐛 修复：直接创建数据库管理器，不依赖config_manager
            database_manager = getattr(self.config_manager, 'database_manager', None)
            if not database_manager:
                logger.debug(f"🔧 [档位获取] 通道{self.channel_number} config_manager中无database_manager，直接创建")
                from data.database_manager import DatabaseManager
                database_manager = DatabaseManager()
                logger.debug(f"✅ [档位获取] 通道{self.channel_number} 成功创建数据库管理器")

            # 获取该通道的最新测试结果
            test_results = database_manager.get_test_results(
                channel_number=self.channel_number,
                limit=1
            )

            if test_results and len(test_results) > 0:
                result = test_results[0]
                rs_grade = result.get('rs_grade')
                rct_grade = result.get('rct_grade')
                is_pass = result.get('is_pass', False)

                logger.debug(f"🔍 [档位获取] 通道{self.channel_number} 从数据库获取档位: Rs={rs_grade}, Rct={rct_grade}, 合格={is_pass}")
                return rs_grade, rct_grade, is_pass
            else:
                logger.debug(f"🔍 [档位获取] 通道{self.channel_number} 数据库中无测试结果")
                return None, None, None

        except Exception as e:
            logger.error(f"❌ [档位获取] 通道{self.channel_number} 从数据库获取档位失败: {e}")
            return None, None, None

    def refresh_display_from_database(self):
        """
        从数据库刷新通道显示数据（简化版 - 使用统一档位管理器）
        """
        try:
            logger.debug(f"🔄 [统一刷新] 通道{self.channel_number} 使用统一档位管理器刷新...")

            from utils.grade_manager import get_grade_manager
            grade_manager = get_grade_manager(self.config_manager)

            # 使用统一档位管理器更新显示
            success = grade_manager.update_channel_display(self.channel_number, self)

            if success:
                logger.info(f"✅ [统一刷新] 通道{self.channel_number} 显示刷新成功")
            else:
                logger.warning(f"⚠️ [统一刷新] 通道{self.channel_number} 显示刷新失败")

        except Exception as e:
            logger.error(f"❌ [统一刷新] 通道{self.channel_number} 刷新失败: {e}")

    def _update_grade_display(self, rs_grade: int, rct_grade: int, is_pass: bool):
        """
        更新档位显示

        Args:
            rs_grade: Rs档位
            rct_grade: Rct档位
            is_pass: 是否合格
        """
        try:
            # 🎯 使用统一显示管理器（按照第一次运行时的标准模式）
            from utils.unified_display_manager import set_channel_display_unified

            success = set_channel_display_unified(
                self.grade_label,
                self.result_label,
                is_pass,
                rs_grade,
                rct_grade
            )

            if success:
                if is_pass and rs_grade is not None and rct_grade is not None:
                    logger.debug(f"✅ [显示更新] 通道{self.channel_number} 档位显示: {rs_grade}-{rct_grade}")
                else:
                    logger.debug(f"✅ [显示更新] 通道{self.channel_number} 显示: 不合格")
            else:
                logger.warning(f"⚠️ [显示更新] 通道{self.channel_number} 统一显示管理器失败")

            # 刷新样式
            self.grade_label.setStyleSheet("")
            self.result_label.setStyleSheet("")
            self.grade_label.update()
            self.result_label.update()

        except Exception as e:
            logger.error(f"❌ [显示更新] 通道{self.channel_number} 更新档位显示失败: {e}")

    def _calculate_grades(self, rs_value: float, rct_value: float) -> tuple:
        """
        计算Rs和Rct档位（已完全弃用：UI不应该计算档位）

        Args:
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)

        Returns:
            (rs_grade, rct_grade) 档位编号
        """
        logger.error(f"❌ [已弃用] 通道{self.channel_number} UI不应该计算档位！")
        logger.error(f"   调用参数: Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")
        logger.error(f"   应该使用后端传递的档位数据，而不是UI层计算")

        # 🐛 修复：UI不再计算档位，返回错误标识
        return 0, 0  # 返回0表示错误，提醒开发者修复

    def _judge_test_result(self, voltage: float, rs_value: float, rct_value: float) -> tuple:
        """
        判定测试结果（已弃用：统一使用后端测试结果管理器）

        注意：此方法已弃用，请直接调用 test_result_manager.judge_test_result()
        """
        logger.warning(f"🔧 [重构] 通道{self.channel_number} 使用了已弃用的_judge_test_result方法，请直接调用后端管理器")
        try:
            # 统一使用后端测试结果管理器
            return self.test_result_manager.judge_test_result(voltage, rs_value, rct_value, channel_num=self.channel_number)
        except Exception as e:
            logger.error(f"通道{self.channel_number}判定测试结果失败: {e}")
            return False, ["系统错误"]

    def _get_fail_result_display(self, fail_items: Optional[list]) -> tuple:
        """
        根据失败项目获取结果显示文本和样式（统一使用后端失败原因管理器）

        注意：此方法保留UI显示逻辑，但失败项目判断应统一使用后端test_result_manager

        Args:
            fail_items: 失败项目列表，如 ["电压", "Rs", "Rct"]

        Returns:
            (result_text, result_style) 结果文本和样式名称
        """
        try:
            # 🔧 统一使用失败结果显示工具类
            return FailResultDisplayUtils.get_fail_result_display(fail_items)

        except Exception as e:
            logger.error(f"通道{self.channel_number}获取失败结果显示失败: {e}")
            return "不合格", "resultFail"

    def complete_test_with_judgment(self, voltage: float, rs_value: float, rct_value: float):
        """
        完成测试并自动判定结果（第三阶段重构：使用测试判定管理器）

        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)

        """
        try:
            # Jack要求移除Rsei相关逻辑
            # 修复获取Rsei值（如果没有传入的话）- 已移除
            # if rsei_value <= 0.0 and hasattr(self, 'test_result_manager'):
            #     try:
            #         rsei_value = self.test_result_manager.get_channel_rsei_value(self.channel_number)
            #         logger.debug(f"通道{self.channel_number}从测试结果管理器获取Rsei值: {rsei_value:.3f}mΩ")
            #     except Exception as e:
            #         logger.debug(f"通道{self.channel_number}获取Rsei值失败: {e}")
            #         rsei_value = 0.0

            # Jack要求更新UI显示，只包含Rs和Rct
            self.update_test_data(voltage, rs_value, rct_value, 100)

            # 🎯 取样测试模式：跳过判断逻辑
            if hasattr(self, 'config_manager'):
                sampling_test = self.config_manager.get('test.sampling_test', False)
                if sampling_test:
                    # 取样测试模式：不进行合格/不合格判断，直接设置为完成状态
                    logger.info(f"🎯 通道{self.channel_number}取样测试模式：跳过判断逻辑")

                    # 修复确保UI显示正确更新，强制更新阻抗显示
                    if hasattr(self, 'ui_updater') and self.ui_updater:
                        self.ui_updater.update_impedance_display(rs_value, rct_value, force_update=True)
                        logger.debug(f"🔧 通道{self.channel_number}强制更新UI阻抗显示: Rs={rs_value:.3f}, Rct={rct_value:.3f}")

                    # 设置为"测试完成"状态，不显示合格/不合格
                    self.set_test_completed_for_sampling(voltage, rs_value, rct_value)

                    logger.debug(f"通道{self.channel_number}取样测试完成: 电压={voltage:.3f}V, Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")
                    return

            # 正常测试模式：使用后端测试结果管理器进行判定
            is_pass, fail_items = self.test_result_manager.judge_test_result(voltage, rs_value, rct_value)

            # 使用后端测试结果管理器计算档位
            rs_grade, rct_grade = self.test_result_manager.calculate_grades(rs_value, rct_value)

            # 🐛 修复：添加档位计算调试日志
            logger.debug(f"🔍 [档位调试] 通道{self.channel_number} 档位计算结果:")
            logger.debug(f"   Rs值: {rs_value:.3f}mΩ → Rs档位: {rs_grade}")
            logger.debug(f"   Rct值: {rct_value:.3f}mΩ → Rct档位: {rct_grade}")

            # 设置测试完成状态（包含失败原因）
            self.set_test_completed(is_pass, rs_grade, rct_grade, fail_items)

            logger.debug(f"通道{self.channel_number}测试完成: {'合格' if is_pass else '不合格'}, 失败项目: {fail_items}")

        except ValueError as e:
            # 数据未准备好，跳过判断
            logger.info(f"通道{self.channel_number}数据未准备好，跳过第一次判断: {e}")
            return  # 直接返回，不进行任何处理
        except Exception as e:
            logger.error(f"通道{self.channel_number}完成测试判定失败: {e}")
            # 出错时设置为不合格
            self.set_test_completed(False, 1, 1, ["系统错误"])

    def complete_test_with_judgment_enhanced(self, voltage: float, rs_value: float, rct_value: float, outlier_result: Optional[str] = None):
        """
        Jack修复：禁用增强判断，避免多套算法冲突
        现在统一使用后端判断，不再执行增强判断逻辑

        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)
            outlier_result: 离群率检测结果
        """
        try:
            # Jack修复：完全禁用增强判断，避免与统一判断冲突
            logger.debug(f"🚫 [禁用增强判断] 通道{self.channel_number} 增强判断已禁用，使用统一后端判断")
            return  # 直接返回，不执行任何增强判断逻辑

            # 以下代码已禁用，保留用于参考
            logger.info(f"通道{self.channel_number}开始增强判定: V={voltage:.3f}V, Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ, 离群率={outlier_result}")

            # 检查数据有效性，避免使用0值进行判断
            if rs_value == 0.0 and rct_value == 0.0:
                logger.warning(f"通道{self.channel_number} 检测到Rs和Rct为0，数据未准备好，跳过判断")
                return

            # 保存Rs/Rct值到实例属性，确保统计能获取到正确的值
            self.rs_value = rs_value
            self.rct_value = rct_value
            self.voltage = voltage

            # 🎯 取样测试模式：跳过判断逻辑
            if hasattr(self, 'config_manager'):
                sampling_test = self.config_manager.get('test.sampling_test', False)
                if sampling_test:
                    # 取样测试模式：不进行合格/不合格判断，直接设置为完成状态
                    logger.info(f"🎯 通道{self.channel_number}取样测试模式：跳过增强判断逻辑")

                    # 设置为"测试完成"状态，不显示合格/不合格
                    self.set_test_completed_for_sampling(voltage, rs_value, rct_value)

                    logger.debug(f"通道{self.channel_number}取样测试完成: 电压={voltage:.3f}V, Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")
                    return

            # 修复使用后端test_result_manager进行基础判断，然后手动处理离群率
            try:
                # 先使用后端测试结果管理器进行基础判断（电压、Rs、Rct）
                is_pass, fail_items = self.test_result_manager.judge_test_result(voltage, rs_value, rct_value)

                # 🚫 离群检测功能已删除

                logger.info(f"通道{self.channel_number} UI增强判断完成: {'合格' if is_pass else '不合格'}, 失败项目: {fail_items}")
            except ValueError as e:
                # 数据未准备好，跳过判断
                logger.info(f"通道{self.channel_number}数据未准备好，跳过增强判断: {e}")
                return  # 直接返回，不进行任何处理

            # 修复删除重复的离群率检测代码，已在上面处理过了

            # 修复优先使用测试执行器传来的档位数据，如果没有则重新计算
            rs_grade = None
            rct_grade = None

            # 尝试从test_result中获取测试执行器传来的档位数据
            if hasattr(self, 'test_result') and self.test_result:
                try:
                    # 尝试字典方式访问
                    if hasattr(self.test_result, 'get'):
                        rs_grade = self.test_result.get('rs_grade')
                        rct_grade = self.test_result.get('rct_grade')
                    else:
                        # 尝试属性方式访问
                        rs_grade = getattr(self.test_result, 'rs_grade', None)
                        rct_grade = getattr(self.test_result, 'rct_grade', None)
                    logger.info(f"通道{self.channel_number} 使用测试执行器档位: Rs={rs_grade}, Rct={rct_grade}")
                except Exception as e:
                    logger.debug(f"通道{self.channel_number} 获取测试执行器档位失败: {e}")
                    rs_grade = None
                    rct_grade = None

            # 如果没有档位数据，则重新计算
            if rs_grade is None or rct_grade is None:
                rs_grade, rct_grade = self.test_result_manager.calculate_grades(rs_value, rct_value)
                logger.info(f"通道{self.channel_number} 重新计算档位: Rs={rs_grade}, Rct={rct_grade}")

            # 紧急修复立即设置测试完成状态，确保基本功能正常
            logger.info(f"通道{self.channel_number} 立即设置测试完成状态")
            self.set_test_completed(is_pass, rs_grade, rct_grade, fail_items)

            # 可选发送判断结果准备信号用于批量显示优化（作为增强功能）
            try:
                logger.debug(f"通道{self.channel_number} 发送判断结果准备信号")
                self.judgment_ready.emit(self.channel_number, is_pass, rs_grade, rct_grade, fail_items)
            except Exception as e:
                logger.debug(f"通道{self.channel_number} 发送批量显示信号失败: {e}")

            # 确保档位数据传递给统计系统
            self._send_statistics_data(is_pass, rs_grade, rct_grade)

            logger.info(f"通道{self.channel_number}增强判定完成: {'合格' if is_pass else '不合格'}, 档位: {rs_grade}-{rct_grade}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}增强判定失败: {e}")
            # 出错时设置为不合格
            self.set_test_completed(False, 1, 1, ["系统错误"])



    def _send_statistics_data(self, is_pass: bool, rs_grade: int, rct_grade: int):
        """
        直接发送统计数据给统计组件

        Args:
            is_pass: 是否合格
            rs_grade: Rs档位
            rct_grade: Rct档位
        """
        try:

            # 方法1：直接通过信号发送统计数据
            if hasattr(self, 'statistics_update_requested'):
                self.statistics_update_requested.emit(is_pass, rs_grade, rct_grade)

            # 方法2：尝试直接访问统计组件
            try:
                # 通过主窗口获取统计组件
                main_window = self.window()
                if hasattr(main_window, 'ui_component_manager') and main_window.ui_component_manager:
                    statistics = main_window.ui_component_manager.get_component('statistics')
                    if statistics and hasattr(statistics, 'add_test_result'):
                        statistics.add_test_result(is_pass, rs_grade, rct_grade)
                        return  # 成功后直接返回
                    else:
                        logger.warning(f"📊 [统计直传] 通道{self.channel_number} 统计组件未找到或无add_test_result方法")
                else:
                    logger.warning(f"📊 [统计直传] 通道{self.channel_number} 主窗口或UI管理器未找到")
            except Exception as e:
                logger.error(f"📊 [统计直传] 通道{self.channel_number} 直接访问统计组件失败: {e}")

            # 方法3：备用方案，通过父组件管理器发送
            if hasattr(self.parent(), 'parent') and hasattr(self.parent().parent(), 'update_test_progress'):
                progress_data = {
                    'state': 'completed',
                    'is_pass': is_pass,
                    'rs_grade': rs_grade,
                    'rct_grade': rct_grade,
                    'statistics_only': True,
                    'timestamp': datetime.now().timestamp()
                }
                self.parent().parent().update_test_progress(self.channel_number, progress_data)
            else:
                logger.error(f"📊 [统计直传] 通道{self.channel_number} 所有统计数据发送方法都失败")

        except Exception as e:
            logger.error(f"通道{self.channel_number}发送统计数据失败: {e}")
            import traceback
            traceback.print_exc()

    def _schedule_delayed_judgment(self, voltage: float, rs_value: float, rct_value: float, outlier_result: Optional[str] = None, backend_result: Optional[dict] = None):
        """
        Jack修复：禁用延迟判断，避免多套算法冲突
        现在统一使用后端判断，不再执行延迟判断逻辑

        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)
            outlier_result: 离群率检测结果
            backend_result: 后端判断结果 {'is_pass': bool, 'fail_items': list}
        """
        try:
            # Jack修复：完全禁用延迟判断，避免与统一判断冲突
            logger.debug(f"🚫 [禁用延迟判断] 通道{self.channel_number} 延迟判断已禁用，使用统一后端判断")
            return  # 直接返回，不执行任何延迟判断逻辑

            # 以下代码已禁用，保留用于参考
            # 重复判断修复优先使用后端判断结果，避免UI层重复判断
            if False and backend_result and ('is_pass' in backend_result or 'rs_grade' in backend_result):

                # 从后端结果获取档位，如果没有则计算
                rs_grade = backend_result.get('rs_grade')
                rct_grade = backend_result.get('rct_grade')

                if rs_grade is None or rct_grade is None:
                    rs_grade, rct_grade = self.test_result_manager.calculate_grades(rs_value, rct_value)

                # 如果有判断结果，直接设置测试完成状态
                if 'is_pass' in backend_result and 'fail_items' in backend_result:
                    self.set_test_completed(
                        backend_result['is_pass'],
                        rs_grade,
                        rct_grade,
                        backend_result['fail_items']
                    )
                    return  # 重复判断修复直接返回，不执行任何延迟判断

                # 重复判断修复如果后端没有提供完整判断结果，也不执行UI层判断
                # 而是使用基本的数据有效性检查
                logger.warning(f"🔧 [重复判断修复] 通道{self.channel_number} 后端未提供完整判断结果，使用基本检查")

                # 基本数据有效性检查
                data_valid = rs_value > 0 and rct_value > 0 and 2.0 <= voltage <= 5.0
                if data_valid:
                    # 数据有效，设为合格
                    self.set_test_completed(True, rs_grade, rct_grade, [])
                else:
                    # 数据无效，设为不合格
                    fail_items = []
                    if rs_value <= 0:
                        fail_items.append("Rs")
                    if rct_value <= 0:
                        fail_items.append("Rct")
                    if not (2.0 <= voltage <= 5.0):
                        fail_items.append("电压")

                    self.set_test_completed(False, rs_grade, rct_grade, fail_items)

                return  # 重复判断修复直接返回，不执行延迟判断

            # 重复判断修复如果没有后端判断结果，也不执行UI层判断
            # 而是使用基本的数据有效性检查作为兜底方案
            logger.warning(f"🔧 [重复判断修复] 通道{self.channel_number} 没有后端判断结果，使用基本数据检查")

            # 计算档位
            rs_grade, rct_grade = self.test_result_manager.calculate_grades(rs_value, rct_value)

            # 基本数据有效性检查
            # 🔧 [单频点修复] 单频点测试时Rct=0是正常的
            is_single_freq_test = (rct_value == 0.0 and rs_value > 0)
            data_valid = rs_value > 0 and (rct_value > 0 or is_single_freq_test) and 2.0 <= voltage <= 5.0
            if data_valid:
                # 数据有效，设为合格
                self.set_test_completed(True, rs_grade, rct_grade, [])
            else:
                # 数据无效，设为不合格
                fail_items = []
                if rs_value <= 0:
                    fail_items.append("Rs")
                # 🔧 [单频点修复] 单频点测试时Rct=0是正常的，不应标记为失败
                if rct_value < 0:  # 只有负数才是异常，0是单频点测试的正常值
                    fail_items.append("Rct")
                if not (2.0 <= voltage <= 5.0):
                    fail_items.append("电压")

                self.set_test_completed(False, rs_grade, rct_grade, fail_items)

        except Exception as e:
            # 🎯 取样测试模式：即使判断处理异常也不显示异常，保持空白
            if hasattr(self, 'config_manager'):
                sampling_test = self.config_manager.get('test.sampling_test', False)
                if sampling_test:
                    logger.info(f"🎯 通道{self.channel_number}取样测试模式：判断处理异常但不显示异常，保持空白")
                    return

            logger.error(f"通道{self.channel_number}处理判断失败: {e}")
            # 重复判断修复异常情况下也不执行UI层判断，而是设为异常状态
            self._set_test_exception("判断处理异常", str(e))

    def _execute_delayed_judgment(self):
        """
        执行延迟的判断（🔧 重复判断修复：已禁用，不再执行UI层判断）
        """
        try:
            # 重复判断修复延迟判断已被禁用，不再执行UI层判断

            # 清理判断数据
            if hasattr(self, '_pending_judgment_data'):
                delattr(self, '_pending_judgment_data')

        except Exception as e:
            logger.error(f"通道{self.channel_number}清理延迟判断数据失败: {e}")

    def _schedule_delayed_completion(self, is_pass: bool, rs_grade: int, rct_grade: int, fail_items: Optional[list] = None):
        """
        安排延迟完成显示，实现批量显示效果

        Args:
            is_pass: 是否合格
            rs_grade: Rs档位
            rct_grade: Rct档位
            fail_items: 失败项目列表
        """
        try:
            # 保存完成参数
            self._pending_completion_data = {
                'is_pass': is_pass,
                'rs_grade': rs_grade,
                'rct_grade': rct_grade,
                'fail_items': fail_items,
                'timestamp': time.time()
            }

            # 检查是否已经有延迟完成定时器
            if not hasattr(self, '_completion_timer') or not self._completion_timer.isActive():
                # 创建延迟完成定时器
                self._completion_timer = QTimer()
                self._completion_timer.setSingleShot(True)
                self._completion_timer.timeout.connect(self._execute_delayed_completion)

                # 设置延迟时间（500ms），让多个通道的完成请求能够聚集
                self._completion_timer.start(500)

                logger.debug(f"通道{self.channel_number} 安排延迟完成显示，500ms后执行")
            else:
                logger.debug(f"通道{self.channel_number} 延迟完成显示已安排，更新完成数据")

        except Exception as e:
            logger.error(f"通道{self.channel_number}安排延迟完成显示失败: {e}")
            # 如果延迟完成失败，立即执行完成显示
            self.set_test_completed(is_pass, rs_grade, rct_grade, fail_items)

    def _execute_delayed_completion(self):
        """
        执行延迟的完成显示
        """
        try:
            if hasattr(self, '_pending_completion_data'):
                completion_data = self._pending_completion_data
                logger.debug(f"通道{self.channel_number} 执行延迟完成显示")

                self.set_test_completed(
                    completion_data['is_pass'],
                    completion_data['rs_grade'],
                    completion_data['rct_grade'],
                    completion_data['fail_items']
                )

                # 清理完成数据
                delattr(self, '_pending_completion_data')
            else:
                logger.warning(f"通道{self.channel_number} 没有待执行的完成数据")

        except Exception as e:
            logger.error(f"通道{self.channel_number}执行延迟完成显示失败: {e}")

    def trigger_result_display(self, is_pass: bool, rs_grade: int, rct_grade: int, fail_items: Optional[list] = None):
        """
        由容器触发的结果显示方法

        Args:
            is_pass: 是否合格
            rs_grade: Rs档位
            rct_grade: Rct档位
            fail_items: 失败项目列表
        """
        try:
            logger.debug(f"通道{self.channel_number} 容器触发结果显示: {'合格' if is_pass else '不合格'}")
            self.set_test_completed(is_pass, rs_grade, rct_grade, fail_items)
        except Exception as e:
            logger.error(f"通道{self.channel_number}容器触发结果显示失败: {e}")

    def _init_capacity_prediction(self):
        """初始化容量预测功能"""
        try:
            # 检查是否启用容量预测功能
            if not self.config_manager.get('test.capacity_prediction_enabled', False):
                logger.debug(f"通道{self.channel_number}容量预测功能未启用")
                return

            # 初始化容量预测算法
            from backend.capacity_prediction_algorithm import CapacityPredictionAlgorithm
            self.capacity_prediction_algorithm = CapacityPredictionAlgorithm(self.config_manager)

            # 尝试加载已训练的模型
            model_path = self.config_manager.get('capacity_prediction.model_path', 'models/capacity_prediction_model.pkl')
            if self.capacity_prediction_algorithm.load_model(model_path):
                logger.info(f"通道{self.channel_number}容量预测模型加载成功")
            else:
                logger.debug(f"通道{self.channel_number}容量预测模型未找到，需要训练")

            # 初始化容量显示
            self._update_capacity_prediction_display("--")

            logger.debug(f"通道{self.channel_number}容量预测功能初始化完成")

        except Exception as e:
            logger.error(f"通道{self.channel_number}容量预测功能初始化失败: {e}")
            self.capacity_prediction_algorithm = None

    def _update_capacity_prediction_display(self, capacity_text: str):
        """🔧 已禁用：更新容量预测显示（用户要求暂时不用）"""
        try:
            # 移除不再更新容量预测显示，用户要求暂时不用
            logger.debug(f"通道{self.channel_number}容量预测显示已禁用: {capacity_text}")
            return

            # 原始代码已注释：
            # capacity_label = None
            # if hasattr(self, 'ui_layout_manager') and self.ui_layout_manager:
            # ui_elements = self.ui_layout_manager.get_all_ui_elements()
            # capacity_label = ui_elements.get('capacity_prediction_label')
            # if not capacity_label and hasattr(self, 'capacity_prediction_label'):
            # capacity_label = self.capacity_prediction_label
            # if capacity_label:
            # capacity_label.setText(capacity_text)

        except Exception as e:
            logger.debug(f"通道{self.channel_number}容量预测显示已禁用: {e}")

    def predict_capacity(self, voltage: float, rs_value: float, rct_value: float, rct_cv: float) -> Optional[float]:
        """
        预测电池容量（V0.80.08版本屏蔽）

        Args:
            voltage: 电压值
            rs_value: Rs值
            rct_value: Rct值
            rct_cv: Rct变异系数

        Returns:
            预测的容量值，如果预测失败返回None
        """
        try:
            # V0.80.08版本屏蔽容量预测功能
            capacity_config = self.config_manager.get('capacity_prediction', {})
            if capacity_config.get('feature_disabled', True):
                return None

            if not self.capacity_prediction_algorithm:
                return None

            # 获取电池类型
            battery_type = self.config_manager.get('product.battery_type', '磷酸铁锂')

            # 检查是否启用SOH预测
            soh_config = self.config_manager.get('soh_prediction', {})
            if soh_config.get('enable_soh_prediction', False):
                # 使用SOH算法预测
                soh_result = self.capacity_prediction_algorithm.predict_soh_and_capacity(
                    voltage, rs_value, rct_value, battery_type
                )

                if soh_result.get('success', False):
                    predicted_capacity = soh_result.get('predicted_capacity')
                    soh_percentage = soh_result.get('recommended_soh')

                    # 更新SOH显示
                    if soh_percentage is not None and soh_config.get('display_soh_percentage', True):
                        self._update_soh_display(soh_percentage)

                    if predicted_capacity is not None:
                        self.predicted_capacity = predicted_capacity
                        self._update_capacity_prediction_display_with_soh(predicted_capacity, soh_percentage)
                        logger.info(f"通道{self.channel_number}SOH预测: SOH={soh_percentage}%, 容量={predicted_capacity:.3f}AH")
                        return predicted_capacity

            # 使用传统算法预测
            predicted_capacity = self.capacity_prediction_algorithm.predict_capacity(
                voltage, rs_value, rct_value, rct_cv
            )

            if predicted_capacity is not None:
                self.predicted_capacity = predicted_capacity

                # 更新显示
                capacity_config = self.config_manager.get('capacity_prediction', {})
                unit = capacity_config.get('capacity_unit', 'AH')
                precision = capacity_config.get('display_precision', 3)

                if unit == 'mAH':
                    display_value = predicted_capacity * 1000
                    capacity_text = f"{display_value:.{precision}f}mAH"
                else:
                    capacity_text = f"{predicted_capacity:.{precision}f}AH"

                self._update_capacity_prediction_display(capacity_text)

                logger.info(f"通道{self.channel_number}容量预测: {capacity_text}")

            return predicted_capacity

        except Exception as e:
            logger.error(f"通道{self.channel_number}容量预测失败: {e}")
            return None

    def reset_test_state(self):
        """重置通道的测试状态和UI显示"""
        try:
            logger.info(f"🔄 通道{self.channel_number}重置测试状态")

            # 1. 重置进度条
            if hasattr(self, 'progress_bar') and self.progress_bar:
                self.progress_bar.setValue(0)
                self.progress_bar.setVisible(True)  # 修复保持进度条可见

            # 2. 重置结果显示为待测试状态
            if hasattr(self, 'result_label') and self.result_label:
                self.result_label.setText("待测试")
                self.result_label.setObjectName("resultWaiting")
                self.result_label.setStyleSheet("")  # 重新应用样式
                self.result_label.setVisible(True)  # 修复保持结果标签可见

            # 🎯 使用统一显示管理器重置档位显示（按照第一次运行时的标准模式）
            if hasattr(self, 'grade_label') and self.grade_label:
                from utils.unified_display_manager import reset_channel_display_unified

                success = reset_channel_display_unified(self.grade_label, self.result_label)
                if not success:
                    # 备用方案：按照第一次运行时的标准模式
                    self.grade_label.setText("--")
                    self.grade_label.setObjectName("gradeDisplay")
                    self.grade_label.setStyleSheet("")

                self.grade_label.setVisible(True)  # 修复保持档位标签可见

            # 4. 重置阻抗值显示（保持电压显示）
            if hasattr(self, 'rs_label') and self.rs_label:
                self.rs_label.setText("--")

            if hasattr(self, 'rct_label') and self.rct_label:
                self.rct_label.setText("--")



            # 5. 重置测试完成管理器状态
            if hasattr(self, 'test_completion_manager') and self.test_completion_manager:
                if hasattr(self.test_completion_manager, 'reset_completion_state'):
                    self.test_completion_manager.reset_completion_state()

            # 6. 重置内部状态标志
            self._is_testing = False
            self._test_completed = False

            # 7. 强制刷新UI显示
            if hasattr(self, 'result_label'):
                self.result_label.update()
            if hasattr(self, 'grade_label'):
                self.grade_label.update()
            if hasattr(self, 'progress_bar'):
                self.progress_bar.update()

            logger.debug(f"✅ 通道{self.channel_number}测试状态重置完成")

        except Exception as e:
            logger.error(f"通道{self.channel_number}重置测试状态失败: {e}")

    def reset_progress(self):
        """重置测试进度显示（轻量级重置）"""
        try:
            logger.debug(f"🔄 通道{self.channel_number}重置进度显示")

            # 只重置进度相关的UI元素，不影响测试结果显示
            if hasattr(self, 'progress_bar') and self.progress_bar:
                self.progress_bar.setValue(0)
                self.progress_bar.setVisible(True)  # 修复保持进度条可见

            # 重置内部测试状态
            self._is_testing = False

            # 注意不重置测试结果和档位显示，保持测试完成后的状态

        except Exception as e:
            logger.error(f"通道{self.channel_number}重置进度显示失败: {e}")

    def _update_soh_display(self, soh_percentage: float):
        """更新SOH显示"""
        try:
            # 这里可以添加SOH显示的UI更新逻辑
            # 例如在通道卡片上显示SOH百分比
            logger.debug(f"通道{self.channel_number}更新SOH显示: {soh_percentage:.1f}%")

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新SOH显示失败: {e}")

    def _update_capacity_prediction_display_with_soh(self, capacity: float, soh: Optional[float]):
        """更新带SOH信息的容量预测显示"""
        try:
            capacity_config = self.config_manager.get('capacity_prediction', {})
            unit = capacity_config.get('capacity_unit', 'AH')
            precision = capacity_config.get('display_precision', 3)

            if unit == 'mAH':
                display_value = capacity * 1000
                capacity_text = f"{display_value:.{precision}f}mAH"
            else:
                capacity_text = f"{capacity:.{precision}f}AH"

            # 如果有SOH信息，添加到显示中
            if soh is not None:
                capacity_text += f" (SOH:{soh:.1f}%)"

            self._update_capacity_prediction_display(capacity_text)

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新容量预测显示失败: {e}")

    def _perform_capacity_prediction_if_enabled(self):
        """在启用容量预测功能时执行容量预测"""
        try:
            # 检查是否启用容量预测功能
            if not self.config_manager.get('test.capacity_prediction_enabled', False):
                return

            # 检查是否为连续测试模式
            continuous_mode = self.config_manager.get('test.continuous_mode', False)
            if not continuous_mode:
                logger.debug(f"通道{self.channel_number}非连续测试模式，跳过容量预测")
                return

            # 检查是否有足够的测试数据
            if not hasattr(self, 'current_voltage') or not hasattr(self, 'current_rs') or not hasattr(self, 'current_rct'):
                logger.debug(f"通道{self.channel_number}测试数据不完整，跳过容量预测")
                return

            # 获取当前测试数据
            voltage = getattr(self, 'current_voltage', 0.0)
            rs_value = getattr(self, 'current_rs', 0.0)
            rct_value = getattr(self, 'current_rct', 0.0)
            rct_cv = self.rct_coefficient_of_variation

            # 执行容量预测
            predicted_capacity = self.predict_capacity(voltage, rs_value, rct_value, rct_cv)

            if predicted_capacity is not None:
                logger.info(f"通道{self.channel_number}容量预测完成: {predicted_capacity:.3f}AH")

                # 保存预测结果到容量预测数据表
                self._save_capacity_prediction_data(voltage, rs_value, rct_value, rct_cv, predicted_capacity)
            else:
                logger.debug(f"通道{self.channel_number}容量预测失败")
                self._update_capacity_prediction_display("预测失败")

        except Exception as e:
            logger.error(f"通道{self.channel_number}执行容量预测失败: {e}")

    def _save_capacity_prediction_data(self, voltage: float, rs_value: float, rct_value: float,
                                     rct_cv: float, predicted_capacity: float):
        """保存容量预测数据到数据库"""
        try:
            # 获取数据库管理器
            from data.database_manager import get_database_manager
            db_manager = get_database_manager()

            if not db_manager:
                logger.warning(f"通道{self.channel_number}数据库管理器未初始化，无法保存容量预测数据")
                return

            # 构建容量预测数据
            prediction_data = {
                'battery_code': self.battery_code,
                'channel_number': self.channel_number,
                'test_date': datetime.now().date(),
                'voltage': voltage,
                'rs_value': rs_value,
                'rct_value': rct_value,
                'rct_coefficient_of_variation': rct_cv,
                'predicted_capacity': predicted_capacity,
                'notes': f'连续测试模式自动预测 - 通道{self.channel_number}'
            }

            # 保存到数据库
            prediction_id = db_manager.save_capacity_prediction_data(prediction_data)

            if prediction_id:
                logger.info(f"通道{self.channel_number}容量预测数据保存成功: ID={prediction_id}")
            else:
                logger.warning(f"通道{self.channel_number}容量预测数据保存失败")

        except Exception as e:
            logger.error(f"通道{self.channel_number}保存容量预测数据失败: {e}")

    def _set_test_exception(self, error_type: str, error_message: str):
        """
        设置测试异常状态

        Args:
            error_type: 异常类型
            error_message: 异常消息
        """
        try:
            # 🎯 取样测试模式：不显示异常状态，保持空白
            if hasattr(self, 'config_manager'):
                sampling_test = self.config_manager.get('test.sampling_test', False)
                if sampling_test:
                    logger.info(f"🎯 通道{self.channel_number}取样测试模式：跳过异常状态显示，保持空白")

                    # 关键修复设置测试结束时间，确保is_testing()返回False
                    from datetime import datetime
                    self.test_end_time = datetime.now()
                    logger.debug(f"🎯 通道{self.channel_number}取样测试异常处理：设置结束时间，确保通道状态检查正确")

                    # 清空结果显示，保持空白状态
                    self.result_label.setText("")
                    self.result_label.setStyleSheet("""
                        QLabel {
                            background-color: transparent;
                            color: transparent;
                            border: none;
                            min-height: 80px;
                            max-height: 80px;
                        }
                    """)

                    # 清空详细信息
                    if hasattr(self, 'details_label') and self.details_label:
                        self.details_label.setText("")
                        self.details_label.setStyleSheet("")

                    # 更新状态为空白
                    self.test_state = 'blank'

                    # 取样测试模式不发送异常信号，避免影响取样数据收集
                    logger.debug(f"🎯 通道{self.channel_number}取样测试模式：异常状态已转换为空白状态")
                    return

            logger.error(f"🔧 [异常处理] 通道{self.channel_number} 设置测试异常: {error_type} - {error_message}")

            # 设置异常显示
            self.result_label.setText("异常")
            self.result_label.setStyleSheet("""
                QLabel {
                    background-color: #ff6b6b;
                    color: white;
                    font-size: 32pt;  /* 统一字体：24pt→32pt，与其他测试结果状态一致 */
                    font-weight: 900;  /* 统一字重：bold→900，与其他测试结果状态一致 */
                    border-radius: 8px;
                    padding: 8px;  /* 统一内边距：10px→8px，与其他测试结果状态一致 */
                    min-height: 80px;  /* 统一高度：与其他测试结果状态一致 */
                    max-height: 80px;
                    text-align: center;
                }
            """)

            # 设置详细信息（安全检查）
            if hasattr(self, 'details_label') and self.details_label:
                self.details_label.setText(f"{error_type}: {error_message}")
                self.details_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
            else:
                logger.debug(f"通道{self.channel_number}没有details_label，跳过详细信息设置")

            # 更新状态
            self.test_state = 'exception'

            # 发送异常信号
            if hasattr(self, 'test_completed'):
                exception_result = {
                    'channel': self.channel_number,
                    'state': 'exception',
                    'error_type': error_type,
                    'error_message': error_message,
                    'is_pass': False,
                    'rs_value': 0.0,
                    'rct_value': 0.0,
                    'voltage': getattr(self, 'voltage', 0.0),
                    'rs_grade': None,
                    'rct_grade': None,
                    'fail_items': [error_type]
                }
                self.test_completed.emit(self.channel_number, exception_result)

        except Exception as e:
            logger.error(f"🔧 [异常处理] 通道{self.channel_number} 设置异常状态失败: {e}")

    def set_test_completed_for_sampling(self, voltage: float, rs_value: float, rct_value: float):
        """
        设置取样测试完成状态（不进行合格/不合格判断）

        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)

        """
        try:
            logger.info(f"🎯 通道{self.channel_number}开始执行set_test_completed_for_sampling方法")

            # 防止重复设置
            if hasattr(self, '_test_completed') and self._test_completed:
                logger.warning(f"通道{self.channel_number}测试已完成，跳过重复设置")
                return

            # 关键修复设置测试结束时间，确保is_testing()返回False
            self.test_end_time = datetime.now()
            logger.debug(f"通道{self.channel_number}取样测试完成，设置结束时间")

            # 标记测试完成
            self._test_completed = True

            # 修复确保UI显示正确更新，强制更新所有阻抗值显示
            if hasattr(self, 'ui_updater') and self.ui_updater:
                self.ui_updater.update_voltage_display(voltage)
                self.ui_updater.update_impedance_display(rs_value, rct_value, force_update=True)
                self.ui_updater.update_progress_display(100)
                logger.debug(f" 通道{self.channel_number}采样测试完成，强制更新UI显示: V={voltage:.3f}, Rs={rs_value:.3f}, Rct={rct_value:.3f}")

            # 🎯 取样测试完成后不显示任何结果，保持空白
            if hasattr(self, 'result_label'):
                self.result_label.setText("")
                self.result_label.setObjectName("resultBlank")
                self.result_label.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                        color: transparent;
                        border: none;
                        min-height: 80px;
                        max-height: 80px;
                    }
                """)

            # 档位显示区域也保持空白
            if hasattr(self, 'grade_label'):
                self.grade_label.setText("")
                self.grade_label.setObjectName("gradeBlank")
                self.grade_label.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                        color: transparent;
                        border: none;
                    }
                """)

            # 存储测试结果数据（用于后续数据收集）
            self._test_result_data = {
                'voltage': voltage,
                'rs_value': rs_value,
                'rct_value': rct_value,
                'w_impedance': 0.0,  # 取样测试暂不使用W阻抗
                'is_pass': None,  # 取样测试不判断合格性
                'grade': 'Sampling',  # 标记为取样数据
                'fail_items': []
            }

            # 发送测试完成信号
            test_result = {
                'channel_number': self.channel_number,
                'voltage': voltage,
                'rs_value': rs_value,
                'rct_value': rct_value,
                'w_impedance': 0.0,
                'is_pass': None,  # 取样测试不判断
                'grade': 'Sampling',
                'fail_items': [],
                'test_mode': 'sampling'
            }

            logger.info(f"🎯 通道{self.channel_number}准备发射test_completed信号")
            self.test_completed.emit(self.channel_number, test_result)
            logger.info(f"🎯 通道{self.channel_number}test_completed信号已发射")

            logger.info(f"✅ 通道{self.channel_number}取样测试完成: 电压={voltage:.3f}V, Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")

        except Exception as e:
            logger.error(f"❌ 通道{self.channel_number}设置取样测试完成状态失败: {e}")

    def set_test_completed(self, is_pass: bool, rs_grade: int, rct_grade: int, fail_items: Optional[list] = None):
        """
        设置测试完成状态（简化版 - 使用统一档位管理器）

        Args:
            is_pass: 是否合格
            rs_grade: Rs档位（已弃用，将从数据库获取）
            rct_grade: Rct档位（已弃用，将从数据库获取）
            fail_items: 失败项目列表，如 ["电压", "Rs", "Rct"]
        """
        try:
            # 🎯 使用统一档位管理器更新显示
            logger.debug(f"🔍 [统一档位] 通道{self.channel_number} 使用统一档位管理器更新显示...")

            from utils.grade_manager import get_grade_manager
            grade_manager = get_grade_manager(self.config_manager)

            # 统一更新通道显示
            success = grade_manager.update_channel_display(self.channel_number, self)

            if success:
                logger.info(f"✅ [统一档位] 通道{self.channel_number} 显示更新成功")
            else:
                logger.warning(f"⚠️ [统一档位] 通道{self.channel_number} 显示更新失败，使用传入参数")
                # 备用方案：使用传入的参数
                self._fallback_update_display(is_pass, rs_grade, rct_grade, fail_items)

            # 防止重复设置
            if hasattr(self, '_test_completed') and self._test_completed:
                logger.warning(f"通道{self.channel_number}测试已完成，跳过重复设置")
                return

            # 标记测试已完成
            self._test_completed = True

            # 记录测试结束时间
            self.test_end_time = datetime.now()

            logger.info(f"通道{self.channel_number}设置测试完成状态: {'合格' if is_pass else '不合格'}, Rs档位={rs_grade}, Rct档位={rct_grade}")

            # 🐛 修复：添加详细的档位传递调试日志
            logger.debug(f"🔍 [档位调试] 通道{self.channel_number} set_test_completed参数:")
            logger.debug(f"   is_pass: {is_pass}")
            logger.debug(f"   rs_grade: {rs_grade} (类型: {type(rs_grade)})")
            logger.debug(f"   rct_grade: {rct_grade} (类型: {type(rct_grade)})")
            logger.debug(f"   fail_items: {fail_items}")

            # 修复设置显示逻辑，确保档位为0时正确显示为不合格
            # 检查档位是否有效（不为0）
            valid_grades = (rs_grade is not None and rct_grade is not None and
                          rs_grade > 0 and rct_grade > 0)

            logger.debug(f"🔍 [档位调试] 通道{self.channel_number} 档位有效性检查: {valid_grades}")

            if is_pass and valid_grades:
                # 合格且档位有效时：左侧显示档位，右侧显示"合格"
                grade_text = f"{rs_grade}-{rct_grade}"
                logger.debug(f"🔍 [档位调试] 通道{self.channel_number} 设置档位文本: '{grade_text}'")
                self.grade_label.setText(grade_text)
                self.grade_label.setObjectName("gradePass")

                # 右侧显示合格状态
                self.result_label.setText("合格")
                self.result_label.setObjectName("resultPass")

                # 🐛 修复：验证档位显示是否正确设置
                actual_grade_text = self.grade_label.text()
                logger.debug(f"🔍 [档位调试] 通道{self.channel_number} 档位标签实际显示: '{actual_grade_text}'")
                if actual_grade_text != grade_text:
                    logger.error(f"❌ [档位错误] 通道{self.channel_number} 档位显示不一致!")
                    logger.error(f"   期望: '{grade_text}'")
                    logger.error(f"   实际: '{actual_grade_text}'")
                    # 强制重新设置
                    self.grade_label.setText(grade_text)
                    logger.info(f"🔧 [档位修复] 通道{self.channel_number} 强制重新设置档位: '{grade_text}'")
            else:
                # 不合格或档位无效时：左侧显示"不合格"，右侧显示失败原因
                self.grade_label.setText("不合格")
                self.grade_label.setObjectName("gradeFail")

                # 修复如果档位为0，添加到失败原因中
                if not valid_grades:
                    if rs_grade == 0 and "Rs" not in fail_items:
                        fail_items.append("Rs")
                    # 🔧 [单频点修复] 单频点测试时Rct=0是正常的，不应标记为失败
                    # 检查是否为单频点测试（Rs>0且Rct=0）
                    current_rs = getattr(self, 'rs_value', 0.0)
                    current_rct = getattr(self, 'rct_value', 0.0)
                    is_single_freq_test = (current_rct == 0.0 and current_rs > 0)
                    if rct_grade == 0 and "Rct" not in fail_items and not is_single_freq_test:
                        fail_items.append("Rct")

                # 右侧显示详细的不合格原因
                result_text, result_style = self._get_fail_result_display(fail_items)
                self.result_label.setText(result_text)
                self.result_label.setObjectName(result_style)

            # 修复应用档位标签样式，确保字体大小与结果标签一致
            self._update_grade_label_style(self.grade_label.objectName())

            # 重新应用结果标签样式
            self.result_label.setStyleSheet("")

            # 确保进度条显示100%
            self.progress_bar.setValue(100)

            # 强制刷新UI组件，确保显示更新
            self.grade_label.update()
            self.result_label.update()
            self.progress_bar.update()
            self.update()  # 刷新整个组件

            # 启用扫码按钮（如果存在）
            if hasattr(self, 'scan_button'):
                self.scan_button.setEnabled(True)

            # 增加测试计数
            self.increment_test_count()

            # 构建测试结果数据并发送信号
            current_voltage = getattr(self, 'voltage', 0.0)
            current_rs = getattr(self, 'rs_value', 0.0)
            current_rct = getattr(self, 'rct_value', 0.0)

            # 如果当前值为0，尝试从其他属性获取
            if current_rs == 0.0:
                current_rs = getattr(self, 'current_rs', 0.0)
            if current_rct == 0.0:
                current_rct = getattr(self, 'current_rct', 0.0)
            if current_voltage == 0.0:
                current_voltage = getattr(self, 'current_voltage', 0.0)

            # 已移除离群率数据保存（功能已完全移除）

            self.test_result = {
                'is_pass': is_pass,
                'rs_grade': rs_grade,
                'rct_grade': rct_grade,
                'voltage': current_voltage,
                'rs': current_rs,  # 保持原有字段名
                'rct': current_rct,  # 保持原有字段名
                'rs_value': current_rs,  # 修复兼容打印模块的字段名
                'rct_value': current_rct,  # 修复兼容打印模块的字段名
                'battery_code': self.battery_code,
                'channel_number': self.channel_number,  # 新增通道号
                'test_time': datetime.now().isoformat(),
                'rct_coefficient_of_variation': self.rct_coefficient_of_variation,
                # 已移除离群率相关数据（功能已完全移除）
                # 新增失败原因信息
                'fail_items': fail_items if fail_items else [],
                'fail_reason': self._generate_fail_reason_text(fail_items) if fail_items else ''
            }

            # 修复保存最近的测试数据供打印使用，确保档位信息正确
            self._last_test_data = {
                'is_pass': is_pass,
                'rs_grade': rs_grade,
                'rct_grade': rct_grade,
                'voltage': current_voltage,
                'rs_value': current_rs,
                'rct_value': current_rct,
                'fail_items': fail_items if fail_items else [],
                'fail_reason': self._generate_fail_reason_text(fail_items) if fail_items else ''
            }

            # 在连续测试模式下进行容量预测
            self._perform_capacity_prediction_if_enabled()

            self.test_completed.emit(self.channel_number, self.test_result)

            logger.info(f"通道{self.channel_number}测试完成状态已设置: {'合格' if is_pass else '不合格'}, 档位{rs_grade}-{rct_grade}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}设置测试完成状态失败: {e}")

    def _fallback_update_display(self, is_pass: bool, rs_grade: int, rct_grade: int, fail_items: Optional[list]):
        """备用显示更新方法（统一样式版本）"""
        try:
            # 检查数据有效性
            has_valid_data = (rs_grade is not None and rct_grade is not None and
                            rs_grade != '--' and rct_grade != '--' and rs_grade != 0 and rct_grade != 0)

            if not has_valid_data:
                logger.warning(f"🔧 通道{self.channel_number}备用数据无效(Rs档位={rs_grade}, Rct档位={rct_grade})，跳过UI设置")
                return

            # 🎯 统一样式：与GradeManager保持完全一致
            if is_pass and has_valid_data:
                grade_text = f"{rs_grade}-{rct_grade}"
                self.grade_label.setText(grade_text)
                self.grade_label.setObjectName("gradePass")  # 统一使用gradePass
                self.result_label.setText("合格")
                self.result_label.setObjectName("resultPass")  # 统一使用resultPass

                logger.debug(f"🎯 [备用显示] 通道{self.channel_number} 档位显示: '{grade_text}' (ObjectName: gradePass)")
            else:
                self.grade_label.setText("不合格")
                self.grade_label.setObjectName("gradeFail")  # 统一使用gradeFail
                self.result_label.setText("不合格")
                self.result_label.setObjectName("resultFail")  # 统一使用resultFail

                logger.debug(f"🎯 [备用显示] 通道{self.channel_number} 显示: '不合格' (ObjectName: gradeFail)")

            # 🎯 统一样式刷新：与GradeManager保持一致
            self._apply_unified_style_widget(self.grade_label)
            self._apply_unified_style_widget(self.result_label)

        except Exception as e:
            logger.error(f"通道{self.channel_number}备用显示更新失败: {e}")

    def _apply_unified_style_widget(self, widget):
        """应用统一样式（组件方法 - 修复字体一致性）"""
        try:
            # 🎯 修复：清空内联样式，让ObjectName样式生效
            widget.setStyleSheet("")

            # 🎯 修复：强制重新应用样式，确保CSS文件中的样式生效
            if hasattr(widget, 'style'):
                style = widget.style()
                if hasattr(style, 'unpolish') and hasattr(style, 'polish'):
                    style.unpolish(widget)
                    style.polish(widget)

            # 🎯 修复：强制刷新父组件样式，确保继承正确
            parent = widget.parent()
            if parent and hasattr(parent, 'style'):
                parent_style = parent.style()
                if hasattr(parent_style, 'polish'):
                    parent_style.polish(widget)

            # 🎯 修复：强制更新显示
            widget.update()
            widget.repaint()  # 添加repaint确保立即重绘

            logger.debug(f"🎯 [组件样式修复] 组件样式已刷新: ObjectName='{widget.objectName()}'")

        except Exception as e:
            logger.error(f"❌ [组件样式] 应用统一样式失败: {e}")

    def _generate_fail_reason_text(self, fail_items: list) -> str:
        """
        生成失败原因文本

        Args:
            fail_items: 失败项目列表

        Returns:
            失败原因文本
        """
        if not fail_items:
            return ''

        if len(fail_items) == 1:
            return f"不合格-{fail_items[0]}"
        else:
            return f"不合格-{'/'.join(fail_items[:2])}"  # 最多显示前两个失败项目

    def set_testing_state(self, is_testing: bool):
        """
        设置测试状态（用于UI更新）

        Args:
            is_testing: 是否正在测试
        """
        try:
            if is_testing:
                # 测试开始时的状态设置
                if not self.is_testing():
                    # 如果还没有开始测试，启动计时器
                    self.test_start_time = datetime.now()
                    self.test_end_time = None
                    self.test_time_label.setText("00:00:00")
                    logger.debug(f"通道{self.channel_number}开始测试计时")

                    # 修复测试开始时重置测试完成标记，确保能接收新的判断结果
                    if hasattr(self, '_test_completed'):
                        self._test_completed = False
                        logger.debug(f"通道{self.channel_number}重置测试完成标记（测试开始）")

                # 禁用扫码按钮（如果存在）
                if hasattr(self, 'scan_button'):
                    self.scan_button.setEnabled(False)

                # 设置测试状态
                self.set_test_state("testing")

            else:
                # 测试完成时的状态设置
                if self.is_testing():
                    # 停止计时
                    self.test_end_time = datetime.now()
                    logger.debug(f"通道{self.channel_number}测试完成，停止计时")

                # 启用扫码按钮（如果存在）
                if hasattr(self, 'scan_button'):
                    self.scan_button.setEnabled(True)

                # 设置完成状态
                self.set_test_state("completed")

            logger.debug(f"通道{self.channel_number}测试状态设置: {'测试中' if is_testing else '已完成'}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}设置测试状态失败: {e}")


    def get_print_data(self) -> dict:
        """
        获取用于打印的测试数据

        Returns:
            包含完整测试数据的字典
        """
        try:
            # 修复确保获取最新的测试数据
            current_voltage = getattr(self, 'voltage', 0.0)
            current_rs = getattr(self, 'rs_value', 0.0)
            current_rct = getattr(self, 'rct_value', 0.0)

            # 修复如果当前值为0，尝试从其他属性获取
            if current_rs == 0.0:
                current_rs = getattr(self, 'current_rs', 0.0)
            if current_rct == 0.0:
                current_rct = getattr(self, 'current_rct', 0.0)
            if current_voltage == 0.0:
                current_voltage = getattr(self, 'current_voltage', 0.0)


            # 修复优先从UI显示获取档位信息，确保与UI显示一致
            rs_grade = None
            rct_grade = None
            is_pass = False

            # 修复优先从最近的测试数据获取档位信息，这是最可靠的数据源
            if hasattr(self, '_last_test_data') and self._last_test_data:
                rs_grade = self._last_test_data.get('rs_grade')
                rct_grade = self._last_test_data.get('rct_grade')
                is_pass = self._last_test_data.get('is_pass', False)

            # 备用：从test_result获取
            elif hasattr(self, 'test_result') and self.test_result:
                try:
                    # 兼容字典和对象两种方式
                    if isinstance(self.test_result, dict):
                        rs_grade = self.test_result.get('rs_grade')
                        rct_grade = self.test_result.get('rct_grade')
                        is_pass = self.test_result.get('is_pass', False)
                    else:
                        # 对象方式访问
                        rs_grade = getattr(self.test_result, 'rs_grade', None)
                        rct_grade = getattr(self.test_result, 'rct_grade', None)
                        is_pass = getattr(self.test_result, 'is_pass', False)
                except Exception as e:
                    logger.debug(f"通道{self.channel_number} 获取test_result数据失败: {e}")
                    rs_grade = None
                    rct_grade = None
                    is_pass = False

            # 修复如果仍然没有档位信息，根据测试结果设置正确的档位显示
            if rs_grade is None or rct_grade is None:
                if is_pass:
                    # 合格但没有档位信息，使用默认值
                    rs_grade = rs_grade if rs_grade is not None else 1
                    rct_grade = rct_grade if rct_grade is not None else 1
                else:
                    # 不合格时档位应该显示为"--"
                    rs_grade = "--"
                    rct_grade = "--"

            # 构建打印数据
            print_data = {
                'channel_number': self.channel_number,
                'battery_code': self.battery_code,
                'voltage': current_voltage,
                'rs': current_rs,  # 保持原有字段名
                'rct': current_rct,  # 保持原有字段名
                'rs_value': current_rs,  # 兼容打印模块的字段名
                'rct_value': current_rct,  # 兼容打印模块的字段名
                'rs_grade': rs_grade,
                'rct_grade': rct_grade,
                'is_pass': is_pass,
                'timestamp': datetime.now(),
                # 已移除离群率相关数据（功能已完全移除）
            }


            return print_data

        except Exception as e:
            logger.error(f"通道{self.channel_number}获取打印数据失败: {e}")
            return {}

    def set_exception_state(self, exception_type: str, error_message: str, voltage: float = 0.0):
        """
        设置异常状态显示

        Args:
            exception_type: 异常类型 ('contact_poor', 'battery_error', 'hardware_error', 'exception')
            error_message: 错误消息
            voltage: 检测到的电压值
        """
        try:
            # 新增设置异常状态的显示
            if exception_type == 'contact_poor':
                fail_items = ['接触不良']
                self.grade_label.setText("不合格")
                self.grade_label.setObjectName("gradeFail")

                result_text = "不合格-接触不良"
                result_style = "resultContactPoor"

            elif exception_type == 'battery_error':
                fail_items = ['电池异常']
                self.grade_label.setText("不合格")
                self.grade_label.setObjectName("gradeFail")

                result_text = "不合格-电池异常"
                result_style = "resultBatteryError"

            elif exception_type == 'hardware_error':
                fail_items = ['硬件异常']
                self.grade_label.setText("不合格")
                self.grade_label.setObjectName("gradeFail")

                result_text = "不合格-硬件异常"
                result_style = "resultHardwareError"

            elif exception_type == 'frequency_error':
                fail_items = ['频点出错']
                self.grade_label.setText("不合格")
                self.grade_label.setObjectName("gradeFail")

                result_text = error_message  # 使用传入的错误消息
                result_style = "resultFrequencyError"

            else:  # 通用异常
                fail_items = ['异常']
                self.grade_label.setText("不合格")
                self.grade_label.setObjectName("gradeFail")

                result_text = "不合格-异常"
                result_style = "resultException"

            # 设置结果显示
            self.result_label.setText(result_text)
            self.result_label.setObjectName(result_style)

            # 更新电压显示（如果有检测到电压）
            if voltage > 0:
                self.voltage_label.setText(f"{voltage:.3f}V")
                self.voltage = voltage
            else:
                self.voltage_label.setText("0.000V")
                self.voltage = 0.0

            # 清除Rs和Rct显示
            self.rs_label.setText("0.000mΩ")
            self.rct_label.setText("0.000mΩ")
            self.rs_value = 0.0
            self.rct_value = 0.0

            # 设置进度条为100%（异常完成）
            self.progress_bar.setValue(100)

            # 重新应用样式
            self.grade_label.setStyleSheet("")
            self.result_label.setStyleSheet("")

            # 停止测试状态
            if self.is_testing():
                self.set_testing_state(False)

            # 新增构建异常测试结果数据，确保包含正确的字段名
            self.test_result = {
                'is_pass': False,
                'rs_grade': '--',
                'rct_grade': '--',
                'voltage': voltage,
                'rs': 0.0,  # 保持原有字段名
                'rct': 0.0,  # 保持原有字段名
                'rs_value': 0.0,  # 新增兼容打印模块的字段名
                'rct_value': 0.0,  # 新增兼容打印模块的字段名
                'battery_code': self.battery_code,
                'test_time': datetime.now().isoformat(),
                'exception_type': exception_type,
                'error_message': error_message,
                'fail_items': fail_items,
                # 已移除离群率相关数据（功能已完全移除）
            }

            # 发送异常完成信号
            self.test_completed.emit(self.channel_number, self.test_result)

            logger.warning(f"通道{self.channel_number}异常状态已设置: {exception_type} - {error_message}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}设置异常状态失败: {e}")
