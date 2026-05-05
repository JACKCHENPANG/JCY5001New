"""
重构后的并行错频测试管理器 - 简化版本
只保留核心接口，具体功能由专门的管理器实现
"""

import time
import logging
from typing import Optional, Callable, List
from enum import Enum

# 导入重构后的管理器
from backend.parallel_test_managers.frequency_classifier import FrequencyClassifier
from backend.parallel_test_managers.staggered_test_executor import StaggeredTestExecutor
from backend.parallel_test_managers.simultaneous_test_executor import SimultaneousTestExecutor
from backend.parallel_test_managers.test_data_collector import TestDataCollector
from backend.parallel_test_managers.test_progress_tracker import TestProgressTracker
from backend.parallel_test_managers.test_error_recovery import TestErrorRecovery

logger = logging.getLogger(__name__)


class ParallelStaggeredTestState(Enum):
    """并行错频测试状态"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    CLASSIFYING_FREQUENCIES = "classifying_frequencies"
    STARTING_STAGGERED_MEASUREMENT = "starting_staggered_measurement"
    STAGGERED_MEASUREMENT = "staggered_measurement"
    STARTING_SIMULTANEOUS_MEASUREMENT = "starting_simultaneous_measurement"
    SIMULTANEOUS_MEASUREMENT = "simultaneous_measurement"
    COLLECTING_DATA = "collecting_data"
    COMPLETED = "completed"
    ERROR = "error"
    STOPPED = "stopped"


class ParallelStaggeredTestConfig:
    """并行错频测试配置"""
    def __init__(self):
        self.enabled_channels = []
        self.frequencies = []
        self.critical_frequency = 100.0
        self.timeout_seconds = 30.0
        self.status_check_interval = 0.1


class ParallelStaggeredTestManagerSimplified:
    """
    重构后的并行错频测试管理器 - 简化版本
    
    这个版本只保留核心接口，具体功能由6个专门的管理器实现：
    1. FrequencyClassifier - 频率分类
    2. StaggeredTestExecutor - 错频测试执行
    3. SimultaneousTestExecutor - 同时测试执行
    4. TestDataCollector - 数据收集
    5. TestProgressTracker - 进度跟踪
    6. TestErrorRecovery - 错误恢复
    """

    def __init__(self, comm_manager, impedance_data_manager=None):
        """初始化重构后的并行错频测试管理器"""
        self.comm_manager = comm_manager
        self.impedance_data_manager = impedance_data_manager

        # 测试状态
        self.state = ParallelStaggeredTestState.IDLE
        self.config: Optional[ParallelStaggeredTestConfig] = None
        self.start_time = 0.0

        # 修复添加停止事件
        import threading
        self.stop_event = threading.Event()

        # 修复：添加停止操作锁，防止递归调用
        self._stop_in_progress = False
        self._stop_lock = threading.Lock()

        # 初始化重构后的6个管理器
        self._initialize_refactored_managers()

        # 回调函数（保持向后兼容）
        self.status_callback: Optional[Callable] = None
        self.progress_callback: Optional[Callable] = None
        self.channel_progress_callback: Optional[Callable] = None

        # 🧹 初始化测试状态清理器
        try:
            from .test_state_cleaner import TestStateCleaner
            self.state_cleaner = TestStateCleaner()
        except ImportError:
            logger.warning("测试状态清理器模块未找到，跳过初始化")
            self.state_cleaner = None

        logger.debug("重构后的并行错频测试管理器初始化完成")

    def set_channel_progress_callback(self, callback: Callable):
        """设置通道进度回调函数"""
        self.channel_progress_callback = callback

        # 将回调函数传递给子执行器（安全检查）
        try:
            if hasattr(self, 'staggered_executor') and self.staggered_executor:
                if hasattr(self.staggered_executor, 'set_channel_progress_callback'):
                    self.staggered_executor.set_channel_progress_callback(callback)
            if hasattr(self, 'simultaneous_executor') and self.simultaneous_executor:
                if hasattr(self.simultaneous_executor, 'channel_progress_callback'):
                    self.simultaneous_executor.channel_progress_callback = callback

            logger.debug("通道进度回调函数已设置并传递给子执行器")
        except Exception as e:
            logger.error(f"传递回调函数到子执行器失败: {e}")

    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback
        logger.debug("进度回调函数已设置")

    def set_status_callback(self, callback: Callable):
        """设置状态回调函数"""
        self.status_callback = callback
        logger.debug("状态回调函数已设置")

    def _initialize_refactored_managers(self):
        """初始化重构后的6个专门管理器"""
        try:
            # 1. 频率分类器
            self.frequency_classifier = FrequencyClassifier()

            # 2. 错频测试执行器（传递停止事件）
            self.staggered_executor = StaggeredTestExecutor(
                self.comm_manager,
                self.frequency_classifier,
                self.stop_event
            )

            # 3. 同时测试执行器（传递停止事件）
            self.simultaneous_executor = SimultaneousTestExecutor(
                self.comm_manager,
                self.frequency_classifier,
                self.stop_event
            )

            # 4. 数据收集器（传递阻抗数据管理器实例以避免重复创建）
            # 修复传递主线程的阻抗数据管理器实例，避免创建新实例导致设置丢失
            self.data_collector = TestDataCollector(
                db_manager=None,  # 让它自动创建数据库管理器
                impedance_data_manager=self.impedance_data_manager  # 传递主实例
            )

            # 5. 进度跟踪器
            self.progress_tracker = TestProgressTracker()

            # 6. 错误恢复器
            self.error_recovery = TestErrorRecovery(self.comm_manager)

            # 设置回调函数（如果已经设置了的话）
            self._setup_callbacks()

            logger.debug("✅ 重构后的6个管理器初始化完成")

        except Exception as e:
            logger.error(f"❌ 初始化重构后的管理器失败: {e}")
            raise

    def _setup_callbacks(self):
        """设置回调函数到子管理器"""
        try:
            # 将通道进度回调传递给执行器（安全检查）
            if self.channel_progress_callback:
                # 检查staggered_executor
                if hasattr(self, 'staggered_executor') and self.staggered_executor:
                    if hasattr(self.staggered_executor, 'set_channel_progress_callback'):
                        self.staggered_executor.set_channel_progress_callback(self.channel_progress_callback)
                    else:
                        logger.debug("staggered_executor没有set_channel_progress_callback方法")

                # 检查simultaneous_executor
                if hasattr(self, 'simultaneous_executor') and self.simultaneous_executor:
                    if hasattr(self.simultaneous_executor, 'channel_progress_callback'):
                        self.simultaneous_executor.channel_progress_callback = self.channel_progress_callback
                    else:
                        logger.debug("simultaneous_executor没有channel_progress_callback属性")

            logger.debug("回调函数已设置到子管理器")
        except Exception as e:
            logger.debug(f"设置回调函数失败: {e}")  # 降级为debug，减少错误日志

    def _set_state(self, new_state: ParallelStaggeredTestState):
        """设置测试状态"""
        try:
            old_state = self.state
            self.state = new_state
            logger.debug(f"状态变更: {old_state.value} -> {new_state.value}")
            
            # 通知状态回调
            if self.status_callback:
                try:
                    self.status_callback({
                        'state': new_state.value,
                        'old_state': old_state.value,
                        'timestamp': time.time()
                    })
                except Exception as e:
                    logger.error(f"状态回调失败: {e}")
                    
        except Exception as e:
            logger.error(f"设置状态失败: {e}")

    def start_test(self, config: ParallelStaggeredTestConfig) -> bool:
        """
        启动重构后的并行错频测试
        
        Args:
            config: 测试配置
            
        Returns:
            是否启动成功
        """
        try:
            # 1. 验证配置
            if not config or not config.enabled_channels or not config.frequencies:
                logger.error("❌ 测试配置无效")
                return False
            
            print(f"🚀 [并行错频管理器] 启动测试: {len(config.enabled_channels)}个通道, "
                  f"{len(config.frequencies)}个频点, 临界频点: {config.critical_frequency}Hz")
            logger.info(f"🚀 启动并行错频测试: {len(config.enabled_channels)}个通道, "
                       f"{len(config.frequencies)}个频点, 临界频点: {config.critical_frequency}Hz")

            # 保存配置
            self.config = config

            # 修复正确设置测试开始时间（只设置一次）
            self.start_time = time.time()

            # 修复清除停止事件，准备新的测试
            self.stop_event.clear()

            # 🧹 新增：全面清理测试状态，确保干净的测试环境
            self._clean_test_environment()

            # 清空重构后的管理器数据
            self.data_collector.clear_all_data()
            self.error_recovery.reset()
            
            # 检查设备连接（如果通信管理器支持连接检查）
            if hasattr(self.comm_manager, 'is_connected') and not self.comm_manager.is_connected:
                print(f"⚠️⚠️⚠️ [并行错频管理器] 设备未连接，尝试自动连接...")
                logger.warning("设备未连接，尝试自动连接...")

                # 尝试自动连接
                try:
                    if hasattr(self.comm_manager, 'connect') and callable(self.comm_manager.connect):
                        if not self.comm_manager.connect():
                            logger.error("❌ 自动连接失败")
                            return False
                        logger.info("✅ 自动连接成功")
                except Exception as e:
                    logger.error(f"❌ 自动连接异常: {e}")
                    return False

            # 2. 使用重构后的频率分类器
            self._set_state(ParallelStaggeredTestState.CLASSIFYING_FREQUENCIES)
            high_frequencies, low_frequencies = self.frequency_classifier.classify_frequencies(
                config.frequencies, config.critical_frequency
            )
            
            # 3. 使用重构后的错频测试执行器测试高频点
            if high_frequencies:
                staggered_success, failed_frequencies = self.staggered_executor.execute_high_frequency_test(
                    config.enabled_channels, config
                )
                if staggered_success:
                    staggered_results = self.staggered_executor.get_test_results()
                    self.data_collector.collect_staggered_results(staggered_results)

                # 如果有失败频点，通知UI并停止全部测试
                if failed_frequencies:
                    logger.error(f"❌ 高频点测试失败，失败频点: {failed_frequencies}Hz")
                    # 通过状态回调通知UI频点错误
                    if self.channel_progress_callback:
                        for channel_index in config.enabled_channels:
                            channel_num = channel_index + 1
                            try:
                                self.channel_progress_callback(channel_num, {
                                    'state': 'frequency_error',
                                    'progress': 0,
                                    'message': f'不合格-频点出错: {", ".join([f"{f}Hz" for f in failed_frequencies])}',
                                    'failed_frequencies': failed_frequencies,
                                    'error_type': 'frequency_error'
                                })
                                logger.info(f"通道{channel_num}已通知频点错误: {failed_frequencies}Hz")
                            except Exception as e:
                                logger.error(f"通道{channel_num}频点错误通知失败: {e}")

                    # 继续执行低频点测试
                    logger.warning(f"⚠️ 高频点测试有失败频点: {failed_frequencies}Hz，继续执行低频点测试")

            # 4. 使用重构后的同时测试执行器测试低频点
            if low_frequencies:
                simultaneous_success, low_failed_frequencies = self.simultaneous_executor.execute_low_frequency_test(
                    config.enabled_channels, config
                )
                if simultaneous_success:
                    simultaneous_results = self.simultaneous_executor.get_test_results()
                    self.data_collector.collect_simultaneous_results(simultaneous_results)

                # 如果有失败频点，通知UI
                if low_failed_frequencies:
                    logger.error(f"❌ 低频点测试失败，失败频点: {low_failed_frequencies}Hz")
                    # 通过状态回调通知UI频点错误
                    if self.channel_progress_callback:
                        for channel_index in config.enabled_channels:
                            channel_num = channel_index + 1
                            try:
                                self.channel_progress_callback(channel_num, {
                                    'state': 'frequency_error',
                                    'progress': 0,
                                    'message': f'不合格-频点出错: {", ".join([f"{f}Hz" for f in low_failed_frequencies])}',
                                    'failed_frequencies': low_failed_frequencies,
                                    'error_type': 'frequency_error'
                                })
                                logger.info(f"通道{channel_num}已通知频点错误: {low_failed_frequencies}Hz")
                            except Exception as e:
                                logger.error(f"通道{channel_num}频点错误通知失败: {e}")

                    # 记录低频测试失败，但继续执行后续步骤（合并结果等）
                    logger.warning(f"⚠️ 低频点测试有失败频点，但继续执行结果合并")

            # 检查全局超时（120秒），超时直接标记完成
            total_elapsed = time.time() - self.start_time
            if total_elapsed > 120:
                logger.warning(f"测试全局超时({total_elapsed:.1f}s>120s)，强制完成")

            # 5. 合并所有测试结果
            self.data_collector.combine_all_results(config.enabled_channels)

            # 关键修复在测试完成时发送最终的completed状态给所有通道
            self._notify_test_completion(config.enabled_channels)

            # 所有频点测试完成
            self._set_state(ParallelStaggeredTestState.COMPLETED)

            # 修复确保时间计算正确
            if self.start_time > 0:
                elapsed_time = time.time() - self.start_time
                if elapsed_time < 0 or elapsed_time > 3600:  # 如果时间异常（负数或超过1小时）
                    elapsed_time = 0.0
                    logger.warning("测试时间计算异常，重置为0")
            else:
                # 如果start_time为0，尝试重新设置为当前时间减去一个合理的默认值
                elapsed_time = 0.0
                logger.debug("测试开始时间未设置，使用默认耗时0秒")

            print(f"✅✅✅ [并行错频管理器] 测试完成，总耗时: {elapsed_time:.3f}秒")
            logger.info(f"✅ 并行错频测试完成，总耗时: {elapsed_time:.3f}秒")

            return True
            
        except Exception as e:
            logger.error(f"执行重构后的并行错频测试失败: {e}")
            self._set_state(ParallelStaggeredTestState.ERROR)
            return False

    def _notify_test_completion(self, enabled_channels: List[int]):
        """
        通知测试完成，发送最终的completed状态给所有通道

        Args:
            enabled_channels: 启用的通道列表
        """
        try:
            if self.channel_progress_callback:
                logger.debug(f" [并行错频管理器] 发送最终测试完成状态给所有通道")

                for channel_index in enabled_channels:
                    channel_num = channel_index + 1

                    # 发送最终的completed状态
                    progress_data = {
                        'state': 'completed',
                        'progress': 100,
                        'message': '测试完成',
                        'frequency': None,
                        'frequency_index': len(self.config.frequencies),
                        'total_frequencies': len(self.config.frequencies),
                        'mode': 'test_completed',  # 标识为最终测试完成
                        'completed_frequency': None
                    }

                    # 调用通道进度回调
                    self.channel_progress_callback(channel_num, progress_data)

                    logger.debug(f" [并行错频管理器] 通道{channel_num}测试完成，发送completed状态")

        except Exception as e:
            logger.error(f"通知测试完成失败: {e}")

    def stop_test(self):
        """停止测试（增强版）"""
        # 修复：使用线程锁防止重复执行
        with self._stop_lock:
            if self._stop_in_progress:
                logger.warning("🛑 并行错频测试管理器停止操作已在进行中，跳过重复调用")
                return

            self._stop_in_progress = True

        try:

            logger.info("🛑 [增强版] 并行错频测试管理器开始停止...")

            # 1. 立即设置停止标志
            self._set_state(ParallelStaggeredTestState.STOPPED)
            self.stop_event.set()
            
            # 2. 立即停止设备测试
            self._enhanced_stop_device_immediately()
            
            # 3. 停止所有子执行器
            self._enhanced_stop_all_executors()
            
            # 4. 清理状态
            self._enhanced_cleanup_state()
            
            logger.info("✅ [增强版] 并行错频测试管理器停止完成")

        except Exception as e:
            logger.error(f"❌ [增强版] 并行错频测试管理器停止失败: {e}")
        finally:
            # 修复：确保停止标志被重置
            with self._stop_lock:
                self._stop_in_progress = False
    
    def _enhanced_stop_device_immediately(self):
        """增强的立即停止设备"""
        try:
            if hasattr(self, 'comm_manager') and self.comm_manager:
                # 停止所有通道
                all_channels = list(range(8))
                self.comm_manager.stop_impedance_measurement(all_channels)
                logger.info("✅ 设备测试已强制停止")
        except Exception as e:
            logger.error(f"强制停止设备失败: {e}")
    
    def _enhanced_stop_all_executors(self):
        """增强的停止所有执行器"""
        try:
            # 停止错频测试执行器
            if hasattr(self, 'staggered_executor') and self.staggered_executor:
                try:
                    if hasattr(self.staggered_executor, 'stop_event') and self.staggered_executor.stop_event:
                        self.staggered_executor.stop_event.set()
                    logger.info("✅ 错频测试执行器已停止")
                except Exception as e:
                    logger.error(f"停止错频测试执行器失败: {e}")

            # 停止同时测试执行器
            if hasattr(self, 'simultaneous_executor') and self.simultaneous_executor:
                try:
                    if hasattr(self.simultaneous_executor, 'stop_event') and self.simultaneous_executor.stop_event:
                        self.simultaneous_executor.stop_event.set()
                    logger.info("✅ 同时测试执行器已停止")
                except Exception as e:
                    logger.error(f"停止同时测试执行器失败: {e}")
        except Exception as e:
            logger.error(f"停止所有执行器失败: {e}")
    
    def _enhanced_cleanup_state(self):
        """增强的状态清理"""
        try:
            # 重置所有状态
            self._set_state(ParallelStaggeredTestState.IDLE)
            if hasattr(self, 'current_round'):
                self.current_round = 0
            # 安全地清理测试结果
            try:
                test_results = getattr(self, 'test_results', None)
                if test_results is not None and hasattr(test_results, 'clear'):
                    test_results.clear()
            except Exception as e:
                logger.debug(f"清理测试结果时出错: {e}")
            logger.info("✅ 状态清理完成")
        except Exception as e:
            logger.error(f"状态清理失败: {e}")
    def get_test_results(self):
        """获取测试结果"""
        try:
            if self.data_collector:
                # 获取原始数据
                raw_data = self.data_collector.export_to_dict()

                # 转换为TestExecutor期望的格式: {frequency: {channel_index: data}}
                combined_results = {}

                # 合并错频测试结果
                staggered_results = raw_data.get('staggered_results', {})
                for frequency, channels_data in staggered_results.items():
                    if frequency not in combined_results:
                        combined_results[frequency] = {}
                    combined_results[frequency].update(channels_data)

                # 合并同时测试结果
                simultaneous_results = raw_data.get('simultaneous_results', {})
                for frequency, channels_data in simultaneous_results.items():
                    if frequency not in combined_results:
                        combined_results[frequency] = {}
                    combined_results[frequency].update(channels_data)

                # 合并组合结果
                combined_data = raw_data.get('combined_results', {})
                for channel_index, channel_frequencies in combined_data.items():
                    for frequency, data in channel_frequencies.items():
                        if frequency not in combined_results:
                            combined_results[frequency] = {}
                        combined_results[frequency][channel_index] = data

                logger.info(f"测试结果格式转换完成: {len(combined_results)}个频点")
                return combined_results
            return {}
        except Exception as e:
            logger.error(f"获取测试结果失败: {e}")
            return {}

    def get_test_state(self) -> ParallelStaggeredTestState:
        """获取当前测试状态"""
        return self.state

    def is_testing(self) -> bool:
        """是否正在测试"""
        return self.state not in [
            ParallelStaggeredTestState.IDLE,
            ParallelStaggeredTestState.COMPLETED,
            ParallelStaggeredTestState.ERROR,
            ParallelStaggeredTestState.STOPPED
        ]

    def _clean_test_environment(self):
        """清理测试环境，确保干净的测试状态"""
        try:
            logger.debug("🧹 并行错频测试管理器开始清理测试环境...")

            # 清理内部状态
            self.start_time = 0.0

            # 清理数据收集器
            if hasattr(self, 'data_collector') and self.data_collector:
                self.data_collector.clear_all_data()

            # 重置进度跟踪器
            if hasattr(self, 'progress_tracker') and self.progress_tracker:
                if hasattr(self.progress_tracker, 'reset'):
                    self.progress_tracker.reset()

            # 重置错误恢复器
            if hasattr(self, 'error_recovery') and self.error_recovery:
                self.error_recovery.reset()

            logger.debug("✅ 并行错频测试管理器测试环境清理完成")

        except Exception as e:
            logger.error(f"❌ 并行错频测试管理器清理测试环境失败: {e}")

    def clean_channel_states(self, channel_widgets: list):
        """清理通道状态（供外部调用）"""
        try:
            if hasattr(self, 'state_cleaner') and self.state_cleaner:
                return self.state_cleaner.clean_all_test_states(channel_widgets)
            else:
                logger.warning("状态清理器未初始化，跳过通道状态清理")
                return False

        except Exception as e:
            logger.error(f"清理通道状态失败: {e}")
            return False
