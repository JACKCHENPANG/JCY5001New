# -*- coding: utf-8 -*-
"""
客户端解锁申请对话框
用于客户申请软件解锁和输入解锁码

Author: Jack
Date: 2025-06-08
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QGroupBox, QMessageBox, QApplication,
    QTabWidget, QWidget, QFrame, QMenu, QAction
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

logger = logging.getLogger(__name__)


class UnlockRequestDialog(QDialog):
    """客户端解锁申请对话框"""
    
    # 信号定义
    unlock_successful = pyqtSignal()  # 解锁成功信号
    
    def __init__(self, license_manager, parent=None):
        """
        初始化解锁申请对话框
        
        Args:
            license_manager: 授权管理器
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.license_manager = license_manager
        self.hardware_fingerprint = ""
        self.unlock_code_inputs = []
        
        self._init_ui()
        self._load_hardware_fingerprint()
        
        logger.debug("客户端解锁申请对话框初始化完成")
    
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("软件解锁申请")
        self.setFixedSize(650, 650)  # 增加高度以确保所有内容正常显示
        self.setModal(True)
        
        # 设置窗口图标
        try:
            self.setWindowIcon(QIcon("resources/icons/unlock.png"))
        except:
            pass
        
        # 应用样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                color: #2c3e50;
            }
            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                background-color: white;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #ecf0f1;
                color: #2c3e50;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #3498db;
                color: white;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 12pt;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建标题
        self._create_title(main_layout)
        
        # 创建选项卡
        self._create_tabs(main_layout)
        
        # 创建底部按钮
        self._create_bottom_buttons(main_layout)
    
    def _create_title(self, main_layout):
        """创建标题区域"""
        title_frame = QFrame()
        title_frame.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        title_layout = QVBoxLayout(title_frame)
        
        # 主标题
        title_label = QLabel("软件解锁申请")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white; margin: 5px;")
        
        # 副标题
        subtitle_label = QLabel("JCY5001AS 8路EIS阻抗筛选仪")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(11)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("color: #bdc3c7; margin: 2px;")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        main_layout.addWidget(title_frame)
    
    def _create_tabs(self, main_layout):
        """创建选项卡"""
        self.tab_widget = QTabWidget()
        
        # 申请解锁选项卡
        self.request_tab = self._create_request_tab()
        self.tab_widget.addTab(self.request_tab, "📋 申请解锁")
        
        # 输入解锁码选项卡
        self.unlock_tab = self._create_unlock_tab()
        self.tab_widget.addTab(self.unlock_tab, "🔑 输入解锁码")
        
        main_layout.addWidget(self.tab_widget)
    
    def _create_request_tab(self):
        """创建申请解锁选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 说明信息
        info_group = QGroupBox("解锁申请说明")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel("""
<b>如何申请软件解锁：</b><br><br>
1. 复制下方的硬件指纹码<br>
2. 发送硬件指纹码给软件供应商<br>
3. 供应商会为您生成专用的解锁码<br>
4. 在"输入解锁码"选项卡中输入解锁码完成解锁<br><br>
<b>联系方式：</b><br>
• 邮箱：support@jingceyun.com<br>
• 电话：400-xxx-xxxx<br>
• QQ：123456789
        """)
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #34495e; line-height: 1.5;")
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_group)
        
        # 硬件指纹显示
        fingerprint_group = QGroupBox("本机硬件指纹码")
        fingerprint_layout = QVBoxLayout(fingerprint_group)
        
        # 硬件指纹显示框
        self.fingerprint_display = QTextEdit()
        self.fingerprint_display.setMaximumHeight(100)
        self.fingerprint_display.setReadOnly(True)
        self.fingerprint_display.setPlaceholderText("正在获取硬件指纹...")
        self.fingerprint_display.setStyleSheet("""
            QTextEdit {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Courier New', monospace;
                font-size: 12pt;
                background-color: #f8f9fa;
                color: #2c3e50;
            }
        """)
        fingerprint_layout.addWidget(self.fingerprint_display)
        
        # 复制按钮
        copy_button = QPushButton("📋 复制硬件指纹")
        copy_button.clicked.connect(self._copy_fingerprint)
        copy_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        fingerprint_layout.addWidget(copy_button)
        
        layout.addWidget(fingerprint_group)
        
        return tab
    
    def _create_unlock_tab(self):
        """创建输入解锁码选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 解锁码输入组
        unlock_group = QGroupBox("输入解锁码")
        unlock_layout = QVBoxLayout(unlock_group)
        
        # 说明文字
        instruction_label = QLabel("请输入供应商提供的解锁码：")
        instruction_label.setFont(QFont("", 11))
        instruction_label.setStyleSheet("color: #34495e; margin-bottom: 10px;")
        unlock_layout.addWidget(instruction_label)
        
        # 解锁码输入框（4段式）
        code_layout = QHBoxLayout()
        
        for i in range(4):
            code_input = QLineEdit()
            code_input.setMaxLength(8)
            code_input.setPlaceholderText("XXXXXXXX")
            code_input.setStyleSheet("""
                QLineEdit {
                    border: 2px solid #bdc3c7;
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 12pt;
                    font-family: 'Courier New', monospace;
                    text-align: center;
                }
                QLineEdit:focus {
                    border-color: #3498db;
                }
            """)
            code_input.textChanged.connect(self._on_code_input_changed)
            # 添加右键菜单支持粘贴
            code_input.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            code_input.customContextMenuRequested.connect(lambda pos, input_box=code_input: self._show_context_menu(pos, input_box))
            self.unlock_code_inputs.append(code_input)
            code_layout.addWidget(code_input)
            
            if i < 3:
                dash_label = QLabel("-")
                dash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                dash_label.setFont(QFont("", 16, QFont.Bold))
                code_layout.addWidget(dash_label)
        
        unlock_layout.addLayout(code_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 清空按钮
        clear_button = QPushButton("清空")
        clear_button.clicked.connect(self._clear_unlock_code)
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        
        # 验证按钮
        self.verify_button = QPushButton("🔓 验证并解锁")
        self.verify_button.setEnabled(False)
        self.verify_button.clicked.connect(self._verify_unlock_code)
        self.verify_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover:enabled {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        
        button_layout.addWidget(clear_button)
        button_layout.addStretch()
        button_layout.addWidget(self.verify_button)
        
        unlock_layout.addLayout(button_layout)
        
        layout.addWidget(unlock_group)
        
        # 解锁状态显示
        status_group = QGroupBox("解锁状态")
        status_layout = QVBoxLayout(status_group)
        
        self.status_display = QTextEdit()
        self.status_display.setMaximumHeight(80)
        self.status_display.setReadOnly(True)
        self.status_display.setPlaceholderText("解锁操作结果将显示在这里...")
        self.status_display.setStyleSheet("""
            QTextEdit {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 8px;
                font-size: 10pt;
                background-color: #f8f9fa;
            }
        """)
        
        status_layout.addWidget(self.status_display)
        layout.addWidget(status_group)
        
        return tab
    
    def _create_bottom_buttons(self, main_layout):
        """创建底部按钮"""
        button_layout = QHBoxLayout()
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
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
                self.hardware_fingerprint = self.license_manager.get_hardware_fingerprint()
                
                # 格式化显示硬件指纹
                formatted_fingerprint = self._format_fingerprint(self.hardware_fingerprint)
                self.fingerprint_display.setText(formatted_fingerprint)
            else:
                self.fingerprint_display.setText("无法获取硬件指纹：授权管理器未初始化")
                
        except Exception as e:
            logger.error(f"加载硬件指纹失败: {e}")
            self.fingerprint_display.setText(f"获取硬件指纹失败: {e}")
    
    def _format_fingerprint(self, fingerprint):
        """格式化硬件指纹显示"""
        try:
            # 将长字符串分行显示，每行16个字符
            lines = []
            for i in range(0, len(fingerprint), 16):
                line = fingerprint[i:i+16]
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
            if self.hardware_fingerprint:
                clipboard = QApplication.clipboard()
                clipboard.setText(self.hardware_fingerprint)
                QMessageBox.information(
                    self, 
                    "复制成功", 
                    "硬件指纹已复制到剪贴板！\n\n请将此硬件指纹发送给软件供应商以获取解锁码。"
                )
            else:
                QMessageBox.warning(self, "复制失败", "没有可复制的硬件指纹")
                
        except Exception as e:
            logger.error(f"复制硬件指纹失败: {e}")
            QMessageBox.warning(self, "复制失败", f"复制失败：{e}")
    
    def _on_code_input_changed(self):
        """解锁码输入变化处理"""
        try:
            # 检查是否所有输入框都有内容
            all_filled = all(input_box.text().strip() for input_box in self.unlock_code_inputs)
            self.verify_button.setEnabled(all_filled)
            
            # 自动跳转到下一个输入框
            sender = self.sender()
            if sender and len(sender.text()) == 8:
                current_index = self.unlock_code_inputs.index(sender)
                if current_index < len(self.unlock_code_inputs) - 1:
                    self.unlock_code_inputs[current_index + 1].setFocus()
                    
        except Exception as e:
            logger.error(f"处理解锁码输入变化失败: {e}")
    
    def _clear_unlock_code(self):
        """清空解锁码输入"""
        try:
            for input_box in self.unlock_code_inputs:
                input_box.clear()
            self.unlock_code_inputs[0].setFocus()
            self.verify_button.setEnabled(False)
            self.status_display.clear()
            
        except Exception as e:
            logger.error(f"清空解锁码失败: {e}")
    
    def _get_unlock_code(self):
        """获取输入的解锁码"""
        try:
            code_parts = [input_box.text().strip() for input_box in self.unlock_code_inputs]
            return "-".join(code_parts)
        except Exception as e:
            logger.error(f"获取解锁码失败: {e}")
            return ""
    
    def _verify_unlock_code(self):
        """验证解锁码"""
        try:
            unlock_code = self._get_unlock_code()
            
            if not unlock_code or unlock_code.count("-") != 3:
                QMessageBox.warning(self, "输入错误", "请输入完整的解锁码")
                return
            
            # 显示验证状态
            self.status_display.setText("正在验证解锁码...")
            QApplication.processEvents()
            
            # 验证并解锁
            result = self.license_manager.unlock_with_code(unlock_code)
            
            if result.get('success', False):
                unlock_type = result.get('unlock_type', 'unknown')
                message = result.get('message', '解锁成功')
                
                self.status_display.setText(f"✅ {message}")
                
                QMessageBox.information(
                    self,
                    "解锁成功",
                    f"{message}\n\n您现在可以正常使用软件了。"
                )
                
                # 发送解锁成功信号
                self.unlock_successful.emit()
                
                # 清空输入框
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

    def _show_context_menu(self, pos, input_box):
        """显示右键菜单"""
        try:
            menu = QMenu(self)

            # 粘贴动作
            paste_action = QAction("粘贴", self)
            paste_action.triggered.connect(lambda: self._paste_unlock_code(input_box))
            menu.addAction(paste_action)

            # 清空动作
            clear_action = QAction("清空", self)
            clear_action.triggered.connect(lambda: self._clear_unlock_code())
            menu.addAction(clear_action)

            # 显示菜单
            menu.exec_(input_box.mapToGlobal(pos))

        except Exception as e:
            logger.error(f"显示右键菜单失败: {e}")

    def _paste_unlock_code(self, target_input=None):
        """粘贴解锁码"""
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text().strip()

            if not text:
                QMessageBox.information(self, "提示", "剪贴板为空")
                return

            # 尝试解析解锁码格式
            if "-" in text:
                # 带分隔符的格式：XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX
                parts = text.split("-")
                if len(parts) == 4:
                    for i, part in enumerate(parts):
                        if i < len(self.unlock_code_inputs):
                            self.unlock_code_inputs[i].setText(part.strip().upper())
                    QMessageBox.information(self, "成功", "解锁码已粘贴")
                    return

            # 无分隔符的格式：32位连续字符
            if len(text) == 32 and text.replace("-", "").isalnum():
                # 分割为4个8位段
                for i in range(4):
                    start = i * 8
                    end = start + 8
                    if i < len(self.unlock_code_inputs):
                        self.unlock_code_inputs[i].setText(text[start:end].upper())
                QMessageBox.information(self, "成功", "解锁码已粘贴")
                return

            # 如果是硬件指纹格式，提示用户
            if len(text) == 64 and all(c in '0123456789abcdefABCDEF' for c in text):
                QMessageBox.information(
                    self,
                    "提示",
                    "检测到硬件指纹格式。\n\n请将此硬件指纹发送给软件供应商以获取解锁码。"
                )
                return

            # 其他格式，直接粘贴到当前输入框
            if target_input:
                target_input.setText(text[:8].upper())
            else:
                QMessageBox.warning(self, "格式错误", "无法识别的解锁码格式")

        except Exception as e:
            logger.error(f"粘贴解锁码失败: {e}")
            QMessageBox.critical(self, "错误", f"粘贴失败：{e}")
