# -*- coding: utf-8 -*-
"""
启动策略管理器
负责管理不同频率下的阻抗测量启动策略，包括并行启动、序列启动、错频启动等

从TestFlowController中提取的启动策略功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
import time
import os
import json
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class StartupStrategyManager:
    """
    启动策略管理器
    
    职责：
    - 管理不同频率的启动策略
    - 错频启动配置和执行
    - 启动延时计算
    - 启动成功率统计
    """
    
    def __init__(self, comm_manager, config_manager):
        """
        初始化启动策略管理器
        
        Args:
            comm_manager: 通信管理器
            config_manager: 配置管理器
        """
        self.comm_manager = comm_manager
        self.config_manager = config_manager
        
        # 启动策略配置缓存
        self._stagger_config = None
        
        # 启动统计信息
        self.startup_stats = {
            'total_attempts': 0,
            'successful_attempts': 0,
            'failed_attempts': 0,
            'frequency_stats': {}
        }
        
        logger.debug("启动策略管理器初始化完成")
    
    def start_measurement(self, channel_indices: List[int], frequency: float, startup_mode: str = 'auto') -> bool:
        """
        启动阻抗测量
        
        Args:
            channel_indices: 通道索引列表（0-7）
            frequency: 测试频率
            startup_mode: 启动模式 ('parallel', 'sequential', 'auto')
            
        Returns:
            是否启动成功
        """
        try:
            logger.info(f"启动阻抗测量: {frequency}Hz, 通道{[ch+1 for ch in channel_indices]}, 模式={startup_mode}")
            
            # 记录启动尝试
            self._record_startup_attempt(frequency)
            
            success = False
            
            if startup_mode == 'parallel':
                # 模式A：真正的并行启动（所有通道同时启动）
                logger.info(f"🚀 模式A-并行启动: {frequency}Hz，所有通道同时启动")
                success = self._start_parallel_measurement(channel_indices, frequency)
            elif startup_mode == 'sequential':
                # 模式B：独立序列启动（依次启动，异步数据收集）
                logger.info(f"🔄 模式B-序列启动: {frequency}Hz，依次启动异步收集")
                success = self._start_sequential_measurement(channel_indices, frequency)
            else:
                # 自动模式：统一使用0FH群发启动（不做错频优化）
                success = self._start_parallel_measurement(channel_indices, frequency)
            
            # 记录启动结果
            self._record_startup_result(frequency, success)
            
            return success
            
        except Exception as e:
            logger.error(f"启动阻抗测量失败: {e}")
            self._record_startup_result(frequency, False)
            return False
    
    def _start_parallel_measurement(self, channel_indices: List[int], frequency: float) -> bool:
        """
        并行启动阻抗测量（使用0FH群发启动命令）

        Args:
            channel_indices: 通道索引列表（0-7）
            frequency: 测试频率

        Returns:
            是否启动成功
        """
        try:
            logger.info(f"🚀 真正并行启动阻抗测量: {frequency}Hz，使用0FH群发启动")

            start_time = time.time()

            # 使用0FH群发启动命令同时启动所有通道
            success = self.comm_manager.start_impedance_measurement_broadcast(channel_indices)

            total_time = time.time() - start_time

            if success:
                logger.info(f"✅ 0FH群发启动成功: {len(channel_indices)}个通道同时启动，耗时{total_time:.3f}秒")
                return True
            else:
                logger.warning(f"⚠️ 0FH群发启动失败，回退到逐个启动模式")
                # 回退到原来的逐个启动方式
                return self._start_parallel_measurement_fallback(channel_indices, frequency)

        except Exception as e:
            logger.error(f"并行启动失败: {e}")
            # 回退到原来的逐个启动方式
            return self._start_parallel_measurement_fallback(channel_indices, frequency)

    def _start_parallel_measurement_fallback(self, channel_indices: List[int], frequency: float) -> bool:
        """
        并行启动阻抗测量（回退方案：逐个启动）

        Args:
            channel_indices: 通道索引列表（0-7）
            frequency: 测试频率

        Returns:
            是否启动成功
        """
        try:
            logger.info(f"🔄 回退到逐个启动模式: {frequency}Hz")

            success_count = 0
            start_time = time.time()

            # 逐个启动所有通道（无延时）
            for channel_index in channel_indices:
                if self.comm_manager.start_single_channel_measurement(channel_index):
                    success_count += 1
                    logger.debug(f"✅ 回退通道{channel_index+1}启动成功")
                else:
                    logger.error(f"❌ 回退通道{channel_index+1}启动失败")

            total_time = time.time() - start_time
            logger.info(f"🎯 回退启动完成: {success_count}/{len(channel_indices)}个通道, 耗时{total_time:.3f}秒")

            return success_count == len(channel_indices)

        except Exception as e:
            logger.error(f"回退启动失败: {e}")
            return False
    
    def _start_sequential_measurement(self, channel_indices: List[int], frequency: float) -> bool:
        """
        序列启动阻抗测量（改为使用0FH群发启动，不做错频优化）

        Args:
            channel_indices: 通道索引列表（0-7）
            frequency: 测试频率

        Returns:
            是否启动成功
        """
        try:
            logger.info(f"🚀 序列模式改为群发启动: {frequency}Hz，使用0FH群发启动")

            start_time = time.time()

            # 使用0FH群发启动命令同时启动所有通道（不做错频）
            success = self.comm_manager.start_impedance_measurement_broadcast(channel_indices)

            total_time = time.time() - start_time

            if success:
                logger.info(f"✅ 序列模式0FH群发启动成功: {len(channel_indices)}个通道同时启动，耗时{total_time:.3f}秒")
                return True
            else:
                logger.warning(f"⚠️ 序列模式0FH群发启动失败，回退到逐个启动模式")
                # 回退到原来的逐个启动方式
                return self._start_parallel_measurement_fallback(channel_indices, frequency)

        except Exception as e:
            logger.error(f"序列启动失败: {e}")
            # 回退到原来的逐个启动方式
            return self._start_parallel_measurement_fallback(channel_indices, frequency)
    
    def _start_ultra_high_frequency(self, channel_indices: List[int], frequency: float) -> bool:
        """
        超高频启动策略（≥500Hz）：最大间隔，最强防干扰
        """
        try:
            logger.info(f"🚀 超高频启动策略: {frequency}Hz")
            
            # 使用配置的延时
            stagger_delay = self._calculate_stagger_delay(frequency)
            logger.info(f"⏱️ 超高频防干扰延时: {stagger_delay*1000:.0f}ms")
            
            success_count = 0
            start_time = time.time()
            
            # 逐个启动，最大间隔
            for i, channel_index in enumerate(channel_indices):
                if self.comm_manager.start_single_channel_measurement(channel_index):
                    success_count += 1
                    logger.info(f"✅ 超高频通道{channel_index+1}启动成功")
                    
                    # 超高频防干扰延时
                    if i < len(channel_indices) - 1:
                        time.sleep(stagger_delay)
                        logger.debug(f"⏱️ 超高频防干扰延时: {stagger_delay*1000:.0f}ms")
                else:
                    logger.error(f"❌ 超高频通道{channel_index+1}启动失败")
            
            total_time = time.time() - start_time
            logger.info(f"🎯 超高频启动完成: {success_count}/{len(channel_indices)}个通道, 耗时{total_time:.3f}秒")
            
            return success_count == len(channel_indices)
            
        except Exception as e:
            logger.error(f"超高频启动失败: {e}")
            return False
    
    def _start_high_frequency_grouped(self, channel_indices: List[int], frequency: float) -> bool:
        """
        高频分组启动策略（100-500Hz）：分组启动，减少总时间
        """
        try:
            logger.info(f"🔄 高频分组启动策略: {frequency}Hz")
            
            # 分成2组，每组4个通道
            group_size = 4
            groups = [channel_indices[i:i+group_size] for i in range(0, len(channel_indices), group_size)]
            
            success_count = 0
            start_time = time.time()
            
            for group_idx, group in enumerate(groups):
                
                # 组内逐个启动
                for i, channel_index in enumerate(group):
                    if self.comm_manager.start_single_channel_measurement(channel_index):
                        success_count += 1
                        logger.debug(f"✅ 高频通道{channel_index+1}启动成功")
                        
                        # 组内延时
                        if i < len(group) - 1:
                            time.sleep(0.2)  # 组内200ms延时
                    else:
                        logger.error(f"❌ 高频通道{channel_index+1}启动失败")
                
                # 组间延时
                if group_idx < len(groups) - 1:
                    time.sleep(0.8)  # 组间800ms延时
                    logger.debug(f"⏱️ 组间防干扰延时: 800ms")
            
            total_time = time.time() - start_time
            logger.info(f"🎯 高频分组启动完成: {success_count}/{len(channel_indices)}个通道, 耗时{total_time:.3f}秒")
            
            return success_count == len(channel_indices)
            
        except Exception as e:
            logger.error(f"高频分组启动失败: {e}")
            return False
    
    def _start_standard_staggered(self, channel_indices: List[int], frequency: float) -> bool:
        """
        标准错频启动策略（<100Hz）：标准间隔
        """
        try:
            
            stagger_delay = self._calculate_stagger_delay(frequency)
            logger.info(f"⏱️ 标准错频延时: {stagger_delay*1000:.0f}ms")
            
            success_count = 0
            start_time = time.time()
            
            # 逐个启动通道
            for i, channel_index in enumerate(channel_indices):
                if self.comm_manager.start_single_channel_measurement(channel_index):
                    success_count += 1
                    logger.debug(f"✅ 标准通道{channel_index+1}启动成功")
                    
                    # 标准错频延时
                    if i < len(channel_indices) - 1:
                        time.sleep(stagger_delay)
                        logger.debug(f"⏱️ 标准错频延时: {stagger_delay*1000:.0f}ms")
                else:
                    logger.error(f"❌ 标准通道{channel_index+1}启动失败")
            
            total_time = time.time() - start_time
            logger.info(f"🎯 标准错频启动完成: {success_count}/{len(channel_indices)}个通道, 耗时{total_time:.3f}秒")
            
            return success_count == len(channel_indices)
            
        except Exception as e:
            logger.error(f"标准错频启动失败: {e}")
            return False

    def _calculate_stagger_delay(self, frequency: float) -> float:
        """
        计算错频启动延时（秒）- 可配置优化版本

        Args:
            frequency: 测试频率 (Hz)

        Returns:
            启动延时时间 (秒)
        """
        try:
            # 加载配置
            if not hasattr(self, '_stagger_config') or self._stagger_config is None:
                self._stagger_config = self._load_stagger_config()

            delays = self._stagger_config.get('stagger_delays', {})

            # 根据频率选择延时
            if frequency >= delays.get('ultra_high_freq', {}).get('threshold', 500):
                # 超高频测试：800ms间隔（最强防干扰）
                delay_ms = delays.get('ultra_high_freq', {}).get('delay_ms', 800)
                return delay_ms / 1000.0
            elif frequency >= delays.get('high_freq', {}).get('threshold', 100):
                # 高频测试：400ms间隔（增强防干扰）
                delay_ms = delays.get('high_freq', {}).get('delay_ms', 400)
                return delay_ms / 1000.0
            elif frequency >= delays.get('mid_freq', {}).get('threshold', 10):
                # 中频测试：250ms间隔
                delay_ms = delays.get('mid_freq', {}).get('delay_ms', 250)
                return delay_ms / 1000.0
            elif frequency >= delays.get('low_freq', {}).get('threshold', 1):
                # 低频测试：150ms间隔
                delay_ms = delays.get('low_freq', {}).get('delay_ms', 150)
                return delay_ms / 1000.0
            else:
                # 极低频测试：100ms间隔
                delay_ms = delays.get('very_low_freq', {}).get('delay_ms', 100)
                return delay_ms / 1000.0

        except Exception as e:
            logger.error(f"计算错频延时失败: {e}")
            return 0.4  # 默认400ms

    def _load_stagger_config(self) -> Dict[str, Any]:
        """加载错频配置参数"""
        try:
            config_path = 'config/stagger_config.json'
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"错频配置文件不存在: {config_path}，使用默认配置")
                return self._get_default_stagger_config()
        except Exception as e:
            logger.error(f"加载错频配置失败: {e}，使用默认配置")
            return self._get_default_stagger_config()

    def _get_default_stagger_config(self) -> Dict[str, Any]:
        """获取默认错频配置"""
        return {
            "stagger_delays": {
                "ultra_high_freq": {"threshold": 500, "delay_ms": 800},
                "high_freq": {"threshold": 100, "delay_ms": 400, "group_delay_ms": 800},
                "mid_freq": {"threshold": 10, "delay_ms": 250},
                "low_freq": {"threshold": 1, "delay_ms": 150},
                "very_low_freq": {"threshold": 0, "delay_ms": 100}
            },
            "adaptive_settings": {"enabled": True, "quality_threshold": 0.15}
        }

    def _record_startup_attempt(self, frequency: float):
        """记录启动尝试"""
        self.startup_stats['total_attempts'] += 1

        if frequency not in self.startup_stats['frequency_stats']:
            self.startup_stats['frequency_stats'][frequency] = {
                'attempts': 0,
                'successes': 0,
                'failures': 0
            }

        self.startup_stats['frequency_stats'][frequency]['attempts'] += 1

    def _record_startup_result(self, frequency: float, success: bool):
        """记录启动结果"""
        if success:
            self.startup_stats['successful_attempts'] += 1
            self.startup_stats['frequency_stats'][frequency]['successes'] += 1
        else:
            self.startup_stats['failed_attempts'] += 1
            self.startup_stats['frequency_stats'][frequency]['failures'] += 1

    def get_startup_stats(self) -> Dict[str, Any]:
        """获取启动统计信息"""
        stats = self.startup_stats.copy()

        # 计算成功率
        total = stats['total_attempts']
        if total > 0:
            stats['success_rate'] = stats['successful_attempts'] / total
        else:
            stats['success_rate'] = 0.0

        # 计算每个频率的成功率
        for freq, freq_stats in stats['frequency_stats'].items():
            attempts = freq_stats['attempts']
            if attempts > 0:
                freq_stats['success_rate'] = freq_stats['successes'] / attempts
            else:
                freq_stats['success_rate'] = 0.0

        return stats

    def reset_startup_stats(self):
        """重置启动统计信息"""
        self.startup_stats = {
            'total_attempts': 0,
            'successful_attempts': 0,
            'failed_attempts': 0,
            'frequency_stats': {}
        }
        logger.info("启动统计信息已重置")

    def get_recommended_startup_mode(self, frequency: float) -> str:
        """
        根据频率推荐启动模式（统一推荐parallel模式，使用0FH群发启动）

        Args:
            frequency: 测试频率

        Returns:
            推荐的启动模式
        """
        # 统一推荐parallel模式，使用0FH群发启动，不做错频优化
        return 'parallel'
