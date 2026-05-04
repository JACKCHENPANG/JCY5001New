# -*- coding: utf-8 -*-
"""
窗口管理器
负责主窗口的基本设置、样式、布局等功能

从MainWindow中提取的窗口管理功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import os
import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import QTimer

logger = logging.getLogger(__name__)


class WindowManager:
    """
    窗口管理器
    
    职责：
    - 窗口基本属性设置
    - 窗口样式管理
    - 窗口布局管理
    - 窗口设置保存和加载
    """
    
    def __init__(self, main_window, config_manager):
        """
        初始化窗口管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
        """
        self.main_window = main_window
        self.config_manager = config_manager
        
        # 绘图事件禁用修复: 初始化绘图标志
        self.main_window._painting = False
        
        logger.debug("窗口管理器初始化完成")
    
    def setup_window_properties(self):
        """设置窗口基本属性"""
        try:
            # 设置窗口标题，包含版本号
            app_name = self.config_manager.get('app.name', 'JCY5001 八通道EIS综合测试仪')
            app_version = self.config_manager.get('app.version', 'V0.92.55')
            title = f"{app_name} {app_version}"
            self.main_window.setWindowTitle(title)
            
            # 设置最小尺寸
            self.main_window.setMinimumSize(1200, 800)
            
            # 设置窗口图标
            self._set_application_icon()
            
            logger.info(f"窗口属性设置完成: {title}")
            
        except Exception as e:
            logger.error(f"设置窗口属性失败: {e}")
    
    def _set_application_icon(self):
        """设置应用程序图标"""
        try:
            # 使用图标管理器设置窗口图标
            from utils.icon_manager import set_window_icon
            set_window_icon(self.main_window)
            
        except Exception as e:
            logger.error(f"设置应用图标失败: {e}")
    
    def create_main_layout(self):
        """创建主布局"""
        try:
            # 创建中央窗口部件
            central_widget = QWidget()
            self.main_window.setCentralWidget(central_widget)

            # 创建主布局 - 使用精确高度比例控制
            main_layout = QVBoxLayout(central_widget)
            main_layout.setContentsMargins(5, 5, 5, 5)
            main_layout.setSpacing(5)

            return main_layout

        except Exception as e:
            logger.error(f"创建主布局失败: {e}")
            return None
    
    def create_proportional_layout(self, main_layout):
        """
        创建精确比例布局

        Args:
            main_layout: 主布局

        Returns:
            各区域的容器字典
        """
        try:
            # 创建各区域容器
            containers = {}

            # 标题区域容器 (5%)
            header_container = QWidget()
            header_container.setFixedHeight(40)  # 固定高度，后续会动态调整
            main_layout.addWidget(header_container)
            containers['header'] = header_container

            # 上层区域容器 (25%) - 统计+批次+控制
            upper_container = QWidget()
            main_layout.addWidget(upper_container)
            containers['upper'] = upper_container

            # 第一行通道容器 (35%)
            channels_row1_container = QWidget()
            main_layout.addWidget(channels_row1_container)
            containers['channels_row1'] = channels_row1_container

            # 第二行通道容器 (35%)
            channels_row2_container = QWidget()
            main_layout.addWidget(channels_row2_container)
            containers['channels_row2'] = channels_row2_container

            # 设置布局拉伸因子实现精确比例 - 进一步压缩优化：上层区域从20%减少到15%，通道区域增加
            # 使用整数比例：5% + 15% + 40% + 40% = 100%
            main_layout.setStretchFactor(header_container, 5)      # 5%
            main_layout.setStretchFactor(upper_container, 15)      # 15% (从20%减少到15%，缩小到原来的75%)
            main_layout.setStretchFactor(channels_row1_container, 40)  # 40% (从35%增加到40%)
            main_layout.setStretchFactor(channels_row2_container, 40)  # 40% (从35%增加到40%，总计100%)

            return containers

        except Exception as e:
            logger.error(f"创建比例布局失败: {e}")
            return None

    def create_upper_layout(self, container):
        """
        为上层容器创建布局

        Args:
            container: 上层容器窗口部件

        Returns:
            上层区域布局
        """
        try:
            layout = QHBoxLayout(container)
            layout.setContentsMargins(3, 3, 3, 3)  # 进一步压缩优化：从5px减少到3px
            layout.setSpacing(6)                   # 进一步压缩优化：从10px减少到6px

            return layout

        except Exception as e:
            logger.error(f"创建上层布局失败: {e}")
            return None

    def create_upper_widget(self):
        """
        创建上层区域窗口部件
        
        Returns:
            上层区域窗口部件
        """
        try:
            upper_widget = QWidget()
            layout = QHBoxLayout(upper_widget)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(10)
            
            return upper_widget, layout
            
        except Exception as e:
            logger.error(f"创建上层区域失败: {e}")
            return None, None
    

    
    def setup_upper_widget_proportions(self, layout, batch_widget, statistics_widget, control_widget):
        """
        设置上层区域各组件比例
        
        Args:
            layout: 上层区域布局
            batch_widget: 批次信息组件
            statistics_widget: 统计组件
            control_widget: 控制组件
        """
        try:
            # 设置各区域的比例
            layout.setStretchFactor(batch_widget, 1)
            layout.setStretchFactor(statistics_widget, 2)
            layout.setStretchFactor(control_widget, 1)
            
        except Exception as e:
            logger.error(f"设置上层区域比例失败: {e}")
    
    def apply_styles(self):
        """应用样式表"""
        try:
            style_file = os.path.join("resources", "styles", "main_style.qss")
            if os.path.exists(style_file):
                with open(style_file, 'r', encoding='utf-8') as f:
                    self.main_window.setStyleSheet(f.read())
                logger.info("样式文件加载成功")
            else:
                logger.warning(f"样式文件不存在: {style_file}")
                
        except Exception as e:
            logger.warning(f"样式文件加载失败: {e}")
    
    def load_window_settings(self):
        """加载窗口设置"""
        try:
            # 加载窗口大小
            size = self.config_manager.get('ui.window_size', [1280, 800])
            self.main_window.resize(size[0], size[1])
            
            # 加载窗口位置
            pos = self.config_manager.get('ui.window_position', [100, 100])

            # 验证窗口位置是否在屏幕范围内
            from PyQt5.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                # 确保窗口至少有一部分在屏幕内
                if (pos[0] < -100 or pos[0] > screen_geometry.width() or
                    pos[1] < -100 or pos[1] > screen_geometry.height()):
                    pos = [100, 100]  # 重置到安全位置
                    logger.warning(f"窗口位置超出屏幕范围，重置到默认位置: {pos}")

            self.main_window.move(pos[0], pos[1])
            
            logger.info(f"窗口设置加载完成: 大小{size}, 位置{pos}")
            
        except Exception as e:
            logger.warning(f"窗口设置加载失败: {e}")
    
    def save_window_settings(self):
        """保存窗口设置"""
        try:
            # 保存窗口大小
            size = self.main_window.size()
            self.config_manager.set('ui.window_size', [size.width(), size.height()])
            
            # 保存窗口位置
            pos = self.main_window.pos()
            self.config_manager.set('ui.window_position', [pos.x(), pos.y()])
            
            logger.info(f"窗口设置已保存: 大小[{size.width()}, {size.height()}], 位置[{pos.x()}, {pos.y()}]")
            
        except Exception as e:
            logger.warning(f"窗口设置保存失败: {e}")
    
    def setup_paint_event_fix(self):
        """设置绘图事件修复"""
        try:
            # 重写绘图事件，防止递归绘图
            original_paint_event = self.main_window.paintEvent
            
            def fixed_paint_event(event):
                """修复后的绘图事件"""
                try:
                    # 检查是否正在绘制
                    if hasattr(self.main_window, '_painting') and self.main_window._painting:
                        return
                    
                    self.main_window._painting = True
                    try:
                        original_paint_event(event)
                    finally:
                        self.main_window._painting = False
                        
                except Exception as e:
                    logger.error(f"主窗口绘图事件异常: {e}")
                    if hasattr(self.main_window, '_painting'):
                        self.main_window._painting = False
            
            # 替换绘图事件
            self.main_window.paintEvent = fixed_paint_event
            
        except Exception as e:
            logger.error(f"设置绘图事件修复失败: {e}")
    
    def setup_timers(self):
        """设置定时器"""
        try:
            # 定时器线程修复: 确保在主线程中创建定时器
            from PyQt5.QtWidgets import QApplication
            
            # 检查是否在主线程中
            app = QApplication.instance()
            if app and app.thread() != self.main_window.thread():
                logger.warning("⚠️ 定时器不在主线程中创建，可能导致问题")
            
            # 界面更新定时器
            self.main_window.update_timer = QTimer(self.main_window)
            self.main_window.update_timer.timeout.connect(self._update_display)
            self.main_window.update_timer.start(100)  # 100ms更新一次
            
            # 配置保存定时器
            self.main_window.save_timer = QTimer(self.main_window)
            self.main_window.save_timer.timeout.connect(self._save_config)
            self.main_window.save_timer.setSingleShot(True)
            
            logger.info("定时器设置完成")
            
        except Exception as e:
            logger.error(f"设置定时器失败: {e}")
    
    def _update_display(self):
        """更新显示内容"""
        # 这里可以添加需要定期更新的内容
        pass
    
    def _save_config(self):
        """保存配置"""
        try:
            self.config_manager.save_config()
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def cleanup_timers(self):
        """清理定时器"""
        try:
            if hasattr(self.main_window, 'update_timer'):
                self.main_window.update_timer.stop()
            if hasattr(self.main_window, 'save_timer'):
                self.main_window.save_timer.stop()
            
            logger.info("定时器已清理")
            
        except Exception as e:
            logger.error(f"清理定时器失败: {e}")
    
    def get_window_info(self):
        """
        获取窗口信息
        
        Returns:
            窗口信息字典
        """
        try:
            size = self.main_window.size()
            pos = self.main_window.pos()
            
            return {
                'title': self.main_window.windowTitle(),
                'size': [size.width(), size.height()],
                'position': [pos.x(), pos.y()],
                'minimum_size': [self.main_window.minimumWidth(), self.main_window.minimumHeight()],
                'is_visible': self.main_window.isVisible(),
                'is_maximized': self.main_window.isMaximized()
            }
            
        except Exception as e:
            logger.error(f"获取窗口信息失败: {e}")
            return {}
