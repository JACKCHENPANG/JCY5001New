#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JCY5001AS电池阻抗测试系统 - 智能测量超时管理器（增强版）

功能：
1. 根据频点特性动态调整测量超时时间
2. 早期完成检测，避免不必要的等待
3. 自适应超时优化，提升测试效率
4. 异常通道快速跳过机制
5. 接触不良通道检测和处理

作者：Jack
创建时间：2025-01-31
更新时间：2025-06-20
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class FrequencyRange(Enum):
    """频率范围枚举"""
    ULTRA_HIGH = "ultra_high"  # >1000Hz
    HIGH = "high"              # 100-1000Hz
    MEDIUM = "medium"          # 10-100Hz
    LOW = "low"                # 1-10Hz
    ULTRA_LOW = "ultra_low"    # <1Hz

@dataclass
class TimeoutConfig:
    """超时配置（增强版）"""
    base_timeout: float        # 基础超时时间（秒）
    max_timeout: float         # 最大超时时间（秒）
    min_timeout: float         # 最小超时时间（秒）
    stability_check_interval: float  # 稳定性检查间隔（秒）
    stability_threshold: float # 稳定性阈值（相对变化）
    # 新增字段
    exception_timeout: float   # 异常通道超时时间（秒）
    contact_poor_timeout: float # 接触不良通道超时时间（秒）

class SmartTimeoutManager:
    """智能测量超时管理器"""
    
    def __init__(self):
        # 频率范围阈值
        self.frequency_thresholds = {
            FrequencyRange.ULTRA_HIGH: 1000.0,
            FrequencyRange.HIGH: 100.0,
            FrequencyRange.MEDIUM: 10.0,
            FrequencyRange.LOW: 1.0
        }
        
        # 各频率范围的超时配置（增强版，包含异常通道处理）
        self.timeout_configs = {
            FrequencyRange.ULTRA_HIGH: TimeoutConfig(
                base_timeout=5.0, max_timeout=12.0, min_timeout=3.0,
                stability_check_interval=0.5, stability_threshold=0.01,
                exception_timeout=2.0, contact_poor_timeout=3.0  # 新增
            ),
            FrequencyRange.HIGH: TimeoutConfig(
                base_timeout=8.0, max_timeout=18.0, min_timeout=5.0,
                stability_check_interval=0.8, stability_threshold=0.01,
                exception_timeout=3.0, contact_poor_timeout=4.0  # 新增
            ),
            FrequencyRange.MEDIUM: TimeoutConfig(
                base_timeout=12.0, max_timeout=25.0, min_timeout=8.0,
                stability_check_interval=1.0, stability_threshold=0.02,
                exception_timeout=4.0, contact_poor_timeout=6.0  # 新增
            ),
            FrequencyRange.LOW: TimeoutConfig(
                base_timeout=18.0, max_timeout=35.0, min_timeout=12.0,
                stability_check_interval=1.5, stability_threshold=0.02,
                exception_timeout=5.0, contact_poor_timeout=8.0  # 新增
            ),
            FrequencyRange.ULTRA_LOW: TimeoutConfig(
                base_timeout=25.0, max_timeout=45.0, min_timeout=18.0,
                stability_check_interval=2.0, stability_threshold=0.03,
                exception_timeout=6.0, contact_poor_timeout=10.0  # 新增
            )
        }
        
        # 历史性能数据（用于自适应优化）
        self.frequency_performance_history: Dict[float, List[float]] = {}
        self.max_history_size = 10

        # 新增异常通道管理
        self.exception_channels: Set[int] = set()  # 异常通道集合
        self.contact_poor_channels: Set[int] = set()  # 接触不良通道集合
        self.channel_timeout_history: Dict[int, List[float]] = {}  # 通道超时历史

        # 新增快速跳过配置
        self.enable_fast_skip = True  # 是否启用快速跳过
        self.fast_skip_threshold = 3  # 连续异常次数阈值
        self.channel_exception_count: Dict[int, int] = {}  # 通道异常计数

        logger.debug("🎯 智能测量超时管理器（增强版）初始化完成")
    
    def get_frequency_range(self, frequency: float) -> FrequencyRange:
        """获取频率范围"""
        if frequency >= self.frequency_thresholds[FrequencyRange.ULTRA_HIGH]:
            return FrequencyRange.ULTRA_HIGH
        elif frequency >= self.frequency_thresholds[FrequencyRange.HIGH]:
            return FrequencyRange.HIGH
        elif frequency >= self.frequency_thresholds[FrequencyRange.MEDIUM]:
            return FrequencyRange.MEDIUM
        elif frequency >= self.frequency_thresholds[FrequencyRange.LOW]:
            return FrequencyRange.LOW
        else:
            return FrequencyRange.ULTRA_LOW
    
    def get_smart_timeout(self, frequency: float, channel_number: Optional[int] = None) -> Tuple[float, float]:
        """
        获取智能超时配置（增强版，支持异常通道快速跳过）

        Args:
            frequency: 测试频率
            channel_number: 通道号（可选，用于异常通道检测）

        Returns:
            (超时时间, 稳定性检查间隔)
        """
        freq_range = self.get_frequency_range(frequency)
        config = self.timeout_configs[freq_range]

        # 新增检查是否为异常通道
        if channel_number is not None:
            if channel_number in self.exception_channels:
                logger.debug(f"通道{channel_number}为异常通道，使用快速超时: {config.exception_timeout:.1f}s")
                return config.exception_timeout, config.stability_check_interval
            elif channel_number in self.contact_poor_channels:
                logger.debug(f"通道{channel_number}为接触不良通道，使用快速超时: {config.contact_poor_timeout:.1f}s")
                return config.contact_poor_timeout, config.stability_check_interval

        # 基础超时时间
        timeout = config.base_timeout

        # 根据历史性能数据调整
        if frequency in self.frequency_performance_history:
            history = self.frequency_performance_history[frequency]
            if history:
                # 使用历史平均时间 + 安全余量
                avg_time = sum(history) / len(history)
                safety_margin = 1.5  # 50%安全余量
                adaptive_timeout = avg_time * safety_margin

                # 限制在配置范围内
                timeout = max(config.min_timeout,
                            min(config.max_timeout, adaptive_timeout))

                logger.debug(f"频率{frequency}Hz自适应超时: {timeout:.1f}s (历史平均: {avg_time:.1f}s)")

        return timeout, config.stability_check_interval
    
    def record_measurement_time(self, frequency: float, measurement_time: float):
        """
        记录测量时间（用于自适应优化）
        
        Args:
            frequency: 测试频率
            measurement_time: 实际测量时间
        """
        if frequency not in self.frequency_performance_history:
            self.frequency_performance_history[frequency] = []
        
        history = self.frequency_performance_history[frequency]
        history.append(measurement_time)
        
        # 限制历史记录大小
        if len(history) > self.max_history_size:
            history.pop(0)
        
        logger.debug(f"记录频率{frequency}Hz测量时间: {measurement_time:.1f}s")
    
    def check_measurement_stability(self, frequency: float, 
                                  recent_values: List[complex]) -> bool:
        """
        检查测量数据稳定性
        
        Args:
            frequency: 测试频率
            recent_values: 最近的测量值列表
            
        Returns:
            是否达到稳定状态
        """
        if len(recent_values) < 3:
            return False
        
        freq_range = self.get_frequency_range(frequency)
        config = self.timeout_configs[freq_range]
        
        # 计算最近几个值的变化率
        last_values = recent_values[-3:]
        
        # 计算幅值变化率
        magnitudes = [abs(val) for val in last_values]
        if magnitudes[0] == 0:
            return False
        
        max_change = 0
        for i in range(1, len(magnitudes)):
            change_rate = abs(magnitudes[i] - magnitudes[i-1]) / magnitudes[i-1]
            max_change = max(max_change, change_rate)
        
        is_stable = max_change < config.stability_threshold
        
        if is_stable:
            logger.debug(f"频率{frequency}Hz测量稳定 (变化率: {max_change:.3f} < {config.stability_threshold:.3f})")
        
        return is_stable
    
    def get_performance_summary(self) -> Dict:
        """获取性能摘要"""
        summary = {
            'total_frequencies': len(self.frequency_performance_history),
            'frequency_ranges': {},
            'average_times': {},
            'optimization_potential': {}
        }
        
        # 按频率范围统计
        for freq, times in self.frequency_performance_history.items():
            freq_range = self.get_frequency_range(freq)
            range_name = freq_range.value
            
            if range_name not in summary['frequency_ranges']:
                summary['frequency_ranges'][range_name] = {
                    'count': 0,
                    'total_time': 0.0,
                    'frequencies': []
                }
            
            avg_time = sum(times) / len(times)
            summary['frequency_ranges'][range_name]['count'] += 1
            summary['frequency_ranges'][range_name]['total_time'] += avg_time
            summary['frequency_ranges'][range_name]['frequencies'].append(freq)
            summary['average_times'][freq] = avg_time
        
        # 计算优化潜力
        for range_name, data in summary['frequency_ranges'].items():
            if data['count'] > 0:
                avg_time = data['total_time'] / data['count']
                freq_range = FrequencyRange(range_name)
                base_timeout = self.timeout_configs[freq_range].base_timeout
                
                optimization = max(0, base_timeout - avg_time)
                summary['optimization_potential'][range_name] = {
                    'average_time': avg_time,
                    'base_timeout': base_timeout,
                    'time_saved': optimization,
                    'efficiency': (optimization / base_timeout * 100) if base_timeout > 0 else 0
                }
        
        return summary
    
    def optimize_timeouts(self):
        """基于历史数据优化超时配置"""
        optimized_count = 0
        
        for freq_range in FrequencyRange:
            # 收集该频率范围的历史数据
            range_times = []
            for freq, times in self.frequency_performance_history.items():
                if self.get_frequency_range(freq) == freq_range:
                    range_times.extend(times)
            
            if len(range_times) >= 5:  # 至少5个数据点才进行优化
                avg_time = sum(range_times) / len(range_times)
                max_time = max(range_times)
                
                config = self.timeout_configs[freq_range]
                
                # 计算新的基础超时时间
                new_base_timeout = avg_time * 1.3  # 30%安全余量
                new_max_timeout = max_time * 1.5   # 50%安全余量
                
                # 更新配置（在合理范围内）
                if (config.min_timeout <= new_base_timeout <= config.max_timeout * 0.8 and
                    new_max_timeout <= config.max_timeout * 1.2):
                    
                    old_base = config.base_timeout
                    config.base_timeout = new_base_timeout
                    config.max_timeout = min(config.max_timeout, new_max_timeout)
                    
                    optimized_count += 1
                    logger.info(f"优化{freq_range.value}频率范围超时: {old_base:.1f}s → {new_base_timeout:.1f}s")
        
        if optimized_count > 0:
            logger.info(f"✅ 完成超时优化，优化了{optimized_count}个频率范围")
        else:
            pass

    # 新增异常通道管理方法

    def mark_channel_as_exception(self, channel_number: int, reason: str = "异常"):
        """
        标记通道为异常通道

        Args:
            channel_number: 通道号
            reason: 异常原因
        """
        self.exception_channels.add(channel_number)
        self._increment_exception_count(channel_number)
        logger.warning(f"🚨 标记通道{channel_number}为异常通道: {reason}")

    def mark_channel_as_contact_poor(self, channel_number: int, reason: str = "接触不良"):
        """
        标记通道为接触不良通道

        Args:
            channel_number: 通道号
            reason: 接触不良原因
        """
        self.contact_poor_channels.add(channel_number)
        self._increment_exception_count(channel_number)
        logger.warning(f"🔌 标记通道{channel_number}为接触不良通道: {reason}")

    def restore_channel(self, channel_number: int):
        """
        恢复通道为正常状态

        Args:
            channel_number: 通道号
        """
        removed_from_exception = channel_number in self.exception_channels
        removed_from_contact_poor = channel_number in self.contact_poor_channels

        self.exception_channels.discard(channel_number)
        self.contact_poor_channels.discard(channel_number)
        self.channel_exception_count.pop(channel_number, None)

        if removed_from_exception or removed_from_contact_poor:
            logger.info(f"✅ 恢复通道{channel_number}为正常状态")

    def is_channel_exception(self, channel_number: int) -> bool:
        """检查通道是否为异常通道"""
        return channel_number in self.exception_channels

    def is_channel_contact_poor(self, channel_number: int) -> bool:
        """检查通道是否为接触不良通道"""
        return channel_number in self.contact_poor_channels

    def should_fast_skip_channel(self, channel_number: int) -> bool:
        """
        检查通道是否应该快速跳过

        Args:
            channel_number: 通道号

        Returns:
            是否应该快速跳过
        """
        if not self.enable_fast_skip:
            return False

        exception_count = self.channel_exception_count.get(channel_number, 0)
        return exception_count >= self.fast_skip_threshold

    def _increment_exception_count(self, channel_number: int):
        """增加通道异常计数"""
        if channel_number not in self.channel_exception_count:
            self.channel_exception_count[channel_number] = 0
        self.channel_exception_count[channel_number] += 1

    def reset_exception_channels(self):
        """重置所有异常通道状态"""
        exception_count = len(self.exception_channels)
        contact_poor_count = len(self.contact_poor_channels)

        self.exception_channels.clear()
        self.contact_poor_channels.clear()
        self.channel_exception_count.clear()

        if exception_count > 0 or contact_poor_count > 0:
            logger.info(f"🔄 重置异常通道状态: 异常通道{exception_count}个, 接触不良通道{contact_poor_count}个")

    def get_exception_summary(self) -> Dict[str, Any]:
        """
        获取异常通道摘要

        Returns:
            异常通道摘要字典
        """
        return {
            'exception_channels': list(self.exception_channels),
            'contact_poor_channels': list(self.contact_poor_channels),
            'exception_counts': dict(self.channel_exception_count),
            'fast_skip_enabled': self.enable_fast_skip,
            'fast_skip_threshold': self.fast_skip_threshold,
            'total_exception_channels': len(self.exception_channels),
            'total_contact_poor_channels': len(self.contact_poor_channels)
        }

    def configure_fast_skip(self, enabled: bool = True, threshold: int = 3):
        """
        配置快速跳过参数

        Args:
            enabled: 是否启用快速跳过
            threshold: 连续异常次数阈值
        """
        self.enable_fast_skip = enabled
        self.fast_skip_threshold = threshold


    def get_channel_timeout_recommendation(self, channel_number: int, frequency: float) -> float:
        """
        获取通道超时时间建议

        Args:
            channel_number: 通道号
            frequency: 测试频率

        Returns:
            建议的超时时间（秒）
        """
        # 获取基础超时时间
        timeout, _ = self.get_smart_timeout(frequency, channel_number)

        # 根据通道历史表现调整
        if channel_number in self.channel_timeout_history:
            history = self.channel_timeout_history[channel_number]
            if history:
                avg_timeout = sum(history) / len(history)
                # 如果历史超时时间较短，可以适当减少超时时间
                if avg_timeout < timeout * 0.7:
                    timeout = max(timeout * 0.8, avg_timeout * 1.2)
                    logger.debug(f"通道{channel_number}基于历史调整超时: {timeout:.1f}s")

        return timeout
