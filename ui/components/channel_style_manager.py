# -*- coding: utf-8 -*-
"""
通道样式管理器
负责单通道显示组件的样式管理和主题应用

Author: Jack
Date: 2025-01-30
"""

import logging
from PyQt5.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class ChannelStyleManager:
    """通道样式管理器"""
    
    def __init__(self, channel_number: int, parent_widget: QWidget):
        """
        初始化样式管理器
        
        Args:
            channel_number: 通道号
            parent_widget: 父组件
        """
        self.channel_number = channel_number
        self.parent_widget = parent_widget
        
    def apply_default_styles(self):
        """应用默认样式"""
        try:
            style_sheet = self._get_default_stylesheet()
            self.parent_widget.setStyleSheet(style_sheet)
            logger.debug(f"通道{self.channel_number}默认样式已应用")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}应用默认样式失败: {e}")
    
    def _get_default_stylesheet(self) -> str:
        """获取默认样式表"""
        return """
            QGroupBox#channelGroup {
                font-weight: bold;
                font-size: 12pt;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 8px;
                background-color: #ffffff;
            }
            
            QGroupBox#channelGroup::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #2c3e50;
                background-color: #ffffff;
            }
            
            QLabel#countLabel {
                font-size: 11pt;
                font-weight: bold;
                color: #27ae60;
                background-color: transparent;
            }
            
            QLabel#timeLabel {
                font-size: 10pt;
                font-weight: bold;
                color: #3498db;
                background-color: transparent;
            }
            
            QLineEdit#batteryCodeEdit {
                font-size: 10pt;
                padding: 4px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #ffffff;
                selection-background-color: #3498db;
                min-width: 160px;
                max-height: 28px;
            }

            QLineEdit#batteryCodeEdit:focus {
                border: 2px solid #3498db;
            }
            
            QLabel#dataLabel {
                font-size: 11pt;
                font-weight: bold;
                color: #2c3e50;
                background-color: transparent;
                padding: 2px 4px;
                border: 1px solid #ecf0f1;
                border-radius: 3px;
                background-color: #f8f9fa;
            }
            
            QLabel#rsValue, QLabel#rctValue, QLabel#rseiValue, QLabel#impedance_ratioValue {
                font-size: 13pt;  /* 调整字体大小，既清晰又不被截取 */
                font-weight: bold;
                color: #2c3e50;
                background-color: transparent;
                padding: 3px;  /* 调整内边距 */
                border: 1px solid #ecf0f1;
                border-radius: 3px;
                background-color: #f8f9fa;
                max-height: 44px;  /* 适应字体大小 */
            }
            
            QLabel#outlierRateLabel {
                font-size: 10pt;
                font-weight: bold;
                color: #7f8c8d;
                background-color: transparent;
            }
            
            QProgressBar#testProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                text-align: center;
                font-size: 10pt;
                font-weight: bold;
                background-color: #ecf0f1;
            }
            
            QProgressBar#testProgressBar::chunk {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #3498db, stop: 1 #2980b9);
                border-radius: 3px;
            }
            
            QFrame#resultContainer {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #f8f9fa;
                padding: 2px;
            }
            
            QLabel#gradeDisplay {
                font-size: 24pt;
                font-weight: bold;
                color: #2c3e50;
                background-color: #f8f9fa;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            QLabel#resultWaiting {
                font-size: 24pt;
                font-weight: bold;
                color: #7f8c8d;
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }
            
            QLabel.passResult {
                font-size: 24pt;
                font-weight: bold;
                color: #ffffff;
                background-color: #27ae60;
                border: 1px solid #229954;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            QLabel.failResult {
                font-size: 24pt;
                font-weight: bold;
                color: #ffffff;
                background-color: #e74c3c;
                border: 1px solid #c0392b;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            QLabel.waitingResult {
                font-size: 24pt;
                font-weight: bold;
                color: #7f8c8d;
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            QLabel.testingResult {
                font-size: 24pt;
                font-weight: bold;
                color: #ffffff;
                background-color: #f39c12;
                border: 1px solid #e67e22;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            /* 测试结果状态样式 */
            QLabel#resultTesting {
                font-size: 24pt;
                font-weight: bold;
                color: #ffffff;
                background-color: #f39c12;
                border: 1px solid #e67e22;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            QLabel#resultDisabled {
                font-size: 24pt;
                font-weight: bold;
                color: #7f8c8d;
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            QLabel#resultFailed {
                font-size: 24pt;
                font-weight: bold;
                color: #ffffff;
                background-color: #e74c3c;
                border: 1px solid #c0392b;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            QLabel#resultChannelError, QLabel#resultBatteryError, QLabel#resultHardwareError {
                font-size: 24pt;
                font-weight: bold;
                color: #ffffff;
                background-color: #e74c3c;
                border: 1px solid #c0392b;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            QLabel#resultSkipped {
                font-size: 24pt;
                font-weight: bold;
                color: #7f8c8d;
                background-color: #f8f9fa;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            /* 不合格结果详细样式 */
            QLabel#resultFail, QLabel#resultFailV, QLabel#resultFailRs, QLabel#resultFailRct, QLabel#resultFailOutlier {
                font-size: 24pt;
                font-weight: bold;
                color: #ffffff;
                background-color: #e74c3c;
                border: 1px solid #c0392b;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            QLabel#resultPass {
                font-size: 24pt;
                font-weight: bold;
                color: #ffffff;
                background-color: #27ae60;
                border: 1px solid #229954;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            /* 取样测试结果样式 */
            QLabel#resultSampling {
                font-size: 24pt;
                font-weight: bold;
                color: #ffffff;
                background-color: #3498db;
                border: 1px solid #2980b9;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            /* 档位结果状态样式 */
            QLabel#gradeBatteryError, QLabel#gradeHardwareError, QLabel#gradeChannelError {
                font-size: 24pt;
                font-weight: bold;
                color: #ffffff;
                background-color: #e74c3c;
                border: 1px solid #c0392b;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            QLabel#gradeSkipped {
                font-size: 24pt;
                font-weight: bold;
                color: #7f8c8d;
                background-color: #f8f9fa;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }

            /* 取样测试档位样式 */
            QLabel#gradeSampling {
                font-size: 24pt;
                font-weight: bold;
                color: #ffffff;
                background-color: #e67e22;
                border: 1px solid #d35400;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
                qproperty-alignment: AlignCenter;
                line-height: 109px;
            }
        """
    
    def apply_enabled_style(self, enabled: bool):
        """应用启用/禁用样式"""
        try:
            if enabled:
                self._apply_enabled_style()
            else:
                self._apply_disabled_style()
                
            logger.debug(f"通道{self.channel_number}{'启用' if enabled else '禁用'}样式已应用")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}应用启用样式失败: {e}")
    
    def _apply_enabled_style(self):
        """应用启用样式"""
        enabled_style = """
            QGroupBox#channelGroup {
                border: 2px solid #3498db;
                background-color: #ffffff;
            }
            
            QGroupBox#channelGroup::title {
                color: #2c3e50;
            }
        """
        self._append_style(enabled_style)
    
    def _apply_disabled_style(self):
        """应用禁用样式"""
        disabled_style = """
            QGroupBox#channelGroup {
                border: 2px solid #bdc3c7;
                background-color: #f8f9fa;
            }
            
            QGroupBox#channelGroup::title {
                color: #7f8c8d;
            }
            
            QLabel {
                color: #7f8c8d;
            }
            
            QLineEdit {
                background-color: #ecf0f1;
                color: #7f8c8d;
            }
        """
        self._append_style(disabled_style)
    
    def apply_test_state_style(self, test_state: str):
        """应用测试状态样式"""
        try:
            if test_state == "testing":
                self._apply_testing_style()
            elif test_state == "completed":
                self._apply_completed_style()
            elif test_state == "failed":
                self._apply_failed_style()
            else:
                self._apply_idle_style()
                
            logger.debug(f"通道{self.channel_number}测试状态样式已应用: {test_state}")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}应用测试状态样式失败: {e}")
    
    def _apply_testing_style(self):
        """应用测试中样式"""
        testing_style = """
            QGroupBox#channelGroup {
                border: 2px solid #f39c12;
                background-color: #fef9e7;
            }
        """
        self._append_style(testing_style)
    
    def _apply_completed_style(self):
        """应用测试完成样式"""
        completed_style = """
            QGroupBox#channelGroup {
                border: 2px solid #27ae60;
                background-color: #eafaf1;
            }
        """
        self._append_style(completed_style)
    
    def _apply_failed_style(self):
        """应用测试失败样式"""
        failed_style = """
            QGroupBox#channelGroup {
                border: 2px solid #e74c3c;
                background-color: #fdedec;
            }
        """
        self._append_style(failed_style)
    
    def _apply_idle_style(self):
        """应用空闲样式"""
        idle_style = """
            QGroupBox#channelGroup {
                border: 2px solid #bdc3c7;
                background-color: #ffffff;
            }
        """
        self._append_style(idle_style)
    
    def apply_result_style(self, result_label, is_pass: bool):
        """应用测试结果样式"""
        try:
            if is_pass:
                result_label.setProperty("class", "passResult")
            else:
                result_label.setProperty("class", "failResult")
            
            # 强制刷新样式
            result_label.style().unpolish(result_label)
            result_label.style().polish(result_label)
            
            logger.debug(f"通道{self.channel_number}结果样式已应用: {'合格' if is_pass else '不合格'}")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}应用结果样式失败: {e}")
    
    def apply_count_color_style(self, count_label, test_count: int):
        """应用测试计数颜色样式"""
        try:
            if test_count == 0:
                color = "#7f8c8d"  # 灰色
            elif test_count < 10:
                color = "#27ae60"  # 绿色
            elif test_count < 50:
                color = "#f39c12"  # 橙色
            elif test_count < 100:
                color = "#e67e22"  # 深橙色
            else:
                color = "#e74c3c"  # 红色
            
            count_label.setStyleSheet(f"""
                font-size: 11pt;
                font-weight: bold;
                color: {color};
                background-color: transparent;
            """)
            
            logger.debug(f"通道{self.channel_number}计数颜色样式已应用: {test_count} -> {color}")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}应用计数颜色样式失败: {e}")
    
    def _append_style(self, additional_style: str):
        """追加样式到现有样式表"""
        try:
            current_style = self.parent_widget.styleSheet()
            new_style = current_style + "\n" + additional_style
            self.parent_widget.setStyleSheet(new_style)
            
        except Exception as e:
            logger.error(f"追加样式失败: {e}")
    
    def reset_styles(self):
        """重置所有样式"""
        try:
            self.apply_default_styles()
            logger.debug(f"通道{self.channel_number}样式已重置")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}重置样式失败: {e}")
