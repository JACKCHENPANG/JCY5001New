# -*- coding: utf-8 -*-
"""
测试进度管理器
负责管理测试进度计算、进度更新、进度回调等功能

从TestEngine中提取的进度管理功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import time
import logging
from typing import Dict, List, Optional, Callable
from threading import Lock
from datetime import datetime
from .unified_progress_manager import UnifiedProgressManager

logger = logging.getLogger(__name__)


class TestProgressManager:
    """
    测试进度管理器

    职责：
    - 进度计算和更新
    - 进度回调管理
    - 频点进度处理
    - 进度单调性保护
    - UI更新频率控制
    - 平滑递进进度更新
    """

    def __init__(self, progress_callback=None, frequency_callback=None):
        """
        初始化测试进度管理器
        现在使用统一进度管理器作为核心

        Args:
            progress_callback: 进度回调函数
            frequency_callback: 频点回调函数
        """
        self.progress_callback = progress_callback
        self.frequency_callback = frequency_callback

        # 新架构使用统一进度管理器
        self.unified_manager = UnifiedProgressManager(progress_callback=self._unified_progress_callback)

        # 保留兼容性支持（逐步迁移）
        self.progress_lock = Lock()
        self.channel_progress = {i: 0.0 for i in range(1, 9)}
        self.frequency_progress = {}
        self.frequency_mapping = {}

        # 保留进度计算配置（向后兼容）
        self.progress_config = {
            'base_progress_start': 5,    # 基础进度起始点 (5%)
            'base_progress_end': 95,     # 基础进度结束点 (95%)
            'completion_progress': 100   # 完成进度 (100%)
        }

        # 保留总测试时间管理
        self.test_start_time = None
        self.estimated_test_duration = 0  # 预估测试总时长（秒）

        logger.debug("测试进度管理器初始化完成（使用统一进度管理器）")

    def _unified_progress_callback(self, channel_num: int, progress_data: Dict):
        """
        统一进度管理器的回调处理

        Args:
            channel_num: 通道号
            progress_data: 进度数据
        """
        try:
            # 同步到本地缓存（向后兼容）
            with self.progress_lock:
                self.channel_progress[channel_num] = progress_data.get('progress', 0)

            # 调用原始回调
            if self.progress_callback:
                self.progress_callback(channel_num, progress_data)

        except Exception as e:
            logger.error(f"统一进度回调处理失败: {e}")

    def start_test_timer(self, estimated_duration: float = 0):
        """
        开始测试计时

        Args:
            estimated_duration: 预估测试时长（秒）
        """
        # 新架构使用统一进度管理器
        self.unified_manager.start_test(estimated_duration)

        # 保留向后兼容
        self.test_start_time = time.time()
        self.estimated_test_duration = estimated_duration
        logger.info(f"测试计时开始，预估时长: {estimated_duration:.1f}秒")

    def get_test_elapsed_time(self) -> float:
        """
        获取测试已用时间

        Returns:
            已用时间（秒）
        """
        if self.test_start_time is None:
            return 0.0
        return time.time() - self.test_start_time

    def get_time_based_progress(self) -> float:
        """
        获取基于时间的总体进度

        Returns:
            进度百分比 (0-100)
        """
        if self.test_start_time is None or self.estimated_test_duration <= 0:
            return 0.0

        elapsed = self.get_test_elapsed_time()
        progress = min(95.0, (elapsed / self.estimated_test_duration) * 100)
        return progress

    def set_test_mode(self, enabled: bool = True):
        """
        设置测试模式，跳过UI更新频率控制

        Args:
            enabled: 是否启用测试模式
        """
        if enabled:
            self._test_mode = True
            logger.debug("测试模式已启用，跳过UI更新频率控制")
        else:
            if hasattr(self, '_test_mode'):
                delattr(self, '_test_mode')
            logger.debug("测试模式已禁用")

    def reset_progress(self):
        """
        重置所有进度
        """
        # 新架构使用统一进度管理器
        self.unified_manager.reset_all()

        # 保留向后兼容
        with self.progress_lock:
            self.channel_progress = {i: 0.0 for i in range(1, 9)}
            self.frequency_progress.clear()
            self.frequency_mapping.clear()

        # 重置测试时间
        self.test_start_time = None
        self.estimated_test_duration = 0

        logger.info("🔄 [进度管理] 测试进度已完全重置，清除所有进度状态")

    def initialize_frequency_mapping(self, channel_num: int, total_frequencies: int):
        """
        初始化通道的频点映射

        Args:
            channel_num: 通道号 (1-8)
            total_frequencies: 总频点数
        """
        try:
            # 新架构使用统一进度管理器
            self.unified_manager.initialize_channel(channel_num, total_frequencies)

            # 保留向后兼容
            with self.progress_lock:
                self.frequency_mapping[channel_num] = {
                    'total_frequencies': total_frequencies,
                    'completed_frequencies': 0,
                    'current_frequency_index': 0
                }

            logger.debug(f"通道{channel_num}频点映射初始化: 总频点数={total_frequencies}")

        except Exception as e:
            logger.error(f"初始化通道{channel_num}频点映射失败: {e}")

    # 已删除 calculate_linear_progress 方法，使用 calculate_unified_progress 替代

    def update_frequency_completion(self, channel_num: int, frequency_index: int, total_frequencies: int):
        """
        更新频点完成状态

        Args:
            channel_num: 通道号 (1-8)
            frequency_index: 完成的频点索引 (1-based)
            total_frequencies: 总频点数
        """
        try:
            # 新架构使用统一进度管理器标记频点完成
            # 假设频率值，实际应该从调用方传入
            frequency = 0.0  # 占位符，实际使用时需要传入真实频率
            self.unified_manager.complete_frequency(channel_num, frequency, frequency_index)

            # 保留向后兼容的频点映射更新
            with self.progress_lock:
                if channel_num not in self.frequency_mapping:
                    self.frequency_mapping[channel_num] = {
                        'total_frequencies': total_frequencies,
                        'completed_frequencies': 0,
                        'current_frequency_index': 0
                    }

                # 更新完成的频点数量
                self.frequency_mapping[channel_num]['completed_frequencies'] = frequency_index
                self.frequency_mapping[channel_num]['current_frequency_index'] = frequency_index

            logger.debug(f"通道{channel_num}频点完成更新: 第{frequency_index}个频点完成")

        except Exception as e:
            logger.error(f"更新通道{channel_num}频点完成状态失败: {e}")

    def update_frequency_progress_unified(self, channel_num: int, frequency: float,
                                         frequency_index: int, status: str = 'testing') -> bool:
        """
        更新频点进度（新方法，支持统一进度管理器）

        Args:
            channel_num: 通道号 (1-8)
            frequency: 当前频率
            frequency_index: 频点索引 (1-based)
            status: 频点状态 ('starting', 'testing', 'completed')

        Returns:
            是否更新成功
        """
        try:
            # 新架构使用统一进度管理器
            return self.unified_manager.update_frequency_progress(
                channel_num, frequency, frequency_index, status
            )

        except Exception as e:
            logger.error(f"更新通道{channel_num}频点进度失败: {e}")
            return False

    def calculate_unified_progress(self, channel_num: int, freq_index: int, total_freqs: int,
                                 elapsed_time: float = 0, timeout: float = 60,
                                 frequency_completed: bool = False, total_test_time: float = 0,
                                 estimated_total_time: float = 0) -> float:
        """
        统一的进度计算方法 - 基于总测试时间进度

        Args:
            channel_num: 通道号 (1-8)
            freq_index: 当前频点索引 (从1开始)
            total_freqs: 总频点数
            elapsed_time: 已用时间（秒）
            timeout: 超时时间（秒）
            frequency_completed: 当前频点是否已完成
            total_test_time: 总测试已用时间（秒）
            estimated_total_time: 预估总测试时间（秒）

        Returns:
            进度百分比 (0-100)
        """
        try:
            if total_freqs <= 0:
                return 0.0

            # 优先使用总测试时间进度
            if total_test_time > 0 and estimated_total_time > 0:
                # 基于总测试时间的进度计算
                time_progress = min(95.0, (total_test_time / estimated_total_time) * 100)
                logger.debug(f"通道{channel_num}时间进度: {time_progress:.1f}% (已用时{total_test_time:.1f}s/预估{estimated_total_time:.1f}s)")
                return time_progress

            # 备用方案基于频点的简化进度计算
            start_progress = self.progress_config['base_progress_start']  # 5%
            end_progress = self.progress_config['base_progress_end']      # 95%
            progress_range = end_progress - start_progress               # 90%

            if frequency_completed:
                # 频点完成：直接计算到下一个频点的起始位置
                completed_frequencies = freq_index  # 已完成的频点数
                progress = start_progress + (completed_frequencies / total_freqs) * progress_range

                # 如果是最后一个频点完成，设置为100%
                if freq_index >= total_freqs:
                    progress = self.progress_config['completion_progress']

                logger.debug(f"通道{channel_num}频点完成进度: {progress:.1f}%")

            else:
                # 频点进行中：基础进度 + 时间内进度
                completed_frequencies = max(0, freq_index - 1)  # 已完成的频点数
                base_progress = start_progress + (completed_frequencies / total_freqs) * progress_range

                # 当前频点的进度范围
                freq_progress_range = progress_range / total_freqs

                # 基于测试时间的频点内进度
                if elapsed_time > 0 and timeout > 0:
                    within_freq_progress = min(0.95, elapsed_time / timeout)
                    progress = base_progress + freq_progress_range * within_freq_progress
                else:
                    progress = base_progress

                logger.debug(f"通道{channel_num}测试进度: {progress:.1f}%")

            # 确保进度在合理范围内
            final_progress = min(end_progress if not frequency_completed else 100.0,
                               max(start_progress, progress))

            return final_progress

        except Exception as e:
            logger.error(f"计算统一进度失败: {e}")
            return 0.0

    def calculate_channel_progress(self, channel_num: int, freq_index: int,
                                 total_freqs: int, elapsed_time: float = 0,
                                 timeout: float = 60, frequency_completed: bool = False,
                                 total_test_time: float = 0, estimated_total_time: float = 0) -> float:
        """
        计算通道进度 - 使用统一进度计算系统

        Args:
            channel_num: 通道号 (1-8)
            freq_index: 当前频点索引
            total_freqs: 总频点数
            elapsed_time: 已用时间
            timeout: 超时时间
            frequency_completed: 当前频点是否已完成
            total_test_time: 总测试已用时间
            estimated_total_time: 预估总测试时间

        Returns:
            进度百分比 (0-100)
        """
        try:
            # 使用统一的进度计算方法
            progress = self.calculate_unified_progress(
                channel_num, freq_index, total_freqs,
                elapsed_time, timeout, frequency_completed,
                total_test_time, estimated_total_time
            )

            # 移除强制进度单调性保护，允许自然进度更新
            with self.progress_lock:
                last_progress = self.channel_progress.get(channel_num, 0)

                # 直接更新进度，不强制保护
                self.channel_progress[channel_num] = progress
                logger.debug(f"通道{channel_num}进度更新: {last_progress:.1f}% -> {progress:.1f}%")
                return progress

        except Exception as e:
            logger.error(f"计算通道{channel_num}进度失败: {e}")
            return self.channel_progress.get(channel_num, 0)

    def update_channel_progress(self, channel_num: int, progress: float,
                              message: str = "", frequency: float = 0,
                              freq_index: int = 0, total_freqs: int = 1,
                              state: str = "testing") -> bool:
        """
        更新通道进度

        Args:
            channel_num: 通道号 (1-8)
            progress: 进度百分比 (0-100)
            message: 进度消息
            frequency: 当前频率
            freq_index: 频点索引
            total_freqs: 总频点数
            state: 测试状态

        Returns:
            是否更新成功
        """
        try:
            # 新架构处理特殊进度标记和验证进度单调性
            if progress == 'keep_current':
                # 特殊标记：保持当前进度，用于异常状态
                current_state = self.unified_manager.get_channel_progress(channel_num)
                if current_state:
                    progress = current_state.current_progress
                    logger.debug(f"通道{channel_num}保持当前进度: {progress}%")
                else:
                    progress = 0
            elif isinstance(progress, (int, float)):
                # 数值进度：验证单调性
                current_state = self.unified_manager.get_channel_progress(channel_num)
                if current_state and progress < current_state.current_progress:
                    logger.warning(f"通道{channel_num}进度回退被阻止: {progress:.1f}% < {current_state.current_progress:.1f}%")
                    progress = current_state.current_progress  # 使用当前进度，防止回退

            # 保留向后兼容的进度更新
            with self.progress_lock:
                self.channel_progress[channel_num] = progress

            # 构建进度数据
            progress_data = {
                'state': state,
                'progress': int(progress),
                'message': message,
                'current_frequency': frequency,
                'frequency_index': freq_index,
                'total_frequencies': total_freqs,
                'timestamp': datetime.now()
            }

            # 通知进度更新
            self._notify_progress(channel_num, progress_data)

            logger.debug(f"通道{channel_num}进度更新: {progress:.1f}% - {message}")
            return True

        except Exception as e:
            logger.error(f"更新通道{channel_num}进度失败: {e}")
            return False

    def complete_channel_progress(self, channel_num: int, message: str = "测试完成"):
        """
        完成通道进度（设置为100%）

        Args:
            channel_num: 通道号 (1-8)
            message: 完成消息
        """
        try:
            # 新架构使用统一进度管理器完成测试
            self.unified_manager.complete_test(channel_num)

            # 保留向后兼容
            with self.progress_lock:
                self.channel_progress[channel_num] = 100.0

            progress_data = {
                'state': 'completed',
                'progress': 100,
                'message': message,
                'timestamp': datetime.now()
            }

            self._notify_progress(channel_num, progress_data)
            logger.info(f"通道{channel_num}进度完成: {message}")

        except Exception as e:
            logger.error(f"完成通道{channel_num}进度失败: {e}")

    def reset_channel_progress(self, channel_num: int):
        """
        重置通道进度

        Args:
            channel_num: 通道号 (1-8)
        """
        try:
            # 新架构使用统一进度管理器重置
            self.unified_manager.reset_channel(channel_num)

            # 保留向后兼容
            with self.progress_lock:
                self.channel_progress[channel_num] = 0.0

            logger.debug(f"通道{channel_num}进度已重置")

        except Exception as e:
            logger.error(f"重置通道{channel_num}进度失败: {e}")

    def reset_all_progress(self):
        """重置所有通道进度"""
        try:
            with self.progress_lock:
                self.channel_progress = {i: 0.0 for i in range(1, 9)}

            # 移除UI更新时间控制相关缓存清理
            self.frequency_progress.clear()

            logger.info("所有通道进度已重置")

        except Exception as e:
            logger.error(f"重置所有进度失败: {e}")

    def get_channel_progress(self, channel_num: int) -> float:
        """
        获取通道当前进度

        Args:
            channel_num: 通道号 (1-8)

        Returns:
            进度百分比 (0-100)
        """
        return self.channel_progress.get(channel_num, 0.0)

    def get_all_progress(self) -> Dict[int, float]:
        """
        获取所有通道进度

        Returns:
            通道进度字典
        """
        return self.channel_progress.copy()

    def _should_update_ui(self, channel_num: int) -> bool:
        """
        🔧 已禁用：UI更新频率控制（移除强制限制，提高响应性）

        Args:
            channel_num: 通道号（保留参数以维持接口兼容性）

        Returns:
            始终返回True，允许实时更新
        """
        # 移除强制UI更新频率控制，始终允许更新
        _ = channel_num  # 避免未使用参数警告
        return True

    def _apply_progress_protection(self, channel_num: int, progress: float) -> float:
        """
        🔧 已简化：进度保护（移除强制单调性保护）

        Args:
            channel_num: 通道号
            progress: 新进度

        Returns:
            直接返回新进度值
        """
        # 移除强制进度单调性保护，允许自然进度更新
        with self.progress_lock:
            self.channel_progress[channel_num] = progress
            return progress

    def _notify_progress(self, channel_num: int, progress_data: Dict):
        """
        通知进度更新

        Args:
            channel_num: 通道号
            progress_data: 进度数据
        """
        if self.progress_callback:
            try:
                self.progress_callback(channel_num, progress_data)
            except Exception as e:
                logger.error(f"进度回调失败: {e}")

    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback
        logger.debug("进度回调函数已设置")

    def set_frequency_callback(self, callback: Callable):
        """设置频点回调函数"""
        self.frequency_callback = callback
        logger.debug("频点回调函数已设置")

    def get_progress_summary(self) -> Dict:
        """
        获取进度总结

        Returns:
            进度总结字典
        """
        try:
            total_progress = sum(self.channel_progress.values())
            avg_progress = total_progress / 8 if total_progress > 0 else 0

            completed_channels = [ch for ch, prog in self.channel_progress.items() if prog >= 100]
            testing_channels = [ch for ch, prog in self.channel_progress.items() if 0 < prog < 100]
            idle_channels = [ch for ch, prog in self.channel_progress.items() if prog == 0]

            return {
                'total_progress': total_progress,
                'average_progress': avg_progress,
                'completed_count': len(completed_channels),
                'testing_count': len(testing_channels),
                'idle_count': len(idle_channels),
                'completed_channels': completed_channels,
                'testing_channels': testing_channels,
                'idle_channels': idle_channels,
                'channel_progress': self.channel_progress.copy()
            }

        except Exception as e:
            logger.error(f"获取进度总结失败: {e}")
            return {}

    def set_ui_update_interval(self, interval: float):
        """
        🔧 已禁用：设置UI更新间隔（移除强制频率控制）

        Args:
            interval: 更新间隔（秒）- 保留参数以维持接口兼容性
        """
        # 移除UI更新间隔控制，不再限制更新频率
        _ = interval  # 避免未使用参数警告
        logger.info("UI更新间隔控制已禁用，允许实时更新")

    def fail_channel_progress(self, channel_num: int, message: str = "测试失败"):
        """
        通道进度失败

        Args:
            channel_num: 通道号 (1-8)
            message: 失败消息
        """
        try:
            progress_data = {
                'state': 'failed',
                'progress': self.channel_progress.get(channel_num, 0),
                'message': message,
                'timestamp': datetime.now()
            }

            self._notify_progress(channel_num, progress_data)
            logger.warning(f"通道{channel_num}进度失败: {message}")

        except Exception as e:
            logger.error(f"设置通道{channel_num}进度失败状态失败: {e}")

    def update_frequency_progress(self, channel_num: int, frequency: float,
                                freq_index: int, total_freqs: int,
                                status: str = "testing") -> bool:
        """
        更新频点进度

        Args:
            channel_num: 通道号 (1-8, 0表示所有通道)
            frequency: 当前频率
            freq_index: 频点索引
            total_freqs: 总频点数
            status: 频点状态 ("waiting", "testing", "completed")

        Returns:
            是否更新成功
        """
        try:
            logger.debug(f"频点进度更新: 通道{channel_num}, {frequency}Hz ({freq_index}/{total_freqs}) {status}")

            # 缓存频点进度信息
            freq_key = f"{channel_num}_{freq_index}"
            self.frequency_progress[freq_key] = {
                'frequency': frequency,
                'index': freq_index,
                'total': total_freqs,
                'status': status,
                'timestamp': datetime.now()
            }

            # 通知频点更新
            self._notify_frequency(channel_num, frequency, freq_index, total_freqs, status)

            logger.debug(f"频点进度更新: 通道{channel_num}, {frequency}Hz, {freq_index}/{total_freqs}, {status}")
            return True

        except Exception as e:
            logger.error(f"更新频点进度失败: {e}")
            return False

    def get_frequency_progress(self, channel_num: int) -> Optional[Dict]:
        """
        获取通道的频点进度信息

        Args:
            channel_num: 通道号 (1-8)

        Returns:
            频点进度信息或None
        """
        # 查找该通道最新的频点进度
        latest_freq = None
        latest_time = None

        for key, freq_info in self.frequency_progress.items():
            if key.startswith(f"{channel_num}_"):
                if latest_time is None or freq_info['timestamp'] > latest_time:
                    latest_freq = freq_info
                    latest_time = freq_info['timestamp']

        return latest_freq

    def _notify_frequency(self, channel_num: int, frequency: float,
                         current_index: int, total_count: int, status: str):
        """
        通知频点更新

        Args:
            channel_num: 通道号 (1-8, 0表示所有通道)
            frequency: 当前频点 (Hz)
            current_index: 当前频点索引 (从1开始)
            total_count: 总频点数量
            status: 频点状态 ("waiting", "testing", "completed")
        """
        logger.debug(f"频点通知: 通道{channel_num}, {frequency}Hz ({current_index}/{total_count}) {status}")

        if self.frequency_callback:
            try:
                self.frequency_callback(channel_num, frequency, current_index, total_count, status)
            except Exception as e:
                logger.error(f"频点回调失败: {e}")
        else:
            logger.debug("frequency_callback 为 None，无法调用")

    def debug_progress_info(self, channel_num: int, freq_index: int, total_freqs: int,
                          frequency: float, elapsed_time: float = 0):
        """
        输出进度计算调试信息

        Args:
            channel_num: 通道号
            freq_index: 频点索引
            total_freqs: 总频点数
            frequency: 当前频率
            elapsed_time: 已用时间
        """
        try:
            base_progress = ((freq_index - 1) / total_freqs) * 100
            freq_progress_range = 100 / total_freqs
            current_progress = self.calculate_channel_progress(channel_num, freq_index, total_freqs, elapsed_time)

            logger.info(f"   频率: {frequency}Hz, 频点索引: {freq_index}/{total_freqs}")
            logger.info(f"   基础进度: {base_progress:.1f}%")
            logger.info(f"   频点范围: {freq_progress_range:.1f}%")
            logger.info(f"   最终进度: {current_progress:.1f}%")
            logger.info(f"   已用时间: {elapsed_time:.1f}秒")

        except Exception as e:
            logger.error(f"输出进度调试信息失败: {e}")