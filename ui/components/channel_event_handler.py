#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通道事件处理器
负责处理通道相关的事件，包括鼠标点击、状态变化等

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Optional, Dict, Any, Callable
from PyQt5.QtCore import QObject, pyqtSignal, QEvent
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QMouseEvent

from .channel_state_manager import ChannelStateManager, StateChangeEvent

logger = logging.getLogger(__name__)


class ChannelEventHandler(QObject):
    """通道事件处理器"""
    
    # 信号定义
    channel_clicked = pyqtSignal(int)  # 通道被点击
    channel_double_clicked = pyqtSignal(int)  # 通道被双击
    enable_state_changed = pyqtSignal(int, bool)  # 使能状态变化
    test_state_changed = pyqtSignal(int, str, str)  # 测试状态变化 (channel, old_state, new_state)
    
    def __init__(self, channel_number: int, widget: QWidget):
        """
        初始化事件处理器
        
        Args:
            channel_number: 通道号（1-8）
            widget: 关联的widget
        """
        super().__init__()
        
        self.channel_number = channel_number
        self.channel_index = channel_number - 1
        self.widget = widget
        
        # 事件回调
        self.click_callbacks = []
        self.double_click_callbacks = []
        self.enable_change_callbacks = []
        self.state_change_callbacks = []
        
        # 鼠标事件状态
        self._mouse_pressed = False
        self._click_position = None
        
        # 安装事件过滤器
        if self.widget:
            self.widget.installEventFilter(self)
        
        logger.debug(f"通道{self.channel_number}事件处理器初始化完成")
    
    def eventFilter(self, obj, event):
        """事件过滤器"""
        try:
            if obj == self.widget:
                if event.type() == QEvent.MouseButtonPress:
                    return self._handle_mouse_press(event)
                elif event.type() == QEvent.MouseButtonRelease:
                    return self._handle_mouse_release(event)
                elif event.type() == QEvent.MouseButtonDblClick:
                    return self._handle_mouse_double_click(event)
            
            return super().eventFilter(obj, event)
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}事件过滤器处理失败: {e}")
            return False
    
    def _handle_mouse_press(self, event: QMouseEvent) -> bool:
        """处理鼠标按下事件"""
        try:
            if event.button() == Qt.LeftButton:
                self._mouse_pressed = True
                self._click_position = event.pos()
                logger.debug(f"通道{self.channel_number}鼠标按下: {event.pos()}")
            
            return False  # 不阻止事件传播
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}处理鼠标按下事件失败: {e}")
            return False
    
    def _handle_mouse_release(self, event: QMouseEvent) -> bool:
        """处理鼠标释放事件"""
        try:
            if event.button() == Qt.LeftButton and self._mouse_pressed:
                self._mouse_pressed = False
                
                # 检查是否为有效点击（位置没有移动太多）
                if self._click_position is not None and self._is_valid_click(event.pos()):
                    self._trigger_click_event()
                
                self._click_position = None
                logger.debug(f"通道{self.channel_number}鼠标释放: {event.pos()}")
            
            return False  # 不阻止事件传播
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}处理鼠标释放事件失败: {e}")
            return False
    
    def _handle_mouse_double_click(self, event: QMouseEvent) -> bool:
        """处理鼠标双击事件"""
        try:
            if event.button() == Qt.LeftButton:
                self._trigger_double_click_event()
                logger.debug(f"通道{self.channel_number}鼠标双击: {event.pos()}")
            
            return False  # 不阻止事件传播
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}处理鼠标双击事件失败: {e}")
            return False
    
    def _is_valid_click(self, current_pos) -> bool:
        """检查是否为有效点击"""
        if self._click_position is None:
            return False
        
        # 计算位置偏移
        dx = abs(current_pos.x() - self._click_position.x())
        dy = abs(current_pos.y() - self._click_position.y())
        
        # 如果偏移小于5像素，认为是有效点击
        return dx < 5 and dy < 5
    
    def _trigger_click_event(self):
        """触发点击事件"""
        try:
            # 发射信号
            self.channel_clicked.emit(self.channel_number)
            
            # 调用回调函数
            for callback in self.click_callbacks:
                try:
                    callback(self.channel_number)
                except Exception as e:
                    logger.error(f"通道{self.channel_number}点击回调执行失败: {e}")
            
            logger.debug(f"通道{self.channel_number}点击事件触发")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}触发点击事件失败: {e}")
    
    def _trigger_double_click_event(self):
        """触发双击事件"""
        try:
            # 发射信号
            self.channel_double_clicked.emit(self.channel_number)
            
            # 调用回调函数
            for callback in self.double_click_callbacks:
                try:
                    callback(self.channel_number)
                except Exception as e:
                    logger.error(f"通道{self.channel_number}双击回调执行失败: {e}")
            
            logger.debug(f"通道{self.channel_number}双击事件触发")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}触发双击事件失败: {e}")
    
    def handle_enable_state_change(self, enabled: bool):
        """处理使能状态变化"""
        try:
            # 发射信号
            self.enable_state_changed.emit(self.channel_number, enabled)
            
            # 调用回调函数
            for callback in self.enable_change_callbacks:
                try:
                    callback(self.channel_number, enabled)
                except Exception as e:
                    logger.error(f"通道{self.channel_number}使能状态变化回调执行失败: {e}")
            
            logger.debug(f"通道{self.channel_number}使能状态变化: {enabled}")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}处理使能状态变化失败: {e}")
    
    def handle_state_change_event(self, event: StateChangeEvent):
        """处理状态变化事件"""
        try:
            # 发射信号
            self.test_state_changed.emit(
                self.channel_number,
                event.old_state.value,
                event.new_state.value
            )
            
            # 调用回调函数
            for callback in self.state_change_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"通道{self.channel_number}状态变化回调执行失败: {e}")
            
            logger.debug(f"通道{self.channel_number}状态变化事件处理: {event.old_state.value} -> {event.new_state.value}")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}处理状态变化事件失败: {e}")
    
    def add_click_callback(self, callback: Callable[[int], None]) -> bool:
        """
        添加点击回调
        
        Args:
            callback: 回调函数
            
        Returns:
            是否添加成功
        """
        try:
            if callback not in self.click_callbacks:
                self.click_callbacks.append(callback)
                logger.debug(f"通道{self.channel_number}添加点击回调")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}添加点击回调失败: {e}")
            return False
    
    def add_double_click_callback(self, callback: Callable[[int], None]) -> bool:
        """
        添加双击回调
        
        Args:
            callback: 回调函数
            
        Returns:
            是否添加成功
        """
        try:
            if callback not in self.double_click_callbacks:
                self.double_click_callbacks.append(callback)
                logger.debug(f"通道{self.channel_number}添加双击回调")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}添加双击回调失败: {e}")
            return False
    
    def add_enable_change_callback(self, callback: Callable[[int, bool], None]) -> bool:
        """
        添加使能状态变化回调
        
        Args:
            callback: 回调函数
            
        Returns:
            是否添加成功
        """
        try:
            if callback not in self.enable_change_callbacks:
                self.enable_change_callbacks.append(callback)
                logger.debug(f"通道{self.channel_number}添加使能状态变化回调")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}添加使能状态变化回调失败: {e}")
            return False
    
    def add_state_change_callback(self, callback: Callable[[StateChangeEvent], None]) -> bool:
        """
        添加状态变化回调
        
        Args:
            callback: 回调函数
            
        Returns:
            是否添加成功
        """
        try:
            if callback not in self.state_change_callbacks:
                self.state_change_callbacks.append(callback)
                logger.debug(f"通道{self.channel_number}添加状态变化回调")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}添加状态变化回调失败: {e}")
            return False
    
    def remove_click_callback(self, callback: Callable[[int], None]) -> bool:
        """移除点击回调"""
        try:
            if callback in self.click_callbacks:
                self.click_callbacks.remove(callback)
                logger.debug(f"通道{self.channel_number}移除点击回调")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}移除点击回调失败: {e}")
            return False
    
    def remove_double_click_callback(self, callback: Callable[[int], None]) -> bool:
        """移除双击回调"""
        try:
            if callback in self.double_click_callbacks:
                self.double_click_callbacks.remove(callback)
                logger.debug(f"通道{self.channel_number}移除双击回调")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}移除双击回调失败: {e}")
            return False
    
    def remove_enable_change_callback(self, callback: Callable[[int, bool], None]) -> bool:
        """移除使能状态变化回调"""
        try:
            if callback in self.enable_change_callbacks:
                self.enable_change_callbacks.remove(callback)
                logger.debug(f"通道{self.channel_number}移除使能状态变化回调")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}移除使能状态变化回调失败: {e}")
            return False
    
    def remove_state_change_callback(self, callback: Callable[[StateChangeEvent], None]) -> bool:
        """移除状态变化回调"""
        try:
            if callback in self.state_change_callbacks:
                self.state_change_callbacks.remove(callback)
                logger.debug(f"通道{self.channel_number}移除状态变化回调")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}移除状态变化回调失败: {e}")
            return False
    
    def clear_all_callbacks(self):
        """清除所有回调"""
        try:
            self.click_callbacks.clear()
            self.double_click_callbacks.clear()
            self.enable_change_callbacks.clear()
            self.state_change_callbacks.clear()
            logger.debug(f"通道{self.channel_number}所有回调已清除")
        except Exception as e:
            logger.error(f"通道{self.channel_number}清除回调失败: {e}")
    
    def get_event_summary(self) -> Dict[str, Any]:
        """
        获取事件摘要
        
        Returns:
            事件摘要字典
        """
        try:
            return {
                'channel_number': self.channel_number,
                'click_callbacks_count': len(self.click_callbacks),
                'double_click_callbacks_count': len(self.double_click_callbacks),
                'enable_change_callbacks_count': len(self.enable_change_callbacks),
                'state_change_callbacks_count': len(self.state_change_callbacks),
                'mouse_pressed': self._mouse_pressed
            }
        except Exception as e:
            logger.error(f"通道{self.channel_number}获取事件摘要失败: {e}")
            return {}
