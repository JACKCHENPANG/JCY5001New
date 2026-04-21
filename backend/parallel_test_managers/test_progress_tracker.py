# -*- coding: utf-8 -*-
"""
测试进度跟踪器
从ParallelStaggeredTestManager中提取的进度跟踪相关功能

职责：
- 测试进度计算
- 进度状态管理
- 进度回调处理
- 时间估算

Author: Jack
Date: 2025-01-30
"""

import logging
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TestProgressTracker:
    """
    测试进度跟踪器
    
    职责：
    - 跟踪测试进度
    - 计算完成百分比
    - 估算剩余时间
    - 管理进度回调
    """
    
    def __init__(self):
        """初始化测试进度跟踪器"""
        self.total_frequencies = 0
        self.completed_frequencies = 0
        self.current_frequency_index = 0
        
        self.start_time: Optional[float] = None
        self.last_update_time: Optional[float] = None
        
        # 进度回调
        self.progress_callback: Optional[Callable] = None
        
        # 通道进度状态
        self.channel_progress: Dict[int, Dict[str, Any]] = {}
        
        logger.debug("测试进度跟踪器初始化完成")
    
    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def initialize_test(self, total_frequencies: int, enabled_channels: List[int]):
        """
        初始化测试进度跟踪
        
        Args:
            total_frequencies: 总频率数
            enabled_channels: 启用的通道列表
        """
        try:
            self.total_frequencies = total_frequencies
            self.completed_frequencies = 0
            self.current_frequency_index = 0
            
            self.start_time = time.time()
            self.last_update_time = self.start_time
            
            # 初始化通道进度
            self.channel_progress.clear()
            for channel_index in enabled_channels:
                channel_num = channel_index + 1
                self.channel_progress[channel_num] = {
                    'state': 'ready',
                    'progress': 0,
                    'current_frequency': None,
                    'frequency_index': 0,
                    'message': '准备测试',
                    'last_update': time.time()
                }
            
            logger.info(f"测试进度跟踪初始化: {total_frequencies}个频点, {len(enabled_channels)}个通道")
            
        except Exception as e:
            logger.error(f"初始化测试进度跟踪失败: {e}")
    
    def update_frequency_progress(self, frequency_index: int, frequency: float):
        """
        更新频率进度
        
        Args:
            frequency_index: 频率索引
            frequency: 当前频率
        """
        try:
            self.current_frequency_index = frequency_index
            self.last_update_time = time.time()
            
            # 计算总体进度
            overall_progress = int((frequency_index / self.total_frequencies) * 100)
            
            logger.debug(f"更新频率进度: {frequency_index}/{self.total_frequencies} ({overall_progress}%) - {frequency}Hz")
            
        except Exception as e:
            logger.error(f"更新频率进度失败: {e}")
    
    def update_channel_progress(self, channel_num: int, progress_data: Dict[str, Any]):
        """
        更新通道进度
        
        Args:
            channel_num: 通道号 (1-8)
            progress_data: 进度数据
        """
        try:
            if channel_num not in self.channel_progress:
                self.channel_progress[channel_num] = {}
            
            # 更新通道进度数据
            self.channel_progress[channel_num].update(progress_data)
            self.channel_progress[channel_num]['last_update'] = time.time()
            
            # 调用进度回调
            if self.progress_callback:
                try:
                    self.progress_callback(channel_num, progress_data)
                except Exception as e:
                    logger.error(f"进度回调失败: {e}")
            
            logger.debug(f"更新通道{channel_num}进度: {progress_data.get('state', 'unknown')} - {progress_data.get('progress', 0)}%")
            
        except Exception as e:
            logger.error(f"更新通道{channel_num}进度失败: {e}")
    
    def mark_frequency_completed(self, frequency: float):
        """
        标记频率完成
        
        Args:
            frequency: 完成的频率
        """
        try:
            self.completed_frequencies += 1
            self.last_update_time = time.time()
            
            completion_percentage = (self.completed_frequencies / self.total_frequencies) * 100
            
            logger.info(f"频率{frequency}Hz完成 ({self.completed_frequencies}/{self.total_frequencies}, {completion_percentage:.1f}%)")
            
        except Exception as e:
            logger.error(f"标记频率完成失败: {e}")
    
    def get_overall_progress(self) -> Dict[str, Any]:
        """
        获取总体进度信息
        
        Returns:
            总体进度字典
        """
        try:
            if self.total_frequencies == 0:
                return {
                    'progress_percentage': 0,
                    'completed_frequencies': 0,
                    'total_frequencies': 0,
                    'current_frequency_index': 0,
                    'elapsed_time': 0,
                    'estimated_remaining_time': 0,
                    'estimated_total_time': 0
                }
            
            # 计算进度百分比
            progress_percentage = (self.completed_frequencies / self.total_frequencies) * 100
            
            # 计算时间信息
            current_time = time.time()
            elapsed_time = current_time - self.start_time if self.start_time else 0
            
            # 估算剩余时间
            if self.completed_frequencies > 0:
                avg_time_per_frequency = elapsed_time / self.completed_frequencies
                remaining_frequencies = self.total_frequencies - self.completed_frequencies
                estimated_remaining_time = avg_time_per_frequency * remaining_frequencies
                estimated_total_time = elapsed_time + estimated_remaining_time
            else:
                estimated_remaining_time = 0
                estimated_total_time = 0
            
            return {
                'progress_percentage': round(progress_percentage, 1),
                'completed_frequencies': self.completed_frequencies,
                'total_frequencies': self.total_frequencies,
                'current_frequency_index': self.current_frequency_index,
                'elapsed_time': round(elapsed_time, 1),
                'estimated_remaining_time': round(estimated_remaining_time, 1),
                'estimated_total_time': round(estimated_total_time, 1)
            }
            
        except Exception as e:
            logger.error(f"获取总体进度失败: {e}")
            return {}
    
    def get_channel_progress(self, channel_num: int) -> Optional[Dict[str, Any]]:
        """
        获取指定通道的进度信息
        
        Args:
            channel_num: 通道号
            
        Returns:
            通道进度字典
        """
        try:
            if channel_num in self.channel_progress:
                return self.channel_progress[channel_num].copy()
            else:
                return None
                
        except Exception as e:
            logger.error(f"获取通道{channel_num}进度失败: {e}")
            return None
    
    def get_all_channels_progress(self) -> Dict[int, Dict[str, Any]]:
        """
        获取所有通道的进度信息
        
        Returns:
            所有通道进度字典
        """
        try:
            return {ch: data.copy() for ch, data in self.channel_progress.items()}
            
        except Exception as e:
            logger.error(f"获取所有通道进度失败: {e}")
            return {}
    
    def calculate_eta(self) -> Optional[datetime]:
        """
        计算预计完成时间 (ETA)
        
        Returns:
            预计完成时间
        """
        try:
            overall_progress = self.get_overall_progress()
            remaining_time = overall_progress.get('estimated_remaining_time', 0)
            
            if remaining_time > 0:
                eta = datetime.now() + timedelta(seconds=remaining_time)
                return eta
            else:
                return None
                
        except Exception as e:
            logger.error(f"计算ETA失败: {e}")
            return None
    
    def format_time_duration(self, seconds: float) -> str:
        """
        格式化时间持续时间
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时间字符串
        """
        try:
            if seconds < 60:
                return f"{seconds:.1f}秒"
            elif seconds < 3600:
                minutes = seconds / 60
                return f"{minutes:.1f}分钟"
            else:
                hours = seconds / 3600
                return f"{hours:.1f}小时"
                
        except Exception as e:
            logger.error(f"格式化时间失败: {e}")
            return "未知"
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """
        获取进度摘要
        
        Returns:
            进度摘要字典
        """
        try:
            overall = self.get_overall_progress()
            eta = self.calculate_eta()
            
            # 统计通道状态
            channel_states = {}
            for channel_num, progress in self.channel_progress.items():
                state = progress.get('state', 'unknown')
                if state not in channel_states:
                    channel_states[state] = 0
                channel_states[state] += 1
            
            summary = {
                'overall_progress': overall,
                'channel_states': channel_states,
                'total_channels': len(self.channel_progress),
                'eta': eta.isoformat() if eta else None,
                'eta_formatted': eta.strftime('%H:%M:%S') if eta else None,
                'elapsed_time_formatted': self.format_time_duration(overall.get('elapsed_time', 0)),
                'remaining_time_formatted': self.format_time_duration(overall.get('estimated_remaining_time', 0))
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"获取进度摘要失败: {e}")
            return {}
    
    def is_test_completed(self) -> bool:
        """
        检查测试是否完成
        
        Returns:
            是否完成
        """
        try:
            return self.completed_frequencies >= self.total_frequencies
            
        except Exception as e:
            logger.error(f"检查测试完成状态失败: {e}")
            return False
    
    def reset(self):
        """重置进度跟踪器"""
        try:
            self.total_frequencies = 0
            self.completed_frequencies = 0
            self.current_frequency_index = 0
            
            self.start_time = None
            self.last_update_time = None
            
            self.channel_progress.clear()
            
            logger.debug("测试进度跟踪器已重置")
            
        except Exception as e:
            logger.error(f"重置进度跟踪器失败: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标
        
        Returns:
            性能指标字典
        """
        try:
            overall = self.get_overall_progress()
            elapsed_time = overall.get('elapsed_time', 0)
            completed_frequencies = overall.get('completed_frequencies', 0)
            
            metrics = {
                'average_time_per_frequency': elapsed_time / completed_frequencies if completed_frequencies > 0 else 0,
                'frequencies_per_minute': (completed_frequencies / elapsed_time) * 60 if elapsed_time > 0 else 0,
                'test_efficiency': (completed_frequencies / self.total_frequencies) * 100 if self.total_frequencies > 0 else 0,
                'active_channels': len([ch for ch, data in self.channel_progress.items() if data.get('state') in ['testing', 'ready']]),
                'error_channels': len([ch for ch, data in self.channel_progress.items() if data.get('state') == 'error'])
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"获取性能指标失败: {e}")
            return {}