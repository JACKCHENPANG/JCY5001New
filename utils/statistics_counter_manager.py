#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计计数器管理器

负责管理独立的统计计数器，实现持久化存储，
解决清除统计数据后重新从数据库读取历史数据的问题。

作者：Jack
日期：2025-01-31
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StatisticsCounterManager:
    """统计计数器管理器"""
    
    def __init__(self, config_manager):
        """
        初始化统计计数器管理器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        
        # 计数器文件路径
        self.counter_file_path = os.path.join(
            self.config_manager.get('app.data_dir', 'data'),
            'statistics_counter.json'
        )
        
        # 默认计数器数据
        self.default_counters = {
            'total_count': 0,
            'pass_count': 0,
            'fail_count': 0,
            'grade_distribution': {
                'Rs1-Rct1': 0, 'Rs1-Rct2': 0, 'Rs1-Rct3': 0,
                'Rs2-Rct1': 0, 'Rs2-Rct2': 0, 'Rs2-Rct3': 0,
                'Rs3-Rct1': 0, 'Rs3-Rct2': 0, 'Rs3-Rct3': 0
            },
            'last_clear_time': None,
            'created_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'updated_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 当前计数器数据
        self.counters = self.default_counters.copy()
        
        # 加载计数器数据
        self._load_counters()
        
        logger.debug("统计计数器管理器初始化完成")
    
    def _load_counters(self):
        """加载计数器数据"""
        try:
            if os.path.exists(self.counter_file_path):
                with open(self.counter_file_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    
                # 合并默认数据和加载的数据
                self.counters.update(loaded_data)
                
                # 确保所有必需的字段都存在
                for key, value in self.default_counters.items():
                    if key not in self.counters:
                        self.counters[key] = value
                
                # 确保档位分布数据完整
                for grade_key in self.default_counters['grade_distribution']:
                    if grade_key not in self.counters['grade_distribution']:
                        self.counters['grade_distribution'][grade_key] = 0
                
                logger.info(f"成功加载统计计数器数据: {self.counter_file_path}")
            else:
                logger.info("计数器文件不存在，使用默认数据")
                self._save_counters()
                
        except Exception as e:
            logger.error(f"加载统计计数器失败: {e}")
            self.counters = self.default_counters.copy()
    
    def _save_counters(self):
        """保存计数器数据"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.counter_file_path), exist_ok=True)
            
            # 更新时间戳
            self.counters['updated_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 保存到文件
            with open(self.counter_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.counters, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"统计计数器数据已保存: {self.counter_file_path}")
            
        except Exception as e:
            logger.error(f"保存统计计数器失败: {e}")
    
    def add_test_result(self, is_pass: bool, rs_grade: Optional[int] = None, rct_grade: Optional[int] = None):
        """
        添加测试结果到计数器

        Args:
            is_pass: 是否通过测试
            rs_grade: Rs档位 (整数: 1, 2, 3 或 None)
            rct_grade: Rct档位 (整数: 1, 2, 3 或 None)
        """
        try:
            old_total = self.counters['total_count']
            
            # 更新总数
            self.counters['total_count'] += 1

            # 更新通过/失败数
            if is_pass:
                self.counters['pass_count'] += 1

                # 更新档位分布（只统计合格的）
                if rs_grade is not None and rct_grade is not None:
                    grade_key = f"Rs{rs_grade}-Rct{rct_grade}"
                    if grade_key in self.counters['grade_distribution']:
                        self.counters['grade_distribution'][grade_key] += 1
                        logger.debug(f"🔢 [计数器] 档位分布更新: {grade_key} = {self.counters['grade_distribution'][grade_key]}")
                    else:
                        logger.warning(f"🔢 [计数器] 档位组合不存在: {grade_key}")
                else:
                    logger.debug(f"🔢 [计数器] 档位为None，不更新分布: Rs={rs_grade}, Rct={rct_grade}")
            else:
                self.counters['fail_count'] += 1

            # 保存数据
            self._save_counters()

            # 最终修复详细的统计变化日志
            logger.info(f"🔢 [计数器] 统计更新: {old_total} -> {self.counters['total_count']} (增加1), 通过={is_pass}, Rs档位={rs_grade}, Rct档位={rct_grade}")
            logger.info(f"🔢 [计数器] 当前统计: 总数={self.counters['total_count']}, 合格={self.counters['pass_count']}, 不合格={self.counters['fail_count']}")

        except Exception as e:
            logger.error(f"添加测试结果到计数器失败: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取当前统计数据
        
        Returns:
            统计数据字典
        """
        try:
            total = self.counters['total_count']
            passed = self.counters['pass_count']
            failed = self.counters['fail_count']
            
            # 计算良率
            yield_rate = (passed / total * 100) if total > 0 else 0.0
            
            return {
                'total_count': total,
                'pass_count': passed,
                'fail_count': failed,
                'yield_rate': yield_rate,
                'grade_distribution': self.counters['grade_distribution'].copy(),
                'last_clear_time': self.counters.get('last_clear_time'),
                'updated_time': self.counters.get('updated_time')
            }
            
        except Exception as e:
            logger.error(f"获取统计数据失败: {e}")
            return {
                'total_count': 0,
                'pass_count': 0,
                'fail_count': 0,
                'yield_rate': 0.0,
                'grade_distribution': {},
                'last_clear_time': None,
                'updated_time': None
            }
    
    def clear_statistics(self):
        """清除统计数据"""
        try:
            # 记录清除时间
            clear_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 重置计数器
            self.counters['total_count'] = 0
            self.counters['pass_count'] = 0
            self.counters['fail_count'] = 0
            self.counters['last_clear_time'] = clear_time
            
            # 重置档位分布
            for grade_key in self.counters['grade_distribution']:
                self.counters['grade_distribution'][grade_key] = 0
            
            # 保存数据
            self._save_counters()
            
            logger.info(f"统计数据已清除，清除时间: {clear_time}")
            
        except Exception as e:
            logger.error(f"清除统计数据失败: {e}")
    
    def reset_to_defaults(self):
        """重置为默认值"""
        try:
            self.counters = self.default_counters.copy()
            self.counters['created_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_counters()
            
            logger.info("统计计数器已重置为默认值")
            
        except Exception as e:
            logger.error(f"重置统计计数器失败: {e}")
    
    def get_counter_file_info(self) -> Dict[str, Any]:
        """
        获取计数器文件信息
        
        Returns:
            文件信息字典
        """
        try:
            if os.path.exists(self.counter_file_path):
                stat = os.stat(self.counter_file_path)
                return {
                    'file_path': self.counter_file_path,
                    'file_size': stat.st_size,
                    'modified_time': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    'exists': True
                }
            else:
                return {
                    'file_path': self.counter_file_path,
                    'file_size': 0,
                    'modified_time': None,
                    'exists': False
                }
                
        except Exception as e:
            logger.error(f"获取计数器文件信息失败: {e}")
            return {
                'file_path': self.counter_file_path,
                'file_size': 0,
                'modified_time': None,
                'exists': False,
                'error': str(e)
            }
