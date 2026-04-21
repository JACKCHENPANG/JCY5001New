# -*- coding: utf-8 -*-
"""
频率分类器
从ParallelStaggeredTestManager中提取的频率分类相关功能

职责：
- 频率点分类
- 高低频点划分
- 频率索引查找
- 频率分配计算

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class FrequencyClassifier:
    """
    频率分类器
    
    职责：
    - 根据临界频点分类频率
    - 计算频率分配策略
    - 提供频率索引查找功能
    """
    
    def __init__(self):
        """初始化频率分类器"""
        self.high_frequencies: List[float] = []  # 高频点（>临界频点）
        self.low_frequencies: List[float] = []   # 低频点（≤临界频点）
        self.all_frequencies: List[float] = []   # 所有频率列表
        self.critical_frequency: float = 0.0     # 临界频点
        
        logger.debug("频率分类器初始化完成")
    
    def _remove_duplicate_frequencies(self, frequencies: List[float]) -> List[float]:
        """
        去除重复的频率点

        Args:
            frequencies: 原始频率列表

        Returns:
            去重后的频率列表（保持原有顺序）
        """
        try:
            if not frequencies:
                return []

            # 使用有序集合去重，保持原有顺序
            seen = set()
            unique_frequencies = []

            for freq in frequencies:
                if freq not in seen:
                    seen.add(freq)
                    unique_frequencies.append(freq)

            removed_count = len(frequencies) - len(unique_frequencies)
            if removed_count > 0:
                logger.info(f"频率分类器去重: 原始{len(frequencies)}个频点，去重后{len(unique_frequencies)}个频点，移除{removed_count}个重复频点")

            return unique_frequencies

        except Exception as e:
            logger.error(f"频率去重失败: {e}")
            return frequencies

    def classify_frequencies(self, frequencies: List[float], critical_frequency: float) -> Tuple[List[float], List[float]]:
        """
        根据临界频点分类频率（自动去重）

        Args:
            frequencies: 频率列表
            critical_frequency: 临界频点

        Returns:
            (高频点列表, 低频点列表)
        """
        try:
            # 先去重处理
            deduplicated_frequencies = self._remove_duplicate_frequencies(frequencies)

            self.all_frequencies = deduplicated_frequencies.copy()
            self.critical_frequency = critical_frequency
            self.high_frequencies.clear()
            self.low_frequencies.clear()

            logger.debug(f"开始频率分类: 临界频率={critical_frequency}Hz, 总频率数={len(deduplicated_frequencies)}")

            for i, frequency in enumerate(deduplicated_frequencies):
                try:
                    if frequency > critical_frequency:
                        self.high_frequencies.append(frequency)
                    else:
                        self.low_frequencies.append(frequency)
                except Exception as e:
                    logger.error(f"频率分类异常: 频率{frequency}, 错误{e}")

            logger.info(f"频率分类完成: 高频点{len(self.high_frequencies)}个, 低频点{len(self.low_frequencies)}个")
            logger.debug(f"高频点: {self.high_frequencies[:3]}{'...' if len(self.high_frequencies) > 3 else ''}")
            logger.debug(f"低频点: {self.low_frequencies[:3]}{'...' if len(self.low_frequencies) > 3 else ''}")

            return self.high_frequencies.copy(), self.low_frequencies.copy()

        except Exception as e:
            logger.error(f"频率分类失败: {e}")
            return [], []
    
    def calculate_frequency_assignments(self, enabled_channels: List[int], round_index: int) -> Dict[int, float]:
        """
        计算频点分配
        
        Args:
            enabled_channels: 启用的通道索引列表
            round_index: 轮次索引
            
        Returns:
            通道频点分配字典 {channel_index: frequency}
        """
        try:
            assignments = {}
            num_frequencies = len(self.high_frequencies)
            
            if num_frequencies == 0:
                logger.warning("没有高频点可分配")
                return assignments
            
            for i, channel_index in enumerate(enabled_channels):
                # 循环分配频点，每轮偏移round_index
                freq_index = (i + round_index) % num_frequencies
                frequency = self.high_frequencies[freq_index]
                assignments[channel_index] = frequency
            
            logger.debug(f"第{round_index + 1}轮频点分配: {assignments}")
            return assignments
            
        except Exception as e:
            logger.error(f"计算频点分配失败: {e}")
            return {}
    
    def find_frequency_index(self, frequency: float) -> int:
        """
        查找频率在总频率列表中的索引
        
        Args:
            frequency: 要查找的频率
            
        Returns:
            频率索引（从1开始），如果未找到返回1
        """
        try:
            if not self.all_frequencies:
                return 1

            # 精确匹配
            for i, freq in enumerate(self.all_frequencies):
                if abs(freq - frequency) < 0.001:  # 处理浮点精度问题
                    return i + 1  # 返回从1开始的索引

            # 如果没有精确匹配，返回最接近的索引
            closest_index = 0
            min_diff = float('inf')
            for i, freq in enumerate(self.all_frequencies):
                diff = abs(freq - frequency)
                if diff < min_diff:
                    min_diff = diff
                    closest_index = i

            logger.debug(f"频率{frequency}Hz未精确匹配，使用最接近的索引{closest_index + 1}")
            return closest_index + 1

        except Exception as e:
            logger.error(f"查找频率索引失败: {e}")
            return 1
    
    def get_high_frequencies(self) -> List[float]:
        """获取高频点列表"""
        return self.high_frequencies.copy()
    
    def get_low_frequencies(self) -> List[float]:
        """获取低频点列表"""
        return self.low_frequencies.copy()
    
    def get_all_frequencies(self) -> List[float]:
        """获取所有频率列表"""
        return self.all_frequencies.copy()
    
    def get_critical_frequency(self) -> float:
        """获取临界频点"""
        return self.critical_frequency
    
    def get_classification_info(self) -> Dict[str, any]:
        """
        获取分类信息
        
        Returns:
            分类信息字典
        """
        return {
            'total_frequencies': len(self.all_frequencies),
            'high_frequencies_count': len(self.high_frequencies),
            'low_frequencies_count': len(self.low_frequencies),
            'critical_frequency': self.critical_frequency,
            'high_frequencies': self.high_frequencies.copy(),
            'low_frequencies': self.low_frequencies.copy()
        }
    
    def is_high_frequency(self, frequency: float) -> bool:
        """
        判断是否为高频点
        
        Args:
            frequency: 频率值
            
        Returns:
            是否为高频点
        """
        return frequency > self.critical_frequency
    
    def is_low_frequency(self, frequency: float) -> bool:
        """
        判断是否为低频点
        
        Args:
            frequency: 频率值
            
        Returns:
            是否为低频点
        """
        return frequency <= self.critical_frequency
    
    def get_frequency_type(self, frequency: float) -> str:
        """
        获取频率类型
        
        Args:
            frequency: 频率值
            
        Returns:
            频率类型 ('high' 或 'low')
        """
        return 'high' if self.is_high_frequency(frequency) else 'low'
    
    def calculate_rounds_needed(self, enabled_channels: List[int]) -> int:
        """
        计算需要的测试轮次
        
        Args:
            enabled_channels: 启用的通道列表
            
        Returns:
            需要的轮次数
        """
        try:
            num_channels = len(enabled_channels)
            num_high_frequencies = len(self.high_frequencies)
            
            if num_high_frequencies == 0:
                return 0
            
            # 对于错频测试，需要的轮次等于高频点数量
            return num_high_frequencies
            
        except Exception as e:
            logger.error(f"计算测试轮次失败: {e}")
            return 0
    
    def validate_frequencies(self, frequencies: List[float]) -> bool:
        """
        验证频率列表的有效性
        
        Args:
            frequencies: 频率列表
            
        Returns:
            是否有效
        """
        try:
            if not frequencies:
                logger.error("频率列表为空")
                return False
            
            # 检查频率是否为正数
            for freq in frequencies:
                if not isinstance(freq, (int, float)) or freq <= 0:
                    logger.error(f"无效频率: {freq}")
                    return False
            
            # 检查是否有重复频率
            unique_count = len(set(frequencies))
            if len(frequencies) != unique_count:
                duplicate_count = len(frequencies) - unique_count
                logger.warning(f"频率列表包含{duplicate_count}个重复值，建议使用去重功能")
            
            return True
            
        except Exception as e:
            logger.error(f"验证频率列表失败: {e}")
            return False
    
    def reset(self):
        """重置分类器状态"""
        self.high_frequencies.clear()
        self.low_frequencies.clear()
        self.all_frequencies.clear()
        self.critical_frequency = 0.0
        logger.debug("频率分类器已重置")