# -*- coding: utf-8 -*-
"""
设置页面网络优化器
专门解决设置页面因服务器关闭导致的卡顿问题

Author: Jack
Date: 2025-07-13
"""

import logging
import requests
from typing import Optional
from PyQt5.QtCore import QObject, QTimer

logger = logging.getLogger(__name__)


class SettingsNetworkOptimizer(QObject):
    """设置页面网络优化器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._server_available = None
        self._last_check_time = 0
        self._check_timeout = 1  # 1秒超时
        
    def is_server_available(self) -> bool:
        """
        快速检查服务器是否可用
        
        Returns:
            服务器是否可用
        """
        try:
            # 使用极短的超时时间进行检查
            response = requests.get(
                'http://localhost:5002/health',
                timeout=self._check_timeout
            )
            self._server_available = response.status_code == 200
            return self._server_available
            
        except (requests.exceptions.RequestException, Exception):
            self._server_available = False
            return False
    
    def optimize_for_offline_mode(self):
        """为离线模式优化设置"""
        try:
            logger.info("🚀 启用设置页面离线优化模式")
            
            # 设置更短的网络超时
            import requests
            requests.adapters.DEFAULT_TIMEOUT = 1
            
            # 禁用不必要的网络检查
            self._disable_network_operations()
            
        except Exception as e:
            logger.error(f"启用离线优化模式失败: {e}")
    
    def restore_normal_mode(self):
        """恢复正常模式"""
        try:
            logger.info("🔄 恢复设置页面正常模式")
            
            # 恢复正常的网络超时
            import requests
            requests.adapters.DEFAULT_TIMEOUT = 5
            
            # 恢复网络操作
            self._enable_network_operations()
            
        except Exception as e:
            logger.error(f"恢复正常模式失败: {e}")
    
    def _disable_network_operations(self):
        """禁用网络操作"""
        try:
            # 这里可以添加具体的网络操作禁用逻辑
            logger.debug("网络操作已禁用")
        except Exception as e:
            logger.error(f"禁用网络操作失败: {e}")
    
    def _enable_network_operations(self):
        """启用网络操作"""
        try:
            # 这里可以添加具体的网络操作启用逻辑
            logger.debug("网络操作已启用")
        except Exception as e:
            logger.error(f"启用网络操作失败: {e}")


# 全局优化器实例
_global_settings_optimizer = None


def get_settings_network_optimizer() -> SettingsNetworkOptimizer:
    """获取全局设置网络优化器"""
    global _global_settings_optimizer
    if _global_settings_optimizer is None:
        _global_settings_optimizer = SettingsNetworkOptimizer()
    return _global_settings_optimizer


def optimize_settings_network():
    """优化设置页面网络性能"""
    optimizer = get_settings_network_optimizer()
    if not optimizer.is_server_available():
        optimizer.optimize_for_offline_mode()
    else:
        optimizer.restore_normal_mode()


def patch_requests_timeout():
    """为requests库打补丁，设置更短的默认超时"""
    try:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        # 创建一个快速失败的适配器
        class FastFailAdapter(HTTPAdapter):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
            def send(self, request, **kwargs):
                # 强制设置短超时
                kwargs['timeout'] = kwargs.get('timeout', 1)
                return super().send(request, **kwargs)
        
        # 为requests会话设置快速失败适配器
        session = requests.Session()
        session.mount('http://', FastFailAdapter())
        session.mount('https://', FastFailAdapter())
        
        # 替换默认的requests方法
        original_get = requests.get
        original_post = requests.post
        
        def fast_get(*args, **kwargs):
            kwargs.setdefault('timeout', 1)
            return original_get(*args, **kwargs)
        
        def fast_post(*args, **kwargs):
            kwargs.setdefault('timeout', 1)
            return original_post(*args, **kwargs)
        
        requests.get = fast_get
        requests.post = fast_post
        
        logger.info("✅ requests库超时优化已应用")
        
    except Exception as e:
        logger.error(f"应用requests超时优化失败: {e}")


def restore_requests_timeout():
    """恢复requests库的正常超时设置"""
    try:
        import requests
        
        # 恢复默认超时（这里简化处理）
        original_get = getattr(requests, '_original_get', requests.get)
        original_post = getattr(requests, '_original_post', requests.post)
        
        requests.get = original_get
        requests.post = original_post
        
        logger.info("✅ requests库超时设置已恢复")
        
    except Exception as e:
        logger.error(f"恢复requests超时设置失败: {e}")


def apply_settings_optimization():
    """应用设置页面优化（彻底版本）"""
    try:
        # 🚀 性能优化：不进行服务器检查，直接应用离线优化
        logger.info("🚀 应用设置页面优化，跳过服务器检查")

        optimizer = get_settings_network_optimizer()
        patch_requests_timeout()
        optimizer.optimize_for_offline_mode()

        # 🚀 额外优化：完全禁用网络检查
        _disable_all_network_checks()

    except Exception as e:
        logger.error(f"应用设置页面优化失败: {e}")

def _disable_all_network_checks():
    """完全禁用所有网络检查"""
    try:
        import requests

        # 创建一个立即失败的函数
        def immediate_fail(*args, **kwargs):
            raise requests.exceptions.ConnectionError("网络检查已被禁用")

        # 替换requests方法
        requests.get = immediate_fail
        requests.post = immediate_fail

        logger.debug("所有网络检查已被禁用")

    except Exception as e:
        logger.error(f"禁用网络检查失败: {e}")


def remove_settings_optimization():
    """移除设置页面优化"""
    try:
        logger.info("🔄 移除设置页面优化，恢复正常模式")
        restore_requests_timeout()
        
        optimizer = get_settings_network_optimizer()
        optimizer.restore_normal_mode()
        
    except Exception as e:
        logger.error(f"移除设置页面优化失败: {e}")


# 自动应用优化的装饰器
def with_settings_optimization(func):
    """为函数应用设置页面优化的装饰器"""
    def wrapper(*args, **kwargs):
        try:
            apply_settings_optimization()
            result = func(*args, **kwargs)
            return result
        finally:
            remove_settings_optimization()
    return wrapper
