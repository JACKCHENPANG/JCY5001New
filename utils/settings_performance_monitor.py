# -*- coding: utf-8 -*-
"""
设置页面性能监控器
实时监控设置页面性能，提供优化建议

Author: Jack
Date: 2025-01-09
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Callable
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class SettingsPerformanceMonitor(QObject):
    """设置页面性能监控器"""
    
    # 信号定义
    performance_warning = pyqtSignal(str, float)  # 性能警告信号
    optimization_suggestion = pyqtSignal(str)     # 优化建议信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._monitoring_active = False
        self._performance_data = {}
        self._operation_times = {}
        self._network_timeouts = []
        self._ui_freeze_count = 0
        
        # 性能阈值
        self.SLOW_OPERATION_THRESHOLD = 0.5  # 500ms
        self.FREEZE_THRESHOLD = 1.0          # 1秒
        self.NETWORK_TIMEOUT_THRESHOLD = 0.2  # 200ms
        
        # 监控定时器
        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._check_performance)
        
    def start_monitoring(self):
        """开始性能监控"""
        try:
            if self._monitoring_active:
                return
                
            self._monitoring_active = True
            self._reset_performance_data()
            
            # 启动监控定时器，每100ms检查一次
            self._monitor_timer.start(100)
            
            logger.info("🚀 设置页面性能监控已启动")
            
        except Exception as e:
            logger.error(f"启动性能监控失败: {e}")
    
    def stop_monitoring(self):
        """停止性能监控"""
        try:
            if not self._monitoring_active:
                return
                
            self._monitoring_active = False
            self._monitor_timer.stop()
            
            # 生成性能报告
            self._generate_performance_report()
            
            logger.info("🚀 设置页面性能监控已停止")
            
        except Exception as e:
            logger.error(f"停止性能监控失败: {e}")
    
    def record_operation_start(self, operation_name: str):
        """记录操作开始时间"""
        try:
            self._operation_times[operation_name] = time.time()
            
        except Exception as e:
            logger.error(f"记录操作开始时间失败: {e}")
    
    def record_operation_end(self, operation_name: str):
        """记录操作结束时间并分析性能"""
        try:
            if operation_name not in self._operation_times:
                return
                
            start_time = self._operation_times[operation_name]
            end_time = time.time()
            duration = end_time - start_time
            
            # 记录到性能数据
            if operation_name not in self._performance_data:
                self._performance_data[operation_name] = []
            self._performance_data[operation_name].append(duration)
            
            # 检查是否超过阈值
            if duration > self.SLOW_OPERATION_THRESHOLD:
                self.performance_warning.emit(operation_name, duration)
                logger.warning(f"🚀 慢操作检测: {operation_name} 耗时 {duration:.3f}秒")
                
                # 提供优化建议
                self._suggest_optimization(operation_name, duration)
            
            # 清理记录
            del self._operation_times[operation_name]
            
        except Exception as e:
            logger.error(f"记录操作结束时间失败: {e}")
    
    def record_network_timeout(self, url: str, timeout_duration: float):
        """记录网络超时"""
        try:
            self._network_timeouts.append({
                'url': url,
                'duration': timeout_duration,
                'timestamp': time.time()
            })
            
            if timeout_duration > self.NETWORK_TIMEOUT_THRESHOLD:
                logger.warning(f"🚀 网络超时检测: {url} 超时 {timeout_duration:.3f}秒")
                self.optimization_suggestion.emit(f"建议优化网络请求: {url}")
            
        except Exception as e:
            logger.error(f"记录网络超时失败: {e}")
    
    def record_ui_freeze(self, freeze_duration: float):
        """记录UI冻结"""
        try:
            self._ui_freeze_count += 1
            
            if freeze_duration > self.FREEZE_THRESHOLD:
                logger.warning(f"🚀 UI冻结检测: 冻结 {freeze_duration:.3f}秒")
                self.performance_warning.emit("UI冻结", freeze_duration)
                self.optimization_suggestion.emit("建议将耗时操作移到后台线程")
            
        except Exception as e:
            logger.error(f"记录UI冻结失败: {e}")
    
    def _check_performance(self):
        """检查当前性能状态（非阻塞，安全退出）"""
        try:
            if not getattr(self, '_monitoring_active', False):
                return

            # 检查应用程序响应性
            app = QApplication.instance()
            if not app:
                return

            # 简单的响应性测试，限制处理时间窗口，避免在退出时阻塞
            start_time = time.time()
            app.processEvents()
            process_time = time.time() - start_time

            if process_time > 0.05:  # 50ms
                self.record_ui_freeze(process_time)
        except KeyboardInterrupt:
            logger.info("性能检查被中断，停止监视定时器")
            try:
                if hasattr(self, '_timer'):
                    self._timer.stop()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"性能检查失败: {e}")

    def _suggest_optimization(self, operation_name: str, duration: float):
        """根据操作类型提供优化建议"""
        try:
            suggestions = {
                'save_settings': '建议使用异步保存，避免阻塞UI线程',
                'validate_settings': '建议简化验证逻辑，跳过非关键检查',
                'apply_settings': '建议批量应用设置，减少IO操作',
                'network_request': '建议设置更短的超时时间或使用缓存',
                'file_operation': '建议使用后台线程处理文件操作',
                'ui_update': '建议批量更新UI，减少重绘次数'
            }
            
            for key, suggestion in suggestions.items():
                if key in operation_name.lower():
                    self.optimization_suggestion.emit(suggestion)
                    break
            else:
                # 通用建议
                if duration > 1.0:
                    self.optimization_suggestion.emit(f"建议优化 {operation_name} 操作，当前耗时 {duration:.3f}秒")
            
        except Exception as e:
            logger.error(f"提供优化建议失败: {e}")
    
    def _reset_performance_data(self):
        """重置性能数据"""
        try:
            self._performance_data.clear()
            self._operation_times.clear()
            self._network_timeouts.clear()
            self._ui_freeze_count = 0
            
        except Exception as e:
            logger.error(f"重置性能数据失败: {e}")
    
    def _generate_performance_report(self):
        """生成性能报告"""
        try:
            if not self._performance_data:
                logger.info("🚀 性能报告: 无性能数据")
                return
            
            logger.info("🚀 设置页面性能报告:")
            
            for operation, times in self._performance_data.items():
                if times:
                    avg_time = sum(times) / len(times)
                    max_time = max(times)
                    min_time = min(times)
                    
                    logger.info(f"  📊 {operation}: 平均 {avg_time:.3f}s, 最大 {max_time:.3f}s, 最小 {min_time:.3f}s, 次数 {len(times)}")
            
            if self._network_timeouts:
                logger.info(f"  🌐 网络超时次数: {len(self._network_timeouts)}")
            
            if self._ui_freeze_count > 0:
                logger.info(f"  ❄️ UI冻结次数: {self._ui_freeze_count}")
            
        except Exception as e:
            logger.error(f"生成性能报告失败: {e}")
    
    def get_performance_summary(self) -> Dict:
        """获取性能摘要"""
        try:
            summary = {
                'total_operations': len(self._performance_data),
                'slow_operations': 0,
                'network_timeouts': len(self._network_timeouts),
                'ui_freezes': self._ui_freeze_count,
                'average_times': {}
            }
            
            for operation, times in self._performance_data.items():
                if times:
                    avg_time = sum(times) / len(times)
                    summary['average_times'][operation] = avg_time
                    
                    if avg_time > self.SLOW_OPERATION_THRESHOLD:
                        summary['slow_operations'] += 1
            
            return summary
            
        except Exception as e:
            logger.error(f"获取性能摘要失败: {e}")
            return {}


# 全局性能监控器实例
_performance_monitor = None


def get_performance_monitor() -> SettingsPerformanceMonitor:
    """获取全局性能监控器实例"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = SettingsPerformanceMonitor()
    return _performance_monitor


def start_settings_performance_monitoring():
    """启动设置页面性能监控"""
    monitor = get_performance_monitor()
    monitor.start_monitoring()


def stop_settings_performance_monitoring():
    """停止设置页面性能监控"""
    monitor = get_performance_monitor()
    monitor.stop_monitoring()


def record_operation(operation_name: str):
    """装饰器：记录操作性能"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            monitor.record_operation_start(operation_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                monitor.record_operation_end(operation_name)
        return wrapper
    return decorator
