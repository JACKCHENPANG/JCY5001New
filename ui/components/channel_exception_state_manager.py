# -*- coding: utf-8 -*-
"""
通道异常状态管理器
负责单个通道的异常状态处理，包括异常类型识别、状态设置、UI更新等

Author: Jack
Date: 2025-06-27
"""

import logging
from datetime import datetime
from typing import Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ChannelExceptionStateManager(QObject):
    """通道异常状态管理器"""
    
    # 信号定义
    exception_occurred = pyqtSignal(int, str, str, float)  # 异常发生信号 (channel, type, message, voltage)
    test_completed = pyqtSignal(int, dict)  # 测试完成信号 (channel, result)
    
    def __init__(self, channel_number: int, parent=None):
        """
        初始化异常状态管理器
        
        Args:
            channel_number: 通道号
            parent: 父对象
        """
        super().__init__(parent)
        
        self.channel_number = channel_number
        
        # UI元素引用
        self.grade_label = None
        self.result_label = None
        self.voltage_label = None
        self.rs_label = None
        self.rct_label = None
        self.progress_bar = None
        
    def set_ui_elements(self, ui_elements: dict):
        """
        设置UI元素引用
        
        Args:
            ui_elements: UI元素字典
        """
        self.grade_label = ui_elements.get('grade_label')
        self.result_label = ui_elements.get('result_label')
        self.voltage_label = ui_elements.get('voltage_label')
        self.rs_label = ui_elements.get('rs_label')
        self.rct_label = ui_elements.get('rct_label')
        self.progress_bar = ui_elements.get('progress_bar')
        
    def set_exception_state(self, exception_type: str, error_message: str, voltage: float = 0.0, battery_code: str = "") -> dict:
        """
        设置异常状态显示

        Args:
            exception_type: 异常类型 ('contact_poor', 'battery_error', 'hardware_error', 'exception')
            error_message: 错误消息
            voltage: 检测到的电压值
            battery_code: 电池码

        Returns:
            异常测试结果字典
        """
        try:
            # 根据异常类型设置显示内容
            fail_items, result_text, result_style = self._get_exception_display_info(exception_type)

            # 更新UI显示
            self._update_exception_display(fail_items, result_text, result_style, voltage)

            # 构建异常测试结果数据
            test_result = self._build_exception_result_data(
                exception_type, error_message, voltage, battery_code, fail_items
            )

            # 发送异常发生信号
            self.exception_occurred.emit(self.channel_number, exception_type, error_message, voltage)

            # 发送异常完成信号
            self.test_completed.emit(self.channel_number, test_result)

            logger.warning(f"通道{self.channel_number}异常状态已设置: {exception_type} - {error_message}")

            return test_result

        except Exception as e:
            logger.error(f"通道{self.channel_number}设置异常状态失败: {e}")
            return {}

    def _get_exception_display_info(self, exception_type: str) -> tuple:
        """
        获取异常显示信息
        
        Args:
            exception_type: 异常类型
            
        Returns:
            (失败项目列表, 结果文本, 结果样式)
        """
        if exception_type == 'contact_poor':
            return ['接触不良'], "不合格-接触不良", "resultContactPoor"
        elif exception_type == 'battery_error':
            return ['电池异常'], "不合格-电池异常", "resultBatteryError"
        elif exception_type == 'hardware_error':
            return ['硬件异常'], "不合格-硬件异常", "resultHardwareError"
        else:  # 通用异常
            return ['异常'], "不合格-异常", "resultException"

    def _update_exception_display(self, fail_items: list, result_text: str, result_style: str, voltage: float):
        """更新异常状态UI显示"""
        try:
            if not self.grade_label or not self.result_label:
                logger.warning(f"通道{self.channel_number}UI元素未设置，无法更新异常显示")
                return

            # 设置档位标签显示"不合格"
            self.grade_label.setText("不合格")
            self.grade_label.setObjectName("gradeFail")

            # 设置结果显示
            self.result_label.setText(result_text)
            self.result_label.setObjectName(result_style)

            # 更新电压显示（如果有检测到电压）
            if self.voltage_label:
                if voltage > 0:
                    self.voltage_label.setText(f"{voltage:.3f}")
                else:
                    self.voltage_label.setText("0.000")

            # 清除Rs和Rct显示
            if self.rs_label:
                self.rs_label.setText("0.000mΩ")
            if self.rct_label:
                self.rct_label.setText("0.000mΩ")

            # 设置进度条为100%（异常完成）
            if self.progress_bar:
                self.progress_bar.setValue(100)

            # 重新应用样式
            self.grade_label.setStyleSheet("")
            self.result_label.setStyleSheet("")

            # 强制刷新UI组件
            self.grade_label.update()
            self.result_label.update()
            if self.voltage_label:
                self.voltage_label.update()
            if self.rs_label:
                self.rs_label.update()
            if self.rct_label:
                self.rct_label.update()
            if self.progress_bar:
                self.progress_bar.update()

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新异常状态UI显示失败: {e}")

    def _build_exception_result_data(self, exception_type: str, error_message: str, 
                                   voltage: float, battery_code: str, fail_items: list) -> dict:
        """构建异常测试结果数据"""
        try:
            test_result = {
                'is_pass': False,
                'rs_grade': '--',
                'rct_grade': '--',
                'voltage': voltage,
                'rs': 0.0,  # 保持原有字段名
                'rct': 0.0,  # 保持原有字段名
                'rs_value': 0.0,  # 兼容打印模块的字段名
                'rct_value': 0.0,  # 兼容打印模块的字段名
                'battery_code': battery_code,
                'channel_number': self.channel_number,
                'test_time': datetime.now().isoformat(),
                'exception_type': exception_type,
                'error_message': error_message,
                'fail_items': fail_items,
                'fail_reason': f"不合格-{fail_items[0]}" if fail_items else "不合格-异常",
                # 离群率相关数据
                'outlier_result': '--',
                'outlier_rate': '--',  # 兼容字段名
                'frequency_deviations': {},
                'max_deviation_percent': 0.0,
                'baseline_filename': '',
                'baseline_id': None
            }

            return test_result

        except Exception as e:
            logger.error(f"通道{self.channel_number}构建异常测试结果数据失败: {e}")
            return {}

    def set_contact_poor_exception(self, voltage: float = 0.0, battery_code: str = "") -> dict:
        """设置接触不良异常"""
        return self.set_exception_state('contact_poor', '电池接触不良，请检查电池连接', voltage, battery_code)

    def set_battery_error_exception(self, voltage: float = 0.0, battery_code: str = "") -> dict:
        """设置电池异常"""
        return self.set_exception_state('battery_error', '电池状态异常，请检查电池', voltage, battery_code)

    def set_hardware_error_exception(self, voltage: float = 0.0, battery_code: str = "") -> dict:
        """设置硬件异常"""
        return self.set_exception_state('hardware_error', '硬件设备异常，请检查设备连接', voltage, battery_code)

    def set_general_exception(self, error_message: str, voltage: float = 0.0, battery_code: str = "") -> dict:
        """设置通用异常"""
        return self.set_exception_state('exception', error_message, voltage, battery_code)

    def clear_exception_state(self):
        """清除异常状态"""
        try:
            if self.grade_label:
                self.grade_label.setText("--")
                self.grade_label.setObjectName("")
            if self.result_label:
                self.result_label.setText("--")
                self.result_label.setObjectName("")
            if self.voltage_label:
                self.voltage_label.setText("0.000")
            if self.rs_label:
                self.rs_label.setText("0.000mΩ")
            if self.rct_label:
                self.rct_label.setText("0.000mΩ")
            if self.progress_bar:
                self.progress_bar.setValue(0)

            logger.debug(f"通道{self.channel_number}异常状态已清除")

        except Exception as e:
            logger.error(f"通道{self.channel_number}清除异常状态失败: {e}")

    def is_exception_type_critical(self, exception_type: str) -> bool:
        """
        判断异常类型是否为严重异常
        
        Args:
            exception_type: 异常类型
            
        Returns:
            是否为严重异常
        """
        critical_types = ['hardware_error', 'contact_poor']
        return exception_type in critical_types

    def get_exception_recovery_suggestion(self, exception_type: str) -> str:
        """
        获取异常恢复建议
        
        Args:
            exception_type: 异常类型
            
        Returns:
            恢复建议文本
        """
        suggestions = {
            'contact_poor': '请检查电池连接是否良好，清洁接触点后重试',
            'battery_error': '请更换电池或检查电池状态',
            'hardware_error': '请检查设备连接，重启设备后重试',
            'exception': '请检查系统状态，必要时重启软件'
        }
        
        return suggestions.get(exception_type, '请联系技术支持')
