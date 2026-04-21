# -*- coding: utf-8 -*-
"""
厂家端授权管理对话框
包含解锁码生成工具和授权管理功能

Author: Jack
Date: 2025-01-30
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QTextEdit, QMessageBox, QComboBox,
    QSpinBox, QTabWidget, QWidget, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class LicenseManagerDialog(QDialog):
    """厂家端授权管理对话框"""
    
    # 信号定义
    license_status_changed = pyqtSignal()  # 授权状态变更信号
    
    def __init__(self, config_manager=None, parent=None):
        """
        初始化授权管理对话框
        
        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.license_manager = None
        self._init_license_manager()
        self._init_ui()
        
        logger.debug("厂家端授权管理对话框初始化完成")
    
    def _init_license_manager(self):
        """初始化授权管理器"""
        try:
            from utils.license_manager import LicenseManager
            self.license_manager = LicenseManager(self.config_manager)
        except Exception as e:
            logger.error(f"初始化授权管理器失败: {e}")
    
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("JCY5001AS - 厂家端授权管理工具")
        self.setFixedSize(900, 750)
        self.setModal(True)
        
        # 应用工业设计风格
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                color: #2c3e50;
            }
            QTabWidget::pane {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                background-color: white;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background-color: #ecf0f1;
                color: #2c3e50;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #3498db;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #5dade2;
                color: white;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 14pt;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit, QTextEdit {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 16px;
                font-size: 14pt;
                background-color: white;
                min-height: 35px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #3498db;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 14px 28px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12pt;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("厂家端授权管理工具")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 15px;")
        main_layout.addWidget(title_label)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # 解锁码生成选项卡
        self._create_unlock_generator_tab()
        
        # 授权状态选项卡
        self._create_license_status_tab()
        
        main_layout.addWidget(self.tab_widget)
        
        # 底部按钮
        self._create_buttons(main_layout)
    
    def _create_unlock_generator_tab(self):
        """创建解锁码生成选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 身份验证区域
        auth_group = QGroupBox("身份验证")
        auth_layout = QVBoxLayout(auth_group)
        
        password_layout = QHBoxLayout()
        password_label = QLabel("管理员密码:")
        password_label.setMinimumWidth(140)
        password_label.setStyleSheet("font-size: 13pt; font-weight: bold;")
        
        self.admin_password_input = QLineEdit()
        self.admin_password_input.setEchoMode(QLineEdit.Password)
        self.admin_password_input.setPlaceholderText("请输入管理员密码")
        
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.admin_password_input)
        auth_layout.addLayout(password_layout)
        
        layout.addWidget(auth_group)
        
        # 解锁码生成区域
        gen_group = QGroupBox("解锁码生成")
        gen_layout = QVBoxLayout(gen_group)
        
        # 客户硬件指纹
        fingerprint_layout = QVBoxLayout()
        fingerprint_label = QLabel("客户硬件指纹:")
        fingerprint_label.setStyleSheet("font-size: 13pt; font-weight: bold; margin-bottom: 8px;")
        
        self.customer_fingerprint_input = QTextEdit()
        self.customer_fingerprint_input.setMinimumHeight(140)
        self.customer_fingerprint_input.setMaximumHeight(160)
        self.customer_fingerprint_input.setPlaceholderText("请粘贴客户提供的硬件指纹...")
        self.customer_fingerprint_input.setStyleSheet("""
            QTextEdit {
                font-size: 13pt;
                line-height: 1.5;
                padding: 16px;
            }
        """)
        
        fingerprint_layout.addWidget(fingerprint_label)
        fingerprint_layout.addWidget(self.customer_fingerprint_input)
        gen_layout.addLayout(fingerprint_layout)
        
        # 解锁类型和天数设置
        type_layout = QHBoxLayout()
        
        type_label = QLabel("解锁类型:")
        type_label.setMinimumWidth(120)
        type_label.setStyleSheet("font-size: 13pt; font-weight: bold;")
        
        self.unlock_type_combo = QComboBox()
        self.unlock_type_combo.addItems(["完整解锁", "临时解锁"])
        self.unlock_type_combo.currentTextChanged.connect(self._on_unlock_type_changed)
        self.unlock_type_combo.setStyleSheet("font-size: 12pt; padding: 8px;")
        
        self.days_label = QLabel("天数:")
        self.days_label.setStyleSheet("font-size: 13pt; font-weight: bold;")
        self.days_spinbox = QSpinBox()
        self.days_spinbox.setRange(1, 365)
        self.days_spinbox.setValue(30)
        self.days_spinbox.setSuffix(" 天")
        self.days_spinbox.setStyleSheet("font-size: 12pt; padding: 8px;")
        
        # 初始隐藏天数设置
        self.days_label.setVisible(False)
        self.days_spinbox.setVisible(False)
        
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.unlock_type_combo)
        type_layout.addWidget(self.days_label)
        type_layout.addWidget(self.days_spinbox)
        type_layout.addStretch()
        
        gen_layout.addLayout(type_layout)
        
        # 生成按钮
        self.generate_button = QPushButton("生成解锁码")
        self.generate_button.clicked.connect(self._generate_unlock_code)
        self.generate_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                font-size: 12pt;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        gen_layout.addWidget(self.generate_button)
        
        layout.addWidget(gen_group)
        
        # 结果显示区域
        result_group = QGroupBox("生成的解锁码")
        result_layout = QVBoxLayout(result_group)
        
        self.result_display = QTextEdit()
        self.result_display.setMinimumHeight(140)
        self.result_display.setMaximumHeight(160)
        self.result_display.setReadOnly(True)
        self.result_display.setPlaceholderText("生成的解锁码将显示在这里...")
        self.result_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                font-family: 'Courier New', monospace;
                font-size: 15pt;
                font-weight: bold;
                line-height: 1.5;
                padding: 16px;
            }
        """)
        
        # 复制按钮
        copy_button = QPushButton("复制解锁码")
        copy_button.clicked.connect(self._copy_unlock_code)
        copy_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        
        result_layout.addWidget(self.result_display)
        result_layout.addWidget(copy_button)
        
        layout.addWidget(result_group)
        
        self.tab_widget.addTab(tab, "🔑 解锁码生成")
    
    def _create_license_status_tab(self):
        """创建授权状态选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 授权状态显示
        status_group = QGroupBox("授权状态信息")
        status_layout = QVBoxLayout(status_group)
        
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setPlaceholderText("授权状态信息将显示在这里...")
        self.status_display.setMinimumHeight(200)
        self.status_display.setStyleSheet("""
            QTextEdit {
                font-size: 12pt;
                line-height: 1.5;
                padding: 16px;
            }
        """)
        
        status_layout.addWidget(self.status_display)
        
        # 刷新按钮
        refresh_button = QPushButton("刷新状态")
        refresh_button.clicked.connect(self._refresh_license_status)
        status_layout.addWidget(refresh_button)
        
        layout.addWidget(status_group)
        
        self.tab_widget.addTab(tab, "📊 授权状态")
        
        # 初始加载状态
        self._refresh_license_status()
    
    def _create_buttons(self, main_layout):
        """创建底部按钮"""
        button_layout = QHBoxLayout()
        
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
    
    def _on_unlock_type_changed(self, unlock_type):
        """解锁类型变更处理"""
        is_temp = (unlock_type == "临时解锁")
        self.days_label.setVisible(is_temp)
        self.days_spinbox.setVisible(is_temp)
    
    def _generate_unlock_code(self):
        """生成解锁码"""
        try:
            # 验证管理员密码
            admin_password = self.admin_password_input.text().strip()
            if not admin_password:
                QMessageBox.warning(self, "输入错误", "请输入管理员密码")
                return
            
            if admin_password != "JCY5001-ADMIN":
                QMessageBox.warning(self, "验证失败", "管理员密码错误")
                return
            
            # 获取客户硬件指纹
            customer_fingerprint = self.customer_fingerprint_input.toPlainText().strip()
            if not customer_fingerprint:
                QMessageBox.warning(self, "输入错误", "请输入客户硬件指纹")
                return
            
            # 清理硬件指纹（移除空格、换行等）
            customer_fingerprint = ''.join(customer_fingerprint.split())
            
            # 获取解锁类型和天数
            unlock_type_text = self.unlock_type_combo.currentText()
            if unlock_type_text == "完整解锁":
                unlock_type = "full"
                extend_days = None
            else:
                unlock_type = "temp"
                extend_days = self.days_spinbox.value()
            
            # 生成解锁码
            if not self.license_manager:
                QMessageBox.critical(self, "错误", "授权管理器未初始化")
                return
            
            result = self.license_manager.generate_unlock_code(
                customer_fingerprint=customer_fingerprint,
                customer_id="CUSTOMER_001",
                unlock_type=unlock_type,
                extend_days=extend_days
            )
            
            if result.get('success', False):
                unlock_code = result.get('unlock_code', '')
                self.result_display.setText(unlock_code)
                
                QMessageBox.information(
                    self,
                    "生成成功",
                    f"解锁码生成成功！\n\n类型: {result.get('unlock_type', '')}\n"
                    f"{'天数: ' + str(extend_days) + ' 天' if extend_days else ''}"
                )
            else:
                error_msg = result.get('message', '生成失败')
                QMessageBox.warning(self, "生成失败", error_msg)
                
        except Exception as e:
            logger.error(f"生成解锁码失败: {e}")
            QMessageBox.critical(self, "错误", f"生成解锁码时发生错误：\n\n{e}")
    
    def _copy_unlock_code(self):
        """复制解锁码"""
        try:
            unlock_code = self.result_display.toPlainText().strip()
            if unlock_code:
                clipboard = QApplication.clipboard()
                clipboard.setText(unlock_code)
                QMessageBox.information(self, "复制成功", "解锁码已复制到剪贴板")
            else:
                QMessageBox.warning(self, "复制失败", "没有可复制的解锁码")
                
        except Exception as e:
            logger.error(f"复制解锁码失败: {e}")
            QMessageBox.warning(self, "复制失败", f"复制失败：{e}")
    
    def _refresh_license_status(self):
        """刷新授权状态"""
        try:
            if not self.license_manager:
                self.status_display.setText("授权管理器未初始化")
                return
            
            # 获取授权状态
            status = self.license_manager.check_license()
            
            # 格式化显示
            status_text = "=== 授权状态信息 ===\n\n"
            status_text += f"授权状态: {'已授权' if status.get('is_licensed', False) else '未授权'}\n"
            status_text += f"试用状态: {'试用中' if status.get('is_trial', False) else '非试用'}\n"
            status_text += f"是否过期: {'是' if status.get('is_expired', False) else '否'}\n"
            
            if status.get('is_trial', False):
                remaining_days = status.get('remaining_days', 0)
                status_text += f"剩余天数: {remaining_days} 天\n"
            
            status_text += f"授权类型: {status.get('license_type', '未知')}\n"
            
            # 获取硬件指纹
            fingerprint = self.license_manager.get_hardware_fingerprint()
            if fingerprint:
                status_text += f"\n=== 硬件指纹 ===\n{fingerprint}\n"
            
            self.status_display.setText(status_text)
            
        except Exception as e:
            logger.error(f"刷新授权状态失败: {e}")
            self.status_display.setText(f"刷新失败: {e}")
