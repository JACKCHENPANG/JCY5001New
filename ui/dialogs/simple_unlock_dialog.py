# -*- coding: utf-8 -*-
"""
简化的解锁对话框
客户端使用的简洁解锁界面

Author: Jack
Date: 2025-01-30
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QTextEdit, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class SimpleUnlockDialog(QDialog):
    """简化的解锁对话框"""
    
    # 信号定义
    unlock_successful = pyqtSignal()  # 解锁成功信号
    
    def __init__(self, parent=None):
        """
        初始化简化解锁对话框
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.license_manager = None
        self._init_license_manager()
        self._init_ui()
        self._load_hardware_fingerprint()
        
        logger.debug("简化解锁对话框初始化完成")
    
    def _init_license_manager(self):
        """初始化授权管理器"""
        try:
            from utils.license_manager import LicenseManager
            self.license_manager = LicenseManager()
        except Exception as e:
            logger.error(f"初始化授权管理器失败: {e}")
    
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("软件解锁")
        self.setFixedSize(600, 550)
        self.setModal(True)
        
        # 应用工业设计风格
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                color: #2c3e50;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 11pt;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit, QTextEdit {
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                padding: 12px;
                font-size: 12pt;
                background-color: white;
                min-height: 25px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #3498db;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 10pt;
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
        title_label = QLabel("软件解锁")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # 硬件指纹显示区域
        self._create_fingerprint_section(main_layout)
        
        # 解锁码输入区域
        self._create_unlock_section(main_layout)
        
        # 状态显示区域
        self._create_status_section(main_layout)
        
        # 底部按钮
        self._create_buttons(main_layout)
    
    def _create_fingerprint_section(self, main_layout):
        """创建硬件指纹显示区域"""
        fingerprint_group = QGroupBox("本机硬件指纹")
        fingerprint_layout = QVBoxLayout(fingerprint_group)
        
        # 说明文字
        info_label = QLabel("请将以下硬件指纹发送给软件供应商以获取解锁码：")
        info_label.setStyleSheet("color: #7f8c8d; font-size: 9pt;")
        fingerprint_layout.addWidget(info_label)
        
        # 硬件指纹显示
        self.fingerprint_display = QTextEdit()
        self.fingerprint_display.setMinimumHeight(100)
        self.fingerprint_display.setMaximumHeight(120)
        self.fingerprint_display.setReadOnly(True)
        self.fingerprint_display.setPlaceholderText("正在获取硬件指纹...")
        self.fingerprint_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                font-family: 'Courier New', monospace;
                font-size: 11pt;
                line-height: 1.4;
            }
        """)
        
        # 复制按钮
        copy_button = QPushButton("复制硬件指纹")
        copy_button.clicked.connect(self._copy_fingerprint)
        copy_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        
        fingerprint_layout.addWidget(self.fingerprint_display)
        fingerprint_layout.addWidget(copy_button)
        
        main_layout.addWidget(fingerprint_group)
    
    def _create_unlock_section(self, main_layout):
        """创建解锁码输入区域"""
        unlock_group = QGroupBox("输入解锁码")
        unlock_layout = QVBoxLayout(unlock_group)
        
        # 说明文字
        info_label = QLabel("请输入从软件供应商处获得的解锁码：")
        info_label.setStyleSheet("color: #7f8c8d; font-size: 9pt;")
        unlock_layout.addWidget(info_label)
        
        # 解锁码输入
        self.unlock_code_input = QLineEdit()
        self.unlock_code_input.setPlaceholderText("请粘贴完整的解锁码...")
        self.unlock_code_input.setMinimumHeight(40)
        self.unlock_code_input.setStyleSheet("""
            QLineEdit {
                font-size: 12pt;
                padding: 12px;
            }
        """)
        self.unlock_code_input.textChanged.connect(self._on_unlock_code_changed)
        
        unlock_layout.addWidget(self.unlock_code_input)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        clear_button = QPushButton("清空")
        clear_button.clicked.connect(self._clear_unlock_code)
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        
        self.unlock_button = QPushButton("验证解锁")
        self.unlock_button.setEnabled(False)
        self.unlock_button.clicked.connect(self._verify_unlock_code)
        self.unlock_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                font-size: 11pt;
                padding: 12px 24px;
            }
            QPushButton:hover:enabled {
                background-color: #c0392b;
            }
        """)
        
        button_layout.addWidget(clear_button)
        button_layout.addStretch()
        button_layout.addWidget(self.unlock_button)
        
        unlock_layout.addLayout(button_layout)
        
        main_layout.addWidget(unlock_group)
    
    def _create_status_section(self, main_layout):
        """创建状态显示区域"""
        status_group = QGroupBox("解锁状态")
        status_layout = QVBoxLayout(status_group)
        
        self.status_display = QTextEdit()
        self.status_display.setMinimumHeight(80)
        self.status_display.setMaximumHeight(100)
        self.status_display.setReadOnly(True)
        self.status_display.setPlaceholderText("解锁状态将显示在这里...")
        self.status_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                font-size: 11pt;
                line-height: 1.4;
            }
        """)
        
        status_layout.addWidget(self.status_display)
        
        # 更新当前状态
        self._update_license_status()
        
        main_layout.addWidget(status_group)
    
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
    
    def _load_hardware_fingerprint(self):
        """加载硬件指纹"""
        try:
            if self.license_manager:
                fingerprint = self.license_manager.get_hardware_fingerprint()
                
                # 格式化显示硬件指纹
                formatted_fingerprint = self._format_fingerprint(fingerprint)
                self.fingerprint_display.setText(formatted_fingerprint)
            else:
                self.fingerprint_display.setText("无法获取硬件指纹：授权管理器未初始化")
                
        except Exception as e:
            logger.error(f"加载硬件指纹失败: {e}")
            self.fingerprint_display.setText(f"获取硬件指纹失败: {e}")
    
    def _format_fingerprint(self, fingerprint):
        """格式化硬件指纹显示"""
        try:
            # 将长字符串分行显示，每行20个字符
            lines = []
            for i in range(0, len(fingerprint), 20):
                line = fingerprint[i:i+20]
                # 每4个字符加一个空格
                formatted_line = ' '.join([line[j:j+4] for j in range(0, len(line), 4)])
                lines.append(formatted_line)
            
            return '\n'.join(lines)
            
        except Exception as e:
            logger.error(f"格式化硬件指纹失败: {e}")
            return fingerprint
    
    def _copy_fingerprint(self):
        """复制硬件指纹"""
        try:
            if self.license_manager:
                fingerprint = self.license_manager.get_hardware_fingerprint()
                clipboard = QApplication.clipboard()
                clipboard.setText(fingerprint)
                QMessageBox.information(
                    self, 
                    "复制成功", 
                    "硬件指纹已复制到剪贴板！\n\n请将此硬件指纹发送给软件供应商以获取解锁码。"
                )
            else:
                QMessageBox.warning(self, "复制失败", "无法获取硬件指纹")
                
        except Exception as e:
            logger.error(f"复制硬件指纹失败: {e}")
            QMessageBox.warning(self, "复制失败", f"复制失败：{e}")
    
    def _on_unlock_code_changed(self):
        """解锁码输入变化处理"""
        try:
            unlock_code = self.unlock_code_input.text().strip()
            self.unlock_button.setEnabled(bool(unlock_code))
            
        except Exception as e:
            logger.error(f"处理解锁码输入变化失败: {e}")
    
    def _clear_unlock_code(self):
        """清空解锁码"""
        try:
            self.unlock_code_input.clear()
            self.status_display.clear()
            self._update_license_status()
            
        except Exception as e:
            logger.error(f"清空解锁码失败: {e}")
    
    def _verify_unlock_code(self):
        """验证解锁码"""
        try:
            unlock_code = self.unlock_code_input.text().strip()
            
            if not unlock_code:
                QMessageBox.warning(self, "输入错误", "请输入解锁码")
                return
            
            # 显示验证状态
            self.status_display.setText("正在验证解锁码...")
            QApplication.processEvents()
            
            # 验证并解锁
            if not self.license_manager:
                QMessageBox.critical(self, "错误", "授权管理器未初始化")
                return
            
            result = self.license_manager.unlock_with_code(unlock_code)
            
            if result.get('success', False):
                message = result.get('message', '解锁成功')
                self.status_display.setText(f"✅ {message}")
                
                QMessageBox.information(
                    self,
                    "解锁成功",
                    f"{message}\n\n您现在可以正常使用软件了。"
                )
                
                # 发送解锁成功信号
                self.unlock_successful.emit()
                
                # 清空输入框并更新状态
                self._clear_unlock_code()
                
            else:
                error_msg = result.get('message', '解锁码无效')
                self.status_display.setText(f"❌ {error_msg}")
                
                QMessageBox.warning(
                    self,
                    "解锁失败",
                    f"{error_msg}\n\n请检查解锁码是否正确，或联系软件供应商。"
                )
                
        except Exception as e:
            logger.error(f"验证解锁码失败: {e}")
            self.status_display.setText(f"❌ 验证失败: {e}")
            QMessageBox.critical(self, "解锁错误", f"解锁过程中发生错误：\n\n{e}")
    
    def _update_license_status(self):
        """更新授权状态显示"""
        try:
            if self.license_manager:
                status = self.license_manager.check_license()

                if status.get('is_licensed', False):
                    license_type = status.get('license_type', 'full')

                    if license_type == 'temp':
                        # 临时授权
                        remaining_days = status.get('remaining_days', 0)
                        self.status_display.setText(f"⏰ 获得 {remaining_days} 天临时授权")
                        # 临时授权期间仍可以输入新的解锁码
                        self.unlock_code_input.setEnabled(True)
                        self.unlock_button.setEnabled(True)
                    else:
                        # 永久授权
                        self.status_display.setText("✅ 软件已授权，可正常使用所有功能")
                        self.unlock_code_input.setEnabled(False)
                        self.unlock_button.setEnabled(False)
                elif status.get('is_trial', False) and not status.get('is_expired', False):
                    remaining_days = status.get('remaining_days', 0)
                    self.status_display.setText(f"⏰ 试用期剩余 {remaining_days} 天")
                else:
                    self.status_display.setText("❌ 试用期已到期，请输入解锁码")

        except Exception as e:
            logger.error(f"更新授权状态失败: {e}")
