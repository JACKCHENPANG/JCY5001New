# -*- coding: utf-8 -*-
"""
窗口布局管理器
从MainWindow中提取的窗口布局相关功能

职责：
- 窗口属性设置
- 主布局创建
- 比例布局管理
- 样式应用

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Dict, Any
from PyQt5.QtCore import QObject, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QSizePolicy

logger = logging.getLogger(__name__)


class WindowLayoutManager(QObject):
    """
    窗口布局管理器
    
    职责：
    - 窗口基本属性设置
    - 主布局创建和管理
    - 比例布局控制
    - 样式应用
    """
    
    def __init__(self, main_window, config_manager):
        """
        初始化窗口布局管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
        """
        super().__init__()
        
        self.main_window = main_window
        self.config_manager = config_manager
        
        logger.debug("窗口布局管理器初始化完成")
    
    def setup_window_properties(self):
        """设置窗口基本属性"""
        try:
            # 设置窗口标题，包含版本号
            app_name = self.config_manager.get('app.name', 'JCY5001AS鲸测云8路EIS阻抗筛选仪')
            app_version = self.config_manager.get('app.version', 'V0.92.40')
            title = f"{app_name} {app_version}"
            self.main_window.setWindowTitle(title)
            
            # 设置窗口大小
            width = self.config_manager.get('ui.window.width', 1920)
            height = self.config_manager.get('ui.window.height', 1080)
            self.main_window.resize(width, height)
            
            # 设置最小尺寸
            min_width = self.config_manager.get('ui.window.min_width', 1200)
            min_height = self.config_manager.get('ui.window.min_height', 800)
            self.main_window.setMinimumSize(min_width, min_height)
            
            logger.info(f"窗口属性设置完成: {width}x{height}")
            
        except Exception as e:
            logger.error(f"设置窗口属性失败: {e}")
    
    def create_main_layout(self) -> QVBoxLayout:
        """
        创建主布局
        
        Returns:
            主布局对象
        """
        try:
            # 创建中央窗口部件
            central_widget = QWidget()
            self.main_window.setCentralWidget(central_widget)
            
            # 创建主布局
            main_layout = QVBoxLayout(central_widget)
            main_layout.setContentsMargins(5, 5, 5, 5)
            main_layout.setSpacing(5)
            
            logger.info("主布局创建完成")
            return main_layout
            
        except Exception as e:
            logger.error(f"创建主布局失败: {e}")
            raise
    
    def create_proportional_layout(self, main_layout) -> Dict[str, QWidget]:
        """
        创建精确比例布局容器 - 工业设计风格优化

        按照工业设计+苹果设计语言优化布局比例：
        - 标题区域：5%
        - 统计区域：25% (增加显示空间，确保Rs-Rct明细数据完整显示)
        - 第一行通道卡片：37.5%
        - 第二行通道卡片：32.5%

        Args:
            main_layout: 主布局

        Returns:
            布局容器字典
        """
        try:
            # 创建垂直分割器
            main_splitter = QSplitter()
            main_splitter.setOrientation(Qt.Vertical)  # 垂直方向
            main_splitter.setChildrenCollapsible(False)  # 防止区域被折叠
            main_layout.addWidget(main_splitter)

            # 创建各个区域容器
            containers = {}

            # 1. 顶部标题栏容器 (5% - 约54px @ 1080p)
            containers['header'] = QWidget()
            containers['header'].setFixedHeight(54)  # 精确高度控制
            containers['header'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            main_splitter.addWidget(containers['header'])

            # 2. 上层区域容器 (18.75% - 约203px @ 1080p，缩短至75%)
            containers['upper'] = QWidget()
            containers['upper'].setFixedHeight(203)  # 缩短至75%：270 * 0.75 = 203px
            containers['upper'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            main_splitter.addWidget(containers['upper'])

            # 3. 通道区域容器 (70% - 剩余空间)
            channels_widget = QWidget()
            channels_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            main_splitter.addWidget(channels_widget)

            # 创建通道区域的垂直布局
            channels_layout = QVBoxLayout(channels_widget)
            channels_layout.setContentsMargins(8, 8, 8, 8)  # 增加边距，提升视觉层次
            channels_layout.setSpacing(12)  # 增加间距，符合苹果设计语言

            # 通道第一行容器 (50% of remaining space - 均分高度)
            containers['channels_row1'] = QWidget()
            containers['channels_row1'].setMinimumHeight(320)  # 增加高度以适应新布局
            containers['channels_row1'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            channels_layout.addWidget(containers['channels_row1'], 50)  # 权重50 (均分)

            # 通道第二行容器 (50% of remaining space - 均分高度)
            containers['channels_row2'] = QWidget()
            containers['channels_row2'].setMinimumHeight(320)  # 增加高度以适应新布局
            containers['channels_row2'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            channels_layout.addWidget(containers['channels_row2'], 50)  # 权重50 (均分)

            # 设置精确比例 (基于1080p高度，优化后)
            # 标题54px + 统计203px + 通道823px = 1080px
            main_splitter.setSizes([54, 203, 823])

            logger.info("工业设计风格比例布局容器创建完成")
            return containers

        except Exception as e:
            logger.error(f"创建比例布局失败: {e}")
            return {}
    
    def create_upper_layout(self, upper_container) -> QHBoxLayout:
        """
        创建上层区域布局
        
        Args:
            upper_container: 上层容器
            
        Returns:
            上层布局对象
        """
        try:
            upper_layout = QHBoxLayout(upper_container)
            upper_layout.setContentsMargins(5, 5, 5, 5)
            upper_layout.setSpacing(10)
            
            logger.info("上层区域布局创建完成")
            return upper_layout
            
        except Exception as e:
            logger.error(f"创建上层区域布局失败: {e}")
            raise

    def setup_upper_widget_proportions(self, upper_layout, batch_widget, statistics_widget, control_widget):
        """
        设置上层区域组件比例

        Args:
            upper_layout: 上层布局
            batch_widget: 批次信息组件
            statistics_widget: 统计组件
            control_widget: 控制组件
        """
        try:
            # 设置拉伸因子：批次信息(2) : 统计(3) : 控制(2)
            upper_layout.setStretchFactor(batch_widget, 2)
            upper_layout.setStretchFactor(statistics_widget, 3)
            upper_layout.setStretchFactor(control_widget, 2)

            logger.info("上层组件比例设置完成")

        except Exception as e:
            logger.error(f"设置上层组件比例失败: {e}")

    def apply_styles(self):
        """应用窗口样式"""
        try:
            # 获取样式配置
            style_enabled = self.config_manager.get('ui.style.enabled', True)

            if not style_enabled:
                logger.info("样式应用已禁用")
                return

            # 应用基础样式
            self._apply_base_styles()

            # 应用主题样式
            theme = self.config_manager.get('ui.style.theme', 'default')
            self._apply_theme_styles(theme)

            logger.info(f"窗口样式应用完成: {theme}")

        except Exception as e:
            logger.error(f"应用窗口样式失败: {e}")

    def _apply_base_styles(self):
        """应用工业设计风格基础样式"""
        try:
            base_style = """
            /* 工业设计风格主窗口 - 白色背景优化 */
            QMainWindow {
                background-color: #ffffff;  /* 纯白色背景，提升视觉舒适度 */
                font-family: "Microsoft YaHei UI", "Segoe UI", Arial, sans-serif;  /* 更现代的字体栈 */
                font-size: 9pt;
                color: #1f2937;  /* 深色文字，确保在白色背景上的对比度 */
            }

            QWidget {
                background-color: #ffffff;
                font-family: "Microsoft YaHei UI", "Segoe UI", Arial, sans-serif;
            }

            /* 工业设计风格分割器 */
            QSplitter::handle {
                background-color: #e5e7eb;  /* 更浅的分割线 */
                border: none;  /* 移除边框，更简洁 */
            }

            QSplitter::handle:horizontal {
                width: 2px;  /* 更细的分割线 */
            }

            QSplitter::handle:vertical {
                height: 2px;  /* 更细的分割线 */
            }

            QSplitter::handle:hover {
                background-color: #d1d5db;  /* 悬停时稍微深一点 */
            }
            """

            self.main_window.setStyleSheet(base_style)

        except Exception as e:
            logger.error(f"应用基础样式失败: {e}")

    def _apply_theme_styles(self, theme: str):
        """
        应用主题样式

        Args:
            theme: 主题名称
        """
        try:
            if theme == 'dark':
                self._apply_dark_theme()
            elif theme == 'light':
                self._apply_light_theme()
            else:
                # 默认主题
                pass

        except Exception as e:
            logger.error(f"应用主题样式失败: {e}")

    def _apply_dark_theme(self):
        """应用深色主题"""
        dark_style = """
        QMainWindow {
            background-color: #1a2b3c;
            color: #ffffff;
        }
        """
        current_style = self.main_window.styleSheet()
        self.main_window.setStyleSheet(current_style + dark_style)

    def _apply_light_theme(self):
        """应用浅色主题"""
        light_style = """
        QMainWindow {
            background-color: #ffffff;
            color: #000000;
        }
        """
        current_style = self.main_window.styleSheet()
        self.main_window.setStyleSheet(current_style + light_style)

    def get_layout_info(self) -> Dict[str, Any]:
        """
        获取布局信息

        Returns:
            布局信息字典
        """
        try:
            return {
                'window_size': {
                    'width': self.main_window.width(),
                    'height': self.main_window.height()
                },
                'window_position': {
                    'x': self.main_window.x(),
                    'y': self.main_window.y()
                },
                'is_maximized': self.main_window.isMaximized(),
                'is_fullscreen': self.main_window.isFullScreen()
            }

        except Exception as e:
            logger.error(f"获取布局信息失败: {e}")
            return {}

    def save_window_settings(self):
        """保存窗口设置"""
        try:
            # 获取当前窗口状态
            layout_info = self.get_layout_info()
            
            # 保存到配置管理器
            if not layout_info.get('is_maximized', False):
                # 只在非最大化状态下保存尺寸和位置
                self.config_manager.set('ui.window.width', layout_info['window_size']['width'])
                self.config_manager.set('ui.window.height', layout_info['window_size']['height'])
                self.config_manager.set('ui.window.x', layout_info['window_position']['x'])
                self.config_manager.set('ui.window.y', layout_info['window_position']['y'])
            
            self.config_manager.set('ui.window.maximized', layout_info['is_maximized'])
            self.config_manager.set('ui.window.fullscreen', layout_info['is_fullscreen'])
            
            logger.info("窗口设置已保存")
            
        except Exception as e:
            logger.error(f"保存窗口设置失败: {e}")

    def cleanup_timers(self):
        """清理定时器（兼容性方法）"""
        try:
            # 这个方法主要用于兼容性，窗口布局管理器本身不管理定时器
            # 如果将来需要管理定时器，可以在这里添加相关逻辑
            logger.debug("窗口布局管理器定时器清理完成")
            
        except Exception as e:
            logger.error(f"清理定时器失败: {e}")
