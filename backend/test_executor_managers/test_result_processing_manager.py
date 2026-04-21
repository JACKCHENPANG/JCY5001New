# -*- coding: utf-8 -*-
"""
测试结果处理管理器
负责测试结果的收集、处理、分析和回调发送等功能

Author: Jack
Date: 2025-06-27
"""

import logging
import time
import hashlib
from typing import Dict, Any, List, Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class TestResultProcessingManager(QObject):
    """测试结果处理管理器"""
    
    # 信号定义
    results_collected = pyqtSignal(list, dict)  # 结果收集完成信号 (channels, results)
    results_processed = pyqtSignal(dict)  # 结果处理完成信号 (processed_results)
    callback_sent = pyqtSignal(int, dict)  # 回调发送信号 (channel, callback_data)
    
    def __init__(self, comm_manager, device_config_manager, test_result_manager=None, config_manager=None, parent=None):
        """
        初始化测试结果处理管理器

        Args:
            comm_manager: 通信管理器
            device_config_manager: 设备配置管理器
            test_result_manager: 测试结果管理器
            config_manager: 配置管理器
            parent: 父对象
        """
        super().__init__(parent)

        self.comm_manager = comm_manager
        self.device_config_manager = device_config_manager
        self.test_result_manager = test_result_manager  # 添加测试结果管理器引用
        self.config_manager = config_manager  # 添加配置管理器引用

        # 回调去重
        self._sent_callbacks = set()

        # 回调函数
        self.progress_callback = None
        
    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback

    def collect_cycle_test_results(self, enabled_channels: List[int]) -> Dict[str, Any]:
        """
        收集本轮测试结果数据
        
        Args:
            enabled_channels: 启用的通道列表
            
        Returns:
            收集的测试结果字典
        """
        try:
            
            results = {}
            
            for channel_num in enabled_channels:
                try:
                    # 修复从测试结果管理器获取通道数据
                    channel_data = self._get_channel_test_data_from_result_manager(channel_num)

                    if channel_data:
                        results[channel_num] = {
                            'voltage': channel_data.get('voltage', 0.0),
                            'rs_value': channel_data.get('rs_value', 0.0),
                            'rct_value': channel_data.get('rct_value', 0.0),
                            'rsei_value': channel_data.get('rsei_value', 0.0),  # 添加Rsei值
                            'impedance_data': channel_data.get('impedance_data', {}),
                            'frequency_data': channel_data.get('frequency_data', {}),
                            'test_progress': channel_data.get('test_progress', 100),
                            'collection_time': time.time()
                        }

                        logger.debug(f"通道{channel_num}结果收集完成: V={channel_data.get('voltage', 0):.3f}V, "
                                   f"Rs={channel_data.get('rs_value', 0):.3f}mΩ, Rct={channel_data.get('rct_value', 0):.3f}mΩ, "
                                   f"Rsei={channel_data.get('rsei_value', 0):.3f}mΩ")
                    else:
                        logger.warning(f"通道{channel_num}无测试数据")
                        results[channel_num] = self._create_empty_result()
                        
                except Exception as e:
                    logger.error(f"收集通道{channel_num}结果失败: {e}")
                    results[channel_num] = self._create_empty_result()
            
            # 发送结果收集完成信号
            self.results_collected.emit(enabled_channels, results)
            
            logger.info(f"✅ 测试结果收集完成，共{len(results)}个通道")
            return results
            
        except Exception as e:
            logger.error(f"❌ 收集测试结果失败: {e}")
            return {}

    def process_test_completion(self, channel_indices: List[int], test_config: Dict[str, Any]):
        """
        处理测试完成后的EIS分析和结果显示（修复版）

        Args:
            channel_indices: 通道索引列表
            test_config: 测试配置
        """
        try:
            logger.info(f"🔬 处理测试完成，通道: {channel_indices}")

            # 🎯 检查是否为取样测试模式
            sampling_test = False
            if hasattr(self, 'config_manager'):
                sampling_test = self.config_manager.get('test.sampling_test', False)
                if sampling_test:
                    logger.info("🎯 取样测试模式：执行数据处理，跳过UI回调")

            processed_results = {}

            for channel_idx in channel_indices:
                channel_num = channel_idx + 1  # 转换为通道号
                
                try:
                    # 修复从测试结果管理器获取通道测试数据
                    channel_data = self._get_channel_test_data_from_result_manager(channel_num)

                    if not channel_data:
                        logger.warning(f"通道{channel_num}无测试数据，跳过处理")
                        continue
                    
                    # 执行EIS分析
                    eis_result = self._perform_eis_analysis(channel_num, channel_data, test_config)
                    
                    # 处理结果数据
                    result_data = self._process_channel_result(channel_num, channel_data, eis_result, test_config)

                    processed_results[channel_num] = result_data

                    # 修复采样测试模式下也需要发送UI回调，确保通道完成状态能被正确检测
                    if not sampling_test:
                        # 发送进度回调（带去重检查）
                        self._send_callback_with_dedup(channel_num, result_data)
                    else:
                        logger.info(f"🎯 通道{channel_num}取样测试模式：发送UI回调确保完成状态检测")
                        # 修复采样测试模式下也发送回调，确保通道能正确设置完成状态
                        self._send_callback_with_dedup(channel_num, result_data)

                    logger.debug(f"通道{channel_num}测试完成处理完成")
                    
                except Exception as e:
                    logger.error(f"处理通道{channel_num}测试完成失败: {e}")
            
            # 🎯 取样测试模式：跳过结果处理完成信号，但返回处理结果
            if not sampling_test:
                # 发送结果处理完成信号
                self.results_processed.emit(processed_results)
            else:
                logger.info("🎯 取样测试模式：跳过结果处理完成信号")

            logger.info(f"✅ 测试完成处理完成，共处理{len(processed_results)}个通道")

            # 🎯 返回处理结果供取样测试使用
            return processed_results
            
        except Exception as e:
            logger.error(f"❌ 处理测试完成失败: {e}")

    def _perform_eis_analysis(self, channel_num: int, channel_data: Dict[str, Any], test_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行EIS分析
        
        Args:
            channel_num: 通道号
            channel_data: 通道数据
            test_config: 测试配置
            
        Returns:
            EIS分析结果
        """
        try:
            # 获取阻抗数据
            impedance_data = channel_data.get('impedance_data', {})
            
            if not impedance_data:
                logger.warning(f"通道{channel_num}无阻抗数据，跳过EIS分析")
                return {}
            
            # 简化算法：直接使用标准EIS分析器，确保算法一致性
            from backend.eis_analyzer import EISAnalyzer

            # 创建标准EIS分析器
            eis_analyzer = EISAnalyzer()

            # 执行分析（使用标准算法）
            frequencies = impedance_data.get('frequencies', [])
            real_parts = impedance_data.get('real_parts', [])
            imag_parts = impedance_data.get('imag_parts', [])

            if frequencies and real_parts and imag_parts:
                cell_id = f"CH_{channel_num}"
                analysis_result = eis_analyzer.calculate_rs_rct_enhanced(
                    frequencies, real_parts, imag_parts, cell_id
                )
            else:
                logger.warning(f"通道{channel_num}阻抗数据不完整，跳过EIS分析")
                analysis_result = {}
            
            logger.debug(f"通道{channel_num}EIS分析完成")
            return analysis_result
            
        except Exception as e:
            logger.error(f"通道{channel_num}EIS分析失败: {e}")
            return {}

    def _process_channel_result(self, channel_num: int, channel_data: Dict[str, Any], 
                               eis_result: Dict[str, Any], test_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理通道结果数据
        
        Args:
            channel_num: 通道号
            channel_data: 通道数据
            eis_result: EIS分析结果
            test_config: 测试配置
            
        Returns:
            处理后的结果数据
        """
        try:
            # 基础测试数据
            result_data = {
                'channel_number': channel_num,
                'voltage': channel_data.get('voltage', 0.0),
                'rs_value': channel_data.get('rs_value', 0.0),
                'rct_value': channel_data.get('rct_value', 0.0),
                'rsei_value': channel_data.get('rsei_value', 0.0),  # 添加Rsei值
                'test_progress': 100,  # 测试完成
                'timestamp': time.time()
            }
            
            # 添加EIS分析结果
            if eis_result:
                result_data.update({
                    'eis_analysis': eis_result,
                    'fitted_rs': eis_result.get('fitted_rs', result_data['rs_value']),
                    'fitted_rct': eis_result.get('fitted_rct', result_data['rct_value']),
                    'fit_quality': eis_result.get('fit_quality', 0.0)
                })
            
            # 添加频率数据
            frequency_data = channel_data.get('frequency_data', {})
            if frequency_data:
                result_data['frequency_data'] = frequency_data
            
            # 添加阻抗数据
            impedance_data = channel_data.get('impedance_data', {})
            if impedance_data:
                result_data['impedance_data'] = impedance_data

            # 移除重复的打印触发，避免重复打印（打印由test_result_manager统一处理）
            # self._trigger_auto_print_for_channel(channel_num, result_data)

            return result_data
            
        except Exception as e:
            logger.error(f"处理通道{channel_num}结果数据失败: {e}")
            return self._create_empty_result(channel_num)

    def _send_callback_with_dedup(self, channel_num: int, callback_data: dict):
        """
        发送带去重检查的回调
        
        Args:
            channel_num: 通道号
            callback_data: 回调数据
        """
        try:
            # 生成回调ID用于去重
            callback_id = self._generate_callback_id(channel_num, callback_data)
            
            # 检查是否已经发送过
            if self._is_callback_already_sent(callback_id):
                logger.debug(f"通道{channel_num}回调已发送过，跳过重复发送")
                return
            
            # 发送回调
            if self.progress_callback:
                self.progress_callback(channel_num, callback_data)
                
                # 记录已发送的回调
                self._sent_callbacks.add(callback_id)
                
                # 发送回调信号
                self.callback_sent.emit(channel_num, callback_data)
                
                logger.debug(f"通道{channel_num}回调发送成功")
            
        except Exception as e:
            logger.error(f"发送通道{channel_num}回调失败: {e}")

    def _generate_callback_id(self, channel_num: int, callback_data: dict) -> str:
        """
        生成回调ID用于去重
        
        Args:
            channel_num: 通道号
            callback_data: 回调数据
            
        Returns:
            回调ID
        """
        try:
            # 提取关键数据用于生成ID
            key_data = {
                'channel': channel_num,
                'voltage': callback_data.get('voltage', 0),
                'rs_value': callback_data.get('rs_value', 0),
                'rct_value': callback_data.get('rct_value', 0),
                'progress': callback_data.get('test_progress', 0)
            }
            
            # 生成哈希ID
            data_str = str(sorted(key_data.items()))
            callback_id = hashlib.md5(data_str.encode()).hexdigest()[:16]
            
            return f"{channel_num}_{callback_id}"
            
        except Exception as e:
            logger.error(f"生成回调ID失败: {e}")
            return f"{channel_num}_{int(time.time())}"

    def _is_callback_already_sent(self, callback_id: str) -> bool:
        """
        检查回调是否已经发送过
        
        Args:
            callback_id: 回调ID
            
        Returns:
            是否已发送
        """
        return callback_id in self._sent_callbacks

    def _create_empty_result(self, channel_num: Optional[int] = None) -> Dict[str, Any]:
        """创建空的结果数据"""
        return {
            'channel_number': channel_num,
            'voltage': 0.0,
            'rs_value': 0.0,
            'rct_value': 0.0,
            'rsei_value': 0.0,  # 添加Rsei值
            'test_progress': 0,
            'timestamp': time.time(),
            'error': True
        }

    def _get_channel_test_data_from_result_manager(self, channel_num: int) -> Dict[str, Any]:
        """
        从测试结果管理器获取通道测试数据

        Args:
            channel_num: 通道号（1-8）

        Returns:
            通道测试数据字典
        """
        try:
            # 从测试结果管理器获取最新测试结果
            if hasattr(self, 'test_result_manager') and self.test_result_manager:
                # 获取通道的Rs和Rct值
                rs_value, rct_value = self.test_result_manager.calculate_rs_rct_for_channel(channel_num)

                # 修复获取Rsei值
                rsei_value = self.test_result_manager.get_channel_rsei_value(channel_num)

                # 获取阻抗数据
                impedance_data = {}
                if hasattr(self.test_result_manager, 'impedance_data_manager'):
                    impedance_data = self.test_result_manager.impedance_data_manager.get_channel_impedance_data(channel_num)

                # 获取电压（从设备配置管理器）
                voltage = 3.7  # 默认值
                if hasattr(self, 'device_config_manager') and self.device_config_manager:
                    voltage = self.device_config_manager.read_channel_voltage(channel_num)
                # Rsei值已经在测试结果管理器中计算完成
                logger.debug(f"通道{channel_num}获取Rsei值: {rsei_value:.3f}mΩ")

                # 新增计算阻抗比 Rp/Rs，其中 Rp = Rsei + Rct
                impedance_ratio = 0.0
                if rs_value > 0:
                    rp_value = rsei_value + rct_value  # 极化电阻
                    impedance_ratio = rp_value / rs_value
                    logger.debug(f"通道{channel_num}阻抗比计算: Rp({rp_value:.3f})/Rs({rs_value:.3f}) = {impedance_ratio:.3f}")
                else:
                    logger.warning(f"通道{channel_num}Rs值为0，阻抗比设为0")

                return {
                    'voltage': voltage,
                    'rs_value': rs_value,
                    'rct_value': rct_value,
                    'rsei_value': rsei_value,  # 包含Rsei值
                    'impedance_ratio': impedance_ratio,  # 新增阻抗比 Rp/Rs
                    'impedance_data': impedance_data,
                    'frequency_data': impedance_data,  # 兼容性
                    'test_progress': 100,
                    'timestamp': time.time()
                }
            else:
                logger.warning(f"测试结果管理器不可用，返回空数据")
                return self._create_empty_result(channel_num)

        except Exception as e:
            logger.error(f"从测试结果管理器获取通道{channel_num}数据失败: {e}")
            return self._create_empty_result(channel_num)

    def create_mock_test_results(self, enabled_channels: List[int]) -> Dict[str, Any]:
        """
        创建模拟测试结果数据（包含EIS频点数据）
        
        Args:
            enabled_channels: 启用的通道列表
            
        Returns:
            模拟测试结果字典
        """
        try:
            logger.debug(f"创建模拟测试结果，通道: {enabled_channels}")
            
            import random
            
            mock_results = {}
            
            for channel_num in enabled_channels:
                # 生成模拟数据
                voltage = round(random.uniform(3.2, 4.2), 3)
                rs_value = round(random.uniform(5.0, 50.0), 3)
                rct_value = round(random.uniform(10.0, 100.0), 3)
                
                # 生成模拟频点数据
                frequencies = [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, 7800.0]
                impedance_data = {}
                
                for freq in frequencies:
                    # 模拟阻抗和相位数据
                    z_magnitude = round(random.uniform(10.0, 200.0), 3)
                    z_phase = round(random.uniform(-90.0, 0.0), 2)
                    
                    impedance_data[freq] = {
                        'magnitude': z_magnitude,
                        'phase': z_phase,
                        'real': round(z_magnitude * random.uniform(0.5, 1.0), 3),
                        'imaginary': round(z_magnitude * random.uniform(-0.5, 0.0), 3)
                    }
                
                mock_results[channel_num] = {
                    'channel_number': channel_num,
                    'voltage': voltage,
                    'rs_value': rs_value,
                    'rct_value': rct_value,
                    'impedance_data': impedance_data,
                    'frequency_data': {freq: {'frequency': freq} for freq in frequencies},
                    'test_progress': 100,
                    'timestamp': time.time(),
                    'mock_data': True
                }
                
                logger.debug(f"通道{channel_num}模拟结果: V={voltage}V, Rs={rs_value}mΩ, Rct={rct_value}mΩ")
            
            logger.info(f"✅ 模拟测试结果创建完成，共{len(mock_results)}个通道")
            return mock_results
            
        except Exception as e:
            logger.error(f"❌ 创建模拟测试结果失败: {e}")
            return {}

    def clear_callback_history(self):
        """清除回调历史记录"""
        try:
            self._sent_callbacks.clear()
            logger.debug("回调历史记录已清除")
        except Exception as e:
            logger.error(f"清除回调历史记录失败: {e}")

    def get_callback_statistics(self) -> Dict[str, Any]:
        """获取回调统计信息"""
        try:
            return {
                'total_callbacks_sent': len(self._sent_callbacks),
                'callback_ids': list(self._sent_callbacks),
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"获取回调统计信息失败: {e}")
            return {}

    # 移除重复的打印触发方法，避免重复打印（打印由test_result_manager统一处理）
    # def _trigger_auto_print_for_channel(self, channel_num: int, result_data: Dict[str, Any]):

    def cleanup(self):
        """清理资源"""
        try:
            # 清除回调历史
            self.clear_callback_history()
            
            # 清除回调函数
            self.progress_callback = None
            
            logger.debug("测试结果处理管理器资源已清理")
            
        except Exception as e:
            logger.error(f"清理测试结果处理管理器资源失败: {e}")
