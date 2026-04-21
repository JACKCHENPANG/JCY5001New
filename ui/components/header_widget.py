# -*- coding: utf-8 -*-
"""
顶部标题栏组件
显示产品名称、logo和试用倒计时

Author: Jack
Date: 2025-01-27
"""

import os
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
import logging

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager


class HeaderWidget(QWidget):
    """顶部标题栏组件"""

    # 信号定义
    trial_expired = pyqtSignal()  # 试用期到期信号
    unlock_requested = pyqtSignal()  # 解锁请求信号

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        初始化顶部标题栏

        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.trial_days = config_manager.get('app.trial_days', 30)

        # 初始化授权管理器
        self.license_manager = None
        self._init_license_manager()

        # 初始化界面
        self._init_ui()
        self._init_timer()

        # 更新授权状态显示
        self._update_license_status()

        logger.debug("顶部标题栏组件初始化完成")

    def _init_license_manager(self):
        """初始化授权管理器"""
        try:
            from utils.license_manager import LicenseManager
            self.license_manager = LicenseManager(self.config_manager)

            # 初始化试用期（如果是首次运行）
            trial_days = self.config_manager.get('app.trial_days', 30)
            self.license_manager.initialize_trial(trial_days)

            logger.debug("授权管理器初始化完成")

        except Exception as e:
            logger.error(f"初始化授权管理器失败: {e}")
            self.license_manager = None

    def _init_ui(self):
        """初始化用户界面"""
        # 设置组件属性 - 确保标题栏有良好的可见性
        self.setStyleSheet("""
            HeaderWidget {
                background-color: #f0f0f0;  /* 浅灰色背景 */
                border-radius: 8px;
                border-bottom: 1px solid #d0d0d0;
            }
            QLabel {
                color: #000000;  /* 黑色文字确保最佳可见性 */
                background-color: transparent;
                font-weight: bold;
            }
            QPushButton {
                background-color: transparent;
            }
        """)

        # 创建主布局 - 优化：紧凑布局适配5%高度限制
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 2, 10, 2)  # 进一步减少边距适配5%高度
        main_layout.setSpacing(10)  # 减少间距

        # 左侧：Logo
        self._create_logo_section(main_layout)

        # 中间：产品名称
        self._create_title_section(main_layout)

        # 右侧：试用倒计时
        self._create_countdown_section(main_layout)

    def _create_logo_section(self, layout):
        """创建Logo区域"""
        # 优化：改为水平布局，减小logo尺寸以适配5%高度
        self.logo_label = QLabel()

        # 使用图标管理器获取Logo
        from utils.icon_manager import get_logo_pixmap
        from PyQt5.QtCore import QSize

        logo_pixmap = get_logo_pixmap(QSize(32, 32))  # 进一步缩小到32x32适配5%高度
        if not logo_pixmap.isNull():
            self.logo_label.setPixmap(logo_pixmap)
        else:
            # 如果没有logo文件，显示文字
            self.logo_label.setText("🔋")
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = QFont()
            font.setPointSize(16)  # 缩小字体适配5%高度
            self.logo_label.setFont(font)

        self.logo_label.setFixedSize(32, 32)  # 优化：缩小到32x32像素适配5%高度
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.logo_label)

    def _create_title_section(self, layout):
        """创建标题区域"""
        # 创建产品名称标签
        self.title_label = QLabel()
        app_name = self.config_manager.get('app.name', 'JCY5001AS鲸测云8路EIS阻抗筛选仪')
        app_version = self.config_manager.get('app.version', 'V0.92.42')
        title_text = f"{app_name} {app_version}"
        self.title_label.setText(title_text)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 设置产品名称字体 - 使用大字体确保可见性
        title_font = QFont()
        title_font.setPointSize(24)  # 使用24pt字体，确保在标题区域清晰可见
        title_font.setBold(True)
        self.title_label.setFont(title_font)

        # 设置产品名称样式 - 黑色字体，确保在浅色背景下清晰可见
        self.title_label.setStyleSheet("""
            color: #000000;
            font-weight: bold;
            background-color: transparent;
            padding: 5px;
        """)

        layout.addWidget(self.title_label)
        layout.setStretchFactor(self.title_label, 1)  # 标题区域占据剩余空间

    def _create_countdown_section(self, layout):
        """创建授权状态区域"""
        # 创建授权状态显示组件
        license_widget = QWidget()
        license_widget.setVisible(True)  # 显示授权状态区域

        license_layout = QHBoxLayout(license_widget)
        license_layout.setContentsMargins(5, 2, 5, 2)
        license_layout.setSpacing(8)

        # 授权状态显示区域
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(2)

        # 主状态显示 - 增大字体和改善可见性
        self.countdown_label = QLabel()
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        countdown_value_font = QFont()
        countdown_value_font.setPointSize(16)  # 增大字体从10pt到16pt
        countdown_value_font.setBold(True)
        self.countdown_label.setFont(countdown_value_font)
        # 设置明确的文字颜色，确保在浅色背景下可见
        self.countdown_label.setStyleSheet("color: #000000; font-weight: bold; background-color: transparent;")

        # 详细信息显示 - 增大字体和改善可见性
        self.expire_date_label = QLabel()
        self.expire_date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        expire_date_font = QFont()
        expire_date_font.setPointSize(12)  # 增大字体从8pt到12pt
        expire_date_font.setBold(True)
        self.expire_date_label.setFont(expire_date_font)
        # 设置明确的文字颜色，确保在浅色背景下可见
        self.expire_date_label.setStyleSheet("color: #333333; font-weight: bold; background-color: transparent;")

        status_layout.addWidget(self.countdown_label)
        status_layout.addWidget(self.expire_date_label)

        # 解锁按钮 - 增大尺寸和改善样式
        self.unlock_button = QPushButton("解锁")
        self.unlock_button.setFixedSize(60, 40)  # 增大按钮尺寸
        self.unlock_button.clicked.connect(self._on_unlock_requested)
        # 改善解锁按钮样式，确保在浅色背景下清晰可见
        self.unlock_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: 2px solid #d32f2f;
                border-radius: 6px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
                border-color: #b71c1c;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        self.unlock_button.setVisible(False)  # 默认隐藏

        license_layout.addWidget(status_widget)
        license_layout.addWidget(self.unlock_button)

        # 添加到主布局，显示授权状态区域
        layout.addWidget(license_widget)

    def _init_timer(self):
        """初始化定时器"""
        # 定时器线程修复: 确保在主线程中创建定时器
        from PyQt5.QtCore import QTimer
        from PyQt5.QtWidgets import QApplication

        # 检查是否在主线程中
        app = QApplication.instance()
        if app and app.thread() != self.thread():
            logger.warning("⚠️ 头部组件定时器不在主线程中创建，可能导致问题")

        # 创建定时器，每分钟更新一次授权状态
        self.countdown_timer = QTimer(self)  # 定时器线程修复: 指定父对象
        self.countdown_timer.timeout.connect(self._update_license_status)
        self.countdown_timer.start(60000)  # 60秒更新一次

    def _update_license_status(self):
        """更新授权状态显示"""
        try:
            if self.license_manager is None:
                self.countdown_label.setText("授权错误")
                self.countdown_label.setStyleSheet("color: #d32f2f; font-weight: bold; font-size: 16pt; background-color: transparent;")
                self.expire_date_label.setText("请联系供应商")
                self.expire_date_label.setStyleSheet("color: #d32f2f; font-weight: bold; font-size: 12pt; background-color: transparent;")
                self.unlock_button.setVisible(True)
                return

            # 获取授权状态
            status = self.license_manager.get_license_status()

            if status['is_licensed']:
                license_type = status.get('license_type', 'full')

                if license_type == 'temp':
                    # 临时授权
                    remaining_days = status.get('remaining_days', 0)
                    expire_date = status.get('expire_date', '')

                    self.countdown_label.setText(f"临时授权剩余{remaining_days}天")

                    # 显示到期日期
                    if expire_date:
                        expire_dt = datetime.fromisoformat(expire_date)
                        expire_str = expire_dt.strftime("%Y-%m-%d")
                        self.expire_date_label.setText(f"到期时间：{expire_str}")
                    else:
                        self.expire_date_label.setText("临时授权期内")

                    # 根据剩余时间设置颜色
                    if remaining_days <= 3:
                        # 紧急状态 - 红色
                        self.countdown_label.setStyleSheet("color: #d32f2f; font-weight: bold; font-size: 16pt; background-color: transparent;")
                        self.expire_date_label.setStyleSheet("color: #d32f2f; font-weight: bold; font-size: 12pt; background-color: transparent;")
                    elif remaining_days <= 7:
                        # 警告状态 - 橙色
                        self.countdown_label.setStyleSheet("color: #f57c00; font-weight: bold; font-size: 16pt; background-color: transparent;")
                        self.expire_date_label.setStyleSheet("color: #f57c00; font-weight: bold; font-size: 12pt; background-color: transparent;")
                    else:
                        # 正常状态 - 蓝色（区别于永久授权的绿色）
                        self.countdown_label.setStyleSheet("color: #1976d2; font-weight: bold; font-size: 16pt; background-color: transparent;")
                        self.expire_date_label.setStyleSheet("color: #1976d2; font-weight: bold; font-size: 12pt; background-color: transparent;")

                    self.unlock_button.setVisible(True)  # 临时授权期间仍显示解锁按钮
                else:
                    # 永久授权
                    self.countdown_label.setText("已授权")
                    self.countdown_label.setStyleSheet("color: #2e7d32; font-weight: bold; font-size: 16pt; background-color: transparent;")
                    self.expire_date_label.setText("无限制使用")
                    self.expire_date_label.setStyleSheet("color: #2e7d32; font-weight: bold; font-size: 12pt; background-color: transparent;")
                    self.unlock_button.setVisible(False)

            elif not status['is_trial_expired']:
                # 试用期内
                remaining_days = status['remaining_days']
                expire_date = status.get('expire_date', '')

                if remaining_days > 0:
                    self.countdown_label.setText(f"试用期剩余{remaining_days}天")
                else:
                    self.countdown_label.setText("试用期今日到期")

                # 显示到期日期
                if expire_date:
                    expire_dt = datetime.fromisoformat(expire_date)
                    expire_str = expire_dt.strftime("%Y-%m-%d")
                    self.expire_date_label.setText(f"到期时间：{expire_str}")
                else:
                    self.expire_date_label.setText("试用期内")

                # 根据剩余时间设置颜色，确保在浅色背景下清晰可见
                if remaining_days <= 3:
                    # 紧急状态 - 红色
                    self.countdown_label.setStyleSheet("color: #d32f2f; font-weight: bold; font-size: 16pt; background-color: transparent;")
                    self.expire_date_label.setStyleSheet("color: #d32f2f; font-weight: bold; font-size: 12pt; background-color: transparent;")
                elif remaining_days <= 7:
                    # 警告状态 - 橙色
                    self.countdown_label.setStyleSheet("color: #f57c00; font-weight: bold; font-size: 16pt; background-color: transparent;")
                    self.expire_date_label.setStyleSheet("color: #f57c00; font-weight: bold; font-size: 12pt; background-color: transparent;")
                else:
                    # 正常状态 - 绿色
                    self.countdown_label.setStyleSheet("color: #2e7d32; font-weight: bold; font-size: 16pt; background-color: transparent;")
                    self.expire_date_label.setStyleSheet("color: #333333; font-weight: bold; font-size: 12pt; background-color: transparent;")

                self.unlock_button.setVisible(False)

            else:
                # 试用期已到期
                self.countdown_label.setText("试用期已到期")
                self.countdown_label.setStyleSheet("color: #d32f2f; font-weight: bold; font-size: 16pt; background-color: transparent;")
                self.expire_date_label.setText("需要解锁码")
                self.expire_date_label.setStyleSheet("color: #d32f2f; font-weight: bold; font-size: 12pt; background-color: transparent;")
                self.unlock_button.setVisible(True)

                # 发送试用期到期信号
                self.trial_expired.emit()

        except Exception as e:
            logger.error(f"更新授权状态失败: {e}")
            self.countdown_label.setText("状态错误")
            self.countdown_label.setStyleSheet("color: #d32f2f; font-weight: bold; font-size: 16pt; background-color: transparent;")
            self.expire_date_label.setText("请重启软件")
            self.expire_date_label.setStyleSheet("color: #d32f2f; font-weight: bold; font-size: 12pt; background-color: transparent;")
            self.unlock_button.setVisible(True)

    def _on_unlock_requested(self):
        """处理解锁请求"""
        try:
            self.unlock_requested.emit()
        except Exception as e:
            logger.error(f"处理解锁请求失败: {e}")

    def get_remaining_days(self) -> int:
        """
        获取剩余试用天数

        Returns:
            剩余天数，如果已到期返回0
        """
        try:
            if self.license_manager:
                status = self.license_manager.get_license_status()
                return status.get('remaining_days', 0)
            else:
                return 0

        except Exception as e:
            logger.error(f"获取剩余天数失败: {e}")
            return 0

    def is_trial_expired(self) -> bool:
        """
        检查试用期是否已到期

        Returns:
            True如果已到期，False如果未到期
        """
        try:
            if self.license_manager:
                status = self.license_manager.get_license_status()
                return status.get('is_trial_expired', True)
            else:
                return True
        except Exception as e:
            logger.error(f"检查试用期状态失败: {e}")
            return True

    def is_licensed(self) -> bool:
        """
        检查软件是否已授权

        Returns:
            True如果已授权，False如果未授权
        """
        try:
            if self.license_manager:
                return self.license_manager.is_authorized()
            else:
                return False
        except Exception as e:
            logger.error(f"检查授权状态失败: {e}")
            return False

    def refresh_license_status(self):
        """刷新授权状态显示"""
        try:
            self._update_license_status()
            logger.info("授权状态已刷新")
        except Exception as e:
            logger.error(f"刷新授权状态失败: {e}")

    def get_license_manager(self):
        """获取授权管理器实例"""
        return self.license_manager
