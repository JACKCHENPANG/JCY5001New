# -*- coding: utf-8 -*-
"""
测试配置管理器
负责测试参数的配置和设备参数设置

从TestFlowManager中提取的配置管理功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import List, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class TestConfigurationManager(QObject):
    """
    测试配置管理器
    
    职责：
    - 设备参数配置
    - 测试参数验证
    - 通道配置管理
    """
    
    # 信号定义
    configuration_completed = pyqtSignal(bool)  # 配置完成
    configuration_progress = pyqtSignal(str, str)  # 配置进度 (参数, 状态)
    
    def __init__(self, config_manager, comm_manager):
        """
        初始化测试配置管理器
        
        Args:
            config_manager: 配置管理器
            comm_manager: 通信管理器
        """
        super().__init__()
        
        self.config_manager = config_manager
        self.comm_manager = comm_manager
        
        logger.debug("测试配置管理器初始化完成")
    
    def configure_device(self) -> bool:
        """
        配置设备参数
        
        Returns:
            是否配置成功
        """
        try:
            logger.info("📋 配置设备参数...")
            
            # 修复统一使用resistance_range配置项，避免混乱
            gain = self.config_manager.get('test_params.gain', 'auto')
            average_times = self.config_manager.get('test_params.average_times', 1)

            # 优先使用resistance_range，如果没有则使用battery_range作为备用
            resistance_range = self.config_manager.get('test_params.resistance_range', '5R')
            battery_range = self.config_manager.get('test_params.battery_range', '10mΩ以下')

            # 转换参数
            gain_value = self._convert_gain_parameter(gain)
            resistor_range = self._convert_range_parameter_fixed(resistance_range, battery_range)

            # 修复显示正确的档位映射关系
            range_display_map = {0x00: "1R档位(1mΩ以内)", 0x01: "5R档位(10mΩ以内)", 0x02: "10R档位(100mΩ以内)"}
            range_display = range_display_map.get(resistor_range, f"未知档位(0x{resistor_range:02X})")

            
            # 设置电阻档位
            self.configuration_progress.emit("电阻档位", "设置中")
            if not self.comm_manager.set_resistance_range_broadcast(resistor_range):
                logger.error("设置电阻档位失败")
                self.configuration_progress.emit("电阻档位", "失败")
                return False
            self.configuration_progress.emit("电阻档位", "完成")
            
            # 设置增益
            if gain_value > 0:
                self.configuration_progress.emit("增益设置", "设置中")
                if not self.comm_manager.set_gain(gain_value):
                    logger.warning("设置增益失败，继续测试")
                    self.configuration_progress.emit("增益设置", "警告")
                else:
                    self.configuration_progress.emit("增益设置", "完成")
            
            # 设置平均次数
            self.configuration_progress.emit("平均次数", "设置中")
            if not self.comm_manager.set_average_times(average_times):
                logger.warning("设置平均次数失败，继续测试")
                self.configuration_progress.emit("平均次数", "警告")
            else:
                self.configuration_progress.emit("平均次数", "完成")
            
            logger.info("✅ 设备参数配置完成")
            self.configuration_completed.emit(True)
            return True
            
        except Exception as e:
            logger.error(f"配置设备参数失败: {e}")
            self.configuration_completed.emit(False)
            return False
    
    def _convert_gain_parameter(self, gain: str) -> int:
        """
        转换增益参数
        
        Args:
            gain: 增益字符串
            
        Returns:
            增益数值
        """
        gain_map = {
            'auto': 0,
            '1': 1,
            '4': 4,
            '16': 16
        }
        return gain_map.get(gain, 0)
    
    def _convert_range_parameter(self, battery_range: str) -> int:
        """
        转换电阻档位参数（旧版本，保持兼容性）

        Args:
            battery_range: 电阻档位字符串

        Returns:
            档位数值
        """
        range_map = {
            '1mΩ以下': 0x00,   # 1R档位
            '10mΩ以下': 0x01,  # 5R档位
            '100mΩ以下': 0x02  # 10R档位
        }
        return range_map.get(battery_range, 0x01)

    def _convert_range_parameter_fixed(self, resistance_range: str, battery_range: str) -> int:
        """
        统一的电阻档位参数转换

        Args:
            resistance_range: 设备档位字符串 (1R/5R/10R)
            battery_range: UI显示档位字符串 (1mΩ以下/10mΩ以下/100mΩ以下)

        Returns:
            档位数值 (0x00/0x01/0x02)
        """
        # 优先使用resistance_range（设备标准格式）
        if resistance_range:
            device_range_map = {
                '1R': 0x00,   # 00H：1R档位 (1mΩ以内)
                '5R': 0x01,   # 01H：5R档位 (10mΩ以内)
                '10R': 0x02   # 02H：10R档位 (100mΩ以内)
            }
            if resistance_range in device_range_map:
                return device_range_map[resistance_range]

        # 备用：使用battery_range（UI显示格式）
        ui_range_map = {
            '1mΩ以下': 0x00,   # 1R档位
            '10mΩ以下': 0x01,  # 5R档位
            '100mΩ以下': 0x02  # 10R档位
        }
        result = ui_range_map.get(battery_range, 0x01)
        return result
    
    def get_enabled_channels(self) -> List[int]:
        """
        获取启用的通道列表
        
        Returns:
            启用的通道列表
        """
        try:
            # 从配置获取启用的通道
            enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))
            
            # 确保返回有效的通道列表
            if not enabled_channels:
                logger.warning("配置中没有启用的通道，使用默认通道1-8")
                enabled_channels = list(range(1, 9))
            
            # 验证通道号范围
            valid_channels = []
            for channel in enabled_channels:
                if isinstance(channel, int) and 1 <= channel <= 8:
                    valid_channels.append(channel)
                else:
                    logger.warning(f"无效的通道号: {channel}")
            
            if not valid_channels:
                logger.warning("没有有效的通道，使用默认通道1-8")
                valid_channels = list(range(1, 9))
            
            logger.debug(f"启用的通道: {valid_channels}")
            return valid_channels
            
        except Exception as e:
            logger.error(f"获取启用通道失败: {e}")
            return list(range(1, 9))  # 默认返回所有通道
    
    def get_test_parameters(self) -> Dict[str, Any]:
        """
        获取测试参数
        
        Returns:
            测试参数字典
        """
        try:
            return {
                'gain': self.config_manager.get('test_params.gain', 'auto'),
                'average_times': self.config_manager.get('test_params.average_times', 1),
                'battery_range': self.config_manager.get('test_params.battery_range', '10mΩ以下'),
                'test_mode': self.config_manager.get('test_params.test_mode', 'simultaneous'),
                'voltage_range': self.config_manager.get('test_params.voltage_range', {'min': 2.0, 'max': 5.0}),
                'enabled_channels': self.get_enabled_channels()
            }
            
        except Exception as e:
            logger.error(f"获取测试参数失败: {e}")
            return {}
    
    def validate_test_parameters(self) -> bool:
        """
        验证测试参数的有效性
        
        Returns:
            参数是否有效
        """
        try:
            parameters = self.get_test_parameters()
            
            # 验证增益设置
            valid_gains = ['auto', '1', '4', '16']
            if parameters.get('gain') not in valid_gains:
                logger.error(f"无效的增益设置: {parameters.get('gain')}")
                return False
            
            # 验证平均次数
            average_times = parameters.get('average_times', 1)
            if not isinstance(average_times, int) or average_times < 1 or average_times > 10:
                logger.error(f"无效的平均次数: {average_times}")
                return False
            
            # 验证电阻档位
            valid_ranges = ['1mΩ以下', '10mΩ以下', '100mΩ以下']
            if parameters.get('battery_range') not in valid_ranges:
                logger.error(f"无效的电阻档位: {parameters.get('battery_range')}")
                return False
            
            # 验证启用通道
            enabled_channels = parameters.get('enabled_channels', [])
            if not enabled_channels:
                logger.error("没有启用的通道")
                return False
            
            # 验证电压范围
            voltage_range = parameters.get('voltage_range', {})
            min_voltage = voltage_range.get('min', 2.0)
            max_voltage = voltage_range.get('max', 5.0)
            if min_voltage >= max_voltage or min_voltage < 0 or max_voltage > 10:
                logger.error(f"无效的电压范围: {min_voltage}V - {max_voltage}V")
                return False
            
            logger.info("✅ 测试参数验证通过")
            return True
            
        except Exception as e:
            logger.error(f"验证测试参数失败: {e}")
            return False
    
    def update_configuration(self, config_updates: Dict[str, Any]) -> bool:
        """
        更新配置
        
        Args:
            config_updates: 配置更新字典
            
        Returns:
            是否更新成功
        """
        try:
            for key, value in config_updates.items():
                if not self.config_manager.set(key, value):
                    logger.error(f"更新配置失败: {key} = {value}")
                    return False
            
            # 保存配置
            if not self.config_manager.save_config():
                logger.error("保存配置失败")
                return False
            
            logger.info(f"✅ 配置更新完成: {list(config_updates.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False
    
    def get_frequency_configuration(self) -> Dict[str, Any]:
        """
        获取频率配置
        
        Returns:
            频率配置字典
        """
        try:
            return {
                'mode': self.config_manager.get('frequency.mode', 'multi'),
                'multi_freq': self.config_manager.get('frequency.multi_freq', {}),
                'custom_list': self.config_manager.get('frequency.multi_freq.custom_list', [])
            }
            
        except Exception as e:
            logger.error(f"获取频率配置失败: {e}")
            return {}
    
    def get_outlier_detection_configuration(self) -> Dict[str, Any]:
        """
        获取离群检测配置
        
        Returns:
            离群检测配置字典
        """
        try:
            return {
                'enabled': self.config_manager.get('outlier_detection.enabled', False),
                'baseline_file': self.config_manager.get('outlier_detection.baseline_file', ''),
                'threshold': self.config_manager.get('outlier_detection.threshold', 20.0),
                'method': self.config_manager.get('outlier_detection.method', 'median')
            }
            
        except Exception as e:
            logger.error(f"获取离群检测配置失败: {e}")
            return {}
