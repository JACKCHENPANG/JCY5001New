"""
简单自动打印管理器 - 测试版本
"""

import logging

logger = logging.getLogger(__name__)


class AutoPrintManager:
    """简单自动打印管理器"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self._printed_test_ids = set()
        logger.info("✅ 自动打印管理器初始化完成")
    
    def trigger_print_for_test_result(self, test_result_data):
        """为单个测试结果触发打印"""
        try:
            test_id = test_result_data.get('id')
            channel_num = test_result_data.get('channel_number')

            if not test_id or not channel_num:
                logger.warning(f"测试结果数据不完整，跳过打印: ID={test_id}, 通道={channel_num}")
                return

            # Jack要求检查测试是否被停止，如果停止则不打印
            if hasattr(self.main_window, 'test_executor') and self.main_window.test_executor:
                if hasattr(self.main_window.test_executor, 'stop_event') and self.main_window.test_executor.stop_event.is_set():
                    logger.warning(f"🛑 通道{channel_num}测试已被停止，跳过打印，避免打印脏数据")
                    return

            if test_id in self._printed_test_ids:
                logger.debug(f"通道{channel_num}测试结果(ID:{test_id})已打印过，跳过")
                return
            
            # 检查是否启用自动打印
            if not self._is_auto_print_enabled():
                logger.debug(f"通道{channel_num}自动打印未启用，跳过")
                return
            
            # 检查打印机是否就绪
            if not self._is_printer_ready():
                logger.warning(f"通道{channel_num}打印机未就绪，跳过打印")
                return
            
            # 检查取样测试模式
            if hasattr(self.main_window, 'config_manager') and self.main_window.config_manager:
                sampling_test = self.main_window.config_manager.get('test.sampling_test', False)
                if sampling_test:
                    logger.info(f"🎯 通道{channel_num}取样测试模式：跳过打印")
                    return
            
            # 准备打印数据
            print_data = self._prepare_print_data(test_result_data)
            if not print_data:
                logger.warning(f"通道{channel_num}打印数据准备失败")
                return
            
            # 执行打印
            if hasattr(self.main_window, 'label_print_manager') and self.main_window.label_print_manager:
                job_id = self.main_window.label_print_manager.print_test_result(print_data)
                
                if job_id:
                    self._printed_test_ids.add(test_id)
                    logger.info(f"✅ 通道{channel_num}打印成功: Rs={print_data.get('rs_value', 0):.3f}mΩ, Rct={print_data.get('rct_value', 0):.3f}mΩ, 任务ID={job_id}")
                else:
                    logger.error(f"❌ 通道{channel_num}打印失败")
            else:
                logger.warning(f"通道{channel_num}标签打印管理器未找到")
                
        except Exception as e:
            logger.error(f"触发通道{test_result_data.get('channel_number', '?')}打印失败: {e}")
    
    def _is_auto_print_enabled(self):
        """检查是否启用自动打印"""
        try:
            if hasattr(self.main_window, 'label_print_manager') and self.main_window.label_print_manager:
                return self.main_window.label_print_manager.is_auto_print_enabled()
        except Exception as e:
            logger.error(f"检查自动打印状态失败: {e}")
        return False
    
    def _is_printer_ready(self):
        """检查打印机是否就绪"""
        try:
            if hasattr(self.main_window, 'label_print_manager') and self.main_window.label_print_manager:
                return self.main_window.label_print_manager.is_printer_ready()
        except Exception as e:
            logger.error(f"检查打印机状态失败: {e}")
        return False
    
    def _prepare_print_data(self, test_result_data):
        """准备打印数据"""
        try:
            channel_num = test_result_data.get('channel_number')
            rs_value = test_result_data.get('rs_value', 0)
            rct_value = test_result_data.get('rct_value', 0)
            
            if rs_value == 0 and rct_value == 0:
                logger.warning(f"通道{channel_num}测试数据异常: Rs={rs_value}, Rct={rct_value}")
                return None
            
            print_data = {
                'channel_number': channel_num,
                'rs_value': rs_value,
                'rct_value': rct_value,
                'rsei_value': test_result_data.get('rsei_value', 0),
                'voltage': test_result_data.get('voltage', 0),
                'rs_grade': test_result_data.get('rs_grade', 0),
                'rct_grade': test_result_data.get('rct_grade', 0),
                'is_pass': test_result_data.get('is_pass', False),
                'fail_reason': test_result_data.get('fail_reason', ''),
                'battery_code': test_result_data.get('battery_code', ''),
                'test_time': test_result_data.get('test_time', ''),
                'impedance_ratio': test_result_data.get('impedance_ratio', 0),
            }
            
            logger.debug(f"通道{channel_num}打印数据准备完成: Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")
            return print_data
            
        except Exception as e:
            logger.error(f"准备通道{test_result_data.get('channel_number', '?')}打印数据失败: {e}")
            return None
    
    def reset_printed_records(self):
        """重置已打印记录"""
        self._printed_test_ids.clear()
        logger.info("🔄 已打印记录已重置")
    
    def get_printed_count(self):
        """获取已打印的数量"""
        return len(self._printed_test_ids)
