# -*- coding: utf-8 -*-
"""
8通道容器组件
管理8个通道的显示和数据同步

Author: Jack
Date: 2025-01-27
"""

from PyQt5.QtWidgets import (
    QWidget, QGridLayout
)
from PyQt5.QtCore import pyqtSignal
from typing import Optional
import logging

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager
from ui.components.channel_display_widget import ChannelDisplayWidget

# 常量定义
CHANNEL_COUNT = 8  # 通道总数
GRID_ROWS = 2      # 网格行数
GRID_COLS = 4      # 网格列数
LAYOUT_MARGIN = 3  # 1920*1080深度优化减小布局边距
LAYOUT_SPACING = 3 # 1920*1080深度优化减小布局间距


class ChannelsContainerWidget(QWidget):
    """8通道容器组件"""

    # 信号定义
    channel_test_completed = pyqtSignal(int, dict)  # 通道测试完成信号
    channel_battery_code_changed = pyqtSignal(int, str)  # 通道电池码变更信号
    all_channels_ready = pyqtSignal()  # 所有通道准备就绪信号

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        初始化8通道容器

        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.channels = []  # 通道组件列表

        # 初始化界面
        self._init_ui()
        self._connect_signals()

        logger.debug("8通道容器组件初始化完成")

    def _is_valid_channel(self, channel_number: int) -> bool:
        """
        验证通道号是否有效

        Args:
            channel_number: 通道号

        Returns:
            是否有效
        """
        return 1 <= channel_number <= len(self.channels)

    def _get_channel_widget(self, channel_number: int):
        """
        获取通道组件

        Args:
            channel_number: 通道号

        Returns:
            通道组件或None
        """
        if self._is_valid_channel(channel_number):
            return self.channels[channel_number - 1]
        return None

    def _init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN)
        main_layout.setSpacing(LAYOUT_SPACING)

        # 创建通道组件，采用2行4列布局
        for i in range(CHANNEL_COUNT):
            channel_number = i + 1
            channel = ChannelDisplayWidget(channel_number, self.config_manager)
            self.channels.append(channel)

            # 计算网格位置
            row = i // GRID_COLS
            col = i % GRID_COLS

            main_layout.addWidget(channel, row, col)

        # 设置行列拉伸
        for row in range(GRID_ROWS):
            main_layout.setRowStretch(row, 1)
        for col in range(GRID_COLS):
            main_layout.setColumnStretch(col, 1)

    def _connect_signals(self):
        """连接信号"""
        for channel in self.channels:
            # 连接测试完成信号
            channel.test_completed.connect(self._on_channel_test_completed)

            # 连接电池码变更信号
            channel.battery_code_changed.connect(self._on_channel_battery_code_changed)

            # 连接统计更新信号
            if hasattr(channel, 'statistics_update_requested'):
                channel.statistics_update_requested.connect(self._on_channel_statistics_update_requested)

            # 连接判断结果准备信号
            if hasattr(channel, 'judgment_ready'):
                channel.judgment_ready.connect(self._on_channel_judgment_ready)

    def _on_channel_test_completed(self, channel_number: int, result: dict):
        """通道测试完成处理"""
        logger.info(f"🎯 通道容器收到通道{channel_number}测试完成信号")
        self.channel_test_completed.emit(channel_number, result)

        # 检查是否所有通道都完成测试
        logger.debug(f"🎯 通道{channel_number}测试完成，开始检查所有通道状态")
        self._check_all_channels_status()

    def _on_channel_battery_code_changed(self, channel_number: int, code: str):
        """通道电池码变更处理"""
        logger.debug(f"通道{channel_number}电池码变更: {code}")
        self.channel_battery_code_changed.emit(channel_number, code)

    def _on_channel_statistics_update_requested(self, is_pass: bool, rs_grade: int, rct_grade: int):
        """通道统计更新请求处理"""
        try:
            # 获取发送信号的通道
            sender_channel = self.sender()
            channel_number = getattr(sender_channel, 'channel_number', 0)


            # 直接访问统计组件进行更新
            try:
                # 通过主窗口获取统计组件
                main_window = self.window()
                if hasattr(main_window, 'ui_component_manager') and main_window.ui_component_manager:
                    statistics = main_window.ui_component_manager.get_component('statistics')
                    if statistics and hasattr(statistics, 'add_test_result'):
                        statistics.add_test_result(is_pass, rs_grade, rct_grade)
                    else:
                        logger.warning(f"📊 [容器统计] 通道{channel_number} 统计组件未找到或无add_test_result方法")
                else:
                    logger.warning(f"📊 [容器统计] 通道{channel_number} 主窗口或UI管理器未找到")
            except Exception as e:
                logger.error(f"📊 [容器统计] 通道{channel_number} 统计更新失败: {e}")

        except Exception as e:
            logger.error(f"处理通道统计更新请求失败: {e}")

    def _on_channel_judgment_ready(self, channel_number: int, is_pass: bool, rs_grade: int, rct_grade: int, fail_items: list):
        """
        通道判断结果准备处理 - 实现批量显示控制

        Args:
            channel_number: 通道号
            is_pass: 是否合格
            rs_grade: Rs档位
            rct_grade: Rct档位
            fail_items: 失败项目列表
        """
        try:
            logger.info(f"🎯 [批量显示] 通道{channel_number}判断结果准备: {'合格' if is_pass else '不合格'}, Rs档位={rs_grade}, Rct档位={rct_grade}")
            pass

            # 优化初始化批量显示管理器（如果不存在），但缩短延迟时间
            if not hasattr(self, '_batch_display_manager'):
                import time
                self._batch_display_manager = {
                    'pending_results': {},  # 待显示的结果
                    'timer': None,  # 批量显示定时器
                    'batch_delay': 300  # 批量显示延迟（毫秒）- 缩短到300ms
                }

            # 保存通道的判断结果
            self._batch_display_manager['pending_results'][channel_number] = {
                'is_pass': is_pass,
                'rs_grade': rs_grade,
                'rct_grade': rct_grade,
                'fail_items': fail_items,
                'timestamp': time.time()
            }

            # 启动或重置批量显示定时器
            self._start_batch_display_timer()

            logger.debug(f"🎯 [批量显示] 通道{channel_number}结果已收集，当前待显示通道数: {len(self._batch_display_manager['pending_results'])}")

        except Exception as e:
            logger.error(f"处理通道{channel_number}判断结果准备失败: {e}")
            # 如果批量显示失败，立即显示该通道结果
            try:
                channel_widget = self.get_channel_widget(channel_number)
                if channel_widget and hasattr(channel_widget, 'trigger_result_display'):
                    channel_widget.trigger_result_display(is_pass, rs_grade, rct_grade, fail_items)
            except Exception as fallback_error:
                logger.error(f"通道{channel_number}备用显示也失败: {fallback_error}")

    def _start_batch_display_timer(self):
        """
        启动批量显示定时器
        """
        try:
            # 如果定时器已存在且活跃，重置它
            if self._batch_display_manager['timer'] and self._batch_display_manager['timer'].isActive():
                self._batch_display_manager['timer'].stop()

            # 创建新的定时器
            from PyQt5.QtCore import QTimer
            self._batch_display_manager['timer'] = QTimer()
            self._batch_display_manager['timer'].setSingleShot(True)
            self._batch_display_manager['timer'].timeout.connect(self._execute_batch_display)

            # 启动定时器
            self._batch_display_manager['timer'].start(self._batch_display_manager['batch_delay'])

            logger.debug(f"🎯 [批量显示] 批量显示定时器已启动，{self._batch_display_manager['batch_delay']}ms后执行")

        except Exception as e:
            logger.error(f"启动批量显示定时器失败: {e}")

    def _execute_batch_display(self):
        """
        执行批量显示
        """
        try:
            if not hasattr(self, '_batch_display_manager') or not self._batch_display_manager['pending_results']:
                logger.warning("🎯 [批量显示] 没有待显示的结果")
                return

            pending_results = self._batch_display_manager['pending_results']
            logger.info(f"🎯 [批量显示] 开始批量显示 {len(pending_results)} 个通道的结果")

            # 批量触发所有通道的结果显示
            for channel_number, result_data in pending_results.items():
                try:
                    channel_widget = self.get_channel_widget(channel_number)
                    if channel_widget and hasattr(channel_widget, 'trigger_result_display'):
                        channel_widget.trigger_result_display(
                            result_data['is_pass'],
                            result_data['rs_grade'],
                            result_data['rct_grade'],
                            result_data['fail_items']
                        )
                        logger.debug(f"🎯 [批量显示] 通道{channel_number}结果显示已触发")
                    else:
                        logger.warning(f"🎯 [批量显示] 通道{channel_number}组件未找到或不支持结果显示")
                except Exception as e:
                    logger.error(f"🎯 [批量显示] 通道{channel_number}结果显示失败: {e}")

            # 清理待显示结果
            self._batch_display_manager['pending_results'].clear()
            logger.info(f"🎯 [批量显示] 批量显示完成，结果已清理")

        except Exception as e:
            logger.error(f"执行批量显示失败: {e}")

    def update_all_outlier_detection_status(self, enabled: bool):
        """
        🔧 已移除：更新所有通道的离群检测状态（功能已完全移除）
        """
        # 离群率功能已完全移除，不执行任何操作
        logger.info(f"离群检测功能已移除，忽略状态更新请求: {'启用' if enabled else '禁用'}")
        pass

    def update_channel_outlier_rate_result(self, channel_number: int, result: str, baseline_filename: str = "", frequency_deviations: Optional[dict] = None, is_final: bool = False):
        """
        🔧 已移除：更新指定通道的离群率结果（功能已完全移除）
        """
        # 离群率功能已完全移除，不执行任何操作
        logger.debug(f"离群检测功能已移除，忽略通道{channel_number}离群率结果更新: {result}")
        pass

    def _check_all_channels_status(self):
        """检查所有通道状态"""
        try:
            all_ready = True
            testing_channels = []
            channel_status_details = []

            for i, channel in enumerate(self.channels):
                channel_num = i + 1
                is_testing = channel.is_testing()

                # 获取详细状态信息
                test_start_time = getattr(channel, 'test_start_time', None)
                test_end_time = getattr(channel, 'test_end_time', None)

                channel_status_details.append(f"通道{channel_num}: is_testing={is_testing}, start_time={test_start_time}, end_time={test_end_time}")

                if is_testing:
                    all_ready = False
                    testing_channels.append(channel_num)

            logger.info(f"🎯 检查所有通道状态:")
            for detail in channel_status_details:
                logger.info(f"  {detail}")

            if all_ready:
                logger.info("🎯 所有通道已就绪，发送all_channels_ready信号")
                self.all_channels_ready.emit()
            else:
                logger.info(f"还有{len(testing_channels)}个通道在测试中: {testing_channels}")

        except Exception as e:
            logger.error(f"检查所有通道状态失败: {e}")

    def start_all_tests(self, battery_codes: Optional[list] = None):
        """
        开始所有通道测试

        Args:
            battery_codes: 电池码列表，如果为None则使用当前输入的电池码
        """
        try:
            for i, channel in enumerate(self.channels):
                battery_code = ""
                if battery_codes and i < len(battery_codes):
                    battery_code = battery_codes[i]

                channel.start_test(battery_code)

            logger.info("所有通道开始测试")

        except Exception as e:
            logger.error(f"开始所有通道测试失败: {e}")

    def stop_all_tests(self):
        """停止所有通道测试"""
        try:
            for channel in self.channels:
                channel.stop_test()

            logger.info("所有通道停止测试")

        except Exception as e:
            logger.error(f"停止所有通道测试失败: {e}")

    def reset_all_channels(self):
        """重置所有通道"""
        try:
            for channel in self.channels:
                channel.reset()

            logger.info("所有通道已重置")

        except Exception as e:
            logger.error(f"重置所有通道失败: {e}")

    def update_channel_data(self, channel_number: int, voltage: float, rs: float, rct: float, progress: int):
        """
        更新指定通道的测试数据 - Jack的简化版本

        Args:
            channel_number: 通道号 (1-8)
            voltage: 电压值
            rs: Rs值
            rct: Rct值 - 总极化阻抗，包含原Rsei+Rct
            progress: 测试进度
        """
        try:
            logger.debug(f"容器通道{channel_number}数据更新: V={voltage:.3f}, Rs={rs:.3f}, Rct={rct:.3f}, 进度={progress}%")

            channel_widget = self._get_channel_widget(channel_number)
            if channel_widget:
                channel_widget.update_test_data(voltage, rs, rct, progress)
            else:
                logger.warning(f"无效的通道号: {channel_number}")

        except Exception as e:
            logger.error(f"容器更新通道{channel_number}数据失败: {e}")

    def set_channel_result(self, channel_number: int, result: str, is_pass: bool = True):
        """
        设置指定通道的测试结果

        Args:
            channel_number: 通道号 (1-8)
            result: 测试结果文本
            is_pass: 是否合格
        """
        try:
            channel_widget = self._get_channel_widget(channel_number)
            if channel_widget:
                channel_widget.set_test_result(result, is_pass)
            else:
                logger.warning(f"无效的通道号: {channel_number}")

        except Exception as e:
            logger.error(f"设置通道{channel_number}结果失败: {e}")

    def get_channel_results(self) -> dict:
        """
        获取所有通道的测试结果

        Returns:
            通道结果字典 {channel_number: result}
        """
        results = {}
        try:
            for i, channel in enumerate(self.channels):
                channel_number = i + 1
                result = channel.get_test_result()
                if result:
                    results[channel_number] = result

        except Exception as e:
            logger.error(f"获取通道结果失败: {e}")

        return results

    def get_testing_channels(self) -> list:
        """
        获取正在测试的通道列表

        Returns:
            正在测试的通道号列表
        """
        testing_channels = []
        try:
            for i, channel in enumerate(self.channels):
                if channel.is_testing():
                    testing_channels.append(i + 1)

        except Exception as e:
            logger.error(f"获取测试中通道失败: {e}")

        return testing_channels

    def get_channel_battery_codes(self) -> dict:
        """
        获取所有通道的电池码

        Returns:
            通道电池码字典 {channel_number: battery_code}
        """
        battery_codes = {}
        try:
            for i, channel in enumerate(self.channels):
                channel_number = i + 1
                battery_codes[channel_number] = channel.battery_code

        except Exception as e:
            logger.error(f"获取通道电池码失败: {e}")

        return battery_codes

    def set_channel_battery_code(self, channel_number: int, battery_code: str):
        """
        设置指定通道的电池码

        Args:
            channel_number: 通道号 (1-8)
            battery_code: 电池码
        """
        try:
            channel_widget = self._get_channel_widget(channel_number)
            if channel_widget and hasattr(channel_widget, 'battery_code_edit'):
                channel_widget.battery_code_edit.setText(battery_code)
            else:
                logger.warning(f"无效的通道号或通道组件: {channel_number}")

        except Exception as e:
            logger.error(f"设置通道{channel_number}电池码失败: {e}")

    def get_channel_count(self) -> int:
        """
        获取通道数量

        Returns:
            通道数量
        """
        return len(self.channels)

    def update_frequency_info_for_channel(self, channel_num: int, frequency: float, current_index: int, total_count: int, status: str = "waiting"):
        """
        更新指定通道的频点信息（线程安全版本）

        Args:
            channel_num: 通道号 (1-8)
            frequency: 当前测试频点 (Hz)
            current_index: 当前频点索引 (从1开始)
            total_count: 总频点数量
            status: 频点测试状态 ("waiting", "testing", "completed")
        """
        try:
            if self._is_valid_channel(channel_num):
                self._safe_update_channel_frequency_ui(channel_num, frequency, current_index, total_count, status)
                logger.debug(f"计划更新通道{channel_num}频点信息: {frequency}Hz ({current_index}/{total_count}) {status}")
            else:
                logger.warning(f"无效的通道号: {channel_num}")

        except Exception as e:
            logger.error(f"更新通道{channel_num}频点信息失败: {e}")

    def force_update_frequency_info_for_channel(self, channel_num: int, frequency: float, current_index: int, total_count: int, status: str = "waiting"):
        """
        强制更新指定通道的频点信息（绕过状态保持逻辑）

        Args:
            channel_num: 通道号 (1-8)
            frequency: 当前测试频点 (Hz)
            current_index: 当前频点索引 (从1开始)
            total_count: 总频点数量
            status: 频点测试状态 ("waiting", "testing", "completed")
        """
        try:
            if self._is_valid_channel(channel_num):
                channel = self.channels[channel_num - 1]
                if hasattr(channel, 'force_update_frequency_info'):
                    channel.force_update_frequency_info(frequency, current_index, total_count, status)
                    logger.debug(f"强制更新通道{channel_num}频点信息: {frequency}Hz ({current_index}/{total_count}) {status}")
                else:
                    # 如果没有强制更新方法，使用普通更新
                    channel.update_frequency_info(frequency, current_index, total_count, status)
            else:
                logger.warning(f"无效的通道号: {channel_num}")

        except Exception as e:
            logger.error(f"强制更新通道{channel_num}频点信息失败: {e}")

    def _safe_update_channel_frequency_ui(self, channel_num: int, frequency: float, current_index: int, total_count: int, status: str):
        """
        安全的单个通道频点UI更新方法（在主线程中执行）
        """
        try:
            # 闪退修复: 检查通道是否有效
            if not hasattr(self, 'channels') or not self.channels or channel_num < 1 or channel_num > len(self.channels):
                logger.debug(f"通道{channel_num}无效，跳过频点更新")
                return

            channel = self.channels[channel_num - 1]
            if hasattr(channel, 'update_frequency_info'):
                channel.update_frequency_info(frequency, current_index, total_count, status)
                logger.debug(f"安全更新通道{channel_num}频点UI: {frequency}Hz ({current_index}/{total_count}) {status}")

        except Exception as e:
            logger.debug(f"安全通道{channel_num}频点UI更新失败: {e}")
            # 闪退修复: 不抛出异常，确保程序稳定

    def update_frequency_info_for_all(self, frequency: float, current_index: int, total_count: int, status: str = "waiting"):
        """
        更新所有通道的频点信息（线程安全版本）

        Args:
            frequency: 当前测试频点 (Hz)
            current_index: 当前频点索引 (从1开始)
            total_count: 总频点数量
            status: 频点测试状态 ("waiting", "testing", "completed")
        """
        try:
            # 错频模式保护：如果有通道正在使用错频模式，不执行统一更新
            if hasattr(self, '_staggered_channel_frequencies') and self._staggered_channel_frequencies:
                return

            # 闪退修复: 防递归保护机制
            if hasattr(self, '_updating_all_frequency') and self._updating_all_frequency:
                logger.debug("所有通道频点更新已在进行中，跳过")
                return

            # 闪退修复: 设置批量更新标志
            self._updating_all_frequency = True

            try:
                # 闪退修复: 直接在当前线程中安全更新UI（移除QTimer避免线程问题）
                self._safe_update_all_frequency_ui(frequency, current_index, total_count, status)

                logger.debug(f"计划更新所有通道频点信息: {frequency}Hz ({current_index}/{total_count}) {status}")

            finally:
                # 闪退修复: 清除批量更新标志
                self._updating_all_frequency = False

        except Exception as e:
            logger.error(f"更新所有通道频点信息失败: {e}")
            # 确保清除标志
            if hasattr(self, '_updating_all_frequency'):
                self._updating_all_frequency = False

    def _safe_update_all_frequency_ui(self, frequency: float, current_index: int, total_count: int, status: str):
        """
        安全的所有通道频点UI更新方法（在主线程中执行）
        """
        try:
            # 闪退修复: 检查组件是否仍然有效
            if not hasattr(self, 'channels') or not self.channels:
                logger.debug("通道容器无效或无通道，跳过频点更新")
                return

            # 错频模式保护检查是否有通道处于错频模式
            if hasattr(self, '_staggered_channel_frequencies') and self._staggered_channel_frequencies:
                protected_channels = list(self._staggered_channel_frequencies.keys())

                # 只更新非错频模式的通道
                for i, channel in enumerate(self.channels):
                    channel_num = i + 1
                    if channel_num not in protected_channels:
                        try:
                            if hasattr(channel, 'update_frequency_info'):
                                channel.update_frequency_info(frequency, current_index, total_count, status)
                        except Exception as e:
                            logger.debug(f"通道{channel_num}频点更新失败: {e}")

                return

            # 闪退修复: 逐个安全更新通道，避免批量操作导致的问题
            for i, channel in enumerate(self.channels):
                try:
                    # 频点显示功能已移除，跳过频点更新
                    pass
                except Exception as e:
                    logger.debug(f"通道{i+1}频点更新失败: {e}")
                    # 继续更新其他通道，不中断整个流程

            logger.debug(f"安全更新所有通道频点UI: {frequency}Hz ({current_index}/{total_count}) {status}")

        except Exception as e:
            logger.debug(f"安全所有通道频点UI更新失败: {e}")
            # 闪退修复: 不抛出异常，确保程序稳定

    def clear_frequency_info_for_all(self):
        """清空所有通道的频点信息（频点显示功能已移除）"""
        try:
            # 频点显示功能已移除，此方法保留为空以保持兼容性
            logger.debug("频点显示功能已移除，跳过清空频点信息")

        except Exception as e:
            logger.error(f"清空所有通道频点信息失败: {e}")

    def set_frequency_completed_for_channel(self, channel_num: int):
        """
        设置指定通道的频点测试为完成状态

        Args:
            channel_num: 通道号 (1-8)
        """
        try:
            if 1 <= channel_num <= 8:
                channel = self.channels[channel_num - 1]
                # 保持当前频点信息，只更新状态为完成
                channel.update_frequency_info(
                    channel.current_frequency,
                    channel.frequency_index,
                    channel.total_frequencies,
                    "completed"
                )
                logger.debug(f"通道{channel_num}频点测试完成")
            else:
                logger.warning(f"无效的通道号: {channel_num}")

        except Exception as e:
            logger.error(f"设置通道{channel_num}频点完成状态失败: {e}")

    def update_channel_progress(self, channel_number: int, progress_data: dict):
        """
        更新指定通道的测试进度

        Args:
            channel_number: 通道号 (1-8)
            progress_data: 进度数据字典
        """
        try:
            frequency = progress_data.get('frequency', 0.0)
            mode = progress_data.get('mode', 'unknown')
            state = progress_data.get('state', 'idle')
            progress = progress_data.get('progress', 0)


            if mode == 'staggered':
                pass
            elif mode == 'simultaneous':
                pass
            elif mode == 'unknown' and frequency > 0:
                pass

            if 1 <= channel_number <= len(self.channels):
                channel_widget = self.channels[channel_number - 1]

                # 从进度数据中提取信息
                progress = progress_data.get('progress', 0)
                state = progress_data.get('state', 'idle')
                voltage = progress_data.get('voltage', 0.0)
                # 修复优先从result_data中获取Rs/Rct/Rsei值，确保数据完整性
                result_data = progress_data.get('result_data', {})
                rs = result_data.get('rs_value', progress_data.get('rs_value', progress_data.get('rs', 0.0)))
                rct = result_data.get('rct_value', progress_data.get('rct_value', progress_data.get('rct', 0.0)))
                raw_rsei = result_data.get('rsei_value', progress_data.get('rsei_value', progress_data.get('rsei', 0.0)))

                # 只有在检测到有效SEI特征时才传递Rsei值
                rsei = raw_rsei if raw_rsei > 0.1 else 0.0
                frequency = progress_data.get('frequency', 0.0)
                frequency_index = progress_data.get('frequency_index', 0)
                completed_frequency_count = progress_data.get(
                    'completed_frequency_count',
                    progress_data.get('completed_frequencies', frequency_index)
                )
                total_frequencies = progress_data.get('total_frequencies', 0)

                if state == 'completed':
                    pass

                # 更新通道状态
                if state == 'testing' or state == 'measuring':
                    pass
                    if hasattr(channel_widget, 'set_testing_state'):
                        channel_widget.set_testing_state(True)

                    # 检查是否为子进度（测量过程中的进度）
                    is_sub_progress = progress_data.get('sub_progress', False)

                    # 更新进度条和数据
                    if hasattr(channel_widget, 'update_test_data'):
                        pass
                        if not is_sub_progress:
                            pass
                            # 正常进度更新，包括进度条 - Jack的简化版本
                            channel_widget.update_test_data(voltage, rs, rct, progress)
                        else:
                            # 子进度更新：只更新电压，不更新进度条
                            if voltage > 0 and hasattr(channel_widget, 'voltage_label'):
                                channel_widget.voltage_label.setText(f"{voltage:.3f}")
                                logger.debug(f"通道{channel_number}电压更新: {voltage:.3f}V")


                    # 更新频率信息 - 修复频点索引重复加1的问题
                    if frequency > 0 and hasattr(channel_widget, 'update_frequency_info'):
                        pass

                        # 检查是否为错频模式
                        mode = progress_data.get('mode', 'unknown')

                        if mode == 'staggered':
                            pass
                            # 错频模式：记录通道的专用频率，防止被统一更新覆盖
                            if not hasattr(self, '_staggered_channel_frequencies'):
                                self._staggered_channel_frequencies = {}

                            self._staggered_channel_frequencies[channel_number] = frequency

                        # 修复调用频率更新
                        channel_widget.update_frequency_info(
                            frequency, frequency_index, total_frequencies, state, completed_frequency_count
                        )
                    else:
                        pass

                elif state == 'reset':
                    pass
                    # 修复处理测试重置状态，清空频点显示
                    logger.debug(f"通道{channel_number}收到重置状态，清空频点信息")

                    # 清空频点信息
                    if hasattr(channel_widget, 'clear_frequency_info'):
                        channel_widget.clear_frequency_info()
                        logger.debug(f"通道{channel_number}频点信息已清空")

                    # 重置测试状态
                    if hasattr(channel_widget, 'set_testing_state'):
                        channel_widget.set_testing_state(False)

                    # 清除该通道的错频保护
                    if hasattr(self, '_staggered_channel_frequencies') and channel_number in self._staggered_channel_frequencies:
                        del self._staggered_channel_frequencies[channel_number]
                        logger.debug(f"通道{channel_number}错频保护已清除")

                elif state == 'completed':
                    pass
                    # 修复直接使用传递的Rs/Rct/Rsei值，不进行任何过滤
                    final_voltage = voltage if voltage > 0 else 0.0
                    final_rs = rs  # 直接使用传递的Rs值
                    final_rct = rct  # 直接使用传递的Rct值
                    final_rsei = rsei  # 直接使用传递的Rsei值

                    # 强制更新测试数据，确保100%进度和所有结果值都显示 - Jack的简化版本
                    if hasattr(channel_widget, 'update_test_data'):
                        channel_widget.update_test_data(final_voltage, final_rs, final_rct, 100)

                    # 修复检查是否有离群率数据需要处理
                    outlier_result = progress_data.get('outlier_result')
                    frequency_deviations = progress_data.get('frequency_deviations', {})

                    # 如果有离群率数据，确保通道卡片已经处理了离群率更新
                    if outlier_result is not None and outlier_result not in ["--", "等待"] and hasattr(channel_widget, 'update_outlier_rate_result'):
                        channel_widget.update_outlier_rate_result(outlier_result, "", frequency_deviations, True)

                    # 检查是否只由UI组件进行判断
                    ui_judgment_only = progress_data.get('ui_judgment_only', False)
                    if ui_judgment_only:
                        logger.debug(f"通道{channel_number}容器检测到ui_judgment_only标记，跳过容器层面的判断结果设置")
                        # 只设置测试状态，不设置判断结果，让UI组件自己判断
                    else:
                        # 先设置测试完成状态（包含结果显示），再设置测试状态
                        if hasattr(channel_widget, 'set_test_completed'):
                            is_pass = progress_data.get('is_pass', False)
                            rs_grade = progress_data.get('rs_grade', 1)
                            rct_grade = progress_data.get('rct_grade', 1)
                            fail_items = progress_data.get('fail_items', [])  # 获取失败项目列表

                            channel_widget.set_test_completed(is_pass, rs_grade, rct_grade, fail_items)
                            logger.debug(f"通道{channel_number}测试完成状态已设置: {'合格' if is_pass else '不合格'}")

                    # 最后设置测试状态为完成（不会覆盖结果显示）
                    if hasattr(channel_widget, 'set_testing_state'):
                        channel_widget.set_testing_state(False)

                # 新增处理异常状态
                elif state in ['exception', 'contact_poor', 'no_battery', 'error']:
                    pass
                    # 处理异常状态显示
                    exception_type = progress_data.get('exception_type', 'exception')
                    error_message = progress_data.get('error_message', '通道异常')

                    # 使用新的异常状态设置方法
                    if hasattr(channel_widget, 'set_exception_state'):
                        channel_widget.set_exception_state(exception_type, error_message, voltage)
                        logger.warning(f"通道{channel_number}异常状态已设置: {exception_type} - {error_message}")
                    else:
                        # 回退到传统方法
                        if hasattr(channel_widget, 'set_test_completed'):
                            fail_items = [self._get_exception_display_text(exception_type)]
                            channel_widget.set_test_completed(False, '--', '--', fail_items)

                        if hasattr(channel_widget, 'set_testing_state'):
                            channel_widget.set_testing_state(False)

                        logger.warning(f"通道{channel_number}异常状态已设置（回退方法）: {exception_type}")

                # 新增处理失败状态
                elif state == 'failed':
                    fail_reason = progress_data.get('fail_reason', '测试失败')
                    fail_items = progress_data.get('fail_items', ['测试失败'])

                    # 更新测试数据
                    if hasattr(channel_widget, 'update_test_data'):
                        channel_widget.update_test_data(voltage, rs, rct, 100)

                    # 设置失败状态
                    if hasattr(channel_widget, 'set_test_completed'):
                        channel_widget.set_test_completed(False, '--', '--', fail_items)
                        logger.warning(f"通道{channel_number}测试失败: {fail_reason}")

                    # 停止测试状态
                    if hasattr(channel_widget, 'set_testing_state'):
                        channel_widget.set_testing_state(False)

                logger.debug(f"通道{channel_number}进度已更新: 状态={state}, 进度={progress}%, 频率={frequency}Hz")
            else:
                logger.warning(f"无效的通道号: {channel_number}")

        except Exception as e:
            logger.error(f"更新通道{channel_number}进度失败: {e}")

    def update_channel_enable_status(self, enabled_channels: list):
        """
        更新通道使能状态

        Args:
            enabled_channels: 启用的通道列表
        """
        try:
            for channel_num in range(1, CHANNEL_COUNT + 1):
                is_enabled = channel_num in enabled_channels
                channel_widget = self._get_channel_widget(channel_num)

                if channel_widget:
                    pass
                    # 更新通道的使能状态
                    if hasattr(channel_widget, 'set_enabled'):
                        channel_widget.set_enabled(is_enabled)

                    # 更新通道的视觉状态
                    if hasattr(channel_widget, 'update_enable_status'):
                        channel_widget.update_enable_status(is_enabled)

                    # 设置通道的启用状态属性
                    if hasattr(channel_widget, 'is_enabled'):
                        channel_widget.is_enabled = is_enabled

                    logger.debug(f"通道{channel_num}使能状态更新: {'启用' if is_enabled else '禁用'}")

            logger.info(f"通道使能状态更新完成: 启用{len(enabled_channels)}个通道")

        except Exception as e:
            logger.error(f"更新通道使能状态失败: {e}")

    def update_channel_test_count(self, channel_num: int, count: int):
        """
        更新指定通道的测试计数

        Args:
            channel_num: 通道号
            count: 测试计数
        """
        try:
            channel_widget = self._get_channel_widget(channel_num)
            if channel_widget:
                pass
                # 更新测试计数
                if hasattr(channel_widget, 'test_count'):
                    channel_widget.test_count = count

                # 更新测试计数显示
                if hasattr(channel_widget, '_update_test_count_display'):
                    channel_widget._update_test_count_display()

                logger.debug(f"通道{channel_num}测试计数已更新: {count}")
            else:
                logger.warning(f"无效的通道号: {channel_num}")

        except Exception as e:
            logger.error(f"更新通道{channel_num}测试计数失败: {e}")

    def clear_all_results(self):
        """清除所有通道的测试结果"""
        try:
            for channel_widget in self.channels:
                if hasattr(channel_widget, 'clear_test_result'):
                    channel_widget.clear_test_result()

            # 清除错频模式保护
            if hasattr(self, '_staggered_channel_frequencies'):
                self._staggered_channel_frequencies.clear()

            logger.info("所有通道测试结果已清除")
        except Exception as e:
            logger.error(f"清除所有通道测试结果失败: {e}")

    def clear_staggered_mode_protection(self):
        """清除错频模式保护，允许统一频率更新"""
        try:
            if hasattr(self, '_staggered_channel_frequencies'):
                self._staggered_channel_frequencies.clear()
        except Exception as e:
            logger.error(f"清除错频模式保护失败: {e}")

    def enable_frequency_display_for_all_channels(self, enabled: bool = True):
        """
        启用或禁用所有通道的频点显示功能

        Args:
            enabled: True=显示频点信息, False=隐藏频点信息
        """
        try:
            for channel_widget in self.channels:
                if hasattr(channel_widget, 'enable_frequency_display'):
                    channel_widget.enable_frequency_display(enabled)

            logger.info(f"所有通道频点显示功能: {'启用' if enabled else '禁用'}")

        except Exception as e:
            logger.error(f"批量切换频点显示状态失败: {e}")

    def _get_exception_display_text(self, exception_type: str) -> str:
        """
        获取异常类型的显示文本

        Args:
            exception_type: 异常类型

        Returns:
            显示文本
        """
        exception_text_mapping = {
            'contact_poor': '接触不良',
            'battery_error': '电池异常',
            'hardware_error': '硬件异常',
            'setting_error': '设置异常',
            'response_timeout': '响应超时',
            'no_battery': '无电池',
            'voltage_error': '电压异常',
            'exception': '异常',
            'error': '错误'
        }

        return exception_text_mapping.get(exception_type, '异常')

    def set_channel_exception_state(self, channel_number: int, exception_type: str,
                                  error_message: str, voltage: float = 0.0):
        """
        设置指定通道的异常状态

        Args:
            channel_number: 通道号
            exception_type: 异常类型
            error_message: 错误消息
            voltage: 电压值
        """
        try:
            if 1 <= channel_number <= len(self.channels):
                channel_widget = self.channels[channel_number - 1]

                if hasattr(channel_widget, 'set_exception_state'):
                    channel_widget.set_exception_state(exception_type, error_message, voltage)
                    logger.warning(f"通道{channel_number}异常状态已设置: {exception_type} - {error_message}")
                else:
                    logger.warning(f"通道{channel_number}不支持异常状态设置方法")
            else:
                logger.warning(f"无效的通道号: {channel_number}")

        except Exception as e:
            logger.error(f"设置通道{channel_number}异常状态失败: {e}")

    def get_exception_channels_summary(self) -> dict:
        """
        获取异常通道摘要

        Returns:
            异常通道摘要字典
        """
        try:
            summary = {
                'exception_channels': [],
                'contact_poor_channels': [],
                'no_battery_channels': [],
                'total_exception_count': 0
            }

            for i, channel_widget in enumerate(self.channels):
                channel_num = i + 1

                # 检查通道是否有异常状态
                if hasattr(channel_widget, 'test_result') and channel_widget.test_result:
                    result = channel_widget.test_result
                    if not result.get('is_pass', True):
                        exception_type = result.get('exception_type', '')
                        if exception_type == 'contact_poor':
                            summary['contact_poor_channels'].append(channel_num)
                        elif exception_type == 'battery_error' or 'no_battery' in result.get('fail_items', []):
                            summary['no_battery_channels'].append(channel_num)
                        else:
                            summary['exception_channels'].append(channel_num)

                        summary['total_exception_count'] += 1

            return summary

        except Exception as e:
            logger.error(f"获取异常通道摘要失败: {e}")
            return {
                'exception_channels': [],
                'contact_poor_channels': [],
                'no_battery_channels': [],
                'total_exception_count': 0
            }

    def refresh_all_channels_from_database(self):
        """
        从数据库刷新所有通道的显示数据（使用统一档位管理器）
        """
        try:
            logger.info("🔄 [统一批量刷新] 使用统一档位管理器刷新所有通道...")

            from utils.grade_manager import get_grade_manager
            grade_manager = get_grade_manager()

            # 使用统一档位管理器批量刷新
            refreshed_count = grade_manager.refresh_all_channels()

            logger.info(f"✅ [统一批量刷新] 完成，成功刷新{refreshed_count}/8个通道")

        except Exception as e:
            logger.error(f"❌ [统一批量刷新] 失败: {e}")
            # 备用方案：逐个刷新
            self._fallback_refresh_all_channels()

    def refresh_channel_from_database(self, channel_number: int):
        """
        从数据库刷新指定通道的显示数据（使用统一档位管理器）

        Args:
            channel_number: 通道号
        """
        try:
            from utils.grade_manager import get_grade_manager
            grade_manager = get_grade_manager()

            # 使用统一档位管理器刷新指定通道
            success = grade_manager.update_channel_display(channel_number)

            if success:
                logger.info(f"✅ [统一单通道刷新] 通道{channel_number}显示已刷新")
            else:
                logger.warning(f"⚠️ [统一单通道刷新] 通道{channel_number}刷新失败")

        except Exception as e:
            logger.error(f"❌ [统一单通道刷新] 通道{channel_number}刷新失败: {e}")

    def _fallback_refresh_all_channels(self):
        """备用批量刷新方法"""
        try:
            refreshed_count = 0
            for channel in self.channels:
                try:
                    if hasattr(channel, 'refresh_display_from_database'):
                        channel.refresh_display_from_database()
                        refreshed_count += 1
                except Exception as e:
                    logger.error(f"❌ [备用刷新] 通道{channel.channel_number}刷新失败: {e}")

            logger.info(f"✅ [备用刷新] 完成，成功刷新{refreshed_count}个通道")

        except Exception as e:
            logger.error(f"❌ [备用刷新] 失败: {e}")
