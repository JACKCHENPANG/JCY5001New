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
from typing import Optional, Tuple, List
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
from .channel_frequency_manager import ChannelFrequencyManager
from .channel_config_manager import ChannelConfigManager

# 导入测试控制器
from .channel_test_controller import ChannelTestController

# 导入增强版样式管理器
from .channel_style_manager_enhanced import ChannelStyleManagerEnhanced

# 导入数据更新处理器
from .channel_data_updater import ChannelDataUpdater

# 导入事件处理器
from .channel_event_processor import ChannelEventProcessor

# 导入后端测试结果管理器
from backend.test_result_manager import TestResultManager


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

        # 频点测试数据
        self.current_frequency = 0.0
        self.frequency_index = 0
        self.total_frequencies = 0
        self.frequency_status = "waiting"  # waiting, testing, completed

        # 频点更新状态跟踪
        self._last_frequency_update = None

        # 测试计数跟踪（第三阶段重构：使用配置管理器）
        self.test_count = 0  # 将在后面通过配置管理器加载

        # 通道状态管理 - 修复通道状态显示问题（第二阶段集成：添加回退属性）
        self._is_enabled = True  # 通道是否启用（回退属性）
        self._test_state = "idle"  # idle, testing, completed, failed, disabled（回退属性）

        # 离群检测相关数据
        self.outlier_rate_result = "--"  # 离群率结果
        self.outlier_detection_enabled = False  # 离群检测是否启用
        self.baseline_filename = ""  # 基准文件名
        self.frequency_deviations = {}  # 各频点偏差数据
        self.max_deviation_percent = 0.0  # 新增最大偏差百分比

        # 初始化UI布局管理器（第三阶段重构）
        self.ui_layout_manager = ChannelUILayoutManager(channel_number, self)

        # 初始化测试控制器
        self.test_controller = ChannelTestController(channel_number, config_manager, self)

        # 连接测试控制器信号
        self.test_controller.test_completed.connect(self.test_completed)
        self.test_controller.statistics_update_requested.connect(self.statistics_update_requested)
        self.test_controller.judgment_ready.connect(self.judgment_ready)

        # 初始化样式管理器（第三阶段重构）
        self.style_manager = ChannelStyleManager(channel_number, self)

        # 初始化增强版样式管理器
        self.enhanced_style_manager = ChannelStyleManagerEnhanced(channel_number, self)

        # 初始化数据更新处理器
        self.data_updater = ChannelDataUpdater(channel_number, self)

        # 初始化事件处理器
        self.event_processor = ChannelEventProcessor(channel_number, self, config_manager)

        # 初始化频点管理器（第三阶段重构）
        self.frequency_manager = ChannelFrequencyManager(channel_number)
        self.frequency_manager.frequency_updated.connect(self._on_frequency_updated)

        # 初始化配置管理器（第三阶段重构）
        self.channel_config_manager = ChannelConfigManager(channel_number, config_manager)

        # 初始化测试结果管理器（简化版本，用于UI层判断）
        self._init_test_result_manager()

        # 初始化界面
        self._init_ui()
        self._init_timer()

        # 加载测试计数（第三阶段重构：使用配置管理器）
        self.test_count = self.channel_config_manager.load_test_count()

    def _init_test_result_manager(self):
        """初始化测试结果管理器（简化版本）"""
        try:
            # 创建一个简化的测试结果管理器，只用于UI层的基本判断
            # 不需要完整的后端依赖
            self.test_result_manager = SimpleTestResultManager(self.config_manager)
            logger.debug(f"通道{self.channel_number}测试结果管理器初始化成功")
        except Exception as e:
            logger.error(f"通道{self.channel_number}测试结果管理器初始化失败: {e}")
            # 创建一个最基本的备用管理器
            self.test_result_manager = BasicTestResultManager(self.config_manager)

        # 初始化测试计数显示
        self._update_test_count_display()

        # 初始化计时器管理器（第二阶段集成）
        self.timer_manager = ChannelTimerManager(self.channel_number)
        self.timer_manager.timer_updated.connect(self._on_timer_updated)

        # 初始化状态管理器（第二阶段集成）
        self.state_manager = ChannelStateManager(self.channel_number)
        self.state_manager.add_state_change_callback(self._on_state_changed)

        # 初始化UI更新器（第二阶段集成）
        self._init_ui_updater()

        # 初始化事件处理器（第二阶段集成）
        self._init_event_handler()

        # 容量预测功能已移到测试控制器中

        # 安全QPainter导入移除: 暂时移除绘图保护安装
        # install_paint_filter(self)

        logger.debug(f"通道{self.channel_number}显示组件初始化完成")

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
        # 委托给事件处理器
        self.event_processor.on_timer_updated(channel_number, elapsed_time)

    def _on_state_changed(self, event):
        """状态变化回调（第二阶段集成）"""
        # 委托给事件处理器
        self.event_processor.on_state_changed(event)

    def _init_ui_updater(self):
        """初始化UI更新器（第二阶段集成）"""
        try:
            # 收集UI元素引用
            ui_elements = {
                'voltage_label': getattr(self, 'voltage_label', None),
                'rs_label': getattr(self, 'rs_label', None),
                'rct_label': getattr(self, 'rct_label', None),
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
        """通道点击事件处理（委托给事件处理器）"""
        self.event_processor.on_channel_clicked(channel_number)

    def _on_channel_double_clicked(self, channel_number: int):
        """通道双击事件处理（委托给事件处理器）"""
        self.event_processor.on_channel_double_clicked(channel_number)

    def _on_frequency_updated(self, channel_number: int, frequency: float, current_index: int, total_count: int, status: str):
        """频点更新回调（第三阶段重构：使用频点管理器）"""
        # 委托给事件处理器
        self.event_processor.on_frequency_updated(channel_number, frequency, current_index, total_count, status)

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

            # 应用增强版样式
            self.enhanced_style_manager.apply_main_styles()

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
            self.enhanced_style_manager.apply_main_styles()

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
        """创建主内容区域 - 工业设计风格优化的2列布局"""
        # 创建主内容容器
        main_container = QFrame()
        main_container.setObjectName("mainContentContainer")
        main_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main_layout = QHBoxLayout(main_container)
        main_layout.setSpacing(16)  # 增加间距，符合苹果设计语言
        main_layout.setContentsMargins(8, 8, 8, 8)  # 增加边距，提升视觉层次

        # 左列：基本信息 (保持原有比例)
        left_column = self._create_left_column()
        main_layout.addLayout(left_column, 3)  # 左列占3份权重

        # 右列：阻抗值显示 (保持原有比例)
        right_column = self._create_right_column()
        main_layout.addLayout(right_column, 2)  # 右列占2份权重

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

        # 频点显示区域（第四行）
        self._create_frequency_display(left_column)

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
        """创建电池码输入区域"""
        battery_layout = QHBoxLayout()
        battery_layout.setSpacing(4)

        battery_label = QLabel("电池码:")
        battery_label.setStyleSheet("font-size: 14pt; color: #7f8c8d; font-weight: bold;")  # 精确调整从12pt增大到14pt (+2pt)
        battery_layout.addWidget(battery_label)

        self.battery_code_edit = QLineEdit()
        self.battery_code_edit.setObjectName("batteryCodeEdit")
        self.battery_code_edit.setPlaceholderText("扫码或输入")
        self.battery_code_edit.textChanged.connect(self._on_battery_code_changed)
        battery_layout.addWidget(self.battery_code_edit)
        battery_layout.addStretch()  # 添加弹性空间

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
        voltage_layout.addStretch()

        layout.addLayout(voltage_layout)

    def _create_right_column(self):
        """创建右列 - 阻抗值显示（紧凑格式）"""
        right_column = QVBoxLayout()
        right_column.setSpacing(4)
        right_column.setContentsMargins(0, 0, 0, 0)

        # 创建Rs显示区域（紧凑单行格式）
        self._create_compact_impedance_area(right_column, "Rs(mΩ)", "rs")

        # 创建Rct显示区域（紧凑单行格式）
        self._create_compact_impedance_area(right_column, "Rct(mΩ)", "rct")

        # 添加离群率显示区域（替换扫码按钮）
        self._create_outlier_rate_area(right_column)

        # 减少弹性空间，为结果区域留出更多垂直空间
        right_column.addStretch(1)

        return right_column

    def _create_compact_impedance_area(self, layout, title: str, object_name: str):
        """
        创建紧凑的阻抗值显示区域（类似电压显示格式）

        Args:
            layout: 父布局
            title: 显示标题
            object_name: 对象名称前缀
        """
        impedance_layout = QHBoxLayout()
        impedance_layout.setSpacing(4)

        # 标题标签
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14pt; color: #7f8c8d; font-weight: bold;")  # 精确调整从12pt增大到14pt (+2pt)
        impedance_layout.addWidget(title_label)

        # 数值标签 - 启用自动换行功能
        value_label = QLabel("0.000")
        value_label.setObjectName(f"{object_name}Value")
        value_label.setWordWrap(True)  # 启用自动换行
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 居中对齐
        impedance_layout.addWidget(value_label)
        impedance_layout.addStretch()

        # 保存数值标签引用
        if object_name == "rs":
            self.rs_label = value_label
        elif object_name == "rct":
            self.rct_label = value_label

        layout.addLayout(impedance_layout)

    def _create_outlier_rate_area(self, layout):
        """创建离群率显示区域（🔧 功能已屏蔽）"""
        outlier_layout = QHBoxLayout()
        outlier_layout.setSpacing(4)
        outlier_layout.setContentsMargins(0, 4, 0, 0)

        # 离群率标签（🔧 屏蔽功能）
        outlier_title_label = QLabel("离群率:")
        outlier_title_label.setStyleSheet("font-size: 14pt; color: #7f8c8d; font-weight: bold;")  # 精确调整从12pt增大到14pt (+2pt)
        outlier_layout.addWidget(outlier_title_label)

        # 离群率值显示（🔧 屏蔽功能）
        self.outlier_rate_label = QLabel("功能已屏蔽")
        self.outlier_rate_label.setObjectName("outlierRateValueDisabled")  # 强制禁用状态
        self.outlier_rate_label.setStyleSheet("color: gray; font-style: italic;")  # 灰色斜体显示
        outlier_layout.addWidget(self.outlier_rate_label)
        outlier_layout.addStretch()

        layout.addLayout(outlier_layout)

    def _create_progress_area(self, layout):
        """创建进度条区域"""
        # 添加分隔空间
        layout.addSpacing(8)

        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("testProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.progress_bar)

    def _create_result_area(self, layout):
        """创建测试结果显示区域（档位+判定双区域格式）- 工业设计风格优化"""
        # 添加分隔空间
        layout.addSpacing(8)  # 增加间距，提升视觉层次

        # 创建水平布局容器
        result_container = QHBoxLayout()
        result_container.setSpacing(8)  # 增加间距，符合苹果设计语言
        result_container.setContentsMargins(0, 0, 0, 0)

        # 第一个区域：档位显示 (1/3宽度) - 超大字体优化
        self.grade_label = QLabel("--")
        self.grade_label.setObjectName("gradeDisplay")
        self.grade_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grade_label.setFixedHeight(160)  # 2倍高度，最大化利用垂直空间
        self.grade_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        result_container.addWidget(self.grade_label, 1)  # 占1份权重

        # 第二个区域：测试结果判定 (2/3宽度) - 超大字体优化
        self.result_label = QLabel("待测试")
        self.result_label.setObjectName("resultWaiting")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setFixedHeight(160)  # 2倍高度，最大化利用垂直空间
        self.result_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        result_container.addWidget(self.result_label, 2)  # 占2份权重

        # 将水平布局添加到主布局
        result_widget = QWidget()
        result_widget.setLayout(result_container)
        layout.addWidget(result_widget)

    def _create_frequency_display(self, layout):
        """创建频点显示区域"""
        # ===== 频点显示功能暂时屏蔽 =====
        # 说明：为简化当前界面，专注于核心测试功能，暂时隐藏频点显示
        # 保留后端逻辑和数据处理，只隐藏前端UI显示
        # 将来需要时可以通过设置setVisible(True)重新启用

        # 频点显示容器
        freq_container = QHBoxLayout()
        freq_container.setSpacing(4)
        freq_container.setContentsMargins(0, 2, 0, 2)

        # 频点标签
        freq_title_label = QLabel("当前频点:")
        freq_title_label.setStyleSheet("font-size: 8pt; color: #7f8c8d;")
        freq_title_label.setVisible(False)  # 暂时隐藏
        freq_container.addWidget(freq_title_label)

        # 频点值显示
        self.frequency_value_label = QLabel("--")
        self.frequency_value_label.setObjectName("frequencyValue")
        self.frequency_value_label.setVisible(False)  # 暂时隐藏
        freq_container.addWidget(self.frequency_value_label)

        # 进度信息显示
        self.frequency_progress_label = QLabel("")
        self.frequency_progress_label.setObjectName("frequencyProgress")
        self.frequency_progress_label.setVisible(False)  # 暂时隐藏
        freq_container.addWidget(self.frequency_progress_label)

        # 状态指示器
        self.frequency_status_label = QLabel("●")
        self.frequency_status_label.setObjectName("frequencyStatusWaiting")
        self.frequency_status_label.setVisible(False)  # 暂时隐藏
        freq_container.addWidget(self.frequency_status_label)

        freq_container.addStretch()

        # 暂时隐藏整个频点显示容器
        freq_widget = QWidget()
        freq_widget.setLayout(freq_container)
        freq_widget.setVisible(False)  # 隐藏整个频点显示区域

        # 创建一个包装布局来添加隐藏的频点容器
        freq_wrapper_layout = QVBoxLayout()
        freq_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        freq_wrapper_layout.addWidget(freq_widget)
        layout.addLayout(freq_wrapper_layout)

        # ===== 频点显示功能屏蔽结束 =====

        # 保存频点显示组件的引用，方便将来重新启用
        self._freq_title_label = freq_title_label
        self._freq_widget = freq_widget

    def enable_frequency_display(self, enabled: bool = True):
        """
        启用或禁用频点显示功能

        Args:
            enabled: True=显示频点信息, False=隐藏频点信息
        """
        try:
            if hasattr(self, '_freq_widget'):
                self._freq_widget.setVisible(enabled)
            if hasattr(self, '_freq_title_label'):
                self._freq_title_label.setVisible(enabled)
            if hasattr(self, 'frequency_value_label'):
                self.frequency_value_label.setVisible(enabled)
            if hasattr(self, 'frequency_progress_label'):
                self.frequency_progress_label.setVisible(enabled)
            if hasattr(self, 'frequency_status_label'):
                self.frequency_status_label.setVisible(enabled)

            logger.debug(f"通道{self.channel_number}频点显示功能: {'启用' if enabled else '禁用'}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}切换频点显示状态失败: {e}")

    # 样式管理功能已移到增强版样式管理器中

    def _init_timer(self):
        """初始化定时器"""
        # 测试时间更新定时器
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self._update_test_time)
        self.time_timer.start(1000)  # 每秒更新一次

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

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新测试时间失败: {e}")

    def _on_battery_code_changed(self, text: str):
        """电池码变更处理（委托给事件处理器）"""
        self.event_processor.on_battery_code_changed(text)

    def update_outlier_detection_status(self, enabled: bool):
        """
        更新离群检测状态（🔧 功能已屏蔽）

        Args:
            enabled: 是否启用离群检测
        """
        try:
            # 屏蔽功能始终保持禁用状态
            self.outlier_detection_enabled = False  # 强制禁用

            # 屏蔽功能始终显示屏蔽状态
            self.outlier_rate_label.setObjectName("outlierRateValueDisabled")
            self.outlier_rate_label.setText("功能已屏蔽")
            self.outlier_rate_label.setStyleSheet("color: gray; font-style: italic;")

            # 重新应用样式
            self.outlier_rate_label.style().unpolish(self.outlier_rate_label)
            self.outlier_rate_label.style().polish(self.outlier_rate_label)

            logger.debug(f"通道{self.channel_number}离群检测功能已屏蔽")

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新离群检测状态失败: {e}")

    def update_outlier_rate_result(self, result: str, baseline_filename: str = "", frequency_deviations: Optional[dict] = None, is_final: bool = False):
        """
        更新离群率结果

        Args:
            result: 离群率结果（"PASS"或偏差百分比值）
            baseline_filename: 基准文件名
            frequency_deviations: 各频点偏差数据
            is_final: 是否为最终结果（测试完成后）
        """
        # 委托给数据更新处理器
        self.data_updater.update_outlier_rate_result(result, baseline_filename, frequency_deviations, is_final)

    def _format_outlier_rate_display(self, result: str, is_final: bool) -> str:
        """
        格式化离群率显示文本

        Args:
            result: 原始结果（"PASS"或偏差百分比值）
            is_final: 是否为最终结果

        Returns:
            格式化后的显示文本
        """
        try:
            if not is_final:
                # 测试过程中：显示实时偏差百分比值
                if result == "PASS":
                    # 如果当前频点通过，显示具体的偏差值
                    if hasattr(self, 'frequency_deviations') and self.frequency_deviations:
                        # 获取最新频点的偏差值
                        latest_deviation = max(self.frequency_deviations.values()) if self.frequency_deviations else 0
                        return f"{latest_deviation:.1f}%"
                    else:
                        return "0.0%"
                else:
                    # 显示具体的偏差百分比值
                    return result
            else:
                # 测试完成后：根据最大偏差显示最终结果
                if hasattr(self, 'frequency_deviations') and self.frequency_deviations:
                    max_deviation = max(self.frequency_deviations.values())

                    # 从配置中获取阈值
                    threshold = 10.0  # 默认阈值
                    try:
                        from backend.outlier_detection_manager import OutlierDetectionManager
                        outlier_manager = OutlierDetectionManager()
                        config = outlier_manager.get_detection_config()
                        threshold = config.get('deviation_threshold', 10.0)
                    except Exception as e:
                        logger.warning(f"获取离群率阈值失败，使用默认值10.0%: {e}")

                    if max_deviation <= threshold:
                        # 合格情况：只显示最大偏差百分比
                        return f"{max_deviation:.1f}%"
                    else:
                        # 不合格情况：显示最大偏差百分比+不合格标识
                        return f"{max_deviation:.1f}%-不合格"
                else:
                    # 修复如果没有偏差数据，尝试从result中提取数值
                    if result == "PASS":
                        return "0.0%"  # 合格但没有具体数据
                    elif result in ["已禁用", "无数据", "检测失败"]:
                        # 特殊状态直接显示
                        return result
                    elif result and result != "PASS":
                        # 如果result包含百分比数值，直接显示
                        if "%" in result:
                            return result
                        else:
                            # 尝试解析数值并添加百分比
                            try:
                                value = float(result)
                                return f"{value:.1f}%"
                            except (ValueError, TypeError):
                                return result
                    else:
                        return result if result else "无数据"

        except Exception as e:
            logger.error(f"通道{self.channel_number}格式化离群率显示失败: {e}")
            return result

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

            # 修复统一重置所有测试完成标志，防止第二次测试被跳过
            self._test_completed = False

            # 重置测试完成管理器的状态（主要标志）
            if hasattr(self, 'completion_manager') and self.completion_manager:
                self.completion_manager.reset_completion_state()
                logger.debug(f"通道{self.channel_number}测试完成管理器状态已重置")

            logger.debug(f"通道{self.channel_number}所有测试完成标志已重置")

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

            # 修复强制刷新UI组件，确保第二次测试时能正常更新
            self.result_label.update()
            self.grade_label.update()
            self.progress_bar.update()

            # 修复强制清空频点信息，确保新测试时频点能正常更新
            self.clear_frequency_info()
            logger.debug(f"通道{self.channel_number}开始测试时已清空频点信息")

            # 重置离群率显示
            self.outlier_rate_result = "--"
            if self.outlier_detection_enabled:
                self.outlier_rate_label.setText("等待")

            # 修复强制刷新UI显示
            self.update()

            # 通知测试控制器开始测试
            self.test_controller.start_test(battery_code)

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

                logger.info(f"通道{self.channel_number}停止测试，结果已清除")
            else:
                # 保持测试结果，只重置进行中的状态
                if self.is_testing():
                    # 如果正在测试中被停止，重置进度但保持结果
                    self.test_progress = 0
                    self.progress_bar.setValue(0)

                logger.info(f"通道{self.channel_number}停止测试，结果已保持")

            # 清空频点信息
            self.clear_frequency_info()

            # 启用扫码按钮（如果存在）
            if hasattr(self, 'scan_button'):
                self.scan_button.setEnabled(True)

            # 通知测试控制器停止测试
            self.test_controller.stop_test(clear_results)

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
        更新测试数据

        Args:
            voltage: 电压值 (V)
            rs: Rs值 (mΩ)
            rct: Rct值 (mΩ)
            progress: 测试进度 (0-100)
        """
        try:
            # EIS同步修复: 移除数据变化检查，确保UI始终更新
            # 这样可以确保EIS计算的新值能够正确同步到UI显示
            logger.debug(f"通道{self.channel_number}更新数据: V={voltage:.3f}, Rs={rs:.3f}, Rct={rct:.3f}, 进度={progress}%")

            # 修复强化进度状态管理，严格防止进度回退
            original_progress = progress

            # 新增检测测试开始，自动重置进度状态
            if (progress > 0 and self.current_progress == 0 and
                self.max_progress_reached == 0 and not self.is_testing()):
                logger.info(f"🎯 [进度管理] 通道{self.channel_number}检测到新测试开始，重置进度状态")
                self.reset_progress_state(force_reset=True)

            # 修复移除测试重新开始的特殊处理，确保进度始终单调递增
            # 注释掉原有代码，防止进度回退
            # if (self.current_progress > 40 and progress < 10):
            # logger.info(f"🔄 [进度管理] 通道{self.channel_number}检测到测试重新开始，重置进度状态: {self.current_progress}% -> {progress}%")
            # self.reset_progress_state(force_reset=True)
            # self.current_progress = progress
            # self.max_progress_reached = progress
            
            # 确保进度只能单调递增（所有情况）
            elif progress > self.max_progress_reached:
                # 进度正常递增
                self.max_progress_reached = progress
                self.current_progress = progress
                logger.debug(f"🎯 [进度管理] 通道{self.channel_number}进度递增: {progress}% (新最高进度)")
            elif progress < self.current_progress:
                # 修复只在非测试重启情况下才警告进度回退（添加频率限制）
                if not (self.current_progress > 40 and progress < 10):
                    # 减少重复的进度回退警告
                    if not hasattr(self, '_progress_rollback_warned'):
                        self._progress_rollback_warned = 0
                    if self._progress_rollback_warned < 3:  # 最多警告3次
                        logger.debug(f"通道{self.channel_number}检测到进度回退: {original_progress}% < {self.current_progress}%，强制保持当前进度")
                        self._progress_rollback_warned += 1
                    progress = self.current_progress  # 强制使用当前进度，防止回退
                else:
                    # 测试重启情况，允许进度重置
                    self.current_progress = progress
                    self.max_progress_reached = progress
                    logger.debug(f"🔄 [进度管理] 通道{self.channel_number}测试重启，进度重置: {progress}%")
            elif progress == self.current_progress:
                # 进度相同，正常保持
                logger.debug(f"🎯 [进度管理] 通道{self.channel_number}进度保持: {progress}%")
            else:
                # 进度略有增加但未超过历史最高，正常更新
                self.current_progress = progress
                logger.debug(f"🎯 [进度管理] 通道{self.channel_number}进度更新: {progress}%")

            # 修复更新内部数据，确保数据能够正确保存
            self.voltage = voltage
            # 使用强制更新确保Rs和Rct值能够保存，绕过验证限制
            if hasattr(self, 'data_manager') and self.data_manager:
                self.data_manager.force_update_impedance(rs, rct)
            
            # 修复同时更新所有相关属性，确保数据一致性
            # 只有在接收到有效数据时才更新，避免0值覆盖正确数据
            if rs > 0 and rct > 0:
                self.rs_value = rs
                self.rct_value = rct
                self.current_rs = rs
                self.current_rct = rct
                # 修复如果正在等待有效数据，现在收到了，清除等待标志
                if getattr(self, '_waiting_for_valid_data', False):
                    self._waiting_for_valid_data = False

            if voltage > 0:
                self.voltage = voltage
                self.current_voltage = voltage

            self.test_progress = progress


            # 委托给数据更新处理器处理UI更新
            self.data_updater._safe_update_ui_data(voltage, rs, rct, progress)

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新测试数据失败: {e}")

    def update_battery_status(self, status: str, voltage: float):
        """更新电池状态显示"""
        try:
            logger.info(f"🔋 通道{self.channel_number}更新电池状态: {status} ({voltage:.2f}V)")

            # 获取电池状态指示器 - 修复：增强调试和多种获取方式
            indicator = None

            # 方法1：尝试从UI布局管理器获取电池状态指示器
            if hasattr(self, 'ui_layout_manager') and self.ui_layout_manager:
                ui_elements = self.ui_layout_manager.get_all_ui_elements()
                indicator = ui_elements.get('battery_status_indicator')

            # 方法2：备用方案：直接从属性获取
            if not indicator and hasattr(self, 'battery_status_indicator'):
                indicator = self.battery_status_indicator

            # 方法3：通过对象名称查找
            if not indicator:
                indicator = self.findChild(QLabel, "batteryStatusIndicator")

            # 方法4：遍历所有QLabel查找
            if not indicator:
                for child in self.findChildren(QLabel):
                    if child.objectName() == "batteryStatusIndicator":
                        indicator = child
                        break

            if indicator:
                # 委托给增强版样式管理器处理
                self.enhanced_style_manager.apply_battery_status_style(indicator, status, voltage)
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
                    self.update_frequency_info(frequency, current_index, total_count, "testing")

            elif state == 'completed':
                # 修复测试完成时停止计时器
                if self.is_testing():
                    self.set_testing_state(False)
                    logger.debug(f"通道{self.channel_number}测试完成，停止计时器")

                # 修复只有在接收到有效数据时才保存，避免0值覆盖正确数据
                if rs_value > 0 and rct_value > 0:
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

                    if stored_rs > 0 and stored_rct > 0:
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
                        # 仍然更新进度到100%，但不立即设置异常状态
                        self.update_test_data(voltage, 0, 0, 100)
                        # 优化增加延迟时间，给后端更多时间完成计算和数据传递
                        QTimer.singleShot(1000, lambda: self._check_delayed_data_completion())
                        # 新增设置一个备用检查，如果第一次检查失败，再等待一段时间
                        QTimer.singleShot(2000, lambda: self._check_delayed_data_completion_backup())

                # 更新Rct变异系数
                if rct_cv > 0:
                    self.rct_coefficient_of_variation = rct_cv

                # 修复处理离群率检测结果显示
                outlier_result = progress_data.get('outlier_result')
                frequency_deviations = progress_data.get('frequency_deviations', {})

                logger.debug(f"通道{self.channel_number}收到离群率数据: outlier_result={outlier_result}, frequency_deviations={frequency_deviations}")

                # 修复确保离群率数据正确保存到通道组件属性
                if outlier_result is not None and outlier_result not in ["--", "等待"]:
                    # 保存离群率数据到通道组件属性
                    self.outlier_rate_result = outlier_result
                    self.frequency_deviations = frequency_deviations or {}
                    self.max_deviation_percent = max(frequency_deviations.values()) if frequency_deviations else 0.0

                    # 有明确的离群率结果，直接显示（不管功能是否启用）
                    self.update_outlier_rate_result(outlier_result, "", frequency_deviations, True)
                else:
                    # 没有离群率结果，根据功能启用状态显示
                    if self.outlier_detection_enabled:
                        # 离群检测已启用但没有结果，显示"无数据"
                        self.outlier_rate_result = "无数据"
                        self.update_outlier_rate_result("无数据", "", {}, True)
                        logger.warning(f"🔍 [离群率同步] 通道{self.channel_number}离群检测已启用但无结果数据，显示'无数据'")
                    else:
                        # 离群检测未启用，显示"已禁用"
                        self.outlier_rate_result = "已禁用"
                        self.update_outlier_rate_result("已禁用", "", {}, True)

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
                    if (rs_value <= 0 or rct_value <= 0) and (stored_rs > 0 and stored_rct > 0):
                        rs_value = stored_rs
                        rct_value = stored_rct
                        if voltage <= 0 and stored_voltage > 0:
                            voltage = stored_voltage

                    # 修复如果正在等待有效数据，且现在收到了有效数据，清除等待标志
                    if getattr(self, '_waiting_for_valid_data', False) and rs_value > 0 and rct_value > 0:
                        self._waiting_for_valid_data = False

                    # 只有在所有值都无效且不在等待状态时才标记为异常
                    if (rs_value <= 0 or rct_value <= 0) and not getattr(self, '_waiting_for_valid_data', False):
                        logger.error(f"🔧 [修复] 通道{self.channel_number} Rs/Rct值无效: Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")
                        # 标记为测试异常
                        self._set_test_exception("数据计算失败", f"Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")
                        return
                    else:
                        # 修复Rs/Rct值正常但缺少判断结果，使用后端测试结果管理器进行判断
                        logger.warning(f"🔧 [修复] 通道{self.channel_number} Rs/Rct值正常但缺少判断结果，使用后端判断逻辑")

                        # 计算档位
                        rs_grade, rct_grade = self.test_result_manager.calculate_grades(rs_value, rct_value)

                        # 修复使用后端测试结果管理器进行精确判断，并添加离群率检测
                        try:
                            # 获取离群率结果
                            outlier_result = getattr(self, 'outlier_rate_result', None)
                            if outlier_result in ["已禁用", "无数据", "--"]:
                                outlier_result = None

                            is_pass, fail_items = self.test_result_manager.judge_test_result(
                                voltage, rs_value, rct_value, outlier_result=outlier_result, channel_num=self.channel_number
                            )

                            logger.debug(f"🔧 [修复] 通道{self.channel_number} 后端判断结果: 合格={is_pass}, 失败项目={fail_items}, 离群率={outlier_result}")

                        except Exception as e:
                            logger.error(f"🔧 [修复] 通道{self.channel_number} 后端判断失败: {e}")
                            # 如果后端判断失败，延迟处理，等待后端数据
                            logger.warning(f"🔧 [修复] 通道{self.channel_number} 延迟处理，等待后端判断结果")
                            QTimer.singleShot(1000, lambda: self._check_delayed_judgment_completion(voltage, rs_value, rct_value))
                            return

                        # 设置测试完成状态
                        self.set_test_completed(is_pass, rs_grade, rct_grade, fail_items)
                        return

                # 修复频率显示为完成状态使用正确的频点信息
                if frequency > 0:
                    # 从进度数据中获取频点信息
                    current_index = progress_data.get('current_frequency_index', 20)  # 默认最后一个频点
                    total_count = progress_data.get('total_frequency_count', 20)

                    logger.debug(f"通道{self.channel_number}测试完成频点显示: {frequency}Hz ({current_index}/{total_count}) completed")
                    self.update_frequency_info(frequency, current_index, total_count, "completed")

            elif state == 'failed':
                # 修复测试失败时也要停止计时器
                if self.is_testing():
                    self.set_testing_state(False)
                    logger.debug(f"通道{self.channel_number}测试失败，停止计时器")

                # 测试失败
                fail_reason = progress_data.get('fail_reason', '测试失败')
                self.set_test_result("测试失败", False, None, None, [fail_reason])

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

            if stored_rs > 0 and stored_rct > 0:
                # 清除等待标志
                self._waiting_for_valid_data = False
                # 更新最终数据
                self.update_test_data(stored_voltage, stored_rs, stored_rct, 100)
            else:
                logger.error(f"🔧 通道{self.channel_number}延迟检查仍无有效数据，设置为异常: Rs={stored_rs:.3f}mΩ, Rct={stored_rct:.3f}mΩ")
                # 清除等待标志
                self._waiting_for_valid_data = False
                # 设置为测试异常
                self._set_test_exception("数据计算失败", f"Rs={stored_rs:.3f}mΩ, Rct={stored_rct:.3f}mΩ")

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

            if stored_rs > 0 and stored_rct > 0:
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
                logger.error(f"🔧 通道{self.channel_number}延迟判断仍然失败: {e}")
                # 最后的备用方案：标记为异常
                self._set_test_exception("判断逻辑失败", f"Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")

        except Exception as e:
            logger.error(f"通道{self.channel_number}延迟判断完成检查失败: {e}")

    # UI数据更新功能已移到数据更新处理器中


    def update_frequency_info(self, frequency: float, current_index: int, total_count: int, status: str = "waiting"):
        """
        更新频点信息显示（第三阶段重构：使用频点管理器）

        Args:
            frequency: 当前测试频点 (Hz)
            current_index: 当前频点索引 (从1开始)
            total_count: 总频点数量
            status: 频点测试状态 ("waiting", "testing", "completed")
        """
        # 委托给数据更新处理器
        self.data_updater.update_frequency_info(frequency, current_index, total_count, status)

    def _should_update_frequency_display(self, frequency: float, current_index: int, total_count: int, status: str) -> bool:
        """
        判断是否应该更新频点显示（修复：频点显示状态保持逻辑）

        Args:
            frequency: 新的频点值
            current_index: 新的频点索引
            total_count: 总频点数量
            status: 新的频点状态

        Returns:
            是否应该更新显示
        """
        try:
            # 修复如果是第一次更新或频点已重置，总是允许
            if not hasattr(self, 'current_frequency') or self.current_frequency == 0:
                logger.debug(f"通道{self.channel_number}首次频点更新，允许")
                return True

            # 获取当前状态
            current_status = getattr(self, 'frequency_status', 'waiting')
            current_freq = getattr(self, 'current_frequency', 0)
            current_idx = getattr(self, 'frequency_index', 0)

            # 修复如果频点状态为waiting且频点值为0，说明是新测试开始
            if current_freq == 0 and current_status == "waiting":
                logger.debug(f"通道{self.channel_number}新测试开始，允许频点更新")
                return True

            # 修复如果当前状态为waiting且新状态为testing，说明是新测试开始
            if current_status == "waiting" and status == "testing":
                logger.debug(f"通道{self.channel_number}从等待状态开始新测试，允许频点更新")
                return True

            # 修复：频点进度数值一致性检查
            # 如果总频点数发生变化，说明是新的测试序列，总是允许
            current_total = getattr(self, 'total_frequencies', 0)
            if total_count != current_total and total_count > 0:
                logger.debug(f"通道{self.channel_number}总频点数变化({current_total}->{total_count})，允许更新")
                return True

            # 优化简化状态保持规则，减少过度保护
            if current_status == "testing":
                # 允许测试完成的状态更新
                if status == "completed":
                    logger.debug(f"通道{self.channel_number}测试完成，允许")
                    return True
                # 允许频点切换（正常的测试流程）
                elif frequency != current_freq:
                    logger.debug(f"通道{self.channel_number}频点切换: {current_freq}Hz -> {frequency}Hz，允许")
                    return True
                # 允许相同频点的索引修正或状态更新
                elif frequency == current_freq:
                    logger.debug(f"通道{self.channel_number}相同频点更新，允许")
                    return True
                # 其他情况也允许，避免卡死
                else:
                    logger.debug(f"通道{self.channel_number}测试中其他更新，允许")
                    return True

            # 优化大幅简化状态保持逻辑，提高性能
            # 基本原则：只阻止明显错误的更新，其他都允许

            # 允许所有正常的测试状态更新
            if status in ["testing", "completed", "waiting"]:
                logger.debug(f"通道{self.channel_number}正常状态更新，允许: {frequency}Hz({current_index}/{total_count}) {status}")
                return True

            # 允许当前状态为等待或完成时的任何更新
            if current_status in ["waiting", "completed"]:
                logger.debug(f"通道{self.channel_number}从{current_status}状态更新，允许")
                return True

            # 允许相同频点的任何更新
            if frequency == current_freq:
                logger.debug(f"通道{self.channel_number}相同频点更新，允许")
                return True

            # 默认允许（避免卡死）
            logger.debug(f"通道{self.channel_number}默认允许更新: {frequency}Hz({current_index}/{total_count}) {status}")
            return True

        except Exception as e:
            logger.error(f"通道{self.channel_number}判断频点更新失败: {e}")
            # 出错时允许更新，避免卡死
            return True

    def _safe_update_frequency_ui(self, frequency: float, current_index: int, total_count: int, status: str):
        """
        安全的频点UI更新方法（在主线程中执行）
        """
        try:
            # 修复安全的频点UI更新
            logger.debug(f"通道{self.channel_number}安全更新频点UI: {frequency}Hz ({current_index}/{total_count}) {status}")

            # 闪退修复: 检查组件是否仍然有效
            if not hasattr(self, 'frequency_value_label') or self.frequency_value_label is None:
                logger.debug(f"通道{self.channel_number}频点UI组件无效，跳过更新")
                return

            # 闪退修复: 简化UI更新，只更新必要内容
            freq_text = "--"
            progress_text = ""

            # 更新频点值显示（三位小数）
            if frequency > 0:
                if frequency >= 1000:
                    freq_text = f"{frequency/1000:.3f}kHz"
                else:
                    freq_text = f"{frequency:.3f}Hz"

            # 闪退修复: 安全的文本更新
            try:
                self.frequency_value_label.setText(freq_text)
            except:
                pass  # 忽略UI更新错误

            # 更新进度信息（修复：确保数值一致性和范围验证）
            if total_count > 1:
                # 确保当前索引在有效范围内
                valid_index = max(1, min(current_index, total_count))
                if valid_index != current_index:
                    logger.warning(f"通道{self.channel_number}频点索引超出范围: {current_index}/{total_count}, 修正为{valid_index}")

                # 修复：确保总频点数一致性
                # 如果已有内部状态，优先使用内部状态的总数（避免跳变）
                display_total = total_count
                if hasattr(self, 'total_frequencies') and self.total_frequencies > 0:
                    # 如果内部状态的总数与传入的总数不同，且不是初始化，记录警告
                    if self.total_frequencies != total_count and getattr(self, 'current_frequency', 0) > 0:
                        logger.warning(f"通道{self.channel_number}总频点数不一致: 内部{self.total_frequencies} vs 传入{total_count}")
                        # 在测试过程中保持总数稳定
                        if status in ["testing", "completed"]:
                            display_total = self.total_frequencies
                            logger.debug(f"通道{self.channel_number}保持总频点数稳定: {display_total}")

                progress_text = f"({valid_index}/{display_total})"
            elif total_count == 1:
                progress_text = "(单频)"
            else:
                progress_text = ""

            # 闪退修复: 安全的进度更新
            try:
                self.frequency_progress_label.setText(progress_text)
            except:
                pass  # 忽略UI更新错误

            # 闪退修复: 简化状态指示器更新，避免样式冲突和频繁更新
            try:
                if hasattr(self, 'frequency_status_label') and self.frequency_status_label is not None:
                    # 只更新文本，不更新样式，减少UI负载
                    if status == "testing":
                        self.frequency_status_label.setText("●")
                    elif status == "completed":
                        self.frequency_status_label.setText("✓")
                    else:
                        self.frequency_status_label.setText("○")
            except:
                pass  # 忽略状态更新错误

            logger.debug(f"通道{self.channel_number}安全更新频点UI: {freq_text} {progress_text} {status}")

        except Exception as e:
            logger.debug(f"通道{self.channel_number}安全频点UI更新失败: {e}")
            # 闪退修复: 不抛出异常，确保程序稳定

    def force_update_frequency_info(self, frequency: float, current_index: int, total_count: int, status: str = "waiting"):
        """
        强制更新频点信息显示（第三阶段重构：使用频点管理器）

        Args:
            frequency: 当前测试频点 (Hz)
            current_index: 当前频点索引 (从1开始)
            total_count: 总频点数量
            status: 频点测试状态 ("waiting", "testing", "completed")
        """
        try:
            # 使用频点管理器强制更新频点信息
            self.frequency_manager.force_update_frequency_info(frequency, current_index, total_count, status)

        except Exception as e:
            logger.error(f"通道{self.channel_number}强制更新频点信息失败: {e}")

    def update_frequency_progress_only(self, current_index: int, total_count: int, status: str = "waiting"):
        """
        仅更新频点进度显示（修复：确保进度数值一致性）

        Args:
            current_index: 当前频点索引 (从1开始)
            total_count: 总频点数量
            status: 频点测试状态 ("waiting", "testing", "completed")
        """
        try:
            # 验证参数有效性
            if total_count <= 0:
                logger.warning(f"通道{self.channel_number}无效的总频点数: {total_count}")
                return

            # 确保当前索引在有效范围内
            valid_index = max(1, min(current_index, total_count))
            if valid_index != current_index:
                logger.warning(f"通道{self.channel_number}频点索引超出范围: {current_index}/{total_count}, 修正为{valid_index}")

            # 更新内部状态
            self.frequency_index = valid_index
            if not hasattr(self, 'total_frequencies') or self.total_frequencies == 0:
                self.total_frequencies = total_count
            self.frequency_status = status

            # 生成进度文本
            if total_count > 1:
                # 使用稳定的总频点数
                display_total = self.total_frequencies
                progress_text = f"({valid_index}/{display_total})"
            elif total_count == 1:
                progress_text = "(单频)"
            else:
                progress_text = ""

            # 更新进度显示
            try:
                self.frequency_progress_label.setText(progress_text)
                logger.debug(f"通道{self.channel_number}更新频点进度: {progress_text} ({status})")
            except:
                pass  # 忽略UI更新错误

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新频点进度失败: {e}")

    def clear_frequency_info(self):
        """清空频点信息显示（第三阶段重构：使用频点管理器）"""
        try:
            # 使用频点管理器清空频点信息
            self.frequency_manager.clear_frequency_info()

        except Exception as e:
            logger.error(f"通道{self.channel_number}清空频点信息失败: {e}")

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
                # 保持现有的测试结果显示
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
                font-size: 11pt;  /* 字体优化：从10pt增加到11pt */
                font-weight: bold;
                border-radius: 4px;
                padding: 4px 8px;
                text-align: center;
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

            # 修复设置与结果标签相同的字体大小（24pt）
            self.grade_label.setStyleSheet(f"""
                font-size: 24pt;  /* 与结果标签保持一致的大字体 */
                font-weight: bold;
                border-radius: 4px;
                padding: 4px 8px;
                text-align: center;
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
                else:
                    # 如果没有传入档位，则计算档位
                    rs_grade, rct_grade = self._calculate_grades(self.rs_value, self.rct_value)
                    grade_text = f"{rs_grade}-{rct_grade}"

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
        self.stop_test(clear_results=True)  # 强制清除结果
        self.battery_code_edit.clear()
        self.voltage_label.setText("0.000")
        self.rs_label.setText("0.000")
        self.rct_label.setText("0.000")
        self.clear_frequency_info()

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

            # 🧹 额外清理：清除频点信息
            self.clear_frequency_info()

            # 🧹 额外清理：重置离群率
            self.outlier_rate_result = "--"
            if hasattr(self, 'outlier_rate_label'):
                self.outlier_rate_label.setText("等待")

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
        """检测到新电池时的处理（委托给事件处理器）"""
        self.event_processor.on_new_battery_detected()

    def on_battery_removed(self):
        """电池移除时的处理（委托给事件处理器）"""
        self.event_processor.on_battery_removed()



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
        # 委托给数据更新处理器
        self.data_updater.update_test_count(count)

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
                            font-size: 14pt;
                            font-weight: bold;
                            padding: 8px;
                            border-radius: 6px;
                            text-align: center;
                        }
                    """)
                else:
                    self.channel_title.setStyleSheet("""
                        QLabel {
                            background-color: #95a5a6;
                            color: #7f8c8d;
                            font-size: 14pt;
                            font-weight: bold;
                            padding: 8px;
                            border-radius: 6px;
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

    def _calculate_grades(self, rs_value: float, rct_value: float) -> tuple:
        """
        计算Rs和Rct档位（已弃用：第三阶段重构，使用测试判定管理器）

        Args:
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)

        Returns:
            (rs_grade, rct_grade) 档位编号
        """
        return self.test_controller.calculate_grades(rs_value, rct_value)

    def _judge_test_result(self, voltage: float, rs_value: float, rct_value: float) -> tuple:
        """
        判定测试结果（已弃用：第三阶段重构，使用测试判定管理器）

        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)

        Returns:
            (is_pass, fail_items) 是否合格和不合格项目列表
        """
        return self.test_controller.judge_test_result(voltage, rs_value, rct_value)

    def _get_fail_result_display(self, fail_items: Optional[list]) -> tuple:
        """
        根据失败项目获取结果显示文本和样式（组合显示多个失败原因）

        Args:
            fail_items: 失败项目列表，如 ["电压", "Rs", "Rct"]

        Returns:
            (result_text, result_style) 结果文本和样式名称
        """
        try:

            if not fail_items or len(fail_items) == 0:
                # 没有失败项目，但标记为不合格（可能是其他原因）
                return "不合格", "resultFail"

            # 增强组合显示多个失败项目，支持异常状态
            # 按优先级排序失败项目（异常状态优先级最高）
            priority_order = ["异常", "接触不良", "电池异常", "硬件异常", "电压", "离群率", "Rs", "Rct"]
            sorted_fail_items = []

            # 按优先级添加失败项目
            for item in priority_order:
                if item in fail_items:
                    sorted_fail_items.append(item)

            # 添加其他不在优先级列表中的失败项目
            for item in fail_items:
                if item not in priority_order and item not in sorted_fail_items:
                    sorted_fail_items.append(item)

            # 增强组合显示文本，特殊处理异常状态
            if len(sorted_fail_items) == 1:
                item = sorted_fail_items[0]
                if item in ["异常", "接触不良", "电池异常", "硬件异常"]:
                    result_text = f"不合格-{item}"
                else:
                    result_text = f"不合格-{item}"
            else:
                # 多个失败项目时，如果包含异常状态，优先显示异常
                if any(item in ["异常", "接触不良", "电池异常", "硬件异常"] for item in sorted_fail_items):
                    exception_items = [item for item in sorted_fail_items if item in ["异常", "接触不良", "电池异常", "硬件异常"]]
                    if len(exception_items) == 1:
                        result_text = f"不合格-{exception_items[0]}"
                    else:
                        result_text = f"不合格-{'/'.join(exception_items)}"
                else:
                    result_text = f"不合格-{'/'.join(sorted_fail_items)}"

            # 增强根据最高优先级的失败项目确定样式，支持异常状态
            if "异常" in fail_items:
                result_style = "resultException"
            elif "接触不良" in fail_items:
                result_style = "resultContactPoor"
            elif "电池异常" in fail_items:
                result_style = "resultBatteryError"
            elif "硬件异常" in fail_items:
                result_style = "resultHardwareError"
            elif "电压" in fail_items:
                result_style = "resultFailV"
            elif "离群率" in fail_items:
                result_style = "resultFailOutlier"
            elif "Rs" in fail_items:
                result_style = "resultFailRs"
            elif "Rct" in fail_items:
                result_style = "resultFailRct"
            else:
                result_style = "resultFail"

            return result_text, result_style

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
        # 委托给测试控制器处理
        self.test_controller.complete_test_with_judgment(voltage, rs_value, rct_value)

    def complete_test_with_judgment_enhanced(self, voltage: float, rs_value: float, rct_value: float, outlier_result: Optional[str] = None):
        """
        完成测试并自动判定结果（增强版：包含离群率检测）
        使用现有的test_judgment_manager进行判断，避免重复实现判断逻辑

        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)
            outlier_result: 离群率检测结果
        """
        try:
            logger.info(f"通道{self.channel_number}开始增强判定: V={voltage:.3f}V, Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ, 离群率={outlier_result}")

            # 检查数据有效性，避免使用0值进行判断
            if rs_value == 0.0 and rct_value == 0.0:
                logger.warning(f"通道{self.channel_number} 检测到Rs和Rct为0，数据未准备好，跳过判断")
                return

            # 保存Rs/Rct值到实例属性，确保统计能获取到正确的值
            self.rs_value = rs_value
            self.rct_value = rct_value
            self.voltage = voltage

            # 修复使用后端test_result_manager进行基础判断，然后手动处理离群率
            try:
                # 先使用后端测试结果管理器进行基础判断（电压、Rs、Rct）
                is_pass, fail_items = self.test_result_manager.judge_test_result(voltage, rs_value, rct_value)

                # 修复手动处理离群率检测，正确处理None和各种状态
                if outlier_result is not None and outlier_result not in ["PASS", "--", "已禁用", "无数据", "检测失败"]:
                    # 检查是否启用离群检测
                    try:
                        from backend.outlier_detection_manager import OutlierDetectionManager
                        outlier_manager = OutlierDetectionManager()
                        config = outlier_manager.get_detection_config()

                        if config.get('is_enabled', False):
                            fail_items.append("离群率")
                            is_pass = False
                            logger.debug(f"通道{self.channel_number}离群率不合格: {outlier_result}")
                    except Exception as e:
                        logger.debug(f"检查离群检测配置失败: {e}")
                elif outlier_result is None:
                    # 修复当outlier_result为None时，检查是否启用了离群检测但没有基准数据
                    try:
                        from backend.outlier_detection_manager import OutlierDetectionManager
                        outlier_manager = OutlierDetectionManager()
                        config = outlier_manager.get_detection_config()

                        if config.get('is_enabled', False):
                            logger.warning(f"通道{self.channel_number}离群检测已启用但outlier_result为None，可能缺少基准数据")
                            # 不影响判断结果，只记录警告
                    except Exception as e:
                        logger.debug(f"检查离群检测配置失败: {e}")

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
        安排延迟判断（委托给事件处理器）

        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)
            outlier_result: 离群率检测结果
            backend_result: 后端判断结果 {'is_pass': bool, 'fail_items': list}
        """
        # 委托给事件处理器
        self.event_processor.schedule_delayed_judgment(voltage, rs_value, rct_value, outlier_result, backend_result)
        # 延迟判断逻辑已移到事件处理器中

    # 延迟判断执行功能已移到事件处理器中

    def _schedule_delayed_completion(self, is_pass: bool, rs_grade: int, rct_grade: int, fail_items: Optional[list] = None):
        """
        安排延迟完成显示（委托给事件处理器）

        Args:
            is_pass: 是否合格
            rs_grade: Rs档位
            rct_grade: Rct档位
            fail_items: 失败项目列表
        """
        # 委托给事件处理器
        self.event_processor.schedule_delayed_completion(is_pass, rs_grade, rct_grade, fail_items)

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
        由容器触发的结果显示方法（委托给事件处理器）

        Args:
            is_pass: 是否合格
            rs_grade: Rs档位
            rct_grade: Rct档位
            fail_items: 失败项目列表
        """
        # 委托给事件处理器
        self.event_processor.trigger_result_display(is_pass, rs_grade, rct_grade, fail_items)

    # 容量预测功能已移到测试控制器中

    # 容量预测显示功能已移到测试控制器中

    # 容量预测功能已移到测试控制器中

    # SOH和容量预测显示功能已移到测试控制器中

    # 容量预测执行功能已移到测试控制器中

    # 容量预测数据保存功能已移到测试控制器中

    def _set_test_exception(self, error_type: str, error_message: str):
        """
        设置测试异常状态

        Args:
            error_type: 异常类型
            error_message: 异常消息
        """
        try:
            logger.error(f"🔧 [异常处理] 通道{self.channel_number} 设置测试异常: {error_type} - {error_message}")

            # 设置异常显示
            self.result_label.setText("异常")
            self.result_label.setStyleSheet("""
                QLabel {
                    background-color: #ff6b6b;
                    color: white;
                    font-size: 24pt;
                    font-weight: bold;
                    border-radius: 8px;
                    padding: 10px;
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

    def set_test_completed(self, is_pass: bool, rs_grade: int, rct_grade: int, fail_items: Optional[list] = None):
        """
        设置测试完成状态

        Args:
            is_pass: 是否合格
            rs_grade: Rs档位
            rct_grade: Rct档位
            fail_items: 失败项目列表，如 ["电压", "Rs", "Rct"]
        """
        try:
            # 修复直接阻止无效数据显示，只允许有效数据设置UI
            # 检查数据是否有效（Rs/Rct档位必须有效）
            has_valid_data = (rs_grade is not None and rct_grade is not None and
                            rs_grade != '--' and rct_grade != '--')

            # 如果数据无效，直接跳过，不设置UI
            if not has_valid_data:
                logger.warning(f"🔧 通道{self.channel_number}数据无效(Rs档位={rs_grade}, Rct档位={rct_grade})，跳过UI设置")
                return

            # 修复统一使用completion_manager的_test_completed标志，避免重复标志
            if hasattr(self, 'completion_manager') and self.completion_manager:
                if self.completion_manager.is_test_completed():
                    logger.warning(f"通道{self.channel_number}测试已完成，跳过重复设置")
                    return
            else:
                # 如果没有completion_manager，使用本地标志作为备用
                if hasattr(self, '_test_completed') and self._test_completed:
                    logger.warning(f"通道{self.channel_number}测试已完成，跳过重复设置（备用检查）")
                    return

            # 标记测试已完成（保留作为备用）
            self._test_completed = True

            # 记录测试结束时间
            self.test_end_time = datetime.now()

            logger.info(f"通道{self.channel_number}设置测试完成状态: {'合格' if is_pass else '不合格'}, Rs档位={rs_grade}, Rct档位={rct_grade}")

            # 设置显示逻辑：左侧显示档位/状态，右侧显示测试结果
            if is_pass:
                # 合格时：左侧显示档位，右侧显示"合格"
                grade_text = f"{rs_grade}-{rct_grade}"
                self.grade_label.setText(grade_text)
                self.grade_label.setObjectName("gradePass")

                # 右侧显示合格状态
                self.result_label.setText("合格")
                self.result_label.setObjectName("resultPass")
            else:
                # 不合格时：左侧显示"不合格"，右侧显示失败原因
                self.grade_label.setText("不合格")
                self.grade_label.setObjectName("gradeFail")

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

            # 修复确保离群率数据正确保存
            outlier_result = getattr(self, 'outlier_rate_result', '--')
            frequency_deviations = getattr(self, 'frequency_deviations', {})
            max_deviation_percent = getattr(self, 'max_deviation_percent', 0.0)
            baseline_filename = getattr(self, 'baseline_filename', '')
            baseline_id = getattr(self, 'baseline_id', None)

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
                # 修复离群率相关数据
                'outlier_result': outlier_result,
                'outlier_rate': outlier_result,  # 兼容字段名
                'frequency_deviations': frequency_deviations,
                'max_deviation_percent': max_deviation_percent,
                'baseline_filename': baseline_filename,
                'baseline_id': baseline_id,
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
            try:
                if hasattr(self, '_perform_capacity_prediction_if_enabled'):
                    self._perform_capacity_prediction_if_enabled()
                else:
                    logger.debug(f"通道{self.channel_number}容量预测方法不存在，跳过")
            except Exception as e:
                logger.warning(f"通道{self.channel_number}容量预测失败: {e}")

            self.test_completed.emit(self.channel_number, self.test_result)

            logger.info(f"通道{self.channel_number}测试完成状态已设置: {'合格' if is_pass else '不合格'}, 档位{rs_grade}-{rct_grade}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}设置测试完成状态失败: {e}")

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
                # 离群率相关数据
                'outlier_result': getattr(self, 'outlier_rate_result', '--'),
                'outlier_rate': getattr(self, 'outlier_rate_result', '--'),  # 兼容字段名
                'frequency_deviations': getattr(self, 'frequency_deviations', {}),
                'max_deviation_percent': getattr(self, 'max_deviation_percent', 0.0),
                'baseline_filename': getattr(self, 'baseline_filename', ''),
                'baseline_id': getattr(self, 'baseline_id', None)
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
                # 新增离群率相关数据
                'outlier_result': '--',
                'outlier_rate': '--',  # 兼容字段名
                'frequency_deviations': {},
                'max_deviation_percent': 0.0
            }

            # 发送异常完成信号
            self.test_completed.emit(self.channel_number, self.test_result)

            logger.warning(f"通道{self.channel_number}异常状态已设置: {exception_type} - {error_message}")

        except Exception as e:
            logger.error(f"通道{self.channel_number}设置异常状态失败: {e}")


# ===== 简化的测试结果管理器类 =====

class SimpleTestResultManager:
    """简化的测试结果管理器，用于UI层的基本判断"""

    def __init__(self, config_manager):
        self.config_manager = config_manager
        logger.debug("简化测试结果管理器初始化完成")

    def calculate_grades(self, rs_value: float, rct_value: float) -> tuple:
        """计算Rs和Rct档位"""
        try:
            # 获取Rs档位配置
            rs_grade_count = self.config_manager.get('impedance.rs_grade_count', 3)
            rs_thresholds = []
            for i in range(1, rs_grade_count + 1):
                threshold = self.config_manager.get(f'impedance.rs_grade_{i}_max', 10.0 + i * 5.0)
                rs_thresholds.append(threshold)

            # 计算Rs档位
            rs_grade = rs_grade_count  # 默认最高档位
            for i, threshold in enumerate(rs_thresholds):
                if rs_value <= threshold:
                    rs_grade = i + 1
                    break

            # 获取Rct档位配置
            rct_grade_count = self.config_manager.get('impedance.rct_grade_count', 3)
            rct_thresholds = []
            for i in range(1, rct_grade_count + 1):
                threshold = self.config_manager.get(f'impedance.rct_grade_{i}_max', 5.0 + i * 2.0)
                rct_thresholds.append(threshold)

            # 计算Rct档位
            rct_grade = rct_grade_count  # 默认最高档位
            for i, threshold in enumerate(rct_thresholds):
                if rct_value <= threshold:
                    rct_grade = i + 1
                    break

            return rs_grade, rct_grade

        except Exception as e:
            logger.error(f"计算档位失败: {e}")
            return 3, 3  # 默认档位

    def judge_test_result(self, voltage: float, rs_value: float, rct_value: float, outlier_result: Optional[str] = None, channel_num: Optional[int] = None) -> Tuple[bool, List[str]]:
        """
        判断测试结果（简化版本）

        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)
            outlier_result: 离群率检测结果（"PASS"或偏差百分比）
            channel_num: 通道号（用于调试日志）

        Returns:
            (is_pass, fail_items) 元组
        """
        try:
            fail_items = []

            # 电压判断
            voltage_min = self.config_manager.get('test_config.voltage_range.min', 3.0)
            voltage_max = self.config_manager.get('test_config.voltage_range.max', 4.0)
            if voltage < voltage_min or voltage > voltage_max:
                fail_items.append("电压")

            # Rs判断
            rs_min = self.config_manager.get('impedance.rs_min', 10.0)
            rs_max = self.config_manager.get('impedance.rs_max', 18.0)
            if rs_value < rs_min or rs_value > rs_max:
                fail_items.append("Rs")

            # Rct判断
            rct_min = self.config_manager.get('impedance.rct_min', 0.2)
            rct_max = self.config_manager.get('impedance.rct_max', 10.0)
            if rct_value < rct_min or rct_value > rct_max:
                fail_items.append("Rct")

            # 离群率判断（如果提供了离群率结果）
            if outlier_result and outlier_result not in ["PASS", "--", "已禁用", "无数据", "检测失败"]:
                fail_items.append("离群率")

            is_pass = len(fail_items) == 0

            if channel_num:
                if is_pass:
                    logger.debug(f"通道{channel_num}测试合格: 电压={voltage:.3f}V, Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ, 离群率={outlier_result}")
                else:
                    logger.debug(f"通道{channel_num}测试不合格: 失败项目={fail_items}")

            return is_pass, fail_items

        except Exception as e:
            logger.error(f"判断测试结果失败: {e}")
            return False, ["系统错误"]




class BasicTestResultManager:
    """最基本的测试结果管理器，作为备用"""

    def __init__(self, config_manager):
        self.config_manager = config_manager
        logger.debug("基本测试结果管理器初始化完成")

    def calculate_grades(self, rs_value: float, rct_value: float) -> tuple:
        """计算档位（基本版本）"""
        # 简单的档位计算
        rs_grade = 1 if rs_value <= 15.0 else (2 if rs_value <= 20.0 else 3)
        rct_grade = 1 if rct_value <= 7.0 else (2 if rct_value <= 12.0 else 3)
        return rs_grade, rct_grade

    def judge_test_result(self, voltage: float, rs_value: float, rct_value: float, channel_num: Optional[int] = None) -> tuple:
        """判断测试结果（基本版本）"""
        fail_items = []

        # 基本判断逻辑
        if voltage < 3.0 or voltage > 4.0:
            fail_items.append("电压")
        if rs_value < 10.0 or rs_value > 18.0:
            fail_items.append("Rs")
        if rct_value < 5.0 or rct_value > 10.0:
            fail_items.append("Rct")

        is_pass = len(fail_items) == 0
        return is_pass, fail_items
