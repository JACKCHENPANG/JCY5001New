# -*- coding: utf-8 -*-
"""
保存基准对话框
用于保存学习功能的中位值数据为离群检测基准

Author: Jack
Date: 2025-06-01
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton,
    QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SaveBaselineDialog(QDialog):
    """保存基准对话框"""

    def __init__(self, parent=None):
        """
        初始化保存基准对话框

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        
        self._init_ui()
        self._init_connections()
        
        logger.debug("保存基准对话框初始化完成")

    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("保存基准数据")
        self.setModal(True)
        self.setFixedSize(450, 350)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("保存学习结果为离群检测基准")
        title_label.setFont(QFont("", 12, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 基准信息组
        info_group = self._create_baseline_info_group()
        main_layout.addWidget(info_group)
        
        # 按钮区域
        button_layout = self._create_button_area()
        main_layout.addLayout(button_layout)

    def _create_baseline_info_group(self) -> QGroupBox:
        """创建基准信息组"""
        group = QGroupBox("基准信息")
        group.setFont(QFont("", 10, QFont.Bold))
        
        layout = QGridLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 基准名称
        layout.addWidget(QLabel("基准名称:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入基准名称（必填）")
        
        # 生成默认名称
        current_time = datetime.now()
        default_name = f"基准_{current_time.strftime('%Y%m%d_%H%M%S')}"
        self.name_edit.setText(default_name)
        
        layout.addWidget(self.name_edit, 0, 1)

        # 描述信息
        layout.addWidget(QLabel("描述信息:"), 1, 0, Qt.AlignTop)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("请输入基准描述信息（可选）")
        
        # 生成默认描述
        default_description = (
            f"基于学习功能生成的基准数据\n"
            f"创建时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"用途: 离群检测"
        )
        self.description_edit.setPlainText(default_description)
        
        layout.addWidget(self.description_edit, 1, 1)
        
        return group

    def _create_button_area(self) -> QHBoxLayout:
        """创建按钮区域"""
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        layout.addStretch()
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumWidth(80)
        layout.addWidget(self.cancel_btn)
        
        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setMinimumWidth(80)
        self.save_btn.setDefault(True)
        layout.addWidget(self.save_btn)
        
        return layout

    def _init_connections(self):
        """初始化信号连接"""
        try:
            self.cancel_btn.clicked.connect(self.reject)
            self.save_btn.clicked.connect(self._save_baseline)
            self.name_edit.textChanged.connect(self._validate_input)
            
        except Exception as e:
            logger.error(f"初始化信号连接失败: {e}")

    def _validate_input(self):
        """验证输入"""
        try:
            name = self.name_edit.text().strip()
            self.save_btn.setEnabled(len(name) > 0)
            
        except Exception as e:
            logger.error(f"验证输入失败: {e}")

    def _save_baseline(self):
        """保存基准"""
        try:
            # 验证输入
            name = self.name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "输入错误", "请输入基准名称")
                self.name_edit.setFocus()
                return
            
            # 检查名称长度
            if len(name) > 50:
                QMessageBox.warning(self, "输入错误", "基准名称不能超过50个字符")
                self.name_edit.setFocus()
                return
            
            # 检查名称是否包含特殊字符
            invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
            if any(char in name for char in invalid_chars):
                QMessageBox.warning(
                    self, "输入错误", 
                    f"基准名称不能包含以下字符: {' '.join(invalid_chars)}"
                )
                self.name_edit.setFocus()
                return
            
            # 获取描述信息
            description = self.description_edit.toPlainText().strip()
            if len(description) > 500:
                QMessageBox.warning(self, "输入错误", "描述信息不能超过500个字符")
                self.description_edit.setFocus()
                return
            
            # 确认保存
            reply = QMessageBox.question(
                self, "确认保存",
                f"确定要保存基准数据吗？\n\n"
                f"基准名称: {name}\n"
                f"通道模式: 平均模式\n"
                f"描述: {description[:50]}{'...' if len(description) > 50 else ''}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.accept()
            
        except Exception as e:
            logger.error(f"保存基准失败: {e}")
            QMessageBox.critical(self, "错误", f"保存基准失败: {e}")

    def get_baseline_info(self) -> Dict[str, Any]:
        """
        获取基准信息

        Returns:
            基准信息字典
        """
        try:
            return {
                'name': self.name_edit.text().strip(),
                'channel_mode': 'average_all',  # 统一使用平均模式
                'description': self.description_edit.toPlainText().strip()
            }

        except Exception as e:
            logger.error(f"获取基准信息失败: {e}")
            return {
                'name': '',
                'channel_mode': 'average_all',
                'description': ''
            }

    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
        
        # 设置焦点到名称输入框
        self.name_edit.setFocus()
        self.name_edit.selectAll()
        
        # 初始验证
        self._validate_input()

    def keyPressEvent(self, event):
        """按键事件"""
        # 处理回车键
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.save_btn.isEnabled():
                self._save_baseline()
            return
        
        # 处理ESC键
        if event.key() == Qt.Key_Escape:
            self.reject()
            return
        
        super().keyPressEvent(event)
