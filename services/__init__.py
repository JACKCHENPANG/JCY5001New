# -*- coding: utf-8 -*-
"""
统一服务模块
提供优化后的统一服务，替代原有的多个重复组件

Author: Jack
Date: 2025-01-30
"""

from .unified_print_service import UnifiedPrintService, get_print_service, reset_print_service
from .unified_channel_service import UnifiedChannelService, get_channel_service, reset_channel_service
from .unified_test_controller import UnifiedTestController, get_test_controller, reset_test_controller

__all__ = [
    # 统一打印服务
    'UnifiedPrintService', 'get_print_service', 'reset_print_service',
    
    # 统一通道服务
    'UnifiedChannelService', 'get_channel_service', 'reset_channel_service',
    
    # 统一测试控制器
    'UnifiedTestController', 'get_test_controller', 'reset_test_controller'
]
