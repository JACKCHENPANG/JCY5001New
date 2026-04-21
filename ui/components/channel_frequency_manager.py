# -*- coding: utf-8 -*-
"""
通道频点管理器
负责单通道的频点信息显示和管理

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Optional
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ChannelFrequencyManager(QObject):
    """通道频点管理器"""
    
    # 信号定义
    frequency_updated = pyqtSignal(int, float, int, int, str)  # channel, frequency, current_index, total_count, status
    
    def __init__(self, channel_number: int):
        """
        初始化频点管理器
        
        Args:
            channel_number: 通道号
        """
        super().__init__()
        self.channel_number = channel_number
        
        # 频点测试数据
        self.current_frequency = 0.0
        self.frequency_index = 0
        self.total_frequencies = 0
        self.frequency_status = "waiting"  # waiting, testing, completed
        
        # 频点更新状态跟踪
        self._last_frequency_update = None
        
    def update_frequency_info(self, frequency: float, current_index: int, total_count: int, status: str = "waiting"):
        """
        更新频点信息
        
        Args:
            frequency: 当前频率 (Hz)
            current_index: 当前频点索引 (从1开始)
            total_count: 总频点数
            status: 频点状态 ("waiting", "testing", "completed")
        """
        try:
            # 状态保持逻辑：避免重复更新相同的频点信息
            current_time = datetime.now()
            
            # 检查是否需要更新
            should_update = self._should_update_frequency(frequency, current_index, total_count, status, current_time)
            
            if should_update:
                # 更新内部状态
                self.current_frequency = frequency
                self.frequency_index = current_index
                self.total_frequencies = total_count
                self.frequency_status = status
                self._last_frequency_update = current_time
                
                # 发送更新信号
                self.frequency_updated.emit(self.channel_number, frequency, current_index, total_count, status)
                
                logger.debug(f"通道{self.channel_number}频点信息已更新: {frequency:.2f}Hz ({current_index}/{total_count}) - {status}")
            else:
                logger.debug(f"通道{self.channel_number}频点信息无需更新: {frequency:.2f}Hz ({current_index}/{total_count}) - {status}")
                
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新频点信息失败: {e}")
    
    def _should_update_frequency(self, frequency: float, current_index: int, total_count: int, status: str, current_time: datetime) -> bool:
        """
        判断是否需要更新频点信息
        
        Args:
            frequency: 频率
            current_index: 当前索引
            total_count: 总数
            status: 状态
            current_time: 当前时间
            
        Returns:
            bool: 是否需要更新
        """
        try:
            # 如果是第一次更新，直接更新
            if self._last_frequency_update is None:
                return True
            
            # 如果频率、索引或状态发生变化，需要更新
            if (frequency != self.current_frequency or 
                current_index != self.frequency_index or 
                status != self.frequency_status or
                total_count != self.total_frequencies):
                return True
            
            # 如果距离上次更新超过1秒，允许更新（防止卡住）
            time_diff = (current_time - self._last_frequency_update).total_seconds()
            if time_diff > 1.0:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"判断频点更新条件失败: {e}")
            return True  # 出错时允许更新
    
    def force_update_frequency_info(self, frequency: float, current_index: int, total_count: int, status: str = "waiting"):
        """
        强制更新频点信息（绕过状态保持逻辑）
        
        Args:
            frequency: 当前频率 (Hz)
            current_index: 当前频点索引 (从1开始)
            total_count: 总频点数
            status: 频点状态
        """
        try:
            # 直接更新内部状态
            self.current_frequency = frequency
            self.frequency_index = current_index
            self.total_frequencies = total_count
            self.frequency_status = status
            self._last_frequency_update = datetime.now()
            
            # 发送更新信号
            self.frequency_updated.emit(self.channel_number, frequency, current_index, total_count, status)
            
            logger.debug(f"通道{self.channel_number}频点信息强制更新: {frequency:.2f}Hz ({current_index}/{total_count}) - {status}")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}强制更新频点信息失败: {e}")
    
    def update_frequency_progress_only(self, current_index: int, total_count: int, status: str = "waiting"):
        """
        仅更新频点进度显示
        
        Args:
            current_index: 当前频点索引
            total_count: 总频点数
            status: 频点状态
        """
        try:
            # 保持当前频率不变，只更新进度
            self.frequency_index = current_index
            self.total_frequencies = total_count
            self.frequency_status = status
            self._last_frequency_update = datetime.now()
            
            # 发送更新信号
            self.frequency_updated.emit(self.channel_number, self.current_frequency, current_index, total_count, status)
            
            logger.debug(f"通道{self.channel_number}频点进度已更新: ({current_index}/{total_count}) - {status}")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新频点进度失败: {e}")
    
    def clear_frequency_info(self):
        """清空频点信息显示"""
        try:
            logger.debug(f"通道{self.channel_number}开始清空频点信息...")
            
            # 重置所有频点相关数据
            self.current_frequency = 0.0
            self.frequency_index = 0
            self.total_frequencies = 0
            self.frequency_status = "waiting"
            self._last_frequency_update = None
            
            # 发送清空信号
            self.frequency_updated.emit(self.channel_number, 0.0, 0, 0, "waiting")
            
            logger.debug(f"通道{self.channel_number}频点信息已清空")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}清空频点信息失败: {e}")
    
    def get_current_frequency_info(self) -> dict:
        """
        获取当前频点信息
        
        Returns:
            dict: 频点信息字典
        """
        return {
            'frequency': self.current_frequency,
            'index': self.frequency_index,
            'total': self.total_frequencies,
            'status': self.frequency_status,
            'last_update': self._last_frequency_update
        }
    
    def is_frequency_testing(self) -> bool:
        """
        判断是否正在进行频点测试
        
        Returns:
            bool: 是否正在测试
        """
        return self.frequency_status == "testing"
    
    def is_frequency_completed(self) -> bool:
        """
        判断频点测试是否完成
        
        Returns:
            bool: 是否完成
        """
        return self.frequency_status == "completed"
    
    def get_frequency_progress_percentage(self) -> float:
        """
        获取频点测试进度百分比
        
        Returns:
            float: 进度百分比 (0-100)
        """
        try:
            if self.total_frequencies <= 0:
                return 0.0
            
            progress = (self.frequency_index / self.total_frequencies) * 100
            return min(100.0, max(0.0, progress))
            
        except Exception as e:
            logger.error(f"计算频点进度百分比失败: {e}")
            return 0.0
    
    def format_frequency_display(self) -> str:
        """
        格式化频点显示文本
        
        Returns:
            str: 格式化的频点显示文本
        """
        try:
            if self.current_frequency <= 0:
                return "频点: --"
            
            # 根据频率大小选择合适的单位
            if self.current_frequency >= 1000:
                return f"频点: {self.current_frequency/1000:.2f}kHz"
            else:
                return f"频点: {self.current_frequency:.2f}Hz"
                
        except Exception as e:
            logger.error(f"格式化频点显示失败: {e}")
            return "频点: --"
    
    def format_progress_display(self) -> str:
        """
        格式化进度显示文本
        
        Returns:
            str: 格式化的进度显示文本
        """
        try:
            if self.total_frequencies <= 0:
                return "进度: --"
            
            return f"进度: {self.frequency_index}/{self.total_frequencies}"
            
        except Exception as e:
            logger.error(f"格式化进度显示失败: {e}")
            return "进度: --"
