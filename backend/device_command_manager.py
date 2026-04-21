# -*- coding: utf-8 -*-
"""
设备命令管理器
负责设备命令的构建和执行，包括频率设置、参数配置等

从CommunicationManager中提取的设备命令功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class DeviceCommandManager:
    """
    设备命令管理器
    
    职责：
    - 设备频率设置
    - 设备参数配置
    - 测量控制命令
    - 设备状态查询
    """
    
    def __init__(self, protocol_handler, connection_manager):
        """
        初始化设备命令管理器

        Args:
            protocol_handler: Modbus协议处理器
            connection_manager: 串口连接管理器
        """
        self.protocol_handler = protocol_handler
        self.connection_manager = connection_manager

        # 设备配置缓存
        self.device_config = {}

        # 🚀 优化：预加载频率匹配器，避免重复导入
        from utils.frequency_matcher import frequency_matcher
        self.frequency_matcher = frequency_matcher

        # 新增停止命令去重机制
        self._stop_command_sent = False  # 标记是否已发送停止命令
        self._is_stopping = False  # 标记是否正在停止过程中

        logger.debug("设备命令管理器初始化完成")
    
    def set_frequency(self, frequency_hz: float) -> bool:
        """
        设置测量频率（群发所有通道）- 优化版本

        Args:
            frequency_hz: 频率值（Hz）

        Returns:
            是否设置成功
        """
        try:
            # 🚀 优化：使用预加载的频率匹配器
            original_freq = frequency_hz
            matched_freq = self.frequency_matcher.find_closest_preset_frequency(frequency_hz)

            # 🚀 优化：检查频率是否已经设置过，避免重复设置
            current_freq = self.device_config.get('frequency')
            if current_freq == matched_freq:
                logger.debug(f"频率未变化，跳过设置: {matched_freq}Hz")
                return True

            # 记录频率匹配信息（只在有差异时记录）
            if abs(matched_freq - original_freq) > 0.001:
                logger.info(f"频率匹配: {original_freq}Hz -> {matched_freq}Hz (差值: {matched_freq - original_freq:+.4f}Hz)")

            # 使用匹配后的频率
            frequency_hz = matched_freq
            
            # 频率值需要乘以1000
            freq_value = int(frequency_hz * 1000)
            
            # 构建频率数据（4字节）
            freq_data = [
                (freq_value >> 24) & 0xFF,
                (freq_value >> 16) & 0xFF,
                (freq_value >> 8) & 0xFF,
                freq_value & 0xFF
            ]
            
            # 构建命令
            command = self.protocol_handler.build_command(
                function_code=0x10,  # 写多个寄存器
                start_address=0x4F07,  # 群发地址
                count=2,  # 2个寄存器（32位数据）
                data=bytes(freq_data)
            )
            
            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.error("设置频率失败：无响应")
                return False
            
            # 验证响应
            if self.protocol_handler.parse_write_response(response, 0x4F07, 2):
                logger.info(f"✅ 频率设置成功: {frequency_hz}Hz")
                self.device_config['frequency'] = frequency_hz
                return True
            else:
                logger.error("设置频率失败：响应验证失败")
                return False
                
        except Exception as e:
            logger.error(f"设置频率失败: {e}")
            return False
    
    def set_gain(self, gain_value: int) -> bool:
        """
        设置通道增益（群发）
        
        Args:
            gain_value: 增益值（1, 4, 16）
            
        Returns:
            是否设置成功
        """
        try:
            # 增益值映射
            gain_mapping = {1: 0, 4: 1, 16: 2}
            if gain_value not in gain_mapping:
                logger.error(f"无效的增益值: {gain_value}")
                return False
            
            gain_code = gain_mapping[gain_value]
            
            # 构建命令：42 80 群发增益设置
            command = self.protocol_handler.build_command(
                function_code=0x06,  # 写单个寄存器
                start_address=0x4280,  # 群发增益地址
                count=gain_code,  # 增益码作为值
            )
            
            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.error("设置增益失败：无响应")
                return False
            
            # 验证响应
            if self.protocol_handler.parse_write_response(response, 0x4280, gain_code):
                logger.info(f"✅ 增益设置成功: {gain_value}")
                self.device_config['gain'] = gain_value
                return True
            else:
                logger.error("设置增益失败：响应验证失败")
                return False
                
        except Exception as e:
            logger.error(f"设置增益失败: {e}")
            return False
    
    def set_average_times(self, average_times: int) -> bool:
        """
        设置平均次数（群发）
        
        Args:
            average_times: 平均次数
            
        Returns:
            是否设置成功
        """
        try:
            # 构建命令：4F 01 群发平均次数设置
            command = self.protocol_handler.build_command(
                function_code=0x06,  # 写单个寄存器
                start_address=0x4F01,  # 群发平均次数地址
                count=average_times,  # 平均次数作为值
            )
            
            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.error("设置平均次数失败：无响应")
                return False
            
            # 验证响应
            if self.protocol_handler.parse_write_response(response, 0x4F01, average_times):
                logger.info(f"✅ 平均次数设置成功: {average_times}")
                self.device_config['average_times'] = average_times
                return True
            else:
                logger.error("设置平均次数失败：响应验证失败")
                return False
                
        except Exception as e:
            logger.error(f"设置平均次数失败: {e}")
            return False
    
    def set_resistance_range_broadcast(self, range_value: int) -> bool:
        """
        设置电阻档位（群发所有通道）

        Args:
            range_value: 电阻档位值（0x00=1R, 0x01=5R, 0x02=10R）

        Returns:
            是否设置成功
        """
        try:
            # 修正根据实际通信日志，使用4F03地址
            # 实际日志：01 06 4F 03 00 01 AE DE (设置5R档位)
            command = self.protocol_handler.build_command(
                function_code=0x06,  # 写单个寄存器
                start_address=0x4F03,  # 修正群发电阻档位地址 (4F02 -> 4F03)
                count=range_value,  # 档位值
            )

            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.error("❌ [设备命令] 设置电阻档位失败：无响应")
                return False

            # 验证响应
            if self.protocol_handler.parse_write_response(response, 0x4F03, range_value):
                # 修复显示完整的档位信息，明确档位与阻抗范围的对应关系
                range_details = {
                    0x00: "1R档位(1mΩ以内)",
                    0x01: "5R档位(10mΩ以内)",
                    0x02: "10R档位(100mΩ以内)"
                }
                range_detail = range_details.get(range_value, f"未知档位(0x{range_value:02X})")
                logger.info(f"✅ [设备命令] 电阻档位设置成功: {range_detail}")
                self.device_config['resistance_range'] = range_value
                return True
            else:
                logger.error("❌ [设备命令] 设置电阻档位失败：响应验证失败")
                return False

        except Exception as e:
            logger.error(f"设置电阻档位失败: {e}")
            return False

    def read_resistance_range_broadcast(self) -> Optional[List[int]]:
        """
        读取所有通道的电阻档位设置

        根据实际通信日志：
        发送：01 03 4F 03 00 00 A3 1E
        接收：01 03 10 00 01 00 01 00 01 00 01 00 01 00 01 00 01 00 01 93 B4
        (8个通道，每个通道2字节，值为00 01表示5R档位)

        Returns:
            各通道的档位值列表，失败返回None
        """
        try:
            # 根据实际日志读取8个通道的档位设置 (每通道2字节，共16字节)
            command = self.protocol_handler.build_command(
                function_code=0x03,  # 读保持寄存器
                start_address=0x4F03,  # 群发电阻档位地址
                count=8,  # 读取8个寄存器（8个通道）
            )

            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.error("❌ [设备命令] 读取电阻档位失败：无响应")
                return None

            # 解析响应
            values = self.protocol_handler.parse_read_registers_response(response)
            if values is None:
                logger.error("❌ [设备命令] 读取电阻档位失败：响应解析失败")
                return None

            # 根据实际日志每个通道的档位值是16位寄存器的低字节
            # 实际返回：00 01 00 01 00 01 00 01 00 01 00 01 00 01 00 01
            # 表示8个通道都是01(5R档位)
            channel_ranges = []
            for i, value in enumerate(values):
                range_value = value & 0xFF  # 取低字节作为档位值
                channel_ranges.append(range_value)

                range_details = {
                    0x00: "1R档位(1mΩ以内)",
                    0x01: "5R档位(10mΩ以内)",
                    0x02: "10R档位(100mΩ以内)"
                }
                range_detail = range_details.get(range_value, f"未知档位(0x{range_value:02X})")

            logger.info(f"✅ [设备命令] 电阻档位读取成功: {len(channel_ranges)}个通道")
            return channel_ranges

        except Exception as e:
            logger.error(f"读取电阻档位失败: {e}")
            return None
    
    def start_all_channels_measurement(self, channel_indices: List[int]) -> bool:
        """
        群发启动多个通道的阻抗测量（使用0FH命令）

        Args:
            channel_indices: 通道索引列表（0-7）

        Returns:
            是否启动成功
        """
        try:
            logger.info(f"🚀 0FH群发启动通道测量: {[ch+1 for ch in channel_indices]}")

            # 使用0FH命令真正的群发启动
            success = self._start_channels_with_0f_command(channel_indices)

            if success:
                logger.info(f"✅ 0FH群发启动成功: {len(channel_indices)}个通道同时启动")
                return True
            else:
                logger.warning("⚠️ 0FH群发启动失败，回退到逐个启动模式")
                # 回退到原来的逐个启动方式
                return self._start_channels_individually(channel_indices)

        except Exception as e:
            logger.error(f"群发启动测量失败: {e}")
            return False

    def _start_channels_with_0f_command(self, channel_indices: List[int]) -> bool:
        """
        使用0FH命令真正群发启动多个通道

        Args:
            channel_indices: 通道索引列表（0-7）

        Returns:
            是否启动成功
        """
        try:
            # 计算通道掩码：通道1对应bit 0，通道8对应bit 7
            channel_mask = 0
            for channel_index in channel_indices:
                if 0 <= channel_index < 8:
                    channel_mask |= (1 << channel_index)

            logger.debug(f"通道掩码: 0x{channel_mask:02X} (二进制: {channel_mask:08b})")

            # 构建0FH命令：01 0F 00 00 00 08 01 [通道掩码] xx xx
            command = self.protocol_handler.build_command(
                function_code=0x0F,  # 写多个线圈
                start_address=0x0000,  # 起始地址
                count=8,  # 8个通道（线圈数量）
                data=bytes([channel_mask])  # 通道掩码数据
            )

            if not command:
                logger.error("构建0FH命令失败")
                return False

            logger.debug(f"发送0FH命令: {' '.join(f'{b:02X}' for b in command)}")

            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.error("0FH群发启动无响应")
                return False

            logger.debug(f"收到0FH响应: {' '.join(f'{b:02X}' for b in response)}")

            # 验证0FH响应：应该是8字节固定格式
            if self._validate_0f_response(response, channel_indices):
                logger.info(f"✅ 0FH群发启动成功: 通道{[ch+1 for ch in channel_indices]}")
                return True
            else:
                logger.error("0FH群发启动响应验证失败")
                return False

        except Exception as e:
            logger.error(f"0FH群发启动异常: {e}")
            return False

    def _validate_0f_response(self, response: bytes, channel_indices: List[int]) -> bool:
        """
        验证0FH命令的响应

        Args:
            response: 设备响应
            channel_indices: 启动的通道列表

        Returns:
            响应是否有效
        """
        try:
            if not response or len(response) < 8:
                logger.error(f"0FH响应长度不足: {len(response) if response else 0}字节")
                return False

            # 0FH响应格式：01 0F 00 00 00 08 xx xx
            if response[0] != 0x01 or response[1] != 0x0F:
                logger.error(f"0FH响应头错误: {response[0]:02X} {response[1]:02X}")
                return False

            # 检查地址和数量
            start_addr = (response[2] << 8) | response[3]
            count = (response[4] << 8) | response[5]

            if start_addr != 0x0000 or count != 8:
                logger.error(f"0FH响应地址/数量错误: 地址={start_addr:04X}, 数量={count}")
                return False

            logger.debug("✅ 0FH响应验证通过")
            return True

        except Exception as e:
            logger.error(f"0FH响应验证异常: {e}")
            return False

    def _start_channels_individually(self, channel_indices: List[int]) -> bool:
        """
        逐个启动通道（回退方法）

        Args:
            channel_indices: 通道索引列表（0-7）

        Returns:
            是否启动成功
        """
        try:
            logger.info(f"回退到逐个启动模式: {[ch+1 for ch in channel_indices]}")

            success_count = 0
            for channel_index in channel_indices:
                if self.start_single_channel_measurement(channel_index):
                    success_count += 1
                else:
                    logger.warning(f"通道{channel_index+1}启动失败")

            if success_count == len(channel_indices):
                logger.info(f"✅ 逐个启动成功: {success_count}/{len(channel_indices)}个通道")
                return True
            elif success_count > 0:
                logger.warning(f"⚠️ 部分启动成功: {success_count}/{len(channel_indices)}个通道")
                return True
            else:
                logger.error("❌ 逐个启动失败: 所有通道都启动失败")
                return False

        except Exception as e:
            logger.error(f"逐个启动异常: {e}")
            return False

    def set_single_channel_frequency(self, channel_index: int, frequency_hz: float) -> bool:
        """
        设置单个通道的测量频率

        Args:
            channel_index: 通道索引（0-7）
            frequency_hz: 频率值（Hz）

        Returns:
            是否设置成功
        """
        try:
            if not 0 <= channel_index <= 7:
                logger.error(f"无效的通道索引: {channel_index}")
                return False

            # 🚀 优化：使用预加载的频率匹配器
            original_freq = frequency_hz
            matched_freq = self.frequency_matcher.find_closest_preset_frequency(frequency_hz)

            # 🚀 优化：检查通道频率是否已经设置过
            channel_freq_key = f'channel_{channel_index}_frequency'
            current_freq = self.device_config.get(channel_freq_key)
            if current_freq == matched_freq:
                logger.debug(f"通道{channel_index+1}频率未变化，跳过设置: {matched_freq}Hz")
                return True

            # 记录频率匹配信息（只在有差异时记录）
            if abs(matched_freq - original_freq) > 0.001:
                logger.debug(f"通道{channel_index+1}频率匹配: {original_freq}Hz -> {matched_freq}Hz")

            # 使用匹配后的频率
            frequency_hz = matched_freq

            # 频率值需要乘以1000
            freq_value = int(frequency_hz * 1000)

            # 构建频率数据（4字节）
            freq_data = [
                (freq_value >> 24) & 0xFF,
                (freq_value >> 16) & 0xFF,
                (freq_value >> 8) & 0xFF,
                freq_value & 0xFF
            ]

            # 计算单通道频率地址：4200H + 通道偏移*2（每个通道独立地址）
            # 通道1=4200H, 通道2=4202H, ..., 通道8=420EH
            channel_freq_address = 0x4200 + (channel_index * 2)


            # 构建命令
            command = self.protocol_handler.build_command(
                function_code=0x10,  # 写多个寄存器
                start_address=channel_freq_address,
                count=2,  # 2个寄存器（32位数据）
                data=bytes(freq_data)
            )

            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.error(f"设置通道{channel_index+1}频率失败：无响应")
                return False

            # 验证响应
            if self.protocol_handler.parse_write_response(response, channel_freq_address, 2):
                logger.debug(f"✅ 通道{channel_index+1}频率设置成功: {frequency_hz}Hz (地址: 0x{channel_freq_address:04X})")
                # 🚀 优化：缓存通道频率设置
                channel_freq_key = f'channel_{channel_index}_frequency'
                self.device_config[channel_freq_key] = frequency_hz
                return True
            else:
                logger.error(f"设置通道{channel_index+1}频率失败：响应验证失败 (地址: 0x{channel_freq_address:04X})")
                return False

        except Exception as e:
            logger.error(f"设置通道{channel_index+1}频率失败: {e}")
            return False

    def start_single_channel_measurement(self, channel_index: int) -> bool:
        """
        启动单个通道的阻抗测量

        Args:
            channel_index: 通道索引（0-7）

        Returns:
            是否启动成功
        """
        try:
            if not 0 <= channel_index <= 7:
                logger.error(f"无效的通道索引: {channel_index}")
                return False

            # 计算通道地址：00 00 + 通道偏移（正确的地址范围）
            channel_address = 0x0000 + channel_index

            # 构建命令：启动测量（使用05H功能码写单个线圈）
            command = self.protocol_handler.build_command(
                function_code=0x05,  # 写单个线圈（正确的功能码）
                start_address=channel_address,
                count=0xFF00,  # 启动值（FF00H表示启动）
            )

            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.error(f"启动通道{channel_index+1}测量失败：无响应")
                return False

            # 验证响应（05H命令的响应应该与发送命令相同）
            if self.protocol_handler.parse_write_response(response, channel_address, 0xFF00):
                logger.debug(f"✅ 通道{channel_index+1}测量启动成功")
                return True
            else:
                logger.error(f"启动通道{channel_index+1}测量失败：响应验证失败")
                return False

        except Exception as e:
            logger.error(f"启动通道{channel_index+1}测量失败: {e}")
            return False

    def reset_stop_state(self):
        """
        重置停止状态（用于新测试开始时）
        """
        self._stop_command_sent = False
        self._is_stopping = False
        logger.debug("🔄 停止状态已重置")

    def get_measurement_status(self, channel_index: int) -> Optional[int]:
        """
        获取通道测量状态
        
        Args:
            channel_index: 通道索引（0-7）
            
        Returns:
            状态值（0x0006表示完成）
        """
        try:
            if not 0 <= channel_index <= 7:
                logger.error(f"无效的通道索引: {channel_index}")
                return None
            
            # 计算状态地址：33 80 + 通道偏移（根据协议文档）
            status_address = 0x3380 + channel_index
            
            # 构建读取状态命令（使用04H读输入寄存器，根据协议文档）
            command = self.protocol_handler.build_read_registers_command(
                start_address=status_address,
                count=1,
                function_code=0x04
            )
            
            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.debug(f"读取通道{channel_index+1}状态失败：无响应")
                return None
            
            # 解析响应
            values = self.protocol_handler.parse_read_registers_response(response)
            if values and len(values) > 0:
                status = values[0]
                logger.debug(f"通道{channel_index+1}状态: 0x{status:04X}")
                return status
            else:
                logger.debug(f"解析通道{channel_index+1}状态失败")
                return None
                
        except Exception as e:
            logger.error(f"获取通道{channel_index+1}状态失败: {e}")
            return None
    
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
                            logger.warning(f"CRC校验失败 (尝试 {attempt + 1}/{retry_count})")
                    else:
                        logger.warning(f"未收到响应 (尝试 {attempt + 1}/{retry_count})")
                    
                    # 如果不是最后一次尝试，等待后重试
                    if attempt < retry_count - 1:
                        time.sleep(retry_delay)
                        
                except Exception as e:
                    logger.warning(f"发送命令失败 (尝试 {attempt + 1}/{retry_count}): {e}")
                    if attempt < retry_count - 1:
                        time.sleep(retry_delay)
            
            logger.error("发送命令失败：所有重试都失败")
            return None
            
        except Exception as e:
            logger.error(f"发送命令异常: {e}")
            return None
    
    def get_device_config(self) -> Dict[str, Any]:
        """
        获取设备配置缓存
        
        Returns:
            设备配置字典
        """
        return self.device_config.copy()
    
    def clear_device_config(self):
        """清空设备配置缓存"""
        self.device_config.clear()
        logger.info("设备配置缓存已清空")

    # ===== 同时测试模式批量操作方法 =====

    def set_frequency_broadcast(self, frequency_hz: float) -> bool:
        """
        群发设置频点（同时测试模式）

        Args:
            frequency_hz: 频率值（Hz）

        Returns:
            是否设置成功
        """
        try:
            logger.info(f"🔄 群发设置频点: {frequency_hz}Hz")

            # 使用现有的群发频率设置方法
            success = self.set_frequency(frequency_hz)

            if success:
                logger.info(f"✅ 群发频点设置成功: {frequency_hz}Hz")
            else:
                logger.error(f"❌ 群发频点设置失败: {frequency_hz}Hz")

            return success

        except Exception as e:
            logger.error(f"群发设置频点失败: {e}")
            return False

    def set_frequency_single_channel(self, channel_index: int, frequency_hz: float) -> bool:
        """
        为单个通道设置频点（并行错频模式）

        Args:
            channel_index: 通道索引（0-7）
            frequency_hz: 频率值（Hz）

        Returns:
            是否设置成功
        """
        try:

            # 使用现有的单通道频率设置方法
            success = self.set_single_channel_frequency(channel_index, frequency_hz)

            if success:
                logger.debug(f"✅ 通道{channel_index + 1}频点设置成功: {frequency_hz}Hz")
            else:
                logger.error(f"❌ 通道{channel_index + 1}频点设置失败: {frequency_hz}Hz")

            return success

        except Exception as e:
            logger.error(f"设置通道{channel_index + 1}频点异常: {e}")
            return False

    def set_staggered_frequencies_batch(self, frequency_assignments: Dict[int, float]) -> bool:
        """
        批量设置错频频点（4200H指令）- 一次性为多个通道设置不同频率

        Args:
            frequency_assignments: 通道频点分配字典 {channel_index: frequency}

        Returns:
            是否设置成功
        """
        try:

            # 🚀 优化：使用预加载的频率匹配器
            # 构建数据：每个通道4字节频率数据
            freq_data = []
            channel_count = 0

            # 按通道顺序（0-7）构建数据
            for channel_index in range(8):
                if channel_index in frequency_assignments:
                    frequency_hz = frequency_assignments[channel_index]

                    # 🚀 优化：使用预加载的频率匹配器
                    matched_freq = self.frequency_matcher.find_closest_preset_frequency(frequency_hz)

                    # 频率值需要乘以1000
                    freq_value = int(matched_freq * 1000)

                    # 添加4字节频率数据（大端序）
                    freq_data.extend([
                        (freq_value >> 24) & 0xFF,
                        (freq_value >> 16) & 0xFF,
                        (freq_value >> 8) & 0xFF,
                        freq_value & 0xFF
                    ])

                    channel_count += 1
                    # 🚀 优化：只在有差异时记录详细日志
                    if abs(matched_freq - frequency_hz) > 0.001:
                        logger.debug(f"   通道{channel_index+1}: {frequency_hz}Hz -> {matched_freq}Hz (0x{freq_value:08X})")
                    else:
                        logger.debug(f"   通道{channel_index+1}: {matched_freq}Hz (0x{freq_value:08X})")
                else:
                    # 未分配的通道使用0频率
                    freq_data.extend([0x00, 0x00, 0x00, 0x00])

            # 构建4200H批量设置命令
            # 地址：4200H，寄存器数量：16个（8个通道 * 2个寄存器/通道）
            command = self.protocol_handler.build_command(
                function_code=0x10,  # 写多个寄存器
                start_address=0x4200,  # 4200H起始地址
                count=16,  # 16个寄存器（8个通道，每个通道2个寄存器）
                data=bytes(freq_data)
            )

            logger.debug(f"发送4200H批量频率设置命令: {len(freq_data)}字节数据")

            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.error("4200H批量频率设置失败：无响应")
                return False

            # 验证响应
            if self.protocol_handler.parse_write_response(response, 0x4200, 16):
                logger.debug(f"✅ 4200H批量频率设置成功: {channel_count}个通道")
                return True
            else:
                logger.error("4200H批量频率设置失败：响应验证失败")
                return False

        except Exception as e:
            logger.error(f"4200H批量频率设置失败: {e}")
            return False

    def start_impedance_measurement_broadcast(self, channel_indices: List[int]) -> bool:
        """
        群发开启阻抗测试（同时测试模式）

        Args:
            channel_indices: 通道索引列表（0-7）

        Returns:
            是否启动成功
        """
        try:
            # 新增重置停止状态，准备新的测试
            self.reset_stop_state()

            logger.info(f"🚀 群发开启阻抗测试: 通道{[ch+1 for ch in channel_indices]}")

            # 使用现有的群发启动方法
            success = self.start_all_channels_measurement(channel_indices)

            if success:
                logger.info(f"✅ 群发阻抗测试启动成功: {len(channel_indices)}个通道")
            else:
                logger.error(f"❌ 群发阻抗测试启动失败")

            return success

        except Exception as e:
            logger.error(f"群发开启阻抗测试失败: {e}")
            return False

    def get_measurement_status_broadcast(self) -> List[Optional[int]]:
        """
        群发读取状态码（同时测试模式）

        Returns:
            所有通道的状态码列表
        """
        try:

            # 尝试使用群发状态查询
            statuses = self._get_all_channel_status_broadcast()

            if statuses:
                logger.debug(f"✅ 群发状态查询成功: {[f'0x{s:04X}' if s is not None else 'None' for s in statuses]}")
                return statuses
            else:
                # 回退到逐个查询
                logger.debug("群发状态查询失败，回退到逐个查询")
                return self._get_all_channel_status_individually()

        except Exception as e:
            logger.error(f"群发读取状态码失败: {e}")
            return [None] * 8

    def read_impedance_data_broadcast(self) -> dict:
        """
        批量获取阻抗数据（同时测试模式）

        Returns:
            包含所有通道阻抗数据的字典
        """
        try:

            # 使用数据管理器的批量读取方法
            from .data_read_manager import DataReadManager

            # 创建临时数据管理器实例来读取数据
            data_manager = DataReadManager(self.protocol_handler, self.connection_manager)

            # 读取实部和虚部阻抗
            real_impedances = data_manager.read_impedance_real()
            imag_impedances = data_manager.read_impedance_imag()

            if real_impedances is None or imag_impedances is None:
                logger.error("批量阻抗数据读取失败")
                return {}

            # 构建结果字典（按通道索引组织）
            result = {}

            # 确保两个列表长度一致
            min_length = min(len(real_impedances), len(imag_impedances))

            for channel_index in range(min_length):
                result[channel_index] = {
                    'real': real_impedances[channel_index],
                    'imag': imag_impedances[channel_index]
                }

            logger.debug(f"✅ 批量阻抗数据获取成功: {len(result)}个通道")
            if result:
                sample_data = [f"R={v['real']:.3f}, X={v['imag']:.3f}" for v in list(result.values())[:2]]
            return result

        except Exception as e:
            logger.error(f"批量获取阻抗数据失败: {e}")
            return {}

    def _get_all_channel_status_broadcast(self) -> List[Optional[int]]:
        """
        群发读取所有通道状态（优化版本）

        Returns:
            所有通道的状态码列表
        """
        try:
            # 构建群发状态查询命令：读取33 80到33 87（8个连续寄存器）
            command = self.protocol_handler.build_read_registers_command(
                start_address=0x3380,  # 起始地址：通道0状态
                count=8,  # 读取8个寄存器（8个通道）
                function_code=0x04  # 读输入寄存器
            )

            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.debug("群发状态查询无响应")
                return []

            # 解析响应
            values = self.protocol_handler.parse_read_registers_response(response)
            if values and len(values) >= 8:
                logger.debug(f"群发状态查询成功: {[f'0x{v:04X}' for v in values[:8]]}")
                return values[:8]
            else:
                logger.debug("群发状态查询响应解析失败")
                return []

        except Exception as e:
            logger.debug(f"群发状态查询失败: {e}")
            return []

    def start_impedance_measurement(self, channel_indices: List[int], independent: bool = False) -> bool:
        """
        启动阻抗测量

        Args:
            channel_indices: 通道索引列表（0-7）
            independent: 是否独立启动

        Returns:
            是否启动成功
        """
        try:
            # 新增重置停止状态，准备新的测试
            self.reset_stop_state()

            if independent:
                # 独立启动每个通道
                success_count = 0
                for channel_index in channel_indices:
                    if self.start_single_channel_measurement(channel_index):
                        success_count += 1
                return success_count == len(channel_indices)
            else:
                # 批量启动
                return self.start_all_channels_measurement(channel_indices)

        except Exception as e:
            logger.error(f"启动阻抗测量失败: {e}")
            return False

    def stop_impedance_measurement(self, channel_indices: List[int]) -> bool:
        """
        停止阻抗测量

        Args:
            channel_indices: 通道索引列表（0-7）

        Returns:
            是否停止成功
        """
        # 修复：使用线程锁防止重复执行
        if not hasattr(self, '_stop_impedance_lock'):
            import threading
            self._stop_impedance_lock = threading.Lock()
            self._stop_impedance_in_progress = False

        with self._stop_impedance_lock:
            if self._stop_impedance_in_progress:
                logger.warning("🛑 停止阻抗测量操作已在进行中，跳过重复调用")
                return True

            self._stop_impedance_in_progress = True

        try:
            # 新增检查是否已经发送过停止命令，避免重复
            if self._stop_command_sent or self._is_stopping:
                logger.debug("🛑 停止命令已发送或正在停止中，跳过重复调用")
                return True

            # 标记正在停止
            self._is_stopping = True

            logger.info(f"🛑 停止{len(channel_indices)}个通道的阻抗测量")

            # 修复检查连接状态，避免在断开时发送命令
            if not self.connection_manager.is_connected:
                logger.debug("🛑 设备连接已断开，跳过停止命令发送")
                self._stop_command_sent = True  # 标记已处理
                self._is_stopping = False
                return True  # 连接已断开，认为停止成功

            # 修复发送真正的停止命令到设备
            # 构建0FH命令停止所有通道: 01 0F 00 00 00 08 01 00
            command = self.protocol_handler.build_write_coils_command(
                start_address=0x0000,  # 起始地址：0000H
                coil_count=8,  # 线圈数量：8个通道
                coil_values=[False] * 8  # 停止所有通道（全部设为False）
            )

            if not command:
                logger.error("❌ 构建停止命令失败")
                self._is_stopping = False
                return False

            logger.info(f"🛑 发送停止命令: {' '.join(f'{b:02X}' for b in command)}")

            # 发送命令
            response = self._send_command_with_retry(command)
            if not response:
                logger.warning("⚠️ 停止阻抗测量无响应（可能设备已断开）")
                self._stop_command_sent = True  # 标记已处理
                self._is_stopping = False
                return True  # 无响应时也认为停止成功，避免错误日志

            logger.debug(f"收到停止响应: {' '.join(f'{b:02X}' for b in response)}")

            # 验证响应：0FH命令的响应格式
            if self.protocol_handler.parse_write_response(response, 0x0000, 8):
                logger.info(f"✅ 停止阻抗测量成功，通道: {[ch+1 for ch in channel_indices]}")
                self._stop_command_sent = True  # 标记停止命令已成功发送
                self._is_stopping = False
                return True
            else:
                logger.error("❌ 停止阻抗测量失败：响应验证失败")
                logger.debug(f"期望地址: 0x0000, 期望数量: 8")
                self._is_stopping = False
                return False

        except Exception as e:
            logger.error(f"❌ 停止阻抗测量失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            self._is_stopping = False
            return False
        finally:
            # 修复：确保停止标志被重置
            if hasattr(self, '_stop_impedance_lock'):
                with self._stop_impedance_lock:
                    self._stop_impedance_in_progress = False

    def set_channel_frequency(self, channel_index: int, frequency: float) -> bool:
        """
        为单个通道设置频率

        Args:
            channel_index: 通道索引（0-7）
            frequency: 频率值（Hz）

        Returns:
            是否设置成功
        """
        try:
            # 使用现有的单通道频率设置方法
            return self.set_single_channel_frequency(channel_index, frequency)

        except Exception as e:
            logger.error(f"设置通道{channel_index}频率失败: {e}")
            return False

    def get_all_measurement_status(self) -> List[Optional[int]]:
        """
        获取所有通道的测量状态

        Returns:
            所有通道的状态码列表
        """
        try:
            return self.get_measurement_status_broadcast()

        except Exception as e:
            logger.error(f"获取所有通道状态失败: {e}")
            return [None] * 8

    def _get_all_channel_status_individually(self) -> List[Optional[int]]:
        """
        逐个读取所有通道状态（回退方法）

        Returns:
            所有通道的状态码列表
        """
        try:
            statuses = []
            for channel_index in range(8):
                status = self.get_measurement_status(channel_index)
                statuses.append(status)

            logger.debug(f"逐个状态查询完成: {[f'0x{s:04X}' if s is not None else 'None' for s in statuses]}")
            return statuses

        except Exception as e:
            logger.error(f"逐个状态查询失败: {e}")
            return [None] * 8
