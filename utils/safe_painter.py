# -*- coding: utf-8 -*-
"""
安全的QPainter上下文管理器
防止QPainter状态混乱导致的闪退问题

Author: Jack
Date: 2025-01-27
"""

import logging
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import QObject

logger = logging.getLogger(__name__)


class SafePainterContext:
    """安全的QPainter上下文管理器"""
    
    def __init__(self, device, auto_end=True):
        """
        初始化安全绘图上下文
        
        Args:
            device: 绘图设备
            auto_end: 是否自动结束绘图
        """
        self.device = device
        self.painter = None
        self.auto_end = auto_end
        self.is_active = False
    
    def __enter__(self):
        """进入上下文"""
        try:
            self.painter = QPainter(self.device)
            self.is_active = True
            logger.debug("✅ QPainter上下文已创建")
            return self.painter
        except Exception as e:
            logger.error(f"❌ 创建QPainter上下文失败: {e}")
            self.is_active = False
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        try:
            if self.painter and self.is_active and self.auto_end:
                if self.painter.isActive():
                    self.painter.end()
                    logger.debug("✅ QPainter已安全结束")
                else:
                    logger.debug("ℹ️ QPainter已经结束")
            self.is_active = False
        except Exception as e:
            logger.error(f"❌ 结束QPainter上下文失败: {e}")
        finally:
            self.painter = None


def safe_painter(device, auto_end=True):
    """
    创建安全的QPainter上下文管理器
    
    Args:
        device: 绘图设备
        auto_end: 是否自动结束绘图
    
    Returns:
        SafePainterContext实例
    
    Example:
        with safe_painter(widget) as painter:
            painter.drawText(10, 10, "Hello")
    """
    return SafePainterContext(device, auto_end)


class SafeUpdateContext:
    """安全的UI更新上下文管理器"""
    
    def __init__(self, widget):
        """
        初始化安全更新上下文
        
        Args:
            widget: 要更新的组件
        """
        self.widget = widget
        self.was_enabled = True
    
    def __enter__(self):
        """进入上下文"""
        try:
            if self.widget and hasattr(self.widget, 'updatesEnabled'):
                self.was_enabled = self.widget.updatesEnabled()
                if self.was_enabled:
                    self.widget.setUpdatesEnabled(False)
                    logger.debug("✅ UI更新已暂停")
            return self.widget
        except Exception as e:
            logger.error(f"❌ 暂停UI更新失败: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        try:
            if self.widget and hasattr(self.widget, 'setUpdatesEnabled') and self.was_enabled:
                self.widget.setUpdatesEnabled(True)
                logger.debug("✅ UI更新已恢复")
        except Exception as e:
            logger.error(f"❌ 恢复UI更新失败: {e}")


def safe_update(widget):
    """
    创建安全的UI更新上下文管理器
    
    Args:
        widget: 要更新的组件
    
    Returns:
        SafeUpdateContext实例
    
    Example:
        with safe_update(widget):
            widget.setText("New text")
            widget.setValue(50)
    """
    return SafeUpdateContext(widget)


class PaintEventFilter(QObject):
    """绘图事件过滤器，防止递归绘图"""
    
    def __init__(self):
        super().__init__()
        self.painting_widgets = set()
    
    def eventFilter(self, obj, event):
        """事件过滤器"""
        try:
            if event.type() == event.Paint:
                widget_id = id(obj)
                
                # 检查是否已在绘制中
                if widget_id in self.painting_widgets:
                    logger.warning(f"⚠️ 检测到递归绘图，跳过: {obj.__class__.__name__}")
                    return True  # 拦截事件
                
                # 标记开始绘制
                self.painting_widgets.add(widget_id)
                
                # 处理完成后清除标记
                def cleanup():
                    self.painting_widgets.discard(widget_id)
                
                # 使用定时器延迟清除标记
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, cleanup)
            
            return False  # 继续处理事件
            
        except Exception as e:
            logger.error(f"❌ 绘图事件过滤失败: {e}")
            return False


# 全局绘图事件过滤器实例
_paint_filter = PaintEventFilter()


def install_paint_filter(widget):
    """
    为组件安装绘图事件过滤器
    
    Args:
        widget: 要保护的组件
    """
    # 绘图事件过滤器禁用: 暂时禁用绘图事件过滤器，避免递归检测问题
    try:
        # widget.installEventFilter(_paint_filter)  # 暂时禁用
        logger.debug(f"✅ 已为 {widget.__class__.__name__} 跳过绘图保护安装")
    except Exception as e:
        logger.error(f"❌ 安装绘图保护失败: {e}")


def remove_paint_filter(widget):
    """
    移除组件的绘图事件过滤器
    
    Args:
        widget: 要移除保护的组件
    """
    try:
        widget.removeEventFilter(_paint_filter)
        logger.debug(f"✅ 已为 {widget.__class__.__name__} 移除绘图保护")
    except Exception as e:
        logger.error(f"❌ 移除绘图保护失败: {e}")
