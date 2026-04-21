# -*- coding: utf-8 -*-
"""
测试统计管理器
负责测试统计数据的收集、计算和管理

从TestFlowManager中提取的统计管理功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class TestStatisticsManager(QObject):
    """
    测试统计管理器
    
    职责：
    - 测试统计数据收集
    - 统计指标计算
    - 测试报告生成
    """
    
    # 信号定义
    statistics_updated = pyqtSignal(dict)  # 统计数据更新
    test_completed = pyqtSignal(dict)  # 测试完成统计
    
    def __init__(self, config_manager):
        """
        初始化测试统计管理器
        
        Args:
            config_manager: 配置管理器
        """
        super().__init__()
        
        self.config_manager = config_manager
        
        # 测试统计数据
        self.test_statistics = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_start_time': None,
            'test_end_time': None,
            'batch_info': {},
            'channel_statistics': {},
            'grade_statistics': {
                'rs_grades': {'1': 0, '2': 0, '3': 0},
                'rct_grades': {'1': 0, '2': 0, '3': 0}
            },
            'test_duration_total': 0.0,
            'average_test_duration': 0.0
        }
        
        logger.debug("测试统计管理器初始化完成")
    
    def reset_statistics(self):
        """重置统计数据"""
        try:
            self.test_statistics = {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'test_start_time': datetime.now(),
                'test_end_time': None,
                'batch_info': {},
                'channel_statistics': {},
                'grade_statistics': {
                    'rs_grades': {'1': 0, '2': 0, '3': 0},
                    'rct_grades': {'1': 0, '2': 0, '3': 0}
                },
                'test_duration_total': 0.0,
                'average_test_duration': 0.0
            }
            
            logger.info("测试统计数据已重置")
            self.statistics_updated.emit(self.test_statistics.copy())
            
        except Exception as e:
            logger.error(f"重置统计数据失败: {e}")
    
    def add_test_result(self, channel_num: int, test_result: Dict[str, Any]):
        """
        添加测试结果到统计
        
        Args:
            channel_num: 通道号
            test_result: 测试结果字典
        """
        try:
            # 更新总测试数
            self.test_statistics['total_tests'] += 1
            
            # 更新通过/失败统计
            is_pass = test_result.get('is_pass', False)
            if is_pass:
                self.test_statistics['passed_tests'] += 1
            else:
                self.test_statistics['failed_tests'] += 1
            
            # 更新通道统计
            if channel_num not in self.test_statistics['channel_statistics']:
                self.test_statistics['channel_statistics'][channel_num] = {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'last_result': None
                }
            
            channel_stats = self.test_statistics['channel_statistics'][channel_num]
            channel_stats['total'] += 1
            if is_pass:
                channel_stats['passed'] += 1
            else:
                channel_stats['failed'] += 1
            channel_stats['last_result'] = test_result
            
            # 更新档位统计
            rs_grade = test_result.get('rs_grade')
            rct_grade = test_result.get('rct_grade')
            
            if rs_grade and str(rs_grade) in self.test_statistics['grade_statistics']['rs_grades']:
                self.test_statistics['grade_statistics']['rs_grades'][str(rs_grade)] += 1
            
            if rct_grade and str(rct_grade) in self.test_statistics['grade_statistics']['rct_grades']:
                self.test_statistics['grade_statistics']['rct_grades'][str(rct_grade)] += 1
            
            # 更新测试时长统计
            test_duration = test_result.get('test_duration', 0.0)
            if test_duration > 0:
                self.test_statistics['test_duration_total'] += test_duration
                self.test_statistics['average_test_duration'] = (
                    self.test_statistics['test_duration_total'] / self.test_statistics['total_tests']
                )
            
            logger.debug(f"通道{channel_num}测试结果已添加到统计: {'通过' if is_pass else '失败'}")
            self.statistics_updated.emit(self.test_statistics.copy())
            
        except Exception as e:
            logger.error(f"添加测试结果到统计失败: {e}")
    
    def set_batch_info(self, batch_info: Dict[str, Any]):
        """
        设置批次信息
        
        Args:
            batch_info: 批次信息字典
        """
        try:
            self.test_statistics['batch_info'] = batch_info.copy()
            logger.info(f"批次信息已设置: {batch_info.get('batch_number', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"设置批次信息失败: {e}")
    
    def complete_test_session(self):
        """完成测试会话"""
        try:
            self.test_statistics['test_end_time'] = datetime.now()
            
            # 计算总测试时长
            if self.test_statistics['test_start_time']:
                total_session_time = (
                    self.test_statistics['test_end_time'] - 
                    self.test_statistics['test_start_time']
                ).total_seconds()
                self.test_statistics['total_session_time'] = total_session_time
            
            logger.info("测试会话已完成")
            self.test_completed.emit(self.test_statistics.copy())
            
        except Exception as e:
            logger.error(f"完成测试会话失败: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取当前统计数据
        
        Returns:
            统计数据字典
        """
        return self.test_statistics.copy()
    
    def get_yield_rate(self) -> float:
        """
        获取良率
        
        Returns:
            良率百分比
        """
        try:
            total = self.test_statistics['total_tests']
            if total == 0:
                return 0.0
            
            passed = self.test_statistics['passed_tests']
            return (passed / total) * 100.0
            
        except Exception as e:
            logger.error(f"计算良率失败: {e}")
            return 0.0
    
    def get_channel_yield_rate(self, channel_num: int) -> float:
        """
        获取指定通道的良率
        
        Args:
            channel_num: 通道号
            
        Returns:
            通道良率百分比
        """
        try:
            channel_stats = self.test_statistics['channel_statistics'].get(channel_num)
            if not channel_stats or channel_stats['total'] == 0:
                return 0.0
            
            return (channel_stats['passed'] / channel_stats['total']) * 100.0
            
        except Exception as e:
            logger.error(f"计算通道{channel_num}良率失败: {e}")
            return 0.0
    
    def get_grade_distribution(self) -> Dict[str, Dict[str, int]]:
        """
        获取档位分布统计
        
        Returns:
            档位分布字典
        """
        return self.test_statistics['grade_statistics'].copy()
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """
        生成汇总报告
        
        Returns:
            汇总报告字典
        """
        try:
            report = {
                'batch_info': self.test_statistics['batch_info'],
                'test_summary': {
                    'total_tests': self.test_statistics['total_tests'],
                    'passed_tests': self.test_statistics['passed_tests'],
                    'failed_tests': self.test_statistics['failed_tests'],
                    'yield_rate': self.get_yield_rate()
                },
                'time_summary': {
                    'start_time': self.test_statistics['test_start_time'],
                    'end_time': self.test_statistics['test_end_time'],
                    'total_duration': self.test_statistics.get('total_session_time', 0),
                    'average_test_duration': self.test_statistics['average_test_duration']
                },
                'channel_summary': {},
                'grade_distribution': self.get_grade_distribution()
            }
            
            # 生成通道汇总
            for channel_num, stats in self.test_statistics['channel_statistics'].items():
                report['channel_summary'][channel_num] = {
                    'total': stats['total'],
                    'passed': stats['passed'],
                    'failed': stats['failed'],
                    'yield_rate': self.get_channel_yield_rate(channel_num)
                }
            
            return report
            
        except Exception as e:
            logger.error(f"生成汇总报告失败: {e}")
            return {}
    
    def export_statistics_to_dict(self) -> Dict[str, Any]:
        """
        导出统计数据为字典格式
        
        Returns:
            可序列化的统计数据字典
        """
        try:
            export_data = self.test_statistics.copy()
            
            # 转换datetime对象为字符串
            if export_data['test_start_time']:
                export_data['test_start_time'] = export_data['test_start_time'].isoformat()
            
            if export_data['test_end_time']:
                export_data['test_end_time'] = export_data['test_end_time'].isoformat()
            
            return export_data
            
        except Exception as e:
            logger.error(f"导出统计数据失败: {e}")
            return {}
    
    def clear_statistics(self):
        """清空统计数据"""
        try:
            self.reset_statistics()
            logger.info("统计数据已清空")
            
        except Exception as e:
            logger.error(f"清空统计数据失败: {e}")
