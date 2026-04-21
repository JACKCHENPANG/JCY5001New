# -*- coding: utf-8 -*-
"""
统一事件总线
用于替代多层回调，实现事件驱动架构

Author: Jack
Date: 2025-01-30
"""

import logging
import threading
from typing import Dict, List, Callable, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型枚举"""
    # 测试相关事件
    TEST_STARTED = "test_started"
    TEST_STOPPED = "test_stopped"
    TEST_COMPLETED = "test_completed"
    TEST_PROGRESS = "test_progress"
    
    # 通道相关事件
    CHANNEL_STARTED = "channel_started"
    CHANNEL_COMPLETED = "channel_completed"
    CHANNEL_ERROR = "channel_error"
    CHANNEL_PROGRESS = "channel_progress"
    
    # 结果相关事件
    RESULT_CALCULATED = "result_calculated"
    RESULT_SAVED = "result_saved"
    RESULT_PRINTED = "result_printed"
    
    # 状态相关事件
    STATE_CHANGED = "state_changed"
    ERROR_OCCURRED = "error_occurred"
    
    # UI相关事件
    UI_UPDATE = "ui_update"
    UI_REFRESH = "ui_refresh"


@dataclass
class Event:
    """事件数据结构"""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime
    source: str = "unknown"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class EventHandler:
    """事件处理器基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
    
    def handle(self, event: Event) -> bool:
        """
        处理事件
        
        Args:
            event: 事件对象
            
        Returns:
            是否处理成功
        """
        if not self.enabled:
            return True
            
        try:
            return self._handle_event(event)
        except Exception as e:
            logger.error(f"事件处理器{self.name}处理事件{event.event_type}失败: {e}")
            return False
    
    def _handle_event(self, event: Event) -> bool:
        """子类需要实现的事件处理方法"""
        raise NotImplementedError


class EventBus:
    """
    统一事件总线
    
    职责：
    - 事件发布和订阅
    - 事件路由和分发
    - 异步事件处理
    - 事件历史记录
    """
    
    def __init__(self):
        self.subscribers: Dict[EventType, List[EventHandler]] = {}
        self.event_history: List[Event] = []
        self.max_history_size = 1000
        self._lock = threading.RLock()
        self.enabled = True
        
        logger.info("✅ 事件总线初始化完成")
    
    def subscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理器
            
        Returns:
            是否订阅成功
        """
        try:
            with self._lock:
                if event_type not in self.subscribers:
                    self.subscribers[event_type] = []
                
                if handler not in self.subscribers[event_type]:
                    self.subscribers[event_type].append(handler)
                    logger.debug(f"✅ 事件处理器{handler.name}订阅事件{event_type.value}")
                    return True
                else:
                    logger.warning(f"⚠️ 事件处理器{handler.name}已订阅事件{event_type.value}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 订阅事件{event_type.value}失败: {e}")
            return False
    
    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """
        取消订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理器
            
        Returns:
            是否取消成功
        """
        try:
            with self._lock:
                if event_type in self.subscribers:
                    if handler in self.subscribers[event_type]:
                        self.subscribers[event_type].remove(handler)
                        logger.debug(f"✅ 事件处理器{handler.name}取消订阅事件{event_type.value}")
                        return True
                
                logger.warning(f"⚠️ 事件处理器{handler.name}未订阅事件{event_type.value}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 取消订阅事件{event_type.value}失败: {e}")
            return False
    
    def publish(self, event_type: EventType, data: Dict[str, Any], source: str = "unknown") -> bool:
        """
        发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            source: 事件源
            
        Returns:
            是否发布成功
        """
        if not self.enabled:
            return True
            
        try:
            # 创建事件对象
            event = Event(
                event_type=event_type,
                data=data,
                timestamp=datetime.now(),
                source=source
            )
            
            # 记录事件历史
            self._record_event(event)
            
            # 分发事件
            return self._dispatch_event(event)
            
        except Exception as e:
            logger.error(f"❌ 发布事件{event_type.value}失败: {e}")
            return False
    
    def _dispatch_event(self, event: Event) -> bool:
        """
        分发事件给订阅者
        
        Args:
            event: 事件对象
            
        Returns:
            是否分发成功
        """
        try:
            with self._lock:
                handlers = self.subscribers.get(event.event_type, [])
                
                if not handlers:
                    logger.debug(f"📭 事件{event.event_type.value}没有订阅者")
                    return True
                
                success_count = 0
                for handler in handlers:
                    if handler.handle(event):
                        success_count += 1
                    else:
                        logger.warning(f"⚠️ 处理器{handler.name}处理事件{event.event_type.value}失败")
                
                logger.debug(f"📨 事件{event.event_type.value}分发完成: {success_count}/{len(handlers)}成功")
                return success_count == len(handlers)
                
        except Exception as e:
            logger.error(f"❌ 分发事件{event.event_type.value}失败: {e}")
            return False
    
    def _record_event(self, event: Event):
        """记录事件历史"""
        try:
            with self._lock:
                self.event_history.append(event)
                
                # 限制历史记录大小
                if len(self.event_history) > self.max_history_size:
                    self.event_history = self.event_history[-self.max_history_size:]
                    
        except Exception as e:
            logger.error(f"❌ 记录事件历史失败: {e}")
    
    def get_event_history(self, event_type: EventType = None, limit: int = 100) -> List[Event]:
        """
        获取事件历史
        
        Args:
            event_type: 事件类型过滤（可选）
            limit: 返回数量限制
            
        Returns:
            事件历史列表
        """
        try:
            with self._lock:
                if event_type is None:
                    events = self.event_history
                else:
                    events = [e for e in self.event_history if e.event_type == event_type]
                
                return events[-limit:] if limit > 0 else events
                
        except Exception as e:
            logger.error(f"❌ 获取事件历史失败: {e}")
            return []
    
    def clear_history(self):
        """清空事件历史"""
        try:
            with self._lock:
                self.event_history.clear()
                logger.info("🧹 事件历史已清空")
                
        except Exception as e:
            logger.error(f"❌ 清空事件历史失败: {e}")
    
    def get_subscriber_count(self, event_type: EventType) -> int:
        """获取指定事件类型的订阅者数量"""
        with self._lock:
            return len(self.subscribers.get(event_type, []))
    
    def get_all_subscribers(self) -> Dict[EventType, int]:
        """获取所有事件类型的订阅者数量"""
        with self._lock:
            return {event_type: len(handlers) for event_type, handlers in self.subscribers.items()}
    
    def enable(self):
        """启用事件总线"""
        self.enabled = True
        logger.info("✅ 事件总线已启用")
    
    def disable(self):
        """禁用事件总线"""
        self.enabled = False
        logger.info("⏸️ 事件总线已禁用")


# 全局事件总线实例
_global_event_bus = None


def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def reset_event_bus():
    """重置全局事件总线（主要用于测试）"""
    global _global_event_bus
    _global_event_bus = None
