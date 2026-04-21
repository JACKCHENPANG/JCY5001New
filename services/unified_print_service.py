# -*- coding: utf-8 -*-
"""
统一打印服务
合并所有自动打印管理器，提供统一的打印接口

Author: Jack
Date: 2025-01-30
"""

import logging
import threading
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from core import get_event_bus, get_state_manager, EventType, EventHandler

logger = logging.getLogger(__name__)


class PrintEventHandler(EventHandler):
    """打印事件处理器"""
    
    def __init__(self, print_service):
        super().__init__("print_event_handler")
        self.print_service = print_service
    
    def _handle_event(self, event):
        """处理打印相关事件"""
        try:
            if event.event_type == EventType.RESULT_CALCULATED:
                # 测试结果计算完成，触发打印检查
                channel_num = event.data.get('channel_num')
                result_data = event.data.get('result_data')
                if channel_num and result_data:
                    return self.print_service.handle_test_result(channel_num, result_data)
            
            elif event.event_type == EventType.TEST_COMPLETED:
                # 测试完成，触发批量打印检查
                return self.print_service.handle_test_completion(event.data)
            
            elif event.event_type == EventType.TEST_STOPPED:
                # 测试停止，清理打印状态
                return self.print_service.handle_test_stopped()
            
            return True
            
        except Exception as e:
            logger.error(f"处理打印事件失败: {e}")
            return False


class UnifiedPrintService:
    """
    统一打印服务
    
    职责：
    - 统一管理所有打印逻辑
    - 替代多个自动打印管理器
    - 提供事件驱动的打印机制
    - 管理打印状态和去重
    """
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.config_manager = main_window.config_manager if hasattr(main_window, 'config_manager') else None
        self.label_print_manager = main_window.label_print_manager if hasattr(main_window, 'label_print_manager') else None
        
        # 打印状态管理
        self._printed_test_ids: Set[int] = set()
        self._current_test_id: Optional[int] = None
        self._print_lock = threading.RLock()
        
        # 核心服务
        self.event_bus = get_event_bus()
        self.state_manager = get_state_manager()
        
        # 注册事件处理器
        self.print_event_handler = PrintEventHandler(self)
        self._register_event_handlers()
        
        logger.info("✅ 统一打印服务初始化完成")
    
    def _register_event_handlers(self):
        """注册事件处理器"""
        try:
            # 订阅相关事件
            self.event_bus.subscribe(EventType.RESULT_CALCULATED, self.print_event_handler)
            self.event_bus.subscribe(EventType.TEST_COMPLETED, self.print_event_handler)
            self.event_bus.subscribe(EventType.TEST_STOPPED, self.print_event_handler)
            
            logger.debug("✅ 打印事件处理器注册完成")
            
        except Exception as e:
            logger.error(f"❌ 注册打印事件处理器失败: {e}")
    
    def start_new_test_session(self, test_id: int):
        """
        开始新的测试会话
        
        Args:
            test_id: 测试ID
        """
        try:
            with self._print_lock:
                self._current_test_id = test_id
                self._printed_test_ids.clear()
                
                # 通知标签打印管理器
                if self.label_print_manager:
                    self.label_print_manager.start_new_test_session(test_id)
                
                logger.info(f"🆕 开始新的打印会话: {test_id}")
                
        except Exception as e:
            logger.error(f"❌ 开始新打印会话失败: {e}")
    
    def handle_test_result(self, channel_num: int, result_data: Dict[str, Any]) -> bool:
        """
        处理单个测试结果的打印
        
        Args:
            channel_num: 通道号
            result_data: 测试结果数据
            
        Returns:
            是否处理成功
        """
        try:
            # Jack要求检查测试是否被停止
            if self.state_manager.test_state.value in ['stopping', 'idle']:
                logger.warning(f"🛑 通道{channel_num}测试已停止，跳过打印")
                return True
            
            # 检查是否启用自动打印
            if not self._is_auto_print_enabled():
                logger.debug(f"通道{channel_num}自动打印未启用，跳过")
                return True
            
            # 检查取样测试模式
            if self._is_sampling_test_mode():
                logger.info(f"🎯 通道{channel_num}取样测试模式：跳过打印")
                return True
            
            # 检查打印机是否就绪
            if not self._is_printer_ready():
                logger.warning(f"通道{channel_num}打印机未就绪，跳过打印")
                return True
            
            # 检查是否已经打印过
            test_id = result_data.get('id')
            if test_id and self._is_already_printed(test_id):
                logger.debug(f"通道{channel_num}测试结果(ID:{test_id})已打印过，跳过")
                return True
            
            # 准备打印数据
            print_data = self._prepare_print_data(result_data)
            if not print_data:
                logger.warning(f"通道{channel_num}打印数据准备失败")
                return False
            
            # 执行打印
            job_id = self._execute_print(print_data)
            
            if job_id:
                # 记录已打印
                if test_id:
                    self._mark_as_printed(test_id)
                
                logger.info(f"✅ 通道{channel_num}打印成功: Rs={print_data.get('rs_value', 0):.3f}mΩ, "
                           f"Rct={print_data.get('rct_value', 0):.3f}mΩ, 任务ID={job_id}")
                
                # 发布打印完成事件
                self.event_bus.publish(
                    EventType.RESULT_PRINTED,
                    {
                        'channel_num': channel_num,
                        'test_id': test_id,
                        'job_id': job_id,
                        'print_data': print_data
                    },
                    "unified_print_service"
                )
                
                return True
            else:
                logger.error(f"❌ 通道{channel_num}打印失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 处理通道{channel_num}测试结果打印失败: {e}")
            return False
    
    def handle_test_completion(self, completion_data: Dict[str, Any]) -> bool:
        """
        处理测试完成的批量打印
        
        Args:
            completion_data: 测试完成数据
            
        Returns:
            是否处理成功
        """
        try:
            # Jack要求检查测试是否被停止
            if self.state_manager.test_state.value in ['stopping', 'idle']:
                logger.warning("🛑 测试已停止，跳过批量打印")
                return True
            
            # 获取测试结果
            test_results = completion_data.get('test_results', [])
            if not test_results:
                logger.debug("没有测试结果需要批量打印")
                return True
            
            logger.debug(f" 开始批量打印检查: {len(test_results)}个结果")
            
            printed_count = 0
            for result in test_results:
                channel_num = result.get('channel_number')
                if channel_num and self.handle_test_result(channel_num, result):
                    printed_count += 1
            
            logger.info(f"✅ 批量打印完成: {printed_count}/{len(test_results)}成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 处理测试完成批量打印失败: {e}")
            return False
    
    def handle_test_stopped(self) -> bool:
        """
        处理测试停止
        
        Returns:
            是否处理成功
        """
        try:
            logger.info("🛑 测试停止，清理打印状态")
            
            with self._print_lock:
                # 不清理已打印记录，保持去重功能
                # self._printed_test_ids.clear()
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 处理测试停止失败: {e}")
            return False
    
    def _is_auto_print_enabled(self) -> bool:
        """检查是否启用自动打印"""
        try:
            if self.label_print_manager:
                return self.label_print_manager.is_auto_print_enabled()
            return False
        except Exception as e:
            logger.error(f"检查自动打印状态失败: {e}")
            return False
    
    def _is_sampling_test_mode(self) -> bool:
        """检查是否为取样测试模式"""
        try:
            if self.config_manager:
                return self.config_manager.get('test.sampling_test', False)
            return False
        except Exception as e:
            logger.error(f"检查取样测试模式失败: {e}")
            return False
    
    def _is_printer_ready(self) -> bool:
        """检查打印机是否就绪"""
        try:
            if self.label_print_manager:
                return self.label_print_manager.is_printer_ready()
            return False
        except Exception as e:
            logger.error(f"检查打印机状态失败: {e}")
            return False
    
    def _is_already_printed(self, test_id: int) -> bool:
        """检查是否已经打印过"""
        with self._print_lock:
            return test_id in self._printed_test_ids
    
    def _mark_as_printed(self, test_id: int):
        """标记为已打印"""
        with self._print_lock:
            self._printed_test_ids.add(test_id)
    
    def _prepare_print_data(self, result_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        准备打印数据
        
        Args:
            result_data: 测试结果数据
            
        Returns:
            打印数据或None
        """
        try:
            # 提取关键数据
            print_data = {
                'channel_number': result_data.get('channel_number'),
                'battery_code': result_data.get('battery_code', ''),
                'voltage': result_data.get('voltage', 0.0),
                'rs_value': result_data.get('rs_value', 0.0),
                'rct_value': result_data.get('rct_value', 0.0),
                'rsei_value': result_data.get('rsei_value', 0.0),
                'rs_grade': result_data.get('rs_grade', 0),
                'rct_grade': result_data.get('rct_grade', 0),
                'is_pass': result_data.get('is_pass', False),
                'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'operator': result_data.get('operator', ''),
                'battery_type': result_data.get('battery_type', ''),
                'battery_spec': result_data.get('battery_spec', '')
            }
            
            # 验证必要字段
            if not print_data['channel_number']:
                logger.warning("打印数据缺少通道号")
                return None
            
            return print_data
            
        except Exception as e:
            logger.error(f"准备打印数据失败: {e}")
            return None
    
    def _execute_print(self, print_data: Dict[str, Any]) -> Optional[str]:
        """
        执行打印
        
        Args:
            print_data: 打印数据
            
        Returns:
            打印任务ID或None
        """
        try:
            if self.label_print_manager:
                return self.label_print_manager.print_test_result(print_data)
            else:
                logger.warning("标签打印管理器不可用")
                return None
                
        except Exception as e:
            logger.error(f"执行打印失败: {e}")
            return None
    
    def get_print_stats(self) -> Dict[str, Any]:
        """获取打印统计信息"""
        with self._print_lock:
            return {
                'current_test_id': self._current_test_id,
                'printed_count': len(self._printed_test_ids),
                'printed_test_ids': list(self._printed_test_ids),
                'auto_print_enabled': self._is_auto_print_enabled(),
                'sampling_test_mode': self._is_sampling_test_mode(),
                'printer_ready': self._is_printer_ready()
            }
    
    def reset_printed_records(self):
        """重置已打印记录"""
        with self._print_lock:
            self._printed_test_ids.clear()
            logger.info("🔄 已打印记录已重置")
    
    def cleanup(self):
        """清理资源"""
        try:
            # 取消事件订阅
            self.event_bus.unsubscribe(EventType.RESULT_CALCULATED, self.print_event_handler)
            self.event_bus.unsubscribe(EventType.TEST_COMPLETED, self.print_event_handler)
            self.event_bus.unsubscribe(EventType.TEST_STOPPED, self.print_event_handler)
            
            # 清理状态
            with self._print_lock:
                self._printed_test_ids.clear()
                self._current_test_id = None
            
            logger.info("🧹 统一打印服务已清理")
            
        except Exception as e:
            logger.error(f"❌ 清理统一打印服务失败: {e}")


# 全局统一打印服务实例
_global_print_service = None


def get_print_service(main_window=None) -> Optional[UnifiedPrintService]:
    """获取全局统一打印服务实例"""
    global _global_print_service
    if _global_print_service is None and main_window:
        _global_print_service = UnifiedPrintService(main_window)
    return _global_print_service


def reset_print_service():
    """重置全局统一打印服务（主要用于测试）"""
    global _global_print_service
    if _global_print_service:
        _global_print_service.cleanup()
    _global_print_service = None
