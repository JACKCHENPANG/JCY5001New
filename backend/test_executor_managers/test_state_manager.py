# -*- coding: utf-8 -*-
"""
测试状态管理器
负责测试状态跟踪、进度监控、状态变更通知等功能

Author: Jack
Date: 2025-06-27
"""

import logging
import time
import threading
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class TestState(Enum):
    """测试状态枚举"""
    IDLE = "idle"                    # 空闲
    PREPARING = "preparing"          # 准备中
    RUNNING = "running"              # 运行中
    PAUSED = "paused"               # 暂停
    STOPPING = "stopping"           # 停止中
    COMPLETED = "completed"          # 完成
    FAILED = "failed"               # 失败
    CANCELLED = "cancelled"          # 取消


class TestStateManager(QObject):
    """测试状态管理器"""
    
    # 信号定义
    state_changed = pyqtSignal(str, str)  # 状态变更信号 (old_state, new_state)
    progress_updated = pyqtSignal(dict)  # 进度更新信号 (progress_info)
    channel_state_changed = pyqtSignal(int, str)  # 通道状态变更信号 (channel, state)
    
    def __init__(self, parent=None):
        """
        初始化测试状态管理器
        
        Args:
            parent: 父对象
        """
        super().__init__(parent)
        
        # 全局测试状态
        self.current_state = TestState.IDLE
        self.previous_state = TestState.IDLE
        
        # 通道状态
        self.channel_states = {}  # {channel_num: state}
        self.channel_progress = {}  # {channel_num: progress_info}
        
        # 测试进度
        self.overall_progress = 0.0
        self.test_start_time = None
        self.test_end_time = None
        
        # 状态锁
        self._state_lock = threading.Lock()
        
        # 状态回调
        self.state_callbacks = []
        
    def set_state(self, new_state: TestState, reason: str = ""):
        """
        设置测试状态
        
        Args:
            new_state: 新状态
            reason: 状态变更原因
        """
        try:
            with self._state_lock:
                old_state = self.current_state
                
                if old_state == new_state:
                    logger.debug(f"状态未变更: {new_state.value}")
                    return
                
                # 验证状态转换是否合法
                if not self._is_valid_state_transition(old_state, new_state):
                    logger.warning(f"无效的状态转换: {old_state.value} -> {new_state.value}")
                    return
                
                # 更新状态
                self.previous_state = old_state
                self.current_state = new_state
                
                # 记录时间戳
                if new_state == TestState.RUNNING and not self.test_start_time:
                    self.test_start_time = time.time()
                elif new_state in [TestState.COMPLETED, TestState.FAILED, TestState.CANCELLED]:
                    self.test_end_time = time.time()
                
                logger.info(f"🔄 测试状态变更: {old_state.value} -> {new_state.value} ({reason})")
                
                # 发送状态变更信号
                self.state_changed.emit(old_state.value, new_state.value)
                
                # 调用状态回调
                self._notify_state_callbacks(old_state, new_state, reason)
                
        except Exception as e:
            logger.error(f"设置测试状态失败: {e}")

    def get_state(self) -> TestState:
        """获取当前测试状态"""
        return self.current_state

    def get_state_info(self) -> Dict[str, Any]:
        """
        获取状态信息
        
        Returns:
            状态信息字典
        """
        try:
            with self._state_lock:
                duration = 0.0
                if self.test_start_time:
                    end_time = self.test_end_time or time.time()
                    duration = end_time - self.test_start_time
                
                return {
                    'current_state': self.current_state.value,
                    'previous_state': self.previous_state.value,
                    'overall_progress': self.overall_progress,
                    'test_duration': duration,
                    'start_time': self.test_start_time,
                    'end_time': self.test_end_time,
                    'channel_count': len(self.channel_states),
                    'active_channels': [ch for ch, state in self.channel_states.items() if state == 'running'],
                    'timestamp': time.time()
                }
                
        except Exception as e:
            logger.error(f"获取状态信息失败: {e}")
            return {}

    def set_channel_state(self, channel_num: int, state: str, progress_info: Optional[Dict[str, Any]] = None):
        """
        设置通道状态
        
        Args:
            channel_num: 通道号
            state: 通道状态
            progress_info: 进度信息
        """
        try:
            old_state = self.channel_states.get(channel_num, 'idle')
            
            if old_state != state:
                self.channel_states[channel_num] = state
                logger.debug(f"通道{channel_num}状态变更: {old_state} -> {state}")
                
                # 发送通道状态变更信号
                self.channel_state_changed.emit(channel_num, state)
            
            # 更新通道进度
            if progress_info:
                self.channel_progress[channel_num] = progress_info
                self._update_overall_progress()
                
        except Exception as e:
            logger.error(f"设置通道{channel_num}状态失败: {e}")

    def get_channel_state(self, channel_num: int) -> str:
        """获取通道状态"""
        return self.channel_states.get(channel_num, 'idle')

    def get_channel_progress(self, channel_num: int) -> Dict[str, Any]:
        """获取通道进度"""
        return self.channel_progress.get(channel_num, {})

    def update_progress(self, progress_info: Dict[str, Any]):
        """
        更新测试进度
        
        Args:
            progress_info: 进度信息
        """
        try:
            # 更新整体进度
            if 'overall_progress' in progress_info:
                self.overall_progress = progress_info['overall_progress']
            
            # 更新通道进度
            if 'channel_progress' in progress_info:
                for channel_num, channel_info in progress_info['channel_progress'].items():
                    self.channel_progress[channel_num] = channel_info
            
            # 发送进度更新信号
            self.progress_updated.emit(progress_info)
            
            logger.debug(f"测试进度更新: {self.overall_progress:.1f}%")
            
        except Exception as e:
            logger.error(f"更新测试进度失败: {e}")

    def _update_overall_progress(self):
        """更新整体进度"""
        try:
            if not self.channel_progress:
                self.overall_progress = 0.0
                return
            
            # 计算所有通道的平均进度
            total_progress = 0.0
            channel_count = len(self.channel_progress)
            
            for channel_info in self.channel_progress.values():
                channel_progress = channel_info.get('test_progress', 0)
                total_progress += channel_progress
            
            self.overall_progress = total_progress / channel_count if channel_count > 0 else 0.0
            
        except Exception as e:
            logger.error(f"更新整体进度失败: {e}")

    def _is_valid_state_transition(self, old_state: TestState, new_state: TestState) -> bool:
        """
        验证状态转换是否合法
        
        Args:
            old_state: 旧状态
            new_state: 新状态
            
        Returns:
            是否合法
        """
        # 定义合法的状态转换
        valid_transitions = {
            TestState.IDLE: [TestState.PREPARING],
            TestState.PREPARING: [TestState.RUNNING, TestState.FAILED, TestState.CANCELLED],
            TestState.RUNNING: [TestState.PAUSED, TestState.STOPPING, TestState.COMPLETED, TestState.FAILED],
            TestState.PAUSED: [TestState.RUNNING, TestState.STOPPING, TestState.CANCELLED],
            TestState.STOPPING: [TestState.COMPLETED, TestState.FAILED, TestState.CANCELLED],
            TestState.COMPLETED: [TestState.IDLE],
            TestState.FAILED: [TestState.IDLE],
            TestState.CANCELLED: [TestState.IDLE]
        }
        
        allowed_states = valid_transitions.get(old_state, [])
        return new_state in allowed_states

    def _notify_state_callbacks(self, old_state: TestState, new_state: TestState, reason: str):
        """通知状态回调"""
        try:
            for callback in self.state_callbacks:
                try:
                    callback(old_state, new_state, reason)
                except Exception as e:
                    logger.error(f"状态回调执行失败: {e}")
        except Exception as e:
            logger.error(f"通知状态回调失败: {e}")

    def add_state_callback(self, callback: Callable):
        """添加状态回调"""
        if callback not in self.state_callbacks:
            self.state_callbacks.append(callback)
            logger.debug("状态回调已添加")

    def remove_state_callback(self, callback: Callable):
        """移除状态回调"""
        if callback in self.state_callbacks:
            self.state_callbacks.remove(callback)
            logger.debug("状态回调已移除")

    def reset_state(self):
        """重置状态"""
        try:
            with self._state_lock:
                logger.info("🔄 重置测试状态")
                
                # 重置全局状态
                old_state = self.current_state
                self.current_state = TestState.IDLE
                self.previous_state = TestState.IDLE
                
                # 重置进度
                self.overall_progress = 0.0
                self.test_start_time = None
                self.test_end_time = None
                
                # 重置通道状态
                self.channel_states.clear()
                self.channel_progress.clear()
                
                # 发送状态变更信号
                if old_state != TestState.IDLE:
                    self.state_changed.emit(old_state.value, TestState.IDLE.value)
                
                logger.info("✅ 测试状态重置完成")
                
        except Exception as e:
            logger.error(f"重置测试状态失败: {e}")

    def is_testing(self) -> bool:
        """检查是否正在测试"""
        return self.current_state in [TestState.PREPARING, TestState.RUNNING, TestState.PAUSED]

    def is_idle(self) -> bool:
        """检查是否空闲"""
        return self.current_state == TestState.IDLE

    def is_completed(self) -> bool:
        """检查是否完成"""
        return self.current_state == TestState.COMPLETED

    def is_failed(self) -> bool:
        """检查是否失败"""
        return self.current_state == TestState.FAILED

    def get_test_duration(self) -> float:
        """获取测试持续时间"""
        try:
            if not self.test_start_time:
                return 0.0
            
            end_time = self.test_end_time or time.time()
            return end_time - self.test_start_time
            
        except Exception as e:
            logger.error(f"获取测试持续时间失败: {e}")
            return 0.0

    def get_channel_summary(self) -> Dict[str, Any]:
        """获取通道状态摘要"""
        try:
            summary = {
                'total_channels': len(self.channel_states),
                'running_channels': 0,
                'completed_channels': 0,
                'failed_channels': 0,
                'idle_channels': 0
            }
            
            for state in self.channel_states.values():
                if state == 'running':
                    summary['running_channels'] += 1
                elif state == 'completed':
                    summary['completed_channels'] += 1
                elif state == 'failed':
                    summary['failed_channels'] += 1
                else:
                    summary['idle_channels'] += 1
            
            return summary
            
        except Exception as e:
            logger.error(f"获取通道状态摘要失败: {e}")
            return {}

    def cleanup(self):
        """清理资源"""
        try:
            # 重置状态
            self.reset_state()
            
            # 清除回调
            self.state_callbacks.clear()
            
            logger.debug("测试状态管理器资源已清理")
            
        except Exception as e:
            logger.error(f"清理测试状态管理器资源失败: {e}")
