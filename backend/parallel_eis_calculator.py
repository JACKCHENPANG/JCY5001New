#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并行EIS计算器 - 优化Rs、Rct、Rsei计算性能

作者: Jack
版本: V0.91.00
日期: 2025-08-03
"""

import time
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)


class ParallelEISCalculator:
    """并行EIS计算器"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.cache_enabled = True
        self.fast_mode = False
        
        # 性能统计
        self.calculation_times = []
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info(f"🚀 并行EIS计算器初始化完成，工作线程数: {max_workers}")
        
    def enable_fast_mode(self):
        """启用快速计算模式"""
        self.fast_mode = True
        logger.info("⚡ EIS快速计算模式已启用")
        
    def disable_fast_mode(self):
        """禁用快速计算模式"""
        self.fast_mode = False
        logger.info("🔄 EIS快速计算模式已禁用")
        
    def calculate_parallel(self, channels_data: Dict[int, Dict]) -> Dict[int, Dict]:
        """
        并行计算多个通道的EIS参数
        
        Args:
            channels_data: {channel_num: {'frequencies': [], 'real_parts': [], 'imag_parts': []}}
            
        Returns:
            {channel_num: {'rs': float, 'rct': float, 'rsei': float, 'success': bool}}
        """
        start_time = time.time()
        results = {}
        
        if not channels_data:
            return results
            
        logger.info(f"🔄 开始并行计算 {len(channels_data)} 个通道的EIS参数...")
        
        # 提交所有计算任务
        future_to_channel = {}
        for channel_num, data in channels_data.items():
            future = self.executor.submit(
                self._calculate_single_channel,
                channel_num, data
            )
            future_to_channel[future] = channel_num
            
        # 收集结果
        for future in as_completed(future_to_channel):
            channel_num = future_to_channel[future]
            try:
                result = future.result(timeout=5.0)  # 5秒超时
                results[channel_num] = result
                logger.debug(f"✅ 通道{channel_num}计算完成: Rs={result.get('rs', 0):.3f}mΩ")
            except Exception as e:
                logger.error(f"❌ 通道{channel_num}计算失败: {e}")
                results[channel_num] = {
                    'rs': 0.0, 'rct': 0.0, 'rsei': 0.0, 
                    'success': False, 'error': str(e)
                }
                
        calculation_time = time.time() - start_time
        self.calculation_times.append(calculation_time)
        
        logger.info(f"✅ 并行EIS计算完成，耗时: {calculation_time:.2f}秒")
        return results
        
    def _calculate_single_channel(self, channel_num: int, data: Dict) -> Dict:
        """计算单个通道的EIS参数"""
        try:
            frequencies = np.array(data['frequencies'])
            real_parts = np.array(data['real_parts'])
            imag_parts = np.array(data['imag_parts'])
            
            # 生成缓存键
            cache_key = self._generate_cache_key(frequencies, real_parts, imag_parts)
            
            # 检查缓存
            if self.cache_enabled:
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    self.cache_hits += 1
                    logger.debug(f"通道{channel_num}使用缓存结果")
                    return cached_result
                    
            self.cache_misses += 1
            
            # 执行计算
            if self.fast_mode:
                result = self._calculate_fast_mode(frequencies, real_parts, imag_parts)
            else:
                result = self._calculate_standard_mode(frequencies, real_parts, imag_parts)
                
            result['success'] = True
            result['channel'] = channel_num
            
            # 缓存结果
            if self.cache_enabled:
                self._cache_result(cache_key, result)
                
            return result
            
        except Exception as e:
            logger.error(f"通道{channel_num}EIS计算异常: {e}")
            return {
                'rs': 0.0, 'rct': 0.0, 'rsei': 0.0,
                'success': False, 'error': str(e), 'channel': channel_num
            }
            
    def _calculate_fast_mode(self, frequencies: np.ndarray, 
                           real_parts: np.ndarray, 
                           imag_parts: np.ndarray) -> Dict:
        """快速计算模式（简化算法）"""
        try:
            # 快速Rs计算：使用最高频点
            rs_value = float(np.min(real_parts))
            rs_value = max(0.001, min(50.0, rs_value))  # Jack算法修正允许小Rs值
            
            # 快速Rct计算：使用低频-高频差值
            rp_value = float(np.max(real_parts))
            rct_value = max(0.0, rp_value - rs_value)
            
            # 快速Rsei计算：使用中频段估算
            mid_freq_mask = (frequencies >= 10) & (frequencies <= 100)
            if np.any(mid_freq_mask):
                mid_freq_real = np.mean(real_parts[mid_freq_mask])
                rsei_value = max(0.0, mid_freq_real - rs_value)
            else:
                rsei_value = rct_value * 0.3  # 经验估算
                
            return {
                'rs': rs_value,
                'rct': rct_value,
                'rsei': rsei_value,
                'mode': 'fast'
            }
            
        except Exception as e:
            logger.error(f"快速模式计算失败: {e}")
            return {'rs': 5.0, 'rct': 10.0, 'rsei': 2.0, 'mode': 'fast_fallback'}
            
    def _calculate_standard_mode(self, frequencies: np.ndarray,
                               real_parts: np.ndarray,
                               imag_parts: np.ndarray) -> Dict:
        """标准计算模式（完整算法）"""
        try:
            # 简化算法：直接使用标准EIS分析器
            from backend.eis_analyzer import EISAnalyzer

            analyzer = EISAnalyzer()
            result = analyzer.calculate_rs_rct_enhanced(
                frequencies, real_parts, imag_parts, "PARALLEL_CALC"
            )

            if result and result.get('analysis_success'):
                return {
                    'rs': result.get('rs_value', 0.0),
                    'rct': result.get('rct_value', 0.0),
                    'rsei': result.get('rsei_value', 0.0),
                    'mode': 'standard'
                }
            else:
                err = result.get('error') if isinstance(result, dict) else 'enhanced analysis failed'
                logger.error(f"并行计算：增强版EIS分析失败（不回退）：{err}")
                return {'error': err, 'mode': 'error'}

        except Exception as e:
            logger.error(f"并行计算：标准模式异常（不回退）：{e}")
            return {'error': str(e), 'mode': 'error'}
            
    @lru_cache(maxsize=128)
    def _generate_cache_key(self, frequencies: np.ndarray,
                          real_parts: np.ndarray,
                          imag_parts: np.ndarray) -> str:
        """生成缓存键"""
        try:
            # 使用数据的哈希值作为缓存键
            data_str = f"{frequencies.tobytes()}{real_parts.tobytes()}{imag_parts.tobytes()}"
            return hashlib.md5(data_str.encode()).hexdigest()[:16]
        except:
            return f"fallback_{time.time()}"
            
    def _get_cached_result(self, cache_key: str) -> Optional[Dict]:
        """获取缓存结果"""
        # 简单的内存缓存实现
        if not hasattr(self, '_cache'):
            self._cache = {}
            
        return self._cache.get(cache_key)
        
    def _cache_result(self, cache_key: str, result: Dict):
        """缓存结果"""
        if not hasattr(self, '_cache'):
            self._cache = {}
            
        # 限制缓存大小
        if len(self._cache) > 100:
            # 删除最旧的一半缓存
            keys_to_remove = list(self._cache.keys())[:50]
            for key in keys_to_remove:
                del self._cache[key]
                
        self._cache[cache_key] = result.copy()
        
    def get_performance_stats(self) -> Dict:
        """获取性能统计"""
        if not self.calculation_times:
            return {}
            
        avg_time = sum(self.calculation_times) / len(self.calculation_times)
        total_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0
        
        return {
            'average_calculation_time': avg_time,
            'total_calculations': len(self.calculation_times),
            'cache_hit_rate': cache_hit_rate,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'fast_mode': self.fast_mode
        }
        
    def clear_cache(self):
        """清空缓存"""
        if hasattr(self, '_cache'):
            self._cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info("🧹 EIS计算缓存已清空")
        
    def shutdown(self):
        """关闭计算器"""
        self.executor.shutdown(wait=True)
        logger.info("🔒 并行EIS计算器已关闭")
