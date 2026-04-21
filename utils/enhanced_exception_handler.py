# -*- coding: utf-8 -*-
"""
增强的异常处理装饰器
提供统一的异常处理、用户友好提示和自动恢复机制

Author: Jack
Date: 2025-01-09
"""

import logging
import functools
import time
from typing import Callable, Optional, Any, Dict, List, Union
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, QThread, pyqtSignal

from backend.exceptions import ErrorCode, TestSystemException
from utils.user_friendly_error_manager import get_error_manager
from ui.dialogs.user_friendly_error_dialog import show_user_friendly_error

logger = logging.getLogger(__name__)


class ExceptionHandlingConfig:
    """异常处理配置"""
    
    def __init__(self):
        self.show_user_dialog = True          # 是否显示用户友好对话框
        self.auto_retry = False               # 是否自动重试
        self.max_retries = 3                  # 最大重试次数
        self.retry_delay = 1.0                # 重试延迟（秒）
        self.log_level = "error"              # 日志级别
        self.fallback_value = None            # 降级返回值
        self.critical_operation = False       # 是否为关键操作
        self.user_notification = True         # 是否通知用户
        self.auto_close_dialog = 0            # 对话框自动关闭时间（秒）


class EnhancedExceptionHandler:
    """增强的异常处理器"""
    
    def __init__(self):
        self.error_manager = get_error_manager()
        self.exception_stats = {}  # 异常统计
        self.recent_exceptions = []  # 最近异常记录
        
    def handle_exception(self, 
                        config: ExceptionHandlingConfig = None,
                        error_code_mapping: Dict[type, ErrorCode] = None):
        """
        异常处理装饰器
        
        Args:
            config: 异常处理配置
            error_code_mapping: 异常类型到错误码的映射
        """
        if config is None:
            config = ExceptionHandlingConfig()
            
        if error_code_mapping is None:
            error_code_mapping = self._get_default_error_mapping()
            
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return self._execute_with_exception_handling(
                    func, args, kwargs, config, error_code_mapping
                )
            return wrapper
        return decorator
    
    def _execute_with_exception_handling(self, 
                                       func: Callable, 
                                       args: tuple, 
                                       kwargs: dict,
                                       config: ExceptionHandlingConfig,
                                       error_code_mapping: Dict[type, ErrorCode]) -> Any:
        """执行带异常处理的函数"""
        last_exception = None
        
        for attempt in range(config.max_retries + 1):
            try:
                # 执行原函数
                result = func(*args, **kwargs)
                
                # 如果之前有异常但这次成功了，记录恢复
                if last_exception and attempt > 0:
                    logger.info(f"函数 {func.__name__} 在第 {attempt + 1} 次尝试后成功恢复")
                    
                return result
                
            except Exception as e:
                last_exception = e
                
                # 记录异常统计
                self._record_exception_stats(func.__name__, e)
                
                # 确定错误码
                error_code = self._determine_error_code(e, error_code_mapping)
                
                # 记录日志
                self._log_exception(func, e, error_code, attempt + 1, config)
                
                # 如果还有重试机会且配置允许自动重试
                if attempt < config.max_retries and config.auto_retry:
                    logger.info(f"函数 {func.__name__} 第 {attempt + 1} 次执行失败，{config.retry_delay}秒后重试...")
                    time.sleep(config.retry_delay)
                    continue
                else:
                    # 最后一次尝试失败，处理异常
                    return self._handle_final_exception(
                        func, e, error_code, config, attempt + 1
                    )
        
        # 理论上不会到达这里
        return config.fallback_value
    
    def _determine_error_code(self, exception: Exception, 
                            error_code_mapping: Dict[type, ErrorCode]) -> ErrorCode:
        """确定错误码"""
        try:
            # 如果是自定义异常，直接使用其错误码
            if isinstance(exception, TestSystemException):
                return exception.error_code
            
            # 根据异常类型映射
            for exc_type, error_code in error_code_mapping.items():
                if isinstance(exception, exc_type):
                    return error_code
            
            # 默认未知错误
            return ErrorCode.UNKNOWN_ERROR
            
        except Exception as e:
            logger.error(f"确定错误码失败: {e}")
            return ErrorCode.UNKNOWN_ERROR
    
    def _log_exception(self, func: Callable, exception: Exception, 
                      error_code: ErrorCode, attempt: int, 
                      config: ExceptionHandlingConfig):
        """记录异常日志"""
        try:
            log_func = getattr(logger, config.log_level, logger.error)
            
            log_message = f"函数 {func.__name__} 执行异常 (第{attempt}次尝试)"
            log_message += f" - 错误码: {error_code.name}"
            log_message += f" - 异常: {str(exception)}"
            
            if config.critical_operation:
                log_message = f"[关键操作] {log_message}"
                
            log_func(log_message)
            
            # 记录详细异常信息（仅在DEBUG级别）
            if logger.isEnabledFor(logging.DEBUG):
                import traceback
                logger.debug(f"异常详情: {traceback.format_exc()}")
                
        except Exception as e:
            logger.error(f"记录异常日志失败: {e}")
    
    def _handle_final_exception(self, func: Callable, exception: Exception,
                              error_code: ErrorCode, config: ExceptionHandlingConfig,
                              total_attempts: int) -> Any:
        """处理最终异常"""
        try:
            # 构建技术详情
            technical_detail = f"函数: {func.__name__}, 尝试次数: {total_attempts}, 异常: {str(exception)}"
            
            # 如果配置要求显示用户对话框
            if config.show_user_dialog and config.user_notification:
                self._show_user_error_dialog(error_code, technical_detail, config)
            
            # 如果是关键操作，抛出异常
            if config.critical_operation:
                if isinstance(exception, TestSystemException):
                    raise exception
                else:
                    raise TestSystemException(
                        error_code,
                        detail=f"关键操作失败: {func.__name__}",
                        cause=exception
                    )
            
            # 返回降级值
            return config.fallback_value
            
        except Exception as e:
            logger.error(f"处理最终异常失败: {e}")
            return config.fallback_value
    
    def _show_user_error_dialog(self, error_code: ErrorCode, 
                              technical_detail: str, 
                              config: ExceptionHandlingConfig):
        """显示用户错误对话框"""
        try:
            # 检查是否在主线程中
            app = QApplication.instance()
            if app and QThread.currentThread() == app.thread():
                # 在主线程中，直接显示对话框
                dialog = show_user_friendly_error(
                    error_code=error_code,
                    technical_detail=technical_detail,
                    show_retry=config.auto_retry,
                    auto_close_seconds=config.auto_close_dialog
                )
                if dialog:
                    dialog.exec_()
            else:
                # 在子线程中，使用信号槽机制
                logger.warning("在子线程中检测到异常，无法直接显示对话框")
                
        except Exception as e:
            logger.error(f"显示用户错误对话框失败: {e}")
    
    def _record_exception_stats(self, func_name: str, exception: Exception):
        """记录异常统计"""
        try:
            exc_type = type(exception).__name__
            key = f"{func_name}:{exc_type}"
            
            if key not in self.exception_stats:
                self.exception_stats[key] = {
                    'count': 0,
                    'first_occurrence': time.time(),
                    'last_occurrence': time.time(),
                    'function': func_name,
                    'exception_type': exc_type
                }
            
            self.exception_stats[key]['count'] += 1
            self.exception_stats[key]['last_occurrence'] = time.time()
            
            # 记录最近异常
            self.recent_exceptions.append({
                'timestamp': time.time(),
                'function': func_name,
                'exception_type': exc_type,
                'message': str(exception)
            })
            
            # 只保留最近100个异常记录
            if len(self.recent_exceptions) > 100:
                self.recent_exceptions = self.recent_exceptions[-100:]
                
        except Exception as e:
            logger.error(f"记录异常统计失败: {e}")
    
    def _get_default_error_mapping(self) -> Dict[type, ErrorCode]:
        """获取默认的异常类型到错误码映射"""
        return {
            ConnectionError: ErrorCode.DEVICE_CONNECTION_FAILED,
            TimeoutError: ErrorCode.TIMEOUT_ERROR,
            ValueError: ErrorCode.INVALID_PARAMETER,
            FileNotFoundError: ErrorCode.CONFIG_NOT_FOUND,
            PermissionError: ErrorCode.PERMISSION_DENIED,
            OSError: ErrorCode.OPERATION_FAILED,
            RuntimeError: ErrorCode.OPERATION_FAILED,
            KeyError: ErrorCode.DATA_FORMAT_ERROR,
            TypeError: ErrorCode.INVALID_PARAMETER,
        }
    
    def get_exception_statistics(self) -> Dict[str, Any]:
        """获取异常统计信息"""
        try:
            total_exceptions = sum(stat['count'] for stat in self.exception_stats.values())
            
            # 按发生次数排序
            top_exceptions = sorted(
                self.exception_stats.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:10]
            
            return {
                'total_exceptions': total_exceptions,
                'unique_exception_types': len(self.exception_stats),
                'top_exceptions': top_exceptions,
                'recent_exceptions': self.recent_exceptions[-10:],  # 最近10个
                'statistics_period': {
                    'start': min(stat['first_occurrence'] for stat in self.exception_stats.values()) if self.exception_stats else 0,
                    'end': time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"获取异常统计失败: {e}")
            return {}


# 全局异常处理器实例
_exception_handler = None


def get_exception_handler() -> EnhancedExceptionHandler:
    """获取全局异常处理器实例"""
    global _exception_handler
    if _exception_handler is None:
        _exception_handler = EnhancedExceptionHandler()
    return _exception_handler


# 便捷装饰器函数
def handle_exceptions(show_dialog: bool = True, 
                     auto_retry: bool = False,
                     max_retries: int = 3,
                     critical: bool = False,
                     fallback_value: Any = None):
    """
    便捷的异常处理装饰器
    
    Args:
        show_dialog: 是否显示用户友好对话框
        auto_retry: 是否自动重试
        max_retries: 最大重试次数
        critical: 是否为关键操作
        fallback_value: 降级返回值
    """
    config = ExceptionHandlingConfig()
    config.show_user_dialog = show_dialog
    config.auto_retry = auto_retry
    config.max_retries = max_retries
    config.critical_operation = critical
    config.fallback_value = fallback_value
    
    handler = get_exception_handler()
    return handler.handle_exception(config)


def handle_ui_exceptions(fallback_value: Any = None):
    """UI操作异常处理装饰器"""
    config = ExceptionHandlingConfig()
    config.show_user_dialog = True
    config.auto_retry = False
    config.critical_operation = False
    config.fallback_value = fallback_value
    config.auto_close_dialog = 5  # UI异常5秒后自动关闭
    
    handler = get_exception_handler()
    return handler.handle_exception(config)


def handle_critical_exceptions():
    """关键操作异常处理装饰器"""
    config = ExceptionHandlingConfig()
    config.show_user_dialog = True
    config.auto_retry = False
    config.critical_operation = True
    config.user_notification = True
    
    handler = get_exception_handler()
    return handler.handle_exception(config)
