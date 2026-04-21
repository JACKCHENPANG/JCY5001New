#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫码输入对话框
提供用户友好的USB扫码枪输入界面

Author: Jack
Date: 2025-01-28
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QGroupBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from utils.scan_gun_manager import ScanGunManager
from utils.input_method_manager import InputMethodManager
from ui.widgets.safe_line_edit import SafeLineEdit

logger = logging.getLogger(__name__)


class ScanInputDialog(QDialog):
    """扫码输入对话框"""

    # 信号定义
    scan_completed = pyqtSignal(str)  # 扫码完成信号 (battery_code)

    def __init__(self, channel_number: int, parent=None):
        """
        初始化扫码输入对话框

        Args:
            channel_number: 通道号
            parent: 父窗口
        """
        super().__init__(parent)

        self.channel_number = channel_number
        self.scanned_code = ""

        # 初始化扫码管理器
        self.scan_manager = ScanGunManager(self)

        # 初始化输入法管理器
        self.input_method_manager = InputMethodManager(self)

        # 初始化界面
        self._init_ui()
        self._init_connections()
        self._init_styles()

        # 开始扫码
        self._start_scanning()

        logger.debug(f"扫码输入对话框初始化完成 - 通道{channel_number}")

    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(f"通道{self.channel_number} - 扫码输入")
        # self.setWindowIcon(QIcon("resources/icons/scan.png"))  # 暂时注释掉图标
        self.setModal(True)
        self.setFixedSize(700, 600)  # 进一步增大界面尺寸：从600x480增加到700x600

        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)  # 进一步增加边距
        main_layout.setSpacing(25)  # 进一步增加间距

        # 创建标题区域
        self._create_title_area(main_layout)

        # 创建扫码状态区域
        self._create_status_area(main_layout)

        # 创建输入区域
        self._create_input_area(main_layout)

        # 创建按钮区域
        self._create_button_area(main_layout)

        # 创建提示区域
        self._create_tips_area(main_layout)

    def _create_title_area(self, layout):
        """创建标题区域"""
        title_frame = QFrame()
        title_frame.setObjectName("titleFrame")
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(15, 15, 15, 15)  # 增加内边距

        # 扫码图标
        icon_label = QLabel("🔫")
        icon_label.setFont(QFont("", 32))  # 增大图标字体：从24增加到32
        title_layout.addWidget(icon_label)

        # 标题文字
        title_label = QLabel(f"通道 {self.channel_number} 扫码")
        title_label.setFont(QFont("", 20, QFont.Bold))  # 增大标题字体：从16增加到20
        title_label.setObjectName("titleLabel")
        title_layout.addWidget(title_label)

        title_layout.addStretch()
        layout.addWidget(title_frame)

    def _create_status_area(self, layout):
        """创建扫码状态区域"""
        status_group = QGroupBox("扫码状态")
        status_group.setFont(QFont("", 12, QFont.Bold))  # 增大组标题字体
        status_layout = QVBoxLayout(status_group)
        status_layout.setSpacing(15)  # 增加间距
        status_layout.setContentsMargins(15, 20, 15, 15)  # 增加内边距

        # 状态标签
        self.status_label = QLabel("🔍 请使用扫码枪扫描电池二维码...")
        self.status_label.setFont(QFont("", 14))  # 增大状态字体：从12增加到14
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumHeight(60)  # 设置最小高度，确保多行文本显示
        self.status_label.setWordWrap(True)  # 启用自动换行
        status_layout.addWidget(self.status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 30)  # 30秒超时
        self.progress_bar.setValue(30)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("剩余时间: %v 秒")
        self.progress_bar.setMinimumHeight(25)  # 增加进度条高度
        self.progress_bar.setFont(QFont("", 11))  # 设置进度条字体
        status_layout.addWidget(self.progress_bar)

        layout.addWidget(status_group)

    def _create_input_area(self, layout):
        """创建输入区域"""
        input_group = QGroupBox("扫码结果")
        input_group.setFont(QFont("", 13, QFont.Bold))  # 进一步增大组标题字体
        input_layout = QVBoxLayout(input_group)
        input_layout.setSpacing(18)  # 进一步增加间距
        input_layout.setContentsMargins(20, 25, 20, 20)  # 进一步增加内边距

        # 输入框标签
        input_label = QLabel("电池码:")
        input_label.setFont(QFont("", 14))  # 进一步增大标签字体：从12增加到14
        input_layout.addWidget(input_label)

        # 电池码输入框 - 允许回车键传递给父控件
        self.battery_code_edit = SafeLineEdit(allow_enter_passthrough=True)
        self.battery_code_edit.setPlaceholderText("扫码后自动填入，也可手动输入...")
        self.battery_code_edit.setFont(QFont("", 16))  # 进一步增大输入框字体：从14增加到16
        self.battery_code_edit.setMinimumHeight(58)  # 进一步增加输入框高度：从45增加到58
        self.battery_code_edit.setObjectName("batteryCodeEdit")
        self.battery_code_edit.textChanged.connect(self._on_manual_input)
        input_layout.addWidget(self.battery_code_edit)

        # 添加一些额外的垂直空间
        input_layout.addSpacing(10)

        layout.addWidget(input_group)

    def _create_button_area(self, layout):
        """创建按钮区域"""
        # 添加一些垂直空间
        layout.addSpacing(15)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)  # 进一步增加按钮间距

        # 重新扫码按钮
        self.rescan_button = QPushButton("重新扫码")
        self.rescan_button.setFont(QFont("", 14))  # 进一步增大按钮字体：从12增加到14
        self.rescan_button.setMinimumHeight(50)  # 进一步增加按钮高度：从40增加到50
        self.rescan_button.setMinimumWidth(120)  # 增加最小宽度
        self.rescan_button.setObjectName("rescanButton")
        self.rescan_button.clicked.connect(self._restart_scanning)
        button_layout.addWidget(self.rescan_button)

        button_layout.addStretch()

        # 确定按钮
        self.ok_button = QPushButton("确定")
        self.ok_button.setFont(QFont("", 14, QFont.Bold))  # 进一步增大按钮字体：从12增加到14
        self.ok_button.setMinimumHeight(50)  # 进一步增加按钮高度：从40增加到50
        self.ok_button.setMinimumWidth(120)  # 增加最小宽度
        self.ok_button.setObjectName("okButton")
        self.ok_button.setEnabled(False)
        self.ok_button.setDefault(True)  # 设置为默认按钮，支持回车键触发
        self.ok_button.clicked.connect(self._on_ok_clicked)
        button_layout.addWidget(self.ok_button)

        # 跳过按钮（替代取消按钮，更友好的提示）
        self.skip_button = QPushButton("跳过此通道")
        self.skip_button.setFont(QFont("", 14))  # 进一步增大按钮字体：从12增加到14
        self.skip_button.setMinimumHeight(50)  # 进一步增加按钮高度：从40增加到50
        self.skip_button.setMinimumWidth(140)  # 增加最小宽度
        self.skip_button.setObjectName("skipButton")
        self.skip_button.clicked.connect(self._on_skip_clicked)
        button_layout.addWidget(self.skip_button)

        layout.addLayout(button_layout)

        # 添加底部空间
        layout.addSpacing(10)

    def _create_tips_area(self, layout):
        """创建提示区域"""
        tips_group = QGroupBox("使用提示")
        tips_group.setFont(QFont("", 13, QFont.Bold))  # 进一步增大组标题字体
        tips_layout = QVBoxLayout(tips_group)
        tips_layout.setContentsMargins(20, 25, 20, 20)  # 进一步增加内边距

        tips_text = """
• 将扫码枪对准电池二维码，按下扫码键
• 扫码成功后会自动进入下一个通道（无需点击确定）
• 也可以手动输入电池码，然后点击"确定"
• 点击"跳过此通道"可跳过当前通道
• 注意：跳过通道将导致该通道无法进行测试
        """.strip()

        tips_label = QLabel(tips_text)
        tips_label.setFont(QFont("", 12))  # 进一步增大提示字体：从11增加到12
        tips_label.setObjectName("tipsLabel")
        tips_label.setWordWrap(True)
        tips_label.setMinimumHeight(120)  # 进一步增加最小高度：从80增加到120
        tips_layout.addWidget(tips_label)

        layout.addWidget(tips_group)

    def _init_connections(self):
        """初始化信号连接"""
        # 扫码管理器信号
        self.scan_manager.scan_completed.connect(self._on_scan_completed)
        self.scan_manager.scan_failed.connect(self._on_scan_failed)
        self.scan_manager.scan_timeout.connect(self._on_scan_timeout)

        # 进度条更新定时器
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress)
        self.progress_timer.start(1000)  # 每秒更新

    def _init_styles(self):
        """初始化样式"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }

            QFrame#titleFrame {
                background-color: #e3f2fd;
                border: 1px solid #bbdefb;
                border-radius: 6px;
            }

            QLabel#titleLabel {
                color: #1976d2;
                font-weight: bold;
            }



            QLineEdit#batteryCodeEdit {
                padding: 18px;  /* 进一步增加内边距：从15px增加到18px，配合更高的输入框 */
                border: 2px solid #ddd;
                border-radius: 8px;  /* 进一步增加圆角：从6px增加到8px */
                font-size: 16pt;  /* 进一步增大字体：从14pt增加到16pt */
                line-height: 1.2;  /* 添加行高设置，确保文字垂直居中 */
            }

            QLineEdit#batteryCodeEdit:focus {
                border-color: #2196f3;
            }

            QPushButton#okButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 8px;  /* 进一步增加圆角：从6px增加到8px */
                padding: 15px 30px;  /* 进一步增加内边距：从12px 24px增加到15px 30px */
                min-width: 120px;  /* 进一步增加最小宽度：从100px增加到120px */
                font-size: 14pt;  /* 进一步增大字体：从12pt增加到14pt */
            }

            QPushButton#okButton:hover {
                background-color: #45a049;
            }

            QPushButton#okButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }

            QPushButton#rescanButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 8px;  /* 进一步增加圆角：从6px增加到8px */
                padding: 15px 25px;  /* 进一步增加内边距：从12px 20px增加到15px 25px */
                font-size: 14pt;  /* 进一步增大字体：从12pt增加到14pt */
            }

            QPushButton#rescanButton:hover {
                background-color: #f57c00;
            }

            QPushButton#skipButton {
                background-color: #ff5722;
                color: white;
                border: none;
                border-radius: 8px;  /* 进一步增加圆角：从6px增加到8px */
                padding: 15px 25px;  /* 进一步增加内边距：从12px 20px增加到15px 25px */
                font-size: 14pt;  /* 进一步增大字体：从12pt增加到14pt */
            }

            QPushButton#skipButton:hover {
                background-color: #e64a19;
            }

            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 10px;  /* 进一步增加圆角：从8px增加到10px */
                margin-top: 15px;  /* 进一步增加上边距：从12px增加到15px */
                padding-top: 12px;  /* 进一步增加上内边距：从10px增加到12px */
                font-size: 13pt;  /* 进一步增大组框标题字体：从12pt增加到13pt */
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;  /* 进一步增加左边距：从12px增加到15px */
                padding: 0 15px 0 15px;  /* 进一步增加内边距：从12px增加到15px */
            }

            QLabel#tipsLabel {
                color: #666;
                line-height: 1.6;  /* 进一步增加行高：从1.5增加到1.6 */
                font-size: 12pt;  /* 进一步增大提示文本字体：从11pt增加到12pt */
            }

            QLabel#statusLabel {
                color: #2e7d32;
                padding: 18px;  /* 进一步增加内边距：从15px增加到18px */
                background-color: #e8f5e8;
                border: 1px solid #c8e6c9;
                border-radius: 8px;  /* 增加圆角：从6px增加到8px */
                font-size: 14pt;  /* 保持状态标签字体大小 */
            }
        """)

    def _start_scanning(self):
        """开始扫码"""
        try:
            # 清空输入框，确保新的扫码不会与之前的内容混合
            self.battery_code_edit.clear()

            # 🔤 自动切换输入法到英文，防止中文输入法干扰扫码
            logger.info(f"🔤 通道{self.channel_number}开始扫码，自动切换输入法")
            if self.input_method_manager.auto_switch_for_scanning():
                logger.info(f"🔤 通道{self.channel_number}输入法切换成功")
            else:
                logger.warning(f"🔤 通道{self.channel_number}输入法切换失败，但继续扫码")

            if self.scan_manager.start_scanning():
                self.status_label.setText("🔍 扫码枪已就绪，请扫描电池二维码\n（扫码枪对准二维码，按下扫码键）\n💡 已自动切换到英文输入法")
                self.progress_bar.setValue(30)
                logger.info(f"通道{self.channel_number}开始扫码")
            else:
                self.status_label.setText("❌ 启动扫码失败")

        except Exception as e:
            logger.error(f"启动扫码失败: {e}")
            self.status_label.setText(f"❌ 启动扫码失败: {e}")

    def _restart_scanning(self):
        """重新开始扫码"""
        try:
            self.battery_code_edit.clear()
            self.scanned_code = ""
            self.ok_button.setEnabled(False)
            self._start_scanning()

            # 确保输入框重新获得焦点
            QTimer.singleShot(100, self._set_input_focus)

            logger.info(f"通道{self.channel_number}重新开始扫码")

        except Exception as e:
            logger.error(f"重新开始扫码失败: {e}")

    def _update_progress(self):
        """更新进度条"""
        try:
            if self.scan_manager.is_scanning:
                status = self.scan_manager.get_scan_status()
                remaining = max(0, int(status['timeout_remaining']))
                self.progress_bar.setValue(remaining)

                if remaining <= 5:
                    self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #f44336; }")
                elif remaining <= 10:
                    self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff9800; }")
                else:
                    self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #4caf50; }")

        except Exception as e:
            logger.error(f"更新进度条失败: {e}")

    def _on_scan_completed(self, battery_code: str):
        """扫码完成处理"""
        try:
            logger.info(f"收到扫码完成信号: '{battery_code}' (长度: {len(battery_code)})")

            # 检查扫码内容是否为空
            if not battery_code or not battery_code.strip():
                logger.warning("收到空的扫码内容，继续等待扫码...")
                self.status_label.setText("⚠️ 扫码内容为空，请重新扫码")
                return

            # 保存扫码结果
            self.scanned_code = battery_code

            # 临时断开textChanged信号，避免触发手动输入处理
            self.battery_code_edit.textChanged.disconnect()

            # 设置文本内容
            self.battery_code_edit.setText(battery_code)

            # 重新连接信号
            self.battery_code_edit.textChanged.connect(self._on_manual_input)

            # 更新状态
            self.status_label.setText(f"✅ 扫码成功: {battery_code} - 自动进入下一通道...")
            self.ok_button.setEnabled(True)
            self.progress_timer.stop()

            logger.info(f"通道{self.channel_number}扫码成功: {battery_code}")

            # 自动确认并进入下一通道（延迟500ms让用户看到成功提示）
            QTimer.singleShot(500, self._auto_confirm)

        except Exception as e:
            logger.error(f"处理扫码完成失败: {e}")
            # 确保信号重新连接
            try:
                self.battery_code_edit.textChanged.connect(self._on_manual_input)
            except:
                pass

    def _on_scan_failed(self, error_message: str):
        """扫码失败处理"""
        try:
            self.status_label.setText(f"❌ 扫码失败: {error_message}")
            logger.warning(f"通道{self.channel_number}扫码失败: {error_message}")

        except Exception as e:
            logger.error(f"处理扫码失败失败: {e}")

    def _on_scan_timeout(self):
        """扫码超时处理"""
        try:
            self.status_label.setText("⏰ 扫码超时，请重新扫码")
            self.progress_timer.stop()
            logger.warning(f"通道{self.channel_number}扫码超时")

        except Exception as e:
            logger.error(f"处理扫码超时失败: {e}")

    def _on_manual_input(self, text: str):
        """手动输入处理"""
        try:
            # 如果有手动输入，启用确定按钮
            self.ok_button.setEnabled(len(text.strip()) >= 3)

            # 如果正在扫码状态，检查是否是扫码枪输入
            if self.scan_manager.is_scanning and text.strip() and len(text.strip()) >= 6:
                # 扫码枪通常会快速输入完整内容，如果输入长度足够，可能是扫码完成
                logger.info(f"检测到可能的扫码输入: '{text}' (长度: {len(text)})")

                # 延迟检测，给扫码枪时间完成输入
                QTimer.singleShot(200, self._check_scan_completion)

        except Exception as e:
            logger.error(f"处理手动输入失败: {e}")

    def _check_scan_completion(self):
        """检查扫码是否完成"""
        try:
            current_text = self.battery_code_edit.text().strip()
            if self.scan_manager.is_scanning and current_text and len(current_text) >= 6:
                # 如果文本没有继续变化，认为扫码完成
                logger.info(f"扫码输入稳定，触发完成: '{current_text}'")
                self._trigger_scan_completion(current_text)

        except Exception as e:
            logger.error(f"检查扫码完成失败: {e}")

    def _trigger_scan_completion(self, battery_code: str):
        """触发扫码完成"""
        try:
            if self.scan_manager.is_scanning:
                logger.info(f"手动触发扫码完成: '{battery_code}'")
                self.scan_manager.stop_scanning()
                self._on_scan_completed(battery_code)

        except Exception as e:
            logger.error(f"触发扫码完成失败: {e}")

    def _on_ok_clicked(self):
        """确定按钮点击处理"""
        try:
            battery_code = self.battery_code_edit.text().strip()
            if battery_code:
                self.scanned_code = battery_code
                self.scan_completed.emit(battery_code)
                self.accept()
                logger.info(f"通道{self.channel_number}确认电池码: {battery_code}")

        except Exception as e:
            logger.error(f"确定按钮处理失败: {e}")

    def _auto_confirm(self):
        """自动确认扫码结果"""
        try:
            battery_code = self.battery_code_edit.text().strip()

            if battery_code:
                self.scanned_code = battery_code
                logger.info(f"自动确认电池码: '{battery_code}'")
                self.scan_completed.emit(battery_code)
                self.accept()
                logger.info(f"通道{self.channel_number}自动确认完成")
            else:
                logger.warning(f"通道{self.channel_number}自动确认失败: 电池码为空")

        except Exception as e:
            logger.error(f"🚀 自动确认失败: {e}")

    def _on_skip_clicked(self):
        """跳过按钮点击处理"""
        try:
            # 停止扫码
            if self.scan_manager.is_scanning:
                self.scan_manager.stop_scanning()

            # 停止定时器
            if hasattr(self, 'progress_timer'):
                self.progress_timer.stop()

            logger.info(f"用户选择跳过通道{self.channel_number}")
            self.reject()  # 返回取消状态

        except Exception as e:
            logger.error(f"跳过按钮处理失败: {e}")
            self.reject()

    def keyPressEvent(self, event):
        """键盘事件处理"""
        try:
            # 获取按键信息
            key = event.key()
            text = event.text()

            # 处理回车键 - 使用正确的Qt常量
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                logger.debug("检测到回车键")

                # 如果正在扫码，检查是否应该触发扫码完成
                if self.scan_manager.is_scanning:
                    current_text = self.battery_code_edit.text().strip()
                    if current_text and len(current_text) >= 6:
                        logger.info(f"回车键触发扫码完成: '{current_text}'")
                        self._trigger_scan_completion(current_text)
                        return
                    else:
                        # 传递回车符给扫码管理器
                        self.scan_manager.process_input('\r')
                        super().keyPressEvent(event)
                        return
                else:
                    # 扫码完成后，如果确认按钮可用，触发确认操作
                    if self.ok_button.isEnabled():
                        logger.info("回车键触发确认按钮")
                        self._on_ok_clicked()
                        return

            # 如果正在扫码，将其他字符输入传递给扫码管理器
            if self.scan_manager.is_scanning and text:
                # 传递给扫码管理器处理
                self.scan_manager.process_input(text)
                # 让输入正常显示在输入框中
                super().keyPressEvent(event)
                return

            # 其他键盘事件正常处理
            super().keyPressEvent(event)

        except Exception as e:
            logger.error(f"键盘事件处理失败: {e}")
            super().keyPressEvent(event)

    def showEvent(self, event):
        """窗口显示事件 - 确保输入框获得焦点"""
        try:
            super().showEvent(event)

            # 确保窗口激活并获得焦点
            self.activateWindow()
            self.raise_()
            self.setFocus()

            # 延迟设置焦点，确保窗口完全显示后再设置
            QTimer.singleShot(50, self._set_input_focus)
            # 再次延迟确保焦点设置成功
            QTimer.singleShot(150, self._set_input_focus)

            logger.debug(f"通道{self.channel_number}扫码对话框显示完成")

        except Exception as e:
            logger.error(f"窗口显示事件处理失败: {e}")
            super().showEvent(event)

    def _set_input_focus(self):
        """设置输入框焦点"""
        try:
            # 确保输入框获得焦点
            self.battery_code_edit.setFocus()
            self.battery_code_edit.selectAll()  # 选中所有文本，方便扫码枪覆盖

            logger.debug(f"通道{self.channel_number}输入框焦点设置完成")

        except Exception as e:
            logger.error(f"设置输入框焦点失败: {e}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 停止扫码
            if self.scan_manager.is_scanning:
                self.scan_manager.stop_scanning()

            # 停止定时器
            if hasattr(self, 'progress_timer'):
                self.progress_timer.stop()

            # 🔤 恢复之前的输入法
            logger.info(f"🔤 通道{self.channel_number}扫码对话框关闭，恢复输入法")
            if self.input_method_manager.restore_previous_input_method():
                logger.info(f"🔤 通道{self.channel_number}输入法恢复成功")
            else:
                logger.warning(f"🔤 通道{self.channel_number}输入法恢复失败")

            event.accept()

        except Exception as e:
            logger.error(f"窗口关闭事件处理失败: {e}")
            event.accept()

    def get_scanned_code(self) -> str:
        """
        获取扫码结果

        Returns:
            扫码得到的电池码
        """
        return self.scanned_code
