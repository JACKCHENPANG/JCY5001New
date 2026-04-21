# -*- coding: utf-8 -*-
"""
异步网络检查器
为设置页面提供异步网络检查功能，避免UI卡顿

Author: Jack
Date: 2025-07-13
"""

import logging
import time
import requests
from typing import Dict, Any, Optional, Callable
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QObject

logger = logging.getLogger(__name__)


class AsyncNetworkChecker(QThread):
    """异步网络检查器"""
    
    # 信号定义
    check_completed = pyqtSignal(str, bool, str)  # 检查类型, 是否成功, 消息
    check_failed = pyqtSignal(str, str)  # 检查类型, 错误信息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._check_queue = []  # 检查队列
        self._cache = {}  # 结果缓存
        self._cache_timeout = 30  # 缓存超时时间（秒）
        self._request_timeout = 2  # 网络请求超时时间（秒）
        self._running = False
        
    def add_check(self, check_type: str, url: str, callback: Optional[Callable] = None):
        """
        添加网络检查任务
        
        Args:
            check_type: 检查类型（如'upload_test', 'health_check'等）
            url: 检查的URL
            callback: 完成后的回调函数
        """
        try:
            # 检查缓存
            cache_key = f"{check_type}_{url}"
            if self._is_cache_valid(cache_key):
                cached_result = self._cache[cache_key]
                logger.debug(f"🚀 使用缓存结果: {check_type}")
                if callback:
                    callback(cached_result['success'], cached_result['message'])
                self.check_completed.emit(check_type, cached_result['success'], cached_result['message'])
                return
            
            # 添加到检查队列
            self._check_queue.append({
                'type': check_type,
                'url': url,
                'callback': callback,
                'cache_key': cache_key
            })
            
            # 启动检查线程
            if not self.isRunning():
                self._running = True
                self.start()
                
        except Exception as e:
            logger.error(f"添加网络检查任务失败: {e}")
            if callback:
                callback(False, f"添加检查任务失败: {e}")
            self.check_failed.emit(check_type, str(e))
    
    def run(self):
        """执行网络检查"""
        try:
            while self._running and self._check_queue:
                check_task = self._check_queue.pop(0)
                self._perform_check(check_task)
                
        except Exception as e:
            logger.error(f"网络检查线程异常: {e}")
        finally:
            self._running = False
    
    def _perform_check(self, task: Dict[str, Any]):
        """执行单个检查任务"""
        try:
            check_type = task['type']
            url = task['url']
            callback = task.get('callback')
            cache_key = task['cache_key']
            
            logger.debug(f"🔍 执行网络检查: {check_type} -> {url}")
            
            # 执行网络请求
            start_time = time.time()
            success, message = self._test_url(url)
            elapsed_time = time.time() - start_time
            
            # 缓存结果
            self._cache[cache_key] = {
                'success': success,
                'message': message,
                'timestamp': time.time()
            }
            
            logger.debug(f"✅ 网络检查完成: {check_type}, 耗时: {elapsed_time:.2f}s, 结果: {success}")
            
            # 回调处理
            if callback:
                callback(success, message)
            
            # 发送信号
            self.check_completed.emit(check_type, success, message)
            
        except Exception as e:
            logger.error(f"执行网络检查失败: {e}")
            if callback:
                callback(False, f"检查失败: {e}")
            self.check_failed.emit(task['type'], str(e))
    
    def _test_url(self, url: str) -> tuple:
        """
        测试URL连接

        Returns:
            (是否成功, 消息)
        """
        try:
            # 修复创建独立的session，完全不受全局设置影响
            session = requests.Session()

            # 设置独立的适配器，避免全局DEFAULT_TIMEOUT影响
            adapter = requests.adapters.HTTPAdapter()
            session.mount('http://', adapter)
            session.mount('https://', adapter)

            logger.debug(f"🔗 开始测试连接: {url}")
            start_time = time.time()

            response = session.get(
                url,
                timeout=10,  # 使用明确的10秒超时
                headers={'User-Agent': 'JCY5001AS/1.0'}
            )

            duration = time.time() - start_time
            logger.debug(f"📊 连接测试完成，耗时: {duration:.3f}秒，状态码: {response.status_code}")

            if response.status_code == 200:
                return True, "连接成功"
            else:
                return False, f"服务器响应错误: {response.status_code}"

        except requests.exceptions.Timeout:
            duration = time.time() - start_time if 'start_time' in locals() else 0
            logger.warning(f"⏰ 连接超时: {url}，耗时: {duration:.3f}秒")
            return False, "连接超时（10秒）"
        except requests.exceptions.ConnectionError as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0
            logger.warning(f"🔌 连接错误: {url}，耗时: {duration:.3f}秒，错误: {e}")
            return False, "服务器连接失败！\n连接失败，请检查网络连接和服务器配置。"
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0
            logger.error(f"📡 请求异常: {url}，耗时: {duration:.3f}秒，错误: {e}")
            return False, f"请求异常: {e}"
        except Exception as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0
            logger.error(f"❌ 未知错误: {url}，耗时: {duration:.3f}秒，错误: {e}")
            return False, f"未知错误: {e}"
        finally:
            # 确保session被正确关闭
            if 'session' in locals():
                session.close()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache:
            return False
        
        cache_time = self._cache[cache_key]['timestamp']
        return (time.time() - cache_time) < self._cache_timeout
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.debug("网络检查缓存已清空")
    
    def stop_checker(self):
        """停止检查器"""
        self._running = False
        self._check_queue.clear()
        if self.isRunning():
            self.quit()
            self.wait(3000)  # 等待3秒


class NetworkCheckerManager(QObject):
    """网络检查器管理器（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            super().__init__()
            self._checker = AsyncNetworkChecker()
            self._initialized = True
    
    def get_checker(self) -> AsyncNetworkChecker:
        """获取网络检查器实例"""
        return self._checker
    
    def test_upload_connection(self, config: Dict[str, Any], callback: Optional[Callable] = None):
        """测试上传连接"""
        server_url = config.get('server_url', 'http://localhost:5002')
        health_url = f"{server_url}/health"
        self._checker.add_check('upload_test', health_url, callback)
    
    def test_server_health(self, server_url: str = 'http://localhost:5002', callback: Optional[Callable] = None):
        """测试服务器健康状态"""
        health_url = f"{server_url}/health"
        self._checker.add_check('health_check', health_url, callback)
    
    def cleanup(self):
        """清理资源"""
        if hasattr(self, '_checker'):
            self._checker.stop_checker()


# 全局管理器实例
def get_network_checker() -> NetworkCheckerManager:
    """获取全局网络检查器管理器"""
    return NetworkCheckerManager()


def test_connection_async(url: str, callback: Callable, check_type: str = 'general'):
    """
    异步测试连接的便捷函数
    
    Args:
        url: 要测试的URL
        callback: 回调函数，接收(success: bool, message: str)参数
        check_type: 检查类型
    """
    manager = get_network_checker()
    manager.get_checker().add_check(check_type, url, callback)
