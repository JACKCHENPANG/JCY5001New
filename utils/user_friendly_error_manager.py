# -*- coding: utf-8 -*-
"""
用户友好错误消息管理器
将技术性错误转换为用户易懂的中文消息，并提供解决建议

Author: Jack
Date: 2025-01-09
"""

import logging
from typing import Dict, Tuple, Optional, List
from enum import Enum
from backend.exceptions import ErrorCode

logger = logging.getLogger(__name__)


class ErrorSeverityLevel(Enum):
    """错误严重程度级别"""
    INFO = ("信息", "#2196F3", "ℹ️")      # 蓝色，信息图标
    WARNING = ("警告", "#FF9800", "⚠️")   # 橙色，警告图标  
    ERROR = ("错误", "#F44336", "❌")     # 红色，错误图标
    CRITICAL = ("严重", "#9C27B0", "🚨")  # 紫色，严重图标


class UserFriendlyErrorManager:
    """用户友好错误消息管理器"""
    
    def __init__(self):
        self.error_messages = self._init_error_messages()
        self.error_solutions = self._init_error_solutions()
        self.error_severity_mapping = self._init_severity_mapping()
        
    def _init_error_messages(self) -> Dict[ErrorCode, str]:
        """初始化用户友好的错误消息"""
        return {
            # 通用错误
            ErrorCode.UNKNOWN_ERROR: "系统遇到了未知问题",
            ErrorCode.INVALID_PARAMETER: "输入的参数不正确",
            ErrorCode.OPERATION_FAILED: "操作执行失败",
            ErrorCode.TIMEOUT_ERROR: "操作超时，请稍后重试",
            ErrorCode.PERMISSION_DENIED: "没有执行此操作的权限",
            
            # 设备通信错误
            ErrorCode.DEVICE_NOT_CONNECTED: "设备未连接",
            ErrorCode.DEVICE_CONNECTION_FAILED: "无法连接到测试设备",
            ErrorCode.DEVICE_COMMUNICATION_ERROR: "与设备通信时出现问题",
            ErrorCode.DEVICE_RESPONSE_TIMEOUT: "设备响应超时",
            ErrorCode.DEVICE_COMMAND_FAILED: "设备命令执行失败",
            ErrorCode.INVALID_DEVICE_RESPONSE: "设备返回了无效的响应",
            
            # 通道状态错误
            ErrorCode.CHANNEL_BATTERY_ERROR: "通道电池状态异常",
            ErrorCode.CHANNEL_HARDWARE_ERROR: "通道硬件出现故障",
            ErrorCode.CHANNEL_SETTING_ERROR: "通道设置有误",
            ErrorCode.CHANNEL_STATUS_UNKNOWN: "通道状态未知",
            ErrorCode.CHANNEL_BALANCING_ERROR: "通道平衡功能异常",
            
            # 测试流程错误
            ErrorCode.TEST_NOT_STARTED: "测试尚未开始",
            ErrorCode.TEST_ALREADY_RUNNING: "测试已在运行中",
            ErrorCode.TEST_CONFIGURATION_ERROR: "测试配置有误",
            ErrorCode.TEST_EXECUTION_FAILED: "测试执行失败",
            ErrorCode.TEST_DATA_INVALID: "测试数据无效",
            ErrorCode.TEST_CHANNEL_ERROR: "测试通道异常",
            
            # 数据处理错误
            ErrorCode.DATA_PROCESSING_ERROR: "数据处理出错",
            ErrorCode.DATA_VALIDATION_FAILED: "数据验证失败",
            ErrorCode.DATA_SAVE_FAILED: "数据保存失败",
            ErrorCode.DATA_LOAD_FAILED: "数据加载失败",
            ErrorCode.DATA_FORMAT_ERROR: "数据格式错误",
            ErrorCode.CALCULATION_ERROR: "计算错误",

            # 配置错误
            ErrorCode.CONFIG_LOAD_FAILED: "配置加载失败",
            ErrorCode.CONFIG_SAVE_FAILED: "配置保存失败",
            ErrorCode.CONFIG_VALIDATION_FAILED: "配置验证失败",
            ErrorCode.CONFIG_NOT_FOUND: "找不到配置文件",
            ErrorCode.CONFIG_FORMAT_ERROR: "配置格式错误",

            # 数据库错误
            ErrorCode.DATABASE_CONNECTION_FAILED: "无法连接到数据库",
            ErrorCode.DATABASE_QUERY_FAILED: "数据库查询失败",
            ErrorCode.DATABASE_INSERT_FAILED: "数据库插入失败",
            ErrorCode.DATABASE_UPDATE_FAILED: "数据库更新失败",
            ErrorCode.DATABASE_DELETE_FAILED: "数据库删除失败",

            # UI错误
            ErrorCode.UI_COMPONENT_ERROR: "界面组件出现错误",
            ErrorCode.UI_UPDATE_FAILED: "界面更新失败",
            ErrorCode.UI_EVENT_HANDLER_ERROR: "界面事件处理出错",
        }
    
    def _init_error_solutions(self) -> Dict[ErrorCode, List[str]]:
        """初始化错误解决建议"""
        return {
            # 设备通信错误解决方案
            ErrorCode.DEVICE_NOT_CONNECTED: [
                "1. 检查设备电源是否开启",
                "2. 确认USB或串口连接线是否正常连接",
                "3. 检查设备驱动程序是否正确安装",
                "4. 尝试重新连接设备"
            ],
            ErrorCode.DEVICE_CONNECTION_FAILED: [
                "1. 检查设备是否正常工作",
                "2. 确认连接端口设置是否正确",
                "3. 尝试使用不同的USB端口",
                "4. 重启设备和软件"
            ],
            ErrorCode.DEVICE_COMMUNICATION_ERROR: [
                "1. 检查连接线是否有损坏",
                "2. 确认设备通信参数设置正确",
                "3. 尝试降低通信速率",
                "4. 联系技术支持"
            ],
            
            # 通道错误解决方案
            ErrorCode.CHANNEL_BATTERY_ERROR: [
                "1. 检查电池是否正确安装",
                "2. 确认电池电压是否在正常范围内",
                "3. 清洁电池接触点",
                "4. 更换电池重新测试"
            ],
            ErrorCode.CHANNEL_HARDWARE_ERROR: [
                "1. 检查通道连接是否牢固",
                "2. 确认测试夹具工作正常",
                "3. 重启设备",
                "4. 联系技术支持进行硬件检查"
            ],
            
            # 测试流程错误解决方案
            ErrorCode.TEST_CONFIGURATION_ERROR: [
                "1. 检查测试参数设置是否正确",
                "2. 确认频率范围设置合理",
                "3. 验证通道选择是否正确",
                "4. 重置为默认配置后重试"
            ],
            ErrorCode.TEST_EXECUTION_FAILED: [
                "1. 检查所有设备连接是否正常",
                "2. 确认电池安装正确",
                "3. 重新启动测试",
                "4. 查看详细错误日志"
            ],
            
            # 数据错误解决方案
            ErrorCode.DATA_SAVE_FAILED: [
                "1. 检查磁盘空间是否充足",
                "2. 确认文件权限设置正确",
                "3. 尝试保存到不同位置",
                "4. 重启软件后重试"
            ],
            
            # 配置错误解决方案
            ErrorCode.CONFIG_NOT_FOUND: [
                "1. 检查配置文件是否存在",
                "2. 尝试重新生成默认配置",
                "3. 从备份恢复配置文件",
                "4. 重新安装软件"
            ],
            
            # 数据库错误解决方案
            ErrorCode.DATABASE_CONNECTION_FAILED: [
                "1. 检查数据库服务是否运行",
                "2. 确认数据库连接参数正确",
                "3. 检查网络连接状态",
                "4. 重启数据库服务"
            ]
        }
    
    def _init_severity_mapping(self) -> Dict[ErrorCode, ErrorSeverityLevel]:
        """初始化错误严重程度映射"""
        return {
            # 信息级别
            ErrorCode.TEST_NOT_STARTED: ErrorSeverityLevel.INFO,
            
            # 警告级别
            ErrorCode.TIMEOUT_ERROR: ErrorSeverityLevel.WARNING,
            ErrorCode.DEVICE_RESPONSE_TIMEOUT: ErrorSeverityLevel.WARNING,
            ErrorCode.TEST_CHANNEL_ERROR: ErrorSeverityLevel.WARNING,
            ErrorCode.CHANNEL_BALANCING_ERROR: ErrorSeverityLevel.WARNING,
            
            # 错误级别
            ErrorCode.INVALID_PARAMETER: ErrorSeverityLevel.ERROR,
            ErrorCode.OPERATION_FAILED: ErrorSeverityLevel.ERROR,
            ErrorCode.DEVICE_COMMUNICATION_ERROR: ErrorSeverityLevel.ERROR,
            ErrorCode.TEST_CONFIGURATION_ERROR: ErrorSeverityLevel.ERROR,
            ErrorCode.TEST_EXECUTION_FAILED: ErrorSeverityLevel.ERROR,
            ErrorCode.DATA_VALIDATION_FAILED: ErrorSeverityLevel.ERROR,
            ErrorCode.CONFIG_VALIDATION_FAILED: ErrorSeverityLevel.ERROR,

            # 严重级别
            ErrorCode.DEVICE_NOT_CONNECTED: ErrorSeverityLevel.CRITICAL,
            ErrorCode.DEVICE_CONNECTION_FAILED: ErrorSeverityLevel.CRITICAL,
            ErrorCode.CHANNEL_HARDWARE_ERROR: ErrorSeverityLevel.CRITICAL,
            ErrorCode.DATABASE_CONNECTION_FAILED: ErrorSeverityLevel.CRITICAL,
            ErrorCode.CONFIG_NOT_FOUND: ErrorSeverityLevel.CRITICAL,
        }
    
    def get_user_friendly_message(self, error_code: ErrorCode, 
                                 technical_detail: str = "") -> Tuple[str, ErrorSeverityLevel]:
        """
        获取用户友好的错误消息
        
        Args:
            error_code: 错误码
            technical_detail: 技术详情
            
        Returns:
            (用户友好消息, 严重程度级别)
        """
        try:
            # 获取用户友好消息
            user_message = self.error_messages.get(
                error_code, 
                f"系统遇到了问题 (错误码: {error_code.name})"
            )
            
            # 如果有技术详情，适当添加
            if technical_detail and len(technical_detail) < 100:
                # 只有当技术详情不太长且有用时才添加
                if not any(tech_word in technical_detail.lower() 
                          for tech_word in ['traceback', 'exception', 'error:', 'failed:']):
                    user_message += f"：{technical_detail}"
            
            # 获取严重程度
            severity = self.error_severity_mapping.get(
                error_code, 
                ErrorSeverityLevel.ERROR
            )
            
            return user_message, severity
            
        except Exception as e:
            logger.error(f"获取用户友好消息失败: {e}")
            return "系统遇到了未知问题，请联系技术支持", ErrorSeverityLevel.ERROR
    
    def get_solution_suggestions(self, error_code: ErrorCode) -> List[str]:
        """
        获取错误解决建议
        
        Args:
            error_code: 错误码
            
        Returns:
            解决建议列表
        """
        try:
            suggestions = self.error_solutions.get(error_code, [])
            
            if not suggestions:
                # 提供通用建议
                suggestions = [
                    "1. 尝试重新执行操作",
                    "2. 检查系统状态是否正常",
                    "3. 重启软件后重试",
                    "4. 如问题持续，请联系技术支持"
                ]
            
            return suggestions
            
        except Exception as e:
            logger.error(f"获取解决建议失败: {e}")
            return ["请联系技术支持获取帮助"]
    
    def format_error_display(self, error_code: ErrorCode, 
                           technical_detail: str = "") -> Dict[str, any]:
        """
        格式化错误显示信息
        
        Args:
            error_code: 错误码
            technical_detail: 技术详情
            
        Returns:
            格式化的错误显示信息字典
        """
        try:
            user_message, severity = self.get_user_friendly_message(error_code, technical_detail)
            suggestions = self.get_solution_suggestions(error_code)
            
            return {
                'title': f"{severity.value[2]} {severity.value[0]}",
                'message': user_message,
                'severity': severity.name.lower(),
                'color': severity.value[1],
                'icon': severity.value[2],
                'suggestions': suggestions,
                'error_code': error_code.name,
                'technical_detail': technical_detail if technical_detail else None
            }
            
        except Exception as e:
            logger.error(f"格式化错误显示信息失败: {e}")
            return {
                'title': "❌ 错误",
                'message': "系统遇到了问题",
                'severity': 'error',
                'color': '#F44336',
                'icon': '❌',
                'suggestions': ["请联系技术支持"],
                'error_code': 'UNKNOWN_ERROR',
                'technical_detail': str(e)
            }


# 全局实例
_error_manager = None


def get_error_manager() -> UserFriendlyErrorManager:
    """获取全局错误管理器实例"""
    global _error_manager
    if _error_manager is None:
        _error_manager = UserFriendlyErrorManager()
    return _error_manager


def format_user_friendly_error(error_code: ErrorCode, technical_detail: str = "") -> Dict[str, any]:
    """
    快速格式化用户友好错误信息
    
    Args:
        error_code: 错误码
        technical_detail: 技术详情
        
    Returns:
        格式化的错误信息
    """
    manager = get_error_manager()
    return manager.format_error_display(error_code, technical_detail)
