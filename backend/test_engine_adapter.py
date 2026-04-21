#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TestEngine适配器类
将重构后的5个类组合成与原TestEngine兼容的接口

这个适配器类的作用：
1. 保持与原TestEngine相同的接口
2. 内部使用重构后的5个类
3. 确保向后兼容性
4. 提供平滑的迁移路径

Author: Augment Agent
Date: 2025-05-30
"""

import logging
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# 导入重构后的4个类（删除了TestResultProcessor）
from backend.test_flow_controller import TestFlowController
from backend.test_state_manager import TestStateManager
from backend.test_progress_manager import TestProgressManager
from backend.test_config_manager import TestConfigManager

# 导入其他必要的类
from backend.data_processor import DataProcessor
from data.database_manager import DatabaseManager


class TestEngineAdapter:
    """
    TestEngine适配器类

    将重构后的5个类组合成与原TestEngine兼容的接口
    """

    def __init__(self, config_manager, db_manager, comm_manager):
        """
        初始化TestEngine适配器

        Args:
            config_manager: 配置管理器
            db_manager: 数据库管理器
            comm_manager: 通信管理器
        """

        self.config_manager = config_manager
        self.db_manager = db_manager
        self.comm_manager = comm_manager

        # 回调函数存储
        self._status_callback = None
        self._progress_callback = None
        self._result_callback = None
        self._frequency_callback = None

        # 初始化重构后的5个类
        self._init_refactored_components()

        logger.debug("✅ TestEngine适配器初始化完成")

    def _init_refactored_components(self):
        """初始化重构后的5个组件"""
        try:

            # 1. 创建测试配置管理器
            def config_change_callback(config_type, changes):
                logger.debug(f"配置变更: {config_type} - {changes}")

            self.test_config_manager = TestConfigManager(
                config_manager=self.config_manager,
                config_change_callback=config_change_callback
            )

            # 2. 创建状态管理器
            def status_callback(status_data):
                if self._status_callback:
                    # 适配状态回调格式
                    is_testing = status_data.get('is_testing', False)
                    self._status_callback(is_testing)

            def progress_callback(channel_num, progress_data):
                if self._progress_callback:
                    self._progress_callback(channel_num, progress_data)

            self.test_state_manager = TestStateManager(
                progress_callback=progress_callback,
                status_callback=status_callback
            )

            # 3. 创建进度管理器
            def frequency_callback(channel_num, frequency, current_index, total_count, status):
                if self._frequency_callback:
                    self._frequency_callback(channel_num, frequency, current_index, total_count, status)

            self.test_progress_manager = TestProgressManager(
                progress_callback=progress_callback,
                frequency_callback=frequency_callback
            )

            # 4. 创建数据处理器
            self.data_processor = DataProcessor(self.config_manager)

            # 5. 结果处理器已删除，功能合并到test_result_manager中
            # 结果回调直接使用
            def result_callback(channel_num, result_data):
                if self._result_callback:
                    self._result_callback(channel_num, result_data)

            self._result_callback_func = result_callback

            # 6. 创建流程控制器（核心协调器）
            self.test_flow_controller = TestFlowController(
                config_manager=self.test_config_manager,
                comm_manager=self.comm_manager,
                progress_callback=progress_callback,
                status_callback=status_callback
            )

            logger.debug("✅ 重构后的组件初始化完成")

        except Exception as e:
            logger.error(f"❌ 初始化重构组件失败: {e}")
            raise

    def set_status_callback(self, callback: Callable[[bool], None]):
        """
        设置状态回调函数

        Args:
            callback: 状态回调函数，参数为is_testing(bool)
        """
        self._status_callback = callback
        logger.debug("状态回调函数已设置")

    def set_progress_callback(self, callback: Callable[[int, Dict], None]):
        """
        设置进度回调函数

        Args:
            callback: 进度回调函数，参数为(channel_num, progress_data)
        """
        self._progress_callback = callback
        logger.debug("进度回调函数已设置")

    def set_result_callback(self, callback: Callable[[int, Dict], None]):
        """
        设置结果回调函数

        Args:
            callback: 结果回调函数，参数为(channel_num, result_data)
        """
        self._result_callback = callback
        logger.debug("结果回调函数已设置")

    def set_frequency_callback(self, callback: Callable[[int, float, int, int, str], None]):
        """
        设置频点回调函数

        Args:
            callback: 频点回调函数，参数为(channel_num, frequency, current_index, total_count, status)
        """
        self._frequency_callback = callback
        logger.debug("频点回调函数已设置")

    def start_batch_test(self, batch_info: Dict, battery_codes: List[str]) -> bool:
        """
        启动批次测试

        Args:
            batch_info: 批次信息
            battery_codes: 电池码列表

        Returns:
            是否启动成功
        """
        try:
            logger.info(f"🚀 启动批次测试: {batch_info.get('batch_number', 'Unknown')}")
            logger.info(f"📋 电池码: {battery_codes}")

            # 使用流程控制器启动批次测试
            result = self.test_flow_controller.start_batch_test(batch_info, battery_codes)

            if result:
                logger.info("✅ 批次测试启动成功")
            else:
                logger.error("❌ 批次测试启动失败")

            return result

        except Exception as e:
            logger.error(f"❌ 启动批次测试失败: {e}")
            return False

    def stop_test(self):
        """停止测试"""
        try:
            logger.info("🛑 停止测试...")

            # 使用流程控制器停止测试
            self.test_flow_controller.stop_test()

            logger.info("✅ 测试已停止")

        except Exception as e:
            logger.error(f"❌ 停止测试失败: {e}")

    def get_test_status(self) -> Dict:
        """
        获取测试状态

        Returns:
            测试状态字典
        """
        try:
            return self.test_flow_controller.get_test_status()
        except Exception as e:
            logger.error(f"❌ 获取测试状态失败: {e}")
            return {'is_testing': False, 'error': str(e)}

    def is_testing(self) -> bool:
        """
        检查是否正在测试

        Returns:
            是否正在测试
        """
        try:
            status = self.get_test_status()
            return status.get('is_testing', False)
        except Exception as e:
            logger.error(f"❌ 检查测试状态失败: {e}")
            return False

    def get_progress_info(self, channel_num: int) -> Dict:
        """
        获取通道进度信息

        Args:
            channel_num: 通道号

        Returns:
            进度信息字典
        """
        try:
            return self.test_progress_manager.get_channel_progress_info(channel_num)
        except Exception as e:
            logger.error(f"❌ 获取通道{channel_num}进度信息失败: {e}")
            return {}

    def __del__(self):
        """析构函数"""
        try:
            if hasattr(self, 'test_flow_controller'):
                self.test_flow_controller.stop_test()
        except:
            pass
