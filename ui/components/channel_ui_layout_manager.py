# -*- coding: utf-8 -*-
"""
通道UI布局管理器
负责单通道显示组件的UI布局创建和样式管理

Author: Jack
Date: 2025-01-30
"""

import logging
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QProgressBar, QFrame, QLineEdit, QSizePolicy, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class ChannelUILayoutManager:
    """通道UI布局管理器"""
    
    def __init__(self, channel_number: int, parent_widget):
        """
        初始化UI布局管理器
        
        Args:
            channel_number: 通道号
            parent_widget: 父组件
        """
        self.channel_number = channel_number
        self.parent_widget = parent_widget
        self.ui_elements = {}  # 存储UI元素引用
        
    def create_main_layout(self):
        """创建主布局"""
        try:
            # 创建主布局
            main_layout = QVBoxLayout(self.parent_widget)
            main_layout.setContentsMargins(2, 2, 2, 2)
            main_layout.setSpacing(2)

            # 创建分组框
            group_box = QGroupBox()
            group_box.setObjectName("channelGroup")
            main_layout.addWidget(group_box)

            # 创建自定义标题布局
            self._create_custom_title(group_box)

            # 获取或创建内容布局
            content_layout = group_box.layout()
            if content_layout is None:
                content_layout = QVBoxLayout(group_box)
                content_layout.setContentsMargins(6, 8, 6, 6)
                content_layout.setSpacing(3)

            # 创建显示区域
            self._create_display_areas(content_layout)
            
            return main_layout
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}创建主布局失败: {e}")
            return None
    
    def _create_display_areas(self, layout):
        """创建显示区域 - 紧凑2列布局"""
        # 创建各个区域
        self._create_main_content_area(layout)
        self._create_progress_area(layout)
        self._create_result_area(layout)

    def _create_main_content_area(self, layout):
        """创建主内容区域 - 2列布局"""
        # 创建主内容容器
        main_container = QFrame()
        main_container.setObjectName("mainContentContainer")
        main_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        main_layout = QHBoxLayout(main_container)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(4, 6, 4, 6)

        # 左列：基本信息
        left_column = self._create_left_column()
        main_layout.addLayout(left_column, 3)  # 左列占3份权重

        # 右列：阻抗值显示
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

        # 添加弹性空间，确保内容顶部对齐
        left_column.addStretch()

        return left_column

    def _create_count_time_area(self, layout):
        """创建测试计数和测试时间区域"""
        count_time_layout = QHBoxLayout()
        count_time_layout.setSpacing(8)
        count_time_layout.setContentsMargins(0, 0, 0, 2)

        # 测试计数显示
        count_label = QLabel("测试计数:")
        count_label.setStyleSheet("font-size: 10pt; color: #7f8c8d; font-weight: bold;")
        count_time_layout.addWidget(count_label)

        test_count_label = QLabel("0")
        test_count_label.setObjectName("countLabel")
        test_count_label.setStyleSheet("font-size: 11pt; color: #27ae60; font-weight: bold;")
        count_time_layout.addWidget(test_count_label)
        self.ui_elements['test_count_label'] = test_count_label

        # 分隔符
        count_time_layout.addWidget(QLabel("|"))

        # 测试时间显示
        time_label = QLabel("测试用时:")
        time_label.setStyleSheet("font-size: 10pt; color: #7f8c8d; font-weight: bold;")
        count_time_layout.addWidget(time_label)

        test_time_label = QLabel("00:00:00")
        test_time_label.setObjectName("timeLabel")
        count_time_layout.addWidget(test_time_label)
        self.ui_elements['test_time_label'] = test_time_label

        count_time_layout.addStretch()
        layout.addLayout(count_time_layout)

    def _create_battery_code_area(self, layout):
        """创建电池码输入区域"""
        battery_layout = QHBoxLayout()
        battery_layout.setSpacing(4)

        battery_label = QLabel("电池码:")
        battery_label.setStyleSheet("font-size: 10pt; color: #7f8c8d; font-weight: bold;")
        battery_layout.addWidget(battery_label)

        battery_code_edit = QLineEdit()
        battery_code_edit.setObjectName("batteryCodeEdit")
        battery_code_edit.setPlaceholderText("扫码或输入")
        battery_layout.addWidget(battery_code_edit)
        battery_layout.addStretch()  # 添加弹性空间
        self.ui_elements['battery_code_edit'] = battery_code_edit

        layout.addLayout(battery_layout)

    def _create_voltage_area(self, layout):
        """创建电压显示区域"""
        voltage_layout = QHBoxLayout()
        voltage_layout.setSpacing(4)

        voltage_label = QLabel("电压(V):")
        voltage_label.setStyleSheet("font-size: 10pt; color: #7f8c8d; font-weight: bold;")
        voltage_layout.addWidget(voltage_label)

        voltage_value_label = QLabel("0.000")
        voltage_value_label.setObjectName("dataLabel")
        voltage_layout.addWidget(voltage_value_label)
        voltage_layout.addStretch()
        self.ui_elements['voltage_label'] = voltage_value_label

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

        # Jack要求移除Rsei显示区域（SEI膜电阻）
        # self._create_compact_impedance_area(right_column, "Rsei(mΩ)", "rsei")

        # 保持移除继续隐藏Rp/Rs阻抗比显示
        # self._create_compact_impedance_area(right_column, "Rp/Rs", "impedance_ratio")

        # 移除离群率显示区域（用户要求不再显示）
        # self._create_outlier_rate_area(right_column)

        # 移除取消容量预测显示区域（用户要求暂时不用）
        # self._create_capacity_prediction_area(right_column)

        # 添加弹性空间
        right_column.addStretch()

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
        title_label.setStyleSheet("font-size: 10pt; color: #7f8c8d; font-weight: bold;")
        impedance_layout.addWidget(title_label)

        # 数值标签
        value_label = QLabel("0.000")
        value_label.setObjectName(f"{object_name}Value")
        impedance_layout.addWidget(value_label)
        impedance_layout.addStretch()

        # 保存数值标签引用
        if object_name == "rs":
            self.ui_elements['rs_label'] = value_label
        elif object_name == "rct":
            self.ui_elements['rct_label'] = value_label
        # Jack要求移除Rsei标签引用
        # elif object_name == "rsei":
        #     self.ui_elements['rsei_label'] = value_label
        # 保持移除继续隐藏阻抗比标签引用
        # elif object_name == "impedance_ratio":
        # self.ui_elements['impedance_ratio_label'] = value_label

        layout.addLayout(impedance_layout)

    def _create_outlier_rate_area(self, layout):
        """🔧 已移除：离群率显示区域（用户要求不再显示）"""
        # 离群率功能已完全移除，不再创建任何UI元素
        # 这样可以为阻抗值显示腾出更多空间
        pass

    def _create_capacity_prediction_area(self, layout):
        """🔧 已移除：创建容量预测显示区域（用户要求暂时不用）"""
        # 移除取消容量预测显示，用户要求暂时不用
        pass

        # 原始代码已注释：
        # capacity_layout = QHBoxLayout()
        # capacity_layout.setSpacing(4)
        # capacity_label = QLabel("容量:")
        # capacity_label.setStyleSheet("font-size: 10pt; color: #7f8c8d; font-weight: bold;")
        # capacity_layout.addWidget(capacity_label)
        # capacity_value_label = QLabel("--")
        # capacity_value_label.setObjectName("capacityPredictionLabel")
        # capacity_value_label.setStyleSheet("font-size: 10pt; color: #e67e22; font-weight: bold;")
        # capacity_layout.addWidget(capacity_value_label)
        # capacity_layout.addStretch()
        # self.ui_elements['capacity_prediction_label'] = capacity_value_label
        # layout.addLayout(capacity_layout)

    def _create_progress_area(self, layout):
        """创建进度条区域"""
        # 添加分隔空间
        layout.addSpacing(8)

        # 创建进度条
        progress_bar = QProgressBar()
        progress_bar.setObjectName("testProgressBar")
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("进度: %p%")
        layout.addWidget(progress_bar)
        self.ui_elements['progress_bar'] = progress_bar

    def _create_result_area(self, layout):
        """创建测试结果显示区域（档位+判定双区域格式）- 工业设计风格优化"""
        # 添加分隔空间
        layout.addSpacing(8)  # 增加间距，提升视觉层次

        # 创建结果容器
        result_container = QFrame()
        result_container.setObjectName("resultContainer")
        result_layout = QHBoxLayout(result_container)
        result_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距，让区域占满宽度
        result_layout.setSpacing(8)  # 增加间距，符合苹果设计语言

        # 档位显示区域 (1/3宽度) - 紧凑优化，给上方数据更多空间
        grade_label = QLabel("--")
        grade_label.setObjectName("gradeDisplay")
        grade_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grade_label.setFixedHeight(80)  # 减小高度至80px，节省空间给上方数据显示
        grade_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        result_layout.addWidget(grade_label, 1)  # 占1份权重
        self.ui_elements['grade_label'] = grade_label

        # 判定结果显示区域 (2/3宽度) - 紧凑优化，给上方数据更多空间
        result_label = QLabel("待测试")
        result_label.setObjectName("resultWaiting")
        result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_label.setFixedHeight(80)  # 减小高度至80px，节省空间给上方数据显示
        result_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        result_layout.addWidget(result_label, 2)  # 占2份权重
        self.ui_elements['result_label'] = result_label

        layout.addWidget(result_container)

    def _create_frequency_display(self, layout):
        """创建频点显示区域"""
        # ===== 频点显示功能暂时屏蔽 =====
        # 说明：为简化当前界面，专注于核心测试功能，暂时隐藏频点显示
        # 如需启用，可调用 enable_frequency_display(True)
        pass

    def get_ui_element(self, name: str):
        """获取UI元素引用"""
        return self.ui_elements.get(name)
    
    def get_all_ui_elements(self):
        """获取所有UI元素引用"""
        return self.ui_elements.copy()

    def _create_custom_title(self, group_box):
        """创建自定义标题，包含通道号和电池状态指示器"""
        try:
            # 创建标题容器 - 紧凑高度优化
            title_widget = QWidget()
            title_widget.setFixedHeight(32)  # 限制标题容器高度，给Rs/Rct更多空间
            title_layout = QHBoxLayout(title_widget)
            title_layout.setContentsMargins(6, 2, 6, 2)  # 减小垂直边距：4→2
            title_layout.setSpacing(6)  # 减小间距：8→6

            # 通道号标签 - 减小字体
            channel_title = QLabel(f"通道 {self.channel_number}")
            channel_title.setObjectName("channelTitle")
            channel_title.setStyleSheet("font-weight: bold; font-size: 10pt;")  # 减小字体：12pt→10pt
            title_layout.addWidget(channel_title)

            # 添加弹性空间
            title_layout.addStretch()

            # 电池状态指示器 - 在电池侦测模式下始终可见
            battery_status_indicator = QLabel("○")
            battery_status_indicator.setObjectName("batteryStatusIndicator")
            battery_status_indicator.setStyleSheet("""
                QLabel {
                    font-size: 16pt;
                    font-weight: bold;
                    color: #95a5a6;
                    min-width: 24px;
                    min-height: 24px;
                    max-width: 24px;
                    max-height: 24px;
                    text-align: center;
                    border-radius: 12px;
                    padding: 1px;
                    background-color: rgba(149, 165, 166, 0.1);
                    border: 1px solid rgba(149, 165, 166, 0.3);
                }
            """)
            battery_status_indicator.setToolTip("电池状态：未知")
            # 确保电池状态指示器始终可见
            battery_status_indicator.setVisible(True)
            battery_status_indicator.show()
            battery_status_indicator.raise_()  # 确保在最上层显示
            title_layout.addWidget(battery_status_indicator)

            # 将标题容器设置为分组框的标题
            group_box.setTitle("")  # 清空默认标题

            # 获取分组框的布局并在顶部插入标题
            if group_box.layout() is None:
                # 如果还没有布局，先创建一个
                temp_layout = QVBoxLayout(group_box)
                temp_layout.setContentsMargins(6, 8, 6, 6)
                temp_layout.setSpacing(3)

            # 在分组框布局的顶部插入标题
            group_box.layout().insertWidget(0, title_widget)

            # 保存电池状态指示器的引用
            self.ui_elements['battery_status_indicator'] = battery_status_indicator
            self.ui_elements['channel_title'] = channel_title

            logger.debug(f"通道{self.channel_number}自定义标题创建完成")

        except Exception as e:
            logger.error(f"通道{self.channel_number}创建自定义标题失败: {e}")
            # 回退到默认标题
            group_box.setTitle(f"通道 {self.channel_number}")

    def get_rsei_label(self):
        """
        获取Rsei标签

        Returns:
            Rsei标签对象或None
        """
        return self.ui_elements.get('rsei_label')
