# -*- coding: utf-8 -*-
"""
底部状态栏组件
显示设备连接状态、打印机状态等信息

Author: Jack
Date: 2025-01-27
"""

from PyQt5.QtWidgets import (
    QStatusBar, QLabel, QHBoxLayout, QWidget, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon
import logging

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager


class StatusBarWidget(QStatusBar):
    """底部状态栏组件"""

    # 信号定义
    device_status_changed = pyqtSignal(bool)  # 设备状态变更信号
    printer_status_changed = pyqtSignal(bool)  # 打印机状态变更信号

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        初始化状态栏

        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.device_connected = False
        self.printer_connected = False

        # 初始化界面
        self._init_ui()
        self._init_timers()

        logger.debug("底部状态栏组件初始化完成")

    def _init_ui(self):
        """初始化用户界面"""
        # 设置状态栏样式 - 优化高度，更紧凑
        self.setStyleSheet("""
            QStatusBar {
                background-color: #f0f0f0;
                border-top: 1px solid #d0d0d0;
                padding: 1px;
                max-height: 28px;
                min-height: 28px;
            }
            QLabel {
                padding: 1px 6px;
                margin: 0px 1px;
                font-size: 12px;
            }
        """)

        # 创建状态指示器容器 - 优化间距，更紧凑
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(3, 0, 3, 0)
        status_layout.setSpacing(10)

        # 设备连接状态
        self.device_status_label = QLabel()
        self._update_device_status(False)
        status_layout.addWidget(self.device_status_label)

        # 串口连接信息
        self.port_info_label = QLabel()
        self._update_port_info("")
        status_layout.addWidget(self.port_info_label)

        # 添加分隔线
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.VLine)
        separator1.setFrameShadow(QFrame.Sunken)
        separator1.setStyleSheet("color: #d0d0d0;")
        status_layout.addWidget(separator1)

        # 打印机连接状态
        self.printer_status_label = QLabel()
        self._update_printer_status(False)
        status_layout.addWidget(self.printer_status_label)

        # 添加分隔线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        separator2.setFrameShadow(QFrame.Sunken)
        separator2.setStyleSheet("color: #d0d0d0;")
        status_layout.addWidget(separator2)

        # 系统状态信息
        self.system_status_label = QLabel("系统就绪")
        self.system_status_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
        status_layout.addWidget(self.system_status_label)

        # 添加弹性空间
        status_layout.addStretch()

        # 时间显示
        self.time_label = QLabel()
        self.time_label.setStyleSheet("color: #666; font-family: 'Consolas', monospace;")
        status_layout.addWidget(self.time_label)

        # 将状态容器添加到状态栏
        self.addPermanentWidget(status_widget, 1)

        # 设置默认消息
        self.showMessage("就绪", 2000)

    def _init_timers(self):
        """初始化定时器"""
        # 定时器线程修复: 确保在主线程中创建定时器
        from PyQt5.QtCore import QTimer
        from PyQt5.QtWidgets import QApplication
        
        # 检查是否在主线程中
        app = QApplication.instance()
        if app and app.thread() != self.thread():
            logger.warning("⚠️ 状态栏定时器不在主线程中创建，可能导致问题")
        
        # 时间更新定时器
        self.time_timer = QTimer(self)  # 定时器线程修复: 指定父对象
        self.time_timer.timeout.connect(self._update_time)
        self.time_timer.start(1000)  # 每秒更新时间

        # 设备状态检查定时器
        self.status_timer = QTimer(self)  # 定时器线程修复: 指定父对象
        self.status_timer.timeout.connect(self._check_device_status)
        self.status_timer.start(5000)  # 每5秒检查一次设备状态

        # 立即更新一次时间
        self._update_time()

    def _update_time(self):
        """更新时间显示"""
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(current_time)

    def _check_device_status(self):
        """检查设备状态"""
        # 设备状态检查由通信管理器负责，此处不需要额外检查
        pass

    def _update_device_status(self, connected: bool):
        """更新设备状态显示"""
        if connected:
            self.device_status_label.setText("🟢 设备已连接")
            self.device_status_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
        else:
            self.device_status_label.setText("🔴 设备未连接")
            self.device_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")

    def _update_port_info(self, port: str):
        """更新串口信息显示"""
        if port:
            self.port_info_label.setText(f"📡 已连接 {port}")  # 功能优化：简化显示格式，更清晰
            self.port_info_label.setStyleSheet("color: #1976d2; font-weight: bold;")
            logger.debug(f"串口信息已更新: 已连接 {port}")  # 功能优化：添加调试日志
        else:
            self.port_info_label.setText("📡 未连接")  # 功能优化：简化显示格式
            self.port_info_label.setStyleSheet("color: #757575; font-weight: normal;")
            logger.debug("串口信息已更新: 未连接")  # 功能优化：添加调试日志

    def _update_printer_status(self, connected: bool):
        """更新打印机状态显示"""
        if connected:
            self.printer_status_label.setText("🖨️ 打印机就绪")
            self.printer_status_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
        else:
            self.printer_status_label.setText("🖨️ 打印机离线")
            self.printer_status_label.setStyleSheet("color: #f57c00; font-weight: bold;")

    def set_device_status(self, connected: bool, port: str = ""):
        """
        设置设备连接状态

        Args:
            connected: 是否连接
            port: 连接的串口号
        """
        # 功能优化：无论状态是否变化都更新显示，确保实时更新
        old_connected = self.device_connected
        self.device_connected = connected
        self._update_device_status(connected)

        # 功能优化：总是更新串口信息显示，确保实时反映当前状态
        self._update_port_info(port if connected else "")

        # 只在状态真正变化时发送信号和显示消息
        if old_connected != connected:
            self.device_status_changed.emit(connected)

            if connected:
                # 优化只在有端口信息时显示详细信息，避免无意义的连接成功日志
                if port:
                    self.showMessage(f"设备连接成功 ({port})", 3000)
                    logger.info(f"设备连接成功: {port}")
                else:
                    logger.debug("设备状态更新为已连接（无端口信息）")
            else:
                self.showMessage("设备连接断开", 3000)
                logger.info("设备连接断开")
        else:
            # 功能优化：即使状态未变化也记录调试信息，便于排查问题
            logger.debug(f"设备状态保持: {'已连接' if connected else '未连接'} {port}")

    def set_port_info(self, port: str):
        """
        设置串口信息显示

        Args:
            port: 串口号
        """
        self._update_port_info(port)

    def set_printer_status(self, connected: bool):
        """
        设置打印机连接状态

        Args:
            connected: 是否连接
        """
        if self.printer_connected != connected:
            self.printer_connected = connected
            self._update_printer_status(connected)
            self.printer_status_changed.emit(connected)

            if connected:
                self.showMessage("打印机连接成功", 3000)
                logger.info("打印机连接成功")
            else:
                self.showMessage("打印机连接断开", 3000)
                logger.warning("打印机连接断开")

    def set_system_status(self, status: str, status_type: str = "info"):
        """
        设置系统状态信息

        Args:
            status: 状态文本
            status_type: 状态类型 ("info", "warning", "error", "success")
        """
        self.system_status_label.setText(status)

        # 根据状态类型设置颜色
        color_map = {
            "info": "#1976d2",
            "warning": "#f57c00",
            "error": "#d32f2f",
            "success": "#2e7d32"
        }

        color = color_map.get(status_type, "#1976d2")
        self.system_status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        # 在状态栏显示临时消息
        self.showMessage(status, 3000)

    def show_test_status(self, testing: bool):
        """
        显示测试状态

        Args:
            testing: 是否正在测试
        """
        if testing:
            self.set_system_status("正在测试...", "info")
        else:
            self.set_system_status("测试停止", "warning")

    def set_battery_status(self, channel_num: int, status: str, voltage: float = 0.0):
        """
        设置电池状态信息

        Args:
            channel_num: 通道号
            status: 电池状态 ("connected", "removed", "unknown")
            voltage: 电池电压
        """
        try:
            # 根据状态设置显示文本和颜色
            if status == "connected":
                status_text = f"通道{channel_num}: 电池已连接"
                if voltage > 0:
                    status_text += f" ({voltage:.2f}V)"
                self.set_system_status(status_text, "success")
            elif status == "removed":
                status_text = f"通道{channel_num}: 电池已移除"
                if voltage > 0:
                    status_text += f" ({voltage:.2f}V)"
                self.set_system_status(status_text, "warning")
            else:  # unknown
                status_text = f"通道{channel_num}: 电池状态未知"
                if voltage > 0:
                    status_text += f" ({voltage:.2f}V)"
                self.set_system_status(status_text, "info")

            logger.debug(f"状态栏电池状态更新: {status_text}")

        except Exception as e:
            logger.error(f"设置电池状态失败: {e}")

    def show_progress_message(self, message: str):
        """
        显示进度消息

        Args:
            message: 消息内容
        """
        self.showMessage(message, 2000)

    def get_device_status(self) -> bool:
        """
        获取设备连接状态

        Returns:
            设备是否连接
        """
        return self.device_connected

    def get_printer_status(self) -> bool:
        """
        获取打印机连接状态

        Returns:
            打印机是否连接
        """
        return self.printer_connected

    def is_system_ready(self) -> bool:
        """
        检查系统是否就绪

        Returns:
            系统是否就绪（设备和打印机都连接）
        """
        return self.device_connected and self.printer_connected