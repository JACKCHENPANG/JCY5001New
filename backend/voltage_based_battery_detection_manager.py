#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于电压的实时电池检测管理器
实现简化的单次检测逻辑，提高响应速度

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
    last_voltage: Optional[float] = None
    state_change_time: Optional[datetime] = None


class VoltageBasedBatteryDetectionManager:
    """基于电压的实时电池检测管理器"""
    
    def __init__(self, comm_manager, config_manager):
        """
        初始化电池检测管理器
        
        Args:
            comm_manager: 通信管理器
            config_manager: 配置管理器
        """
        self.comm_manager = comm_manager
        self.config_manager = config_manager
        
        # 检测状态
        self.is_detecting = False
        self.stop_event = threading.Event()
        self.detection_thread: Optional[threading.Thread] = None
        
        # 通道状态管理
        self.channels: Dict[int, ChannelDetectionState] = {}
        for i in range(1, 9):
            self.channels[i] = ChannelDetectionState(channel_number=i)
        
        # 检测参数 - 🔧 优化：提高检测频率，改为基于电压跳变的即时检测
        self.voltage_threshold_min = 2.0  # 最低正常电压
        self.voltage_threshold_max = 5.0  # 最高正常电压
        self.detection_interval = 0.5     # 检测间隔（秒）- 从1秒改为0.5秒，提高响应速度
        self.voltage_jump_threshold = 0.5  # 电压跳变阈值（V）- 新增：用于检测电压跳变
        
        # 回调函数
        self.battery_removed_callback: Optional[Callable] = None
        self.new_battery_detected_callback: Optional[Callable] = None
        self.status_update_callback: Optional[Callable] = None
        
        logger.debug("基于电压的实时电池检测管理器初始化完成")
    
    def set_callbacks(self, battery_removed_callback=None, new_battery_detected_callback=None, status_update_callback=None):
        """设置回调函数"""
        logger.info(f"🔧 [回调设置] 设置电池检测回调函数:")
        logger.info(f"  - battery_removed_callback: {battery_removed_callback}")
        logger.info(f"  - new_battery_detected_callback: {new_battery_detected_callback}")
        logger.info(f"  - status_update_callback: {status_update_callback}")

        self.battery_removed_callback = battery_removed_callback
        self.new_battery_detected_callback = new_battery_detected_callback
        self.status_update_callback = status_update_callback

        logger.info(f"✅ [回调设置] 回调函数设置完成，status_update_callback存在: {self.status_update_callback is not None}")
    
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
            
            logger.info(f"启动基于电压的实时电池侦测，监控通道: {enabled_channels}")
            
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
                    self.channels[channel_num].last_voltage = None
            
            # 启动侦测线程
            self.detection_thread = threading.Thread(
                target=self._detection_worker,
                args=(enabled_channels,),
                daemon=True,
                name="VoltageBasedBatteryDetection"
            )
            self.detection_thread.start()
            
            logger.info("✅ 基于电压的实时电池侦测已启动")
            
        except Exception as e:
            logger.error(f"启动电池侦测失败: {e}")
            self.is_detecting = False
    
    def stop_detection(self):
        """停止电池侦测"""
        try:
            if not self.is_detecting:
                logger.info("电池侦测未在运行")
                return
            
            logger.info("正在停止电池侦测...")
            
            # 设置停止标志
            self.stop_event.set()
            self.is_detecting = False
            
            # 等待线程结束
            if self.detection_thread and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=3.0)
                if self.detection_thread.is_alive():
                    logger.warning("电池侦测线程未能及时结束")
            
            logger.info("✅ 电池侦测已停止")
            
        except Exception as e:
            logger.error(f"停止电池侦测失败: {e}")
    
    def _detection_worker(self, enabled_channels: List[int]):
        """侦测工作线程"""
        try:
            logger.info(f"基于电压的实时电池侦测工作线程启动，监控通道: {enabled_channels}")
            
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
            
            logger.info("基于电压的实时电池侦测工作线程结束")
            
        except Exception as e:
            logger.error(f"电池侦测工作线程失败: {e}")
    
    def _read_channel_voltages(self, enabled_channels: List[int]) -> Dict[int, float]:
        """读取指定通道的电压"""
        try:
            voltages = {}
            
            # 检查通信管理器是否可用
            if not self.comm_manager or not self.comm_manager.is_connected:
                logger.warning("通信管理器未连接，跳过电压读取")
                return {}
            
            # 尝试群发读取所有电压
            try:
                all_voltages = self.comm_manager.read_battery_voltages()
                if all_voltages and len(all_voltages) >= 8:
                    for channel_num in enabled_channels:
                        if 1 <= channel_num <= 8:
                            voltage = all_voltages[channel_num - 1]
                            voltages[channel_num] = voltage
                    return voltages
            except Exception as e:
                logger.debug(f"群发读取电压失败，改为逐个读取: {e}")
            
            # 群发失败，逐个读取通道电压
            for channel_num in enabled_channels:
                try:
                    voltage = self.comm_manager.read_voltage(channel_num - 1)  # 转换为0基索引
                    if voltage is not None:
                        voltages[channel_num] = voltage
                    else:
                        logger.debug(f"通道{channel_num}电压读取失败(侦测模式)")
                except Exception as e:
                    logger.debug(f"通道{channel_num}电压读取异常(侦测模式): {e}")
            
            return voltages
            
        except Exception as e:
            logger.error(f"读取通道电压失败: {e}")
            return {}
    
    def _analyze_voltage_changes(self, voltages: Dict[int, float], enabled_channels: List[int]):
        """分析电压变化并更新电池状态（优化版：基于电压跳变的即时检测）"""
        try:
            for channel_num in enabled_channels:
                if channel_num not in voltages:
                    continue

                voltage = voltages[channel_num]
                channel_state = self.channels[channel_num]

                # 优化检测电压跳变，提高响应速度
                voltage_jump_detected = False
                if channel_state.last_voltage is not None:
                    voltage_diff = abs(voltage - channel_state.last_voltage)
                    if voltage_diff >= self.voltage_jump_threshold:
                        voltage_jump_detected = True
                        logger.debug(f"通道{channel_num}检测到电压跳变: {channel_state.last_voltage:.3f}V -> {voltage:.3f}V (差值: {voltage_diff:.3f}V)")

                # 根据当前电压直接判断状态（单次检测）
                new_state = self._determine_battery_state(voltage)
                old_state = channel_state.battery_state

                # 优化如果检测到电压跳变或状态变化，立即处理
                if new_state != old_state or voltage_jump_detected:
                    if new_state != old_state:
                        logger.info(f"通道{channel_num}电池状态变化: {old_state.value} -> {new_state.value} (电压: {voltage:.3f}V)")
                        self._handle_state_change(channel_num, channel_state, new_state, voltage)
                    elif voltage_jump_detected:
                        logger.debug(f"通道{channel_num}电压跳变但状态未变: {new_state.value} (电压: {voltage:.3f}V)")

                # 更新最后电压值
                channel_state.last_voltage = voltage

                # 修复只在状态变化或电压跳变时通知状态更新，避免频繁调用
                if (new_state != old_state or voltage_jump_detected):
                    logger.info(f"🔋 通知状态更新: 通道{channel_num} -> {new_state.value} ({voltage:.3f}V)")
                    if self.status_update_callback:
                        try:
                            logger.info(f"🔋 [回调调用] 调用status_update_callback: 通道{channel_num}, 状态={new_state.value}, 电压={voltage:.3f}V")
                            self.status_update_callback(channel_num, new_state.value, voltage)
                            logger.info(f"✅ [回调调用] status_update_callback调用成功")
                        except Exception as e:
                            logger.error(f"状态更新回调失败: {e}")
                            import traceback
                            logger.error(f"状态更新回调详细错误: {traceback.format_exc()}")
                    else:
                        logger.warning(f"⚠️ [回调调用] status_update_callback为None，无法调用")

        except Exception as e:
            logger.error(f"分析电压变化失败: {e}")
    
    def _determine_battery_state(self, voltage: float) -> BatteryState:
        """根据电压判断电池状态（新逻辑）"""
        if voltage < self.voltage_threshold_min:
            # 电压低于2V，判定为电池已移除
            return BatteryState.REMOVED
        elif self.voltage_threshold_min <= voltage <= self.voltage_threshold_max:
            # 电压在2V-5V范围内，判定为电池已连接
            return BatteryState.CONNECTED
        else:
            # 电压高于5V，判定为异常状态（可能是电池移除后的电压上升）
            return BatteryState.REMOVED

    def mark_test_completed(self, channel_num: int):
        """标记通道测试完成"""
        try:
            if channel_num in self.channels:
                # 为兼容性添加测试完成标记
                # 在基于电压的检测中，这主要用于状态同步
                logger.debug(f"通道{channel_num}测试已标记为完成")
            else:
                logger.warning(f"通道{channel_num}不在监控范围内")
        except Exception as e:
            logger.error(f"标记通道{channel_num}测试完成失败: {e}")

    def reset_channel_state(self, channel_num: int):
        """重置通道状态"""
        try:
            if channel_num in self.channels:
                channel_state = self.channels[channel_num]
                channel_state.battery_state = BatteryState.UNKNOWN
                channel_state.last_voltage = None
                logger.debug(f"通道{channel_num}状态已重置")
            else:
                logger.warning(f"通道{channel_num}不在监控范围内")
        except Exception as e:
            logger.error(f"重置通道{channel_num}状态失败: {e}")
    
    def _handle_state_change(self, channel_num: int, channel_state: ChannelDetectionState,
                           new_state: BatteryState, voltage: float):
        """处理状态变化（简化版：立即处理）"""
        try:
            old_state = channel_state.battery_state
            
            # 更新状态
            channel_state.battery_state = new_state
            channel_state.state_change_time = datetime.now()

            logger.info(f"🔋 通道{channel_num}状态已更新: {old_state.value} -> {new_state.value} (电压: {voltage:.3f}V)")

            # 处理特定的状态变化
            if old_state == BatteryState.CONNECTED and new_state == BatteryState.REMOVED:
                # 电池被移除
                logger.info(f"🔋 处理电池移除: 通道{channel_num}")
                self._handle_battery_removed(channel_num, voltage)

            elif old_state == BatteryState.REMOVED and new_state == BatteryState.CONNECTED:
                # 检测到新电池插入
                logger.info(f"🔋 处理新电池插入: 通道{channel_num}")
                self._handle_new_battery_detected(channel_num, voltage)

            elif old_state == BatteryState.UNKNOWN and new_state == BatteryState.CONNECTED:
                # 从未知状态变为连接状态（可能是新电池）
                logger.info(f"🔋 处理未知->连接状态变化: 通道{channel_num}")
                self._handle_new_battery_detected(channel_num, voltage)
                
        except Exception as e:
            logger.error(f"处理状态变化失败: {e}")
    
    def _handle_battery_removed(self, channel_num: int, voltage: float):
        """处理电池移除事件"""
        try:
            logger.info(f"🔋 通道{channel_num}检测到电池移除 (电压: {voltage:.3f}V)")
            
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
            logger.info(f"🔋 通道{channel_num}检测到新电池插入 (电压: {voltage:.3f}V)")
            
            # 通知新电池检测
            if self.new_battery_detected_callback:
                try:
                    self.new_battery_detected_callback(channel_num, voltage)
                except Exception as e:
                    logger.error(f"新电池检测回调失败: {e}")
                    
        except Exception as e:
            logger.error(f"处理新电池检测事件失败: {e}")
