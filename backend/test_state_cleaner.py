#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试状态清理管理器

负责在每次测试开始前清除所有上次测试遗留的状态和数据，
确保测试环境的干净和准确性。

功能包括：
1. 清除测试结果数据
2. 重置界面状态
3. 清理测试状态
4. 清除数据缓存

作者：Jack
日期：2025-01-31
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TestStateCleaner:
    """测试状态清理管理器"""
    
    def __init__(self):
        """初始化测试状态清理管理器"""
        self.cleanup_history = []
        self.last_cleanup_time = None
        
        logger.debug("测试状态清理管理器初始化完成")
    
    def clean_all_test_states(self, channel_widgets: List, test_managers: Optional[Dict] = None) -> bool:
        """
        清除所有测试状态和数据
        
        Args:
            channel_widgets: 通道组件列表
            test_managers: 测试管理器字典（可选）
            
        Returns:
            是否清理成功
        """
        try:
            import time
            cleanup_start_time = datetime.now()
            perf_start_time = time.time()
            logger.info("🧹 开始全面清理测试状态...")
            
            # 记录清理开始
            cleanup_record = {
                'start_time': cleanup_start_time,
                'channels_count': len(channel_widgets),
                'managers_count': len(test_managers) if test_managers else 0,
                'success': False,
                'details': {}
            }
            
            # 1. 清除通道测试数据
            channel_success = self._clean_channel_test_data(channel_widgets)
            cleanup_record['details']['channels'] = channel_success
            
            # 2. 重置通道界面状态
            ui_success = self._reset_channel_ui_states(channel_widgets)
            cleanup_record['details']['ui'] = ui_success
            
            # 3. 清理通道测试状态
            state_success = self._clear_channel_test_states(channel_widgets)
            cleanup_record['details']['states'] = state_success
            
            # 4. 清除数据缓存
            cache_success = self._clear_data_caches(channel_widgets)
            cleanup_record['details']['cache'] = cache_success
            
            # 5. 重置测试管理器（如果提供）
            manager_success = True
            if test_managers:
                manager_success = self._reset_test_managers(test_managers)
                cleanup_record['details']['managers'] = manager_success
            
            # 计算总体成功率
            total_success = all([channel_success, ui_success, state_success, cache_success, manager_success])
            cleanup_record['success'] = total_success
            cleanup_record['end_time'] = datetime.now()
            cleanup_record['duration'] = (cleanup_record['end_time'] - cleanup_start_time).total_seconds()
            
            # 记录清理历史
            self.cleanup_history.append(cleanup_record)
            self.last_cleanup_time = cleanup_start_time
            
            perf_total_time = time.time() - perf_start_time
            if total_success:
                logger.info(f"✅ 测试状态清理完成，耗时 {cleanup_record['duration']:.2f}秒 (性能监控: {perf_total_time:.3f}秒)")
            else:
                logger.warning(f"⚠️ 测试状态清理部分失败，详情: {cleanup_record['details']}")

            return total_success
            
        except Exception as e:
            logger.error(f"❌ 测试状态清理失败: {e}")
            return False
    
    def _clean_channel_test_data(self, channel_widgets: List) -> bool:
        """清除通道测试结果数据"""
        try:
            logger.debug("🧹 清除通道测试结果数据...")
            success_count = 0
            
            for channel_widget in channel_widgets:
                try:
                    # 修复检查通道是否有测试结果，如果有则不清除数据
                    has_test_result = False
                    if hasattr(channel_widget, 'test_result') and channel_widget.test_result:
                        has_test_result = True
                    elif (hasattr(channel_widget, 'rs_value') and hasattr(channel_widget, 'rct_value') and
                          channel_widget.rs_value > 0 and channel_widget.rct_value > 0):
                        has_test_result = True

                    if has_test_result:
                        logger.debug(f"通道{getattr(channel_widget, 'channel_number', '?')}有测试结果，跳过数据清理")
                        success_count += 1
                        continue

                    # 清除测试结果数据（只有在没有测试结果时才清除）
                    if hasattr(channel_widget, 'clear_previous_results'):
                        channel_widget.clear_previous_results()

                    # 重置测试数据（只有在没有测试结果时才重置）
                    if hasattr(channel_widget, 'reset_test_data'):
                        try:
                            channel_widget.reset_test_data()
                        except AttributeError as e:
                            if 'clear_frequency_info' in str(e):
                                logger.debug(f"通道{getattr(channel_widget, 'channel_number', '?')}频点显示功能已移除，跳过相关清理")
                            else:
                                raise e

                    # 清除测试结果（只有在没有测试结果时才清除）
                    if hasattr(channel_widget, 'test_result'):
                        channel_widget.test_result = None

                    # 重置数值显示（只有在没有测试结果时才重置）
                    if hasattr(channel_widget, 'voltage'):
                        channel_widget.voltage = 0.0
                    if hasattr(channel_widget, 'rs_value'):
                        channel_widget.rs_value = 0.0
                    if hasattr(channel_widget, 'rct_value'):
                        channel_widget.rct_value = 0.0

                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"清除通道{getattr(channel_widget, 'channel_number', '?')}测试数据失败: {e}")
            
            success_rate = success_count / len(channel_widgets) if channel_widgets else 1.0
            logger.debug(f"✅ 通道测试数据清除完成: {success_count}/{len(channel_widgets)} ({success_rate:.1%})")
            
            return success_rate >= 0.8  # 80%成功率认为成功
            
        except Exception as e:
            logger.error(f"❌ 清除通道测试数据失败: {e}")
            return False
    
    def _reset_channel_ui_states(self, channel_widgets: List) -> bool:
        """重置通道界面状态"""
        try:
            logger.debug("🧹 重置通道界面状态...")
            success_count = 0
            
            for channel_widget in channel_widgets:
                try:
                    # 修复检查通道是否有测试结果，如果有则不重置UI显示
                    has_test_result = False
                    if hasattr(channel_widget, 'test_result') and channel_widget.test_result:
                        has_test_result = True
                    elif (hasattr(channel_widget, 'rs_value') and hasattr(channel_widget, 'rct_value') and
                          channel_widget.rs_value > 0 and channel_widget.rct_value > 0):
                        has_test_result = True

                    if has_test_result:
                        logger.debug(f"通道{getattr(channel_widget, 'channel_number', '?')}有测试结果，跳过UI重置")
                        success_count += 1
                        continue

                    # 重置进度条（只有在没有测试结果时才重置）
                    if hasattr(channel_widget, 'progress_bar'):
                        channel_widget.progress_bar.setValue(0)

                    # 重置进度状态（只有在没有测试结果时才重置）
                    if hasattr(channel_widget, 'current_progress'):
                        channel_widget.current_progress = 0
                    if hasattr(channel_widget, 'max_progress_reached'):
                        channel_widget.max_progress_reached = 0
                    if hasattr(channel_widget, 'test_progress'):
                        channel_widget.test_progress = 0

                    # 重置结果显示（只有在没有测试结果时才重置）
                    if hasattr(channel_widget, 'result_label'):
                        channel_widget.result_label.setText("待测试")
                        channel_widget.result_label.setObjectName("resultWaiting")
                        channel_widget.result_label.setStyleSheet("")

                    # 重置档位显示（只有在没有测试结果时才重置）
                    if hasattr(channel_widget, 'grade_label'):
                        channel_widget.grade_label.setText("--")
                        channel_widget.grade_label.setStyleSheet("")

                    # 重置测试时间显示（只有在没有测试结果时才重置）
                    if hasattr(channel_widget, 'test_time_label'):
                        channel_widget.test_time_label.setText("00:00:00")

                    # 重置数值标签显示（只有在没有测试结果时才重置）
                    if hasattr(channel_widget, 'voltage_label'):
                        channel_widget.voltage_label.setText("0.000")
                    if hasattr(channel_widget, 'rs_label'):
                        channel_widget.rs_label.setText("0.000")
                    if hasattr(channel_widget, 'rct_label'):
                        channel_widget.rct_label.setText("0.000")

                    # 清除频点信息（只有在没有测试结果时才清除）
                    if hasattr(channel_widget, 'clear_frequency_info'):
                        channel_widget.clear_frequency_info()

                    # 重置离群率显示（只有在没有测试结果时才重置）
                    if hasattr(channel_widget, 'outlier_rate_result'):
                        channel_widget.outlier_rate_result = "--"
                    if hasattr(channel_widget, 'outlier_rate_label'):
                        channel_widget.outlier_rate_label.setText("等待")

                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"重置通道{getattr(channel_widget, 'channel_number', '?')}界面状态失败: {e}")
            
            success_rate = success_count / len(channel_widgets) if channel_widgets else 1.0
            logger.debug(f"✅ 通道界面状态重置完成: {success_count}/{len(channel_widgets)} ({success_rate:.1%})")
            
            return success_rate >= 0.8
            
        except Exception as e:
            logger.error(f"❌ 重置通道界面状态失败: {e}")
            return False
    
    def _clear_channel_test_states(self, channel_widgets: List) -> bool:
        """清理通道测试状态"""
        try:
            logger.debug("🧹 清理通道测试状态...")
            success_count = 0
            
            for channel_widget in channel_widgets:
                try:
                    # 重置测试时间
                    if hasattr(channel_widget, 'test_start_time'):
                        channel_widget.test_start_time = None
                    if hasattr(channel_widget, 'test_end_time'):
                        channel_widget.test_end_time = None
                    
                    # 清除异常状态标记
                    if hasattr(channel_widget, 'error_message'):
                        channel_widget.error_message = None
                    if hasattr(channel_widget, 'status_code'):
                        channel_widget.status_code = None
                    
                    # 修复强制重置进度状态，解决进度回退警告
                    if hasattr(channel_widget, 'reset_progress_state'):
                        channel_widget.reset_progress_state(force_reset=True)
                        logger.debug(f"通道{getattr(channel_widget, 'channel_number', '?')}进度状态已强制重置")

                    # 修复检查通道是否有测试结果，如果有则不重置状态
                    has_test_result = False
                    if hasattr(channel_widget, 'test_result') and channel_widget.test_result:
                        has_test_result = True
                    elif (hasattr(channel_widget, 'rs_value') and hasattr(channel_widget, 'rct_value') and
                          channel_widget.rs_value > 0 and channel_widget.rct_value > 0):
                        has_test_result = True

                    # 重置测试状态（只有在没有测试结果时才重置）
                    if hasattr(channel_widget, 'set_test_state'):
                        if has_test_result:
                            logger.debug(f"通道{getattr(channel_widget, 'channel_number', '?')}有测试结果，保持当前状态")
                        else:
                            if hasattr(channel_widget, 'is_enabled') and channel_widget.is_enabled:
                                channel_widget.set_test_state("idle")
                            else:
                                channel_widget.set_test_state("disabled")
                    
                    # 重置计时器状态
                    if hasattr(channel_widget, 'timer_manager'):
                        channel_widget.timer_manager.stop_timer()
                        channel_widget.timer_manager.reset_timer()
                    
                    # 清除状态管理器状态（只有在没有测试结果时才清除）
                    if hasattr(channel_widget, 'state_manager') and not has_test_result:
                        if hasattr(channel_widget.state_manager, 'reset_state'):
                            channel_widget.state_manager.reset_state()
                        if hasattr(channel_widget.state_manager, 'clear_error_state'):
                            channel_widget.state_manager.clear_error_state()
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"清理通道{getattr(channel_widget, 'channel_number', '?')}测试状态失败: {e}")
            
            success_rate = success_count / len(channel_widgets) if channel_widgets else 1.0
            logger.debug(f"✅ 通道测试状态清理完成: {success_count}/{len(channel_widgets)} ({success_rate:.1%})")
            
            return success_rate >= 0.8
            
        except Exception as e:
            logger.error(f"❌ 清理通道测试状态失败: {e}")
            return False
    
    def _clear_data_caches(self, channel_widgets: List) -> bool:
        """清除数据缓存"""
        try:
            logger.debug("🧹 清除数据缓存...")
            success_count = 0
            
            for channel_widget in channel_widgets:
                try:
                    # 清除测试数据缓存
                    if hasattr(channel_widget, 'test_data_cache'):
                        if hasattr(channel_widget.test_data_cache, 'clear'):
                            channel_widget.test_data_cache.clear()
                        else:
                            channel_widget.test_data_cache = {}
                    
                    # 重置测试计数器
                    if hasattr(channel_widget, 'test_count'):
                        channel_widget.test_count = 0
                    if hasattr(channel_widget, 'measurement_count'):
                        channel_widget.measurement_count = 0
                    
                    # 清除频率数据缓存
                    if hasattr(channel_widget, 'frequency_data'):
                        channel_widget.frequency_data = {}
                    
                    # 清除阻抗数据缓存
                    if hasattr(channel_widget, 'impedance_data'):
                        channel_widget.impedance_data = []
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"清除通道{getattr(channel_widget, 'channel_number', '?')}数据缓存失败: {e}")
            
            success_rate = success_count / len(channel_widgets) if channel_widgets else 1.0
            logger.debug(f"✅ 数据缓存清除完成: {success_count}/{len(channel_widgets)} ({success_rate:.1%})")
            
            return success_rate >= 0.8
            
        except Exception as e:
            logger.error(f"❌ 清除数据缓存失败: {e}")
            return False
    
    def _reset_test_managers(self, test_managers: Dict) -> bool:
        """重置测试管理器"""
        try:
            logger.debug("🧹 重置测试管理器...")
            success_count = 0
            
            for manager_name, manager in test_managers.items():
                try:
                    # 停止测试管理器
                    if hasattr(manager, 'stop_test'):
                        manager.stop_test()
                    elif hasattr(manager, 'stop_simultaneous_test'):
                        manager.stop_simultaneous_test()
                    elif hasattr(manager, 'stop'):
                        manager.stop()
                    
                    # 清除测试结果
                    if hasattr(manager, 'test_results'):
                        manager.test_results.clear()
                    if hasattr(manager, 'error_info'):
                        manager.error_info.clear()
                    
                    # 重置状态
                    if hasattr(manager, 'state'):
                        # 尝试设置为IDLE状态
                        if hasattr(manager, '_set_state'):
                            try:
                                # 导入相应的状态枚举
                                if 'simultaneous' in manager_name.lower():
                                    from backend.simultaneous_test_manager import SimultaneousTestState
                                    manager._set_state(SimultaneousTestState.IDLE)
                                elif 'parallel' in manager_name.lower():
                                    from backend.parallel_staggered_test_manager import ParallelStaggeredTestState
                                    manager._set_state(ParallelStaggeredTestState.IDLE)
                            except ImportError:
                                logger.debug(f"无法导入{manager_name}的状态枚举，跳过状态重置")
                    
                    # 清除配置
                    if hasattr(manager, 'config'):
                        manager.config = None
                    
                    # 重置计数器
                    if hasattr(manager, 'current_frequency_index'):
                        manager.current_frequency_index = 0
                    
                    success_count += 1
                    logger.debug(f"✅ 测试管理器 {manager_name} 重置成功")
                    
                except Exception as e:
                    logger.error(f"重置测试管理器 {manager_name} 失败: {e}")
            
            success_rate = success_count / len(test_managers) if test_managers else 1.0
            logger.debug(f"✅ 测试管理器重置完成: {success_count}/{len(test_managers)} ({success_rate:.1%})")
            
            return success_rate >= 0.8
            
        except Exception as e:
            logger.error(f"❌ 重置测试管理器失败: {e}")
            return False
    
    def get_cleanup_statistics(self) -> Dict[str, Any]:
        """获取清理统计信息"""
        try:
            if not self.cleanup_history:
                return {
                    'total_cleanups': 0,
                    'last_cleanup': None,
                    'average_duration': 0,
                    'success_rate': 0
                }
            
            total_cleanups = len(self.cleanup_history)
            successful_cleanups = sum(1 for record in self.cleanup_history if record['success'])
            success_rate = successful_cleanups / total_cleanups if total_cleanups > 0 else 0
            
            durations = [record.get('duration', 0) for record in self.cleanup_history if record.get('duration')]
            average_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                'total_cleanups': total_cleanups,
                'successful_cleanups': successful_cleanups,
                'success_rate': success_rate,
                'last_cleanup': self.last_cleanup_time.isoformat() if self.last_cleanup_time else None,
                'average_duration': average_duration,
                'recent_cleanups': self.cleanup_history[-5:]  # 最近5次清理记录
            }
            
        except Exception as e:
            logger.error(f"获取清理统计信息失败: {e}")
            return {}
    
    def clear_cleanup_history(self):
        """清除清理历史记录"""
        try:
            self.cleanup_history.clear()
            self.last_cleanup_time = None
            logger.debug("清理历史记录已清除")
            
        except Exception as e:
            logger.error(f"清除清理历史记录失败: {e}")
