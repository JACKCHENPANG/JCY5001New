# -*- coding: utf-8 -*-
"""
试用期管理组件
用于开发和测试目的的试用期管理功能

Author: Jack
Date: 2025-01-27
"""

import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QLabel, QSpinBox, QPushButton, QTextEdit, 
                             QMessageBox, QInputDialog, QCheckBox, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont, QIcon
from utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class TrialManagementWidget(QWidget):
    """试用期管理组件"""
    
    # 信号定义
    settings_changed = pyqtSignal()
    trial_reset = pyqtSignal()  # 试用期重置信号
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        初始化试用期管理组件
        
        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.license_manager = None
        
        # 初始化授权管理器
        self._init_license_manager()
        
        # 初始化界面
        self._init_ui()
        self._init_connections()
        self._load_settings()
        
        logger.debug("试用期管理组件初始化完成")
    
    def _init_license_manager(self):
        """初始化授权管理器"""
        try:
            from utils.license_manager import LicenseManager
            self.license_manager = LicenseManager(self.config_manager)
            logger.debug("授权管理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化授权管理器失败: {e}")
            self.license_manager = None
    
    def _init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 添加警告信息
        warning_frame = self._create_warning_frame()
        main_layout.addWidget(warning_frame)
        
        # 创建调试模式开关
        debug_group = self._create_debug_mode_group()
        main_layout.addWidget(debug_group)
        
        # 创建试用期管理组
        trial_group = self._create_trial_management_group()
        main_layout.addWidget(trial_group)
        
        # 创建测试功能组
        test_group = self._create_test_functions_group()
        main_layout.addWidget(test_group)
        
        # 创建状态信息组
        status_group = self._create_status_info_group()
        main_layout.addWidget(status_group)
        
        # 添加弹性空间
        main_layout.addStretch()
    
    def _create_warning_frame(self) -> QFrame:
        """创建警告信息框"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Box)
        frame.setStyleSheet("""
            QFrame {
                background-color: #fff3cd;
                border: 2px solid #ffc107;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        # 警告标题
        title_label = QLabel("⚠️ 开发/测试功能警告")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #856404;")
        layout.addWidget(title_label)
        
        # 警告内容
        warning_text = """
此页面包含的功能仅用于开发和测试目的，请勿在生产环境中使用！

• 所有操作都需要管理员密码验证
• 操作记录将被详细记录在日志中
• 误用这些功能可能导致授权状态异常
• 建议仅在受控的测试环境中使用
        """
        
        content_label = QLabel(warning_text.strip())
        content_label.setStyleSheet("color: #856404;")
        content_label.setWordWrap(True)
        layout.addWidget(content_label)
        
        return frame
    
    def _create_debug_mode_group(self) -> QGroupBox:
        """创建调试模式组"""
        group = QGroupBox("调试模式设置")
        group.setFont(QFont("", 10, QFont.Bold))
        
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # 调试模式开关
        self.debug_mode_checkbox = QCheckBox("启用调试模式")
        self.debug_mode_checkbox.setToolTip("启用后将显示试用期管理功能，并启用详细日志记录")
        layout.addWidget(self.debug_mode_checkbox)
        
        # 说明文字
        info_label = QLabel("启用调试模式后，试用期管理功能才会生效。\n生产环境建议保持关闭状态。")
        info_label.setStyleSheet("color: #666666; font-size: 9pt;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        return group
    
    def _create_trial_management_group(self) -> QGroupBox:
        """创建试用期管理组"""
        group = QGroupBox("试用期管理")
        group.setFont(QFont("", 10, QFont.Bold))
        
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        
        # 试用天数设置
        days_layout = QHBoxLayout()
        days_layout.addWidget(QLabel("试用天数:"))
        
        self.trial_days_spin = QSpinBox()
        self.trial_days_spin.setRange(1, 365)
        self.trial_days_spin.setValue(30)
        self.trial_days_spin.setSuffix(" 天")
        days_layout.addWidget(self.trial_days_spin)
        
        days_layout.addStretch()
        layout.addLayout(days_layout)
        
        # 重置试用期按钮
        self.reset_trial_button = QPushButton("🔄 重置试用期")
        self.reset_trial_button.setToolTip("重置试用期到指定天数，需要管理员密码")
        layout.addWidget(self.reset_trial_button)
        
        # 恢复试用状态按钮
        self.restore_trial_button = QPushButton("↩️ 恢复试用状态")
        self.restore_trial_button.setToolTip("将已授权状态重置为试用状态，需要管理员密码")
        layout.addWidget(self.restore_trial_button)
        
        return group
    
    def _create_test_functions_group(self) -> QGroupBox:
        """创建测试功能组"""
        group = QGroupBox("测试功能")
        group.setFont(QFont("", 10, QFont.Bold))
        
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # 快速到期测试
        expire_layout = QHBoxLayout()
        expire_layout.addWidget(QLabel("快速到期:"))
        
        self.expire_minutes_spin = QSpinBox()
        self.expire_minutes_spin.setRange(1, 60)
        self.expire_minutes_spin.setValue(1)
        self.expire_minutes_spin.setSuffix(" 分钟")
        expire_layout.addWidget(self.expire_minutes_spin)
        
        self.quick_expire_button = QPushButton("⏰ 设置快速到期")
        self.quick_expire_button.setToolTip("设置试用期在指定分钟后到期，用于测试锁定功能")
        expire_layout.addWidget(self.quick_expire_button)
        
        expire_layout.addStretch()
        layout.addLayout(expire_layout)
        
        # 模拟到期按钮
        simulate_layout = QHBoxLayout()
        self.simulate_expire_button = QPushButton("🎭 模拟到期状态")
        self.simulate_expire_button.setToolTip("模拟试用期到期状态，不修改实际数据")
        simulate_layout.addWidget(self.simulate_expire_button)
        
        self.clear_simulation_button = QPushButton("🔄 清除模拟")
        self.clear_simulation_button.setToolTip("清除模拟状态，恢复正常")
        simulate_layout.addWidget(self.clear_simulation_button)
        
        simulate_layout.addStretch()
        layout.addLayout(simulate_layout)
        
        return group
    
    def _create_status_info_group(self) -> QGroupBox:
        """创建状态信息组"""
        group = QGroupBox("管理信息")
        group.setFont(QFont("", 10, QFont.Bold))
        
        layout = QVBoxLayout(group)
        
        # 状态信息显示
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(120)
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9pt;
            }
        """)
        layout.addWidget(self.status_text)
        
        # 刷新按钮
        self.refresh_status_button = QPushButton("🔄 刷新状态")
        layout.addWidget(self.refresh_status_button)
        
        return group
    
    def _init_connections(self):
        """初始化信号连接"""
        # 调试模式开关
        self.debug_mode_checkbox.toggled.connect(self._on_debug_mode_changed)
        
        # 试用期管理按钮
        self.reset_trial_button.clicked.connect(self._on_reset_trial_clicked)
        self.restore_trial_button.clicked.connect(self._on_restore_trial_clicked)
        
        # 测试功能按钮
        self.quick_expire_button.clicked.connect(self._on_quick_expire_clicked)
        self.simulate_expire_button.clicked.connect(self._on_simulate_expire_clicked)
        self.clear_simulation_button.clicked.connect(self._on_clear_simulation_clicked)
        
        # 状态刷新按钮
        self.refresh_status_button.clicked.connect(self._refresh_status_info)
        
        # 数值变化
        self.trial_days_spin.valueChanged.connect(self._on_setting_changed)
        self.expire_minutes_spin.valueChanged.connect(self._on_setting_changed)
    
    def _load_settings(self):
        """加载设置"""
        try:
            # 加载调试模式设置
            debug_mode = self.config_manager.get('debug.trial_management_enabled', False)
            self.debug_mode_checkbox.setChecked(debug_mode)
            
            # 加载试用天数设置
            trial_days = self.config_manager.get('app.trial_days', 30)
            self.trial_days_spin.setValue(trial_days)
            
            # 更新UI状态
            self._update_ui_state()
            
            # 刷新状态信息
            self._refresh_status_info()
            
            logger.debug("试用期管理设置加载完成")
            
        except Exception as e:
            logger.error(f"加载试用期管理设置失败: {e}")
    
    def apply_settings(self):
        """应用设置"""
        try:
            # 保存调试模式设置
            debug_mode = self.debug_mode_checkbox.isChecked()
            self.config_manager.set('debug.trial_management_enabled', debug_mode)

            # 保存试用天数设置
            trial_days = self.trial_days_spin.value()
            self.config_manager.set('app.trial_days', trial_days)

            logger.info("试用期管理设置应用成功")

        except Exception as e:
            logger.error(f"应用试用期管理设置失败: {e}")
            raise

    def _on_debug_mode_changed(self, enabled: bool):
        """调试模式变化处理"""
        try:
            self._update_ui_state()
            self._on_setting_changed()

            if enabled:
                logger.warning("试用期管理调试模式已启用")
            else:
                logger.info("试用期管理调试模式已禁用")

        except Exception as e:
            logger.error(f"处理调试模式变化失败: {e}")

    def _update_ui_state(self):
        """更新UI状态"""
        try:
            debug_enabled = self.debug_mode_checkbox.isChecked()

            # 根据调试模式启用/禁用功能按钮
            buttons = [
                self.reset_trial_button,
                self.restore_trial_button,
                self.quick_expire_button,
                self.simulate_expire_button,
                self.clear_simulation_button
            ]

            for button in buttons:
                button.setEnabled(debug_enabled)

            # 更新试用天数输入框状态
            self.trial_days_spin.setEnabled(debug_enabled)
            self.expire_minutes_spin.setEnabled(debug_enabled)

        except Exception as e:
            logger.error(f"更新UI状态失败: {e}")

    def _on_reset_trial_clicked(self):
        """重置试用期按钮点击处理"""
        try:
            if not self.license_manager:
                QMessageBox.warning(self, "错误", "授权管理器未初始化")
                return

            # 获取管理员密码
            password, ok = QInputDialog.getText(
                self, "管理员验证",
                "请输入管理员密码:",
                QInputDialog.Password
            )

            if not ok or not password:
                return

            # 确认操作
            reply = QMessageBox.question(
                self, "确认重置",
                f"确定要重置试用期为 {self.trial_days_spin.value()} 天吗？\n\n"
                "此操作将清除当前试用期数据并重新开始计时。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 执行重置
            trial_days = self.trial_days_spin.value()
            success = self.license_manager.reset_trial_period(trial_days, password)

            if success:
                QMessageBox.information(self, "成功", f"试用期已重置为 {trial_days} 天")
                self._refresh_status_info()
                self.trial_reset.emit()  # 发送重置信号
            else:
                QMessageBox.warning(self, "失败", "重置试用期失败，请检查管理员密码")

        except Exception as e:
            logger.error(f"重置试用期失败: {e}")
            QMessageBox.critical(self, "错误", f"重置试用期失败: {e}")

    def _on_restore_trial_clicked(self):
        """恢复试用状态按钮点击处理"""
        try:
            if not self.license_manager:
                QMessageBox.warning(self, "错误", "授权管理器未初始化")
                return

            # 获取管理员密码
            password, ok = QInputDialog.getText(
                self, "管理员验证",
                "请输入管理员密码:",
                QInputDialog.Password
            )

            if not ok or not password:
                return

            # 确认操作
            reply = QMessageBox.question(
                self, "确认恢复",
                "确定要将已授权状态恢复为试用状态吗？\n\n"
                "此操作将清除授权信息并重新启用试用期倒计时。\n"
                "原始授权信息将被备份。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 执行恢复
            success = self.license_manager.restore_trial_status(password)

            if success:
                QMessageBox.information(self, "成功", "已恢复为试用状态")
                self._refresh_status_info()
                self.trial_reset.emit()  # 发送重置信号
            else:
                QMessageBox.warning(self, "失败", "恢复试用状态失败，请检查管理员密码")

        except Exception as e:
            logger.error(f"恢复试用状态失败: {e}")
            QMessageBox.critical(self, "错误", f"恢复试用状态失败: {e}")

    def _on_quick_expire_clicked(self):
        """快速到期按钮点击处理"""
        try:
            if not self.license_manager:
                QMessageBox.warning(self, "错误", "授权管理器未初始化")
                return

            # 获取管理员密码
            password, ok = QInputDialog.getText(
                self, "管理员验证",
                "请输入管理员密码:",
                QInputDialog.Password
            )

            if not ok or not password:
                return

            # 确认操作
            minutes = self.expire_minutes_spin.value()
            reply = QMessageBox.question(
                self, "确认设置",
                f"确定要设置试用期在 {minutes} 分钟后到期吗？\n\n"
                "此功能用于测试锁定机制是否正常工作。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 执行设置
            success = self.license_manager.set_trial_expire_soon(minutes, password)

            if success:
                QMessageBox.information(self, "成功", f"试用期已设置为 {minutes} 分钟后到期")
                self._refresh_status_info()
            else:
                QMessageBox.warning(self, "失败", "设置快速到期失败，请检查管理员密码或当前状态")

        except Exception as e:
            logger.error(f"设置快速到期失败: {e}")
            QMessageBox.critical(self, "错误", f"设置快速到期失败: {e}")

    def _on_simulate_expire_clicked(self):
        """模拟到期按钮点击处理"""
        try:
            if not self.license_manager:
                QMessageBox.warning(self, "错误", "授权管理器未初始化")
                return

            # 确认操作
            reply = QMessageBox.question(
                self, "确认模拟",
                "确定要启用试用期到期模拟模式吗？\n\n"
                "此模式不会修改实际数据，但会模拟到期状态。\n"
                "可以用于测试到期后的界面表现。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 执行模拟
            success = self.license_manager.simulate_trial_expired()

            if success:
                QMessageBox.information(self, "成功", "已启用试用期到期模拟模式")
                self._refresh_status_info()
            else:
                QMessageBox.warning(self, "失败", "启用模拟模式失败")

        except Exception as e:
            logger.error(f"启用模拟模式失败: {e}")
            QMessageBox.critical(self, "错误", f"启用模拟模式失败: {e}")

    def _on_clear_simulation_clicked(self):
        """清除模拟按钮点击处理"""
        try:
            if not self.license_manager:
                QMessageBox.warning(self, "错误", "授权管理器未初始化")
                return

            # 执行清除
            success = self.license_manager.clear_simulation_mode()

            if success:
                QMessageBox.information(self, "成功", "已清除模拟模式")
                self._refresh_status_info()
            else:
                QMessageBox.warning(self, "失败", "清除模拟模式失败")

        except Exception as e:
            logger.error(f"清除模拟模式失败: {e}")
            QMessageBox.critical(self, "错误", f"清除模拟模式失败: {e}")

    def _refresh_status_info(self):
        """刷新状态信息"""
        try:
            if not self.license_manager:
                self.status_text.setText("授权管理器未初始化")
                return

            # 获取授权状态
            license_status = self.license_manager.get_license_status()
            management_info = self.license_manager.get_trial_management_info()

            # 构建状态信息
            status_lines = []
            status_lines.append("=== 当前授权状态 ===")
            status_lines.append(f"授权状态: {'已授权' if license_status.get('is_licensed') else '试用期'}")
            status_lines.append(f"试用期状态: {'已到期' if license_status.get('is_trial_expired') else '有效'}")
            status_lines.append(f"剩余天数: {license_status.get('remaining_days', 0)}")
            status_lines.append(f"试用天数: {license_status.get('trial_days', 0)}")
            status_lines.append(f"授权类型: {license_status.get('license_type', 'unknown')}")

            if license_status.get('expire_date'):
                status_lines.append(f"到期时间: {license_status['expire_date'][:19]}")

            status_lines.append("")
            status_lines.append("=== 管理操作记录 ===")
            status_lines.append(f"重置次数: {management_info.get('reset_count', 0)}")
            status_lines.append(f"恢复次数: {management_info.get('restore_count', 0)}")

            if management_info.get('last_reset_time'):
                status_lines.append(f"最后重置: {management_info['last_reset_time'][:19]}")

            if management_info.get('last_restore_time'):
                status_lines.append(f"最后恢复: {management_info['last_restore_time'][:19]}")

            if management_info.get('quick_expire_test'):
                status_lines.append(f"快速到期测试: 已启用")
                if management_info.get('quick_expire_time'):
                    status_lines.append(f"设置时间: {management_info['quick_expire_time'][:19]}")

            if management_info.get('simulated_expired'):
                status_lines.append("模拟模式: 已启用")

            if management_info.get('has_backup'):
                status_lines.append("授权备份: 存在")

            # 显示状态信息
            self.status_text.setText("\n".join(status_lines))

        except Exception as e:
            logger.error(f"刷新状态信息失败: {e}")
            self.status_text.setText(f"刷新状态信息失败: {e}")

    def _on_setting_changed(self):
        """设置变更处理"""
        self.settings_changed.emit()
