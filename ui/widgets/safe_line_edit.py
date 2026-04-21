#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全的QLineEdit组件

防止回车键意外关闭对话框的自定义QLineEdit组件

Author: Jack
Date: 2025-05-31
"""

import logging
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent

logger = logging.getLogger(__name__)


class SafeLineEdit(QLineEdit):
    """
    安全的QLineEdit，防止回车键关闭对话框
    
    功能特性：
    1. 拦截回车键事件，防止意外关闭对话框
    2. 回车键只确认输入并移动焦点到下一个控件
    3. 保持Tab键的正常焦点切换功能
    4. 支持Shift+Tab反向焦点切换
    5. 其他键盘事件正常处理
    """
    
    def __init__(self, parent=None, allow_enter_passthrough=False):
        """
        初始化SafeLineEdit

        Args:
            parent: 父控件
            allow_enter_passthrough: 是否允许回车键传递给父控件
        """
        super().__init__(parent)

        # 设置是否允许回车键传递
        self.allow_enter_passthrough = allow_enter_passthrough

        # 设置工具提示
        if allow_enter_passthrough:
            self.setToolTip("按回车键触发父控件的确认操作")
        else:
            self.setToolTip("按回车键确认输入并移动到下一个控件")

        logger.debug(f"SafeLineEdit初始化完成，允许回车键传递: {allow_enter_passthrough}")
    
    def keyPressEvent(self, event: QKeyEvent):
        """
        重写键盘事件处理
        
        Args:
            event: 键盘事件
        """
        try:
            # 获取按键代码
            key = event.key()
            
            # 处理回车键（Enter/Return）
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                logger.debug(f"SafeLineEdit: 检测到回车键，允许传递: {self.allow_enter_passthrough}")

                if self.allow_enter_passthrough:
                    # 允许回车键传递给父控件（如对话框的确认按钮）
                    logger.debug("SafeLineEdit: 回车键传递给父控件")
                    super().keyPressEvent(event)
                    return
                else:
                    # 拦截回车键，防止触发对话框默认按钮
                    logger.debug("SafeLineEdit: 拦截回车键事件")

                    # 确认当前输入（失去焦点会触发editingFinished信号）
                    self.clearFocus()

                    # 移动焦点到下一个控件
                    self.focusNextChild()

                    # 不传递事件给父控件
                    return
            
            # 处理Tab键（正常处理，移动到下一个控件）
            elif key == Qt.Key.Key_Tab:
                logger.debug("SafeLineEdit: 处理Tab键")
                super().keyPressEvent(event)
                return

            # 处理Shift+Tab键（反向移动焦点）
            elif key == Qt.Key.Key_Backtab:
                logger.debug("SafeLineEdit: 处理Shift+Tab键")
                super().keyPressEvent(event)
                return

            # 处理Escape键（清除输入或失去焦点）
            elif key == Qt.Key.Key_Escape:
                logger.debug("SafeLineEdit: 处理Escape键")
                # 如果有选中文本，先清除选择
                if self.hasSelectedText():
                    self.deselect()
                else:
                    # 否则失去焦点
                    self.clearFocus()
                return
            
            # 其他键正常处理
            else:
                super().keyPressEvent(event)
                
        except Exception as e:
            logger.error(f"SafeLineEdit键盘事件处理失败: {e}")
            # 发生异常时也要调用父类方法，确保基本功能正常
            try:
                super().keyPressEvent(event)
            except Exception as fallback_error:
                logger.error(f"SafeLineEdit键盘事件回退处理也失败: {fallback_error}")
    
    def focusInEvent(self, event):
        """
        重写焦点进入事件
        
        Args:
            event: 焦点事件
        """
        try:
            super().focusInEvent(event)
            logger.debug("SafeLineEdit: 获得焦点")
            
        except Exception as e:
            logger.error(f"SafeLineEdit焦点进入事件处理失败: {e}")
    
    def focusOutEvent(self, event):
        """
        重写焦点离开事件
        
        Args:
            event: 焦点事件
        """
        try:
            super().focusOutEvent(event)
            logger.debug("SafeLineEdit: 失去焦点")
            
        except Exception as e:
            logger.error(f"SafeLineEdit焦点离开事件处理失败: {e}")
    
    def setText(self, text: str):
        """
        重写setText方法，添加日志记录
        
        Args:
            text: 要设置的文本
        """
        try:
            super().setText(text)
            logger.debug(f"SafeLineEdit: 设置文本 '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
        except Exception as e:
            logger.error(f"SafeLineEdit设置文本失败: {e}")
    
    def setPlaceholderText(self, text: str):
        """
        重写setPlaceholderText方法，添加日志记录
        
        Args:
            text: 占位符文本
        """
        try:
            super().setPlaceholderText(text)
            logger.debug(f"SafeLineEdit: 设置占位符文本 '{text}'")
            
        except Exception as e:
            logger.error(f"SafeLineEdit设置占位符文本失败: {e}")


class SafePasswordLineEdit(SafeLineEdit):
    """
    安全的密码输入框
    
    继承SafeLineEdit的所有功能，并添加密码输入特性
    """
    
    def __init__(self, parent=None):
        """
        初始化SafePasswordLineEdit
        
        Args:
            parent: 父控件
        """
        super().__init__(parent)
        
        # 设置密码模式
        self.setEchoMode(QLineEdit.Password)
        
        # 更新工具提示
        self.setToolTip("密码输入框 - 按回车键确认输入并移动到下一个控件")
        
        logger.debug("SafePasswordLineEdit初始化完成")
    
    def keyPressEvent(self, event: QKeyEvent):
        """
        重写键盘事件处理（密码输入框特殊处理）
        
        Args:
            event: 键盘事件
        """
        try:
            # 对于密码输入框，可以添加特殊的键盘处理逻辑
            # 例如：Ctrl+A全选、Ctrl+C复制等可能需要禁用
            
            key = event.key()
            modifiers = event.modifiers()
            
            # 禁用Ctrl+C复制（安全考虑）
            if key == Qt.Key.Key_C and modifiers == Qt.KeyboardModifier.ControlModifier:
                logger.debug("SafePasswordLineEdit: 禁用密码复制")
                return
            
            # 其他事件交给父类处理
            super().keyPressEvent(event)
            
        except Exception as e:
            logger.error(f"SafePasswordLineEdit键盘事件处理失败: {e}")
            # 回退到父类处理
            try:
                super().keyPressEvent(event)
            except Exception as fallback_error:
                logger.error(f"SafePasswordLineEdit键盘事件回退处理也失败: {fallback_error}")


# 为了向后兼容，提供一个工厂函数
def create_safe_line_edit(parent=None, password=False):
    """
    创建安全的QLineEdit控件
    
    Args:
        parent: 父控件
        password: 是否为密码输入框
        
    Returns:
        SafeLineEdit或SafePasswordLineEdit实例
    """
    if password:
        return SafePasswordLineEdit(parent)
    else:
        return SafeLineEdit(parent)
