#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数建议对话框
显示基于取样数据计算的建议参数范围，并允许用户应用到系统设置

Author: Jack
Date: 2025-07-09
Version: V0.90.01
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QFrame,
    QDoubleSpinBox, QScrollArea, QWidget, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ParameterSuggestionDialog(QDialog):
    """参数建议对话框"""
    
    # 信号定义
    parameters_applied = pyqtSignal(dict)  # 参数应用信号
    
    def __init__(self, suggestions: Dict[str, Dict], 
                 statistics_data: Optional[Dict] = None, 
                 sample_count: int = 0, parent=None):
        """
        初始化参数建议对话框
        
        Args:
            suggestions: 建议参数字典
            statistics_data: 统计数据
            sample_count: 样本数量
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.suggestions = suggestions
        self.statistics_data = statistics_data or {}
        self.sample_count = sample_count
        
        # 存储用户调整后的参数
        self.adjusted_parameters = {}
        
        self._init_ui()
        self._init_connections()
        self._load_suggestions()
        
        logger.debug(f"参数建议对话框初始化完成，样本数量: {sample_count}")
    
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("判断参数建议")
        # 进一步增加对话框尺寸，提升字体显示效果
        self.setFixedSize(1400, 900)
        self.setModal(True)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 标题和说明
        header_layout = self._create_header_layout()
        main_layout.addLayout(header_layout)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        # 内容容器
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        # 参数建议组
        self.suggestion_group = self._create_suggestion_group()
        content_layout.addWidget(self.suggestion_group)
        
        # 统计信息组
        if self.statistics_data:
            statistics_group = self._create_statistics_group()
            content_layout.addWidget(statistics_group)
        
        content_layout.addStretch()
        main_layout.addWidget(scroll_area)
        
        # 按钮布局
        button_layout = self._create_button_layout()
        main_layout.addLayout(button_layout)
    
    def _create_header_layout(self) -> QVBoxLayout:
        """创建标题和说明布局"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("判断参数建议")
        title_label.setFont(QFont("", 18, QFont.Bold))  # 增大标题字体
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 8px;")
        layout.addWidget(title_label)

        # 说明
        desc_label = QLabel(f"基于 {self.sample_count} 个有效样本的统计分析，系统建议以下判断参数范围：")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #7f8c8d; font-size: 12pt; margin-bottom: 15px;")  # 增大说明字体
        layout.addWidget(desc_label)
        
        # 提示
        tip_label = QLabel("💡 您可以根据实际需求调整参数范围，然后点击\"应用参数\"更新系统设置")
        tip_label.setAlignment(Qt.AlignCenter)
        tip_label.setStyleSheet("color: #e67e22; font-size: 9pt; font-weight: bold;")
        layout.addWidget(tip_label)
        
        return layout
    
    def _create_suggestion_group(self) -> QGroupBox:
        """创建参数建议组"""
        group = QGroupBox("建议参数范围")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QGridLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 表头
        # 修改表头，为电压参数使用不同的编辑方式
        headers = ["参数", "建议值/范围", "范围说明", "平均值", "标准差", "参数调整", "快速调整"]
        for col, header in enumerate(headers):
            header_label = QLabel(header)
            header_label.setFont(QFont("", 11, QFont.Bold))  # 增大表头字体
            header_label.setStyleSheet("color: #495057; background-color: #e9ecef; padding: 10px; border: 1px solid #dee2e6;")  # 增加内边距
            header_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(header_label, 0, col)

        # 存储调整控件的引用
        self.adjustment_widgets = {}

        return group
    
    def _create_statistics_group(self) -> QGroupBox:
        """创建统计信息组"""
        group = QGroupBox("样本统计信息")
        group.setFont(QFont("", 10, QFont.Bold))
        
        layout = QGridLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # 表头
        headers = ["参数", "样本数", "最小值", "最大值", "平均值", "标准差", "变异系数"]
        for col, header in enumerate(headers):
            header_label = QLabel(header)
            header_label.setFont(QFont("", 9, QFont.Bold))
            header_label.setStyleSheet("color: #495057; background-color: #f8f9fa; padding: 5px; border: 1px solid #dee2e6;")
            header_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(header_label, 0, col)
        
        # 数据行
        row = 1
        parameter_names = {
            'voltage': '电压(V)',
            'rs_value': 'Rs(mΩ)',
            'rct_value': 'Rct(mΩ)',
            'rsei_value': 'Rsei(mΩ)'
        }
        
        for param_key, param_name in parameter_names.items():
            if param_key in self.statistics_data:
                stats = self.statistics_data[param_key]
                
                # 计算变异系数
                cv = (stats.std_dev / stats.mean_value * 100) if stats.mean_value != 0 else 0
                
                # 参数名
                param_label = QLabel(param_name)
                param_label.setAlignment(Qt.AlignCenter)
                param_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #f8f9fa;")
                layout.addWidget(param_label, row, 0)
                
                # 样本数
                count_label = QLabel(f"{stats.count}")
                count_label.setAlignment(Qt.AlignCenter)
                count_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
                layout.addWidget(count_label, row, 1)
                
                # 最小值
                min_label = QLabel(f"{stats.min_value:.3f}")
                min_label.setAlignment(Qt.AlignCenter)
                min_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
                layout.addWidget(min_label, row, 2)
                
                # 最大值
                max_label = QLabel(f"{stats.max_value:.3f}")
                max_label.setAlignment(Qt.AlignCenter)
                max_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
                layout.addWidget(max_label, row, 3)
                
                # 平均值
                mean_label = QLabel(f"{stats.mean_value:.3f}")
                mean_label.setAlignment(Qt.AlignCenter)
                mean_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
                layout.addWidget(mean_label, row, 4)
                
                # 标准差
                std_label = QLabel(f"{stats.std_dev:.3f}")
                std_label.setAlignment(Qt.AlignCenter)
                std_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
                layout.addWidget(std_label, row, 5)
                
                # 变异系数
                cv_label = QLabel(f"{cv:.1f}%")
                cv_label.setAlignment(Qt.AlignCenter)
                cv_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
                layout.addWidget(cv_label, row, 6)
                
                row += 1
        
        return group
    
    def _create_button_layout(self) -> QHBoxLayout:
        """创建按钮布局"""
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # 添加弹性空间
        layout.addStretch()
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedSize(100, 40)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        layout.addWidget(self.cancel_btn)
        
        # 应用参数按钮
        self.apply_btn = QPushButton("应用参数")
        self.apply_btn.setFixedSize(120, 40)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        layout.addWidget(self.apply_btn)
        
        layout.addStretch()
        
        return layout
    
    def _init_connections(self):
        """初始化信号连接"""
        self.cancel_btn.clicked.connect(self.reject)
        self.apply_btn.clicked.connect(self._on_apply_parameters)
    
    def _load_suggestions(self):
        """加载建议参数到界面"""
        try:
            # 修复直接使用保存的组件引用
            if not hasattr(self, 'suggestion_group') or not self.suggestion_group:
                logger.error("❌ 建议参数范围组件未初始化")
                return

            layout = self.suggestion_group.layout()
            if not layout:
                logger.error("❌ 建议参数范围组件没有布局")
                return
            
            # 参数名称映射
            parameter_names = {
                'rs': 'Rs(mΩ)',
                'rct': 'Rct(mΩ)',
                'voltage': '电压(V)'
            }
            
            row = 1
            for param_key, param_name in parameter_names.items():
                if param_key in self.suggestions:
                    suggestion = self.suggestions[param_key]
                    
                    # 参数名
                    param_label = QLabel(param_name)
                    param_label.setFont(QFont("", 10, QFont.Bold))  # 增大参数名字体
                    param_label.setAlignment(Qt.AlignCenter)
                    param_label.setStyleSheet("padding: 10px; border: 1px solid #dee2e6; background-color: #f8f9fa;")  # 增加内边距
                    layout.addWidget(param_label, row, 0)
                    
                    # 电压参数使用平均值±偏差值格式，其他参数保持范围格式
                    if param_key == 'voltage':
                        # 电压参数：计算偏差值（范围的一半）
                        deviation = (suggestion['max_range'] - suggestion['min_range']) / 2

                        # 建议值显示为平均值±偏差值格式
                        suggest_label = QLabel(f"{suggestion['mean']:.3f} ± {deviation:.3f}")
                        suggest_label.setFont(QFont("", 10, QFont.Bold))  # 增大建议值字体
                        suggest_label.setAlignment(Qt.AlignCenter)
                        suggest_label.setStyleSheet("padding: 10px; border: 1px solid #dee2e6; background-color: #e8f5e8; font-weight: bold;")
                        layout.addWidget(suggest_label, row, 1)

                        # 范围说明显示计算出的范围
                        range_desc_label = QLabel(f"范围: {suggestion['min_range']:.3f} - {suggestion['max_range']:.3f}")
                        range_desc_label.setFont(QFont("", 9))  # 增大范围说明字体
                        range_desc_label.setAlignment(Qt.AlignCenter)
                        range_desc_label.setStyleSheet("padding: 10px; border: 1px solid #dee2e6; background-color: #f8f9fa; color: #666;")
                        layout.addWidget(range_desc_label, row, 2)
                    else:
                        # 其他参数：保持原有的最小值-最大值格式
                        min_suggest_label = QLabel(f"{suggestion['min_range']:.3f}")
                        min_suggest_label.setFont(QFont("", 10, QFont.Bold))  # 增大字体
                        min_suggest_label.setAlignment(Qt.AlignCenter)
                        min_suggest_label.setStyleSheet("padding: 10px; border: 1px solid #dee2e6; background-color: #e8f5e8;")
                        layout.addWidget(min_suggest_label, row, 1)

                        # 建议最大值
                        max_suggest_label = QLabel(f"{suggestion['max_range']:.3f}")
                        max_suggest_label.setFont(QFont("", 10, QFont.Bold))  # 增大字体
                        max_suggest_label.setAlignment(Qt.AlignCenter)
                        max_suggest_label.setStyleSheet("padding: 10px; border: 1px solid #dee2e6; background-color: #e8f5e8;")
                        layout.addWidget(max_suggest_label, row, 2)
                    
                    # 平均值
                    mean_label = QLabel(f"{suggestion['mean']:.3f}")
                    mean_label.setFont(QFont("", 10))  # 增大字体
                    mean_label.setAlignment(Qt.AlignCenter)
                    mean_label.setStyleSheet("padding: 10px; border: 1px solid #dee2e6; background-color: #ffffff;")
                    layout.addWidget(mean_label, row, 3)

                    # 标准差
                    std_label = QLabel(f"{suggestion['std_dev']:.3f}")
                    std_label.setFont(QFont("", 10))  # 增大字体
                    std_label.setAlignment(Qt.AlignCenter)
                    std_label.setStyleSheet("padding: 10px; border: 1px solid #dee2e6; background-color: #ffffff;")
                    layout.addWidget(std_label, row, 4)
                    
                    # 电压参数使用平均值和偏差值输入框，其他参数使用最小值/最大值输入框
                    if param_key == 'voltage':
                        # 电压参数：创建平均值和偏差值输入框的容器
                        voltage_adjust_widget = QWidget()
                        voltage_adjust_layout = QVBoxLayout(voltage_adjust_widget)
                        voltage_adjust_layout.setContentsMargins(5, 5, 5, 5)
                        voltage_adjust_layout.setSpacing(5)

                        # 平均值输入框
                        mean_layout = QHBoxLayout()
                        mean_label = QLabel("平均值:")
                        mean_label.setFont(QFont("", 9))  # 设置标签字体
                        mean_layout.addWidget(mean_label)
                        mean_adjust_spin = QDoubleSpinBox()
                        mean_adjust_spin.setRange(1.000, 10.000)
                        mean_adjust_spin.setDecimals(3)
                        mean_adjust_spin.setValue(suggestion['mean'])
                        mean_adjust_spin.setSuffix(" V")
                        mean_adjust_spin.setFont(QFont("", 9))  # 设置输入框字体
                        mean_adjust_spin.setStyleSheet("padding: 5px; border: 1px solid #007bff;")  # 增加内边距
                        mean_adjust_spin.setToolTip("设置电压的平均值")
                        mean_layout.addWidget(mean_adjust_spin)
                        voltage_adjust_layout.addLayout(mean_layout)

                        # 偏差值输入框
                        deviation_layout = QHBoxLayout()
                        deviation_label = QLabel("偏差值:")
                        deviation_label.setFont(QFont("", 9))  # 设置标签字体
                        deviation_layout.addWidget(deviation_label)
                        deviation_adjust_spin = QDoubleSpinBox()
                        deviation_adjust_spin.setRange(0.001, 2.000)
                        deviation_adjust_spin.setDecimals(3)
                        deviation_adjust_spin.setValue((suggestion['max_range'] - suggestion['min_range']) / 2)
                        deviation_adjust_spin.setSuffix(" V")
                        deviation_adjust_spin.setFont(QFont("", 9))  # 设置输入框字体
                        deviation_adjust_spin.setStyleSheet("padding: 5px; border: 1px solid #007bff;")  # 增加内边距
                        deviation_adjust_spin.setToolTip("设置电压的允许偏差值")
                        deviation_layout.addWidget(deviation_adjust_spin)
                        voltage_adjust_layout.addLayout(deviation_layout)

                        layout.addWidget(voltage_adjust_widget, row, 5)

                        # 存储电压参数的特殊控件引用
                        self.adjustment_widgets[param_key] = {
                            'mean': mean_adjust_spin,
                            'deviation': deviation_adjust_spin,
                            'suggestion': suggestion  # 保存原始建议值
                        }
                    else:
                        # 其他参数：使用最小值/最大值输入框的容器
                        other_adjust_widget = QWidget()
                        other_adjust_layout = QVBoxLayout(other_adjust_widget)
                        other_adjust_layout.setContentsMargins(5, 5, 5, 5)
                        other_adjust_layout.setSpacing(5)

                        # 最小值输入框
                        min_layout = QHBoxLayout()
                        min_label = QLabel("最小值:")
                        min_label.setFont(QFont("", 9))  # 设置标签字体
                        min_layout.addWidget(min_label)
                        min_adjust_spin = QDoubleSpinBox()
                        min_adjust_spin.setRange(0.0, 9999.999)
                        min_adjust_spin.setDecimals(3)
                        min_adjust_spin.setValue(suggestion['min_range'])
                        min_adjust_spin.setFont(QFont("", 9))  # 设置输入框字体
                        min_adjust_spin.setStyleSheet("padding: 5px; border: 1px solid #007bff;")  # 增加内边距
                        min_layout.addWidget(min_adjust_spin)
                        other_adjust_layout.addLayout(min_layout)

                        # 最大值输入框
                        max_layout = QHBoxLayout()
                        max_label = QLabel("最大值:")
                        max_label.setFont(QFont("", 9))  # 设置标签字体
                        max_layout.addWidget(max_label)
                        max_adjust_spin = QDoubleSpinBox()
                        max_adjust_spin.setRange(0.0, 9999.999)
                        max_adjust_spin.setDecimals(3)
                        max_adjust_spin.setValue(suggestion['max_range'])
                        max_adjust_spin.setFont(QFont("", 9))  # 设置输入框字体
                        max_adjust_spin.setStyleSheet("padding: 5px; border: 1px solid #007bff;")  # 增加内边距
                        max_layout.addWidget(max_adjust_spin)
                        other_adjust_layout.addLayout(max_layout)

                        layout.addWidget(other_adjust_widget, row, 5)

                        # 存储其他参数的控件引用
                        self.adjustment_widgets[param_key] = {
                            'min': min_adjust_spin,
                            'max': max_adjust_spin,
                            'suggestion': suggestion  # 保存原始建议值
                        }

                    # 快速调整按钮组
                    quick_adjust_layout = QVBoxLayout()
                    quick_adjust_layout.setSpacing(3)

                    # 第一行：重置和大幅调整
                    row1_layout = QHBoxLayout()
                    row1_layout.setSpacing(3)

                    # 重置按钮
                    reset_btn = QPushButton("重置")
                    reset_btn.setFixedSize(40, 26)  # 增大按钮尺寸
                    reset_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #6c757d;
                            color: white;
                            border: none;
                            border-radius: 3px;
                            font-size: 8pt;
                        }
                        QPushButton:hover {
                            background-color: #5a6268;
                        }
                    """)
                    reset_btn.clicked.connect(lambda checked, pk=param_key: self._reset_parameter(pk))
                    row1_layout.addWidget(reset_btn)

                    # 放宽按钮（增加10%范围）
                    widen_btn = QPushButton("放宽")
                    widen_btn.setFixedSize(40, 26)  # 增大按钮尺寸
                    widen_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #ffc107;
                            color: black;
                            border: none;
                            border-radius: 3px;
                            font-size: 8pt;
                        }
                        QPushButton:hover {
                            background-color: #e0a800;
                        }
                    """)
                    widen_btn.clicked.connect(lambda checked, pk=param_key: self._widen_parameter(pk))
                    row1_layout.addWidget(widen_btn)

                    # 收紧按钮（减少10%范围）
                    tighten_btn = QPushButton("收紧")
                    tighten_btn.setFixedSize(40, 26)  # 增大按钮尺寸
                    tighten_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #dc3545;
                            color: white;
                            border: none;
                            border-radius: 3px;
                            font-size: 8pt;
                        }
                        QPushButton:hover {
                            background-color: #c82333;
                        }
                    """)
                    tighten_btn.clicked.connect(lambda checked, pk=param_key: self._tighten_parameter(pk))
                    row1_layout.addWidget(tighten_btn)

                    quick_adjust_layout.addLayout(row1_layout)

                    # 第二行：精细调整
                    row2_layout = QHBoxLayout()
                    row2_layout.setSpacing(3)

                    # 微调放宽按钮（增加2%范围）
                    fine_widen_btn = QPushButton("+2%")
                    fine_widen_btn.setFixedSize(40, 26)  # 增大按钮尺寸
                    fine_widen_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #28a745;
                            color: white;
                            border: none;
                            border-radius: 3px;
                            font-size: 8pt;
                        }
                        QPushButton:hover {
                            background-color: #218838;
                        }
                    """)
                    fine_widen_btn.clicked.connect(lambda checked, pk=param_key: self._fine_widen_parameter(pk))
                    row2_layout.addWidget(fine_widen_btn)

                    # 微调收紧按钮（减少2%范围）
                    fine_tighten_btn = QPushButton("-2%")
                    fine_tighten_btn.setFixedSize(40, 26)  # 增大按钮尺寸
                    fine_tighten_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #17a2b8;
                            color: white;
                            border: none;
                            border-radius: 3px;
                            font-size: 8pt;
                        }
                        QPushButton:hover {
                            background-color: #138496;
                        }
                    """)
                    fine_tighten_btn.clicked.connect(lambda checked, pk=param_key: self._fine_tighten_parameter(pk))
                    row2_layout.addWidget(fine_tighten_btn)

                    # 占位符保持对齐
                    spacer = QWidget()
                    spacer.setFixedSize(35, 22)
                    row2_layout.addWidget(spacer)

                    quick_adjust_layout.addLayout(row2_layout)

                    quick_adjust_widget = QWidget()
                    quick_adjust_widget.setLayout(quick_adjust_layout)
                    layout.addWidget(quick_adjust_widget, row, 6)  # 调整列位置

                    row += 1
            
            logger.debug(f"参数建议加载完成，参数数量: {len(self.adjustment_widgets)}")
            
        except Exception as e:
            logger.error(f"❌ 加载参数建议失败: {e}")
    
    def _on_apply_parameters(self):
        """应用参数按钮点击处理"""
        try:
            # 收集用户调整后的参数
            adjusted_params = {}

            for param_key, widgets in self.adjustment_widgets.items():
                if param_key == 'voltage':
                    # 电压参数：从平均值和偏差值计算最小值和最大值
                    mean_value = widgets['mean'].value()
                    deviation_value = widgets['deviation'].value()

                    min_value = mean_value - deviation_value
                    max_value = mean_value + deviation_value

                    # 确保范围合理
                    min_value = max(0.1, min_value)  # 最小不低于0.1V
                    max_value = min(50.0, max_value)  # 最大不超过50V

                    # 验证参数范围
                    if min_value >= max_value:
                        QMessageBox.warning(self, "参数错误",
                                          f"电压参数的平均值和偏差值设置不合理，请检查设置")
                        return

                    adjusted_params[param_key] = {
                        'min_range': min_value,
                        'max_range': max_value
                    }
                else:
                    # 其他参数：直接使用最小值和最大值
                    min_value = widgets['min'].value()
                    max_value = widgets['max'].value()

                    # 验证参数范围
                    if min_value >= max_value:
                        QMessageBox.warning(self, "参数错误",
                                          f"{param_key}参数的最小值必须小于最大值")
                        return

                    adjusted_params[param_key] = {
                        'min_range': min_value,
                        'max_range': max_value
                    }
            
            # 构建详细的确认信息
            confirm_text = "确定要将这些参数应用到系统判断设置中吗？\n\n"
            confirm_text += "将要应用的参数：\n"

            for param_key, param_data in adjusted_params.items():
                param_names = {
                    'rs': 'Rs(溶液电阻)',
                    'rct': 'Rct(电荷转移电阻)',
                    'voltage': '电压',
                    'rsei': 'Rsei(SEI膜电阻)'
                }
                param_name = param_names.get(param_key, param_key)

                # 电压参数使用平均值±偏差值格式显示
                if param_key == 'voltage':
                    mean_value = (param_data['min_range'] + param_data['max_range']) / 2
                    deviation = (param_data['max_range'] - param_data['min_range']) / 2
                    confirm_text += f"• {param_name}: {mean_value:.3f}V ± {deviation:.3f}V (范围: {param_data['min_range']:.3f} - {param_data['max_range']:.3f})\n"
                else:
                    confirm_text += f"• {param_name}: {param_data['min_range']:.3f} - {param_data['max_range']:.3f}\n"

            confirm_text += "\n⚠️ 这将覆盖当前的判断参数设置。"

            # 确认应用
            reply = QMessageBox.question(self, "确认应用参数", confirm_text,
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # 发送参数应用信号
                self.parameters_applied.emit(adjusted_params)
                
                # 关闭对话框
                self.accept()
                
                logger.info(f"✅ 用户确认应用参数建议: {adjusted_params}")
            
        except Exception as e:
            logger.error(f"❌ 应用参数建议失败: {e}")
            QMessageBox.critical(self, "应用失败", f"应用参数建议失败：{str(e)}")
    
    def get_adjusted_parameters(self) -> dict:
        """
        获取用户调整后的参数

        Returns:
            调整后的参数字典
        """
        adjusted_params = {}

        for param_key, widgets in self.adjustment_widgets.items():
            if param_key == 'voltage':
                # 电压参数：从平均值和偏差值计算最小值和最大值
                mean_value = widgets['mean'].value()
                deviation_value = widgets['deviation'].value()

                min_value = mean_value - deviation_value
                max_value = mean_value + deviation_value

                # 确保范围合理
                min_value = max(0.1, min_value)  # 最小不低于0.1V
                max_value = min(50.0, max_value)  # 最大不超过50V

                adjusted_params[param_key] = {
                    'min_range': min_value,
                    'max_range': max_value
                }
            else:
                # 其他参数：直接使用最小值和最大值
                adjusted_params[param_key] = {
                    'min_range': widgets['min'].value(),
                    'max_range': widgets['max'].value()
                }

        return adjusted_params

    def _reset_parameter(self, param_key: str):
        """重置参数到建议值"""
        try:
            if param_key in self.adjustment_widgets:
                widgets = self.adjustment_widgets[param_key]
                suggestion = widgets['suggestion']

                if param_key == 'voltage':
                    # 电压参数：重置平均值和偏差值
                    widgets['mean'].setValue(suggestion['mean'])
                    deviation = (suggestion['max_range'] - suggestion['min_range']) / 2
                    widgets['deviation'].setValue(deviation)
                else:
                    # 其他参数：重置最小值和最大值
                    widgets['min'].setValue(suggestion['min_range'])
                    widgets['max'].setValue(suggestion['max_range'])

                logger.debug(f"参数{param_key}已重置到建议值")

        except Exception as e:
            logger.error(f"重置参数{param_key}失败: {e}")

    def _widen_parameter(self, param_key: str):
        """放宽参数范围（增加10%）"""
        try:
            if param_key in self.adjustment_widgets:
                widgets = self.adjustment_widgets[param_key]

                if param_key == 'voltage':
                    # 电压参数：增加偏差值
                    current_deviation = widgets['deviation'].value()
                    new_deviation = current_deviation * 1.1  # 增加10%
                    widgets['deviation'].setValue(min(2.0, new_deviation))  # 限制最大偏差值

                    logger.debug(f"电压参数偏差值已放宽: {current_deviation:.3f} -> {new_deviation:.3f}")
                else:
                    # 其他参数：按原有逻辑放宽范围
                    current_min = widgets['min'].value()
                    current_max = widgets['max'].value()
                    range_size = current_max - current_min

                    # 增加10%的范围
                    new_min = max(0, current_min - range_size * 0.05)
                    new_max = current_max + range_size * 0.05

                    widgets['min'].setValue(new_min)
                    widgets['max'].setValue(new_max)

                    logger.debug(f"参数{param_key}范围已放宽: {new_min:.3f} - {new_max:.3f}")

        except Exception as e:
            logger.error(f"放宽参数{param_key}失败: {e}")

    def _tighten_parameter(self, param_key: str):
        """收紧参数范围（减少10%）"""
        try:
            if param_key in self.adjustment_widgets:
                widgets = self.adjustment_widgets[param_key]

                if param_key == 'voltage':
                    # 电压参数：减少偏差值
                    current_deviation = widgets['deviation'].value()
                    new_deviation = current_deviation * 0.9  # 减少10%

                    # 确保偏差值不会过小
                    if new_deviation >= 0.01:  # 最小偏差值保护
                        widgets['deviation'].setValue(new_deviation)
                        logger.debug(f"电压参数偏差值已收紧: {current_deviation:.3f} -> {new_deviation:.3f}")
                    else:
                        QMessageBox.warning(self, "范围调整", f"电压参数偏差值已经很小，无法进一步收紧")
                else:
                    # 其他参数：按原有逻辑收紧范围
                    current_min = widgets['min'].value()
                    current_max = widgets['max'].value()
                    range_size = current_max - current_min

                    # 减少10%的范围，但确保最小值不超过最大值
                    new_min = current_min + range_size * 0.05
                    new_max = current_max - range_size * 0.05

                    # 确保范围有效
                    if new_min < new_max:
                        widgets['min'].setValue(new_min)
                        widgets['max'].setValue(new_max)
                        logger.debug(f"参数{param_key}范围已收紧: {new_min:.3f} - {new_max:.3f}")
                    else:
                        QMessageBox.warning(self, "范围调整", f"{param_key}参数范围已经很紧，无法进一步收紧")

        except Exception as e:
            logger.error(f"收紧参数{param_key}失败: {e}")

    def _fine_widen_parameter(self, param_key: str):
        """精细放宽参数范围（增加2%）"""
        try:
            if param_key in self.adjustment_widgets:
                widgets = self.adjustment_widgets[param_key]

                if param_key == 'voltage':
                    # 电压参数：增加偏差值
                    current_deviation = widgets['deviation'].value()
                    new_deviation = current_deviation * 1.02  # 增加2%
                    widgets['deviation'].setValue(min(2.0, new_deviation))  # 限制最大偏差值

                    logger.debug(f"电压参数偏差值已精细放宽: {current_deviation:.3f} -> {new_deviation:.3f}")
                else:
                    # 其他参数：按原有逻辑精细放宽范围
                    current_min = widgets['min'].value()
                    current_max = widgets['max'].value()
                    range_size = current_max - current_min

                    # 增加2%的范围
                    new_min = max(0, current_min - range_size * 0.01)
                    new_max = current_max + range_size * 0.01

                    widgets['min'].setValue(new_min)
                    widgets['max'].setValue(new_max)

                    logger.debug(f"参数{param_key}范围已精细放宽: {new_min:.3f} - {new_max:.3f}")

        except Exception as e:
            logger.error(f"精细放宽参数{param_key}失败: {e}")

    def _fine_tighten_parameter(self, param_key: str):
        """精细收紧参数范围（减少2%）"""
        try:
            if param_key in self.adjustment_widgets:
                widgets = self.adjustment_widgets[param_key]

                if param_key == 'voltage':
                    # 电压参数：减少偏差值
                    current_deviation = widgets['deviation'].value()
                    new_deviation = current_deviation * 0.98  # 减少2%

                    # 确保偏差值不会过小
                    if new_deviation >= 0.01:  # 最小偏差值保护
                        widgets['deviation'].setValue(new_deviation)
                        logger.debug(f"电压参数偏差值已精细收紧: {current_deviation:.3f} -> {new_deviation:.3f}")
                    else:
                        logger.warning(f"电压参数偏差值已经很小，无法进一步收紧")
                else:
                    # 其他参数：按原有逻辑精细收紧范围
                    current_min = widgets['min'].value()
                    current_max = widgets['max'].value()
                    range_size = current_max - current_min

                    # 减少2%的范围，但确保最小值不超过最大值
                    new_min = current_min + range_size * 0.01
                    new_max = current_max - range_size * 0.01

                    # 确保范围有效
                    if new_min < new_max:
                        widgets['min'].setValue(new_min)
                        widgets['max'].setValue(new_max)
                        logger.debug(f"参数{param_key}范围已精细收紧: {new_min:.3f} - {new_max:.3f}")
                    else:
                        QMessageBox.warning(self, "范围调整", f"{param_key}参数范围已经很紧，无法进一步收紧")

        except Exception as e:
            logger.error(f"精细收紧参数{param_key}失败: {e}")
