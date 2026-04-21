# -*- coding: utf-8 -*-
"""
网络监控器
负责监控网络连接状态，支持断点续传功能

Author: Jack
Date: 2025-07-07
"""

import logging
import time
import threading
import requests
from typing import Callable, Optional
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

logger = logging.getLogger(__name__)


class NetworkMonitor(QObject):
    """
    网络监控器
    
    功能：
    - 监控网络连接状态
    - 检测网络恢复
    - 触发断点续传
    """
    
    # 信号定义
    network_connected = pyqtSignal()      # 网络连接信号
    network_disconnected = pyqtSignal()   # 网络断开信号
    network_recovered = pyqtSignal()      # 网络恢复信号
    
    def __init__(self, server_url: str = "http://localhost:5002", check_interval: int = 30):
        """
        初始化网络监控器
        
        Args:
            server_url: 服务器地址
            check_interval: 检查间隔（秒）
        """
        super().__init__()
        
        self.server_url = server_url
        self.check_interval = check_interval
        self.is_monitoring = False
        self.last_status = None  # None, True, False
        
        # 使用QTimer进行定时检查
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_network)
        
        # 回调函数
        self.on_connected_callback = None
        self.on_disconnected_callback = None
        self.on_recovered_callback = None
        
        logger.debug("网络监控器初始化完成")
    
    def start_monitoring(self):
        """开始监控网络状态"""
        if self.is_monitoring:
            logger.debug("网络监控已在运行")
            return
        
        self.is_monitoring = True
        self.timer.start(self.check_interval * 1000)  # 转换为毫秒
        logger.info(f"开始网络监控，检查间隔: {self.check_interval}秒")
        
        # 立即进行一次检查
        self._check_network()
    
    def stop_monitoring(self):
        """停止监控网络状态"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        self.timer.stop()
        logger.info("网络监控已停止")
    
    def _check_network(self):
        """检查网络连接状态"""
        try:
            current_status = self._test_connection()
            
            # 状态变化处理
            if self.last_status is None:
                # 首次检查
                if current_status:
                    logger.info("✅ 网络连接正常")
                    self.network_connected.emit()
                    if self.on_connected_callback:
                        self.on_connected_callback()
                else:
                    logger.warning("❌ 网络连接异常")
                    self.network_disconnected.emit()
                    if self.on_disconnected_callback:
                        self.on_disconnected_callback()
            
            elif self.last_status != current_status:
                # 状态发生变化
                if current_status:
                    logger.info("🔄 网络已恢复连接")
                    self.network_recovered.emit()
                    if self.on_recovered_callback:
                        self.on_recovered_callback()
                else:
                    logger.warning("💔 网络连接中断")
                    self.network_disconnected.emit()
                    if self.on_disconnected_callback:
                        self.on_disconnected_callback()
            
            self.last_status = current_status
            
        except Exception as e:
            logger.error(f"网络状态检查失败: {e}")
    
    def _test_connection(self) -> bool:
        """
        测试网络连接
        
        Returns:
            是否连接正常
        """
        try:
            # 测试服务器健康检查端点
            response = requests.get(
                f"{self.server_url}/health",
                timeout=5
            )
            return response.status_code == 200
            
        except requests.exceptions.RequestException:
            return False
        except Exception as e:
            logger.debug(f"网络测试异常: {e}")
            return False
    
    def is_connected(self) -> Optional[bool]:
        """
        获取当前网络连接状态
        
        Returns:
            网络连接状态，None表示未知
        """
        return self.last_status
    
    def test_connection_now(self) -> bool:
        """
        立即测试网络连接
        
        Returns:
            是否连接正常
        """
        return self._test_connection()
    
    def set_callbacks(self, on_connected: Optional[Callable] = None,
                     on_disconnected: Optional[Callable] = None,
                     on_recovered: Optional[Callable] = None):
        """
        设置回调函数
        
        Args:
            on_connected: 网络连接回调
            on_disconnected: 网络断开回调
            on_recovered: 网络恢复回调
        """
        self.on_connected_callback = on_connected
        self.on_disconnected_callback = on_disconnected
        self.on_recovered_callback = on_recovered
        
        logger.debug("网络监控回调函数已设置")
    
    def update_server_url(self, server_url: str):
        """
        更新服务器地址
        
        Args:
            server_url: 新的服务器地址
        """
        self.server_url = server_url
        logger.info(f"服务器地址已更新: {server_url}")
    
    def update_check_interval(self, interval: int):
        """
        更新检查间隔
        
        Args:
            interval: 新的检查间隔（秒）
        """
        self.check_interval = interval
        
        if self.is_monitoring:
            # 重启定时器以应用新间隔
            self.timer.stop()
            self.timer.start(interval * 1000)
        
        logger.info(f"检查间隔已更新: {interval}秒")
    
    def get_status_info(self) -> dict:
        """
        获取监控状态信息
        
        Returns:
            状态信息字典
        """
        return {
            'is_monitoring': self.is_monitoring,
            'server_url': self.server_url,
            'check_interval': self.check_interval,
            'last_status': self.last_status,
            'status_text': self._get_status_text()
        }
    
    def _get_status_text(self) -> str:
        """获取状态文本描述"""
        if self.last_status is None:
            return "未知"
        elif self.last_status:
            return "已连接"
        else:
            return "已断开"


class SimpleNetworkMonitor:
    """
    简单网络监控器（非Qt版本）
    用于不依赖Qt的场景
    """
    
    def __init__(self, server_url: str = "http://localhost:5002", check_interval: int = 30):
        """
        初始化简单网络监控器
        
        Args:
            server_url: 服务器地址
            check_interval: 检查间隔（秒）
        """
        self.server_url = server_url
        self.check_interval = check_interval
        self.is_monitoring = False
        self.last_status = None
        self.monitor_thread = None
        
        # 回调函数
        self.on_connected_callback = None
        self.on_disconnected_callback = None
        self.on_recovered_callback = None
        
        logger.debug("简单网络监控器初始化完成")
    
    def start_monitoring(self):
        """开始监控网络状态"""
        if self.is_monitoring:
            logger.debug("网络监控已在运行")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"开始网络监控，检查间隔: {self.check_interval}秒")
    
    def stop_monitoring(self):
        """停止监控网络状态"""
        self.is_monitoring = False
        logger.info("网络监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                current_status = self._test_connection()
                
                # 状态变化处理
                if self.last_status is None:
                    # 首次检查
                    if current_status:
                        logger.info("✅ 网络连接正常")
                        if self.on_connected_callback:
                            self.on_connected_callback()
                    else:
                        logger.warning("❌ 网络连接异常")
                        if self.on_disconnected_callback:
                            self.on_disconnected_callback()
                
                elif self.last_status != current_status:
                    # 状态发生变化
                    if current_status:
                        logger.info("🔄 网络已恢复连接")
                        if self.on_recovered_callback:
                            self.on_recovered_callback()
                    else:
                        logger.warning("💔 网络连接中断")
                        if self.on_disconnected_callback:
                            self.on_disconnected_callback()
                
                self.last_status = current_status
                
            except Exception as e:
                logger.error(f"网络状态检查失败: {e}")
            
            # 等待下次检查
            time.sleep(self.check_interval)
    
    def _test_connection(self) -> bool:
        """
        测试网络连接

        Returns:
            是否连接正常
        """
        try:
            # 修复减少超时时间，避免退出卡顿
            response = requests.get(f"{self.server_url}/health", timeout=1)
            return response.status_code == 200
        except:
            return False
    
    def is_connected(self) -> Optional[bool]:
        """获取当前网络连接状态"""
        return self.last_status
    
    def set_callbacks(self, on_connected: Optional[Callable] = None,
                     on_disconnected: Optional[Callable] = None,
                     on_recovered: Optional[Callable] = None):
        """设置回调函数"""
        self.on_connected_callback = on_connected
        self.on_disconnected_callback = on_disconnected
        self.on_recovered_callback = on_recovered
