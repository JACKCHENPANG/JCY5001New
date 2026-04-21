# -*- coding: utf-8 -*-
"""
电池类型配置对话框
用于添加和编辑电池类型参数

Author: Jack
Date: 2025-06-22
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QDoubleSpinBox, QPushButton, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BatteryTypeDialog(QDialog):
    """电池类型配置对话框"""
    
    def __init__(self, parent=None, battery_data: Optional[Dict[str, Any]] = None):
        """
        初始化电池类型对话框
        
        Args:
            parent: 父窗口
            battery_data: 现有电池数据（编辑模式）
        """
        super().__init__(parent)
        
        self.battery_data = battery_data or {}
        self.is_edit_mode = battery_data is not None
        
        self._init_ui()
        self._init_connections()
        self._load_data()
        
        logger.debug(f"电池类型对话框初始化完成 (编辑模式: {self.is_edit_mode})")
    
    def _init_ui(self):
        """初始化界面"""
        # 设置对话框属性
        title = "编辑电池类型" if self.is_edit_mode else "添加电池类型"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(400, 350)
        
        # 创建主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)
        
        # 电池类型名称
        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText("例如: LiFePO4_3000mAh")
        basic_layout.addRow("电池类型:", self.type_edit)
        
        # 标称容量
        self.capacity_spin = QDoubleSpinBox()
        self.capacity_spin.setRange(0.1, 100.0)
        self.capacity_spin.setDecimals(3)
        self.capacity_spin.setSuffix(" AH")
        self.capacity_spin.setValue(3.0)
        basic_layout.addRow("标称容量:", self.capacity_spin)
        
        layout.addWidget(basic_group)
        
        # 基准阻抗组
        baseline_group = QGroupBox("基准阻抗")
        baseline_layout = QFormLayout(baseline_group)
        
        # 基准Rs
        self.baseline_rs_spin = QDoubleSpinBox()
        self.baseline_rs_spin.setRange(0.1, 100.0)
        self.baseline_rs_spin.setDecimals(3)
        self.baseline_rs_spin.setSuffix(" mΩ")
        self.baseline_rs_spin.setValue(2.0)
        baseline_layout.addRow("基准Rs:", self.baseline_rs_spin)
        
        # 基准Rct
        self.baseline_rct_spin = QDoubleSpinBox()
        self.baseline_rct_spin.setRange(0.1, 1000.0)
        self.baseline_rct_spin.setDecimals(3)
        self.baseline_rct_spin.setSuffix(" mΩ")
        self.baseline_rct_spin.setValue(5.0)
        baseline_layout.addRow("基准Rct:", self.baseline_rct_spin)
        
        layout.addWidget(baseline_group)
        
        # SOH系数组
        coefficient_group = QGroupBox("SOH系数")
        coefficient_layout = QFormLayout(coefficient_group)
        
        # Rs系数a
        self.rs_a_spin = QDoubleSpinBox()
        self.rs_a_spin.setRange(-100.0, 100.0)
        self.rs_a_spin.setDecimals(3)
        self.rs_a_spin.setValue(-6.67)
        coefficient_layout.addRow("Rs系数a:", self.rs_a_spin)
        
        # Rs系数b
        self.rs_b_spin = QDoubleSpinBox()
        self.rs_b_spin.setRange(0.0, 200.0)
        self.rs_b_spin.setDecimals(3)
        self.rs_b_spin.setValue(88.33)
        coefficient_layout.addRow("Rs系数b:", self.rs_b_spin)
        
        # Rct系数a
        self.rct_a_spin = QDoubleSpinBox()
        self.rct_a_spin.setRange(-100.0, 100.0)
        self.rct_a_spin.setDecimals(3)
        self.rct_a_spin.setValue(-1.0)
        coefficient_layout.addRow("Rct系数a:", self.rct_a_spin)
        
        # Rct系数b
        self.rct_b_spin = QDoubleSpinBox()
        self.rct_b_spin.setRange(0.0, 200.0)
        self.rct_b_spin.setDecimals(3)
        self.rct_b_spin.setValue(95.0)
        coefficient_layout.addRow("Rct系数b:", self.rct_b_spin)
        
        layout.addWidget(coefficient_group)
        
        # 说明标签
        info_label = QLabel("注意：系数a和b用于SOH计算公式 SOH = a * Δ阻抗 + b")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(info_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("确定")
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("取消")
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def _init_connections(self):
        """初始化信号连接"""
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.cancel_button.clicked.connect(self.reject)
    
    def _load_data(self):
        """加载数据"""
        if not self.is_edit_mode:
            return
        
        try:
            # 加载基本信息
            self.type_edit.setText(self.battery_data.get('type', ''))
            self.capacity_spin.setValue(self.battery_data.get('nominal_capacity', 3.0))
            
            # 加载基准阻抗
            self.baseline_rs_spin.setValue(self.battery_data.get('baseline_rs', 2.0))
            self.baseline_rct_spin.setValue(self.battery_data.get('baseline_rct', 5.0))
            
            # 加载SOH系数
            rs_method = self.battery_data.get('rs_method', {})
            self.rs_a_spin.setValue(rs_method.get('a', -6.67))
            self.rs_b_spin.setValue(rs_method.get('b', 88.33))
            
            rct_method = self.battery_data.get('rct_method', {})
            self.rct_a_spin.setValue(rct_method.get('a', -1.0))
            self.rct_b_spin.setValue(rct_method.get('b', 95.0))
            
            # 编辑模式下禁用类型名称修改
            self.type_edit.setReadOnly(True)
            
        except Exception as e:
            logger.error(f"加载电池数据失败: {e}")
            QMessageBox.warning(self, "警告", f"加载电池数据失败: {e}")
    
    def _on_ok_clicked(self):
        """确定按钮点击处理"""
        if self._validate_data():
            self.accept()
    
    def _validate_data(self) -> bool:
        """验证数据"""
        # 验证电池类型名称
        battery_type = self.type_edit.text().strip()
        if not battery_type:
            QMessageBox.warning(self, "验证失败", "电池类型名称不能为空")
            self.type_edit.setFocus()
            return False
        
        # 验证容量
        if self.capacity_spin.value() <= 0:
            QMessageBox.warning(self, "验证失败", "标称容量必须大于0")
            self.capacity_spin.setFocus()
            return False
        
        # 验证基准阻抗
        if self.baseline_rs_spin.value() <= 0:
            QMessageBox.warning(self, "验证失败", "基准Rs必须大于0")
            self.baseline_rs_spin.setFocus()
            return False
        
        if self.baseline_rct_spin.value() <= 0:
            QMessageBox.warning(self, "验证失败", "基准Rct必须大于0")
            self.baseline_rct_spin.setFocus()
            return False
        
        return True
    
    def get_battery_data(self) -> Dict[str, Any]:
        """获取电池数据"""
        return {
            'type': self.type_edit.text().strip(),
            'nominal_capacity': self.capacity_spin.value(),
            'baseline_rs': self.baseline_rs_spin.value(),
            'baseline_rct': self.baseline_rct_spin.value(),
            'rs_method': {
                'a': self.rs_a_spin.value(),
                'b': self.rs_b_spin.value()
            },
            'rct_method': {
                'a': self.rct_a_spin.value(),
                'b': self.rct_b_spin.value()
            }
        }
