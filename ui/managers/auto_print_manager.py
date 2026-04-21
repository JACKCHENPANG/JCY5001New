"""
自动打印管理器 - 全新的简单直接的打印机制
不依赖任何信号传递，直接基于数据库数据触发打印
"""

import logging

logger = logging.getLogger(__name__)


class AutoPrintManager:
    """自动打印管理器 - 简单直接的打印机制"""

    def __init__(self, main_window):
        self.main_window = main_window
        self.label_print_manager = getattr(main_window, 'label_print_manager', None)
        self.config_manager = getattr(main_window, 'config_manager', None)

        # 已打印的测试结果ID集合（防止重复打印）
        self._printed_test_ids = set()

        # 最后检查时间
        self._last_check_time = 0

        logger.info("✅ 自动打印管理器初始化完成")

    def reset_for_new_session(self):
        """开始新的测试会话时重置自动打印去重集合"""
        try:
            old = len(self._printed_test_ids)
            self._printed_test_ids.clear()
            logger.info(f"🆕 自动打印会话已重置，清空已打印ID: {old} 个")
        except Exception as e:
            logger.error(f"重置自动打印会话失败: {e}")

    def trigger_print_for_test_result(self, test_result_data):
        """
        为单个测试结果触发打印

        Args:
            test_result_data: 测试结果数据字典
        """
        try:
            # 获取测试结果ID和通道号
            test_id = test_result_data.get('id')
            channel_num = test_result_data.get('channel_number')

            if not test_id or not channel_num:
                logger.warning(f"测试结果数据不完整，跳过打印: ID={test_id}, 通道={channel_num}")
                return

            # 不做去重：允许同一测试结果重复打印（由上位机流程保证不会误触发）
            # if test_id in self._printed_test_ids:
            #     logger.debug(f"通道{channel_num}测试结果(ID:{test_id})已打印过，跳过")
            #     return

            # 检查是否启用自动打印
            if not self._is_auto_print_enabled():
                logger.debug(f"通道{channel_num}自动打印未启用，跳过")
                return

            # 检查打印机是否就绪
            if not self._is_printer_ready():
                logger.warning(f"通道{channel_num}打印机未就绪，跳过打印")
                return

            # 🎯 取样测试模式：跳过打印
            sampling_test = self.config_manager.get('test.sampling_test', False)
            if sampling_test:
                logger.info(f"🎯 通道{channel_num}取样测试模式：跳过打印")
                return

            # 准备打印数据
            print_data = self._prepare_print_data(test_result_data)
            if not print_data:
                logger.warning(f"通道{channel_num}打印数据准备失败")
                return

            # 执行打印
            logger.debug(f"🖨️ [自动打印] 准备提交打印: CH={channel_num}, 数据摘要={{'V': print_data.get('voltage'), 'Rs': print_data.get('rs_value'), 'Rct': print_data.get('rct_value')}}")
            job_id = self.label_print_manager.print_test_result(print_data)

            if job_id:
                # 标记为已打印
                self._printed_test_ids.add(test_id)
                logger.info(f"✅ 通道{channel_num}打印提交成功, 任务ID={job_id}")
            else:
                logger.error(f"❌ 通道{channel_num}打印未提交（可能因未启用/打印机未就绪/去重）")

        except Exception as e:
            logger.error(f"触发通道{test_result_data.get('channel_number', '?')}打印失败: {e}")

    def trigger_print_for_all_latest_results(self):
        """为所有最新的测试结果触发打印（批量处理）"""
        try:
            # 获取测试执行器
            if not hasattr(self.main_window, 'test_executor') or not self.main_window.test_executor:
                logger.debug("测试执行器未找到，跳过批量打印检查")
                return

            # Jack要求检查测试是否被停止，如果停止则不进行批量打印
            test_executor = self.main_window.test_executor
            if hasattr(test_executor, 'stop_event') and test_executor.stop_event.is_set():
                logger.warning("🛑 测试已被停止，跳过批量打印检查，避免打印脏数据")
                return

            test_result_manager = test_executor.test_result_manager
            if not test_result_manager:
                logger.debug("测试结果管理器未找到，跳过批量打印检查")
                return

            # 获取启用的通道
            enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))

            # 获取所有启用通道的最新测试结果
            latest_results = test_result_manager.get_latest_test_results(enabled_channels)

            if not latest_results:
                logger.debug("没有找到最新的测试结果")
                return

            logger.debug(f" 检查到{len(latest_results)}个最新测试结果，开始批量打印检查")

            # 为每个结果触发打印
            printed_count = 0
            for result in latest_results:
                channel_num = result.get('channel_number')
                test_id = result.get('id')

                # 检查是否已经打印过
                if test_id not in self._printed_test_ids:
                    self.trigger_print_for_test_result(result)
                    printed_count += 1
                else:
                    logger.debug(f"通道{channel_num}测试结果(ID:{test_id})已打印过")

            if printed_count > 0:
                logger.info(f"✅ 批量打印完成: {printed_count}个通道触发了打印")
            else:
                logger.debug("批量打印检查完成: 没有新的测试结果需要打印")

        except Exception as e:
            logger.error(f"批量打印检查失败: {e}")

    def _is_auto_print_enabled(self) -> bool:
        """检查是否启用自动打印"""
        try:
            return self.label_print_manager.is_auto_print_enabled()
        except Exception as e:
            logger.error(f"检查自动打印状态失败: {e}")
            return False

    def _is_printer_ready(self) -> bool:
        """检查打印机是否就绪"""
        try:
            return self.label_print_manager.is_printer_ready()
        except Exception as e:
            logger.error(f"检查打印机状态失败: {e}")
            return False

    def _prepare_print_data(self, test_result_data):
        """
        准备打印数据

        Args:
            test_result_data: 测试结果数据

        Returns:
            打印数据字典，如果准备失败则返回None
        """
        try:
            channel_num = test_result_data.get('channel_number')

            # 基本数据验证
            rs_value = test_result_data.get('rs_value', 0)
            rct_value = test_result_data.get('rct_value', 0)

            if rs_value == 0 and rct_value == 0:
                logger.warning(f"通道{channel_num}测试数据异常: Rs={rs_value}, Rct={rct_value}")
                return None

            # 构建打印数据
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
        """重置已打印记录（用于新的测试轮次）"""
        self._printed_test_ids.clear()
        logger.info("🔄 已打印记录已重置")

    def get_printed_count(self) -> int:
        """获取已打印的数量"""
        return len(self._printed_test_ids)
