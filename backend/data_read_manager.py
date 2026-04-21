# -*- coding: utf-8 -*-
"""
数据读取管理器
负责从设备读取各种数据，包括电压、阻抗、设备信息等

从CommunicationManager中提取的数据读取功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class DataReadManager:
    """
    数据读取管理器
    
    职责：
    - 电池电压读取
    - 阻抗数据读取
    - 设备信息读取
    - 通道数读取
    """
    
    def __init__(self, protocol_handler, connection_manager):
        """
        初始化数据读取管理器

        Args:
            protocol_handler: Modbus协议处理器
            connection_manager: 串口连接管理器
        """
        self.protocol_handler = protocol_handler
        self.connection_manager = connection_manager

        # 数据缓存
        self.data_cache = {}

        # 电压缓存时效性控制（秒）- 修复测试中电压显示为0的问题
        self.voltage_cache_timeout = 30.0  # 30秒缓存有效期，避免测试过程中频繁失效
        self.voltage_cache_timestamp = 0

        # 最后成功读取的电压值（用于容错）
        self.last_valid_voltages = {}

        logger.debug("数据读取管理器初始化完成")
    
    def get_channel_count(self) -> int:
        """
        获取设备通道数
        
        Returns:
            通道数量
        """
        try:
            # 构建读取通道数命令
            command = self.protocol_handler.build_read_registers_command(
                start_address=0x3E00,  # 通道数地址
                count=1,
                function_code=0x04
            )
            
            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.error("读取通道数失败：无响应")
                return 0
            
            # 解析响应
            values = self.protocol_handler.parse_read_registers_response(response)
            if values and len(values) > 0:
                channel_count = values[0]
                logger.info(f"读取到设备通道数: {channel_count}")
                self.data_cache['channel_count'] = channel_count
                return channel_count
            else:
                logger.error("解析通道数响应失败")
                return 0
                
        except Exception as e:
            logger.error(f"获取通道数失败: {e}")
            return 0
    
    def read_battery_voltages(self) -> List[float]:
        """
        读取所有通道的电池电压（群发读取：01 04 33 40 00 08）

        Returns:
            电压列表（单位：V）
        """
        try:
            # 构建群发读取电压命令
            command = self.protocol_handler.build_read_registers_command(
                start_address=0x3340,  # 电压起始地址
                count=8,  # 8个通道
                function_code=0x04
            )

            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.error("群发读取电池电压失败：无响应")
                return []

            # 解析响应
            values = self.protocol_handler.parse_read_registers_response(response)
            if not values or len(values) < 8:
                logger.error("群发读取电池电压响应数据不足")
                return []

            # 转换为电压值
            voltages = []
            for i, value in enumerate(values[:8]):
                voltage = value / 10000.0  # 除以10000得到电压值
                voltages.append(voltage)
                logger.debug(f"通道{i+1}电压: {voltage:.4f}V")

                # 更新最后有效电压值（用于容错）
                self.last_valid_voltages[i] = voltage

            # 更新缓存和时间戳
            import time
            self.data_cache['battery_voltages'] = voltages
            self.voltage_cache_timestamp = time.time()

            logger.debug(f"群发读取电池电压成功: {voltages}")
            return voltages

        except Exception as e:
            logger.error(f"群发读取电池电压失败: {e}")
            return []
    
    def read_voltage(self, channel_index: int) -> Optional[float]:
        """
        读取单个通道的电压（优化版：使用群发读取缓存）

        Args:
            channel_index: 通道索引（0-7）

        Returns:
            电压值（V）
        """
        try:
            if not 0 <= channel_index <= 7:
                logger.error(f"无效的通道索引: {channel_index}")
                return None

            import time
            current_time = time.time()

            # 检查缓存是否有效（时效性检查）
            cache_valid = (
                'battery_voltages' in self.data_cache and
                self.voltage_cache_timestamp > 0 and
                (current_time - self.voltage_cache_timestamp) < self.voltage_cache_timeout
            )

            # 优化：优先使用有效缓存的群发电压数据
            if cache_valid:
                cached_voltages = self.data_cache['battery_voltages']
                if cached_voltages and channel_index < len(cached_voltages):
                    voltage = cached_voltages[channel_index]
                    logger.debug(f"使用缓存电压 - 通道{channel_index+1}: {voltage:.4f}V")
                    return voltage

            # 缓存无效或不存在，使用群发读取更新缓存
            logger.debug(f"缓存无效或过期，使用群发读取更新电压缓存")
            voltages = self.read_battery_voltages()

            if voltages and channel_index < len(voltages):
                voltage = voltages[channel_index]
                logger.debug(f"群发读取电压 - 通道{channel_index+1}: {voltage:.4f}V")
                return voltage
            else:
                logger.warning(f"群发读取失败，回退到单个读取 - 通道{channel_index+1}")
                voltage = self._read_single_voltage(channel_index)

                # 如果单个读取也失败，使用最后有效的电压值
                if voltage is None and channel_index in self.last_valid_voltages:
                    voltage = self.last_valid_voltages[channel_index]
                    logger.warning(f"使用最后有效电压值 - 通道{channel_index+1}: {voltage:.4f}V")

                return voltage

        except Exception as e:
            logger.error(f"读取通道{channel_index+1}电压失败: {e}")

            # 异常情况下也尝试使用最后有效的电压值
            if channel_index in self.last_valid_voltages:
                voltage = self.last_valid_voltages[channel_index]
                logger.warning(f"异常情况使用最后有效电压值 - 通道{channel_index+1}: {voltage:.4f}V")
                return voltage

            return None

    def _read_single_voltage(self, channel_index: int) -> Optional[float]:
        """
        读取单个通道电压（回退方法）

        Args:
            channel_index: 通道索引（0-7）

        Returns:
            电压值（V）
        """
        try:
            # 计算通道电压地址
            voltage_address = 0x3340 + channel_index

            # 构建读取命令
            command = self.protocol_handler.build_read_registers_command(
                start_address=voltage_address,
                count=1,
                function_code=0x04
            )

            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.debug(f"读取通道{channel_index+1}电压失败：无响应")
                return None

            # 解析响应
            values = self.protocol_handler.parse_read_registers_response(response)
            if values and len(values) > 0:
                voltage = values[0] / 10000.0
                logger.debug(f"单个读取电压 - 通道{channel_index+1}: {voltage:.4f}V")

                # 更新最后有效电压值（用于容错）
                self.last_valid_voltages[channel_index] = voltage

                return voltage
            else:
                logger.debug(f"解析通道{channel_index+1}电压失败")
                return None

        except Exception as e:
            logger.error(f"单个读取通道{channel_index+1}电压失败: {e}")
            return None
    
    def read_impedance_real(self) -> Optional[List[float]]:
        """
        读取所有通道的实部阻抗

        Returns:
            实部阻抗列表（单位：μΩ）
        """
        try:
            # 构建读取实部阻抗命令 - 修复地址和数据格式
            command = self.protocol_handler.build_read_registers_command(
                start_address=0x3000,  # 修复：正确的实部阻抗起始地址
                count=32,  # 修复：8个通道，每个4个寄存器（64位）
                function_code=0x04
            )

            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.error("读取实部阻抗失败：无响应")
                return None

            # 解析响应
            values = self.protocol_handler.parse_read_registers_response(response)
            if not values or len(values) < 32:
                logger.error(f"读取实部阻抗响应数据不足，期望32个寄存器，实际{len(values) if values else 0}个")
                return None

            # 转换为阻抗值（64位数据）
            impedances = []
            for i in range(8):
                # 每个通道4个寄存器（64位），大端序
                offset = i * 4
                value = 0
                for j in range(4):
                    value = (value << 16) | values[offset + j]

                # 处理64位有符号数
                if value & 0x8000000000000000:  # 负数
                    value = value - 0x10000000000000000

                # 除以100000得到微欧姆值
                impedance = value / 100000.0
                impedances.append(impedance)
                logger.debug(f"通道{i+1}实部阻抗: {impedance:.3f}μΩ")

            logger.debug(f"读取实部阻抗成功: {impedances}")
            return impedances

        except Exception as e:
            logger.error(f"读取实部阻抗失败: {e}")
            return None
    
    def read_impedance_imag(self) -> Optional[List[float]]:
        """
        读取所有通道的虚部阻抗

        Returns:
            虚部阻抗列表（单位：μΩ）
        """
        try:
            # 构建读取虚部阻抗命令 - 修复地址和数据格式
            command = self.protocol_handler.build_read_registers_command(
                start_address=0x3080,  # 修复：正确的虚部阻抗起始地址
                count=32,  # 修复：8个通道，每个4个寄存器（64位）
                function_code=0x04
            )

            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.error("读取虚部阻抗失败：无响应")
                return None

            # 解析响应
            values = self.protocol_handler.parse_read_registers_response(response)
            if not values or len(values) < 32:
                logger.error(f"读取虚部阻抗响应数据不足，期望32个寄存器，实际{len(values) if values else 0}个")
                return None

            # 转换为阻抗值（64位数据）
            impedances = []
            for i in range(8):
                # 每个通道4个寄存器（64位），大端序
                offset = i * 4
                value = 0
                for j in range(4):
                    value = (value << 16) | values[offset + j]

                # 处理64位有符号数
                if value & 0x8000000000000000:  # 负数
                    value = value - 0x10000000000000000

                # 除以100000得到微欧姆值
                impedance = value / 100000.0
                impedances.append(impedance)
                logger.debug(f"通道{i+1}虚部阻抗: {impedance:.3f}μΩ")

            logger.debug(f"读取虚部阻抗成功: {impedances}")
            return impedances

        except Exception as e:
            logger.error(f"读取虚部阻抗失败: {e}")
            return None
    
    def read_device_info(self) -> Dict[str, Any]:
        """
        读取设备信息
        
        Returns:
            设备信息字典
        """
        try:
            info = {
                'device_type': 'JCY5001A阻抗测试仪',
                'communication_type': 'Modbus RTU',
                'connected': self.connection_manager.is_connected
            }
            
            # 添加连接信息
            conn_info = self.connection_manager.get_connection_info()
            info.update(conn_info)
            
            if self.connection_manager.is_connected:
                # 获取通道数
                channel_count = self.get_channel_count()
                info['channel_count'] = channel_count
                
                # 获取电池电压（作为设备状态指示）
                voltages = self.read_battery_voltages()
                if voltages:
                    info['battery_voltages'] = voltages
                    info['status'] = '正常'
                else:
                    info['status'] = '读取数据失败'
            else:
                info['status'] = '未连接'
            
            self.data_cache['device_info'] = info
            return info
            
        except Exception as e:
            logger.error(f"获取设备信息失败: {e}")
            return {
                'device_type': 'JCY5001A阻抗测试仪',
                'communication_type': 'Modbus RTU',
                'status': f'错误: {e}',
                'connected': False
            }
    
    def test_connection(self) -> bool:
        """
        测试连接 - 通过读取设备通道数
        
        Returns:
            连接是否正常
        """
        try:
            channel_count = self.get_channel_count()
            return channel_count > 0
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
    
    def _send_command_with_retry(self, command: bytes) -> Optional[bytes]:
        """
        发送命令并重试
        
        Args:
            command: 要发送的命令
            
        Returns:
            响应数据
        """
        try:
            retry_config = self.connection_manager.get_retry_config()
            retry_count = retry_config['retry_count']
            retry_delay = retry_config['retry_delay']
            
            for attempt in range(retry_count):
                try:
                    # 发送命令并接收响应
                    response = self.connection_manager.send_and_receive(command)
                    
                    if response:
                        # 验证CRC
                        if self.protocol_handler.verify_crc(response):
                            self.connection_manager.reset_failure_count()
                            return response
                        else:
                            logger.debug(f"CRC校验失败 (尝试 {attempt + 1}/{retry_count})")
                    else:
                        logger.debug(f"未收到响应 (尝试 {attempt + 1}/{retry_count})")
                    
                    # 如果不是最后一次尝试，等待后重试
                    if attempt < retry_count - 1:
                        time.sleep(retry_delay)
                        
                except Exception as e:
                    logger.debug(f"发送命令失败 (尝试 {attempt + 1}/{retry_count}): {e}")
                    if attempt < retry_count - 1:
                        time.sleep(retry_delay)
            
            logger.debug("发送命令失败：所有重试都失败")
            return None
            
        except Exception as e:
            logger.error(f"发送命令异常: {e}")
            return None
    
    def get_data_cache(self) -> Dict[str, Any]:
        """
        获取数据缓存
        
        Returns:
            数据缓存字典
        """
        return self.data_cache.copy()
    
    def clear_data_cache(self):
        """清空数据缓存"""
        self.data_cache.clear()
        logger.info("数据缓存已清空")
