"""
日志记录工具类 - 统一日志记录模式
用于减少项目中重复的日志记录代码
"""

import logging
import functools
from typing import Any, Optional, Callable
from datetime import datetime


class LoggerHelper:
    """日志记录助手类 - 提供统一的日志记录功能"""
    
    @staticmethod
    def log_operation_start(logger: logging.Logger, operation: str, **kwargs) -> None:
        """
        记录操作开始日志
        
        Args:
            logger: 日志记录器
            operation: 操作名称
            **kwargs: 额外的上下文信息
        """
        context = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        message = f"🚀 开始{operation}"
        if context:
            message += f" ({context})"
        logger.info(message)
    
    @staticmethod
    def log_operation_success(logger: logging.Logger, operation: str, **kwargs) -> None:
        """
        记录操作成功日志
        
        Args:
            logger: 日志记录器
            operation: 操作名称
            **kwargs: 额外的上下文信息
        """
        context = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        message = f"✅ {operation}成功"
        if context:
            message += f" ({context})"
        logger.info(message)
    
    @staticmethod
    def log_operation_failure(logger: logging.Logger, operation: str, error: Exception, **kwargs) -> None:
        """
        记录操作失败日志
        
        Args:
            logger: 日志记录器
            operation: 操作名称
            error: 异常对象
            **kwargs: 额外的上下文信息
        """
        context = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        message = f"❌ {operation}失败: {error}"
        if context:
            message += f" ({context})"
        logger.error(message, exc_info=True)
    
    @staticmethod
    def log_progress(logger: logging.Logger, operation: str, current: int, total: int, **kwargs) -> None:
        """
        记录进度日志
        
        Args:
            logger: 日志记录器
            operation: 操作名称
            current: 当前进度
            total: 总数
            **kwargs: 额外的上下文信息
        """
        percentage = (current / total * 100) if total > 0 else 0
        context = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        message = f"📊 {operation}进度: {current}/{total} ({percentage:.1f}%)"
        if context:
            message += f" ({context})"
        logger.debug(message)
    
    @staticmethod
    def log_config_change(logger: logging.Logger, config_key: str, old_value: Any, new_value: Any) -> None:
        """
        记录配置变更日志
        
        Args:
            logger: 日志记录器
            config_key: 配置键名
            old_value: 旧值
            new_value: 新值
        """
    
    @staticmethod
    def log_device_status(logger: logging.Logger, device: str, status: str, **kwargs) -> None:
        """
        记录设备状态日志
        
        Args:
            logger: 日志记录器
            device: 设备名称
            status: 状态描述
            **kwargs: 额外的设备信息
        """
        context = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        message = f"🔌 设备状态: {device} - {status}"
        if context:
            message += f" ({context})"
        logger.info(message)
    
    @staticmethod
    def log_test_result(logger: logging.Logger, channel: int, result: dict) -> None:
        """
        记录测试结果日志
        
        Args:
            logger: 日志记录器
            channel: 通道号
            result: 测试结果字典
        """
        voltage = result.get('voltage', 0.0)
        rs_value = result.get('rs_value', 0.0)
        rct_value = result.get('rct_value', 0.0)
        is_pass = result.get('is_pass', False)
        
        status = "✅ 合格" if is_pass else "❌ 不合格"
        logger.info(f"📋 通道{channel}测试结果: {status} (电压={voltage:.3f}V, Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ)")
    
    @staticmethod
    def log_performance_metric(logger: logging.Logger, metric_name: str, value: float, unit: str = "") -> None:
        """
        记录性能指标日志
        
        Args:
            logger: 日志记录器
            metric_name: 指标名称
            value: 指标值
            unit: 单位
        """
        logger.debug(f"⏱️ 性能指标: {metric_name} = {value:.3f}{unit}")


def log_function_call(logger: Optional[logging.Logger] = None):
    """
    函数调用日志装饰器
    
    Args:
        logger: 日志记录器，如果为None则使用函数所在模块的logger
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取日志记录器
            func_logger = logger or logging.getLogger(func.__module__)
            
            # 记录函数调用开始
            func_name = func.__name__
            LoggerHelper.log_operation_start(func_logger, f"调用{func_name}")
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 记录函数调用成功
                LoggerHelper.log_operation_success(func_logger, f"调用{func_name}")
                
                return result
                
            except Exception as e:
                # 记录函数调用失败
                LoggerHelper.log_operation_failure(func_logger, f"调用{func_name}", e)
                raise
        
        return wrapper
    return decorator


def log_method_call(logger: Optional[logging.Logger] = None):
    """
    方法调用日志装饰器
    
    Args:
        logger: 日志记录器，如果为None则使用方法所在类的logger
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # 获取日志记录器
            method_logger = logger or logging.getLogger(self.__class__.__module__)
            
            # 记录方法调用开始
            class_name = self.__class__.__name__
            method_name = func.__name__
            LoggerHelper.log_operation_start(method_logger, f"{class_name}.{method_name}")
            
            try:
                # 执行方法
                result = func(self, *args, **kwargs)
                
                # 记录方法调用成功
                LoggerHelper.log_operation_success(method_logger, f"{class_name}.{method_name}")
                
                return result
                
            except Exception as e:
                # 记录方法调用失败
                LoggerHelper.log_operation_failure(method_logger, f"{class_name}.{method_name}", e)
                raise
        
        return wrapper
    return decorator


class ContextLogger:
    """上下文日志记录器 - 用于记录操作的开始和结束"""
    
    def __init__(self, logger: logging.Logger, operation: str, **context):
        """
        初始化上下文日志记录器
        
        Args:
            logger: 日志记录器
            operation: 操作名称
            **context: 上下文信息
        """
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        """进入上下文时记录开始日志"""
        self.start_time = datetime.now()
        LoggerHelper.log_operation_start(self.logger, self.operation, **self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时记录结束日志"""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            self.context['耗时'] = f"{duration:.3f}s"
        
        if exc_type is None:
            # 正常结束
            LoggerHelper.log_operation_success(self.logger, self.operation, **self.context)
        else:
            # 异常结束
            LoggerHelper.log_operation_failure(self.logger, self.operation, exc_val, **self.context)


# 便捷函数
def create_context_logger(logger: logging.Logger, operation: str, **context) -> ContextLogger:
    """
    创建上下文日志记录器
    
    Args:
        logger: 日志记录器
        operation: 操作名称
        **context: 上下文信息
        
    Returns:
        上下文日志记录器
    """
    return ContextLogger(logger, operation, **context)


def get_logger_for_class(cls) -> logging.Logger:
    """
    为类获取日志记录器
    
    Args:
        cls: 类对象
        
    Returns:
        日志记录器
    """
    return logging.getLogger(f"{cls.__module__}.{cls.__name__}")


def get_logger_for_function(func) -> logging.Logger:
    """
    为函数获取日志记录器
    
    Args:
        func: 函数对象
        
    Returns:
        日志记录器
    """
    return logging.getLogger(f"{func.__module__}.{func.__name__}")
