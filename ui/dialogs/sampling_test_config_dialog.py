#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
取样测试配置对话框
用于设置取样测试的参数

Author: Jack
Date: 2025-07-09
Version: V0.90.01
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSpinBox, QPushButton, QGroupBox,
    QTextEdit, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
import logging

logger = logging.getLogger(__name__)


class SamplingTestConfigDialog(QDialog):
    """取样测试配置对话框"""
    
    # 信号定义
    config_confirmed = pyqtSignal(dict)  # 配置确认信号
    
    def __init__(self, parent=None):
        """
        初始化取样测试配置对话框
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.sample_count = 30  # 默认取样数量
        
        self._init_ui()
        self._init_connections()
        
        logger.debug("取样测试配置对话框初始化完成")
    
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("取样测试配置")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("取样测试配置")
        title_label.setFont(QFont("", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # 配置参数组
        config_group = self._create_config_group()
        main_layout.addWidget(config_group)
        
        # 说明信息组
        info_group = self._create_info_group()
        main_layout.addWidget(info_group)
        
        # 按钮布局
        button_layout = self._create_button_layout()
        main_layout.addLayout(button_layout)
    
    def _create_config_group(self) -> QGroupBox:
        """创建配置参数组"""
        group = QGroupBox("参数设置")
        group.setFont(QFont("", 10, QFont.Bold))
        
        layout = QGridLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 取样数量设置
        layout.addWidget(QLabel("取样数量:"), 0, 0)
        self.sample_count_spin = QSpinBox()
        self.sample_count_spin.setRange(5, 200)
        self.sample_count_spin.setValue(30)
        self.sample_count_spin.setSuffix(" 个")
        self.sample_count_spin.setToolTip("设置需要收集的有效样本数量")
        layout.addWidget(self.sample_count_spin, 0, 1)
        
        # 取样数量说明
        count_desc = QLabel("建议取样数量：\n• 快速评估：10-20个\n• 标准评估：30-50个\n• 精确评估：50-100个")
        count_desc.setStyleSheet("color: #7f8c8d; font-size: 9pt; margin-top: 10px;")
        layout.addWidget(count_desc, 1, 0, 1, 2)
        
        return group
    
    def _create_info_group(self) -> QGroupBox:
        """创建说明信息组"""
        group = QGroupBox("功能说明")
        group.setFont(QFont("", 10, QFont.Bold))
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 功能说明文本
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(120)
        info_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 10px;
                font-size: 9pt;
                color: #495057;
            }
        """)
        
        info_content = """取样测试功能说明：

1. 测试流程：按手动模式进行测试，每次测试完成后显示结果确认对话框
2. 数据确认：用户可选择"使用数据"或"放弃数据"，只有确认使用的数据才计入有效样本
3. 实时统计：显示当前测试结果和所有有效数据的统计范围（最小值-最大值）
4. 自动建议：达到目标取样数量后，系统自动计算并建议判断参数范围
5. 参数应用：用户确认后可一键应用建议参数到系统判断设置中"""
        
        info_text.setPlainText(info_content)
        layout.addWidget(info_text)
        
        return group
    
    def _create_button_layout(self) -> QHBoxLayout:
        """创建按钮布局"""
        layout = QHBoxLayout()
        layout.setSpacing(15)
        
        # 添加弹性空间
        layout.addStretch()
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedSize(80, 35)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        layout.addWidget(self.cancel_btn)
        
        # 确认按钮
        self.confirm_btn = QPushButton("开始取样")
        self.confirm_btn.setFixedSize(100, 35)
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        layout.addWidget(self.confirm_btn)
        
        return layout
    
    def _init_connections(self):
        """初始化信号连接"""
        self.cancel_btn.clicked.connect(self.reject)
        self.confirm_btn.clicked.connect(self._on_confirm)
        self.sample_count_spin.valueChanged.connect(self._on_sample_count_changed)
    
    def _on_sample_count_changed(self, value: int):
        """取样数量变更处理"""
        self.sample_count = value
        
        # 更新按钮文本
        self.confirm_btn.setText(f"开始取样({value}个)")
    
    def _on_confirm(self):
        """确认按钮点击处理"""
        try:
            # 验证参数
            if self.sample_count < 5:
                QMessageBox.warning(self, "参数错误", "取样数量不能少于5个")
                return
            
            if self.sample_count > 200:
                QMessageBox.warning(self, "参数错误", "取样数量不能超过200个")
                return
            
            # 构建配置数据
            config_data = {
                'sample_count': self.sample_count,
                'mode': 'sampling_test'
            }
            
            # 发送配置确认信号
            self.config_confirmed.emit(config_data)
            
            # 关闭对话框
            self.accept()
            
            logger.info(f"✅ 取样测试配置确认：取样数量={self.sample_count}")
            
        except Exception as e:
            logger.error(f"❌ 确认取样测试配置失败: {e}")
            QMessageBox.critical(self, "错误", f"配置失败：{str(e)}")
    
    def get_config(self) -> dict:
        """
        获取配置数据
        
        Returns:
            配置数据字典
        """
        return {
            'sample_count': self.sample_count,
            'mode': 'sampling_test'
        }
    
    def set_config(self, config: dict):
        """
        设置配置数据
        
        Args:
            config: 配置数据字典
        """
        try:
            if 'sample_count' in config:
                sample_count = config['sample_count']
                if 5 <= sample_count <= 200:
                    self.sample_count_spin.setValue(sample_count)
                    self.sample_count = sample_count
            
            logger.debug(f"取样测试配置已设置：{config}")
            
        except Exception as e:
            logger.error(f"❌ 设置取样测试配置失败: {e}")
    
    @staticmethod
    def get_sampling_config(parent=None) -> tuple:
        """
        静态方法：获取取样测试配置
        
        Args:
            parent: 父窗口
            
        Returns:
            (是否确认, 配置数据)
        """
        dialog = SamplingTestConfigDialog(parent)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            return True, dialog.get_config()
        else:
            return False, {}
