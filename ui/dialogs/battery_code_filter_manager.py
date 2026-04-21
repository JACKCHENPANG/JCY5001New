# -*- coding: utf-8 -*-
"""
电池码筛选管理器
负责管理电池码搜索功能

Author: Jack
Date: 2024-12-14
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QCheckBox, QGroupBox,
                            QComboBox)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class BatteryCodeFilterWidget(QWidget):
    """
    电池码筛选组件
    
    职责：
    - 提供电池码搜索界面
    - 管理搜索模式（精确/模糊）
    - 发送搜索条件变更信号
    """
    
    # 信号定义
    filter_changed = pyqtSignal(str, bool)  # 筛选条件变更信号：(搜索文本, 是否模糊搜索)
    
    def __init__(self, parent=None):
        """
        初始化电池码筛选组件
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        
        # 搜索延迟定时器
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._emit_filter_changed)
        
        # 初始化界面
        self._init_ui()
        self._init_connections()
        
        logger.debug("电池码筛选组件初始化完成")
    
    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 标题
        title_label = QLabel("电池码搜索")
        title_label.setFont(QFont("", 9, QFont.Bold))
        layout.addWidget(title_label)
        
        # 搜索模式选择
        mode_layout = QHBoxLayout()
        mode_label = QLabel("搜索模式:")
        self.search_mode_combo = QComboBox()
        self.search_mode_combo.addItem("精确匹配", False)
        self.search_mode_combo.addItem("模糊搜索", True)
        self.search_mode_combo.setCurrentIndex(1)  # 默认模糊搜索
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.search_mode_combo)
        layout.addLayout(mode_layout)
        
        # 搜索输入框
        search_layout = QVBoxLayout()
        search_label = QLabel("电池码:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入电池码进行搜索...")
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.clear_button = QPushButton("清空")
        self.search_button = QPushButton("搜索")
        
        self.clear_button.setMaximumHeight(25)
        self.search_button.setMaximumHeight(25)
        
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.search_button)
        layout.addLayout(button_layout)
        
        # 搜索提示
        self.hint_label = QLabel("提示：模糊搜索支持部分匹配")
        self.hint_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.hint_label)
    
    def _init_connections(self):
        """初始化信号连接"""
        # 搜索输入框变更
        self.search_input.textChanged.connect(self._on_search_text_changed)
        
        # 搜索模式变更
        self.search_mode_combo.currentIndexChanged.connect(self._on_search_mode_changed)
        
        # 按钮点击
        self.clear_button.clicked.connect(self._clear_search)
        self.search_button.clicked.connect(self._emit_filter_changed)
    
    def _on_search_text_changed(self):
        """搜索文本变更处理"""
        # 延迟搜索，避免频繁查询
        self.search_timer.stop()
        self.search_timer.start(500)  # 500ms延迟
    
    def _on_search_mode_changed(self):
        """搜索模式变更处理"""
        is_fuzzy = self.search_mode_combo.currentData()
        if is_fuzzy:
            self.hint_label.setText("提示：模糊搜索支持部分匹配")
        else:
            self.hint_label.setText("提示：精确匹配需要完全相同")
        
        # 如果有搜索内容，立即触发搜索
        if self.search_input.text().strip():
            self._emit_filter_changed()
    
    def _clear_search(self):
        """清空搜索"""
        self.search_input.clear()
        self._emit_filter_changed()
    
    def _emit_filter_changed(self):
        """发送筛选条件变更信号"""
        search_text = self.search_input.text().strip()
        is_fuzzy = self.search_mode_combo.currentData()
        
        self.filter_changed.emit(search_text, is_fuzzy)
        logger.debug(f"电池码筛选条件变更: '{search_text}', 模糊搜索: {is_fuzzy}")
    
    def get_filter_condition(self) -> Tuple[str, bool]:
        """
        获取当前筛选条件
        
        Returns:
            (搜索文本, 是否模糊搜索)
        """
        search_text = self.search_input.text().strip()
        is_fuzzy = self.search_mode_combo.currentData()
        return search_text, is_fuzzy
    
    def set_search_text(self, text: str):
        """
        设置搜索文本
        
        Args:
            text: 搜索文本
        """
        self.search_input.setText(text)
    
    def set_search_mode(self, is_fuzzy: bool):
        """
        设置搜索模式
        
        Args:
            is_fuzzy: 是否模糊搜索
        """
        index = 1 if is_fuzzy else 0
        self.search_mode_combo.setCurrentIndex(index)


class BatteryCodeFilterManager:
    """
    电池码筛选管理器
    
    职责：
    - 管理电池码筛选逻辑
    - 处理搜索条件转换
    - 提供筛选条件接口
    """
    
    def __init__(self):
        """初始化电池码筛选管理器"""
        self.search_text = ""
        self.is_fuzzy_search = True
        logger.debug("电池码筛选管理器初始化完成")
    
    def update_filter_condition(self, search_text: str, is_fuzzy: bool):
        """
        更新筛选条件
        
        Args:
            search_text: 搜索文本
            is_fuzzy: 是否模糊搜索
        """
        self.search_text = search_text.strip()
        self.is_fuzzy_search = is_fuzzy
        logger.debug(f"更新电池码筛选条件: '{self.search_text}', 模糊搜索: {self.is_fuzzy_search}")
    
    def get_filter_condition(self) -> Optional[Tuple[str, bool]]:
        """
        获取筛选条件
        
        Returns:
            筛选条件，None表示不筛选，否则返回(搜索文本, 是否模糊搜索)
        """
        if not self.search_text:
            return None
        return self.search_text, self.is_fuzzy_search
    
    def has_filter(self) -> bool:
        """
        检查是否有筛选条件
        
        Returns:
            是否有筛选条件
        """
        return bool(self.search_text)
    
    def clear_filter(self):
        """清空筛选条件"""
        self.search_text = ""
        logger.debug("清空电池码筛选条件")
    
    def matches_battery_code(self, battery_code: str) -> bool:
        """
        检查电池码是否匹配筛选条件
        
        Args:
            battery_code: 要检查的电池码
            
        Returns:
            是否匹配
        """
        if not self.search_text:
            return True
        
        if not battery_code:
            return False
        
        if self.is_fuzzy_search:
            # 模糊搜索：不区分大小写的部分匹配
            return self.search_text.lower() in battery_code.lower()
        else:
            # 精确匹配：区分大小写的完全匹配
            return self.search_text == battery_code
