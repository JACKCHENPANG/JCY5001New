# -*- coding: utf-8 -*-
"""
用户登录对话框
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMessageBox, QButtonGroup, QRadioButton
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from ui.widgets.safe_line_edit import SafePasswordLineEdit
import logging

logger = logging.getLogger(__name__)

class UserLoginDialog(QDialog):
    """用户登录对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_role = "operator"
        self._init_ui()
    
    def _init_ui(self):
        """初始化界面"""
        self.setWindowTitle("用户登录")
        self.setModal(True)
        self.setFixedSize(400, 250)  # 增大界面尺寸，确保密码输入框完整显示
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("请选择用户角色")
        title_label.setFont(QFont("", 12, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 角色选择
        role_layout = QVBoxLayout()
        self.role_group = QButtonGroup()
        
        self.operator_radio = QRadioButton("操作员")
        self.operator_radio.setChecked(True)
        self.operator_radio.toggled.connect(lambda: self._on_role_changed("operator"))
        
        self.admin_radio = QRadioButton("管理员")
        self.admin_radio.toggled.connect(lambda: self._on_role_changed("admin"))
        
        self.role_group.addButton(self.operator_radio)
        self.role_group.addButton(self.admin_radio)
        
        role_layout.addWidget(self.operator_radio)
        role_layout.addWidget(self.admin_radio)
        layout.addLayout(role_layout)
        
        # 密码输入（仅管理员需要）
        self.password_layout = QHBoxLayout()
        self.password_label = QLabel("密码:")
        self.password_edit = SafePasswordLineEdit()
        self.password_edit.setPlaceholderText("请输入管理员密码")
        
        self.password_layout.addWidget(self.password_label)
        self.password_layout.addWidget(self.password_edit)
        layout.addLayout(self.password_layout)
        
        # 初始隐藏密码输入
        self.password_label.setVisible(False)
        self.password_edit.setVisible(False)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.login_button = QPushButton("登录")
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self._on_login)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        # 样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333;
            }
            QRadioButton {
                font-size: 11pt;
                padding: 5px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
    
    def _on_role_changed(self, role):
        """角色变更处理"""
        self.selected_role = role
        
        # 管理员需要密码，操作员不需要
        is_admin = (role == "admin")
        self.password_label.setVisible(is_admin)
        self.password_edit.setVisible(is_admin)
        
        if is_admin:
            self.password_edit.setFocus()
        else:
            self.password_edit.clear()
    
    def _on_login(self):
        """登录处理"""
        if self.selected_role == "admin":
            password = self.password_edit.text()
            if not password:
                QMessageBox.warning(self, "警告", "请输入管理员密码")
                return
            
            # 验证密码
            if password != "JCY5001-ADMIN":  # 修改管理员密码为JCY5001-ADMIN
                QMessageBox.warning(self, "错误", "管理员密码错误")
                return
        
        self.accept()
    
    def get_selected_role(self):
        """获取选择的角色"""
        return self.selected_role
    
    def get_password(self):
        """获取输入的密码"""
        return self.password_edit.text()
