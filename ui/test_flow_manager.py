# -*- coding: utf-8 -*-
"""
测试流程管理器 - 重构版本
使用适配器模式，将重构后的6个专门管理器组合成统一接口

重构说明：
- 原1100行的大类已拆分为6个专门的管理器
- 使用适配器模式保持向后兼容性
- 遵循单一职责原则

重构后的管理器：
1. TestFlowController - 核心流程控制
2. TestPreCheckManager - 测试前预检查
3. TestConfigurationManager - 测试配置管理
4. TestStatisticsManager - 统计管理
5. TestUIUpdateManager - UI更新管理
6. TestErrorHandler - 错误处理

Author: Jack
Date: 2025-01-30
Version: 重构版本 - 使用适配器模式
"""

import logging
from ui.test_flow_managers.test_flow_manager_adapter import TestFlowManagerAdapter

logger = logging.getLogger(__name__)

# 使用适配器类作为TestFlowManager的实现
# 这样可以保持向后兼容性，同时使用重构后的架构
TestFlowManager = TestFlowManagerAdapter

logger.info("✅ TestFlowManager重构完成 - 使用适配器模式，拆分为6个专门管理器")