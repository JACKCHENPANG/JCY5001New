# -*- coding: utf-8 -*-
"""
同时测试执行器
从ParallelStaggeredTestManager中提取的同时测试执行相关功能

职责：
- 同时测试执行
- 低频点测试管理
- 同时模式监控
- 同时数据读取

Author: Jack
Date: 2025-01-30
"""

import logging
import time
from typing import Dict, List, Optional, Callable, Any
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


class SimultaneousTestExecutor:
    """
    同时测试执行器
    
    职责：
    - 执行同时测试流程
    - 管理低频点测试
    - 监控同时测试完成状态
    - 读取同时测试数据
    """
    
    def __init__(self, comm_manager, frequency_classifier, stop_event=None):
        """
        初始化同时测试执行器
        
        Args:
            comm_manager: 通信管理器
            frequency_classifier: 频率分类器
            stop_event: 停止事件
        """
        self.comm_manager = comm_manager
        self.frequency_classifier = frequency_classifier
        self.stop_event = stop_event
        
        self.state = SimultaneousTestState.IDLE
        self.test_results: Dict[float, Dict[int, Any]] = {}
        
        # 回调函数
        self.channel_progress_callback: Optional[Callable] = None
        
        # 状态码管理器
        from backend.device_status_manager import DeviceStatusManager
        self.status_manager = DeviceStatusManager()
        
        logger.debug("同时测试执行器初始化完成")
    
    def set_channel_progress_callback(self, callback: Callable):
        """设置通道进度回调函数"""
        self.channel_progress_callback = callback
    
    def execute_low_frequency_test(self, enabled_channels: List[int], config: Any) -> tuple:
        """
        执行低频点同时测试

        Args:
            enabled_channels: 启用的通道列表
            config: 测试配置

        Returns:
            (success, failed_frequencies) 是否测试成功和失败频点列表
        """
        try:
            # 修复不再重置进度记录，确保进度连续性
            # 初始化进度记录（如果不存在）
            if not hasattr(self, 'last_progress'):
                self.last_progress = {}
            
            if not hasattr(self, 'exception_channels'):
                self.exception_channels = set()
            
            logger.debug("同时测试进度记录已初始化（保持连续性）")

            low_frequencies = self.frequency_classifier.get_low_frequencies()

            if not low_frequencies:
                logger.info("没有低频点，跳过同时测试")
                return True, []

            logger.info(f"开始低频点同时测试: {len(low_frequencies)}个频点")

            failed_frequencies = []  # 记录失败的频点

            # 逐个测试低频点（使用同时模式）
            for frequency in low_frequencies:
                logger.info(f"测试低频点: {frequency}Hz (同时模式)")

                # 为每个频点添加重试机制（最多3次）
                max_retries = 3
                frequency_success = False

                for retry_index in range(max_retries):
                    logger.info(f"低频点{frequency}Hz - 尝试{retry_index + 1}/{max_retries}")

                    # 修复在每个频点开始前检查停止事件
                    if self.stop_event and self.stop_event.is_set():
                        logger.info("同时测试被用户停止")
                        return True, failed_frequencies

                    # 修复通知频率前检查停止事件
                    if self.stop_event and self.stop_event.is_set():
                        logger.info("同时测试在通知频率前被用户停止")
                        return True, failed_frequencies

                    # 通知频率设置
                    self._notify_simultaneous_frequencies(frequency, enabled_channels, config)

                    # 修复设置频率前检查停止事件
                    if self.stop_event and self.stop_event.is_set():
                        logger.info("同时测试在设置频率前被用户停止")
                        return True, failed_frequencies

                    # 设置频率
                    if not self.comm_manager.set_frequency_broadcast(frequency):
                        logger.error(f"第{retry_index + 1}次尝试：设置频率{frequency}Hz失败")
                        if retry_index < max_retries - 1:
                            logger.info(f"等待0.5秒后重试...")
                            time.sleep(0.5)
                            continue
                        else:
                            logger.error(f"频率{frequency}Hz设置失败（已重试{max_retries}次）")
                            failed_frequencies.append(frequency)
                            break

                    # 修复启动测试前检查停止事件
                    if self.stop_event and self.stop_event.is_set():
                        logger.info("同时测试在启动测试前被用户停止")
                        return True, failed_frequencies

                    # 启动测试
                    if not self.comm_manager.start_impedance_measurement_broadcast(enabled_channels):
                        logger.error(f"第{retry_index + 1}次尝试：启动频率{frequency}Hz测试失败")
                        if retry_index < max_retries - 1:
                            logger.info(f"等待0.5秒后重试...")
                            time.sleep(0.5)
                            continue
                        else:
                            logger.error(f"频率{frequency}Hz启动测试失败（已重试{max_retries}次）")
                            failed_frequencies.append(frequency)
                            break

                    # 修复监控前检查停止事件
                    if self.stop_event and self.stop_event.is_set():
                        logger.info("同时测试在监控前被用户停止")
                        return True, failed_frequencies

                    # 等待完成（这个方法内部已经有停止事件检查）
                    if not self._monitor_simultaneous_completion(enabled_channels, config):
                        logger.error(f"第{retry_index + 1}次尝试：频率{frequency}Hz测试超时")
                        if retry_index < max_retries - 1:
                            logger.info(f"等待0.5秒后重试...")
                            time.sleep(0.5)
                            continue
                        else:
                            logger.error(f"频率{frequency}Hz测试超时（已重试{max_retries}次）")
                            failed_frequencies.append(frequency)
                            break

                    # 修复读取数据前检查停止事件
                    if self.stop_event and self.stop_event.is_set():
                        logger.info("同时测试在读取数据前被用户停止")
                        return True, failed_frequencies

                    # 等待数据寄存器稳定（固件状态滞后于数据写入，0.3s settling）
                    time.sleep(0.3)
                    # 读取数据
                    # 只重读不重测！测量已完成，数据在设备寄存器
                    _read_ok = False
                    for _rr in range(10):
                        if self._read_simultaneous_data(frequency, enabled_channels):
                            _read_ok = True
                            break
                        time.sleep(0.15)  # 增加等待时间，让数据寄存器充分更新
                    if not _read_ok:
                        logger.error(f"频率{frequency}Hz数据读取失败（10次内部重试）")
                        failed_frequencies.append(frequency)
                        break

                    # 修复通知完成前检查停止事件
                    if self.stop_event and self.stop_event.is_set():
                        logger.info("同时测试在通知完成前被用户停止")
                        return True, failed_frequencies

                    # 成功完成，退出重试循环
                    frequency_success = True
                    logger.info(f"低频点{frequency}Hz测试成功（第{retry_index + 1}次尝试）")
                    break

            logger.info(f"低频点同时测试完成，失败频点: {failed_frequencies}")
            return True, failed_frequencies

        except Exception as e:
            logger.error(f"低频点测试失败: {e}")
            return False, []
    
    def _monitor_simultaneous_completion(self, enabled_channels: List[int], config: Any) -> bool:
        """
        监控同时测试完成状态

        Args:
            enabled_channels: 启用的通道列表
            config: 测试配置

        Returns:
            是否所有通道都完成测试
        """
        try:
            timeout = 60.0  # 增加超时时间到60秒，给低频点更多完成时间
            start_time = time.time()
            completed_channels = set()

            logger.debug("开始监控同时测试完成状态")

            while time.time() - start_time < timeout:
                # 检查停止事件
                if self.stop_event and self.stop_event.is_set():
                    logger.info("同时测试监控被用户停止")
                    return False

                elapsed_time = time.time() - start_time

                # 群发读取状态码
                statuses = self.comm_manager.get_measurement_status_broadcast()

                if not statuses or len(statuses) < max(enabled_channels) + 1:
                    logger.debug("状态读取失败，继续监控")
                    time.sleep(config.status_check_interval)
                    continue

                # 检查启用通道的状态
                current_completed = set()
                skipped_channels = set()

                for channel_index in enabled_channels:
                    if channel_index < len(statuses):
                        status = statuses[channel_index]

                        # 检查状态码
                        status_info = self.status_manager.get_channel_status_info(channel_index, status)

                        if status == 0x0006:  # 测量完成
                            current_completed.add(channel_index)
                        elif status_info.should_skip:  # 需要跳过的状态（包括0x0003等）
                            if channel_index not in skipped_channels:
                                skipped_channels.add(channel_index)
                                logger.warning(f"通道{channel_index + 1}状态异常，跳过测试: {status_info.description} (0x{status:04X})")

                                # 修复使用新的异常处理方法
                                self.handle_channel_exception(
                                    channel_index + 1,
                                    f"{status_info.description} (0x{status:04X})",
                                    enabled_channels
                                )

                            # 将跳过的通道视为已完成
                            current_completed.add(channel_index)

                # 检查是否有新完成的通道
                newly_completed = current_completed - completed_channels
                if newly_completed:
                    for ch_idx in newly_completed:
                        logger.debug(f"通道{ch_idx + 1}同时测量完成")
                    completed_channels = current_completed

                # 检查是否全部完成
                if len(completed_channels) == len(enabled_channels):
                    logger.debug(f"所有通道同时测量完成，耗时: {elapsed_time:.3f}秒")
                    return True

                time.sleep(config.status_check_interval)

            # 超时处理
            elapsed_time = time.time() - start_time
            logger.error(f"同时测试超时: {elapsed_time:.3f}秒")
            return False

        except Exception as e:
            logger.error(f"监控同时测试完成失败: {e}")
            return False
    
    def _read_simultaneous_data(self, frequency: float, enabled_channels: List[int]) -> bool:
        """
        读取同时测试数据（带重试机制和数据验证）

        Args:
            frequency: 测试频率
            enabled_channels: 启用的通道列表

        Returns:
            是否读取成功
        """
        try:
            logger.debug(f"读取同时测试数据: {frequency}Hz")

            max_retries = 3  # 最多重试3次
            read_success = False

            for retry_index in range(max_retries):
                logger.debug(f"读取数据尝试{retry_index + 1}/{max_retries}")

                # 批量读取阻抗数据
                impedance_data = self.comm_manager.read_impedance_data_broadcast()

                if not impedance_data:
                    logger.error(f"第{retry_index + 1}次尝试：读取频率{frequency}Hz阻抗数据失败")
                    if retry_index < max_retries - 1:
                        logger.info(f"等待0.5秒后重试...")
                        time.sleep(0.5)
                        continue
                    else:
                        logger.error(f"频率{frequency}Hz数据读取失败（已重试{max_retries}次）")
                        return False

                # 检查数据格式 - 实际返回格式是 {channel_index: {'real': value, 'imag': value}}
                if not isinstance(impedance_data, dict) or not impedance_data:
                    logger.error("阻抗数据格式错误或为空")
                    if retry_index < max_retries - 1:
                        logger.info(f"等待0.5秒后重试...")
                        time.sleep(0.5)
                        continue
                    else:
                        logger.error("阻抗数据格式错误或为空（已重试{max_retries}次）")
                        return False

                # 验证数据有效性
                valid_data_count = 0
                for channel_index in enabled_channels:
                    if channel_index in impedance_data:
                        channel_raw_data = impedance_data[channel_index]

                        # 检查数据格式
                        if not isinstance(channel_raw_data, dict) or 'real' not in channel_raw_data or 'imag' not in channel_raw_data:
                            logger.warning(f"通道{channel_index + 1}数据格式错误: {channel_raw_data}")
                            continue

                        real_value = channel_raw_data.get('real', 0)
                        imag_value = channel_raw_data.get('imag', 0)

                        # 陈旧数据检测：与同通道已有数据对比
                        is_stale = False
                        if frequency in self.test_results:
                            for prev_ch in self.test_results[frequency].values():
                                if isinstance(prev_ch, dict) and abs(real_value - prev_ch.get("real", 0)) < 1.0 and abs(imag_value - prev_ch.get("imag", 0)) < 1.0:
                                    is_stale = True
                                    break
                        # 验证数据有效性（排除陈旧数据）
                        if not is_stale and (real_value != 0 or imag_value != 0):
                            valid_data_count += 1
                            logger.debug(f"通道{channel_index + 1}数据有效: Re={real_value:.3f}μΩ, Im={imag_value:.3f}μΩ")
                        else:
                            logger.warning(f"通道{channel_index + 1}数据无效或陈旧: Re={real_value:.3f}μΩ, Im={imag_value:.3f}μΩ")

                # 如果没有有效数据，重试
                if valid_data_count == 0:
                    logger.warning(f"频率{frequency}Hz所有通道数据无效，重试...")
                    if retry_index < max_retries - 1:
                        logger.info(f"等待0.5秒后重试...")
                        time.sleep(0.5)
                        continue
                    else:
                        logger.error(f"频率{frequency}Hz所有通道数据无效（已重试{max_retries}次）")
                        return False

                # 二次读取验证：防止读到设备未刷新的旧数据
                time.sleep(0.1)
                verify_data = self.comm_manager.read_impedance_data_broadcast()
                if verify_data and isinstance(verify_data, dict):
                    for ch_idx in enabled_channels:
                        if ch_idx in impedance_data and ch_idx in verify_data:
                            orig = impedance_data[ch_idx]
                            verf = verify_data[ch_idx]
                            if isinstance(orig, dict) and isinstance(verf, dict):
                                if abs(orig.get("real", 0) - verf.get("real", 0)) > 1.0 or abs(orig.get("imag", 0) - verf.get("imag", 0)) > 1.0:
                                    logger.warning(f"通道{ch_idx+1}二次验证不一致，使用新数据")
                                    impedance_data[ch_idx] = verf
                
                # 保存数据
                if frequency not in self.test_results:
                    self.test_results[frequency] = {}

                for channel_index in enabled_channels:
                    if channel_index in impedance_data:
                        channel_raw_data = impedance_data[channel_index]

                        # 再次检查数据格式
                        if not isinstance(channel_raw_data, dict) or 'real' not in channel_raw_data or 'imag' not in channel_raw_data:
                            logger.warning(f"通道{channel_index + 1}数据格式错误: {channel_raw_data}")
                            continue

                        # 构建通道数据
                        channel_data = {
                            'real_impedance': channel_raw_data['real'],
                            'imaginary_impedance': channel_raw_data['imag'],
                            'magnitude': (channel_raw_data['real']**2 + channel_raw_data['imag']**2)**0.5,
                            'phase': 0.0  # 可以后续计算
                        }

                        self.test_results[frequency][channel_index] = channel_data
                        logger.debug(f"保存通道{channel_index + 1}频点{frequency}Hz数据: Re={channel_raw_data['real']:.3f}μΩ, Im={channel_raw_data['imag']:.3f}μΩ")
                    else:
                        logger.warning(f"通道{channel_index + 1}数据缺失")

                logger.debug(f"频率{frequency}Hz同时测试数据读取完成，有效通道: {valid_data_count}/{len(enabled_channels)}")
                return True

        except Exception as e:
            logger.error(f"读取频率{frequency}Hz同时测试数据失败: {e}")
            return False
    
    def _notify_simultaneous_frequencies(self, frequency: float, enabled_channels: List[int], config: Any):
        """
        通知同时模式的频率设置

        Args:
            frequency: 测试频率
            enabled_channels: 启用的通道列表
            config: 测试配置
        """
        if self.channel_progress_callback:
            try:
                total_frequencies = len(config.frequencies)
                completed_frequencies = len(self.test_results)

                # 修复添加详细的进度计算日志

                # 修复使用统一的进度计算基础，确保与完成时的计算一致
                # 基础进度：已完成频点的进度 (0-100%)
                # 计算高频测试完成后的基础进度（45%）
                high_freq_count = len(self.frequency_classifier.get_high_frequencies())
                low_freq_count = len(self.frequency_classifier.get_low_frequencies())
                
                # 修复初始化 low_freq_progress_ratio 变量
                low_freq_progress_ratio = 0.0
                
                if high_freq_count > 0 and low_freq_count > 0:
                    # 高频测试占总进度的45%
                    high_freq_progress = 45.0
                    # 低频测试占总进度的55%
                    low_freq_base = high_freq_progress
                    # 当前低频测试的进度比例
                    low_freq_progress_ratio = (completed_frequencies / low_freq_count) * 55.0
                    # 总进度 = 高频基础进度 + 当前低频进度
                    base_progress = low_freq_base + low_freq_progress_ratio
                else:
                    # 如果没有高频测试，则低频测试占100%
                    base_progress = (completed_frequencies / total_frequencies) * 100.0
                
                # 当前频点的启动进度 (2%)
                current_freq_progress = 2.0
                # 总进度，但不超过100%
                calculated_progress = min(100.0, base_progress + current_freq_progress)
                progress = int(calculated_progress)
                

                for channel_index in enabled_channels:
                    channel_num = channel_index + 1  # 转换为1-8的通道号
                    
                    # 确保进度不会回退如果计算出的进度小于之前的进度，使用之前的进度
                    if hasattr(self, 'last_progress'):
                        last_channel_progress = self.last_progress.get(channel_num, 0)
                        if progress < last_channel_progress:
                            progress = last_channel_progress
                            logger.debug(f"通道{channel_num}进度保护: {calculated_progress:.1f}% -> {progress}% (防止回退)")
                        else:
                            self.last_progress[channel_num] = progress
                    else:
                        self.last_progress = {}
                        self.last_progress[channel_num] = progress

                    # 修复添加进度计算详细日志

                    # 构建进度数据
                    progress_data = {
                        'state': 'testing',
                        'progress': progress,
                        'message': f'同时测试: {frequency}Hz',
                        'frequency': frequency,  # 所有通道使用相同频率
                        'frequency_index': completed_frequencies + 1,
                        'total_frequencies': total_frequencies,
                        'mode': 'simultaneous',  # 标识为同时模式
                        'base_frequency': frequency
                    }

                    # 调用通道进度回调
                    self.channel_progress_callback(channel_num, progress_data)

                logger.debug(f"通知所有通道频率: {frequency}Hz (同时模式)")

            except Exception as e:
                logger.error(f"同时频率通知失败: {e}")

    def _notify_frequency_completed(self, frequency: float, config: Any):
        """
        通知频点完成，更新进度

        Args:
            frequency: 完成的频率
            config: 测试配置
        """
        if self.channel_progress_callback:
            try:
                total_frequencies = len(config.frequencies)
                completed_frequencies = len(self.test_results)

                # 修复频点完成后的精确进度计算
                # 确保进度计算的一致性和单调递增
                if completed_frequencies >= total_frequencies:
                    # 所有频点完成，设置为100%
                    final_progress = 100
                    logger.debug(f"同时测试全部完成，进度: {final_progress}%")
                else:
                    # 计算高频测试完成后的基础进度（45%）
                    high_freq_count = len(self.frequency_classifier.get_high_frequencies())
                    low_freq_count = len(self.frequency_classifier.get_low_frequencies())
                    
                    if high_freq_count > 0 and low_freq_count > 0:
                        # 高频测试占总进度的45%
                        high_freq_progress = 45.0
                        # 低频测试占总进度的55%
                        low_freq_base = high_freq_progress
                        # 当前低频测试的进度比例
                        low_freq_progress = (completed_frequencies / low_freq_count) * 55.0
                        # 总进度 = 高频基础进度 + 当前低频进度
                        base_progress = low_freq_base + low_freq_progress
                    else:
                        # 如果没有高频测试，则低频测试占100%
                        base_progress = (completed_frequencies / total_frequencies) * 100.0
                    
                    final_progress = int(base_progress)
                    logger.debug(f"同时测试频点{frequency}Hz完成，进度: {final_progress}% (已完成{completed_frequencies}/{low_freq_count}低频点)")

                # 通知所有启用的通道进度更新
                for channel_index in config.enabled_channels:
                    channel_num = channel_index + 1

                    # 确保进度不会回退检查之前的进度
                    channel_final_progress = final_progress
                    if hasattr(self, 'last_progress'):
                        last_channel_progress = self.last_progress.get(channel_num, 0)
                        if channel_final_progress < last_channel_progress:
                            channel_final_progress = last_channel_progress
                            logger.debug(f"通道{channel_num}完成进度保护: {final_progress}% -> {channel_final_progress}% (防止回退)")
                        else:
                            self.last_progress[channel_num] = channel_final_progress
                    else:
                        self.last_progress = {}
                        self.last_progress[channel_num] = channel_final_progress

                    # 修复根据完成状态设置正确的测试状态
                    test_state = 'completed' if channel_final_progress >= 100 else 'testing'

                    progress_data = {
                        'state': test_state,
                        'progress': channel_final_progress,
                        'message': f'同时测试频点{frequency}Hz完成' if test_state == 'testing' else '测试完成',
                        'frequency': frequency,
                        'frequency_index': completed_frequencies,
                        'total_frequencies': total_frequencies,
                        'mode': 'simultaneous_completed',  # 标识为同时测试完成
                        'completed_frequency': frequency
                    }

                    # 调用通道进度回调
                    self.channel_progress_callback(channel_num, progress_data)

                    logger.debug(f"通道{channel_num}同时测试进度更新: {channel_final_progress}% (频点{frequency}Hz完成, 状态={test_state})")

            except Exception as e:
                logger.error(f"同时测试频点完成通知失败: {e}")

    def handle_channel_exception(self, channel_num: int, error_message: str, enabled_channels: List[int]):
        """
        处理通道异常，确保异常通道不影响正常通道进度

        Args:
            channel_num: 异常通道号 (1-8)
            error_message: 错误消息
            enabled_channels: 启用的通道列表
        """
        try:
            if self.channel_progress_callback:
                # 修复记录异常通道，避免后续覆盖
                if not hasattr(self, 'exception_channels'):
                    self.exception_channels = set()
                self.exception_channels.add(channel_num)

                # 设置异常通道状态，保持当前进度不回退
                exception_data = {
                    'state': 'exception',
                    'progress': 'keep_current',  # 特殊标记，保持当前进度
                    'message': f'通道异常: {error_message}',
                    'error_message': error_message,
                    'timestamp': time.time()
                }

                self.channel_progress_callback(channel_num, exception_data)
                logger.warning(f"通道{channel_num}设置为异常状态: {error_message}")

                # 继续更新正常通道的进度
                normal_channels = [ch for ch in enabled_channels if ch + 1 != channel_num]
                if normal_channels:
                    logger.debug(f"继续更新正常通道进度: {[ch + 1 for ch in normal_channels]}")

        except Exception as e:
            logger.error(f"处理通道{channel_num}异常失败: {e}")

    def notify_test_completion(self, enabled_channels: List[int]):
        """
        通知测试完成，确保所有正常通道都设置为100%

        Args:
            enabled_channels: 启用的通道列表
        """
        try:
            if self.channel_progress_callback:
                # 修复检查异常通道列表
                exception_channels = getattr(self, 'exception_channels', set())

                for channel_index in enabled_channels:
                    channel_num = channel_index + 1

                    # 修复跳过异常通道，避免覆盖异常状态
                    if channel_num in exception_channels:
                        logger.debug(f"跳过异常通道{channel_num}的完成通知")
                        continue

                    # 修复完全跳过发送完成数据，避免UI接收到不完整的数据
                    # 不发送任何回调，让EIS分析完成后统一发送完整数据
                    logger.debug(f"通道{channel_num}同时测试完成，跳过发送回调，等待EIS分析完成后统一发送")

        except Exception as e:
            logger.error(f"通知测试完成失败: {e}")

    def get_test_results(self) -> Dict[float, Dict[int, Any]]:
        """获取测试结果"""
        return self.test_results.copy()
    
    def clear_results(self):
        """清空测试结果"""
        self.test_results.clear()
    
    def get_state(self) -> SimultaneousTestState:
        """获取当前状态"""
        return self.state
    
    def reset(self):
        """重置执行器状态"""
        self.state = SimultaneousTestState.IDLE
        self.test_results.clear()

        # 新增重置进度记录
        if hasattr(self, 'last_progress'):
            self.last_progress.clear()
        if hasattr(self, 'exception_channels'):
            self.exception_channels.clear()

        logger.debug("同时测试执行器已重置")
