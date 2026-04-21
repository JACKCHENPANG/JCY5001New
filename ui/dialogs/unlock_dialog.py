# -*- coding: utf-8 -*-
"""
软件解锁对话框
提供解锁码输入和验证功能

Author: Jack
Date: 2025-06-03
"""

import logging
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QGroupBox,
                             QMessageBox, QApplication, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap

logger = logging.getLogger(__name__)


class UnlockDialog(QDialog):
    """软件解锁对话框"""
    
    # 信号定义
    unlock_successful = pyqtSignal()  # 解锁成功信号
    
    def __init__(self, license_manager, parent=None):
        """
        初始化解锁对话框
        
        Args:
            license_manager: 授权管理器
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.license_manager = license_manager
        self.unlock_code_inputs = []
        
        self._init_ui()
        self._update_status_display()
        
        logger.debug("解锁对话框初始化完成")
    
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("软件授权解锁")
        self.setFixedSize(500, 600)
        self.setModal(True)
        
        # 设置窗口图标
        try:
            self.setWindowIcon(QIcon("resources/icons/lock.png"))
        except:
            pass
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("JCY5001AS 软件授权解锁")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # 当前状态组
        self._create_status_group(main_layout)
        
        # 硬件指纹组
        self._create_fingerprint_group(main_layout)
        
        # 解锁码输入组
        self._create_unlock_code_group(main_layout)
        
        # 按钮组
        self._create_button_group(main_layout)
        
        # 说明文本
        self._create_help_text(main_layout)
    
    def _create_status_group(self, main_layout):
        """创建状态显示组"""
        status_group = QGroupBox("当前授权状态")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                background-color: #ecf0f1;
                font-size: 12pt;
            }
        """)
        status_layout.addWidget(self.status_label)
        
        main_layout.addWidget(status_group)
    
    def _create_fingerprint_group(self, main_layout):
        """创建硬件指纹组"""
        fingerprint_group = QGroupBox("硬件指纹信息")
        fingerprint_layout = QVBoxLayout(fingerprint_group)
        
        # 说明文本
        info_label = QLabel("请将以下硬件指纹提供给软件供应商以获取解锁码：")
        info_label.setStyleSheet("color: #7f8c8d; font-size: 10pt;")
        fingerprint_layout.addWidget(info_label)
        
        # 硬件指纹显示
        self.fingerprint_text = QTextEdit()
        self.fingerprint_text.setMaximumHeight(80)
        self.fingerprint_text.setReadOnly(True)
        self.fingerprint_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Courier New', monospace;
                font-size: 11pt;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        # 设置硬件指纹
        fingerprint = self.license_manager.get_hardware_fingerprint()
        formatted_fingerprint = self._format_fingerprint(fingerprint)
        self.fingerprint_text.setPlainText(formatted_fingerprint)
        
        fingerprint_layout.addWidget(self.fingerprint_text)
        
        # 复制按钮
        copy_button = QPushButton("复制硬件指纹")
        copy_button.clicked.connect(self._copy_fingerprint)
        copy_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        fingerprint_layout.addWidget(copy_button)
        
        main_layout.addWidget(fingerprint_group)
    
    def _create_unlock_code_group(self, main_layout):
        """创建解锁码输入组"""
        unlock_group = QGroupBox("解锁码输入")
        unlock_layout = QVBoxLayout(unlock_group)
        
        # 说明文本
        info_label = QLabel("请输入从软件供应商获取的解锁码：")
        info_label.setStyleSheet("color: #7f8c8d; font-size: 10pt;")
        unlock_layout.addWidget(info_label)
        
        # 解锁码输入框（4个分组）
        code_layout = QHBoxLayout()
        self.unlock_code_inputs = []
        
        for i in range(4):
            input_field = QLineEdit()
            input_field.setMaxLength(8)
            input_field.setPlaceholderText("8位字符")
            input_field.setStyleSheet("""
                QLineEdit {
                    font-family: 'Courier New', monospace;
                    font-size: 12pt;
                    padding: 8px;
                    border: 2px solid #bdc3c7;
                    border-radius: 4px;
                    text-align: center;
                }
                QLineEdit:focus {
                    border-color: #3498db;
                }
            """)
            input_field.textChanged.connect(self._on_unlock_code_changed)
            self.unlock_code_inputs.append(input_field)
            code_layout.addWidget(input_field)
            
            # 添加分隔符（除了最后一个）
            if i < 3:
                separator = QLabel("-")
                separator.setAlignment(Qt.AlignCenter)
                separator.setStyleSheet("font-size: 14pt; font-weight: bold; color: #7f8c8d;")
                code_layout.addWidget(separator)
        
        unlock_layout.addLayout(code_layout)
        
        main_layout.addWidget(unlock_group)
    
    def _create_button_group(self, main_layout):
        """创建按钮组"""
        button_layout = QHBoxLayout()
        
        # 验证解锁码按钮
        self.unlock_button = QPushButton("验证并解锁")
        self.unlock_button.setEnabled(False)
        self.unlock_button.clicked.connect(self._unlock_software)
        self.unlock_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.unlock_button)
        
        main_layout.addLayout(button_layout)
    
    def _create_help_text(self, main_layout):
        """创建帮助文本"""
        help_text = QLabel("""
<b>使用说明：</b><br>
1. 复制上方的硬件指纹信息<br>
2. 联系软件供应商并提供硬件指纹<br>
3. 获取解锁码后输入到上方输入框中<br>
4. 点击"验证并解锁"完成授权
        """)
        help_text.setWordWrap(True)
        help_text.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 9pt;
                padding: 10px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        main_layout.addWidget(help_text)

    def _format_fingerprint(self, fingerprint: str) -> str:
        """
        格式化硬件指纹显示

        Args:
            fingerprint: 硬件指纹

        Returns:
            格式化后的指纹
        """
        if not fingerprint:
            return "无法获取硬件指纹"

        # 每8个字符一组，用空格分隔
        formatted = ""
        for i in range(0, len(fingerprint), 8):
            if formatted:
                formatted += " "
            formatted += fingerprint[i:i+8]

        return formatted.upper()

    def _copy_fingerprint(self):
        """复制硬件指纹到剪贴板"""
        try:
            clipboard = QApplication.clipboard()
            fingerprint = self.license_manager.get_hardware_fingerprint()
            clipboard.setText(fingerprint)

            QMessageBox.information(self, "复制成功", "硬件指纹已复制到剪贴板")

        except Exception as e:
            logger.error(f"复制硬件指纹失败: {e}")
            QMessageBox.warning(self, "复制失败", "无法复制硬件指纹到剪贴板")

    def _on_unlock_code_changed(self):
        """解锁码输入变化处理"""
        try:
            # 检查所有输入框是否都有内容
            all_filled = all(input_field.text().strip() for input_field in self.unlock_code_inputs)

            # 启用/禁用解锁按钮
            self.unlock_button.setEnabled(all_filled)

            # 自动跳转到下一个输入框
            sender = self.sender()
            if isinstance(sender, QLineEdit) and len(sender.text()) == 8:
                current_index = self.unlock_code_inputs.index(sender)
                if current_index < len(self.unlock_code_inputs) - 1:
                    self.unlock_code_inputs[current_index + 1].setFocus()

        except Exception as e:
            logger.error(f"处理解锁码输入变化失败: {e}")

    def _get_unlock_code(self) -> str:
        """
        获取完整的解锁码

        Returns:
            解锁码字符串
        """
        code_parts = [input_field.text().strip() for input_field in self.unlock_code_inputs]
        return "-".join(code_parts)

    def _unlock_software(self):
        """解锁软件"""
        try:
            unlock_code = self._get_unlock_code()

            if not unlock_code or unlock_code.count("-") != 3:
                QMessageBox.warning(self, "输入错误", "请输入完整的解锁码")
                return

            # 验证并解锁
            if self.license_manager.unlock_software(unlock_code):
                QMessageBox.information(
                    self,
                    "解锁成功",
                    "软件已成功解锁！\n\n您现在可以无限制使用本软件。"
                )

                # 发送解锁成功信号
                self.unlock_successful.emit()

                # 关闭对话框
                self.accept()
            else:
                QMessageBox.warning(
                    self,
                    "解锁失败",
                    "解锁码无效！\n\n请检查解锁码是否正确，或联系软件供应商。"
                )

        except Exception as e:
            logger.error(f"解锁软件失败: {e}")
            QMessageBox.critical(self, "解锁错误", f"解锁过程中发生错误：\n\n{e}")

    def _update_status_display(self):
        """更新状态显示"""
        try:
            status = self.license_manager.get_license_status()

            if status['is_licensed']:
                license_type = status.get('license_type', 'full')

                if license_type == 'temp':
                    # 临时授权
                    remaining_days = status.get('remaining_days', 0)
                    expire_date = status.get('expire_date', '')

                    if expire_date:
                        from datetime import datetime
                        expire_dt = datetime.fromisoformat(expire_date)
                        expire_str = expire_dt.strftime("%Y年%m月%d日")
                    else:
                        expire_str = "未知"

                    status_text = f"⏰ 获得 {remaining_days} 天临时授权\n\n到期时间：{expire_str}"
                    status_color = "#f39c12"  # 橙色，表示临时状态
                else:
                    # 永久授权
                    status_text = "✅ 软件已授权\n\n您可以无限制使用本软件。"
                    status_color = "#27ae60"
            elif not status['is_trial_expired']:
                remaining_days = status['remaining_days']
                expire_date = status.get('expire_date', '')

                if expire_date:
                    from datetime import datetime
                    expire_dt = datetime.fromisoformat(expire_date)
                    expire_str = expire_dt.strftime("%Y年%m月%d日")
                else:
                    expire_str = "未知"

                status_text = f"⏰ 试用期剩余 {remaining_days} 天\n\n到期时间：{expire_str}"
                status_color = "#f39c12"
            else:
                status_text = "❌ 试用期已到期\n\n请输入解锁码以继续使用软件。"
                status_color = "#e74c3c"

            self.status_label.setText(status_text)
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    padding: 10px;
                    border: 1px solid #bdc3c7;
                    border-radius: 5px;
                    background-color: #ecf0f1;
                    font-size: 12pt;
                    color: {status_color};
                }}
            """)

        except Exception as e:
            logger.error(f"更新状态显示失败: {e}")
            self.status_label.setText("❓ 无法获取授权状态")

    def showEvent(self, event):
        """对话框显示事件"""
        super().showEvent(event)
        # 刷新状态显示
        self._update_status_display()

        # 设置焦点到第一个输入框
        if self.unlock_code_inputs:
            self.unlock_code_inputs[0].setFocus()
