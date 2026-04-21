# -*- coding: utf-8 -*-
"""
网络性能优化器
专门解决服务器关闭时设置页面卡顿问题

Author: Jack
Date: 2025-07-13
"""

import logging
import time
from typing import Dict, Any, Optional, Callable
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class NetworkPerformanceOptimizer(QObject):
    """网络性能优化器"""
    
    # 信号定义
    network_status_changed = pyqtSignal(bool)  # 网络状态变更
    optimization_applied = pyqtSignal(str)  # 优化已应用
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 网络状态缓存
        self._network_available = None
        self._last_check_time = 0
        self._check_interval = 10  # 10秒检查间隔
        
        # 优化状态
        self._optimization_enabled = True
        self._fast_fail_mode = False
        
        # 管理器引用
        self._heartbeat_manager = None
        self._data_upload_manager = None
        self._network_monitor = None
        
        # 定时器
        self._status_check_timer = QTimer()
        self._status_check_timer.timeout.connect(self._check_network_status)
        
    def initialize(self, main_window):
        """
        初始化优化器
        
        Args:
            main_window: 主窗口实例
        """
        try:
            # 获取管理器引用
            self._heartbeat_manager = getattr(main_window, 'heartbeat_manager', None)
            self._data_upload_manager = getattr(main_window, 'data_upload_manager', None)
            self._network_monitor = getattr(main_window, 'network_monitor', None)
            
            # 启动状态检查
            self._status_check_timer.start(self._check_interval * 1000)
            
            logger.info("✅ 网络性能优化器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化网络性能优化器失败: {e}")
    
    def _check_network_status(self):
        """检查网络状态"""
        try:
            current_time = time.time()
            
            # 避免频繁检查
            if current_time - self._last_check_time < self._check_interval:
                return
            
            self._last_check_time = current_time
            
            # 快速网络检查
            network_available = self._quick_network_check()
            
            # 状态变更处理
            if self._network_available != network_available:
                self._network_available = network_available
                self.network_status_changed.emit(network_available)
                
                if network_available:
                    self._enable_normal_mode()
                else:
                    self._enable_fast_fail_mode()
                    
        except Exception as e:
            logger.error(f"网络状态检查失败: {e}")
    
    def _quick_network_check(self) -> bool:
        """快速网络检查"""
        try:
            # 使用心跳管理器进行快速检查
            if self._heartbeat_manager:
                return self._heartbeat_manager.test_connection()
            
            # 备用检查方法
            import requests
            response = requests.get('http://localhost:5002/health', timeout=1)
            return response.status_code == 200
            
        except:
            return False
    
    def _enable_fast_fail_mode(self):
        """启用快速失败模式"""
        try:
            if self._fast_fail_mode:
                return
                
            self._fast_fail_mode = True
            logger.info("🚀 启用快速失败模式 - 优化网络超时设置")
            
            # 优化心跳管理器
            if self._heartbeat_manager:
                self._optimize_heartbeat_manager()
            
            # 优化数据上传管理器
            if self._data_upload_manager:
                self._optimize_data_upload_manager()
            
            # 优化网络监控器
            if self._network_monitor:
                self._optimize_network_monitor()
            
            self.optimization_applied.emit("fast_fail_mode_enabled")
            
        except Exception as e:
            logger.error(f"启用快速失败模式失败: {e}")
    
    def _enable_normal_mode(self):
        """启用正常模式"""
        try:
            if not self._fast_fail_mode:
                return
                
            self._fast_fail_mode = False
            logger.info("🔄 恢复正常模式 - 恢复标准网络设置")
            
            # 恢复心跳管理器
            if self._heartbeat_manager:
                self._restore_heartbeat_manager()
            
            # 恢复数据上传管理器
            if self._data_upload_manager:
                self._restore_data_upload_manager()
            
            # 恢复网络监控器
            if self._network_monitor:
                self._restore_network_monitor()
            
            self.optimization_applied.emit("normal_mode_restored")
            
        except Exception as e:
            logger.error(f"恢复正常模式失败: {e}")
    
    def _optimize_heartbeat_manager(self):
        """优化心跳管理器"""
        try:
            if not self._heartbeat_manager:
                return

            # 暂停心跳发送
            if hasattr(self._heartbeat_manager, 'pause_heartbeat'):
                self._heartbeat_manager.pause_heartbeat()
                logger.debug("心跳管理器已暂停")

        except Exception as e:
            logger.error(f"优化心跳管理器失败: {e}")

    def _optimize_data_upload_manager(self):
        """优化数据上传管理器"""
        try:
            if not self._data_upload_manager:
                return

            # 暂停上传线程
            if hasattr(self._data_upload_manager, 'pause_upload_thread'):
                self._data_upload_manager.pause_upload_thread()
                logger.debug("数据上传管理器已暂停")

        except Exception as e:
            logger.error(f"优化数据上传管理器失败: {e}")

    def _optimize_network_monitor(self):
        """优化网络监控器"""
        try:
            if not self._network_monitor:
                return

            # 停止网络监控
            if hasattr(self._network_monitor, 'stop_monitoring'):
                self._network_monitor.stop_monitoring()
                logger.debug("网络监控器已停止")

        except Exception as e:
            logger.error(f"优化网络监控器失败: {e}")

    def _restore_heartbeat_manager(self):
        """恢复心跳管理器"""
        try:
            if not self._heartbeat_manager:
                return

            # 恢复心跳发送
            if hasattr(self._heartbeat_manager, 'resume_heartbeat'):
                self._heartbeat_manager.resume_heartbeat()
                logger.debug("心跳管理器已恢复")

        except Exception as e:
            logger.error(f"恢复心跳管理器失败: {e}")

    def _restore_data_upload_manager(self):
        """恢复数据上传管理器"""
        try:
            if not self._data_upload_manager:
                return

            # 恢复上传线程
            if hasattr(self._data_upload_manager, 'resume_upload_thread'):
                self._data_upload_manager.resume_upload_thread()
                logger.debug("数据上传管理器已恢复")

        except Exception as e:
            logger.error(f"恢复数据上传管理器失败: {e}")

    def _restore_network_monitor(self):
        """恢复网络监控器"""
        try:
            if not self._network_monitor:
                return

            # 恢复网络监控
            if hasattr(self._network_monitor, 'start_monitoring'):
                self._network_monitor.start_monitoring()
                logger.debug("网络监控器已恢复")

        except Exception as e:
            logger.error(f"恢复网络监控器失败: {e}")
    
    def force_fast_fail_mode(self):
        """强制启用快速失败模式"""
        self._network_available = False
        self._enable_fast_fail_mode()
    
    def force_normal_mode(self):
        """强制启用正常模式"""
        self._network_available = True
        self._enable_normal_mode()
    
    def is_network_available(self) -> Optional[bool]:
        """获取网络可用状态"""
        return self._network_available
    
    def is_fast_fail_mode(self) -> bool:
        """是否处于快速失败模式"""
        return self._fast_fail_mode
    
    def cleanup(self):
        """清理资源"""
        try:
            self._status_check_timer.stop()
            self._enable_normal_mode()  # 恢复正常模式
            logger.debug("网络性能优化器已清理")
            
        except Exception as e:
            logger.error(f"清理网络性能优化器失败: {e}")


# 全局优化器实例
_global_optimizer = None


def get_network_performance_optimizer() -> NetworkPerformanceOptimizer:
    """获取全局网络性能优化器"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = NetworkPerformanceOptimizer()
    return _global_optimizer


def optimize_settings_for_offline_mode():
    """为离线模式优化设置"""
    optimizer = get_network_performance_optimizer()
    optimizer.force_fast_fail_mode()


def restore_settings_for_online_mode():
    """为在线模式恢复设置"""
    optimizer = get_network_performance_optimizer()
    optimizer.force_normal_mode()
