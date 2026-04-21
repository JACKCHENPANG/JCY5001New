# -*- coding: utf-8 -*-
"""
许可证集成管理器
负责处理许可证相关的集成功能，包括试用期管理、解锁请求、授权状态检查等

Author: Jack
Date: 2025-06-27
"""

import logging
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QMessageBox, QInputDialog

logger = logging.getLogger(__name__)


class LicenseIntegrationManager(QObject):
    """许可证集成管理器"""
    
    # 信号定义
    trial_expired = pyqtSignal()  # 试用期到期信号
    unlock_requested = pyqtSignal()  # 解锁请求信号
    license_status_changed = pyqtSignal(str)  # 许可证状态变更信号 (status)
    unlock_successful = pyqtSignal()  # 解锁成功信号
    
    def __init__(self, main_window, config_manager, parent=None):
        """
        初始化许可证集成管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
            parent: 父对象
        """
        super().__init__(parent)
        
        self.main_window = main_window
        self.config_manager = config_manager
        
        # 许可证状态
        self.license_status = "unknown"
        self.trial_days_remaining = 0
        self.is_licensed = False
        
        # 检查定时器
        self.license_check_timer = QTimer()
        self.license_check_timer.timeout.connect(self._periodic_license_check)
        
    def initialize(self):
        """初始化许可证集成管理器"""
        try:
            # 连接授权管理器信号
            self._connect_authorization_manager_signals()
            
            # 启动定期检查
            check_interval = self.config_manager.get('license.check_interval_minutes', 60)
            self.license_check_timer.start(check_interval * 60 * 1000)  # 转换为毫秒
            
            logger.debug("许可证集成管理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化许可证集成管理器失败: {e}")

    def _connect_authorization_manager_signals(self):
        """连接授权管理器信号"""
        try:
            if hasattr(self.main_window, 'authorization_manager'):
                auth_manager = self.main_window.authorization_manager
                
                # 连接试用期到期信号
                if hasattr(auth_manager, 'trial_expired'):
                    auth_manager.trial_expired.connect(self._on_trial_expired)
                
                # 连接解锁请求信号
                if hasattr(auth_manager, 'unlock_requested'):
                    auth_manager.unlock_requested.connect(self._on_unlock_requested)
                
                # 连接许可证状态变更信号
                if hasattr(auth_manager, 'license_status_changed'):
                    auth_manager.license_status_changed.connect(self._on_license_status_changed)
                    
        except Exception as e:
            logger.error(f"连接授权管理器信号失败: {e}")

    def check_license_on_startup(self):
        """启动时检查授权状态"""
        try:
            logger.info("🔐 启动时检查授权状态...")
            
            # 获取许可证管理器
            license_manager = self._get_license_manager()
            if not license_manager:
                logger.warning("许可证管理器未找到")
                return
            
            # 检查授权状态
            license_info = license_manager.get_license_info()
            
            if license_info.get('is_valid', False):
                self.is_licensed = True
                self.license_status = "valid"
                logger.info("✅ 授权有效")
            elif license_info.get('is_trial', False):
                self.trial_days_remaining = license_info.get('trial_days_remaining', 0)
                self.license_status = "trial"
                logger.info(f"⏰ 试用期剩余: {self.trial_days_remaining}天")
                
                if self.trial_days_remaining <= 0:
                    self._handle_trial_expired()
                elif self.trial_days_remaining <= 7:
                    self._show_trial_warning()
            else:
                self.license_status = "expired"
                logger.warning("❌ 授权已过期")
                self._handle_license_expired()
            
            # 发送状态变更信号
            self.license_status_changed.emit(self.license_status)
            
        except Exception as e:
            logger.error(f"启动时检查授权状态失败: {e}")

    def _get_license_manager(self):
        """获取许可证管理器"""
        try:
            if hasattr(self.main_window, 'license_manager'):
                return self.main_window.license_manager
            elif hasattr(self.main_window, 'authorization_manager'):
                auth_manager = self.main_window.authorization_manager
                if hasattr(auth_manager, 'license_manager'):
                    return auth_manager.license_manager
            return None
        except Exception as e:
            logger.error(f"获取许可证管理器失败: {e}")
            return None

    def _on_trial_expired(self):
        """处理试用期到期"""
        try:
            logger.warning("⏰ 试用期已到期")
            
            self.license_status = "trial_expired"
            self.trial_days_remaining = 0
            
            # 发送试用期到期信号
            self.trial_expired.emit()
            
            # 显示试用期到期对话框
            self._show_trial_expired_dialog()
            
        except Exception as e:
            logger.error(f"处理试用期到期失败: {e}")

    def _on_unlock_requested(self):
        """处理解锁请求"""
        try:
            logger.info("🔓 收到解锁请求")
            
            # 发送解锁请求信号
            self.unlock_requested.emit()
            
            # 显示解锁对话框
            license_manager = self._get_license_manager()
            if license_manager:
                self._show_unlock_dialog(license_manager)
            else:
                logger.error("许可证管理器未找到，无法显示解锁对话框")
                
        except Exception as e:
            logger.error(f"处理解锁请求失败: {e}")

    def _on_license_status_changed(self):
        """处理授权状态变更"""
        try:
            logger.info("🔄 授权状态发生变更")
            
            # 重新检查授权状态
            self.check_license_on_startup()
            
        except Exception as e:
            logger.error(f"处理授权状态变更失败: {e}")

    def _show_trial_expired_dialog(self):
        """显示试用期到期对话框"""
        try:
            msg_box = QMessageBox(self.main_window)
            msg_box.setWindowTitle("试用期到期")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText("软件试用期已到期，请联系供应商获取正式授权。")
            msg_box.setInformativeText("您可以继续使用基本功能，但部分高级功能将被限制。")
            
            unlock_button = msg_box.addButton("立即解锁", QMessageBox.ButtonRole.AcceptRole)
            later_button = msg_box.addButton("稍后处理", QMessageBox.ButtonRole.RejectRole)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == unlock_button:
                self._on_unlock_requested()
                
        except Exception as e:
            logger.error(f"显示试用期到期对话框失败: {e}")

    def _show_trial_warning(self):
        """显示试用期警告"""
        try:
            if self.trial_days_remaining <= 3:
                # 剩余3天内每次启动都提醒
                self._show_trial_warning_dialog()
            elif self.trial_days_remaining <= 7:
                # 剩余7天内每天提醒一次
                last_warning_date = self.config_manager.get('license.last_warning_date', '')
                from datetime import datetime
                today = datetime.now().strftime('%Y-%m-%d')
                
                if last_warning_date != today:
                    self._show_trial_warning_dialog()
                    self.config_manager.set('license.last_warning_date', today)
                    
        except Exception as e:
            logger.error(f"显示试用期警告失败: {e}")

    def _show_trial_warning_dialog(self):
        """显示试用期警告对话框"""
        try:
            msg_box = QMessageBox(self.main_window)
            msg_box.setWindowTitle("试用期提醒")
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText(f"软件试用期剩余 {self.trial_days_remaining} 天")
            msg_box.setInformativeText("请及时联系供应商获取正式授权，避免影响正常使用。")
            
            unlock_button = msg_box.addButton("立即解锁", QMessageBox.ButtonRole.AcceptRole)
            ok_button = msg_box.addButton("我知道了", QMessageBox.ButtonRole.RejectRole)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == unlock_button:
                self._on_unlock_requested()
                
        except Exception as e:
            logger.error(f"显示试用期警告对话框失败: {e}")

    def _handle_license_expired(self):
        """处理许可证过期"""
        try:
            logger.warning("❌ 许可证已过期，限制功能使用")
            
            # 禁用部分功能
            self._disable_premium_features()
            
            # 显示过期提示
            self._show_license_expired_dialog()
            
        except Exception as e:
            logger.error(f"处理许可证过期失败: {e}")

    def _show_license_expired_dialog(self):
        """显示许可证过期对话框"""
        try:
            msg_box = QMessageBox(self.main_window)
            msg_box.setWindowTitle("许可证过期")
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setText("软件许可证已过期")
            msg_box.setInformativeText("请联系供应商续费或获取新的授权许可证。")
            
            unlock_button = msg_box.addButton("立即解锁", QMessageBox.ButtonRole.AcceptRole)
            ok_button = msg_box.addButton("确定", QMessageBox.ButtonRole.RejectRole)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == unlock_button:
                self._on_unlock_requested()
                
        except Exception as e:
            logger.error(f"显示许可证过期对话框失败: {e}")

    def _handle_trial_expired(self):
        """处理试用期到期"""
        try:
            logger.warning("⏰ 试用期已到期，限制功能使用")
            
            # 禁用部分功能
            self._disable_premium_features()
            
            # 显示到期提示
            self._show_trial_expired_dialog()
            
        except Exception as e:
            logger.error(f"处理试用期到期失败: {e}")

    def _disable_premium_features(self):
        """禁用高级功能"""
        try:
            # 禁用数据导出功能
            if hasattr(self.main_window, 'data_analysis_widget'):
                data_widget = self.main_window.data_analysis_widget
                if hasattr(data_widget, 'set_export_enabled'):
                    data_widget.set_export_enabled(False)
            
            # 禁用高级测试模式
            if hasattr(self.main_window, 'test_flow_manager'):
                test_manager = self.main_window.test_flow_manager
                if hasattr(test_manager, 'set_advanced_mode_enabled'):
                    test_manager.set_advanced_mode_enabled(False)
            
            logger.info("高级功能已禁用")
            
        except Exception as e:
            logger.error(f"禁用高级功能失败: {e}")

    def _show_unlock_dialog(self, license_manager):
        """显示解锁对话框"""
        try:
            unlock_code, ok = QInputDialog.getText(
                self.main_window,
                "软件解锁",
                "请输入解锁码:",
                text=""
            )
            
            if ok and unlock_code:
                # 验证解锁码
                if license_manager.validate_unlock_code(unlock_code):
                    self._on_unlock_successful()
                else:
                    QMessageBox.warning(
                        self.main_window,
                        "解锁失败",
                        "解锁码无效，请检查后重试。"
                    )
                    
        except Exception as e:
            logger.error(f"显示解锁对话框失败: {e}")

    def _on_unlock_successful(self):
        """处理解锁成功"""
        try:
            logger.info("🎉 软件解锁成功")
            
            self.is_licensed = True
            self.license_status = "valid"
            
            # 发送解锁成功信号
            self.unlock_successful.emit()
            
            # 启用所有功能
            self._enable_all_features()
            
            # 显示成功消息
            QMessageBox.information(
                self.main_window,
                "解锁成功",
                "软件已成功解锁，所有功能现已可用。"
            )
            
            # 发送状态变更信号
            self.license_status_changed.emit(self.license_status)
            
        except Exception as e:
            logger.error(f"处理解锁成功失败: {e}")

    def _enable_all_features(self):
        """启用所有功能"""
        try:
            # 启用数据导出功能
            if hasattr(self.main_window, 'data_analysis_widget'):
                data_widget = self.main_window.data_analysis_widget
                if hasattr(data_widget, 'set_export_enabled'):
                    data_widget.set_export_enabled(True)
            
            # 启用高级测试模式
            if hasattr(self.main_window, 'test_flow_manager'):
                test_manager = self.main_window.test_flow_manager
                if hasattr(test_manager, 'set_advanced_mode_enabled'):
                    test_manager.set_advanced_mode_enabled(True)
            
            logger.info("所有功能已启用")
            
        except Exception as e:
            logger.error(f"启用所有功能失败: {e}")

    def _periodic_license_check(self):
        """定期许可证检查"""
        try:
            logger.debug("执行定期许可证检查")
            
            license_manager = self._get_license_manager()
            if license_manager:
                license_info = license_manager.get_license_info()
                
                # 检查状态是否发生变化
                old_status = self.license_status
                
                if license_info.get('is_valid', False):
                    self.license_status = "valid"
                    self.is_licensed = True
                elif license_info.get('is_trial', False):
                    self.license_status = "trial"
                    self.trial_days_remaining = license_info.get('trial_days_remaining', 0)
                    
                    if self.trial_days_remaining <= 0:
                        self._handle_trial_expired()
                else:
                    self.license_status = "expired"
                    self.is_licensed = False
                
                # 如果状态发生变化，发送信号
                if old_status != self.license_status:
                    self.license_status_changed.emit(self.license_status)
                    
        except Exception as e:
            logger.error(f"定期许可证检查失败: {e}")

    def get_license_status(self) -> dict:
        """获取许可证状态"""
        return {
            'status': self.license_status,
            'is_licensed': self.is_licensed,
            'trial_days_remaining': self.trial_days_remaining
        }

    def show_debug_dialog(self):
        """显示授权调试对话框（隐藏功能）"""
        try:
            license_manager = self._get_license_manager()
            if license_manager and hasattr(license_manager, 'show_debug_dialog'):
                license_manager.show_debug_dialog()
        except Exception as e:
            logger.error(f"显示调试对话框失败: {e}")

    def cleanup(self):
        """清理资源"""
        try:
            # 停止定期检查定时器
            if self.license_check_timer.isActive():
                self.license_check_timer.stop()
                
            logger.debug("许可证集成管理器资源已清理")
            
        except Exception as e:
            logger.error(f"清理许可证集成管理器资源失败: {e}")
