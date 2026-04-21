# -*- coding: utf-8 -*-
"""
简化版主窗口类（用于测试基础框架）
仅包含已实现的组件

Author: Jack
Date: 2025-01-27
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QAction, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
import logging

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager
from ui.components.header_widget import HeaderWidget
from ui.base.window_base import WindowBase


class SimpleMainWindow(WindowBase):
    """简化版主窗口类（用于测试）"""
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        初始化主窗口

        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        # 调用基础类初始化（自动处理窗口属性、图标、样式）
        super().__init__(config_manager, parent)

        # 初始化简化版特有的界面
        self._init_simple_ui()
        self._init_menu()

        # 加载窗口设置（基础类已提供）
        self.load_window_settings()

        logger.debug("简化版主窗口初始化完成")
    
    def _init_simple_ui(self):
        """初始化简化版特有的用户界面"""
        # 基础窗口属性已由基础类处理，这里只处理简化版特有的内容

        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 创建顶部标题栏
        self.header_widget = HeaderWidget(self.config_manager)
        main_layout.addWidget(self.header_widget)

        # 创建占位区域
        placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(placeholder_widget)

        # 上层占位
        upper_placeholder = QLabel("上层区域占位\n（批次信息、统计、测试控制）")
        upper_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        upper_placeholder.setStyleSheet("""
            QLabel {
                background-color: #ecf0f1;
                border: 2px dashed #bdc3c7;
                border-radius: 8px;
                color: #7f8c8d;
                font-size: 14pt;
                padding: 20px;
            }
        """)
        upper_placeholder.setMinimumHeight(200)

        # 下层占位
        lower_placeholder = QLabel("下层区域占位\n（8通道显示）")
        lower_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lower_placeholder.setStyleSheet("""
            QLabel {
                background-color: #ecf0f1;
                border: 2px dashed #bdc3c7;
                border-radius: 8px;
                color: #7f8c8d;
                font-size: 14pt;
                padding: 20px;
            }
        """)
        lower_placeholder.setMinimumHeight(400)

        placeholder_layout.addWidget(upper_placeholder)
        placeholder_layout.addWidget(lower_placeholder)
        placeholder_layout.setStretchFactor(upper_placeholder, 1)
        placeholder_layout.setStretchFactor(lower_placeholder, 2)

        main_layout.addWidget(placeholder_widget)
    
    def _init_menu(self):
        """初始化菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件(&F)')
        
        # 退出
        exit_action = QAction('退出(&X)', self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.setStatusTip('退出应用程序')
        exit_action.triggered.connect(self._on_exit)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助(&H)')
        
        # 关于
        about_action = QAction('关于(&A)', self)
        about_action.setStatusTip('关于本软件')
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _on_exit(self):
        """退出应用程序"""
        self.close()
    
    def _on_about(self):
        """关于对话框"""
        about_text = f"""
        <h3>{self.config_manager.get('app.name')}</h3>
        <p>版本: {self.config_manager.get('app.version')}</p>
        <p>专业的电池阻抗测试解决方案</p>
        <p>Copyright © 2025 鲸测云</p>
        <br>
        <p><b>第1天基础框架测试版本</b></p>
        <p>✅ 项目结构初始化</p>
        <p>✅ 配置管理器</p>
        <p>✅ 主窗口框架</p>
        <p>✅ 样式系统</p>
        <p>✅ 顶部标题栏</p>
        """
        QMessageBox.about(self, '关于', about_text)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 调用基础类的关闭事件处理（自动保存窗口设置和配置）
        super().closeEvent(event)
