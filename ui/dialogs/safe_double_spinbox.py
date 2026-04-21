#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全的双精度数值输入框
支持小数点后3位精度和安全的回车键处理

Author: Jack
Date: 2025-06-04
"""

import logging
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent

logger = logging.getLogger(__name__)


class SafeDoubleSpinBox(QDoubleSpinBox):
    """安全的QDoubleSpinBox，支持小数点后3位精度和安全的回车键处理"""

    def __init__(self, parent=None):
        """初始化SafeDoubleSpinBox"""
        super().__init__(parent)
        
        # 默认设置3位小数精度
        self.setDecimals(3)
        
        # 设置合理的范围
        self.setRange(0.001, 9999.999)
        
        # 设置步长为0.001
        self.setSingleStep(0.001)
        
        # 启用键盘跟踪
        self.setKeyboardTracking(True)

    def keyPressEvent(self, event: QKeyEvent):
        """重写键盘事件处理"""
        try:
            # 如果是回车键，确认输入并移动到下一个控件
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                # 先让父类处理输入，确保值被正确解析
                super().keyPressEvent(event)
                # 确保文本被正确解释为数值
                self.interpretText()
                # 移动焦点到下一个控件（而不是清除焦点）
                self.focusNextChild()
                return

            # Tab键正常处理（移动到下一个控件）
            elif event.key() == Qt.Key.Key_Tab:
                super().keyPressEvent(event)
                return

            # Shift+Tab键正常处理（移动到上一个控件）
            elif event.key() == Qt.Key.Key_Backtab:
                super().keyPressEvent(event)
                return

            # 其他键正常处理
            super().keyPressEvent(event)

        except Exception as e:
            logger.error(f"SafeDoubleSpinBox键盘事件处理失败: {e}")
            # 发生异常时也要调用父类方法
            try:
                super().keyPressEvent(event)
            except:
                pass

    def setValue(self, value: float):
        """重写setValue方法，确保精度正确"""
        try:
            # 确保值在有效范围内
            value = max(self.minimum(), min(self.maximum(), value))
            # 调用父类方法
            super().setValue(value)
        except Exception as e:
            logger.error(f"SafeDoubleSpinBox设置值失败: {e}")

    def value(self) -> float:
        """重写value方法，确保返回正确精度的值"""
        try:
            val = super().value()
            # 确保返回值的精度符合设置
            return round(val, self.decimals())
        except Exception as e:
            logger.error(f"SafeDoubleSpinBox获取值失败: {e}")
            return 0.0
    
    def setValueSafe(self, value: float, min_val: float = None, max_val: float = None):
        """安全设置值，可选择性设置范围"""
        try:
            if min_val is not None and max_val is not None:
                self.setRange(min_val, max_val)
            
            # 确保值在范围内
            value = max(self.minimum(), min(self.maximum(), value))
            self.setValue(value)
            
        except Exception as e:
            logger.error(f"安全设置值失败: {e}")
    
    def setRangeSafe(self, min_val: float, max_val: float):
        """安全设置范围"""
        try:
            # 确保最小值小于最大值
            if min_val >= max_val:
                logger.warning(f"范围设置错误: min({min_val}) >= max({max_val})")
                return
            
            self.setRange(min_val, max_val)
            
            # 如果当前值超出范围，调整到范围内
            current_val = self.value()
            if current_val < min_val:
                self.setValue(min_val)
            elif current_val > max_val:
                self.setValue(max_val)
                
        except Exception as e:
            logger.error(f"安全设置范围失败: {e}")
    
    def getValueSafe(self) -> float:
        """安全获取值"""
        try:
            return self.value()
        except Exception as e:
            logger.error(f"安全获取值失败: {e}")
            return 0.0
    
    def setDecimalsSafe(self, decimals: int):
        """安全设置小数位数"""
        try:
            if decimals < 0:
                decimals = 0
            elif decimals > 6:  # 限制最大小数位数
                decimals = 6
            
            self.setDecimals(decimals)
            
        except Exception as e:
            logger.error(f"安全设置小数位数失败: {e}")
    
    def setSuffixSafe(self, suffix: str):
        """安全设置后缀"""
        try:
            if suffix is None:
                suffix = ""
            self.setSuffix(suffix)
            
        except Exception as e:
            logger.error(f"安全设置后缀失败: {e}")
    
    def setPrefixSafe(self, prefix: str):
        """安全设置前缀"""
        try:
            if prefix is None:
                prefix = ""
            self.setPrefix(prefix)
            
        except Exception as e:
            logger.error(f"安全设置前缀失败: {e}")
    
    def setToolTipSafe(self, tooltip: str):
        """安全设置工具提示"""
        try:
            if tooltip is None:
                tooltip = ""
            self.setToolTip(tooltip)
            
        except Exception as e:
            logger.error(f"安全设置工具提示失败: {e}")
    
    def setStepSafe(self, step: float):
        """安全设置步长"""
        try:
            if step <= 0:
                step = 0.001  # 默认步长
            
            self.setSingleStep(step)
            
        except Exception as e:
            logger.error(f"安全设置步长失败: {e}")
    
    def resetToDefault(self):
        """重置到默认设置"""
        try:
            self.setDecimals(3)
            self.setRange(0.001, 9999.999)
            self.setSingleStep(0.001)
            self.setValue(0.001)
            self.setSuffix("")
            self.setPrefix("")
            
        except Exception as e:
            logger.error(f"重置到默认设置失败: {e}")
    
    def validateInput(self) -> bool:
        """验证当前输入是否有效"""
        try:
            current_val = self.value()
            return self.minimum() <= current_val <= self.maximum()
            
        except Exception as e:
            logger.error(f"验证输入失败: {e}")
            return False
    
    def getDisplayText(self) -> str:
        """获取显示文本（包含前缀和后缀）"""
        try:
            return self.text()
        except Exception as e:
            logger.error(f"获取显示文本失败: {e}")
            return ""
    
    def setReadOnlySafe(self, readonly: bool):
        """安全设置只读状态"""
        try:
            self.setReadOnly(readonly)
            if readonly:
                self.setStyleSheet("QDoubleSpinBox { background-color: #f0f0f0; }")
            else:
                self.setStyleSheet("")
                
        except Exception as e:
            logger.error(f"安全设置只读状态失败: {e}")
    
    def setEnabledSafe(self, enabled: bool):
        """安全设置启用状态"""
        try:
            self.setEnabled(enabled)
            
        except Exception as e:
            logger.error(f"安全设置启用状态失败: {e}")
    
    def clearValue(self):
        """清除值（设置为最小值）"""
        try:
            self.setValue(self.minimum())
            
        except Exception as e:
            logger.error(f"清除值失败: {e}")
    
    def incrementSafe(self):
        """安全递增"""
        try:
            current_val = self.value()
            step = self.singleStep()
            new_val = current_val + step
            
            if new_val <= self.maximum():
                self.setValue(new_val)
                return True
            return False
            
        except Exception as e:
            logger.error(f"安全递增失败: {e}")
            return False
    
    def decrementSafe(self):
        """安全递减"""
        try:
            current_val = self.value()
            step = self.singleStep()
            new_val = current_val - step
            
            if new_val >= self.minimum():
                self.setValue(new_val)
                return True
            return False
            
        except Exception as e:
            logger.error(f"安全递减失败: {e}")
            return False
