# -*- coding: utf-8 -*-
"""
授权管理器
从MainWindow中提取的授权相关功能

职责：
- 授权状态检查
- 试用期管理
- 解锁码处理
- 授权相关UI更新

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


class AuthorizationManager(QObject):
    """
    授权管理器
    
    职责：
    - 软件授权状态检查
    - 试用期管理
    - 解锁码验证
    - 授权到期处理
    """
    
    def __init__(self, main_window, config_manager):
        """
        初始化授权管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
        """
        super().__init__()
        
        self.main_window = main_window
        self.config_manager = config_manager
        
        logger.debug("授权管理器初始化完成")
    
    def check_license_on_startup(self):
        """启动时检查授权状态"""
        try:
            logger.info("开始检查软件授权状态...")

            # 获取授权管理器
            license_manager = self._get_license_manager()
            if not license_manager:
                logger.error("无法获取授权管理器")
                return

            # 检查授权状态
            status = license_manager.check_license()
            
            if status.get('is_valid', False):
                if status.get('is_trial', False):
                    # 试用版
                    self._handle_trial_status(status)
                elif status.get('license_type') == 'temp':
                    # 临时授权
                    self._handle_temp_license_status(status)
                else:
                    # 正式版
                    logger.info("软件已正式授权")
            else:
                # 授权无效
                self._handle_invalid_license(status)

        except Exception as e:
            logger.error(f"启动时检查授权状态失败: {e}")
    
    def _get_license_manager(self):
        """获取授权管理器实例"""
        try:
            from utils.license_manager import LicenseManager
            return LicenseManager()
        except Exception as e:
            logger.error(f"获取授权管理器失败: {e}")
            return None
    
    def _handle_trial_status(self, status: Dict[str, Any]):
        """处理试用版状态"""
        try:
            if status.get('is_expired', False):
                logger.warning("软件试用期已到期")
                self._handle_trial_expired()
            else:
                remaining_days = status.get('remaining_days', 0)
                logger.info(f"软件在试用期内，剩余{remaining_days}天")

                # 修复根据配置决定是否显示启动提醒
                show_startup_dialog = self.main_window.config_manager.get('app.show_startup_license_dialog', False)

                # 如果剩余天数较少且配置允许，显示提醒
                if remaining_days <= 7 and show_startup_dialog:
                    QMessageBox.information(
                        self.main_window,
                        "试用期提醒",
                        f"软件试用期剩余 {remaining_days} 天。\n\n如需继续使用，请及时联系供应商获取解锁码。"
                    )
                elif remaining_days <= 7:
                    # 只记录日志，不显示弹窗
                    logger.info(f"试用期剩余 {remaining_days} 天（启动提醒已禁用）")
        except Exception as e:
            logger.error(f"处理试用版状态失败: {e}")

    def _handle_temp_license_status(self, status: Dict[str, Any]):
        """处理临时授权状态"""
        try:
            remaining_days = status.get('remaining_days', 0)
            expire_date = status.get('expire_date', '')

            logger.info(f"软件处于临时授权状态，剩余 {remaining_days} 天")

            # 修复默认不显示启动时的临时授权提醒弹窗，只记录日志
            if remaining_days <= 7:
                from datetime import datetime
                if expire_date:
                    expire_dt = datetime.fromisoformat(expire_date)
                    expire_str = expire_dt.strftime("%Y年%m月%d日")
                else:
                    expire_str = "未知"

                logger.info(f"临时授权剩余 {remaining_days} 天，到期时间：{expire_str}（启动提醒已禁用，避免弹窗影响用户体验）")
                # 注释掉弹窗代码，改善客户体验
                # QMessageBox.information(
                # self.main_window,
                # "临时授权提醒",
                # f"软件临时授权剩余 {remaining_days} 天。\n\n到期时间：{expire_str}\n\n如需继续使用，请及时联系供应商获取正式授权。"
                # )
        except Exception as e:
            logger.error(f"处理临时授权状态失败: {e}")

    def _handle_invalid_license(self, status: Dict[str, Any]):
        """处理无效授权"""
        try:
            error_message = status.get('error', '授权验证失败')
            logger.error(f"软件授权无效: {error_message}")

            # 修复默认不显示启动时的授权错误弹窗，只记录日志
            logger.error(f"授权验证失败：{error_message}（启动提醒已禁用，避免弹窗影响用户体验）")
            # 注释掉弹窗代码，改善客户体验
            # QMessageBox.critical(
            # self.main_window,
            # "授权错误",
            # f"软件授权验证失败：\n\n{error_message}\n\n请联系供应商获取有效的授权。"
            # )

        except Exception as e:
            logger.error(f"处理无效授权失败: {e}")
    
    def _handle_trial_expired(self):
        """处理试用期到期"""
        try:
            logger.warning("软件试用期已到期，显示解锁对话框")

            # 禁用测试功能
            self._disable_test_functions()

            # 显示解锁对话框
            self._show_unlock_dialog()

        except Exception as e:
            logger.error(f"处理试用期到期失败: {e}")

    def _disable_test_functions(self):
        """禁用测试功能"""
        try:
            # 获取测试流程管理器并禁用测试功能
            if hasattr(self.main_window, 'test_flow_manager'):
                test_manager = self.main_window.test_flow_manager
                if hasattr(test_manager, 'set_test_enabled'):
                    test_manager.set_test_enabled(False)
                    logger.info("已禁用测试功能（试用期到期）")

            # 禁用测试相关UI按钮
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                control_panel = ui_manager.get_component('control_panel')
                if control_panel and hasattr(control_panel, 'set_test_buttons_enabled'):
                    control_panel.set_test_buttons_enabled(False)
                    logger.info("已禁用测试按钮（试用期到期）")

        except Exception as e:
            logger.error(f"禁用测试功能失败: {e}")
    
    def _show_unlock_dialog(self):
        """显示解锁对话框"""
        try:
            from PyQt5.QtWidgets import QInputDialog, QLineEdit, QMessageBox

            while True:  # 循环直到解锁成功或用户选择退出
                # 显示输入解锁码的对话框
                unlock_code, ok = QInputDialog.getText(
                    self.main_window,
                    "软件解锁 - 试用期已到期",
                    "软件试用期已到期，测试功能已被禁用。\n\n请输入解锁码以继续使用：\n\n如需购买授权，请联系软件供应商。",
                    QLineEdit.Password
                )

                if ok and unlock_code:
                    # 验证解锁码
                    result = self._verify_unlock_code(unlock_code)
                    if result:
                        QMessageBox.information(
                            self.main_window,
                            "解锁成功",
                            "软件解锁成功！感谢您的使用。\n\n所有功能现已可用。"
                        )
                        logger.info("软件解锁成功")

                        # 重新启用测试功能
                        self._enable_test_functions()

                        # 刷新授权状态显示
                        self._refresh_license_display()
                        break
                    else:
                        # 解锁失败，询问是否重试
                        retry = QMessageBox.question(
                            self.main_window,
                            "解锁失败",
                            "解锁码无效，请检查后重试。\n\n是否重新输入解锁码？",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.Yes
                        )

                        if retry == QMessageBox.No:
                            logger.info("用户选择不重试解锁")
                            self._handle_unlock_cancelled()
                            break
                else:
                    logger.info("用户取消解锁")
                    self._handle_unlock_cancelled()
                    break

        except Exception as e:
            logger.error(f"显示解锁对话框失败: {e}")

    def _enable_test_functions(self):
        """重新启用测试功能"""
        try:
            # 启用测试流程管理器
            if hasattr(self.main_window, 'test_flow_manager'):
                test_manager = self.main_window.test_flow_manager
                if hasattr(test_manager, 'set_test_enabled'):
                    test_manager.set_test_enabled(True)
                    logger.info("已启用测试功能（解锁成功）")

            # 启用测试相关UI按钮
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                control_panel = ui_manager.get_component('control_panel')
                if control_panel and hasattr(control_panel, 'set_test_buttons_enabled'):
                    control_panel.set_test_buttons_enabled(True)
                    logger.info("已启用测试按钮（解锁成功）")

        except Exception as e:
            logger.error(f"启用测试功能失败: {e}")

    def _refresh_license_display(self):
        """刷新授权状态显示"""
        try:
            # 刷新header组件的授权状态显示
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                header = ui_manager.get_component('header')
                if header and hasattr(header, 'refresh_license_status'):
                    header.refresh_license_status()
                    logger.info("已刷新授权状态显示")

        except Exception as e:
            logger.error(f"刷新授权状态显示失败: {e}")

    def _handle_unlock_cancelled(self):
        """处理用户取消解锁"""
        try:
            # 显示功能限制提示
            QMessageBox.warning(
                self.main_window,
                "功能受限",
                "由于试用期已到期且未解锁，测试功能将保持禁用状态。\n\n您仍可以：\n• 查看软件界面\n• 访问设置菜单\n• 查看历史数据\n\n如需使用测试功能，请点击右上角的\"解锁\"按钮。",
                QMessageBox.Ok
            )
            logger.info("用户取消解锁，功能受限模式")

        except Exception as e:
            logger.error(f"处理取消解锁失败: {e}")
    
    def _verify_unlock_code(self, unlock_code: str) -> bool:
        """
        验证解锁码

        Args:
            unlock_code: 解锁码

        Returns:
            是否验证成功
        """
        try:
            license_manager = self._get_license_manager()
            if not license_manager:
                logger.error("无法获取授权管理器")
                return False

            # 使用授权管理器验证解锁码
            result = license_manager.unlock_with_code(unlock_code)
            success = result.get('success', False)

            if success:
                logger.info("解锁码验证成功")
            else:
                error_msg = result.get('message', '未知错误')
                logger.warning(f"解锁码验证失败: {error_msg}")

            return success

        except Exception as e:
            logger.error(f"验证解锁码失败: {e}")
            return False

    def handle_trial_expired(self):
        """处理试用期到期事件（外部调用）"""
        try:
            logger.warning("收到试用期到期事件")
            self._handle_trial_expired()

        except Exception as e:
            logger.error(f"处理试用期到期事件失败: {e}")

    def handle_unlock_requested(self):
        """处理解锁请求事件（外部调用）"""
        try:
            logger.info("收到解锁请求事件")
            self._show_unlock_dialog()

        except Exception as e:
            logger.error(f"处理解锁请求事件失败: {e}")

    def get_license_status(self) -> Dict[str, Any]:
        """
        获取当前授权状态

        Returns:
            授权状态字典
        """
        try:
            license_manager = self._get_license_manager()
            if not license_manager:
                return {'error': '无法获取授权管理器'}

            return license_manager.check_license()

        except Exception as e:
            logger.error(f"获取授权状态失败: {e}")
            return {'error': str(e)}

    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        检查特定功能是否启用

        Args:
            feature_name: 功能名称

        Returns:
            功能是否启用
        """
        try:
            license_status = self.get_license_status()

            if not license_status.get('is_valid', False):
                return False

            # 检查功能权限
            enabled_features = license_status.get('enabled_features', [])
            return feature_name in enabled_features

        except Exception as e:
            logger.error(f"检查功能启用状态失败: {e}")
            return False

    def get_remaining_trial_days(self) -> Optional[int]:
        """
        获取剩余试用天数

        Returns:
            剩余天数，如果不是试用版则返回None
        """
        try:
            license_status = self.get_license_status()

            if license_status.get('is_trial', False):
                return license_status.get('remaining_days')

            return None

        except Exception as e:
            logger.error(f"获取剩余试用天数失败: {e}")
            return None

    def refresh_license_status(self):
        """刷新授权状态"""
        try:
            logger.info("刷新授权状态...")

            # 重新检查授权状态
            self.check_license_on_startup()

        except Exception as e:
            logger.error(f"刷新授权状态失败: {e}")

    def get_authorization_info(self) -> Dict[str, Any]:
        """
        获取授权信息摘要

        Returns:
            授权信息字典
        """
        try:
            license_status = self.get_license_status()

            return {
                'is_valid': license_status.get('is_valid', False),
                'is_trial': license_status.get('is_trial', False),
                'is_expired': license_status.get('is_expired', False),
                'remaining_days': license_status.get('remaining_days'),
                'license_type': license_status.get('license_type', 'unknown'),
                'enabled_features': license_status.get('enabled_features', []),
                'last_check_time': license_status.get('last_check_time')
            }

        except Exception as e:
            logger.error(f"获取授权信息失败: {e}")
            return {'error': str(e)}