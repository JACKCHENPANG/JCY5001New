#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JCY5001AS电池阻抗测试系统 - 启动性能监控工具

功能：
1. 监控通道启动时序和间隔时间
2. 测量频率测试完成时间
3. 分析启动性能瓶颈
4. 生成性能对比报告

作者：Jack
创建时间：2025-01-27
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from PyQt5.QtCore import QObject, pyqtSignal
import logging

logger = logging.getLogger(__name__)

@dataclass
class ChannelStartupEvent:
    """通道启动事件记录"""
    channel_num: int
    frequency: float
    timestamp: datetime
    event_type: str  # 'start', 'complete', 'timeout'
    duration: Optional[float] = None  # 测试持续时间（秒）

@dataclass
class FrequencyTestSession:
    """频率测试会话记录"""
    frequency: float
    start_time: datetime
    end_time: Optional[datetime] = None
    channels: List[ChannelStartupEvent] = field(default_factory=list)
    startup_mode: str = "unknown"
    total_duration: Optional[float] = None
    
    def add_channel_event(self, event: ChannelStartupEvent):
        """添加通道事件"""
        self.channels.append(event)
    
    def calculate_startup_intervals(self) -> List[float]:
        """计算通道间启动间隔"""
        start_events = [e for e in self.channels if e.event_type == 'start']
        start_events.sort(key=lambda x: x.timestamp)
        
        intervals = []
        for i in range(1, len(start_events)):
            interval = (start_events[i].timestamp - start_events[i-1].timestamp).total_seconds() * 1000
            intervals.append(interval)
        
        return intervals
    
    def get_completion_times(self) -> Dict[int, float]:
        """获取各通道完成时间"""
        completion_times = {}
        for event in self.channels:
            if event.event_type == 'complete' and event.duration is not None:
                completion_times[event.channel_num] = event.duration
        return completion_times

class StartupPerformanceMonitor(QObject):
    """启动性能监控器"""
    
    # 信号定义
    performance_update = pyqtSignal(dict)  # 性能数据更新
    session_complete = pyqtSignal(dict)    # 测试会话完成
    
    def __init__(self):
        super().__init__()
        self.is_monitoring = False
        self.current_session: Optional[FrequencyTestSession] = None
        self.test_sessions: List[FrequencyTestSession] = []
        self.performance_data = {}
        self._lock = threading.Lock()
        
        # 性能统计
        self.total_tests = 0
        self.total_startup_time = 0.0
        self.average_startup_interval = 0.0
        self.startup_mode_stats = {}
        
    
    def start_monitoring(self, startup_mode: str = "unknown"):
        """开始监控测试会话"""
        with self._lock:
            if self.is_monitoring:
                logger.warning("性能监控已在运行")
                return
            
            self.is_monitoring = True
            logger.info(f"🚀 开始监控启动性能 - 模式: {startup_mode}")
    
    def stop_monitoring(self):
        """停止监控"""
        with self._lock:
            if not self.is_monitoring:
                return
            
            self.is_monitoring = False
            if self.current_session:
                self._finalize_current_session()
            
            logger.info("⏹️ 启动性能监控已停止")
    
    def start_frequency_test(self, frequency: float, startup_mode: str):
        """开始频率测试会话"""
        with self._lock:
            if not self.is_monitoring:
                return
            
            # 完成上一个会话
            if self.current_session:
                self._finalize_current_session()
            
            # 创建新会话
            self.current_session = FrequencyTestSession(
                frequency=frequency,
                start_time=datetime.now(),
                startup_mode=startup_mode
            )
            
    
    def record_channel_start(self, channel_num: int, frequency: float):
        """记录通道启动事件"""
        if not self.is_monitoring or not self.current_session:
            return
        
        event = ChannelStartupEvent(
            channel_num=channel_num,
            frequency=frequency,
            timestamp=datetime.now(),
            event_type='start'
        )
        
        self.current_session.add_channel_event(event)
        logger.debug(f"📝 记录通道{channel_num}启动: {frequency}Hz")
    
    def record_channel_complete(self, channel_num: int, frequency: float, duration: float):
        """记录通道完成事件"""
        if not self.is_monitoring or not self.current_session:
            return
        
        event = ChannelStartupEvent(
            channel_num=channel_num,
            frequency=frequency,
            timestamp=datetime.now(),
            event_type='complete',
            duration=duration
        )
        
        self.current_session.add_channel_event(event)
        logger.debug(f"✅ 记录通道{channel_num}完成: {frequency}Hz, 用时: {duration:.2f}s")
    
    def record_channel_timeout(self, channel_num: int, frequency: float):
        """记录通道超时事件"""
        if not self.is_monitoring or not self.current_session:
            return
        
        event = ChannelStartupEvent(
            channel_num=channel_num,
            frequency=frequency,
            timestamp=datetime.now(),
            event_type='timeout'
        )
        
        self.current_session.add_channel_event(event)
        logger.warning(f"⏰ 记录通道{channel_num}超时: {frequency}Hz")
    
    def _finalize_current_session(self):
        """完成当前测试会话"""
        if not self.current_session:
            return
        
        self.current_session.end_time = datetime.now()
        self.current_session.total_duration = (
            self.current_session.end_time - self.current_session.start_time
        ).total_seconds()
        
        # 添加到会话列表
        self.test_sessions.append(self.current_session)
        
        # 更新统计数据
        self._update_statistics()
        
        # 发送会话完成信号
        session_data = self._get_session_summary(self.current_session)
        self.session_complete.emit(session_data)
        
        logger.info(f"📋 完成频率 {self.current_session.frequency}Hz 测试会话")
        self.current_session = None
    
    def _update_statistics(self):
        """更新性能统计数据"""
        if not self.test_sessions:
            return
        
        self.total_tests = len(self.test_sessions)
        
        # 计算总启动时间
        self.total_startup_time = sum(
            session.total_duration for session in self.test_sessions 
            if session.total_duration
        )
        
        # 计算平均启动间隔
        all_intervals = []
        for session in self.test_sessions:
            intervals = session.calculate_startup_intervals()
            all_intervals.extend(intervals)
        
        if all_intervals:
            self.average_startup_interval = sum(all_intervals) / len(all_intervals)
        
        # 统计启动模式
        self.startup_mode_stats = {}
        for session in self.test_sessions:
            mode = session.startup_mode
            if mode not in self.startup_mode_stats:
                self.startup_mode_stats[mode] = {'count': 0, 'total_time': 0.0}
            
            self.startup_mode_stats[mode]['count'] += 1
            if session.total_duration:
                self.startup_mode_stats[mode]['total_time'] += session.total_duration
        
        # 更新性能数据
        self.performance_data = {
            'total_tests': self.total_tests,
            'total_startup_time': self.total_startup_time,
            'average_startup_interval': self.average_startup_interval,
            'startup_mode_stats': self.startup_mode_stats.copy(),
            'last_update': datetime.now().isoformat()
        }
        
        # 发送性能更新信号
        self.performance_update.emit(self.performance_data.copy())
    
    def _get_session_summary(self, session: FrequencyTestSession) -> dict:
        """获取会话摘要"""
        intervals = session.calculate_startup_intervals()
        completion_times = session.get_completion_times()
        
        return {
            'frequency': session.frequency,
            'startup_mode': session.startup_mode,
            'total_duration': session.total_duration,
            'channel_count': len([e for e in session.channels if e.event_type == 'start']),
            'startup_intervals': intervals,
            'average_interval': sum(intervals) / len(intervals) if intervals else 0,
            'completion_times': completion_times,
            'timeout_count': len([e for e in session.channels if e.event_type == 'timeout']),
            'start_time': session.start_time.isoformat(),
            'end_time': session.end_time.isoformat() if session.end_time else None
        }
    
    def get_performance_report(self) -> dict:
        """获取性能报告"""
        with self._lock:
            report = {
                'summary': self.performance_data.copy(),
                'sessions': [self._get_session_summary(session) for session in self.test_sessions],
                'analysis': self._analyze_performance()
            }
            return report
    
    def _analyze_performance(self) -> dict:
        """分析性能数据"""
        if not self.test_sessions:
            return {'message': '暂无测试数据'}
        
        # 分析启动间隔分布
        all_intervals = []
        for session in self.test_sessions:
            intervals = session.calculate_startup_intervals()
            all_intervals.extend(intervals)
        
        analysis = {
            'total_sessions': len(self.test_sessions),
            'interval_analysis': {
                'count': len(all_intervals),
                'min': min(all_intervals) if all_intervals else 0,
                'max': max(all_intervals) if all_intervals else 0,
                'average': sum(all_intervals) / len(all_intervals) if all_intervals else 0
            },
            'mode_performance': {},
            'recommendations': []
        }
        
        # 分析各模式性能
        for mode, stats in self.startup_mode_stats.items():
            if stats['count'] > 0:
                analysis['mode_performance'][mode] = {
                    'test_count': stats['count'],
                    'total_time': stats['total_time'],
                    'average_time': stats['total_time'] / stats['count']
                }
        
        # 生成优化建议
        if analysis['interval_analysis']['average'] > 100:  # 超过100ms
            analysis['recommendations'].append("启动间隔较长，建议优化延迟配置")
        
        if analysis['interval_analysis']['max'] > 500:  # 超过500ms
            analysis['recommendations'].append("检测到异常长的启动间隔，需要排查性能瓶颈")
        
        return analysis
    
    def clear_data(self):
        """清除监控数据"""
        with self._lock:
            self.test_sessions.clear()
            self.current_session = None
            self.performance_data.clear()
            self.total_tests = 0
            self.total_startup_time = 0.0
            self.average_startup_interval = 0.0
            self.startup_mode_stats.clear()
            
            logger.info("🗑️ 性能监控数据已清除")
