# -*- coding: utf-8 -*-
"""
分行8通道容器组件
管理8个通道的显示，分为两行显示（第一行4个通道，第二行4个通道）

Author: Jack
Date: 2025-06-03
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
LAYOUT_MARGIN = 5  # 布局边距
LAYOUT_SPACING = 5 # 布局间距


class SplitChannelsContainerWidget(QWidget):
    """分行8通道容器组件"""

    # 信号定义
    channel_test_completed = pyqtSignal(int, dict)  # 通道测试完成信号
    channel_battery_code_changed = pyqtSignal(int, str)  # 通道电池码变更信号
    all_channels_ready = pyqtSignal()  # 所有通道准备就绪信号

    def __init__(self, config_manager: ConfigManager, row1_container, row2_container, parent=None):
        """
        初始化分行8通道容器

        Args:
            config_manager: 配置管理器
            row1_container: 第一行容器
            row2_container: 第二行容器
            parent: 父窗口
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.row1_container = row1_container
        self.row2_container = row2_container
        self.channels = []  # 通道组件列表

        # 初始化界面
        self._init_ui()
        self._connect_signals()

        logger.debug("分行8通道容器组件初始化完成")

    def _is_valid_channel(self, channel_number: int) -> bool:
        """
        验证通道号是否有效

        Args:
            channel_number: 通道号

        Returns:
            是否有效
        """
        return 1 <= channel_number <= len(self.channels)

    def _init_ui(self):
        """初始化用户界面"""
        # 创建第一行布局（通道1-4）
        row1_layout = QGridLayout(self.row1_container)
        row1_layout.setContentsMargins(LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN)
        row1_layout.setSpacing(LAYOUT_SPACING)

        # 创建第二行布局（通道5-8）
        row2_layout = QGridLayout(self.row2_container)
        row2_layout.setContentsMargins(LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN)
        row2_layout.setSpacing(LAYOUT_SPACING)

        # 创建通道组件
        for i in range(CHANNEL_COUNT):
            channel_number = i + 1
            channel = ChannelDisplayWidget(channel_number, self.config_manager)
            self.channels.append(channel)

            # 计算位置
            if i < 4:  # 第一行（通道1-4）
                col = i
                row1_layout.addWidget(channel, 0, col)
                # 设置列拉伸
                row1_layout.setColumnStretch(col, 1)
            else:  # 第二行（通道5-8）
                col = i - 4
                row2_layout.addWidget(channel, 0, col)
                # 设置列拉伸
                row2_layout.setColumnStretch(col, 1)

        # 设置行拉伸
        row1_layout.setRowStretch(0, 1)
        row2_layout.setRowStretch(0, 1)

    def _connect_signals(self):
        """连接信号"""
        try:
            for channel in self.channels:
                # 连接通道信号
                channel.test_completed.connect(self._on_channel_test_completed)
                channel.battery_code_changed.connect(self._on_channel_battery_code_changed)

                # 连接统计更新信号
                if hasattr(channel, 'statistics_update_requested'):
                    channel.statistics_update_requested.connect(self._on_channel_statistics_update_requested)

                # 连接判断结果准备信号
                if hasattr(channel, 'judgment_ready'):
                    channel.judgment_ready.connect(self._on_channel_judgment_ready)

        except Exception as e:
            logger.error(f"连接通道信号失败: {e}")

    def _on_channel_test_completed(self, channel_num: int, result_data: dict):
        """通道测试完成处理"""
        try:
            logger.debug(f"通道{channel_num}测试完成")
            
            # 转发信号
            self.channel_test_completed.emit(channel_num, result_data)
            
            # 检查是否所有通道都完成测试
            self._check_all_channels_ready()
            
        except Exception as e:
            logger.error(f"处理通道{channel_num}测试完成失败: {e}")

    def _on_channel_battery_code_changed(self, channel_num: int, battery_code: str):
        """通道电池码变更处理"""
        try:
            # 通道电池码变更 - 运行时不输出日志
            pass

            # 转发信号
            self.channel_battery_code_changed.emit(channel_num, battery_code)

        except Exception as e:
            logger.error(f"处理通道{channel_num}电池码变更失败: {e}")

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
                        logger.warning(f"📊 [分行容器统计] 通道{channel_number} 统计组件未找到或无add_test_result方法")
                else:
                    logger.warning(f"📊 [分行容器统计] 通道{channel_number} 主窗口或UI管理器未找到")
            except Exception as e:
                logger.error(f"📊 [分行容器统计] 通道{channel_number} 统计更新失败: {e}")

        except Exception as e:
            logger.error(f"处理通道统计更新请求失败: {e}")

    def _on_channel_judgment_ready(self, channel_number: int, is_pass: bool, rs_grade: int, rct_grade: int, fail_items: list):
        """通道判断结果准备处理 - 实现批量显示控制"""
        try:
            logger.info(f"🎯 [分行批量显示] 通道{channel_number}判断结果准备: {'合格' if is_pass else '不合格'}")

            # 优化初始化批量显示管理器（如果不存在），但缩短延迟时间
            if not hasattr(self, '_batch_display_manager'):
                import time
                self._batch_display_manager = {
                    'pending_results': {},
                    'timer': None,
                    'batch_delay': 300  # 缩短到300ms
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

        except Exception as e:
            logger.error(f"处理通道{channel_number}判断结果准备失败: {e}")

    def _start_batch_display_timer(self):
        """启动批量显示定时器"""
        try:
            if self._batch_display_manager['timer'] and self._batch_display_manager['timer'].isActive():
                self._batch_display_manager['timer'].stop()

            from PyQt5.QtCore import QTimer
            self._batch_display_manager['timer'] = QTimer()
            self._batch_display_manager['timer'].setSingleShot(True)
            self._batch_display_manager['timer'].timeout.connect(self._execute_batch_display)
            self._batch_display_manager['timer'].start(self._batch_display_manager['batch_delay'])

        except Exception as e:
            logger.error(f"启动批量显示定时器失败: {e}")

    def _execute_batch_display(self):
        """执行批量显示"""
        try:
            if not hasattr(self, '_batch_display_manager') or not self._batch_display_manager['pending_results']:
                return

            pending_results = self._batch_display_manager['pending_results']
            logger.info(f"🎯 [分行批量显示] 开始批量显示 {len(pending_results)} 个通道的结果")

            for channel_number, result_data in pending_results.items():
                try:
                    channel_widget = self.get_channel(channel_number)
                    if channel_widget and hasattr(channel_widget, 'trigger_result_display'):
                        channel_widget.trigger_result_display(
                            result_data['is_pass'],
                            result_data['rs_grade'],
                            result_data['rct_grade'],
                            result_data['fail_items']
                        )
                except Exception as e:
                    logger.error(f"🎯 [分行批量显示] 通道{channel_number}结果显示失败: {e}")

            self._batch_display_manager['pending_results'].clear()

        except Exception as e:
            logger.error(f"执行批量显示失败: {e}")

    def _check_all_channels_ready(self):
        """检查所有通道是否准备就绪"""
        try:
            # 修复检查所有通道是否都完成测试
            all_ready = True
            ready_count = 0
            total_count = len(self.channels)

            for channel in self.channels:
                # 修复使用_test_completed属性而不是is_test_completed方法
                if hasattr(channel, '_test_completed') and channel._test_completed:
                    ready_count += 1
                    logger.debug(f"通道{channel.channel_number}已完成测试")
                elif hasattr(channel, 'is_test_completed') and callable(channel.is_test_completed) and channel.is_test_completed():
                    ready_count += 1
                    logger.debug(f"通道{channel.channel_number}已完成测试（方法检查）")
                else:
                    # 修复检查是否不在测试状态（采样测试模式下的特殊处理）
                    if hasattr(channel, 'is_testing') and callable(channel.is_testing) and not channel.is_testing():
                        # 检查是否有测试数据
                        if (hasattr(channel, 'rs_value') and hasattr(channel, 'rct_value') and
                            channel.rs_value > 0 and channel.rct_value > 0):
                            ready_count += 1
                            logger.debug(f"通道{channel.channel_number}已完成测试（数据检查）")
                        else:
                            all_ready = False
                            logger.debug(f"通道{channel.channel_number}未完成测试：无有效数据")
                    else:
                        all_ready = False
                        logger.debug(f"通道{channel.channel_number}未完成测试：仍在测试中")

            logger.info(f"通道完成状态检查: {ready_count}/{total_count} 通道已完成")

            if all_ready and ready_count == total_count:
                logger.info("🎯 所有通道测试完成，发射all_channels_ready信号")
                self.all_channels_ready.emit()
            else:
                logger.debug(f"等待更多通道完成: {ready_count}/{total_count}")

        except Exception as e:
            logger.error(f"检查所有通道状态失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

    def get_channel(self, channel_number: int) -> Optional[ChannelDisplayWidget]:
        """
        获取指定通道组件

        Args:
            channel_number: 通道号

        Returns:
            通道组件或None
        """
        if self._is_valid_channel(channel_number):
            return self.channels[channel_number - 1]
        return None

    def update_channel_progress(self, channel_num: int, progress_data: dict):
        """
        更新通道测试进度

        Args:
            channel_num: 通道号
            progress_data: 进度数据
        """
        try:
            channel = self.get_channel(channel_num)
            if channel:
                # 修复添加频点信息处理逻辑
                # 提取频点信息，确保类型安全
                frequency = progress_data.get('frequency', 0)
                frequency_index = progress_data.get('frequency_index', 0)
                completed_frequency_count = progress_data.get(
                    'completed_frequency_count',
                    progress_data.get('completed_frequencies', frequency_index)
                )
                total_frequencies = progress_data.get('total_frequencies', 0)
                state = progress_data.get('state', 'unknown')

                # 确保频率值不为None
                if frequency is None:
                    frequency = 0
                if frequency_index is None:
                    frequency_index = 0
                if total_frequencies is None:
                    total_frequencies = 0

                # 更新通道测试进度
                channel.update_test_progress(progress_data)

                # 修复如果有频点信息，更新频点显示
                if frequency > 0 and hasattr(channel, 'update_frequency_info'):
                    # 检查是否为错频模式
                    mode = progress_data.get('mode', 'unknown')

                    if mode == 'staggered':
                        # 错频模式：记录通道的专用频率，防止被统一更新覆盖
                        if not hasattr(self, '_staggered_channel_frequencies'):
                            self._staggered_channel_frequencies = {}

                        self._staggered_channel_frequencies[channel_num] = frequency

                    # 调用频率更新
                    channel.update_frequency_info(
                        frequency, frequency_index, total_frequencies, state, completed_frequency_count
                    )
            else:
                logger.warning(f"通道{channel_num}不存在")

        except Exception as e:
            logger.error(f"更新通道{channel_num}进度失败: {e}")

    def update_channel_outlier_rate_result(self, channel_num: int, outlier_result: dict,
                                         baseline_filename: str, frequency_deviations: dict, is_final: bool):
        """
        🔧 已移除：更新通道离群率结果（功能已完全移除）
        """
        # 离群率功能已完全移除，不执行任何操作
        logger.debug(f"离群检测功能已移除，忽略通道{channel_num}离群率结果更新")
        pass

    def set_channel_enabled(self, channel_num: int, enabled: bool):
        """
        设置通道启用状态

        Args:
            channel_num: 通道号
            enabled: 是否启用
        """
        try:
            channel = self.get_channel(channel_num)
            if channel:
                channel.set_enabled(enabled)
            else:
                logger.warning(f"通道{channel_num}不存在")

        except Exception as e:
            logger.error(f"设置通道{channel_num}启用状态失败: {e}")

    def update_all_outlier_detection_status(self, enabled: bool):
        """
        🔧 已移除：更新所有通道的离群检测状态（功能已完全移除）
        """
        # 离群率功能已完全移除，不执行任何操作
        logger.info(f"离群检测功能已移除，忽略状态更新请求: {'启用' if enabled else '禁用'}")
        pass

    def reset_all_channels(self):
        """重置所有通道状态"""
        try:
            for channel in self.channels:
                if hasattr(channel, 'reset_channel'):
                    channel.reset_channel()

        except Exception as e:
            logger.error(f"重置所有通道失败: {e}")

    def get_all_channel_data(self) -> dict:
        """
        获取所有通道数据

        Returns:
            所有通道数据字典
        """
        try:
            data = {}
            for i, channel in enumerate(self.channels):
                channel_num = i + 1
                if hasattr(channel, 'get_channel_data'):
                    data[channel_num] = channel.get_channel_data()
                else:
                    data[channel_num] = {}

            return data

        except Exception as e:
            logger.error(f"获取所有通道数据失败: {e}")
            return {}

    def set_channel_battery_code(self, channel_number: int, battery_code: str):
        """
        设置指定通道的电池码

        Args:
            channel_number: 通道号 (1-8)
            battery_code: 电池码
        """
        try:
            channel_widget = self.get_channel(channel_number)
            if channel_widget and hasattr(channel_widget, 'battery_code_edit'):
                channel_widget.battery_code_edit.setText(battery_code)
                # 通道电池码已设置 - 运行时不输出日志
                pass
            else:
                logger.warning(f"❌ 无效的通道号或通道组件: {channel_number}")

        except Exception as e:
            logger.error(f"❌ 设置通道{channel_number}电池码失败: {e}")

    def get_channel_battery_codes(self) -> list:
        """
        获取所有通道的电池码

        Returns:
            电池码列表 (8个元素，对应通道1-8)
        """
        battery_codes = [""] * CHANNEL_COUNT

        try:
            for i, channel in enumerate(self.channels):
                if hasattr(channel, 'battery_code_edit'):
                    battery_codes[i] = channel.battery_code_edit.text().strip()

        except Exception as e:
            logger.error(f"获取通道电池码失败: {e}")

        return battery_codes

    def get_enabled_channels(self) -> list:
        """
        获取启用的通道列表

        Returns:
            启用的通道号列表
        """
        enabled_channels = []

        try:
            for i, channel in enumerate(self.channels):
                channel_num = i + 1
                if hasattr(channel, 'is_enabled') and channel.is_enabled:
                    enabled_channels.append(channel_num)
                elif not hasattr(channel, 'is_enabled'):
                    # 如果没有is_enabled属性，默认认为启用
                    enabled_channels.append(channel_num)

        except Exception as e:
            logger.error(f"获取启用通道列表失败: {e}")
            # 返回默认的所有通道
            enabled_channels = list(range(1, CHANNEL_COUNT + 1))

        return enabled_channels

    def update_channel_test_count(self, channel_num: int, count: int):
        """
        更新指定通道的测试计数显示
        
        Args:
            channel_num: 通道号
            count: 测试计数
        """
        try:
            channel = self.get_channel(channel_num)
            if channel:
                # 检查通道是否有测试计数更新方法
                if hasattr(channel, 'update_test_count'):
                    channel.update_test_count(count)
                    logger.debug(f"✅ 通道{channel_num}测试计数已更新: {count}")
                elif hasattr(channel, 'set_test_count'):
                    channel.set_test_count(count)
                    logger.debug(f"✅ 通道{channel_num}测试计数已设置: {count}")
                else:
                    logger.debug(f"⚠️ 通道{channel_num}不支持测试计数更新")
            else:
                logger.warning(f"❌ 通道{channel_num}不存在")
                
        except Exception as e:
            logger.error(f"❌ 更新通道{channel_num}测试计数失败: {e}")

    def refresh_all_test_counts(self):
        """刷新所有通道的测试计数显示"""
        try:
            for i in range(CHANNEL_COUNT):
                channel_num = i + 1
                # 从配置获取测试计数
                count = self.config_manager.get(f'test_count.channel_{channel_num}', 0)
                self.update_channel_test_count(channel_num, count)
            
            logger.info("✅ 所有通道测试计数已刷新")
            
        except Exception as e:
            logger.error(f"❌ 刷新所有通道测试计数失败: {e}")
