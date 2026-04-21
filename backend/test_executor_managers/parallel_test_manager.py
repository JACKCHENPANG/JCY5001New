# -*- coding: utf-8 -*-
"""
并行测试管理器
负责并行测试的协调、错频启动、同时启动等功能

Author: Jack
Date: 2025-06-27
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ParallelTestManager(QObject):
    """并行测试管理器"""
    
    # 信号定义
    parallel_test_started = pyqtSignal(str, list)  # 并行测试开始信号 (mode, channels)
    parallel_test_completed = pyqtSignal(str, bool)  # 并行测试完成信号 (mode, success)
    channel_coordination_updated = pyqtSignal(dict)  # 通道协调更新信号 (coordination_info)
    
    def __init__(self, comm_manager, device_config_manager, test_executor=None, parent=None):
        """
        初始化并行测试管理器

        Args:
            comm_manager: 通信管理器
            device_config_manager: 设备配置管理器
            test_executor: 测试执行器（用于访问锁定电压）
            parent: 父对象
        """
        super().__init__(parent)

        self.comm_manager = comm_manager
        self.device_config_manager = device_config_manager
        self.test_executor = test_executor  # 新增测试执行器引用

        # 并行测试状态
        self.active_staggered_manager = None
        self.active_simultaneous_manager = None

        # 回调函数
        self.progress_callback = None
        
    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback

    def execute_parallel_staggered_test(self, frequencies: List[float], enabled_channel_indices: List[int],
                                      test_config: Dict[str, Any]) -> bool:
        """
        执行并行错频测试
        
        Args:
            frequencies: 频率列表
            enabled_channel_indices: 启用的通道索引列表
            test_config: 测试配置
            
        Returns:
            是否执行成功
        """
        try:
            logger.info(f"🔀 开始并行错频测试，频率: {frequencies}, 通道: {enabled_channel_indices}")
            
            # 发送并行测试开始信号
            self.parallel_test_started.emit("staggered", enabled_channel_indices)
            
            # 导入并行错频测试管理器
            from backend.parallel_staggered_test_manager import ParallelStaggeredTestManager
            
            # 创建错频测试管理器
            staggered_manager = ParallelStaggeredTestManager(
                comm_manager=self.comm_manager,
                device_config_manager=self.device_config_manager
            )
            
            # 设置为活跃管理器
            self.active_staggered_manager = staggered_manager
            
            # 设置进度回调
            def staggered_progress_callback(progress_info):
                # 整体进度回调
                pass

            def channel_progress_callback(channel_num, progress_data):
                if self.progress_callback:
                    # 修复使用锁定的测试前电压，而不是实时电压
                    enhanced_progress_data = progress_data.copy()

                    # 优先使用锁定的测试前电压
                    locked_voltage = None
                    if self.test_executor and hasattr(self.test_executor, 'pre_test_voltages'):
                        locked_voltage = self.test_executor.pre_test_voltages.get(channel_num)

                    if locked_voltage is not None:
                        # 使用锁定的测试前电压
                        enhanced_progress_data['voltage'] = locked_voltage
                        enhanced_progress_data['voltage_locked'] = True
                        logger.debug(f"通道{channel_num}并行错频测试使用锁定电压: {locked_voltage:.3f}V")
                    elif 'voltage' not in enhanced_progress_data or enhanced_progress_data['voltage'] == 0:
                        # 如果没有锁定电压且进度数据中没有电压信息，尝试从设备获取
                        try:
                            current_voltage = self.device_config_manager.get_channel_voltage(channel_num)
                            if current_voltage > 0:
                                enhanced_progress_data['voltage'] = current_voltage
                                enhanced_progress_data['voltage_locked'] = False
                                logger.debug(f"通道{channel_num}并行错频测试使用实时电压: {current_voltage:.3f}V")
                        except Exception as e:
                            logger.debug(f"获取通道{channel_num}电压失败: {e}")

                    self.progress_callback(channel_num, enhanced_progress_data)

            staggered_manager.set_progress_callback(staggered_progress_callback)
            staggered_manager.set_channel_progress_callback(channel_progress_callback)
            
            # 执行错频测试
            success = staggered_manager.execute_staggered_test(frequencies, enabled_channel_indices, test_config)
            
            # 清除活跃管理器引用
            self.active_staggered_manager = None
            
            # 发送并行测试完成信号
            self.parallel_test_completed.emit("staggered", success)
            
            if success:
                logger.info("✅ 并行错频测试完成")
            else:
                logger.warning("⚠️ 并行错频测试失败")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 并行错频测试失败: {e}")
            self.active_staggered_manager = None
            self.parallel_test_completed.emit("staggered", False)
            return False

    def execute_traditional_simultaneous_test(self, frequencies: List[float], enabled_channel_indices: List[int],
                                            test_config: Dict[str, Any]) -> bool:
        """
        执行传统同时启动测试
        
        Args:
            frequencies: 频率列表
            enabled_channel_indices: 启用的通道索引列表
            test_config: 测试配置
            
        Returns:
            是否执行成功
        """
        try:
            logger.info(f"⚡ 开始传统同时启动测试，频率: {frequencies}, 通道: {enabled_channel_indices}")
            
            # 发送并行测试开始信号
            self.parallel_test_started.emit("simultaneous", enabled_channel_indices)
            
            # 导入同时启动测试管理器
            from backend.traditional_simultaneous_test_manager import TraditionalSimultaneousTestManager
            
            # 创建同时启动测试管理器
            simultaneous_manager = TraditionalSimultaneousTestManager(
                comm_manager=self.comm_manager,
                device_config_manager=self.device_config_manager
            )
            
            # 设置为活跃管理器
            self.active_simultaneous_manager = simultaneous_manager
            
            # 设置进度回调
            if self.progress_callback:
                simultaneous_manager.set_progress_callback(self.progress_callback)
            
            # 执行同时启动测试
            success = simultaneous_manager.execute_simultaneous_test(frequencies, enabled_channel_indices, test_config)
            
            # 清除活跃管理器引用
            self.active_simultaneous_manager = None
            
            # 发送并行测试完成信号
            self.parallel_test_completed.emit("simultaneous", success)
            
            if success:
                logger.info("✅ 传统同时启动测试完成")
            else:
                logger.warning("⚠️ 传统同时启动测试失败")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 传统同时启动测试失败: {e}")
            self.active_simultaneous_manager = None
            self.parallel_test_completed.emit("simultaneous", False)
            return False

    def stop_active_parallel_tests(self):
        """停止活跃的并行测试"""
        try:
            logger.info("🛑 停止活跃的并行测试")
            
            # 停止错频测试管理器
            if self.active_staggered_manager:
                try:
                    if hasattr(self.active_staggered_manager, 'stop'):
                        self.active_staggered_manager.stop()
                        logger.debug("错频测试管理器已停止")
                except Exception as e:
                    logger.error(f"停止错频测试管理器失败: {e}")
                finally:
                    self.active_staggered_manager = None
            
            # 停止同时测试管理器
            if self.active_simultaneous_manager:
                try:
                    if hasattr(self.active_simultaneous_manager, 'stop'):
                        self.active_simultaneous_manager.stop()
                        logger.debug("同时测试管理器已停止")
                except Exception as e:
                    logger.error(f"停止同时测试管理器失败: {e}")
                finally:
                    self.active_simultaneous_manager = None
            
            logger.info("✅ 活跃的并行测试已停止")
            
        except Exception as e:
            logger.error(f"❌ 停止活跃并行测试失败: {e}")

    def get_parallel_test_status(self) -> Dict[str, Any]:
        """
        获取并行测试状态
        
        Returns:
            并行测试状态字典
        """
        try:
            status = {
                'has_active_staggered': self.active_staggered_manager is not None,
                'has_active_simultaneous': self.active_simultaneous_manager is not None,
                'staggered_manager_type': type(self.active_staggered_manager).__name__ if self.active_staggered_manager else None,
                'simultaneous_manager_type': type(self.active_simultaneous_manager).__name__ if self.active_simultaneous_manager else None,
                'timestamp': time.time()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"获取并行测试状态失败: {e}")
            return {}

    def coordinate_channel_execution(self, channel_indices: List[int], coordination_strategy: str = "staggered") -> Dict[str, Any]:
        """
        协调通道执行
        
        Args:
            channel_indices: 通道索引列表
            coordination_strategy: 协调策略 ("staggered" 或 "simultaneous")
            
        Returns:
            协调信息字典
        """
        try:
            logger.debug(f"协调通道执行: {channel_indices}, 策略: {coordination_strategy}")
            
            coordination_info = {
                'strategy': coordination_strategy,
                'channel_indices': channel_indices,
                'channel_count': len(channel_indices),
                'coordination_time': time.time()
            }
            
            if coordination_strategy == "staggered":
                # 错频协调：计算启动间隔
                stagger_interval = 0.5  # 500ms间隔
                coordination_info['stagger_interval'] = stagger_interval
                coordination_info['total_stagger_time'] = stagger_interval * (len(channel_indices) - 1)
                
                # 计算每个通道的启动时间
                start_times = {}
                for i, channel_idx in enumerate(channel_indices):
                    start_times[channel_idx] = i * stagger_interval
                coordination_info['start_times'] = start_times
                
            elif coordination_strategy == "simultaneous":
                # 同时协调：所有通道同时启动
                coordination_info['simultaneous_start'] = True
                start_times = {channel_idx: 0.0 for channel_idx in channel_indices}
                coordination_info['start_times'] = start_times
            
            # 发送协调更新信号
            self.channel_coordination_updated.emit(coordination_info)
            
            return coordination_info
            
        except Exception as e:
            logger.error(f"协调通道执行失败: {e}")
            return {}

    def validate_parallel_test_config(self, test_config: Dict[str, Any], enabled_channels: List[int]) -> bool:
        """
        验证并行测试配置
        
        Args:
            test_config: 测试配置
            enabled_channels: 启用的通道列表
            
        Returns:
            配置是否有效
        """
        try:
            # 检查通道数量
            if len(enabled_channels) < 2:
                logger.warning("并行测试需要至少2个通道")
                return False
            
            # 检查频率配置
            frequencies = test_config.get('frequencies', [])
            if not frequencies:
                logger.error("并行测试需要频率配置")
                return False
            
            # 检查启动策略
            startup_strategy = test_config.get('startup_strategy', 'staggered')
            if startup_strategy not in ['staggered', 'simultaneous']:
                logger.error(f"无效的启动策略: {startup_strategy}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证并行测试配置失败: {e}")
            return False

    def get_active_managers(self) -> Dict[str, Any]:
        """获取活跃的管理器"""
        return {
            'staggered_manager': self.active_staggered_manager,
            'simultaneous_manager': self.active_simultaneous_manager
        }

    def set_active_staggered_manager(self, manager):
        """设置活跃的错频测试管理器"""
        self.active_staggered_manager = manager
        logger.debug("活跃错频测试管理器已设置")

    def set_active_simultaneous_manager(self, manager):
        """设置活跃的同时测试管理器"""
        self.active_simultaneous_manager = manager
        logger.debug("活跃同时测试管理器已设置")

    def cleanup(self):
        """清理资源"""
        try:
            # 停止所有活跃的并行测试
            self.stop_active_parallel_tests()
            
            # 清除回调
            self.progress_callback = None
            
            logger.debug("并行测试管理器资源已清理")
            
        except Exception as e:
            logger.error(f"清理并行测试管理器资源失败: {e}")
