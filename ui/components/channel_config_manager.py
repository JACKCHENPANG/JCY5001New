# -*- coding: utf-8 -*-
"""
通道配置管理器
负责单通道的配置加载、保存和管理

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Any, Optional
from utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ChannelConfigManager:
    """通道配置管理器"""
    
    def __init__(self, channel_number: int, config_manager: ConfigManager):
        """
        初始化通道配置管理器
        
        Args:
            channel_number: 通道号
            config_manager: 全局配置管理器
        """
        self.channel_number = channel_number
        self.config_manager = config_manager
        
    def load_test_count(self) -> int:
        """
        加载测试计数
        
        Returns:
            int: 测试计数
        """
        try:
            count = self.config_manager.get(f'test_count.channel_{self.channel_number}', 0)
            logger.debug(f"通道{self.channel_number}测试计数已加载: {count}")
            return count
        except Exception as e:
            logger.error(f"通道{self.channel_number}加载测试计数失败: {e}")
            return 0
    
    def save_test_count(self, count: int):
        """
        保存测试计数
        
        Args:
            count: 测试计数
        """
        try:
            self.config_manager.set(f'test_count.channel_{self.channel_number}', count)
            logger.debug(f"通道{self.channel_number}测试计数已保存: {count}")
        except Exception as e:
            logger.error(f"通道{self.channel_number}保存测试计数失败: {e}")
    
    def get_channel_enabled(self) -> bool:
        """
        获取通道启用状态
        
        Returns:
            bool: 是否启用
        """
        try:
            enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))
            is_enabled = self.channel_number in enabled_channels
            logger.debug(f"通道{self.channel_number}启用状态: {is_enabled}")
            return is_enabled
        except Exception as e:
            logger.error(f"通道{self.channel_number}获取启用状态失败: {e}")
            return True  # 默认启用
    
    def set_channel_enabled(self, enabled: bool):
        """
        设置通道启用状态
        
        Args:
            enabled: 是否启用
        """
        try:
            enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))
            
            if enabled and self.channel_number not in enabled_channels:
                enabled_channels.append(self.channel_number)
                enabled_channels.sort()
            elif not enabled and self.channel_number in enabled_channels:
                enabled_channels.remove(self.channel_number)
            
            self.config_manager.set('test.enabled_channels', enabled_channels)
            logger.debug(f"通道{self.channel_number}启用状态已设置: {enabled}")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}设置启用状态失败: {e}")
    
    def get_auto_detect_enabled(self) -> bool:
        """
        获取自动检测启用状态
        
        Returns:
            bool: 是否启用自动检测
        """
        try:
            enabled = self.config_manager.get('test_config.auto_detect', True)
            return enabled
        except Exception as e:
            logger.error(f"获取自动检测状态失败: {e}")
            return True  # 默认启用
    
    def get_voltage_range(self) -> tuple:
        """
        获取电压范围配置
        
        Returns:
            tuple: (最小值, 最大值)
        """
        try:
            min_voltage = self.config_manager.get('test_params.voltage_range.min', 2.889)
            max_voltage = self.config_manager.get('test_params.voltage_range.max', 3.531)
            return min_voltage, max_voltage
        except Exception as e:
            logger.error(f"获取电压范围配置失败: {e}")
            return 2.889, 3.531  # 默认范围
    
    def get_rs_range(self) -> tuple:
        """
        获取Rs范围配置
        
        Returns:
            tuple: (最小值, 最大值)
        """
        try:
            rs_grade_count = self.config_manager.get('impedance.rs_grade_count', 3)
            rs_min = self.config_manager.get('impedance.rs_min', 0.5)
            
            if rs_grade_count == 1:
                rs_max = self.config_manager.get('impedance.rs_grade1_max', 50.0)
            elif rs_grade_count == 2:
                rs_max = self.config_manager.get('impedance.rs_grade2_max', 50.0)
            else:  # 3档
                rs_max = self.config_manager.get('impedance.rs_grade3_max', 50.0)
            
            return rs_min, rs_max
        except Exception as e:
            logger.error(f"获取Rs范围配置失败: {e}")
            return 0.5, 50.0  # 默认范围
    
    def get_rct_range(self) -> tuple:
        """
        获取Rct范围配置
        
        Returns:
            tuple: (最小值, 最大值)
        """
        try:
            rct_min = self.config_manager.get('impedance.rct_min', 0.5)
            rct_max = self.config_manager.get('impedance.rct_grade3_max', 100.0)
            return rct_min, rct_max
        except Exception as e:
            logger.error(f"获取Rct范围配置失败: {e}")
            return 0.5, 100.0  # 默认范围
    
    def get_rs_grade_config(self) -> dict:
        """
        获取Rs档位配置
        
        Returns:
            dict: Rs档位配置
        """
        try:
            rs_grade_count = self.config_manager.get('impedance.rs_grade_count', 3)
            
            config = {
                'grade_count': rs_grade_count,
                'grade1_max': self.config_manager.get('impedance.rs_grade1_max', 17.0),
                'grade2_max': self.config_manager.get('impedance.rs_grade2_max', 33.5),
                'grade3_max': self.config_manager.get('impedance.rs_grade3_max', 50.0)
            }
            
            return config
        except Exception as e:
            logger.error(f"获取Rs档位配置失败: {e}")
            return {'grade_count': 3, 'grade1_max': 17.0, 'grade2_max': 33.5, 'grade3_max': 50.0}
    
    def get_rct_grade_config(self) -> dict:
        """
        获取Rct档位配置
        
        Returns:
            dict: Rct档位配置
        """
        try:
            config = {
                'grade1_max': self.config_manager.get('impedance.rct_grade1_max', 35.0),
                'grade2_max': self.config_manager.get('impedance.rct_grade2_max', 70.0),
                'grade3_max': self.config_manager.get('impedance.rct_grade3_max', 100.0)
            }
            
            return config
        except Exception as e:
            logger.error(f"获取Rct档位配置失败: {e}")
            return {'grade1_max': 35.0, 'grade2_max': 70.0, 'grade3_max': 100.0}
    
    def get_outlier_detection_config(self) -> dict:
        """
        获取离群检测配置
        
        Returns:
            dict: 离群检测配置
        """
        try:
            config = {
                'enabled': self.config_manager.get('outlier_detection.is_enabled', False),
                'threshold': self.config_manager.get('outlier_detection.threshold', 0.1),
                'baseline_file': self.config_manager.get('outlier_detection.baseline_file', '')
            }
            
            return config
        except Exception as e:
            logger.error(f"获取离群检测配置失败: {e}")
            return {'enabled': False, 'threshold': 0.1, 'baseline_file': ''}
    
    def save_channel_settings(self, settings: dict):
        """
        保存通道设置
        
        Args:
            settings: 设置字典
        """
        try:
            for key, value in settings.items():
                config_key = f'channel_{self.channel_number}.{key}'
                self.config_manager.set(config_key, value)
            
            logger.debug(f"通道{self.channel_number}设置已保存: {settings}")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}保存设置失败: {e}")
    
    def load_channel_settings(self) -> dict:
        """
        加载通道设置
        
        Returns:
            dict: 设置字典
        """
        try:
            settings = {}
            
            # 加载常用设置
            settings['enabled'] = self.get_channel_enabled()
            settings['test_count'] = self.load_test_count()
            settings['auto_detect'] = self.get_auto_detect_enabled()
            
            logger.debug(f"通道{self.channel_number}设置已加载: {settings}")
            return settings
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}加载设置失败: {e}")
            return {}
    
    def reset_channel_settings(self):
        """重置通道设置到默认值"""
        try:
            # 重置测试计数
            self.save_test_count(0)
            
            # 重置启用状态（默认启用）
            self.set_channel_enabled(True)
            
            logger.debug(f"通道{self.channel_number}设置已重置")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}重置设置失败: {e}")
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（通用方法）
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        try:
            return self.config_manager.get(key, default)
        except Exception as e:
            logger.error(f"获取配置值失败 {key}: {e}")
            return default
    
    def set_config_value(self, key: str, value: Any):
        """
        设置配置值（通用方法）
        
        Args:
            key: 配置键
            value: 配置值
        """
        try:
            self.config_manager.set(key, value)
        except Exception as e:
            logger.error(f"设置配置值失败 {key}: {e}")
