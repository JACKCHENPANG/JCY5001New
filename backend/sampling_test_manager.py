#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
取样测试管理器
负责管理取样测试的流程、数据收集和统计分析

Author: Jack
Date: 2025-07-09
Version: V0.90.01
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import statistics

logger = logging.getLogger(__name__)


@dataclass
class SamplingTestData:
    """取样测试数据结构"""
    test_id: str
    timestamp: datetime
    channel_data: Dict[int, Dict]  # 通道号 -> 测试数据
    is_valid: bool = True  # 用户是否选择使用该数据


@dataclass
class SamplingStatistics:
    """取样统计数据结构"""
    parameter_name: str
    values: List[float]
    min_value: float
    max_value: float
    mean_value: float
    std_dev: float
    count: int


class SamplingTestManager:
    """取样测试管理器"""
    
    def __init__(self, config_manager):
        """
        初始化取样测试管理器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.is_sampling_mode = False
        # 修复：从配置文件动态读取取样数量，而不是硬编码
        self.target_sample_count = self.config_manager.get('test.sampling_count', 30)
        self.current_sample_count = 0
        self.valid_sample_count = 0
        
        # 存储取样数据
        self.sampling_data: List[SamplingTestData] = []
        
        # 统计数据缓存
        self._statistics_cache: Dict[str, SamplingStatistics] = {}
        
        logger.info("✅ 取样测试管理器初始化完成")

    def update_target_count_from_config(self):
        """从配置文件更新目标取样数量"""
        try:
            new_target_count = self.config_manager.get('test.sampling_count', 30)
            if new_target_count != self.target_sample_count:
                old_count = self.target_sample_count
                self.target_sample_count = new_target_count
                logger.info(f"🔄 目标取样数量已更新: {old_count} -> {new_target_count}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ 更新目标取样数量失败: {e}")
            return False

    def get_last_test_data(self) -> Optional[Dict]:
        """获取最后一次测试的数据"""
        try:
            if not self.sample_data:
                return None

            # 获取最后一个测试ID
            last_test_id = list(self.sample_data.keys())[-1]
            last_data = self.sample_data[last_test_id]

            return {
                'test_id': last_test_id,
                'channel_data': last_data.get('channel_data', {}),
                'timestamp': last_data.get('timestamp'),
                'is_valid': last_data.get('is_valid', None)
            }

        except Exception as e:
            logger.error(f"❌ 获取最后一次测试数据失败: {e}")
            return None

    def start_sampling_test(self, target_count: int) -> bool:
        """
        开始取样测试

        Args:
            target_count: 目标取样数量

        Returns:
            是否成功开始
        """
        try:
            logger.info(f"🎯 SamplingTestManager: 开始取样测试，目标数量: {target_count}")
            logger.debug(f" 启动前状态: is_sampling_mode={self.is_sampling_mode}, current_count={self.current_sample_count}, valid_count={self.valid_sample_count}")

            # 确保状态完全重置
            self.is_sampling_mode = True
            self.target_sample_count = target_count
            self.current_sample_count = 0
            self.valid_sample_count = 0
            self.sampling_data.clear()
            self._statistics_cache.clear()

            logger.info(f"✅ SamplingTestManager: 取样测试已启动，状态验证: is_sampling_mode={self.is_sampling_mode}")
            return True

        except Exception as e:
            logger.error(f"❌ SamplingTestManager: 开始取样测试失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    def stop_sampling_test(self):
        """停止取样测试"""
        try:
            logger.info(f"⏹️ SamplingTestManager: 停止取样测试，当前状态: is_sampling_mode={self.is_sampling_mode}")
            logger.debug(f" 停止前统计: 有效样本数={self.valid_sample_count}, 总测试数={self.current_sample_count}, 目标数={self.target_sample_count}")

            # 停止取样模式
            self.is_sampling_mode = False

            # 完全重置所有计数和数据
            self.reset_all_counts()

            logger.info(f"✅ SamplingTestManager: 取样测试已停止并完全重置，计数已清零")

        except Exception as e:
            logger.error(f"❌ SamplingTestManager: 停止取样测试失败: {e}")
            # 确保状态被重置
            self.is_sampling_mode = False
            try:
                self.reset_all_counts()
            except:
                # 最后的保险措施
                self.current_sample_count = 0
                self.valid_sample_count = 0
                self.sampling_data.clear()
                self._statistics_cache.clear()
    
    def add_sample_data(self, channel_data: Dict[int, Dict]) -> str:
        """
        添加取样数据
        
        Args:
            channel_data: 通道测试数据
            
        Returns:
            测试ID
        """
        try:
            test_id = f"SAMPLE_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}"
            
            sample_data = SamplingTestData(
                test_id=test_id,
                timestamp=datetime.now(),
                channel_data=channel_data,
                is_valid=True  # 默认有效，等待用户确认
            )
            
            self.sampling_data.append(sample_data)
            self.current_sample_count += 1
            
            logger.info(f"📊 添加取样数据: {test_id}, 当前进度: {self.current_sample_count}/{self.target_sample_count}")
            return test_id
            
        except Exception as e:
            logger.error(f"❌ 添加取样数据失败: {e}")
            return ""
    
    def confirm_sample_data(self, test_id: str, is_valid: bool):
        """
        确认取样数据是否有效
        
        Args:
            test_id: 测试ID
            is_valid: 是否有效
        """
        try:
            for sample in self.sampling_data:
                if sample.test_id == test_id:
                    sample.is_valid = is_valid
                    if is_valid:
                        self.valid_sample_count += 1
                        logger.info(f"✅ 确认使用取样数据: {test_id}")
                    else:
                        logger.info(f"❌ 放弃取样数据: {test_id}")
                    
                    # 清除统计缓存，强制重新计算
                    self._statistics_cache.clear()
                    break
                    
        except Exception as e:
            logger.error(f"❌ 确认取样数据失败: {e}")
    
    def get_progress_info(self) -> Tuple[int, int, int]:
        """
        获取进度信息
        
        Returns:
            (当前样本数, 有效样本数, 目标样本数)
        """
        return self.current_sample_count, self.valid_sample_count, self.target_sample_count
    
    def is_sampling_complete(self) -> bool:
        """
        检查取样是否完成
        
        Returns:
            是否完成
        """
        return self.valid_sample_count >= self.target_sample_count
    
    def get_current_statistics(self) -> Dict[str, SamplingStatistics]:
        """
        获取当前统计数据
        
        Returns:
            统计数据字典
        """
        if not self._statistics_cache:
            self._calculate_statistics()
        return self._statistics_cache.copy()
    
    def _calculate_statistics(self):
        """计算统计数据"""
        try:
            # 获取有效数据
            valid_samples = [s for s in self.sampling_data if s.is_valid]
            if not valid_samples:
                return
            
            # 收集所有通道的参数数据
            parameter_data = {
                'voltage': [],
                'rs_value': [],
                'rct_value': [],
                'rsei_value': []
            }
            
            for sample in valid_samples:
                for channel_num, data in sample.channel_data.items():
                    if 'voltage' in data:
                        parameter_data['voltage'].append(data['voltage'])
                    if 'rs_value' in data:
                        parameter_data['rs_value'].append(data['rs_value'])
                    if 'rct_value' in data:
                        parameter_data['rct_value'].append(data['rct_value'])
                    if 'rsei_value' in data:
                        parameter_data['rsei_value'].append(data['rsei_value'])
            
            # 计算每个参数的统计信息
            for param_name, values in parameter_data.items():
                if values:
                    self._statistics_cache[param_name] = SamplingStatistics(
                        parameter_name=param_name,
                        values=values,
                        min_value=min(values),
                        max_value=max(values),
                        mean_value=statistics.mean(values),
                        std_dev=statistics.stdev(values) if len(values) > 1 else 0.0,
                        count=len(values)
                    )
            
            logger.debug(f"📈 统计数据计算完成，参数数量: {len(self._statistics_cache)}")
            
        except Exception as e:
            logger.error(f"❌ 计算统计数据失败: {e}")
    
    def get_suggested_parameters(self) -> Dict[str, Dict]:
        """
        获取建议的判断参数
        
        Returns:
            建议参数字典
        """
        try:
            statistics_data = self.get_current_statistics()
            suggestions = {}
            
            # Rs参数建议
            if 'rs_value' in statistics_data:
                rs_stats = statistics_data['rs_value']
                suggestions['rs'] = {
                    'min_range': max(0, rs_stats.min_value - rs_stats.std_dev),
                    'max_range': rs_stats.max_value + rs_stats.std_dev,
                    'mean': rs_stats.mean_value,
                    'std_dev': rs_stats.std_dev
                }
            
            # Rct参数建议
            if 'rct_value' in statistics_data:
                rct_stats = statistics_data['rct_value']
                suggestions['rct'] = {
                    'min_range': max(0, rct_stats.min_value - rct_stats.std_dev),
                    'max_range': rct_stats.max_value + rct_stats.std_dev,
                    'mean': rct_stats.mean_value,
                    'std_dev': rct_stats.std_dev
                }
            
            # 修复电压参数建议（基于标准差的动态计算）
            if 'voltage' in statistics_data:
                voltage_stats = statistics_data['voltage']

                # 使用标准差计算合理的电压范围，但设置最小偏差值
                voltage_deviation = max(voltage_stats.std_dev * 2, 0.05)  # 至少±0.05V偏差

                # 计算建议范围
                min_voltage = max(0.1, voltage_stats.mean_value - voltage_deviation)  # 最小不低于0.1V
                max_voltage = min(50.0, voltage_stats.mean_value + voltage_deviation)  # 最大不超过50V

                suggestions['voltage'] = {
                    'min_range': min_voltage,
                    'max_range': max_voltage,
                    'mean': voltage_stats.mean_value,
                    'std_dev': voltage_stats.std_dev
                }

                logger.debug(f"电压参数建议: 平均值={voltage_stats.mean_value:.3f}V, 标准差={voltage_stats.std_dev:.3f}V, 建议偏差=±{voltage_deviation:.3f}V")

            # Rsei参数建议
            if 'rsei_value' in statistics_data:
                rsei_stats = statistics_data['rsei_value']
                # 过滤掉0值（无效的Rsei值）
                valid_rsei_values = [v for v in rsei_stats.values if v > 0.001]
                if valid_rsei_values:
                    # 重新计算有效Rsei的统计数据
                    import statistics as stats
                    rsei_mean = stats.mean(valid_rsei_values)
                    rsei_std = stats.stdev(valid_rsei_values) if len(valid_rsei_values) > 1 else 0.0
                    rsei_min = min(valid_rsei_values)
                    rsei_max = max(valid_rsei_values)

                    suggestions['rsei'] = {
                        'min_range': max(0, rsei_min - rsei_std),
                        'max_range': rsei_max + rsei_std,
                        'mean': rsei_mean,
                        'std_dev': rsei_std
                    }
                    logger.debug(f"Rsei参数建议: 有效样本{len(valid_rsei_values)}个，范围{suggestions['rsei']['min_range']:.3f}-{suggestions['rsei']['max_range']:.3f}mΩ")

            logger.info(f"💡 生成参数建议完成，参数数量: {len(suggestions)}")
            return suggestions
            
        except Exception as e:
            logger.error(f"❌ 生成参数建议失败: {e}")
            return {}
    
    def get_valid_sample_data(self) -> List[SamplingTestData]:
        """
        获取有效的取样数据
        
        Returns:
            有效取样数据列表
        """
        return [s for s in self.sampling_data if s.is_valid]
    
    def clear_sampling_data(self):
        """清除取样数据"""
        self.sampling_data.clear()
        self._statistics_cache.clear()
        self.current_sample_count = 0
        self.valid_sample_count = 0
        logger.info("🧹 取样数据已清除")

    def reset_all_counts(self):
        """重置所有计数（用于退出取样测试时）"""
        try:
            logger.info(f"🔄 重置所有计数 - 当前状态: current={self.current_sample_count}, valid={self.valid_sample_count}")

            self.current_sample_count = 0
            self.valid_sample_count = 0
            self.sampling_data.clear()
            self._statistics_cache.clear()

            logger.info("✅ 所有计数已重置为0，取样数据已清空")

        except Exception as e:
            logger.error(f"❌ 重置计数失败: {e}")
            # 强制重置
            self.current_sample_count = 0
            self.valid_sample_count = 0
