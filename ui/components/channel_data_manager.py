#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通道数据管理器
负责管理通道的测试数据，包括电压、阻抗、进度等

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ChannelTestData:
    """通道测试数据"""
    voltage: float = 0.0
    rs_value: float = 0.0
    rct_value: float = 0.0
    rsei_value: float = 0.0  # SEI膜电阻值
    test_progress: int = 0
    frequency_points: List[Tuple[float, float, float]] = field(default_factory=list)  # (freq, rs, rct)
    battery_code: str = ""  # 电池码
    test_start_time: Optional[float] = None  # 测试开始时间
    test_end_time: Optional[float] = None  # 测试结束时间

    def __post_init__(self):
        if self.frequency_points is None:
            self.frequency_points = []


@dataclass
class ChannelTestResult:
    """通道测试结果"""
    is_pass: bool = False
    grade: Optional[str] = None
    rs_final: float = 0.0
    rct_final: float = 0.0
    rsei_final: float = 0.0  # SEI膜电阻最终值
    voltage_final: float = 0.0
    test_time: float = 0.0
    error_messages: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        # error_messages 现在使用 field(default_factory=list)，不需要额外初始化
        pass


class ChannelDataManager:
    """通道数据管理器"""
    
    def __init__(self, channel_number: int):
        """
        初始化数据管理器
        
        Args:
            channel_number: 通道号（1-8）
        """
        self.channel_number = channel_number
        self.channel_index = channel_number - 1
        
        # 测试数据
        self.test_data = ChannelTestData()
        self.test_result = ChannelTestResult()
        
        # 数据验证范围
        self.voltage_range = (0.0, 5.0)  # 电压范围 0-5V
        self.rs_range = (0.0, 1000.0)   # Rs范围 0-1000mΩ
        self.rct_range = (0.0, 10000.0) # Rct范围 0-10000mΩ
        
        logger.debug(f"通道{self.channel_number}数据管理器初始化完成")
    
    def update_voltage(self, voltage: float) -> bool:
        """
        更新电压值
        
        Args:
            voltage: 电压值(V)
            
        Returns:
            是否更新成功
        """
        try:
            if self.validate_voltage(voltage):
                self.test_data.voltage = voltage
                logger.debug(f"通道{self.channel_number}电压更新: {voltage:.3f}V")
                return True
            else:
                logger.debug(f"通道{self.channel_number}电压值无效: {voltage:.3f}V")
                return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新电压失败: {e}")
            return False
    
    def update_impedance(self, rs_value: float, rct_value: float) -> bool:
        """
        更新阻抗值 - Jack的简化版本

        Args:
            rs_value: Rs值(mΩ)
            rct_value: Rct值(mΩ) - 总极化阻抗，包含原Rsei+Rct

        Returns:
            是否更新成功
        """
        try:
            rs_valid = self.validate_rs(rs_value)
            rct_valid = self.validate_rct(rct_value)

            # 修复放宽验证条件，允许单独更新Rs或Rct值
            # 这样可以确保测试过程中的数据能够正确保存
            if rs_valid or rct_valid:
                if rs_valid:
                    self.test_data.rs_value = rs_value
                if rct_valid:
                    self.test_data.rct_value = rct_value
                # Jack要求设置Rsei为0，不再单独计算
                self.test_data.rsei_value = 0.0
                return True
            else:
                logger.warning(f"通道{self.channel_number}阻抗值无效: Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")
                return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新阻抗失败: {e}")
            return False

    def force_update_impedance(self, rs_value: float, rct_value: float) -> bool:
        """
        强制更新阻抗值（绕过验证，用于打印等场景） - Jack的简化版本

        Args:
            rs_value: Rs值(mΩ)
            rct_value: Rct值(mΩ) - 总极化阻抗，包含原Rsei+Rct

        Returns:
            是否更新成功
        """
        try:
            self.test_data.rs_value = rs_value
            self.test_data.rct_value = rct_value
            # Jack要求设置Rsei为0，不再单独计算
            self.test_data.rsei_value = 0.0
            return True
        except Exception as e:
            logger.error(f"通道{self.channel_number}强制更新阻抗失败: {e}")
            return False

    def update_progress(self, progress: int) -> bool:
        """
        更新测试进度

        Args:
            progress: 进度百分比(0-100)

        Returns:
            是否更新成功
        """
        try:
            if 0 <= progress <= 100:
                self.test_data.test_progress = progress
                logger.debug(f"通道{self.channel_number}进度更新: {progress}%")
                return True
            else:
                logger.warning(f"通道{self.channel_number}进度值无效: {progress}%")
                return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新进度失败: {e}")
            return False

    def update_battery_code(self, battery_code: str) -> bool:
        """
        更新电池码

        Args:
            battery_code: 电池码

        Returns:
            是否更新成功
        """
        try:
            self.test_data.battery_code = battery_code
            # 通道电池码更新 - 运行时不输出日志
            pass
            return True
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新电池码失败: {e}")
            return False
    
    def update_all_data(self, voltage: float, rs_value: float, rct_value: float, progress: int) -> bool:
        """
        批量更新所有数据
        
        Args:
            voltage: 电压值(V)
            rs_value: Rs值(mΩ)
            rct_value: Rct值(mΩ)
            progress: 进度百分比(0-100)
            
        Returns:
            是否更新成功
        """
        try:
            success = True
            
            if voltage > 0:
                success &= self.update_voltage(voltage)
            
            if rs_value > 0 or rct_value > 0:
                success &= self.update_impedance(rs_value, rct_value)
            
            if progress >= 0:
                success &= self.update_progress(progress)
            
            return success
        except Exception as e:
            logger.error(f"通道{self.channel_number}批量更新数据失败: {e}")
            return False
    
    def add_frequency_point(self, frequency: float, rs: float, rct: float) -> bool:
        """
        添加频点数据
        
        Args:
            frequency: 频率(Hz)
            rs: Rs值(mΩ)
            rct: Rct值(mΩ)
            
        Returns:
            是否添加成功
        """
        try:
            if frequency > 0 and self.validate_rs(rs) and self.validate_rct(rct):
                self.test_data.frequency_points.append((frequency, rs, rct))
                logger.debug(f"通道{self.channel_number}添加频点: {frequency}Hz, Rs={rs:.3f}mΩ, Rct={rct:.3f}mΩ")
                return True
            else:
                logger.warning(f"通道{self.channel_number}频点数据无效")
                return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}添加频点失败: {e}")
            return False
    
    def set_test_result(self, is_pass: bool, grade: Optional[str], rs_final: float, 
                       rct_final: float, voltage_final: float, test_time: float,
                       error_messages: Optional[List[str]] = None) -> bool:
        """
        设置测试结果
        
        Args:
            is_pass: 是否通过
            grade: 档位等级
            rs_final: 最终Rs值
            rct_final: 最终Rct值
            voltage_final: 最终电压值
            test_time: 测试时间
            error_messages: 错误消息列表
            
        Returns:
            是否设置成功
        """
        try:
            self.test_result.is_pass = is_pass
            self.test_result.grade = grade
            self.test_result.rs_final = rs_final
            self.test_result.rct_final = rct_final
            self.test_result.voltage_final = voltage_final
            self.test_result.test_time = test_time
            
            if error_messages:
                self.test_result.error_messages = error_messages.copy()
            else:
                self.test_result.error_messages.clear()
            
            logger.debug(f"通道{self.channel_number}测试结果设置: {'通过' if is_pass else '失败'}, 档位={grade}")
            return True
        except Exception as e:
            logger.error(f"通道{self.channel_number}设置测试结果失败: {e}")
            return False
    
    def reset_data(self) -> bool:
        """
        重置所有数据
        
        Returns:
            是否重置成功
        """
        try:
            self.test_data = ChannelTestData()
            self.test_result = ChannelTestResult()
            logger.debug(f"通道{self.channel_number}数据已重置")
            return True
        except Exception as e:
            logger.error(f"通道{self.channel_number}重置数据失败: {e}")
            return False
    
    def validate_voltage(self, voltage: float) -> bool:
        """验证电压值是否有效"""
        return self.voltage_range[0] <= voltage <= self.voltage_range[1]
    
    def validate_rs(self, rs_value: float) -> bool:
        """验证Rs值是否有效"""
        return self.rs_range[0] <= rs_value <= self.rs_range[1]
    
    def validate_rct(self, rct_value: float) -> bool:
        """验证Rct值是否有效"""
        return self.rct_range[0] <= rct_value <= self.rct_range[1]

    def validate_rsei(self, rsei_value: float) -> bool:
        """验证Rsei值是否有效"""
        # Rsei值通常在0-100mΩ范围内，允许0值
        return 0.0 <= rsei_value <= 100.0
    
    def get_data_summary(self) -> Dict[str, Any]:
        """
        获取数据摘要
        
        Returns:
            数据摘要字典
        """
        try:
            return {
                'channel_number': self.channel_number,
                'voltage': self.test_data.voltage,
                'rs_value': self.test_data.rs_value,
                'rct_value': self.test_data.rct_value,
                'progress': self.test_data.test_progress,
                'frequency_points_count': len(self.test_data.frequency_points),
                'test_result': {
                    'is_pass': self.test_result.is_pass,
                    'grade': self.test_result.grade,
                    'test_time': self.test_result.test_time,
                    'error_count': len(self.test_result.error_messages)
                }
            }
        except Exception as e:
            logger.error(f"通道{self.channel_number}获取数据摘要失败: {e}")
            return {}
    
    def get_formatted_values(self) -> Dict[str, str]:
        """
        获取格式化的显示值
        
        Returns:
            格式化值字典
        """
        try:
            return {
                'voltage': f"{self.test_data.voltage:.3f}V",
                'rs_value': f"{self.test_data.rs_value:.3f}mΩ",
                'rct_value': f"{self.test_data.rct_value:.3f}mΩ",
                'progress': f"{self.test_data.test_progress}%"
            }
        except Exception as e:
            logger.error(f"通道{self.channel_number}获取格式化值失败: {e}")
            return {
                'voltage': "0.000V",
                'rs_value': "0.000mΩ",
                'rct_value': "0.000mΩ",
                'progress': "0%"
            }
