#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元素属性管理器
负责标签元素属性的编辑和管理

Author: Jack
Date: 2025-06-04
"""

import logging
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QGroupBox, QFormLayout, QLineEdit, QComboBox, QSpinBox,
    QPushButton, QCheckBox, QColorDialog, QFontComboBox,
    QHBoxLayout, QVBoxLayout, QLabel, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QColor

# 导入标签相关类
from .label_template_config import LabelElement, ElementType
from .dynamic_parameter_selector import DynamicParameterSelector, EnhancedTextEdit

logger = logging.getLogger(__name__)


class ElementPropertyWidget(QGroupBox):
    """元素属性编辑组件"""
    
    # 信号定义
    element_updated = pyqtSignal(str, dict)  # 元素更新信号 (element_id, properties)
    
    def __init__(self, parent=None):
        """初始化属性编辑组件"""
        super().__init__("元素属性", parent)
        
        self.current_element: Optional[LabelElement] = None
        
        # 初始化界面
        self._init_ui()
        
        # 连接信号
        self._connect_signals()
    
    def _init_ui(self):
        """初始化用户界面"""
        layout = QFormLayout(self)
        layout.setContentsMargins(10, 15, 10, 10)
        layout.setSpacing(8)
        
        # 基本属性
        self.element_id_edit = QLineEdit()
        self.element_id_edit.setReadOnly(True)
        layout.addRow("元素ID:", self.element_id_edit)
        
        self.element_type_combo = QComboBox()
        self.element_type_combo.addItems(ElementType.get_all_types())
        layout.addRow("元素类型:", self.element_type_combo)
        
        # 位置和尺寸
        position_frame = QFrame()
        position_layout = QHBoxLayout(position_frame)
        position_layout.setContentsMargins(0, 0, 0, 0)
        
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 1000)
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 1000)
        
        position_layout.addWidget(QLabel("X:"))
        position_layout.addWidget(self.x_spin)
        position_layout.addWidget(QLabel("Y:"))
        position_layout.addWidget(self.y_spin)
        
        layout.addRow("位置:", position_frame)
        
        size_frame = QFrame()
        size_layout = QHBoxLayout(size_frame)
        size_layout.setContentsMargins(0, 0, 0, 0)
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 1000)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 1000)
        
        size_layout.addWidget(QLabel("宽:"))
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(QLabel("高:"))
        size_layout.addWidget(self.height_spin)
        
        layout.addRow("尺寸:", size_frame)
        
        # 内容 - 使用增强文本编辑器和动态参数选择器
        content_frame = QFrame()
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(5)

        self.content_edit = EnhancedTextEdit()
        content_layout.addWidget(self.content_edit, 1)  # 占用大部分空间

        # 动态参数选择器
        self.param_selector = DynamicParameterSelector()
        self.param_selector.parameter_selected.connect(self._on_parameter_selected)
        content_layout.addWidget(self.param_selector)

        layout.addRow("内容:", content_frame)
        
        # 字体属性
        self.font_family_combo = QFontComboBox()
        layout.addRow("字体:", self.font_family_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 72)  # 🔤 超大字体：扩大范围支持到72px
        layout.addRow("字体大小:", self.font_size_spin)

        # 字体样式
        self.font_style_combo = QComboBox()
        self.font_style_combo.addItems(["normal", "bold", "italic", "bold_italic"])
        self.font_style_combo.setCurrentText("normal")
        layout.addRow("字体样式:", self.font_style_combo)
        
        # 颜色选择
        color_frame = QFrame()
        color_layout = QHBoxLayout(color_frame)
        color_layout.setContentsMargins(0, 0, 0, 0)
        
        self.text_color_btn = QPushButton("选择颜色")
        self.text_color_btn.clicked.connect(self._select_text_color)
        color_layout.addWidget(self.text_color_btn)
        
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(30, 20)
        self.color_preview.setStyleSheet("background-color: black; border: 1px solid gray;")
        color_layout.addWidget(self.color_preview)
        
        layout.addRow("文本颜色:", color_frame)
        
        # 可见性
        self.visible_check = QCheckBox("可见")
        self.visible_check.setChecked(True)
        layout.addRow("", self.visible_check)
        
        # 应用按钮
        self.apply_btn = QPushButton("应用更改")
        self.apply_btn.clicked.connect(self._apply_changes)
        layout.addRow("", self.apply_btn)
        
        # 初始状态禁用
        self.setEnabled(False)
    
    def _connect_signals(self):
        """连接信号"""
        # 实时更新信号连接
        self.x_spin.valueChanged.connect(self._on_property_changed)
        self.y_spin.valueChanged.connect(self._on_property_changed)
        self.width_spin.valueChanged.connect(self._on_property_changed)
        self.height_spin.valueChanged.connect(self._on_property_changed)
        self.content_edit.textChanged.connect(self._on_property_changed)
        self.font_family_combo.currentTextChanged.connect(self._on_property_changed)
        self.font_size_spin.valueChanged.connect(self._on_property_changed)
        self.font_style_combo.currentTextChanged.connect(self._on_property_changed)
        self.visible_check.toggled.connect(self._on_property_changed)
    
    def set_element(self, element: Optional[LabelElement]):
        """设置当前编辑的元素"""
        self.current_element = element
        
        if element:
            self.setEnabled(True)
            self._load_element_properties(element)
        else:
            self.setEnabled(False)
            self._clear_properties()
    
    def _load_element_properties(self, element: LabelElement):
        """加载元素属性到界面"""
        # 阻止信号触发
        self.blockSignals(True)
        
        try:
            self.element_id_edit.setText(element.element_id)
            self.element_type_combo.setCurrentText(element.element_type)
            
            self.x_spin.setValue(element.x)
            self.y_spin.setValue(element.y)
            self.width_spin.setValue(element.width)
            self.height_spin.setValue(element.height)
            
            self.content_edit.setText(element.content)
            self.font_family_combo.setCurrentText(element.font_family)
            self.font_size_spin.setValue(element.font_size)

            # 设置字体样式
            font_style = getattr(element, 'font_style', 'normal')
            self.font_style_combo.setCurrentText(font_style)

            # 更新颜色预览
            self.color_preview.setStyleSheet(
                f"background-color: {element.text_color}; border: 1px solid gray;"
            )
            
            self.visible_check.setChecked(element.visible)
            
        finally:
            # 恢复信号
            self.blockSignals(False)
    
    def _clear_properties(self):
        """清空属性界面"""
        self.element_id_edit.clear()
        self.content_edit.clear()
        self.x_spin.setValue(0)
        self.y_spin.setValue(0)
        self.width_spin.setValue(100)
        self.height_spin.setValue(20)
        self.font_size_spin.setValue(36)  # 🔤 超大字体：默认字体大小从14改为36
        self.visible_check.setChecked(True)
    
    def _select_text_color(self):
        """选择文本颜色"""
        if not self.current_element:
            return
        
        current_color = QColor(self.current_element.text_color)
        color = QColorDialog.getColor(current_color, self, "选择文本颜色")
        
        if color.isValid():
            color_name = color.name()
            self.color_preview.setStyleSheet(
                f"background-color: {color_name}; border: 1px solid gray;"
            )
            self._on_property_changed()
    
    def _on_property_changed(self):
        """属性变化处理"""
        if not self.current_element:
            return
        
        # 实时应用更改
        self._apply_changes()
    
    def _apply_changes(self):
        """应用更改"""
        if not self.current_element:
            return

        try:
            # 收集属性
            properties = {
                'x': self.x_spin.value(),
                'y': self.y_spin.value(),
                'width': self.width_spin.value(),
                'height': self.height_spin.value(),
                'content': self.content_edit.text(),
                'font_family': self.font_family_combo.currentText(),
                'font_size': self.font_size_spin.value(),
                'font_style': self.font_style_combo.currentText(),
                'text_color': self.color_preview.styleSheet().split('background-color: ')[1].split(';')[0],
                'visible': self.visible_check.isChecked()
            }

            # 发送更新信号
            self.element_updated.emit(self.current_element.element_id, properties)

        except Exception as e:
            logger.error(f"应用元素属性更改失败: {e}")

    def _on_parameter_selected(self, parameter: str):
        """动态参数选择处理"""
        try:
            # 将参数插入到文本编辑器中
            self.content_edit.insert_parameter(parameter)

            # 触发属性更改
            self._on_property_changed()

            logger.debug(f"插入动态参数: {parameter}")

        except Exception as e:
            logger.error(f"插入动态参数失败: {e}")


class ElementPropertyManager(QObject):
    """
    元素属性管理器
    
    职责：
    - 管理元素属性编辑组件
    - 处理属性更新逻辑
    - 管理属性状态
    """
    
    # 信号定义
    element_updated = pyqtSignal(str, dict)  # 元素更新信号
    
    def __init__(self, parent=None):
        """初始化元素属性管理器"""
        super().__init__(parent)
        
        self.property_widget = None
        self.current_element = None
        
        logger.debug("元素属性管理器初始化完成")
    
    def create_property_widget(self, parent=None) -> ElementPropertyWidget:
        """创建属性编辑组件"""
        try:
            self.property_widget = ElementPropertyWidget(parent)
            
            # 连接信号
            self.property_widget.element_updated.connect(self._on_element_updated)
            
            logger.debug("属性编辑组件创建完成")
            return self.property_widget
            
        except Exception as e:
            logger.error(f"创建属性编辑组件失败: {e}")
            return None
    
    def set_current_element(self, element: Optional[LabelElement]):
        """设置当前编辑的元素"""
        try:
            self.current_element = element
            
            if self.property_widget:
                self.property_widget.set_element(element)
            
            logger.debug(f"设置当前元素: {element.element_id if element else 'None'}")
            
        except Exception as e:
            logger.error(f"设置当前元素失败: {e}")
    
    def _on_element_updated(self, element_id: str, properties: Dict[str, Any]):
        """处理元素更新"""
        try:
            # 转发信号
            self.element_updated.emit(element_id, properties)
            
            logger.debug(f"元素属性更新: {element_id}")
            
        except Exception as e:
            logger.error(f"处理元素更新失败: {e}")
    
    def get_property_widget(self) -> Optional[ElementPropertyWidget]:
        """获取属性编辑组件"""
        return self.property_widget
    
    def cleanup(self):
        """清理资源"""
        try:
            self.current_element = None
            if self.property_widget:
                self.property_widget.set_element(None)
            
            logger.debug("元素属性管理器资源清理完成")
            
        except Exception as e:
            logger.error(f"元素属性管理器清理失败: {e}")
