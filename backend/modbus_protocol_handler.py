# -*- coding: utf-8 -*-
"""
Modbus协议处理器
负责Modbus RTU协议的处理，包括CRC计算、命令构建、响应解析等

从CommunicationManager中提取的协议处理功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ModbusFunction(Enum):
    """Modbus功能码枚举"""
    READ_COILS = 0x01
    READ_DISCRETE_INPUTS = 0x02
    READ_HOLDING_REGISTERS = 0x03
    READ_INPUT_REGISTERS = 0x04
    WRITE_SINGLE_COIL = 0x05
    WRITE_SINGLE_REGISTER = 0x06
    WRITE_MULTIPLE_COILS = 0x0F
    WRITE_MULTIPLE_REGISTERS = 0x10


class ModbusProtocolHandler:
    """
    Modbus协议处理器
    
    职责：
    - CRC16校验计算
    - Modbus命令构建
    - 响应数据解析
    - 协议格式验证
    """
    
    def __init__(self, device_address: int = 1):
        """
        初始化Modbus协议处理器
        
        Args:
            device_address: 设备地址
        """
        self.device_address = device_address
        
        logger.debug(f"Modbus协议处理器初始化完成，设备地址: {self.device_address}")
    
    @staticmethod
    def calculate_crc16(data: bytes) -> int:
        """
        计算Modbus CRC16校验码
        
        Args:
            data: 待校验的数据
            
        Returns:
            CRC16校验码
        """
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc
    
    def build_command(self, function_code: int, start_address: int, 
                     count: int, data: Optional[bytes] = None) -> bytes:
        """
        构建Modbus命令
        
        Args:
            function_code: 功能码
            start_address: 起始地址
            count: 数量或值
            data: 附加数据（用于写操作）
            
        Returns:
            完整的Modbus命令（包含CRC）
        """
        try:
            # 构建基本命令
            cmd = bytearray([
                self.device_address,
                function_code,
                (start_address >> 8) & 0xFF,
                start_address & 0xFF,
                (count >> 8) & 0xFF,
                count & 0xFF
            ])
            
            # 添加数据（如果有）
            if data:
                if function_code in [0x0F, 0x10]:  # 写多个寄存器/线圈
                    cmd.append(len(data))  # 字节数
                cmd.extend(data)
            
            # 计算并添加CRC
            crc = self.calculate_crc16(cmd)
            cmd.extend([crc & 0xFF, (crc >> 8) & 0xFF])
            
            return bytes(cmd)
            
        except Exception as e:
            logger.error(f"构建Modbus命令失败: {e}")
            return b''
    
    def build_read_registers_command(self, start_address: int, count: int, 
                                   function_code: int = 0x04) -> bytes:
        """
        构建读取寄存器命令
        
        Args:
            start_address: 起始地址
            count: 寄存器数量
            function_code: 功能码（默认0x04读输入寄存器）
            
        Returns:
            Modbus命令
        """
        return self.build_command(function_code, start_address, count)
    
    def build_write_registers_command(self, start_address: int, values: List[int]) -> bytes:
        """
        构建写多个寄存器命令
        
        Args:
            start_address: 起始地址
            values: 要写入的值列表
            
        Returns:
            Modbus命令
        """
        try:
            # 构建数据部分
            data = bytearray()
            for value in values:
                data.extend([(value >> 8) & 0xFF, value & 0xFF])
            
            return self.build_command(0x10, start_address, len(values), data)
            
        except Exception as e:
            logger.error(f"构建写寄存器命令失败: {e}")
            return b''
    
    def build_write_single_register_command(self, address: int, value: int) -> bytes:
        """
        构建写单个寄存器命令

        Args:
            address: 寄存器地址
            value: 要写入的值

        Returns:
            Modbus命令
        """
        return self.build_command(0x06, address, value)

    def build_write_coils_command(self, start_address: int, coil_count: int, coil_values: List[bool]) -> bytes:
        """
        构建写多个线圈命令（0FH功能码）

        Args:
            start_address: 起始地址
            coil_count: 线圈数量
            coil_values: 线圈值列表（True=启动，False=停止）

        Returns:
            Modbus命令
        """
        try:

            # 将布尔值列表转换为字节数据
            # 每个字节包含8个线圈状态，低位在前
            byte_count = (coil_count + 7) // 8  # 向上取整
            data = bytearray()

            for byte_index in range(byte_count):
                byte_value = 0
                for bit_index in range(8):
                    coil_index = byte_index * 8 + bit_index
                    if coil_index < len(coil_values) and coil_values[coil_index]:
                        byte_value |= (1 << bit_index)
                data.append(byte_value)


            # 使用通用build_command方法构建0FH命令
            command = self.build_command(0x0F, start_address, coil_count, bytes(data))

            if command:
                logger.debug(f"✅ 0FH命令构建成功: {' '.join(f'{b:02X}' for b in command)}")
            else:
                logger.error("❌ 0FH命令构建失败")

            return command

        except Exception as e:
            logger.error(f"❌ 构建写线圈命令失败: {e}")
            return b''
    
    def verify_crc(self, data: bytes) -> bool:
        """
        验证CRC校验码
        
        Args:
            data: 包含CRC的数据
            
        Returns:
            是否校验通过
        """
        if len(data) < 4:
            return False
        
        # 分离数据和CRC
        message = data[:-2]
        received_crc = (data[-1] << 8) | data[-2]  # 高字节在后，低字节在前
        
        # 计算CRC
        calculated_crc = self.calculate_crc16(message)
        
        return received_crc == calculated_crc
    
    def get_expected_response_length(self, response: bytes) -> int:
        """
        获取期望的响应长度
        
        Args:
            response: 已接收的响应数据
            
        Returns:
            期望的总长度
        """
        if len(response) < 3:
            return 0
        
        func_code = response[1]
        
        if func_code in [0x03, 0x04]:  # 读取寄存器
            if len(response) >= 3:
                data_len = response[2]
                return 3 + data_len + 2  # 地址 + 功能码 + 数据长度 + 数据 + CRC
        elif func_code in [0x05, 0x06, 0x0F, 0x10]:  # 写入操作
            return 8  # 固定8字节响应
        elif func_code == 0x02:  # 读取离散输入
            if len(response) >= 3:
                data_len = response[2]
                return 3 + data_len + 2
        
        return 8  # 默认长度
    
    def parse_read_registers_response(self, response: bytes) -> Optional[List[int]]:
        """
        解析读取寄存器响应
        
        Args:
            response: 响应数据
            
        Returns:
            寄存器值列表
        """
        try:
            if len(response) < 5:
                logger.error("响应数据长度不足")
                return None
            
            # 验证地址和功能码
            if response[0] != self.device_address:
                logger.error(f"设备地址不匹配: 期望{self.device_address}, 收到{response[0]}")
                return None
            
            if response[1] not in [0x03, 0x04]:
                logger.error(f"功能码不匹配: 收到{response[1]}")
                return None
            
            # 获取数据长度
            data_len = response[2]
            if len(response) < 3 + data_len + 2:
                logger.error("响应数据长度不完整")
                return None
            
            # 解析寄存器值
            values = []
            for i in range(0, data_len, 2):
                offset = 3 + i
                value = (response[offset] << 8) | response[offset + 1]
                values.append(value)
            
            return values
            
        except Exception as e:
            logger.error(f"解析读取寄存器响应失败: {e}")
            return None
    
    def parse_write_response(self, response: bytes, expected_address: int, 
                           expected_count: int) -> bool:
        """
        解析写操作响应
        
        Args:
            response: 响应数据
            expected_address: 期望的地址
            expected_count: 期望的数量
            
        Returns:
            是否写入成功
        """
        try:
            if len(response) < 8:
                logger.error("写操作响应长度不足")
                return False
            
            # 验证响应格式
            if (response[0] == self.device_address and
                response[1] in [0x05, 0x06, 0x0F, 0x10] and  # 修复添加0x0F（写多个线圈）
                ((response[2] << 8) | response[3]) == expected_address):

                if response[1] == 0x10:  # 写多个寄存器
                    count = (response[4] << 8) | response[5]
                    return count == expected_count
                elif response[1] == 0x0F:  # 修复写多个线圈（0FH命令）
                    count = (response[4] << 8) | response[5]
                    return count == expected_count
                elif response[1] == 0x05:  # 写单个线圈
                    # 对于05H命令，验证返回的值是否正确
                    returned_value = (response[4] << 8) | response[5]
                    return returned_value == expected_count
                else:  # 写单个寄存器 (0x06)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"解析写操作响应失败: {e}")
            return False
    
    def format_command_hex(self, command: bytes) -> str:
        """
        格式化命令为十六进制字符串（用于日志）
        
        Args:
            command: 命令字节序列
            
        Returns:
            十六进制字符串
        """
        return ' '.join([f'{b:02X}' for b in command])
    
    def validate_response_basic(self, response: bytes, expected_function: int) -> bool:
        """
        基本响应验证
        
        Args:
            response: 响应数据
            expected_function: 期望的功能码
            
        Returns:
            是否验证通过
        """
        if len(response) < 3:
            return False
        
        return (response[0] == self.device_address and 
                response[1] == expected_function)
    
    def is_error_response(self, response: bytes) -> bool:
        """
        检查是否为错误响应
        
        Args:
            response: 响应数据
            
        Returns:
            是否为错误响应
        """
        if len(response) < 3:
            return False
        
        # Modbus错误响应的功能码会设置最高位
        return (response[0] == self.device_address and 
                response[1] & 0x80 != 0)
    
    def get_error_code(self, response: bytes) -> Optional[int]:
        """
        获取错误码
        
        Args:
            response: 错误响应数据
            
        Returns:
            错误码
        """
        if self.is_error_response(response) and len(response) >= 3:
            return response[2]
        return None
