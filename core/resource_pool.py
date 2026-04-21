# -*- coding: utf-8 -*-
"""
资源池管理器
用于统一管理和复用系统资源，避免重复创建

Author: Jack
Date: 2025-01-30
"""

import logging
import threading
from typing import Dict, List, Any, Optional, Type, Callable
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)


class PooledResource(ABC):
    """池化资源基类"""
    
    def __init__(self, resource_id: str):
        self.resource_id = resource_id
        self.created_at = datetime.now()
        self.last_used_at = datetime.now()
        self.use_count = 0
        self.is_active = True
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化资源"""
        pass
    
    @abstractmethod
    def cleanup(self) -> bool:
        """清理资源"""
        pass
    
    @abstractmethod
    def reset(self) -> bool:
        """重置资源状态"""
        pass
    
    def mark_used(self):
        """标记资源被使用"""
        self.last_used_at = datetime.now()
        self.use_count += 1


class ChannelManager(PooledResource):
    """通道管理器（池化资源）"""
    
    def __init__(self, channel_num: int):
        super().__init__(f"channel_{channel_num}")
        self.channel_num = channel_num
        self.display_widget = None
        self.timer_manager = None
        self.ui_updater = None
        self.style_manager = None
        
        logger.debug(f"✅ 通道{channel_num}管理器创建")
    
    def initialize(self) -> bool:
        """初始化通道管理器"""
        try:
            # 这里可以初始化通道相关的组件
            # 暂时返回True，具体实现在后续步骤中添加
            self.is_active = True
            logger.debug(f"✅ 通道{self.channel_num}管理器初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 通道{self.channel_num}管理器初始化失败: {e}")
            return False
    
    def cleanup(self) -> bool:
        """清理通道管理器"""
        try:
            # 清理相关组件
            if self.timer_manager:
                self.timer_manager.stop()
            
            self.is_active = False
            logger.debug(f"✅ 通道{self.channel_num}管理器清理完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 通道{self.channel_num}管理器清理失败: {e}")
            return False
    
    def reset(self) -> bool:
        """重置通道管理器"""
        try:
            # 重置状态
            if self.ui_updater:
                self.ui_updater.reset()
            
            logger.debug(f"✅ 通道{self.channel_num}管理器重置完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 通道{self.channel_num}管理器重置失败: {e}")
            return False


class TimerManager(PooledResource):
    """计时器管理器（池化资源）"""
    
    def __init__(self, timer_id: str):
        super().__init__(timer_id)
        self.timer = None
        self.callbacks = []
        self.interval = 100  # 默认100ms
        self.is_running = False
        
        logger.debug(f"✅ 计时器{timer_id}管理器创建")
    
    def initialize(self) -> bool:
        """初始化计时器"""
        try:
            from PyQt5.QtCore import QTimer
            self.timer = QTimer()
            self.timer.timeout.connect(self._on_timeout)
            
            self.is_active = True
            logger.debug(f"✅ 计时器{self.resource_id}初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 计时器{self.resource_id}初始化失败: {e}")
            return False
    
    def cleanup(self) -> bool:
        """清理计时器"""
        try:
            if self.timer:
                self.timer.stop()
                self.timer.deleteLater()
                self.timer = None
            
            self.callbacks.clear()
            self.is_active = False
            logger.debug(f"✅ 计时器{self.resource_id}清理完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 计时器{self.resource_id}清理失败: {e}")
            return False
    
    def reset(self) -> bool:
        """重置计时器"""
        try:
            if self.is_running:
                self.stop()
            
            self.callbacks.clear()
            logger.debug(f"✅ 计时器{self.resource_id}重置完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 计时器{self.resource_id}重置失败: {e}")
            return False
    
    def start(self) -> bool:
        """启动计时器"""
        try:
            if self.timer and not self.is_running:
                self.timer.start(self.interval)
                self.is_running = True
                self.mark_used()
                logger.debug(f"✅ 计时器{self.resource_id}已启动")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ 启动计时器{self.resource_id}失败: {e}")
            return False
    
    def stop(self) -> bool:
        """停止计时器"""
        try:
            if self.timer and self.is_running:
                self.timer.stop()
                self.is_running = False
                logger.debug(f"✅ 计时器{self.resource_id}已停止")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ 停止计时器{self.resource_id}失败: {e}")
            return False
    
    def add_callback(self, callback: Callable):
        """添加回调函数"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """移除回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _on_timeout(self):
        """计时器超时处理"""
        for callback in self.callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"❌ 计时器回调执行失败: {e}")


class ResourcePool:
    """
    资源池管理器
    
    职责：
    - 管理池化资源的创建和销毁
    - 提供资源复用机制
    - 监控资源使用情况
    - 自动清理无用资源
    """
    
    def __init__(self):
        self._pools: Dict[str, Dict[str, PooledResource]] = {}
        self._lock = threading.RLock()
        self.max_idle_time = 300  # 5分钟无使用则清理
        self.cleanup_interval = 60  # 1分钟检查一次
        
        # 初始化资源池
        self._pools['channels'] = {}
        self._pools['timers'] = {}
        
        logger.info("✅ 资源池管理器初始化完成")
    
    def get_channel_manager(self, channel_num: int) -> ChannelManager:
        """
        获取通道管理器
        
        Args:
            channel_num: 通道号（1-8）
            
        Returns:
            通道管理器实例
        """
        if not (1 <= channel_num <= 8):
            raise ValueError(f"无效的通道号: {channel_num}")
        
        resource_id = f"channel_{channel_num}"
        
        with self._lock:
            # 检查是否已存在
            if resource_id in self._pools['channels']:
                manager = self._pools['channels'][resource_id]
                manager.mark_used()
                logger.debug(f"🔄 复用通道{channel_num}管理器")
                return manager
            
            # 创建新的管理器
            manager = ChannelManager(channel_num)
            if manager.initialize():
                self._pools['channels'][resource_id] = manager
                logger.debug(f"✅ 创建通道{channel_num}管理器")
                return manager
            else:
                raise RuntimeError(f"通道{channel_num}管理器初始化失败")
    
    def get_timer_manager(self, timer_id: str) -> TimerManager:
        """
        获取计时器管理器
        
        Args:
            timer_id: 计时器ID
            
        Returns:
            计时器管理器实例
        """
        with self._lock:
            # 检查是否已存在
            if timer_id in self._pools['timers']:
                manager = self._pools['timers'][timer_id]
                manager.mark_used()
                logger.debug(f"🔄 复用计时器{timer_id}")
                return manager
            
            # 创建新的管理器
            manager = TimerManager(timer_id)
            if manager.initialize():
                self._pools['timers'][timer_id] = manager
                logger.debug(f"✅ 创建计时器{timer_id}")
                return manager
            else:
                raise RuntimeError(f"计时器{timer_id}初始化失败")
    
    def release_resource(self, pool_name: str, resource_id: str) -> bool:
        """
        释放资源
        
        Args:
            pool_name: 资源池名称
            resource_id: 资源ID
            
        Returns:
            是否释放成功
        """
        try:
            with self._lock:
                if pool_name in self._pools and resource_id in self._pools[pool_name]:
                    resource = self._pools[pool_name][resource_id]
                    resource.cleanup()
                    del self._pools[pool_name][resource_id]
                    logger.debug(f"✅ 释放资源: {pool_name}/{resource_id}")
                    return True
                else:
                    logger.warning(f"⚠️ 资源不存在: {pool_name}/{resource_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 释放资源失败: {pool_name}/{resource_id}, {e}")
            return False
    
    def cleanup_idle_resources(self) -> int:
        """
        清理空闲资源
        
        Returns:
            清理的资源数量
        """
        cleaned_count = 0
        current_time = datetime.now()
        
        try:
            with self._lock:
                for pool_name, pool in self._pools.items():
                    to_remove = []
                    
                    for resource_id, resource in pool.items():
                        # 检查是否超过空闲时间
                        idle_time = (current_time - resource.last_used_at).total_seconds()
                        if idle_time > self.max_idle_time:
                            to_remove.append(resource_id)
                    
                    # 清理空闲资源
                    for resource_id in to_remove:
                        if self.release_resource(pool_name, resource_id):
                            cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"🧹 清理了{cleaned_count}个空闲资源")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ 清理空闲资源失败: {e}")
            return 0
    
    def reset_all_resources(self) -> bool:
        """重置所有资源"""
        try:
            with self._lock:
                for pool_name, pool in self._pools.items():
                    for resource in pool.values():
                        resource.reset()
                
                logger.info("🔄 所有资源已重置")
                return True
                
        except Exception as e:
            logger.error(f"❌ 重置所有资源失败: {e}")
            return False
    
    def cleanup_all_resources(self) -> bool:
        """清理所有资源"""
        try:
            with self._lock:
                for pool_name, pool in self._pools.items():
                    for resource in pool.values():
                        resource.cleanup()
                    pool.clear()
                
                logger.info("🧹 所有资源已清理")
                return True
                
        except Exception as e:
            logger.error(f"❌ 清理所有资源失败: {e}")
            return False
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """获取资源统计信息"""
        with self._lock:
            stats = {}
            
            for pool_name, pool in self._pools.items():
                pool_stats = {
                    'total_count': len(pool),
                    'active_count': sum(1 for r in pool.values() if r.is_active),
                    'total_use_count': sum(r.use_count for r in pool.values()),
                    'resources': {}
                }
                
                for resource_id, resource in pool.items():
                    pool_stats['resources'][resource_id] = {
                        'created_at': resource.created_at.isoformat(),
                        'last_used_at': resource.last_used_at.isoformat(),
                        'use_count': resource.use_count,
                        'is_active': resource.is_active
                    }
                
                stats[pool_name] = pool_stats
            
            return stats


# 全局资源池实例
_global_resource_pool = None


def get_resource_pool() -> ResourcePool:
    """获取全局资源池实例"""
    global _global_resource_pool
    if _global_resource_pool is None:
        _global_resource_pool = ResourcePool()
    return _global_resource_pool


def reset_resource_pool():
    """重置全局资源池（主要用于测试）"""
    global _global_resource_pool
    if _global_resource_pool:
        _global_resource_pool.cleanup_all_resources()
    _global_resource_pool = None
