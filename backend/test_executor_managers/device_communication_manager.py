# -*- coding: utf-8 -*-
"""
设备通信管理器
负责与测试设备的通信、命令发送、数据读取等功能

Author: Jack
Date: 2025-06-27
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class DeviceCommunicationManager(QObject):
    """设备通信管理器"""
    
    # 信号定义
    command_sent = pyqtSignal(str, dict)  # 命令发送信号 (command, params)
    data_received = pyqtSignal(dict)  # 数据接收信号 (data)
    communication_error = pyqtSignal(str)  # 通信错误信号 (error_message)
    measurement_completed = pyqtSignal(list, float)  # 测量完成信号 (channels, frequency)
    
    def __init__(self, comm_manager, device_config_manager, parent=None):
        """
        初始化设备通信管理器
        
        Args:
            comm_manager: 通信管理器
            device_config_manager: 设备配置管理器
            parent: 父对象
        """
        super().__init__(parent)
        
        self.comm_manager = comm_manager
        self.device_config_manager = device_config_manager
        
        # 通信状态
        self.is_connected = False
        self.last_command_time = 0
        self.command_timeout = 30.0  # 命令超时时间（秒）
        
    def prepare_test_environment(self, test_config: Dict[str, Any]) -> bool:
        """
        准备测试环境
        
        Args:
            test_config: 测试配置
            
        Returns:
            是否准备成功
        """
        try:
            
            # 检查设备连接
            if not self._check_device_connection():
                logger.error("设备未连接，无法准备测试环境")
                return False
            
            # 配置测试参数
            if not self._configure_test_parameters(test_config):
                logger.error("配置测试参数失败")
                return False
            
            # 初始化测试通道
            enabled_channels = test_config.get('enabled_channels', [])
            if not self._initialize_test_channels(enabled_channels):
                logger.error("初始化测试通道失败")
                return False
            
            logger.info("✅ 测试环境准备完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 准备测试环境失败: {e}")
            return False



    def _check_device_connection(self) -> bool:
        """检查设备连接状态"""
        try:
            if not self.comm_manager:
                logger.error("通信管理器未初始化")
                return False
            
            # 检查串口连接
            if not self.comm_manager.is_connected:
                logger.error("串口未连接")
                return False
            
            # 发送设备状态查询命令
            response = self.comm_manager.send_command("STATUS")
            if not response or response.get('success') != True:
                logger.error("设备状态查询失败")
                return False
            
            self.is_connected = True
            logger.debug("设备连接正常")
            return True
            
        except Exception as e:
            logger.error(f"检查设备连接失败: {e}")
            return False

    def _configure_test_parameters(self, test_config: Dict[str, Any]) -> bool:
        """配置测试参数"""
        try:
            logger.debug("配置测试参数")
            
            # 配置测试模式
            test_mode = test_config.get('test_mode', 'impedance')
            if not self._send_device_command("SET_MODE", {'mode': test_mode}):
                return False
            
            # 配置测试范围
            test_range = test_config.get('test_range', 'auto')
            if not self._send_device_command("SET_RANGE", {'range': test_range}):
                return False
            
            # 配置采样参数
            sampling_config = test_config.get('sampling', {})
            if sampling_config:
                if not self._send_device_command("SET_SAMPLING", sampling_config):
                    return False
            
            logger.debug("测试参数配置完成")
            return True
            
        except Exception as e:
            logger.error(f"配置测试参数失败: {e}")
            return False

    def _initialize_test_channels(self, enabled_channels: List[int]) -> bool:
        """初始化测试通道"""
        try:
            logger.debug(f"初始化测试通道: {enabled_channels}")
            
            # 禁用所有通道
            if not self._send_device_command("DISABLE_ALL_CHANNELS"):
                return False
            
            # 启用指定通道
            for channel_num in enabled_channels:
                if not self._send_device_command("ENABLE_CHANNEL", {'channel': channel_num}):
                    logger.error(f"启用通道{channel_num}失败")
                    return False
            
            logger.debug("测试通道初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化测试通道失败: {e}")
            return False

    def _set_test_frequency(self, frequency: float) -> bool:
        """设置测试频率"""
        try:
            logger.debug(f"设置测试频率: {frequency}Hz")
            
            response = self._send_device_command("SET_FREQUENCY", {'frequency': frequency})
            if not response:
                return False
            
            # 等待频率设置稳定
            time.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"设置测试频率失败: {e}")
            return False

    def _start_frequency_test(self, enabled_channels: List[int]) -> bool:
        """启动频点测试"""
        try:
            logger.debug(f"启动频点测试，通道: {enabled_channels}")
            
            # 发送启动测试命令
            response = self._send_device_command("START_TEST", {'channels': enabled_channels})
            if not response:
                return False
            
            # 记录测试启动时间
            self.last_command_time = time.time()
            
            return True
            
        except Exception as e:
            logger.error(f"启动频点测试失败: {e}")
            return False

    def _wait_for_measurement_completion(self, channel_indices: List[int], frequency: float) -> bool:
        """
        等待测量完成（智能超时优化版本）
        
        Args:
            channel_indices: 通道索引列表
            frequency: 测试频率
            
        Returns:
            是否测量完成
        """
        try:
            logger.debug(f"等待测量完成: 频率{frequency}Hz, 通道{channel_indices}")
            
            # 根据频率计算超时时间
            base_timeout = self._calculate_frequency_timeout(frequency)
            channel_count = len(channel_indices)
            total_timeout = base_timeout * max(1, channel_count / 4)  # 多通道适当延长
            
            start_time = time.time()
            check_interval = 0.5  # 检查间隔
            
            while time.time() - start_time < total_timeout:
                # 检查测量状态
                if self._check_measurement_status(channel_indices):
                    logger.debug(f"测量完成，耗时: {time.time() - start_time:.2f}秒")
                    
                    # 发送测量完成信号
                    self.measurement_completed.emit(channel_indices, frequency)
                    return True
                
                # 短暂等待
                time.sleep(check_interval)
            
            # 超时
            logger.warning(f"测量超时: 频率{frequency}Hz, 超时时间{total_timeout:.1f}秒")
            return False
            
        except Exception as e:
            logger.error(f"等待测量完成失败: {e}")
            return False

    def _calculate_frequency_timeout(self, frequency: float) -> float:
        """根据频率计算超时时间"""
        try:
            if frequency <= 0.1:
                return 30.0  # 低频需要更长时间
            elif frequency <= 1.0:
                return 20.0
            elif frequency <= 10.0:
                return 15.0
            elif frequency <= 100.0:
                return 10.0
            else:
                return 8.0   # 高频测试较快
        except Exception:
            return 15.0  # 默认超时时间

    def _check_measurement_status(self, channel_indices: List[int]) -> bool:
        """检查测量状态"""
        try:
            # 查询设备状态
            response = self._send_device_command("GET_STATUS")
            if not response:
                return False
            
            status_data = response.get('data', {})
            
            # 检查所有通道是否完成测量
            for channel_idx in channel_indices:
                channel_status = status_data.get(f'channel_{channel_idx + 1}', {})
                if not channel_status.get('measurement_complete', False):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查测量状态失败: {e}")
            return False

    def _read_test_results(self, enabled_channels: List[int], frequency: float) -> bool:
        """读取测试结果"""
        try:
            logger.debug(f"读取测试结果: 频率{frequency}Hz, 通道{enabled_channels}")
            
            for channel_num in enabled_channels:
                # 读取通道数据
                response = self._send_device_command("READ_CHANNEL", {'channel': channel_num})
                if not response:
                    logger.error(f"读取通道{channel_num}数据失败")
                    continue
                
                # 处理通道数据
                channel_data = response.get('data', {})
                self._process_channel_data(channel_num, frequency, channel_data)
            
            return True
            
        except Exception as e:
            logger.error(f"读取测试结果失败: {e}")
            return False

    def _process_channel_data(self, channel_num: int, frequency: float, channel_data: Dict[str, Any]):
        """处理通道数据"""
        try:
            # 提取测量数据
            voltage = channel_data.get('voltage', 0.0)
            impedance = channel_data.get('impedance', 0.0)
            phase = channel_data.get('phase', 0.0)
            
            # 更新设备配置管理器中的数据
            self.device_config_manager.update_channel_data(channel_num, {
                'frequency': frequency,
                'voltage': voltage,
                'impedance': impedance,
                'phase': phase,
                'timestamp': time.time()
            })
            
            # 发送数据接收信号
            self.data_received.emit({
                'channel': channel_num,
                'frequency': frequency,
                'data': channel_data
            })
            
            logger.debug(f"通道{channel_num}数据处理完成: V={voltage:.3f}V, Z={impedance:.3f}Ω")
            
        except Exception as e:
            logger.error(f"处理通道{channel_num}数据失败: {e}")

    def _send_device_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        发送设备命令
        
        Args:
            command: 命令名称
            params: 命令参数
            
        Returns:
            命令响应
        """
        try:
            if not self.comm_manager:
                logger.error("通信管理器未初始化")
                return None
            
            # 发送命令
            response = self.comm_manager.send_command(command, params or {})
            
            # 发送命令信号
            self.command_sent.emit(command, params or {})
            
            if not response or not response.get('success'):
                error_msg = response.get('error', '未知错误') if response else '无响应'
                logger.error(f"设备命令失败: {command}, 错误: {error_msg}")
                self.communication_error.emit(f"命令失败: {command} - {error_msg}")
                return None
            
            return response
            
        except Exception as e:
            logger.error(f"发送设备命令失败: {command}, 错误: {e}")
            self.communication_error.emit(f"通信异常: {command} - {str(e)}")
            return None

    def stop_device_test(self) -> bool:
        """停止设备测试"""
        try:
            logger.info("🛑 停止设备测试")
            
            # 发送停止命令
            response = self._send_device_command("STOP_TEST")
            if not response:
                logger.error("发送停止命令失败")
                return False
            
            # 等待设备响应
            time.sleep(0.5)
            
            logger.info("✅ 设备测试已停止")
            return True
            
        except Exception as e:
            logger.error(f"❌ 停止设备测试失败: {e}")
            return False

    def get_communication_status(self) -> Dict[str, Any]:
        """获取通信状态"""
        try:
            return {
                'is_connected': self.is_connected,
                'last_command_time': self.last_command_time,
                'command_timeout': self.command_timeout,
                'comm_manager_available': self.comm_manager is not None,
                'device_config_manager_available': self.device_config_manager is not None,
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"获取通信状态失败: {e}")
            return {}

    def cleanup(self):
        """清理资源"""
        try:
            # 停止设备测试
            self.stop_device_test()
            
            # 重置状态
            self.is_connected = False
            self.last_command_time = 0
            
            logger.debug("设备通信管理器资源已清理")
            
        except Exception as e:
            logger.error(f"清理设备通信管理器资源失败: {e}")
