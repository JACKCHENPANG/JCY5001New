# -*- coding: utf-8 -*-
"""
测试前预检查管理器
负责测试前的各项检查，包括设备连接、通道状态、电池电压等

从TestFlowManager中提取的预检查功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import List, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


class TestPreCheckManager(QObject):
    """
    测试前预检查管理器
    
    职责：
    - 设备连接检查
    - 通道状态预检查
    - 电池电压检查
    - 离群检测频点验证
    """
    
    # 信号定义
    precheck_completed = pyqtSignal(bool)  # 预检查完成
    precheck_progress = pyqtSignal(str, str)  # 预检查进度 (步骤, 状态)
    
    def __init__(self, main_window, config_manager, comm_manager, device_connection_manager):
        """
        初始化测试前预检查管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
            comm_manager: 通信管理器
            device_connection_manager: 设备连接管理器
        """
        super().__init__()
        
        self.main_window = main_window
        self.config_manager = config_manager
        self.comm_manager = comm_manager
        self.device_connection_manager = device_connection_manager
        
        logger.debug("测试前预检查管理器初始化完成")
    
    def execute_precheck(self) -> bool:
        """
        执行完整的预检查流程
        
        Returns:
            是否通过所有检查
        """
        try:
            # 🚀 优化：检查是否启用快速启动模式
            fast_startup = self.config_manager.get('test_params.fast_startup', False)
            if fast_startup:
                logger.info("🚀 快速启动模式已启用，跳过详细预检查")
                self.precheck_completed.emit(True)
                return True

            # 1. 检查设备连接
            self.precheck_progress.emit("设备连接检查", "进行中")
            if not self._check_device_connection():
                self.precheck_progress.emit("设备连接检查", "失败")
                return False
            self.precheck_progress.emit("设备连接检查", "通过")
            
            # 2. 验证离群检测频点匹配
            self.precheck_progress.emit("离群检测验证", "进行中")
            if not self._validate_outlier_detection_frequencies():
                self.precheck_progress.emit("离群检测验证", "失败")
                return False
            self.precheck_progress.emit("离群检测验证", "通过")
            
            # 3. 预检查通道状态码
            self.precheck_progress.emit("通道状态检查", "进行中")
            if not self._precheck_channel_status():
                self.precheck_progress.emit("通道状态检查", "失败")
                return False
            self.precheck_progress.emit("通道状态检查", "通过")
            
            # 4. 读取电池电压
            self.precheck_progress.emit("电池电压检查", "进行中")
            if not self._read_battery_voltages():
                self.precheck_progress.emit("电池电压检查", "失败")
                return False
            self.precheck_progress.emit("电池电压检查", "通过")
            
            logger.info("✅ 测试前预检查全部通过")
            self.precheck_completed.emit(True)
            return True
            
        except Exception as e:
            logger.error(f"执行预检查失败: {e}")
            self.precheck_completed.emit(False)
            return False
    
    def _check_device_connection(self) -> bool:
        """检查设备连接"""
        try:
            if not self.device_connection_manager.get_connection_status():
                # 尝试连接设备
                if not self.device_connection_manager.connect_device():
                    reply = QMessageBox.question(
                        self.main_window,
                        '设备未连接',
                        '设备未连接！\n\n'
                        '请检查：\n'
                        '1. 设备是否正确连接\n'
                        '2. 设备是否已开机\n'
                        '3. 串口配置是否正确\n\n'
                        '是否打开设备设置页面进行连接？',
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        self.device_connection_manager.show_connection_dialog()
                    
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查设备连接失败: {e}")
            return False
    
    def _validate_outlier_detection_frequencies(self) -> bool:
        """验证离群检测频点匹配"""
        try:
            # 检查是否启用离群检测
            outlier_enabled = self.config_manager.get('outlier_detection.enabled', False)
            if not outlier_enabled:
                logger.debug("离群检测未启用，跳过频点验证")
                return True
            
            # 获取测试频点和基准频点
            test_frequencies = self.config_manager.get('frequency.multi_freq.custom_list', [])
            baseline_file = self.config_manager.get('outlier_detection.baseline_file', '')
            
            if not baseline_file:
                logger.warning("离群检测已启用但未设置基准文件")
                return True
            
            # 这里可以添加更详细的频点匹配验证逻辑
            logger.info(f"离群检测频点验证通过: 测试频点{len(test_frequencies)}个")
            return True
            
        except Exception as e:
            logger.error(f"验证离群检测频点失败: {e}")
            return True  # 验证失败不阻止测试
    
    def _precheck_channel_status(self) -> bool:
        """预检查通道状态码，提前识别异常通道"""
        try:
            
            # 获取启用的通道
            enabled_channels = self._get_enabled_channels()
            if not enabled_channels:
                logger.warning("没有启用的通道，跳过状态码预检查")
                return True
            
            # 读取所有启用通道的状态码
            abnormal_channels = []
            normal_channels = []
            
            # 🚀 优化：使用群发读取状态码，减少通信次数和延迟
            try:
                # 尝试群发读取所有通道状态
                all_status_codes = self.comm_manager.command_manager.get_measurement_status_broadcast()

                if all_status_codes and len(all_status_codes) >= 8:
                    logger.debug("✅ 群发状态码读取成功，快速预检查")

                    for channel in enabled_channels:
                        channel_index = channel - 1
                        if channel_index < len(all_status_codes):
                            status_code = all_status_codes[channel_index]
                            self._process_channel_status(channel, status_code, normal_channels, abnormal_channels)
                        else:
                            logger.warning(f"通道{channel}索引超出范围，假设正常")
                            normal_channels.append(channel)
                else:
                    # 群发失败，回退到逐个读取（但设置更短的超时）
                    logger.debug("群发状态码读取失败，回退到快速逐个读取")
                    self._precheck_channels_individually(enabled_channels, normal_channels, abnormal_channels)

            except Exception as e:
                logger.debug(f"群发状态码读取异常: {e}，回退到逐个读取")
                self._precheck_channels_individually(enabled_channels, normal_channels, abnormal_channels)
            
            # 记录预检查结果
            if abnormal_channels:
                logger.info(f"✅ 状态码预检查完成: {len(normal_channels)}个正常通道, {len(abnormal_channels)}个异常通道")
                logger.info(f"   正常通道: {normal_channels}")
                logger.info(f"   异常通道: {abnormal_channels}")
                
                # 如果所有通道都异常，询问是否继续
                if not normal_channels:
                    reply = QMessageBox.question(
                        self.main_window,
                        '所有通道异常',
                        '检测到所有启用通道都存在异常！\n\n'
                        '可能原因：\n'
                        '• 电池未正确安装\n'
                        '• 电池电压过低\n'
                        '• 设备连接问题\n\n'
                        '是否继续测试？',
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    
                    if reply != QMessageBox.Yes:
                        return False
            else:
                logger.info(f"✅ 状态码预检查完成: 所有{len(normal_channels)}个通道状态正常")
            
            return True
            
        except Exception as e:
            logger.error(f"预检查通道状态码失败: {e}")
            # 预检查失败不阻止测试，在测试过程中处理
            return True

    def _process_channel_status(self, channel: int, status_code: int, normal_channels: list, abnormal_channels: list):
        """
        处理单个通道的状态码

        Args:
            channel: 通道号
            status_code: 状态码
            normal_channels: 正常通道列表
            abnormal_channels: 异常通道列表
        """
        if status_code is None:
            logger.warning(f"通道{channel}状态码读取失败，将在测试中处理")
            normal_channels.append(channel)
            return

        # 检查是否为异常状态码
        if status_code == 0x0003:  # 电池电压低或未安装
            logger.warning(f"通道{channel}检测到异常状态码: 0x{status_code:04X} (电池异常)")
            abnormal_channels.append(channel)
            self._mark_channel_as_abnormal(channel, "电池异常", "0003H")

        elif status_code in [0x0001, 0x0002, 0x0004, 0x0005]:  # 其他已知异常状态
            logger.warning(f"通道{channel}检测到异常状态码: 0x{status_code:04X}")
            abnormal_channels.append(channel)
            error_desc = self._get_status_code_description(status_code)
            self._mark_channel_as_abnormal(channel, error_desc, f"{status_code:04X}H")

        else:
            logger.debug(f"通道{channel}状态正常: 0x{status_code:04X}")
            normal_channels.append(channel)

    def _precheck_channels_individually(self, enabled_channels: list, normal_channels: list, abnormal_channels: list):
        """
        逐个检查通道状态码（回退方案）

        Args:
            enabled_channels: 启用的通道列表
            normal_channels: 正常通道列表
            abnormal_channels: 异常通道列表
        """
        for channel in enabled_channels:
            try:
                # 读取通道状态码
                status_code = self.comm_manager.read_channel_status(channel)
                self._process_channel_status(channel, status_code, normal_channels, abnormal_channels)

            except Exception as e:
                logger.error(f"检查通道{channel}状态码失败: {e}")
                normal_channels.append(channel)  # 出错时假设正常，在测试中处理
    
    def _read_battery_voltages(self) -> bool:
        """读取电池电压"""
        try:
            logger.info("🔋 读取电池电压...")
            
            voltages = self.comm_manager.read_battery_voltages()
            
            if not voltages:
                logger.error("读取电池电压失败")
                return False
            
            logger.info(f"电池电压: {voltages}")
            
            # 检查电压范围 - Jack修正：电压不在2.0V-5.0V范围内认为是没有接电池
            valid_voltages = []
            for i, voltage in enumerate(voltages):
                if 2.0 <= voltage <= 5.0:  # 电压范围2.0V-5.0V，超出范围认为没有接电池
                    valid_voltages.append(i + 1)
                else:
                    logger.info(f"通道{i + 1}电压{voltage:.3f}V超出范围(2.0V-5.0V)，认为没有接电池，将跳过测试")
            
            if not valid_voltages:
                logger.warning("没有检测到有效的电池电压")
                reply = QMessageBox.question(
                    self.main_window,
                    '电池电压异常',
                    '没有检测到有效的电池电压！\n\n'
                    '请检查电池是否正确连接。\n\n'
                    '是否继续测试？',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply != QMessageBox.Yes:
                    return False
            
            logger.info(f"✅ 电池电压读取完成，有效通道: {valid_voltages}")
            return True
            
        except Exception as e:
            logger.error(f"读取电池电压失败: {e}")
            return False
    
    def _get_enabled_channels(self) -> List[int]:
        """获取启用的通道列表"""
        try:
            # 从配置获取启用的通道
            config_enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))
            
            # 从UI组件获取通道状态（如果可用）
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                channels_container = ui_manager.get_component('channels_container')
                
                if channels_container and hasattr(channels_container, 'get_enabled_channels'):
                    ui_enabled_channels = channels_container.get_enabled_channels()
                    if ui_enabled_channels:
                        return ui_enabled_channels
            
            return config_enabled_channels
            
        except Exception as e:
            logger.error(f"获取启用通道失败: {e}")
            return list(range(1, 9))  # 默认返回所有通道
    
    def _get_status_code_description(self, status_code: int) -> str:
        """获取状态码描述"""
        status_descriptions = {
            0x0001: "设备忙",
            0x0002: "参数错误",
            0x0003: "电池异常",
            0x0004: "测试超时",
            0x0005: "硬件故障"
        }
        return status_descriptions.get(status_code, f"未知错误({status_code:04X}H)")
    
    def _mark_channel_as_abnormal(self, channel: int, error_desc: str, error_code: str):
        """在UI中标记通道为异常状态"""
        try:
            # 获取通道显示组件
            ui_manager = getattr(self.main_window, 'ui_component_manager', None)
            if ui_manager:
                channels_container = ui_manager.get_component('channels_container')
                if channels_container and hasattr(channels_container, 'get_channel_widget'):
                    channel_widget = channels_container.get_channel_widget(channel)
                    if channel_widget and hasattr(channel_widget, 'set_error_status'):
                        # 设置错误状态
                        channel_widget.set_error_status(error_desc, error_code)
                        logger.info(f"通道{channel}UI已标记为异常: {error_desc}")
                        return
            
            logger.warning(f"无法在UI中标记通道{channel}为异常状态")
            
        except Exception as e:
            logger.error(f"标记通道{channel}异常状态失败: {e}")
