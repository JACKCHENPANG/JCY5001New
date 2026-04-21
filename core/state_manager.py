# -*- coding: utf-8 -*-
"""
统一状态管理器
用于管理整个系统的状态，避免状态冲突和重复维护

Author: Jack
Date: 2025-01-30
"""

import logging
import threading
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from .event_bus import get_event_bus, EventType

logger = logging.getLogger(__name__)


class TestState(Enum):
    """测试状态枚举"""
    IDLE = "idle"                    # 空闲状态
    PREPARING = "preparing"          # 准备中
    RUNNING = "running"              # 运行中
    PAUSED = "paused"               # 暂停
    STOPPING = "stopping"           # 停止中
    COMPLETED = "completed"         # 完成
    FAILED = "failed"               # 失败
    ERROR = "error"                 # 错误


class ChannelState(Enum):
    """通道状态枚举"""
    DISCONNECTED = "disconnected"   # 未连接
    CONNECTED = "connected"         # 已连接
    TESTING = "testing"             # 测试中
    COMPLETED = "completed"         # 完成
    ERROR = "error"                 # 错误
    ABNORMAL = "abnormal"           # 异常


@dataclass
class StateChange:
    """状态变化记录"""
    timestamp: datetime
    old_state: Any
    new_state: Any
    reason: str = ""
    source: str = "unknown"


class StateObserver:
    """状态观察者基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
    
    def on_test_state_changed(self, old_state: TestState, new_state: TestState, reason: str = ""):
        """测试状态变化回调"""
        pass
    
    def on_channel_state_changed(self, channel_num: int, old_state: ChannelState, new_state: ChannelState, reason: str = ""):
        """通道状态变化回调"""
        pass
    
    def on_property_changed(self, property_name: str, old_value: Any, new_value: Any):
        """属性变化回调"""
        pass


class UnifiedStateManager:
    """
    统一状态管理器
    
    职责：
    - 管理测试状态
    - 管理通道状态
    - 管理系统属性
    - 状态变化通知
    - 状态历史记录
    """
    
    def __init__(self):
        # 状态数据
        self._test_state = TestState.IDLE
        self._channel_states: Dict[int, ChannelState] = {}
        self._properties: Dict[str, Any] = {}
        
        # 观察者和历史
        self._observers: List[StateObserver] = []
        self._state_history: List[StateChange] = []
        self._max_history_size = 500
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 事件总线
        self.event_bus = get_event_bus()
        
        # 初始化通道状态
        for i in range(1, 9):
            self._channel_states[i] = ChannelState.DISCONNECTED
        
        logger.info("✅ 统一状态管理器初始化完成")
    
    @property
    def test_state(self) -> TestState:
        """获取测试状态"""
        with self._lock:
            return self._test_state
    
    @property
    def is_testing(self) -> bool:
        """是否正在测试"""
        return self.test_state in [TestState.PREPARING, TestState.RUNNING, TestState.PAUSED]
    
    @property
    def is_idle(self) -> bool:
        """是否空闲"""
        return self.test_state == TestState.IDLE
    
    def set_test_state(self, new_state: TestState, reason: str = "", source: str = "unknown") -> bool:
        """
        设置测试状态
        
        Args:
            new_state: 新状态
            reason: 变化原因
            source: 变化源
            
        Returns:
            是否设置成功
        """
        try:
            with self._lock:
                old_state = self._test_state
                
                if old_state == new_state:
                    logger.debug(f"测试状态无变化: {new_state.value}")
                    return True
                
                # 验证状态转换是否合法
                if not self._is_valid_test_state_transition(old_state, new_state):
                    logger.warning(f"⚠️ 无效的测试状态转换: {old_state.value} -> {new_state.value}")
                    return False
                
                # 更新状态
                self._test_state = new_state
                
                # 记录状态变化
                change = StateChange(
                    timestamp=datetime.now(),
                    old_state=old_state,
                    new_state=new_state,
                    reason=reason,
                    source=source
                )
                self._record_state_change(change)
                
                logger.info(f"🔄 测试状态变化: {old_state.value} -> {new_state.value} ({reason})")
                
                # 通知观察者
                self._notify_test_state_observers(old_state, new_state, reason)
                
                # 发布事件
                self.event_bus.publish(
                    EventType.STATE_CHANGED,
                    {
                        'type': 'test_state',
                        'old_state': old_state.value,
                        'new_state': new_state.value,
                        'reason': reason
                    },
                    source
                )
                
                return True
                
        except Exception as e:
            logger.error(f"❌ 设置测试状态失败: {e}")
            return False
    
    def get_channel_state(self, channel_num: int) -> ChannelState:
        """获取通道状态"""
        with self._lock:
            return self._channel_states.get(channel_num, ChannelState.DISCONNECTED)
    
    def set_channel_state(self, channel_num: int, new_state: ChannelState, reason: str = "", source: str = "unknown") -> bool:
        """
        设置通道状态
        
        Args:
            channel_num: 通道号
            new_state: 新状态
            reason: 变化原因
            source: 变化源
            
        Returns:
            是否设置成功
        """
        try:
            if not (1 <= channel_num <= 8):
                logger.error(f"❌ 无效的通道号: {channel_num}")
                return False
            
            with self._lock:
                old_state = self._channel_states.get(channel_num, ChannelState.DISCONNECTED)
                
                if old_state == new_state:
                    logger.debug(f"通道{channel_num}状态无变化: {new_state.value}")
                    return True
                
                # 更新状态
                self._channel_states[channel_num] = new_state
                
                # 记录状态变化
                change = StateChange(
                    timestamp=datetime.now(),
                    old_state=old_state,
                    new_state=new_state,
                    reason=f"通道{channel_num}: {reason}",
                    source=source
                )
                self._record_state_change(change)
                
                logger.debug(f"🔄 通道{channel_num}状态变化: {old_state.value} -> {new_state.value} ({reason})")
                
                # 通知观察者
                self._notify_channel_state_observers(channel_num, old_state, new_state, reason)
                
                # 发布事件
                self.event_bus.publish(
                    EventType.STATE_CHANGED,
                    {
                        'type': 'channel_state',
                        'channel_num': channel_num,
                        'old_state': old_state.value,
                        'new_state': new_state.value,
                        'reason': reason
                    },
                    source
                )
                
                return True
                
        except Exception as e:
            logger.error(f"❌ 设置通道{channel_num}状态失败: {e}")
            return False
    
    def get_property(self, name: str, default: Any = None) -> Any:
        """获取属性值"""
        with self._lock:
            return self._properties.get(name, default)
    
    def set_property(self, name: str, value: Any, source: str = "unknown") -> bool:
        """
        设置属性值
        
        Args:
            name: 属性名
            value: 属性值
            source: 变化源
            
        Returns:
            是否设置成功
        """
        try:
            with self._lock:
                old_value = self._properties.get(name)
                
                if old_value == value:
                    return True
                
                # 更新属性
                self._properties[name] = value
                
                logger.debug(f"🔄 属性变化: {name} = {value}")
                
                # 通知观察者
                self._notify_property_observers(name, old_value, value)
                
                return True
                
        except Exception as e:
            logger.error(f"❌ 设置属性{name}失败: {e}")
            return False
    
    def add_observer(self, observer: StateObserver) -> bool:
        """添加状态观察者"""
        try:
            with self._lock:
                if observer not in self._observers:
                    self._observers.append(observer)
                    logger.debug(f"✅ 添加状态观察者: {observer.name}")
                    return True
                else:
                    logger.warning(f"⚠️ 状态观察者已存在: {observer.name}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 添加状态观察者失败: {e}")
            return False
    
    def remove_observer(self, observer: StateObserver) -> bool:
        """移除状态观察者"""
        try:
            with self._lock:
                if observer in self._observers:
                    self._observers.remove(observer)
                    logger.debug(f"✅ 移除状态观察者: {observer.name}")
                    return True
                else:
                    logger.warning(f"⚠️ 状态观察者不存在: {observer.name}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 移除状态观察者失败: {e}")
            return False
    
    def _is_valid_test_state_transition(self, old_state: TestState, new_state: TestState) -> bool:
        """验证测试状态转换是否合法"""
        # 定义合法的状态转换
        valid_transitions = {
            TestState.IDLE: [TestState.PREPARING, TestState.ERROR],
            TestState.PREPARING: [TestState.RUNNING, TestState.FAILED, TestState.ERROR, TestState.IDLE],
            TestState.RUNNING: [TestState.PAUSED, TestState.STOPPING, TestState.COMPLETED, TestState.ERROR, TestState.FAILED],
            TestState.PAUSED: [TestState.RUNNING, TestState.STOPPING, TestState.ERROR],
            TestState.STOPPING: [TestState.IDLE, TestState.ERROR],
            TestState.COMPLETED: [TestState.IDLE],
            TestState.FAILED: [TestState.IDLE],
            TestState.ERROR: [TestState.IDLE]
        }
        
        return new_state in valid_transitions.get(old_state, [])
    
    def _record_state_change(self, change: StateChange):
        """记录状态变化历史"""
        try:
            self._state_history.append(change)
            
            # 限制历史记录大小
            if len(self._state_history) > self._max_history_size:
                self._state_history = self._state_history[-self._max_history_size:]
                
        except Exception as e:
            logger.error(f"❌ 记录状态变化失败: {e}")
    
    def _notify_test_state_observers(self, old_state: TestState, new_state: TestState, reason: str):
        """通知测试状态观察者"""
        for observer in self._observers:
            if observer.enabled:
                try:
                    observer.on_test_state_changed(old_state, new_state, reason)
                except Exception as e:
                    logger.error(f"❌ 通知观察者{observer.name}测试状态变化失败: {e}")
    
    def _notify_channel_state_observers(self, channel_num: int, old_state: ChannelState, new_state: ChannelState, reason: str):
        """通知通道状态观察者"""
        for observer in self._observers:
            if observer.enabled:
                try:
                    observer.on_channel_state_changed(channel_num, old_state, new_state, reason)
                except Exception as e:
                    logger.error(f"❌ 通知观察者{observer.name}通道状态变化失败: {e}")
    
    def _notify_property_observers(self, property_name: str, old_value: Any, new_value: Any):
        """通知属性观察者"""
        for observer in self._observers:
            if observer.enabled:
                try:
                    observer.on_property_changed(property_name, old_value, new_value)
                except Exception as e:
                    logger.error(f"❌ 通知观察者{observer.name}属性变化失败: {e}")
    
    def get_state_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        with self._lock:
            return {
                'test_state': self._test_state.value,
                'is_testing': self.is_testing,
                'channel_states': {ch: state.value for ch, state in self._channel_states.items()},
                'properties_count': len(self._properties),
                'observers_count': len(self._observers),
                'history_count': len(self._state_history)
            }
    
    def reset(self):
        """重置所有状态"""
        try:
            with self._lock:
                # 重置测试状态
                self.set_test_state(TestState.IDLE, "系统重置", "state_manager")
                
                # 重置通道状态
                for channel_num in range(1, 9):
                    self.set_channel_state(channel_num, ChannelState.DISCONNECTED, "系统重置", "state_manager")
                
                # 清空属性
                self._properties.clear()
                
                # 清空历史
                self._state_history.clear()
                
                logger.info("🔄 状态管理器已重置")
                
        except Exception as e:
            logger.error(f"❌ 重置状态管理器失败: {e}")


# 全局状态管理器实例
_global_state_manager = None


def get_state_manager() -> UnifiedStateManager:
    """获取全局状态管理器实例"""
    global _global_state_manager
    if _global_state_manager is None:
        _global_state_manager = UnifiedStateManager()
    return _global_state_manager


def reset_state_manager():
    """重置全局状态管理器（主要用于测试）"""
    global _global_state_manager
    _global_state_manager = None
