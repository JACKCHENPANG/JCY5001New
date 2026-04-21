#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通道计时器管理器
负责管理通道的测试计时功能

Author: Jack
Date: 2025-01-30
"""

import logging
import time
from typing import Optional, Dict, Any, Callable
from PyQt5.QtCore import QTimer, QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ChannelTimerManager(QObject):
    """通道计时器管理器"""
    
    # 信号定义
    timer_updated = pyqtSignal(int, float)  # 计时器更新 (channel, elapsed_time)
    timer_started = pyqtSignal(int)  # 计时器开始
    timer_stopped = pyqtSignal(int, float)  # 计时器停止 (channel, total_time)
    timer_reset = pyqtSignal(int)  # 计时器重置
    
    def __init__(self, channel_number: int):
        """
        初始化计时器管理器
        
        Args:
            channel_number: 通道号（1-8）
        """
        super().__init__()
        
        self.channel_number = channel_number
        self.channel_index = channel_number - 1
        
        # 计时器
        self.timer = QTimer()
        self.timer.timeout.connect(self._on_timer_timeout)
        
        # 时间记录
        self.start_time = None
        self.end_time = None
        self.elapsed_time = 0.0
        self.total_time = 0.0
        
        # 计时器状态
        self.is_running = False
        self.is_paused = False
        
        # 更新间隔（毫秒）
        self.update_interval = 100  # 100ms更新一次
        
        # 回调函数
        self.update_callbacks = []
        self.start_callbacks = []
        self.stop_callbacks = []
        self.reset_callbacks = []
        
        logger.debug(f"通道{self.channel_number}计时器管理器初始化完成")
    
    def start_timer(self) -> bool:
        """
        启动计时器
        
        Returns:
            是否启动成功
        """
        try:
            if not self.is_running:
                self.start_time = time.time()
                self.is_running = True
                self.is_paused = False
                
                # 启动QTimer
                self.timer.start(self.update_interval)
                
                # 发射信号
                self.timer_started.emit(self.channel_number)
                
                # 调用回调
                for callback in self.start_callbacks:
                    try:
                        callback(self.channel_number)
                    except Exception as e:
                        logger.error(f"通道{self.channel_number}计时器启动回调执行失败: {e}")
                
                logger.debug(f"通道{self.channel_number}计时器启动")
                return True
            else:
                logger.warning(f"通道{self.channel_number}计时器已在运行")
                return False
                
        except Exception as e:
            logger.error(f"通道{self.channel_number}启动计时器失败: {e}")
            return False
    
    def stop_timer(self) -> bool:
        """
        停止计时器
        
        Returns:
            是否停止成功
        """
        try:
            if self.is_running:
                self.end_time = time.time()
                self.is_running = False
                self.is_paused = False
                
                # 计算总时间
                if self.start_time:
                    self.total_time = self.end_time - self.start_time
                
                # 停止QTimer
                self.timer.stop()
                
                # 发射信号
                self.timer_stopped.emit(self.channel_number, self.total_time)
                
                # 调用回调
                for callback in self.stop_callbacks:
                    try:
                        callback(self.channel_number, self.total_time)
                    except Exception as e:
                        logger.error(f"通道{self.channel_number}计时器停止回调执行失败: {e}")
                
                logger.debug(f"通道{self.channel_number}计时器停止，总时间: {self.total_time:.2f}秒")
                return True
            else:
                logger.debug(f"通道{self.channel_number}计时器未在运行")
                return False
                
        except Exception as e:
            logger.error(f"通道{self.channel_number}停止计时器失败: {e}")
            return False
    
    def pause_timer(self) -> bool:
        """
        暂停计时器
        
        Returns:
            是否暂停成功
        """
        try:
            if self.is_running and not self.is_paused:
                self.is_paused = True
                self.timer.stop()
                
                # 记录暂停时的时间
                if self.start_time:
                    self.elapsed_time = time.time() - self.start_time
                
                logger.debug(f"通道{self.channel_number}计时器暂停")
                return True
            else:
                logger.warning(f"通道{self.channel_number}计时器无法暂停")
                return False
                
        except Exception as e:
            logger.error(f"通道{self.channel_number}暂停计时器失败: {e}")
            return False
    
    def resume_timer(self) -> bool:
        """
        恢复计时器
        
        Returns:
            是否恢复成功
        """
        try:
            if self.is_running and self.is_paused:
                # 调整开始时间，使得已暂停的时间不被计算
                current_time = time.time()
                self.start_time = current_time - self.elapsed_time
                
                self.is_paused = False
                self.timer.start(self.update_interval)
                
                logger.debug(f"通道{self.channel_number}计时器恢复")
                return True
            else:
                logger.warning(f"通道{self.channel_number}计时器无法恢复")
                return False
                
        except Exception as e:
            logger.error(f"通道{self.channel_number}恢复计时器失败: {e}")
            return False
    
    def reset_timer(self) -> bool:
        """
        重置计时器
        
        Returns:
            是否重置成功
        """
        try:
            # 停止计时器
            self.timer.stop()
            
            # 重置所有时间记录
            self.start_time = None
            self.end_time = None
            self.elapsed_time = 0.0
            self.total_time = 0.0
            
            # 重置状态
            self.is_running = False
            self.is_paused = False
            
            # 发射信号
            self.timer_reset.emit(self.channel_number)
            
            # 调用回调
            for callback in self.reset_callbacks:
                try:
                    callback(self.channel_number)
                except Exception as e:
                    logger.error(f"通道{self.channel_number}计时器重置回调执行失败: {e}")
            
            logger.debug(f"通道{self.channel_number}计时器重置")
            return True
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}重置计时器失败: {e}")
            return False
    
    def get_elapsed_time(self) -> float:
        """
        获取已经过的时间
        
        Returns:
            已经过的时间（秒）
        """
        try:
            if self.is_running and not self.is_paused and self.start_time:
                return time.time() - self.start_time
            elif self.is_paused:
                return self.elapsed_time
            elif self.total_time > 0:
                return self.total_time
            else:
                return 0.0
        except Exception as e:
            logger.error(f"通道{self.channel_number}获取已过时间失败: {e}")
            return 0.0
    
    def get_total_time(self) -> float:
        """
        获取总时间
        
        Returns:
            总时间（秒）
        """
        return self.total_time
    
    def format_time(self, seconds: Optional[float] = None) -> str:
        """
        格式化时间显示
        
        Args:
            seconds: 要格式化的秒数，如果为None则使用当前已过时间
            
        Returns:
            格式化的时间字符串
        """
        try:
            if seconds is None:
                seconds = self.get_elapsed_time()
            
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                minutes = int(seconds // 60)
                secs = seconds % 60
                return f"{minutes}m{secs:.1f}s"
            else:
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = seconds % 60
                return f"{hours}h{minutes}m{secs:.1f}s"
                
        except Exception as e:
            logger.error(f"通道{self.channel_number}格式化时间失败: {e}")
            return "0.0s"
    
    def set_update_interval(self, interval_ms: int) -> bool:
        """
        设置更新间隔
        
        Args:
            interval_ms: 更新间隔（毫秒）
            
        Returns:
            是否设置成功
        """
        try:
            if 10 <= interval_ms <= 1000:  # 限制在10ms到1000ms之间
                self.update_interval = interval_ms
                
                # 如果计时器正在运行，重新启动以应用新间隔
                if self.is_running and not self.is_paused:
                    self.timer.start(self.update_interval)
                
                logger.debug(f"通道{self.channel_number}更新间隔设置为: {interval_ms}ms")
                return True
            else:
                logger.warning(f"通道{self.channel_number}更新间隔无效: {interval_ms}ms")
                return False
                
        except Exception as e:
            logger.error(f"通道{self.channel_number}设置更新间隔失败: {e}")
            return False
    
    def _on_timer_timeout(self):
        """计时器超时处理"""
        try:
            if self.is_running and not self.is_paused:
                current_elapsed = self.get_elapsed_time()
                
                # 发射信号
                self.timer_updated.emit(self.channel_number, current_elapsed)
                
                # 调用回调
                for callback in self.update_callbacks:
                    try:
                        callback(self.channel_number, current_elapsed)
                    except Exception as e:
                        logger.error(f"通道{self.channel_number}计时器更新回调执行失败: {e}")
                        
        except Exception as e:
            logger.error(f"通道{self.channel_number}计时器超时处理失败: {e}")
    
    def add_update_callback(self, callback: Callable[[int, float], None]) -> bool:
        """添加更新回调"""
        try:
            if callback not in self.update_callbacks:
                self.update_callbacks.append(callback)
                logger.debug(f"通道{self.channel_number}添加计时器更新回调")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}添加更新回调失败: {e}")
            return False
    
    def add_start_callback(self, callback: Callable[[int], None]) -> bool:
        """添加启动回调"""
        try:
            if callback not in self.start_callbacks:
                self.start_callbacks.append(callback)
                logger.debug(f"通道{self.channel_number}添加计时器启动回调")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}添加启动回调失败: {e}")
            return False
    
    def add_stop_callback(self, callback: Callable[[int, float], None]) -> bool:
        """添加停止回调"""
        try:
            if callback not in self.stop_callbacks:
                self.stop_callbacks.append(callback)
                logger.debug(f"通道{self.channel_number}添加计时器停止回调")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}添加停止回调失败: {e}")
            return False
    
    def add_reset_callback(self, callback: Callable[[int], None]) -> bool:
        """添加重置回调"""
        try:
            if callback not in self.reset_callbacks:
                self.reset_callbacks.append(callback)
                logger.debug(f"通道{self.channel_number}添加计时器重置回调")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}添加重置回调失败: {e}")
            return False
    
    def get_timer_summary(self) -> Dict[str, Any]:
        """
        获取计时器摘要
        
        Returns:
            计时器摘要字典
        """
        try:
            return {
                'channel_number': self.channel_number,
                'is_running': self.is_running,
                'is_paused': self.is_paused,
                'elapsed_time': self.get_elapsed_time(),
                'total_time': self.total_time,
                'formatted_time': self.format_time(),
                'update_interval': self.update_interval,
                'callbacks_count': {
                    'update': len(self.update_callbacks),
                    'start': len(self.start_callbacks),
                    'stop': len(self.stop_callbacks),
                    'reset': len(self.reset_callbacks)
                }
            }
        except Exception as e:
            logger.error(f"通道{self.channel_number}获取计时器摘要失败: {e}")
            return {}
