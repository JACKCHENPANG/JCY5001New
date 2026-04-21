# -*- coding: utf-8 -*-
"""
测试状态管理器
负责管理通道状态、测试状态跟踪、状态变更通知等功能

从TestEngine中提取的状态管理功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Dict, List, Optional, Callable
from enum import Enum
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)


class TestState(Enum):
    """测试状态枚举"""
    IDLE = "idle"
    PREPARING = "preparing"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class ChannelTest:
    """单通道测试类"""
    
    def __init__(self, channel_num: int):
        self.channel_num = channel_num
        self.state = TestState.IDLE
        self.battery_code = ""
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.test_data = {}
        self.error_message = ""
        self.impedance_details = []  # 阻抗明细数据
        self.enabled = True  # 通道是否启用
    
    def reset(self):
        """重置测试状态（保留电池码和启用状态）"""
        self.state = TestState.IDLE
        # 不重置 battery_code 和 enabled，保留已设置的值
        self.start_time = None
        self.end_time = None
        self.test_data = {}
        self.error_message = ""
        self.impedance_details = []
    
    def set_battery_code(self, battery_code: str):
        """设置电池码"""
        self.battery_code = battery_code
        logger.debug(f"通道{self.channel_num}设置电池码: {battery_code}")
    
    def set_enabled(self, enabled: bool):
        """设置通道启用状态"""
        self.enabled = enabled
        logger.debug(f"通道{self.channel_num}设置启用状态: {enabled}")
    
    def start_test(self):
        """开始测试"""
        self.state = TestState.TESTING
        self.start_time = datetime.now()
        self.error_message = ""
        logger.debug(f"通道{self.channel_num}开始测试")
    
    def complete_test(self, test_data: Dict = None):
        """完成测试"""
        self.state = TestState.COMPLETED
        self.end_time = datetime.now()
        if test_data:
            self.test_data = test_data
        logger.debug(f"通道{self.channel_num}测试完成")
    
    def fail_test(self, error_message: str):
        """测试失败"""
        self.state = TestState.FAILED
        self.end_time = datetime.now()
        self.error_message = error_message
        logger.debug(f"通道{self.channel_num}测试失败: {error_message}")
    
    def stop_test(self):
        """停止测试"""
        self.state = TestState.STOPPED
        self.end_time = datetime.now()
        logger.debug(f"通道{self.channel_num}测试停止")


class TestStateManager:
    """
    测试状态管理器
    
    职责：
    - 通道状态管理
    - 测试状态跟踪
    - 状态变更通知
    - 状态验证
    """
    
    def __init__(self, progress_callback=None, status_callback=None):
        """
        初始化测试状态管理器
        
        Args:
            progress_callback: 进度回调函数
            status_callback: 状态回调函数
        """
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        
        # 通道测试对象
        self.channels = {i: ChannelTest(i) for i in range(1, 9)}
        
        # 状态锁，确保线程安全
        self.state_lock = Lock()
        
        # 启用的通道列表
        self.enabled_channels = list(range(1, 9))
        
        logger.debug("测试状态管理器初始化完成")
    
    def get_channel(self, channel_num: int) -> Optional[ChannelTest]:
        """
        获取通道对象
        
        Args:
            channel_num: 通道号 (1-8)
            
        Returns:
            通道对象或None
        """
        if channel_num not in self.channels:
            logger.warning(f"无效的通道号: {channel_num}")
            return None
        return self.channels[channel_num]
    
    def get_channel_state(self, channel_num: int) -> Dict:
        """
        获取通道状态
        
        Args:
            channel_num: 通道号 (1-8)
            
        Returns:
            通道状态字典
        """
        if channel_num not in self.channels:
            return {}
        
        channel = self.channels[channel_num]
        
        with self.state_lock:
            return {
                'channel_num': channel_num,
                'state': channel.state.value,
                'battery_code': channel.battery_code,
                'start_time': channel.start_time,
                'end_time': channel.end_time,
                'error_message': channel.error_message,
                'enabled': channel.enabled,
                'test_duration': self._calculate_test_duration(channel)
            }
    
    def get_all_channel_states(self) -> Dict[int, Dict]:
        """
        获取所有通道状态
        
        Returns:
            所有通道状态字典
        """
        states = {}
        for channel_num in range(1, 9):
            states[channel_num] = self.get_channel_state(channel_num)
        return states
    
    def set_battery_codes(self, battery_codes: List[str]):
        """
        设置电池码列表
        
        Args:
            battery_codes: 电池码列表
        """
        with self.state_lock:
            for i, code in enumerate(battery_codes[:8]):
                if i < 8:
                    channel_num = i + 1
                    self.channels[channel_num].set_battery_code(code)
                    logger.info(f"设置通道{channel_num}电池码: {code}")
    
    def set_channel_battery_code(self, channel_num: int, battery_code: str):
        """
        设置单个通道的电池码
        
        Args:
            channel_num: 通道号 (1-8)
            battery_code: 电池码
        """
        channel = self.get_channel(channel_num)
        if channel:
            with self.state_lock:
                channel.set_battery_code(battery_code)
    
    def update_enabled_channels(self, enabled_channels: List[int]):
        """
        更新启用的通道列表
        
        Args:
            enabled_channels: 启用的通道列表
        """
        try:
            with self.state_lock:
                self.enabled_channels = enabled_channels.copy()
                
                # 更新所有通道的启用状态
                for channel_num in range(1, 9):
                    is_enabled = channel_num in enabled_channels
                    channel = self.channels[channel_num]
                    channel.set_enabled(is_enabled)
                    
                    # 通知UI更新通道使能状态
                    if self.progress_callback:
                        try:
                            self.progress_callback(channel_num, {
                                'state': 'enabled' if is_enabled else 'disabled',
                                'progress': 0,
                                'message': '启用' if is_enabled else '未启用',
                                'enabled': is_enabled
                            })
                        except Exception as e:
                            logger.warning(f"通知通道{channel_num}使能状态失败: {e}")
                
                logger.info(f"通道使能状态更新完成: 启用{len(enabled_channels)}个通道，"
                           f"禁用{8-len(enabled_channels)}个通道")
                
        except Exception as e:
            logger.error(f"更新启用通道列表失败: {e}")
    
    def get_enabled_channels(self) -> List[int]:
        """
        获取启用的通道列表
        
        Returns:
            启用的通道列表
        """
        return self.enabled_channels.copy()
    
    def get_active_channels(self) -> List[ChannelTest]:
        """
        获取活跃通道列表（既有电池码又启用的通道）
        
        Returns:
            活跃通道对象列表
        """
        active_channels = []
        for channel_num in self.enabled_channels:
            channel = self.channels[channel_num]
            if channel.battery_code and channel.enabled:
                active_channels.append(channel)
        return active_channels
    
    def reset_all_channels(self):
        """重置所有通道状态"""
        with self.state_lock:
            for channel in self.channels.values():
                channel.reset()
            logger.info("所有通道状态已重置")
    
    def reset_channel(self, channel_num: int):
        """
        重置单个通道状态
        
        Args:
            channel_num: 通道号 (1-8)
        """
        channel = self.get_channel(channel_num)
        if channel:
            with self.state_lock:
                channel.reset()
                logger.info(f"通道{channel_num}状态已重置")
    
    def start_channel_test(self, channel_num: int):
        """
        开始通道测试
        
        Args:
            channel_num: 通道号 (1-8)
        """
        channel = self.get_channel(channel_num)
        if channel:
            with self.state_lock:
                channel.start_test()
                
            # 通知进度更新
            self._notify_progress(channel_num, {
                'state': 'testing',
                'progress': 0,
                'message': '开始测试'
            })
    
    def complete_channel_test(self, channel_num: int, test_data: Dict = None):
        """
        完成通道测试
        
        Args:
            channel_num: 通道号 (1-8)
            test_data: 测试数据
        """
        channel = self.get_channel(channel_num)
        if channel:
            with self.state_lock:
                channel.complete_test(test_data)
                
            # 通知进度更新
            self._notify_progress(channel_num, {
                'state': 'completed',
                'progress': 100,
                'message': '测试完成'
            })
    
    def fail_channel_test(self, channel_num: int, error_message: str):
        """
        通道测试失败
        
        Args:
            channel_num: 通道号 (1-8)
            error_message: 错误信息
        """
        channel = self.get_channel(channel_num)
        if channel:
            with self.state_lock:
                channel.fail_test(error_message)
                
            # 通知进度更新
            self._notify_progress(channel_num, {
                'state': 'failed',
                'progress': 0,
                'message': f'测试失败: {error_message}'
            })
    
    def stop_all_tests(self):
        """停止所有测试"""
        with self.state_lock:
            for channel in self.channels.values():
                if channel.state == TestState.TESTING:
                    channel.stop_test()
            logger.info("所有测试已停止")
    
    def stop_channel_test(self, channel_num: int):
        """
        停止通道测试
        
        Args:
            channel_num: 通道号 (1-8)
        """
        channel = self.get_channel(channel_num)
        if channel:
            with self.state_lock:
                if channel.state == TestState.TESTING:
                    channel.stop_test()
                    
            # 通知进度更新
            self._notify_progress(channel_num, {
                'state': 'stopped',
                'progress': 0,
                'message': '测试已停止'
            })
    
    def get_testing_channels(self) -> List[int]:
        """
        获取正在测试的通道列表
        
        Returns:
            正在测试的通道号列表
        """
        testing_channels = []
        for channel_num, channel in self.channels.items():
            if channel.state == TestState.TESTING:
                testing_channels.append(channel_num)
        return testing_channels
    
    def get_completed_channels(self) -> List[int]:
        """
        获取已完成测试的通道列表
        
        Returns:
            已完成测试的通道号列表
        """
        completed_channels = []
        for channel_num, channel in self.channels.items():
            if channel.state == TestState.COMPLETED:
                completed_channels.append(channel_num)
        return completed_channels
    
    def get_failed_channels(self) -> List[int]:
        """
        获取测试失败的通道列表
        
        Returns:
            测试失败的通道号列表
        """
        failed_channels = []
        for channel_num, channel in self.channels.items():
            if channel.state == TestState.FAILED:
                failed_channels.append(channel_num)
        return failed_channels
    
    def is_any_channel_testing(self) -> bool:
        """
        检查是否有任何通道正在测试
        
        Returns:
            是否有通道正在测试
        """
        return len(self.get_testing_channels()) > 0
    
    def is_all_channels_completed(self) -> bool:
        """
        检查所有活跃通道是否都已完成测试
        
        Returns:
            是否所有活跃通道都已完成
        """
        active_channels = self.get_active_channels()
        if not active_channels:
            return False
            
        for channel in active_channels:
            if channel.state not in [TestState.COMPLETED, TestState.FAILED, TestState.STOPPED]:
                return False
        return True
    
    def get_test_summary(self) -> Dict:
        """
        获取测试总结
        
        Returns:
            测试总结字典
        """
        active_channels = self.get_active_channels()
        testing_channels = self.get_testing_channels()
        completed_channels = self.get_completed_channels()
        failed_channels = self.get_failed_channels()
        
        return {
            'total_channels': len(active_channels),
            'testing_count': len(testing_channels),
            'completed_count': len(completed_channels),
            'failed_count': len(failed_channels),
            'testing_channels': testing_channels,
            'completed_channels': completed_channels,
            'failed_channels': failed_channels,
            'is_any_testing': self.is_any_channel_testing(),
            'is_all_completed': self.is_all_channels_completed()
        }
    
    def _calculate_test_duration(self, channel: ChannelTest) -> float:
        """
        计算测试持续时间
        
        Args:
            channel: 通道对象
            
        Returns:
            测试持续时间（秒）
        """
        if channel.start_time and channel.end_time:
            return (channel.end_time - channel.start_time).total_seconds()
        elif channel.start_time:
            return (datetime.now() - channel.start_time).total_seconds()
        return 0.0
    
    def _notify_progress(self, channel_num: int, progress_data: Dict):
        """
        通知进度更新
        
        Args:
            channel_num: 通道号
            progress_data: 进度数据
        """
        if self.progress_callback:
            try:
                self.progress_callback(channel_num, progress_data)
            except Exception as e:
                logger.error(f"进度回调失败: {e}")
    
    def _notify_status(self, status_data: Dict):
        """
        通知状态更新
        
        Args:
            status_data: 状态数据
        """
        if self.status_callback:
            try:
                self.status_callback(status_data)
            except Exception as e:
                logger.error(f"状态回调失败: {e}")
    
    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def set_status_callback(self, callback: Callable):
        """设置状态回调函数"""
        self.status_callback = callback