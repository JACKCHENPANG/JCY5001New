# -*- coding: utf-8 -*-
"""
错频测试执行器
从ParallelStaggeredTestManager中提取的错频测试执行相关功能

职责：
- 错频测试执行
- 频率设置管理
- 错频轮次控制
- 错频数据读取

Author: Jack
Date: 2025-01-30
"""

import logging
import time
from typing import Dict, List, Optional, Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)


class UserStoppedException(Exception):
    """用户停止测试异常"""
    pass


class StaggeredTestState(Enum):
    """错频测试状态"""
    IDLE = "idle"
    SETTING_FREQUENCIES = "setting_frequencies"
    STARTING_MEASUREMENT = "starting_measurement"
    MONITORING = "monitoring"
    READING_DATA = "reading_data"
    COMPLETED = "completed"
    ERROR = "error"


class StaggeredTestExecutor:
    """
    错频测试执行器
    
    职责：
    - 执行错频测试流程
    - 管理频率设置
    - 监控测试完成状态
    - 读取测试数据
    """
    
    def __init__(self, comm_manager, frequency_classifier, stop_event=None):
        """
        初始化错频测试执行器
        
        Args:
            comm_manager: 通信管理器
            frequency_classifier: 频率分类器
            stop_event: 停止事件
        """
        self.comm_manager = comm_manager
        self.frequency_classifier = frequency_classifier
        self.stop_event = stop_event
        
        self.state = StaggeredTestState.IDLE
        self.test_results: Dict[float, Dict[int, Any]] = {}
        
        # 回调函数
        self.channel_progress_callback: Optional[Callable] = None
        
        # 状态码管理器
        from backend.device_status_manager import DeviceStatusManager
        self.status_manager = DeviceStatusManager()
        
        logger.debug("错频测试执行器初始化完成")
    
    def set_channel_progress_callback(self, callback: Callable):
        """设置通道进度回调函数"""
        self.channel_progress_callback = callback
    
    def execute_high_frequency_test(self, enabled_channels: List[int], config: Any) -> tuple:
        """
        执行高频点错频测试

        Args:
            enabled_channels: 启用的通道列表
            config: 测试配置

        Returns:
            (success, failed_frequencies) 是否测试成功和失败频点列表
        """
        try:
            high_frequencies = self.frequency_classifier.get_high_frequencies()

            if not high_frequencies:
                logger.info("没有高频点，跳过错频测试")
                return True, []

            logger.info(f"开始高频点错频测试: {len(high_frequencies)}个频点")

            # 计算需要的轮次
            num_rounds = len(high_frequencies)
            failed_frequencies = []  # 记录失败的频点

            logger.debug(f"错频测试参数: {len(enabled_channels)}个通道, {len(high_frequencies)}个频点, {num_rounds}轮")

            # 执行多轮错频测试
            for round_index in range(num_rounds):
                logger.info(f"执行第{round_index + 1}/{num_rounds}轮错频测试")

                if not self._execute_staggered_round(round_index, enabled_channels, config):
                    # 检查是否是用户停止
                    if self.stop_event and self.stop_event.is_set():
                        logger.info(f"第{round_index + 1}轮错频测试被用户停止，停止后续轮次")
                        return True, failed_frequencies  # 用户停止视为正常完成
                    else:
                        # 记录失败的频点
                        failed_frequency = high_frequencies[round_index]
                        failed_frequencies.append(failed_frequency)
                        logger.error(f"第{round_index + 1}轮错频测试失败，频点{failed_frequency}Hz已重试3次仍失败")
                        # 继续下一个频点
                        continue

            logger.info(f"高频点错频测试完成，失败频点: {failed_frequencies}")
            return True, failed_frequencies

        except Exception as e:
            logger.error(f"高频点测试失败: {e}")
            return False, []
    
    def _execute_staggered_round(self, round_index: int, enabled_channels: List[int], config: Any) -> bool:
        """
        执行一轮错频测试（带重试机制）

        Args:
            round_index: 轮次索引
            enabled_channels: 启用的通道列表
            config: 测试配置

        Returns:
            是否执行成功
        """
        try:
            # 修复在轮次开始前检查停止事件
            if self.stop_event and self.stop_event.is_set():
                logger.info(f"第{round_index + 1}轮错频测试在开始前被用户停止")
                raise UserStoppedException(f"第{round_index + 1}轮错频测试在开始前被用户停止")

            # 1. 计算频点分配
            frequency_assignments = self.frequency_classifier.calculate_frequency_assignments(
                enabled_channels, round_index
            )

            logger.debug(f"第{round_index + 1}轮频点分配: {frequency_assignments}")

            # 修复在设置频点前检查停止事件
            if self.stop_event and self.stop_event.is_set():
                logger.info(f"第{round_index + 1}轮错频测试在设置频点前被用户停止")
                raise UserStoppedException(f"第{round_index + 1}轮错频测试在设置频点前被用户停止")

            # 状态读取不稳定时不要反复整轮重测；优先尝试读取数据确认完成。
            max_retries = 2
            round_success = False

            for retry_index in range(max_retries):
                logger.info(f"第{round_index + 1}轮错频测试 - 尝试{retry_index + 1}/{max_retries}")
                stage_t0 = time.time()

                # 2. 设置各通道频点
                self.state = StaggeredTestState.SETTING_FREQUENCIES

                if not self._set_staggered_frequencies(frequency_assignments):
                    logger.error(f"第{retry_index + 1}次尝试：设置错频频点失败")
                    if retry_index < max_retries - 1:
                        logger.info(f"等待0.1秒后重试...")
                        time.sleep(0.1)
                        continue
                    else:
                        logger.error(f"第{round_index + 1}轮错频测试：设置频点失败（已重试{max_retries}次）")
                        return False

                set_freq_elapsed = time.time() - stage_t0

                # 修复在通知频率前检查停止事件
                if self.stop_event and self.stop_event.is_set():
                    logger.info(f"第{round_index + 1}轮错频测试在通知频率前被用户停止")
                    return False

                # 通知每个通道的频率设置
                self._notify_channel_frequencies(frequency_assignments, round_index, config)

                # 修复在启动测量前检查停止事件
                if self.stop_event and self.stop_event.is_set():
                    logger.info(f"第{round_index + 1}轮错频测试在启动测量前被用户停止")
                    return False

                # 2.5. 首轮预热延迟：给电路稳定时间，防止第一点跑飞
                if round_index == 0:
                    time.sleep(0.5)
                    logger.debug("首轮错频预热延迟0.5s完成")

                # 3. 同时启动所有通道
                start_measure_t0 = time.time()
                self.state = StaggeredTestState.STARTING_MEASUREMENT
                if not self.comm_manager.start_impedance_measurement_broadcast(enabled_channels):
                    logger.error(f"第{retry_index + 1}次尝试：启动错频测量失败")
                    if retry_index < max_retries - 1:
                        logger.info(f"等待0.1秒后重试...")
                        time.sleep(0.1)
                        continue
                    else:
                        logger.error(f"第{round_index + 1}轮错频测试：启动测量失败（已重试{max_retries}次）")
                        return False

                # 修复在监控前检查停止事件
                if self.stop_event and self.stop_event.is_set():
                    logger.info(f"第{round_index + 1}轮错频测试在监控前被用户停止")
                    return False

                # 4. 监控测试完成（最多2秒）
                self.state = StaggeredTestState.MONITORING
                if not self._monitor_staggered_completion(enabled_channels, config):
                    logger.warning(f"第{retry_index + 1}次尝试：错频测试监控超时，尝试直接读取数据确认结果")

                monitor_elapsed = time.time() - start_measure_t0

                # 监控完成→数据寄存器稳定延迟（防止读到旧数据）
                settle_t0 = time.time()
                time.sleep(0.4)
                settle_elapsed = time.time() - settle_t0

                # 修复在读取数据前检查停止事件
                if self.stop_event and self.stop_event.is_set():
                    logger.info(f"第{round_index + 1}轮错频测试在读取数据前被用户停止")
                    raise UserStoppedException(f"第{round_index + 1}轮错频测试在读取数据前被用户停止")

                # 5. 读取阻抗数据（带二次验证）
                read_t0 = time.time()
                self.state = StaggeredTestState.READING_DATA
                _read_ok = self._read_staggered_data_with_retries(frequency_assignments)
                if not _read_ok:
                    logger.error(f"第{round_index + 1}轮错频：数据读取失败")
                    if retry_index < max_retries - 1:
                        logger.info("等待0.1秒后重试本轮...")
                        time.sleep(0.1)
                        continue
                    return False

                read_elapsed = time.time() - read_t0
                total_stage_elapsed = time.time() - stage_t0
                logger.info(
                    f"[TIMING][HF] round={round_index + 1} attempt={retry_index + 1} "
                    f"set_freq={set_freq_elapsed:.3f}s monitor_plus_start={monitor_elapsed:.3f}s "
                    f"settle={settle_elapsed:.3f}s read_verify={read_elapsed:.3f}s total={total_stage_elapsed:.3f}s"
                )

                # 成功完成，退出重试循环
                round_success = True
                logger.info(f"第{round_index + 1}轮错频测试成功（第{retry_index + 1}次尝试）")
                break

            # 检查是否成功
            if not round_success:
                logger.error(f"第{round_index + 1}轮错频测试失败（已重试{max_retries}次）")
                return False

            # 修复在数据读取完成后，通知频点完成并更新进度
            # 获取这一轮测试的所有频率
            completed_frequencies = list(frequency_assignments.values())
            for frequency in set(completed_frequencies):  # 去重，因为可能有重复频率
                self._notify_frequency_completed(frequency, config)

            logger.debug(f"第{round_index + 1}轮错频测试完成")
            return True

        except UserStoppedException as e:
            logger.info(f"第{round_index + 1}轮错频测试被用户停止: {e}")
            return False  # 用户停止，返回False以停止后续轮次
        except Exception as e:
            logger.error(f"执行第{round_index + 1}轮错频测试失败: {e}")
            return False

    def _read_staggered_data_with_retries(self, frequency_assignments: Dict[int, float]) -> bool:
        """高频错频数据稳定读取，避免寄存器刷新瞬间造成跳点。"""
        try:
            last_snapshot = None
            max_reads = 4
            for read_index in range(max_reads):
                first_snapshot = self.comm_manager.read_impedance_data_broadcast()
                if not first_snapshot:
                    time.sleep(0.05)
                    continue

                time.sleep(0.12)
                second_snapshot = self.comm_manager.read_impedance_data_broadcast()
                if not second_snapshot:
                    last_snapshot = first_snapshot
                    time.sleep(0.05)
                    continue

                last_snapshot = second_snapshot
                if self._is_staggered_snapshot_stable(first_snapshot, second_snapshot, frequency_assignments):
                    return self._read_staggered_data(frequency_assignments, second_snapshot)

                logger.warning(f"高频错频数据第{read_index + 1}次稳定性检查未通过，继续重读")
                time.sleep(0.08)

            if last_snapshot:
                logger.warning("高频错频数据多次稳定性检查未完全通过，使用最后一次读数")
                return self._read_staggered_data(frequency_assignments, last_snapshot)
            return False
        except Exception as e:
            logger.error(f"错频数据重读失败: {e}")
            return False

    def _is_staggered_snapshot_stable(self, first_snapshot: Dict[int, Any],
                                      second_snapshot: Dict[int, Any],
                                      frequency_assignments: Dict[int, float]) -> bool:
        """判断两次阻抗快照在本轮有效通道上是否稳定。"""
        try:
            for channel_index in frequency_assignments:
                first_data = first_snapshot.get(channel_index)
                second_data = second_snapshot.get(channel_index)
                if not isinstance(first_data, dict) or not isinstance(second_data, dict):
                    logger.debug(f"通道{channel_index + 1}稳定性检查数据缺失")
                    return False
                if 'real' not in first_data or 'imag' not in first_data or 'real' not in second_data or 'imag' not in second_data:
                    logger.debug(f"通道{channel_index + 1}稳定性检查数据格式错误")
                    return False

                real_delta = abs(float(first_data['real']) - float(second_data['real']))
                imag_delta = abs(float(first_data['imag']) - float(second_data['imag']))
                magnitude = max(
                    (float(first_data['real']) ** 2 + float(first_data['imag']) ** 2) ** 0.5,
                    (float(second_data['real']) ** 2 + float(second_data['imag']) ** 2) ** 0.5,
                    1.0
                )
                tolerance = max(20.0, magnitude * 0.02)
                if real_delta > tolerance or imag_delta > tolerance:
                    logger.warning(
                        f"通道{channel_index + 1}高频读数未稳定: "
                        f"dRe={real_delta:.3f}, dIm={imag_delta:.3f}, tol={tolerance:.3f}"
                    )
                    return False
            return True
        except Exception as e:
            logger.error(f"高频错频数据稳定性检查失败: {e}")
            return False
    
    def _set_staggered_frequencies(self, frequency_assignments: Dict[int, float]) -> bool:
        """
        设置错频频点（使用4200H批量设置指令）

        Args:
            frequency_assignments: 通道频点分配

        Returns:
            是否设置成功
        """
        try:
            logger.debug("尝试4200H指令批量设置错频频点")

            # 首先尝试使用4200H批量频率设置指令
            batch_success = self.comm_manager.set_staggered_frequencies_batch(frequency_assignments)

            if batch_success:
                logger.debug("4200H批量错频频点设置成功")
                # 记录每个通道的频点分配
                for channel_index, frequency in frequency_assignments.items():
                    logger.debug(f"   通道{channel_index + 1}: {frequency}Hz")
                return True
            else:
                logger.warning("4200H批量设置失败，改用逐个通道设置")

                # 改用逐个通道设置频率
                individual_success = True
                for channel_index, frequency in frequency_assignments.items():
                    try:
                        if self.comm_manager.set_channel_frequency(channel_index, frequency):
                            logger.debug(f"通道{channel_index+1}频率设置成功: {frequency}Hz")
                        else:
                            logger.error(f"通道{channel_index+1}频率设置失败: {frequency}Hz")
                            individual_success = False
                    except Exception as e:
                        logger.error(f"通道{channel_index+1}频率设置异常: {e}")
                        individual_success = False

                if individual_success:
                    logger.debug("逐个通道频率设置成功")
                else:
                    logger.error("逐个通道频率设置失败")

                return individual_success

        except Exception as e:
            logger.error(f"设置错频频点失败: {e}")
            return False
    
    def _monitor_staggered_completion(self, enabled_channels: List[int], config: Any) -> bool:
        """
        监控错频测试完成状态

        Args:
            enabled_channels: 启用的通道列表
            config: 测试配置

        Returns:
            是否所有通道都完成测试
        """
        try:
            timeout = 3.0  # 每次最多等待2秒（因为1秒内就可以完成）
            start_time = time.time()
            completed_channels = set()

            logger.debug("开始监控错频测试完成状态")

            while time.time() - start_time < timeout:
                # 检查停止事件
                if self.stop_event and self.stop_event.is_set():
                    logger.info("错频测试监控被用户停止")
                    # 修复：用户停止使用异常处理，而不是返回失败
                    raise UserStoppedException("错频测试监控被用户停止")

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

                                # 通知UI更新通道状态
                                if self.channel_progress_callback:
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

                # 检查是否有新完成的通道
                newly_completed = current_completed - completed_channels
                if newly_completed:
                    for ch_idx in newly_completed:
                        logger.debug(f"通道{ch_idx + 1}错频测量完成")
                    completed_channels = current_completed

                # 检查是否全部完成
                if len(completed_channels) == len(enabled_channels):
                    logger.debug(f"所有通道错频测量完成，耗时: {elapsed_time:.3f}秒")
                    return True

                time.sleep(config.status_check_interval)

            # 超时处理
            elapsed_time = time.time() - start_time
            logger.error(f"错频测试超时: {elapsed_time:.3f}秒")
            return False

        except UserStoppedException as e:
            logger.info(f"错频测试监控被用户停止: {e}")
            return False  # 用户停止，返回False以停止测试
        except Exception as e:
            logger.error(f"监控错频测试完成失败: {e}")
            return False
    
    def _read_staggered_data(self, frequency_assignments: Dict[int, float],
                             impedance_data: Optional[Dict[int, Any]] = None) -> bool:
        """
        读取错频测试数据

        Args:
            frequency_assignments: 通道频点分配

        Returns:
            是否读取成功
        """
        try:
            logger.debug("读取错频测试数据")

            # 批量读取阻抗数据
            if impedance_data is None:
                impedance_data = self.comm_manager.read_impedance_data_broadcast()

            if not impedance_data:
                logger.error("读取错频阻抗数据失败")
                return False

            # 检查数据格式 - 实际返回格式是 {channel_index: {'real': value, 'imag': value}}
            if not isinstance(impedance_data, dict) or not impedance_data:
                logger.error("阻抗数据格式错误或为空")
                return False

            # 按频率组织数据
            for channel_index, frequency in frequency_assignments.items():
                if channel_index in impedance_data:
                    channel_raw_data = impedance_data[channel_index]

                    # 检查通道数据格式
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

                    # 初始化频率结果字典
                    if frequency not in self.test_results:
                        self.test_results[frequency] = {}

                    # 保存通道数据
                    self.test_results[frequency][channel_index] = channel_data

                    logger.debug(f"保存通道{channel_index + 1}频点{frequency}Hz数据: Re={channel_raw_data['real']:.3f}μΩ, Im={channel_raw_data['imag']:.3f}μΩ")
                else:
                    logger.warning(f"通道{channel_index + 1}数据缺失")

            logger.debug("错频测试数据读取完成")
            return True

        except Exception as e:
            logger.error(f"读取错频测试数据失败: {e}")
            return False
    
    def _notify_channel_frequencies(self, frequency_assignments: Dict[int, float], round_index: int, config: Any):
        """
        通知每个通道的频率设置

        Args:
            frequency_assignments: 通道频率分配
            round_index: 轮次索引
            config: 测试配置
        """
        if self.channel_progress_callback:
            try:
                total_frequencies = len(config.frequencies)

                # 修复添加详细的进度计算日志

                for channel_index, frequency in frequency_assignments.items():
                    channel_num = channel_index + 1  # 转换为1-8的通道号

                    completed_frequencies = self._get_channel_completed_frequency_count(channel_index)
                    current_frequency_index = min(completed_frequencies + 1, total_frequencies)

                    # 修复进度计算应该基于已完成的频点，而不是正在开始的频点
                    # 在频点开始时，进度应该反映之前已完成的频点数量
                    base_progress = (completed_frequencies / total_frequencies) * 100.0
                    if not hasattr(self, '_progress_start'):
                        self._progress_start = time.time()
                    elapsed = time.time() - self._progress_start
                    time_floor = min(elapsed * 3.0, 25.0)
                    progress = int(max(base_progress, time_floor))

                    # 简化进度计算日志
                    logger.debug(f"通道{channel_num}进度: {progress}%, 当前频率: {frequency}Hz")

                    # 构建进度数据
                    progress_data = {
                        'state': 'testing',
                        'progress': progress,
                        'message': f'错频测试: {frequency}Hz',
                        'frequency': frequency,  # 每个通道的实际频率
                        'frequency_index': completed_frequencies,
                        'current_frequency_index': current_frequency_index,
                        'completed_frequency_count': completed_frequencies,
                        'completed_frequencies': completed_frequencies,
                        'total_frequencies': total_frequencies,
                        'round_index': round_index + 1,
                        'mode': 'staggered',  # 标识为错频模式
                        'base_frequency': self.frequency_classifier.get_high_frequencies()[round_index] if round_index < len(self.frequency_classifier.get_high_frequencies()) else frequency
                    }

                    # 调用通道进度回调
                    self.channel_progress_callback(channel_num, progress_data)

                    logger.debug(
                        f"通知通道{channel_num}频率: {frequency}Hz (错频模式), "
                        f"已完成频点: {completed_frequencies}/{total_frequencies}"
                    )

            except Exception as e:
                logger.error(f"通道频率通知失败: {e}")

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

                if not hasattr(self, '_progress_start'):
                    self._progress_start = time.time()
                elapsed = time.time() - self._progress_start
                time_floor = min(elapsed * 3.0, 25.0)

                logger.debug(f"频点{frequency}Hz完成，按通道更新频点进度")

                # 通知所有启用的通道进度更新
                for channel_index in config.enabled_channels:
                    channel_num = channel_index + 1
                    completed_frequencies = self._get_channel_completed_frequency_count(channel_index)
                    base_progress = (completed_frequencies / total_frequencies) * 100.0
                    progress = int(max(base_progress, time_floor))

                    # 关键修复根据进度确定状态，测试完成时发送completed状态
                    test_state = 'completed' if progress >= 100 else 'testing'

                    progress_data = {
                        'state': test_state,  # 修复动态设置状态而不是固定为testing
                        'progress': progress,
                        'message': f'频点{frequency}Hz完成',
                        'frequency': frequency,
                        'frequency_index': completed_frequencies,
                        'current_frequency_index': completed_frequencies,
                        'completed_frequency_count': completed_frequencies,
                        'completed_frequencies': completed_frequencies,
                        'total_frequencies': total_frequencies,
                        'mode': 'staggered_completed',  # 标识为错频完成
                        'completed_frequency': frequency
                    }

                    # 调用通道进度回调
                    self.channel_progress_callback(channel_num, progress_data)

                    if test_state == 'completed':
                        logger.debug(f" [错频执行器] 通道{channel_num}测试完成，发送completed状态，进度: {progress}%")
                    else:
                        logger.debug(f"通道{channel_num}进度更新: {progress}%")

            except Exception as e:
                logger.error(f"频点完成通知失败: {e}")

    def get_test_results(self) -> Dict[float, Dict[int, Any]]:
        """获取测试结果"""
        return self.test_results.copy()

    def _get_channel_completed_frequency_count(self, channel_index: int) -> int:
        """统计指定通道已经保存数据的频点数。"""
        try:
            return sum(
                1
                for channel_results in self.test_results.values()
                if isinstance(channel_results, dict) and channel_index in channel_results
            )
        except Exception as e:
            logger.debug(f"统计通道{channel_index + 1}已完成频点数失败: {e}")
            return 0
    
    def clear_results(self):
        """清空测试结果"""
        self.test_results.clear()
    
    def get_state(self) -> StaggeredTestState:
        """获取当前状态"""
        return self.state
    
    def reset(self):
        """重置执行器状态"""
        self.state = StaggeredTestState.IDLE
        self.test_results.clear()
        logger.debug("错频测试执行器已重置")
