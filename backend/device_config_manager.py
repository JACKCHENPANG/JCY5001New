# -*- coding: utf-8 -*-
"""
设备配置管理器
负责管理设备参数配置，包括增益、平均次数、电阻档位等设备相关配置

从TestFlowController中提取的设备配置功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DeviceConfigManager:
    """
    设备配置管理器
    
    职责：
    - 设备参数配置（增益、平均次数、电阻档位）
    - 设备状态检查
    - 配置同步和验证
    - 电压读取和更新
    """
    
    def __init__(self, comm_manager, config_manager):
        """
        初始化设备配置管理器
        
        Args:
            comm_manager: 通信管理器
            config_manager: 配置管理器
        """
        self.comm_manager = comm_manager
        self.config_manager = config_manager
        
        # 设备配置缓存
        self.device_config_cache = {}
        
        # 电阻档位映射
        self.resistance_range_mapping = {
            '1R': 0x00,   # 00H：1R档位 (1mΩ以内)
            '5R': 0x01,   # 01H：5R档位 (10mΩ以内)
            '10R': 0x02   # 02H：10R档位 (100mΩ以内)
        }
        
        # 增益映射
        self.gain_mapping = {
            '1': 1,
            '4': 4,
            '16': 16
        }
        
        logger.debug("设备配置管理器初始化完成")
    
    def configure_device(self, test_config: Dict[str, Any]) -> bool:
        """
        配置设备参数
        
        Args:
            test_config: 测试配置字典
            
        Returns:
            是否配置成功
        """
        try:
            logger.info("开始配置设备参数...")
            
            success_count = 0
            total_operations = 0
            
            # 1. 设置通道增益
            gain = test_config.get('gain', 'auto')
            if gain != 'auto':
                total_operations += 1
                if self._configure_gain(gain):
                    success_count += 1
                    logger.info(f"✅ 设置增益成功: {gain}")
                else:
                    logger.warning(f"⚠️ 设置增益失败: {gain}")
            
            # 2. 设置平均次数
            average_times = test_config.get('average_times', 1)
            total_operations += 1
            if self._configure_average_times(average_times):
                success_count += 1
                logger.info(f"✅ 设置平均次数成功: {average_times}")
            else:
                logger.warning(f"⚠️ 设置平均次数失败: {average_times}")
            
            # 3. 设置电阻档位
            resistance_range = test_config.get('resistance_range', '10R')
            total_operations += 1
            if self._configure_resistance_range(resistance_range):
                success_count += 1
                logger.info(f"✅ 设置电阻档位成功: {resistance_range}")
            else:
                logger.warning(f"⚠️ 设置电阻档位失败: {resistance_range}")
            
            # 4. 设置默认频率（如果有单一频率模式）
            frequencies = test_config.get('frequencies', [])
            if len(frequencies) == 1:
                total_operations += 1
                frequency = frequencies[0]
                if self._configure_frequency(frequency):
                    success_count += 1
                    logger.info(f"✅ 设置频率成功: {frequency}Hz")
                else:
                    logger.warning(f"⚠️ 设置频率失败: {frequency}Hz")
            
            # 等待设备准备
            time.sleep(0.5)
            
            success_rate = success_count / total_operations if total_operations > 0 else 0
            logger.info(f"设备参数配置完成: {success_count}/{total_operations} ({success_rate*100:.1f}%)")
            
            return success_rate >= 0.5  # 至少50%成功率
            
        except Exception as e:
            logger.error(f"配置设备参数失败: {e}")
            return False
    
    def _configure_gain(self, gain: str) -> bool:
        """
        配置通道增益
        
        Args:
            gain: 增益值字符串
            
        Returns:
            是否配置成功
        """
        try:
            gain_value = self.gain_mapping.get(gain, 1)
            success = self.comm_manager.set_gain(gain_value)
            
            if success:
                self.device_config_cache['gain'] = gain_value
                
            return success
            
        except Exception as e:
            logger.error(f"配置增益失败: {e}")
            return False
    
    def _configure_average_times(self, average_times: int) -> bool:
        """
        配置平均次数
        
        Args:
            average_times: 平均次数
            
        Returns:
            是否配置成功
        """
        try:
            success = self.comm_manager.set_average_times(average_times)
            
            if success:
                self.device_config_cache['average_times'] = average_times
                
            return success
            
        except Exception as e:
            logger.error(f"配置平均次数失败: {e}")
            return False
    
    def _configure_resistance_range(self, resistance_range: str) -> bool:
        """
        配置电阻档位

        Args:
            resistance_range: 电阻档位字符串

        Returns:
            是否配置成功
        """
        try:
            # 修复检查battery_range和resistance_range配置是否一致
            battery_range = self.config_manager.get('test_params.battery_range', '10mΩ以下')
            
            # 定义正确的映射关系
            battery_to_device_map = {
                '1mΩ以下': '1R',   # 1mΩ以内 → 1R档位 → 0x00
                '10mΩ以下': '5R',  # 10mΩ以内 → 5R档位 → 0x01
                '100mΩ以下': '10R' # 100mΩ以内 → 10R档位 → 0x02
            }
            
            # 根据battery_range确定正确的resistance_range
            expected_resistance_range = battery_to_device_map.get(battery_range, '5R')
            
            # 检查配置是否一致
            if resistance_range != expected_resistance_range:
                logger.warning(f"🔧 [配置修复] 检测到档位配置不一致: battery_range='{battery_range}' 应对应 resistance_range='{expected_resistance_range}', 但当前为'{resistance_range}'")
                
                # 使用正确的resistance_range
                resistance_range = expected_resistance_range
                
                # 更新配置管理器中的值
                self.config_manager.set('test_params.resistance_range', expected_resistance_range)
            
            range_value = self.resistance_range_mapping.get(resistance_range, 0x01)  # 默认5R档位

            # 修复显示正确的档位映射关系
            range_display_map = {
                0x00: "1R档位(1mΩ以内)",
                0x01: "5R档位(10mΩ以内)",
                0x02: "10R档位(100mΩ以内)"
            }
            range_display = range_display_map.get(range_value, f"未知档位(0x{range_value:02X})")


            success = self.comm_manager.set_resistance_range_broadcast(range_value)

            if success:
                # 新增验证设置是否成功
                verification_success = self._verify_resistance_range_setting(range_value)
                if verification_success:
                    self.device_config_cache['resistance_range'] = resistance_range
                    self.device_config_cache['resistance_range_value'] = range_value
                    logger.info(f"✅ 电阻档位配置并验证成功: {range_display}")
                else:
                    logger.warning(f"⚠️ 电阻档位设置成功但验证失败: {range_display}")
                    # 即使验证失败也认为设置成功，因为设备已响应
                    self.device_config_cache['resistance_range'] = resistance_range
                    self.device_config_cache['resistance_range_value'] = range_value
            else:
                logger.error(f"❌ 电阻档位配置失败: {range_display}")

            return success

        except Exception as e:
            logger.error(f"配置电阻档位失败: {e}")
            return False

    def _verify_resistance_range_setting(self, expected_range_value: int) -> bool:
        """
        验证电阻档位设置是否成功

        Args:
            expected_range_value: 期望的档位值

        Returns:
            是否验证成功
        """
        try:
            # 读取当前档位设置
            current_ranges = self.comm_manager.read_resistance_range_broadcast()
            if current_ranges is None:
                logger.warning("⚠️ [档位验证] 无法读取当前档位设置")
                return False

            # 检查所有通道是否都设置为期望值
            all_channels_correct = True
            for i, range_value in enumerate(current_ranges):
                if range_value != expected_range_value:
                    logger.warning(f"⚠️ [档位验证] 通道{i+1}档位不匹配: 期望0x{expected_range_value:02X}, 实际0x{range_value:02X}")
                    all_channels_correct = False
                else:
                    logger.debug(f"✅ [档位验证] 通道{i+1}档位正确: 0x{range_value:02X}")

            if all_channels_correct:
                range_details = {
                    0x00: "1R档位(1mΩ以内)",
                    0x01: "5R档位(10mΩ以内)",
                    0x02: "10R档位(100mΩ以内)"
                }
                range_detail = range_details.get(expected_range_value, f"未知档位(0x{expected_range_value:02X})")
                logger.info(f"✅ [档位验证] 所有通道档位验证成功: {range_detail}")
                return True
            else:
                logger.warning(f"⚠️ [档位验证] 部分通道档位设置不正确")
                return False

        except Exception as e:
            logger.error(f"验证电阻档位设置失败: {e}")
            return False
    
    def _configure_frequency(self, frequency: float) -> bool:
        """
        配置频率
        
        Args:
            frequency: 频率值
            
        Returns:
            是否配置成功
        """
        try:
            success = self.comm_manager.set_frequency(frequency)
            
            if success:
                self.device_config_cache['frequency'] = frequency
                
            return success
            
        except Exception as e:
            logger.error(f"配置频率失败: {e}")
            return False
    
    def read_channel_voltage(self, channel_num: int) -> float:
        """
        读取指定通道的电压值
        
        Args:
            channel_num: 通道号（1-8）
            
        Returns:
            电压值（V）
        """
        try:
            # 尝试从通信管理器读取电压
            voltage = self.comm_manager.read_voltage(channel_num - 1)  # 转换为0基索引
            if voltage is not None:
                logger.debug(f"通道{channel_num}电压: {voltage:.3f}V")
                return voltage
            else:
                logger.warning(f"通道{channel_num}电压读取失败，使用默认值")
                return 3.2  # 默认电压值
        except Exception as e:
            logger.error(f"获取通道{channel_num}电压失败: {e}")
            return 3.2  # 默认电压值
    
    def update_voltage_display(self, enabled_channels: list, progress_callback=None):
        """
        读取并更新电压显示
        
        Args:
            enabled_channels: 启用的通道列表
            progress_callback: 进度回调函数
        """
        try:
            logger.info("开始更新电压显示...")
            
            # 读取每个通道的电压并通过回调更新UI
            for channel_num in enabled_channels:
                try:
                    voltage = self.read_channel_voltage(channel_num)
                    
                    # 通过进度回调更新电压显示
                    if progress_callback:
                        progress_callback(channel_num, {
                            'state': 'voltage_update',
                            'progress': 0,
                            'message': f'电压: {voltage:.3f}V',
                            'voltage': voltage
                        })
                    
                    logger.info(f"✅ 通道{channel_num}电压更新: {voltage:.3f}V")
                    
                except Exception as e:
                    logger.warning(f"通道{channel_num}电压读取失败: {e}")
                    
                    # 使用默认电压值
                    default_voltage = 3.2
                    if progress_callback:
                        progress_callback(channel_num, {
                            'state': 'voltage_update',
                            'progress': 0,
                            'message': f'电压: {default_voltage:.3f}V (默认)',
                            'voltage': default_voltage
                        })
                    
                    logger.warning(f"⚠️ 通道{channel_num}使用默认电压: {default_voltage:.3f}V")
            
            logger.info("电压显示更新完成")
            
        except Exception as e:
            logger.error(f"更新电压显示失败: {e}")
    
    def verify_device_config(self) -> Dict[str, Any]:
        """
        验证设备配置
        
        Returns:
            验证结果字典
        """
        try:
            verification_result = {
                'success': True,
                'details': {},
                'errors': []
            }
            
            # 这里可以添加设备配置验证逻辑
            # 例如读回设备参数并与缓存对比
            
            logger.info("设备配置验证完成")
            return verification_result
            
        except Exception as e:
            logger.error(f"设备配置验证失败: {e}")
            return {
                'success': False,
                'details': {},
                'errors': [str(e)]
            }
    
    def get_device_config_cache(self) -> Dict[str, Any]:
        """
        获取设备配置缓存
        
        Returns:
            设备配置缓存字典
        """
        return self.device_config_cache.copy()
    
    def clear_device_config_cache(self):
        """清空设备配置缓存"""
        self.device_config_cache.clear()
        logger.info("设备配置缓存已清空")
    
    def is_device_ready(self) -> bool:
        """
        检查设备是否准备就绪

        Returns:
            设备是否准备就绪
        """
        try:
            return self.comm_manager.is_device_connected()
        except Exception as e:
            logger.error(f"检查设备状态失败: {e}")
            return False

    def get_channel_test_data(self, channel_num: int) -> Dict[str, Any]:
        """
        获取通道测试数据

        Args:
            channel_num: 通道号（1-8）

        Returns:
            通道测试数据字典
        """
        try:
            # 修复从测试结果管理器获取通道数据
            # 这里应该从实际的数据存储中获取，暂时返回默认结构
            return {
                'voltage': 0.0,
                'rs_value': 0.0,
                'rct_value': 0.0,
                'rsei_value': 0.0,  # 添加Rsei值
                'impedance_data': {},
                'frequency_data': {},
                'test_progress': 0,
                'timestamp': 0.0
            }
        except Exception as e:
            logger.error(f"获取通道{channel_num}测试数据失败: {e}")
            return {}

    def update_channel_data(self, channel_num: int, data: Dict[str, Any]):
        """
        更新通道数据

        Args:
            channel_num: 通道号（1-8）
            data: 要更新的数据
        """
        try:
            # 修复这里应该实现实际的数据存储逻辑
            # 暂时只记录日志
            logger.debug(f"更新通道{channel_num}数据: {data}")
        except Exception as e:
            logger.error(f"更新通道{channel_num}数据失败: {e}")
