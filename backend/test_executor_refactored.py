# -*- coding: utf-8 -*-
"""
重构后的测试执行器类
将原有的复杂测试执行器拆分为6个专门管理器，主类简化为纯协调器角色

重构说明：
- 原始文件1986行，34个方法，职责过于复杂
- 拆分为6个专门管理器，每个管理器负责特定功能
- 主类只负责管理器的初始化和协调

管理器分工：
1. TestExecutionControlManager - 测试执行控制（启动、停止、暂停等）
2. ContinuousTestManager - 连续测试管理（计数、统计、循环控制等）
3. ParallelTestManager - 并行测试管理（错频、同时启动等）
4. TestResultProcessingManager - 测试结果处理（收集、分析、回调等）
5. TestStateManager - 测试状态管理（状态跟踪、进度监控等）
6. DeviceCommunicationManager - 设备通信管理（命令发送、数据读取等）

Author: Jack
Date: 2025-06-27
Version: 重构版本 - 拆分为6个专门管理器
"""

import logging
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

# 导入所有管理器
from backend.test_executor_managers import (
    TestExecutionControlManager,
    ContinuousTestManager,
    ParallelTestManager,
    TestResultProcessingManager,
    TestStateManager,
    TestState,
    DeviceCommunicationManager
)


class TestExecutor:
    """
    重构后的测试执行器类 - 纯协调器角色

    职责：
    - 6个管理器的初始化和生命周期管理
    - 管理器之间的协调和通信
    - 统一的测试执行接口
    - 兼容性保证

    重构成果：
    - 原1986行代码拆分为6个专门管理器
    - 主类简化为纯协调器，不包含具体业务逻辑
    - 遵循单一职责原则和开闭原则
    """

    def __init__(self, comm_manager, test_config_manager, device_config_manager,
                 impedance_data_manager, test_result_manager, startup_strategy_manager):
        """
        初始化重构后的测试执行器

        Args:
            comm_manager: 通信管理器
            test_config_manager: 测试配置管理器
            device_config_manager: 设备配置管理器
            impedance_data_manager: 阻抗数据管理器
            test_result_manager: 测试结果管理器
            startup_strategy_manager: 启动策略管理器
        """
        # 保存依赖管理器
        self.comm_manager = comm_manager
        self.test_config_manager = test_config_manager
        self.device_config_manager = device_config_manager
        self.impedance_data_manager = impedance_data_manager
        self.test_result_manager = test_result_manager
        self.startup_strategy_manager = startup_strategy_manager

        # 初始化6个专门管理器
        self._initialize_all_managers()

        # 设置管理器之间的协调
        self._setup_manager_coordination()

        # 兼容性属性（保持向后兼容）
        self._setup_compatibility_attributes()

        logger.debug("重构后的测试执行器初始化完成")

    def _initialize_all_managers(self):
        """初始化所有6个管理器"""
        try:

            # 1. 测试执行控制管理器
            self.execution_control_manager = TestExecutionControlManager()

            # 2. 连续测试管理器
            self.continuous_test_manager = ContinuousTestManager()

            # 3. 并行测试管理器
            self.parallel_test_manager = ParallelTestManager(
                self.comm_manager,
                self.device_config_manager,
                test_executor=self  # 新增传递测试执行器引用以访问锁定电压
            )

            # 4. 测试结果处理管理器
            self.result_processing_manager = TestResultProcessingManager(
                self.comm_manager,
                self.device_config_manager,
                self.test_result_manager,  # 传递测试结果管理器引用
                self.test_config_manager.config_manager  # 传递配置管理器引用
            )

            # 5. 测试状态管理器
            self.state_manager = TestStateManager()

            # 6. 设备通信管理器
            self.device_communication_manager = DeviceCommunicationManager(
                self.comm_manager,
                self.device_config_manager
            )

            logger.debug("✅ 所有6个测试执行管理器初始化完成")

        except Exception as e:
            logger.error(f"❌ 初始化测试执行管理器失败: {e}")
            raise

    def _setup_manager_coordination(self):
        """设置管理器之间的协调"""
        try:
            logger.debug("设置管理器协调...")

            # 连接执行控制管理器信号
            self.execution_control_manager.test_started.connect(self._on_test_started)
            self.execution_control_manager.test_stopped.connect(self._on_test_stopped)

            # 连接连续测试管理器信号
            self.continuous_test_manager.cycle_completed.connect(self._on_cycle_completed)
            self.continuous_test_manager.count_updated.connect(self._on_count_updated)  # 修复：添加计数更新信号连接
            self.continuous_test_manager.continuous_test_started.connect(self._on_continuous_test_started)
            self.continuous_test_manager.continuous_test_stopped.connect(self._on_continuous_test_stopped)
            self.continuous_test_manager.statistics_updated.connect(self._on_statistics_updated)

            # 连接并行测试管理器信号
            self.parallel_test_manager.parallel_test_completed.connect(self._on_parallel_test_completed)

            # 连接结果处理管理器信号
            self.result_processing_manager.results_processed.connect(self._on_results_processed)

            # 连接状态管理器信号
            self.state_manager.state_changed.connect(self._on_state_changed)

            # 连接设备通信管理器信号
            self.device_communication_manager.measurement_completed.connect(self._on_measurement_completed)

            logger.debug("管理器协调设置完成")

        except Exception as e:
            logger.error(f"设置管理器协调失败: {e}")

    def _setup_compatibility_attributes(self):
        """设置兼容性属性"""
        try:
            # 兼容原有接口
            self.stop_event = self.execution_control_manager.stop_event
            self.continuous_test_count = 0  # 将委托给连续测试管理器

            # 兼容原有的管理器引用
            self._current_staggered_manager = None
            self._current_simultaneous_manager = None

            # 兼容原有的回调
            self.progress_callback = None
            self.status_callback = None

        except Exception as e:
            logger.error(f"设置兼容性属性失败: {e}")

    # ===== 主要测试执行接口 =====

    def execute_test(self, test_config: Dict[str, Any], enabled_channels: List[int]) -> bool:
        """
        执行测试（主要入口）
        
        Args:
            test_config: 测试配置
            enabled_channels: 启用的通道列表
            
        Returns:
            是否执行成功
        """
        try:
            logger.info("🚀 开始执行测试")

            # 设置测试状态为准备中
            self.state_manager.set_state(TestState.PREPARING, "开始测试")

            # 启动执行控制
            if not self.execution_control_manager.start_test(test_config, enabled_channels):
                self.state_manager.set_state(TestState.FAILED, "启动执行控制失败")
                return False

            # 准备测试环境
            if not self.device_communication_manager.prepare_test_environment(test_config):
                self.state_manager.set_state(TestState.FAILED, "准备测试环境失败")
                return False

            # 设置测试状态为运行中
            self.state_manager.set_state(TestState.RUNNING, "测试环境准备完成")

            # 记录测试开始时间
            self.test_result_manager.record_test_start(enabled_channels)

            # 根据测试模式执行不同的测试流程
            continuous_mode = test_config.get('continuous_mode', False)
            if continuous_mode:
                logger.info("开始连续测试模式")
                success = self._execute_continuous_test(test_config, enabled_channels)
            else:
                logger.info("开始单次测试模式")
                success = self._execute_single_test(test_config, enabled_channels)

            # 记录测试结束时间
            self.test_result_manager.record_test_end(enabled_channels)

            # 设置最终状态
            if success:
                self.state_manager.set_state(TestState.COMPLETED, "测试执行成功")
            else:
                self.state_manager.set_state(TestState.FAILED, "测试执行失败")

            logger.info(f"测试执行完成: {'成功' if success else '失败'}")
            return success

        except Exception as e:
            logger.error(f"测试执行失败: {e}")
            self.state_manager.set_state(TestState.FAILED, f"异常: {str(e)}")
            return False

    def _execute_single_test(self, test_config: Dict[str, Any], enabled_channels: List[int]) -> bool:
        """执行单次测试"""
        try:
            # 获取频率列表
            frequencies = test_config.get('frequencies', [])
            if not frequencies:
                logger.error("测试配置中无频率列表")
                return False

            # 执行多频点测试
            return self._execute_multi_frequency_test(frequencies, enabled_channels, test_config)

        except Exception as e:
            logger.error(f"执行单次测试失败: {e}")
            return False

    def _execute_continuous_test(self, test_config: Dict[str, Any], enabled_channels: List[int]) -> bool:
        """执行连续测试"""
        try:
            # 保存当前测试配置，供信号处理使用
            self._current_test_config = test_config

            # 启动连续测试管理器
            if not self.continuous_test_manager.start_continuous_test(test_config):
                return False

            # 连续测试循环
            while self.continuous_test_manager.should_continue_testing(test_config):
                # 检查停止信号
                if self.execution_control_manager.is_stop_requested():
                    logger.info("收到停止信号，终止连续测试")
                    break

                # 执行一个测试周期
                success = self.continuous_test_manager.execute_test_cycle(
                    test_config,
                    enabled_channels,
                    self._execute_single_test
                )

                # 等待下一个周期
                if not self.continuous_test_manager.wait_for_next_cycle(test_config, self.stop_event):
                    break

            # 停止连续测试
            self.continuous_test_manager.stop_continuous_test("测试完成")
            return True

        except Exception as e:
            logger.error(f"执行连续测试失败: {e}")
            self.continuous_test_manager.stop_continuous_test("执行异常")
            return False

    def _execute_multi_frequency_test(self, frequencies: List[float], enabled_channels: List[int],
                                    test_config: Dict[str, Any]) -> bool:
        """执行多频点测试"""
        try:
            # 获取启动策略
            startup_strategy = test_config.get('startup_strategy', 'staggered')
            enabled_channel_indices = [ch - 1 for ch in enabled_channels]  # 转换为索引

            if startup_strategy == 'staggered':
                # 并行错频测试
                return self.parallel_test_manager.execute_parallel_staggered_test(
                    frequencies, enabled_channel_indices, test_config
                )
            else:
                # 传统同时启动测试
                return self.parallel_test_manager.execute_traditional_simultaneous_test(
                    frequencies, enabled_channel_indices, test_config
                )

        except Exception as e:
            logger.error(f"执行多频点测试失败: {e}")
            return False

    # ===== 信号处理方法 =====

    def _on_test_started(self, test_config: Dict[str, Any], enabled_channels: List[int]):
        """测试开始信号处理"""
        logger.info(f"测试开始: 通道{enabled_channels}")

    def _on_test_stopped(self, reason: str):
        """测试停止信号处理"""
        logger.info(f"测试停止: {reason}")

    def _on_cycle_completed(self, cycle_num: int, success: bool, duration: float):
        """测试周期完成信号处理"""
        logger.info(f"第{cycle_num}轮测试完成: {'成功' if success else '失败'}, 耗时{duration:.2f}秒")

    def _on_count_updated(self, count: int):
        """连续测试计数更新信号处理"""
        try:
            logger.info(f"🔄 连续测试计数更新: 第{count}轮")

            # 通过status_callback通知UI更新计数
            if hasattr(self, 'status_callback') and self.status_callback:
                # 获取最大计数限制
                max_count = 0
                if hasattr(self, '_current_test_config'):
                    test_config = self._current_test_config
                    count_limit_enabled = test_config.get('count_limit_enabled', False)
                    if count_limit_enabled:
                        max_count = test_config.get('max_count', 100)

                # 发送计数更新事件
                self.status_callback({
                    'action': 'continuous_test_count_updated',
                    'count': count,
                    'max_count': max_count
                })
                logger.info(f"✅ 连续测试计数更新事件已发送: 第{count}轮")
            else:
                logger.warning("⚠️ status_callback 不存在，无法通知UI更新计数")

        except Exception as e:
            logger.error(f"❌ 处理连续测试计数更新失败: {e}")

    def _on_continuous_test_started(self, test_config: Dict[str, Any]):
        """连续测试开始信号处理"""
        logger.info(f"🔄 连续测试已开始")
        # 保存当前测试配置，供计数更新时使用
        self._current_test_config = test_config

    def _on_continuous_test_stopped(self, reason: str):
        """连续测试停止信号处理"""
        logger.info(f"🛑 连续测试已停止: {reason}")
        # 清除当前测试配置
        if hasattr(self, '_current_test_config'):
            delattr(self, '_current_test_config')

    def _on_statistics_updated(self, statistics: Dict[str, Any]):
        """连续测试统计数据更新信号处理"""
        logger.debug(f"📊 连续测试统计数据更新: {statistics.get('total_cycles', 0)}轮")

    def _on_parallel_test_completed(self, mode: str, success: bool):
        """并行测试完成信号处理"""
        logger.info(f"{mode}并行测试完成: {'成功' if success else '失败'}")

    def _on_results_processed(self, processed_results: Dict[str, Any]):
        """结果处理完成信号处理"""
        logger.info(f"测试结果处理完成: {len(processed_results)}个通道")

    def _on_state_changed(self, old_state: str, new_state: str):
        """状态变更信号处理"""
        logger.debug(f"测试状态变更: {old_state} -> {new_state}")

    def _on_measurement_completed(self, channels: List[int], frequency: float):
        """测量完成信号处理"""
        logger.debug(f"测量完成: 频率{frequency}Hz, 通道{channels}")

    # ===== 兼容性方法 =====

    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback
        # 分发到各个管理器
        self.execution_control_manager.set_progress_callback(callback)
        self.parallel_test_manager.set_progress_callback(callback)
        self.result_processing_manager.set_progress_callback(callback)

    def set_status_callback(self, callback: Callable):
        """设置状态回调函数"""
        self.status_callback = callback
        self.execution_control_manager.set_status_callback(callback)

    def set_stop_event(self, stop_event):
        """设置停止事件"""
        self.execution_control_manager.set_stop_event(stop_event)

    def stop_execution(self):
        """停止执行"""
        self.execution_control_manager.stop_test("用户停止")

    def reset_execution(self):
        """重置执行状态"""
        self.execution_control_manager.reset_execution()
        self.state_manager.reset_state()

    def get_execution_status(self) -> Dict[str, Any]:
        """获取执行状态"""
        return {
            'execution_control': self.execution_control_manager.get_execution_status(),
            'test_state': self.state_manager.get_state_info(),
            'continuous_test': self.continuous_test_manager.get_statistics(),
            'parallel_test': self.parallel_test_manager.get_parallel_test_status(),
            'communication': self.device_communication_manager.get_communication_status()
        }

    def reset_continuous_test_count(self):
        """重置连续测试计数"""
        self.continuous_test_manager.reset_continuous_test_count()

    @property
    def continuous_test_count(self):
        """获取连续测试计数（兼容性属性）"""
        return self.continuous_test_manager.get_continuous_test_count()

    def get_manager(self, manager_name: str):
        """获取指定的管理器"""
        manager_map = {
            'execution_control': self.execution_control_manager,
            'continuous_test': self.continuous_test_manager,
            'parallel_test': self.parallel_test_manager,
            'result_processing': self.result_processing_manager,
            'state': self.state_manager,
            'device_communication': self.device_communication_manager
        }
        return manager_map.get(manager_name)

    def cleanup(self):
        """清理资源"""
        try:
            # 清理各个管理器的资源
            managers = [
                self.execution_control_manager,
                self.continuous_test_manager,
                self.parallel_test_manager,
                self.result_processing_manager,
                self.state_manager,
                self.device_communication_manager
            ]

            for manager in managers:
                if hasattr(manager, 'cleanup'):
                    manager.cleanup()

            logger.info("测试执行器资源清理完成")

        except Exception as e:
            logger.error(f"清理测试执行器资源失败: {e}")
