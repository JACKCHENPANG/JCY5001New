# -*- coding: utf-8 -*-
"""
核心服务模块
提供统一的事件总线、状态管理和资源池服务

Author: Jack
Date: 2025-01-30
"""

from .event_bus import EventBus, EventType, Event, EventHandler, get_event_bus, reset_event_bus
from .state_manager import (
    UnifiedStateManager, TestState, ChannelState, StateObserver, 
    get_state_manager, reset_state_manager
)
from .resource_pool import (
    ResourcePool, PooledResource, ChannelManager, TimerManager,
    get_resource_pool, reset_resource_pool
)

__all__ = [
    # 事件总线
    'EventBus', 'EventType', 'Event', 'EventHandler', 'get_event_bus', 'reset_event_bus',
    
    # 状态管理
    'UnifiedStateManager', 'TestState', 'ChannelState', 'StateObserver', 
    'get_state_manager', 'reset_state_manager',
    
    # 资源池
    'ResourcePool', 'PooledResource', 'ChannelManager', 'TimerManager',
    'get_resource_pool', 'reset_resource_pool'
]
