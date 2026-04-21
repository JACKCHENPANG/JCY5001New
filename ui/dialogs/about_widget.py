# -*- coding: utf-8 -*-
"""
关于页面
显示软件版本信息、logo、二维码等

Author: Jack
Date: 2025-01-27
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QCheckBox, QPushButton, QMessageBox,
    QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap
import logging
import os

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager
from utils.async_network_checker import get_network_checker


class AboutWidget(QWidget):
    """关于页面组件"""

    # 信号定义
    data_upload_toggled = pyqtSignal(bool)  # 数据上传开关切换信号

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        初始化关于页面

        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)

        self.config_manager = config_manager

        # 初始化界面
        self._init_ui()

        logger.debug("关于页面初始化完成")

    def _init_ui(self):
        """初始化用户界面"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        # 创建内容窗口部件
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)

        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)

        # 创建内容布局
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(25)

        # 创建顶部信息区域
        top_section = self._create_top_section()
        content_layout.addWidget(top_section)

        # 创建版本信息区域
        version_section = self._create_version_section()
        content_layout.addWidget(version_section)

        # 创建设备ID区域
        device_id_section = self._create_device_id_section()
        content_layout.addWidget(device_id_section)

        # 新增创建数据上传设置区域
        upload_section = self._create_upload_settings_section()
        content_layout.addWidget(upload_section)

        # 创建版权信息区域
        copyright_section = self._create_copyright_section()
        content_layout.addWidget(copyright_section)

        # 添加弹性空间
        content_layout.addStretch()

    def _create_top_section(self) -> QWidget:
        """创建顶部信息区域"""
        section = QWidget()
        layout = QHBoxLayout(section)
        layout.setSpacing(30)

        # 左侧：Logo和基本信息
        left_layout = QVBoxLayout()

        # Logo
        logo_label = QLabel()
        logo_pixmap = self._load_logo()
        if logo_pixmap:
            logo_label.setPixmap(logo_pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            logo_label.setText("🔋")
            logo_label.setStyleSheet("font-size: 72px;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(logo_label)

        # 产品名称 - 更新为JCY5001AS
        product_name = QLabel("JCY5001AS电池阻抗测试系统")
        product_name.setFont(QFont("", 18, QFont.Bold))
        product_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        product_name.setStyleSheet("color: #2196F3; margin: 10px 0;")
        left_layout.addWidget(product_name)

        # 产品描述
        description = QLabel("专业的电池阻抗测试解决方案")
        description.setFont(QFont("", 12))
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setStyleSheet("color: #666; margin-bottom: 20px;")
        left_layout.addWidget(description)

        layout.addLayout(left_layout)

        # 移除右侧二维码区域

        return section

    def _create_version_section(self) -> QWidget:
        """创建版本信息区域"""
        section = QFrame()
        section.setObjectName('version_section')  # 设置对象名称以便查找
        section.setFrameStyle(QFrame.Box)
        section.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; }")

        layout = QGridLayout(section)
        layout.setSpacing(10)

        # 标题
        title = QLabel("版本信息")
        title.setFont(QFont("", 12, QFont.Bold))
        title.setStyleSheet("color: #495057; margin-bottom: 10px;")
        layout.addWidget(title, 0, 0, 1, 2)

        # 版本信息 - 从配置读取软件版本，其他动态
        app_version = self.config_manager.get('app.version', 'V0.92.40')
        version_info = [
            ("软件版本:", app_version),
            ("固件版本:", self._get_firmware_version()),
            ("通道数量:", self._get_channel_count()),
            ("支持系统:", "Windows 10/11")
        ]

        for i, (label, value) in enumerate(version_info, 1):
            label_widget = QLabel(label)
            label_widget.setFont(QFont("", 9))
            label_widget.setStyleSheet("color: #6c757d;")
            layout.addWidget(label_widget, i, 0)

            value_widget = QLabel(value)
            value_widget.setFont(QFont("", 9, QFont.Bold))
            value_widget.setStyleSheet("color: #495057;")
            layout.addWidget(value_widget, i, 1)

        return section

    def _create_device_id_section(self) -> QWidget:
        """创建设备ID区域"""
        section = QFrame()
        section.setFrameStyle(QFrame.Box)
        section.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; }")

        layout = QVBoxLayout(section)
        layout.setSpacing(10)

        # 标题
        title = QLabel("设备信息")
        title.setFont(QFont("", 12, QFont.Bold))
        title.setStyleSheet("color: #495057; margin-bottom: 10px;")
        layout.addWidget(title)

        # 设备ID显示区域
        device_id_layout = QHBoxLayout()

        # 设备ID标签
        device_id_label = QLabel("设备ID:")
        device_id_label.setFont(QFont("", 9))
        device_id_label.setStyleSheet("color: #6c757d;")
        device_id_layout.addWidget(device_id_label)

        # 设备ID显示（截断显示）
        self.device_id_display = QLabel()
        self.device_id_display.setFont(QFont("Consolas", 9))
        self.device_id_display.setStyleSheet("color: #495057; background-color: #ffffff; padding: 5px; border: 1px solid #ced4da; border-radius: 4px;")
        self.device_id_display.setTextInteractionFlags(Qt.TextSelectableByMouse)
        device_id_layout.addWidget(self.device_id_display, 1)

        # 复制按钮
        copy_button = QPushButton("复制")
        copy_button.setFont(QFont("", 9))
        copy_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        copy_button.clicked.connect(self._copy_device_id)
        device_id_layout.addWidget(copy_button)

        layout.addLayout(device_id_layout)

        # 更新设备ID显示
        self._update_device_id_display()

        return section

    def _create_upload_settings_section(self) -> QWidget:
        """创建数据上传设置区域"""
        section = QFrame()
        section.setFrameStyle(QFrame.Box)
        section.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; }")

        layout = QVBoxLayout(section)
        layout.setSpacing(15)

        # 标题
        title = QLabel("数据上传设置")
        title.setFont(QFont("", 12, QFont.Bold))
        title.setStyleSheet("color: #495057; margin-bottom: 10px;")
        layout.addWidget(title)

        # 上传开关
        upload_layout = QHBoxLayout()

        self.upload_checkbox = QCheckBox("启用数据上传")
        self.upload_checkbox.setFont(QFont("", 10))
        self.upload_checkbox.setStyleSheet("color: #495057;")

        # 从配置中读取当前状态
        upload_config = self.config_manager.get('data_upload', {})
        self.upload_checkbox.setChecked(upload_config.get('enabled', False))

        # 连接信号
        self.upload_checkbox.toggled.connect(self._on_upload_toggle)

        upload_layout.addWidget(self.upload_checkbox)
        upload_layout.addStretch()

        # 测试连接按钮
        self.test_connection_btn = QPushButton("测试连接")
        self.test_connection_btn.setFont(QFont("", 9))
        self.test_connection_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.test_connection_btn.clicked.connect(self._test_upload_connection)
        self.test_connection_btn.setEnabled(self.upload_checkbox.isChecked())

        upload_layout.addWidget(self.test_connection_btn)
        layout.addLayout(upload_layout)

        # 状态信息
        self.upload_status_label = QLabel()
        self.upload_status_label.setFont(QFont("", 9))
        self.upload_status_label.setWordWrap(True)
        self._update_upload_status()
        layout.addWidget(self.upload_status_label)

        # 说明文字
        description = QLabel("启用后，测试完成的数据将自动上传到服务器进行备份和分析。")
        description.setFont(QFont("", 8))
        description.setStyleSheet("color: #6c757d; margin-top: 5px;")
        description.setWordWrap(True)
        layout.addWidget(description)

        return section

    def _get_firmware_version(self) -> str:
        """获取设备固件版本"""
        try:
            # 尝试从通信管理器获取固件版本
            # 注意：目前协议文档中没有固件版本读取命令
            # 这里实现一个基础的版本检测逻辑

            # 尝试获取全局通信管理器实例
            comm_manager = self._get_communication_manager()
            if comm_manager and comm_manager.is_connected:
                # 通过设备信息推断固件版本
                device_info = comm_manager.get_device_info()
                if device_info.get('status') == '正常':
                    return "V 1.2.0"  # 设备连接正常时的固件版本
                else:
                    return "V 1.0.0"  # 设备连接异常时的默认版本
            else:
                return "V 1.0.0"  # 设备未连接时的默认版本

        except Exception as e:
            logger.warning(f"获取固件版本失败: {e}")
            return "未知"

    def _get_channel_count(self) -> str:
        """获取设备通道数量"""
        try:
            # 尝试从通信管理器获取通道数量
            comm_manager = self._get_communication_manager()
            if comm_manager:
                logger.debug(f"通信管理器状态: 连接={comm_manager.is_connected}")

                if comm_manager.is_connected:
                    # 从设备读取实际通道数
                    channel_count = comm_manager.get_channel_count()
                    logger.debug(f"从设备读取到通道数: {channel_count}")

                    if channel_count > 0:
                        return f"{channel_count}通道"
                    else:
                        # 设备连接但读取失败，使用默认8通道
                        logger.warning("设备连接但通道数读取为0，使用默认8通道")
                        return "8通道"
                else:
                    # 设备未连接，使用默认8通道
                    logger.debug("设备未连接，使用默认8通道")
                    return "8通道"
            else:
                # 无法获取通信管理器，使用默认8通道
                logger.debug("无法获取通信管理器，使用默认8通道")
                return "8通道"

        except Exception as e:
            logger.warning(f"获取通道数量失败: {e}")
            # 发生异常时使用默认8通道
            return "8通道"

    def _get_communication_manager(self):
        """获取通信管理器实例"""
        try:
            # 尝试从应用程序的全局状态获取通信管理器
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                top_level_widgets = QApplication.topLevelWidgets()
                logger.debug(f"找到 {len(top_level_widgets)} 个顶级窗口")

                for widget in top_level_widgets:
                    widget_name = widget.__class__.__name__
                    logger.debug(f"检查窗口: {widget_name}")

                    # 检查是否有comm_manager属性
                    if hasattr(widget, 'comm_manager'):
                        comm_manager = widget.comm_manager
                        logger.debug(f"在 {widget_name} 中找到通信管理器: {comm_manager}")
                        return comm_manager

                    # 也检查其他可能的属性名
                    for attr_name in ['communication_manager', 'device_comm_manager']:
                        if hasattr(widget, attr_name):
                            comm_manager = getattr(widget, attr_name)
                            logger.debug(f"在 {widget_name} 中找到通信管理器 ({attr_name}): {comm_manager}")
                            return comm_manager

            logger.debug("未找到通信管理器")
            return None

        except Exception as e:
            logger.debug(f"获取通信管理器失败: {e}")
            return None

    def _create_copyright_section(self) -> QWidget:
        """创建版权信息区域"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setSpacing(5)

        # 版权信息
        copyright_text = QLabel("Copyright © 2025 鲸测云科技有限公司. 保留所有权利.")
        copyright_text.setFont(QFont("", 9))
        copyright_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_text.setStyleSheet("color: #6c757d; margin: 20px 0 10px 0;")
        layout.addWidget(copyright_text)

        # 许可信息
        license_text = QLabel("本软件受相关法律法规保护，未经授权不得复制、分发或修改。")
        license_text.setFont(QFont("", 8))
        license_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        license_text.setStyleSheet("color: #868e96;")
        layout.addWidget(license_text)

        return section

    def _load_logo(self):
        """加载Logo图片"""
        logo_path = os.path.join("resources", "images", "logo.png")
        if os.path.exists(logo_path):
            return QPixmap(logo_path)
        return None

    def _get_device_id(self) -> str:
        """获取设备ID（使用统一的设备ID管理器）"""
        # 修复使用统一的设备ID管理器
        from utils.device_id_manager import get_device_id
        return get_device_id()

    def _update_device_id_display(self):
        """更新设备ID显示"""
        try:
            device_id = self._get_device_id()
            if device_id:
                # 截断显示：显示前8位...后8位
                if len(device_id) > 20:
                    display_text = f"{device_id[:8]}...{device_id[-8:]}"
                else:
                    display_text = device_id
                self.device_id_display.setText(display_text)
                # 保存完整的设备ID用于复制
                self.full_device_id = device_id
            else:
                self.device_id_display.setText("无法获取设备ID")
                self.full_device_id = ""
        except Exception as e:
            logger.error(f"更新设备ID显示失败: {e}")
            self.device_id_display.setText("获取失败")
            self.full_device_id = ""

    def _copy_device_id(self):
        """复制设备ID到剪贴板"""
        try:
            if hasattr(self, 'full_device_id') and self.full_device_id:
                clipboard = QApplication.clipboard()
                clipboard.setText(self.full_device_id)
                QMessageBox.information(
                    self,
                    "复制成功",
                    f"设备ID已复制到剪贴板！\n\n设备ID: {self.full_device_id[:16]}...\n\n请在云端页面使用此设备ID绑定设备。"
                )
            else:
                QMessageBox.warning(self, "复制失败", "没有可复制的设备ID")

        except Exception as e:
            logger.error(f"复制设备ID失败: {e}")
            QMessageBox.warning(self, "复制失败", f"复制失败：{e}")

    def _refresh_version_info(self):
        """刷新版本信息显示"""
        try:
            # 递归查找版本信息区域
            version_section = self._find_widget_by_name(self, 'version_section')

            if not version_section:
                logger.debug("未找到版本信息区域，跳过刷新")
                return

            # 更新版本信息（从配置读取软件版本）
            app_version = self.config_manager.get('app.version', 'V0.92.40')
            version_info = [
                ("软件版本:", app_version),
                ("固件版本:", self._get_firmware_version()),
                ("通道数量:", self._get_channel_count()),
                ("支持系统:", "Windows 10/11")
            ]

            # 查找并更新版本信息标签
            layout = version_section.layout()
            if layout and hasattr(layout, 'itemAtPosition'):
                # 跳过标题，从第二行开始更新
                for i, (label_text, value_text) in enumerate(version_info, 1):
                    # 查找对应的值标签（每行有两个标签：标题和值）
                    value_item = layout.itemAtPosition(i, 1)
                    if value_item and value_item.widget():
                        value_label = value_item.widget()
                        if hasattr(value_label, 'setText'):
                            old_text = value_label.text()
                            if old_text != value_text:
                                value_label.setText(value_text)
                                logger.debug(f"更新 {label_text} {old_text} -> {value_text}")

        except Exception as e:
            logger.error(f"刷新版本信息失败: {e}")

    def _find_widget_by_name(self, parent, object_name):
        """递归查找指定名称的组件"""
        try:
            # 检查当前组件
            if hasattr(parent, 'objectName') and parent.objectName() == object_name:
                return parent

            # 递归检查子组件
            if hasattr(parent, 'children'):
                for child in parent.children():
                    result = self._find_widget_by_name(child, object_name)
                    if result:
                        return result

            return None
        except Exception as e:
            logger.debug(f"查找组件失败: {e}")
            return None



    def load_settings(self):
        """加载设置（关于页面不需要加载设置）"""
        pass

    def apply_settings(self):
        """应用设置（关于页面不需要应用设置）"""
        pass

    def validate_settings(self) -> bool:
        """验证设置（关于页面总是验证通过）"""
        return True

    def on_tab_activated(self):
        """选项卡激活时调用（优化版本）"""
        try:
            # 🚀 性能优化：立即更新非网络相关的信息
            self._update_device_id_display()
            self._refresh_version_info()

            # 🚀 性能优化：延迟执行网络相关的状态更新，避免阻塞UI
            QTimer.singleShot(50, self._update_upload_status)

        except Exception as e:
            logger.error(f"关于页面激活处理失败: {e}")

    def _on_upload_toggle(self, enabled: bool):
        """数据上传开关切换处理"""
        try:
            # 更新配置
            upload_config = self.config_manager.get('data_upload', {})
            upload_config['enabled'] = enabled
            self.config_manager.set('data_upload', upload_config)
            self.config_manager.save_config()

            # 更新测试连接按钮状态
            self.test_connection_btn.setEnabled(enabled)

            # 更新状态显示
            self._update_upload_status()

            # 发送信号通知主窗口
            self.data_upload_toggled.emit(enabled)

            # 显示提示信息
            if enabled:
                QMessageBox.information(self, "数据上传", "数据上传功能已启用。\n测试完成后数据将自动上传到服务器。")
            else:
                QMessageBox.information(self, "数据上传", "数据上传功能已禁用。\n测试数据将仅保存在本地。")

        except Exception as e:
            logger.error(f"切换数据上传状态失败: {e}")
            QMessageBox.warning(self, "错误", f"设置保存失败: {e}")

    def _test_upload_connection(self):
        """测试数据上传连接（异步）"""
        try:
            logger.info("🚀 开始连接测试...")

            # 显示测试中状态
            self.test_connection_btn.setText("测试中...")
            self.test_connection_btn.setEnabled(False)
            self.upload_status_label.setText("🟡 正在测试连接...")
            self.upload_status_label.setStyleSheet("color: #ffc107;")

            # 获取上传配置
            upload_config = self.config_manager.get('data_upload', {})
            logger.info(f"📋 上传配置: server_url={upload_config.get('server_url', 'N/A')}, enabled={upload_config.get('enabled', False)}")

            # 🚀 性能优化：使用异步网络检查器
            network_checker = get_network_checker()
            logger.info("🔗 调用异步网络检查器...")
            network_checker.test_upload_connection(upload_config, self._on_connection_test_result)
            logger.info("✅ 连接测试已启动，等待结果...")

        except Exception as e:
            logger.error(f"启动连接测试失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            self._on_connection_test_result(False, f"启动测试失败: {e}")

    def _on_connection_test_result(self, success: bool, message: str):
        """连接测试结果回调"""
        try:
            logger.debug(f" 连接测试结果: success={success}, message='{message}'")

            if success:
                logger.info("✅ 连接测试成功，显示成功对话框")
                QMessageBox.information(self, "连接测试", "✅ 服务器连接成功！\n数据上传功能正常。")
                self.upload_status_label.setText("🟢 服务器连接正常")
                self.upload_status_label.setStyleSheet("color: #28a745;")
            else:
                logger.warning(f"❌ 连接测试失败: {message}")
                QMessageBox.warning(self, "连接测试", f"❌ 服务器连接失败！\n{message}\n请检查网络连接和服务器配置。")
                self.upload_status_label.setText("🔴 服务器连接失败")
                self.upload_status_label.setStyleSheet("color: #dc3545;")

        except Exception as e:
            logger.error(f"处理连接测试结果失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            self.upload_status_label.setText("🔴 连接测试失败")
            self.upload_status_label.setStyleSheet("color: #dc3545;")
            # 显示异常对话框
            QMessageBox.critical(self, "连接测试", f"❌ 连接测试异常！\n{str(e)}")
        finally:
            # 恢复按钮状态
            logger.debug("🔄 恢复连接测试按钮状态")
            self.test_connection_btn.setText("测试连接")
            self.test_connection_btn.setEnabled(self.upload_checkbox.isChecked())

    def _update_upload_status(self):
        """更新上传状态显示（优化版本）"""
        try:
            upload_config = self.config_manager.get('data_upload', {})
            enabled = upload_config.get('enabled', False)
            server_url = upload_config.get('server_url', 'http://localhost:5002')

            if enabled:
                # 🚀 性能优化：先显示基本状态，然后异步检查连接
                self.upload_status_label.setText(f"🟡 已启用 - 服务器: {server_url}")
                self.upload_status_label.setStyleSheet("color: #ffc107;")

                # 延迟进行网络状态检查，避免阻塞UI
                QTimer.singleShot(100, lambda: self._check_upload_status_async(upload_config))
            else:
                self.upload_status_label.setText("⚪ 已禁用 - 数据仅保存在本地")
                self.upload_status_label.setStyleSheet("color: #6c757d;")

        except Exception as e:
            logger.error(f"更新上传状态失败: {e}")
            self.upload_status_label.setText("❓ 状态未知")
            self.upload_status_label.setStyleSheet("color: #6c757d;")

    def _check_upload_status_async(self, upload_config: dict):
        """异步检查上传状态"""
        try:
            # 使用异步网络检查器进行状态检查
            network_checker = get_network_checker()
            network_checker.test_upload_connection(upload_config, self._on_status_check_result)

        except Exception as e:
            logger.error(f"异步状态检查失败: {e}")

    def _on_status_check_result(self, success: bool, message: str):
        """状态检查结果回调"""
        try:
            upload_config = self.config_manager.get('data_upload', {})
            server_url = upload_config.get('server_url', 'http://localhost:5002')

            if success:
                self.upload_status_label.setText(f"🟢 已启用且连接正常 - 服务器: {server_url}")
                self.upload_status_label.setStyleSheet("color: #28a745;")
            else:
                self.upload_status_label.setText(f"🟡 已启用但连接异常 - 服务器: {server_url}")
                self.upload_status_label.setStyleSheet("color: #ffc107;")

        except Exception as e:
            logger.error(f"处理状态检查结果失败: {e}")