# -*- coding: utf-8 -*-
"""
测试流程管理器
负责测试流程的启动、停止、控制等功能

从MainWindow中提取的测试流程管理功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
Version: 第二阶段集成版本 - 已完成管理器类集成
"""

import logging
import time
from typing import List, Optional
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QMetaObject, Qt
from PyQt5.QtWidgets import QMessageBox

from ui.battery_code_manager import BatteryCodeManager

logger = logging.getLogger(__name__)


class TestFlowManager(QObject):
    """
    测试流程管理器
    
    职责：
    - 测试流程启动和停止
    - 测试状态管理
    - 测试结果处理
    - 测试进度监控
    """
    
    # 信号定义
    test_started = pyqtSignal()  # 测试开始
    test_stopped = pyqtSignal()  # 测试停止
    test_progress_updated = pyqtSignal(int, dict)  # 测试进度更新
    test_completed = pyqtSignal(dict)  # 测试完成
    test_failed = pyqtSignal(str)  # 测试失败
    channel_test_completed = pyqtSignal(int, dict)  # 通道测试完成
    show_continuous_report = pyqtSignal(int, int, dict)  # 显示连续测试报告信号
    
    def __init__(self, main_window, config_manager, comm_manager, device_connection_manager):
        """
        初始化测试流程管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
            comm_manager: 通信管理器
            device_connection_manager: 设备连接管理器
        """
        super().__init__()
        
        self.main_window = main_window
        self.config_manager = config_manager
        self.comm_manager = comm_manager
        self.device_connection_manager = device_connection_manager

        # 测试状态
        self.is_testing = False
        self.test_flow_controller = None

        # 电池码管理器
        self.battery_code_manager = BatteryCodeManager(config_manager, main_window)
        self._init_battery_code_manager_connections()

        # 立即尝试设置通道容器组件，如果失败则延迟重试
        self._setup_channels_container()

        # 设置延迟重试定时器（防止初始化时序问题）
        self._setup_channels_container_timer = QTimer()
        self._setup_channels_container_timer.setSingleShot(True)
        self._setup_channels_container_timer.timeout.connect(self._setup_channels_container)
        self._setup_channels_container_timer.start(2000)  # 2秒后重试设置

        # 连接连续测试报告信号
        self.show_continuous_report.connect(self._do_show_continuous_test_report)
        
        # 测试统计
        self.test_statistics = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_start_time': None,
            'test_end_time': None
        }
        
        logger.debug("测试流程管理器初始化完成")

    def _init_battery_code_manager_connections(self):
        """初始化电池码管理器信号连接"""
        try:
            self.battery_code_manager.codes_ready.connect(self._on_battery_codes_ready)
            self.battery_code_manager.error_occurred.connect(self._on_battery_code_error)
            logger.debug("电池码管理器信号连接完成")

        except Exception as e:
            logger.error(f"初始化电池码管理器连接失败: {e}")

    def _setup_channels_container(self):
        """设置通道容器组件"""
        try:
            # 检查电池码管理器是否已有通道容器
            if self.battery_code_manager.channels_container is not None:
                logger.debug("通道容器已设置，跳过重复设置")
                return

            # 从主界面获取通道容器组件
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                channels_container = ui_manager.get_component('channels_container')

                if channels_container:
                    self.battery_code_manager.set_channels_container(channels_container)
                    logger.info("✅ 通道容器组件已设置到电池码管理器")

                    # 验证设置是否成功
                    if hasattr(channels_container, 'set_channel_battery_code'):
                        logger.info("✅ 通道容器支持电池码设置功能")
                    else:
                        logger.warning("⚠️ 通道容器不支持电池码设置功能")

                    # 停止重试定时器
                    if hasattr(self, '_setup_channels_container_timer'):
                        self._setup_channels_container_timer.stop()

                else:
                    logger.warning("❌ 未找到通道容器组件，将稍后重试")
            else:
                logger.warning("❌ 主界面UI组件管理器未找到，将稍后重试")

        except Exception as e:
            logger.error(f"❌ 设置通道容器组件失败: {e}")

    def start_test(self) -> bool:
        """
        开始测试

        Returns:
            是否启动成功
        """
        try:
            if self.is_testing:
                logger.warning("测试已在进行中")
                return False

            logger.info("🚀 开始启动测试流程...")

            # 0. 检查软件授权状态
            if not self._check_authorization():
                return False

            # 1. 检查设备连接
            if not self._check_device_connection():
                return False

            # 2. 配置设备参数
            if not self._configure_device_parameters():
                return False

            # 2.5. 验证离群检测频点匹配（新增）
            if not self._validate_outlier_detection_frequencies():
                return False

            # 3. 读取电池电压
            if not self._read_battery_voltages():
                return False

            # 4. 获取电池码（扫码或自动生成）
            if not self._get_battery_codes():
                return False

            # 5. 更新测试状态
            self.is_testing = True
            self._reset_test_statistics()

            # 发送测试开始信号
            self.test_started.emit()

            logger.info("✅ 测试流程启动成功")
            return True

        except Exception as e:
            logger.error(f"启动测试流程失败: {e}")
            self._show_error_message("启动测试失败", str(e))
            return False
    
    def stop_test(self):
        """停止测试"""
        try:
            if not self.is_testing:
                logger.warning("当前没有进行测试")
                return
            
            logger.info("🛑 停止测试流程...")
            
            # 停止测试引擎
            if self.test_flow_controller:
                self.test_flow_controller.stop_test()
            
            # 更新测试状态
            self.is_testing = False
            
            # 发送测试停止信号
            self.test_stopped.emit()
            
            logger.info("✅ 测试流程已停止")
            
        except Exception as e:
            logger.error(f"停止测试流程失败: {e}")

    def _check_authorization(self) -> bool:
        """检查软件授权状态"""
        try:
            logger.info("🔐 检查软件授权状态...")

            # 获取授权管理器
            if hasattr(self.main_window, 'authorization_manager'):
                auth_manager = self.main_window.authorization_manager
                license_status = auth_manager.get_license_status()

                # 检查授权是否有效
                if not license_status.get('is_valid', False):
                    # 试用期已到期且未授权
                    if license_status.get('is_expired', True):
                        self._show_error_message(
                            "软件试用期已到期",
                            "软件试用期已到期，测试功能已被禁用。\n\n请输入解锁码以继续使用测试功能。\n\n如需购买授权，请联系软件供应商。"
                        )

                        # 触发解锁对话框
                        auth_manager.handle_unlock_requested()
                        return False
                    else:
                        self._show_error_message(
                            "软件授权无效",
                            "软件授权验证失败，无法使用测试功能。\n\n请联系软件供应商获取有效授权。"
                        )
                        return False

                # 检查测试功能是否启用
                enabled_features = license_status.get('enabled_features', [])
                if 'basic_test' not in enabled_features:
                    self._show_error_message(
                        "测试功能未授权",
                        "当前授权不包含测试功能。\n\n请联系软件供应商升级授权。"
                    )
                    return False

                logger.info("✅ 软件授权检查通过")
                return True
            else:
                logger.warning("授权管理器未找到，跳过授权检查")
                return True

        except Exception as e:
            logger.error(f"检查软件授权失败: {e}")
            self._show_error_message("授权检查失败", f"无法验证软件授权状态：{str(e)}")
            return False

    def _check_device_connection(self) -> bool:
        """检查设备连接"""
        try:
            if not self.device_connection_manager.get_connection_status():
                # 尝试连接设备
                if not self.device_connection_manager.connect_device():
                    reply = QMessageBox.question(
                        self.main_window,
                        '设备未连接',
                        '设备未连接！\n\n'
                        '请检查：\n'
                        '1. 设备是否正确连接\n'
                        '2. 设备是否已开机\n'
                        '3. 串口配置是否正确\n\n'
                        '是否打开设备设置页面进行连接？',
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        self.device_connection_manager.show_connection_dialog()
                    
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查设备连接失败: {e}")
            return False
    
    def _configure_device_parameters(self) -> bool:
        """配置设备参数"""
        try:
            logger.info("📋 配置设备参数...")
            
            # 获取配置参数
            gain = self.config_manager.get('test_params.gain', 'auto')
            average_times = self.config_manager.get('test_params.average_times', 1)
            battery_range = self.config_manager.get('test_params.battery_range', '10mΩ以下')
            
            # 转换参数
            gain_map = {'auto': 0, '1': 1, '4': 4, '16': 16}
            gain_value = gain_map.get(gain, 0)
            
            range_map = {
                '1mΩ以下': 0x00,   # 1R档位
                '10mΩ以下': 0x01,  # 5R档位
                '100mΩ以下': 0x02  # 10R档位
            }
            resistor_range = range_map.get(battery_range, 0x01)
            
            logger.info(f"设备参数: 增益={gain}({gain_value}), 平均次数={average_times}, 档位={battery_range}({resistor_range:02X})")
            
            # 设置参数
            if not self.comm_manager.set_resistance_range_broadcast(resistor_range):
                logger.error("设置电阻档位失败")
                return False
            
            if gain_value > 0:
                if not self.comm_manager.set_gain(gain_value):
                    logger.warning("设置增益失败，继续测试")
            
            if not self.comm_manager.set_average_times(average_times):
                logger.warning("设置平均次数失败，继续测试")
            
            logger.info("✅ 设备参数配置完成")
            return True
            
        except Exception as e:
            logger.error(f"配置设备参数失败: {e}")
            return False
    
    def _read_battery_voltages(self) -> bool:
        """读取电池电压"""
        try:
            logger.info("🔋 读取电池电压...")
            
            voltages = self.comm_manager.read_battery_voltages()
            
            if not voltages:
                logger.error("读取电池电压失败")
                return False
            
            logger.info(f"电池电压: {voltages}")
            
            # 检查电压范围 - Jack修正：电压不在2.0V-5.0V范围内认为是没有接电池
            valid_voltages = []
            for i, voltage in enumerate(voltages):
                if 2.0 <= voltage <= 5.0:  # 电压范围2.0V-5.0V，超出范围认为没有接电池
                    valid_voltages.append(i + 1)
                else:
                    logger.info(f"通道{i + 1}电压{voltage:.3f}V超出范围(2.0V-5.0V)，认为没有接电池，将跳过测试")
            
            if not valid_voltages:
                logger.warning("没有检测到有效的电池电压")
                reply = QMessageBox.question(
                    self.main_window,
                    '电池电压异常',
                    '没有检测到有效的电池电压！\n\n'
                    '请检查电池是否正确连接。\n\n'
                    '是否继续测试？',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply != QMessageBox.Yes:
                    return False
            
            logger.info(f"✅ 电池电压读取完成，有效通道: {valid_voltages}")
            return True
            
        except Exception as e:
            logger.error(f"读取电池电压失败: {e}")
            return False

    def _get_battery_codes(self) -> bool:
        """获取电池码（扫码或自动生成）"""
        try:

            # 获取启用的通道
            enabled_channels = self._get_enabled_channels()

            if not enabled_channels:
                logger.warning("没有启用的通道")
                return True  # 没有通道也算成功

            # 显示模式信息
            mode_desc = self.battery_code_manager.get_mode_description()
            logger.info(f"电池码获取模式: {mode_desc}")

            # 启动电池码获取（异步操作）
            success = self.battery_code_manager.get_battery_codes(enabled_channels)

            if not success:
                logger.error("启动电池码获取失败")
                return False

            # 异步操作，返回True表示启动成功
            # 实际结果通过信号回调处理
            return True

        except Exception as e:
            logger.error(f"获取电池码失败: {e}")
            return False

    def _get_enabled_channels(self) -> List[int]:
        """获取启用的通道列表"""
        try:
            enabled_channels = []

            # 从配置获取启用的通道
            config_enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))

            # 从UI组件获取通道状态（如果可用）
            if hasattr(self.main_window, 'ui_component_manager'):
                ui_manager = self.main_window.ui_component_manager
                channels_container = ui_manager.get_component('channels_container')

                if channels_container and hasattr(channels_container, 'get_enabled_channels'):
                    # 如果通道容器支持获取启用通道
                    ui_enabled_channels = channels_container.get_enabled_channels()
                    if ui_enabled_channels:
                        enabled_channels = ui_enabled_channels
                        logger.debug(f"从UI获取启用通道: {enabled_channels}")
                    else:
                        enabled_channels = config_enabled_channels
                        logger.debug(f"UI未返回启用通道，使用配置: {enabled_channels}")
                else:
                    enabled_channels = config_enabled_channels
                    logger.debug(f"通道容器不支持获取启用通道，使用配置: {enabled_channels}")
            else:
                enabled_channels = config_enabled_channels
                logger.debug(f"UI组件管理器未找到，使用配置: {enabled_channels}")

            # 确保返回有效的通道列表
            if not enabled_channels:
                enabled_channels = list(range(1, 9))  # 默认全部通道
                logger.warning(f"未获取到启用通道，使用默认全部通道: {enabled_channels}")

            logger.info(f"启用的通道: {enabled_channels}")
            return enabled_channels

        except Exception as e:
            logger.error(f"获取启用通道失败: {e}")
            return list(range(1, 9))  # 出错时返回默认全部通道

    def _on_battery_codes_ready(self, battery_codes: List[str]):
        """电池码准备完成回调"""
        try:
            valid_count = len([c for c in battery_codes if c.strip()])
            logger.info(f"🎯 电池码获取完成: {valid_count}个有效码")

            # 打印电池码详情
            for i, code in enumerate(battery_codes):
                if code.strip():
                    logger.info(f"  通道{i+1}: {code}")

            # 强制刷新UI显示（确保电池码显示在界面上）
            if hasattr(self.battery_code_manager, 'refresh_ui_display'):
                refresh_success = self.battery_code_manager.refresh_ui_display()
                if refresh_success:
                    logger.info("✅ 电池码UI刷新成功")
                else:
                    logger.warning("⚠️ 电池码UI刷新失败，但将继续测试")

            # 继续启动测试引擎
            if not self._start_test_engine(battery_codes):
                self.test_failed.emit("启动测试引擎失败")
                return

        except Exception as e:
            logger.error(f"❌ 处理电池码完成失败: {e}")
            self.test_failed.emit(f"处理电池码失败: {e}")

    def _on_battery_code_error(self, error_message: str):
        """电池码获取错误回调"""
        try:
            logger.error(f"电池码获取错误: {error_message}")

            # 提供更友好的错误信息
            if "跳过了扫码操作" in error_message:
                friendly_message = "扫码操作被跳过，测试已停止。\n提示：如需继续测试，请重新开始并完成扫码操作。"
            elif "扫码操作已取消" in error_message:
                friendly_message = "扫码操作被取消，测试已停止。\n提示：如需继续测试，请重新开始并完成扫码操作。"
            else:
                friendly_message = f"电池码获取失败: {error_message}"

            self.test_failed.emit(friendly_message)

        except Exception as e:
            logger.error(f"处理电池码错误失败: {e}")

    def _start_test_engine(self, battery_codes: Optional[List[str]] = None) -> bool:
        """启动测试引擎"""
        try:

            # 导入测试流程控制器
            from backend.test_flow_controller import TestFlowController

            # 创建测试流程控制器
            self.test_flow_controller = TestFlowController(
                self.config_manager,
                self.comm_manager,
                progress_callback=self._on_test_progress,
                status_callback=self._on_test_status
            )

            # 修复准备详细的批次信息
            import time
            batch_info = {
                'batch_number': f"BATCH_{int(time.time())}",
                'operator': self.config_manager.get('user.current_user', 'Unknown'),
                'start_time': time.time(),
                'product_name': self.config_manager.get('product.name', '默认产品'),
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            }

            # 修复准备电池码列表，确保与启用通道匹配
            enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))
            if battery_codes is None:
                # 根据启用通道生成电池码
                battery_codes = [f"BAT_{ch:02d}_{int(time.time())}" for ch in enabled_channels]
            else:
                # 确保电池码数量与启用通道匹配
                if len(battery_codes) < len(enabled_channels):
                    # 补充缺失的电池码
                    for i in range(len(battery_codes), len(enabled_channels)):
                        battery_codes.append(f"BAT_{enabled_channels[i]:02d}_{int(time.time())}")

            # 修复验证关键配置
            test_config = self.test_flow_controller.test_config_manager.get_config()
            logger.info(f"  - 启用通道: {test_config.get('enabled_channels', [])}")
            logger.info(f"  - 测试频率: {test_config.get('frequencies', [])}")
            logger.info(f"  - 连续模式: {test_config.get('continuous_mode', False)}")

            if not test_config.get('enabled_channels'):
                logger.error("❌ 没有启用的通道，无法启动测试")
                return False

            if not test_config.get('frequencies'):
                logger.error("❌ 没有配置测试频率，无法启动测试")
                return False

            # 启动批次测试
            success = self.test_flow_controller.start_batch_test(batch_info, battery_codes)

            if success:
                logger.info("✅ 测试引擎启动成功")
                return True
            else:
                logger.error("❌ 测试引擎启动失败")
                return False

        except Exception as e:
            logger.error(f"❌ 启动测试引擎失败: {e}")
            import traceback
            logger.error(f"❌ 详细错误信息: {traceback.format_exc()}")
            return False
    
    def _on_test_progress(self, channel_num: int, progress_data: dict):
        """测试进度回调"""
        try:
            # 调试日志：跟踪进度更新
            logger.debug(f"测试流程管理器收到进度更新: 通道{channel_num}, 状态={progress_data.get('state')}, 进度={progress_data.get('progress')}%, 频率={progress_data.get('frequency')}Hz")

            # 修复只发送test_progress_updated信号，避免重复统计
            # 统计更新由UI组件管理器统一处理，打印等其他处理由主窗口处理
            self.test_progress_updated.emit(channel_num, progress_data)

            # 修复测试完成时不再额外发送channel_test_completed信号
            # 避免重复处理，所有处理都通过test_progress_updated信号统一进行
            if progress_data.get('state') == 'completed':
                # 不再调用 self._on_channel_test_completed，避免重复信号发送
                pass

        except Exception as e:
            logger.error(f"处理测试进度失败: {e}")
    
    def _on_test_status(self, status_data: dict):
        """测试状态回调（增强版：支持连续测试状态）"""
        try:
            logger.debug(f"测试状态更新: {status_data}")

            # 处理连续测试相关状态
            action = status_data.get('action', '')

            if action == 'continuous_test_started':
                self._handle_continuous_test_started(status_data)
            elif action == 'continuous_test_stopped':
                self._handle_continuous_test_stopped(status_data)
            elif action == 'continuous_test_count_updated':
                self._handle_continuous_test_count_updated(status_data)
            elif action == 'continuous_test_cycle_cleanup':
                self._handle_continuous_test_cycle_cleanup(status_data)
            elif action == 'continuous_test_paused':
                self._handle_continuous_test_paused(status_data)
            elif action == 'continuous_test_restarted':
                self._handle_continuous_test_restarted(status_data)
            elif action == 'battery_voltage_abnormal':
                self._handle_battery_voltage_abnormal(status_data)
            elif action == 'continuous_test_completed':
                self._handle_continuous_test_completed(status_data)
            elif action == 'test_completed_manual_mode':
                self._handle_test_completed_manual_mode(status_data)

        except Exception as e:
            logger.error(f"处理测试状态失败: {e}")

    def _handle_continuous_test_started(self, status_data: dict):
        """处理连续测试启动"""
        try:
            count = status_data.get('count', 0)
            max_count = status_data.get('max_count', 0)


            # 修复确保连续测试状态指示器正确显示
            # 启动时显示初始状态（0次），后续会通过计数更新事件更新
            self._update_continuous_test_ui(True, count, max_count)

            # 修复强制刷新UI显示
            from PyQt5.QtCore import QTimer

            def force_ui_refresh():
                try:
                    ui_manager = self.main_window.get_manager('ui_component')
                    if ui_manager:
                        test_control = ui_manager.get_component('test_control')
                        if test_control:
                            # 确保连续测试状态指示器可见
                            if hasattr(test_control, 'continuous_status_container'):
                                test_control.continuous_status_container.setVisible(True)
                                test_control.continuous_status_container.update()
                                logger.info(f"✅ 强制显示连续测试状态指示器")

                            # 设置初始计数显示
                            if hasattr(test_control, 'set_continuous_test_status'):
                                interval = self.config_manager.get('test.continuous_test_delay', 2.0)
                                test_control.set_continuous_test_status(True, count, max_count, interval)
                                logger.info(f"✅ 设置连续测试初始状态: {count}/{max_count}")

                except Exception as e:
                    logger.error(f"❌ 强制UI刷新失败: {e}")

            # 延迟100ms执行，确保在主线程中
            QTimer.singleShot(100, force_ui_refresh)

        except Exception as e:
            logger.error(f"处理连续测试启动失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _handle_continuous_test_stopped(self, status_data: dict):
        """处理连续测试停止"""
        try:
            count = status_data.get('count', 0)
            statistics = status_data.get('statistics', {})

            logger.info(f"连续测试已停止: 总共完成{count}次")

            # 修复连续测试停止后重置UI状态
            self._reset_continuous_test_ui_state()

            # 更新主界面连续测试状态显示
            self._update_continuous_test_ui(False, count, 0)

            # 修复如果连续测试有数据，也显示报告
            if count > 0 and statistics.get('test_results'):
                self._show_continuous_test_report(count, 0, statistics)
            else:
                pass

        except Exception as e:
            logger.error(f"处理连续测试停止失败: {e}")

    def _handle_continuous_test_count_updated(self, status_data: dict):
        """处理连续测试计数更新（修复版）"""
        try:
            count = status_data.get('count', 0)
            max_count = status_data.get('max_count', 0)
            status = status_data.get('status', 'testing')

            logger.debug(f" 收到连续测试计数更新事件: count={count}, max_count={max_count}, status={status}")

            # 修复确保在主线程中更新UI
            from PyQt5.QtCore import QTimer, QMetaObject, Qt

            def update_ui():
                try:
                    logger.debug(f" 开始执行UI更新: count={count}, max_count={max_count}")

                    # 1. 更新主界面连续测试状态显示
                    self._update_continuous_test_ui(True, count, max_count)

                    # 2. 直接调用测试控制组件的更新方法
                    ui_manager = self.main_window.get_manager('ui_component')
                    if ui_manager:
                        test_control = ui_manager.get_component('test_control')
                        if test_control and hasattr(test_control, 'update_continuous_test_count'):
                            logger.debug(f" 调用测试控制组件更新方法: count={count}, max_count={max_count}")
                            test_control.update_continuous_test_count(count, max_count)
                            logger.info(f"✅ 测试控制组件计数更新完成: {count}/{max_count}")
                        else:
                            logger.warning("❌ 测试控制组件或update_continuous_test_count方法不存在")
                    else:
                        logger.warning("❌ UI组件管理器不存在")

                    # 3. 强制刷新UI显示
                    if hasattr(self.main_window, 'update'):
                        self.main_window.update()
                        self.main_window.repaint()  # 强制重绘

                    logger.debug(f" UI更新完成: count={count}, max_count={max_count}")

                except Exception as e:
                    logger.error(f"❌ UI更新失败: {e}")
                    import traceback
                    logger.error(f"详细错误信息: {traceback.format_exc()}")

            # 修复使用QTimer确保在主线程中执行
            QTimer.singleShot(0, update_ui)

        except Exception as e:
            logger.error(f"处理连续测试计数更新失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _handle_continuous_test_cycle_cleanup(self, status_data: dict):
        """处理连续测试循环清理（增强版 - 修复UI残留问题）"""
        try:
            count = status_data.get('count', 0)
            max_count = status_data.get('max_count', 0)

            logger.info(f"🧹 连续测试第{count}轮：开始全面状态清理")

            # 修复执行全面的状态清理
            self._perform_continuous_test_cleanup()

            # 修复额外的UI强制刷新
            self._force_ui_refresh_for_continuous_test()

            # 更新UI显示当前轮次
            self._update_continuous_test_ui(True, count, max_count)

            logger.info(f"✅ 连续测试第{count}轮：状态清理完成")

        except Exception as e:
            logger.error(f"处理连续测试循环清理失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _force_ui_refresh_for_continuous_test(self):
        """强制刷新UI以确保连续测试状态清理生效"""
        try:

            # 获取通道容器
            channels_container = self.main_window.ui_component_manager.get_component('channels_container')
            if channels_container:
                # 强制刷新所有通道组件
                for channel_widget in channels_container.channels:
                    if hasattr(channel_widget, 'update'):
                        channel_widget.update()

                # 强制刷新通道容器
                if hasattr(channels_container, 'update'):
                    channels_container.update()

            # 强制刷新主窗口
            if hasattr(self.main_window, 'update'):
                self.main_window.update()

            logger.debug("✅ 连续测试UI强制刷新完成")

        except Exception as e:
            logger.error(f"❌ 连续测试UI强制刷新失败: {e}")

    def _perform_continuous_test_cleanup(self):
        """执行连续测试状态清理"""
        try:
            # 1. 清理通道显示状态
            self._cleanup_channel_displays()

            # 2. 重置进度管理器
            self._reset_progress_manager()

            # 3. 清理测试结果数据
            self._cleanup_test_results()

            logger.info("🧹 连续测试状态清理完成")

        except Exception as e:
            logger.error(f"执行连续测试状态清理失败: {e}")

    def _cleanup_channel_displays(self):
        """清理通道显示状态（增强版 - 修复连续测试UI残留问题）"""
        try:
            # 获取通道容器
            channels_container = self.main_window.ui_component_manager.get_component('channels_container')
            if not channels_container:
                logger.warning("通道容器未找到，跳过通道显示清理")
                return

            logger.info("🧹 开始清理所有通道的UI显示状态...")

            # 清理每个通道的显示状态
            for channel_widget in channels_container.channels:
                try:
                    channel_num = getattr(channel_widget, 'channel_number', '未知')
                    logger.debug(f"🧹 清理通道{channel_num}的UI状态...")

                    # 修复只对启用的通道进行清理
                    if hasattr(channel_widget, 'is_enabled') and channel_widget.is_enabled:
                        # 修复连续测试模式下强制执行完整的UI清理
                        logger.debug(f"🧹 通道{channel_num}开始连续测试UI清理...")

                        # 1. 首先使用通道组件的专用重置方法
                        if hasattr(channel_widget, 'reset_test_data'):
                            channel_widget.reset_test_data()
                            logger.debug(f"✅ 通道{channel_num}使用reset_test_data方法清理完成")

                        # 2. 无论是否有reset_test_data方法，都执行强制清理确保UI状态正确
                        self._force_cleanup_channel_ui(channel_widget, channel_num)

                        # 3. 确保启用通道的结果显示为"待测试"
                        if hasattr(channel_widget, 'result_label'):
                            channel_widget.result_label.setText("待测试")
                            channel_widget.result_label.setObjectName("resultWaiting")
                            channel_widget.result_label.setStyleSheet("")
                    else:
                        logger.debug(f"⏭️ 通道{channel_num}未启用，跳过清理")

                    # 修复强制刷新UI显示
                    if hasattr(channel_widget, 'update'):
                        channel_widget.update()

                except Exception as e:
                    logger.error(f"❌ 清理通道{getattr(channel_widget, 'channel_number', '未知')}失败: {e}")
                    continue

            logger.info("✅ 所有通道UI显示状态清理完成")

        except Exception as e:
            logger.error(f"清理通道显示状态失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _force_cleanup_channel_ui(self, channel_widget, channel_num):
        """强制清理单个通道的UI状态（连续测试专用 - 优化双进度系统）"""
        try:
            logger.debug(f"🧹 通道{channel_num}开始强制UI清理（双进度系统优化）...")

            # 优化第一步 - 重置后端进度管理器的状态（频点进度系统）
            self._reset_backend_progress_manager(channel_num)

            # 优化第二步 - 重置通道组件的进度状态（测试进度系统）
            self._reset_channel_progress_state(channel_widget, channel_num)

            # 优化第三步 - 重置UI显示状态
            self._reset_channel_ui_display(channel_widget, channel_num)

            # 优化第四步 - 重置测试状态变量
            self._reset_channel_test_variables(channel_widget, channel_num)

            # 优化第五步 - 强制刷新整个通道组件
            if hasattr(channel_widget, 'update'):
                channel_widget.update()

            logger.debug(f"✅ 通道{channel_num}强制UI清理完成（双进度系统已同步重置）")

        except Exception as e:
            logger.error(f"❌ 强制清理通道{channel_num}UI失败: {e}")

    def _reset_backend_progress_manager(self, channel_num):
        """重置后端进度管理器的状态（频点进度系统）"""
        try:
            # 尝试获取测试执行器中的进度管理器
            test_executor = getattr(self, 'test_executor', None)
            if test_executor and hasattr(test_executor, 'progress_manager'):
                progress_manager = test_executor.progress_manager

                # 重置通道进度缓存
                if hasattr(progress_manager, 'channel_progress'):
                    progress_manager.channel_progress[channel_num] = 0.0
                    logger.debug(f"🧹 通道{channel_num}后端进度缓存已重置为0%")

                # 重置频点进度映射
                if hasattr(progress_manager, 'frequency_mapping'):
                    if channel_num in progress_manager.frequency_mapping:
                        progress_manager.frequency_mapping[channel_num] = {
                            'total_frequencies': 0,
                            'completed_frequencies': 0,
                            'current_frequency_index': 0
                        }
                        logger.debug(f"🧹 通道{channel_num}频点进度映射已重置")

                # 重置频点进度缓存
                if hasattr(progress_manager, 'frequency_progress'):
                    # 清除该通道的频点进度记录
                    keys_to_remove = [key for key in progress_manager.frequency_progress.keys()
                                    if isinstance(key, tuple) and len(key) > 0 and key[0] == channel_num]
                    for key in keys_to_remove:
                        del progress_manager.frequency_progress[key]
                    logger.debug(f"🧹 通道{channel_num}频点进度缓存已清除")

                logger.debug(f"✅ 通道{channel_num}后端进度管理器状态已重置")
            else:
                logger.debug(f"⚠️ 通道{channel_num}未找到后端进度管理器，跳过重置")

        except Exception as e:
            logger.error(f"❌ 重置通道{channel_num}后端进度管理器失败: {e}")

    def _reset_channel_progress_state(self, channel_widget, channel_num):
        """重置通道组件的进度状态（测试进度系统）"""
        try:
            # 优化强制重置进度管理状态变量（解决进度回退问题）
            if hasattr(channel_widget, 'current_progress'):
                channel_widget.current_progress = 0
                logger.debug(f"🧹 通道{channel_num}current_progress已强制重置为0")
            if hasattr(channel_widget, 'max_progress_reached'):
                channel_widget.max_progress_reached = 0
                logger.debug(f"🧹 通道{channel_num}max_progress_reached已强制重置为0")
            if hasattr(channel_widget, 'test_progress'):
                channel_widget.test_progress = 0
                logger.debug(f"🧹 通道{channel_num}test_progress已强制重置为0")

            logger.debug(f"✅ 通道{channel_num}进度状态变量已重置")

        except Exception as e:
            logger.error(f"❌ 重置通道{channel_num}进度状态失败: {e}")

    def _reset_channel_ui_display(self, channel_widget, channel_num):
        """重置通道UI显示状态"""
        try:
            # 优化强制重置进度条为0%
            if hasattr(channel_widget, 'progress_bar'):
                channel_widget.progress_bar.setValue(0)
                channel_widget.progress_bar.update()
                logger.debug(f"🧹 通道{channel_num}进度条已强制重置为0%")

            # 🎯 使用统一显示管理器重置档位显示（按照第一次运行时的标准模式）
            if hasattr(channel_widget, 'grade_label') and hasattr(channel_widget, 'result_label'):
                from utils.unified_display_manager import reset_channel_display_unified

                success = reset_channel_display_unified(channel_widget.grade_label, channel_widget.result_label)
                if success:
                    logger.debug(f"✅ 通道{channel_num}使用统一显示管理器重置成功")
                else:
                    # 备用方案：按照第一次运行时的标准模式
                    channel_widget.grade_label.setText("--")
                    channel_widget.grade_label.setObjectName("gradeDisplay")
                    channel_widget.grade_label.setStyleSheet("")
                    channel_widget.grade_label.update()
                    logger.debug(f"🧹 通道{channel_num}档位显示已重置为'--'")

            # 优化强制重置测试结果为"待测试"
            if hasattr(channel_widget, 'result_label'):
                channel_widget.result_label.setText("待测试")
                channel_widget.result_label.setObjectName("resultWaiting")
                channel_widget.result_label.setStyleSheet("")
                channel_widget.result_label.update()
                logger.debug(f"🧹 通道{channel_num}测试结果已强制重置为'待测试'")

            # 优化强制重置测试数据显示
            if hasattr(channel_widget, 'voltage_label'):
                channel_widget.voltage_label.setText("0.000")
                channel_widget.voltage_label.update()
            if hasattr(channel_widget, 'rs_label'):
                channel_widget.rs_label.setText("0.000")
                channel_widget.rs_label.update()
            if hasattr(channel_widget, 'rct_label'):
                channel_widget.rct_label.setText("0.000")
                channel_widget.rct_label.update()
            logger.debug(f"🧹 通道{channel_num}测试数据显示已强制重置")

            # 优化强制重置测试时间
            if hasattr(channel_widget, 'test_time_label'):
                channel_widget.test_time_label.setText("00:00:00")
                channel_widget.test_time_label.update()
                logger.debug(f"🧹 通道{channel_num}测试时间已强制重置")

            # 优化清除频点信息（频点显示功能已移除）
            # 频点显示功能已移除，跳过清除频点信息
            logger.debug(f"🧹 通道{channel_num}频点显示功能已移除，跳过清除")

            # 优化重置SOC显示（如果存在）
            if hasattr(channel_widget, 'soc_label'):
                channel_widget.soc_label.setText("SOC: --")
                channel_widget.soc_label.update()
                logger.debug(f"🧹 通道{channel_num}SOC显示已重置")

            # 优化重置离群率显示（如果存在）
            if hasattr(channel_widget, 'outlier_rate_label'):
                channel_widget.outlier_rate_label.setText("等待")
                channel_widget.outlier_rate_label.update()
                logger.debug(f"🧹 通道{channel_num}离群率显示已重置")

            logger.debug(f"✅ 通道{channel_num}UI显示状态已重置")

        except Exception as e:
            logger.error(f"❌ 重置通道{channel_num}UI显示失败: {e}")

    def _reset_channel_test_variables(self, channel_widget, channel_num):
        """重置通道测试状态变量"""
        try:
            # 优化重置测试状态变量
            if hasattr(channel_widget, 'test_result'):
                channel_widget.test_result = None
            if hasattr(channel_widget, 'test_start_time'):
                channel_widget.test_start_time = None
            if hasattr(channel_widget, 'test_end_time'):
                channel_widget.test_end_time = None

            logger.debug(f"✅ 通道{channel_num}测试状态变量已重置")

        except Exception as e:
            logger.error(f"❌ 重置通道{channel_num}测试状态变量失败: {e}")

    def _manual_cleanup_channel(self, channel_widget, channel_num):
        """手动清理单个通道的UI状态（回退方案）"""
        try:
            # 修复重置进度条为0%
            if hasattr(channel_widget, 'progress_bar'):
                channel_widget.progress_bar.setValue(0)
                logger.debug(f"🧹 通道{channel_num}进度条已重置为0%")

            # 修复重置档位显示为"--"
            if hasattr(channel_widget, 'grade_label'):
                channel_widget.grade_label.setText("--")
                channel_widget.grade_label.setStyleSheet("")
                logger.debug(f"🧹 通道{channel_num}档位显示已重置为'--'")

            # 修复重置测试结果为"待测试"
            if hasattr(channel_widget, 'result_label'):
                channel_widget.result_label.setText("待测试")
                channel_widget.result_label.setObjectName("resultWaiting")
                channel_widget.result_label.setStyleSheet("")
                logger.debug(f"🧹 通道{channel_num}测试结果已重置为'待测试'")

            # 修复重置测试数据显示
            if hasattr(channel_widget, 'voltage_label'):
                channel_widget.voltage_label.setText("0.000")
            if hasattr(channel_widget, 'rs_label'):
                channel_widget.rs_label.setText("0.000")
            if hasattr(channel_widget, 'rct_label'):
                channel_widget.rct_label.setText("0.000")
            logger.debug(f"🧹 通道{channel_num}测试数据显示已重置")

            # 修复重置测试时间
            if hasattr(channel_widget, 'test_time_label'):
                channel_widget.test_time_label.setText("00:00:00")
                logger.debug(f"🧹 通道{channel_num}测试时间已重置")

            # 修复清除频点信息
            if hasattr(channel_widget, 'clear_frequency_info'):
                channel_widget.clear_frequency_info()
                logger.debug(f"🧹 通道{channel_num}频点信息已清除")

            # 修复重置SOC显示（如果存在）
            if hasattr(channel_widget, 'soc_label'):
                channel_widget.soc_label.setText("SOC: --")
                logger.debug(f"🧹 通道{channel_num}SOC显示已重置")

            # 修复重置离群率显示（如果存在）
            if hasattr(channel_widget, 'outlier_rate_label'):
                channel_widget.outlier_rate_label.setText("等待")
                logger.debug(f"🧹 通道{channel_num}离群率显示已重置")

            # 修复重置电池状态指示器（如果存在）
            if hasattr(channel_widget, 'battery_status_indicator'):
                # 重置为默认状态，具体颜色根据电池连接状态确定
                pass  # 这个会在电池检测时自动更新

            logger.debug(f"✅ 通道{channel_num}手动清理完成")

        except Exception as e:
            logger.error(f"❌ 手动清理通道{channel_num}失败: {e}")

    def _reset_progress_manager(self):
        """重置进度管理器"""
        try:
            # 重置测试进度管理器
            if hasattr(self, 'test_progress_manager') and self.test_progress_manager:
                self.test_progress_manager.reset_progress()
                logger.debug("测试进度管理器已重置")

        except Exception as e:
            logger.error(f"重置进度管理器失败: {e}")

    def _cleanup_test_results(self):
        """清理测试结果数据"""
        try:
            # 清理测试结果管理器中的数据
            if hasattr(self, 'test_result_manager') and self.test_result_manager:
                # 重置测试开始时间记录
                if hasattr(self.test_result_manager, 'test_start_times'):
                    self.test_result_manager.test_start_times.clear()

                # 清除临时测试数据
                if hasattr(self.test_result_manager, 'temp_test_data'):
                    self.test_result_manager.temp_test_data.clear()

                logger.debug("测试结果数据已清理")

        except Exception as e:
            logger.error(f"清理测试结果数据失败: {e}")

    def _reset_continuous_test_ui_state(self):
        """重置连续测试UI状态"""
        try:

            # 1. 重置测试控制组件的按钮状态
            test_control = self.main_window.ui_component_manager.get_component('test_control')
            if test_control:

                # 调用专门的连续测试重置方法
                if hasattr(test_control, 'reset_button_state_for_continuous_test'):
                    test_control.reset_button_state_for_continuous_test()
                else:
                    # 回退到手动重置
                    test_control.is_testing = False
                    test_control.start_stop_button.setText("开始测试")
                    test_control.start_stop_button.setObjectName("startButton")
                    test_control.start_stop_button.setStyleSheet("")  # 重新应用样式

                    # 启用其他按钮
                    test_control.clear_button.setEnabled(True)
                    test_control.settings_button.setEnabled(True)

                logger.info("✅ 测试控制组件按钮状态已重置")
            else:
                logger.warning("❌ 无法获取测试控制组件")

            # 2. 重置主窗口的测试状态
            if hasattr(self.main_window, 'is_testing'):
                self.main_window.is_testing = False
                logger.info("✅ 主窗口测试状态已重置")

            # 3. 重置连续测试模式配置（可选，根据需求决定）
            # self.config_manager.set('test.continuous_mode', False)

            # 4. 更新状态栏显示
            status_bar = self.main_window.ui_component_manager.get_component('status_bar')
            if status_bar and hasattr(status_bar, 'set_system_status'):
                status_bar.set_system_status("连续测试已完成", "success")
                logger.info("✅ 状态栏显示已更新")


        except Exception as e:
            logger.error(f"重置连续测试UI状态失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

    def _handle_continuous_test_paused(self, status_data: dict):
        """处理连续测试暂停"""
        try:
            channel = status_data.get('channel', 0)
            reason = status_data.get('reason', '未知原因')

            logger.warning(f"连续测试已暂停: 通道{channel}, 原因: {reason}")

            # 显示暂停提示
            self._show_continuous_test_paused_message(channel, reason)

        except Exception as e:
            logger.error(f"处理连续测试暂停失败: {e}")

    def _handle_continuous_test_restarted(self, status_data: dict):
        """处理连续测试重启"""
        try:
            channel = status_data.get('channel', 0)
            count = status_data.get('count', 0)

            logger.info(f"连续测试已重启: 通道{channel}, 第{count}次")

        except Exception as e:
            logger.error(f"处理连续测试重启失败: {e}")

    def _handle_battery_voltage_abnormal(self, status_data: dict):
        """处理电池电压异常"""
        try:
            channel = status_data.get('channel', 0)
            voltage = status_data.get('voltage', 0)
            message = status_data.get('message', '电池电压异常')

            logger.warning(f"通道{channel}电池电压异常: {voltage:.3f}V")

            # 显示电压异常提示
            self._show_voltage_abnormal_message(channel, voltage, message)

        except Exception as e:
            logger.error(f"处理电池电压异常失败: {e}")

    def _handle_continuous_test_completed(self, status_data: dict):
        """处理连续测试完成"""
        try:
            count = status_data.get('count', 0)
            max_count = status_data.get('max_count', 0)
            statistics = status_data.get('statistics', {})

            logger.info(f"连续测试已完成: 总共{count}次，达到最大限制{max_count}次")

            # 修复连续测试完成后重置UI状态
            self._reset_continuous_test_ui_state()

            # 更新主界面连续测试状态显示
            self._update_continuous_test_ui(False, count, max_count)

            # 显示详细的连续测试报告
            self._show_continuous_test_report(count, max_count, statistics)

        except Exception as e:
            logger.error(f"处理连续测试完成失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _update_continuous_test_ui(self, is_continuous: bool, count: int, max_count: int):
        """更新连续测试UI显示"""
        try:

            # 获取测试控制组件
            ui_manager = self.main_window.get_manager('ui_component')
            if not ui_manager:
                logger.error("❌ 无法获取UI组件管理器")
                return

            test_control = ui_manager.get_component('test_control')
            if not test_control:
                logger.error("❌ 无法获取测试控制组件")
                return

            if not hasattr(test_control, 'set_continuous_test_status'):
                logger.error("❌ 测试控制组件没有 set_continuous_test_status 方法")
                return

            # 获取间隔时间
            interval = self.config_manager.get('test.continuous_test_delay', 2.0)


            # 修复确保在主线程中执行UI更新
            from PyQt5.QtCore import QMetaObject, Qt

            def update_ui():
                try:
                    # 更新连续测试状态显示
                    test_control.set_continuous_test_status(is_continuous, count, max_count, interval)
                    logger.info(f"✅ 连续测试UI更新完成")
                except Exception as e:
                    logger.error(f"❌ UI更新执行失败: {e}")

            # 如果当前在主线程，直接执行；否则通过信号槽机制执行
            if self.main_window.thread() == self.main_window.thread().currentThread():
                update_ui()
            else:
                QMetaObject.invokeMethod(self.main_window, "update_ui", Qt.QueuedConnection)

        except Exception as e:
            logger.error(f"更新连续测试UI显示失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _show_continuous_test_paused_message(self, channel: int, reason: str):
        """显示连续测试暂停消息"""
        try:
            QMessageBox.warning(
                self.main_window,
                '连续测试暂停',
                f'通道{channel}连续测试已暂停\n\n'
                f'原因: {reason}\n\n'
                f'系统将继续监控电池状态，\n'
                f'电池连接正常后将自动恢复测试。'
            )
        except Exception as e:
            logger.error(f"显示连续测试暂停消息失败: {e}")

    def _show_voltage_abnormal_message(self, channel: int, voltage: float, message: str):
        """显示电压异常消息"""
        try:
            # 只在第一次异常时显示，避免重复弹窗
            if not hasattr(self, '_voltage_warning_shown'):
                self._voltage_warning_shown = set()

            if channel not in self._voltage_warning_shown:
                self._voltage_warning_shown.add(channel)

                QMessageBox.warning(
                    self.main_window,
                    '电池电压异常',
                    f'通道{channel}: {message}\n\n'
                    f'当前电压: {voltage:.3f}V\n'
                    f'正常范围: 2.0V - 5.0V\n\n'
                    f'请检查电池连接状态。'
                )
        except Exception as e:
            logger.error(f"显示电压异常消息失败: {e}")

    def _show_continuous_test_report(self, count: int, max_count: int, statistics: dict):
        """显示连续测试报告（使用信号机制）"""
        try:

            # 使用信号机制确保在主线程中执行
            self.show_continuous_report.emit(count, max_count, statistics)

        except Exception as e:
            logger.error(f"准备连续测试报告失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            # 最终回退方案
            try:
                QMessageBox.information(
                    self.main_window,
                    '连续测试完成',
                    f'连续测试已完成！\n\n'
                    f'总测试次数: {count} 次\n'
                    f'设定最大次数: {max_count} 次\n\n'
                    f'所有测试已按计划完成。'
                )
            except Exception as final_error:
                logger.error(f"最终回退方案也失败: {final_error}")

    def _do_show_continuous_test_report(self, count: int, max_count: int, statistics: dict):
        """实际显示连续测试报告（在主线程中执行）"""
        try:

            # 准备报告数据
            report_data = {
                'total_cycles': count,
                'max_count': max_count,
                'start_time': statistics.get('start_time', ''),
                'end_time': statistics.get('end_time', ''),
                'cycle_times': statistics.get('cycle_times', []),
                'test_results': statistics.get('test_results', [])
            }


            # 新增自动生成EIS分析报告
            if report_data['test_results']:
                try:
                    from backend.continuous_test_analyzer import ContinuousTestAnalyzer

                    analyzer = ContinuousTestAnalyzer()
                    analysis_result = analyzer.analyze_continuous_test_data(report_data['test_results'])

                    if analysis_result:
                        report_data['analysis_result'] = analysis_result
                        logger.info("✅ EIS分析报告自动生成完成")
                    else:
                        logger.warning("⚠️ EIS分析报告生成失败，但继续显示报告")

                except Exception as e:
                    logger.error(f"❌ 自动生成EIS分析报告失败: {e}")
                    # 继续显示报告，即使分析失败

            try:
                from ui.continuous_test_report_dialog import ContinuousTestReportDialog

                # 在主线程中创建并显示报告对话框
                report_dialog = ContinuousTestReportDialog(self.main_window, report_data)
                report_dialog.exec_()

                logger.info("连续测试报告对话框已显示")

            except Exception as e:
                logger.error(f"显示连续测试报告失败: {e}")
                import traceback
                logger.error(f"详细错误信息: {traceback.format_exc()}")
                # 如果报告对话框失败，回退到简单消息框
                try:
                    QMessageBox.information(
                        self.main_window,
                        '连续测试完成',
                        f'连续测试已完成！\n\n'
                        f'总测试次数: {count} 次\n'
                        f'设定最大次数: {max_count} 次\n\n'
                        f'所有测试已按计划完成。\n\n'
                        f'注意: 详细报告显示失败，请检查日志。'
                    )
                except Exception as fallback_error:
                    logger.error(f"回退消息框也失败: {fallback_error}")

        except Exception as e:
            logger.error(f"执行连续测试报告显示失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _handle_test_completed_manual_mode(self, status_data: dict):
        """处理手动模式测试完成"""
        try:
            channel = status_data.get('channel', 0)
            message = status_data.get('message', '测试完成，等待手动操作')

            logger.info(f"手动模式：通道{channel}测试完成，{message}")

            # 通知测试控制组件重置按钮状态
            self._reset_manual_mode_button_state()

        except Exception as e:
            logger.error(f"处理手动模式测试完成失败: {e}")

    def _reset_manual_mode_button_state(self):
        """重置手动模式按钮状态"""
        try:
            # 获取测试控制组件
            ui_manager = self.main_window.get_manager('ui_component')
            if ui_manager:
                test_control = ui_manager.get_component('test_control')
                if test_control and hasattr(test_control, 'on_test_completed'):
                    # 调用测试控制组件的测试完成处理方法
                    test_control.on_test_completed()
                    logger.info("已通知测试控制组件重置按钮状态（手动模式）")

        except Exception as e:
            logger.error(f"重置手动模式按钮状态失败: {e}")
    
    def _on_channel_test_completed(self, channel_num: int, result_data: dict):
        """通道测试完成处理"""
        try:
            # 修复移除重复的统计更新，统计数据由UI组件管理器统一处理
            # 这里只记录日志和发送信号，避免重复计算统计数据
            logger.info(f"通道{channel_num}测试完成: {'通过' if result_data.get('is_pass') else '失败'}")

            # 发送通道测试完成信号给MainWindow
            self.channel_test_completed.emit(channel_num, result_data)

        except Exception as e:
            logger.error(f"处理通道测试完成失败: {e}")
    
    def _reset_test_statistics(self):
        """重置测试统计"""
        self.test_statistics = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_start_time': time.time(),
            'test_end_time': None
        }
    
    def _show_error_message(self, title: str, message: str):
        """显示错误消息"""
        try:
            QMessageBox.critical(self.main_window, title, message)
        except Exception as e:
            logger.error(f"显示错误消息失败: {e}")
    
    def get_test_status(self) -> dict:
        """
        获取测试状态
        
        Returns:
            测试状态字典
        """
        status = {
            'is_testing': self.is_testing,
            'statistics': self.test_statistics.copy()
        }
        
        if self.test_flow_controller:
            status['flow_status'] = self.test_flow_controller.get_test_status()
        
        return status
    
    def get_test_statistics(self) -> dict:
        """
        获取测试统计
        
        Returns:
            测试统计字典
        """
        return self.test_statistics.copy()
    
    def cleanup(self):
        """清理资源"""
        try:
            # 添加调试输出

            # 检查是否为连续测试模式，如果是则不停止测试
            continuous_test = self.config_manager.get('test.continuous_test', False)
            auto_detect = self.config_manager.get('test.auto_detect', True)


            # 只有在非连续测试且非自动侦测模式下才停止测试
            should_stop = not continuous_test and not auto_detect

            if self.is_testing:
                if should_stop:
                    logger.info("✅ cleanup检测到手动模式，停止测试")
                    self.stop_test()
                else:
                    logger.info(f"ℹ️ cleanup检测到连续测试或自动侦测模式，不停止测试（连续测试: {continuous_test}, 自动侦测: {auto_detect}）")

            # 清理测试流程控制器（但不影响正在运行的测试）
            # self.test_flow_controller = None  # 注释掉，避免影响正在运行的测试

            logger.info("测试流程管理器资源已清理")

        except Exception as e:
            logger.error(f"清理测试流程管理器资源失败: {e}")

    def _validate_outlier_detection_frequencies(self) -> bool:
        """
        验证离群检测频点匹配

        Returns:
            是否验证通过
        """
        try:

            # 🚫 离群检测功能已删除，跳过频点验证
            return True

            # 获取当前测试频点
            test_frequencies = self.config_manager.get('frequency.list', [])
            if not test_frequencies:
                logger.warning("未配置测试频点")
                return True

            # 获取基准频点
            try:
                baseline_details = outlier_manager.get_baseline_details(config['active_baseline_id'])
                if not baseline_details:
                    logger.warning("基准数据为空")
                    return True

                # 提取基准频点（去重）
                baseline_frequencies = list(set([detail['frequency'] for detail in baseline_details]))
                baseline_frequencies.sort()

                # 对比频点
                test_freq_set = set([float(f) for f in test_frequencies])
                baseline_freq_set = set(baseline_frequencies)

                if test_freq_set != baseline_freq_set:
                    # 频点不匹配，显示错误提示
                    missing_in_test = baseline_freq_set - test_freq_set
                    missing_in_baseline = test_freq_set - baseline_freq_set

                    error_msg = "离群检测频点不匹配！\n\n"
                    error_msg += f"测试频点数量: {len(test_frequencies)}\n"
                    error_msg += f"基准频点数量: {len(baseline_frequencies)}\n\n"

                    if missing_in_test:
                        error_msg += f"基准中有但测试中缺少的频点:\n"
                        for freq in sorted(missing_in_test):
                            error_msg += f"  {freq}Hz\n"
                        error_msg += "\n"

                    if missing_in_baseline:
                        error_msg += f"测试中有但基准中缺少的频点:\n"
                        for freq in sorted(missing_in_baseline):
                            error_msg += f"  {freq}Hz\n"
                        error_msg += "\n"

                    error_msg += "请选择以下操作:\n"
                    error_msg += "• 更换匹配的基准文件\n"
                    error_msg += "• 关闭离群检测功能\n"
                    error_msg += "• 修改测试频点配置"

                    reply = QMessageBox.critical(
                        self.main_window,
                        '离群检测频点不匹配',
                        error_msg,
                        QMessageBox.Ok
                    )

                    logger.error("离群检测频点验证失败：频点不匹配")
                    return False

                logger.info(f"✅ 离群检测频点验证通过，共{len(test_frequencies)}个频点")
                return True

            except Exception as e:
                logger.error(f"获取基准数据失败: {e}")
                return False

        except Exception as e:
            logger.error(f"验证离群检测频点失败: {e}")
            return False
