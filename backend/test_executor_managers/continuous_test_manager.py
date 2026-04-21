# -*- coding: utf-8 -*-
"""
连续测试管理器
负责连续测试模式的执行、计数管理、统计数据收集等功能

Author: Jack
Date: 2025-06-27
"""

import logging
import time
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ContinuousTestManager(QObject):
    """连续测试管理器"""
    
    # 信号定义
    continuous_test_started = pyqtSignal(dict)  # 连续测试开始信号 (config)
    continuous_test_stopped = pyqtSignal(str)  # 连续测试停止信号 (reason)
    cycle_completed = pyqtSignal(int, bool, float)  # 测试周期完成信号 (cycle_num, success, duration)
    count_updated = pyqtSignal(int)  # 计数更新信号 (count)
    statistics_updated = pyqtSignal(dict)  # 统计数据更新信号 (statistics)
    
    def __init__(self, parent=None):
        """
        初始化连续测试管理器
        
        Args:
            parent: 父对象
        """
        super().__init__(parent)
        
        # 连续测试状态
        self.continuous_test_count = 0
        self.continuous_test_statistics = {
            'start_time': None,
            'end_time': None,
            'total_cycles': 0,
            'successful_cycles': 0,
            'failed_cycles': 0,
            'cycle_times': [],
            'average_cycle_time': 0.0,
            'total_duration': 0.0
        }
        
        # 配置
        self.count_file_path = "data/continuous_test_count.json"
        
        # 加载保存的计数
        self._load_continuous_test_count()
        
    def _load_continuous_test_count(self) -> int:
        """
        加载保存的连续测试计数
        
        Returns:
            加载的计数值
        """
        try:
            if os.path.exists(self.count_file_path):
                with open(self.count_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    count = data.get('count', 0)
                    self.continuous_test_count = count
                    return count
            else:
                logger.debug("连续测试计数文件不存在，使用默认值0")
                return 0
        except Exception as e:
            logger.error(f"加载连续测试计数失败: {e}")
            return 0

    def _save_continuous_test_count(self):
        """保存当前的连续测试计数"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.count_file_path), exist_ok=True)
            
            data = {
                'count': self.continuous_test_count,
                'last_updated': datetime.now().isoformat(),
                'statistics': self.continuous_test_statistics
            }
            
            with open(self.count_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"连续测试计数已保存: {self.continuous_test_count}")
            
        except Exception as e:
            logger.error(f"保存连续测试计数失败: {e}")

    def reset_continuous_test_count(self):
        """重置连续测试计数（手动调用）"""
        try:
            self.continuous_test_count = 0
            self._save_continuous_test_count()
            self.count_updated.emit(self.continuous_test_count)
            logger.info("🔄 连续测试计数已重置为0")
        except Exception as e:
            logger.error(f"重置连续测试计数失败: {e}")

    def start_continuous_test(self, test_config: Dict[str, Any]) -> bool:
        """
        启动连续测试
        
        Args:
            test_config: 测试配置
            
        Returns:
            是否启动成功
        """
        try:
            logger.info("🔄 启动连续测试模式")
            
            # 验证连续测试配置
            if not self._validate_continuous_config(test_config):
                return False
            
            # 重置统计数据
            self._reset_statistics()
            
            # 记录开始时间
            self.continuous_test_statistics['start_time'] = time.time()
            
            # 发送连续测试开始信号
            self.continuous_test_started.emit(test_config)
            
            logger.info("✅ 连续测试模式启动成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动连续测试失败: {e}")
            return False

    def stop_continuous_test(self, reason: str = "用户停止"):
        """
        停止连续测试
        
        Args:
            reason: 停止原因
        """
        try:
            logger.info(f"🛑 停止连续测试: {reason}")
            
            # 记录结束时间
            self.continuous_test_statistics['end_time'] = time.time()
            
            # 计算总持续时间
            if self.continuous_test_statistics['start_time']:
                self.continuous_test_statistics['total_duration'] = (
                    self.continuous_test_statistics['end_time'] - 
                    self.continuous_test_statistics['start_time']
                )
            
            # 计算平均周期时间
            self._calculate_average_cycle_time()
            
            # 保存最终统计数据
            self._save_continuous_test_count()
            
            # 发送连续测试停止信号
            self.continuous_test_stopped.emit(reason)
            
            # 发送最终统计数据
            self.statistics_updated.emit(self.continuous_test_statistics)
            
            logger.info(f"✅ 连续测试停止完成: {reason}")
            
        except Exception as e:
            logger.error(f"❌ 停止连续测试失败: {e}")

    def execute_test_cycle(self, test_config: Dict[str, Any], enabled_channels: List[int], 
                          single_test_executor) -> bool:
        """
        执行一个测试周期
        
        Args:
            test_config: 测试配置
            enabled_channels: 启用的通道列表
            single_test_executor: 单次测试执行器函数
            
        Returns:
            本周期是否成功
        """
        try:
            # 增加测试计数
            self.continuous_test_count += 1
            
            # 记录周期开始时间
            cycle_start_time = time.time()
            
            logger.info(f"🎯 执行第{self.continuous_test_count}轮测试...")
            
            # 执行单次测试
            success = single_test_executor(test_config, enabled_channels)
            
            # 记录周期结束时间
            cycle_end_time = time.time()
            cycle_duration = cycle_end_time - cycle_start_time
            
            # 更新统计数据
            self._update_cycle_statistics(success, cycle_duration)
            
            # 保存计数
            self._save_continuous_test_count()
            
            # 发送信号
            self.cycle_completed.emit(self.continuous_test_count, success, cycle_duration)
            self.count_updated.emit(self.continuous_test_count)
            self.statistics_updated.emit(self.continuous_test_statistics)
            
            if success:
                logger.info(f"✅ 第{self.continuous_test_count}轮测试完成，耗时: {cycle_duration:.2f}秒")
            else:
                logger.warning(f"⚠️ 第{self.continuous_test_count}轮测试失败，继续下一轮")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 执行测试周期失败: {e}")
            return False

    def should_continue_testing(self, test_config: Dict[str, Any]) -> bool:
        """
        检查是否应该继续测试
        
        Args:
            test_config: 测试配置
            
        Returns:
            是否应该继续
        """
        try:
            # 检查是否启用计数限制
            count_limit_enabled = test_config.get('count_limit_enabled', False)
            max_count = test_config.get('max_count', 100)
            
            if count_limit_enabled and self.continuous_test_count >= max_count:
                logger.info(f"🏁 达到最大测试次数限制: {max_count}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查是否继续测试失败: {e}")
            return False

    def wait_for_next_cycle(self, test_config: Dict[str, Any], stop_event) -> bool:
        """
        等待下一个测试周期
        
        Args:
            test_config: 测试配置
            stop_event: 停止事件
            
        Returns:
            是否应该继续（False表示收到停止信号）
        """
        try:
            interval = test_config.get('interval', 2)
            
            logger.debug(f"⏳ 等待{interval}秒后开始下一轮测试...")
            
            # 分段等待，以便及时响应停止信号
            wait_time = 0
            while wait_time < interval:
                if stop_event.is_set():
                    logger.info("收到停止信号，终止连续测试")
                    return False
                
                time.sleep(0.1)
                wait_time += 0.1
            
            return True
            
        except Exception as e:
            logger.error(f"等待下一个测试周期失败: {e}")
            return False

    def _validate_continuous_config(self, test_config: Dict[str, Any]) -> bool:
        """验证连续测试配置"""
        try:
            continuous_mode = test_config.get('continuous_mode', False)
            if not continuous_mode:
                logger.error("❌ 连续测试模式未启用，无法执行连续测试")
                return False
            
            # 验证其他必要配置
            interval = test_config.get('interval', 2)
            if interval < 0:
                logger.error(f"❌ 无效的测试间隔: {interval}")
                return False
            
            count_limit_enabled = test_config.get('count_limit_enabled', False)
            if count_limit_enabled:
                max_count = test_config.get('max_count', 100)
                if max_count <= 0:
                    logger.error(f"❌ 无效的最大测试次数: {max_count}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证连续测试配置失败: {e}")
            return False

    def _reset_statistics(self):
        """重置统计数据"""
        self.continuous_test_statistics = {
            'start_time': None,
            'end_time': None,
            'total_cycles': 0,
            'successful_cycles': 0,
            'failed_cycles': 0,
            'cycle_times': [],
            'average_cycle_time': 0.0,
            'total_duration': 0.0
        }

    def _update_cycle_statistics(self, success: bool, cycle_duration: float):
        """更新周期统计数据"""
        try:
            self.continuous_test_statistics['total_cycles'] = self.continuous_test_count
            self.continuous_test_statistics['cycle_times'].append(cycle_duration)
            
            if success:
                self.continuous_test_statistics['successful_cycles'] += 1
            else:
                self.continuous_test_statistics['failed_cycles'] += 1
            
            # 计算平均周期时间
            self._calculate_average_cycle_time()
            
        except Exception as e:
            logger.error(f"更新周期统计数据失败: {e}")

    def _calculate_average_cycle_time(self):
        """计算平均周期时间"""
        try:
            cycle_times = self.continuous_test_statistics['cycle_times']
            if cycle_times:
                self.continuous_test_statistics['average_cycle_time'] = sum(cycle_times) / len(cycle_times)
            else:
                self.continuous_test_statistics['average_cycle_time'] = 0.0
        except Exception as e:
            logger.error(f"计算平均周期时间失败: {e}")

    def get_continuous_test_count(self) -> int:
        """获取当前连续测试计数"""
        return self.continuous_test_count

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计数据"""
        return self.continuous_test_statistics.copy()

    def export_statistics(self, file_path: str) -> bool:
        """
        导出统计数据到文件
        
        Args:
            file_path: 导出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            export_data = {
                'continuous_test_count': self.continuous_test_count,
                'statistics': self.continuous_test_statistics,
                'export_time': datetime.now().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"统计数据已导出到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出统计数据失败: {e}")
            return False

    def cleanup(self):
        """清理资源"""
        try:
            # 保存最终数据
            self._save_continuous_test_count()
            
            logger.debug("连续测试管理器资源已清理")
            
        except Exception as e:
            logger.error(f"清理连续测试管理器资源失败: {e}")
