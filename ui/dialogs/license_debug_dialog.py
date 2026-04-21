# -*- coding: utf-8 -*-
"""
授权调试对话框
用于开发和测试环境中调试试用期和授权锁定机制

功能：
- 试用期重置和快进到期
- 锁定机制验证
- 解锁功能测试
- 授权状态查看

安全要求：
- 需要管理员密码验证
- 仅在开发/测试环境启用
- 所有操作记录日志

Author: Jack
Date: 2025-06-08
"""

import logging
import os
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QTextEdit, QMessageBox, QSpinBox,
    QTabWidget, QWidget, QCheckBox, QFrame, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon

logger = logging.getLogger(__name__)


class LicenseDebugDialog(QDialog):
    """授权调试对话框"""
    
    # 信号定义
    license_status_changed = pyqtSignal()  # 授权状态变更信号
    
    def __init__(self, config_manager=None, parent=None):
        """
        初始化授权调试对话框
        
        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.license_manager = None
        self.is_authenticated = False
        
        # 检查是否允许调试功能
        if not self._is_debug_enabled():
            QMessageBox.warning(
                parent, 
                "功能不可用", 
                "调试功能仅在开发/测试环境中可用。\n\n生产环境中此功能已禁用。"
            )
            self.reject()
            return
        
        self._init_license_manager()
        self._init_ui()
        
        logger.debug("授权调试对话框初始化完成")
    
    def _is_debug_enabled(self) -> bool:
        """检查是否启用调试功能"""
        try:
            # 检查环境变量
            if os.getenv('JCY5001_DEBUG_MODE') == '1':
                return True
            
            # 检查配置文件
            if self.config_manager:
                try:
                    debug_config = self.config_manager.get('debug', {})
                    if debug_config.get('enable_license_debug', False):
                        return True
                except AttributeError:
                    # 如果config_manager没有get方法，尝试其他方法
                    logger.debug("ConfigManager没有get方法，跳过配置文件检查")
            
            # 检查是否存在调试标记文件
            debug_file = os.path.join(os.path.dirname(__file__), '..', '..', '.debug_mode')
            if os.path.exists(debug_file):
                return True
            
            # 默认禁用
            return False
            
        except Exception as e:
            logger.error(f"检查调试模式失败: {e}")
            return False
    
    def _init_license_manager(self):
        """初始化授权管理器"""
        try:
            from utils.license_manager import LicenseManager
            self.license_manager = LicenseManager(self.config_manager)
        except Exception as e:
            logger.error(f"初始化授权管理器失败: {e}")
    
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("JCY5001AS - 授权调试工具（开发专用）")
        self.setFixedSize(800, 700)
        self.setModal(True)
        
        # 设置窗口图标
        try:
            self.setWindowIcon(QIcon("resources/icons/debug.png"))
        except:
            pass
        
        # 应用样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 12pt;
                color: #2c3e50;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #e74c3c;
            }
            QLineEdit, QTextEdit {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 8px;
                font-size: 11pt;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #3498db;
            }
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 10pt;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            QPushButton.success {
                background-color: #27ae60;
            }
            QPushButton.success:hover {
                background-color: #229954;
            }
            QPushButton.warning {
                background-color: #f39c12;
            }
            QPushButton.warning:hover {
                background-color: #e67e22;
            }
        """)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题和警告
        self._create_header(main_layout)
        
        # 身份验证区域
        self._create_auth_section(main_layout)
        
        # 调试功能选项卡
        self._create_debug_tabs(main_layout)
        
        # 底部按钮
        self._create_buttons(main_layout)
        
        # 初始状态
        self._update_ui_state()
    
    def _create_header(self, main_layout):
        """创建标题和警告区域"""
        # 标题
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #e74c3c; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # 警告标签
        warning_label = QLabel("⚠️ 开发专用工具 - 仅用于测试授权机制")
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_label.setStyleSheet("""
            color: #e74c3c;
            font-weight: bold;
            font-size: 11pt;
            background-color: #fdf2f2;
            border: 2px solid #e74c3c;
            border-radius: 5px;
            padding: 8px;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(warning_label)
    
    def _create_auth_section(self, main_layout):
        """创建身份验证区域"""
        auth_group = QGroupBox("身份验证")
        auth_layout = QHBoxLayout(auth_group)
        
        # 密码输入
        password_label = QLabel("管理员密码:")
        password_label.setMinimumWidth(100)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("请输入管理员密码")
        self.password_input.returnPressed.connect(self._authenticate)
        
        # 验证按钮
        self.auth_button = QPushButton("🔐 验证身份")
        self.auth_button.clicked.connect(self._authenticate)
        
        auth_layout.addWidget(password_label)
        auth_layout.addWidget(self.password_input)
        auth_layout.addWidget(self.auth_button)
        
        main_layout.addWidget(auth_group)
    
    def _create_debug_tabs(self, main_layout):
        """创建调试功能选项卡"""
        self.tab_widget = QTabWidget()
        
        # 试用期调试选项卡
        self._create_trial_debug_tab()
        
        # 锁定机制验证选项卡
        self._create_lock_test_tab()
        
        # 解锁功能测试选项卡
        self._create_unlock_test_tab()
        
        # 授权状态查看选项卡
        self._create_status_view_tab()
        
        main_layout.addWidget(self.tab_widget)
    
    def _create_trial_debug_tab(self):
        """创建试用期调试选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 重置试用期
        reset_group = QGroupBox("重置试用期")
        reset_layout = QVBoxLayout(reset_group)
        
        days_layout = QHBoxLayout()
        days_label = QLabel("试用天数:")
        self.trial_days_spinbox = QSpinBox()
        self.trial_days_spinbox.setRange(1, 365)
        self.trial_days_spinbox.setValue(30)
        self.trial_days_spinbox.setSuffix(" 天")
        
        self.reset_trial_button = QPushButton("🔄 重置试用期")
        self.reset_trial_button.clicked.connect(self._reset_trial_period)
        self.reset_trial_button.setProperty("class", "warning")
        
        days_layout.addWidget(days_label)
        days_layout.addWidget(self.trial_days_spinbox)
        days_layout.addStretch()
        days_layout.addWidget(self.reset_trial_button)
        
        reset_layout.addLayout(days_layout)
        layout.addWidget(reset_group)
        
        # 快进到期
        expire_group = QGroupBox("快进到期")
        expire_layout = QVBoxLayout(expire_group)
        
        expire_layout.addWidget(QLabel("将试用期设置为即将到期状态，用于测试到期处理逻辑"))
        
        minutes_layout = QHBoxLayout()
        minutes_label = QLabel("剩余时间:")
        self.expire_minutes_spinbox = QSpinBox()
        self.expire_minutes_spinbox.setRange(1, 60)
        self.expire_minutes_spinbox.setValue(5)
        self.expire_minutes_spinbox.setSuffix(" 分钟")
        
        self.quick_expire_button = QPushButton("⏰ 快进到期")
        self.quick_expire_button.clicked.connect(self._quick_expire)
        self.quick_expire_button.setProperty("class", "warning")
        
        minutes_layout.addWidget(minutes_label)
        minutes_layout.addWidget(self.expire_minutes_spinbox)
        minutes_layout.addStretch()
        minutes_layout.addWidget(self.quick_expire_button)
        
        expire_layout.addLayout(minutes_layout)
        layout.addWidget(expire_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "试用期调试")

    def _create_lock_test_tab(self):
        """创建锁定机制验证选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # 锁定状态测试
        lock_group = QGroupBox("锁定机制验证")
        lock_layout = QVBoxLayout(lock_group)

        lock_layout.addWidget(QLabel("测试软件在试用期到期后的锁定行为"))

        test_layout = QHBoxLayout()
        self.test_lock_button = QPushButton("🔒 测试锁定机制")
        self.test_lock_button.clicked.connect(self._test_lock_mechanism)

        self.verify_restrictions_button = QPushButton("🔍 验证功能限制")
        self.verify_restrictions_button.clicked.connect(self._verify_restrictions)

        test_layout.addWidget(self.test_lock_button)
        test_layout.addWidget(self.verify_restrictions_button)
        test_layout.addStretch()

        lock_layout.addLayout(test_layout)
        layout.addWidget(lock_group)

        # 测试结果显示
        result_group = QGroupBox("测试结果")
        result_layout = QVBoxLayout(result_group)

        self.lock_test_result = QTextEdit()
        self.lock_test_result.setMaximumHeight(200)
        self.lock_test_result.setReadOnly(True)
        self.lock_test_result.setPlaceholderText("锁定机制测试结果将显示在这里...")

        result_layout.addWidget(self.lock_test_result)
        layout.addWidget(result_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "锁定机制验证")

    def _create_unlock_test_tab(self):
        """创建解锁功能测试选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # 解锁码测试
        unlock_group = QGroupBox("解锁功能测试")
        unlock_layout = QVBoxLayout(unlock_group)

        # 测试解锁码输入
        code_layout = QVBoxLayout()
        code_label = QLabel("测试解锁码:")

        self.test_unlock_code_input = QLineEdit()
        self.test_unlock_code_input.setPlaceholderText("输入解锁码进行测试...")

        code_layout.addWidget(code_label)
        code_layout.addWidget(self.test_unlock_code_input)
        unlock_layout.addLayout(code_layout)

        # 测试按钮
        test_buttons_layout = QHBoxLayout()

        self.verify_code_button = QPushButton("🔍 验证解锁码")
        self.verify_code_button.clicked.connect(self._verify_unlock_code)

        self.test_unlock_button = QPushButton("🔓 测试解锁")
        self.test_unlock_button.clicked.connect(self._test_unlock)

        test_buttons_layout.addWidget(self.verify_code_button)
        test_buttons_layout.addWidget(self.test_unlock_button)
        test_buttons_layout.addStretch()

        unlock_layout.addLayout(test_buttons_layout)
        layout.addWidget(unlock_group)

        # 解锁测试结果
        unlock_result_group = QGroupBox("解锁测试结果")
        unlock_result_layout = QVBoxLayout(unlock_result_group)

        self.unlock_test_result = QTextEdit()
        self.unlock_test_result.setMaximumHeight(200)
        self.unlock_test_result.setReadOnly(True)
        self.unlock_test_result.setPlaceholderText("解锁测试结果将显示在这里...")

        unlock_result_layout.addWidget(self.unlock_test_result)
        layout.addWidget(unlock_result_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "解锁功能测试")

    def _create_status_view_tab(self):
        """创建授权状态查看选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # 当前状态显示
        status_group = QGroupBox("当前授权状态")
        status_layout = QVBoxLayout(status_group)

        # 刷新按钮
        refresh_layout = QHBoxLayout()
        self.refresh_status_button = QPushButton("🔄 刷新状态")
        self.refresh_status_button.clicked.connect(self._refresh_status)
        self.refresh_status_button.setProperty("class", "success")

        refresh_layout.addWidget(self.refresh_status_button)
        refresh_layout.addStretch()
        status_layout.addLayout(refresh_layout)

        # 状态显示区域
        self.status_display = QTextEdit()
        self.status_display.setMinimumHeight(300)
        self.status_display.setReadOnly(True)
        self.status_display.setPlaceholderText("点击刷新按钮查看当前授权状态...")

        status_layout.addWidget(self.status_display)
        layout.addWidget(status_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "授权状态查看")

    def _create_buttons(self, main_layout):
        """创建底部按钮"""
        button_layout = QHBoxLayout()

        # 清除日志按钮
        self.clear_log_button = QPushButton("🗑️ 清除日志")
        self.clear_log_button.clicked.connect(self._clear_debug_log)
        self.clear_log_button.setProperty("class", "warning")

        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)

        button_layout.addWidget(self.clear_log_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        main_layout.addLayout(button_layout)

    def _update_ui_state(self):
        """更新UI状态"""
        # 根据身份验证状态启用/禁用功能
        self.tab_widget.setEnabled(self.is_authenticated)
        self.clear_log_button.setEnabled(self.is_authenticated)

        if self.is_authenticated:
            self.auth_button.setText("✅ 已验证")
            self.auth_button.setProperty("class", "success")
            self.auth_button.setEnabled(False)
            self.password_input.setEnabled(False)
        else:
            self.auth_button.setText("🔐 验证身份")
            self.auth_button.setProperty("class", "")
            self.auth_button.setEnabled(True)
            self.password_input.setEnabled(True)

        # 刷新样式
        self.auth_button.style().unpolish(self.auth_button)
        self.auth_button.style().polish(self.auth_button)

    def _authenticate(self):
        """身份验证"""
        try:
            password = self.password_input.text().strip()

            if not password:
                QMessageBox.warning(self, "输入错误", "请输入管理员密码")
                return

            # 验证管理员密码
            if password == "JCY5001-ADMIN":
                self.is_authenticated = True
                self._update_ui_state()
                self._refresh_status()  # 自动刷新状态

                # 记录验证日志
                self._log_debug_operation("身份验证", "管理员身份验证成功")

                QMessageBox.information(self, "验证成功", "管理员身份验证成功！\n\n调试功能已启用。")
            else:
                QMessageBox.warning(self, "验证失败", "管理员密码错误！")
                self.password_input.clear()
                self.password_input.setFocus()

                # 记录失败日志
                self._log_debug_operation("身份验证", "管理员密码验证失败")

        except Exception as e:
            logger.error(f"身份验证失败: {e}")
            QMessageBox.critical(self, "验证错误", f"身份验证过程出错：\n\n{e}")

    def _reset_trial_period(self):
        """重置试用期"""
        try:
            if not self.is_authenticated:
                QMessageBox.warning(self, "权限不足", "请先进行身份验证")
                return

            if not self.license_manager:
                QMessageBox.critical(self, "错误", "授权管理器未初始化")
                return

            # 确认操作
            trial_days = self.trial_days_spinbox.value()
            reply = QMessageBox.question(
                self,
                "确认重置",
                f"确定要重置试用期为 {trial_days} 天吗？\n\n"
                "此操作将清除当前授权状态并重新开始试用期。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 执行重置
            success = self.license_manager.reset_trial_period(trial_days, "JCY5001-ADMIN")

            if success:
                self._log_debug_operation("重置试用期", f"试用期重置为 {trial_days} 天")
                QMessageBox.information(
                    self,
                    "重置成功",
                    f"试用期已重置为 {trial_days} 天！\n\n请重启软件以使更改生效。"
                )

                # 发送状态变更信号
                self.license_status_changed.emit()

                # 自动刷新状态
                self._refresh_status()
            else:
                QMessageBox.warning(self, "重置失败", "试用期重置失败，请检查日志获取详细信息。")

        except Exception as e:
            logger.error(f"重置试用期失败: {e}")
            QMessageBox.critical(self, "重置错误", f"重置试用期时发生错误：\n\n{e}")

    def _quick_expire(self):
        """快进到期"""
        try:
            if not self.is_authenticated:
                QMessageBox.warning(self, "权限不足", "请先进行身份验证")
                return

            if not self.license_manager:
                QMessageBox.critical(self, "错误", "授权管理器未初始化")
                return

            # 确认操作
            minutes = self.expire_minutes_spinbox.value()
            reply = QMessageBox.question(
                self,
                "确认快进",
                f"确定要将试用期设置为 {minutes} 分钟后到期吗？\n\n"
                "此操作用于测试到期处理逻辑。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 执行快进
            success = self.license_manager.set_trial_expire_soon(minutes, "JCY5001-ADMIN")

            if success:
                self._log_debug_operation("快进到期", f"试用期设置为 {minutes} 分钟后到期")
                QMessageBox.information(
                    self,
                    "设置成功",
                    f"试用期已设置为 {minutes} 分钟后到期！\n\n"
                    "可以用于测试到期处理逻辑。"
                )

                # 发送状态变更信号
                self.license_status_changed.emit()

                # 自动刷新状态
                self._refresh_status()
            else:
                QMessageBox.warning(self, "设置失败", "快进到期设置失败，请检查日志获取详细信息。")

        except Exception as e:
            logger.error(f"快进到期失败: {e}")
            QMessageBox.critical(self, "设置错误", f"快进到期时发生错误：\n\n{e}")

    def _test_lock_mechanism(self):
        """测试锁定机制"""
        try:
            if not self.is_authenticated:
                QMessageBox.warning(self, "权限不足", "请先进行身份验证")
                return

            if not self.license_manager:
                QMessageBox.critical(self, "错误", "授权管理器未初始化")
                return

            # 获取当前授权状态
            status = self.license_manager.get_license_status()

            result_text = "🔒 锁定机制测试结果\n"
            result_text += "=" * 40 + "\n\n"

            # 检查当前状态
            result_text += f"当前授权状态: {'已授权' if status.get('is_licensed', False) else '未授权'}\n"
            result_text += f"试用期状态: {'已过期' if status.get('is_trial_expired', False) else '有效'}\n"
            result_text += f"剩余天数: {status.get('remaining_days', 0)} 天\n\n"

            # 测试锁定逻辑
            is_locked = status.get('is_trial_expired', False) and not status.get('is_licensed', False)

            if is_locked:
                result_text += "✅ 锁定机制正常工作\n"
                result_text += "- 试用期已过期且软件未授权\n"
                result_text += "- 软件应该处于锁定状态\n"
                result_text += "- 用户应该只能访问解锁功能\n"
            else:
                result_text += "ℹ️ 软件当前未锁定\n"
                if status.get('is_licensed', False):
                    result_text += "- 软件已正式授权\n"
                elif not status.get('is_trial_expired', False):
                    result_text += "- 试用期仍然有效\n"
                result_text += "- 所有功能应该可以正常使用\n"

            result_text += f"\n测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

            self.lock_test_result.setText(result_text)
            self._log_debug_operation("锁定机制测试", f"锁定状态: {is_locked}")

        except Exception as e:
            logger.error(f"测试锁定机制失败: {e}")
            self.lock_test_result.setText(f"❌ 测试失败: {e}")

    def _verify_restrictions(self):
        """验证功能限制"""
        try:
            if not self.is_authenticated:
                QMessageBox.warning(self, "权限不足", "请先进行身份验证")
                return

            result_text = "🔍 功能限制验证结果\n"
            result_text += "=" * 40 + "\n\n"

            # 这里可以添加具体的功能限制检查
            # 例如检查主界面的按钮状态、菜单可用性等

            result_text += "验证项目:\n"
            result_text += "- 测试按钮状态: 需要在主界面中实现\n"
            result_text += "- 菜单项可用性: 需要在主界面中实现\n"
            result_text += "- 功能模块访问: 需要在各模块中实现\n\n"

            result_text += "建议:\n"
            result_text += "- 在主界面中添加锁定状态检查\n"
            result_text += "- 在关键功能入口添加授权验证\n"
            result_text += "- 显示适当的锁定提示信息\n"

            result_text += f"\n验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

            self.lock_test_result.setText(result_text)
            self._log_debug_operation("功能限制验证", "验证完成")

        except Exception as e:
            logger.error(f"验证功能限制失败: {e}")
            self.lock_test_result.setText(f"❌ 验证失败: {e}")

    def _verify_unlock_code(self):
        """验证解锁码"""
        try:
            if not self.is_authenticated:
                QMessageBox.warning(self, "权限不足", "请先进行身份验证")
                return

            if not self.license_manager:
                QMessageBox.critical(self, "错误", "授权管理器未初始化")
                return

            unlock_code = self.test_unlock_code_input.text().strip()
            if not unlock_code:
                QMessageBox.warning(self, "输入错误", "请输入解锁码")
                return

            # 验证解锁码
            result = self.license_manager.verify_unlock_code(unlock_code)

            result_text = "🔍 解锁码验证结果\n"
            result_text += "=" * 40 + "\n\n"

            if result.get('success', False):
                result_text += "✅ 解锁码验证成功\n\n"
                result_text += f"解锁类型: {result.get('unlock_type', 'unknown')}\n"

                extend_days = result.get('extend_days', 0)
                if extend_days > 0:
                    result_text += f"延长天数: {extend_days} 天\n"

                result_text += f"验证消息: {result.get('message', '')}\n"
            else:
                result_text += "❌ 解锁码验证失败\n\n"
                result_text += f"失败原因: {result.get('message', '未知错误')}\n"

            result_text += f"\n验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

            self.unlock_test_result.setText(result_text)
            self._log_debug_operation("解锁码验证", f"结果: {result.get('success', False)}")

        except Exception as e:
            logger.error(f"验证解锁码失败: {e}")
            self.unlock_test_result.setText(f"❌ 验证失败: {e}")

    def _test_unlock(self):
        """测试解锁"""
        try:
            if not self.is_authenticated:
                QMessageBox.warning(self, "权限不足", "请先进行身份验证")
                return

            if not self.license_manager:
                QMessageBox.critical(self, "错误", "授权管理器未初始化")
                return

            unlock_code = self.test_unlock_code_input.text().strip()
            if not unlock_code:
                QMessageBox.warning(self, "输入错误", "请输入解锁码")
                return

            # 确认操作
            reply = QMessageBox.question(
                self,
                "确认解锁",
                "确定要使用此解锁码进行解锁测试吗？\n\n"
                "此操作将修改当前的授权状态。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 执行解锁
            result = self.license_manager.unlock_with_code(unlock_code)

            result_text = "🔓 解锁测试结果\n"
            result_text += "=" * 40 + "\n\n"

            if result.get('success', False):
                result_text += "✅ 解锁成功\n\n"
                result_text += f"解锁类型: {result.get('unlock_type', 'unknown')}\n"
                result_text += f"解锁消息: {result.get('message', '')}\n\n"

                # 显示新的授权状态
                license_status = result.get('license_status', {})
                result_text += "新的授权状态:\n"
                result_text += f"- 已授权: {'是' if license_status.get('is_licensed', False) else '否'}\n"
                result_text += f"- 试用期过期: {'是' if license_status.get('is_trial_expired', False) else '否'}\n"
                result_text += f"- 剩余天数: {license_status.get('remaining_days', 0)} 天\n"

                # 发送状态变更信号
                self.license_status_changed.emit()

            else:
                result_text += "❌ 解锁失败\n\n"
                result_text += f"失败原因: {result.get('message', '未知错误')}\n"

            result_text += f"\n测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

            self.unlock_test_result.setText(result_text)
            self._log_debug_operation("解锁测试", f"结果: {result.get('success', False)}")

            # 自动刷新状态
            self._refresh_status()

        except Exception as e:
            logger.error(f"测试解锁失败: {e}")
            self.unlock_test_result.setText(f"❌ 测试失败: {e}")

    def _refresh_status(self):
        """刷新授权状态"""
        try:
            if not self.license_manager:
                self.status_display.setText("❌ 授权管理器未初始化")
                return

            # 获取详细状态信息
            status = self.license_manager.get_license_status()
            hardware_fingerprint = self.license_manager.get_hardware_fingerprint()

            status_text = "📊 当前授权状态详情\n"
            status_text += "=" * 50 + "\n\n"

            # 基本信息
            status_text += "基本信息:\n"
            status_text += f"- 软件已授权: {'是' if status.get('is_licensed', False) else '否'}\n"
            status_text += f"- 授权类型: {status.get('license_type', 'unknown')}\n"
            status_text += f"- 试用期过期: {'是' if status.get('is_trial_expired', False) else '否'}\n"
            status_text += f"- 剩余天数: {status.get('remaining_days', 0)} 天\n"
            status_text += f"- 总试用天数: {status.get('trial_days', 0)} 天\n\n"

            # 时间信息
            expire_date = status.get('expire_date')
            if expire_date:
                try:
                    from datetime import datetime
                    expire_dt = datetime.fromisoformat(expire_date)
                    status_text += f"- 到期时间: {expire_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                except:
                    status_text += f"- 到期时间: {expire_date}\n"

            status_text += "\n"

            # 硬件信息
            status_text += "硬件信息:\n"
            status_text += f"- 硬件指纹: {hardware_fingerprint[:16]}...\n"
            status_text += f"- 完整指纹: {hardware_fingerprint}\n\n"

            # 锁定状态判断
            is_locked = status.get('is_trial_expired', False) and not status.get('is_licensed', False)
            status_text += "锁定状态:\n"
            status_text += f"- 软件锁定: {'是' if is_locked else '否'}\n"

            if is_locked:
                status_text += "- 锁定原因: 试用期已过期且未授权\n"
                status_text += "- 建议操作: 使用解锁码进行授权\n"
            else:
                if status.get('is_licensed', False):
                    status_text += "- 状态说明: 软件已正式授权\n"
                else:
                    status_text += "- 状态说明: 试用期内，功能正常\n"

            status_text += f"\n刷新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

            self.status_display.setText(status_text)
            self._log_debug_operation("状态刷新", "授权状态已刷新")

        except Exception as e:
            logger.error(f"刷新状态失败: {e}")
            self.status_display.setText(f"❌ 刷新失败: {e}")

    def _clear_debug_log(self):
        """清除调试日志"""
        try:
            if not self.is_authenticated:
                QMessageBox.warning(self, "权限不足", "请先进行身份验证")
                return

            reply = QMessageBox.question(
                self,
                "确认清除",
                "确定要清除所有调试日志吗？\n\n此操作不可撤销。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 清除各个显示区域
            self.lock_test_result.clear()
            self.unlock_test_result.clear()
            self.status_display.clear()

            # 记录清除操作
            self._log_debug_operation("清除日志", "所有调试日志已清除")

            QMessageBox.information(self, "清除完成", "调试日志已清除")

        except Exception as e:
            logger.error(f"清除调试日志失败: {e}")
            QMessageBox.critical(self, "清除错误", f"清除调试日志时发生错误：\n\n{e}")

    def _log_debug_operation(self, operation: str, details: str):
        """记录调试操作日志"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'operation': operation,
                'details': details,
                'user': 'debug_admin'
            }

            # 记录到主日志
            logger.warning(f"调试操作 - {operation}: {details}")

            # 如果授权管理器可用，也记录到授权日志
            if self.license_manager and hasattr(self.license_manager, '_log_operation'):
                self.license_manager._log_operation(log_entry)

        except Exception as e:
            logger.error(f"记录调试日志失败: {e}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            if self.is_authenticated:
                self._log_debug_operation("关闭调试工具", "授权调试工具已关闭")

            event.accept()

        except Exception as e:
            logger.error(f"关闭事件处理失败: {e}")
            event.accept()
