# -*- coding: utf-8 -*-
"""
顶针寿命管理器
负责管理顶针寿命计数、归零操作和相关配置

Author: Jack
Date: 2025-06-21
"""

import logging
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ProbePinManager(QObject):
    """顶针寿命管理器"""
    
    # 信号定义
    lifetime_reset = pyqtSignal()  # 寿命归零信号
    warning_threshold_reached = pyqtSignal(int, int)  # 警告阈值达到信号 (通道号, 当前计数)
    max_lifetime_reached = pyqtSignal(int, int)  # 最大寿命达到信号 (通道号, 当前计数)
    test_count_updated = pyqtSignal(int, int)  # 测试计数更新信号 (通道号, 新计数)
    
    def __init__(self, config_manager, parent=None):
        """
        初始化顶针寿命管理器
        
        Args:
            config_manager: 配置管理器
            parent: 父对象
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        # 获取配置参数
        self.warning_threshold = self.config_manager.get('probe_pin.warning_threshold', 1000)
        self.max_lifetime = self.config_manager.get('probe_pin.max_lifetime', 10000)
        
        logger.debug(f"顶针寿命管理器初始化完成 - 警告阈值: {self.warning_threshold}, 最大寿命: {self.max_lifetime}")
    
    def get_test_count(self, channel_num: int) -> int:
        """
        获取指定通道的测试计数
        
        Args:
            channel_num: 通道号 (1-8)
            
        Returns:
            测试计数
        """
        try:
            count = self.config_manager.get(f'test_count.channel_{channel_num}', 0)
            return int(count)
        except Exception as e:
            logger.error(f"获取通道{channel_num}测试计数失败: {e}")
            return 0
    
    def increment_test_count(self, channel_num: int) -> int:
        """
        增加指定通道的测试计数
        
        Args:
            channel_num: 通道号 (1-8)
            
        Returns:
            新的测试计数
        """
        try:
            current_count = self.get_test_count(channel_num)
            new_count = current_count + 1
            
            # 更新配置
            self.config_manager.set(f'test_count.channel_{channel_num}', new_count)
            
            # 发送更新信号
            self.test_count_updated.emit(channel_num, new_count)
            
            # 检查是否达到警告阈值或最大寿命
            self._check_lifetime_thresholds(channel_num, new_count)
            
            logger.debug(f"通道{channel_num}测试计数已增加: {current_count} -> {new_count}")
            return new_count
            
        except Exception as e:
            logger.error(f"增加通道{channel_num}测试计数失败: {e}")
            return self.get_test_count(channel_num)
    
    def set_test_count(self, channel_num: int, count: int) -> bool:
        """
        设置指定通道的测试计数
        
        Args:
            channel_num: 通道号 (1-8)
            count: 新的测试计数
            
        Returns:
            是否设置成功
        """
        try:
            if count < 0:
                logger.warning(f"测试计数不能为负数: {count}")
                return False
            
            old_count = self.get_test_count(channel_num)
            
            # 更新配置
            self.config_manager.set(f'test_count.channel_{channel_num}', count)
            
            # 发送更新信号
            self.test_count_updated.emit(channel_num, count)
            
            # 检查是否达到警告阈值或最大寿命
            self._check_lifetime_thresholds(channel_num, count)
            
            logger.info(f"通道{channel_num}测试计数已设置: {old_count} -> {count}")
            return True
            
        except Exception as e:
            logger.error(f"设置通道{channel_num}测试计数失败: {e}")
            return False
    
    def reset_test_count(self, channel_num: int) -> bool:
        """
        重置指定通道的测试计数为0
        
        Args:
            channel_num: 通道号 (1-8)
            
        Returns:
            是否重置成功
        """
        try:
            return self.set_test_count(channel_num, 0)
        except Exception as e:
            logger.error(f"重置通道{channel_num}测试计数失败: {e}")
            return False
    
    def reset_all_test_counts(self) -> bool:
        """
        重置所有通道的测试计数为0
        
        Returns:
            是否重置成功
        """
        try:
            success_count = 0
            
            for channel_num in range(1, 9):
                if self.reset_test_count(channel_num):
                    success_count += 1
            
            # 发送寿命归零信号
            if success_count > 0:
                self.lifetime_reset.emit()
                logger.info(f"✅ 顶针寿命归零完成，成功重置{success_count}个通道")
            
            return success_count == 8
            
        except Exception as e:
            logger.error(f"重置所有通道测试计数失败: {e}")
            return False
    
    def get_all_test_counts(self) -> Dict[int, int]:
        """
        获取所有通道的测试计数
        
        Returns:
            通道号到测试计数的映射
        """
        try:
            counts = {}
            for channel_num in range(1, 9):
                counts[channel_num] = self.get_test_count(channel_num)
            return counts
        except Exception as e:
            logger.error(f"获取所有通道测试计数失败: {e}")
            return {}
    
    def get_lifetime_status(self, channel_num: int) -> Dict[str, Any]:
        """
        获取指定通道的寿命状态
        
        Args:
            channel_num: 通道号 (1-8)
            
        Returns:
            寿命状态信息
        """
        try:
            current_count = self.get_test_count(channel_num)
            
            # 计算百分比
            warning_percentage = (current_count / self.warning_threshold * 100) if self.warning_threshold > 0 else 0
            max_percentage = (current_count / self.max_lifetime * 100) if self.max_lifetime > 0 else 0
            
            # 确定状态
            if current_count >= self.max_lifetime:
                status = "exceeded"  # 超过最大寿命
                level = "critical"
            elif current_count >= self.warning_threshold:
                status = "warning"   # 达到警告阈值
                level = "warning"
            else:
                status = "normal"    # 正常
                level = "normal"
            
            return {
                'channel_num': channel_num,
                'current_count': current_count,
                'warning_threshold': self.warning_threshold,
                'max_lifetime': self.max_lifetime,
                'warning_percentage': min(warning_percentage, 100.0),
                'max_percentage': min(max_percentage, 100.0),
                'status': status,
                'level': level,
                'remaining_to_warning': max(0, self.warning_threshold - current_count),
                'remaining_to_max': max(0, self.max_lifetime - current_count)
            }
            
        except Exception as e:
            logger.error(f"获取通道{channel_num}寿命状态失败: {e}")
            return {
                'channel_num': channel_num,
                'current_count': 0,
                'warning_threshold': self.warning_threshold,
                'max_lifetime': self.max_lifetime,
                'warning_percentage': 0.0,
                'max_percentage': 0.0,
                'status': 'error',
                'level': 'error',
                'remaining_to_warning': self.warning_threshold,
                'remaining_to_max': self.max_lifetime
            }
    
    def get_all_lifetime_status(self) -> Dict[int, Dict[str, Any]]:
        """
        获取所有通道的寿命状态
        
        Returns:
            通道号到寿命状态的映射
        """
        try:
            status_dict = {}
            for channel_num in range(1, 9):
                status_dict[channel_num] = self.get_lifetime_status(channel_num)
            return status_dict
        except Exception as e:
            logger.error(f"获取所有通道寿命状态失败: {e}")
            return {}
    
    def update_thresholds(self, warning_threshold: Optional[int] = None, max_lifetime: Optional[int] = None) -> bool:
        """
        更新寿命阈值配置
        
        Args:
            warning_threshold: 新的警告阈值
            max_lifetime: 新的最大寿命
            
        Returns:
            是否更新成功
        """
        try:
            updated = False
            
            if warning_threshold is not None and warning_threshold > 0:
                self.warning_threshold = warning_threshold
                self.config_manager.set('probe_pin.warning_threshold', warning_threshold)
                updated = True
                logger.info(f"警告阈值已更新: {warning_threshold}")
            
            if max_lifetime is not None and max_lifetime > 0:
                self.max_lifetime = max_lifetime
                self.config_manager.set('probe_pin.max_lifetime', max_lifetime)
                updated = True
                logger.info(f"最大寿命已更新: {max_lifetime}")
            
            # 重新检查所有通道的阈值状态
            if updated:
                self._check_all_thresholds()
            
            return updated
            
        except Exception as e:
            logger.error(f"更新寿命阈值失败: {e}")
            return False
    
    def _check_lifetime_thresholds(self, channel_num: int, count: int):
        """
        检查指定通道是否达到寿命阈值
        
        Args:
            channel_num: 通道号
            count: 当前测试计数
        """
        try:
            # 检查是否达到最大寿命
            if count >= self.max_lifetime:
                logger.warning(f"通道{channel_num}达到最大寿命: {count}/{self.max_lifetime}")
                self.max_lifetime_reached.emit(channel_num, count)
            
            # 检查是否达到警告阈值
            elif count >= self.warning_threshold:
                logger.warning(f"通道{channel_num}达到警告阈值: {count}/{self.warning_threshold}")
                self.warning_threshold_reached.emit(channel_num, count)
                
        except Exception as e:
            logger.error(f"检查通道{channel_num}寿命阈值失败: {e}")
    
    def _check_all_thresholds(self):
        """检查所有通道的寿命阈值"""
        try:
            for channel_num in range(1, 9):
                count = self.get_test_count(channel_num)
                self._check_lifetime_thresholds(channel_num, count)
        except Exception as e:
            logger.error(f"检查所有通道寿命阈值失败: {e}")
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        获取顶针寿命统计摘要
        
        Returns:
            统计摘要信息
        """
        try:
            all_counts = self.get_all_test_counts()
            
            if not all_counts:
                return {
                    'total_tests': 0,
                    'average_count': 0.0,
                    'max_count': 0,
                    'min_count': 0,
                    'channels_at_warning': 0,
                    'channels_at_max': 0,
                    'channels_normal': 8
                }
            
            counts = list(all_counts.values())
            total_tests = sum(counts)
            average_count = total_tests / len(counts) if counts else 0.0
            max_count = max(counts) if counts else 0
            min_count = min(counts) if counts else 0
            
            # 统计各状态通道数
            channels_at_warning = 0
            channels_at_max = 0
            channels_normal = 0
            
            for count in counts:
                if count >= self.max_lifetime:
                    channels_at_max += 1
                elif count >= self.warning_threshold:
                    channels_at_warning += 1
                else:
                    channels_normal += 1
            
            return {
                'total_tests': total_tests,
                'average_count': round(average_count, 2),
                'max_count': max_count,
                'min_count': min_count,
                'channels_at_warning': channels_at_warning,
                'channels_at_max': channels_at_max,
                'channels_normal': channels_normal,
                'warning_threshold': self.warning_threshold,
                'max_lifetime': self.max_lifetime
            }
            
        except Exception as e:
            logger.error(f"获取顶针寿命统计摘要失败: {e}")
            return {}
    
    def export_lifetime_data(self) -> Dict[str, Any]:
        """
        导出顶针寿命数据
        
        Returns:
            完整的寿命数据
        """
        try:
            return {
                'test_counts': self.get_all_test_counts(),
                'lifetime_status': self.get_all_lifetime_status(),
                'summary_statistics': self.get_summary_statistics(),
                'configuration': {
                    'warning_threshold': self.warning_threshold,
                    'max_lifetime': self.max_lifetime
                },
                'export_timestamp': self._get_current_timestamp()
            }
        except Exception as e:
            logger.error(f"导出顶针寿命数据失败: {e}")
            return {}
    
    def import_lifetime_data(self, data: Dict[str, Any]) -> bool:
        """
        导入顶针寿命数据
        
        Args:
            data: 要导入的寿命数据
            
        Returns:
            是否导入成功
        """
        try:
            success_count = 0
            
            # 导入测试计数
            if 'test_counts' in data:
                test_counts = data['test_counts']
                for channel_num, count in test_counts.items():
                    if isinstance(channel_num, str):
                        channel_num = int(channel_num)
                    if self.set_test_count(channel_num, count):
                        success_count += 1
            
            # 导入配置
            if 'configuration' in data:
                config = data['configuration']
                warning_threshold = config.get('warning_threshold')
                max_lifetime = config.get('max_lifetime')
                self.update_thresholds(warning_threshold, max_lifetime)
            
            logger.info(f"顶针寿命数据导入完成，成功导入{success_count}个通道")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"导入顶针寿命数据失败: {e}")
            return False
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        try:
            from datetime import datetime
            return datetime.now().isoformat()
        except Exception:
            return ""
