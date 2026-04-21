#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JCY5001AS电池阻抗测试系统 - 性能优化配置管理器

功能：
1. 集中管理所有性能优化配置
2. 动态调整优化参数
3. 性能监控和报告
4. 自适应优化建议

作者：Jack
创建时间：2025-01-31
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class CommunicationOptimization:
    """通信优化配置（保守调整）"""
    timeout: float = 0.8
    retry_count: int = 2
    retry_delay: float = 0.03
    command_delay: int = 15
    response_timeout: float = 0.8
    polling_interval: float = 0.1  # 轮询间隔（秒）

@dataclass
class StaggeredDelayOptimization:
    """错频启动延时优化配置（保守调整）"""
    enable: bool = True
    high_frequency_delay: int = 15
    medium_frequency_delay: int = 20
    low_frequency_delay: int = 35
    ultra_low_frequency_delay: int = 0

@dataclass
class UIOptimization:
    """UI更新优化配置"""
    progress_update_interval: float = 1.0  # 进度更新间隔（秒）
    performance_monitor_interval: int = 2000  # 性能监控间隔（毫秒）
    status_check_interval: int = 3  # 状态检查间隔（秒）
    batch_update_enabled: bool = True  # 批量更新

@dataclass
class MeasurementOptimization:
    """测量优化配置（保守调整）"""
    enable_smart_timeout: bool = True
    enable_early_completion: bool = False  # 暂时禁用早期完成
    stability_detection: bool = False      # 暂时禁用稳定性检测
    adaptive_timeout: bool = True
    max_timeout_reduction: float = 0.3     # 减少最大超时时间减少比例

class PerformanceOptimizer:
    """性能优化配置管理器"""
    
    def __init__(self, config_file: str = "config/performance_optimization.json"):
        self.config_file = Path(config_file)
        
        # 默认优化配置
        self.communication = CommunicationOptimization()
        self.staggered_delay = StaggeredDelayOptimization()
        self.ui_optimization = UIOptimization()
        self.measurement = MeasurementOptimization()
        
        # 性能统计
        self.performance_stats = {
            'optimization_start_time': None,
            'total_tests': 0,
            'average_test_time': 0.0,
            'time_saved': 0.0,
            'optimization_efficiency': 0.0
        }
        
        # 加载配置
        self.load_config()
        
        logger.debug("🚀 性能优化配置管理器初始化完成")
    
    def load_config(self):
        """加载优化配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 更新配置
                if 'communication' in config_data:
                    self.communication = CommunicationOptimization(**config_data['communication'])
                
                if 'staggered_delay' in config_data:
                    self.staggered_delay = StaggeredDelayOptimization(**config_data['staggered_delay'])
                
                if 'ui_optimization' in config_data:
                    self.ui_optimization = UIOptimization(**config_data['ui_optimization'])
                
                if 'measurement' in config_data:
                    self.measurement = MeasurementOptimization(**config_data['measurement'])
                
                if 'performance_stats' in config_data:
                    self.performance_stats.update(config_data['performance_stats'])
                
                logger.info("✅ 性能优化配置加载成功")
            else:
                logger.info("📝 使用默认性能优化配置")
                self.save_config()
                
        except Exception as e:
            logger.error(f"加载性能优化配置失败: {e}")
    
    def save_config(self):
        """保存优化配置"""
        try:
            # 确保配置目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config_data = {
                'communication': asdict(self.communication),
                'staggered_delay': asdict(self.staggered_delay),
                'ui_optimization': asdict(self.ui_optimization),
                'measurement': asdict(self.measurement),
                'performance_stats': self.performance_stats,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info("💾 性能优化配置保存成功")
            
        except Exception as e:
            logger.error(f"保存性能优化配置失败: {e}")
    
    def apply_to_app_config(self, app_config_path: str = "config/app_config.json"):
        """将优化配置应用到主配置文件"""
        try:
            app_config_file = Path(app_config_path)
            if not app_config_file.exists():
                logger.error(f"主配置文件不存在: {app_config_path}")
                return False
            
            # 读取主配置
            with open(app_config_file, 'r', encoding='utf-8') as f:
                app_config = json.load(f)
            
            # 应用通信优化
            if 'device' in app_config and 'connection' in app_config['device']:
                conn_config = app_config['device']['connection']
                conn_config['timeout'] = self.communication.timeout
                conn_config['retry_count'] = self.communication.retry_count
                conn_config['retry_delay'] = self.communication.retry_delay
            
            if 'communication' in app_config:
                comm_config = app_config['communication']
                comm_config['timeout'] = self.communication.timeout
                comm_config['command_delay'] = self.communication.command_delay
                comm_config['response_timeout'] = self.communication.response_timeout
            
            # 应用错频延时优化
            if 'staggered_delay' in app_config:
                delay_config = app_config['staggered_delay']
                delay_config['enable'] = self.staggered_delay.enable
                delay_config['high_frequency_delay'] = self.staggered_delay.high_frequency_delay
                delay_config['medium_frequency_delay'] = self.staggered_delay.medium_frequency_delay
                delay_config['low_frequency_delay'] = self.staggered_delay.low_frequency_delay
                delay_config['ultra_low_frequency_delay'] = self.staggered_delay.ultra_low_frequency_delay
            
            # 保存更新后的配置
            with open(app_config_file, 'w', encoding='utf-8') as f:
                json.dump(app_config, f, indent=2, ensure_ascii=False)
            
            logger.info("✅ 性能优化配置已应用到主配置文件")
            return True
            
        except Exception as e:
            logger.error(f"应用优化配置到主配置文件失败: {e}")
            return False
    
    def start_performance_tracking(self):
        """开始性能跟踪"""
        self.performance_stats['optimization_start_time'] = time.time()
    
    def record_test_completion(self, test_duration: float):
        """记录测试完成"""
        self.performance_stats['total_tests'] += 1
        
        # 更新平均测试时间
        total_time = (self.performance_stats['average_test_time'] * 
                     (self.performance_stats['total_tests'] - 1) + test_duration)
        self.performance_stats['average_test_time'] = total_time / self.performance_stats['total_tests']
        
        # 估算节省的时间（与优化前的基准时间比较）
        baseline_time = 600.0  # 假设优化前需要10分钟
        if test_duration < baseline_time:
            self.performance_stats['time_saved'] += (baseline_time - test_duration)
        
        # 计算优化效率
        if baseline_time > 0:
            self.performance_stats['optimization_efficiency'] = (
                (baseline_time - self.performance_stats['average_test_time']) / baseline_time * 100
            )
        
        logger.info(f"📈 记录测试完成: 耗时{test_duration:.1f}s, 平均{self.performance_stats['average_test_time']:.1f}s")
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """获取优化报告"""
        report = {
            'summary': {
                'total_tests': self.performance_stats['total_tests'],
                'average_test_time': self.performance_stats['average_test_time'],
                'time_saved': self.performance_stats['time_saved'],
                'optimization_efficiency': self.performance_stats['optimization_efficiency']
            },
            'current_config': {
                'communication': asdict(self.communication),
                'staggered_delay': asdict(self.staggered_delay),
                'ui_optimization': asdict(self.ui_optimization),
                'measurement': asdict(self.measurement)
            },
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 基于测试次数的建议
        if self.performance_stats['total_tests'] > 10:
            avg_time = self.performance_stats['average_test_time']
            
            if avg_time > 300:  # 超过5分钟
                recommendations.append("测试时间仍较长，建议进一步优化测量超时配置")
            elif avg_time < 120:  # 少于2分钟
                recommendations.append("测试时间已优化良好，可考虑启用更多稳定性检测")
        
        # 基于优化效率的建议
        efficiency = self.performance_stats['optimization_efficiency']
        if efficiency > 50:
            recommendations.append(f"优化效果显著（{efficiency:.1f}%），当前配置表现良好")
        elif efficiency < 20:
            recommendations.append("优化效果有限，建议检查设备通信状态和测量参数")
        
        # 配置相关建议
        if self.communication.timeout > 0.5:
            recommendations.append("通信超时时间较长，可尝试进一步降低")
        
        if not self.measurement.enable_smart_timeout:
            recommendations.append("建议启用智能超时功能以提升测试效率")
        
        return recommendations
    
    def optimize_for_frequency_range(self, frequencies: List[float]):
        """根据频率范围优化配置"""
        try:
            if not frequencies:
                return
            
            min_freq = min(frequencies)
            max_freq = max(frequencies)
            freq_count = len(frequencies)
            
            # 根据频率范围调整超时配置
            if max_freq > 1000:  # 包含高频
                self.communication.timeout = 0.2
                self.communication.polling_interval = 0.03
            elif min_freq < 1:  # 包含超低频
                self.communication.timeout = 0.5
                self.communication.polling_interval = 0.1
            
            # 根据频点数量调整UI更新频率
            if freq_count > 15:
                self.ui_optimization.progress_update_interval = 1.5
                self.ui_optimization.performance_monitor_interval = 3000
            elif freq_count < 10:
                self.ui_optimization.progress_update_interval = 0.8
                self.ui_optimization.performance_monitor_interval = 1500
            
            logger.info(f"🎯 根据频率范围优化配置: {min_freq:.2f}-{max_freq:.2f}Hz, {freq_count}个频点")
            
        except Exception as e:
            logger.error(f"频率范围优化失败: {e}")
    
    def reset_to_defaults(self):
        """重置为默认配置"""
        self.communication = CommunicationOptimization()
        self.staggered_delay = StaggeredDelayOptimization()
        self.ui_optimization = UIOptimization()
        self.measurement = MeasurementOptimization()
        
        logger.info("🔄 性能优化配置已重置为默认值")
        self.save_config()


# 全局性能优化器实例
_global_performance_optimizer: Optional[PerformanceOptimizer] = None

def get_global_performance_optimizer() -> PerformanceOptimizer:
    """获取全局性能优化器实例"""
    global _global_performance_optimizer
    if _global_performance_optimizer is None:
        _global_performance_optimizer = PerformanceOptimizer()
    return _global_performance_optimizer
