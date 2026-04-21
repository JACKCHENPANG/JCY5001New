# -*- coding: utf-8 -*-
"""
测试数据收集器
从ParallelStaggeredTestManager中提取的数据收集相关功能

职责：
- 测试数据收集
- 数据格式化处理
- 结果合并整理
- 数据验证检查

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TestDataCollector:
    """
    测试数据收集器
    
    职责：
    - 收集和整理测试数据
    - 合并错频和同时测试结果
    - 格式化输出数据
    - 验证数据完整性
    """
    
    def __init__(self, db_manager=None, impedance_data_manager=None):
        """初始化测试数据收集器"""
        self.staggered_results: Dict[float, Dict[int, Any]] = {}
        self.simultaneous_results: Dict[float, Dict[int, Any]] = {}
        self.combined_results: Dict[int, Dict[float, Any]] = {}

        # 数据库管理器和阻抗数据管理器
        self.db_manager = db_manager
        self.impedance_data_manager = impedance_data_manager

        # 如果没有提供数据库管理器，尝试创建一个
        if not self.db_manager:
            try:
                from data.database_manager import DatabaseManager
                self.db_manager = DatabaseManager()
                logger.debug("自动创建数据库管理器")
            except Exception as e:
                logger.warning(f"无法创建数据库管理器: {e}")

        # 如果没有提供阻抗数据管理器，尝试获取全局实例
        if not self.impedance_data_manager:
            logger.debug("🔧 [数据收集器] 未提供阻抗数据管理器，尝试获取全局实例")
            try:
                # 尝试从全局实例获取阻抗数据管理器
                from backend.impedance_data_manager import ImpedanceDataManager
                # 获取全局单例实例
                self.impedance_data_manager = ImpedanceDataManager.get_instance()
                if self.impedance_data_manager:
                    logger.info("🔧 [数据收集器] 成功获取全局阻抗数据管理器实例")
                else:
                    logger.warning("🔧 [数据收集器] 全局阻抗数据管理器实例不存在")
            except Exception as e:
                logger.warning(f"🔧 [数据收集器] 获取全局阻抗数据管理器失败: {e}")
                # 如果获取失败，数据保存功能将受限

    def _sync_settings_from_global_instance(self):
        """从全局阻抗数据管理器实例同步设置"""
        try:
            # 尝试从测试执行器或其他地方获取主实例的设置
            # 这里可以通过单例模式或全局变量来获取
            logger.debug("开始同步全局阻抗数据管理器设置")

            # 暂时跳过同步，因为需要更复杂的架构改动
            # 在后续的修复中会通过传递正确的实例来解决
            logger.debug("设置同步完成")

        except Exception as e:
            logger.warning(f"🔧 [数据收集器] 设置同步失败: {e}")

        logger.debug("测试数据收集器初始化完成")
    
    def collect_staggered_results(self, staggered_results: Dict[float, Dict[int, Any]]):
        """
        收集错频测试结果

        Args:
            staggered_results: 错频测试结果
        """
        try:
            self.staggered_results = staggered_results.copy()
            logger.info(f"收集错频测试结果: {len(staggered_results)}个频点")

            # 保存到数据库
            self._save_results_to_database(staggered_results, "staggered")

            for frequency, channels_data in staggered_results.items():
                logger.debug(f"错频频点{frequency}Hz: {len(channels_data)}个通道")

        except Exception as e:
            logger.error(f"收集错频测试结果失败: {e}")
    
    def collect_simultaneous_results(self, simultaneous_results: Dict[float, Dict[int, Any]]):
        """
        收集同时测试结果

        Args:
            simultaneous_results: 同时测试结果
        """
        try:
            self.simultaneous_results = simultaneous_results.copy()
            logger.info(f"收集同时测试结果: {len(simultaneous_results)}个频点")

            # 保存到数据库
            self._save_results_to_database(simultaneous_results, "simultaneous")

            for frequency, channels_data in simultaneous_results.items():
                logger.debug(f"同时频点{frequency}Hz: {len(channels_data)}个通道")

        except Exception as e:
            logger.error(f"收集同时测试结果失败: {e}")
    
    def combine_all_results(self, enabled_channels: List[int]) -> Dict[int, Dict[float, Any]]:
        """
        合并所有测试结果
        
        Args:
            enabled_channels: 启用的通道列表
            
        Returns:
            按通道组织的完整测试结果
        """
        try:
            logger.info("开始合并所有测试结果")
            
            # 清空之前的合并结果
            self.combined_results.clear()
            
            # 初始化通道结果字典
            for channel_index in enabled_channels:
                self.combined_results[channel_index] = {}
            
            # 合并错频测试结果
            self._merge_results_by_mode(self.staggered_results, "staggered")
            
            # 合并同时测试结果
            self._merge_results_by_mode(self.simultaneous_results, "simultaneous")
            
            # 验证数据完整性
            self._validate_combined_results(enabled_channels)
            
            logger.info(f"测试结果合并完成: {len(self.combined_results)}个通道")
            return self.combined_results.copy()
            
        except Exception as e:
            logger.error(f"合并测试结果失败: {e}")
            return {}
    
    def _merge_results_by_mode(self, mode_results: Dict[float, Dict[int, Any]], mode_name: str):
        """
        按模式合并结果
        
        Args:
            mode_results: 模式测试结果
            mode_name: 模式名称
        """
        try:
            for frequency, channels_data in mode_results.items():
                for channel_index, channel_data in channels_data.items():
                    if channel_index in self.combined_results:
                        # 添加模式标识
                        enhanced_data = channel_data.copy()
                        enhanced_data['test_mode'] = mode_name
                        enhanced_data['frequency'] = frequency
                        enhanced_data['timestamp'] = datetime.now().isoformat()
                        
                        self.combined_results[channel_index][frequency] = enhanced_data
                        
                        logger.debug(f"合并通道{channel_index + 1}频点{frequency}Hz数据 ({mode_name})")
                    
        except Exception as e:
            logger.error(f"合并{mode_name}模式结果失败: {e}")
    
    def _validate_combined_results(self, enabled_channels: List[int]):
        """
        验证合并结果的完整性
        
        Args:
            enabled_channels: 启用的通道列表
        """
        try:
            total_expected_frequencies = len(self.staggered_results) + len(self.simultaneous_results)
            
            for channel_index in enabled_channels:
                if channel_index in self.combined_results:
                    channel_frequencies = len(self.combined_results[channel_index])
                    
                    if channel_frequencies < total_expected_frequencies:
                        logger.warning(f"通道{channel_index + 1}数据不完整: {channel_frequencies}/{total_expected_frequencies}个频点")
                    else:
                        logger.debug(f"通道{channel_index + 1}数据完整: {channel_frequencies}个频点")
                else:
                    logger.error(f"通道{channel_index + 1}结果缺失")
                    
        except Exception as e:
            logger.error(f"验证合并结果失败: {e}")
    
    def format_results_for_output(self, enabled_channels: List[int]) -> Dict[str, Any]:
        """
        格式化结果用于输出
        
        Args:
            enabled_channels: 启用的通道列表
            
        Returns:
            格式化的输出结果
        """
        try:
            output_data = {
                'test_summary': {
                    'total_channels': len(enabled_channels),
                    'total_frequencies': len(self.staggered_results) + len(self.simultaneous_results),
                    'staggered_frequencies': len(self.staggered_results),
                    'simultaneous_frequencies': len(self.simultaneous_results),
                    'test_timestamp': datetime.now().isoformat()
                },
                'channel_results': {},
                'frequency_summary': {}
            }
            
            # 按通道整理结果
            for channel_index in enabled_channels:
                channel_num = channel_index + 1
                
                if channel_index in self.combined_results:
                    channel_data = self.combined_results[channel_index]
                    
                    # 格式化通道数据
                    formatted_channel_data = {
                        'channel_number': channel_num,
                        'total_frequencies': len(channel_data),
                        'frequencies': {}
                    }
                    
                    # 按频率整理数据
                    for frequency, freq_data in sorted(channel_data.items()):
                        formatted_freq_data = {
                            'frequency': frequency,
                            'real_impedance': freq_data.get('real_impedance', 0.0),
                            'imaginary_impedance': freq_data.get('imaginary_impedance', 0.0),
                            'magnitude': freq_data.get('magnitude', 0.0),
                            'phase': freq_data.get('phase', 0.0),
                            'test_mode': freq_data.get('test_mode', 'unknown'),
                            'timestamp': freq_data.get('timestamp', '')
                        }
                        
                        formatted_channel_data['frequencies'][frequency] = formatted_freq_data
                    
                    output_data['channel_results'][channel_num] = formatted_channel_data
                else:
                    logger.warning(f"通道{channel_num}数据缺失")
            
            # 频率汇总
            all_frequencies = set()
            all_frequencies.update(self.staggered_results.keys())
            all_frequencies.update(self.simultaneous_results.keys())
            
            for frequency in sorted(all_frequencies):
                mode = 'staggered' if frequency in self.staggered_results else 'simultaneous'
                channels_count = 0
                
                if frequency in self.staggered_results:
                    channels_count = len(self.staggered_results[frequency])
                elif frequency in self.simultaneous_results:
                    channels_count = len(self.simultaneous_results[frequency])
                
                output_data['frequency_summary'][frequency] = {
                    'frequency': frequency,
                    'test_mode': mode,
                    'channels_tested': channels_count
                }
            
            logger.info("测试结果格式化完成")
            return output_data
            
        except Exception as e:
            logger.error(f"格式化输出结果失败: {e}")
            return {}
    
    def get_channel_result(self, channel_index: int) -> Optional[Dict[float, Any]]:
        """
        获取指定通道的测试结果
        
        Args:
            channel_index: 通道索引
            
        Returns:
            通道测试结果
        """
        try:
            if channel_index in self.combined_results:
                return self.combined_results[channel_index].copy()
            else:
                logger.warning(f"通道{channel_index + 1}结果不存在")
                return None
                
        except Exception as e:
            logger.error(f"获取通道{channel_index + 1}结果失败: {e}")
            return None
    
    def get_frequency_result(self, frequency: float) -> Optional[Dict[int, Any]]:
        """
        获取指定频率的测试结果
        
        Args:
            frequency: 频率值
            
        Returns:
            频率测试结果
        """
        try:
            # 先在错频结果中查找
            if frequency in self.staggered_results:
                return self.staggered_results[frequency].copy()
            
            # 再在同时结果中查找
            if frequency in self.simultaneous_results:
                return self.simultaneous_results[frequency].copy()
            
            logger.warning(f"频率{frequency}Hz结果不存在")
            return None
            
        except Exception as e:
            logger.error(f"获取频率{frequency}Hz结果失败: {e}")
            return None
    
    def get_data_statistics(self) -> Dict[str, Any]:
        """
        获取数据统计信息
        
        Returns:
            数据统计字典
        """
        try:
            stats = {
                'staggered_frequencies': len(self.staggered_results),
                'simultaneous_frequencies': len(self.simultaneous_results),
                'total_frequencies': len(self.staggered_results) + len(self.simultaneous_results),
                'channels_with_data': len(self.combined_results),
                'total_data_points': 0
            }
            
            # 计算总数据点数
            for channel_data in self.combined_results.values():
                stats['total_data_points'] += len(channel_data)
            
            return stats
            
        except Exception as e:
            logger.error(f"获取数据统计失败: {e}")
            return {}
    
    def clear_all_data(self):
        """清空所有数据"""
        self.staggered_results.clear()
        self.simultaneous_results.clear()
        self.combined_results.clear()
        logger.debug("测试数据收集器已清空")
    
    def export_to_dict(self) -> Dict[str, Any]:
        """
        导出所有数据为字典格式
        
        Returns:
            包含所有数据的字典
        """
        try:
            return {
                'staggered_results': self.staggered_results.copy(),
                'simultaneous_results': self.simultaneous_results.copy(),
                'combined_results': self.combined_results.copy(),
                'export_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            return {}
    
    def import_from_dict(self, data: Dict[str, Any]):
        """
        从字典导入数据
        
        Args:
            data: 包含数据的字典
        """
        try:
            if 'staggered_results' in data:
                self.staggered_results = data['staggered_results'].copy()
            
            if 'simultaneous_results' in data:
                self.simultaneous_results = data['simultaneous_results'].copy()
            
            if 'combined_results' in data:
                self.combined_results = data['combined_results'].copy()
            
            logger.info("数据导入完成")
            
        except Exception as e:
            logger.error(f"导入数据失败: {e}")

    def _save_results_to_database(self, results: Dict[float, Dict[int, Any]], test_mode: str):
        """
        保存测试结果到数据库

        Args:
            results: 测试结果
            test_mode: 测试模式 ("staggered" 或 "simultaneous")
        """
        try:
            if not self.impedance_data_manager:
                logger.debug("阻抗数据管理器未初始化，跳过数据库保存")
                return

            # 获取当前批次ID（这里需要从配置或其他地方获取）
            batch_id = self._get_current_batch_id()

            for frequency, channels_data in results.items():
                for channel_index, channel_data in channels_data.items():
                    try:
                        # 构建阻抗数据
                        impedance_data = {
                            'frequency': frequency,
                            'channels': {
                                channel_index + 1: {  # 转换为1-8的通道号
                                    'real_impedance': channel_data.get('real_impedance', 0.0),
                                    'imaginary_impedance': channel_data.get('imaginary_impedance', 0.0),
                                    'magnitude': channel_data.get('magnitude', 0.0),
                                    'phase': channel_data.get('phase', 0.0)
                                }
                            }
                        }

                        # 保存到数据库（如果阻抗数据管理器可用）
                        if self.impedance_data_manager:
                            self.impedance_data_manager.save_impedance_data(
                                frequency, impedance_data, batch_id
                            )
                        else:
                            logger.warning(f"阻抗数据管理器不可用，跳过数据保存: 通道{channel_index + 1}, 频率{frequency}Hz")

                        logger.debug(f"保存{test_mode}模式数据到数据库: 通道{channel_index + 1}, 频率{frequency}Hz")

                    except Exception as e:
                        logger.error(f"保存通道{channel_index + 1}频率{frequency}Hz数据失败: {e}")

            logger.info(f"{test_mode}模式测试数据已保存到数据库")

        except Exception as e:
            logger.error(f"保存{test_mode}模式数据到数据库失败: {e}")

    def _get_current_batch_id(self) -> int:
        """
        获取当前批次ID

        Returns:
            批次ID
        """
        try:
            if self.db_manager:
                # 🔧 [修复] 获取最新的活跃批次ID
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id FROM batches
                        ORDER BY created_at DESC
                        LIMIT 1
                    """)
                    result = cursor.fetchone()
                    if result:
                        batch_id = result[0]
                        logger.debug(f"🔍 [数据收集器] 获取到最新批次ID: {batch_id}")
                        return batch_id
                    else:
                        logger.warning("🔍 [数据收集器] 没有找到批次记录，使用默认批次ID 1")
                        return 1
            else:
                logger.warning("🔍 [数据收集器] 数据库管理器不可用，使用默认批次ID 1")
                return 1
        except Exception as e:
            logger.error(f"获取批次ID失败: {e}")
            logger.warning("🔍 [数据收集器] 获取批次ID失败，使用默认批次ID 1")
            return 1