#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通道状态管理器
负责管理通道的各种状态，包括测试状态、使能状态、错误状态等

Author: Jack
Date: 2025-01-30
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class TestState(Enum):
    """测试状态枚举"""
    IDLE = "idle"                    # 空闲
    TESTING = "testing"              # 测试中
    COMPLETED = "completed"          # 测试完成
    FAILED = "failed"                # 测试失败
    DISABLED = "disabled"            # 未启用
    CHANNEL_ERROR = "channel_error"  # 通道异常
    BATTERY_ERROR = "battery_error"  # 电池异常
    HARDWARE_ERROR = "hardware_error" # 硬件异常
    SKIPPED = "skipped"              # 跳过测试


class EnableState(Enum):
    """使能状态枚举"""
    ENABLED = "enabled"              # 启用
    DISABLED = "disabled"            # 禁用


@dataclass
class StateChangeEvent:
    """状态变化事件"""
    channel_number: int
    old_state: TestState
    new_state: TestState
    timestamp: float
    reason: Optional[str] = None


class ChannelStateManager:
    """通道状态管理器"""
    
    def __init__(self, channel_number: int):
        """
        初始化状态管理器
        
        Args:
            channel_number: 通道号（1-8）
        """
        self.channel_number = channel_number
        self.channel_index = channel_number - 1
        
        # 当前状态
        self._test_state = TestState.IDLE
        self._enable_state = EnableState.DISABLED
        self._is_testing = False
        
        # 状态历史
        self.state_history = []
        
        # 状态变化回调
        self.state_change_callbacks = []
        
        # 错误信息
        self.error_message = None
        self.status_code = None
        
        logger.debug(f"通道{self.channel_number}状态管理器初始化完成")
    
    @property
    def test_state(self) -> TestState:
        """获取测试状态"""
        return self._test_state
    
    @property
    def is_enabled(self) -> bool:
        """获取是否启用"""
        return self._enable_state == EnableState.ENABLED
    
    @property
    def is_testing(self) -> bool:
        """获取是否正在测试"""
        return self._is_testing
    
    @property
    def is_idle(self) -> bool:
        """获取是否空闲"""
        return self._test_state == TestState.IDLE
    
    @property
    def is_completed(self) -> bool:
        """获取是否完成"""
        return self._test_state == TestState.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """获取是否失败"""
        return self._test_state == TestState.FAILED
    
    @property
    def has_error(self) -> bool:
        """获取是否有错误"""
        return self._test_state in [
            TestState.CHANNEL_ERROR,
            TestState.BATTERY_ERROR,
            TestState.HARDWARE_ERROR
        ]
    
    @property
    def is_skipped(self) -> bool:
        """获取是否跳过"""
        return self._test_state == TestState.SKIPPED
    
    def set_test_state(self, new_state: TestState, reason: Optional[str] = None) -> bool:
        """
        设置测试状态
        
        Args:
            new_state: 新状态
            reason: 状态变化原因
            
        Returns:
            是否设置成功
        """
        try:
            old_state = self._test_state
            
            # 静默跳过相同状态转换（避免重复日志）
            if old_state == new_state:
                return True
            
            # 验证状态转换是否合法
            if self._validate_state_transition(old_state, new_state):
                self._test_state = new_state
                
                # 更新测试标志
                self._update_testing_flag()
                
                # 记录状态变化
                self._record_state_change(old_state, new_state, reason)
                
                # 触发回调
                self._notify_state_change(old_state, new_state, reason)
                
                logger.debug(f"通道{self.channel_number}状态变化: {old_state.value} -> {new_state.value}")
                return True
            else:
                logger.warning(f"通道{self.channel_number}状态转换无效: {old_state.value} -> {new_state.value}")
                return False
                
        except Exception as e:
            logger.error(f"通道{self.channel_number}设置测试状态失败: {e}")
            return False
    
    def set_enable_state(self, enabled: bool) -> bool:
        """
        设置使能状态
        
        Args:
            enabled: 是否启用
            
        Returns:
            是否设置成功
        """
        try:
            old_enable_state = self._enable_state
            self._enable_state = EnableState.ENABLED if enabled else EnableState.DISABLED
            
            # 如果禁用通道，需要重置测试状态
            if not enabled and self._test_state != TestState.DISABLED:
                self.set_test_state(TestState.DISABLED, "通道被禁用")
            elif enabled and self._test_state == TestState.DISABLED:
                self.set_test_state(TestState.IDLE, "通道被启用")
            
            logger.debug(f"通道{self.channel_number}使能状态变化: {old_enable_state.value} -> {self._enable_state.value}")
            return True
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}设置使能状态失败: {e}")
            return False
    
    def set_testing_state(self, is_testing: bool) -> bool:
        """
        设置测试中标志
        
        Args:
            is_testing: 是否正在测试
            
        Returns:
            是否设置成功
        """
        try:
            self._is_testing = is_testing
            
            # 根据测试标志更新状态
            if is_testing and self._test_state == TestState.IDLE:
                self.set_test_state(TestState.TESTING, "开始测试")
            elif not is_testing and self._test_state == TestState.TESTING:
                # 测试结束，但不自动设置为完成状态，由外部决定
                pass
            
            logger.debug(f"通道{self.channel_number}测试标志设置: {is_testing}")
            return True
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}设置测试标志失败: {e}")
            return False
    
    def set_error_state(self, status_code: int, error_message: str) -> bool:
        """
        设置错误状态
        
        Args:
            status_code: 状态码
            error_message: 错误消息
            
        Returns:
            是否设置成功
        """
        try:
            self.status_code = status_code
            self.error_message = error_message
            
            # 根据状态码设置对应的错误状态
            if status_code == 0x0003:  # 电池电压低或未安装
                error_state = TestState.BATTERY_ERROR
            elif status_code == 0x0005:  # 硬件错误/ADC错误
                error_state = TestState.HARDWARE_ERROR
            elif status_code == 0x0004:  # 设置错误
                error_state = TestState.CHANNEL_ERROR
            elif status_code == 0x0002:  # 平衡功能运行中
                error_state = TestState.SKIPPED
            else:
                error_state = TestState.CHANNEL_ERROR
            
            return self.set_test_state(error_state, f"状态码异常: 0x{status_code:04X}")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}设置错误状态失败: {e}")
            return False
    
    def clear_error_state(self) -> bool:
        """
        清除错误状态
        
        Returns:
            是否清除成功
        """
        try:
            self.status_code = None
            self.error_message = None
            
            # 恢复到正常状态
            if self.has_error or self.is_skipped:
                if self.is_enabled:
                    return self.set_test_state(TestState.IDLE, "错误状态已清除")
                else:
                    return self.set_test_state(TestState.DISABLED, "错误状态已清除")
            
            return True
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}清除错误状态失败: {e}")
            return False
    
    def reset_state(self) -> bool:
        """
        重置所有状态
        
        Returns:
            是否重置成功
        """
        try:
            # 重置状态
            if self.is_enabled:
                self.set_test_state(TestState.IDLE, "状态重置")
            else:
                self.set_test_state(TestState.DISABLED, "状态重置")
            
            self._is_testing = False
            
            # 清除错误信息
            self.status_code = None
            self.error_message = None
            
            # 清空状态历史
            self.state_history.clear()
            
            logger.debug(f"通道{self.channel_number}状态已重置")
            return True
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}重置状态失败: {e}")
            return False
    
    def add_state_change_callback(self, callback: Callable[[StateChangeEvent], None]) -> bool:
        """
        添加状态变化回调
        
        Args:
            callback: 回调函数
            
        Returns:
            是否添加成功
        """
        try:
            if callback not in self.state_change_callbacks:
                self.state_change_callbacks.append(callback)
                logger.debug(f"通道{self.channel_number}添加状态变化回调")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}添加状态变化回调失败: {e}")
            return False
    
    def remove_state_change_callback(self, callback: Callable[[StateChangeEvent], None]) -> bool:
        """
        移除状态变化回调
        
        Args:
            callback: 回调函数
            
        Returns:
            是否移除成功
        """
        try:
            if callback in self.state_change_callbacks:
                self.state_change_callbacks.remove(callback)
                logger.debug(f"通道{self.channel_number}移除状态变化回调")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}移除状态变化回调失败: {e}")
            return False
    
    def _validate_state_transition(self, old_state: TestState, new_state: TestState) -> bool:
        """验证状态转换是否合法"""
        # 定义合法的状态转换
        valid_transitions = {
            TestState.IDLE: [TestState.TESTING, TestState.DISABLED, TestState.CHANNEL_ERROR, 
                           TestState.BATTERY_ERROR, TestState.HARDWARE_ERROR, TestState.SKIPPED],
            TestState.TESTING: [TestState.COMPLETED, TestState.FAILED, TestState.IDLE,
                              TestState.CHANNEL_ERROR, TestState.BATTERY_ERROR, TestState.HARDWARE_ERROR],
            TestState.COMPLETED: [TestState.IDLE, TestState.TESTING],
            TestState.FAILED: [TestState.IDLE, TestState.TESTING],
            TestState.DISABLED: [TestState.IDLE],
            TestState.CHANNEL_ERROR: [TestState.IDLE, TestState.DISABLED],
            TestState.BATTERY_ERROR: [TestState.IDLE, TestState.DISABLED],
            TestState.HARDWARE_ERROR: [TestState.IDLE, TestState.DISABLED],
            TestState.SKIPPED: [TestState.IDLE, TestState.DISABLED]
        }
        
        return new_state in valid_transitions.get(old_state, [])
    
    def _update_testing_flag(self):
        """根据测试状态更新测试标志"""
        self._is_testing = (self._test_state == TestState.TESTING)
    
    def _record_state_change(self, old_state: TestState, new_state: TestState, reason: Optional[str]):
        """记录状态变化"""
        import time
        
        event = StateChangeEvent(
            channel_number=self.channel_number,
            old_state=old_state,
            new_state=new_state,
            timestamp=time.time(),
            reason=reason
        )
        
        self.state_history.append(event)
        
        # 限制历史记录数量
        if len(self.state_history) > 100:
            self.state_history = self.state_history[-50:]
    
    def _notify_state_change(self, old_state: TestState, new_state: TestState, reason: Optional[str]):
        """通知状态变化"""
        import time
        
        event = StateChangeEvent(
            channel_number=self.channel_number,
            old_state=old_state,
            new_state=new_state,
            timestamp=time.time(),
            reason=reason
        )
        
        for callback in self.state_change_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"通道{self.channel_number}状态变化回调执行失败: {e}")
    
    def get_state_summary(self) -> Dict[str, Any]:
        """
        获取状态摘要
        
        Returns:
            状态摘要字典
        """
        try:
            return {
                'channel_number': self.channel_number,
                'test_state': self._test_state.value,
                'is_enabled': self.is_enabled,
                'is_testing': self.is_testing,
                'has_error': self.has_error,
                'error_message': self.error_message,
                'status_code': f'0x{self.status_code:04X}' if self.status_code else None,
                'state_history_count': len(self.state_history)
            }
        except Exception as e:
            logger.error(f"通道{self.channel_number}获取状态摘要失败: {e}")
            return {}
