#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TestEngine模块 - 重构后的兼容性接口
导入TestEngineAdapter以保持向后兼容性

Author: Jack
Date: 2025-06-04
"""

# 导入适配器类并重命名为TestEngine以保持兼容性
from backend.test_engine_adapter import TestEngineAdapter as TestEngine

# 导出TestEngine类
__all__ = ['TestEngine']
