#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备状态码管理器
负责设备状态码的解析、处理和异常检测

Author: Jack
Date: 2025-01-30
"""

import logging
from enum import Enum
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class DeviceStatusCode(Enum):
    """设备状态码枚举"""
    IDLE = 0x0000           # 空闲
    MEASURING = 0x0001      # ZM测量中
    BALANCING = 0x0002      # 平衡功能运行中
    BATTERY_ERROR = 0x0003  # 电池电压低或电池未安装
    SETTING_ERROR = 0x0004  # 设置错误
    HARDWARE_ERROR = 0x0005 # 硬件错误/ADC错误
    COMPLETED = 0x0006      # 测量完成


class ChannelStatusSeverity(Enum):
    """通道状态严重程度"""
    NORMAL = "正常"          # 正常状态
    WARNING = "警告"         # 警告状态
    ERROR = "错误"           # 错误状态
    CRITICAL = "严重"        # 严重错误


@dataclass
class ChannelStatusInfo:
    """通道状态信息"""
    channel_index: int
    status_code: int
    status_enum: DeviceStatusCode
    description: str
    severity: ChannelStatusSeverity
    should_skip: bool
    can_test: bool
    error_message: Optional[str] = None


class DeviceStatusManager:
    """设备状态码管理器"""
    
    def __init__(self):
        """初始化状态码管理器"""
        self.status_descriptions = self._init_status_descriptions()
        self.severity_mapping = self._init_severity_mapping()
        self.skip_conditions = self._init_skip_conditions()
        
        logger.debug("设备状态码管理器初始化完成")
    
    def _init_status_descriptions(self) -> Dict[DeviceStatusCode, str]:
        """初始化状态码描述映射"""
        return {
            DeviceStatusCode.IDLE: "空闲",
            DeviceStatusCode.MEASURING: "测量中",
            DeviceStatusCode.BALANCING: "平衡运行中",
            DeviceStatusCode.BATTERY_ERROR: "电池电压低或未安装",
            DeviceStatusCode.SETTING_ERROR: "设置错误",
            DeviceStatusCode.HARDWARE_ERROR: "硬件错误/ADC错误",
            DeviceStatusCode.COMPLETED: "测量完成"
        }
    
    def _init_severity_mapping(self) -> Dict[DeviceStatusCode, ChannelStatusSeverity]:
        """初始化状态严重程度映射"""
        return {
            DeviceStatusCode.IDLE: ChannelStatusSeverity.NORMAL,
            DeviceStatusCode.MEASURING: ChannelStatusSeverity.NORMAL,
            DeviceStatusCode.BALANCING: ChannelStatusSeverity.WARNING,
            DeviceStatusCode.BATTERY_ERROR: ChannelStatusSeverity.ERROR,
            DeviceStatusCode.SETTING_ERROR: ChannelStatusSeverity.ERROR,
            DeviceStatusCode.HARDWARE_ERROR: ChannelStatusSeverity.CRITICAL,
            DeviceStatusCode.COMPLETED: ChannelStatusSeverity.NORMAL
        }
    
    def _init_skip_conditions(self) -> Dict[DeviceStatusCode, bool]:
        """初始化跳过条件映射"""
        return {
            DeviceStatusCode.IDLE: False,
            DeviceStatusCode.MEASURING: False,
            DeviceStatusCode.BALANCING: True,   # 平衡运行中时跳过
            DeviceStatusCode.BATTERY_ERROR: True,  # 电池异常时跳过
            DeviceStatusCode.SETTING_ERROR: True,  # 设置错误时跳过
            DeviceStatusCode.HARDWARE_ERROR: True, # 硬件错误时跳过
            DeviceStatusCode.COMPLETED: False
        }
    
    def parse_status_code(self, status_code: int) -> DeviceStatusCode:
        """
        解析状态码
        
        Args:
            status_code: 原始状态码
            
        Returns:
            状态码枚举
        """
        try:
            return DeviceStatusCode(status_code)
        except ValueError:
            logger.warning(f"未知状态码: 0x{status_code:04X}")
            return DeviceStatusCode.IDLE  # 默认返回空闲状态
    
    def get_channel_status_info(self, channel_index: int, status_code: int) -> ChannelStatusInfo:
        """
        获取通道状态信息
        
        Args:
            channel_index: 通道索引（0-7）
            status_code: 状态码
            
        Returns:
            通道状态信息
        """
        try:
            status_enum = self.parse_status_code(status_code)
            description = self.status_descriptions.get(status_enum, "未知状态")
            severity = self.severity_mapping.get(status_enum, ChannelStatusSeverity.WARNING)
            should_skip = self.skip_conditions.get(status_enum, False)
            can_test = not should_skip and status_enum in [
                DeviceStatusCode.IDLE, 
                DeviceStatusCode.COMPLETED
            ]
            
            # 生成错误消息
            error_message = None
            if should_skip:
                error_message = f"通道{channel_index + 1}: {description}"
            
            return ChannelStatusInfo(
                channel_index=channel_index,
                status_code=status_code,
                status_enum=status_enum,
                description=description,
                severity=severity,
                should_skip=should_skip,
                can_test=can_test,
                error_message=error_message
            )
            
        except Exception as e:
            logger.error(f"解析通道{channel_index + 1}状态失败: {e}")
            return ChannelStatusInfo(
                channel_index=channel_index,
                status_code=status_code,
                status_enum=DeviceStatusCode.IDLE,
                description="解析失败",
                severity=ChannelStatusSeverity.ERROR,
                should_skip=True,
                can_test=False,
                error_message=f"通道{channel_index + 1}: 状态解析失败"
            )
    
    def check_channels_status(self, status_codes: List[int]) -> Dict[int, ChannelStatusInfo]:
        """
        检查多个通道的状态
        
        Args:
            status_codes: 状态码列表
            
        Returns:
            通道状态信息字典 {channel_index: ChannelStatusInfo}
        """
        try:
            channel_status = {}
            
            for channel_index, status_code in enumerate(status_codes):
                status_info = self.get_channel_status_info(channel_index, status_code)
                channel_status[channel_index] = status_info
                
                # 记录异常状态
                if status_info.should_skip:
                    logger.warning(f"⚠️ {status_info.error_message}")
                elif status_info.severity == ChannelStatusSeverity.CRITICAL:
                    logger.error(f"❌ 通道{channel_index + 1}: {status_info.description}")
            
            return channel_status
            
        except Exception as e:
            logger.error(f"检查通道状态失败: {e}")
            return {}
    
    def get_available_channels(self, status_codes: List[int]) -> List[int]:
        """
        获取可用于测试的通道列表
        
        Args:
            status_codes: 状态码列表
            
        Returns:
            可用通道索引列表
        """
        try:
            available_channels = []
            channel_status = self.check_channels_status(status_codes)
            
            for channel_index, status_info in channel_status.items():
                if status_info.can_test:
                    available_channels.append(channel_index)
            
            logger.info(f"可用测试通道: {[ch + 1 for ch in available_channels]}")
            return available_channels
            
        except Exception as e:
            logger.error(f"获取可用通道失败: {e}")
            return []
    
    def get_error_channels(self, status_codes: List[int]) -> List[Tuple[int, str]]:
        """
        获取异常通道列表
        
        Args:
            status_codes: 状态码列表
            
        Returns:
            异常通道列表 [(channel_index, error_message), ...]
        """
        try:
            error_channels = []
            channel_status = self.check_channels_status(status_codes)
            
            for channel_index, status_info in channel_status.items():
                if status_info.should_skip and status_info.error_message:
                    error_channels.append((channel_index, status_info.error_message))
            
            return error_channels
            
        except Exception as e:
            logger.error(f"获取异常通道失败: {e}")
            return []
    
    def is_battery_error(self, status_code: int) -> bool:
        """
        检查是否为电池异常（0003H）
        
        Args:
            status_code: 状态码
            
        Returns:
            是否为电池异常
        """
        return self.parse_status_code(status_code) == DeviceStatusCode.BATTERY_ERROR
    
    def is_hardware_error(self, status_code: int) -> bool:
        """
        检查是否为硬件异常（0005H）
        
        Args:
            status_code: 状态码
            
        Returns:
            是否为硬件异常
        """
        return self.parse_status_code(status_code) == DeviceStatusCode.HARDWARE_ERROR
    
    def get_status_summary(self, status_codes: List[int]) -> Dict[str, int]:
        """
        获取状态统计摘要
        
        Args:
            status_codes: 状态码列表
            
        Returns:
            状态统计字典
        """
        try:
            summary = {
                "total_channels": len(status_codes),
                "available_channels": 0,
                "error_channels": 0,
                "battery_errors": 0,
                "hardware_errors": 0,
                "setting_errors": 0
            }
            
            channel_status = self.check_channels_status(status_codes)
            
            for status_info in channel_status.values():
                if status_info.can_test:
                    summary["available_channels"] += 1
                if status_info.should_skip:
                    summary["error_channels"] += 1
                
                # 统计具体错误类型
                if status_info.status_enum == DeviceStatusCode.BATTERY_ERROR:
                    summary["battery_errors"] += 1
                elif status_info.status_enum == DeviceStatusCode.HARDWARE_ERROR:
                    summary["hardware_errors"] += 1
                elif status_info.status_enum == DeviceStatusCode.SETTING_ERROR:
                    summary["setting_errors"] += 1
            
            return summary
            
        except Exception as e:
            logger.error(f"获取状态摘要失败: {e}")
            return {"total_channels": len(status_codes), "available_channels": 0, "error_channels": 0}
