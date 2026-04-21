"""
异常处理工具类 - 统一异常处理模式
用于减少项目中重复的异常处理代码
"""

import logging
import functools
import traceback
from typing import Any, Optional, Callable, Type, Union, Dict
from datetime import datetime


class ExceptionHelper:
    """异常处理助手类 - 提供统一的异常处理功能"""
    
    @staticmethod
    def safe_execute(func: Callable, *args, default_return=None, 
                    logger: Optional[logging.Logger] = None, 
                    operation_name: str = None, **kwargs) -> Any:
        """
        安全执行函数，捕获异常并返回默认值
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            default_return: 异常时的默认返回值
            logger: 日志记录器
            operation_name: 操作名称
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果或默认值
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if logger:
                op_name = operation_name or getattr(func, '__name__', '未知操作')
                logger.error(f"安全执行失败 - {op_name}: {e}", exc_info=True)
            return default_return
    
    @staticmethod
    def safe_get_attribute(obj: Any, attr_name: str, default=None, 
                          logger: Optional[logging.Logger] = None) -> Any:
        """
        安全获取对象属性
        
        Args:
            obj: 对象
            attr_name: 属性名
            default: 默认值
            logger: 日志记录器
            
        Returns:
            属性值或默认值
        """
        try:
            return getattr(obj, attr_name, default)
        except Exception as e:
            if logger:
                logger.error(f"获取属性失败 - {attr_name}: {e}")
            return default
    
    @staticmethod
    def safe_dict_get(data: dict, key: str, default=None, 
                     logger: Optional[logging.Logger] = None) -> Any:
        """
        安全获取字典值
        
        Args:
            data: 字典
            key: 键名
            default: 默认值
            logger: 日志记录器
            
        Returns:
            字典值或默认值
        """
        try:
            return data.get(key, default)
        except Exception as e:
            if logger:
                logger.error(f"获取字典值失败 - {key}: {e}")
            return default
    
    @staticmethod
    def safe_convert(value: Any, target_type: Type, default=None, 
                    logger: Optional[logging.Logger] = None) -> Any:
        """
        安全类型转换
        
        Args:
            value: 要转换的值
            target_type: 目标类型
            default: 转换失败时的默认值
            logger: 日志记录器
            
        Returns:
            转换后的值或默认值
        """
        try:
            return target_type(value)
        except Exception as e:
            if logger:
                logger.error(f"类型转换失败 - {value} -> {target_type.__name__}: {e}")
            return default
    
    @staticmethod
    def format_exception_info(exception: Exception) -> Dict[str, Any]:
        """
        格式化异常信息
        
        Args:
            exception: 异常对象
            
        Returns:
            格式化的异常信息字典
        """
        return {
            'type': type(exception).__name__,
            'message': str(exception),
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def log_exception_details(logger: logging.Logger, exception: Exception, 
                             context: str = "", **extra_info) -> None:
        """
        详细记录异常信息
        
        Args:
            logger: 日志记录器
            exception: 异常对象
            context: 上下文信息
            **extra_info: 额外信息
        """
        exc_info = ExceptionHelper.format_exception_info(exception)
        
        message = f"异常详情"
        if context:
            message += f" - {context}"
        
        message += f": {exc_info['type']} - {exc_info['message']}"
        
        if extra_info:
            extra_str = ", ".join([f"{k}={v}" for k, v in extra_info.items()])
            message += f" ({extra_str})"
        
        logger.error(message, exc_info=True)


def exception_handler(default_return=None, logger: Optional[logging.Logger] = None, 
                     reraise: bool = False, log_level: str = "error"):
    """
    异常处理装饰器
    
    Args:
        default_return: 异常时的默认返回值
        logger: 日志记录器
        reraise: 是否重新抛出异常
        log_level: 日志级别
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 记录异常
                func_logger = logger or logging.getLogger(func.__module__)
                log_func = getattr(func_logger, log_level, func_logger.error)
                
                ExceptionHelper.log_exception_details(
                    func_logger, e, f"函数 {func.__name__} 执行失败"
                )
                
                if reraise:
                    raise
                else:
                    return default_return
        
        return wrapper
    return decorator


def method_exception_handler(default_return=None, logger: Optional[logging.Logger] = None, 
                            reraise: bool = False, log_level: str = "error"):
    """
    方法异常处理装饰器
    
    Args:
        default_return: 异常时的默认返回值
        logger: 日志记录器
        reraise: 是否重新抛出异常
        log_level: 日志级别
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                # 记录异常
                method_logger = logger or logging.getLogger(self.__class__.__module__)
                
                ExceptionHelper.log_exception_details(
                    method_logger, e, 
                    f"方法 {self.__class__.__name__}.{func.__name__} 执行失败"
                )
                
                if reraise:
                    raise
                else:
                    return default_return
        
        return wrapper
    return decorator


class ExceptionContext:
    """异常上下文管理器 - 用于统一处理代码块中的异常"""
    
    def __init__(self, logger: logging.Logger, operation: str, 
                 default_return=None, reraise: bool = False, **context):
        """
        初始化异常上下文管理器
        
        Args:
            logger: 日志记录器
            operation: 操作名称
            default_return: 异常时的默认返回值
            reraise: 是否重新抛出异常
            **context: 上下文信息
        """
        self.logger = logger
        self.operation = operation
        self.default_return = default_return
        self.reraise = reraise
        self.context = context
        self.exception_occurred = False
        self.result = None
    
    def __enter__(self):
        """进入上下文"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时处理异常"""
        if exc_type is not None:
            self.exception_occurred = True
            
            # 记录异常详情
            ExceptionHelper.log_exception_details(
                self.logger, exc_val, self.operation, **self.context
            )
            
            if not self.reraise:
                # 抑制异常，返回默认值
                self.result = self.default_return
                return True  # 抑制异常
        
        return False  # 不抑制异常
    
    def get_result(self):
        """获取结果"""
        return self.result


class RetryHandler:
    """重试处理器 - 提供统一的重试机制"""
    
    def __init__(self, max_retries: int = 3, delay: float = 1.0, 
                 backoff_factor: float = 2.0, logger: Optional[logging.Logger] = None):
        """
        初始化重试处理器
        
        Args:
            max_retries: 最大重试次数
            delay: 初始延迟时间（秒）
            backoff_factor: 退避因子
            logger: 日志记录器
        """
        self.max_retries = max_retries
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.logger = logger
    
    def execute_with_retry(self, func: Callable, *args, 
                          exception_types: tuple = (Exception,), **kwargs) -> Any:
        """
        带重试的执行函数
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            exception_types: 需要重试的异常类型
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            最后一次执行的异常
        """
        last_exception = None
        current_delay = self.delay
        
        for attempt in range(self.max_retries + 1):
            try:
                if self.logger and attempt > 0:
                    self.logger.info(f"重试执行 {func.__name__} (第{attempt}次)")
                
                return func(*args, **kwargs)
                
            except exception_types as e:
                last_exception = e
                
                if self.logger:
                    self.logger.warning(f"执行失败 {func.__name__} (第{attempt + 1}次): {e}")
                
                if attempt < self.max_retries:
                    if self.logger:
                        self.logger.info(f"等待 {current_delay:.1f}s 后重试...")
                    
                    import time
                    time.sleep(current_delay)
                    current_delay *= self.backoff_factor
                else:
                    if self.logger:
                        self.logger.error(f"重试次数已用完，最终失败: {e}")
                    break
        
        # 重新抛出最后一次的异常
        if last_exception:
            raise last_exception


def retry_on_exception(max_retries: int = 3, delay: float = 1.0, 
                      backoff_factor: float = 2.0, 
                      exception_types: tuple = (Exception,),
                      logger: Optional[logging.Logger] = None):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff_factor: 退避因子
        exception_types: 需要重试的异常类型
        logger: 日志记录器
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retry_handler = RetryHandler(max_retries, delay, backoff_factor, logger)
            return retry_handler.execute_with_retry(func, *args, 
                                                   exception_types=exception_types, **kwargs)
        
        return wrapper
    return decorator


# 便捷函数
def create_exception_context(logger: logging.Logger, operation: str, 
                           default_return=None, reraise: bool = False, **context) -> ExceptionContext:
    """
    创建异常上下文管理器
    
    Args:
        logger: 日志记录器
        operation: 操作名称
        default_return: 异常时的默认返回值
        reraise: 是否重新抛出异常
        **context: 上下文信息
        
    Returns:
        异常上下文管理器
    """
    return ExceptionContext(logger, operation, default_return, reraise, **context)
