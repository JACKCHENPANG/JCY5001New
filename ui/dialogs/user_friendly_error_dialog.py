# -*- coding: utf-8 -*-
"""
用户友好错误提示对话框
美观的错误显示界面，提供清晰的错误信息和解决建议

Author: Jack
Date: 2025-01-09
"""

import logging
from typing import Dict, List, Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QFrame, QScrollArea, QWidget, QApplication,
    QCheckBox, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QPalette, QIcon

from utils.user_friendly_error_manager import get_error_manager, ErrorSeverityLevel
from backend.exceptions import ErrorCode

logger = logging.getLogger(__name__)


class UserFriendlyErrorDialog(QDialog):
    """用户友好错误提示对话框"""
    
    # 信号定义
    retry_requested = pyqtSignal()  # 重试请求信号
    details_requested = pyqtSignal()  # 详情请求信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.error_manager = get_error_manager()
        self.auto_close_timer = None
        self.show_technical_details = False
        
        self._init_ui()
        self._setup_styles()
        
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("系统提示")
        self.setModal(True)
        self.setMinimumSize(450, 300)
        self.setMaximumSize(600, 500)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题区域
        self._create_title_area(main_layout)
        
        # 消息区域
        self._create_message_area(main_layout)
        
        # 解决建议区域
        self._create_suggestions_area(main_layout)
        
        # 技术详情区域（默认隐藏）
        self._create_technical_details_area(main_layout)
        
        # 按钮区域
        self._create_button_area(main_layout)
        
    def _create_title_area(self, parent_layout):
        """创建标题区域"""
        title_frame = QFrame()
        title_frame.setObjectName("titleFrame")
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # 图标标签
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(32, 32)
        self.icon_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(self.icon_label)
        
        # 标题标签
        self.title_label = QLabel()
        self.title_label.setObjectName("titleLabel")
        title_layout.addWidget(self.title_label)
        
        title_layout.addStretch()
        parent_layout.addWidget(title_frame)
        
    def _create_message_area(self, parent_layout):
        """创建消息区域"""
        self.message_label = QLabel()
        self.message_label.setObjectName("messageLabel")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignTop)
        parent_layout.addWidget(self.message_label)
        
    def _create_suggestions_area(self, parent_layout):
        """创建解决建议区域"""
        suggestions_frame = QFrame()
        suggestions_frame.setObjectName("suggestionsFrame")
        suggestions_layout = QVBoxLayout(suggestions_frame)
        suggestions_layout.setContentsMargins(10, 10, 10, 10)
        
        # 建议标题
        suggestions_title = QLabel("💡 解决建议：")
        suggestions_title.setObjectName("suggestionsTitle")
        suggestions_layout.addWidget(suggestions_title)
        
        # 建议内容滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(120)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarNever)
        
        self.suggestions_widget = QWidget()
        self.suggestions_layout = QVBoxLayout(self.suggestions_widget)
        self.suggestions_layout.setContentsMargins(5, 5, 5, 5)
        
        scroll_area.setWidget(self.suggestions_widget)
        suggestions_layout.addWidget(scroll_area)
        
        parent_layout.addWidget(suggestions_frame)
        
    def _create_technical_details_area(self, parent_layout):
        """创建技术详情区域"""
        self.details_frame = QFrame()
        self.details_frame.setObjectName("detailsFrame")
        self.details_frame.setVisible(False)
        
        details_layout = QVBoxLayout(self.details_frame)
        details_layout.setContentsMargins(10, 10, 10, 10)
        
        # 详情标题
        details_title = QLabel("🔧 技术详情：")
        details_title.setObjectName("detailsTitle")
        details_layout.addWidget(details_title)
        
        # 详情内容
        self.details_text = QTextEdit()
        self.details_text.setObjectName("detailsText")
        self.details_text.setMaximumHeight(100)
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        
        parent_layout.addWidget(self.details_frame)
        
    def _create_button_area(self, parent_layout):
        """创建按钮区域"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 显示详情复选框
        self.show_details_checkbox = QCheckBox("显示技术详情")
        self.show_details_checkbox.stateChanged.connect(self._toggle_technical_details)
        button_layout.addWidget(self.show_details_checkbox)
        
        button_layout.addStretch()
        
        # 重试按钮
        self.retry_button = QPushButton("🔄 重试")
        self.retry_button.setObjectName("retryButton")
        self.retry_button.clicked.connect(self._on_retry_clicked)
        self.retry_button.setVisible(False)
        button_layout.addWidget(self.retry_button)
        
        # 确定按钮
        self.ok_button = QPushButton("确定")
        self.ok_button.setObjectName("okButton")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)
        
        parent_layout.addLayout(button_layout)
        
    def _setup_styles(self):
        """设置样式"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                border-radius: 8px;
            }
            
            #titleFrame {
                background-color: white;
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 5px;
            }
            
            #titleLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                margin-left: 10px;
            }
            
            #messageLabel {
                font-size: 14px;
                color: #555;
                line-height: 1.4;
                padding: 10px;
                background-color: white;
                border-radius: 6px;
                border-left: 4px solid #2196F3;
            }
            
            #suggestionsFrame {
                background-color: white;
                border-radius: 6px;
                border-left: 4px solid #4CAF50;
            }
            
            #suggestionsTitle {
                font-size: 13px;
                font-weight: bold;
                color: #4CAF50;
                margin-bottom: 5px;
            }
            
            #detailsFrame {
                background-color: white;
                border-radius: 6px;
                border-left: 4px solid #FF9800;
            }
            
            #detailsTitle {
                font-size: 13px;
                font-weight: bold;
                color: #FF9800;
                margin-bottom: 5px;
            }
            
            #detailsText {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            
            #okButton {
                background-color: #2196F3;
                color: white;
                border: none;
            }
            
            #okButton:hover {
                background-color: #1976D2;
            }
            
            #retryButton {
                background-color: #4CAF50;
                color: white;
                border: none;
            }
            
            #retryButton:hover {
                background-color: #388E3C;
            }
            
            QCheckBox {
                font-size: 12px;
                color: #666;
            }
            
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
    def show_error(self, error_code: ErrorCode, technical_detail: str = "", 
                   show_retry: bool = False, auto_close_seconds: int = 0):
        """
        显示错误信息
        
        Args:
            error_code: 错误码
            technical_detail: 技术详情
            show_retry: 是否显示重试按钮
            auto_close_seconds: 自动关闭秒数（0表示不自动关闭）
        """
        try:
            # 获取格式化的错误信息
            error_info = self.error_manager.format_error_display(error_code, technical_detail)
            
            # 设置标题和图标
            self.title_label.setText(error_info['title'])
            self.icon_label.setText(error_info['icon'])
            
            # 设置消息
            self.message_label.setText(error_info['message'])
            
            # 根据严重程度调整消息样式
            severity_colors = {
                'info': '#2196F3',
                'warning': '#FF9800', 
                'error': '#F44336',
                'critical': '#9C27B0'
            }
            
            color = severity_colors.get(error_info['severity'], '#2196F3')
            self.message_label.setStyleSheet(f"""
                #messageLabel {{
                    font-size: 14px;
                    color: #555;
                    line-height: 1.4;
                    padding: 10px;
                    background-color: white;
                    border-radius: 6px;
                    border-left: 4px solid {color};
                }}
            """)
            
            # 设置解决建议
            self._set_suggestions(error_info['suggestions'])
            
            # 设置技术详情
            if error_info['technical_detail']:
                self.details_text.setPlainText(error_info['technical_detail'])
                self.show_details_checkbox.setVisible(True)
            else:
                self.show_details_checkbox.setVisible(False)
                
            # 设置重试按钮
            self.retry_button.setVisible(show_retry)
            
            # 设置自动关闭
            if auto_close_seconds > 0:
                self._setup_auto_close(auto_close_seconds)
            
            # 调整窗口大小
            self.adjustSize()
            
            # 居中显示
            self._center_on_parent()
            
            logger.info(f"显示用户友好错误对话框: {error_info['title']} - {error_info['message']}")
            
        except Exception as e:
            logger.error(f"显示错误对话框失败: {e}")
            # 显示简单的错误信息
            self.title_label.setText("❌ 错误")
            self.message_label.setText("系统遇到了问题，请联系技术支持")
            
    def _set_suggestions(self, suggestions: List[str]):
        """设置解决建议"""
        try:
            # 清除现有建议
            for i in reversed(range(self.suggestions_layout.count())):
                child = self.suggestions_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            # 添加新建议
            for suggestion in suggestions:
                suggestion_label = QLabel(suggestion)
                suggestion_label.setWordWrap(True)
                suggestion_label.setStyleSheet("""
                    QLabel {
                        font-size: 12px;
                        color: #666;
                        padding: 3px 0px;
                        margin-left: 10px;
                    }
                """)
                self.suggestions_layout.addWidget(suggestion_label)
                
        except Exception as e:
            logger.error(f"设置解决建议失败: {e}")
            
    def _toggle_technical_details(self, state):
        """切换技术详情显示"""
        try:
            show_details = state == Qt.Checked
            self.details_frame.setVisible(show_details)
            self.adjustSize()
            
        except Exception as e:
            logger.error(f"切换技术详情显示失败: {e}")
            
    def _on_retry_clicked(self):
        """重试按钮点击事件"""
        try:
            self.retry_requested.emit()
            self.accept()
            
        except Exception as e:
            logger.error(f"重试按钮点击处理失败: {e}")
            
    def _setup_auto_close(self, seconds: int):
        """设置自动关闭"""
        try:
            if self.auto_close_timer:
                self.auto_close_timer.stop()
                
            self.auto_close_timer = QTimer()
            self.auto_close_timer.timeout.connect(self.accept)
            self.auto_close_timer.start(seconds * 1000)
            
            # 更新按钮文本显示倒计时
            self.ok_button.setText(f"确定 ({seconds})")
            
            def update_countdown():
                remaining = self.auto_close_timer.remainingTime() // 1000
                if remaining > 0:
                    self.ok_button.setText(f"确定 ({remaining})")
                else:
                    self.ok_button.setText("确定")
                    
            countdown_timer = QTimer()
            countdown_timer.timeout.connect(update_countdown)
            countdown_timer.start(1000)
            
        except Exception as e:
            logger.error(f"设置自动关闭失败: {e}")
            
    def _center_on_parent(self):
        """在父窗口中居中显示"""
        try:
            if self.parent():
                parent_geometry = self.parent().geometry()
                x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
                y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
                self.move(x, y)
            else:
                # 在屏幕中央显示
                screen = QApplication.desktop().screenGeometry()
                x = (screen.width() - self.width()) // 2
                y = (screen.height() - self.height()) // 2
                self.move(x, y)
                
        except Exception as e:
            logger.error(f"居中显示失败: {e}")


def show_user_friendly_error(error_code: ErrorCode, technical_detail: str = "",
                           show_retry: bool = False, auto_close_seconds: int = 0,
                           parent=None) -> UserFriendlyErrorDialog:
    """
    显示用户友好错误对话框的便捷函数
    
    Args:
        error_code: 错误码
        technical_detail: 技术详情
        show_retry: 是否显示重试按钮
        auto_close_seconds: 自动关闭秒数
        parent: 父窗口
        
    Returns:
        错误对话框实例
    """
    try:
        dialog = UserFriendlyErrorDialog(parent)
        dialog.show_error(error_code, technical_detail, show_retry, auto_close_seconds)
        return dialog
        
    except Exception as e:
        logger.error(f"显示用户友好错误对话框失败: {e}")
        # 降级到简单消息框
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(parent, "错误", "系统遇到了问题，请联系技术支持")
        return None
