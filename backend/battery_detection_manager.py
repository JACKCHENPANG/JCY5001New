#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电池自动侦测管理器
实现电池移除检测、新电池插入检测和自动重启测试功能
"""

import time
import threading
from enum import Enum
from typing import Dict, List, Optional, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BatteryState(Enum):
    """电池状态枚举"""
    UNKNOWN = "unknown"           # 未知状态
    CONNECTED = "connected"       # 电池已连接
    REMOVED = "removed"          # 电池已移除
    WAITING_NEW = "waiting_new"  # 等待新电池


class ChannelDetectionState:
    """通道侦测状态"""
    def __init__(self, channel_num: int):
        self.channel_num = channel_num
        self.battery_state = BatteryState.UNKNOWN
        self.pending_state: Optional[BatteryState] = None  # 待确认的状态
        self.last_voltage = 0.0
        self.voltage_history = []  # 电压历史记录
        self.state_change_time = datetime.now()
        self.stable_count = 0  # 稳定状态计数

        # 修复添加防重复检测机制
        self.last_detection_time: Optional[datetime] = None  # 最后一次检测时间
        self.detection_cooldown = 5.0  # 检测冷却时间（秒）
        self.test_completed = False  # 测试是否已完成

    def add_voltage_reading(self, voltage: float):
        """添加电压读数"""
        self.last_voltage = voltage
        self.voltage_history.append({
            'voltage': voltage,
            'timestamp': datetime.now()
        })

        # 只保留最近10次读数
        if len(self.voltage_history) > 10:
            self.voltage_history.pop(0)

    def get_average_voltage(self, count: int = 3) -> float:
        """获取最近几次的平均电压"""
        if not self.voltage_history:
            return 0.0

        recent_readings = self.voltage_history[-count:]
        if not recent_readings:
            return 0.0

        return sum(r['voltage'] for r in recent_readings) / len(recent_readings)


class BatteryDetectionManager:
    """电池自动侦测管理器"""

    def __init__(self, comm_manager, config_manager):
        self.main_comm_manager = comm_manager  # 保存主通信管理器引用
        self.config_manager = config_manager

        # 为电池侦测创建独立的通信管理器
        self.detection_comm_manager = None

        # 侦测状态
        self.is_detecting = False
        self.detection_thread = None
        self.stop_event = threading.Event()

        # 通道状态
        self.channels: Dict[int, ChannelDetectionState] = {}
        for i in range(1, 9):  # 8个通道
            self.channels[i] = ChannelDetectionState(i)

        # 从配置管理器读取配置参数（优化为更敏感的检测）
        self.voltage_threshold_remove = config_manager.get('battery_detection.voltage_threshold_remove', 5.0)
        self.voltage_threshold_min = config_manager.get('battery_detection.voltage_threshold_min', 2.0)
        self.voltage_threshold_max = config_manager.get('battery_detection.voltage_threshold_max', 5.0)
        self.detection_interval = config_manager.get('battery_detection.detection_interval', 0.5)  # 提高检测频率
        self.stable_count_required = config_manager.get('battery_detection.stable_count_required', 2)  # 降低确认要求
        self.auto_restart_delay = config_manager.get('battery_detection.auto_restart_delay', 2.0)

        # 回调函数
        self.battery_removed_callback: Optional[Callable] = None
        self.new_battery_detected_callback: Optional[Callable] = None
        self.status_update_callback: Optional[Callable] = None

        logger.debug("电池侦测管理器初始化完成")

    def _create_detection_comm_manager(self):
        """创建独立的通信管理器用于电池侦测"""
        try:
            # 导入通信管理器类
            from backend.communication_manager import CommunicationManager as ModbusRTUManager

            # 获取主通信管理器的连接参数
            port = self.main_comm_manager.port
            baudrate = self.main_comm_manager.baudrate
            device_address = self.main_comm_manager.device_address
            timeout = self.main_comm_manager.timeout

            # 创建独立的通信管理器配置
            detection_config = {
                'port': port,
                'baudrate': baudrate,
                'device_address': device_address,
                'timeout': timeout,
                'retry_count': 2,  # 减少重试次数，提高响应速度
                'retry_delay': 0.05,  # 减少重试延时
                'max_consecutive_failures': 5  # 减少最大失败次数
            }

            # 创建独立的通信管理器实例
            self.detection_comm_manager = ModbusRTUManager(detection_config)

            # 连接设备
            if self.detection_comm_manager.connect():
                logger.info(f"🔗 电池侦测独立通信管理器连接成功: {port}")
                return True
            else:
                logger.error(f"❌ 电池侦测独立通信管理器连接失败: {port}")
                self.detection_comm_manager = None
                return False

        except Exception as e:
            logger.error(f"创建电池侦测通信管理器失败: {e}")
            self.detection_comm_manager = None
            return False

    def set_callbacks(self, battery_removed_callback=None, new_battery_detected_callback=None, status_update_callback=None):
        """设置回调函数"""
        self.battery_removed_callback = battery_removed_callback
        self.new_battery_detected_callback = new_battery_detected_callback
        self.status_update_callback = status_update_callback

    def start_detection(self, enabled_channels: Optional[List[int]] = None):
        """
        启动电池侦测

        Args:
            enabled_channels: 启用侦测的通道列表，None表示所有通道
        """
        try:
            if self.is_detecting:
                logger.info("电池侦测已在运行中，添加新的监控通道")
                # 如果已经在运行，添加新的监控通道
                if enabled_channels:
                    for channel_num in enabled_channels:
                        if channel_num in self.channels:
                            self.channels[channel_num].battery_state = BatteryState.CONNECTED
                            self.channels[channel_num].stable_count = 0
                    logger.info(f"已添加监控通道: {enabled_channels}")
                return

            # 检查是否启用自动侦测
            auto_detect = self.config_manager.get('test.auto_detect', False)  # 修复：默认值改为False，与屏蔽状态一致
            battery_detection_enabled = self.config_manager.get('battery_detection.enabled', True)

            # 重新启用电池侦测功能，使用独立通信管理器
            logger.info("🔄 电池侦测功能已重新启用，使用独立通信管理器")

            if not auto_detect or not battery_detection_enabled:
                logger.info("自动侦测功能已禁用，跳过启动")
                return

            if enabled_channels is None:
                enabled_channels = list(range(1, 9))  # 默认所有8个通道

            logger.info(f"启动电池侦测，监控通道: {enabled_channels}")

            # 检查主通信管理器是否可用
            if not self.main_comm_manager or not self.main_comm_manager.is_connected:
                logger.error("主通信管理器未连接，跳过电池侦测启动")
                return

            # 重置状态
            self.stop_event.clear()
            self.is_detecting = True

            # 初始化通道状态
            for channel_num in enabled_channels:
                if channel_num in self.channels:
                    self.channels[channel_num].battery_state = BatteryState.CONNECTED
                    self.channels[channel_num].stable_count = 0

            # 启动侦测线程
            self.detection_thread = threading.Thread(
                target=self._detection_worker,
                args=(enabled_channels,),
                daemon=True,
                name="BatteryDetection"
            )
            self.detection_thread.start()

            logger.info("✅ 电池侦测已启动")

        except Exception as e:
            logger.error(f"启动电池侦测失败: {e}")
            self.is_detecting = False

    def stop_detection(self):
        """停止电池侦测"""
        try:
            if not self.is_detecting:
                return

            logger.info("停止电池侦测...")

            self.stop_event.set()
            self.is_detecting = False

            # 等待线程结束
            if self.detection_thread and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=3.0)

            # 清理资源（不需要关闭独立通信管理器，因为使用的是主通信管理器）
            self.detection_comm_manager = None

            logger.info("✅ 电池侦测已停止")

        except Exception as e:
            logger.error(f"停止电池侦测失败: {e}")

    def _detection_worker(self, enabled_channels: List[int]):
        """侦测工作线程"""
        try:
            logger.info(f"电池侦测工作线程启动，监控通道: {enabled_channels}")

            while not self.stop_event.is_set():
                try:
                    # 读取所有通道电压
                    voltages = self._read_channel_voltages(enabled_channels)

                    if voltages:
                        # 分析电压变化并更新状态
                        self._analyze_voltage_changes(voltages, enabled_channels)

                    # 等待下次检测
                    time.sleep(self.detection_interval)

                except Exception as e:
                    logger.error(f"电池侦测循环异常: {e}")
                    time.sleep(2.0)  # 异常时延长等待时间

            logger.info("电池侦测工作线程结束")

        except Exception as e:
            logger.error(f"电池侦测工作线程失败: {e}")

    def _read_channel_voltages(self, enabled_channels: List[int]) -> Dict[int, float]:
        """读取指定通道的电压"""
        try:
            voltages = {}

            # 检查主通信管理器是否可用
            if not self.main_comm_manager or not self.main_comm_manager.is_connected:
                logger.warning("主通信管理器未连接，跳过电压读取")
                return {}

            # 逐个读取通道电压（使用主通信管理器，但增加错误处理）
            for channel_num in enabled_channels:
                try:
                    # 使用主通信管理器读取电压（移除for_detection参数，新架构不支持）
                    voltage = self.main_comm_manager.read_voltage(channel_num - 1)  # 转换为0基索引
                    if voltage is not None:
                        voltages[channel_num] = voltage
                    else:
                        logger.debug(f"通道{channel_num}电压读取失败(侦测模式)")
                except Exception as e:
                    logger.debug(f"通道{channel_num}电压读取异常(侦测模式): {e}")
                    # 电池侦测失败不应该影响主要功能，所以只记录debug级别日志

            return voltages

        except Exception as e:
            logger.error(f"读取通道电压失败: {e}")
            return {}

    def _analyze_voltage_changes(self, voltages: Dict[int, float], enabled_channels: List[int]):
        """分析电压变化并更新电池状态"""
        try:
            for channel_num in enabled_channels:
                if channel_num not in voltages:
                    continue

                voltage = voltages[channel_num]
                channel_state = self.channels[channel_num]

                # 添加电压读数
                channel_state.add_voltage_reading(voltage)

                # 直接根据当前电压判断状态（不使用平均值，提高响应速度）
                new_state = self._determine_battery_state(voltage)

                # 检查状态变化
                if new_state != channel_state.battery_state:
                    # 检测到状态变化，立即处理（减少确认次数要求）
                    if hasattr(channel_state, 'pending_state') and channel_state.pending_state == new_state:
                        # 继续确认相同的新状态
                        channel_state.stable_count += 1
                        logger.info(f"🔄 通道{channel_num}继续确认状态变化: {channel_state.battery_state.value} -> {new_state.value} (确认次数: {channel_state.stable_count}/{self.stable_count_required})")
                    else:
                        # 开始新的状态变化确认
                        channel_state.pending_state = new_state
                        channel_state.stable_count = 1
                        logger.info(f"🔄 通道{channel_num}开始状态变化确认: {channel_state.battery_state.value} -> {new_state.value} (确认次数: 1/{self.stable_count_required})")

                    # 检查是否达到稳定确认要求
                    if channel_state.stable_count >= self.stable_count_required:
                        self._handle_stable_state_change(channel_num, channel_state, new_state, voltage)
                        # 清除待确认状态
                        if hasattr(channel_state, 'pending_state'):
                            delattr(channel_state, 'pending_state')
                            channel_state.stable_count = 0
                else:
                    # 状态没有变化
                    if hasattr(channel_state, 'pending_state'):
                        # 如果有待确认的状态变化，但当前状态又回到原状态
                        # 检查是否是快速变化（电池快速插拔）
                        if channel_state.pending_state == BatteryState.REMOVED and channel_state.battery_state == BatteryState.CONNECTED:
                            # 检测到电池移除信号但又快速回到连接状态，可能是快速插拔
                            # 先触发移除事件，然后重新检测
                            logger.info(f"通道{channel_num}检测到快速电池插拔，触发移除事件")
                            self._handle_battery_removed(channel_num, 5.9)  # 使用典型的移除电压

                            # 清除待确认状态，重新开始检测
                            delattr(channel_state, 'pending_state')
                            channel_state.stable_count = 0

                            # 如果当前是连接状态，可能是新电池
                            if new_state == BatteryState.CONNECTED:
                                logger.info(f"通道{channel_num}检测到新电池插入")
                                self._handle_new_battery_detected(channel_num, voltage)
                        else:
                            # 普通的状态变化取消
                            logger.info(f"↩️ 通道{channel_num}状态变化被取消，回到原状态: {channel_state.battery_state.value}")
                            delattr(channel_state, 'pending_state')
                            channel_state.stable_count = 0

        except Exception as e:
            logger.error(f"分析电压变化失败: {e}")

    def _determine_battery_state(self, voltage: float) -> BatteryState:
        """根据电压判断电池状态"""
        if voltage < 2.5:
            # 电压低于2.5V，判定为电池已移除（实际测试显示移除时电压降到2.0V左右）
            return BatteryState.REMOVED
        elif 2.5 <= voltage <= 4.0:
            # 电压在2.5V-4.0V范围内，判定为电池已连接（正常电池电压3.2V左右）
            return BatteryState.CONNECTED
        else:
            # 其他情况为未知状态
            return BatteryState.UNKNOWN

    def _handle_stable_state_change(self, channel_num: int, channel_state: ChannelDetectionState,
                                   new_state: BatteryState, voltage: float):
        """处理稳定的状态变化"""
        try:
            old_state = channel_state.battery_state

            # 更新状态
            channel_state.battery_state = new_state
            channel_state.state_change_time = datetime.now()

            logger.info(f"通道{channel_num}电池状态确认变化: {old_state.value} -> {new_state.value} (电压: {voltage:.3f}V)")

            # 处理特定的状态变化
            if old_state == BatteryState.CONNECTED and new_state == BatteryState.REMOVED:
                # 电池被移除
                self._handle_battery_removed(channel_num, voltage)

            elif old_state == BatteryState.REMOVED and new_state == BatteryState.CONNECTED:
                # 检测到新电池插入
                self._handle_new_battery_detected(channel_num, voltage)

            elif old_state == BatteryState.UNKNOWN and new_state == BatteryState.CONNECTED:
                # 从未知状态变为连接状态（可能是新电池）
                self._handle_new_battery_detected(channel_num, voltage)

            # 通知状态更新
            if self.status_update_callback:
                try:
                    self.status_update_callback(channel_num, new_state.value, voltage)
                except Exception as e:
                    logger.error(f"状态更新回调失败: {e}")

        except Exception as e:
            logger.error(f"处理状态变化失败: {e}")

    def _handle_battery_removed(self, channel_num: int, voltage: float):
        """处理电池移除事件"""
        try:
            logger.info(f"🔋 通道{channel_num}检测到电池移除 (电压: {voltage:.3f}V)")

            # 修复重置通道状态，允许下次检测
            channel_state = self.channels.get(channel_num)
            if channel_state:
                channel_state.test_completed = False
                channel_state.last_detection_time = None
                logger.debug(f"通道{channel_num}状态已重置，允许下次新电池检测")

            # 通知电池移除
            if self.battery_removed_callback:
                try:
                    self.battery_removed_callback(channel_num, voltage)
                except Exception as e:
                    logger.error(f"电池移除回调失败: {e}")

        except Exception as e:
            logger.error(f"处理电池移除事件失败: {e}")

    def _handle_new_battery_detected(self, channel_num: int, voltage: float):
        """处理新电池检测事件"""
        try:
            # 修复添加防重复检测机制
            channel_state = self.channels.get(channel_num)
            if not channel_state:
                logger.warning(f"通道{channel_num}状态不存在，跳过新电池检测")
                return

            current_time = datetime.now()

            # 检查是否在冷却期内
            if (channel_state.last_detection_time and
                (current_time - channel_state.last_detection_time).total_seconds() < channel_state.detection_cooldown):
                logger.debug(f"通道{channel_num}在检测冷却期内，跳过重复检测")
                return

            # 检查是否已经完成测试但电池未移除
            if channel_state.test_completed:
                logger.info(f"通道{channel_num}测试已完成，等待电池移除，跳过重复检测")
                return

            logger.info(f"🔋 通道{channel_num}检测到新电池插入 (电压: {voltage:.3f}V)")

            # 更新检测时间
            channel_state.last_detection_time = current_time

            # 通知新电池检测
            if self.new_battery_detected_callback:
                try:
                    self.new_battery_detected_callback(channel_num, voltage)
                except Exception as e:
                    logger.error(f"新电池检测回调失败: {e}")

        except Exception as e:
            logger.error(f"处理新电池检测事件失败: {e}")

    def get_channel_state(self, channel_num: int) -> Optional[Dict]:
        """获取通道状态信息"""
        try:
            if channel_num not in self.channels:
                return None

            channel_state = self.channels[channel_num]
            return {
                'channel_num': channel_num,
                'battery_state': channel_state.battery_state.value,
                'last_voltage': channel_state.last_voltage,
                'stable_count': channel_state.stable_count,
                'state_change_time': channel_state.state_change_time
            }

        except Exception as e:
            logger.error(f"获取通道状态失败: {e}")
            return None

    def get_all_channel_states(self) -> Dict[int, Dict]:
        """获取所有通道状态信息"""
        try:
            states = {}
            for channel_num in self.channels:
                state = self.get_channel_state(channel_num)
                if state:
                    states[channel_num] = state
            return states

        except Exception as e:
            logger.error(f"获取所有通道状态失败: {e}")
            return {}

    def is_running(self) -> bool:
        """检查侦测是否正在运行"""
        return (self.is_detecting and
                self.detection_thread is not None and
                self.detection_thread.is_alive())

    def mark_test_completed(self, channel_num: int):
        """标记通道测试完成"""
        try:
            channel_state = self.channels.get(channel_num)
            if channel_state:
                channel_state.test_completed = True
                logger.info(f"通道{channel_num}测试已标记为完成，等待电池移除")
        except Exception as e:
            logger.error(f"标记通道{channel_num}测试完成失败: {e}")

    def reset_channel_state(self, channel_num: int):
        """重置通道状态"""
        try:
            channel_state = self.channels.get(channel_num)
            if channel_state:
                channel_state.test_completed = False
                channel_state.last_detection_time = None
                logger.debug(f"通道{channel_num}状态已重置")
        except Exception as e:
            logger.error(f"重置通道{channel_num}状态失败: {e}")
