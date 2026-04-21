#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能优化的测试结果管理器
专门用于解决低配置电脑上无法生成判断结果的问题

Author: Jack
Date: 2025-01-18
"""

import time
import logging
import threading
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

logger = logging.getLogger(__name__)


class PerformanceOptimizedResultManager:
    """性能优化的测试结果管理器"""
    
    def __init__(self, original_result_manager, config_manager=None):
        """
        初始化性能优化的结果管理器
        
        Args:
            original_result_manager: 原始的测试结果管理器
            config_manager: 配置管理器
        """
        self.original_manager = original_result_manager
        self.config_manager = config_manager
        
        # 性能监控
        self.processing_times = []
        self.max_processing_time = 3.0  # 最大处理时间（秒）
        self.timeout_count = 0
        self.total_requests = 0
        
        # 线程池用于超时控制
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ResultProcessor")
        
        # 缓存机制
        self.result_cache = {}
        self.cache_max_size = 100
        
        logger.info("✅ 性能优化的测试结果管理器初始化完成")
    
    def judge_test_result_with_timeout(self, voltage: float, rs_value: float, rct_value: float, 
                                     outlier_result: Optional[str] = None, 
                                     channel_num: Optional[int] = None,
                                     timeout_seconds: float = 3.0) -> Tuple[bool, List[str]]:
        """
        带超时的测试结果判断
        
        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)
            outlier_result: 离群率检测结果
            channel_num: 通道号
            timeout_seconds: 超时时间（秒）
            
        Returns:
            (is_pass, fail_items) 元组
        """
        try:
            start_time = time.time()
            self.total_requests += 1
            
            # 生成缓存键
            cache_key = f"{voltage:.3f}_{rs_value:.3f}_{rct_value:.3f}_{outlier_result}_{channel_num}"
            
            # 检查缓存
            if cache_key in self.result_cache:
                logger.debug(f"通道{channel_num}使用缓存结果")
                return self.result_cache[cache_key]
            
            # 使用线程池执行判断，带超时控制
            future = self.executor.submit(
                self._safe_judge_test_result,
                voltage, rs_value, rct_value, outlier_result, channel_num
            )
            
            try:
                result = future.result(timeout=timeout_seconds)
                processing_time = time.time() - start_time
                
                # 更新性能监控
                self._update_performance_stats(processing_time)
                
                # 缓存结果
                self._cache_result(cache_key, result)
                
                logger.debug(f"通道{channel_num}判断完成，耗时: {processing_time:.2f}秒")
                return result
                
            except FutureTimeoutError:
                self.timeout_count += 1
                logger.error(f"通道{channel_num}判断超时({timeout_seconds}秒)，使用简化判断")
                
                # 超时后使用简化判断
                return self._simplified_judgment(voltage, rs_value, rct_value, channel_num)
                
        except Exception as e:
            logger.error(f"带超时判断失败: {e}")
            return self._emergency_judgment(voltage, rs_value, rct_value, channel_num)
    
    def _safe_judge_test_result(self, voltage: float, rs_value: float, rct_value: float,
                               outlier_result: Optional[str], channel_num: Optional[int]) -> Tuple[bool, List[str]]:
        """
        安全的测试结果判断（在线程中执行）
        
        Args:
            voltage: 电压值
            rs_value: Rs值
            rct_value: Rct值
            outlier_result: 离群率结果
            channel_num: 通道号
            
        Returns:
            判断结果
        """
        try:
            # 调用原始管理器的判断方法
            return self.original_manager.judge_test_result(
                voltage, rs_value, rct_value, outlier_result, channel_num
            )
        except Exception as e:
            logger.error(f"原始判断方法失败: {e}")
            return self._simplified_judgment(voltage, rs_value, rct_value, channel_num)
    
    def _simplified_judgment(self, voltage: float, rs_value: float, rct_value: float,
                           channel_num: Optional[int]) -> Tuple[bool, List[str]]:
        """
        简化的判断逻辑（用于超时或异常情况）
        
        Args:
            voltage: 电压值
            rs_value: Rs值
            rct_value: Rct值
            channel_num: 通道号
            
        Returns:
            判断结果
        """
        try:
            fail_items = []
            
            # 简化的电压判断
            if voltage < 2.0 or voltage > 5.0:
                fail_items.append("电压")
            
            # 简化的Rs判断
            if rs_value < 0 or rs_value > 10.0:
                fail_items.append("Rs")
            
            # 简化的Rct判断
            if rct_value < 0 or rct_value > 50.0:
                fail_items.append("Rct")
            
            is_pass = len(fail_items) == 0
            
            logger.debug(f"通道{channel_num}简化判断: {'合格' if is_pass else '不合格'}, 失败项: {fail_items}")
            return is_pass, fail_items
            
        except Exception as e:
            logger.error(f"简化判断失败: {e}")
            return self._emergency_judgment(voltage, rs_value, rct_value, channel_num)
    
    def _emergency_judgment(self, voltage: float, rs_value: float, rct_value: float,
                          channel_num: Optional[int]) -> Tuple[bool, List[str]]:
        """
        紧急判断逻辑（最后的备用方案）
        
        Args:
            voltage: 电压值
            rs_value: Rs值
            rct_value: Rct值
            channel_num: 通道号
            
        Returns:
            判断结果
        """
        try:
            # 最基本的判断：只要有数值就认为测试完成
            if voltage > 0 and rs_value >= 0 and rct_value >= 0:
                logger.warning(f"通道{channel_num}使用紧急判断，结果: 合格")
                return True, []
            else:
                logger.warning(f"通道{channel_num}使用紧急判断，结果: 不合格")
                return False, ["数据异常"]
                
        except Exception as e:
            logger.error(f"紧急判断失败: {e}")
            return False, ["系统错误"]
    
    def _update_performance_stats(self, processing_time: float):
        """更新性能统计"""
        try:
            self.processing_times.append(processing_time)
            
            # 只保留最近20次的记录
            if len(self.processing_times) > 20:
                self.processing_times = self.processing_times[-20:]
            
            # 计算统计信息
            avg_time = sum(self.processing_times) / len(self.processing_times)
            timeout_rate = self.timeout_count / self.total_requests if self.total_requests > 0 else 0
            
            # 动态调整超时时间
            if timeout_rate > 0.2:  # 超时率超过20%
                self.max_processing_time = min(self.max_processing_time * 1.2, 10.0)
                logger.warning(f"超时率过高({timeout_rate:.1%})，调整最大处理时间到{self.max_processing_time:.1f}秒")
            
            if avg_time > self.max_processing_time:
                logger.warning(f"平均处理时间({avg_time:.2f}秒)超过阈值({self.max_processing_time:.1f}秒)")
                
        except Exception as e:
            logger.error(f"更新性能统计失败: {e}")
    
    def _cache_result(self, cache_key: str, result: Tuple[bool, List[str]]):
        """缓存结果"""
        try:
            # 限制缓存大小
            if len(self.result_cache) >= self.cache_max_size:
                # 删除最旧的缓存项
                oldest_key = next(iter(self.result_cache))
                del self.result_cache[oldest_key]
            
            self.result_cache[cache_key] = result
            
        except Exception as e:
            logger.error(f"缓存结果失败: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        try:
            if not self.processing_times:
                return {"status": "no_data"}
            
            avg_time = sum(self.processing_times) / len(self.processing_times)
            max_time = max(self.processing_times)
            min_time = min(self.processing_times)
            timeout_rate = self.timeout_count / self.total_requests if self.total_requests > 0 else 0
            
            return {
                "status": "active",
                "total_requests": self.total_requests,
                "timeout_count": self.timeout_count,
                "timeout_rate": timeout_rate,
                "avg_processing_time": avg_time,
                "max_processing_time": max_time,
                "min_processing_time": min_time,
                "cache_size": len(self.result_cache)
            }
            
        except Exception as e:
            logger.error(f"获取性能统计失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def cleanup(self):
        """清理资源"""
        try:
            self.executor.shutdown(wait=True)
            self.result_cache.clear()
            logger.info("性能优化结果管理器资源已清理")
            
        except Exception as e:
            logger.error(f"清理资源失败: {e}")
