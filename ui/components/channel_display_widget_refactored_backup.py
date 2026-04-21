# -*- coding: utf-8 -*-
"""
单通道显示组件（重构版本）
作为协调器角色，负责初始化和协调各个管理器，不包含具体业务逻辑

Author: Jack
Date: 2025-06-27
"""

import logging
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager

# 导入所有管理器类
from .channel_data_manager import ChannelDataManager
from .channel_timer_manager import ChannelTimerManager
from .channel_state_manager import ChannelStateManager, TestState
from .channel_ui_updater import ChannelUIUpdater
from .channel_event_handler import ChannelEventHandler
from .channel_ui_layout_manager import ChannelUILayoutManager
from .channel_test_judgment_manager import ChannelTestJudgmentManager
from .channel_style_manager import ChannelStyleManager
from .channel_frequency_manager import ChannelFrequencyManager
from .channel_config_manager import ChannelConfigManager

# 导入新创建的管理器类
from .channel_capacity_prediction_manager import ChannelCapacityPredictionManager
from .channel_test_completion_manager import ChannelTestCompletionManager
from .channel_exception_state_manager import ChannelExceptionStateManager
from .channel_print_data_manager import ChannelPrintDataManager
from .channel_delayed_judgment_manager import ChannelDelayedJudgmentManager
from .channel_test_count_manager import ChannelTestCountManager
from .channel_outlier_detection_manager import ChannelOutlierDetectionManager


class ChannelDisplayWidget(QWidget):
    """单通道显示组件（重构版本）- 协调器角色"""

    # 信号定义
    battery_code_changed = pyqtSignal(int, str)  # 电池码变更信号 (channel, code)
    test_completed = pyqtSignal(int, dict)  # 测试完成信号 (channel, result)
    statistics_update_requested = pyqtSignal(bool, int, int)  # 统计更新信号 (is_pass, rs_grade, rct_grade)
    judgment_ready = pyqtSignal(int, bool, int, int, list)  # 判断结果准备信号 (channel, is_pass, rs_grade, rct_grade, fail_items)

    def __init__(self, channel_number: int, config_manager: ConfigManager, parent=None):
        """
        初始化单通道显示组件

        Args:
            channel_number: 通道号 (1-8)
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)

        self.channel_number = channel_number
        self.config_manager = config_manager

        # 初始化所有管理器
        self._init_managers()

        # 初始化UI
        self._init_ui()

        # 连接管理器之间的信号
        self._connect_manager_signals()

        logger.debug(f"通道{channel_number}显示组件初始化完成")

    def _init_managers(self):
        """初始化所有管理器"""
        try:
            # 核心数据管理器
            self.data_manager = ChannelDataManager(self.channel_number)
            
            # 计时器管理器
            self.timer_manager = ChannelTimerManager(self.channel_number)
            
            # 状态管理器
            self.state_manager = ChannelStateManager(self.channel_number)
            
            # UI布局管理器
            self.ui_layout_manager = ChannelUILayoutManager(self.channel_number, self)
            
            # 样式管理器
            self.style_manager = ChannelStyleManager(self.channel_number, self)
            
            # 频点管理器
            self.frequency_manager = ChannelFrequencyManager(self.channel_number)
            
            # 配置管理器
            self.channel_config_manager = ChannelConfigManager(self.channel_number, self.config_manager)
            
            # 测试判定管理器
            self.test_judgment_manager = ChannelTestJudgmentManager(self.channel_number, self.config_manager)
            
            # 容量预测管理器
            self.capacity_prediction_manager = ChannelCapacityPredictionManager(self.channel_number, self.config_manager, self)
            
            # 测试完成管理器
            self.test_completion_manager = ChannelTestCompletionManager(self.channel_number, self)
            
            # 异常状态管理器
            self.exception_state_manager = ChannelExceptionStateManager(self.channel_number, self)
            
            # 打印数据管理器
            self.print_data_manager = ChannelPrintDataManager(self.channel_number)
            
            # 延迟判断管理器
            self.delayed_judgment_manager = ChannelDelayedJudgmentManager(self.channel_number, self)
            
            # 测试计数管理器
            self.test_count_manager = ChannelTestCountManager(self.channel_number, self.config_manager, self)
            
            # 离群检测管理器
            self.outlier_detection_manager = ChannelOutlierDetectionManager(self.channel_number, self)
            
            # UI更新器（需要在UI创建后初始化）
            self.ui_updater = None
            
            # 事件处理器（需要在UI创建后初始化）
            self.event_handler = None

            logger.debug(f"通道{self.channel_number}所有管理器初始化完成")
        except Exception as e:
            logger.error(f"通道{self.channel_number}管理器初始化失败: {e}")

    def _init_ui(self):
        """初始化用户界面"""
        try:
            # 使用UI布局管理器创建布局
            main_layout = self.ui_layout_manager.create_main_layout()

            if main_layout is None:
                logger.error(f"通道{self.channel_number}UI布局创建失败")
                return

            # 获取UI元素引用
            ui_elements = self.ui_layout_manager.get_all_ui_elements()

            # 将UI元素引用分发给各个管理器
            self._distribute_ui_elements(ui_elements)

            # 连接UI信号
            self._connect_ui_signals(ui_elements)

            # 应用样式
            self.style_manager.apply_default_styles()

            # 初始化UI更新器和事件处理器
            self._init_ui_components(ui_elements)

            logger.debug(f"通道{self.channel_number}UI初始化完成")
        except Exception as e:
            logger.error(f"通道{self.channel_number}UI初始化失败: {e}")

    def _distribute_ui_elements(self, ui_elements: dict):
        """将UI元素引用分发给各个管理器"""
        try:
            # 分发给容量预测管理器
            self.capacity_prediction_manager.set_ui_elements(ui_elements)
            
            # 分发给测试完成管理器
            self.test_completion_manager.set_ui_elements(ui_elements)
            
            # 分发给异常状态管理器
            self.exception_state_manager.set_ui_elements(ui_elements)
            
            # 分发给测试计数管理器
            self.test_count_manager.set_ui_elements(ui_elements)
            
            # 分发给离群检测管理器
            self.outlier_detection_manager.set_ui_elements(ui_elements)
        except Exception as e:
            logger.error(f"通道{self.channel_number}分发UI元素失败: {e}")

    def _init_ui_components(self, ui_elements: dict):
        """初始化UI组件"""
        try:
            # 初始化UI更新器
            self.ui_updater = ChannelUIUpdater(self.channel_number, ui_elements)
            
            # 初始化事件处理器
            self.event_handler = ChannelEventHandler(self.channel_number, self)
        except Exception as e:
            logger.error(f"通道{self.channel_number}UI组件初始化失败: {e}")

    def _connect_ui_signals(self, ui_elements: dict):
        """连接UI信号"""
        try:
            # 连接电池码输入信号
            battery_code_edit = ui_elements.get('battery_code_edit')
            if battery_code_edit:
                battery_code_edit.textChanged.connect(self._on_battery_code_changed)
        except Exception as e:
            logger.error(f"通道{self.channel_number}连接UI信号失败: {e}")

    def _connect_manager_signals(self):
        """连接管理器之间的信号"""
        try:
            # 连接计时器管理器信号
            self.timer_manager.timer_updated.connect(self._on_timer_updated)
            
            # 连接状态管理器信号
            self.state_manager.add_state_change_callback(self._on_state_changed)
            
            # 连接频点管理器信号
            self.frequency_manager.frequency_updated.connect(self._on_frequency_updated)
            
            # 连接测试完成管理器信号
            self.test_completion_manager.test_completed.connect(self.test_completed.emit)
            self.test_completion_manager.statistics_update_requested.connect(self.statistics_update_requested.emit)
            
            # 连接异常状态管理器信号
            self.exception_state_manager.test_completed.connect(self.test_completed.emit)
            
            # 连接延迟判断管理器信号
            self.delayed_judgment_manager.judgment_ready.connect(self.judgment_ready.emit)
            
            # 设置管理器之间的数据源引用
            self.print_data_manager.set_data_sources(self.test_completion_manager, self.data_manager)
            
            # 设置延迟判断管理器的回调
            self.delayed_judgment_manager.set_judgment_callback(self._execute_judgment)
            self.delayed_judgment_manager.set_completion_callback(self._execute_completion)

        except Exception as e:
            logger.error(f"通道{self.channel_number}连接管理器信号失败: {e}")

    # ===== 兼容性属性和方法 =====

    @property
    def test_progress(self) -> int:
        """测试进度（兼容性属性）"""
        return self.data_manager.test_data.test_progress

    @test_progress.setter
    def test_progress(self, value: int):
        """设置测试进度（兼容性属性）"""
        self.data_manager.update_progress(value)

    @property
    def battery_code(self) -> str:
        """电池码（兼容性属性）"""
        return self.data_manager.test_data.battery_code

    @battery_code.setter
    def battery_code(self, value: str):
        """设置电池码（兼容性属性）"""
        self.data_manager.update_battery_code(value)

    @property
    def voltage(self) -> float:
        """电压（兼容性属性）"""
        return self.data_manager.test_data.voltage

    @voltage.setter
    def voltage(self, value: float):
        """设置电压（兼容性属性）"""
        self.data_manager.update_voltage(value)

    @property
    def rs_value(self) -> float:
        """Rs值（兼容性属性）"""
        return self.data_manager.test_data.rs_value

    @rs_value.setter
    def rs_value(self, value: float):
        """设置Rs值（兼容性属性）"""
        # 使用update_impedance方法，保持原有Rct值
        current_rct = self.data_manager.test_data.rct_value
        self.data_manager.update_impedance(value, current_rct)

    @property
    def rct_value(self) -> float:
        """Rct值（兼容性属性）"""
        return self.data_manager.test_data.rct_value

    @rct_value.setter
    def rct_value(self, value: float):
        """设置Rct值（兼容性属性）"""
        # 使用update_impedance方法，保持原有Rs值
        current_rs = self.data_manager.test_data.rs_value
        self.data_manager.update_impedance(current_rs, value)

    # ===== 事件处理方法 =====

    def _on_timer_updated(self, channel_number: int, elapsed_time: float):
        """计时器更新事件处理"""
        if self.ui_updater:
            self.ui_updater.update_timer_display(elapsed_time)

    def _on_state_changed(self, event):
        """状态变更事件处理"""
        logger.debug(f"通道{self.channel_number}状态变更: {event}")

    def _on_frequency_updated(self, channel_number: int, frequency: float, current_index: int, total_count: int, status: str):
        """频点更新事件处理"""
        if self.ui_updater:
            self.ui_updater.update_frequency_display(frequency, current_index, total_count, status)

    def _on_battery_code_changed(self, text: str):
        """电池码变更事件处理"""
        self.data_manager.update_battery_code(text)
        self.battery_code_changed.emit(self.channel_number, text)

    def _execute_judgment(self, voltage: float, rs_value: float, rct_value: float, outlier_result: Optional[str]):
        """执行判断逻辑"""
        # 委托给测试判定管理器
        pass  # 具体实现需要根据原有逻辑补充

    def _execute_completion(self, is_pass: bool, rs_grade: int, rct_grade: int, fail_items: Optional[list]):
        """执行完成逻辑"""
        # 委托给测试完成管理器
        pass  # 具体实现需要根据原有逻辑补充

    # ===== 公共接口方法 =====

    def start_test(self, battery_code: str = ""):
        """开始测试"""
        try:
            # 设置电池码
            if battery_code:
                self.battery_code = battery_code

            # 启动计时器
            self.timer_manager.start_timer()

            # 设置测试状态
            self.state_manager.set_test_state(TestState.TESTING)

            # 重置测试完成状态
            self.test_completion_manager.reset_completion_state()

            # 重置离群检测数据
            self.outlier_detection_manager.reset_outlier_data()

            logger.debug(f"通道{self.channel_number}开始测试")

        except Exception as e:
            logger.error(f"通道{self.channel_number}开始测试失败: {e}")

    def stop_test(self, clear_results=None):
        """停止测试"""
        try:
            # 停止计时器
            self.timer_manager.stop_timer()

            # 设置测试状态
            self.state_manager.set_test_state(TestState.COMPLETED)

            logger.debug(f"通道{self.channel_number}停止测试")

        except Exception as e:
            logger.error(f"通道{self.channel_number}停止测试失败: {e}")

    def update_test_data(self, voltage: float, rs: float, rct: float, progress: int):
        """更新测试数据"""
        try:
            # 更新数据管理器
            self.data_manager.update_voltage(voltage)
            self.data_manager.update_impedance(rs, rct)
            self.data_manager.update_progress(progress)

            # 更新UI显示
            if self.ui_updater:
                self.ui_updater.update_test_data(voltage, rs, rct, progress)

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新测试数据失败: {e}")

    def update_battery_status(self, status: str, voltage: float):
        """更新电池状态"""
        try:
            # 更新电压
            self.voltage = voltage

            # 更新UI显示
            if self.ui_updater:
                self.ui_updater.update_battery_status(status, voltage)

        except Exception as e:
            logger.error(f"通道{self.channel_number}更新电池状态失败: {e}")

    def complete_test_with_judgment(self, voltage: float, rs_value: float, rct_value: float):
        """完成测试并进行判断"""
        try:
            # 获取离群检测数据
            outlier_data = self.outlier_detection_manager.get_outlier_data()

            # 执行测试完成逻辑
            test_result = self.test_completion_manager.set_test_completed(
                is_pass=True,  # 需要根据判断逻辑确定
                rs_grade=1,    # 需要根据判断逻辑确定
                rct_grade=1,   # 需要根据判断逻辑确定
                voltage=voltage,
                rs_value=rs_value,
                rct_value=rct_value,
                battery_code=self.battery_code,
                fail_items=None,
                outlier_data=outlier_data
            )

            # 增加测试计数
            self.test_count_manager.increment_test_count()

            # 执行容量预测
            self.capacity_prediction_manager.perform_capacity_prediction_if_enabled(
                voltage, rs_value, rct_value, self.battery_code
            )

            return test_result

        except Exception as e:
            logger.error(f"通道{self.channel_number}完成测试判断失败: {e}")
            return {}

    def set_exception_state(self, exception_type: str, error_message: str, voltage: float = 0.0):
        """设置异常状态"""
        return self.exception_state_manager.set_exception_state(
            exception_type, error_message, voltage, self.battery_code
        )

    def get_print_data(self) -> dict:
        """获取打印数据"""
        return self.print_data_manager.get_print_data()

    def update_outlier_detection_status(self, enabled: bool):
        """更新离群检测状态"""
        self.outlier_detection_manager.update_outlier_detection_status(enabled)

    def update_outlier_rate_result(self, result: str, baseline_filename: str = "",
                                 frequency_deviations: Optional[dict] = None, is_final: bool = False):
        """更新离群率结果"""
        self.outlier_detection_manager.update_outlier_rate_result(
            result, baseline_filename, frequency_deviations, is_final
        )

    def update_frequency_info(self, frequency: float, current_index: int, total_count: int, status: str = "waiting"):
        """更新频点信息"""
        self.frequency_manager.update_frequency_info(frequency, current_index, total_count, status)

    def set_channel_enabled(self, enabled: bool):
        """设置通道启用状态"""
        self.state_manager.set_enable_state(enabled)

    def is_testing(self) -> bool:
        """检查是否正在测试"""
        return self.state_manager.test_state == TestState.TESTING

    def reset(self):
        """重置通道状态"""
        try:
            # 重置数据管理器
            self.data_manager.reset_data()

            # 重置计时器
            self.timer_manager.reset_timer()

            # 重置状态
            self.state_manager.set_test_state(TestState.IDLE)

            # 重置测试完成状态
            self.test_completion_manager.reset_completion_state()

            # 重置离群检测数据
            self.outlier_detection_manager.reset_outlier_data()

            # 重置延迟操作
            self.delayed_judgment_manager.reset_delayed_operations()

            logger.debug(f"通道{self.channel_number}状态已重置")

        except Exception as e:
            logger.error(f"通道{self.channel_number}重置状态失败: {e}")

    def get_test_result(self) -> dict:
        """获取测试结果"""
        return self.test_completion_manager.get_test_result()

    def get_test_count(self) -> int:
        """获取测试计数"""
        return self.test_count_manager.get_test_count()

    def reset_test_count(self):
        """重置测试计数"""
        self.test_count_manager.reset_test_count()

    def get_manager(self, manager_name: str):
        """获取指定的管理器"""
        return getattr(self, manager_name, None)

    # 兼容性方法 - 为了保持与旧版本的兼容性
    def set_enabled(self, enabled):
        """设置通道启用状态（兼容性方法）"""
        try:
            self.set_channel_enabled(enabled)
        except Exception as e:
            logger.error(f"设置通道启用状态失败: {e}")

    def update_test_progress(self, progress):
        """更新测试进度（兼容性方法）"""
        try:
            if hasattr(self, 'ui_updater') and self.ui_updater:
                self.ui_updater.update_progress(progress)
        except Exception as e:
            logger.error(f"更新测试进度失败: {e}")
