#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一异常处理系统
定义项目中所有自定义异常类和错误码

Author: Augment Agent
Date: 2025-05-30
"""

from enum import Enum
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """错误码枚举"""
    
    # 通用错误 (1000-1099)
    UNKNOWN_ERROR = (1000, "未知错误")
    INVALID_PARAMETER = (1001, "无效参数")
    OPERATION_FAILED = (1002, "操作失败")
    TIMEOUT_ERROR = (1003, "操作超时")
    PERMISSION_DENIED = (1004, "权限不足")
    
    # 设备通信错误 (1100-1199)
    DEVICE_NOT_CONNECTED = (1100, "设备未连接")
    DEVICE_CONNECTION_FAILED = (1101, "设备连接失败")
    DEVICE_COMMUNICATION_ERROR = (1102, "设备通信错误")
    DEVICE_RESPONSE_TIMEOUT = (1103, "设备响应超时")
    DEVICE_COMMAND_FAILED = (1104, "设备命令执行失败")
    INVALID_DEVICE_RESPONSE = (1105, "无效的设备响应")

    # 设备状态码错误 (1110-1119)
    CHANNEL_BATTERY_ERROR = (1110, "通道电池异常")
    CHANNEL_HARDWARE_ERROR = (1111, "通道硬件异常")
    CHANNEL_SETTING_ERROR = (1112, "通道设置异常")
    CHANNEL_STATUS_UNKNOWN = (1113, "通道状态未知")
    CHANNEL_BALANCING_ERROR = (1114, "通道平衡功能异常")
    
    # 测试流程错误 (1200-1299)
    TEST_NOT_STARTED = (1200, "测试未启动")
    TEST_ALREADY_RUNNING = (1201, "测试已在运行")
    TEST_CONFIGURATION_ERROR = (1202, "测试配置错误")
    TEST_EXECUTION_FAILED = (1203, "测试执行失败")
    TEST_DATA_INVALID = (1204, "测试数据无效")
    TEST_CHANNEL_ERROR = (1205, "测试通道错误")
    BATCH_INFO_INVALID = (1206, "批次信息无效")
    BATTERY_CODE_INVALID = (1207, "电池码无效")
    
    # 数据处理错误 (1300-1399)
    DATA_PROCESSING_ERROR = (1300, "数据处理错误")
    DATA_VALIDATION_FAILED = (1301, "数据验证失败")
    DATA_SAVE_FAILED = (1302, "数据保存失败")
    DATA_LOAD_FAILED = (1303, "数据加载失败")
    DATA_FORMAT_ERROR = (1304, "数据格式错误")
    CALCULATION_ERROR = (1305, "计算错误")
    
    # 配置错误 (1400-1499)
    CONFIG_LOAD_FAILED = (1400, "配置加载失败")
    CONFIG_SAVE_FAILED = (1401, "配置保存失败")
    CONFIG_VALIDATION_FAILED = (1402, "配置验证失败")
    CONFIG_NOT_FOUND = (1403, "配置未找到")
    CONFIG_FORMAT_ERROR = (1404, "配置格式错误")
    
    # 数据库错误 (1500-1599)
    DATABASE_CONNECTION_FAILED = (1500, "数据库连接失败")
    DATABASE_QUERY_FAILED = (1501, "数据库查询失败")
    DATABASE_INSERT_FAILED = (1502, "数据库插入失败")
    DATABASE_UPDATE_FAILED = (1503, "数据库更新失败")
    DATABASE_DELETE_FAILED = (1504, "数据库删除失败")
    
    # UI错误 (1600-1699)
    UI_COMPONENT_ERROR = (1600, "UI组件错误")
    UI_UPDATE_FAILED = (1601, "UI更新失败")
    UI_EVENT_HANDLER_ERROR = (1602, "UI事件处理错误")
    
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class TestSystemException(Exception):
    """测试系统基础异常类"""
    
    def __init__(self, 
                 error_code: ErrorCode, 
                 detail: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None,
                 cause: Optional[Exception] = None):
        """
        初始化异常
        
        Args:
            error_code: 错误码
            detail: 详细错误信息
            context: 错误上下文信息
            cause: 原始异常
        """
        self.error_code = error_code
        self.detail = detail or ""
        self.context = context or {}
        self.cause = cause
        
        # 构建完整的错误消息
        message = f"[{error_code.code}] {error_code.message}"
        if detail:
            message += f": {detail}"
        
        super().__init__(message)
        
        # 记录异常日志
        self._log_exception()
    
    def _log_exception(self):
        """记录异常日志"""
        log_message = f"异常发生 - 错误码: {self.error_code.code}, 消息: {self.error_code.message}"
        if self.detail:
            log_message += f", 详情: {self.detail}"
        if self.context:
            log_message += f", 上下文: {self.context}"
        if self.cause:
            log_message += f", 原因: {str(self.cause)}"
        
        logger.error(log_message, exc_info=self.cause is not None)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_code': self.error_code.code,
            'error_message': self.error_code.message,
            'detail': self.detail,
            'context': self.context,
            'cause': str(self.cause) if self.cause else None
        }


class DeviceException(TestSystemException):
    """设备相关异常"""
    
    def __init__(self, error_code: ErrorCode, detail: Optional[str] = None, 
                 device_info: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        context = {'device_info': device_info} if device_info else None
        super().__init__(error_code, detail, context, cause)


class TestException(TestSystemException):
    """测试流程相关异常"""
    
    def __init__(self, error_code: ErrorCode, detail: Optional[str] = None,
                 test_info: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        context = {'test_info': test_info} if test_info else None
        super().__init__(error_code, detail, context, cause)


class DataException(TestSystemException):
    """数据处理相关异常"""
    
    def __init__(self, error_code: ErrorCode, detail: Optional[str] = None,
                 data_info: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        context = {'data_info': data_info} if data_info else None
        super().__init__(error_code, detail, context, cause)


class ConfigException(TestSystemException):
    """配置相关异常"""
    
    def __init__(self, error_code: ErrorCode, detail: Optional[str] = None,
                 config_info: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        context = {'config_info': config_info} if config_info else None
        super().__init__(error_code, detail, context, cause)


class DatabaseException(TestSystemException):
    """数据库相关异常"""
    
    def __init__(self, error_code: ErrorCode, detail: Optional[str] = None,
                 db_info: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        context = {'db_info': db_info} if db_info else None
        super().__init__(error_code, detail, context, cause)


class UIException(TestSystemException):
    """UI相关异常"""

    def __init__(self, error_code: ErrorCode, detail: Optional[str] = None,
                 ui_info: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        context = {'ui_info': ui_info} if ui_info else None
        super().__init__(error_code, detail, context, cause)


class ChannelStatusException(DeviceException):
    """通道状态异常"""

    def __init__(self, error_code: ErrorCode, channel_index: int, status_code: int,
                 detail: Optional[str] = None, cause: Optional[Exception] = None):
        """
        初始化通道状态异常

        Args:
            error_code: 错误码
            channel_index: 通道索引（0-7）
            status_code: 设备状态码
            detail: 详细错误信息
            cause: 原始异常
        """
        device_info = {
            'channel_index': channel_index,
            'channel_number': channel_index + 1,
            'status_code': status_code,
            'status_code_hex': f'0x{status_code:04X}'
        }

        if not detail:
            detail = f"通道{channel_index + 1}状态异常(0x{status_code:04X})"

        super().__init__(error_code, detail, device_info, cause)


def handle_exception(func):
    """异常处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TestSystemException:
            # 重新抛出自定义异常
            raise
        except Exception as e:
            # 将其他异常包装为TestSystemException
            logger.error(f"未处理的异常在函数 {func.__name__}: {e}", exc_info=True)
            raise TestSystemException(
                ErrorCode.UNKNOWN_ERROR,
                detail=f"函数 {func.__name__} 执行失败: {str(e)}",
                cause=e
            )
    return wrapper


def validate_parameter(condition: bool, parameter_name: str, expected: str):
    """参数验证辅助函数"""
    if not condition:
        raise TestSystemException(
            ErrorCode.INVALID_PARAMETER,
            detail=f"参数 {parameter_name} 无效，期望: {expected}"
        )


def validate_device_connection(is_connected: bool, device_name: str = "设备"):
    """设备连接验证辅助函数"""
    if not is_connected:
        raise DeviceException(
            ErrorCode.DEVICE_NOT_CONNECTED,
            detail=f"{device_name}未连接",
            device_info={'device_name': device_name}
        )


def validate_test_state(is_testing: bool, operation: str):
    """测试状态验证辅助函数"""
    if is_testing and operation in ['start', 'begin']:
        raise TestException(
            ErrorCode.TEST_ALREADY_RUNNING,
            detail=f"无法执行操作 '{operation}'，测试已在运行"
        )
    elif not is_testing and operation in ['stop', 'pause', 'continue']:
        raise TestException(
            ErrorCode.TEST_NOT_STARTED,
            detail=f"无法执行操作 '{operation}'，测试未启动"
        )


def safe_execute(func, *args, error_code: ErrorCode = ErrorCode.OPERATION_FAILED, 
                detail: Optional[str] = None, **kwargs):
    """安全执行函数，自动处理异常"""
    try:
        return func(*args, **kwargs)
    except TestSystemException:
        raise
    except Exception as e:
        raise TestSystemException(
            error_code,
            detail=detail or f"执行函数 {func.__name__} 失败: {str(e)}",
            cause=e
        )
