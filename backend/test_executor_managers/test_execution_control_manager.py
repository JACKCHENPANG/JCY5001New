# -*- coding: utf-8 -*-
"""
测试执行控制管理器
负责测试的启动、停止、暂停、重置等控制功能

Author: Jack
Date: 2025-06-27
"""

import logging
import threading
import time
from typing import Dict, Any, List, Callable, Optional
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class TestExecutionControlManager(QObject):
    """测试执行控制管理器"""
    
    # 信号定义
    test_started = pyqtSignal(dict, list)  # 测试开始信号 (test_config, enabled_channels)
    test_stopped = pyqtSignal(str)  # 测试停止信号 (reason)
    test_paused = pyqtSignal()  # 测试暂停信号
    test_resumed = pyqtSignal()  # 测试恢复信号
    test_reset = pyqtSignal()  # 测试重置信号
    execution_status_changed = pyqtSignal(dict)  # 执行状态变更信号
    
    def __init__(self, parent=None):
        """
        初始化测试执行控制管理器
        
        Args:
            parent: 父对象
        """
        super().__init__(parent)
        
        # 执行控制状态
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.is_testing = False
        self.is_paused = False
        
        # 回调函数
        self.progress_callback = None
        self.status_callback = None
        
        # 活跃的测试管理器引用
        self._current_staggered_manager = None
        self._current_simultaneous_manager = None
        
    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback
        logger.debug("进度回调函数已设置")

    def set_status_callback(self, callback: Callable):
        """设置状态回调函数"""
        self.status_callback = callback
        logger.debug("状态回调函数已设置")

    def set_stop_event(self, stop_event: threading.Event):
        """设置停止事件"""
        self.stop_event = stop_event
        logger.debug("停止事件已设置")

    def start_test(self, test_config: Dict[str, Any], enabled_channels: List[int]) -> bool:
        """
        启动测试
        
        Args:
            test_config: 测试配置
            enabled_channels: 启用的通道列表
            
        Returns:
            是否启动成功
        """
        try:
            if self.is_testing:
                logger.warning("测试已在进行中，无法重复启动")
                return False
            
            logger.info("🚀 启动测试执行控制")
            
            # 重置控制状态
            self.reset_execution()
            
            # 设置测试状态
            self.is_testing = True
            self.is_paused = False
            
            # 发送测试开始信号
            self.test_started.emit(test_config, enabled_channels)
            
            # 更新执行状态
            self._update_execution_status()
            
            logger.info(f"✅ 测试启动成功，通道: {enabled_channels}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动测试失败: {e}")
            self.is_testing = False
            return False

    def stop_test(self, reason: str = "用户停止") -> bool:
        """
        停止测试
        
        Args:
            reason: 停止原因
            
        Returns:
            是否停止成功
        """
        try:
            if not self.is_testing:
                logger.debug("测试未在进行中，无需停止")
                return True
            
            logger.info(f"🛑 停止测试执行: {reason}")
            
            # 设置停止事件
            self.stop_event.set()
            
            # 停止活跃的测试管理器
            self._stop_active_test_managers()
            
            # 设置测试状态
            self.is_testing = False
            self.is_paused = False
            
            # 发送测试停止信号
            self.test_stopped.emit(reason)
            
            # 更新执行状态
            self._update_execution_status()
            
            logger.info(f"✅ 测试停止完成: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 停止测试失败: {e}")
            return False

    def pause_test(self) -> bool:
        """
        暂停测试
        
        Returns:
            是否暂停成功
        """
        try:
            if not self.is_testing:
                logger.warning("测试未在进行中，无法暂停")
                return False
            
            if self.is_paused:
                logger.warning("测试已暂停，无需重复暂停")
                return True
            
            logger.info("⏸️ 暂停测试执行")
            
            # 设置暂停状态
            self.is_paused = True
            self.pause_event.set()
            
            # 发送测试暂停信号
            self.test_paused.emit()
            
            # 更新执行状态
            self._update_execution_status()
            
            logger.info("✅ 测试暂停完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 暂停测试失败: {e}")
            return False

    def resume_test(self) -> bool:
        """
        恢复测试
        
        Returns:
            是否恢复成功
        """
        try:
            if not self.is_testing:
                logger.warning("测试未在进行中，无法恢复")
                return False
            
            if not self.is_paused:
                logger.warning("测试未暂停，无需恢复")
                return True
            
            logger.info("▶️ 恢复测试执行")
            
            # 清除暂停状态
            self.is_paused = False
            self.pause_event.clear()
            
            # 发送测试恢复信号
            self.test_resumed.emit()
            
            # 更新执行状态
            self._update_execution_status()
            
            logger.info("✅ 测试恢复完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 恢复测试失败: {e}")
            return False

    def reset_execution(self):
        """重置执行状态"""
        try:
            logger.debug("🔄 重置测试执行状态")
            
            # 清除所有事件
            self.stop_event.clear()
            self.pause_event.clear()
            
            # 重置状态
            self.is_testing = False
            self.is_paused = False
            
            # 清除活跃管理器引用
            self._current_staggered_manager = None
            self._current_simultaneous_manager = None
            
            # 发送测试重置信号
            self.test_reset.emit()
            
            # 更新执行状态
            self._update_execution_status()
            
            logger.debug("✅ 测试执行状态重置完成")
            
        except Exception as e:
            logger.error(f"❌ 重置执行状态失败: {e}")

    def _stop_active_test_managers(self):
        """停止活跃的测试管理器"""
        try:
            logger.debug("停止活跃的测试管理器")
            
            # 停止错频测试管理器
            if self._current_staggered_manager:
                try:
                    if hasattr(self._current_staggered_manager, 'stop'):
                        self._current_staggered_manager.stop()
                        logger.debug("错频测试管理器已停止")
                except Exception as e:
                    logger.error(f"停止错频测试管理器失败: {e}")
                finally:
                    self._current_staggered_manager = None
            
            # 停止同时测试管理器
            if self._current_simultaneous_manager:
                try:
                    if hasattr(self._current_simultaneous_manager, 'stop'):
                        self._current_simultaneous_manager.stop()
                        logger.debug("同时测试管理器已停止")
                except Exception as e:
                    logger.error(f"停止同时测试管理器失败: {e}")
                finally:
                    self._current_simultaneous_manager = None
                    
        except Exception as e:
            logger.error(f"停止活跃测试管理器失败: {e}")

    def set_active_staggered_manager(self, manager):
        """设置活跃的错频测试管理器"""
        self._current_staggered_manager = manager
        logger.debug("活跃错频测试管理器已设置")

    def set_active_simultaneous_manager(self, manager):
        """设置活跃的同时测试管理器"""
        self._current_simultaneous_manager = manager
        logger.debug("活跃同时测试管理器已设置")

    def get_execution_status(self) -> Dict[str, Any]:
        """
        获取执行状态
        
        Returns:
            执行状态字典
        """
        try:
            status = {
                'is_testing': self.is_testing,
                'is_paused': self.is_paused,
                'stop_event_set': self.stop_event.is_set(),
                'pause_event_set': self.pause_event.is_set(),
                'has_staggered_manager': self._current_staggered_manager is not None,
                'has_simultaneous_manager': self._current_simultaneous_manager is not None,
                'timestamp': time.time()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"获取执行状态失败: {e}")
            return {}

    def _update_execution_status(self):
        """更新执行状态并发送信号"""
        try:
            status = self.get_execution_status()
            self.execution_status_changed.emit(status)
        except Exception as e:
            logger.error(f"更新执行状态失败: {e}")

    def is_stop_requested(self) -> bool:
        """检查是否请求停止"""
        return self.stop_event.is_set()

    def is_pause_requested(self) -> bool:
        """检查是否请求暂停"""
        return self.pause_event.is_set()

    def wait_for_pause_or_stop(self, timeout: Optional[float] = None) -> str:
        """
        等待暂停或停止信号
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            'stop', 'pause', 或 'timeout'
        """
        try:
            # 使用threading.Event的wait方法等待信号
            if self.stop_event.wait(timeout=0):  # 立即检查停止
                return 'stop'
            
            if self.pause_event.wait(timeout=0):  # 立即检查暂停
                return 'pause'
            
            # 如果有超时，等待指定时间
            if timeout and timeout > 0:
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if self.stop_event.is_set():
                        return 'stop'
                    if self.pause_event.is_set():
                        return 'pause'
                    time.sleep(0.1)  # 短暂休眠避免CPU占用过高
                
                return 'timeout'
            
            return 'none'
            
        except Exception as e:
            logger.error(f"等待暂停或停止信号失败: {e}")
            return 'error'

    def cleanup(self):
        """清理资源"""
        try:
            # 停止所有活动
            self.stop_test("清理资源")
            
            # 清除回调
            self.progress_callback = None
            self.status_callback = None
            
            logger.debug("测试执行控制管理器资源已清理")
            
        except Exception as e:
            logger.error(f"清理测试执行控制管理器资源失败: {e}")
