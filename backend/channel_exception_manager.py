#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通道异常检测和跳过管理器
负责检测通道异常状态并实现跳过机制

Author: Jack
Date: 2025-06-11
"""

import logging
from typing import Dict, List, Set, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ChannelExceptionType(Enum):
    """通道异常类型（增强版）"""
    NONE = "none"                    # 无异常
    BATTERY_ERROR = "battery_error"  # 电池异常 (0x0003H)
    HARDWARE_ERROR = "hardware_error" # 硬件异常 (0x0005H)
    SETTING_ERROR = "setting_error"  # 设置错误 (0x0004H)
    BALANCING = "balancing"          # 平衡运行中 (0x0002H)
    CONTACT_POOR = "contact_poor"    # 新增接触不良
    RESPONSE_TIMEOUT = "response_timeout"  # 新增响应超时
    UNKNOWN_STATUS = "unknown_status" # 未知状态码


@dataclass
class ChannelExceptionInfo:
    """通道异常信息（增强版）"""
    channel_number: int
    exception_type: ChannelExceptionType
    status_code: int
    error_message: str
    detection_time: datetime
    frequency_when_detected: Optional[float] = None
    should_skip: bool = True
    # 新增字段
    voltage_when_detected: Optional[float] = None  # 检测时的电压值
    response_time: Optional[float] = None  # 响应时间（毫秒）
    retry_count: int = 0  # 重试次数


class ChannelExceptionManager:
    """通道异常检测和跳过管理器"""
    
    def __init__(self, status_callback: Optional[Callable] = None):
        """
        初始化通道异常管理器
        
        Args:
            status_callback: 状态回调函数
        """
        self.status_callback = status_callback
        
        # 异常通道记录
        self.exception_channels: Dict[int, ChannelExceptionInfo] = {}
        
        # 跳过的通道集合（当前测试周期）
        self.skipped_channels: Set[int] = set()
        
        # 正常状态码定义
        self.normal_status_codes = {0x0001, 0x0006}  # 测试中、测试完成
        
        # 异常状态码映射
        self.exception_status_mapping = {
            0x0003: ChannelExceptionType.BATTERY_ERROR,
            0x0004: ChannelExceptionType.SETTING_ERROR,
            0x0005: ChannelExceptionType.HARDWARE_ERROR,
            0x0002: ChannelExceptionType.BALANCING
        }
        
        # 异常描述映射（增强版）
        self.exception_descriptions = {
            ChannelExceptionType.BATTERY_ERROR: "电池电压低或未安装",
            ChannelExceptionType.HARDWARE_ERROR: "硬件错误/ADC错误",
            ChannelExceptionType.SETTING_ERROR: "设置错误",
            ChannelExceptionType.BALANCING: "平衡功能运行中",
            ChannelExceptionType.CONTACT_POOR: "接触不良",  # 新增
            ChannelExceptionType.RESPONSE_TIMEOUT: "响应超时",  # 新增
            ChannelExceptionType.UNKNOWN_STATUS: "未知状态码"
        }

        # 新增接触不良检测配置
        self.contact_poor_detection_enabled = True
        self.response_timeout_threshold = 5.0  # 响应超时阈值（秒）
        self.max_retry_count = 2  # 最大重试次数

        # 新增电压历史记录（用于检测电压波动）
        self._voltage_history: Dict[int, List[float]] = {}
        self._max_voltage_history = 10  # 最多保存10个历史电压值

        logger.debug("通道异常管理器初始化完成")
    
    def reset_for_new_test(self):
        """重置异常状态，开始新测试"""
        self.exception_channels.clear()
        self.skipped_channels.clear()
        # 保留电压历史记录，用于跨测试周期的接触不良检测
        logger.info("通道异常状态已重置，开始新测试")

    def reset_all_channels(self):
        """重置所有通道状态（完全重置）"""
        try:
            # 清除所有异常状态
            self.exception_channels.clear()
            self.skipped_channels.clear()

            # 清除电压历史记录
            if hasattr(self, '_voltage_history'):
                self._voltage_history.clear()

            # 重置统计信息（如果存在）
            if hasattr(self, 'exception_stats'):
                self.exception_stats = {
                    'total_exceptions': 0,
                    'by_type': {},
                    'by_channel': {}
                }

            logger.info("所有通道异常状态已完全重置")

        except Exception as e:
            logger.error(f"重置所有通道状态失败: {e}")

    def get_exception_channels(self) -> Dict[int, ChannelExceptionInfo]:
        """获取异常通道信息"""
        return self.exception_channels.copy()

    def get_skipped_channels(self) -> Set[int]:
        """获取跳过的通道集合"""
        return self.skipped_channels.copy()

    def clear_all_data(self):
        """清除所有数据（包括电压历史）"""
        self.exception_channels.clear()
        self.skipped_channels.clear()
        self._voltage_history.clear()
        logger.info("通道异常管理器所有数据已清除")
    
    def check_channel_status(self, channel_number: int, status_code: int,
                           current_frequency: Optional[float] = None,
                           voltage: Optional[float] = None,
                           response_time: Optional[float] = None) -> bool:
        """
        增强版通道状态检查（支持接触不良检测）

        Args:
            channel_number: 通道号 (1-8)
            status_code: 状态码
            current_frequency: 当前测试频率
            voltage: 当前电压值
            response_time: 响应时间（毫秒）

        Returns:
            True表示通道正常，False表示通道异常需要跳过
        """
        try:
            # 如果通道已经被标记为异常，直接返回False
            if channel_number in self.skipped_channels:
                return False

            # 检查状态码是否正常
            if status_code in self.normal_status_codes:
                # 即使状态码正常，也要检查是否有接触不良迹象
                if self.contact_poor_detection_enabled:
                    contact_poor_result = self._detect_contact_poor(
                        channel_number, status_code, voltage, response_time, current_frequency
                    )
                    if contact_poor_result['is_contact_poor']:
                        self._mark_channel_as_contact_poor(
                            channel_number, contact_poor_result['reason'],
                            voltage, response_time, current_frequency
                        )
                        return False
                return True

            # 检测到异常状态码
            exception_type = self.exception_status_mapping.get(
                status_code, ChannelExceptionType.UNKNOWN_STATUS
            )

            error_message = self.exception_descriptions.get(
                exception_type, f"未知状态码: 0x{status_code:04X}"
            )

            # 创建异常信息
            exception_info = ChannelExceptionInfo(
                channel_number=channel_number,
                exception_type=exception_type,
                status_code=status_code,
                error_message=error_message,
                detection_time=datetime.now(),
                frequency_when_detected=current_frequency,
                voltage_when_detected=voltage,
                response_time=response_time,
                should_skip=True
            )

            # 记录异常通道
            self.exception_channels[channel_number] = exception_info
            self.skipped_channels.add(channel_number)

            # 记录日志
            logger.warning(f"🚨 检测到通道{channel_number}异常: {error_message} (0x{status_code:04X})")
            if current_frequency:
                logger.warning(f"   异常检测频率: {current_frequency}Hz")
            if voltage:
                logger.warning(f"   检测时电压: {voltage:.3f}V")

            # 通知UI更新
            self._notify_channel_exception(exception_info)

            return False

        except Exception as e:
            logger.error(f"检查通道{channel_number}状态失败: {e}")
            return True  # 出错时默认认为正常，避免误跳过
    
    def is_channel_skipped(self, channel_number: int) -> bool:
        """
        检查通道是否被跳过
        
        Args:
            channel_number: 通道号 (1-8)
            
        Returns:
            是否被跳过
        """
        return channel_number in self.skipped_channels
    
    def get_exception_info(self, channel_number: int) -> Optional[ChannelExceptionInfo]:
        """
        获取通道异常信息
        
        Args:
            channel_number: 通道号 (1-8)
            
        Returns:
            异常信息或None
        """
        return self.exception_channels.get(channel_number)
    
    def get_normal_channels(self, enabled_channels: List[int]) -> List[int]:
        """
        获取正常的通道列表（排除异常通道）
        
        Args:
            enabled_channels: 启用的通道列表
            
        Returns:
            正常的通道列表
        """
        return [ch for ch in enabled_channels if ch not in self.skipped_channels]
    
    def get_skipped_channels(self) -> List[int]:
        """获取被跳过的通道列表"""
        return list(self.skipped_channels)
    
    def get_exception_summary(self) -> Dict:
        """
        获取异常总结
        
        Returns:
            异常总结字典
        """
        summary = {
            'total_exceptions': len(self.exception_channels),
            'skipped_channels': list(self.skipped_channels),
            'exception_details': {}
        }
        
        for channel_num, info in self.exception_channels.items():
            summary['exception_details'][channel_num] = {
                'exception_type': info.exception_type.value,
                'status_code': f"0x{info.status_code:04X}",
                'error_message': info.error_message,
                'detection_time': info.detection_time.strftime('%H:%M:%S'),
                'frequency': info.frequency_when_detected
            }
        
        return summary

    def _detect_contact_poor(self, channel_number: int, status_code: int,
                           voltage: Optional[float], response_time: Optional[float],
                           current_frequency: Optional[float]) -> Dict[str, Any]:
        """
        检测接触不良迹象

        Args:
            channel_number: 通道号
            status_code: 状态码
            voltage: 电压值
            response_time: 响应时间
            current_frequency: 当前频率

        Returns:
            检测结果：{'is_contact_poor': bool, 'reason': str}
        """
        try:
            reasons = []

            # 1. 响应时间检测
            if response_time and response_time > self.response_timeout_threshold * 1000:  # 转换为毫秒
                reasons.append(f"响应超时({response_time:.0f}ms)")

            # 2. 电压异常波动检测（如果有历史数据）
            if voltage and hasattr(self, '_voltage_history'):
                if channel_number in self._voltage_history:
                    voltage_history = self._voltage_history[channel_number]
                    if len(voltage_history) > 3:
                        avg_voltage = sum(voltage_history[-3:]) / 3
                        voltage_deviation = abs(voltage - avg_voltage)
                        if voltage_deviation > 0.5:  # 电压偏差超过0.5V
                            reasons.append(f"电压波动异常({voltage_deviation:.2f}V)")

            # 3. 状态码异常模式检测
            if status_code == 0x0001:  # 测试中状态持续时间过长
                # 这里可以添加更复杂的逻辑，比如检查状态持续时间
                pass

            # 4. 频率相关的接触问题检测
            if current_frequency and current_frequency > 1000:  # 高频时更容易出现接触问题
                if response_time and response_time > 2000:  # 高频时响应时间超过2秒
                    reasons.append(f"高频响应异常({current_frequency}Hz)")

            if reasons:
                return {
                    'is_contact_poor': True,
                    'reason': '; '.join(reasons)
                }
            else:
                return {
                    'is_contact_poor': False,
                    'reason': '正常'
                }

        except Exception as e:
            logger.error(f"接触不良检测失败: {e}")
            return {
                'is_contact_poor': False,
                'reason': f'检测异常: {str(e)}'
            }

    def _mark_channel_as_contact_poor(self, channel_number: int, reason: str,
                                    voltage: Optional[float] = None,
                                    response_time: Optional[float] = None,
                                    current_frequency: Optional[float] = None):
        """
        标记通道为接触不良

        Args:
            channel_number: 通道号
            reason: 接触不良原因
            voltage: 电压值
            response_time: 响应时间
            current_frequency: 当前频率
        """
        try:
            # 创建接触不良异常信息
            exception_info = ChannelExceptionInfo(
                channel_number=channel_number,
                exception_type=ChannelExceptionType.CONTACT_POOR,
                status_code=0x0004,  # 使用设置错误状态码表示接触不良
                error_message=f"接触不良: {reason}",
                detection_time=datetime.now(),
                frequency_when_detected=current_frequency,
                voltage_when_detected=voltage,
                response_time=response_time,
                should_skip=True
            )

            # 记录异常通道
            self.exception_channels[channel_number] = exception_info
            self.skipped_channels.add(channel_number)

            # 记录日志
            logger.warning(f"🔌 检测到通道{channel_number}接触不良: {reason}")
            if voltage:
                logger.warning(f"   检测时电压: {voltage:.3f}V")
            if response_time:
                logger.warning(f"   响应时间: {response_time:.0f}ms")

            # 通知UI更新
            self._notify_channel_exception(exception_info)

        except Exception as e:
            logger.error(f"标记通道{channel_number}接触不良失败: {e}")

    def _notify_channel_exception(self, exception_info: ChannelExceptionInfo):
        """
        通知通道异常
        
        Args:
            exception_info: 异常信息
        """
        if self.status_callback:
            try:
                self.status_callback({
                    'action': 'channel_exception_detected',
                    'channel_number': exception_info.channel_number,
                    'exception_type': exception_info.exception_type.value,
                    'status_code': exception_info.status_code,
                    'error_message': exception_info.error_message,
                    'should_skip': exception_info.should_skip,
                    'detection_time': exception_info.detection_time.isoformat()
                })
            except Exception as e:
                logger.error(f"通道异常状态回调失败: {e}")

    def record_voltage(self, channel_number: int, voltage: float):
        """
        记录通道电压历史（用于接触不良检测）

        Args:
            channel_number: 通道号
            voltage: 电压值
        """
        try:
            if channel_number not in self._voltage_history:
                self._voltage_history[channel_number] = []

            voltage_history = self._voltage_history[channel_number]
            voltage_history.append(voltage)

            # 保持历史记录数量限制
            if len(voltage_history) > self._max_voltage_history:
                voltage_history.pop(0)

        except Exception as e:
            logger.error(f"记录通道{channel_number}电压历史失败: {e}")

    def configure_contact_poor_detection(self, enabled: bool = True,
                                       timeout_threshold: float = 5.0,
                                       max_retry: int = 2):
        """
        配置接触不良检测参数

        Args:
            enabled: 是否启用接触不良检测
            timeout_threshold: 响应超时阈值（秒）
            max_retry: 最大重试次数
        """
        self.contact_poor_detection_enabled = enabled
        self.response_timeout_threshold = timeout_threshold
        self.max_retry_count = max_retry


    def get_detection_statistics(self) -> Dict[str, Any]:
        """
        获取检测统计信息

        Returns:
            统计信息字典
        """
        stats = {
            'total_exceptions': len(self.exception_channels),
            'skipped_channels': list(self.skipped_channels),
            'exception_types': {},
            'voltage_history_channels': list(self._voltage_history.keys()),
            'contact_poor_detection_enabled': self.contact_poor_detection_enabled
        }

        # 统计异常类型分布
        for info in self.exception_channels.values():
            exception_type = info.exception_type.value
            if exception_type not in stats['exception_types']:
                stats['exception_types'][exception_type] = 0
            stats['exception_types'][exception_type] += 1

        return stats

    def force_skip_channel(self, channel_number: int, reason: str = "手动跳过"):
        """
        强制跳过指定通道

        Args:
            channel_number: 通道号
            reason: 跳过原因
        """
        try:
            exception_info = ChannelExceptionInfo(
                channel_number=channel_number,
                exception_type=ChannelExceptionType.SETTING_ERROR,
                status_code=0x0004,
                error_message=f"手动跳过: {reason}",
                detection_time=datetime.now(),
                should_skip=True
            )

            self.exception_channels[channel_number] = exception_info
            self.skipped_channels.add(channel_number)

            logger.info(f"🚫 手动跳过通道{channel_number}: {reason}")

            # 通知UI更新
            self._notify_channel_exception(exception_info)

        except Exception as e:
            logger.error(f"强制跳过通道{channel_number}失败: {e}")

    def restore_channel(self, channel_number: int):
        """
        恢复被跳过的通道

        Args:
            channel_number: 通道号
        """
        try:
            if channel_number in self.skipped_channels:
                self.skipped_channels.remove(channel_number)

            if channel_number in self.exception_channels:
                del self.exception_channels[channel_number]

            logger.info(f"✅ 恢复通道{channel_number}")

        except Exception as e:
            logger.error(f"恢复通道{channel_number}失败: {e}")
