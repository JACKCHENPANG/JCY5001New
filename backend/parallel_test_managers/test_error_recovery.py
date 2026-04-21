# -*- coding: utf-8 -*-
"""
测试错误恢复器
从ParallelStaggeredTestManager中提取的错误恢复相关功能

职责：
- 错误检测处理
- 通道异常恢复
- 重试机制管理
- 错误状态跟踪

Author: Jack
Date: 2025-01-30
"""

import logging
import time
from typing import Dict, List, Optional, Set, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryAction(Enum):
    """恢复动作"""
    RETRY = "retry"
    SKIP_CHANNEL = "skip_channel"
    SKIP_FREQUENCY = "skip_frequency"
    ABORT_TEST = "abort_test"
    CONTINUE = "continue"


class TestErrorRecovery:
    """
    测试错误恢复器
    
    职责：
    - 检测和处理测试错误
    - 管理通道异常状态
    - 实施错误恢复策略
    - 跟踪错误统计
    """
    
    def __init__(self, comm_manager):
        """
        初始化测试错误恢复器
        
        Args:
            comm_manager: 通信管理器
        """
        self.comm_manager = comm_manager
        
        # 错误跟踪
        self.channel_errors: Dict[int, List[Dict[str, Any]]] = {}
        self.frequency_errors: Dict[float, List[Dict[str, Any]]] = {}
        self.skipped_channels: Set[int] = set()
        self.retry_counts: Dict[str, int] = {}
        
        # 配置参数
        self.max_retries = 3
        self.retry_delay = 1.0  # 秒
        self.skip_threshold = 5  # 连续错误次数阈值
        
        # 状态码管理器
        from backend.device_status_manager import DeviceStatusManager
        self.status_manager = DeviceStatusManager()
        
        logger.debug("测试错误恢复器初始化完成")
    
    def set_recovery_config(self, max_retries: int = 3, retry_delay: float = 1.0, skip_threshold: int = 5):
        """
        设置恢复配置
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟时间
            skip_threshold: 跳过阈值
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.skip_threshold = skip_threshold
        
        logger.info(f"错误恢复配置更新: 最大重试{max_retries}次, 延迟{retry_delay}秒, 跳过阈值{skip_threshold}")
    
    def handle_channel_error(self, channel_index: int, error_code: int, frequency: float, context: str = "") -> RecoveryAction:
        """
        处理通道错误
        
        Args:
            channel_index: 通道索引
            error_code: 错误状态码
            frequency: 当前频率
            context: 错误上下文
            
        Returns:
            建议的恢复动作
        """
        try:
            channel_num = channel_index + 1
            
            # 获取状态码信息
            status_info = self.status_manager.get_channel_status_info(channel_index, error_code)
            
            # 记录错误
            error_record = {
                'timestamp': time.time(),
                'error_code': error_code,
                'frequency': frequency,
                'context': context,
                'description': status_info.description,
                'severity': status_info.severity.value,
                'should_skip': status_info.should_skip
            }
            
            # 添加到通道错误记录
            if channel_index not in self.channel_errors:
                self.channel_errors[channel_index] = []
            self.channel_errors[channel_index].append(error_record)
            
            # 添加到频率错误记录
            if frequency not in self.frequency_errors:
                self.frequency_errors[frequency] = []
            self.frequency_errors[frequency].append(error_record)
            
            logger.warning(f"通道{channel_num}错误: {status_info.description} (0x{error_code:04X}) @ {frequency}Hz")
            
            # 根据状态码决定恢复动作
            if status_info.should_skip:
                # 需要跳过的状态码（如0x0003）
                self.skipped_channels.add(channel_index)
                logger.warning(f"通道{channel_num}被标记为跳过: {status_info.description}")
                return RecoveryAction.SKIP_CHANNEL
            
            # 根据错误严重程度决定动作
            if status_info.severity == ErrorSeverity.CRITICAL:
                logger.error(f"通道{channel_num}严重错误，中止测试")
                return RecoveryAction.ABORT_TEST
            elif status_info.severity == ErrorSeverity.HIGH:
                # 检查是否超过跳过阈值
                recent_errors = self._get_recent_channel_errors(channel_index, time_window=300)  # 5分钟内
                if len(recent_errors) >= self.skip_threshold:
                    self.skipped_channels.add(channel_index)
                    logger.warning(f"通道{channel_num}错误过多，跳过该通道")
                    return RecoveryAction.SKIP_CHANNEL
                else:
                    return RecoveryAction.RETRY
            elif status_info.severity == ErrorSeverity.MEDIUM:
                return RecoveryAction.RETRY
            else:
                return RecoveryAction.CONTINUE
                
        except Exception as e:
            logger.error(f"处理通道{channel_index + 1}错误失败: {e}")
            return RecoveryAction.CONTINUE
    
    def should_retry_operation(self, operation_key: str) -> bool:
        """
        检查是否应该重试操作
        
        Args:
            operation_key: 操作键值
            
        Returns:
            是否应该重试
        """
        try:
            current_count = self.retry_counts.get(operation_key, 0)
            
            if current_count < self.max_retries:
                self.retry_counts[operation_key] = current_count + 1
                logger.debug(f"重试操作 {operation_key}: {current_count + 1}/{self.max_retries}")
                return True
            else:
                logger.warning(f"操作 {operation_key} 达到最大重试次数 {self.max_retries}")
                return False
                
        except Exception as e:
            logger.error(f"检查重试状态失败: {e}")
            return False
    
    def reset_retry_count(self, operation_key: str):
        """
        重置重试计数
        
        Args:
            operation_key: 操作键值
        """
        if operation_key in self.retry_counts:
            del self.retry_counts[operation_key]
            logger.debug(f"重置操作 {operation_key} 的重试计数")
    
    def wait_for_retry(self):
        """等待重试延迟"""
        if self.retry_delay > 0:
            logger.debug(f"等待重试延迟: {self.retry_delay}秒")
            time.sleep(self.retry_delay)
    
    def is_channel_skipped(self, channel_index: int) -> bool:
        """
        检查通道是否被跳过
        
        Args:
            channel_index: 通道索引
            
        Returns:
            是否被跳过
        """
        return channel_index in self.skipped_channels
    
    def get_active_channels(self, enabled_channels: List[int]) -> List[int]:
        """
        获取活跃通道列表（排除被跳过的通道）
        
        Args:
            enabled_channels: 启用的通道列表
            
        Returns:
            活跃通道列表
        """
        try:
            active_channels = [ch for ch in enabled_channels if ch not in self.skipped_channels]
            
            if len(active_channels) != len(enabled_channels):
                skipped_count = len(enabled_channels) - len(active_channels)
                logger.info(f"活跃通道: {len(active_channels)}个, 跳过通道: {skipped_count}个")
            
            return active_channels
            
        except Exception as e:
            logger.error(f"获取活跃通道失败: {e}")
            return enabled_channels
    
    def _get_recent_channel_errors(self, channel_index: int, time_window: float = 300) -> List[Dict[str, Any]]:
        """
        获取指定时间窗口内的通道错误
        
        Args:
            channel_index: 通道索引
            time_window: 时间窗口（秒）
            
        Returns:
            最近的错误列表
        """
        try:
            if channel_index not in self.channel_errors:
                return []
            
            current_time = time.time()
            recent_errors = []
            
            for error in self.channel_errors[channel_index]:
                if current_time - error['timestamp'] <= time_window:
                    recent_errors.append(error)
            
            return recent_errors
            
        except Exception as e:
            logger.error(f"获取通道{channel_index + 1}最近错误失败: {e}")
            return []
    
    def attempt_channel_recovery(self, channel_index: int) -> bool:
        """
        尝试恢复通道
        
        Args:
            channel_index: 通道索引
            
        Returns:
            是否恢复成功
        """
        try:
            channel_num = channel_index + 1
            logger.info(f"尝试恢复通道{channel_num}")
            
            # 尝试重置通道状态
            if hasattr(self.comm_manager, 'reset_channel_status'):
                if self.comm_manager.reset_channel_status(channel_index):
                    logger.info(f"通道{channel_num}状态重置成功")
                    
                    # 从跳过列表中移除
                    if channel_index in self.skipped_channels:
                        self.skipped_channels.remove(channel_index)
                        logger.info(f"通道{channel_num}已从跳过列表中移除")
                    
                    return True
                else:
                    logger.warning(f"通道{channel_num}状态重置失败")
            
            # 尝试其他恢复方法
            # 可以在这里添加更多恢复策略
            
            return False
            
        except Exception as e:
            logger.error(f"恢复通道{channel_index + 1}失败: {e}")
            return False
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        获取错误统计信息
        
        Returns:
            错误统计字典
        """
        try:
            stats = {
                'total_channel_errors': sum(len(errors) for errors in self.channel_errors.values()),
                'total_frequency_errors': sum(len(errors) for errors in self.frequency_errors.values()),
                'skipped_channels_count': len(self.skipped_channels),
                'skipped_channels': list(self.skipped_channels),
                'active_retry_operations': len(self.retry_counts),
                'channel_error_counts': {},
                'frequency_error_counts': {},
                'error_severity_distribution': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
            }
            
            # 统计每个通道的错误数
            for channel_index, errors in self.channel_errors.items():
                channel_num = channel_index + 1
                stats['channel_error_counts'][channel_num] = len(errors)
                
                # 统计错误严重程度分布
                for error in errors:
                    severity = error.get('severity', 'low')
                    if severity in stats['error_severity_distribution']:
                        stats['error_severity_distribution'][severity] += 1
            
            # 统计每个频率的错误数
            for frequency, errors in self.frequency_errors.items():
                stats['frequency_error_counts'][frequency] = len(errors)
            
            return stats
            
        except Exception as e:
            logger.error(f"获取错误统计失败: {e}")
            return {}
    
    def get_channel_error_history(self, channel_index: int) -> List[Dict[str, Any]]:
        """
        获取通道错误历史
        
        Args:
            channel_index: 通道索引
            
        Returns:
            错误历史列表
        """
        try:
            if channel_index in self.channel_errors:
                return self.channel_errors[channel_index].copy()
            else:
                return []
                
        except Exception as e:
            logger.error(f"获取通道{channel_index + 1}错误历史失败: {e}")
            return []
    
    def clear_channel_errors(self, channel_index: Optional[int] = None):
        """
        清除通道错误记录
        
        Args:
            channel_index: 通道索引，如果为None则清除所有
        """
        try:
            if channel_index is not None:
                if channel_index in self.channel_errors:
                    del self.channel_errors[channel_index]
                    logger.info(f"清除通道{channel_index + 1}错误记录")
            else:
                self.channel_errors.clear()
                logger.info("清除所有通道错误记录")
                
        except Exception as e:
            logger.error(f"清除错误记录失败: {e}")
    
    def reset(self):
        """重置错误恢复器"""
        try:
            self.channel_errors.clear()
            self.frequency_errors.clear()
            self.skipped_channels.clear()
            self.retry_counts.clear()
            
            logger.debug("测试错误恢复器已重置")
            
        except Exception as e:
            logger.error(f"重置错误恢复器失败: {e}")
    
    def export_error_report(self) -> Dict[str, Any]:
        """
        导出错误报告
        
        Returns:
            错误报告字典
        """
        try:
            report = {
                'timestamp': time.time(),
                'statistics': self.get_error_statistics(),
                'channel_errors': self.channel_errors.copy(),
                'frequency_errors': self.frequency_errors.copy(),
                'skipped_channels': list(self.skipped_channels),
                'retry_counts': self.retry_counts.copy(),
                'config': {
                    'max_retries': self.max_retries,
                    'retry_delay': self.retry_delay,
                    'skip_threshold': self.skip_threshold
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"导出错误报告失败: {e}")
            return {}