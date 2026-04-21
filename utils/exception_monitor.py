# -*- coding: utf-8 -*-
"""
增强的异常监控和统计系统
实时监控系统异常，提供统计分析和健康度评估

Author: Jack
Date: 2025-01-09
"""

import logging
import time
import threading
import sys
import traceback
import os
import psutil
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal

from backend.exceptions import ErrorCode

logger = logging.getLogger(__name__)


class SystemHealthLevel(Enum):
    """系统健康度级别"""
    EXCELLENT = ("优秀", "#4CAF50", 90)    # 绿色，90分以上
    GOOD = ("良好", "#8BC34A", 75)         # 浅绿，75-89分
    FAIR = ("一般", "#FF9800", 60)         # 橙色，60-74分
    POOR = ("较差", "#F44336", 40)         # 红色，40-59分
    CRITICAL = ("严重", "#9C27B0", 0)      # 紫色，40分以下


@dataclass
class ExceptionRecord:
    """异常记录"""
    timestamp: float
    error_code: Optional[ErrorCode]
    function_name: str
    exception_type: str
    message: str
    severity: str
    resolved: bool = False
    resolution_time: Optional[float] = None


class ExceptionMonitor(QObject):
    """增强的异常监控器"""

    # 信号定义
    exception_occurred = pyqtSignal(str, str, str)  # 异常类型, 异常信息, 堆栈信息
    critical_error = pyqtSignal(str)  # 严重错误信号
    health_status_changed = pyqtSignal(dict)  # 健康状态变化信号

    def __init__(self, max_records: int = 1000):
        """初始化异常监控器"""
        super().__init__()

        self.max_records = max_records
        self.exception_records = deque(maxlen=max_records)
        self.exception_stats = defaultdict(int)
        self.function_stats = defaultdict(int)
        self.hourly_stats = defaultdict(int)

        # 原有属性保持兼容性
        self.is_monitoring = False
        self.exception_count = 0
        self.last_exception_time = None
        self.exception_callback: Optional[Callable] = None

        # 监控配置
        self.monitoring_enabled = True
        self.alert_threshold = 10  # 每小时异常数量阈值
        self.health_check_interval = 300  # 健康检查间隔（秒）

        # 线程安全锁
        self._lock = threading.RLock()

        # 创建异常日志文件
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)

        # 设置异常日志文件
        self.exception_log_file = os.path.join(
            self.log_dir,
            f"exceptions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        # 启动健康检查线程
        self._start_health_monitor()
        
        # 配置异常日志记录器
        self._setup_exception_logger()
        
        logger.debug("异常监控器初始化完成")
    
    def _setup_exception_logger(self):
        """设置异常日志记录器"""
        try:
            # 创建异常专用logger
            self.exception_logger = logging.getLogger('exception_monitor')
            self.exception_logger.setLevel(logging.DEBUG)
            
            # 创建文件处理器
            file_handler = logging.FileHandler(
                self.exception_log_file, 
                mode='w', 
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            
            # 创建控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.ERROR)
            
            # 设置格式
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加处理器
            self.exception_logger.addHandler(file_handler)
            self.exception_logger.addHandler(console_handler)
            
            logger.info(f"异常日志文件: {self.exception_log_file}")
            
        except Exception as e:
            logger.error(f"设置异常日志记录器失败: {e}")
    
    def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            logger.warning("异常监控已经在运行")
            return
        
        try:
            # 设置全局异常处理器
            sys.excepthook = self._handle_exception
            
            # 设置线程异常处理器 (Python 3.8+)
            if hasattr(threading, 'excepthook'):
                threading.excepthook = self._handle_thread_exception
            
            self.is_monitoring = True
            self.exception_count = 0
            
            self.exception_logger.info("=" * 60)
            self.exception_logger.info("异常监控开始")
            self.exception_logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"启动异常监控失败: {e}")
    
    def stop_monitoring(self):
        """停止监控"""
        if not self.is_monitoring:
            return
        
        try:
            # 恢复默认异常处理器
            sys.excepthook = sys.__excepthook__
            
            if hasattr(threading, 'excepthook'):
                threading.excepthook = threading.__excepthook__
            
            self.is_monitoring = False
            
            logger.info("🛑 异常监控已停止")
            self.exception_logger.info("=" * 60)
            self.exception_logger.info(f"异常监控结束 - 总异常数: {self.exception_count}")
            self.exception_logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"停止异常监控失败: {e}")
    
    def _handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        处理主线程异常
        
        Args:
            exc_type: 异常类型
            exc_value: 异常值
            exc_traceback: 异常堆栈
        """
        try:
            self.exception_count += 1
            self.last_exception_time = datetime.now()
            
            # 获取异常信息
            exc_type_name = exc_type.__name__ if exc_type else "Unknown"
            exc_message = str(exc_value) if exc_value else "No message"
            
            # 获取堆栈信息
            stack_trace = ''.join(traceback.format_exception(
                exc_type, exc_value, exc_traceback
            ))
            
            # 获取系统状态
            system_info = self._get_system_info()
            
            # 记录异常
            self._log_exception(
                "主线程异常", 
                exc_type_name, 
                exc_message, 
                stack_trace, 
                system_info
            )
            
            # 发送信号
            self.exception_occurred.emit(exc_type_name, exc_message, stack_trace)
            
            # 检查是否为严重错误
            if self._is_critical_error(exc_type_name):
                self.critical_error.emit(f"严重错误: {exc_type_name} - {exc_message}")
            
            # 调用回调函数
            if self.exception_callback:
                self.exception_callback(exc_type_name, exc_message, stack_trace)
            
        except Exception as e:
            # 异常处理器本身出错，使用默认处理
            print(f"异常监控器处理异常时出错: {e}")
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    def _handle_thread_exception(self, args):
        """
        处理线程异常
        
        Args:
            args: 线程异常参数
        """
        try:
            self.exception_count += 1
            self.last_exception_time = datetime.now()
            
            exc_type = args.exc_type
            exc_value = args.exc_value
            exc_traceback = args.exc_traceback
            thread = args.thread
            
            # 获取异常信息
            exc_type_name = exc_type.__name__ if exc_type else "Unknown"
            exc_message = str(exc_value) if exc_value else "No message"
            thread_name = thread.name if thread else "Unknown"
            
            # 获取堆栈信息
            stack_trace = ''.join(traceback.format_exception(
                exc_type, exc_value, exc_traceback
            ))
            
            # 获取系统状态
            system_info = self._get_system_info()
            
            # 记录异常
            self._log_exception(
                f"线程异常 [{thread_name}]", 
                exc_type_name, 
                exc_message, 
                stack_trace, 
                system_info
            )
            
            # 发送信号
            self.exception_occurred.emit(
                f"[线程:{thread_name}] {exc_type_name}", 
                exc_message, 
                stack_trace
            )
            
            # 检查是否为严重错误
            if self._is_critical_error(exc_type_name):
                self.critical_error.emit(
                    f"线程严重错误 [{thread_name}]: {exc_type_name} - {exc_message}"
                )
            
        except Exception as e:
            print(f"线程异常监控器处理异常时出错: {e}")
    
    def _log_exception(self, context: str, exc_type: str, exc_message: str, 
                      stack_trace: str, system_info: Dict[str, Any]):
        """
        记录异常信息
        
        Args:
            context: 异常上下文
            exc_type: 异常类型
            exc_message: 异常消息
            stack_trace: 堆栈信息
            system_info: 系统信息
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            
            self.exception_logger.error(f"""
{'='*80}
时间: {timestamp}
上下文: {context}
异常类型: {exc_type}
异常消息: {exc_message}
系统信息:
  - CPU使用率: {system_info.get('cpu_percent', 'N/A')}%
  - 内存使用率: {system_info.get('memory_percent', 'N/A')}%
  - 可用内存: {system_info.get('memory_available', 'N/A')} MB
  - 线程数: {system_info.get('thread_count', 'N/A')}
堆栈信息:
{stack_trace}
{'='*80}
""")
            
        except Exception as e:
            print(f"记录异常信息失败: {e}")
    
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            process = psutil.Process()
            
            return {
                'cpu_percent': round(psutil.cpu_percent(interval=0.1), 2),
                'memory_percent': round(psutil.virtual_memory().percent, 2),
                'memory_available': round(psutil.virtual_memory().available / 1024 / 1024, 2),
                'thread_count': process.num_threads(),
                'process_memory': round(process.memory_info().rss / 1024 / 1024, 2)
            }
        except Exception as e:
            logger.warning(f"获取系统信息失败: {e}")
            return {}
    
    def _is_critical_error(self, exc_type: str) -> bool:
        """
        判断是否为严重错误
        
        Args:
            exc_type: 异常类型
            
        Returns:
            是否为严重错误
        """
        critical_errors = [
            'MemoryError',
            'SystemExit',
            'KeyboardInterrupt',
            'OSError',
            'RuntimeError'
        ]
        
        return exc_type in critical_errors
    
    def set_exception_callback(self, callback: Callable):
        """
        设置异常回调函数
        
        Args:
            callback: 回调函数
        """
        self.exception_callback = callback
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取监控统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'is_monitoring': self.is_monitoring,
            'exception_count': self.exception_count,
            'last_exception_time': self.last_exception_time,
            'log_file': self.exception_log_file
        }


# 全局异常监控器实例
_global_monitor: Optional[ExceptionMonitor] = None


def get_global_monitor() -> ExceptionMonitor:
    """获取全局异常监控器实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = ExceptionMonitor()
    return _global_monitor


def start_global_monitoring():
    """启动全局异常监控"""
    monitor = get_global_monitor()
    monitor.start_monitoring()
    return monitor


def stop_global_monitoring():
    """停止全局异常监控"""
    global _global_monitor
    if _global_monitor:
        _global_monitor.stop_monitoring()
