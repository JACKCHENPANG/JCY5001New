# -*- coding: utf-8 -*-
"""
设置页面网络阻塞解决器
专门解决设置页面因网络请求导致的卡顿问题

Author: Jack
Date: 2025-07-13
"""

import logging
import threading
import time
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, QTimer

logger = logging.getLogger(__name__)


class SettingsNetworkBlocker(QObject):
    """设置页面网络阻塞解决器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocked_services = []
        self._original_timeouts = {}
        self._blocking_active = False
        
    def block_network_services(self, main_window):
        """阻塞网络服务，防止干扰设置页面"""
        try:
            if self._blocking_active:
                return
                
            self._blocking_active = True
            logger.info("🚀 开始阻塞网络服务，优化设置页面性能")
            
            # 1. 暂停心跳服务
            self._block_heartbeat_service(main_window)
            
            # 2. 暂停数据上传服务
            self._block_data_upload_service(main_window)
            
            # 3. 设置极短的网络超时
            self._set_emergency_timeouts()
            
            logger.info("✅ 网络服务阻塞完成")
            
        except Exception as e:
            logger.error(f"阻塞网络服务失败: {e}")
    
    def unblock_network_services(self, main_window):
        """解除网络服务阻塞"""
        try:
            if not self._blocking_active:
                return
                
            logger.info("🔄 开始解除网络服务阻塞")
            
            # 1. 恢复心跳服务
            self._unblock_heartbeat_service(main_window)
            
            # 2. 恢复数据上传服务
            self._unblock_data_upload_service(main_window)
            
            # 3. 恢复正常超时设置
            self._restore_normal_timeouts()
            
            self._blocking_active = False
            logger.info("✅ 网络服务阻塞已解除")
            
        except Exception as e:
            logger.error(f"解除网络服务阻塞失败: {e}")
    
    def _block_heartbeat_service(self, main_window):
        """阻塞心跳服务"""
        try:
            if hasattr(main_window, 'heartbeat_manager'):
                heartbeat_manager = main_window.heartbeat_manager
                if heartbeat_manager:
                    if hasattr(heartbeat_manager, 'pause_heartbeat'):
                        heartbeat_manager.pause_heartbeat()
                        self._blocked_services.append('heartbeat')
                        logger.debug("心跳服务已暂停")
                    elif hasattr(heartbeat_manager, 'stop'):
                        # 如果没有暂停功能，直接停止
                        heartbeat_manager.stop()
                        self._blocked_services.append('heartbeat_stopped')
                        logger.debug("心跳服务已停止")
                        
        except Exception as e:
            logger.error(f"阻塞心跳服务失败: {e}")
    
    def _unblock_heartbeat_service(self, main_window):
        """解除心跳服务阻塞"""
        try:
            if hasattr(main_window, 'heartbeat_manager'):
                heartbeat_manager = main_window.heartbeat_manager
                if heartbeat_manager:
                    if 'heartbeat' in self._blocked_services:
                        if hasattr(heartbeat_manager, 'resume_heartbeat'):
                            heartbeat_manager.resume_heartbeat()
                            logger.debug("心跳服务已恢复")
                    elif 'heartbeat_stopped' in self._blocked_services:
                        # 延迟重启心跳服务，避免立即网络请求
                        QTimer.singleShot(2000, lambda: self._restart_heartbeat(heartbeat_manager))
                        logger.debug("心跳服务将延迟重启")
                        
            self._blocked_services = [s for s in self._blocked_services if not s.startswith('heartbeat')]
            
        except Exception as e:
            logger.error(f"解除心跳服务阻塞失败: {e}")
    
    def _restart_heartbeat(self, heartbeat_manager):
        """延迟重启心跳服务"""
        try:
            if hasattr(heartbeat_manager, 'start'):
                heartbeat_config = heartbeat_manager.heartbeat_config
                if heartbeat_config.get('enabled', False):
                    heartbeat_manager.start()
                    logger.debug("心跳服务已延迟重启")
        except Exception as e:
            logger.error(f"延迟重启心跳服务失败: {e}")
    
    def _block_data_upload_service(self, main_window):
        """阻塞数据上传服务"""
        try:
            if hasattr(main_window, 'data_upload_manager'):
                upload_manager = main_window.data_upload_manager
                if upload_manager and hasattr(upload_manager, 'pause_upload_thread'):
                    upload_manager.pause_upload_thread()
                    self._blocked_services.append('data_upload')
                    logger.debug("数据上传服务已暂停")
                    
        except Exception as e:
            logger.error(f"阻塞数据上传服务失败: {e}")
    
    def _unblock_data_upload_service(self, main_window):
        """解除数据上传服务阻塞"""
        try:
            if hasattr(main_window, 'data_upload_manager'):
                upload_manager = main_window.data_upload_manager
                if upload_manager and hasattr(upload_manager, 'resume_upload_thread'):
                    upload_manager.resume_upload_thread()
                    logger.debug("数据上传服务已恢复")
                    
            self._blocked_services = [s for s in self._blocked_services if s != 'data_upload']
            
        except Exception as e:
            logger.error(f"解除数据上传服务阻塞失败: {e}")
    
    def _set_emergency_timeouts(self):
        """设置紧急超时时间"""
        try:
            import requests
            
            # 保存原始超时设置
            self._original_timeouts['requests_default'] = getattr(requests.adapters, 'DEFAULT_TIMEOUT', None)
            
            # 设置极短超时
            requests.adapters.DEFAULT_TIMEOUT = 0.5
            
            # 修改全局requests设置
            original_get = requests.get
            original_post = requests.post
            
            def emergency_get(*args, **kwargs):
                kwargs.setdefault('timeout', 0.5)
                return original_get(*args, **kwargs)
            
            def emergency_post(*args, **kwargs):
                kwargs.setdefault('timeout', 0.5)
                return original_post(*args, **kwargs)
            
            requests.get = emergency_get
            requests.post = emergency_post
            
            # 保存原始方法
            self._original_timeouts['requests_get'] = original_get
            self._original_timeouts['requests_post'] = original_post
            
            logger.debug("紧急超时设置已应用")
            
        except Exception as e:
            logger.error(f"设置紧急超时失败: {e}")
    
    def _restore_normal_timeouts(self):
        """恢复正常超时设置"""
        try:
            import requests
            
            # 恢复requests默认超时
            if 'requests_default' in self._original_timeouts:
                requests.adapters.DEFAULT_TIMEOUT = self._original_timeouts['requests_default']
            
            # 恢复原始方法
            if 'requests_get' in self._original_timeouts:
                requests.get = self._original_timeouts['requests_get']
            if 'requests_post' in self._original_timeouts:
                requests.post = self._original_timeouts['requests_post']
            
            self._original_timeouts.clear()
            logger.debug("正常超时设置已恢复")
            
        except Exception as e:
            logger.error(f"恢复正常超时设置失败: {e}")


# 全局网络阻塞器实例
_global_network_blocker = None


def get_settings_network_blocker() -> SettingsNetworkBlocker:
    """获取全局设置网络阻塞器"""
    global _global_network_blocker
    if _global_network_blocker is None:
        _global_network_blocker = SettingsNetworkBlocker()
    return _global_network_blocker


def block_network_for_settings(main_window):
    """为设置页面阻塞网络服务"""
    blocker = get_settings_network_blocker()
    blocker.block_network_services(main_window)


def unblock_network_for_settings(main_window):
    """为设置页面解除网络阻塞"""
    blocker = get_settings_network_blocker()
    blocker.unblock_network_services(main_window)


# 上下文管理器
class SettingsNetworkBlockContext:
    """设置网络阻塞上下文管理器"""
    
    def __init__(self, main_window):
        self.main_window = main_window
    
    def __enter__(self):
        block_network_for_settings(self.main_window)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        unblock_network_for_settings(self.main_window)


def with_network_blocking(main_window):
    """返回网络阻塞上下文管理器"""
    return SettingsNetworkBlockContext(main_window)
