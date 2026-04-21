# -*- coding: utf-8 -*-
"""
打印集成管理器
负责处理打印相关的集成功能，包括标签打印触发、数据准备、打印状态管理等

Author: Jack
Date: 2025-06-27
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class PrintIntegrationManager(QObject):
    """打印集成管理器"""
    
    # 信号定义
    print_triggered = pyqtSignal(int, dict)  # 打印触发信号 (channel, data)
    print_data_prepared = pyqtSignal(int, dict)  # 打印数据准备完成信号 (channel, data)
    print_status_changed = pyqtSignal(bool, dict)  # 打印状态变更信号 (connected, info)
    
    def __init__(self, main_window, config_manager, parent=None):
        """
        初始化打印集成管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
            parent: 父对象
        """
        super().__init__(parent)
        
        self.main_window = main_window
        self.config_manager = config_manager
        
        # 打印状态
        self.print_enabled = False
        self.auto_print_enabled = False
        self.printer_connected = False
        
        # 打印队列
        self.print_queue = []
        
    def initialize(self):
        """初始化打印集成管理器"""
        try:
            # 加载打印设置
            self.print_enabled = self.config_manager.get('print.enabled', True)
            self.auto_print_enabled = self.config_manager.get('test.auto_print', False)
            
            # 连接打印管理器信号
            self._connect_print_manager_signals()
            
            logger.debug("打印集成管理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化打印集成管理器失败: {e}")

    def _connect_print_manager_signals(self):
        """连接打印管理器信号"""
        try:
            if hasattr(self.main_window, 'print_manager'):
                print_manager = self.main_window.print_manager
                
                # 连接打印状态信号
                if hasattr(print_manager, 'printer_status_changed'):
                    print_manager.printer_status_changed.connect(self._on_printer_status_changed)
                
                # 连接打印完成信号
                if hasattr(print_manager, 'label_print_completed'):
                    print_manager.label_print_completed.connect(self._on_label_print_completed)
                
                # 连接打印开始信号
                if hasattr(print_manager, 'label_print_started'):
                    print_manager.label_print_started.connect(self._on_label_print_started)
                
                # 连接打印队列更新信号
                if hasattr(print_manager, 'print_queue_updated'):
                    print_manager.print_queue_updated.connect(self._on_print_queue_updated)
                    
        except Exception as e:
            logger.error(f"连接打印管理器信号失败: {e}")

    def trigger_label_print(self, channel_num: int, result_data: dict):
        """触发标签打印"""
        try:
            # 检查打印是否启用
            if not self.print_enabled:
                logger.debug(f"打印功能未启用，跳过通道{channel_num}打印")
                return
            
            # 检查是否启用自动打印
            if not self.auto_print_enabled:
                logger.debug(f"自动打印未启用，跳过通道{channel_num}打印")
                return
            
            # 检查打印机连接状态
            if not self.printer_connected:
                logger.warning(f"打印机未连接，无法打印通道{channel_num}标签")
                return
            
            logger.info(f"🖨️ 触发通道{channel_num}标签打印")
            
            # 准备打印数据
            print_data = self.prepare_print_data(channel_num, result_data)
            if not print_data:
                logger.error(f"通道{channel_num}打印数据准备失败")
                return
            
            # 发送打印数据准备完成信号
            self.print_data_prepared.emit(channel_num, print_data)
            
            # 执行打印
            self._execute_print(channel_num, print_data)
            
            # 发送打印触发信号
            self.print_triggered.emit(channel_num, print_data)
            
        except Exception as e:
            logger.error(f"触发通道{channel_num}标签打印失败: {e}")

    def prepare_print_data(self, channel_num: int, result_data: dict) -> dict:
        """准备打印数据（统一使用通道组件数据源）"""
        try:
            logger.debug(f"开始准备通道{channel_num}打印数据")
            
            # 获取通道组件
            channel_widget = self._get_channel_widget(channel_num)
            if not channel_widget:
                logger.error(f"通道{channel_num}组件未找到")
                return {}
            
            # 从通道组件获取打印数据
            if hasattr(channel_widget, 'get_print_data'):
                print_data = channel_widget.get_print_data()
                logger.info(f"通道{channel_num}从组件获取打印数据成功")
            else:
                # 备用方法：从result_data构建打印数据
                print_data = self._build_print_data_from_result(channel_num, result_data)
                logger.info(f"通道{channel_num}使用备用方法构建打印数据")
            
            # 验证打印数据
            if not self._validate_print_data(print_data):
                logger.error(f"通道{channel_num}打印数据验证失败")
                return {}
            
            # 添加打印时间戳
            print_data['print_timestamp'] = datetime.now().isoformat()
            
            logger.debug(f"通道{channel_num}打印数据准备完成: {print_data}")
            return print_data
            
        except Exception as e:
            logger.error(f"准备通道{channel_num}打印数据失败: {e}")
            return {}

    def _get_channel_widget(self, channel_num: int):
        """获取通道组件"""
        try:
            if hasattr(self.main_window, 'channel_display_widget'):
                return getattr(self.main_window.channel_display_widget, f'channel_{channel_num}', None)
            return None
        except Exception as e:
            logger.error(f"获取通道{channel_num}组件失败: {e}")
            return None

    def _build_print_data_from_result(self, channel_num: int, result_data: dict) -> dict:
        """从结果数据构建打印数据（备用方法）"""
        try:
            print_data = {
                'channel_number': channel_num,
                'battery_code': result_data.get('battery_code', ''),
                'voltage': result_data.get('voltage', 0.0),
                'rs_value': result_data.get('rs_value', 0.0),
                'rct_value': result_data.get('rct_value', 0.0),
                'rs_grade': result_data.get('rs_grade', '--'),
                'rct_grade': result_data.get('rct_grade', '--'),
                'is_pass': result_data.get('is_pass', False),
                'outlier_rate': result_data.get('outlier_rate', '--'),
                'timestamp': datetime.now()
            }
            
            return print_data
            
        except Exception as e:
            logger.error(f"从结果数据构建打印数据失败: {e}")
            return {}

    def _validate_print_data(self, print_data: dict) -> bool:
        """验证打印数据"""
        try:
            required_fields = ['channel_number', 'battery_code', 'voltage', 'rs_value', 'rct_value']
            
            for field in required_fields:
                if field not in print_data:
                    logger.warning(f"打印数据缺少必需字段: {field}")
                    return False
            
            # 检查数值字段的有效性
            if print_data['voltage'] < 0:
                logger.warning(f"电压值无效: {print_data['voltage']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证打印数据失败: {e}")
            return False

    def _execute_print(self, channel_num: int, print_data: dict):
        """执行打印"""
        try:
            if not hasattr(self.main_window, 'print_manager'):
                logger.error("打印管理器未找到，无法执行打印")
                return
            
            print_manager = self.main_window.print_manager
            
            # 获取当前模板配置
            template_config = self.config_manager.get('label_template', {})
            current_template = template_config.get('current_template', 'default')
            
            # 执行打印
            if hasattr(print_manager, 'print_label'):
                print_manager.print_label(print_data, current_template)
                logger.info(f"通道{channel_num}标签打印已提交")
            else:
                logger.error("打印管理器缺少print_label方法")
                
        except Exception as e:
            logger.error(f"执行通道{channel_num}打印失败: {e}")

    def _on_printer_status_changed(self, connected: bool, printer_info: Optional[dict] = None):
        """打印机状态变更处理"""
        try:
            self.printer_connected = connected
            logger.info(f"打印机状态变更: {'已连接' if connected else '已断开'}")
            
            # 发送打印状态变更信号
            self.print_status_changed.emit(connected, printer_info or {})
            
        except Exception as e:
            logger.error(f"处理打印机状态变更失败: {e}")

    def _on_label_print_started(self, print_job_info: dict):
        """标签打印开始处理"""
        try:
            logger.info(f"标签打印开始: {print_job_info}")
        except Exception as e:
            logger.error(f"处理标签打印开始失败: {e}")

    def _on_label_print_completed(self, print_result: dict):
        """标签打印完成处理"""
        try:
            logger.info(f"标签打印完成: {print_result}")
        except Exception as e:
            logger.error(f"处理标签打印完成失败: {e}")

    def _on_print_queue_updated(self, queue_info: dict):
        """打印队列更新处理"""
        try:
            logger.debug(f"打印队列更新: {queue_info}")
        except Exception as e:
            logger.error(f"处理打印队列更新失败: {e}")

    def set_print_enabled(self, enabled: bool):
        """设置打印启用状态"""
        self.print_enabled = enabled
        self.config_manager.set('print.enabled', enabled)
        logger.info(f"打印功能{'启用' if enabled else '禁用'}")

    def set_auto_print_enabled(self, enabled: bool):
        """设置自动打印启用状态"""
        self.auto_print_enabled = enabled
        self.config_manager.set('test.auto_print', enabled)
        logger.info(f"自动打印功能{'启用' if enabled else '禁用'}")

    def get_print_status(self) -> dict:
        """获取打印状态"""
        return {
            'print_enabled': self.print_enabled,
            'auto_print_enabled': self.auto_print_enabled,
            'printer_connected': self.printer_connected,
            'queue_length': len(self.print_queue)
        }

    def add_to_print_queue(self, channel_num: int, print_data: dict):
        """添加到打印队列"""
        try:
            queue_item = {
                'channel_num': channel_num,
                'print_data': print_data,
                'timestamp': datetime.now(),
                'status': 'pending'
            }
            
            self.print_queue.append(queue_item)
            logger.debug(f"通道{channel_num}已添加到打印队列")
            
        except Exception as e:
            logger.error(f"添加到打印队列失败: {e}")

    def process_print_queue(self):
        """处理打印队列"""
        try:
            if not self.printer_connected:
                logger.debug("打印机未连接，跳过队列处理")
                return
            
            pending_items = [item for item in self.print_queue if item['status'] == 'pending']
            
            for item in pending_items:
                try:
                    self._execute_print(item['channel_num'], item['print_data'])
                    item['status'] = 'printed'
                    logger.debug(f"队列中通道{item['channel_num']}打印完成")
                except Exception as e:
                    item['status'] = 'failed'
                    logger.error(f"队列中通道{item['channel_num']}打印失败: {e}")
                    
        except Exception as e:
            logger.error(f"处理打印队列失败: {e}")

    def clear_print_queue(self):
        """清空打印队列"""
        self.print_queue.clear()
        logger.info("打印队列已清空")

    def get_print_queue_status(self) -> dict:
        """获取打印队列状态"""
        try:
            status_counts = {}
            for item in self.print_queue:
                status = item['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                'total_items': len(self.print_queue),
                'status_counts': status_counts,
                'queue_items': self.print_queue
            }
            
        except Exception as e:
            logger.error(f"获取打印队列状态失败: {e}")
            return {}

    def cleanup(self):
        """清理资源"""
        try:
            # 清空打印队列
            self.clear_print_queue()
            
            logger.debug("打印集成管理器资源已清理")
            
        except Exception as e:
            logger.error(f"清理打印集成管理器资源失败: {e}")
