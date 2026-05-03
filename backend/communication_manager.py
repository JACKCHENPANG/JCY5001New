# -*- coding: utf-8 -*-
"""
重构后的通信管理器
使用组合模式集成各个专门的管理器，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Dict, List, Any, Optional, Callable

# 导入各个管理器
from backend.modbus_protocol_handler import ModbusProtocolHandler
from backend.serial_connection_manager import SerialConnectionManager
from backend.device_command_manager import DeviceCommandManager
from backend.data_read_manager import DataReadManager
from backend.device_status_manager import DeviceStatusManager

# 导入日志和异常工具
from utils.logger_helper import LoggerHelper, create_context_logger
from utils.exception_helper import ExceptionHelper, exception_handler

logger = logging.getLogger(__name__)


class CommunicationManager:
    """
    重构后的通信管理器
    
    职责：
    - 各个管理器的协调和集成
    - 统一的通信接口
    - 兼容性保证
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化重构后的通信管理器
        
        Args:
            config: 通信配置字典
        """
        self.config = config
        
        # 兼容性属性
        self.device_address = config.get('device_address', 1)
        self.port = config.get('port', 'COM16')
        self.baudrate = config.get('baudrate', 115200)
        self.timeout = config.get('timeout', 2.0)
        self.is_connected = False
        
        # 回调函数
        self.status_callback = None
        self.data_callback = None
        
        # 初始化各个管理器
        self._initialize_managers()
        
        LoggerHelper.log_operation_success(
            logger, "通信管理器初始化",
            端口=self.port, 波特率=self.baudrate, 设备地址=self.device_address
        )
    
    def _initialize_managers(self):
        """初始化各个管理器"""
        with create_context_logger(logger, "初始化通信管理器"):
            # 1. Modbus协议处理器
            self.protocol_handler = ModbusProtocolHandler(self.device_address)

            # 2. 串口连接管理器
            self.connection_manager = SerialConnectionManager(self.config)
            self.connection_manager.set_status_callback(self._on_connection_status_changed)

            # 3. 设备命令管理器
            self.command_manager = DeviceCommandManager(self.protocol_handler, self.connection_manager)

            # 4. 数据读取管理器
            self.data_manager = DataReadManager(self.protocol_handler, self.connection_manager)

            # 5. 设备状态码管理器
            self.status_manager = DeviceStatusManager()
    
    def _on_connection_status_changed(self, connected: bool):
        """连接状态变更回调"""
        self.is_connected = connected
        if self.status_callback:
            self.status_callback(connected)
    
    # ===== 连接管理接口 =====
    
    @exception_handler(default_return=False, logger=logger)
    def connect(self) -> bool:
        """
        建立连接（快速版本，跳过设备测试避免阻塞）

        Returns:
            是否连接成功
        """
        LoggerHelper.log_operation_start(logger, "建立通信连接", 端口=self.port, 模式="快速连接")

        # 建立串口连接
        if not self.connection_manager.connect():
            LoggerHelper.log_operation_failure(logger, "建立通信连接", Exception("串口连接失败"))
            return False

        # 跳过设备测试，直接标记为已连接
        # 这样可以避免在连接时阻塞UI
        self.is_connected = True
        LoggerHelper.log_operation_success(logger, "建立通信连接", 端口=self.port, 模式="快速连接")
        return True
    
    def disconnect(self):
        """断开连接"""
        with create_context_logger(logger, "断开通信连接"):
            self.connection_manager.disconnect()
            self.is_connected = False

    def reconnect_with_new_port(self, new_port: str) -> bool:
        """
        使用新端口重新连接

        Args:
            new_port: 新的串口号

        Returns:
            是否连接成功
        """
        try:
            LoggerHelper.log_operation_start(logger, "端口切换重连", 原端口=self.port, 新端口=new_port)

            # 先断开现有连接
            if self.is_connected:
                self.disconnect()

            # 等待端口完全释放
            import time
            time.sleep(0.2)

            # 更新配置
            old_port = self.port
            self.port = new_port
            self.config['port'] = new_port

            # 更新连接管理器的端口配置
            self.connection_manager.port = new_port
            self.connection_manager.config['port'] = new_port

            # 尝试连接新端口
            if self.connect():
                LoggerHelper.log_operation_success(logger, "端口切换重连", 原端口=old_port, 新端口=new_port)
                return True
            else:
                # 连接失败，恢复原端口配置
                self.port = old_port
                self.config['port'] = old_port
                self.connection_manager.port = old_port
                self.connection_manager.config['port'] = old_port

                LoggerHelper.log_operation_failure(logger, "端口切换重连", Exception("新端口连接失败"))
                return False

        except Exception as e:
            LoggerHelper.log_operation_failure(logger, "端口切换重连", e)
            return False
    
    def is_device_connected(self) -> bool:
        """
        检查设备是否已连接
        
        Returns:
            是否已连接
        """
        return self.is_connected and self.connection_manager.is_connection_alive()
    
    # ===== 设备命令接口 =====
    
    def set_frequency(self, frequency_hz: float) -> bool:
        """设置测量频率"""
        return self.command_manager.set_frequency(frequency_hz)
    
    def set_gain(self, gain_value: int) -> bool:
        """设置通道增益"""
        return self.command_manager.set_gain(gain_value)
    
    def set_average_times(self, average_times: int) -> bool:
        """设置平均次数"""
        return self.command_manager.set_average_times(average_times)
    
    def set_resistance_range_broadcast(self, range_value: int) -> bool:
        """设置电阻档位（群发）"""
        return self.command_manager.set_resistance_range_broadcast(range_value)

    def read_resistance_range_broadcast(self) -> Optional[List[int]]:
        """读取所有通道的电阻档位设置"""
        return self.command_manager.read_resistance_range_broadcast()
    
    def start_single_channel_measurement(self, channel_index: int) -> bool:
        """启动单个通道的阻抗测量"""
        return self.command_manager.start_single_channel_measurement(channel_index)
    
    def get_measurement_status(self, channel_index: int) -> Optional[int]:
        """获取通道测量状态"""
        return self.command_manager.get_measurement_status(channel_index)
    
    # ===== 数据读取接口 =====
    
    def get_channel_count(self) -> int:
        """获取设备通道数"""
        return self.data_manager.get_channel_count()
    
    def read_battery_voltages(self) -> List[float]:
        """读取所有通道的电池电压"""
        return self.data_manager.read_battery_voltages()
    
    def read_voltage(self, channel_index: int) -> Optional[float]:
        """读取单个通道的电压"""
        return self.data_manager.read_voltage(channel_index)
    
    def read_impedance_real(self) -> Optional[List[float]]:
        """读取所有通道的实部阻抗"""
        return self.data_manager.read_impedance_real()
    
    def read_impedance_imag(self) -> Optional[List[float]]:
        """读取所有通道的虚部阻抗"""
        return self.data_manager.read_impedance_imag()
    
    def get_device_info(self) -> Dict[str, Any]:
        """获取设备信息"""
        return self.data_manager.read_device_info()

    # ===== 同时测试模式接口 =====

    def set_frequency_broadcast(self, frequency_hz: float) -> bool:
        """群发设置频点（同时测试模式）"""
        return self.command_manager.set_frequency_broadcast(frequency_hz)

    def set_frequency_single_channel(self, channel_index: int, frequency_hz: float) -> bool:
        """为单个通道设置频点（并行错频模式）"""
        return self.command_manager.set_frequency_single_channel(channel_index, frequency_hz)

    def set_staggered_frequencies_batch(self, frequency_assignments: Dict[int, float]) -> bool:
        """批量设置错频频点（4200H指令）"""
        return self.command_manager.set_staggered_frequencies_batch(frequency_assignments)

    def start_impedance_measurement_broadcast(self, channel_indices: List[int]) -> bool:
        """群发开启阻抗测试（同时测试模式）"""
        return self.command_manager.start_impedance_measurement_broadcast(channel_indices)

    def get_measurement_status_broadcast(self) -> List[Optional[int]]:
        """群发读取状态码（同时测试模式）"""
        return self.command_manager.get_measurement_status_broadcast()

    def read_impedance_data_broadcast(self) -> dict:
        """批量获取阻抗数据（同时测试模式）"""
        return self.command_manager.read_impedance_data_broadcast()

    def start_impedance_measurement(self, channel_indices: List[int], independent: bool = False) -> bool:
        """启动阻抗测量"""
        return self.command_manager.start_impedance_measurement(channel_indices, independent)

    def stop_impedance_measurement(self, channel_indices: List[int]) -> bool:
        """停止阻抗测量"""
        return self.command_manager.stop_impedance_measurement(channel_indices)

    def read_impedance_data(self, channel_index: int, frequency: float = None) -> dict:
        """读取单个通道的阻抗数据（支持指定频率）"""
        try:
            reals = self.data_manager.read_impedance_real()
            imags = self.data_manager.read_impedance_imag()
            if reals and imags and 0 <= channel_index < len(reals) and channel_index < len(imags):
                return {'real': reals[channel_index], 'imag': imags[channel_index]}
            return {'real': 0.0, 'imag': 0.0}
        except Exception:
            return {'real': 0.0, 'imag': 0.0}

    def set_channel_frequency(self, channel_index: int, frequency: float) -> bool:
        """为单个通道设置频率"""
        return self.command_manager.set_channel_frequency(channel_index, frequency)

    def get_all_measurement_status(self) -> List[Optional[int]]:
        """获取所有通道的测量状态"""
        return self.command_manager.get_all_measurement_status()

    def read_channel_status(self, channel_number: int) -> Optional[int]:
        """
        读取单个通道的状态码（用于预检查）

        Args:
            channel_number: 通道号（1-8）

        Returns:
            状态码（如0x0003表示电池异常）
        """
        try:
            if not 1 <= channel_number <= 8:
                logger.error(f"无效的通道号: {channel_number}")
                return None

            # 转换为通道索引（0-7）
            channel_index = channel_number - 1

            # 使用现有的状态读取方法
            return self.command_manager.get_measurement_status(channel_index)

        except Exception as e:
            logger.error(f"读取通道{channel_number}状态码失败: {e}")
            return None

    # ===== 回调函数管理 =====
    
    def set_status_callback(self, callback: Callable[[bool], None]):
        """设置状态回调函数"""
        self.status_callback = callback
    
    def set_data_callback(self, callback: Callable[[Dict], None]):
        """设置数据回调函数"""
        self.data_callback = callback
    
    # ===== 兼容性接口 =====
    
    @staticmethod
    def calculate_crc16(data: bytes) -> int:
        """计算Modbus CRC16校验码（兼容性方法）"""
        return ModbusProtocolHandler.calculate_crc16(data)
    
    def send_modbus_command(self, command: bytes) -> Optional[bytes]:
        """
        发送Modbus命令并接收响应（兼容性方法）
        
        Args:
            command: Modbus命令字节序列
            
        Returns:
            响应字节序列
        """
        try:
            # 打印发送的命令
            cmd_hex = self.protocol_handler.format_command_hex(command)
            logger.info(f"📤 发送命令: {cmd_hex}")
            
            # 发送命令并接收响应
            response = self.connection_manager.send_and_receive(command)
            
            if response:
                # 打印接收的响应
                resp_hex = self.protocol_handler.format_command_hex(response)
                logger.info(f"📥 接收响应: {resp_hex} (长度: {len(response)})")
                
                # 验证CRC
                if self.protocol_handler.verify_crc(response):
                    logger.debug("✅ CRC校验通过")
                    self.connection_manager.reset_failure_count()
                    return response
                else:
                    logger.warning("❌ CRC校验失败")
                    return None
            else:
                logger.warning("❌ 未收到响应")
                return None
                
        except Exception as e:
            logger.error(f"发送Modbus命令失败: {e}")
            return None
    
    # ===== 状态码检查接口 =====

    def check_channels_status(self, enabled_channels: List[int]) -> Dict[str, Any]:
        """
        检查启用通道的状态码

        Args:
            enabled_channels: 启用的通道列表（1-8）

        Returns:
            状态检查结果字典
        """
        try:
            LoggerHelper.log_operation_start(logger, "检查通道状态", 通道数=len(enabled_channels))

            # 读取所有通道的状态码
            status_codes = []
            for channel_num in range(1, 9):  # 1-8通道
                channel_index = channel_num - 1
                status = self.command_manager.get_measurement_status(channel_index)
                status_codes.append(status if status is not None else 0x0000)

            # 使用状态管理器分析状态码
            channel_status = self.status_manager.check_channels_status(status_codes)
            available_channels = self.status_manager.get_available_channels(status_codes)
            error_channels = self.status_manager.get_error_channels(status_codes)
            status_summary = self.status_manager.get_status_summary(status_codes)

            # 过滤出启用且可用的通道
            enabled_available_channels = []
            enabled_error_channels = []

            for channel_num in enabled_channels:
                channel_index = channel_num - 1
                if channel_index in available_channels:
                    enabled_available_channels.append(channel_num)
                else:
                    # 检查是否有错误信息
                    for error_channel_index, error_msg in error_channels:
                        if error_channel_index == channel_index:
                            enabled_error_channels.append((channel_num, error_msg))
                            break

            result = {
                'all_status_codes': status_codes,
                'channel_status': channel_status,
                'enabled_channels': enabled_channels,
                'available_channels': enabled_available_channels,
                'error_channels': enabled_error_channels,
                'status_summary': status_summary,
                'can_start_test': len(enabled_available_channels) > 0
            }

            # 记录检查结果
            if enabled_error_channels:
                error_msgs = [msg for _, msg in enabled_error_channels]
                LoggerHelper.log_operation_failure(
                    logger, "检查通道状态",
                    Exception(f"发现异常通道: {error_msgs}"),
                    异常通道数=len(enabled_error_channels)
                )
            else:
                LoggerHelper.log_operation_success(
                    logger, "检查通道状态",
                    可用通道数=len(enabled_available_channels)
                )

            return result

        except Exception as e:
            LoggerHelper.log_operation_failure(logger, "检查通道状态", e)
            return {
                'all_status_codes': [],
                'channel_status': {},
                'enabled_channels': enabled_channels,
                'available_channels': [],
                'error_channels': [],
                'status_summary': {},
                'can_start_test': False,
                'error': str(e)
            }

    def get_channel_status_info(self, channel_index: int) -> Optional[Dict[str, Any]]:
        """
        获取单个通道的状态信息

        Args:
            channel_index: 通道索引（0-7）

        Returns:
            通道状态信息字典
        """
        try:
            status_code = self.command_manager.get_measurement_status(channel_index)
            if status_code is None:
                return None

            status_info = self.status_manager.get_channel_status_info(channel_index, status_code)

            return {
                'channel_index': status_info.channel_index,
                'channel_number': status_info.channel_index + 1,
                'status_code': status_info.status_code,
                'status_code_hex': f'0x{status_info.status_code:04X}',
                'status_enum': status_info.status_enum.name,
                'description': status_info.description,
                'severity': status_info.severity.value,
                'should_skip': status_info.should_skip,
                'can_test': status_info.can_test,
                'error_message': status_info.error_message
            }

        except Exception as e:
            logger.error(f"获取通道{channel_index + 1}状态信息失败: {e}")
            return None

    # ===== 管理器访问接口 =====

    def get_manager(self, manager_name: str):
        """
        获取指定的管理器实例

        Args:
            manager_name: 管理器名称

        Returns:
            管理器实例或None
        """
        managers = {
            'protocol': self.protocol_handler,
            'connection': self.connection_manager,
            'command': self.command_manager,
            'data': self.data_manager,
            'status': self.status_manager
        }
        return managers.get(manager_name)
    
    def get_status_info(self) -> Dict[str, Any]:
        """
        获取状态信息

        Returns:
            状态信息字典
        """
        return {
            'is_connected': self.is_connected,
            'connection_info': self.connection_manager.get_connection_info(),
            'device_config': self.command_manager.get_device_config(),
            'data_cache': self.data_manager.get_data_cache()
        }

    def get_connection_info(self) -> Dict[str, Any]:
        """
        获取连接信息（兼容性方法）

        Returns:
            连接信息字典
        """
        return self.connection_manager.get_connection_info()

    def get_actual_port(self) -> str:
        """
        获取实际连接的串口号

        Returns:
            实际连接的串口号
        """
        try:
            if hasattr(self.connection_manager, 'get_actual_port'):
                return self.connection_manager.get_actual_port()
            else:
                # 兼容性处理
                conn_info = self.connection_manager.get_connection_info()
                return conn_info.get('port', self.port)
        except Exception as e:
            logger.debug(f"获取实际串口号失败: {e}")
            return self.port
    
    def perform_health_check(self) -> bool:
        """执行健康检查"""
        return self.connection_manager.perform_health_check()
    
    def clear_caches(self):
        """清空所有缓存"""
        self.command_manager.clear_device_config()
        self.data_manager.clear_data_cache()
        logger.info("所有缓存已清空")


# 兼容性别名，保持向后兼容
ModbusRTUManager = CommunicationManager
