#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于状态码的电池检测管理器
使用设备状态码0003H来判断电池是否存在，比电压判断更可靠

Author: Jack
Date: 2025-01-30
"""

import logging
import threading
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class BatteryState(Enum):
    """电池状态枚举"""
    UNKNOWN = "unknown"      # 未知状态
    CONNECTED = "connected"  # 电池已连接
    REMOVED = "removed"      # 电池已移除


@dataclass
class ChannelDetectionState:
    """通道检测状态"""
    channel_number: int
    battery_state: BatteryState = BatteryState.UNKNOWN
    last_status_code: Optional[int] = None
    stable_count: int = 0
    state_change_time: Optional[datetime] = None


class StatusBasedBatteryDetectionManager:
    """基于状态码的电池检测管理器"""

    def __init__(self, comm_manager, config_manager):
        """
        初始化电池检测管理器
        
        Args:
            comm_manager: 通信管理器
            config_manager: 配置管理器
        """
        self.comm_manager = comm_manager
        self.config_manager = config_manager

        # 侦测状态
        self.is_detecting = False
        self.detection_thread = None
        self.stop_event = threading.Event()

        # 通道状态
        self.channels: Dict[int, ChannelDetectionState] = {}
        for i in range(1, 9):  # 8个通道
            self.channels[i] = ChannelDetectionState(i)

        # 从配置管理器读取配置参数
        self.detection_interval = config_manager.get('battery_detection.detection_interval', 1.0)
        self.stable_count_required = config_manager.get('battery_detection.stable_count_required', 2)

        # 回调函数
        self.battery_removed_callback: Optional[Callable] = None
        self.new_battery_detected_callback: Optional[Callable] = None
        self.status_update_callback: Optional[Callable] = None

        # 初始化设备状态管理器
        from backend.device_status_manager import DeviceStatusManager
        self.status_manager = DeviceStatusManager()

        logger.debug("基于状态码的电池检测管理器初始化完成")

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
                logger.info("电池侦测已在运行中")
                return

            # 检查是否启用自动侦测
            auto_detect = self.config_manager.get('test.auto_detect', False)  # 修复：默认值改为False，与屏蔽状态一致
            battery_detection_enabled = self.config_manager.get('battery_detection.enabled', True)

            if not auto_detect or not battery_detection_enabled:
                logger.info("自动侦测功能已禁用，跳过启动")
                return

            if enabled_channels is None:
                enabled_channels = list(range(1, 9))  # 默认所有8个通道

            logger.info(f"启动基于状态码的电池侦测，监控通道: {enabled_channels}")

            # 检查通信管理器是否可用
            if not self.comm_manager or not self.comm_manager.is_connected:
                logger.error("通信管理器未连接，跳过电池侦测启动")
                return

            # 重置状态
            self.stop_event.clear()
            self.is_detecting = True

            # 初始化通道状态
            for channel_num in enabled_channels:
                if channel_num in self.channels:
                    self.channels[channel_num].battery_state = BatteryState.UNKNOWN
                    self.channels[channel_num].stable_count = 0
                    self.channels[channel_num].last_status_code = None

            # 启动侦测线程
            self.detection_thread = threading.Thread(
                target=self._detection_worker,
                args=(enabled_channels,),
                daemon=True,
                name="StatusBasedBatteryDetection"
            )
            self.detection_thread.start()

            logger.info("✅ 基于状态码的电池侦测已启动")

        except Exception as e:
            logger.error(f"启动电池侦测失败: {e}")
            self.is_detecting = False

    def stop_detection(self):
        """停止电池侦测"""
        try:
            if not self.is_detecting:
                return

            logger.info("停止基于状态码的电池侦测...")

            self.stop_event.set()
            self.is_detecting = False

            # 等待线程结束
            if self.detection_thread and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=3.0)

            logger.info("✅ 基于状态码的电池侦测已停止")

        except Exception as e:
            logger.error(f"停止电池侦测失败: {e}")

    def _detection_worker(self, enabled_channels: List[int]):
        """侦测工作线程"""
        try:
            logger.info(f"基于状态码的电池侦测工作线程启动，监控通道: {enabled_channels}")

            while not self.stop_event.is_set():
                try:
                    # 读取所有通道状态码
                    status_codes = self._read_channel_status_codes(enabled_channels)

                    if status_codes:
                        # 分析状态码变化并更新状态
                        self._analyze_status_changes(status_codes, enabled_channels)

                    # 等待下次检测
                    time.sleep(self.detection_interval)

                except Exception as e:
                    logger.error(f"电池侦测循环异常: {e}")
                    time.sleep(2.0)  # 异常时延长等待时间

            logger.info("基于状态码的电池侦测工作线程结束")

        except Exception as e:
            logger.error(f"电池侦测工作线程失败: {e}")

    def _read_channel_status_codes(self, enabled_channels: List[int]) -> Dict[int, int]:
        """
        读取通道状态码
        
        Args:
            enabled_channels: 启用的通道列表
            
        Returns:
            通道状态码字典 {channel_num: status_code}
        """
        try:
            status_codes = {}
            
            # 尝试群发读取状态码
            all_status_codes = self.comm_manager.get_measurement_status_broadcast()
            
            if all_status_codes and len(all_status_codes) >= 8:
                # 群发读取成功
                for channel_num in enabled_channels:
                    channel_index = channel_num - 1
                    if channel_index < len(all_status_codes) and all_status_codes[channel_index] is not None:
                        status_codes[channel_num] = all_status_codes[channel_index]
                        logger.debug(f"通道{channel_num}状态码: 0x{all_status_codes[channel_index]:04X}")
            else:
                # 群发读取失败，逐个读取
                logger.debug("群发状态码读取失败，改为逐个读取")
                for channel_num in enabled_channels:
                    channel_index = channel_num - 1
                    status_code = self.comm_manager.read_channel_status(channel_index)
                    if status_code is not None:
                        status_codes[channel_num] = status_code
                        logger.debug(f"通道{channel_num}状态码: 0x{status_code:04X}")

            return status_codes

        except Exception as e:
            logger.error(f"读取通道状态码失败: {e}")
            return {}

    def _analyze_status_changes(self, status_codes: Dict[int, int], enabled_channels: List[int]):
        """
        分析状态码变化
        
        Args:
            status_codes: 通道状态码字典
            enabled_channels: 启用的通道列表
        """
        try:
            for channel_num in enabled_channels:
                if channel_num not in status_codes:
                    continue

                status_code = status_codes[channel_num]
                channel_state = self.channels[channel_num]

                # 根据状态码判断电池状态
                new_state = self._determine_battery_state_from_status(status_code)

                # 检查状态是否发生变化
                if channel_state.battery_state != new_state:
                    # 状态发生变化，开始稳定性检查
                    if not hasattr(channel_state, 'pending_state') or channel_state.pending_state != new_state:
                        # 新的状态变化
                        channel_state.pending_state = new_state
                        channel_state.stable_count = 1
                        logger.debug(f"通道{channel_num}状态变化: {channel_state.battery_state.value} -> {new_state.value} (待确认)")
                    else:
                        # 相同的状态变化，增加稳定计数
                        channel_state.stable_count += 1
                        logger.debug(f"通道{channel_num}状态变化稳定计数: {channel_state.stable_count}/{self.stable_count_required}")

                        # 检查是否达到稳定要求
                        if channel_state.stable_count >= self.stable_count_required:
                            # 状态变化确认
                            self._handle_stable_state_change(channel_num, channel_state, new_state, status_code)
                            delattr(channel_state, 'pending_state')
                            channel_state.stable_count = 0
                else:
                    # 状态没有变化，重置待确认状态
                    if hasattr(channel_state, 'pending_state'):
                        logger.debug(f"通道{channel_num}状态变化被取消，回到原状态: {channel_state.battery_state.value}")
                        delattr(channel_state, 'pending_state')
                        channel_state.stable_count = 0

                # 更新最后的状态码
                channel_state.last_status_code = status_code

        except Exception as e:
            logger.error(f"分析状态码变化失败: {e}")

    def _determine_battery_state_from_status(self, status_code: int) -> BatteryState:
        """
        根据状态码判断电池状态
        
        Args:
            status_code: 设备状态码
            
        Returns:
            电池状态
        """
        if self.status_manager.is_battery_error(status_code):
            # 0003H - 电池电压低或未安装
            return BatteryState.REMOVED
        elif status_code in [0x0000, 0x0001, 0x0006]:  # 空闲、测量中、测量完成
            # 正常状态，表示电池已连接
            return BatteryState.CONNECTED
        else:
            # 其他状态（硬件错误、设置错误等）
            return BatteryState.UNKNOWN

    def _handle_stable_state_change(self, channel_num: int, channel_state: ChannelDetectionState,
                                   new_state: BatteryState, status_code: int):
        """处理稳定的状态变化"""
        try:
            old_state = channel_state.battery_state

            # 更新状态
            channel_state.battery_state = new_state
            channel_state.state_change_time = datetime.now()

            logger.info(f"通道{channel_num}电池状态确认变化: {old_state.value} -> {new_state.value} (状态码: 0x{status_code:04X})")

            # 处理特定的状态变化
            if old_state == BatteryState.CONNECTED and new_state == BatteryState.REMOVED:
                # 电池被移除
                self._handle_battery_removed(channel_num, status_code)

            elif old_state == BatteryState.REMOVED and new_state == BatteryState.CONNECTED:
                # 检测到新电池插入
                self._handle_new_battery_detected(channel_num, status_code)

            elif old_state == BatteryState.UNKNOWN and new_state == BatteryState.CONNECTED:
                # 从未知状态变为连接状态（可能是新电池）
                self._handle_new_battery_detected(channel_num, status_code)

            # 通知状态更新
            if self.status_update_callback:
                try:
                    self.status_update_callback(channel_num, new_state.value, status_code)
                except Exception as e:
                    logger.error(f"状态更新回调失败: {e}")

        except Exception as e:
            logger.error(f"处理状态变化失败: {e}")

    def _handle_battery_removed(self, channel_num: int, status_code: int):
        """处理电池移除事件"""
        try:
            logger.info(f"🔋 通道{channel_num}检测到电池移除 (状态码: 0x{status_code:04X})")

            # 通知电池移除
            if self.battery_removed_callback:
                try:
                    # 传递状态码而不是电压
                    self.battery_removed_callback(channel_num, status_code)
                except Exception as e:
                    logger.error(f"电池移除回调失败: {e}")

        except Exception as e:
            logger.error(f"处理电池移除事件失败: {e}")

    def _handle_new_battery_detected(self, channel_num: int, status_code: int):
        """处理新电池检测事件"""
        try:
            logger.info(f"🔋 通道{channel_num}检测到新电池插入 (状态码: 0x{status_code:04X})")

            # 通知新电池检测
            if self.new_battery_detected_callback:
                try:
                    # 传递状态码而不是电压
                    self.new_battery_detected_callback(channel_num, status_code)
                except Exception as e:
                    logger.error(f"新电池检测回调失败: {e}")

        except Exception as e:
            logger.error(f"处理新电池检测事件失败: {e}")

    def get_detection_status(self) -> Dict[str, any]:
        """获取检测状态信息"""
        return {
            'is_detecting': self.is_detecting,
            'detection_interval': self.detection_interval,
            'stable_count_required': self.stable_count_required,
            'channels_count': len(self.channels),
            'channels_status': {
                ch_num: {
                    'state': ch_state.battery_state.value,
                    'last_status_code': f"0x{ch_state.last_status_code:04X}" if ch_state.last_status_code else None,
                    'stable_count': ch_state.stable_count
                }
                for ch_num, ch_state in self.channels.items()
            }
        }
