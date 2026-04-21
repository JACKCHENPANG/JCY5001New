"""
统一进度管理器
负责整个测试系统的进度计算、更新和状态管理
确保进度的单调递增和线程安全
"""

import time
import threading
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProgressState:
    """进度状态数据类"""
    channel_num: int
    current_progress: float  # 当前进度 (0-100)
    max_progress: float     # 历史最高进度
    frequency_index: int    # 当前频点索引 (1-based)
    total_frequencies: int  # 总频点数
    current_frequency: Optional[float]  # 当前频率
    test_state: str        # 测试状态
    message: str           # 状态消息
    last_update: datetime  # 最后更新时间
    
    def __post_init__(self):
        """确保进度值的有效性"""
        self.current_progress = max(0, min(100, self.current_progress))
        self.max_progress = max(self.current_progress, self.max_progress)


class UnifiedProgressManager:
    """
    统一进度管理器
    
    设计原则：
    1. 单一数据源：所有进度计算都通过此管理器
    2. 单调递增：严格保证进度只能递增
    3. 线程安全：所有操作都是线程安全的
    4. 状态一致：确保所有组件的进度状态同步
    """
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        初始化统一进度管理器
        
        Args:
            progress_callback: 进度更新回调函数
        """
        self.progress_callback = progress_callback
        
        # 线程安全锁
        self._lock = threading.RLock()
        
        # 通道进度状态 {channel_num: ProgressState}
        self._channel_states: Dict[int, ProgressState] = {}
        
        # 测试配置
        self._test_config = {
            'start_progress': 0,      # 测试开始进度
            'end_progress': 100,      # 测试结束进度
            'frequency_weight': 0.9,  # 频点进度权重 (90%)
            'completion_weight': 0.1  # 完成进度权重 (10%)
        }
        
        # 测试时间管理
        self._test_start_time: Optional[float] = None
        self._estimated_duration: float = 0
        
        logger.debug("统一进度管理器初始化完成")
    
    def initialize_channel(self, channel_num: int, total_frequencies: int) -> bool:
        """
        初始化通道进度状态
        
        Args:
            channel_num: 通道号 (1-8)
            total_frequencies: 总频点数
            
        Returns:
            是否初始化成功
        """
        try:
            with self._lock:
                self._channel_states[channel_num] = ProgressState(
                    channel_num=channel_num,
                    current_progress=0.0,
                    max_progress=0.0,
                    frequency_index=0,
                    total_frequencies=total_frequencies,
                    current_frequency=None,
                    test_state='ready',
                    message='准备测试',
                    last_update=datetime.now()
                )
            
            logger.debug(f"通道{channel_num}进度状态初始化: {total_frequencies}个频点")
            return True
            
        except Exception as e:
            logger.error(f"初始化通道{channel_num}进度状态失败: {e}")
            return False
    
    def start_test(self, estimated_duration: float = 0) -> bool:
        """
        开始测试，启动进度计时
        
        Args:
            estimated_duration: 预估测试时长（秒）
            
        Returns:
            是否启动成功
        """
        try:
            with self._lock:
                self._test_start_time = time.time()
                self._estimated_duration = estimated_duration
            
            logger.info(f"测试开始，预估时长: {estimated_duration:.1f}秒")
            return True
            
        except Exception as e:
            logger.error(f"启动测试计时失败: {e}")
            return False
    
    def update_frequency_progress(self, channel_num: int, frequency: float, 
                                frequency_index: int, status: str = 'testing') -> bool:
        """
        更新频点进度
        
        Args:
            channel_num: 通道号 (1-8)
            frequency: 当前频率
            frequency_index: 频点索引 (1-based)
            status: 频点状态 ('starting', 'testing', 'completed')
            
        Returns:
            是否更新成功
        """
        try:
            with self._lock:
                if channel_num not in self._channel_states:
                    logger.warning(f"通道{channel_num}未初始化，跳过进度更新")
                    return False
                
                state = self._channel_states[channel_num]
                
                # 计算新进度
                new_progress = self._calculate_frequency_progress(
                    state, frequency_index, status
                )
                
                # 确保进度单调递增
                if new_progress > state.current_progress:
                    state.current_progress = new_progress
                    state.max_progress = max(state.max_progress, new_progress)
                    state.frequency_index = frequency_index
                    state.current_frequency = frequency
                    state.test_state = status
                    state.message = f'{status}: {frequency}Hz'
                    state.last_update = datetime.now()
                    
                    # 触发回调
                    self._notify_progress_update(channel_num, state)
                    
                    logger.debug(f"通道{channel_num}频点进度更新: {new_progress:.1f}% ({frequency}Hz)")
                    return True
                else:
                    logger.debug(f"通道{channel_num}进度未递增，跳过更新: {new_progress:.1f}% <= {state.current_progress:.1f}%")
                    return False
                    
        except Exception as e:
            logger.error(f"更新通道{channel_num}频点进度失败: {e}")
            return False
    
    def complete_frequency(self, channel_num: int, frequency: float, 
                          frequency_index: int) -> bool:
        """
        标记频点完成
        
        Args:
            channel_num: 通道号 (1-8)
            frequency: 完成的频率
            frequency_index: 频点索引 (1-based)
            
        Returns:
            是否更新成功
        """
        return self.update_frequency_progress(
            channel_num, frequency, frequency_index, 'completed'
        )
    
    def complete_test(self, channel_num: int) -> bool:
        """
        标记测试完成
        
        Args:
            channel_num: 通道号 (1-8)
            
        Returns:
            是否更新成功
        """
        try:
            with self._lock:
                if channel_num not in self._channel_states:
                    logger.warning(f"通道{channel_num}未初始化，无法完成测试")
                    return False
                
                state = self._channel_states[channel_num]
                
                # 设置为100%完成
                state.current_progress = 100.0
                state.max_progress = 100.0
                state.test_state = 'completed'
                state.message = '测试完成'
                state.last_update = datetime.now()
                
                # 触发回调
                self._notify_progress_update(channel_num, state)
                
                logger.info(f"通道{channel_num}测试完成")
                return True
                
        except Exception as e:
            logger.error(f"完成通道{channel_num}测试失败: {e}")
            return False
    
    def reset_channel(self, channel_num: int) -> bool:
        """
        重置通道进度
        
        Args:
            channel_num: 通道号 (1-8)
            
        Returns:
            是否重置成功
        """
        try:
            with self._lock:
                if channel_num in self._channel_states:
                    state = self._channel_states[channel_num]
                    total_frequencies = state.total_frequencies
                    
                    # 重新初始化状态
                    self._channel_states[channel_num] = ProgressState(
                        channel_num=channel_num,
                        current_progress=0.0,
                        max_progress=0.0,
                        frequency_index=0,
                        total_frequencies=total_frequencies,
                        current_frequency=None,
                        test_state='ready',
                        message='准备测试',
                        last_update=datetime.now()
                    )
                    
                    # 触发回调
                    self._notify_progress_update(channel_num, self._channel_states[channel_num])
                    
                    logger.debug(f"通道{channel_num}进度已重置")
                    return True
                else:
                    logger.warning(f"通道{channel_num}不存在，无法重置")
                    return False
                    
        except Exception as e:
            logger.error(f"重置通道{channel_num}进度失败: {e}")
            return False
    
    def reset_all(self) -> bool:
        """
        重置所有通道进度
        
        Returns:
            是否重置成功
        """
        try:
            with self._lock:
                for channel_num in list(self._channel_states.keys()):
                    self.reset_channel(channel_num)
                
                # 重置测试时间
                self._test_start_time = None
                self._estimated_duration = 0
                
                logger.info("🔄 [统一进度管理器] 所有通道进度已重置，清除进度状态缓存")
                return True

        except Exception as e:
            logger.error(f"重置所有进度失败: {e}")
            return False

    def force_reset_channel_progress(self, channel_num: int, new_progress: float = 0.0) -> bool:
        """
        强制重置通道进度，允许进度回退（用于测试重新开始）

        Args:
            channel_num: 通道号 (1-8)
            new_progress: 新的进度值

        Returns:
            是否重置成功
        """
        try:
            with self._lock:
                if channel_num in self._channel_states:
                    state = self._channel_states[channel_num]
                    state.current_progress = new_progress
                    state.max_progress = new_progress
                    state.frequency_index = 0
                    state.current_frequency = None
                    state.test_state = 'ready'
                    state.message = '准备测试'
                    state.last_update = datetime.now()

                    logger.info(f"🔄 [统一进度管理器] 通道{channel_num}进度强制重置: {new_progress}%")
                    return True
                else:
                    logger.warning(f"通道{channel_num}不存在，无法强制重置")
                    return False

        except Exception as e:
            logger.error(f"强制重置通道{channel_num}进度失败: {e}")
            return False
    
    def get_channel_progress(self, channel_num: int) -> Optional[ProgressState]:
        """
        获取通道进度状态
        
        Args:
            channel_num: 通道号 (1-8)
            
        Returns:
            进度状态或None
        """
        with self._lock:
            return self._channel_states.get(channel_num)
    
    def get_all_progress(self) -> Dict[int, ProgressState]:
        """
        获取所有通道进度状态
        
        Returns:
            所有通道的进度状态
        """
        with self._lock:
            return self._channel_states.copy()
    
    def _calculate_frequency_progress(self, state: ProgressState, 
                                    frequency_index: int, status: str) -> float:
        """
        计算频点进度
        
        Args:
            state: 当前状态
            frequency_index: 频点索引 (1-based)
            status: 频点状态
            
        Returns:
            计算的进度值 (0-100)
        """
        if state.total_frequencies <= 0:
            return 0.0
        
        # 基础进度：基于已完成的频点数量
        if status == 'completed':
            # 频点完成：使用当前频点索引
            completed_count = frequency_index
        else:
            # 频点进行中：使用前一个频点的完成数量
            completed_count = max(0, frequency_index - 1)
        
        # 计算基础进度 (0-90%)
        base_progress = (completed_count / state.total_frequencies) * 90.0
        
        # 添加当前频点的部分进度 (0-10%)
        if status == 'starting':
            current_freq_progress = 2.0  # 启动阶段 2%
        elif status == 'testing':
            current_freq_progress = 5.0  # 测试阶段 5%
        elif status == 'completed':
            current_freq_progress = 10.0  # 完成阶段 10%
        else:
            current_freq_progress = 0.0
        
        # 当前频点进度权重
        freq_weight = 10.0 / state.total_frequencies
        current_progress = min(current_freq_progress, freq_weight)
        
        total_progress = base_progress + current_progress
        
        # 确保进度在有效范围内
        return max(0.0, min(100.0, total_progress))
    
    def _notify_progress_update(self, channel_num: int, state: ProgressState):
        """
        通知进度更新
        
        Args:
            channel_num: 通道号
            state: 进度状态
        """
        if self.progress_callback:
            try:
                progress_data = {
                    'state': state.test_state,
                    'progress': int(state.current_progress),
                    'message': state.message,
                    'current_frequency': state.current_frequency,
                    'frequency_index': state.frequency_index,
                    'total_frequencies': state.total_frequencies,
                    'timestamp': state.last_update
                }
                
                self.progress_callback(channel_num, progress_data)

            except Exception as e:
                logger.error(f"进度更新回调失败: {e}")

    def set_channel_exception(self, channel_num: int, error_message: str) -> bool:
        """
        设置通道异常状态

        Args:
            channel_num: 通道号 (1-8)
            error_message: 错误消息

        Returns:
            是否设置成功
        """
        try:
            with self._lock:
                if channel_num not in self._channel_states:
                    logger.warning(f"通道{channel_num}未初始化，无法设置异常状态")
                    return False

                state = self._channel_states[channel_num]
                state.test_state = 'exception'
                state.message = f'异常: {error_message}'
                state.last_update = datetime.now()

                # 触发回调
                self._notify_progress_update(channel_num, state)

                logger.warning(f"通道{channel_num}设置为异常状态: {error_message}")
                return True

        except Exception as e:
            logger.error(f"设置通道{channel_num}异常状态失败: {e}")
            return False

    def is_channel_active(self, channel_num: int) -> bool:
        """
        检查通道是否处于活跃状态

        Args:
            channel_num: 通道号 (1-8)

        Returns:
            是否活跃
        """
        with self._lock:
            if channel_num not in self._channel_states:
                return False

            state = self._channel_states[channel_num]
            return state.test_state in ['ready', 'starting', 'testing']

    def get_overall_progress(self) -> Dict[str, Any]:
        """
        获取整体测试进度摘要

        Returns:
            整体进度信息
        """
        try:
            with self._lock:
                if not self._channel_states:
                    return {
                        'total_channels': 0,
                        'active_channels': 0,
                        'completed_channels': 0,
                        'exception_channels': 0,
                        'average_progress': 0.0,
                        'test_duration': 0.0
                    }

                total_channels = len(self._channel_states)
                active_channels = 0
                completed_channels = 0
                exception_channels = 0
                total_progress = 0.0

                for state in self._channel_states.values():
                    total_progress += state.current_progress

                    if state.test_state in ['ready', 'starting', 'testing']:
                        active_channels += 1
                    elif state.test_state == 'completed':
                        completed_channels += 1
                    elif state.test_state == 'exception':
                        exception_channels += 1

                average_progress = total_progress / total_channels if total_channels > 0 else 0.0

                # 计算测试时长
                test_duration = 0.0
                if self._test_start_time:
                    test_duration = time.time() - self._test_start_time

                return {
                    'total_channels': total_channels,
                    'active_channels': active_channels,
                    'completed_channels': completed_channels,
                    'exception_channels': exception_channels,
                    'average_progress': round(average_progress, 1),
                    'test_duration': round(test_duration, 1)
                }

        except Exception as e:
            logger.error(f"获取整体进度失败: {e}")
            return {}

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标

        Returns:
            性能指标信息
        """
        try:
            with self._lock:
                metrics = {
                    'update_count': 0,
                    'average_update_interval': 0.0,
                    'last_update_time': None,
                    'channels_status': {}
                }

                for channel_num, state in self._channel_states.items():
                    metrics['channels_status'][channel_num] = {
                        'progress': state.current_progress,
                        'max_progress': state.max_progress,
                        'frequency_index': state.frequency_index,
                        'total_frequencies': state.total_frequencies,
                        'state': state.test_state,
                        'last_update': state.last_update.isoformat()
                    }

                return metrics

        except Exception as e:
            logger.error(f"获取性能指标失败: {e}")
            return {}

    def validate_progress_consistency(self) -> Dict[str, Any]:
        """
        验证进度一致性

        Returns:
            验证结果
        """
        try:
            with self._lock:
                issues = []

                for channel_num, state in self._channel_states.items():
                    # 检查进度值范围
                    if not (0 <= state.current_progress <= 100):
                        issues.append(f"通道{channel_num}进度值超出范围: {state.current_progress}")

                    # 检查最大进度一致性
                    if state.current_progress > state.max_progress:
                        issues.append(f"通道{channel_num}当前进度超过最大进度: {state.current_progress} > {state.max_progress}")

                    # 检查频点索引合理性
                    if state.frequency_index > state.total_frequencies:
                        issues.append(f"通道{channel_num}频点索引超出范围: {state.frequency_index} > {state.total_frequencies}")

                return {
                    'is_consistent': len(issues) == 0,
                    'issues': issues,
                    'check_time': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"验证进度一致性失败: {e}")
            return {'is_consistent': False, 'issues': [f"验证失败: {e}"]}
