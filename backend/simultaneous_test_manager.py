# -*- coding: utf-8 -*-
"""
同时测试模式管理器
负责电池阻抗测试的同时测试模式功能，实现批量通信协议操作

Author: Jack
Date: 2025-05-31
"""

import logging
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SimultaneousTestState(Enum):
    """同时测试状态"""
    IDLE = "idle"
    SETTING_FREQUENCY = "setting_frequency"
    STARTING_MEASUREMENT = "starting_measurement"
    MONITORING = "monitoring"
    READING_DATA = "reading_data"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SimultaneousTestConfig:
    """同时测试配置"""
    enabled_channels: List[int]  # 启用的通道列表（0-7）
    frequencies: List[float]  # 测试频率列表
    timeout_seconds: int = 60  # 测试超时时间
    status_check_interval: float = 0.1  # 状态检查间隔（秒）- 优化：从0.5秒减少到0.1秒
    max_retries: int = 3  # 最大重试次数
    error_recovery: bool = True  # 是否启用错误恢复


class SimultaneousTestManager:
    """
    同时测试模式管理器
    
    职责：
    - 协调批量通信协议操作
    - 管理同时测试流程
    - 监控测试状态和进度
    - 处理错误和异常恢复
    """
    
    def __init__(self, communication_manager):
        """
        初始化同时测试模式管理器
        
        Args:
            communication_manager: 通信管理器实例
        """
        self.comm_manager = communication_manager
        
        # 测试状态
        self.state = SimultaneousTestState.IDLE
        self.config: Optional[SimultaneousTestConfig] = None
        self.current_frequency_index = 0
        self.start_time = 0
        
        # 进度回调
        self.progress_callback: Optional[Callable] = None
        self.status_callback: Optional[Callable] = None
        self.channel_progress_callback: Optional[Callable] = None
        
        # 测试结果
        self.test_results = {}
        self.error_info = {}

        # 状态码管理器（修复0003H状态处理）
        from .device_status_manager import DeviceStatusManager
        self.status_manager = DeviceStatusManager()

        # 🧹 初始化测试状态清理器
        from .test_state_cleaner import TestStateCleaner
        self.state_cleaner = TestStateCleaner()

        logger.debug("同时测试模式管理器初始化完成")
    
    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def set_status_callback(self, callback: Callable):
        """设置状态回调函数"""
        self.status_callback = callback

    def set_channel_progress_callback(self, callback: Callable):
        """设置通道级进度回调函数"""
        self.channel_progress_callback = callback
    
    def start_simultaneous_test(self, config: SimultaneousTestConfig) -> bool:
        """
        启动同时测试
        
        Args:
            config: 同时测试配置
            
        Returns:
            是否启动成功
        """
        try:
            if self.state != SimultaneousTestState.IDLE:
                logger.warning("同时测试已在进行中")
                return False
            
            logger.info(f"🚀 启动同时测试: {len(config.enabled_channels)}个通道, {len(config.frequencies)}个频点")
            
            # 🧹 新增：全面清理测试状态，确保干净的测试环境
            self._clean_test_environment()

            # 保存配置
            self.config = config
            self.current_frequency_index = 0
            self.start_time = time.time()
            self.test_results.clear()
            self.error_info.clear()
            
            # 检查设备连接
            if not self.comm_manager.is_connected:
                logger.error("设备未连接，无法启动同时测试")
                self._set_state(SimultaneousTestState.ERROR)
                return False
            
            # 开始测试流程
            return self._execute_test_sequence()
            
        except Exception as e:
            logger.error(f"启动同时测试失败: {e}")
            self._set_state(SimultaneousTestState.ERROR)
            return False
    
    def stop_simultaneous_test(self) -> bool:
        """
        停止同时测试

        Returns:
            是否停止成功
        """
        try:
            logger.info("🛑 同时测试管理器开始停止测试...")

            # 修复1立即停止设备测试
            if hasattr(self, 'comm_manager') and self.comm_manager:
                logger.info("🛑 正在停止设备测试...")
                # 停止所有通道的测试
                all_channels = list(range(8))  # 0-7对应通道1-8
                stop_success = self.comm_manager.stop_impedance_measurement(all_channels)
                if stop_success:
                    logger.info("✅ 设备测试已成功停止")
                else:
                    logger.warning("⚠️ 设备测试停止失败，但软件停止信号已发送")
            else:
                logger.warning("⚠️ 通信管理器不可用，仅发送软件停止信号")

            # 修复2重置状态
            self._set_state(SimultaneousTestState.IDLE)
            self.config = None
            self.current_frequency_index = 0

            logger.info("✅ 同时测试管理器停止测试完成")
            return True

        except Exception as e:
            logger.error(f"❌ 停止同时测试失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    def get_test_progress(self) -> Dict[str, Any]:
        """
        获取测试进度信息
        
        Returns:
            进度信息字典
        """
        if not self.config:
            return {}
        
        total_frequencies = len(self.config.frequencies)
        current_progress = (self.current_frequency_index / total_frequencies) * 100 if total_frequencies > 0 else 0
        
        elapsed_time = time.time() - self.start_time if self.start_time > 0 else 0
        
        return {
            'state': self.state.value,
            'current_frequency_index': self.current_frequency_index,
            'total_frequencies': total_frequencies,
            'progress_percentage': current_progress,
            'elapsed_time': elapsed_time,
            'enabled_channels': self.config.enabled_channels,
            'current_frequency': self.config.frequencies[self.current_frequency_index] if self.current_frequency_index < total_frequencies else None
        }
    
    def get_test_results(self) -> Dict[str, Any]:
        """
        获取测试结果
        
        Returns:
            测试结果字典
        """
        return {
            'results': self.test_results.copy(),
            'errors': self.error_info.copy(),
            'state': self.state.value,
            'config': self.config.__dict__ if self.config else {}
        }
    
    def _execute_test_sequence(self) -> bool:
        """
        执行测试序列
        
        Returns:
            是否执行成功
        """
        try:
            if not self.config:
                return False
            
            # 遍历所有频率点
            for freq_index, frequency in enumerate(self.config.frequencies):
                self.current_frequency_index = freq_index
                
                
                # 执行单个频点的测试
                if not self._test_single_frequency(frequency):
                    if self.config.error_recovery:
                        logger.warning(f"频点{frequency}Hz测试失败，尝试恢复")
                        if not self._recover_from_error():
                            logger.error("错误恢复失败，停止测试")
                            self._set_state(SimultaneousTestState.ERROR)
                            return False
                    else:
                        logger.error(f"频点{frequency}Hz测试失败，停止测试")
                        self._set_state(SimultaneousTestState.ERROR)
                        return False
                
                # 通知进度
                self._notify_progress()
            
            # 所有频点测试完成
            self._set_state(SimultaneousTestState.COMPLETED)
            logger.info("✅ 同时测试完成")
            return True
            
        except Exception as e:
            logger.error(f"执行测试序列失败: {e}")
            self._set_state(SimultaneousTestState.ERROR)
            return False
    
    def _test_single_frequency(self, frequency: float) -> bool:
        """
        测试单个频率点
        
        Args:
            frequency: 测试频率
            
        Returns:
            是否测试成功
        """
        try:
            # 1. 群发设置频点
            self._set_state(SimultaneousTestState.SETTING_FREQUENCY)
            logger.debug(f"🔄 设置频点: {frequency}Hz")
            
            if not self.comm_manager.set_frequency_broadcast(frequency):
                logger.error(f"设置频点{frequency}Hz失败")
                return False
            
            # 2. 群发开启阻抗测试
            self._set_state(SimultaneousTestState.STARTING_MEASUREMENT)
            logger.debug(f"🚀 启动测量: 通道{[ch+1 for ch in self.config.enabled_channels]}")
            
            if not self.comm_manager.start_impedance_measurement_broadcast(self.config.enabled_channels):
                logger.error("启动阻抗测量失败")
                return False
            
            # 3. 监控测试状态
            self._set_state(SimultaneousTestState.MONITORING)
            if not self._monitor_test_completion():
                logger.error("测试监控失败")
                return False
            
            # 4. 批量获取阻抗数据
            self._set_state(SimultaneousTestState.READING_DATA)
            impedance_data = self.comm_manager.read_impedance_data_broadcast()
            
            if not impedance_data:
                logger.error("读取阻抗数据失败")
                return False
            
            # 保存测试结果
            self.test_results[frequency] = impedance_data
            logger.debug(f"✅ 频点{frequency}Hz测试完成")
            
            return True
            
        except Exception as e:
            logger.error(f"测试频点{frequency}Hz失败: {e}")
            return False
    
    def _monitor_test_completion(self) -> bool:
        """
        监控测试完成状态（自适应轮询优化）

        Returns:
            是否所有通道都完成测试
        """
        try:
            timeout = self.config.timeout_seconds
            start_time = time.time()
            last_progress_time = start_time
            completed_channels = set()

            # 自适应轮询间隔策略（优化版本）
            def get_adaptive_interval(elapsed_time: float, progress_ratio: float) -> float:
                """根据测试进度和时间动态调整轮询间隔（更激进的优化）"""
                if elapsed_time < 0.3:
                    return 0.02  # 前300ms：20ms超快速轮询
                elif elapsed_time < 1.0:
                    return 0.05  # 0.3-1秒：50ms快速轮询
                elif progress_ratio > 0.7:
                    return 0.05  # 超过70%完成：50ms加速轮询
                elif progress_ratio > 0.3:
                    return 0.08  # 30-70%完成：80ms中速轮询
                else:
                    return 0.1   # 其他情况：100ms正常轮询


            while time.time() - start_time < timeout:
                current_time = time.time()
                elapsed_time = current_time - start_time

                # 群发读取状态码
                statuses = self.comm_manager.get_measurement_status_broadcast()

                if not statuses or len(statuses) < max(self.config.enabled_channels) + 1:
                    logger.debug("状态读取失败，继续监控")
                    time.sleep(0.1)  # 失败时短暂等待
                    continue

                # 检查启用通道的状态
                current_completed = set()
                testing_count = 0
                error_count = 0
                skipped_channels = set()

                for channel_index in self.config.enabled_channels:
                    if channel_index < len(statuses):
                        status = statuses[channel_index]

                        # 检查状态码
                        status_info = self.status_manager.get_channel_status_info(channel_index, status)

                        if status == 0x0006:  # 测量完成
                            current_completed.add(channel_index)
                        elif status == 0x0001:  # 测量中
                            testing_count += 1
                        elif status_info.should_skip:  # 需要跳过的状态（包括0x0003等）
                            if channel_index not in skipped_channels:
                                skipped_channels.add(channel_index)
                                logger.warning(f"⚠️ 通道{channel_index + 1}状态异常，跳过测试: {status_info.description} (0x{status:04X})")

                                # 通知UI更新通道状态
                                if hasattr(self, 'channel_progress_callback') and self.channel_progress_callback:
                                    try:
                                        self.channel_progress_callback(channel_index + 1, {
                                            'state': 'error',
                                            'status_code': status,
                                            'error_message': status_info.description,
                                            'severity': status_info.severity.value
                                        })
                                    except Exception as e:
                                        logger.error(f"通道状态回调失败: {e}")

                            # 将跳过的通道视为已完成
                            current_completed.add(channel_index)
                            error_count += 1
                        elif status != 0x0000:  # 其他非空闲状态
                            error_count += 1

                # 检查是否有新完成的通道
                newly_completed = current_completed - completed_channels
                if newly_completed:
                    for ch_idx in newly_completed:
                        logger.debug(f"🎯 通道{ch_idx+1}测量完成 (耗时: {elapsed_time:.3f}s)")
                    completed_channels = current_completed
                    last_progress_time = current_time

                # 检查是否全部完成
                if len(completed_channels) == len(self.config.enabled_channels):
                    logger.info(f"✅ 所有通道测量完成，耗时: {elapsed_time:.3f}秒")
                    return True

                # 显示详细进度（每秒最多一次）
                if current_time - last_progress_time >= 1.0:
                    progress_ratio = len(completed_channels) / len(self.config.enabled_channels)
                    logger.info(f"同时测试进度: {len(completed_channels)}/{len(self.config.enabled_channels)} "
                               f"({progress_ratio*100:.1f}%), 测试中:{testing_count}, "
                               f"错误:{error_count}, 耗时:{elapsed_time:.1f}s")
                    last_progress_time = current_time

                # 动态调整轮询间隔
                progress_ratio = len(completed_channels) / len(self.config.enabled_channels)
                check_interval = get_adaptive_interval(elapsed_time, progress_ratio)
                time.sleep(check_interval)

            # 超时处理
            elapsed_time = time.time() - start_time
            logger.error(f"❌ 测试超时: {elapsed_time:.3f}秒, "
                        f"完成{len(completed_channels)}/{len(self.config.enabled_channels)}个通道")
            return False

        except Exception as e:
            logger.error(f"监控测试完成失败: {e}")
            return False
    
    def _recover_from_error(self) -> bool:
        """
        从错误中恢复
        
        Returns:
            是否恢复成功
        """
        try:
            
            # 重试当前频点
            for retry in range(self.config.max_retries):
                logger.debug(f"重试 {retry + 1}/{self.config.max_retries}")
                
                current_frequency = self.config.frequencies[self.current_frequency_index]
                if self._test_single_frequency(current_frequency):
                    logger.info("✅ 错误恢复成功")
                    return True
                
                time.sleep(1)  # 重试间隔
            
            logger.error("❌ 错误恢复失败")
            return False
            
        except Exception as e:
            logger.error(f"错误恢复异常: {e}")
            return False
    
    def _set_state(self, new_state: SimultaneousTestState):
        """设置测试状态"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            logger.debug(f"状态变更: {old_state.value} -> {new_state.value}")
            
            # 通知状态变更
            if self.status_callback:
                try:
                    self.status_callback(new_state.value)
                except Exception as e:
                    logger.error(f"状态回调失败: {e}")
    
    def _notify_progress(self):
        """通知进度更新"""
        if self.progress_callback:
            try:
                progress_info = self.get_test_progress()
                self.progress_callback(progress_info)
            except Exception as e:
                logger.error(f"进度回调失败: {e}")

    def _clean_test_environment(self):
        """清理测试环境，确保干净的测试状态"""
        try:
            logger.debug("🧹 同时测试管理器开始清理测试环境...")

            # 清理内部状态
            self.current_frequency_index = 0
            self.start_time = 0

            # 清理测试结果和错误信息
            self.test_results.clear()
            self.error_info.clear()

            logger.debug("✅ 同时测试管理器测试环境清理完成")

        except Exception as e:
            logger.error(f"❌ 同时测试管理器清理测试环境失败: {e}")

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
