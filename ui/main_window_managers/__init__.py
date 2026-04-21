# -*- coding: utf-8 -*-
"""
主窗口管理器包
包含重构后的主窗口管理相关类

Author: Jack
Date: 2025-01-30
"""

from .window_layout_manager import WindowLayoutManager
from .component_initializer import ComponentInitializer
from .settings_loader import SettingsLoader
from .event_coordinator import EventCoordinator
from .authorization_manager import AuthorizationManager

__all__ = [
    'WindowLayoutManager',
    'ComponentInitializer', 
    'SettingsLoader',
    'EventCoordinator',
    'AuthorizationManager'
]