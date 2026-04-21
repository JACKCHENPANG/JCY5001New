#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误处理管理器
提供统一的错误处理、恢复和通知机制

Author: Augment Agent
Date: 2025-05-30
"""

import logging
import traceback
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from backend.exceptions import (
    TestSystemException, ErrorCode, DeviceException, TestException,
    DataException, ConfigException, DatabaseException, UIException,
    ChannelStatusException
)

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    CRITICAL = "严重"


class ErrorRecoveryStrategy(Enum):
    """错误恢复策略"""
    IGNORE = "忽略"
    RETRY = "重试"
    FALLBACK = "降级"
    STOP = "停止"
    USER_INTERVENTION = "用户干预"


class ErrorRecord:
    """错误记录"""
    
    def __init__(self, exception: TestSystemException, severity: ErrorSeverity,
                 recovery_strategy: ErrorRecoveryStrategy, timestamp: datetime = None):
        self.exception = exception
        self.severity = severity
        self.recovery_strategy = recovery_strategy
        self.timestamp = timestamp or datetime.now()
        self.resolved = False
        self.resolution_notes = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'error_code': self.exception.error_code.code,
            'error_message': self.exception.error_code.message,
            'detail': self.exception.detail,
            'severity': self.severity.value,
            'recovery_strategy': self.recovery_strategy.value,
            'context': self.exception.context,
            'resolved': self.resolved,
            'resolution_notes': self.resolution_notes
        }


class ErrorHandler:
    """错误处理管理器"""
    
    def __init__(self):
        self.error_records: List[ErrorRecord] = []
        self.error_callbacks: Dict[ErrorCode, List[Callable]] = {}
        self.recovery_handlers: Dict[ErrorCode, Callable] = {}
        self.severity_mapping = self._init_severity_mapping()
        self.recovery_mapping = self._init_recovery_mapping()
        
        logger.debug("错误处理管理器初始化完成")
    
    def _init_severity_mapping(self) -> Dict[ErrorCode, ErrorSeverity]:
        """初始化错误严重程度映射"""
        return {
            # 严重错误
            ErrorCode.DEVICE_NOT_CONNECTED: ErrorSeverity.CRITICAL,
            ErrorCode.DATABASE_CONNECTION_FAILED: ErrorSeverity.CRITICAL,
            ErrorCode.TEST_EXECUTION_FAILED: ErrorSeverity.HIGH,
            ErrorCode.CHANNEL_HARDWARE_ERROR: ErrorSeverity.CRITICAL,

            # 高级错误
            ErrorCode.DEVICE_COMMUNICATION_ERROR: ErrorSeverity.HIGH,
            ErrorCode.DATA_SAVE_FAILED: ErrorSeverity.HIGH,
            ErrorCode.CONFIG_LOAD_FAILED: ErrorSeverity.HIGH,
            ErrorCode.CHANNEL_SETTING_ERROR: ErrorSeverity.HIGH,

            # 中级错误
            ErrorCode.DEVICE_RESPONSE_TIMEOUT: ErrorSeverity.MEDIUM,
            ErrorCode.DATA_VALIDATION_FAILED: ErrorSeverity.MEDIUM,
            ErrorCode.TEST_CONFIGURATION_ERROR: ErrorSeverity.MEDIUM,
            ErrorCode.CHANNEL_BATTERY_ERROR: ErrorSeverity.MEDIUM,
            ErrorCode.CHANNEL_BALANCING_ERROR: ErrorSeverity.MEDIUM,

            # 低级错误
            ErrorCode.INVALID_PARAMETER: ErrorSeverity.LOW,
            ErrorCode.UI_UPDATE_FAILED: ErrorSeverity.LOW,
            ErrorCode.CHANNEL_STATUS_UNKNOWN: ErrorSeverity.LOW,
        }
    
    def _init_recovery_mapping(self) -> Dict[ErrorCode, ErrorRecoveryStrategy]:
        """初始化错误恢复策略映射"""
        return {
            # 需要停止的错误
            ErrorCode.DEVICE_NOT_CONNECTED: ErrorRecoveryStrategy.STOP,
            ErrorCode.DATABASE_CONNECTION_FAILED: ErrorRecoveryStrategy.STOP,
            ErrorCode.CHANNEL_HARDWARE_ERROR: ErrorRecoveryStrategy.STOP,

            # 可以重试的错误
            ErrorCode.DEVICE_COMMUNICATION_ERROR: ErrorRecoveryStrategy.RETRY,
            ErrorCode.DEVICE_RESPONSE_TIMEOUT: ErrorRecoveryStrategy.RETRY,
            ErrorCode.DATA_SAVE_FAILED: ErrorRecoveryStrategy.RETRY,

            # 需要降级的错误（跳过异常通道）
            ErrorCode.TEST_CONFIGURATION_ERROR: ErrorRecoveryStrategy.FALLBACK,
            ErrorCode.DATA_VALIDATION_FAILED: ErrorRecoveryStrategy.FALLBACK,
            ErrorCode.CHANNEL_BATTERY_ERROR: ErrorRecoveryStrategy.FALLBACK,
            ErrorCode.CHANNEL_SETTING_ERROR: ErrorRecoveryStrategy.FALLBACK,
            ErrorCode.CHANNEL_BALANCING_ERROR: ErrorRecoveryStrategy.FALLBACK,

            # 可以忽略的错误
            ErrorCode.UI_UPDATE_FAILED: ErrorRecoveryStrategy.IGNORE,
            ErrorCode.CHANNEL_STATUS_UNKNOWN: ErrorRecoveryStrategy.IGNORE,

            # 需要用户干预的错误
            ErrorCode.CONFIG_LOAD_FAILED: ErrorRecoveryStrategy.USER_INTERVENTION,
            ErrorCode.BATCH_INFO_INVALID: ErrorRecoveryStrategy.USER_INTERVENTION,
        }
    
    def register_error_callback(self, error_code: ErrorCode, callback: Callable):
        """注册错误回调函数"""
        if error_code not in self.error_callbacks:
            self.error_callbacks[error_code] = []
        self.error_callbacks[error_code].append(callback)
        logger.debug(f"注册错误回调: {error_code.name}")
    
    def register_recovery_handler(self, error_code: ErrorCode, handler: Callable):
        """注册错误恢复处理器"""
        self.recovery_handlers[error_code] = handler
        logger.debug(f"注册恢复处理器: {error_code.name}")
    
    def handle_exception(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        处理异常
        
        Args:
            exception: 异常对象
            context: 额外上下文信息
            
        Returns:
            是否成功处理异常
        """
        try:
            # 转换为TestSystemException
            if not isinstance(exception, TestSystemException):
                exception = TestSystemException(
                    ErrorCode.UNKNOWN_ERROR,
                    detail=str(exception),
                    context=context,
                    cause=exception
                )
            
            # 获取错误严重程度和恢复策略
            severity = self.severity_mapping.get(exception.error_code, ErrorSeverity.MEDIUM)
            recovery_strategy = self.recovery_mapping.get(exception.error_code, ErrorRecoveryStrategy.USER_INTERVENTION)
            
            # 创建错误记录
            error_record = ErrorRecord(exception, severity, recovery_strategy)
            self.error_records.append(error_record)
            
            # 记录错误日志
            self._log_error(error_record)
            
            # 触发错误回调
            self._trigger_error_callbacks(exception)
            
            # 执行恢复策略
            recovery_success = self._execute_recovery_strategy(error_record)
            
            if recovery_success:
                error_record.resolved = True
                error_record.resolution_notes = f"通过{recovery_strategy.value}策略成功恢复"
                logger.info(f"错误已恢复: {exception.error_code.name}")
            
            return recovery_success
            
        except Exception as e:
            logger.error(f"处理异常时发生错误: {e}", exc_info=True)
            return False
    
    def _log_error(self, error_record: ErrorRecord):
        """记录错误日志"""
        exception = error_record.exception
        log_message = (
            f"错误处理 - 代码: {exception.error_code.code}, "
            f"消息: {exception.error_code.message}, "
            f"严重程度: {error_record.severity.value}, "
            f"恢复策略: {error_record.recovery_strategy.value}"
        )
        
        if exception.detail:
            log_message += f", 详情: {exception.detail}"
        
        # 根据严重程度选择日志级别
        if error_record.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error_record.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error_record.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _trigger_error_callbacks(self, exception: TestSystemException):
        """触发错误回调"""
        callbacks = self.error_callbacks.get(exception.error_code, [])
        for callback in callbacks:
            try:
                callback(exception)
            except Exception as e:
                logger.error(f"错误回调执行失败: {e}", exc_info=True)
    
    def _execute_recovery_strategy(self, error_record: ErrorRecord) -> bool:
        """执行恢复策略"""
        strategy = error_record.recovery_strategy
        exception = error_record.exception
        
        try:
            if strategy == ErrorRecoveryStrategy.IGNORE:
                logger.info(f"忽略错误: {exception.error_code.name}")
                return True
            
            elif strategy == ErrorRecoveryStrategy.RETRY:
                return self._handle_retry_recovery(error_record)
            
            elif strategy == ErrorRecoveryStrategy.FALLBACK:
                return self._handle_fallback_recovery(error_record)
            
            elif strategy == ErrorRecoveryStrategy.STOP:
                return self._handle_stop_recovery(error_record)
            
            elif strategy == ErrorRecoveryStrategy.USER_INTERVENTION:
                return self._handle_user_intervention_recovery(error_record)
            
            else:
                logger.warning(f"未知的恢复策略: {strategy}")
                return False
                
        except Exception as e:
            logger.error(f"执行恢复策略失败: {e}", exc_info=True)
            return False
    
    def _handle_retry_recovery(self, error_record: ErrorRecord) -> bool:
        """处理重试恢复"""
        return self._execute_recovery_handler(
            error_record,
            "重试",
            logger.info,
            True  # 返回处理器结果
        )

    def _handle_fallback_recovery(self, error_record: ErrorRecord) -> bool:
        """处理降级恢复"""
        return self._execute_recovery_handler(
            error_record,
            "降级",
            logger.info,
            True  # 返回处理器结果
        )

    def _handle_stop_recovery(self, error_record: ErrorRecord) -> bool:
        """处理停止恢复"""
        exception = error_record.exception
        logger.critical(f"严重错误，需要停止操作: {exception.error_code.name}")

        # 执行停止处理器，但总是返回False
        self._execute_recovery_handler(
            error_record,
            "停止",
            logger.critical,
            False  # 忽略处理器结果
        )
        return False  # 停止策略总是返回False，表示无法恢复

    def _handle_user_intervention_recovery(self, error_record: ErrorRecord) -> bool:
        """处理用户干预恢复"""
        return self._execute_recovery_handler(
            error_record,
            "用户干预",
            logger.warning,
            True  # 返回处理器结果
        )

    def _execute_recovery_handler(self, error_record: ErrorRecord, recovery_type: str,
                                 log_func, return_handler_result: bool) -> bool:
        """
        执行恢复处理器的通用模板方法

        Args:
            error_record: 错误记录
            recovery_type: 恢复类型名称
            log_func: 日志记录函数
            return_handler_result: 是否返回处理器的执行结果

        Returns:
            恢复是否成功
        """
        exception = error_record.exception

        # 检查是否有注册的恢复处理器
        if exception.error_code in self.recovery_handlers:
            try:
                handler = self.recovery_handlers[exception.error_code]
                result = handler(exception)
                log_func(f"{recovery_type}恢复成功: {exception.error_code.name}")
                return result if return_handler_result else True
            except Exception as e:
                logger.error(f"{recovery_type}恢复失败: {e}", exc_info=True)
                return False

        logger.warning(f"没有注册的{recovery_type}处理器: {exception.error_code.name}")
        return False
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        total_errors = len(self.error_records)
        resolved_errors = sum(1 for record in self.error_records if record.resolved)
        
        severity_counts = {}
        for severity in ErrorSeverity:
            severity_counts[severity.value] = sum(
                1 for record in self.error_records if record.severity == severity
            )
        
        return {
            'total_errors': total_errors,
            'resolved_errors': resolved_errors,
            'unresolved_errors': total_errors - resolved_errors,
            'resolution_rate': resolved_errors / total_errors if total_errors > 0 else 0,
            'severity_distribution': severity_counts,
            'recent_errors': [record.to_dict() for record in self.error_records[-10:]]
        }
    
    def clear_error_history(self):
        """清除错误历史记录"""
        self.error_records.clear()
        logger.info("错误历史记录已清除")


# 全局错误处理器实例
global_error_handler = ErrorHandler()
