#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志去重器

负责检测和防止重复的日志记录，提升日志质量和系统性能

Author: Jack
Date: 2025-06-21
"""

import logging
import time
import hashlib
from typing import Dict, Set, Optional, Tuple
from collections import defaultdict, deque
from threading import Lock
from PyQt5.QtCore import QObject, pyqtSignal


class LogDeduplicator(QObject):
    """日志去重器"""
    
    # 信号定义
    duplicate_detected = pyqtSignal(str, int)  # 检测到重复日志信号
    
    def __init__(self, window_size: int = 10, time_window: int = 60):
        """
        初始化日志去重器
        
        Args:
            window_size: 滑动窗口大小（记录最近N条日志）
            time_window: 时间窗口（秒，在此时间内的重复日志会被抑制）
        """
        super().__init__()
        
        self.window_size = window_size
        self.time_window = time_window
        
        # 日志记录存储
        self._recent_logs = deque(maxlen=window_size)
        self._log_timestamps = {}
        self._duplicate_counts = defaultdict(int)
        
        # 优化特殊处理的日志模式（基于日志分析结果）
        self._suppression_patterns = {
            'initialization': {
                'patterns': [
                    '初始化完成',
                    '管理器初始化完成',
                    '已应用',
                    '设置完成',
                    '✅.*初始化完成',
                    '✅.*管理器初始化',
                    '✅.*已初始化'
                ],
                'max_count': 1,  # 优化初始化日志只允许1次
                'time_window': 300  # 优化延长时间窗口到5分钟
            },
            'voltage_reading': {
                'patterns': [
                    '群发读取电池电压成功',
                    '通道.*电压: .*V',
                    'backend.data_read_manager.*电压',
                    '电压读取完成',
                    '有效通道.*电压'
                ],
                'max_count': 1,  # 新增每分钟只记录1次电压读取
                'time_window': 60
            },
            'battery_detection_verbose': {
                'patterns': [
                    '🔋 通道.*状态已更新',
                    '🔋 处理.*状态变化',
                    '🔋 通道.*检测到新电池插入',
                    '🔋 通知状态更新',
                    '通道.*电池状态变化',
                    '电池状态更新.*电压'
                ],
                'max_count': 1,  # 新增每个通道状态变化只记录1次
                'time_window': 30
            },
            'network_retry': {
                'patterns': [
                    'urllib3.connectionpool.*Retrying',
                    'Connection.*timed out',
                    '心跳服务器不可用',
                    '心跳认证失败',
                    'ConnectTimeoutError',
                    'connection broken'
                ],
                'max_count': 2,  # 新增每5分钟最多2次网络重试日志
                'time_window': 300
            },
            'ui_updates': {
                'patterns': [
                    '配置值未变化，跳过更新',
                    '.*显示更新完成',
                    '.*UI.*已更新',
                    '.*状态保持',
                    '设备状态保持',
                    '批次信息显示刷新完成'
                ],
                'max_count': 1,  # 新增UI更新日志每2分钟最多1次
                'time_window': 120
            },
            'serial_debug': {
                'patterns': [
                    '数据已发送:',
                    '接收到数据:',
                    '接收完成，总长度',
                    '通信失败计数已重置',
                    'backend.serial_connection_manager'
                ],
                'time_window': 60
            },
            'startup_optimization': {
                'patterns': [
                    '🚀 启动性能优化器初始化完成',
                    '⚡ 快速启动管理器初始化完成',
                    '启动性能优化器初始化完成'
                ],
                'max_count': 1,  # 启动优化器只记录一次
                'time_window': 300
            },
            'outlier_detection': {
                'patterns': [
                    '离群检测数据库表结构初始化完成',
                    '离群检测管理器初始化完成',
                    'outlier_detection_manager.*初始化完成'
                ],
                'max_count': 1,  # 优化离群检测管理器只记录一次
                'time_window': 300
            },
            'window_layout': {
                'patterns': [
                    '窗口布局管理器初始化完成',
                    'window_layout_manager.*初始化完成'
                ],
                'max_count': 1,  # 窗口布局管理器只记录一次
                'time_window': 300
            },
            'device_status': {
                'patterns': [
                    '设备状态码管理器初始化完成',
                    'device_status_manager.*初始化完成'
                ],
                'max_count': 1,  # 设备状态管理器只记录一次
                'time_window': 300
            },
            'state_transition': {
                'patterns': [
                    '状态转换无效',
                    'idle -> idle',
                    '计时器未在运行'
                ],
                'max_count': 1,  # 状态转换错误只记录一次
                'time_window': 60
            },
            'device_command': {
                'patterns': [
                    '停止8个通道',
                    '停止阻抗测量',
                    '发送停止命令'
                ],
                'max_count': 1,  # 设备命令在短时间内只记录一次
                'time_window': 5
            },
            'database_operation': {
                'patterns': [
                    '数据库表结构初始化完成',
                    '数据库迁移完成',
                    '数据库管理器初始化完成',
                    '✅ 全局数据库管理器初始化完成'
                ],
                'max_count': 1,  # 数据库操作只记录一次
                'time_window': 300  # 优化延长时间窗口
            },
            'test_result_manager': {
                'patterns': [
                    '测试结果管理器初始化完成',
                    'test_result_manager.*初始化完成',
                    '✅ 测试结果管理器初始化完成'
                ],
                'max_count': 1,  # 测试结果管理器只记录一次
                'time_window': 300
            },
            'config_loading': {
                'patterns': [
                    '🔧 离群检测在配置中已禁用，跳过管理器创建',
                    '🔧 强制刷新UI: 离群检测在配置中已禁用',
                    '离群检测在配置中已禁用'
                ],
                'max_count': 1,  # 配置加载信息只记录一次
                'time_window': 300
            },
            'ui_status_update': {
                'patterns': [
                    '离群检测设置已加载: 禁用',
                    '✅ 离群检测设置已加载并更新UI: 禁用',
                    '所有通道离群检测状态已更新为 禁用'
                ],
                'max_count': 1,  # UI状态更新只记录一次
                'time_window': 300
            },
            'channel_data_warnings': {
                'patterns': [
                    '通道.*电压值无效',
                    '通道.*接收到0值',
                    '数据无效.*跳过打印',
                    '阻抗数据管理器未初始化',
                    '未找到通道容器组件',
                    '测试结果管理器未找到'
                ],
                'max_count': 3,  # 通道数据警告允许3次
                'time_window': 60
            },
            'test_flow_warnings': {
                'patterns': [
                    '批次信息组件未找到',
                    '电池码列表为空',
                    '测试开始时间未正确设置'
                ],
                'max_count': 2,  # 测试流程警告允许2次
                'time_window': 120
            },
            'auto_battery_code': {
                'patterns': [
                    '🎯 自动生成完成: 共生成.*个电池码',
                    '自动生成电池码',
                    '电池码自动生成完成'
                ],
                'max_count': 1,  # 新增电池码生成日志每次测试只记录1次
                'time_window': 180
            },
            'device_communication': {
                'patterns': [
                    '设备通信正常',
                    '串口连接状态检查',
                    '设备响应正常',
                    '通信状态良好'
                ],
                'max_count': 2,  # 新增设备通信状态每5分钟最多2次
                'time_window': 300
            },
            'test_progress': {
                'patterns': [
                    '测试进度更新',
                    '进度条更新',
                    '测试状态更新',
                    '进度显示刷新'
                ],
                'max_count': 5,  # 新增测试进度更新每分钟最多5次
                'time_window': 60
            },
            'memory_cleanup': {
                'patterns': [
                    '内存清理完成',
                    '缓存清理完成',
                    '临时文件清理',
                    '垃圾回收完成'
                ],
                'max_count': 1,  # 新增内存清理日志每10分钟最多1次
                'time_window': 600
            },
            'config_validation': {
                'patterns': [
                    '配置验证通过',
                    '参数验证完成',
                    '设置验证成功',
                    '配置文件检查完成'
                ],
                'max_count': 1,  # 新增配置验证每5分钟最多1次
                'time_window': 300
            }
        }
        
        # 线程安全锁
        self._lock = Lock()
        
        self.logger = logging.getLogger(__name__)
        self.logger.debug("日志去重器初始化完成")
    
    def _generate_log_hash(self, message: str, level: str = 'INFO') -> str:
        """
        生成日志消息的哈希值
        
        Args:
            message: 日志消息
            level: 日志级别
            
        Returns:
            日志哈希值
        """
        # 移除时间戳和动态内容，只保留核心消息
        clean_message = self._clean_message(message)
        hash_input = f"{level}:{clean_message}" if level else clean_message
        return hashlib.md5(hash_input.encode('utf-8')).hexdigest()[:8]
    
    def _clean_message(self, message: str) -> str:
        """
        清理日志消息，移除动态内容
        
        Args:
            message: 原始日志消息
            
        Returns:
            清理后的消息
        """
        import re
        
        # 移除时间戳
        message = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}', '', message)
        
        # 移除具体的数值（保留模式）
        message = re.sub(r'\d+\.\d+秒', 'X.X秒', message)
        message = re.sub(r'\d+个', 'X个', message)
        message = re.sub(r'ID[=:]\s*\d+', 'ID=X', message)
        message = re.sub(r'通道\d+', '通道X', message)
        
        # 移除具体的文件路径
        message = re.sub(r'[a-zA-Z]:[\\\/][^\\\/\s]+', 'PATH', message)
        
        # 移除硬件指纹等唯一标识
        message = re.sub(r'[a-f0-9]{8,}', 'HASH', message)
        
        return message.strip()
    
    def _match_suppression_pattern(self, message: str) -> Optional[str]:
        """
        检查消息是否匹配抑制模式

        Args:
            message: 日志消息

        Returns:
            匹配的模式类型，如果没有匹配返回None
        """
        import re

        for pattern_type, config in self._suppression_patterns.items():
            for pattern in config['patterns']:
                # 支持正则表达式模式（包含.*的模式）
                if '.*' in pattern or pattern.startswith('^') or pattern.endswith('$'):
                    try:
                        if re.search(pattern, message):
                            return pattern_type
                    except re.error:
                        # 如果正则表达式无效，回退到字符串匹配
                        if pattern in message:
                            return pattern_type
                else:
                    # 普通字符串匹配
                    if pattern in message:
                        return pattern_type
        return None
    
    def should_suppress_log(self, message: str, level: str = 'INFO') -> bool:
        """
        检查是否应该抑制此日志
        
        Args:
            message: 日志消息
            level: 日志级别
            
        Returns:
            是否应该抑制日志
        """
        with self._lock:
            current_time = time.time()
            log_hash = self._generate_log_hash(message, level)
            
            # 检查是否匹配特殊抑制模式
            pattern_type = self._match_suppression_pattern(message)
            if pattern_type:
                return self._check_pattern_suppression(
                    log_hash, pattern_type, current_time
                )
            
            # 通用重复检查
            return self._check_general_duplication(
                log_hash, message, current_time
            )
    
    def _check_pattern_suppression(self, log_hash: str, pattern_type: str, 
                                 current_time: float) -> bool:
        """
        检查特定模式的抑制规则
        
        Args:
            log_hash: 日志哈希
            pattern_type: 模式类型
            current_time: 当前时间
            
        Returns:
            是否应该抑制
        """
        config = self._suppression_patterns[pattern_type]
        max_count = config['max_count']
        time_window = config['time_window']
        
        # 检查时间窗口内的计数
        pattern_key = f"{pattern_type}:{log_hash}"
        
        if pattern_key in self._log_timestamps:
            last_time = self._log_timestamps[pattern_key]
            if current_time - last_time < time_window:
                # 在时间窗口内，检查计数
                self._duplicate_counts[pattern_key] += 1
                if self._duplicate_counts[pattern_key] > max_count:
                    self.duplicate_detected.emit(pattern_type, 
                                               self._duplicate_counts[pattern_key])
                    return True
            else:
                # 超出时间窗口，重置计数
                self._duplicate_counts[pattern_key] = 1
        else:
            self._duplicate_counts[pattern_key] = 1
        
        self._log_timestamps[pattern_key] = current_time
        return False
    
    def _check_general_duplication(self, log_hash: str, message: str,
                                 current_time: float) -> bool:
        """
        检查通用重复规则

        Args:
            log_hash: 日志哈希
            message: 日志消息
            current_time: 当前时间

        Returns:
            是否应该抑制
        """
        # 检查时间窗口内的重复
        if log_hash in self._log_timestamps:
            last_time = self._log_timestamps[log_hash]
            if current_time - last_time < self.time_window:
                # 在时间窗口内，增加计数
                self._duplicate_counts[log_hash] += 1
                if self._duplicate_counts[log_hash] > 2:  # 允许最多2次重复（第3次开始抑制）
                    return True
            else:
                # 超出时间窗口，重置计数
                self._duplicate_counts[log_hash] = 1
        else:
            # 首次出现，初始化计数
            self._duplicate_counts[log_hash] = 1

        # 检查滑动窗口
        if log_hash in self._recent_logs:
            # 已在滑动窗口中，可能是重复
            pass
        else:
            # 记录到滑动窗口
            self._recent_logs.append(log_hash)

        # 更新时间戳
        self._log_timestamps[log_hash] = current_time

        return False
    
    def get_suppression_stats(self) -> Dict:
        """
        获取抑制统计信息
        
        Returns:
            抑制统计数据
        """
        with self._lock:
            stats = {
                'total_patterns': len(self._suppression_patterns),
                'active_suppressions': len(self._duplicate_counts),
                'recent_logs_count': len(self._recent_logs),
                'pattern_stats': {}
            }
            
            for pattern_type in self._suppression_patterns:
                pattern_count = sum(
                    count for key, count in self._duplicate_counts.items()
                    if key.startswith(f"{pattern_type}:")
                )
                stats['pattern_stats'][pattern_type] = pattern_count
            
            return stats
    
    def reset_suppression(self):
        """重置抑制状态"""
        with self._lock:
            self._recent_logs.clear()
            self._log_timestamps.clear()
            self._duplicate_counts.clear()
            self.logger.info("日志去重器状态已重置")
    
    def add_suppression_pattern(self, pattern_type: str, patterns: list, 
                              max_count: int = 1, time_window: int = 60):
        """
        添加新的抑制模式
        
        Args:
            pattern_type: 模式类型
            patterns: 匹配模式列表
            max_count: 最大允许次数
            time_window: 时间窗口（秒）
        """
        self._suppression_patterns[pattern_type] = {
            'patterns': patterns,
            'max_count': max_count,
            'time_window': time_window
        }
        self.logger.info(f"添加日志抑制模式: {pattern_type}")


class LogDedupFilter(logging.Filter):
    """日志去重过滤器"""
    
    def __init__(self, deduplicator: LogDeduplicator):
        """
        初始化过滤器
        
        Args:
            deduplicator: 日志去重器实例
        """
        super().__init__()
        self.deduplicator = deduplicator
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        过滤日志记录

        Args:
            record: 日志记录

        Returns:
            是否允许记录此日志
        """
        try:
            message = record.getMessage()
            level = record.levelname

            # 检查是否应该抑制
            should_suppress = self.deduplicator.should_suppress_log(message, level)

            return not should_suppress

        except Exception as e:
            # 过滤器出错时，允许日志通过
            return True


# 全局去重器实例
_log_deduplicator: Optional[LogDeduplicator] = None


def get_log_deduplicator() -> Optional[LogDeduplicator]:
    """获取全局日志去重器实例"""
    return _log_deduplicator


def initialize_log_deduplicator(window_size: int = 10, 
                               time_window: int = 60) -> LogDeduplicator:
    """
    初始化全局日志去重器
    
    Args:
        window_size: 滑动窗口大小
        time_window: 时间窗口
        
    Returns:
        日志去重器实例
    """
    global _log_deduplicator
    
    if _log_deduplicator is None:
        _log_deduplicator = LogDeduplicator(window_size, time_window)
        
        # 为根日志记录器添加去重过滤器
        root_logger = logging.getLogger()
        dedup_filter = LogDedupFilter(_log_deduplicator)
        root_logger.addFilter(dedup_filter)

        # 同时为所有现有的处理器添加过滤器
        for handler in root_logger.handlers:
            handler.addFilter(LogDedupFilter(_log_deduplicator))
        
        logger = logging.getLogger(__name__)
        logger.debug("✅ 全局日志去重器初始化完成")
    
    return _log_deduplicator


def should_suppress_log(message: str, level: str = 'INFO') -> bool:
    """
    检查是否应该抑制日志的便捷函数
    
    Args:
        message: 日志消息
        level: 日志级别
        
    Returns:
        是否应该抑制日志
    """
    deduplicator = get_log_deduplicator()
    if deduplicator:
        return deduplicator.should_suppress_log(message, level)
    return False
