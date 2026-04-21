# -*- coding: utf-8 -*-
"""
通道延迟判断管理器
负责单个通道的延迟判断功能，实现批量显示效果

Author: Jack
Date: 2025-06-27
"""

import logging
import time
from typing import Optional, Dict, Any, Callable
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class ChannelDelayedJudgmentManager(QObject):
    """通道延迟判断管理器"""
    
    # 信号定义
    judgment_ready = pyqtSignal(int, bool, int, int, list)  # 判断结果准备信号 (channel, is_pass, rs_grade, rct_grade, fail_items)
    completion_ready = pyqtSignal(int, bool, int, int, list)  # 完成结果准备信号 (channel, is_pass, rs_grade, rct_grade, fail_items)
    
    def __init__(self, channel_number: int, parent=None):
        """
        初始化延迟判断管理器
        
        Args:
            channel_number: 通道号
            parent: 父对象
        """
        super().__init__(parent)
        
        self.channel_number = channel_number
        
        # 延迟判断相关
        self._pending_judgment_data = None
        self._judgment_timer = None
        
        # 延迟完成相关
        self._pending_completion_data = None
        self._completion_timer = None
        
        # 回调函数
        self.judgment_callback = None
        self.completion_callback = None
        
    def set_judgment_callback(self, callback: Callable):
        """设置判断回调函数"""
        self.judgment_callback = callback
        
    def set_completion_callback(self, callback: Callable):
        """设置完成回调函数"""
        self.completion_callback = callback
        
    def schedule_delayed_judgment(self, voltage: float, rs_value: float, rct_value: float, 
                                outlier_result: Optional[str] = None, backend_result: Optional[dict] = None):
        """
        安排延迟判断，实现批量判断效果

        Args:
            voltage: 电压值
            rs_value: Rs值
            rct_value: Rct值
            outlier_result: 离群检测结果
            backend_result: 后端测试结果
        """
        try:
            # 保存判断参数
            self._pending_judgment_data = {
                'voltage': voltage,
                'rs_value': rs_value,
                'rct_value': rct_value,
                'outlier_result': outlier_result,
                'backend_result': backend_result,
                'timestamp': time.time()
            }

            # 检查是否已经有延迟判断定时器
            if not self._judgment_timer or not self._judgment_timer.isActive():
                # 创建延迟判断定时器
                self._judgment_timer = QTimer()
                self._judgment_timer.setSingleShot(True)
                self._judgment_timer.timeout.connect(self._execute_delayed_judgment)

                # 设置延迟时间（300ms），让多个通道的判断请求能够聚集
                self._judgment_timer.start(300)

                logger.debug(f"通道{self.channel_number} 安排延迟判断，300ms后执行")
            else:
                logger.debug(f"通道{self.channel_number} 延迟判断已安排，更新判断数据")

        except Exception as e:
            logger.error(f"通道{self.channel_number}安排延迟判断失败: {e}")

    def _execute_delayed_judgment(self):
        """执行延迟的判断"""
        try:
            if not self._pending_judgment_data:
                logger.warning(f"通道{self.channel_number} 没有待执行的判断数据")
                return

            judgment_data = self._pending_judgment_data
            logger.debug(f"通道{self.channel_number} 执行延迟判断")

            # 执行判断逻辑
            if self.judgment_callback:
                self.judgment_callback(
                    judgment_data['voltage'],
                    judgment_data['rs_value'],
                    judgment_data['rct_value'],
                    judgment_data['outlier_result']
                )

            # 清理判断数据
            self._pending_judgment_data = None

        except Exception as e:
            logger.error(f"通道{self.channel_number}执行延迟判断失败: {e}")

    def schedule_delayed_completion(self, is_pass: bool, rs_grade: int, rct_grade: int, fail_items: Optional[list] = None):
        """
        安排延迟完成显示，实现批量显示效果

        Args:
            is_pass: 是否合格
            rs_grade: Rs档位
            rct_grade: Rct档位
            fail_items: 失败项目列表
        """
        try:
            # 保存完成参数
            self._pending_completion_data = {
                'is_pass': is_pass,
                'rs_grade': rs_grade,
                'rct_grade': rct_grade,
                'fail_items': fail_items,
                'timestamp': time.time()
            }

            # 检查是否已经有延迟完成定时器
            if not self._completion_timer or not self._completion_timer.isActive():
                # 创建延迟完成定时器
                self._completion_timer = QTimer()
                self._completion_timer.setSingleShot(True)
                self._completion_timer.timeout.connect(self._execute_delayed_completion)

                # 设置延迟时间（500ms），让多个通道的完成请求能够聚集
                self._completion_timer.start(500)

                logger.debug(f"通道{self.channel_number} 安排延迟完成显示，500ms后执行")
            else:
                logger.debug(f"通道{self.channel_number} 延迟完成显示已安排，更新完成数据")

        except Exception as e:
            logger.error(f"通道{self.channel_number}安排延迟完成显示失败: {e}")

    def _execute_delayed_completion(self):
        """执行延迟的完成显示"""
        try:
            if not self._pending_completion_data:
                logger.warning(f"通道{self.channel_number} 没有待执行的完成数据")
                return

            completion_data = self._pending_completion_data
            logger.debug(f"通道{self.channel_number} 执行延迟完成显示")

            # 发送完成准备信号
            self.completion_ready.emit(
                self.channel_number,
                completion_data['is_pass'],
                completion_data['rs_grade'],
                completion_data['rct_grade'],
                completion_data['fail_items']
            )

            # 执行完成逻辑
            if self.completion_callback:
                self.completion_callback(
                    completion_data['is_pass'],
                    completion_data['rs_grade'],
                    completion_data['rct_grade'],
                    completion_data['fail_items']
                )

            # 清理完成数据
            self._pending_completion_data = None

        except Exception as e:
            logger.error(f"通道{self.channel_number}执行延迟完成显示失败: {e}")

    def cancel_delayed_judgment(self):
        """取消延迟判断"""
        try:
            if self._judgment_timer and self._judgment_timer.isActive():
                self._judgment_timer.stop()
                logger.debug(f"通道{self.channel_number} 取消延迟判断")

            self._pending_judgment_data = None

        except Exception as e:
            logger.error(f"通道{self.channel_number}取消延迟判断失败: {e}")

    def cancel_delayed_completion(self):
        """取消延迟完成"""
        try:
            if self._completion_timer and self._completion_timer.isActive():
                self._completion_timer.stop()
                logger.debug(f"通道{self.channel_number} 取消延迟完成")

            self._pending_completion_data = None

        except Exception as e:
            logger.error(f"通道{self.channel_number}取消延迟完成失败: {e}")

    def has_pending_judgment(self) -> bool:
        """检查是否有待执行的判断"""
        return self._pending_judgment_data is not None

    def has_pending_completion(self) -> bool:
        """检查是否有待执行的完成"""
        return self._pending_completion_data is not None

    def get_pending_judgment_data(self) -> Optional[dict]:
        """获取待执行的判断数据"""
        return self._pending_judgment_data

    def get_pending_completion_data(self) -> Optional[dict]:
        """获取待执行的完成数据"""
        return self._pending_completion_data

    def force_execute_judgment(self):
        """强制执行判断（不等待延迟）"""
        try:
            if self._judgment_timer and self._judgment_timer.isActive():
                self._judgment_timer.stop()

            if self._pending_judgment_data:
                self._execute_delayed_judgment()

        except Exception as e:
            logger.error(f"通道{self.channel_number}强制执行判断失败: {e}")

    def force_execute_completion(self):
        """强制执行完成（不等待延迟）"""
        try:
            if self._completion_timer and self._completion_timer.isActive():
                self._completion_timer.stop()

            if self._pending_completion_data:
                self._execute_delayed_completion()

        except Exception as e:
            logger.error(f"通道{self.channel_number}强制执行完成失败: {e}")

    def reset_delayed_operations(self):
        """重置所有延迟操作"""
        try:
            self.cancel_delayed_judgment()
            self.cancel_delayed_completion()
            logger.debug(f"通道{self.channel_number} 重置所有延迟操作")

        except Exception as e:
            logger.error(f"通道{self.channel_number}重置延迟操作失败: {e}")

    def set_judgment_delay(self, delay_ms: int):
        """设置判断延迟时间"""
        if self._judgment_timer and self._judgment_timer.isActive():
            self._judgment_timer.stop()
            self._judgment_timer.start(delay_ms)

    def set_completion_delay(self, delay_ms: int):
        """设置完成延迟时间"""
        if self._completion_timer and self._completion_timer.isActive():
            self._completion_timer.stop()
            self._completion_timer.start(delay_ms)
