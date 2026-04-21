#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通道UI更新器
负责管理通道UI元素的更新，包括标签、进度条、样式等

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import QLabel, QProgressBar, QCheckBox
from PyQt5.QtCore import QTimer

from .channel_data_manager import ChannelDataManager
from .channel_state_manager import ChannelStateManager, TestState

logger = logging.getLogger(__name__)


class ChannelUIUpdater:
    """通道UI更新器"""
    
    def __init__(self, channel_number: int, ui_elements: Dict[str, Any]):
        """
        初始化UI更新器
        
        Args:
            channel_number: 通道号（1-8）
            ui_elements: UI元素字典
        """
        self.channel_number = channel_number
        self.channel_index = channel_number - 1
        
        # UI元素引用
        self.ui_elements = ui_elements
        self.channel_label = ui_elements.get('channel_label')
        self.enable_checkbox = ui_elements.get('enable_checkbox')
        self.voltage_label = ui_elements.get('voltage_label')
        self.rs_label = ui_elements.get('rs_label')
        self.rct_label = ui_elements.get('rct_label')
        # Jack要求移除Rsei标签引用
        # self.rsei_label = ui_elements.get('rsei_label')  # 添加Rsei标签引用
        self.impedance_ratio_label = ui_elements.get('impedance_ratio_label')  # 新增阻抗比标签引用
        self.progress_bar = ui_elements.get('progress_bar')
        self.result_label = ui_elements.get('result_label')
        self.grade_label = ui_elements.get('grade_label')
        
        # 更新标志
        self._update_pending = False
        self._batch_update_timer = QTimer()
        self._batch_update_timer.setSingleShot(True)
        self._batch_update_timer.timeout.connect(self._perform_batch_update)
        
        # 缓存的更新数据
        self._pending_updates = {}

        logger.debug(f"通道{self.channel_number}UI更新器初始化完成")

    def update_channel_label(self, text: str) -> bool:
        """
        更新通道标签
        
        Args:
            text: 标签文本
            
        Returns:
            是否更新成功
        """
        try:
            if self.channel_label:
                self.channel_label.setText(text)
                logger.debug(f"通道{self.channel_number}标签更新: {text}")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新通道标签失败: {e}")
            return False
    
    def update_enable_checkbox(self, enabled: bool, checked: bool) -> bool:
        """
        更新使能复选框
        
        Args:
            enabled: 是否启用复选框
            checked: 是否选中
            
        Returns:
            是否更新成功
        """
        try:
            if self.enable_checkbox:
                self.enable_checkbox.setEnabled(enabled)
                self.enable_checkbox.setChecked(checked)
                logger.debug(f"通道{self.channel_number}使能复选框更新: enabled={enabled}, checked={checked}")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新使能复选框失败: {e}")
            return False
    
    def update_voltage_display(self, voltage: float) -> bool:
        """
        更新电压显示
        
        Args:
            voltage: 电压值(V)
            
        Returns:
            是否更新成功
        """
        try:
            if self.voltage_label:
                text = f"{voltage:.3f}V"
                self.voltage_label.setText(text)
                logger.debug(f"通道{self.channel_number}电压显示更新: {text}")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新电压显示失败: {e}")
            return False
    
    def update_impedance_display(self, rs_value: float, rct_value: float, force_update: bool = False) -> bool:
        """
        更新阻抗显示 - Jack的简化版本

        Args:
            rs_value: Rs值(mΩ)
            rct_value: Rct值(mΩ) - 总极化阻抗，包含原Rsei+Rct
            force_update: 强制更新所有值

        Returns:
            是否更新成功
        """
        try:
            success = True

            if self.rs_label:
                rs_text = f"{rs_value:.3f}"
                self.rs_label.setText(rs_text)
                logger.debug(f"通道{self.channel_number}Rs显示更新: {rs_text}")
            else:
                success = False

            if self.rct_label:
                rct_text = f"{rct_value:.3f}"
                self.rct_label.setText(rct_text)
                logger.debug(f"通道{self.channel_number}Rct显示更新: {rct_text}")
            else:
                success = False

            # Jack要求移除Rsei显示，界面只显示Rs和Rct
            # Rct现在包含总极化阻抗（原Rsei+Rct）
            # if hasattr(self, 'rsei_label') and self.rsei_label:
            # self.rsei_label.setText("--")  # 不再显示Rsei

            # 保持移除继续隐藏阻抗比更新逻辑
            # if hasattr(self, 'impedance_ratio_label') and self.impedance_ratio_label:
            # if rs_value > 0:
            # rp_value = rsei_value + rct_value
            # impedance_ratio = rp_value / rs_value
            # ratio_text = f"{impedance_ratio:.3f}"
            # self.impedance_ratio_label.setText(ratio_text)
            # logger.debug(f"通道{self.channel_number}阻抗比显示更新: {ratio_text}")
            # else:
            # self.impedance_ratio_label.setText("--")
            # logger.debug(f"通道{self.channel_number}Rs为0，阻抗比显示为--")
            # else:
            # logger.debug(f"通道{self.channel_number}阻抗比标签不存在，跳过更新")

            return success
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新阻抗显示失败: {e}")
            return False
    
    def update_progress_display(self, progress: int) -> bool:
        """
        更新进度显示

        Args:
            progress: 进度百分比(0-100)

        Returns:
            是否更新成功
        """
        try:
            if self.progress_bar:
                # 限制进度值范围
                progress = max(0, min(100, progress))
                self.progress_bar.setValue(progress)
                logger.debug(f"通道{self.channel_number}进度显示更新: {progress}%")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新进度显示失败: {e}")
            return False
    
    def update_result_display(self, text: str, object_name: Optional[str] = None) -> bool:
        """
        更新结果显示
        
        Args:
            text: 结果文本
            object_name: 样式对象名
            
        Returns:
            是否更新成功
        """
        try:
            if self.result_label:
                self.result_label.setText(text)
                if object_name:
                    self.result_label.setObjectName(object_name)
                    # 重新应用样式
                    self.result_label.setStyleSheet("")
                logger.debug(f"通道{self.channel_number}结果显示更新: {text}")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新结果显示失败: {e}")
            return False
    
    def update_grade_display(self, text: str, object_name: Optional[str] = None) -> bool:
        """
        更新档位显示

        Args:
            text: 档位文本
            object_name: 样式对象名

        Returns:
            是否更新成功
        """
        try:
            if self.grade_label:
                # 🐛 修复：添加档位更新调试日志
                logger.debug(f"🔍 [UI更新器] 通道{self.channel_number} 更新档位显示: '{text}'")
                self.grade_label.setText(text)
                if object_name:
                    self.grade_label.setObjectName(object_name)
                    # 重新应用样式
                    self.grade_label.setStyleSheet("")
                logger.debug(f"通道{self.channel_number}档位显示更新: {text}")
                return True
            return False
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新档位显示失败: {e}")
            return False
    
    def update_all_data_display(self, data_manager: ChannelDataManager) -> bool:
        """
        批量更新所有数据显示

        Args:
            data_manager: 数据管理器

        Returns:
            是否更新成功
        """
        try:
            formatted_values = data_manager.get_formatted_values()

            try:
                from debug_data_consistency_checker import data_consistency_checker

                # 捕获UI显示的数据
                ui_debug_data = {
                    'voltage': data_manager.test_data.voltage,
                    'rs_value': data_manager.test_data.rs_value,
                    'rct_value': data_manager.test_data.rct_value,
                    'rsei_value': getattr(data_manager.test_data, 'rsei_value', 0.0),
                    'algorithm_used': getattr(data_manager, 'algorithm_used', 'unknown'),
                    'unit_converted': getattr(data_manager, 'unit_converted', False)
                }
                data_consistency_checker.capture_ui_data(self.channel_number, ui_debug_data)

                logger.info(f"🖥️ UI显示调试 - 通道{self.channel_number}:")
                logger.info(f"   电压: {ui_debug_data['voltage']:.3f}V")
                logger.info(f"   Rs: {ui_debug_data['rs_value']:.3f}mΩ")
                logger.info(f"   Rct: {ui_debug_data['rct_value']:.3f}mΩ")
                logger.info(f"   算法: {ui_debug_data['algorithm_used']}")
                logger.info(f"   单位转换: {ui_debug_data['unit_converted']}")

            except ImportError:
                # 如果调试模块不可用，继续正常流程
                pass
            except Exception as debug_e:
                logger.warning(f"UI数据一致性调试失败: {debug_e}")

            success = True
            success &= self.update_voltage_display(data_manager.test_data.voltage)
            success &= self.update_impedance_display(
                data_manager.test_data.rs_value,
                data_manager.test_data.rct_value
            )
            success &= self.update_progress_display(data_manager.test_data.test_progress)

            return success
        except Exception as e:
            logger.error(f"通道{self.channel_number}批量更新数据显示失败: {e}")
            return False
    
    def update_state_display(self, state_manager: ChannelStateManager) -> bool:
        """
        更新状态显示
        
        Args:
            state_manager: 状态管理器
            
        Returns:
            是否更新成功
        """
        try:
            test_state = state_manager.test_state
            
            # 根据状态更新结果显示
            if test_state == TestState.IDLE:
                if state_manager.is_enabled:
                    self.update_result_display("等待测试", "resultWaiting")
                else:
                    self.update_result_display("未启用", "resultDisabled")
            elif test_state == TestState.TESTING:
                self.update_result_display("测试中", "resultTesting")
            elif test_state == TestState.COMPLETED:
                # 保持现有的测试结果显示
                pass
            elif test_state == TestState.FAILED:
                self.update_result_display("测试失败", "resultFailed")
            elif test_state == TestState.DISABLED:
                self.update_result_display("未启用", "resultDisabled")
            elif test_state == TestState.CHANNEL_ERROR:
                self.update_result_display("通道异常", "resultChannelError")
            elif test_state == TestState.BATTERY_ERROR:
                self.update_result_display("电池异常", "resultBatteryError")
            elif test_state == TestState.HARDWARE_ERROR:
                self.update_result_display("硬件异常", "resultHardwareError")
            elif test_state == TestState.SKIPPED:
                self.update_result_display("跳过测试", "resultSkipped")
            
            # 更新使能复选框
            self.update_enable_checkbox(True, state_manager.is_enabled)
            
            logger.debug(f"通道{self.channel_number}状态显示更新: {test_state.value}")
            return True
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新状态显示失败: {e}")
            return False
    
    def update_error_display(self, status_code: int, description: str) -> bool:
        """
        更新错误显示
        
        Args:
            status_code: 状态码
            description: 错误描述
            
        Returns:
            是否更新成功
        """
        try:
            # 根据状态码设置对应的显示
            if status_code == 0x0003:  # 电池电压低或未安装
                self.update_result_display("电池异常", "resultBatteryError")
                self.update_grade_display("电池异常", "gradeBatteryError")
            elif status_code == 0x0005:  # 硬件错误/ADC错误
                self.update_result_display("硬件异常", "resultHardwareError")
                self.update_grade_display("硬件异常", "gradeHardwareError")
            elif status_code == 0x0004:  # 设置错误
                self.update_result_display("通道异常", "resultChannelError")
                self.update_grade_display("设置异常", "gradeChannelError")
            elif status_code == 0x0002:  # 平衡功能运行中
                self.update_result_display("跳过测试", "resultSkipped")
                self.update_grade_display("平衡中", "gradeSkipped")
            else:
                self.update_result_display("状态异常", "resultChannelError")
                self.update_grade_display("状态异常", "gradeChannelError")
            
            logger.warning(f"通道{self.channel_number}错误显示更新: 0x{status_code:04X} - {description}")
            return True
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新错误显示失败: {e}")
            return False
    
    def clear_all_displays(self) -> bool:
        """
        清空所有显示

        Returns:
            是否清空成功
        """
        try:
            self.update_voltage_display(0.0)
            self.update_impedance_display(0.0, 0.0)
            self.update_progress_display(0)
            self.update_result_display("", "")
            self.update_grade_display("", "")

            logger.debug(f"通道{self.channel_number}所有显示已清空")
            return True

        except Exception as e:
            logger.error(f"通道{self.channel_number}清空显示失败: {e}")
            return False

    def schedule_batch_update(self, update_data: Dict[str, Any]) -> bool:
        """
        调度批量更新
        
        Args:
            update_data: 更新数据字典
            
        Returns:
            是否调度成功
        """
        try:
            # 合并更新数据
            self._pending_updates.update(update_data)
            
            # 启动批量更新定时器
            if not self._batch_update_timer.isActive():
                self._batch_update_timer.start(10)  # 10ms后执行批量更新
            
            return True
        except Exception as e:
            logger.error(f"通道{self.channel_number}调度批量更新失败: {e}")
            return False
    
    def _perform_batch_update(self):
        """执行批量更新"""
        try:
            if not self._pending_updates:
                return
            
            # 执行所有待更新的操作
            for update_type, update_value in self._pending_updates.items():
                if update_type == 'voltage':
                    self.update_voltage_display(update_value)
                elif update_type == 'rs_value':
                    self.update_impedance_display(update_value, self._pending_updates.get('rct_value', 0.0))
                elif update_type == 'rct_value':
                    self.update_impedance_display(self._pending_updates.get('rs_value', 0.0), update_value)
                # Jack要求移除Rsei处理
                # elif update_type == 'rsei_value':
                # self.update_impedance_display(self._pending_updates.get('rs_value', 0.0), self._pending_updates.get('rct_value', 0.0), update_value)
                elif update_type == 'progress':
                    self.update_progress_display(update_value)
                elif update_type == 'result':
                    self.update_result_display(update_value.get('text', ''), update_value.get('object_name'))
                elif update_type == 'grade':
                    self.update_grade_display(update_value.get('text', ''), update_value.get('object_name'))
            
            # 清空待更新数据
            self._pending_updates.clear()
            
            logger.debug(f"通道{self.channel_number}批量更新完成")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}执行批量更新失败: {e}")
    
    def get_ui_state(self) -> Dict[str, Any]:
        """
        获取UI状态
        
        Returns:
            UI状态字典
        """
        try:
            return {
                'channel_number': self.channel_number,
                'voltage_text': self.voltage_label.text() if self.voltage_label else "",
                'rs_text': self.rs_label.text() if self.rs_label else "",
                'rct_text': self.rct_label.text() if self.rct_label else "",
                'progress_value': self.progress_bar.value() if self.progress_bar else 0,
                'result_text': self.result_label.text() if self.result_label else "",
                'grade_text': self.grade_label.text() if self.grade_label else "",
                'is_enabled': self.enable_checkbox.isChecked() if self.enable_checkbox else False
            }
        except Exception as e:
            logger.error(f"通道{self.channel_number}获取UI状态失败: {e}")
            return {}

    # 兼容性方法 - 保持与旧版本的接口兼容
    def update_progress(self, progress: int) -> bool:
        """更新进度（兼容性方法）"""
        return self.update_progress_display(progress)

    def update_test_data(self, voltage: float, rs: float, rct: float, progress: int) -> bool:
        """更新测试数据（兼容性方法） - Jack的简化版本"""
        try:
            # 更新电压
            self.update_voltage_display(voltage)
            # 更新阻抗值 - 只有Rs和Rct
            self.update_impedance_display(rs, rct)
            # 更新进度
            self.update_progress_display(progress)
            return True
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新测试数据失败: {e}")
            return False

    def update_battery_status(self, status: str, voltage: float) -> bool:
        """更新电池状态（兼容性方法）"""
        try:
            # 更新电压显示
            self.update_voltage_display(voltage)
            # 可以根据需要添加状态显示逻辑
            return True
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新电池状态失败: {e}")
            return False

    def update_timer_display(self, elapsed_time: float) -> bool:
        """更新计时器显示（兼容性方法）"""
        try:
            # 如果有计时器标签，更新显示
            if hasattr(self, 'timer_label') and self.timer_label:
                self.timer_label.setText(f"{elapsed_time:.1f}s")
            return True
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新计时器显示失败: {e}")
            return False

    def update_frequency_display(self, frequency: float, current_index: int, total_count: int, status: str) -> bool:
        """更新频率显示（兼容性方法）"""
        try:
            # 如果有频率标签，更新显示
            if hasattr(self, 'frequency_label') and self.frequency_label:
                self.frequency_label.setText(f"{frequency:.1f}Hz ({current_index}/{total_count})")
            return True
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新频率显示失败: {e}")
            return False
