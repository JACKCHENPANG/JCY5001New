# -*- coding: utf-8 -*-
"""
设备连接管理器
负责设备连接状态管理、连接控制等功能

从MainWindow中提取的设备连接管理功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


class DeviceConnectionManager(QObject):
    """
    设备连接管理器

    职责：
    - 设备连接状态监控
    - 连接建立和断开
    - 连接状态通知
    - 设备信息获取
    """

    # 信号定义
    connection_status_changed = pyqtSignal(bool)  # 连接状态变更
    device_info_updated = pyqtSignal(dict)  # 设备信息更新

    def __init__(self, main_window, config_manager, comm_manager):
        """
        初始化设备连接管理器

        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
            comm_manager: 通信管理器
        """
        super().__init__()

        self.main_window = main_window
        self.config_manager = config_manager
        self.comm_manager = comm_manager

        # 连接状态
        self.is_connected = False
        self.device_info = {}
        self.current_port = ""  # 当前连接的端口

        # 连接监控定时器
        self.connection_monitor_timer = QTimer()
        self.connection_monitor_timer.timeout.connect(self._check_connection_status)
        self.connection_monitor_timer.start(5000)  # 5秒检查一次

        # 连接超时定时器
        self.connection_timeout_timer = QTimer()
        self.connection_timeout_timer.setSingleShot(True)  # 只触发一次
        self.connection_timeout_timer.timeout.connect(self._handle_connection_timeout)

        # 退出时停止定时器，避免 KeyboardInterrupt
        try:
            if main_window and hasattr(main_window, 'destroyed'):
                main_window.destroyed.connect(self._stop_connection_timers)
        except Exception:
            pass

        # 连接状态标志
        self._is_connecting = False
        self._auto_connect_retry_count = 0
        self._max_auto_connect_retries = 3  # 最多重试3次

        # 设置通信管理器回调
        self.comm_manager.set_status_callback(self._on_connection_status_changed)

        logger.debug("设备连接管理器初始化完成")

    def connect_device(self) -> bool:
        """
        连接设备

        Returns:
            是否连接成功
        """
        try:
            logger.info("开始连接设备...")

            # 尝试连接
            if self.comm_manager.connect():
                self.is_connected = True

                # 异步获取设备信息，避免阻塞
                QTimer.singleShot(100, self._update_device_info)

                # 发送连接成功信号
                self.connection_status_changed.emit(True)

                logger.info("✅ 设备连接成功")
                return True
            else:
                self.is_connected = False
                self.connection_status_changed.emit(False)

                logger.error("❌ 设备连接失败")
                return False

        except Exception as e:
            logger.error(f"连接设备异常: {e}")
            self.is_connected = False
            self.connection_status_changed.emit(False)
            return False

    def disconnect_device(self):
        """断开设备连接"""
        try:
            logger.info("断开设备连接...")

            # 断开连接
            self.comm_manager.disconnect()
            self.is_connected = False

            # 清空设备信息
            self.device_info.clear()

            # 发送断开连接信号
            self.connection_status_changed.emit(False)
            self.device_info_updated.emit({})

            logger.info("✅ 设备连接已断开")

        except Exception as e:
            logger.error(f"断开设备连接异常: {e}")

    def _on_connection_status_changed(self, connected: bool):
        """连接状态变更回调"""
        try:
            if self.is_connected != connected:
                self.is_connected = connected

                if connected:
                    logger.info("📡 设备连接已建立")
                    self._update_device_info()
                else:
                    logger.info("📡 设备连接已断开")
                    self.device_info.clear()
                    self.device_info_updated.emit({})

                # 发送状态变更信号
                self.connection_status_changed.emit(connected)

        except Exception as e:
            logger.error(f"处理连接状态变更失败: {e}")

    def _check_connection_status(self):
        """检查连接状态（防中断版）"""
        try:
            # 执行健康检查
            is_alive = self.comm_manager.perform_health_check()

            if self.is_connected != is_alive:
                self._on_connection_status_changed(is_alive)

        except KeyboardInterrupt:
            logger.info("设备连接状态检查被中断，停止检查定时器")
            try:
                if hasattr(self, 'connection_monitor_timer') and self.connection_monitor_timer.isActive():
                    self.connection_monitor_timer.stop()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"检查连接状态失败: {e}")

    def _update_device_info(self):
        """更新设备信息（非阻塞方式）"""
        try:
            if not self.is_connected:
                return

            logger.debug("开始获取设备信息...")

            # 使用简单的设备信息，避免调用可能阻塞的方法
            try:
                # 获取实际连接的端口信息
                actual_port = self.config_manager.get('device.connection.port', 'Unknown')
                if hasattr(self.comm_manager, 'port'):
                    actual_port = self.comm_manager.port
                elif self.current_port:
                    actual_port = self.current_port

                # 创建基本设备信息，不调用可能阻塞的get_device_info()
                device_info = {
                    'device_type': 'JCY5001AS',
                    'connection_status': 'connected',
                    'port': actual_port,
                    'baudrate': self.config_manager.get('device.connection.baudrate', 115200),
                    'connected_at': str(QTimer().remainingTime())  # 简单的时间戳
                }

                # 更新当前端口信息
                self.current_port = actual_port

                self.device_info = device_info
                self.device_info_updated.emit(device_info)

                logger.info(f"设备信息已更新: {device_info.get('device_type', 'Unknown')}")

            except Exception as e:
                logger.error(f"获取设备信息异常: {e}")

        except Exception as e:
            logger.error(f"更新设备信息失败: {e}")

    def get_connection_status(self) -> bool:
        """
        获取连接状态

        Returns:
            是否已连接
        """
        return self.is_connected

    def get_device_info(self) -> dict:
        """
        获取设备信息

        Returns:
            设备信息字典
        """
        return self.device_info.copy()

    def auto_connect(self) -> bool:
        """
        安全的异步自动连接设备（完全非阻塞）

        Returns:
            是否启动自动连接
        """
        try:
            # 检查是否启用自动连接
            auto_connect_enabled = self.config_manager.get('device.auto_connect', True)

            if not auto_connect_enabled:
                logger.info("自动连接已禁用")
                return False

            # 重置重试计数
            self._auto_connect_retry_count = 0

            # 获取连接配置
            port = self.config_manager.get('device.connection.port', 'COM16')

            logger.info(f"准备安全异步自动连接设备: {port} (最多重试{self._max_auto_connect_retries}次)")

            # 延迟更长时间启动自动连接，确保UI完全加载完成
            QTimer.singleShot(2000, self._safe_auto_connect)  # 2秒后执行

            return True

        except Exception as e:
            logger.error(f"启动自动连接失败: {e}")
            return False

    def _safe_auto_connect(self):
        """安全的自动连接启动方法"""
        try:
            logger.info("开始安全自动连接流程...")

            # 检查UI是否已经完全加载
            if not self.main_window or not self.main_window.isVisible():
                logger.warning("主窗口未完全加载，延迟自动连接")
                QTimer.singleShot(1000, self._safe_auto_connect)  # 再等1秒
                return

            # 启动连接尝试
            self._perform_auto_connect()

        except Exception as e:
            logger.error(f"安全自动连接启动失败: {e}")

    def _perform_auto_connect(self):
        """执行实际的自动连接（安全版本，带超时机制和重试限制）"""
        try:
            # 检查是否已经在连接中
            if self._is_connecting:
                logger.warning("自动连接已在进行中，跳过重复连接")
                return

            # 检查重试次数
            if self._auto_connect_retry_count >= self._max_auto_connect_retries:
                logger.warning(f"⚠️ 自动连接已达到最大重试次数({self._max_auto_connect_retries})，停止尝试")
                self._is_connecting = False
                return

            self._auto_connect_retry_count += 1
            logger.info(f"开始执行安全自动连接... (第{self._auto_connect_retry_count}/{self._max_auto_connect_retries}次尝试)")
            self._is_connecting = True

            # 启动2秒超时定时器（进一步缩短超时时间）
            self.connection_timeout_timer.start(2000)  # 2秒超时

            # 使用更安全的连接方法
            success = self._safe_connect_device()

            # 停止超时定时器
            self.connection_timeout_timer.stop()
            self._is_connecting = False

            if success:
                logger.info("✅ 安全自动连接成功")
                self._auto_connect_retry_count = 0  # 重置重试计数
            else:
                logger.warning(f"⚠️ 安全自动连接失败 (第{self._auto_connect_retry_count}次尝试)")

                # 如果还有重试机会，延迟后重试
                if self._auto_connect_retry_count < self._max_auto_connect_retries:
                    logger.info(f"将在3秒后进行第{self._auto_connect_retry_count + 1}次重试...")
                    QTimer.singleShot(3000, self._perform_auto_connect)  # 3秒后重试
                else:
                    logger.warning("❌ 安全自动连接已达到最大重试次数，停止尝试")

        except Exception as e:
            # 确保清理状态
            if hasattr(self, 'connection_timeout_timer'):
                self.connection_timeout_timer.stop()
            self._is_connecting = False
            logger.error(f"执行安全自动连接异常: {e}")

            # 异常情况下也要检查重试
            if self._auto_connect_retry_count < self._max_auto_connect_retries:
                logger.info(f"异常后将在3秒后重试...")
                QTimer.singleShot(3000, self._perform_auto_connect)

    def _safe_connect_device(self) -> bool:
        """
        安全的设备连接方法（避免阻塞）

        Returns:
            是否连接成功
        """
        try:
            logger.debug("开始安全设备连接...")

            # 尝试连接（这里可能会阻塞，但有超时保护）
            if self.comm_manager.connect():
                self.is_connected = True

                # 获取实际连接的端口信息
                actual_port = self.config_manager.get('device.connection.port', 'Unknown')
                if hasattr(self.comm_manager, 'get_actual_port'):
                    try:
                        actual_port = self.comm_manager.get_actual_port()
                    except:
                        pass
                elif hasattr(self.comm_manager, 'port'):
                    actual_port = self.comm_manager.port

                # 不调用可能阻塞的设备信息获取，使用基本信息
                self.device_info = {
                    'device_type': 'JCY5001AS',
                    'connection_status': 'connected',
                    'port': actual_port,
                    'baudrate': self.config_manager.get('device.connection.baudrate', 115200),
                    'connected_at': str(QTimer().remainingTime())
                }

                # 更新当前端口信息
                self.current_port = actual_port

                # 发送连接成功信号
                self.connection_status_changed.emit(True)

                # 发送设备信息更新信号
                self.device_info_updated.emit(self.device_info)

                logger.info("✅ 安全设备连接成功")
                return True
            else:
                self.is_connected = False
                self.connection_status_changed.emit(False)

                logger.debug("❌ 安全设备连接失败")
                return False

        except Exception as e:
            logger.error(f"安全连接设备异常: {e}")
            self.is_connected = False
            if hasattr(self, 'connection_status_changed'):
                self.connection_status_changed.emit(False)
            return False

    def _handle_connection_timeout(self):
        """处理连接超时"""
        try:
            logger.warning(f"⏰ 自动连接超时（3秒），第{self._auto_connect_retry_count}次尝试失败")

            # 强制断开连接
            if self.is_connected:
                self.disconnect_device()

            # 重置连接状态
            self._is_connecting = False
            self.is_connected = False

            # 发送断开连接信号
            self.connection_status_changed.emit(False)

            # 检查是否需要重试
            if self._auto_connect_retry_count < self._max_auto_connect_retries:
                logger.info(f"超时后将在2秒后进行第{self._auto_connect_retry_count + 1}次重试...")
                QTimer.singleShot(2000, self._perform_auto_connect)  # 2秒后重试
            else:
                logger.warning("❌ 连接超时且已达到最大重试次数，停止尝试")

            logger.info("✅ 连接超时处理完成，UI不会被阻塞")

        except Exception as e:
            logger.error(f"处理连接超时异常: {e}")
            # 确保重置状态
            self._is_connecting = False

    def show_connection_dialog(self):
        """显示连接设置对话框"""
        try:
            # 使用设置对话框中的设备设置页面
            from ui.dialogs.settings_dialog import SettingsDialog

            dialog = SettingsDialog(self.config_manager, self.main_window)
            dialog.switch_to_tab("设备设置")  # 切换到设备设置页面

            if dialog.exec_() == dialog.Accepted:
                # 连接设置已更改，尝试重新连接
                if self.is_connected:
                    self.disconnect_device()

                # 异步重新连接
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(200, self._perform_auto_connect)

        except Exception as e:
            logger.error(f"显示连接对话框失败: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self.main_window,
                '错误',
                f'显示连接对话框失败：\n{e}'
            )

    def test_connection(self) -> bool:
        """
        测试连接

        Returns:
            连接是否正常
        """
        try:
            if not self.is_connected:
                return False

            # 执行连接测试
            return self.comm_manager.is_device_connected()

        except Exception as e:
            logger.error(f"测试连接失败: {e}")
            return False

    def get_connection_statistics(self) -> dict:
        """
        获取连接统计信息

        Returns:
            连接统计信息字典
        """
        try:
            if not self.is_connected:
                return {
                    'status': '未连接',
                    'connection_time': 0,
                    'success_rate': 0.0
                }

            # 获取通信管理器状态
            status_info = self.comm_manager.get_status_info()

            return {
                'status': '已连接' if self.is_connected else '未连接',
                'device_info': self.device_info,
                'connection_info': status_info.get('connection_info', {}),
                'communication_stats': status_info
            }

        except Exception as e:
            logger.error(f"获取连接统计信息失败: {e}")
            return {}

    def reconnect_device(self) -> bool:
        """
        重新连接设备

        Returns:
            是否重连成功
        """
        try:
            logger.info("重新连接设备...")

            # 先断开现有连接
            if self.is_connected:
                self.disconnect_device()

            # 等待一段时间
            import time
            time.sleep(1)

            # 重新连接
            return self.connect_device()

        except Exception as e:
            logger.error(f"重新连接设备失败: {e}")
            return False

    def reconnect_with_new_port(self, new_port: str) -> bool:
        """
        使用新端口重新连接设备

        Args:
            new_port: 新的串口号

        Returns:
            是否连接成功
        """
        try:
            logger.info(f"使用新端口重新连接设备: {new_port}")

            # 先断开现有连接
            if self.is_connected:
                self.disconnect_device()

            # 等待端口完全释放
            import time
            time.sleep(0.5)

            # 更新配置中的端口
            self.config_manager.set('device.connection.port', new_port)

            # 如果通信管理器支持端口切换，使用专门的方法
            if hasattr(self.comm_manager, 'reconnect_with_new_port'):
                success = self.comm_manager.reconnect_with_new_port(new_port)
            else:
                # 否则重新初始化通信管理器
                from backend.communication_manager import CommunicationManager

                new_config = {
                    'port': new_port,
                    'baudrate': self.config_manager.get('device.connection.baudrate', 115200),
                    'timeout': self.config_manager.get('device.connection.timeout', 2.0),
                    'device_address': 1
                }

                self.comm_manager = CommunicationManager(new_config)
                self.comm_manager.set_status_callback(self._on_connection_status_changed)

                success = self.connect_device()

            if success:
                logger.info(f"✅ 端口切换成功: {new_port}")
                return True
            else:
                logger.error(f"❌ 端口切换失败: {new_port}")
                return False

        except Exception as e:
            logger.error(f"端口切换异常: {e}")
            return False

    def cleanup(self):
        """清理资源"""
        try:
            # 停止所有定时器
            if self.connection_monitor_timer.isActive():
                self.connection_monitor_timer.stop()

            if self.connection_timeout_timer.isActive():
                self.connection_timeout_timer.stop()

            # 重置连接状态
            self._is_connecting = False

            # 断开连接
            if self.is_connected:
                self.disconnect_device()

            logger.info("设备连接管理器资源已清理")

        except Exception as e:
            logger.error(f"清理设备连接管理器资源失败: {e}")

    def get_manager_info(self) -> dict:
        """
        获取管理器信息

        Returns:
            管理器信息字典
        """
        return {
            'is_connected': self.is_connected,
            'device_info': self.device_info,
            'monitor_interval': 5000,
            'auto_connect_enabled': self.config_manager.get('device.auto_connect', True)
        }

    def sync_status_to_settings(self, settings_widget):
        """
        同步连接状态到设置页面

        Args:
            settings_widget: 设备设置页面组件
        """
        try:
            if hasattr(settings_widget, 'connection_status_label'):
                if self.is_connected:
                    settings_widget.connection_status_label.setText("已连接")
                    settings_widget.connection_status_label.setStyleSheet("color: green; font-weight: bold;")
                else:
                    settings_widget.connection_status_label.setText("未连接")
                    settings_widget.connection_status_label.setStyleSheet("color: red; font-weight: bold;")

                logger.debug(f"已同步连接状态到设置页面: {'已连接' if self.is_connected else '未连接'}")

        except Exception as e:
            logger.error(f"同步状态到设置页面失败: {e}")

    def _stop_connection_timers(self, *args, **kwargs):
        """停止所有连接相关定时器，防止退出时触发回调"""
        try:
            if hasattr(self, 'connection_monitor_timer') and self.connection_monitor_timer.isActive():
                self.connection_monitor_timer.stop()
                logger.debug("设备连接监控定时器已停止")
            if hasattr(self, 'connection_timeout_timer') and self.connection_timeout_timer.isActive():
                self.connection_timeout_timer.stop()
                logger.debug("设备连接超时定时器已停止")
        except Exception:
            pass