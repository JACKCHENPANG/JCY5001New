#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
取样测试集成管理器
负责协调取样测试的完整流程，包括测试执行、结果确认、数据分析和参数建议

Author: Jack
Date: 2025-07-09
Version: V0.90.01
"""

import logging
from typing import Dict, Optional, Callable
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal

from backend.sampling_test_manager import SamplingTestManager
from ui.dialogs.sampling_test_result_dialog import SamplingTestResultDialog
from ui.dialogs.parameter_suggestion_dialog import ParameterSuggestionDialog

logger = logging.getLogger(__name__)


class SamplingTestIntegrationManager(QObject):
    """取样测试集成管理器"""
    
    # 信号定义
    sampling_completed = pyqtSignal(dict)  # 取样完成信号
    parameters_suggested = pyqtSignal(dict)  # 参数建议信号
    
    def __init__(self, config_manager, test_flow_controller, parent=None):
        """
        初始化取样测试集成管理器

        Args:
            config_manager: 配置管理器
            test_flow_controller: 测试流程控制器（可以为None）
            parent: 父对象
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.test_flow_controller = test_flow_controller

        # 安全获取取样测试管理器
        if test_flow_controller and hasattr(test_flow_controller, 'sampling_test_manager'):
            self.sampling_manager = test_flow_controller.sampling_test_manager
            logger.info("✅ 从测试流程控制器获取取样测试管理器")

            # 关键修复确保从现有管理器获取时也重置计数
            logger.debug(f" 重置现有取样测试管理器的计数")
            self.sampling_manager.reset_all_counts()

        else:
            # 创建独立的取样测试管理器
            self.sampling_manager = SamplingTestManager(config_manager)
            logger.info("✅ 创建独立的取样测试管理器")

            # 关键修复不要在初始化时自动启动，让用户明确启动
            # 这样可以确保每次启动都是干净的状态
            logger.debug(f" 取样测试管理器已创建，等待用户启动")

        # 回调函数
        self.test_completion_callback: Optional[Callable] = None

        logger.info("✅ 取样测试集成管理器初始化完成")

        # 修复：确保取样管理器使用最新的配置值
        self._update_sampling_manager_config()

    def _update_sampling_manager_config(self):
        """更新取样管理器的配置"""
        try:
            if hasattr(self.sampling_manager, 'update_target_count_from_config'):
                self.sampling_manager.update_target_count_from_config()
                logger.debug("✅ 取样管理器配置已更新")
        except Exception as e:
            logger.error(f"❌ 更新取样管理器配置失败: {e}")

    def start_sampling_test(self, sample_count: int) -> bool:
        """
        开始取样测试

        Args:
            sample_count: 取样数量

        Returns:
            是否启动成功
        """
        try:
            logger.info(f"🎯 开始启动取样测试，目标样本数: {sample_count}")

            # 确保状态完全重置 - 先停止之前的取样测试（如果有）
            if self.sampling_manager.is_sampling_mode:
                logger.debug(f" 检测到之前的取样测试状态，先进行清理")
                self.sampling_manager.stop_sampling_test()

            # 强制重置状态，确保干净的开始
            logger.debug(f" 强制重置取样测试管理器状态")
            self.sampling_manager.is_sampling_mode = False
            self.sampling_manager.reset_all_counts()

            # 启动取样测试管理器
            if not self.sampling_manager.start_sampling_test(sample_count):
                logger.error("❌ 启动取样测试管理器失败")
                return False

            # 验证状态是否正确设置
            if not self.sampling_manager.is_sampling_mode:
                logger.error("❌ 取样测试管理器状态设置失败")
                return False

            # 保存配置
            self.config_manager.set('test.sampling_test', True)
            self.config_manager.set('test.sampling_count', sample_count)

            # 禁用其他测试模式（取样测试与其他模式互斥）
            self.config_manager.set('test.continuous_mode', False)
            self.config_manager.set('test.auto_detect', False)

            # 保存配置到文件，确保状态持久化
            self.config_manager.save_config()

            logger.info(f"✅ 取样测试已启动，目标样本数: {sample_count}, 状态验证: {self.sampling_manager.is_sampling_mode}")
            return True

        except Exception as e:
            logger.error(f"❌ 启动取样测试失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    def stop_sampling_test(self):
        """停止取样测试"""
        try:
            logger.info("⏹️ 停止取样测试并重置所有计数")

            # 停止取样测试管理器（会清零计数）
            self.sampling_manager.stop_sampling_test()

            # 确保计数完全重置
            self.sampling_manager.reset_all_counts()

            # 恢复默认测试模式（只禁用取样测试，不影响其他模式）
            self.config_manager.set('test.sampling_test', False)
            # 注意：不强制修改电池侦测设置，保持用户的选择

            logger.info("✅ 取样测试已停止，所有计数已重置为0")

            # 通知UI更新显示
            self._notify_ui_reset_sampling_display()

        except Exception as e:
            logger.error(f"❌ 停止取样测试失败: {e}")
            # 确保即使出错也要重置计数
            try:
                self.sampling_manager.reset_all_counts()
                logger.debug(f" 异常情况下强制重置计数完成")
            except Exception as reset_error:
                logger.error(f"❌ 强制重置计数也失败: {reset_error}")
                # 最后的保险措施
                self.sampling_manager.current_sample_count = 0
                self.sampling_manager.valid_sample_count = 0
    
    def handle_test_completion(self, channel_data: Dict[int, Dict]):
        """
        处理测试完成事件

        Args:
            channel_data: 通道测试数据
        """
        try:
            # 增强状态检查和日志，帮助诊断问题
            sampling_mode_status = self.sampling_manager.is_sampling_mode
            config_sampling_test = self.config_manager.get('test.sampling_test', False)

            logger.debug(f" 取样测试完成处理 - sampling_manager.is_sampling_mode: {sampling_mode_status}, config.sampling_test: {config_sampling_test}")

            # 修复如果配置显示为取样模式但管理器状态不对，尝试恢复状态
            if config_sampling_test and not sampling_mode_status:
                logger.warning("⚠️ 检测到状态不一致：配置为取样模式但管理器状态为非取样模式，尝试恢复状态")

                # 尝试重新启动取样测试状态（不重置数据）
                target_count = self.config_manager.get('test.sampling_count', 30)
                current_count, valid_count, _ = self.sampling_manager.get_progress_info()

                logger.debug(f" 当前进度: {valid_count}/{target_count} (总测试: {current_count})")

                # 如果还没有达到目标数量，恢复取样模式状态
                if valid_count < target_count:
                    logger.debug(f" 恢复取样模式状态，继续处理测试完成")
                    self.sampling_manager.is_sampling_mode = True
                    sampling_mode_status = True
                else:
                    logger.debug(f" 已达到目标数量，但状态异常，强制处理完成")
                    sampling_mode_status = True  # 强制处理这次完成事件

            if not sampling_mode_status:
                logger.warning("⚠️ 非取样测试模式，跳过处理")
                return

            # 添加取样数据
            logger.debug(f" 准备添加取样数据，通道数: {len(channel_data)}")
            test_id = self.sampling_manager.add_sample_data(channel_data)
            if not test_id:
                logger.error("❌ 添加取样数据失败")
                return

            logger.info(f"✅ 取样数据已添加，test_id: {test_id}")

            # 获取统计数据和进度信息
            statistics_data = self.sampling_manager.get_current_statistics()
            progress_info = self.sampling_manager.get_progress_info()

            logger.info(f"✅ 取样数据已添加，当前进度: {progress_info}")
            logger.debug(f" 统计数据: {len(statistics_data) if statistics_data else 0}项")

            # Jack修复对于目标为1次的采样测试，自动确认结果
            current_count, valid_count, target_count = progress_info

            if target_count == 1 and current_count == 1:
                logger.info("🎯 检测到目标为1次的采样测试，自动确认结果")
                # 自动确认数据为有效
                self.sampling_manager.confirm_sample_data(test_id, True)

                # 重新获取进度信息
                progress_info = self.sampling_manager.get_progress_info()
                current_count, valid_count, target_count = progress_info
                logger.info(f"📊 自动确认后进度: {valid_count}/{target_count} (总测试: {current_count})")

                # 检查是否完成
                if self.sampling_manager.is_sampling_complete():
                    logger.info("🎉 采样测试已完成，直接显示参数建议对话框")
                    self._handle_sampling_completion()
                    return
            else:
                # 显示结果确认对话框（仅对多次采样测试）
                logger.debug(f" 准备显示结果确认对话框...")
                self._show_result_confirmation_dialog(test_id, channel_data, statistics_data, progress_info)

        except Exception as e:
            logger.error(f"❌ 处理取样测试完成失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def _show_result_confirmation_dialog(self, test_id: str, channel_data: Dict[int, Dict],
                                       statistics_data: Dict, progress_info: tuple):
        """显示结果确认对话框"""
        try:
            logger.debug(f" 准备显示结果确认对话框: test_id={test_id}, 通道数={len(channel_data)}, 进度={progress_info}")

            # 修复导入对话框类
            from ui.dialogs.sampling_test_result_dialog import SamplingTestResultDialog

            # 创建结果确认对话框
            dialog = SamplingTestResultDialog(
                test_id=test_id,
                channel_data=channel_data,
                statistics_data=statistics_data,
                progress_info=progress_info,
                parent=self.parent()
            )

            logger.info(f"✅ 结果确认对话框已创建")

            # 连接信号
            dialog.data_confirmed.connect(self._on_data_confirmed)
            logger.info(f"✅ 信号已连接")

            # 显示对话框
            logger.debug(f" 正在显示结果确认对话框...")
            result = dialog.exec_()
            logger.info(f"✅ 结果确认对话框已关闭，返回值: {result}")

        except Exception as e:
            logger.error(f"❌ 显示结果确认对话框失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def _on_data_confirmed(self, test_id: str, is_valid: bool):
        """数据确认处理"""
        try:
            # 确认数据有效性
            self.sampling_manager.confirm_sample_data(test_id, is_valid)
            
            # 检查是否完成取样
            if self.sampling_manager.is_sampling_complete():
                self._handle_sampling_completion()
            else:
                # 继续下一次测试
                current_count, valid_count, target_count = self.sampling_manager.get_progress_info()
                logger.info(f"📊 取样进度: {valid_count}/{target_count} (总测试: {current_count})")
                
                # 通知UI更新进度
                if self.test_completion_callback:
                    self.test_completion_callback()
            
        except Exception as e:
            logger.error(f"❌ 数据确认处理失败: {e}")
    
    def _handle_sampling_completion(self):
        """处理取样完成"""
        try:
            logger.info("🎉 取样测试完成！")

            # 获取建议参数
            suggestions = self.sampling_manager.get_suggested_parameters()
            statistics_data = self.sampling_manager.get_current_statistics()
            valid_count = self.sampling_manager.valid_sample_count

            # 先退出取样测试模式，切换到手动模式
            self._exit_sampling_mode()

            # 发送取样完成信号（先发送信号，确保主流程能继续）
            self.sampling_completed.emit({
                'valid_count': valid_count,
                'suggestions': suggestions,
                'statistics': statistics_data
            })

            from PyQt5.QtCore import QTimer
            logger.debug(f" 准备延时显示参数建议对话框，延时200ms...")
            QTimer.singleShot(200, lambda: self._show_parameter_suggestion_dialog_delayed(suggestions, statistics_data, valid_count))

        except Exception as e:
            logger.error(f"❌ 处理取样完成失败: {e}")

    def _exit_sampling_mode(self):
        """退出取样测试模式，切换到手动模式"""
        try:
            logger.info("🔄 退出取样测试模式，切换到手动模式")

            # 详细记录当前状态
            current_count, valid_count, target_count = self.sampling_manager.get_progress_info()
            logger.debug(f" 退出时的取样状态: {valid_count}/{target_count} (总测试: {current_count})")

            # 停止取样测试（这会清零所有计数）
            self.sampling_manager.stop_sampling_test()

            # 确保状态和计数完全清理
            logger.debug(f" 确保取样测试状态和计数完全清理")
            self.sampling_manager.is_sampling_mode = False
            self.sampling_manager.reset_all_counts()

            # 关键修复停止实际的测试执行器
            if hasattr(self, 'test_flow_controller') and self.test_flow_controller:
                logger.info("🛑 停止测试执行器...")
                self.test_flow_controller.stop_test()
                logger.info("✅ 测试执行器已停止")
            else:
                logger.warning("⚠️ 无法获取测试流程控制器，无法停止测试执行器")

            # 更新配置：退出取样模式（不影响其他测试模式设置）
            self.config_manager.set('test.sampling_test', False)
            # 注意：不强制修改连续测试和电池侦测设置，保持用户的选择

            # 保存配置
            self.config_manager.save_config()

            # 验证状态是否正确设置
            final_sampling_status = self.sampling_manager.is_sampling_mode
            final_config_status = self.config_manager.get('test.sampling_test', False)
            final_count_status = self.sampling_manager.get_progress_info()
            logger.info(f"✅ 已退出取样测试模式，状态验证: manager={final_sampling_status}, config={final_config_status}")
            logger.info(f"✅ 计数重置验证: {final_count_status} (应该全部为0)")

            # 通知UI更新显示
            self._notify_ui_reset_sampling_display()

        except Exception as e:
            logger.error(f"❌ 退出取样测试模式失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

            # 确保即使出错也要重置计数
            try:
                self.sampling_manager.is_sampling_mode = False
                self.sampling_manager.reset_all_counts()
                logger.debug(f" 异常情况下强制重置计数完成")
            except Exception as reset_error:
                logger.error(f"❌ 强制重置计数也失败: {reset_error}")
                # 最后的保险措施
                self.sampling_manager.current_sample_count = 0
                self.sampling_manager.valid_sample_count = 0

    def _show_parameter_suggestion_dialog_delayed(self, suggestions: Dict, statistics_data: Dict, sample_count: int):
        """延迟显示参数建议对话框（避免阻塞停止流程）"""
        try:
            logger.info("🔄 延迟显示参数建议对话框开始执行")
            logger.debug(f" 参数建议数据: {len(suggestions) if suggestions else 0}个参数")
            logger.debug(f" 统计数据: {len(statistics_data) if statistics_data else 0}个统计项")
            logger.debug(f" 样本数量: {sample_count}")

            self._show_parameter_suggestion_dialog(suggestions, statistics_data, sample_count)
            logger.info("✅ 延迟显示参数建议对话框执行完成")
        except Exception as e:
            logger.error(f"❌ 延迟显示参数建议对话框失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

    def _show_parameter_suggestion_dialog(self, suggestions: Dict, statistics_data: Dict, sample_count: int):
        """显示参数建议对话框"""
        try:
            logger.info("🎯 开始显示参数建议对话框")
            logger.debug(f" 检查参数建议数据: {suggestions is not None}, 长度: {len(suggestions) if suggestions else 0}")

            if not suggestions:
                logger.warning("⚠️ 参数建议数据为空，显示简单消息")
                # 修复直接显示消息，不再延时
                try:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self.parent(),
                        "取样完成",
                        f"取样测试已完成！\n\n有效样本数: {sample_count}\n\n"
                        f"由于数据不足，无法生成参数建议。\n\n"
                        f"系统已切换到手动模式。"
                    )
                    logger.info("✅ 简单消息已显示")
                except Exception as e:
                    logger.error(f"显示简单消息失败: {e}")
                return

            # 创建参数建议对话框
            try:
                logger.debug(f" 开始创建参数建议对话框...")

                # 修复增加父窗口检查
                parent_widget = self.parent()
                logger.debug(f" 父窗口状态: {parent_widget is not None}, 类型: {type(parent_widget).__name__ if parent_widget else 'None'}")

                dialog = ParameterSuggestionDialog(
                    suggestions=suggestions,
                    statistics_data=statistics_data,
                    sample_count=sample_count,
                    parent=parent_widget
                )
                logger.info("✅ 参数建议对话框创建成功")

                # 连接信号
                dialog.parameters_applied.connect(self._on_parameters_applied)
                logger.info("✅ 信号连接完成")

                # 修复使用exec_()确保对话框能被看到
                logger.debug(f" 准备显示参数建议对话框...")
                dialog.exec_()  # 使用exec_()确保对话框模态显示
                logger.info("✅ 参数建议对话框已显示并关闭")

            except Exception as dialog_error:
                logger.error(f"创建参数建议对话框失败: {dialog_error}")
                import traceback
                logger.error(f"对话框创建详细错误: {traceback.format_exc()}")

                # 如果对话框创建失败，显示简单的成功消息
                try:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self.parent(),
                        "取样完成",
                        f"取样测试已完成！\n\n有效样本数: {sample_count}\n\n"
                        f"系统已切换到手动模式。\n\n"
                        f"注意：参数建议对话框显示失败，请手动设置参数。\n\n"
                        f"错误信息: {str(dialog_error)}"
                    )
                    logger.info("✅ 备用消息已显示")
                except Exception as msg_error:
                    logger.error(f"连备用消息都无法显示: {msg_error}")

        except Exception as e:
            logger.error(f"❌ 显示参数建议对话框失败: {e}")
            # 确保即使出错也能给用户反馈
            try:
                QMessageBox.information(
                    self.parent(),
                    "取样完成",
                    f"取样测试已完成！\n\n有效样本数: {sample_count}\n\n"
                    f"系统已切换到手动模式。"
                )
            except:
                logger.error("连基本消息框都无法显示")
    
    def _on_parameters_applied(self, parameters: Dict):
        """参数应用处理"""
        try:
            # 应用参数到系统设置
            self._apply_parameters_to_system(parameters)
            
            # 发送参数建议信号
            self.parameters_suggested.emit(parameters)

            # 显示成功消息
            QMessageBox.information(
                self.parent(),
                "参数应用成功",
                "建议参数已成功应用到系统判断设置中！\n\n"
                "取样测试已完成，系统已切换到手动模式。"
            )
            
            logger.info("✅ 取样测试参数应用完成")
            
        except Exception as e:
            logger.error(f"❌ 参数应用处理失败: {e}")
            QMessageBox.critical(
                self.parent(),
                "参数应用失败",
                f"应用参数到系统设置时发生错误：\n{str(e)}"
            )
    
    def _apply_parameters_to_system(self, parameters: Dict):
        """应用参数到系统设置"""
        try:
            # 应用Rs参数
            if 'rs' in parameters:
                rs_params = parameters['rs']
                self.config_manager.set('grade_settings.rs_min', rs_params['min_range'])
                self.config_manager.set('grade_settings.rs_max', rs_params['max_range'])
                logger.info(f"✅ Rs参数已应用: {rs_params['min_range']:.3f} - {rs_params['max_range']:.3f}")

            # 应用Rct参数
            if 'rct' in parameters:
                rct_params = parameters['rct']
                self.config_manager.set('grade_settings.rct_min', rct_params['min_range'])
                self.config_manager.set('grade_settings.rct_max', rct_params['max_range'])
                logger.info(f"✅ Rct参数已应用: {rct_params['min_range']:.3f} - {rct_params['max_range']:.3f}")

            # 修复应用电压参数到标准电压和电压差（对应判断设置的显示方式）
            if 'voltage' in parameters:
                voltage_params = parameters['voltage']
                min_voltage = voltage_params['min_range']
                max_voltage = voltage_params['max_range']

                # 计算标准电压（平均值）和电压差（偏差值）
                standard_voltage = (min_voltage + max_voltage) / 2
                voltage_diff = (max_voltage - min_voltage) / 2

                # 同步到判断设置的配置项
                self.config_manager.set('grade_settings.standard_voltage', standard_voltage)
                self.config_manager.set('grade_settings.voltage_diff', voltage_diff)

                # 同时保持最小值和最大值（向后兼容）
                self.config_manager.set('grade_settings.voltage_min', min_voltage)
                self.config_manager.set('grade_settings.voltage_max', max_voltage)

                logger.info(f"✅ 电压参数已应用: 标准电压={standard_voltage:.3f}V, 电压差=±{voltage_diff:.3f}V (范围: {min_voltage:.3f} - {max_voltage:.3f}V)")

            # 应用Rsei参数
            if 'rsei' in parameters:
                rsei_params = parameters['rsei']
                self.config_manager.set('grade_settings.rsei_min', rsei_params['min_range'])
                self.config_manager.set('grade_settings.rsei_max', rsei_params['max_range'])
                logger.info(f"✅ Rsei参数已应用: {rsei_params['min_range']:.3f} - {rsei_params['max_range']:.3f}")

            # 新增自动同步配置到impedance节点，避免用户忘记在设置页面点击应用
            self._sync_grade_settings_to_impedance()

            # 保存配置
            self.config_manager.save_config()

            # 关键修复发送配置变更信号，让判断逻辑重新加载配置
            self._emit_config_change_signals(parameters)

            # 新增强制刷新判断设置界面
            self._refresh_grade_settings_ui()

            # 🔧 关键修复：强制应用判断设置，让新的判断范围立即生效
            self._force_apply_grade_settings()

            # 🔧 修复：强制重新加载测试结果管理器的失败原因管理器配置
            self._force_reload_test_result_manager_config()

            # 🔧 修复：强制重新加载所有相关组件的配置
            self._force_reload_all_related_configs()

        except Exception as e:
            logger.error(f"❌ 应用参数到系统设置失败: {e}")
            raise

    def _sync_grade_settings_to_impedance(self):
        """同步grade_settings配置到impedance节点，避免用户忘记在设置页面点击应用"""
        try:
            logger.info("🔄 开始同步档位配置到impedance节点")

            # 同步Rs配置
            rs_min = self.config_manager.get('grade_settings.rs_min')
            rs_max = self.config_manager.get('grade_settings.rs_max')
            rs_grade_count = self.config_manager.get('grade_settings.rs_grade_count', 3)

            if rs_min is not None and rs_max is not None:
                # 🔧 修复：根据rs_grade_count来计算档位分界值，而不是总是3档均分
                if rs_grade_count == 1:
                    # 1档模式：使用grade_settings中的rs1_min和rs1_max
                    rs_grade1_max = self.config_manager.get('grade_settings.rs1_max', rs_max)
                    rs_grade2_max = rs_max  # 不使用
                    rs_grade3_max = rs_max  # 不使用
                    logger.info(f"🔧 [1档模式] Rs配置: Rs1({rs_min:.3f}-{rs_grade1_max:.3f})")
                elif rs_grade_count == 2:
                    # 2档模式：使用grade_settings中的rs1_max和rs2_max
                    rs_grade1_max = self.config_manager.get('grade_settings.rs1_max', rs_min + (rs_max - rs_min) / 2)
                    rs_grade2_max = self.config_manager.get('grade_settings.rs2_max', rs_max)
                    rs_grade3_max = rs_max  # 不使用
                    logger.info(f"🔧 [2档模式] Rs配置: Rs1({rs_min:.3f}-{rs_grade1_max:.3f}), Rs2({rs_grade1_max:.3f}-{rs_grade2_max:.3f})")
                else:  # 3档
                    # 3档模式：使用grade_settings中的rs1_max、rs2_max、rs3_max
                    rs_grade1_max = self.config_manager.get('grade_settings.rs1_max')
                    rs_grade2_max = self.config_manager.get('grade_settings.rs2_max')
                    rs_grade3_max = self.config_manager.get('grade_settings.rs3_max', rs_max)

                    # 如果grade_settings中没有完整的min/max配置，则使用均分
                    if rs_grade1_max is None or rs_grade2_max is None:
                        rs_range = rs_max - rs_min
                        rs_grade1_max = rs_min + rs_range / 3
                        rs_grade2_max = rs_min + 2 * rs_range / 3
                        rs_grade3_max = rs_max
                        logger.info(f"🔧 [3档模式-均分] Rs配置: Rs1({rs_min:.3f}-{rs_grade1_max:.3f}), Rs2({rs_grade1_max:.3f}-{rs_grade2_max:.3f}), Rs3({rs_grade2_max:.3f}-{rs_grade3_max:.3f})")
                    else:
                        logger.info(f"🔧 [3档模式-自定义] Rs配置: Rs1({rs_min:.3f}-{rs_grade1_max:.3f}), Rs2({rs_grade1_max:.3f}-{rs_grade2_max:.3f}), Rs3({rs_grade2_max:.3f}-{rs_grade3_max:.3f})")

                # 同步到impedance节点
                self.config_manager.set('impedance.rs_min', rs_min)
                self.config_manager.set('impedance.rs_grade1_max', rs_grade1_max)
                self.config_manager.set('impedance.rs_grade2_max', rs_grade2_max)
                self.config_manager.set('impedance.rs_grade3_max', rs_grade3_max)
                self.config_manager.set('impedance.rs_grade_count', rs_grade_count)

                logger.info(f"✅ Rs配置已同步到impedance节点")

            # 同步Rct配置
            rct_min = self.config_manager.get('grade_settings.rct_min')
            rct_max = self.config_manager.get('grade_settings.rct_max')

            if rct_min is not None and rct_max is not None:
                # 计算Rct档位分界值（3档均分）
                rct_range = rct_max - rct_min
                rct_grade1_max = rct_min + rct_range / 3
                rct_grade2_max = rct_min + 2 * rct_range / 3
                rct_grade3_max = rct_max

                # 同步到impedance节点
                self.config_manager.set('impedance.rct_min', rct_min)
                self.config_manager.set('impedance.rct_grade1_max', rct_grade1_max)
                self.config_manager.set('impedance.rct_grade2_max', rct_grade2_max)
                self.config_manager.set('impedance.rct_grade3_max', rct_grade3_max)

                logger.info(f"✅ Rct配置已同步: Rct1({rct_min:.3f}-{rct_grade1_max:.3f}), Rct2({rct_grade1_max:.3f}-{rct_grade2_max:.3f}), Rct3({rct_grade2_max:.3f}-{rct_grade3_max:.3f})")

            # 同步根级别配置（向后兼容）
            if rs_min is not None and rs_max is not None:
                rs_range = rs_max - rs_min
                self.config_manager.set('rs1_max', rs_min + rs_range / 3)
                self.config_manager.set('rs2_max', rs_min + 2 * rs_range / 3)
                self.config_manager.set('rs3_max', rs_max)
                self.config_manager.set('rs_min', rs_min)
                self.config_manager.set('rs_max', rs_max)

            if rct_min is not None and rct_max is not None:
                rct_range = rct_max - rct_min
                self.config_manager.set('rct1_max', rct_min + rct_range / 3)
                self.config_manager.set('rct2_max', rct_min + 2 * rct_range / 3)
                self.config_manager.set('rct3_max', rct_max)
                self.config_manager.set('rct_min', rct_min)
                self.config_manager.set('rct_max', rct_max)

            logger.info("✅ 档位配置同步完成，用户无需手动在设置页面点击应用")

        except Exception as e:
            logger.error(f"❌ 同步档位配置到impedance节点失败: {e}")

    def _emit_config_change_signals(self, parameters: Dict):
        """发送配置变更信号，让判断逻辑重新加载配置"""
        try:
            logger.info("🔄 发送配置变更信号，通知系统重新加载判断配置")

            # 发送grade_settings配置变更信号
            if 'rs' in parameters:
                rs_params = parameters['rs']
                self.config_manager.config_changed.emit('grade_settings.rs_min', rs_params['min_range'])
                self.config_manager.config_changed.emit('grade_settings.rs_max', rs_params['max_range'])
                logger.debug(f"Rs配置变更信号已发送: {rs_params['min_range']:.3f} - {rs_params['max_range']:.3f}")

            if 'rct' in parameters:
                rct_params = parameters['rct']
                self.config_manager.config_changed.emit('grade_settings.rct_min', rct_params['min_range'])
                self.config_manager.config_changed.emit('grade_settings.rct_max', rct_params['max_range'])
                logger.debug(f"Rct配置变更信号已发送: {rct_params['min_range']:.3f} - {rct_params['max_range']:.3f}")

            if 'voltage' in parameters:
                voltage_params = parameters['voltage']
                min_voltage = voltage_params['min_range']
                max_voltage = voltage_params['max_range']
                standard_voltage = (min_voltage + max_voltage) / 2
                voltage_diff = (max_voltage - min_voltage) / 2

                self.config_manager.config_changed.emit('grade_settings.standard_voltage', standard_voltage)
                self.config_manager.config_changed.emit('grade_settings.voltage_diff', voltage_diff)
                logger.debug(f"电压配置变更信号已发送: 标准电压={standard_voltage:.3f}V, 电压差=±{voltage_diff:.3f}V")

            # 发送impedance配置变更信号
            self.config_manager.config_changed.emit('impedance.rs_min', self.config_manager.get('impedance.rs_min'))
            self.config_manager.config_changed.emit('impedance.rs_grade3_max', self.config_manager.get('impedance.rs_grade3_max'))
            self.config_manager.config_changed.emit('impedance.rct_min', self.config_manager.get('impedance.rct_min'))
            self.config_manager.config_changed.emit('impedance.rct_grade3_max', self.config_manager.get('impedance.rct_grade3_max'))

            # 发送通用的档位配置更新信号
            self.config_manager.config_changed.emit('grade_settings.updated', True)

            logger.info("✅ 配置变更信号发送完成，判断逻辑将重新加载配置")

        except Exception as e:
            logger.error(f"❌ 发送配置变更信号失败: {e}")

    def _refresh_grade_settings_ui(self):
        """刷新判断设置界面显示"""
        try:
            # 通过主窗口刷新判断设置界面
            main_window = self.parent()
            if main_window and hasattr(main_window, 'settings_sync_manager'):
                # 发送档位设置变更信号，触发界面更新
                main_window.settings_sync_manager._handle_grade_settings_changed('grade_settings.refresh', True)
                logger.info("✅ 判断设置界面刷新信号已发送")

            # 如果有打开的设置对话框，也需要刷新
            if main_window and hasattr(main_window, 'settings_dialog'):
                settings_dialog = main_window.settings_dialog
                if settings_dialog and hasattr(settings_dialog, 'grade_settings_widget'):
                    grade_widget = settings_dialog.grade_settings_widget
                    if grade_widget and hasattr(grade_widget, 'load_all_config'):
                        # 重新加载配置并更新显示
                        grade_widget.load_all_config()
                        logger.info("✅ 设置对话框中的判断设置界面已刷新")

        except Exception as e:
            logger.error(f"❌ 刷新判断设置界面失败: {e}")

    def _force_apply_grade_settings(self):
        """强制应用判断设置，让新的判断范围立即生效"""
        try:
            logger.info("🔄 强制应用判断设置，让新的判断范围立即生效...")

            # 获取主窗口
            main_window = self._get_main_window()
            if not main_window:
                logger.warning("⚠️ 无法获取主窗口，跳过强制应用判断设置")
                return

            # 方法1：如果设置对话框已打开，直接调用其apply_settings方法
            if hasattr(main_window, 'settings_dialog') and main_window.settings_dialog:
                settings_dialog = main_window.settings_dialog
                if hasattr(settings_dialog, 'grade_settings_widget') and settings_dialog.grade_settings_widget:
                    grade_widget = settings_dialog.grade_settings_widget
                    if hasattr(grade_widget, 'apply_settings'):
                        grade_widget.apply_settings()
                        logger.info("✅ 通过设置对话框强制应用判断设置成功")
                        return

            # 方法2：创建临时的判断设置组件并应用设置
            try:
                from ui.dialogs.grade_settings_widget import GradeSettingsWidget

                # 创建临时的判断设置组件
                temp_grade_widget = GradeSettingsWidget(self.config_manager, parent=None)

                # 重新加载配置（确保使用最新的参数）
                temp_grade_widget.load_all_config()

                # 应用设置
                temp_grade_widget.apply_settings()

                logger.info("✅ 通过临时组件强制应用判断设置成功")

            except Exception as temp_error:
                logger.error(f"❌ 通过临时组件应用判断设置失败: {temp_error}")

            # 方法3：直接通过配置管理器发送强制应用信号
            try:
                # 发送强制应用信号，通知所有相关组件重新加载并应用配置
                self.config_manager.config_changed.emit('grade_settings.force_apply', True)
                logger.info("✅ 强制应用信号已发送")

            except Exception as signal_error:
                logger.error(f"❌ 发送强制应用信号失败: {signal_error}")

            logger.info("✅ 强制应用判断设置完成")

        except Exception as e:
            logger.error(f"❌ 强制应用判断设置失败: {e}")

    def _force_reload_test_result_manager_config(self):
        """强制重新加载测试结果管理器的配置"""
        try:
            logger.info("🔄 强制重新加载测试结果管理器配置...")

            # 获取主窗口
            main_window = self._get_main_window()
            if not main_window:
                logger.warning("⚠️ 无法获取主窗口，跳过测试结果管理器配置重新加载")
                return

            # 重新加载测试结果管理器的失败原因管理器配置
            if hasattr(main_window, 'test_flow_manager') and main_window.test_flow_manager:
                test_flow_manager = main_window.test_flow_manager
                if hasattr(test_flow_manager, 'test_result_manager') and test_flow_manager.test_result_manager:
                    test_result_manager = test_flow_manager.test_result_manager

                    # 强制重新创建失败原因管理器，确保使用最新配置
                    if hasattr(test_result_manager, '_failure_reason_manager'):
                        test_result_manager._failure_reason_manager = None
                        logger.info("✅ 测试结果管理器的失败原因管理器已重置，将使用最新配置")

                    # 如果有reload_config方法，调用它
                    if hasattr(test_result_manager, 'reload_config'):
                        test_result_manager.reload_config()
                        logger.info("✅ 测试结果管理器配置已重新加载")

            logger.info("✅ 测试结果管理器配置重新加载完成")

        except Exception as e:
            logger.error(f"❌ 强制重新加载测试结果管理器配置失败: {e}")

    def _force_reload_all_related_configs(self):
        """强制重新加载所有相关组件的配置"""
        try:
            logger.info("🔄 强制重新加载所有相关组件配置...")

            # 获取主窗口
            main_window = self._get_main_window()
            if not main_window:
                logger.warning("⚠️ 无法获取主窗口，跳过相关组件配置重新加载")
                return

            # 重新加载配置变更管理器
            if hasattr(main_window, 'config_change_manager') and main_window.config_change_manager:
                config_change_manager = main_window.config_change_manager
                if hasattr(config_change_manager, 'force_reload_all_configs'):
                    config_change_manager.force_reload_all_configs()
                    logger.info("✅ 配置变更管理器已强制重新加载所有配置")

            # 重新加载测试配置管理器
            if hasattr(main_window, 'test_config_manager') and main_window.test_config_manager:
                test_config_manager = main_window.test_config_manager
                if hasattr(test_config_manager, 'reload_all_configs'):
                    test_config_manager.reload_all_configs()
                    logger.info("✅ 测试配置管理器已重新加载所有配置")

            logger.info("✅ 所有相关组件配置重新加载完成")

        except Exception as e:
            logger.error(f"❌ 强制重新加载所有相关组件配置失败: {e}")

    def _get_main_window(self):
        """获取主窗口实例"""
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if widget.__class__.__name__ == 'MainWindow':
                        return widget
            return None
        except Exception as e:
            logger.error(f"获取主窗口失败: {e}")
            return None

    def set_test_completion_callback(self, callback: Callable):
        """设置测试完成回调函数"""
        self.test_completion_callback = callback
    
    def get_sampling_progress(self) -> tuple:
        """获取取样进度"""
        return self.sampling_manager.get_progress_info()

    def is_sampling_mode(self) -> bool:
        """检查是否为取样模式"""
        return self.sampling_manager.is_sampling_mode

    def _notify_ui_reset_sampling_display(self):
        """通知UI重置取样测试显示"""
        try:
            # 尝试获取主窗口并更新UI显示
            if hasattr(self, 'config_manager'):
                # 通过配置管理器获取主窗口引用（如果有的话）
                from PyQt5.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    for widget in app.topLevelWidgets():
                        if hasattr(widget, 'ui_component_manager'):
                            ui_manager = widget.ui_component_manager
                            test_control = ui_manager.get_component('test_control')
                            if test_control and hasattr(test_control, 'reset_sampling_test_display'):
                                test_control.reset_sampling_test_display()
                                logger.info("✅ 已通知UI重置取样测试显示")
                                break

        except Exception as e:
            logger.error(f"❌ 通知UI重置取样测试显示失败: {e}")
            # 不抛出异常，避免影响主流程
