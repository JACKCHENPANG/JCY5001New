#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
取样测试结果确认对话框
显示测试结果并允许用户选择是否使用数据

Author: Jack
Date: 2025-07-09
Version: V0.90.01
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QFrame,
    QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SamplingTestResultDialog(QDialog):
    """取样测试结果确认对话框"""
    
    # 信号定义
    data_confirmed = pyqtSignal(str, bool)  # (test_id, is_valid)
    
    def __init__(self, test_id: str, channel_data: Dict[int, Dict], 
                 statistics_data: Optional[Dict] = None, 
                 progress_info: Optional[tuple] = None, parent=None):
        """
        初始化取样测试结果确认对话框
        
        Args:
            test_id: 测试ID
            channel_data: 通道测试数据
            statistics_data: 统计数据
            progress_info: 进度信息 (当前数量, 有效数量, 目标数量)
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.test_id = test_id
        self.channel_data = channel_data
        self.statistics_data = statistics_data or {}
        self.progress_info = progress_info or (0, 0, 0)
        
        self._init_ui()
        self._init_connections()
        
        logger.debug(f"取样测试结果确认对话框初始化完成: {test_id}")
    
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("取样测试结果确认")
        self.setFixedSize(700, 600)
        self.setModal(True)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 标题和进度
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
        
        # 当前测试结果组
        current_result_group = self._create_current_result_group()
        content_layout.addWidget(current_result_group)
        
        # 统计数据组（如果有数据）
        if self.statistics_data:
            statistics_group = self._create_statistics_group()
            content_layout.addWidget(statistics_group)
        
        content_layout.addStretch()
        main_layout.addWidget(scroll_area)
        
        # 按钮布局
        button_layout = self._create_button_layout()
        main_layout.addLayout(button_layout)
    
    def _create_header_layout(self) -> QVBoxLayout:
        """创建标题和进度布局"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("取样测试结果")
        title_label.setFont(QFont("", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 5px;")
        layout.addWidget(title_label)
        
        # 进度信息
        current_count, valid_count, target_count = self.progress_info
        progress_label = QLabel(f"进度：{current_count}/{target_count} (有效样本：{valid_count})")
        progress_label.setAlignment(Qt.AlignCenter)
        progress_label.setStyleSheet("color: #7f8c8d; font-size: 10pt;")
        layout.addWidget(progress_label)
        
        return layout
    
    def _create_current_result_group(self) -> QGroupBox:
        """创建当前测试结果组"""
        group = QGroupBox("当前测试结果")
        group.setFont(QFont("", 10, QFont.Bold))
        
        layout = QGridLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # 表头
        headers = ["通道", "电压(V)", "Rs(mΩ)", "Rct(mΩ)"]
        for col, header in enumerate(headers):
            header_label = QLabel(header)
            header_label.setFont(QFont("", 9, QFont.Bold))
            header_label.setStyleSheet("color: #495057; background-color: #f8f9fa; padding: 5px; border: 1px solid #dee2e6;")
            header_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(header_label, 0, col)
        
        # 数据行
        row = 1
        for channel_num in sorted(self.channel_data.keys()):
            data = self.channel_data[channel_num]
            
            # 通道号
            channel_label = QLabel(f"CH{channel_num}")
            channel_label.setAlignment(Qt.AlignCenter)
            channel_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
            layout.addWidget(channel_label, row, 0)
            
            # 电压
            voltage = data.get('voltage', 0.0)
            voltage_label = QLabel(f"{voltage:.3f}")
            voltage_label.setAlignment(Qt.AlignCenter)
            voltage_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
            layout.addWidget(voltage_label, row, 1)
            
            # Rs值
            rs_value = data.get('rs_value', 0.0)
            rs_label = QLabel(f"{rs_value:.3f}")
            rs_label.setAlignment(Qt.AlignCenter)
            rs_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
            layout.addWidget(rs_label, row, 2)
            
            # Rct值
            rct_value = data.get('rct_value', 0.0)
            rct_label = QLabel(f"{rct_value:.3f}")
            rct_label.setAlignment(Qt.AlignCenter)
            rct_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
            layout.addWidget(rct_label, row, 3)
            
            row += 1
        
        return group
    
    def _create_statistics_group(self) -> QGroupBox:
        """创建统计数据组"""
        group = QGroupBox("统计范围（基于有效样本）")
        group.setFont(QFont("", 10, QFont.Bold))
        
        layout = QGridLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # 表头
        headers = ["参数", "最小值", "最大值", "平均值", "标准差", "样本数"]
        for col, header in enumerate(headers):
            header_label = QLabel(header)
            header_label.setFont(QFont("", 9, QFont.Bold))
            header_label.setStyleSheet("color: #495057; background-color: #e9ecef; padding: 5px; border: 1px solid #dee2e6;")
            header_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(header_label, 0, col)
        
        # 数据行
        row = 1
        parameter_names = {
            'voltage': '电压(V)',
            'rs_value': 'Rs(mΩ)',
            'rct_value': 'Rct(mΩ)'
        }
        
        for param_key, param_name in parameter_names.items():
            if param_key in self.statistics_data:
                stats = self.statistics_data[param_key]
                
                # 参数名
                param_label = QLabel(param_name)
                param_label.setAlignment(Qt.AlignCenter)
                param_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #f8f9fa;")
                layout.addWidget(param_label, row, 0)
                
                # 最小值
                min_label = QLabel(f"{stats.min_value:.3f}")
                min_label.setAlignment(Qt.AlignCenter)
                min_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
                layout.addWidget(min_label, row, 1)
                
                # 最大值
                max_label = QLabel(f"{stats.max_value:.3f}")
                max_label.setAlignment(Qt.AlignCenter)
                max_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
                layout.addWidget(max_label, row, 2)
                
                # 平均值
                mean_label = QLabel(f"{stats.mean_value:.3f}")
                mean_label.setAlignment(Qt.AlignCenter)
                mean_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
                layout.addWidget(mean_label, row, 3)
                
                # 标准差
                std_label = QLabel(f"{stats.std_dev:.3f}")
                std_label.setAlignment(Qt.AlignCenter)
                std_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
                layout.addWidget(std_label, row, 4)
                
                # 样本数
                count_label = QLabel(f"{stats.count}")
                count_label.setAlignment(Qt.AlignCenter)
                count_label.setStyleSheet("padding: 5px; border: 1px solid #dee2e6; background-color: #ffffff;")
                layout.addWidget(count_label, row, 5)
                
                row += 1
        
        return group
    
    def _create_button_layout(self) -> QHBoxLayout:
        """创建按钮布局"""
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # 添加弹性空间
        layout.addStretch()
        
        # 放弃数据按钮
        self.reject_btn = QPushButton("放弃数据")
        self.reject_btn.setFixedSize(100, 40)
        self.reject_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        layout.addWidget(self.reject_btn)
        
        # 使用数据按钮
        self.accept_btn = QPushButton("使用数据")
        self.accept_btn.setFixedSize(100, 40)
        self.accept_btn.setStyleSheet("""
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
        layout.addWidget(self.accept_btn)
        
        layout.addStretch()
        
        return layout
    
    def _init_connections(self):
        """初始化信号连接"""
        self.accept_btn.clicked.connect(self._on_accept_data)
        self.reject_btn.clicked.connect(self._on_reject_data)
    
    def _on_accept_data(self):
        """使用数据按钮点击处理"""
        self.data_confirmed.emit(self.test_id, True)
        self.accept()
        logger.info(f"✅ 用户选择使用取样数据: {self.test_id}")
    
    def _on_reject_data(self):
        """放弃数据按钮点击处理"""
        self.data_confirmed.emit(self.test_id, False)
        self.accept()
        logger.info(f"❌ 用户选择放弃取样数据: {self.test_id}")
