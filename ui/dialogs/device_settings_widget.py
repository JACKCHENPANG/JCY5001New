# -*- coding: utf-8 -*-
"""
设备设置页面 - 重构版本
将原始948行的大文件拆分为6个专门管理器类，遵循单一职责原则

重构结构：
├── ImpedanceDeviceManager - 阻抗测试仪设备管理
├── BarcodeScannerManager - 扫码枪管理  
├── PrinterManager - 打印机管理
├── LoggingSettingsManager - 日志设置管理
├── DeviceSettingsUIManager - 设备设置界面管理
└── DeviceSettingsWidget - 主协调器

Author: Jack
Date: 2025-01-27
Refactored: 2025-06-04
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QComboBox, QSpinBox,
    QPushButton, QTextEdit, QCheckBox, QProgressBar,
    QListWidget, QListWidgetItem, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QObject
from PyQt5.QtGui import QFont
import logging
import serial.tools.list_ports

logger = logging.getLogger(__name__)

# 打印机相关导入
try:
    import win32print
    import win32ui
    PRINTER_SUPPORT = True
except ImportError:
    PRINTER_SUPPORT = False
    logger.warning("打印机支持模块未安装，打印机功能将受限")

from utils.config_manager import ConfigManager


class ImpedanceDeviceManager(QObject):
    """阻抗测试仪设备管理器"""
    
    # 信号定义
    settings_changed = pyqtSignal()
    connection_status_changed = pyqtSignal(bool, str)  # 连接状态, 端口
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._loading = False
        
        # 控件引用（由UI管理器设置）
        self.serial_port_combo = None
        self.serial_baudrate_combo = None
        self.connection_timeout_spin = None
        self.auto_connect_check = None
        self.auto_reconnect_check = None
        self.reconnect_interval_spin = None
        self.connection_status_label = None
        self.refresh_serial_button = None
        self.test_connection_button = None
        
        logger.debug("阻抗设备管理器初始化完成")
    
    def set_ui_controls(self, controls: dict):
        """设置UI控件引用"""
        self.serial_port_combo = controls.get('serial_port_combo')
        self.serial_baudrate_combo = controls.get('serial_baudrate_combo')
        self.connection_timeout_spin = controls.get('connection_timeout_spin')
        self.auto_connect_check = controls.get('auto_connect_check')
        self.auto_reconnect_check = controls.get('auto_reconnect_check')
        self.reconnect_interval_spin = controls.get('reconnect_interval_spin')
        self.connection_status_label = controls.get('connection_status_label')
        self.refresh_serial_button = controls.get('refresh_serial_button')
        self.test_connection_button = controls.get('test_connection_button')
        
        # 连接信号
        self._connect_signals()
    
    def _connect_signals(self):
        """连接信号"""
        if self.serial_port_combo:
            self.serial_port_combo.currentTextChanged.connect(self._on_setting_changed)
        if self.serial_baudrate_combo:
            self.serial_baudrate_combo.currentTextChanged.connect(self._on_setting_changed)
        if self.connection_timeout_spin:
            self.connection_timeout_spin.valueChanged.connect(self._on_setting_changed)
        if self.auto_connect_check:
            self.auto_connect_check.toggled.connect(self._on_setting_changed)
        if self.auto_reconnect_check:
            self.auto_reconnect_check.toggled.connect(self._on_auto_reconnect_changed)
        if self.reconnect_interval_spin:
            self.reconnect_interval_spin.valueChanged.connect(self._on_setting_changed)
        if self.refresh_serial_button:
            self.refresh_serial_button.clicked.connect(self._manual_refresh_serial_ports)
        if self.test_connection_button:
            self.test_connection_button.clicked.connect(self._test_device_connection)
    
    def _on_auto_reconnect_changed(self, checked: bool):
        """自动重连开关变更处理"""
        if self.reconnect_interval_spin:
            self.reconnect_interval_spin.setEnabled(checked)
        self._on_setting_changed()
    
    def _on_setting_changed(self):
        """设置变更处理"""
        if not self._loading:
            self.settings_changed.emit()
    
    def _manual_refresh_serial_ports(self):
        """手动刷新串口列表（显示提示信息）"""
        self._manual_refresh = True
        self._refresh_serial_ports()
        self._manual_refresh = False
    
    def _refresh_serial_ports(self):
        """刷新串口列表"""
        try:
            if not self.serial_port_combo:
                return
                
            # 获取当前选择的串口
            current_port = self.serial_port_combo.currentText()
            
            # 清空列表
            self.serial_port_combo.clear()
            
            # 扫描可用串口
            available_ports = []
            ports = serial.tools.list_ports.comports()
            
            for port in ports:
                port_name = port.device
                port_desc = port.description
                available_ports.append(f"{port_name} - {port_desc}")
                logger.debug(f"发现串口: {port_name} - {port_desc}")
            
            if available_ports:
                # 添加发现的串口
                self.serial_port_combo.addItems(available_ports)
                
                # 尝试恢复之前的选择
                for i, port_info in enumerate(available_ports):
                    if current_port in port_info:
                        self.serial_port_combo.setCurrentIndex(i)
                        break
                
                # 只在手动点击刷新按钮时才显示提示
                if hasattr(self, '_manual_refresh') and self._manual_refresh:
                    QMessageBox.information(
                        self.parent(), "串口刷新",
                        f"发现 {len(available_ports)} 个可用串口"
                    )
            else:
                # 没有发现串口，添加默认选项
                self.serial_port_combo.addItems([
                    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6",
                    "COM7", "COM8", "COM9", "COM10", "COM11", "COM12",
                    "COM13", "COM14", "COM15", "COM16"
                ])
                self.serial_port_combo.setCurrentText("COM13")
                
                # 只在手动点击刷新按钮时才显示提示
                if hasattr(self, '_manual_refresh') and self._manual_refresh:
                    QMessageBox.warning(
                        self.parent(), "串口刷新",
                        "未发现可用串口，已加载默认串口列表"
                    )
            
            logger.info(f"串口列表刷新完成，发现 {len(available_ports)} 个串口")
            
        except Exception as e:
            logger.error(f"刷新串口列表失败: {e}")
            QMessageBox.critical(self.parent(), "错误", f"刷新串口列表失败：\n{e}")
    
    def _test_device_connection(self):
        """测试设备连接"""
        if not self.serial_port_combo or not self.test_connection_button:
            return
            
        port_text = self.serial_port_combo.currentText().strip()
        if not port_text:
            QMessageBox.warning(self.parent(), "警告", "请先选择串口端口！")
            return
        
        # 提取串口名称（如果包含描述信息）
        port = port_text.split(' - ')[0] if ' - ' in port_text else port_text
        
        # 实际连接测试
        self.test_connection_button.setEnabled(False)
        self.test_connection_button.setText("测试中...")
        
        try:
            # 尝试实际连接并获取设备信息
            baudrate = int(self.serial_baudrate_combo.currentText())
            timeout = self.connection_timeout_spin.value()

            # 创建临时通信管理器进行测试
            from backend.communication_manager import CommunicationManager as ModbusRTUManager

            # 创建测试配置，使用更短的超时时间
            test_config = {
                'port': port,
                'baudrate': baudrate,
                'timeout': min(timeout, 2.0),  # 限制最大超时时间
                'device_address': 1,
                'retry_count': 1,  # 减少重试次数，加快测试速度
                'retry_delay': 0.05,
                'write_timeout': 0.5,  # 添加写入超时
                'inter_byte_timeout': 0.1  # 添加字节间超时
            }

            test_comm = None
            try:
                test_comm = ModbusRTUManager(test_config)
                logger.debug(f"创建测试通信管理器: {port}")

                # 尝试连接
                if test_comm.connect():
                    logger.debug(f"串口 {port} 物理连接成功")

                    # 等待连接稳定
                    import time
                    time.sleep(0.1)

                    # 核心测试：获取设备信息（主要是通道数量）
                    logger.info(f"开始测试串口 {port} 的设备通信...")
                    device_info = self._get_device_info(test_comm)

                    # 如果能执行到这里，说明通道数读取成功，连接测试通过
                    channel_count = device_info.get('通道数', '0')
                    connection_quality = device_info.get('连接质量', '1/3')

                    if self.connection_status_label:
                        status_text = f"连接成功 - {channel_count}通道设备 (质量: {connection_quality})"
                        self.connection_status_label.setText(status_text)
                        self.connection_status_label.setStyleSheet("color: green; font-weight: bold;")

                    # 保存成功连接的串口
                    self.config_manager.set('device.connection.last_port', port)

                    # 先通知主窗口断开当前连接，避免端口冲突
                    self._notify_main_window_disconnect()

                    # 等待主窗口完全断开
                    import time
                    time.sleep(0.5)

                    # 发送连接状态变更信号
                    self.connection_status_changed.emit(True, port)

                    logger.info(f"✅ 串口 {port} 连接测试成功，通道数: {channel_count}，连接质量: {connection_quality}")

                    # 显示连接成功信息
                    info_text = f"串口 {port} 连接成功！\n\n设备信息：\n"
                    for key, value in device_info.items():
                        info_text += f"• {key}: {value}\n"
                    info_text += f"\n✅ 设备通信正常，成功读取到 {channel_count} 个通道。"
                    info_text += "\n✅ 连接设置已保存，设备参数将在开始测试时自动下发。"

                    # 获取合适的父窗口
                    parent_widget = None
                    if hasattr(self, 'parent') and callable(self.parent):
                        parent_widget = self.parent()
                        while parent_widget and not isinstance(parent_widget, QWidget):
                            parent_widget = getattr(parent_widget, 'parent', lambda: None)()

                    QMessageBox.information(parent_widget, "连接成功", info_text)
                else:
                    raise Exception("无法建立串口物理连接")

            finally:
                # 确保断开连接
                if test_comm:
                    try:
                        test_comm.disconnect()
                        logger.debug(f"测试连接已断开: {port}")
                    except Exception as e:
                        logger.warning(f"断开测试连接失败: {e}")
            
        except Exception as e:
            if self.connection_status_label:
                self.connection_status_label.setText("连接失败")
                self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
            # 获取合适的父窗口
            parent_widget = None
            if hasattr(self, 'parent') and callable(self.parent):
                parent_widget = self.parent()
                while parent_widget and not isinstance(parent_widget, QWidget):
                    parent_widget = getattr(parent_widget, 'parent', lambda: None)()

            QMessageBox.warning(parent_widget, "连接测试", f"串口 {port} 连接失败：\n{e}")
            
        finally:
            self.test_connection_button.setEnabled(True)
            self.test_connection_button.setText("测试连接")

    def _get_device_info(self, comm_manager) -> dict:
        """获取设备信息"""
        try:
            device_info = {
                '设备型号': 'JCY5001AS',
                '通道数': '0',  # 默认为0，只有成功读取才更新
                '连接状态': '已连接'
            }

            # 核心测试：读取通道数量（这是判断连接成功的关键指标）
            channel_count_success = False
            try:
                logger.debug("开始测试设备通信：读取通道数量...")
                # 测试基本的Modbus通信 - 读取通道数（更可靠的寄存器）
                channel_count = comm_manager.get_channel_count()
                logger.debug(f"通道数量查询结果: {channel_count}")

                if channel_count > 0 and channel_count <= 16:  # 合理的通道数范围
                    device_info['通道数'] = str(channel_count)
                    channel_count_success = True
                    logger.info(f"✅ 成功读取设备通道数: {channel_count}")
                else:
                    logger.error(f"❌ 通道数读取异常: {channel_count}，期望值: 1-16")
                    raise Exception(f"设备返回异常通道数: {channel_count}")
            except Exception as e:
                logger.error(f"❌ 读取通道数失败: {e}")
                # 通道数读取失败是连接测试失败的关键指标
                raise Exception(f"设备通信失败：无法读取通道数量 - {e}")

            # 如果通道数读取成功，继续其他测试（这些是附加信息，失败不影响连接判断）

            # 附加测试1：尝试读取固件版本（失败不影响连接判断）
            try:
                logger.debug("附加测试：读取设备固件版本...")
                if hasattr(comm_manager, 'data_manager'):
                    device_data = comm_manager.data_manager.read_device_info()
                    if device_data and 'status' in device_data and device_data['status'] != '错误':
                        device_info['固件版本'] = "已连接"
                        logger.debug("✅ 通过数据管理器成功读取设备信息")
                    else:
                        device_info['固件版本'] = "读取失败"
                        logger.debug("⚠️ 数据管理器读取失败")
                else:
                    device_info['固件版本'] = "接口不支持"
                    logger.debug("⚠️ 通信管理器不支持数据管理器接口")
            except Exception as e:
                device_info['固件版本'] = "读取失败"
                logger.debug(f"⚠️ 读取固件版本失败: {e}")

            # 附加测试2：尝试读取设备状态（失败不影响连接判断）
            try:
                logger.debug("附加测试：读取设备电池电压状态...")
                if hasattr(comm_manager, 'read_battery_voltages'):
                    voltages = comm_manager.read_battery_voltages()
                    if voltages and len(voltages) > 0:
                        valid_voltages = [v for v in voltages if v > 0]
                        device_info['活跃通道'] = f"{len(valid_voltages)}/{channel_count}"
                        logger.debug(f"✅ 成功读取活跃通道: {len(valid_voltages)}/{channel_count}")
                    else:
                        device_info['活跃通道'] = "读取失败"
                        logger.debug("⚠️ 电池电压数据无效")
                else:
                    device_info['活跃通道'] = "接口不支持"
                    logger.debug("⚠️ 通信管理器不支持电池电压读取接口")
            except Exception as e:
                device_info['活跃通道'] = "读取失败"
                logger.debug(f"⚠️ 读取设备状态失败: {e}")

            # 连接质量评估（基于核心测试结果）
            success_count = 0
            total_tests = 3

            # 核心测试：通道数（必须成功）
            if channel_count_success:
                success_count += 1

            # 附加测试：固件版本（可选）
            if device_info.get('固件版本') not in ['读取失败', '接口不支持']:
                success_count += 1

            # 附加测试：活跃通道（可选）
            if device_info.get('活跃通道') not in ['读取失败', '接口不支持']:
                success_count += 1

            connection_quality = f"{success_count}/{total_tests}"
            device_info['连接质量'] = connection_quality

            # 由于核心测试（通道数）已经成功，连接质量至少为1/3
            logger.info(f"✅ 设备连接测试成功，连接质量: {connection_quality}")
            return device_info

        except Exception as e:
            logger.error(f"❌ 设备连接测试失败: {e}")
            # 连接测试失败，抛出异常让上层处理
            raise Exception(f"设备连接测试失败: {e}")

    def load_settings(self):
        """加载设置（优化版本）"""
        self._loading = True
        try:
            # 🚀 性能优化：延迟刷新串口列表，避免阻塞UI
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self._refresh_serial_ports)
            
            # 加载阻抗仪设置
            if self.serial_port_combo:
                serial_port = self.config_manager.get('device.connection.port', 'COM13')
                self.serial_port_combo.setCurrentText(serial_port)
            
            if self.serial_baudrate_combo:
                baudrate = self.config_manager.get('device.connection.baudrate', 115200)
                self.serial_baudrate_combo.setCurrentText(str(baudrate))
            
            if self.connection_timeout_spin:
                timeout = self.config_manager.get('device.connection.timeout', 2.0)
                self.connection_timeout_spin.setValue(int(timeout))
            
            if self.auto_connect_check:
                auto_connect = self.config_manager.get('device.auto_connect', True)
                self.auto_connect_check.setChecked(auto_connect)
            
            if self.auto_reconnect_check:
                auto_reconnect = self.config_manager.get('device.auto_reconnect', True)
                self.auto_reconnect_check.setChecked(auto_reconnect)
                self._on_auto_reconnect_changed(auto_reconnect)
            
            if self.reconnect_interval_spin:
                reconnect_interval = self.config_manager.get('device.reconnect_interval', 30)
                self.reconnect_interval_spin.setValue(reconnect_interval)
            
            logger.debug("阻抗设备设置加载完成")
            
        except Exception as e:
            logger.error(f"加载阻抗设备设置失败: {e}")
        finally:
            self._loading = False
    
    def apply_settings(self):
        """应用设置"""
        try:
            if not self.serial_port_combo:
                return
                
            # 提取串口名称（如果包含描述信息）
            port_text = self.serial_port_combo.currentText()
            port = port_text.split(' - ')[0] if ' - ' in port_text else port_text
            
            # 保存阻抗仪设置
            self.config_manager.set('device.connection.port', port)
            
            if self.serial_baudrate_combo:
                self.config_manager.set('device.connection.baudrate', int(self.serial_baudrate_combo.currentText()))
            
            if self.connection_timeout_spin:
                self.config_manager.set('device.connection.timeout', float(self.connection_timeout_spin.value()))
            
            if self.auto_connect_check:
                self.config_manager.set('device.auto_connect', self.auto_connect_check.isChecked())
            
            if self.auto_reconnect_check:
                self.config_manager.set('device.auto_reconnect', self.auto_reconnect_check.isChecked())
            
            if self.reconnect_interval_spin:
                self.config_manager.set('device.reconnect_interval', self.reconnect_interval_spin.value())
            
            logger.info("阻抗设备设置应用成功")
            
        except Exception as e:
            logger.error(f"应用阻抗设备设置失败: {e}")
            raise
    
    def sync_connection_status(self):
        """同步当前连接状态"""
        try:
            # 尝试从主窗口获取当前连接状态
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'device_connection_manager'):
                main_window = main_window.parent()
            
            if main_window and hasattr(main_window, 'device_connection_manager'):
                connection_manager = main_window.device_connection_manager
                
                # 获取当前连接状态
                is_connected = getattr(connection_manager, 'is_connected', False)
                current_port = getattr(connection_manager, 'current_port', '')
                
                # 更新连接状态显示
                if is_connected and current_port and self.connection_status_label:
                    self.connection_status_label.setText("已连接")
                    self.connection_status_label.setStyleSheet("color: green; font-weight: bold;")
                    
                    # 更新串口选择
                    if self.serial_port_combo:
                        for i in range(self.serial_port_combo.count()):
                            port_text = self.serial_port_combo.itemText(i)
                            port = port_text.split(' - ')[0] if ' - ' in port_text else port_text
                            if port == current_port:
                                self.serial_port_combo.setCurrentIndex(i)
                                break
                    
                    logger.debug(f"同步连接状态: 已连接到 {current_port}")
                else:
                    if self.connection_status_label:
                        self.connection_status_label.setText("未连接")
                        self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
                    logger.debug("同步连接状态: 未连接")
            else:
                logger.debug("无法获取设备连接管理器，跳过状态同步")
                
        except Exception as e:
            logger.error(f"同步连接状态失败: {e}")
    
    def try_auto_connect(self):
        """尝试自动连接"""
        try:
            if not self.auto_connect_check or not self.auto_connect_check.isChecked():
                return

            last_port = self.config_manager.get('device.connection.last_port', '')
            if last_port and self.serial_port_combo:
                # 查找匹配的串口
                for i in range(self.serial_port_combo.count()):
                    port_text = self.serial_port_combo.itemText(i)
                    port = port_text.split(' - ')[0] if ' - ' in port_text else port_text
                    if port == last_port:
                        self.serial_port_combo.setCurrentIndex(i)
                        logger.info(f"自动选择上次连接的串口: {last_port}")
                        break

        except Exception as e:
            logger.error(f"自动连接失败: {e}")

    def _notify_main_window_disconnect(self):
        """通知主窗口断开当前连接"""
        try:
            # 尝试从主窗口获取设备连接管理器
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'device_connection_manager'):
                main_window = main_window.parent()

            if main_window and hasattr(main_window, 'device_connection_manager'):
                connection_manager = main_window.device_connection_manager

                # 如果当前已连接，先断开
                if hasattr(connection_manager, 'is_connected') and connection_manager.is_connected:
                    logger.info("通知主窗口断开当前连接以避免端口冲突")
                    connection_manager.disconnect_device()

                    # 等待断开完成
                    import time
                    time.sleep(0.3)

                    logger.debug("主窗口连接已断开")
                else:
                    logger.debug("主窗口当前未连接，无需断开")
            else:
                logger.debug("无法获取设备连接管理器，跳过断开通知")

        except Exception as e:
            logger.warning(f"通知主窗口断开连接失败: {e}")


class BarcodeScannerManager(QObject):
    """扫码枪管理器"""

    # 信号定义
    settings_changed = pyqtSignal()

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._loading = False

        # 控件引用（由UI管理器设置）
        self.barcode_scanner_enabled_check = None
        self.serial_length_min_spin = None
        self.serial_length_max_spin = None
        self.format_validation_check = None
        self.uniqueness_check_check = None
        self.prefix_edit = None
        self.separator_edit = None
        self.sequence_digits_spin = None
        self.example_text_label = None

        # UI控件组（用于控制可见性）
        self.scanner_widgets = []
        self.auto_gen_widgets = []

        logger.debug("扫码枪管理器初始化完成")

    def set_ui_controls(self, controls: dict):
        """设置UI控件引用"""
        self.barcode_scanner_enabled_check = controls.get('barcode_scanner_enabled_check')
        self.serial_length_min_spin = controls.get('serial_length_min_spin')
        self.serial_length_max_spin = controls.get('serial_length_max_spin')
        self.format_validation_check = controls.get('format_validation_check')
        self.uniqueness_check_check = controls.get('uniqueness_check_check')
        self.prefix_edit = controls.get('prefix_edit')
        self.separator_edit = controls.get('separator_edit')
        self.sequence_digits_spin = controls.get('sequence_digits_spin')
        self.example_text_label = controls.get('example_text_label')

        # 设置控件组
        self.scanner_widgets = controls.get('scanner_widgets', [])
        self.auto_gen_widgets = controls.get('auto_gen_widgets', [])

        # 连接信号
        self._connect_signals()

    def _connect_signals(self):
        """连接信号"""
        if self.barcode_scanner_enabled_check:
            self.barcode_scanner_enabled_check.toggled.connect(self._on_barcode_scanner_enabled_changed)
        if self.serial_length_min_spin:
            self.serial_length_min_spin.valueChanged.connect(self._on_setting_changed)
        if self.serial_length_max_spin:
            self.serial_length_max_spin.valueChanged.connect(self._on_setting_changed)
        if self.format_validation_check:
            self.format_validation_check.toggled.connect(self._on_setting_changed)
        if self.uniqueness_check_check:
            self.uniqueness_check_check.toggled.connect(self._on_setting_changed)
        if self.prefix_edit:
            self.prefix_edit.textChanged.connect(self._on_auto_generation_changed)
        if self.separator_edit:
            self.separator_edit.textChanged.connect(self._on_auto_generation_changed)
        if self.sequence_digits_spin:
            self.sequence_digits_spin.valueChanged.connect(self._on_auto_generation_changed)

    def _on_barcode_scanner_enabled_changed(self, enabled: bool):
        """扫码枪启用状态变更处理"""
        try:
            # 控制相关控件的可见性
            self._update_barcode_scanner_ui_visibility(enabled)

            # 触发设置变更
            self._on_setting_changed()

            logger.debug(f"扫码枪启用状态变更: {enabled}")

        except Exception as e:
            logger.error(f"处理扫码枪启用状态变更失败: {e}")

    def _update_barcode_scanner_ui_visibility(self, scanner_enabled: bool):
        """更新扫码枪UI控件的可见性"""
        try:
            # 设置扫码枪相关控件的可见性
            for widget in self.scanner_widgets:
                if widget:
                    widget.setVisible(scanner_enabled)

            # 设置自动生成相关控件的可见性（与扫码枪相反）
            for widget in self.auto_gen_widgets:
                if widget:
                    widget.setVisible(not scanner_enabled)

            logger.debug(f"扫码枪UI可见性更新: 扫码枪={scanner_enabled}, 自动生成={not scanner_enabled}")

        except Exception as e:
            logger.error(f"更新扫码枪UI可见性失败: {e}")

    def _on_auto_generation_changed(self):
        """自动生成设置变更处理"""
        try:
            # 更新示例显示
            self._update_serial_example()

            # 触发设置变更
            self._on_setting_changed()

        except Exception as e:
            logger.error(f"处理自动生成设置变更失败: {e}")

    def _update_serial_example(self):
        """更新序列号示例显示"""
        try:
            if not self.example_text_label:
                return

            from datetime import datetime

            # 获取当前设置
            prefix = self.prefix_edit.text().strip() if self.prefix_edit else ""
            separator = self.separator_edit.text().strip() if self.separator_edit else ""
            sequence_digits = self.sequence_digits_spin.value() if self.sequence_digits_spin else 4

            # 生成示例
            current_date = datetime.now().strftime("%Y%m%d")
            sequence = "1".zfill(sequence_digits)

            if prefix and separator:
                example = f"{prefix}{separator}{current_date}{separator}{sequence}"
            elif prefix:
                example = f"{prefix}{current_date}{sequence}"
            else:
                example = f"{current_date}{separator}{sequence}" if separator else f"{current_date}{sequence}"

            # 更新显示
            self.example_text_label.setText(example)

            # 序列号示例更新 - 运行时不输出日志
            pass

        except Exception as e:
            logger.error(f"更新序列号示例失败: {e}")
            if self.example_text_label:
                self.example_text_label.setText("示例生成失败")

    def _on_setting_changed(self):
        """设置变更处理"""
        if not self._loading:
            self.settings_changed.emit()

    def load_settings(self):
        """加载设置"""
        self._loading = True
        try:
            # 加载扫码枪设置
            if self.barcode_scanner_enabled_check:
                scanner_enabled = self.config_manager.get('device.barcode_scanner.enabled', False)
                self.barcode_scanner_enabled_check.setChecked(scanner_enabled)
                self._update_barcode_scanner_ui_visibility(scanner_enabled)

            if self.serial_length_min_spin:
                serial_length_min = self.config_manager.get('device.barcode_scanner.serial_length_min', 8)
                self.serial_length_min_spin.setValue(serial_length_min)

            if self.serial_length_max_spin:
                serial_length_max = self.config_manager.get('device.barcode_scanner.serial_length_max', 20)
                self.serial_length_max_spin.setValue(serial_length_max)

            if self.format_validation_check:
                format_validation = self.config_manager.get('device.barcode_scanner.format_validation', True)
                self.format_validation_check.setChecked(format_validation)

            if self.uniqueness_check_check:
                uniqueness_check = self.config_manager.get('device.barcode_scanner.uniqueness_check', True)
                self.uniqueness_check_check.setChecked(uniqueness_check)

            # 加载自动生成设置
            if self.prefix_edit:
                prefix = self.config_manager.get('device.barcode_scanner.auto_generation.prefix', 'BAT')
                self.prefix_edit.setText(prefix)

            if self.separator_edit:
                separator = self.config_manager.get('device.barcode_scanner.auto_generation.separator', '-')
                self.separator_edit.setText(separator)

            if self.sequence_digits_spin:
                sequence_digits = self.config_manager.get('device.barcode_scanner.auto_generation.sequence_digits', 4)
                self.sequence_digits_spin.setValue(sequence_digits)

            # 更新示例显示
            self._update_serial_example()

            logger.debug("扫码枪设置加载完成")

        except Exception as e:
            logger.error(f"加载扫码枪设置失败: {e}")
        finally:
            self._loading = False

    def apply_settings(self):
        """应用设置"""
        try:
            # 保存扫码枪设置
            if self.barcode_scanner_enabled_check:
                self.config_manager.set('device.barcode_scanner.enabled', self.barcode_scanner_enabled_check.isChecked())

            if self.serial_length_min_spin:
                self.config_manager.set('device.barcode_scanner.serial_length_min', self.serial_length_min_spin.value())

            if self.serial_length_max_spin:
                self.config_manager.set('device.barcode_scanner.serial_length_max', self.serial_length_max_spin.value())

            if self.format_validation_check:
                self.config_manager.set('device.barcode_scanner.format_validation', self.format_validation_check.isChecked())

            if self.uniqueness_check_check:
                self.config_manager.set('device.barcode_scanner.uniqueness_check', self.uniqueness_check_check.isChecked())

            # 保存自动生成设置
            if self.prefix_edit:
                self.config_manager.set('device.barcode_scanner.auto_generation.prefix', self.prefix_edit.text().strip())

            if self.separator_edit:
                self.config_manager.set('device.barcode_scanner.auto_generation.separator', self.separator_edit.text().strip())

            if self.sequence_digits_spin:
                self.config_manager.set('device.barcode_scanner.auto_generation.sequence_digits', self.sequence_digits_spin.value())

            logger.info("扫码枪设置应用成功")

        except Exception as e:
            logger.error(f"应用扫码枪设置失败: {e}")
            raise


class PrinterManager(QObject):
    """打印机管理器"""

    # 信号定义
    settings_changed = pyqtSignal()

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._loading = False

        # 控件引用（由UI管理器设置）
        self.printer_type_combo = None
        self.printer_name_combo = None
        self.printer_connection_combo = None
        self.print_quality_combo = None
        self.printer_status_label = None
        self.refresh_printer_button = None
        self.test_print_button = None

        logger.debug("打印机管理器初始化完成")

    def set_ui_controls(self, controls: dict):
        """设置UI控件引用"""
        self.printer_type_combo = controls.get('printer_type_combo')
        self.printer_name_combo = controls.get('printer_name_combo')
        self.printer_connection_combo = controls.get('printer_connection_combo')
        self.print_quality_combo = controls.get('print_quality_combo')
        self.printer_status_label = controls.get('printer_status_label')
        self.refresh_printer_button = controls.get('refresh_printer_button')
        self.test_print_button = controls.get('test_print_button')

        # 连接信号
        self._connect_signals()

    def _connect_signals(self):
        """连接信号"""
        if self.printer_type_combo:
            self.printer_type_combo.currentTextChanged.connect(self._on_setting_changed)
        if self.printer_name_combo:
            # 修复打印机名称变化时立即保存，不等待应用按钮
            self.printer_name_combo.currentTextChanged.connect(self._on_printer_name_changed)
        if self.printer_connection_combo:
            self.printer_connection_combo.currentTextChanged.connect(self._on_setting_changed)
        if self.print_quality_combo:
            self.print_quality_combo.currentTextChanged.connect(self._on_setting_changed)
        if self.refresh_printer_button:
            self.refresh_printer_button.clicked.connect(self._refresh_printer_list)
        if self.test_print_button:
            self.test_print_button.clicked.connect(self._test_printer)

    def _on_setting_changed(self):
        """设置变更处理"""
        if not self._loading:
            self.settings_changed.emit()

    def _on_printer_name_changed(self, printer_name: str):
        """打印机名称变化处理 - 立即保存"""
        if self._loading:
            return

        try:
            # 修复立即保存打印机选择，不等待应用按钮
            if printer_name and printer_name != "未检测到打印机":
                # 移除状态标识（如"(默认)"）
                clean_printer_name = printer_name.replace(" (默认)", "")

                # 立即保存到配置
                self.config_manager.set('printer.name', clean_printer_name)
                self.config_manager.save_config()

                logger.info(f"✅ 打印机选择已立即保存: {clean_printer_name}")

                # 通知打印机管理器更新（尝试找到主窗口）
                try:
                    # 向上查找主窗口
                    widget = self.parent()
                    while widget and not hasattr(widget, 'printer_manager'):
                        widget = widget.parent()

                    if widget and hasattr(widget, 'printer_manager'):
                        widget.printer_manager.update_printer_config(clean_printer_name)
                        logger.debug("已通知主窗口打印机管理器更新配置")
                except Exception as e:
                    logger.debug(f"通知打印机管理器更新失败: {e}")

            # 仍然发送设置变更信号，但打印机设置已经保存了
            self.settings_changed.emit()

        except Exception as e:
            logger.error(f"立即保存打印机选择失败: {e}")
            # 即使保存失败，也发送设置变更信号
            self.settings_changed.emit()

    def _refresh_printer_list(self):
        """刷新打印机列表"""
        try:
            if not self.printer_name_combo:
                return

            # 🐛 修复：清除打印机失败缓存，强制重新检查所有打印机
            self._clear_printer_cache()

            # 获取当前选择的打印机
            current_text = self.printer_name_combo.currentText()

            # 清空列表
            self.printer_name_combo.clear()

            # 获取系统中的打印机列表
            printers = self._get_system_printers()

            if printers:
                # 添加发现的打印机
                self.printer_name_combo.addItems(printers)

                # 尝试恢复之前的选择
                index = self.printer_name_combo.findText(current_text)
                if index >= 0:
                    self.printer_name_combo.setCurrentIndex(index)

                # 更新打印机状态
                if self.printer_status_label:
                    self.printer_status_label.setText("已检测到打印机")
                    self.printer_status_label.setStyleSheet("color: green; font-weight: bold;")

                QMessageBox.information(None, "刷新完成", f"已找到 {len(printers)} 台打印机\n\n打印机缓存已清除，将重新检查所有打印机状态")
                logger.info(f"发现 {len(printers)} 台打印机: {', '.join(printers)}")
            else:
                # 没有发现打印机
                self.printer_name_combo.addItem("未检测到打印机")
                if self.printer_status_label:
                    self.printer_status_label.setText("未连接")
                    self.printer_status_label.setStyleSheet("color: red; font-weight: bold;")

                QMessageBox.warning(self.parent(), "刷新完成", "未检测到可用的打印机\n请检查打印机是否已正确安装和连接")
                logger.warning("未检测到可用的打印机")

        except Exception as e:
            logger.error(f"刷新打印机列表失败: {e}")
            QMessageBox.critical(self.parent(), "错误", f"刷新打印机列表失败：\n{e}")

    def _clear_printer_cache(self):
        """清除打印机失败缓存"""
        try:
            # 尝试从主窗口获取打印机管理器
            main_window = None
            parent = self.parent()
            while parent:
                if hasattr(parent, 'printer_manager'):
                    main_window = parent
                    break
                parent = parent.parent()

            if main_window and hasattr(main_window.printer_manager, 'clear_failed_printer_cache'):
                main_window.printer_manager.clear_failed_printer_cache()
                logger.info("🔄 已清除打印机失败缓存")
            else:
                logger.debug("未找到打印机管理器，跳过缓存清除")

        except Exception as e:
            logger.error(f"清除打印机缓存失败: {e}")

    def _refresh_printer_list_silent(self):
        """静默刷新打印机列表（不显示消息框）"""
        try:
            if not self.printer_name_combo:
                return

            # 修复优先使用配置中保存的打印机名称，而不是UI当前选择
            # 这样可以避免在页面激活时丢失用户之前保存的选择
            saved_printer_name = self.config_manager.get('printer.name', '')
            current_text = self.printer_name_combo.currentText()

            # 新增如果配置中的打印机名称与当前UI选择一致，则跳过刷新
            # 避免不必要的刷新导致选择丢失
            if saved_printer_name and current_text and saved_printer_name == current_text:
                logger.debug(f"打印机选择一致，跳过刷新: '{saved_printer_name}'")
                return

            # 如果配置中有保存的打印机名称，优先使用它
            target_printer = saved_printer_name if saved_printer_name else current_text

            logger.debug(f"刷新打印机列表 - 配置中的打印机: '{saved_printer_name}', UI当前选择: '{current_text}', 目标打印机: '{target_printer}'")

            self._refresh_printer_list_with_selection(target_printer)

        except Exception as e:
            logger.error(f"静默刷新打印机列表失败: {e}")
            # 静默模式下不显示错误消息框

    def _refresh_printer_list_with_selection(self, target_printer_name: str = ""):
        """刷新打印机列表并尝试保持指定的选择"""
        try:
            if not self.printer_name_combo:
                return

            # 修复保存当前选择的索引和文本，用于后续恢复
            current_index = self.printer_name_combo.currentIndex()
            current_text = self.printer_name_combo.currentText()

            # 清空列表
            self.printer_name_combo.clear()

            # 获取系统中的打印机列表
            printers = self._get_system_printers()

            if printers:
                # 添加发现的打印机
                self.printer_name_combo.addItems(printers)

                # 修复智能选择恢复逻辑
                selected_index = -1

                # 优先级1：尝试恢复指定的目标打印机
                if target_printer_name:
                    selected_index = self._find_best_printer_match(target_printer_name, printers)
                    if selected_index >= 0:
                        logger.info(f"✅ 恢复目标打印机: {target_printer_name} -> {printers[selected_index]}")

                # 优先级2：如果目标打印机未找到，尝试恢复之前的选择
                if selected_index < 0 and current_text and current_text != "未检测到打印机":
                    selected_index = self._find_best_printer_match(current_text, printers)
                    if selected_index >= 0:
                        logger.info(f"✅ 恢复之前的选择: {current_text} -> {printers[selected_index]}")

                # 优先级3：如果都没找到，选择第一个可用的打印机
                if selected_index < 0 and printers:
                    selected_index = 0
                    logger.info(f"⚠️ 使用默认选择: {printers[0]}")

                # 设置选择
                if selected_index >= 0:
                    self.printer_name_combo.setCurrentIndex(selected_index)

                # 更新打印机状态
                if self.printer_status_label:
                    self.printer_status_label.setText("已检测到打印机")
                    self.printer_status_label.setStyleSheet("color: green; font-weight: bold;")

                logger.debug(f"发现 {len(printers)} 台打印机: {', '.join(printers)}")
            else:
                # 没有发现打印机
                self.printer_name_combo.addItem("未检测到打印机")
                if self.printer_status_label:
                    self.printer_status_label.setText("未连接")
                    self.printer_status_label.setStyleSheet("color: red; font-weight: bold;")

                logger.warning("未检测到可用的打印机")

        except Exception as e:
            logger.error(f"刷新打印机列表失败: {e}")
            # 确保至少有一个选项
            if self.printer_name_combo and self.printer_name_combo.count() == 0:
                self.printer_name_combo.addItem("未检测到打印机")

    def _find_best_printer_match(self, target_name: str, available_printers: list) -> int:
        """
        找到最佳的打印机匹配

        Args:
            target_name: 目标打印机名称
            available_printers: 可用打印机列表

        Returns:
            匹配的打印机索引，-1表示未找到
        """
        if not target_name or not available_printers:
            return -1

        # 1. 完全匹配
        for i, printer in enumerate(available_printers):
            if printer == target_name:
                logger.debug(f"🎯 完全匹配: {target_name}")
                return i

        # 2. 去掉状态标识后匹配
        clean_target = target_name.replace(" (默认)", "").strip()
        for i, printer in enumerate(available_printers):
            clean_printer = printer.replace(" (默认)", "").strip()
            if clean_printer == clean_target:
                logger.debug(f"🎯 清理后匹配: {clean_target} -> {printer}")
                return i

        # 3. 部分匹配（包含关系）
        for i, printer in enumerate(available_printers):
            if clean_target in printer or printer.replace(" (默认)", "").strip() in clean_target:
                logger.debug(f"🎯 部分匹配: {clean_target} -> {printer}")
                return i

        logger.debug(f"❌ 未找到匹配的打印机: {target_name}")
        return -1

    def _get_system_printers(self) -> list:
        """获取系统中的打印机列表（只显示在线的打印机）"""
        printers = []

        try:
            if PRINTER_SUPPORT:
                import win32print

                # 获取默认打印机
                try:
                    default_printer = win32print.GetDefaultPrinter()
                    logger.debug(f"默认打印机: {default_printer}")
                except:
                    default_printer = None

                # 枚举所有打印机
                printer_info = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)

                for printer in printer_info:
                    printer_name = printer[2]  # 打印机名称

                    # 修复只有在线的打印机才添加到列表中
                    is_online = self._check_printer_online_status(printer_name)

                    if is_online:
                        # 添加状态标识
                        if printer_name == default_printer:
                            printer_display_name = f"{printer_name} (默认)"
                        else:
                            printer_display_name = printer_name

                        printers.append(printer_display_name)
                        logger.debug(f"发现在线打印机: {printer_display_name}")
                    else:
                        logger.debug(f"跳过脱机打印机: {printer_name}")
            else:
                logger.warning("打印机支持模块未安装，使用备用方法检测打印机")
                # 备用方法：使用subprocess调用系统命令
                printers = self._get_printers_fallback()

        except ImportError:
            logger.warning("win32print模块未安装，使用备用方法检测打印机")
            # 备用方法：使用subprocess调用系统命令
            printers = self._get_printers_fallback()

        except Exception as e:
            logger.error(f"获取系统打印机列表失败: {e}")
            # 使用备用方法
            printers = self._get_printers_fallback()

        return printers

    def _check_printer_online_status(self, printer_name: str) -> bool:
        """检查打印机是否在线（可用）"""
        try:
            if not PRINTER_SUPPORT:
                return True  # 如果没有打印机支持模块，默认认为可用

            import win32print

            # 尝试打开打印机
            handle = win32print.OpenPrinter(printer_name)

            # 获取打印机状态
            printer_info = win32print.GetPrinter(handle, 2)
            win32print.ClosePrinter(handle)

            # 检查打印机状态
            status = printer_info.get('Status', 0)
            attributes = printer_info.get('Attributes', 0)

            # 针对NIIMBOT K3_W打印机的特殊处理
            if "NIIMBOT" in printer_name.upper() or "K3_W" in printer_name.upper():
                # NIIMBOT打印机的可用性检查
                is_available = self._check_niimbot_online_status(printer_name, status, attributes)
            else:
                # 修复对于其他打印机采用更宽松的检查策略
                # 只要不是明确的离线状态，就认为是可用的
                is_available = True  # 默认认为可用

                # 只有在明确的错误状态下才认为不可用
                if status & 0x00000001:  # 离线状态
                    is_available = False
                elif status & 0x00000010:  # 错误状态
                    is_available = False

            if is_available:
                logger.debug(f"打印机 {printer_name} 在线，状态: {status}")
            else:
                logger.debug(f"打印机 {printer_name} 脱机，状态: {status}")

            return is_available

        except Exception as e:
            logger.debug(f"检查打印机 {printer_name} 在线状态失败: {e}")
            return False

    def _check_niimbot_online_status(self, printer_name: str, status: int, attributes: int) -> bool:
        """检查NIIMBOT打印机的在线状态"""
        try:
            # NIIMBOT打印机的状态检查逻辑
            # 状态码参考：
            # 0x00000000 = 正常
            # 0x00000001 = 离线
            # 0x00000002 = 纸张用完
            # 0x00000004 = 纸张卡住
            # 0x00000008 = 门打开
            # 0x00000010 = 错误
            # 0x00000020 = 手动进纸
            # 0x00000040 = 缺纸
            # 0x00000080 = 输出满
            # 0x00000100 = 页面错误
            # 0x00000200 = 用户干预
            # 0x00000400 = 内存不足
            # 0x00000800 = 服务器未知

            # 对于NIIMBOT，我们认为以下状态是在线的：
            # 1. 状态为0（完全正常）
            # 2. 只有手动进纸状态（0x00000020）
            # 3. 只有缺纸状态（0x00000040）- 打印机在线但缺纸

            if status == 0:
                # 完全正常状态
                return True
            elif status == 0x00000020:
                # 手动进纸状态，打印机在线
                logger.debug(f"NIIMBOT打印机 {printer_name} 处于手动进纸状态，但在线")
                return True
            elif status == 0x00000040:
                # 缺纸状态，打印机在线但缺纸
                logger.debug(f"NIIMBOT打印机 {printer_name} 缺纸，但打印机在线")
                return True
            else:
                # 其他状态认为脱机
                logger.debug(f"NIIMBOT打印机 {printer_name} 脱机，状态: 0x{status:08X}")
                return False

        except Exception as e:
            logger.error(f"检查NIIMBOT打印机 {printer_name} 在线状态失败: {e}")
            return False

    def _get_printers_fallback(self) -> list:
        """备用方法：通过系统命令获取打印机列表（只返回在线的打印机）"""
        printers = []

        try:
            import subprocess

            # 修改使用wmic命令获取打印机列表和状态
            result = subprocess.run(
                ['wmic', 'printer', 'get', 'name,workoffline'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # 跳过标题行
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        # 解析打印机名称和状态
                        work_offline = parts[0].upper() if parts[0] else 'FALSE'
                        printer_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

                        if printer_name and printer_name != 'Name':
                            # 修复只添加在线的打印机（WorkOffline为FALSE）
                            if work_offline == 'FALSE':
                                printers.append(printer_name)
                                logger.debug(f"通过wmic发现在线打印机: {printer_name}")
                            else:
                                logger.debug(f"跳过脱机打印机: {printer_name}")
                    elif len(parts) == 1 and parts[0] and parts[0] != 'Name':
                        # 如果只有打印机名称，没有状态信息，默认认为在线
                        printer_name = parts[0]
                        printers.append(printer_name)
                        logger.debug(f"通过wmic发现打印机（状态未知，默认在线）: {printer_name}")

        except Exception as e:
            logger.error(f"备用方法获取打印机列表失败: {e}")

        # 如果没有找到打印机，提供一些常见的默认选项
        if not printers:
            printers = [
                "Microsoft Print to PDF",
                "Microsoft XPS Document Writer",
                "NIIMBOT K3_W",
                "Generic / Text Only",
                "Fax"
            ]
            logger.info("未检测到系统打印机，使用默认打印机列表")

        return printers

    def _test_printer(self):
        """测试打印"""
        if not self.printer_name_combo or not self.test_print_button:
            return

        printer_name = self.printer_name_combo.currentText()
        if not printer_name or printer_name == "未检测到打印机":
            QMessageBox.warning(None, "警告", "请先选择有效的打印机！")
            return

        # 修复测试打印前先保存当前选择的打印机设置
        # 避免测试打印触发设置变更标志导致关闭时恢复原始设置
        try:
            self.config_manager.set('printer.name', printer_name)
            self.config_manager.save_config()
            logger.info(f"测试打印前已保存打印机设置: {printer_name}")
        except Exception as e:
            logger.error(f"保存打印机设置失败: {e}")

        # 移除状态标识（如"(默认)"）
        clean_printer_name = printer_name.replace(" (默认)", "")

        self.test_print_button.setEnabled(False)
        self.test_print_button.setText("打印中...")

        # 使用定时器异步执行打印测试
        QTimer.singleShot(100, lambda: self._execute_print_test(clean_printer_name))

    def _execute_print_test(self, printer_name: str):
        """执行实际的打印测试"""
        try:
            success = self._print_test_page(printer_name)

            if success:
                if self.printer_status_label:
                    self.printer_status_label.setText("就绪")
                    self.printer_status_label.setStyleSheet("color: green; font-weight: bold;")
                QMessageBox.information(None, "打印测试", f"测试页已发送到打印机：{printer_name}")
                logger.info(f"打印机 {printer_name} 测试成功")
            else:
                if self.printer_status_label:
                    self.printer_status_label.setText("错误")
                    self.printer_status_label.setStyleSheet("color: red; font-weight: bold;")
                QMessageBox.warning(None, "打印测试", f"打印机 {printer_name} 测试失败\n请检查打印机状态和连接")
                logger.warning(f"打印机 {printer_name} 测试失败")

        except Exception as e:
            if self.printer_status_label:
                self.printer_status_label.setText("错误")
                self.printer_status_label.setStyleSheet("color: red; font-weight: bold;")
            QMessageBox.critical(None, "打印测试", f"打印测试失败：\n{e}")
            logger.error(f"打印测试失败: {e}")

        finally:
            if self.test_print_button:
                self.test_print_button.setEnabled(True)
                self.test_print_button.setText("测试打印")

    def _print_test_page(self, printer_name: str) -> bool:
        """打印测试页 - 使用当前选择的标签模板"""
        try:
            logger.info(f"🖨️ 开始使用当前模板进行测试打印: {printer_name}")

            # 修改使用标签打印管理器生成测试标签
            success = self._print_template_test_page(printer_name)

            if success:
                logger.info(f"✅ 模板测试打印成功: {printer_name}")
                return True
            else:
                logger.warning(f"⚠️ 模板测试打印失败，尝试备用方法: {printer_name}")
                # 如果模板打印失败，回退到原始的文本打印方法
                return self._print_text_test_page(printer_name)

        except Exception as e:
            logger.error(f"❌ 测试打印失败: {e}")
            return False

    def _print_template_test_page(self, printer_name: str) -> bool:
        """使用当前模板打印测试页"""
        try:
            from datetime import datetime
            from ui.label_print_manager import LabelTemplate

            logger.info("🎯 使用当前选择的标签模板生成测试标签")

            # 创建标签模板实例
            label_template = LabelTemplate(self.config_manager)

            # 生成测试数据
            test_result = self._generate_test_data()

            # 生成标签图像
            label_image = label_template.generate_label_image(test_result)
            logger.info(f"✅ 标签图像生成成功，尺寸: {label_image.size}")

            # 使用标签打印管理器的打印方法
            success = self._print_label_image(label_image, printer_name)

            if success:
                logger.info(f"🎉 模板测试标签打印成功: {printer_name}")
            else:
                logger.error(f"❌ 模板测试标签打印失败: {printer_name}")

            return success

        except Exception as e:
            logger.error(f"❌ 使用模板打印测试页失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False

    def _generate_test_data(self) -> dict:
        """生成测试数据"""
        from datetime import datetime
        import random

        # 生成模拟的电池测试数据
        # 生成离群率测试数据
        max_deviation = round(random.uniform(0.5, 8.5), 1)  # 生成0.5%-8.5%的偏差
        is_pass = max_deviation <= 10.0  # 假设阈值为10%

        test_data = {
            'battery_code': f'TEST{random.randint(1000, 9999)}',
            'channel_number': 1,
            'voltage': round(random.uniform(3.2, 3.8), 3),
            'rs_value': round(random.uniform(0.5, 2.0), 3),
            'rct_value': round(random.uniform(5.0, 15.0), 3),
            'rs_grade': random.choice([1, 2, 3]),
            'rct_grade': random.choice([1, 2, 3]),
            'is_pass': is_pass,
            'timestamp': datetime.now(),
            'test_mode': '测试模式',
            'operator': '系统测试',
            'remarks': '打印机测试',
            # 新增离群率相关数据
            'outlier_result': f"{max_deviation:.1f}%" if max_deviation > 10.0 else "PASS",
            'outlier_rate': f"{max_deviation:.1f}%" if max_deviation > 10.0 else "PASS",
            'max_deviation_percent': max_deviation,
            'frequency_deviations': {
                '1000': round(random.uniform(0.1, max_deviation), 1),
                '100': round(random.uniform(0.1, max_deviation), 1),
                '10': round(random.uniform(0.1, max_deviation), 1)
            },
            'baseline_filename': 'test_baseline.json',
            'baseline_id': 1
        }

        logger.debug(f"生成测试数据: {test_data}")
        return test_data

    def _print_label_image(self, image, printer_name: str) -> bool:
        """打印标签图像"""
        try:
            import win32print
            import win32ui
            from PIL import ImageWin

            logger.debug(f"开始打印标签图像到打印机: {printer_name}")

            # 打开打印机
            hprinter = win32print.OpenPrinter(printer_name)

            try:
                # 创建设备上下文
                hdc = win32ui.CreateDC()
                hdc.CreatePrinterDC(printer_name)

                # 开始打印作业
                hdc.StartDoc("JCY5001AS 标签测试")
                hdc.StartPage()

                # 获取打印机分辨率
                printer_width = hdc.GetDeviceCaps(110)  # HORZRES
                printer_height = hdc.GetDeviceCaps(111)  # VERTRES

                logger.debug(f"打印机分辨率: {printer_width}x{printer_height}")

                # 获取图像尺寸
                img_width, img_height = image.size

                # 计算居中位置
                x = max(0, (printer_width - img_width) // 2)
                y = max(0, (printer_height - img_height) // 2)

                # 打印图像
                dib = ImageWin.Dib(image)
                dib.draw(hdc.GetHandleOutput(), (x, y, x + img_width, y + img_height))

                # 结束打印
                hdc.EndPage()
                hdc.EndDoc()
                hdc.DeleteDC()

                logger.info(f"✅ 标签图像打印完成: {printer_name}")
                return True

            finally:
                win32print.ClosePrinter(hprinter)

        except ImportError:
            logger.warning("win32print模块未安装，无法打印标签图像")
            return False
        except Exception as e:
            logger.error(f"❌ 打印标签图像失败: {e}")
            return False

    def _print_text_test_page(self, printer_name: str) -> bool:
        """打印文本测试页（备用方法）"""
        try:
            import win32print
            import win32ui
            from datetime import datetime

            logger.info(f"🔄 使用文本方式打印测试页: {printer_name}")

            # 打开打印机
            hprinter = win32print.OpenPrinter(printer_name)

            try:
                # 创建打印作业
                hdc = win32ui.CreateDC()
                hdc.CreatePrinterDC(printer_name)

                # 开始打印作业
                hdc.StartDoc("JCY5001AS 测试页")
                hdc.StartPage()

                # 打印测试内容
                test_content = [
                    "JCY5001AS 电池阻抗测试系统",
                    "打印机测试页",
                    "",
                    f"打印机名称: {printer_name}",
                    f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    "如果您能看到此页面，说明打印机工作正常。",
                    "",
                    "测试项目:",
                    "✓ 打印机连接",
                    "✓ 打印机驱动",
                    "✓ 打印质量",
                    "",
                    "JCY5001AS 系统版本: v1.0.0"
                ]

                # 设置字体和位置
                y_pos = 100
                for line in test_content:
                    hdc.TextOut(100, y_pos, line)
                    y_pos += 50

                # 结束打印
                hdc.EndPage()
                hdc.EndDoc()

                logger.info(f"✅ 文本测试页打印完成: {printer_name}")
                return True

            finally:
                win32print.ClosePrinter(hprinter)

        except ImportError:
            logger.warning("win32print模块未安装，使用备用打印方法")
            return self._print_test_page_fallback(printer_name)

        except Exception as e:
            logger.error(f"❌ 打印文本测试页失败: {e}")
            return False

    def _print_test_page_fallback(self, printer_name: str) -> bool:
        """备用打印方法：使用系统命令"""
        try:
            import subprocess
            import tempfile
            import os
            from datetime import datetime

            # 创建临时测试文件
            test_content = f"""JCY5001AS 电池阻抗测试系统
打印机测试页

打印机名称: {printer_name}
测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

如果您能看到此页面，说明打印机工作正常。

测试项目:
✓ 打印机连接
✓ 打印机驱动
✓ 打印质量

JCY5001AS 系统版本: v1.0.0
"""

            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(test_content)
                temp_file = f.name

            try:
                # 使用系统命令打印
                result = subprocess.run(
                    ['notepad', '/p', temp_file],
                    timeout=30,
                    capture_output=True
                )

                return result.returncode == 0

            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file)
                except:
                    pass

        except Exception as e:
            logger.error(f"备用打印方法失败: {e}")
            return False

    def load_settings(self):
        """加载设置"""
        self._loading = True
        try:
            # 修复先从配置中获取保存的打印机名称
            saved_printer_name = self.config_manager.get('printer.name', '')
            logger.debug(f"加载设置 - 配置中保存的打印机: '{saved_printer_name}'")

            # 修复只有在打印机列表为空时才刷新，避免重复刷新覆盖用户选择
            if not self.printer_name_combo or self.printer_name_combo.count() == 0:
                self._refresh_printer_list_with_selection(saved_printer_name)
            else:
                # 修复如果列表已存在，直接尝试恢复选择，不重新刷新
                if saved_printer_name:
                    best_match_index = self._find_best_printer_match(
                        saved_printer_name,
                        [self.printer_name_combo.itemText(i) for i in range(self.printer_name_combo.count())]
                    )
                    if best_match_index >= 0:
                        self.printer_name_combo.setCurrentIndex(best_match_index)
                        current_selection = self.printer_name_combo.currentText()
                        logger.info(f"✅ 直接恢复打印机选择: {saved_printer_name} -> {current_selection}")
                    else:
                        logger.warning(f"⚠️ 无法在现有列表中找到保存的打印机: {saved_printer_name}")

            # 加载打印机设置
            if self.printer_type_combo:
                printer_type = self.config_manager.get('printer.type', '热敏打印机')
                self.printer_type_combo.setCurrentText(printer_type)

            if self.printer_connection_combo:
                connection = self.config_manager.get('printer.connection', 'USB')
                self.printer_connection_combo.setCurrentText(connection)

            if self.print_quality_combo:
                quality = self.config_manager.get('printer.quality', '标准')
                self.print_quality_combo.setCurrentText(quality)

            # 修复最终验证打印机选择是否正确
            if self.printer_name_combo:
                final_selection = self.printer_name_combo.currentText()
                logger.info(f"🎯 最终打印机选择: '{final_selection}'")
                
                # 新增如果最终选择与配置不一致，强制更新配置
                if saved_printer_name and final_selection != saved_printer_name:
                    logger.warning(f"⚠️ 最终选择与配置不一致，强制更新配置: {saved_printer_name} -> {final_selection}")
                    # 但不在加载时更新配置，避免覆盖用户设置

            logger.debug("打印机设置加载完成")

        except Exception as e:
            logger.error(f"加载打印机设置失败: {e}")
        finally:
            self._loading = False

    def apply_settings(self):
        """应用设置"""
        try:
            # 保存打印机设置
            if self.printer_type_combo:
                self.config_manager.set('printer.type', self.printer_type_combo.currentText())

            if self.printer_name_combo:
                # 🐛 修复：清理打印机名称中的状态标识
                printer_name = self.printer_name_combo.currentText()
                clean_printer_name = printer_name.replace(" (默认)", "").strip()
                self.config_manager.set('printer.name', clean_printer_name)

            if self.printer_connection_combo:
                self.config_manager.set('printer.connection', self.printer_connection_combo.currentText())

            if self.print_quality_combo:
                self.config_manager.set('printer.quality', self.print_quality_combo.currentText())

            logger.info("打印机设置应用成功")

        except Exception as e:
            logger.error(f"应用打印机设置失败: {e}")
            raise


class LoggingSettingsManager(QObject):
    """日志设置管理器"""

    # 信号定义
    settings_changed = pyqtSignal()

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._loading = False

        # 控件引用（由UI管理器设置）
        self.enable_logging_check = None
        self.enable_system_log_check = None
        self.log_level_combo = None

        logger.debug("日志设置管理器初始化完成")

    def set_ui_controls(self, controls: dict):
        """设置UI控件引用"""
        self.enable_logging_check = controls.get('enable_logging_check')
        self.enable_system_log_check = controls.get('enable_system_log_check')
        self.log_level_combo = controls.get('log_level_combo')
        self.debug_mode_check = controls.get('debug_mode_check')  # 新增
        self.debug_mode_status_label = controls.get('debug_mode_status_label')  # 新增

        # 连接信号
        self._connect_signals()

    def _connect_signals(self):
        """连接信号"""
        if self.enable_logging_check:
            self.enable_logging_check.toggled.connect(self._on_setting_changed)
        if self.enable_system_log_check:
            self.enable_system_log_check.toggled.connect(self._on_setting_changed)
        if self.log_level_combo:
            self.log_level_combo.currentTextChanged.connect(self._on_setting_changed)

        if self.debug_mode_check:
            self.debug_mode_check.toggled.connect(self._on_debug_mode_changed)

    def _on_setting_changed(self):
        """设置变更处理"""
        if not self._loading:
            self.settings_changed.emit()

    def _on_debug_mode_changed(self, enabled: bool):
        """调试模式变更处理"""
        try:
            if self._loading:
                return

            # 更新状态标签
            self._update_debug_mode_status(enabled)

            # 应用调试模式设置
            self._apply_debug_mode_immediately(enabled)

            # 触发设置变更信号
            self.settings_changed.emit()


        except Exception as e:
            logger.error(f"处理调试模式变更失败: {e}")

    def _update_debug_mode_status(self, enabled: bool):
        """更新调试模式状态显示"""
        try:
            if not self.debug_mode_status_label:
                return

            if enabled:
                self.debug_mode_status_label.setText("调试模式：开启 - 日志输出正常")
                self.debug_mode_status_label.setStyleSheet("""
                    QLabel {
                        color: #27ae60;
                        font-weight: bold;
                        padding: 5px;
                        background-color: #d5f4e6;
                        border-radius: 3px;
                    }
                """)
            else:
                self.debug_mode_status_label.setText("调试模式：关闭 - 日志输出已禁用")
                self.debug_mode_status_label.setStyleSheet("""
                    QLabel {
                        color: #e74c3c;
                        font-weight: bold;
                        padding: 5px;
                        background-color: #fadbd8;
                        border-radius: 3px;
                    }
                """)

        except Exception as e:
            logger.error(f"更新调试模式状态显示失败: {e}")

    def _apply_debug_mode_immediately(self, enabled: bool):
        """立即应用调试模式设置"""
        try:
            # 获取日志配置管理器
            from utils.log_config_manager import get_log_config_manager
            log_config_manager = get_log_config_manager()

            if log_config_manager:
                # 设置调试模式
                log_config_manager.set_debug_mode(enabled)
            else:
                logger.warning("日志配置管理器未初始化，无法立即应用调试模式设置")

        except Exception as e:
            logger.error(f"立即应用调试模式设置失败: {e}")

    def load_settings(self):
        """加载设置"""
        self._loading = True
        try:
            if self.debug_mode_check:
                debug_mode = self.config_manager.get('logging.debug_mode', True)
                self.debug_mode_check.setChecked(debug_mode)
                self._update_debug_mode_status(debug_mode)

            # 加载日志设置
            if self.enable_logging_check:
                logging_enabled = self.config_manager.get('communication.enable_logging', False)
                self.enable_logging_check.setChecked(logging_enabled)

            if self.enable_system_log_check:
                system_log_enabled = self.config_manager.get('logging.enable_system_log', True)
                self.enable_system_log_check.setChecked(system_log_enabled)

            if self.log_level_combo:
                log_level = self.config_manager.get('logging.level', 'INFO')
                self.log_level_combo.setCurrentText(log_level)

            logger.debug("日志设置加载完成")

        except Exception as e:
            logger.error(f"加载日志设置失败: {e}")
        finally:
            self._loading = False

    def apply_settings(self):
        """应用设置"""
        try:
            if self.debug_mode_check:
                debug_mode = self.debug_mode_check.isChecked()
                self.config_manager.set('logging.debug_mode', debug_mode)

            # 保存日志设置
            if self.enable_logging_check:
                self.config_manager.set('communication.enable_logging', self.enable_logging_check.isChecked())

            if self.enable_system_log_check:
                self.config_manager.set('logging.enable_system_log', self.enable_system_log_check.isChecked())

            if self.log_level_combo:
                self.config_manager.set('logging.level', self.log_level_combo.currentText())

            logger.info("日志设置应用成功")

        except Exception as e:
            logger.error(f"应用日志设置失败: {e}")
            raise


class DeviceSettingsUIManager(QObject):
    """设备设置界面管理器"""

    def __init__(self, parent_widget: QWidget):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget

        # 控件字典
        self.controls = {}

        logger.debug("设备设置界面管理器初始化完成")

    def create_ui(self):
        """创建用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self.parent_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # 创建内容容器
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)

        # 创建2列布局
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(20)

        # 创建左列布局
        left_column = QVBoxLayout()
        left_column.setSpacing(15)

        # 创建右列布局
        right_column = QVBoxLayout()
        right_column.setSpacing(15)

        # 左列：阻抗测试仪设置（内容较多，单独占一列）
        impedance_group = self._create_impedance_group()
        left_column.addWidget(impedance_group)

        # 左列添加弹性空间
        left_column.addStretch()

        # 右列：扫码枪设置 + 打印机设置 + 日志设置
        barcode_group = self._create_barcode_scanner_group()
        right_column.addWidget(barcode_group)

        printer_group = self._create_printer_group()
        right_column.addWidget(printer_group)

        log_group = self._create_log_group()
        right_column.addWidget(log_group)

        # 右列添加弹性空间
        right_column.addStretch()

        # 将左右列添加到内容布局
        content_layout.addLayout(left_column, 1)  # 左列占1份
        content_layout.addLayout(right_column, 1)  # 右列占1份

        # 将滚动区域添加到主布局
        main_layout.addWidget(scroll_area)

        return self.controls

    def _create_impedance_group(self) -> QGroupBox:
        """创建阻抗仪设置组"""
        group = QGroupBox("阻抗测试仪设置")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QGridLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 串口端口
        layout.addWidget(QLabel("串口端口:"), 0, 0)
        self.controls['serial_port_combo'] = QComboBox()
        self.controls['serial_port_combo'].setEditable(True)
        self.controls['serial_port_combo'].setToolTip("选择串口端口号")
        # 添加默认串口选项（防止刷新失败时下拉框为空）
        self.controls['serial_port_combo'].addItems([
            "COM1", "COM2", "COM3", "COM4", "COM5", "COM6",
            "COM7", "COM8", "COM9", "COM10", "COM11", "COM12",
            "COM13", "COM14", "COM15", "COM16"
        ])
        self.controls['serial_port_combo'].setCurrentText("COM13")
        layout.addWidget(self.controls['serial_port_combo'], 0, 1)

        # 刷新串口按钮
        self.controls['refresh_serial_button'] = QPushButton("刷新")
        self.controls['refresh_serial_button'].setMaximumWidth(80)
        self.controls['refresh_serial_button'].setToolTip("刷新可用串口列表")
        layout.addWidget(self.controls['refresh_serial_button'], 0, 2)

        # 连接测试按钮
        self.controls['test_connection_button'] = QPushButton("测试连接")
        self.controls['test_connection_button'].setMaximumWidth(100)
        layout.addWidget(self.controls['test_connection_button'], 0, 3)

        # 波特率
        layout.addWidget(QLabel("波特率:"), 1, 0)
        self.controls['serial_baudrate_combo'] = QComboBox()
        self.controls['serial_baudrate_combo'].addItems([
            "9600", "19200", "38400", "57600", "115200", "230400"
        ])
        self.controls['serial_baudrate_combo'].setCurrentText("115200")
        self.controls['serial_baudrate_combo'].setToolTip("设置串口波特率")
        layout.addWidget(self.controls['serial_baudrate_combo'], 1, 1)

        # 连接超时
        layout.addWidget(QLabel("连接超时:"), 2, 0)
        self.controls['connection_timeout_spin'] = QSpinBox()
        self.controls['connection_timeout_spin'].setRange(1, 60)
        self.controls['connection_timeout_spin'].setValue(10)
        self.controls['connection_timeout_spin'].setSuffix(" 秒")
        self.controls['connection_timeout_spin'].setToolTip("设备连接超时时间")
        layout.addWidget(self.controls['connection_timeout_spin'], 2, 1)

        # 自动连接
        self.controls['auto_connect_check'] = QCheckBox("启动时自动连接")
        self.controls['auto_connect_check'].setToolTip("程序启动时自动连接到上次使用的串口")
        layout.addWidget(self.controls['auto_connect_check'], 3, 0, 1, 2)

        # 自动重连
        self.controls['auto_reconnect_check'] = QCheckBox("启用自动重连")
        self.controls['auto_reconnect_check'].setToolTip("连接断开时自动尝试重新连接")
        layout.addWidget(self.controls['auto_reconnect_check'], 4, 0, 1, 2)

        # 重连间隔
        layout.addWidget(QLabel("重连间隔:"), 5, 0)
        self.controls['reconnect_interval_spin'] = QSpinBox()
        self.controls['reconnect_interval_spin'].setRange(1, 300)
        self.controls['reconnect_interval_spin'].setValue(30)
        self.controls['reconnect_interval_spin'].setSuffix(" 秒")
        self.controls['reconnect_interval_spin'].setToolTip("自动重连的间隔时间")
        layout.addWidget(self.controls['reconnect_interval_spin'], 5, 1)

        # 连接状态显示
        layout.addWidget(QLabel("连接状态:"), 6, 0)
        self.controls['connection_status_label'] = QLabel("未连接")
        self.controls['connection_status_label'].setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.controls['connection_status_label'], 6, 1)

        return group

    def _create_barcode_scanner_group(self) -> QGroupBox:
        """创建扫码枪设置组"""
        group = QGroupBox("扫码枪设置")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QGridLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 启用扫码枪
        self.controls['barcode_scanner_enabled_check'] = QCheckBox("启用扫码枪")
        self.controls['barcode_scanner_enabled_check'].setToolTip("启用扫码枪进行电池序列号扫描")
        layout.addWidget(self.controls['barcode_scanner_enabled_check'], 0, 0, 1, 3)

        # 序列号长度设置（启用扫码枪时显示）
        self.controls['serial_length_label'] = QLabel("序列号长度:")
        layout.addWidget(self.controls['serial_length_label'], 1, 0)

        self.controls['serial_length_min_spin'] = QSpinBox()
        self.controls['serial_length_min_spin'].setRange(1, 50)
        self.controls['serial_length_min_spin'].setValue(8)
        self.controls['serial_length_min_spin'].setToolTip("序列号最小长度")
        layout.addWidget(self.controls['serial_length_min_spin'], 1, 1)

        self.controls['serial_length_to_label'] = QLabel("至")
        layout.addWidget(self.controls['serial_length_to_label'], 1, 2)

        self.controls['serial_length_max_spin'] = QSpinBox()
        self.controls['serial_length_max_spin'].setRange(1, 50)
        self.controls['serial_length_max_spin'].setValue(20)
        self.controls['serial_length_max_spin'].setToolTip("序列号最大长度")
        layout.addWidget(self.controls['serial_length_max_spin'], 1, 3)

        self.controls['serial_length_unit_label'] = QLabel("位")
        layout.addWidget(self.controls['serial_length_unit_label'], 1, 4)

        # 格式验证
        self.controls['format_validation_check'] = QCheckBox("启用格式验证")
        self.controls['format_validation_check'].setToolTip("验证序列号是否符合预期格式")
        layout.addWidget(self.controls['format_validation_check'], 2, 0, 1, 3)

        # 唯一性检查
        self.controls['uniqueness_check_check'] = QCheckBox("检查唯一性")
        self.controls['uniqueness_check_check'].setToolTip("检查序列号是否与已有记录重复")
        layout.addWidget(self.controls['uniqueness_check_check'], 3, 0, 1, 3)

        # 自动生成设置（禁用扫码枪时显示）
        self.controls['auto_generation_label'] = QLabel("自动生成规则:")
        layout.addWidget(self.controls['auto_generation_label'], 4, 0)

        # 前缀设置
        self.controls['prefix_label'] = QLabel("前缀:")
        layout.addWidget(self.controls['prefix_label'], 5, 0)

        self.controls['prefix_edit'] = QLineEdit()
        self.controls['prefix_edit'].setText("BAT")
        self.controls['prefix_edit'].setMaxLength(10)
        self.controls['prefix_edit'].setToolTip("序列号前缀，如：BAT")
        layout.addWidget(self.controls['prefix_edit'], 5, 1)

        # 分隔符
        self.controls['separator_label'] = QLabel("分隔符:")
        layout.addWidget(self.controls['separator_label'], 5, 2)

        self.controls['separator_edit'] = QLineEdit()
        self.controls['separator_edit'].setText("-")
        self.controls['separator_edit'].setMaxLength(3)
        self.controls['separator_edit'].setToolTip("分隔符，如：- 或 _")
        layout.addWidget(self.controls['separator_edit'], 5, 3)

        # 流水号位数
        self.controls['sequence_digits_label'] = QLabel("流水号位数:")
        layout.addWidget(self.controls['sequence_digits_label'], 6, 0)

        self.controls['sequence_digits_spin'] = QSpinBox()
        self.controls['sequence_digits_spin'].setRange(2, 8)
        self.controls['sequence_digits_spin'].setValue(4)
        self.controls['sequence_digits_spin'].setToolTip("流水号位数，如：4位表示0001-9999")
        layout.addWidget(self.controls['sequence_digits_spin'], 6, 1)

        # 示例显示
        self.controls['example_label'] = QLabel("示例:")
        layout.addWidget(self.controls['example_label'], 7, 0)

        self.controls['example_text_label'] = QLabel("BAT-20250131-0001")
        self.controls['example_text_label'].setStyleSheet("color: #007bff; font-weight: bold;")
        self.controls['example_text_label'].setToolTip("根据当前设置生成的序列号示例")
        layout.addWidget(self.controls['example_text_label'], 7, 1, 1, 3)

        # 设置控件组（用于控制可见性）
        self.controls['scanner_widgets'] = [
            self.controls['serial_length_label'],
            self.controls['serial_length_min_spin'],
            self.controls['serial_length_to_label'],
            self.controls['serial_length_max_spin'],
            self.controls['serial_length_unit_label'],
            self.controls['format_validation_check'],
            self.controls['uniqueness_check_check']
        ]

        self.controls['auto_gen_widgets'] = [
            self.controls['auto_generation_label'],
            self.controls['prefix_label'],
            self.controls['prefix_edit'],
            self.controls['separator_label'],
            self.controls['separator_edit'],
            self.controls['sequence_digits_label'],
            self.controls['sequence_digits_spin'],
            self.controls['example_label'],
            self.controls['example_text_label']
        ]

        return group

    def _create_printer_group(self) -> QGroupBox:
        """创建打印机设置组"""
        group = QGroupBox("打印机设置")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QGridLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 打印机类型
        layout.addWidget(QLabel("打印机类型:"), 0, 0)
        self.controls['printer_type_combo'] = QComboBox()
        self.controls['printer_type_combo'].addItems([
            "热敏打印机", "喷墨打印机", "激光打印机", "标签打印机"
        ])
        self.controls['printer_type_combo'].setToolTip("选择打印机类型")
        layout.addWidget(self.controls['printer_type_combo'], 0, 1)

        # 打印机名称
        layout.addWidget(QLabel("打印机名称:"), 1, 0)
        self.controls['printer_name_combo'] = QComboBox()
        self.controls['printer_name_combo'].setEditable(True)
        self.controls['printer_name_combo'].setToolTip("选择或输入打印机名称")
        # 添加默认打印机选项（防止刷新失败时下拉框为空）
        self.controls['printer_name_combo'].addItems([
            "Microsoft Print to PDF",
            "Microsoft XPS Document Writer",
            "NIIMBOT K3_W",
            "Generic / Text Only"
        ])
        layout.addWidget(self.controls['printer_name_combo'], 1, 1)

        # 刷新打印机列表按钮
        self.controls['refresh_printer_button'] = QPushButton("刷新")
        self.controls['refresh_printer_button'].setMaximumWidth(80)
        layout.addWidget(self.controls['refresh_printer_button'], 1, 2)

        # 打印机连接方式
        layout.addWidget(QLabel("连接方式:"), 2, 0)
        self.controls['printer_connection_combo'] = QComboBox()
        self.controls['printer_connection_combo'].addItems([
            "USB", "网络", "串口", "蓝牙"
        ])
        self.controls['printer_connection_combo'].setToolTip("选择打印机连接方式")
        layout.addWidget(self.controls['printer_connection_combo'], 2, 1)

        # 打印质量
        layout.addWidget(QLabel("打印质量:"), 3, 0)
        self.controls['print_quality_combo'] = QComboBox()
        self.controls['print_quality_combo'].addItems([
            "草稿", "标准", "高质量", "最佳"
        ])
        self.controls['print_quality_combo'].setToolTip("选择打印质量")
        layout.addWidget(self.controls['print_quality_combo'], 3, 1)

        # 测试打印按钮
        self.controls['test_print_button'] = QPushButton("测试打印")
        self.controls['test_print_button'].setMaximumWidth(100)
        layout.addWidget(self.controls['test_print_button'], 3, 2)

        # 打印机状态
        layout.addWidget(QLabel("打印机状态:"), 4, 0)
        self.controls['printer_status_label'] = QLabel("未连接")
        self.controls['printer_status_label'].setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.controls['printer_status_label'], 4, 1)

        return group

    def _create_log_group(self) -> QGroupBox:
        """创建日志设置组"""
        group = QGroupBox("日志设置")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QGridLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self.controls['debug_mode_check'] = QCheckBox("调试模式")
        self.controls['debug_mode_check'].setToolTip("启用调试模式以显示详细的日志信息\n关闭后将完全禁用日志输出，提升生产环境性能")
        self.controls['debug_mode_check'].setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                color: #2c3e50;
            }
            QCheckBox::indicator:checked {
                background-color: #27ae60;
                border: 2px solid #27ae60;
            }
            QCheckBox::indicator:unchecked {
                background-color: #ecf0f1;
                border: 2px solid #bdc3c7;
            }
        """)
        layout.addWidget(self.controls['debug_mode_check'], 0, 0, 1, 2)

        # 启用通信日志
        self.controls['enable_logging_check'] = QCheckBox("启用通信日志")
        self.controls['enable_logging_check'].setToolTip("记录所有通信数据，用于调试")
        layout.addWidget(self.controls['enable_logging_check'], 1, 0, 1, 2)

        # 启用系统日志
        self.controls['enable_system_log_check'] = QCheckBox("启用系统日志")
        self.controls['enable_system_log_check'].setToolTip("记录系统运行日志")
        layout.addWidget(self.controls['enable_system_log_check'], 2, 0, 1, 2)

        # 日志级别
        layout.addWidget(QLabel("日志级别:"), 3, 0)
        self.controls['log_level_combo'] = QComboBox()
        self.controls['log_level_combo'].addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.controls['log_level_combo'].setCurrentText("INFO")
        self.controls['log_level_combo'].setToolTip("设置日志记录级别\n注意：当调试模式关闭时，所有日志输出都将被禁用")
        layout.addWidget(self.controls['log_level_combo'], 3, 1)

        self.controls['debug_mode_status_label'] = QLabel("调试模式：开启 - 日志输出正常")
        self.controls['debug_mode_status_label'].setStyleSheet("""
            QLabel {
                color: #27ae60;
                font-weight: bold;
                padding: 5px;
                background-color: #d5f4e6;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.controls['debug_mode_status_label'], 4, 0, 1, 2)

        return group


class DeviceSettingsWidget(QWidget):
    """设备设置页面组件 - 主协调器"""

    # 信号定义
    settings_changed = pyqtSignal()  # 设置变更信号

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        初始化设备设置页面

        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self._loading = False  # 防止加载时触发变更信号

        # 初始化管理器
        self._init_managers()

        # 初始化界面
        self._init_ui()

        # 初始化连接
        self._init_connections()

        # 加载设置并刷新设备列表
        self.load_settings()

        logger.debug("设备设置页面初始化完成")

    def _init_managers(self):
        """初始化管理器"""
        # 创建各个管理器
        self.impedance_manager = ImpedanceDeviceManager(self.config_manager, self)
        self.barcode_manager = BarcodeScannerManager(self.config_manager, self)
        self.printer_manager = PrinterManager(self.config_manager, self)
        self.logging_manager = LoggingSettingsManager(self.config_manager, self)
        self.ui_manager = DeviceSettingsUIManager(self)

    def _init_ui(self):
        """初始化用户界面"""
        # 创建UI并获取控件字典
        controls = self.ui_manager.create_ui()

        # 将控件分配给各个管理器
        self._distribute_controls(controls)

    def _distribute_controls(self, controls: dict):
        """将控件分配给各个管理器"""
        # 阻抗设备管理器控件
        impedance_controls = {
            'serial_port_combo': controls.get('serial_port_combo'),
            'serial_baudrate_combo': controls.get('serial_baudrate_combo'),
            'connection_timeout_spin': controls.get('connection_timeout_spin'),
            'auto_connect_check': controls.get('auto_connect_check'),
            'auto_reconnect_check': controls.get('auto_reconnect_check'),
            'reconnect_interval_spin': controls.get('reconnect_interval_spin'),
            'connection_status_label': controls.get('connection_status_label'),
            'refresh_serial_button': controls.get('refresh_serial_button'),
            'test_connection_button': controls.get('test_connection_button'),
        }
        self.impedance_manager.set_ui_controls(impedance_controls)

        # 扫码枪管理器控件
        barcode_controls = {
            'barcode_scanner_enabled_check': controls.get('barcode_scanner_enabled_check'),
            'serial_length_min_spin': controls.get('serial_length_min_spin'),
            'serial_length_max_spin': controls.get('serial_length_max_spin'),
            'format_validation_check': controls.get('format_validation_check'),
            'uniqueness_check_check': controls.get('uniqueness_check_check'),
            'prefix_edit': controls.get('prefix_edit'),
            'separator_edit': controls.get('separator_edit'),
            'sequence_digits_spin': controls.get('sequence_digits_spin'),
            'example_text_label': controls.get('example_text_label'),
            'scanner_widgets': controls.get('scanner_widgets', []),
            'auto_gen_widgets': controls.get('auto_gen_widgets', []),
        }
        self.barcode_manager.set_ui_controls(barcode_controls)

        # 打印机管理器控件
        printer_controls = {
            'printer_type_combo': controls.get('printer_type_combo'),
            'printer_name_combo': controls.get('printer_name_combo'),
            'printer_connection_combo': controls.get('printer_connection_combo'),
            'print_quality_combo': controls.get('print_quality_combo'),
            'printer_status_label': controls.get('printer_status_label'),
            'refresh_printer_button': controls.get('refresh_printer_button'),
            'test_print_button': controls.get('test_print_button'),
        }
        self.printer_manager.set_ui_controls(printer_controls)

        # 日志设置管理器控件
        logging_controls = {
            'enable_logging_check': controls.get('enable_logging_check'),
            'enable_system_log_check': controls.get('enable_system_log_check'),
            'log_level_combo': controls.get('log_level_combo'),
            'debug_mode_check': controls.get('debug_mode_check'),  # 新增
            'debug_mode_status_label': controls.get('debug_mode_status_label'),  # 新增
        }
        self.logging_manager.set_ui_controls(logging_controls)

    def _init_connections(self):
        """初始化信号连接"""
        # 连接各个管理器的设置变更信号
        self.impedance_manager.settings_changed.connect(self._on_setting_changed)
        self.barcode_manager.settings_changed.connect(self._on_setting_changed)
        self.printer_manager.settings_changed.connect(self._on_setting_changed)
        self.logging_manager.settings_changed.connect(self._on_setting_changed)

        # 连接阻抗设备管理器的连接状态变更信号
        self.impedance_manager.connection_status_changed.connect(self._on_connection_status_changed)

    def _on_setting_changed(self):
        """设置变更处理"""
        if not self._loading:
            self.settings_changed.emit()

    def _on_connection_status_changed(self, is_connected: bool, port: str):
        """连接状态变更处理"""
        try:
            # 应用设置
            self.apply_settings()

            # 通知主窗口重新连接
            self._notify_main_window_reconnect()

            logger.info(f"连接状态变更: {is_connected}, 端口: {port}")

        except Exception as e:
            logger.error(f"处理连接状态变更失败: {e}")

    def _notify_main_window_reconnect(self):
        """通知主窗口重新连接"""
        try:
            # 发送设置变更信号
            self.settings_changed.emit()

            # 尝试获取主窗口并触发重新连接
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'device_connection_manager'):
                main_window = main_window.parent()

            if main_window and hasattr(main_window, 'device_connection_manager'):
                # 使用QTimer异步执行重新连接，避免阻塞UI
                QTimer.singleShot(500, lambda: self._perform_reconnect(main_window))
                logger.info("已通知主窗口重新连接")
            else:
                logger.warning("无法找到主窗口，无法自动重新连接")

        except Exception as e:
            logger.error(f"通知主窗口重新连接失败: {e}")

    def _perform_reconnect(self, main_window):
        """执行重新连接"""
        try:
            device_manager = main_window.device_connection_manager

            # 先断开现有连接
            if device_manager.is_connected:
                device_manager.disconnect_device()

            # 等待一下再重新连接
            QTimer.singleShot(200, device_manager._perform_auto_connect)

        except Exception as e:
            logger.error(f"执行重新连接失败: {e}")

    def load_settings(self):
        """加载设置"""
        self._loading = True
        try:
            # 加载各个管理器的设置
            self.impedance_manager.load_settings()
            self.barcode_manager.load_settings()
            self.printer_manager.load_settings()
            self.logging_manager.load_settings()

            logger.debug("设备设置加载完成")

        except Exception as e:
            logger.error(f"加载设备设置失败: {e}")
        finally:
            self._loading = False

    def apply_settings(self):
        """应用设置"""
        try:
            # 应用各个管理器的设置
            self.impedance_manager.apply_settings()
            self.barcode_manager.apply_settings()
            self.printer_manager.apply_settings()
            self.logging_manager.apply_settings()

            logger.info("设备设置应用成功")

        except Exception as e:
            logger.error(f"应用设备设置失败: {e}")
            raise

    def validate_settings(self) -> bool:
        """
        验证设置

        Returns:
            是否验证通过
        """
        try:
            # 验证串口端口
            if self.impedance_manager.serial_port_combo:
                port_text = self.impedance_manager.serial_port_combo.currentText().strip()
                if not port_text:
                    logger.warning("串口端口不能为空")
                    return False

            # 验证波特率
            if self.impedance_manager.serial_baudrate_combo:
                try:
                    baudrate = int(self.impedance_manager.serial_baudrate_combo.currentText())
                    if baudrate <= 0:
                        logger.warning(f"波特率不合理: {baudrate}")
                        return False
                except ValueError:
                    logger.warning("波特率格式错误")
                    return False

            return True

        except Exception as e:
            logger.error(f"验证设备设置失败: {e}")
            return False

    def on_tab_activated(self):
        """选项卡激活时调用（优化版本）"""
        try:
            # 🚀 性能优化：立即同步连接状态，延迟执行耗时操作
            self.impedance_manager.sync_connection_status()

            # 🚀 性能优化：延迟执行设备列表刷新，避免阻塞UI
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self._delayed_device_refresh)

            logger.debug("设备设置页面激活，已启动延迟刷新")

        except Exception as e:
            logger.error(f"设备设置页面激活处理失败: {e}")

    def _delayed_device_refresh(self):
        """延迟执行设备刷新操作"""
        try:
            # 刷新设备列表（确保显示最新的设备信息）
            self.impedance_manager._refresh_serial_ports()
            self.printer_manager._refresh_printer_list_silent()

            # 如果启用自动连接，尝试连接到上次使用的串口
            self.impedance_manager.try_auto_connect()

            logger.debug("设备列表延迟刷新完成")

        except Exception as e:
            logger.error(f"延迟设备刷新失败: {e}")
