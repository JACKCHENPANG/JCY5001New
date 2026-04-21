# -*- coding: utf-8 -*-
"""
窗口管理器
负责主窗口的窗口状态管理、全屏切换、关闭事件等功能

Author: Jack
Date: 2025-06-27
"""

import logging
from typing import Optional
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, Qt

logger = logging.getLogger(__name__)


class WindowManager(QObject):
    """窗口管理器"""
    
    # 信号定义
    fullscreen_toggled = pyqtSignal(bool)  # 全屏状态切换信号
    window_closing = pyqtSignal()  # 窗口关闭信号
    window_status_changed = pyqtSignal(str)  # 窗口状态变更信号
    
    def __init__(self, main_window: QMainWindow, config_manager, parent=None):
        """
        初始化窗口管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
            parent: 父对象
        """
        super().__init__(parent)
        
        self.main_window = main_window
        self.config_manager = config_manager
        
        # 窗口状态
        self.is_fullscreen = False
        self.previous_geometry = None
        
        # 窗口监控定时器
        self.window_monitor_timer = None
        
        # 初始化窗口监控
        self._init_window_monitor()
        
    def _init_window_monitor(self):
        """初始化窗口状态监控定时器"""
        try:
            # 创建定时器监控窗口状态
            self.window_monitor_timer = QTimer()
            self.window_monitor_timer.timeout.connect(self._check_window_status)
            self.window_monitor_timer.start(5000)  # 每5秒检查一次
            logger.info("✅ 窗口状态监控定时器已启动")
        except Exception as e:
            logger.error(f"❌ 初始化窗口监控失败: {e}")

    def _check_window_status(self):
        """检查窗口状态"""
        try:
            if self.main_window.isHidden() or self.main_window.isMinimized():
                logger.warning(f"⚠️ 检测到窗口异常状态: hidden={self.main_window.isHidden()}, minimized={self.main_window.isMinimized()}")
                # 强制显示窗口
                self.main_window.showMaximized()
                self.main_window.raise_()
                self.main_window.activateWindow()
                logger.info(f"✅ 窗口已强制恢复显示")
                self.window_status_changed.emit("restored")
        except Exception as e:
            logger.error(f"❌ 检查窗口状态失败: {e}")

    def handle_key_press_event(self, event):
        """
        处理键盘事件
        
        Args:
            event: 键盘事件
            
        Returns:
            bool: 是否已处理事件
        """
        try:
            # F11键或ESC键切换/退出全屏
            if event.key() == Qt.Key.Key_F11:
                self.toggle_fullscreen()
                return True
            elif event.key() == Qt.Key.Key_Escape and self.main_window.isFullScreen():
                self.exit_fullscreen()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"处理键盘事件失败: {e}")
            return False

    def toggle_fullscreen(self):
        """切换全屏模式"""
        try:
            if self.main_window.isFullScreen():
                self.exit_fullscreen()
            else:
                self.enter_fullscreen()
        except Exception as e:
            logger.error(f"切换全屏模式失败: {e}")

    def enter_fullscreen(self):
        """进入全屏模式"""
        try:
            if not self.main_window.isFullScreen():
                # 保存当前窗口几何信息
                self.previous_geometry = self.main_window.geometry()
                self.main_window.showFullScreen()
                self.is_fullscreen = True
                self.fullscreen_toggled.emit(True)
                logger.info("进入全屏模式")
        except Exception as e:
            logger.error(f"进入全屏模式失败: {e}")

    def exit_fullscreen(self):
        """退出全屏模式"""
        try:
            if self.main_window.isFullScreen():
                self.main_window.showMaximized()
                # 恢复之前的窗口几何信息
                if self.previous_geometry:
                    self.main_window.setGeometry(self.previous_geometry)
                self.is_fullscreen = False
                self.fullscreen_toggled.emit(False)
                logger.info("退出全屏模式")
        except Exception as e:
            logger.error(f"退出全屏模式失败: {e}")

    def handle_close_event(self, event):
        """
        处理窗口关闭事件
        
        Args:
            event: 关闭事件
            
        Returns:
            bool: 是否允许关闭
        """
        try:
            # 发送窗口关闭信号
            self.window_closing.emit()
            
            # 保存窗口设置
            self.save_window_settings()
            
            # 清理资源
            self.cleanup_resources()
            
            logger.info("窗口关闭事件处理完成")
            return True
            
        except Exception as e:
            logger.error(f"处理窗口关闭事件失败: {e}")
            return True  # 即使出错也允许关闭

    def save_window_settings(self):
        """保存窗口设置"""
        try:
            # 保存窗口几何信息
            geometry = self.main_window.geometry()
            self.config_manager.set('window.geometry.x', geometry.x())
            self.config_manager.set('window.geometry.y', geometry.y())
            self.config_manager.set('window.geometry.width', geometry.width())
            self.config_manager.set('window.geometry.height', geometry.height())
            
            # 保存窗口状态
            self.config_manager.set('window.is_maximized', self.main_window.isMaximized())
            self.config_manager.set('window.is_fullscreen', self.main_window.isFullScreen())
            
            logger.debug("窗口设置已保存")
            
        except Exception as e:
            logger.error(f"保存窗口设置失败: {e}")

    def load_window_settings(self):
        """加载窗口设置"""
        try:
            # 加载窗口几何信息
            x = self.config_manager.get('window.geometry.x', 100)
            y = self.config_manager.get('window.geometry.y', 100)
            width = self.config_manager.get('window.geometry.width', 1920)
            height = self.config_manager.get('window.geometry.height', 1080)
            
            self.main_window.setGeometry(x, y, width, height)
            
            # 加载窗口状态
            is_maximized = self.config_manager.get('window.is_maximized', True)
            if is_maximized:
                self.main_window.showMaximized()
            
            logger.debug("窗口设置已加载")
            
        except Exception as e:
            logger.error(f"加载窗口设置失败: {e}")

    def cleanup_resources(self):
        """清理资源"""
        try:
            # 停止窗口监控定时器
            if self.window_monitor_timer and self.window_monitor_timer.isActive():
                self.window_monitor_timer.stop()
                
            logger.debug("窗口管理器资源已清理")
            
        except Exception as e:
            logger.error(f"清理窗口管理器资源失败: {e}")

    def set_window_title(self, title: str):
        """设置窗口标题"""
        try:
            self.main_window.setWindowTitle(title)
        except Exception as e:
            logger.error(f"设置窗口标题失败: {e}")

    def get_window_info(self) -> dict:
        """获取窗口信息"""
        try:
            geometry = self.main_window.geometry()
            return {
                'title': self.main_window.windowTitle(),
                'geometry': {
                    'x': geometry.x(),
                    'y': geometry.y(),
                    'width': geometry.width(),
                    'height': geometry.height()
                },
                'is_maximized': self.main_window.isMaximized(),
                'is_fullscreen': self.main_window.isFullScreen(),
                'is_minimized': self.main_window.isMinimized(),
                'is_hidden': self.main_window.isHidden(),
                'is_visible': self.main_window.isVisible()
            }
        except Exception as e:
            logger.error(f"获取窗口信息失败: {e}")
            return {}

    def center_window(self):
        """将窗口居中显示"""
        try:
            # 获取屏幕几何信息
            screen = self.main_window.screen()
            if screen:
                screen_geometry = screen.geometry()
                window_geometry = self.main_window.geometry()
                
                # 计算居中位置
                x = (screen_geometry.width() - window_geometry.width()) // 2
                y = (screen_geometry.height() - window_geometry.height()) // 2
                
                self.main_window.move(x, y)
                logger.debug("窗口已居中显示")
        except Exception as e:
            logger.error(f"居中窗口失败: {e}")

    def minimize_window(self):
        """最小化窗口"""
        try:
            self.main_window.showMinimized()
            self.window_status_changed.emit("minimized")
        except Exception as e:
            logger.error(f"最小化窗口失败: {e}")

    def maximize_window(self):
        """最大化窗口"""
        try:
            self.main_window.showMaximized()
            self.window_status_changed.emit("maximized")
        except Exception as e:
            logger.error(f"最大化窗口失败: {e}")

    def restore_window(self):
        """恢复窗口"""
        try:
            self.main_window.showNormal()
            self.window_status_changed.emit("normal")
        except Exception as e:
            logger.error(f"恢复窗口失败: {e}")

    def is_window_visible(self) -> bool:
        """检查窗口是否可见"""
        return self.main_window.isVisible() and not self.main_window.isMinimized()

    def bring_to_front(self):
        """将窗口置于前台"""
        try:
            self.main_window.raise_()
            self.main_window.activateWindow()
        except Exception as e:
            logger.error(f"将窗口置于前台失败: {e}")
