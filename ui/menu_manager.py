# -*- coding: utf-8 -*-
"""
菜单管理器
负责主窗口菜单栏的创建和事件处理

从MainWindow中提取的菜单管理功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
from PyQt5.QtWidgets import QAction, QMessageBox
from PyQt5.QtGui import QKeySequence

logger = logging.getLogger(__name__)


class MenuManager:
    """
    菜单管理器
    
    职责：
    - 菜单栏创建
    - 菜单项配置
    - 菜单事件处理
    - 快捷键管理
    """
    
    def __init__(self, main_window, config_manager):
        """
        初始化菜单管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
        """
        self.main_window = main_window
        self.config_manager = config_manager
        
        # 菜单项引用
        self.menu_actions = {}
        
        logger.debug("菜单管理器初始化完成")
    
    def create_menu_bar(self):
        """创建菜单栏"""
        try:
            menubar = self.main_window.menuBar()
            
            # 创建各个菜单
            self._create_file_menu(menubar)
            self._create_settings_menu(menubar)
            self._create_help_menu(menubar)
            
            logger.info("菜单栏创建完成")
            
        except Exception as e:
            logger.error(f"创建菜单栏失败: {e}")
    
    def _create_file_menu(self, menubar):
        """创建文件菜单"""
        try:
            file_menu = menubar.addMenu('文件(&F)')
            
            # 数据分析
            export_action = QAction('数据分析(&E)', self.main_window)
            export_action.setShortcut(QKeySequence.Save)
            export_action.setStatusTip('数据分析和导出')
            export_action.triggered.connect(self._on_export_data)
            file_menu.addAction(export_action)
            self.menu_actions['export'] = export_action

            # 数据同步
            sync_action = QAction('数据同步(&S)', self.main_window)
            sync_action.setShortcut('Ctrl+Shift+S')
            sync_action.setStatusTip('数据库同步管理')
            sync_action.triggered.connect(self._on_database_sync)
            file_menu.addAction(sync_action)
            self.menu_actions['sync'] = sync_action

            # 刷新显示
            refresh_action = QAction('刷新显示(&R)', self.main_window)
            refresh_action.setShortcut('F5')
            refresh_action.setStatusTip('从数据库刷新通道显示数据')
            refresh_action.triggered.connect(self._on_refresh_display)
            file_menu.addAction(refresh_action)
            self.menu_actions['refresh'] = refresh_action

            file_menu.addSeparator()
            
            # 退出
            exit_action = QAction('退出(&X)', self.main_window)
            exit_action.setShortcut(QKeySequence.Quit)
            exit_action.setStatusTip('退出应用程序')
            exit_action.triggered.connect(self.main_window.close)
            file_menu.addAction(exit_action)
            self.menu_actions['exit'] = exit_action
            
        except Exception as e:
            logger.error(f"创建文件菜单失败: {e}")
    
    def _create_settings_menu(self, menubar):
        """创建设置菜单"""
        try:
            settings_menu = menubar.addMenu('设置(&S)')

            # 用户登录
            login_action = QAction('用户登录(&L)', self.main_window)
            login_action.setShortcut('Ctrl+L')
            login_action.setStatusTip('切换用户角色')
            login_action.triggered.connect(self._on_user_login)
            settings_menu.addAction(login_action)
            self.menu_actions['login'] = login_action

            settings_menu.addSeparator()

            # 参数设置
            params_action = QAction('参数设置(&P)', self.main_window)
            params_action.setShortcut('Ctrl+P')
            params_action.setStatusTip('打开参数设置对话框')
            params_action.triggered.connect(self._on_open_settings)
            settings_menu.addAction(params_action)
            self.menu_actions['params'] = params_action

        except Exception as e:
            logger.error(f"创建设置菜单失败: {e}")
    
    def _create_help_menu(self, menubar):
        """创建帮助菜单"""
        try:
            help_menu = menubar.addMenu('帮助(&H)')

            # 申请解锁
            unlock_request_action = QAction('申请解锁(&U)', self.main_window)
            unlock_request_action.setShortcut('Ctrl+U')
            unlock_request_action.setStatusTip('申请软件解锁')
            unlock_request_action.triggered.connect(self._on_unlock_request)
            help_menu.addAction(unlock_request_action)
            self.menu_actions['unlock_request'] = unlock_request_action

            help_menu.addSeparator()

            # 关于
            about_action = QAction('关于(&A)', self.main_window)
            about_action.setStatusTip('关于本软件')
            about_action.triggered.connect(self._on_about)
            help_menu.addAction(about_action)
            self.menu_actions['about'] = about_action

        except Exception as e:
            logger.error(f"创建帮助菜单失败: {e}")
    
    def _on_export_data(self):
        """数据分析和导出"""
        try:
            logger.info("打开数据分析窗口")

            # 导入数据分析窗口
            from ui.dialogs.data_export_dialog import DataExportDialog
            from data.database_manager import DatabaseManager

            # 创建数据库管理器
            db_manager = DatabaseManager()

            # 创建并显示数据分析对话框
            dialog = DataExportDialog(db_manager, self.main_window)
            dialog.exec_()

        except Exception as e:
            logger.error(f"打开数据分析窗口失败: {e}")
            QMessageBox.warning(
                self.main_window,
                '错误',
                f'打开数据分析窗口失败：\n{e}'
            )

    def _on_database_sync(self):
        """数据库同步"""
        try:
            logger.info("打开数据库同步对话框")

            # 获取数据库同步管理器
            sync_manager = None
            if hasattr(self.main_window, 'database_sync_manager'):
                sync_manager = self.main_window.database_sync_manager
                logger.info("使用主窗口的数据库同步管理器")
            else:
                # 尝试创建数据库同步管理器
                try:
                    from backend.database_sync_manager import DatabaseSyncManager
                    from data.database_manager import get_database_manager

                    db_manager = get_database_manager()
                    if db_manager:
                        sync_manager = DatabaseSyncManager(db_manager=db_manager)
                        logger.info("创建新的数据库同步管理器")
                    else:
                        logger.warning("数据库管理器未初始化，无法创建同步管理器")
                except Exception as e:
                    logger.error(f"创建数据库同步管理器失败: {e}")

            # 导入并显示数据库同步对话框
            from ui.dialogs.database_sync_dialog import DatabaseSyncDialog
            dialog = DatabaseSyncDialog(sync_manager, self.main_window)
            dialog.exec_()

        except ImportError as e:
            logger.error(f"导入数据库同步对话框失败: {e}")
            QMessageBox.critical(
                self.main_window,
                '错误',
                '数据库同步模块未找到，请检查安装'
            )
        except Exception as e:
            logger.error(f"打开数据库同步对话框失败: {e}")
            QMessageBox.critical(
                self.main_window,
                '错误',
                f'打开数据库同步对话框失败：\n{e}'
            )

    def _on_user_login(self):
        """用户登录"""
        try:
            logger.info("打开用户登录对话框")
            
            # 导入用户登录对话框
            from ui.dialogs.user_login_dialog import UserLoginDialog
            
            # 创建并显示用户登录对话框
            dialog = UserLoginDialog(self.main_window)
            if dialog.exec_() == dialog.Accepted:
                # 登录成功，更新界面
                self._update_user_interface()
            
        except Exception as e:
            logger.error(f"用户登录失败: {e}")
            QMessageBox.warning(
                self.main_window,
                '错误',
                f'用户登录失败：\n{e}'
            )
    
    def _on_open_settings(self):
        """打开参数设置"""
        try:
            logger.info("打开参数设置对话框")

            # 导入参数设置对话框
            from ui.dialogs.settings_dialog import SettingsDialog

            # 创建并显示参数设置对话框
            dialog = SettingsDialog(self.config_manager, self.main_window)

            # 修复：连接设置应用信号到主界面刷新
            dialog.settings_applied.connect(self._on_settings_applied)
            dialog.settings_saved.connect(self._on_settings_saved)

            # 修复：连接设置变更信号到主界面配置变更处理
            if hasattr(self.main_window, '_on_config_changed'):
                dialog.settings_applied.connect(lambda: self.main_window._on_config_changed('settings', 'applied'))
                dialog.settings_saved.connect(lambda: self.main_window._on_config_changed('settings', 'saved'))

            # 修复连接设置对话框的信号
            if hasattr(dialog, 'settings_applied'):
                dialog.settings_applied.connect(self._on_settings_applied)
                logger.debug("已连接设置应用信号")

            if dialog.exec_() == dialog.Accepted:
                # 设置已更改，发送配置变更信号
                if hasattr(self.main_window, 'config_changed'):
                    self.main_window.config_changed.emit('settings', 'updated')

                # 修复：直接调用配置变更处理
                if hasattr(self.main_window, '_on_config_changed'):
                    self.main_window._on_config_changed('settings', 'updated')

                logger.info("✅ 设置对话框已确认，配置变更信号已发送")

        except Exception as e:
            logger.error(f"打开参数设置失败: {e}")
            QMessageBox.warning(
                self.main_window,
                '错误',
                f'打开参数设置失败：\n{e}'
            )

    def _on_settings_applied(self):
        """设置应用处理（修复：设置实时更新）"""
        try:
            logger.info("设置已应用，刷新主界面")

            # 触发主界面的设置刷新
            if hasattr(self.main_window, '_load_startup_settings'):
                self.main_window._load_startup_settings()

        except Exception as e:
            logger.error(f"处理设置应用失败: {e}")

    def _on_settings_saved(self):
        """设置保存处理（修复：设置实时更新）"""
        try:
            logger.info("设置已保存，刷新主界面")

            # 触发主界面的设置刷新
            if hasattr(self.main_window, '_load_startup_settings'):
                self.main_window._load_startup_settings()

        except Exception as e:
            logger.error(f"处理设置保存失败: {e}")

    def _on_unlock_request(self):
        """申请解锁对话框"""
        try:
            logger.info("打开申请解锁对话框")

            # 导入简化解锁对话框
            from ui.dialogs.simple_unlock_dialog import SimpleUnlockDialog

            # 创建并显示简化解锁对话框
            dialog = SimpleUnlockDialog(self.main_window)

            # 连接解锁成功信号
            dialog.unlock_successful.connect(self._on_unlock_successful)

            dialog.exec_()

        except Exception as e:
            logger.error(f"打开申请解锁对话框失败: {e}")
            QMessageBox.warning(
                self.main_window,
                '错误',
                f'打开申请解锁对话框失败：\n{e}'
            )



    def _on_unlock_successful(self):
        """处理解锁成功事件"""
        try:
            logger.info("软件解锁成功，刷新界面状态")

            # 刷新授权状态显示
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                header = ui_manager.get_component('header')
                if header and hasattr(header, 'refresh_license_status'):
                    header.refresh_license_status()

            # 显示解锁成功消息
            QMessageBox.information(
                self.main_window,
                "解锁成功",
                "软件已成功解锁！\n\n您现在可以无限制使用本软件的所有功能。"
            )

        except Exception as e:
            logger.error(f"处理解锁成功事件失败: {e}")

    def _on_about(self):
        """关于对话框"""
        try:
            # 获取应用信息
            app_name = self.config_manager.get('app.name', 'JCY5001AS鲸测云8路EIS阻抗筛选仪产线版')
            app_version = self.config_manager.get('app.version', 'V0.92.54')
            
            about_text = f"""
            <h2>{app_name}</h2>
            <p><b>版本:</b> {app_version}</p>
            <p><b>作者:</b> Jack</p>
            <p><b>描述:</b> JCY5001A阻抗测试仪产线测试界面</p>
            <p><b>功能:</b></p>
            <ul>
                <li>8通道并行阻抗测试</li>
                <li>实时数据分析和显示</li>
                <li>测试结果统计和导出</li>
                <li>设备参数配置和管理</li>
            </ul>
            <p><b>技术栈:</b> Python + PyQt5 + Modbus RTU</p>
            <p><b>开发时间:</b> 2025年1月</p>
            """
            
            QMessageBox.about(self.main_window, f'关于 {app_name}', about_text)
            
        except Exception as e:
            logger.error(f"显示关于对话框失败: {e}")

    def _on_refresh_display(self):
        """刷新显示处理"""
        try:
            logger.info("🔄 [菜单] 开始刷新通道显示...")

            # 获取通道容器组件
            ui_manager = getattr(self.main_window, 'ui_component_manager', None)
            if ui_manager:
                channels_container = ui_manager.get_component('channels_container')
                if channels_container and hasattr(channels_container, 'refresh_all_channels_from_database'):
                    channels_container.refresh_all_channels_from_database()

                    # 显示成功消息
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self.main_window,
                        "刷新完成",
                        "通道显示数据已从数据库刷新完成！\n\n现在显示的档位数据来自数据库中的最新测试结果。"
                    )

                    logger.info("✅ [菜单] 通道显示刷新完成")
                else:
                    logger.warning("⚠️ [菜单] 通道容器组件未找到或不支持刷新")

                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(
                        self.main_window,
                        "刷新失败",
                        "无法找到通道容器组件，刷新失败。"
                    )
            else:
                logger.warning("⚠️ [菜单] UI组件管理器未找到")

                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self.main_window,
                    "刷新失败",
                    "UI组件管理器未找到，刷新失败。"
                )

        except Exception as e:
            logger.error(f"❌ [菜单] 刷新显示失败: {e}")

            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self.main_window,
                "刷新错误",
                f"刷新显示时发生错误：\n{str(e)}"
            )

    def _update_user_interface(self):
        """更新用户界面（根据用户权限）"""
        try:
            # 导入权限管理器
            from utils.user_permission_manager import permission_manager
            
            # 获取当前用户角色
            current_role = permission_manager.get_current_role()
            
            # 根据用户角色更新菜单项状态
            if current_role.name == 'OPERATOR':
                # 操作员权限：禁用某些菜单项
                if 'params' in self.menu_actions:
                    self.menu_actions['params'].setEnabled(False)
            elif current_role.name in ['ENGINEER', 'ADMIN']:
                # 工程师和管理员权限：启用所有菜单项
                for action in self.menu_actions.values():
                    action.setEnabled(True)
            
            logger.info(f"用户界面已更新，当前角色: {current_role.name}")
            
        except Exception as e:
            logger.error(f"更新用户界面失败: {e}")
    
    def set_menu_enabled(self, menu_name: str, enabled: bool):
        """
        设置菜单项启用状态
        
        Args:
            menu_name: 菜单项名称
            enabled: 是否启用
        """
        try:
            if menu_name in self.menu_actions:
                self.menu_actions[menu_name].setEnabled(enabled)
                logger.debug(f"菜单项 {menu_name} 状态设置为: {enabled}")
            else:
                logger.warning(f"菜单项 {menu_name} 不存在")
                
        except Exception as e:
            logger.error(f"设置菜单项状态失败: {e}")
    
    def get_menu_action(self, menu_name: str):
        """
        获取菜单项动作
        
        Args:
            menu_name: 菜单项名称
            
        Returns:
            QAction实例或None
        """
        return self.menu_actions.get(menu_name)
    
    def update_menu_status(self, is_testing: bool):
        """
        根据测试状态更新菜单
        
        Args:
            is_testing: 是否正在测试
        """
        try:
            # 测试期间禁用某些菜单项
            if is_testing:
                self.set_menu_enabled('params', False)
                self.set_menu_enabled('login', False)
            else:
                self.set_menu_enabled('params', True)
                self.set_menu_enabled('login', True)
            
            logger.debug(f"菜单状态已更新，测试状态: {is_testing}")
            
        except Exception as e:
            logger.error(f"更新菜单状态失败: {e}")
    
    def get_menu_info(self):
        """
        获取菜单信息
        
        Returns:
            菜单信息字典
        """
        try:
            menu_info = {}
            for name, action in self.menu_actions.items():
                menu_info[name] = {
                    'text': action.text(),
                    'shortcut': action.shortcut().toString() if action.shortcut() else '',
                    'status_tip': action.statusTip(),
                    'enabled': action.isEnabled(),
                    'visible': action.isVisible()
                }
            
            return menu_info
            
        except Exception as e:
            logger.error(f"获取菜单信息失败: {e}")
            return {}
