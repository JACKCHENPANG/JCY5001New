# -*- coding: utf-8 -*-
"""
统一通道服务
管理所有通道的显示组件和计时器，使用资源池进行优化

Author: Jack
Date: 2025-01-30
"""

import logging
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime

from core import (
    get_event_bus, get_state_manager, get_resource_pool,
    EventType, EventHandler, StateObserver, ChannelState
)

logger = logging.getLogger(__name__)


class ChannelEventHandler(EventHandler):
    """通道事件处理器"""
    
    def __init__(self, channel_service):
        super().__init__("channel_event_handler")
        self.channel_service = channel_service
    
    def _handle_event(self, event):
        """处理通道相关事件"""
        try:
            if event.event_type == EventType.CHANNEL_STARTED:
                channel_num = event.data.get('channel_num')
                if channel_num:
                    return self.channel_service.handle_channel_started(channel_num, event.data)
            
            elif event.event_type == EventType.CHANNEL_COMPLETED:
                channel_num = event.data.get('channel_num')
                if channel_num:
                    return self.channel_service.handle_channel_completed(channel_num, event.data)
            
            elif event.event_type == EventType.CHANNEL_PROGRESS:
                channel_num = event.data.get('channel_num')
                if channel_num:
                    return self.channel_service.handle_channel_progress(channel_num, event.data)
            
            elif event.event_type == EventType.TEST_STOPPED:
                return self.channel_service.handle_test_stopped()
            
            return True
            
        except Exception as e:
            logger.error(f"处理通道事件失败: {e}")
            return False


class ChannelStateObserver(StateObserver):
    """通道状态观察者"""
    
    def __init__(self, channel_service):
        super().__init__("channel_state_observer")
        self.channel_service = channel_service
    
    def on_channel_state_changed(self, channel_num: int, old_state, new_state, reason: str = ""):
        """通道状态变化回调"""
        try:
            self.channel_service.handle_channel_state_changed(channel_num, old_state, new_state, reason)
        except Exception as e:
            logger.error(f"处理通道{channel_num}状态变化失败: {e}")


class UnifiedChannelService:
    """
    统一通道服务
    
    职责：
    - 管理所有通道的显示组件
    - 统一通道计时器管理
    - 处理通道状态变化
    - 优化通道资源使用
    """
    
    def __init__(self, main_window):
        self.main_window = main_window
        self._lock = threading.RLock()
        
        # 核心服务
        self.event_bus = get_event_bus()
        self.state_manager = get_state_manager()
        self.resource_pool = get_resource_pool()
        
        # 通道数据
        self.channel_widgets: Dict[int, Any] = {}  # 通道显示组件
        self.channel_timers: Dict[int, Any] = {}   # 通道计时器
        self.channel_data: Dict[int, Dict[str, Any]] = {}  # 通道数据缓存
        
        # 注册事件处理器和状态观察者
        self.channel_event_handler = ChannelEventHandler(self)
        self.channel_state_observer = ChannelStateObserver(self)
        self._register_handlers()
        
        logger.info("✅ 统一通道服务初始化完成")
    
    def _register_handlers(self):
        """注册事件处理器和状态观察者"""
        try:
            # 注册事件处理器
            self.event_bus.subscribe(EventType.CHANNEL_STARTED, self.channel_event_handler)
            self.event_bus.subscribe(EventType.CHANNEL_COMPLETED, self.channel_event_handler)
            self.event_bus.subscribe(EventType.CHANNEL_PROGRESS, self.channel_event_handler)
            self.event_bus.subscribe(EventType.TEST_STOPPED, self.channel_event_handler)
            
            # 注册状态观察者
            self.state_manager.add_observer(self.channel_state_observer)
            
            logger.debug("✅ 通道事件处理器和状态观察者注册完成")
            
        except Exception as e:
            logger.error(f"❌ 注册通道处理器失败: {e}")
    
    def initialize_channel(self, channel_num: int, widget=None) -> bool:
        """
        初始化通道
        
        Args:
            channel_num: 通道号（1-8）
            widget: 通道显示组件（可选）
            
        Returns:
            是否初始化成功
        """
        try:
            if not (1 <= channel_num <= 8):
                logger.error(f"❌ 无效的通道号: {channel_num}")
                return False
            
            with self._lock:
                # 获取通道管理器（使用资源池）
                channel_manager = self.resource_pool.get_channel_manager(channel_num)
                
                # 设置通道组件
                if widget:
                    self.channel_widgets[channel_num] = widget
                    channel_manager.display_widget = widget
                
                # 获取通道计时器（使用资源池）
                timer_id = f"channel_{channel_num}_timer"
                timer_manager = self.resource_pool.get_timer_manager(timer_id)
                self.channel_timers[channel_num] = timer_manager
                channel_manager.timer_manager = timer_manager
                
                # 初始化通道数据
                self.channel_data[channel_num] = {
                    'initialized_at': datetime.now(),
                    'last_update': datetime.now(),
                    'test_count': 0,
                    'status': 'initialized'
                }
                
                # 设置通道状态
                self.state_manager.set_channel_state(
                    channel_num, 
                    ChannelState.CONNECTED, 
                    "通道初始化", 
                    "unified_channel_service"
                )
                
                logger.info(f"✅ 通道{channel_num}初始化完成")
                return True
                
        except Exception as e:
            logger.error(f"❌ 初始化通道{channel_num}失败: {e}")
            return False
    
    def get_channel_widget(self, channel_num: int):
        """获取通道显示组件"""
        with self._lock:
            return self.channel_widgets.get(channel_num)
    
    def get_channel_timer(self, channel_num: int):
        """获取通道计时器"""
        with self._lock:
            return self.channel_timers.get(channel_num)
    
    def update_channel_progress(self, channel_num: int, progress: int, status: str = "", publish_event: bool = True) -> bool:
        """
        更新通道进度

        Args:
            channel_num: 通道号
            progress: 进度百分比（0-100）
            status: 状态描述
            publish_event: 是否发布事件（防止递归调用）

        Returns:
            是否更新成功
        """
        try:
            if not (1 <= channel_num <= 8):
                return False

            with self._lock:
                # 更新通道数据
                if channel_num in self.channel_data:
                    self.channel_data[channel_num].update({
                        'progress': progress,
                        'status': status,
                        'last_update': datetime.now()
                    })

                # 更新UI组件
                widget = self.channel_widgets.get(channel_num)
                if widget and hasattr(widget, 'ui_updater'):
                    widget.ui_updater.update_progress_display(progress)

                # 修复：只在需要时发布进度事件，防止递归调用
                if publish_event:
                    self.event_bus.publish(
                        EventType.CHANNEL_PROGRESS,
                        {
                            'channel_num': channel_num,
                            'progress': progress,
                            'status': status
                        },
                        "unified_channel_service"
                    )

                logger.debug(f"📊 通道{channel_num}进度更新: {progress}% - {status}")
                return True

        except Exception as e:
            logger.error(f"❌ 更新通道{channel_num}进度失败: {e}")
            return False
    
    def update_channel_result(self, channel_num: int, result_data: Dict[str, Any]) -> bool:
        """
        更新通道测试结果
        
        Args:
            channel_num: 通道号
            result_data: 测试结果数据
            
        Returns:
            是否更新成功
        """
        try:
            if not (1 <= channel_num <= 8):
                return False
            
            with self._lock:
                # 更新通道数据
                if channel_num in self.channel_data:
                    self.channel_data[channel_num].update({
                        'result_data': result_data,
                        'last_result_time': datetime.now(),
                        'test_count': self.channel_data[channel_num].get('test_count', 0) + 1
                    })
                
                # 更新UI组件
                widget = self.channel_widgets.get(channel_num)
                if widget and hasattr(widget, 'ui_updater'):
                    widget.ui_updater.update_test_result_display(result_data)
                
                # 设置通道状态为完成
                self.state_manager.set_channel_state(
                    channel_num,
                    ChannelState.COMPLETED,
                    "测试完成",
                    "unified_channel_service"
                )
                
                logger.info(f"✅ 通道{channel_num}结果更新完成")
                return True
                
        except Exception as e:
            logger.error(f"❌ 更新通道{channel_num}结果失败: {e}")
            return False
    
    def start_channel_timer(self, channel_num: int) -> bool:
        """启动通道计时器"""
        try:
            timer = self.channel_timers.get(channel_num)
            if timer:
                return timer.start()
            return False
        except Exception as e:
            logger.error(f"❌ 启动通道{channel_num}计时器失败: {e}")
            return False
    
    def stop_channel_timer(self, channel_num: int) -> bool:
        """停止通道计时器"""
        try:
            timer = self.channel_timers.get(channel_num)
            if timer:
                return timer.stop()
            return False
        except Exception as e:
            logger.error(f"❌ 停止通道{channel_num}计时器失败: {e}")
            return False
    
    def handle_channel_started(self, channel_num: int, event_data: Dict[str, Any]) -> bool:
        """处理通道开始事件"""
        try:
            logger.info(f"🚀 通道{channel_num}开始测试")
            
            # 设置通道状态
            self.state_manager.set_channel_state(
                channel_num,
                ChannelState.TESTING,
                "开始测试",
                "unified_channel_service"
            )
            
            # 启动计时器
            self.start_channel_timer(channel_num)
            
            # 重置进度
            self.update_channel_progress(channel_num, 0, "开始测试")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 处理通道{channel_num}开始事件失败: {e}")
            return False
    
    def handle_channel_completed(self, channel_num: int, event_data: Dict[str, Any]) -> bool:
        """处理通道完成事件"""
        try:
            logger.info(f"✅ 通道{channel_num}测试完成")

            # 停止计时器
            self.stop_channel_timer(channel_num)

            # 修复：更新进度为100%时不发布事件，防止递归调用
            self.update_channel_progress(channel_num, 100, "测试完成", publish_event=False)

            # 更新结果
            result_data = event_data.get('result_data', {})
            if result_data:
                self.update_channel_result(channel_num, result_data)

            return True

        except Exception as e:
            logger.error(f"❌ 处理通道{channel_num}完成事件失败: {e}")
            return False
    
    def handle_channel_progress(self, channel_num: int, event_data: Dict[str, Any]) -> bool:
        """处理通道进度事件"""
        try:
            progress = event_data.get('progress', 0)
            status = event_data.get('status', '')

            # 修复：处理事件时不再发布新事件，防止递归调用
            return self.update_channel_progress(channel_num, progress, status, publish_event=False)

        except Exception as e:
            logger.error(f"❌ 处理通道{channel_num}进度事件失败: {e}")
            return False
    
    def handle_channel_state_changed(self, channel_num: int, old_state, new_state, reason: str):
        """处理通道状态变化"""
        try:
            logger.debug(f"🔄 通道{channel_num}状态变化: {old_state.value} -> {new_state.value} ({reason})")
            
            # 更新UI显示
            widget = self.channel_widgets.get(channel_num)
            if widget and hasattr(widget, 'ui_updater'):
                widget.ui_updater.update_channel_state_display(new_state.value)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 处理通道{channel_num}状态变化失败: {e}")
            return False
    
    def handle_test_stopped(self) -> bool:
        """处理测试停止事件"""
        try:
            logger.info("🛑 测试停止，重置所有通道")
            
            with self._lock:
                # 停止所有计时器
                for channel_num in range(1, 9):
                    self.stop_channel_timer(channel_num)
                    
                    # 重置通道状态
                    self.state_manager.set_channel_state(
                        channel_num,
                        ChannelState.CONNECTED,
                        "测试停止",
                        "unified_channel_service"
                    )
                    
                    # 重置进度
                    self.update_channel_progress(channel_num, 0, "已停止")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 处理测试停止失败: {e}")
            return False
    
    def get_channel_stats(self) -> Dict[str, Any]:
        """获取通道统计信息"""
        with self._lock:
            stats = {
                'initialized_channels': len(self.channel_widgets),
                'active_timers': sum(1 for timer in self.channel_timers.values() if timer.is_running),
                'total_tests': sum(data.get('test_count', 0) for data in self.channel_data.values()),
                'channels': {}
            }
            
            for channel_num in range(1, 9):
                channel_state = self.state_manager.get_channel_state(channel_num)
                channel_info = self.channel_data.get(channel_num, {})
                
                stats['channels'][channel_num] = {
                    'state': channel_state.value,
                    'initialized': channel_num in self.channel_widgets,
                    'timer_running': channel_num in self.channel_timers and self.channel_timers[channel_num].is_running,
                    'test_count': channel_info.get('test_count', 0),
                    'last_update': channel_info.get('last_update', '').isoformat() if channel_info.get('last_update') else '',
                    'status': channel_info.get('status', 'unknown')
                }
            
            return stats
    
    def reset_all_channels(self):
        """重置所有通道"""
        try:
            with self._lock:
                # 停止所有计时器
                for timer in self.channel_timers.values():
                    timer.stop()
                
                # 重置所有通道状态
                for channel_num in range(1, 9):
                    self.state_manager.set_channel_state(
                        channel_num,
                        ChannelState.DISCONNECTED,
                        "系统重置",
                        "unified_channel_service"
                    )
                
                # 清理数据
                self.channel_data.clear()
                
                logger.info("🔄 所有通道已重置")
                
        except Exception as e:
            logger.error(f"❌ 重置所有通道失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        try:
            # 取消事件订阅
            self.event_bus.unsubscribe(EventType.CHANNEL_STARTED, self.channel_event_handler)
            self.event_bus.unsubscribe(EventType.CHANNEL_COMPLETED, self.channel_event_handler)
            self.event_bus.unsubscribe(EventType.CHANNEL_PROGRESS, self.channel_event_handler)
            self.event_bus.unsubscribe(EventType.TEST_STOPPED, self.channel_event_handler)
            
            # 移除状态观察者
            self.state_manager.remove_observer(self.channel_state_observer)
            
            # 重置所有通道
            self.reset_all_channels()
            
            # 清理引用
            self.channel_widgets.clear()
            self.channel_timers.clear()
            
            logger.info("🧹 统一通道服务已清理")
            
        except Exception as e:
            logger.error(f"❌ 清理统一通道服务失败: {e}")


# 全局统一通道服务实例
_global_channel_service = None


def get_channel_service(main_window=None) -> Optional[UnifiedChannelService]:
    """获取全局统一通道服务实例"""
    global _global_channel_service
    if _global_channel_service is None and main_window:
        _global_channel_service = UnifiedChannelService(main_window)
    return _global_channel_service


def reset_channel_service():
    """重置全局统一通道服务（主要用于测试）"""
    global _global_channel_service
    if _global_channel_service:
        _global_channel_service.cleanup()
    _global_channel_service = None
