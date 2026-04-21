#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
档位设置UI管理器
负责档位设置界面的整体管理

Author: Jack
Date: 2025-06-04
"""

import logging
from typing import Dict, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QCheckBox, QPushButton, QTextEdit, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont

# 导入安全数值输入框
from .safe_double_spinbox import SafeDoubleSpinBox

logger = logging.getLogger(__name__)


class GradeSettingsUIManager(QObject):
    """
    档位设置UI管理器
    
    职责：
    - 管理档位设置的整体界面布局
    - 协调各个UI组件
    - 处理界面交互逻辑
    """
    
    # 信号定义
    settings_changed = pyqtSignal()  # 设置变更信号
    
    def __init__(self, parent_widget: QWidget):
        """
        初始化档位设置UI管理器
        
        Args:
            parent_widget: 父窗口部件
        """
        super().__init__(parent_widget)
        
        self.parent_widget = parent_widget
        
        # UI组件
        self.voltage_widgets = {}
        self.rs_widgets = {}
        self.rct_widgets = {}
        
        self._loading = False  # 防止加载时触发变更信号
        
        logger.debug("档位设置UI管理器初始化完成")
    
    def create_main_layout(self) -> QVBoxLayout:
        """创建主布局"""
        try:
            main_layout = QVBoxLayout(self.parent_widget)
            main_layout.setContentsMargins(20, 20, 20, 20)
            main_layout.setSpacing(15)
            
            # 创建第一行：离群检测 + 电压范围
            first_row = QHBoxLayout()
            first_row.setSpacing(15)

            # 离群检测设置（预留空间，由外部管理器添加）
            # 注意：离群检测组将由 grade_settings_widget.py 添加

            # 电压范围设置
            voltage_group = self.create_voltage_range_group()
            first_row.addWidget(voltage_group)

            main_layout.addLayout(first_row)
            
            # 创建第二行：Rs档位 + Rct档位
            second_row = QHBoxLayout()
            second_row.setSpacing(15)
            
            # Rs档位设置
            rs_group = self.create_rs_grade_group()
            second_row.addWidget(rs_group)
            
            # Rct档位设置
            rct_group = self.create_rct_grade_group()
            second_row.addWidget(rct_group)
            
            main_layout.addLayout(second_row)
            
            # 添加弹性空间
            main_layout.addStretch()
            
            logger.debug("主布局创建完成")
            return main_layout
            
        except Exception as e:
            logger.error(f"创建主布局失败: {e}")
            return QVBoxLayout(self.parent_widget)
    
    def create_voltage_range_group(self) -> QGroupBox:
        """创建电压范围设置组"""
        try:
            group = QGroupBox("电压范围设置")
            group.setFont(QFont("", 10, QFont.Weight.Bold))
            
            layout = QVBoxLayout(group)
            layout.setSpacing(12)
            layout.setContentsMargins(15, 15, 15, 15)
            
            # 电池类型选择
            type_layout = QHBoxLayout()
            type_layout.addWidget(QLabel("电池类型:"))
            
            self.voltage_widgets['battery_type_combo'] = QComboBox()
            self.voltage_widgets['battery_type_combo'].addItems([
                "磷酸铁锂电池 (3.21V)",
                "三元锂电池 (3.70V)",
                "自定义设置"
            ])
            self.voltage_widgets['battery_type_combo'].setToolTip("选择电池类型以使用预设电压参数")
            type_layout.addWidget(self.voltage_widgets['battery_type_combo'])
            
            layout.addLayout(type_layout)
            
            # 电压参数设置
            params_layout = QGridLayout()
            params_layout.setSpacing(10)
            
            # 标准电压
            params_layout.addWidget(QLabel("标准电压:"), 0, 0)
            self.voltage_widgets['standard_voltage_spin'] = SafeDoubleSpinBox()
            self.voltage_widgets['standard_voltage_spin'].setRange(1.000, 10.000)
            self.voltage_widgets['standard_voltage_spin'].setValue(3.210)
            self.voltage_widgets['standard_voltage_spin'].setSuffix(" V")
            self.voltage_widgets['standard_voltage_spin'].setToolTip("设置电池的标准工作电压")
            params_layout.addWidget(self.voltage_widgets['standard_voltage_spin'], 0, 1)
            
            # 简化电压差设置（移除百分比模式）
            params_layout.addWidget(QLabel("电压差:"), 0, 2)
            self.voltage_widgets['voltage_diff_spin'] = SafeDoubleSpinBox()
            self.voltage_widgets['voltage_diff_spin'].setRange(0.001, 2.0)  # 修复最小值改为0.001V
            self.voltage_widgets['voltage_diff_spin'].setValue(0.16)
            self.voltage_widgets['voltage_diff_spin'].setDecimals(3)
            self.voltage_widgets['voltage_diff_spin'].setSingleStep(0.001)
            self.voltage_widgets['voltage_diff_spin'].setSuffix(" V")
            self.voltage_widgets['voltage_diff_spin'].setToolTip("设置电压的允许偏差绝对值")
            params_layout.addWidget(self.voltage_widgets['voltage_diff_spin'], 0, 3)
            
            # 自动计算范围
            self.voltage_widgets['auto_calc_checkbox'] = QCheckBox("自动计算范围")
            self.voltage_widgets['auto_calc_checkbox'].setChecked(True)
            self.voltage_widgets['auto_calc_checkbox'].setToolTip("根据标准电压和容差自动计算有效范围")
            params_layout.addWidget(self.voltage_widgets['auto_calc_checkbox'], 1, 0)
            
            # 最小电压
            params_layout.addWidget(QLabel("最小电压:"), 1, 1)
            self.voltage_widgets['min_voltage_spin'] = SafeDoubleSpinBox()
            self.voltage_widgets['min_voltage_spin'].setRange(0.100, 10.000)
            self.voltage_widgets['min_voltage_spin'].setValue(2.000)
            self.voltage_widgets['min_voltage_spin'].setDecimals(3)  # 修复设置3位小数
            self.voltage_widgets['min_voltage_spin'].setSingleStep(0.001)  # 修复设置步长为0.001
            self.voltage_widgets['min_voltage_spin'].setSuffix(" V")
            self.voltage_widgets['min_voltage_spin'].setEnabled(False)  # 默认禁用，由自动计算控制
            params_layout.addWidget(self.voltage_widgets['min_voltage_spin'], 1, 2)

            # 最大电压
            params_layout.addWidget(QLabel("最大电压:"), 1, 3)
            self.voltage_widgets['max_voltage_spin'] = SafeDoubleSpinBox()
            self.voltage_widgets['max_voltage_spin'].setRange(0.100, 50.000)
            self.voltage_widgets['max_voltage_spin'].setValue(5.000)
            self.voltage_widgets['max_voltage_spin'].setDecimals(3)  # 修复设置3位小数
            self.voltage_widgets['max_voltage_spin'].setSingleStep(0.001)  # 修复设置步长为0.001
            self.voltage_widgets['max_voltage_spin'].setSuffix(" V")
            self.voltage_widgets['max_voltage_spin'].setEnabled(False)  # 默认禁用，由自动计算控制
            params_layout.addWidget(self.voltage_widgets['max_voltage_spin'], 1, 4)
            
            layout.addLayout(params_layout)
            
            # 范围显示
            self.voltage_widgets['range_display'] = QTextEdit()
            self.voltage_widgets['range_display'].setMaximumHeight(60)
            self.voltage_widgets['range_display'].setReadOnly(True)
            self.voltage_widgets['range_display'].setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6;")
            layout.addWidget(self.voltage_widgets['range_display'])
            
            # 连接信号
            self._connect_voltage_signals()

            # 初始化电压范围计算
            self._update_voltage_range()

            logger.debug("电压范围设置组创建完成")
            return group
            
        except Exception as e:
            logger.error(f"创建电压范围设置组失败: {e}")
            return QGroupBox("电压范围设置（创建失败）")
    
    def create_rs_grade_group(self) -> QGroupBox:
        """创建Rs档位设置组"""
        try:
            group = QGroupBox("Rs档位设置")
            group.setFont(QFont("", 10, QFont.Weight.Bold))
            
            layout = QVBoxLayout(group)
            layout.setSpacing(12)
            layout.setContentsMargins(15, 15, 15, 15)
            
            # 档位数量选择
            count_layout = QHBoxLayout()
            count_layout.addWidget(QLabel("档位数量:"))
            
            self.rs_widgets['grade_count_combo'] = QComboBox()
            self.rs_widgets['grade_count_combo'].addItems(["1档", "2档", "3档"])
            self.rs_widgets['grade_count_combo'].setCurrentIndex(2)  # 默认3档
            self.rs_widgets['grade_count_combo'].setToolTip("选择Rs的档位数量")
            count_layout.addWidget(self.rs_widgets['grade_count_combo'])
            
            count_layout.addStretch()
            layout.addLayout(count_layout)
            
            # 范围设置
            range_layout = QGridLayout()
            range_layout.setSpacing(10)
            
            # 最小值
            range_layout.addWidget(QLabel("最小值:"), 0, 0)
            self.rs_widgets['min_value_spin'] = SafeDoubleSpinBox()
            self.rs_widgets['min_value_spin'].setRange(0.001, 999.999)
            self.rs_widgets['min_value_spin'].setValue(0.500)
            self.rs_widgets['min_value_spin'].setSuffix(" mΩ")
            self.rs_widgets['min_value_spin'].setToolTip("Rs的最小值")
            range_layout.addWidget(self.rs_widgets['min_value_spin'], 0, 1)
            
            # 最大值
            range_layout.addWidget(QLabel("最大值:"), 0, 2)
            self.rs_widgets['max_value_spin'] = SafeDoubleSpinBox()
            self.rs_widgets['max_value_spin'].setRange(0.001, 999.999)
            self.rs_widgets['max_value_spin'].setValue(50.000)
            self.rs_widgets['max_value_spin'].setSuffix(" mΩ")
            self.rs_widgets['max_value_spin'].setToolTip("Rs的最大值")
            range_layout.addWidget(self.rs_widgets['max_value_spin'], 0, 3)
            
            # 自动计算
            self.rs_widgets['auto_calc_checkbox'] = QCheckBox("自动计算档位")
            self.rs_widgets['auto_calc_checkbox'].setChecked(True)
            self.rs_widgets['auto_calc_checkbox'].setToolTip("根据最小值和最大值自动计算档位范围")
            range_layout.addWidget(self.rs_widgets['auto_calc_checkbox'], 1, 0, 1, 2)
            
            layout.addLayout(range_layout)
            
            # 手动档位阈值设置（默认隐藏）
            self.rs_widgets['manual_thresholds_group'] = QGroupBox("手动档位阈值")
            manual_layout = QGridLayout(self.rs_widgets['manual_thresholds_group'])
            manual_layout.setSpacing(8)

            # 1档阈值
            manual_layout.addWidget(QLabel("1档最大值:"), 0, 0)
            self.rs_widgets['grade1_max_spin'] = SafeDoubleSpinBox()
            self.rs_widgets['grade1_max_spin'].setRange(0.001, 999.999)
            self.rs_widgets['grade1_max_spin'].setValue(17.000)
            self.rs_widgets['grade1_max_spin'].setSuffix(" mΩ")
            self.rs_widgets['grade1_max_spin'].setToolTip("Rs 1档的最大值")
            manual_layout.addWidget(self.rs_widgets['grade1_max_spin'], 0, 1)

            # 2档阈值
            manual_layout.addWidget(QLabel("2档最大值:"), 0, 2)
            self.rs_widgets['grade2_max_spin'] = SafeDoubleSpinBox()
            self.rs_widgets['grade2_max_spin'].setRange(0.001, 999.999)
            self.rs_widgets['grade2_max_spin'].setValue(33.500)
            self.rs_widgets['grade2_max_spin'].setSuffix(" mΩ")
            self.rs_widgets['grade2_max_spin'].setToolTip("Rs 2档的最大值")
            manual_layout.addWidget(self.rs_widgets['grade2_max_spin'], 0, 3)

            # 3档阈值
            manual_layout.addWidget(QLabel("3档最大值:"), 1, 0)
            self.rs_widgets['grade3_max_spin'] = SafeDoubleSpinBox()
            self.rs_widgets['grade3_max_spin'].setRange(0.001, 999.999)
            self.rs_widgets['grade3_max_spin'].setValue(50.000)
            self.rs_widgets['grade3_max_spin'].setSuffix(" mΩ")
            self.rs_widgets['grade3_max_spin'].setToolTip("Rs 3档的最大值")
            manual_layout.addWidget(self.rs_widgets['grade3_max_spin'], 1, 1)

            # 默认隐藏手动阈值设置
            self.rs_widgets['manual_thresholds_group'].setVisible(False)
            layout.addWidget(self.rs_widgets['manual_thresholds_group'])

            # 档位显示
            self.rs_widgets['grade_display'] = QTextEdit()
            self.rs_widgets['grade_display'].setMaximumHeight(80)
            self.rs_widgets['grade_display'].setReadOnly(True)
            self.rs_widgets['grade_display'].setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6;")
            layout.addWidget(self.rs_widgets['grade_display'])

            # 连接信号
            self._connect_rs_signals()
            
            logger.debug("Rs档位设置组创建完成")
            return group
            
        except Exception as e:
            logger.error(f"创建Rs档位设置组失败: {e}")
            return QGroupBox("Rs档位设置（创建失败）")
    
    def create_rct_grade_group(self) -> QGroupBox:
        """创建Rct档位设置组"""
        try:
            group = QGroupBox("Rct档位设置")
            group.setFont(QFont("", 10, QFont.Weight.Bold))
            
            layout = QVBoxLayout(group)
            layout.setSpacing(12)
            layout.setContentsMargins(15, 15, 15, 15)
            
            # 固定3档说明
            info_label = QLabel("Rct固定为3档")
            info_label.setStyleSheet("color: #6c757d; font-style: italic;")
            layout.addWidget(info_label)
            
            # 范围设置
            range_layout = QGridLayout()
            range_layout.setSpacing(10)
            
            # 最小值
            range_layout.addWidget(QLabel("最小值:"), 0, 0)
            self.rct_widgets['min_value_spin'] = SafeDoubleSpinBox()
            self.rct_widgets['min_value_spin'].setRange(0.001, 999.999)
            self.rct_widgets['min_value_spin'].setValue(5.000)
            self.rct_widgets['min_value_spin'].setSuffix(" mΩ")
            self.rct_widgets['min_value_spin'].setToolTip("Rct的最小值")
            range_layout.addWidget(self.rct_widgets['min_value_spin'], 0, 1)
            
            # 最大值
            range_layout.addWidget(QLabel("最大值:"), 0, 2)
            self.rct_widgets['max_value_spin'] = SafeDoubleSpinBox()
            self.rct_widgets['max_value_spin'].setRange(0.001, 999.999)
            self.rct_widgets['max_value_spin'].setValue(100.000)
            self.rct_widgets['max_value_spin'].setSuffix(" mΩ")
            self.rct_widgets['max_value_spin'].setToolTip("Rct的最大值")
            range_layout.addWidget(self.rct_widgets['max_value_spin'], 0, 3)
            
            # 自动计算
            self.rct_widgets['auto_calc_checkbox'] = QCheckBox("自动计算档位")
            self.rct_widgets['auto_calc_checkbox'].setChecked(True)
            self.rct_widgets['auto_calc_checkbox'].setToolTip("根据最小值和最大值自动计算档位范围")
            range_layout.addWidget(self.rct_widgets['auto_calc_checkbox'], 1, 0, 1, 2)
            
            layout.addLayout(range_layout)

            # 手动档位阈值设置（默认隐藏）
            self.rct_widgets['manual_thresholds_group'] = QGroupBox("手动档位阈值")
            manual_layout = QGridLayout(self.rct_widgets['manual_thresholds_group'])
            manual_layout.setSpacing(8)

            # 1档阈值
            manual_layout.addWidget(QLabel("1档最大值:"), 0, 0)
            self.rct_widgets['grade1_max_spin'] = SafeDoubleSpinBox()
            self.rct_widgets['grade1_max_spin'].setRange(0.001, 999.999)
            self.rct_widgets['grade1_max_spin'].setValue(35.000)
            self.rct_widgets['grade1_max_spin'].setSuffix(" mΩ")
            self.rct_widgets['grade1_max_spin'].setToolTip("Rct 1档的最大值")
            manual_layout.addWidget(self.rct_widgets['grade1_max_spin'], 0, 1)

            # 2档阈值
            manual_layout.addWidget(QLabel("2档最大值:"), 0, 2)
            self.rct_widgets['grade2_max_spin'] = SafeDoubleSpinBox()
            self.rct_widgets['grade2_max_spin'].setRange(0.001, 999.999)
            self.rct_widgets['grade2_max_spin'].setValue(70.000)
            self.rct_widgets['grade2_max_spin'].setSuffix(" mΩ")
            self.rct_widgets['grade2_max_spin'].setToolTip("Rct 2档的最大值")
            manual_layout.addWidget(self.rct_widgets['grade2_max_spin'], 0, 3)

            # 3档阈值
            manual_layout.addWidget(QLabel("3档最大值:"), 1, 0)
            self.rct_widgets['grade3_max_spin'] = SafeDoubleSpinBox()
            self.rct_widgets['grade3_max_spin'].setRange(0.001, 999.999)
            self.rct_widgets['grade3_max_spin'].setValue(100.000)
            self.rct_widgets['grade3_max_spin'].setSuffix(" mΩ")
            self.rct_widgets['grade3_max_spin'].setToolTip("Rct 3档的最大值")
            manual_layout.addWidget(self.rct_widgets['grade3_max_spin'], 1, 1)

            # 默认隐藏手动阈值设置
            self.rct_widgets['manual_thresholds_group'].setVisible(False)
            layout.addWidget(self.rct_widgets['manual_thresholds_group'])

            # 档位显示
            self.rct_widgets['grade_display'] = QTextEdit()
            self.rct_widgets['grade_display'].setMaximumHeight(80)
            self.rct_widgets['grade_display'].setReadOnly(True)
            self.rct_widgets['grade_display'].setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6;")
            layout.addWidget(self.rct_widgets['grade_display'])

            # 连接信号
            self._connect_rct_signals()
            
            logger.debug("Rct档位设置组创建完成")
            return group
            
        except Exception as e:
            logger.error(f"创建Rct档位设置组失败: {e}")
            return QGroupBox("Rct档位设置（创建失败）")
    
    def _connect_voltage_signals(self):
        """连接电压相关信号"""
        try:
            # 特殊处理电池类型选择器，实现数据联动
            if 'battery_type_combo' in self.voltage_widgets:
                self.voltage_widgets['battery_type_combo'].currentIndexChanged.connect(self._on_battery_type_changed)

            # 连接其他电压相关控件
            for widget_name, widget in self.voltage_widgets.items():
                if widget_name == 'battery_type_combo':
                    continue  # 已经单独处理

                if hasattr(widget, 'valueChanged'):
                    widget.valueChanged.connect(self._on_voltage_value_changed)
                elif hasattr(widget, 'currentTextChanged'):
                    widget.currentTextChanged.connect(self._on_settings_changed)
                elif hasattr(widget, 'toggled'):
                    widget.toggled.connect(self._on_voltage_auto_calc_changed)

            logger.debug("电压相关信号连接完成")

        except Exception as e:
            logger.error(f"连接电压相关信号失败: {e}")
    
    def _connect_rs_signals(self):
        """连接Rs相关信号"""
        try:
            for widget_name, widget in self.rs_widgets.items():
                if widget_name == 'auto_calc_checkbox':
                    # 特殊处理自动计算选项
                    widget.toggled.connect(self._on_rs_auto_calc_changed)
                elif widget_name in ['min_value_spin', 'max_value_spin', 'grade_count_combo']:
                    # 范围相关控件变化时更新显示
                    if hasattr(widget, 'valueChanged'):
                        widget.valueChanged.connect(self._on_rs_range_changed)
                    elif hasattr(widget, 'currentTextChanged'):
                        widget.currentTextChanged.connect(self._on_rs_range_changed)
                elif widget_name.startswith('grade') and widget_name.endswith('_max_spin'):
                    # 手动阈值控件变化时更新显示
                    widget.valueChanged.connect(self._on_rs_manual_threshold_changed)
                else:
                    # 其他控件
                    if hasattr(widget, 'valueChanged'):
                        widget.valueChanged.connect(self._on_settings_changed)
                    elif hasattr(widget, 'currentTextChanged'):
                        widget.currentTextChanged.connect(self._on_settings_changed)
                    elif hasattr(widget, 'toggled'):
                        widget.toggled.connect(self._on_settings_changed)

            logger.debug("Rs相关信号连接完成")

        except Exception as e:
            logger.error(f"连接Rs相关信号失败: {e}")
    
    def _connect_rct_signals(self):
        """连接Rct相关信号"""
        try:
            for widget_name, widget in self.rct_widgets.items():
                if widget_name == 'auto_calc_checkbox':
                    # 特殊处理自动计算选项
                    widget.toggled.connect(self._on_rct_auto_calc_changed)
                elif widget_name in ['min_value_spin', 'max_value_spin']:
                    # 范围相关控件变化时更新显示
                    widget.valueChanged.connect(self._on_rct_range_changed)
                elif widget_name.startswith('grade') and widget_name.endswith('_max_spin'):
                    # 手动阈值控件变化时更新显示
                    widget.valueChanged.connect(self._on_rct_manual_threshold_changed)
                else:
                    # 其他控件
                    if hasattr(widget, 'valueChanged'):
                        widget.valueChanged.connect(self._on_settings_changed)
                    elif hasattr(widget, 'currentTextChanged'):
                        widget.currentTextChanged.connect(self._on_settings_changed)
                    elif hasattr(widget, 'toggled'):
                        widget.toggled.connect(self._on_settings_changed)

            logger.debug("Rct相关信号连接完成")

        except Exception as e:
            logger.error(f"连接Rct相关信号失败: {e}")
    
    def _on_settings_changed(self):
        """设置变更处理"""
        try:
            if not self._loading:
                self.settings_changed.emit()
        except Exception as e:
            logger.error(f"设置变更处理失败: {e}")

    def _on_battery_type_changed(self, index: int):
        """处理电池类型变化"""
        try:
            if self._loading:
                return

            # 根据电池类型设置标准电压
            if index == 0:  # 磷酸铁锂电池 (3.21V)
                standard_voltage = 3.210
                logger.debug("选择磷酸铁锂电池，设置标准电压为3.210V")
            elif index == 1:  # 三元锂电池 (3.70V)
                standard_voltage = 3.700
                logger.debug("选择三元锂电池，设置标准电压为3.700V")
            else:  # 自定义设置
                logger.debug("选择自定义设置，保持当前标准电压")
                self._on_settings_changed()
                return

            # 更新标准电压值
            if 'standard_voltage_spin' in self.voltage_widgets:
                self.voltage_widgets['standard_voltage_spin'].setValue(standard_voltage)

            # 触发电压值变化处理（会自动计算范围）
            self._on_voltage_value_changed()

        except Exception as e:
            logger.error(f"处理电池类型变化失败: {e}")

    def _on_voltage_value_changed(self):
        """处理电压值变化"""
        try:
            if self._loading:
                return

            # 如果启用自动计算，更新电压范围
            if ('auto_calc_checkbox' in self.voltage_widgets and
                self.voltage_widgets['auto_calc_checkbox'].isChecked()):
                self._update_voltage_range()

            # 触发设置变更
            self._on_settings_changed()

        except Exception as e:
            logger.error(f"处理电压值变化失败: {e}")

    def _on_voltage_auto_calc_changed(self, checked: bool):
        """处理自动计算选项变化"""
        try:
            if self._loading:
                return

            # 启用/禁用最小最大电压输入框
            if 'min_voltage_spin' in self.voltage_widgets:
                self.voltage_widgets['min_voltage_spin'].setEnabled(not checked)
            if 'max_voltage_spin' in self.voltage_widgets:
                self.voltage_widgets['max_voltage_spin'].setEnabled(not checked)

            # 如果启用自动计算，立即更新范围
            if checked:
                self._update_voltage_range()

            # 触发设置变更
            self._on_settings_changed()

        except Exception as e:
            logger.error(f"处理自动计算选项变化失败: {e}")

    def _update_voltage_range(self):
        """更新电压范围（仅电压差模式）"""
        try:
            if ('standard_voltage_spin' not in self.voltage_widgets or
                'voltage_diff_spin' not in self.voltage_widgets):
                return

            standard_voltage = self.voltage_widgets['standard_voltage_spin'].value()
            voltage_diff = self.voltage_widgets['voltage_diff_spin'].value()

            # 简化只使用电压差计算方式
            # 计算电压范围：最小电压 = 标准电压 - 电压差值，最大电压 = 标准电压 + 电压差值
            min_voltage = standard_voltage - voltage_diff
            max_voltage = standard_voltage + voltage_diff

            # 确保范围合理
            min_voltage = max(0.1, min_voltage)  # 最小不低于0.1V
            max_voltage = min(50.0, max_voltage)  # 最大不超过50V

            # 更新界面显示
            if 'min_voltage_spin' in self.voltage_widgets:
                self.voltage_widgets['min_voltage_spin'].setValue(min_voltage)
            if 'max_voltage_spin' in self.voltage_widgets:
                self.voltage_widgets['max_voltage_spin'].setValue(max_voltage)

            logger.debug(f"电压范围已更新: {standard_voltage}V ±{voltage_diff}V = {min_voltage:.3f}V - {max_voltage:.3f}V")

        except Exception as e:
            logger.error(f"更新电压范围失败: {e}")
    
    def get_voltage_config(self) -> Dict[str, Any]:
        """获取电压配置（仅电压差模式）"""
        try:
            config = {
                'battery_type': self.voltage_widgets['battery_type_combo'].currentIndex(),
                'standard_voltage': self.voltage_widgets['standard_voltage_spin'].value(),
                'auto_calc_range': self.voltage_widgets['auto_calc_checkbox'].isChecked(),
                'min_voltage': self.voltage_widgets['min_voltage_spin'].value(),
                'max_voltage': self.voltage_widgets['max_voltage_spin'].value()
            }

            # 简化只保留电压差配置项
            if 'voltage_diff_spin' in self.voltage_widgets:
                config['voltage_diff'] = self.voltage_widgets['voltage_diff_spin'].value()

            return config
        except Exception as e:
            logger.error(f"获取电压配置失败: {e}")
            return {}
    
    def get_rs_config(self) -> Dict[str, Any]:
        """获取Rs配置"""
        try:
            config = {
                'grade_count': self.rs_widgets['grade_count_combo'].currentIndex() + 1,
                'min_value': self.rs_widgets['min_value_spin'].value(),
                'max_value': self.rs_widgets['max_value_spin'].value(),
                'auto_calc': self.rs_widgets['auto_calc_checkbox'].isChecked()
            }

            # 添加手动阈值设置
            if 'grade1_max_spin' in self.rs_widgets:
                config['grade1_max'] = self.rs_widgets['grade1_max_spin'].value()
            if 'grade2_max_spin' in self.rs_widgets:
                config['grade2_max'] = self.rs_widgets['grade2_max_spin'].value()
            if 'grade3_max_spin' in self.rs_widgets:
                config['grade3_max'] = self.rs_widgets['grade3_max_spin'].value()

            return config
        except Exception as e:
            logger.error(f"获取Rs配置失败: {e}")
            return {}
    
    def get_rct_config(self) -> Dict[str, Any]:
        """获取Rct配置"""
        try:
            config = {
                'grade_count': 3,  # 固定3档
                'min_value': self.rct_widgets['min_value_spin'].value(),
                'max_value': self.rct_widgets['max_value_spin'].value(),
                'auto_calc': self.rct_widgets['auto_calc_checkbox'].isChecked()
            }

            # 添加手动阈值设置
            if 'grade1_max_spin' in self.rct_widgets:
                config['grade1_max'] = self.rct_widgets['grade1_max_spin'].value()
            if 'grade2_max_spin' in self.rct_widgets:
                config['grade2_max'] = self.rct_widgets['grade2_max_spin'].value()
            if 'grade3_max_spin' in self.rct_widgets:
                config['grade3_max'] = self.rct_widgets['grade3_max_spin'].value()

            return config
        except Exception as e:
            logger.error(f"获取Rct配置失败: {e}")
            return {}
    
    def update_voltage_display(self, text: str):
        """更新电压范围显示"""
        try:
            if 'range_display' in self.voltage_widgets:
                self.voltage_widgets['range_display'].setText(text)
        except Exception as e:
            logger.error(f"更新电压范围显示失败: {e}")
    
    def update_rs_display(self, text: str):
        """更新Rs档位显示"""
        try:
            if 'grade_display' in self.rs_widgets:
                self.rs_widgets['grade_display'].setText(text)
        except Exception as e:
            logger.error(f"更新Rs档位显示失败: {e}")
    
    def update_rct_display(self, text: str):
        """更新Rct档位显示"""
        try:
            if 'grade_display' in self.rct_widgets:
                self.rct_widgets['grade_display'].setText(text)
        except Exception as e:
            logger.error(f"更新Rct档位显示失败: {e}")
    
    def load_rs_config(self, config: Dict[str, Any]):
        """加载Rs配置"""
        try:
            self._loading = True

            # 加载基本配置
            if 'grade_count' in config:
                self.rs_widgets['grade_count_combo'].setCurrentIndex(config['grade_count'] - 1)
            if 'min_value' in config:
                self.rs_widgets['min_value_spin'].setValue(config['min_value'])
            if 'max_value' in config:
                self.rs_widgets['max_value_spin'].setValue(config['max_value'])
            if 'auto_calc' in config:
                self.rs_widgets['auto_calc_checkbox'].setChecked(config['auto_calc'])

            # 加载手动阈值配置
            if 'grade1_max' in config and 'grade1_max_spin' in self.rs_widgets:
                self.rs_widgets['grade1_max_spin'].setValue(config['grade1_max'])
            if 'grade2_max' in config and 'grade2_max_spin' in self.rs_widgets:
                self.rs_widgets['grade2_max_spin'].setValue(config['grade2_max'])
            if 'grade3_max' in config and 'grade3_max_spin' in self.rs_widgets:
                self.rs_widgets['grade3_max_spin'].setValue(config['grade3_max'])

            # 更新UI状态
            auto_calc = config.get('auto_calc', True)
            if 'manual_thresholds_group' in self.rs_widgets:
                self.rs_widgets['manual_thresholds_group'].setVisible(not auto_calc)

            # 更新范围显示
            self._update_rs_range_display()

        except Exception as e:
            logger.error(f"加载Rs配置失败: {e}")
        finally:
            self._loading = False

    def load_rct_config(self, config: Dict[str, Any]):
        """加载Rct配置"""
        try:
            self._loading = True

            # 加载基本配置
            if 'min_value' in config:
                self.rct_widgets['min_value_spin'].setValue(config['min_value'])
            if 'max_value' in config:
                self.rct_widgets['max_value_spin'].setValue(config['max_value'])
            if 'auto_calc' in config:
                self.rct_widgets['auto_calc_checkbox'].setChecked(config['auto_calc'])

            # 加载手动阈值配置
            if 'grade1_max' in config and 'grade1_max_spin' in self.rct_widgets:
                self.rct_widgets['grade1_max_spin'].setValue(config['grade1_max'])
            if 'grade2_max' in config and 'grade2_max_spin' in self.rct_widgets:
                self.rct_widgets['grade2_max_spin'].setValue(config['grade2_max'])
            if 'grade3_max' in config and 'grade3_max_spin' in self.rct_widgets:
                self.rct_widgets['grade3_max_spin'].setValue(config['grade3_max'])

            # 更新UI状态
            auto_calc = config.get('auto_calc', True)
            if 'manual_thresholds_group' in self.rct_widgets:
                self.rct_widgets['manual_thresholds_group'].setVisible(not auto_calc)

            # 更新范围显示
            self._update_rct_range_display()

        except Exception as e:
            logger.error(f"加载Rct配置失败: {e}")
        finally:
            self._loading = False

    def load_voltage_config(self, config: Dict[str, Any]):
        """加载电压配置（仅电压差模式）"""
        try:
            self._loading = True

            # 加载电池类型
            if 'battery_type' in config and 'battery_type_combo' in self.voltage_widgets:
                self.voltage_widgets['battery_type_combo'].setCurrentIndex(config['battery_type'])

            # 加载标准电压
            if 'standard_voltage' in config and 'standard_voltage_spin' in self.voltage_widgets:
                self.voltage_widgets['standard_voltage_spin'].setValue(config['standard_voltage'])

            # 加载最小电压
            if 'min_voltage' in config and 'min_voltage_spin' in self.voltage_widgets:
                self.voltage_widgets['min_voltage_spin'].setValue(config['min_voltage'])

            # 加载最大电压
            if 'max_voltage' in config and 'max_voltage_spin' in self.voltage_widgets:
                self.voltage_widgets['max_voltage_spin'].setValue(config['max_voltage'])

            # 加载自动计算范围选项
            if 'auto_calc_range' in config and 'auto_calc_checkbox' in self.voltage_widgets:
                self.voltage_widgets['auto_calc_checkbox'].setChecked(config['auto_calc_range'])

            # 简化只加载电压差配置项
            if 'voltage_diff' in config and 'voltage_diff_spin' in self.voltage_widgets:
                self.voltage_widgets['voltage_diff_spin'].setValue(config['voltage_diff'])

            # 修复只在自动计算模式下才更新电压范围，避免覆盖用户手动设置的值
            if config.get('auto_calc_range', True):
                self._update_voltage_range()

            logger.debug("电压配置加载完成")

        except Exception as e:
            logger.error(f"加载电压配置失败: {e}")
        finally:
            self._loading = False

    def set_loading(self, loading: bool):
        """设置加载状态"""
        self._loading = loading
    
    def _on_rs_auto_calc_changed(self, checked: bool):
        """处理Rs自动计算选项变化"""
        try:
            if self._loading:
                return

            # 控制手动阈值设置的可见性
            if 'manual_thresholds_group' in self.rs_widgets:
                self.rs_widgets['manual_thresholds_group'].setVisible(not checked)

            # 如果启用自动计算，立即更新范围显示
            if checked:
                self._update_rs_range_display()

            # 触发设置变更
            self._on_settings_changed()

        except Exception as e:
            logger.error(f"处理Rs自动计算选项变化失败: {e}")

    def _on_rct_auto_calc_changed(self, checked: bool):
        """处理Rct自动计算选项变化"""
        try:
            if self._loading:
                return

            # 控制手动阈值设置的可见性
            if 'manual_thresholds_group' in self.rct_widgets:
                self.rct_widgets['manual_thresholds_group'].setVisible(not checked)

            # 如果启用自动计算，立即更新范围显示
            if checked:
                self._update_rct_range_display()

            # 触发设置变更
            self._on_settings_changed()

        except Exception as e:
            logger.error(f"处理Rct自动计算选项变化失败: {e}")

    def _on_rs_range_changed(self):
        """处理Rs范围参数变化"""
        try:
            if self._loading:
                return

            # 如果启用自动计算，更新范围显示
            if ('auto_calc_checkbox' in self.rs_widgets and
                self.rs_widgets['auto_calc_checkbox'].isChecked()):
                self._update_rs_range_display()

            # 触发设置变更
            self._on_settings_changed()

        except Exception as e:
            logger.error(f"处理Rs范围参数变化失败: {e}")

    def _on_rct_range_changed(self):
        """处理Rct范围参数变化"""
        try:
            if self._loading:
                return

            # 如果启用自动计算，更新范围显示
            if ('auto_calc_checkbox' in self.rct_widgets and
                self.rct_widgets['auto_calc_checkbox'].isChecked()):
                self._update_rct_range_display()

            # 触发设置变更
            self._on_settings_changed()

        except Exception as e:
            logger.error(f"处理Rct范围参数变化失败: {e}")

    def _on_rs_manual_threshold_changed(self):
        """处理Rs手动阈值变化"""
        try:
            if self._loading:
                return

            # 如果禁用自动计算，更新范围显示
            if ('auto_calc_checkbox' in self.rs_widgets and
                not self.rs_widgets['auto_calc_checkbox'].isChecked()):
                self._update_rs_range_display()

            # 触发设置变更
            self._on_settings_changed()

        except Exception as e:
            logger.error(f"处理Rs手动阈值变化失败: {e}")

    def _on_rct_manual_threshold_changed(self):
        """处理Rct手动阈值变化"""
        try:
            if self._loading:
                return

            # 如果禁用自动计算，更新范围显示
            if ('auto_calc_checkbox' in self.rct_widgets and
                not self.rct_widgets['auto_calc_checkbox'].isChecked()):
                self._update_rct_range_display()

            # 触发设置变更
            self._on_settings_changed()

        except Exception as e:
            logger.error(f"处理Rct手动阈值变化失败: {e}")

    def _update_rs_range_display(self):
        """更新Rs档位范围显示"""
        try:
            if 'grade_display' not in self.rs_widgets:
                return

            auto_calc = self.rs_widgets.get('auto_calc_checkbox', None)
            if not auto_calc:
                return

            if auto_calc.isChecked():
                # 自动计算模式：根据最小值、最大值和档位数量计算
                grade_count = self.rs_widgets['grade_count_combo'].currentIndex() + 1
                min_value = self.rs_widgets['min_value_spin'].value()
                max_value = self.rs_widgets['max_value_spin'].value()

                ranges = self._calculate_auto_ranges(min_value, max_value, grade_count)
                display_text = self._format_ranges_text("Rs", ranges)
            else:
                # 手动模式：使用手动设置的阈值
                grade_count = self.rs_widgets['grade_count_combo'].currentIndex() + 1
                ranges = []

                if grade_count >= 1:
                    grade1_max = self.rs_widgets['grade1_max_spin'].value()
                    ranges.append((0.0, grade1_max))

                if grade_count >= 2:
                    grade2_max = self.rs_widgets['grade2_max_spin'].value()
                    ranges.append((grade1_max, grade2_max))

                if grade_count >= 3:
                    grade3_max = self.rs_widgets['grade3_max_spin'].value()
                    ranges.append((grade2_max, grade3_max))

                display_text = self._format_ranges_text("Rs", ranges)

            self.rs_widgets['grade_display'].setText(display_text)

        except Exception as e:
            logger.error(f"更新Rs档位范围显示失败: {e}")

    def _update_rct_range_display(self):
        """更新Rct档位范围显示"""
        try:
            if 'grade_display' not in self.rct_widgets:
                return

            auto_calc = self.rct_widgets.get('auto_calc_checkbox', None)
            if not auto_calc:
                return

            if auto_calc.isChecked():
                # 自动计算模式：根据最小值、最大值计算（固定3档）
                min_value = self.rct_widgets['min_value_spin'].value()
                max_value = self.rct_widgets['max_value_spin'].value()

                ranges = self._calculate_auto_ranges(min_value, max_value, 3)
                display_text = self._format_ranges_text("Rct", ranges)
            else:
                # 手动模式：使用手动设置的阈值（固定3档）
                grade1_max = self.rct_widgets['grade1_max_spin'].value()
                grade2_max = self.rct_widgets['grade2_max_spin'].value()
                grade3_max = self.rct_widgets['grade3_max_spin'].value()

                ranges = [
                    (0.0, grade1_max),
                    (grade1_max, grade2_max),
                    (grade2_max, grade3_max)
                ]
                display_text = self._format_ranges_text("Rct", ranges)

            self.rct_widgets['grade_display'].setText(display_text)

        except Exception as e:
            logger.error(f"更新Rct档位范围显示失败: {e}")

    def _calculate_auto_ranges(self, min_value: float, max_value: float, grade_count: int) -> list:
        """自动计算档位范围"""
        try:
            ranges = []
            if grade_count <= 0:
                return ranges

            step = (max_value - min_value) / grade_count

            for i in range(grade_count):
                range_min = min_value + i * step
                range_max = min_value + (i + 1) * step
                ranges.append((range_min, range_max))

            return ranges

        except Exception as e:
            logger.error(f"自动计算档位范围失败: {e}")
            return []

    def _format_ranges_text(self, prefix: str, ranges: list) -> str:
        """格式化档位范围文本"""
        try:
            if not ranges:
                return f"{prefix}档位范围计算失败"

            lines = []
            for i, (min_val, max_val) in enumerate(ranges, 1):
                lines.append(f"{prefix}{i}档: {min_val:.3f} - {max_val:.3f} mΩ")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"格式化档位范围文本失败: {e}")
            return f"{prefix}档位范围显示错误"

    def cleanup(self):
        """清理资源"""
        try:
            self.voltage_widgets.clear()
            self.rs_widgets.clear()
            self.rct_widgets.clear()

            logger.debug("档位设置UI管理器资源清理完成")

        except Exception as e:
            logger.error(f"档位设置UI管理器清理失败: {e}")
