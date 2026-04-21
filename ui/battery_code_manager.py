#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电池码管理器

负责根据扫码枪配置状态，动态切换电池码获取方式（扫码 vs 自动生成）

Author: Jack
Date: 2025-01-31
"""

import logging
from typing import List, Optional
from PyQt5.QtWidgets import QWidget, QMessageBox
from PyQt5.QtCore import QTimer, pyqtSignal, QObject

logger = logging.getLogger(__name__)


class BatteryCodeManager(QObject):
    """电池码管理器"""
    
    # 信号定义
    codes_ready = pyqtSignal(list)  # 电池码准备完成信号 (battery_codes)
    progress_updated = pyqtSignal(int, int, str)  # 进度更新信号 (current, total, message)
    error_occurred = pyqtSignal(str)  # 错误发生信号 (error_message)
    
    def __init__(self, config_manager, parent=None, channels_container=None):
        """
        初始化电池码管理器

        Args:
            config_manager: 配置管理器
            parent: 父窗口
            channels_container: 通道容器组件，用于更新电池码显示
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.parent_widget = parent
        self.channels_container = channels_container
        self.serial_manager = None

        # 初始化序列号管理器
        self._init_serial_manager()

        # 扫码相关状态
        self.current_channel = 0
        self.total_channels = 8
        self.battery_codes = [""] * 8
        self.progress_dialog = None
        self.current_scan_dialog = None
        self.scan_completed_flag = False

        # 电池码缓存（用于在通道容器设置前缓存电池码）
        self._pending_battery_codes = {}

        logger.debug("电池码管理器初始化完成")
        
    def _init_serial_manager(self):
        """初始化序列号管理器"""
        try:
            from utils.serial_number_manager import SerialNumberManager
            self.serial_manager = SerialNumberManager(self.config_manager)
            # 序列号管理器初始化成功 - 运行时不输出日志
            pass
            
        except Exception as e:
            logger.error(f"初始化序列号管理器失败: {e}")
            self.serial_manager = None
    
    def get_battery_codes(self, enabled_channels: Optional[List[int]] = None) -> bool:
        """
        获取电池码（根据配置自动选择扫码或生成模式）

        Args:
            enabled_channels: 启用的通道列表，默认为1-8

        Returns:
            是否启动成功（异步操作）
        """
        try:
            if enabled_channels is None:
                enabled_channels = list(range(1, 9))

            self.total_channels = len(enabled_channels)
            self.battery_codes = [""] * 8  # 重置电池码列表

            # 🔧 检查是否为电池侦测模式且已有扫码结果
            auto_detect = self.config_manager.get('test.auto_detect', False)
            battery_detection_barcodes_ready = self.config_manager.get('temp.battery_detection_barcodes_ready', False)

            if auto_detect and battery_detection_barcodes_ready:
                logger.info("🔧 电池侦测模式：检测到已有扫码结果，直接使用")
                return self._use_battery_detection_barcodes(enabled_channels)

            # 检查扫码枪配置状态
            scanner_enabled = self.config_manager.get('device.barcode_scanner.enabled', False)

            logger.info(f"获取电池码: 扫码枪{'启用' if scanner_enabled else '禁用'}, 通道数: {self.total_channels}")

            if scanner_enabled:
                # 启用扫码枪模式：按通道顺序扫码
                return self._start_scanning_mode(enabled_channels)
            else:
                # 禁用扫码枪模式：自动生成
                return self._start_generation_mode(enabled_channels)

        except Exception as e:
            logger.error(f"获取电池码失败: {e}")
            self.error_occurred.emit(f"获取电池码失败: {e}")
            return False
    
    def _start_scanning_mode(self, enabled_channels: List[int]) -> bool:
        """启动扫码模式"""
        try:
            logger.info("启动扫码模式...")

            # 不再创建进度对话框，改用状态栏显示进度
            self.progress_dialog = None

            # 开始第一个通道的扫码
            self.current_channel = 0
            self.enabled_channels = enabled_channels
            self.total_channels = len(enabled_channels)

            # 直接启动扫码，不需要延迟
            self._scan_next_channel()

            return True

        except Exception as e:
            logger.error(f"启动扫码模式失败: {e}")
            self.error_occurred.emit(f"启动扫码模式失败: {e}")
            return False
    
    def _scan_next_channel(self):
        """扫描下一个通道"""
        try:
            if self.current_channel >= len(self.enabled_channels):
                # 所有通道扫码完成
                self._on_scanning_completed()
                return

            channel_num = self.enabled_channels[self.current_channel]

            # 发送进度更新信号（用于状态栏显示）
            self.progress_updated.emit(self.current_channel + 1, self.total_channels, f"扫描通道 {channel_num}")

            logger.info(f"开始扫描通道 {channel_num} ({self.current_channel + 1}/{self.total_channels})")

            # 导入并创建扫码对话框
            from ui.dialogs.scan_input_dialog import ScanInputDialog

            self.current_scan_dialog = ScanInputDialog(channel_num, self.parent_widget)
            self.scan_completed_flag = False  # 标记扫码是否已完成

            self.current_scan_dialog.scan_completed.connect(
                lambda battery_code: self._on_channel_scan_completed(channel_num, battery_code)
            )

            # 显示扫码对话框
            result = self.current_scan_dialog.exec_()
            logger.debug(f"通道{channel_num}扫码对话框关闭，结果: {result}")

            # 检查扫码结果
            if self.current_scan_dialog:
                # 检查是否是用户主动跳过（点击跳过按钮）
                if result != self.current_scan_dialog.Accepted and not self.scan_completed_flag:
                    # 用户跳过了当前通道，直接进入下一个通道
                    logger.info(f"用户跳过通道 {channel_num}")
                    # 保存空的电池码
                    self.battery_codes[channel_num - 1] = ""
                    # 继续下一个通道
                    self.current_channel += 1

                    # 检查是否还有更多通道需要扫码
                    if self.current_channel >= len(self.enabled_channels):
                        # 所有通道扫码完成
                        self._on_scanning_completed()
                    else:
                        # 延迟启动下一个通道，确保当前扫码对话框完全关闭
                        QTimer.singleShot(200, self._scan_next_channel)
                elif not self.scan_completed_flag:
                    # 扫码未完成但对话框关闭了，可能是重新扫码，重新开始当前通道
                    logger.info(f"重新开始扫描通道 {channel_num}")
                    # 清理引用
                    self.current_scan_dialog = None
                    # 延迟重新开始扫码，确保对话框完全关闭
                    QTimer.singleShot(200, self._scan_next_channel)
                    return

            # 清理引用
            self.current_scan_dialog = None

        except Exception as e:
            logger.error(f"扫描通道失败: {e}")
            self.error_occurred.emit(f"扫描通道失败: {e}")
            self._on_scanning_canceled()
    
    def _on_channel_scan_completed(self, channel_num: int, battery_code: str):
        """单个通道扫码完成处理"""
        try:
            logger.info(f"接收到通道{channel_num}扫码完成信号: '{battery_code}'")
            # 标记扫码已完成
            self.scan_completed_flag = True
            if not battery_code or not battery_code.strip():
                # 扫码结果为空，询问是否跳过
                reply = QMessageBox.question(
                    self.parent_widget or None, "扫码结果为空",
                    f"通道 {channel_num} 扫码结果为空，是否跳过此通道？",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )
                
                if reply == QMessageBox.Cancel:
                    self._on_scanning_canceled()
                    return
                elif reply == QMessageBox.No:
                    # 重新扫码当前通道 - 不增加current_channel，重新开始当前通道扫码
                    logger.info(f"用户选择重新扫码通道 {channel_num}")
                    # 延迟重新开始当前通道扫码
                    QTimer.singleShot(200, self._scan_next_channel)
                    return
                # Yes: 跳过此通道，battery_code保持为空
                
            else:
                # 验证扫码结果
                if self.serial_manager:
                    validation_result = self.serial_manager.validate_serial_number(battery_code)
                    
                    if not validation_result.is_valid:
                        # 验证失败，根据错误类型决定处理方式
                        if validation_result.error_code == "DUPLICATE_SERIAL":
                            # 重复序列号：只显示YES/NO选项，隐藏取消选项
                            reply = QMessageBox.question(
                                self.parent_widget or None, "序列号重复",
                                f"通道 {channel_num} 检测到重复序列号：\n{validation_result.error_message}\n\n是否重新扫码？",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.Yes  # 默认选择重新扫码
                            )

                            if reply == QMessageBox.Yes:
                                # 重新扫码当前通道 - 不增加current_channel，重新开始当前通道扫码
                                # 用户选择重新扫码通道（重复序列号）- 运行时不输出日志
                                pass
                                # 重置扫码完成标志，确保能重新扫码
                                self.scan_completed_flag = False
                                # 延迟重新开始当前通道扫码
                                QTimer.singleShot(200, self._scan_next_channel)
                                return
                            # No: 使用重复的序列号继续（不推荐但允许）
                            # 用户选择继续使用重复序列号 - 运行时不输出日志
                            pass
                        else:
                            # 其他验证错误：显示完整的YES/NO/Cancel选项
                            reply = QMessageBox.question(
                                self.parent_widget or None, "序列号验证失败",
                                f"通道 {channel_num} 序列号验证失败：\n{validation_result.error_message}\n\n是否重新扫码？",
                                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                            )

                            if reply == QMessageBox.Cancel:
                                self._on_scanning_canceled()
                                return
                            elif reply == QMessageBox.Yes:
                                # 重新扫码当前通道 - 不增加current_channel，重新开始当前通道扫码
                                logger.info(f"用户选择重新扫码通道 {channel_num}")
                                # 重置扫码完成标志，确保能重新扫码
                                self.scan_completed_flag = False
                                # 延迟重新开始当前通道扫码
                                QTimer.singleShot(200, self._scan_next_channel)
                                return
                            # No: 使用无效的序列号继续
                    else:
                        # 验证成功，注册序列号
                        self.serial_manager.register_serial_number(battery_code)
            
            # 保存电池码
            self.battery_codes[channel_num - 1] = battery_code.strip()

            # 立即更新通道显示（实时同步）
            self._update_channel_battery_code(channel_num, battery_code.strip())

            # 通道扫码完成 - 运行时不输出日志
            pass

            # 继续下一个通道
            self.current_channel += 1

            # 检查是否还有更多通道需要扫码
            if self.current_channel >= len(self.enabled_channels):
                # 所有通道扫码完成
                self._on_scanning_completed()
            else:
                # 延迟启动下一个通道，确保当前扫码对话框完全关闭
                QTimer.singleShot(200, self._scan_next_channel)
            
        except Exception as e:
            logger.error(f"处理通道扫码完成失败: {e}")
            self.error_occurred.emit(f"处理扫码结果失败: {e}")
            self._on_scanning_canceled()
    
    def _on_scanning_completed(self):
        """扫码完成处理"""
        try:
            # 统计扫码结果
            valid_codes = [code for code in self.battery_codes if code.strip()]

            logger.info(f"扫码完成: 共扫描 {len(valid_codes)} 个有效电池码")

            # 发送完成信号
            self.codes_ready.emit(self.battery_codes.copy())

        except Exception as e:
            logger.error(f"扫码完成处理失败: {e}")
            self.error_occurred.emit(f"扫码完成处理失败: {e}")

    def _on_scanning_canceled(self):
        """扫码取消处理"""
        try:
            logger.info("用户跳过了扫码操作")
            self.error_occurred.emit("用户跳过了扫码操作，请检查是否需要手动输入电池码")

        except Exception as e:
            logger.error(f"扫码取消处理失败: {e}")

    def _use_battery_detection_barcodes(self, enabled_channels: List[int]) -> bool:
        """使用电池侦测模式的扫码结果"""
        try:
            logger.info("🔧 电池侦测模式：使用引导界面的扫码结果")

            # 获取保存的扫码结果
            saved_barcodes = self.config_manager.get('temp.battery_detection_barcodes', [])

            if not saved_barcodes or len(saved_barcodes) != 8:
                logger.warning("⚠️ 电池侦测模式扫码结果无效，回退到正常扫码流程")
                # 清除无效的临时数据
                self.config_manager.set('temp.battery_detection_barcodes_ready', False)
                # 回退到正常扫码流程
                scanner_enabled = self.config_manager.get('device.barcode_scanner.enabled', False)
                if scanner_enabled:
                    return self._start_scanning_mode(enabled_channels)
                else:
                    return self._start_generation_mode(enabled_channels)

            # 使用保存的扫码结果
            self.battery_codes = saved_barcodes.copy()

            # 统计有效的扫码结果
            valid_codes = []
            for i, channel_num in enumerate(enabled_channels):
                if channel_num <= len(self.battery_codes) and self.battery_codes[channel_num - 1].strip():
                    valid_codes.append(self.battery_codes[channel_num - 1])
                    logger.info(f"  ✅ 通道{channel_num}: {self.battery_codes[channel_num - 1]}")

            logger.info(f"🎯 电池侦测模式扫码结果应用完成: 共{len(valid_codes)}个有效码")

            # 清除临时数据
            self.config_manager.set('temp.battery_detection_barcodes_ready', False)
            self.config_manager.set('temp.battery_detection_barcodes', [])

            # 发送完成信号
            self._emit_codes_ready_signal()

            return True

        except Exception as e:
            logger.error(f"❌ 使用电池侦测模式扫码结果失败: {e}")
            self.error_occurred.emit(f"使用电池侦测模式扫码结果失败: {e}")
            return False

    def _start_generation_mode(self, enabled_channels: List[int]) -> bool:
        """启动自动生成模式"""
        try:
            logger.info(f"🚀 启动自动生成模式，启用通道: {enabled_channels}")

            if not self.serial_manager:
                logger.error("❌ 序列号管理器未初始化")
                raise ValueError("序列号管理器未初始化")

            # 序列号管理器已就绪 - 运行时不输出日志
            pass

            # 显示状态提示
            self.progress_updated.emit(0, len(enabled_channels), "正在生成电池码...")

            # 为每个启用的通道生成电池码
            for i, channel_num in enumerate(enabled_channels):
                try:
                    logger.debug(f"🔄 正在为通道{channel_num}生成电池码 ({i+1}/{len(enabled_channels)})")

                    battery_code = self.serial_manager.generate_serial_number()
                    # 通道电池码生成成功 - 运行时不输出日志
                    pass

                    self.battery_codes[channel_num - 1] = battery_code
                    # 电池码已保存到数组 - 运行时不输出日志
                    pass

                    # 注册序列号
                    register_success = self.serial_manager.register_serial_number(battery_code)
                    # 序列号注册结果 - 运行时不输出日志，只在失败时记录错误
                    if not register_success:
                        logger.error(f"序列号注册失败: {battery_code}")

                    # 更新通道显示
                    self._update_channel_battery_code(channel_num, battery_code)

                    # 更新进度
                    self.progress_updated.emit(i + 1, len(enabled_channels), f"通道 {channel_num} 电池码已生成")

                    # 通道处理完成 - 运行时不输出日志
                    pass

                except Exception as channel_error:
                    logger.error(f"❌ 通道{channel_num}电池码生成失败: {channel_error}")
                    # 继续处理下一个通道，不中断整个流程
                    self.battery_codes[channel_num - 1] = ""

            # 统计生成结果
            valid_codes = [code for code in self.battery_codes if code.strip()]

            # 打印所有生成的电池码（调试级别，避免重复输出）
            for i, code in enumerate(self.battery_codes):
                if code.strip():
                    logger.debug(f"  ✅ 通道{i+1}: {code}")
                else:
                    logger.debug(f"  ❌ 通道{i+1}: (空)")

            logger.info(f"🎯 自动生成完成: 共生成 {len(valid_codes)} 个电池码")

            # 发送完成信号
            logger.info("🔄 准备发送电池码完成信号...")
            self._emit_codes_ready_signal()

            return True

        except Exception as e:
            logger.error(f"❌ 启动自动生成模式失败: {e}")
            import traceback
            logger.error(f"❌ 详细错误信息: {traceback.format_exc()}")
            self.error_occurred.emit(f"自动生成电池码失败: {e}")
            return False

    def _emit_codes_ready_signal(self):
        """发射电池码准备完成信号"""
        try:
            # 统计有效电池码
            valid_codes = [code for code in self.battery_codes if code.strip()]
            logger.info(f"🔄 准备发射电池码信号: 共{len(valid_codes)}个有效电池码")

            # 打印电池码详情（仅在调试模式下显示详情，避免重复）
            for i, code in enumerate(self.battery_codes):
                if code.strip():
                    logger.debug(f"  通道{i+1}: {code}")
                else:
                    logger.debug(f"  通道{i+1}: (空)")

            # 检查通道容器状态
            if self.channels_container:
                logger.info("✅ 通道容器已设置，电池码将直接更新到UI")
            else:
                # 通道容器未设置，电池码将被缓存 - 运行时不输出日志
                pass

            self.codes_ready.emit(self.battery_codes.copy())
            logger.info("✅ 电池码准备完成信号已发射")

        except Exception as e:
            logger.error(f"❌ 发射电池码准备完成信号失败: {e}")

    def _update_channel_battery_code(self, channel_num: int, battery_code: str):
        """更新通道电池码显示"""
        try:
            # 更新通道电池码 - 运行时不输出日志

            # 总是缓存电池码
            self._pending_battery_codes[channel_num] = battery_code
            # 电池码已缓存 - 运行时不输出日志

            if self.channels_container:
                if hasattr(self.channels_container, 'set_channel_battery_code'):
                    self.channels_container.set_channel_battery_code(channel_num, battery_code)
                    # 通道电池码已更新到UI - 运行时不输出日志
                    pass
                else:
                    logger.error(f"❌ 通道容器不支持set_channel_battery_code方法")
            else:
                # 通道容器未设置，电池码仅缓存 - 运行时不输出日志
                pass

        except Exception as e:
            logger.error(f"❌ 更新通道{channel_num}电池码显示失败: {e}")

    def set_channels_container(self, channels_container):
        """设置通道容器组件"""
        self.channels_container = channels_container
        logger.info(f"✅ 通道容器组件已设置: {type(channels_container).__name__}")

        # 验证通道容器功能
        if hasattr(channels_container, 'set_channel_battery_code'):
            logger.info("✅ 通道容器支持电池码设置功能")
        else:
            logger.error("❌ 通道容器不支持电池码设置功能")
            return

        # 应用缓存的电池码
        self._apply_pending_battery_codes()

    def _apply_pending_battery_codes(self):
        """应用缓存的电池码到通道容器"""
        try:
            if not self.channels_container:
                logger.warning("⚠️ 通道容器未设置，无法应用缓存的电池码")
                return

            if not self._pending_battery_codes:
                logger.debug("📦 没有缓存的电池码需要应用")
                return

            # 开始应用缓存的电池码 - 运行时不输出日志
            pass

            success_count = 0
            for channel_num, battery_code in self._pending_battery_codes.items():
                try:
                    if hasattr(self.channels_container, 'set_channel_battery_code'):
                        self.channels_container.set_channel_battery_code(channel_num, battery_code)
                        # 应用缓存电池码 - 运行时不输出日志
                        pass
                        success_count += 1
                    else:
                        logger.error(f"❌ 通道容器不支持set_channel_battery_code方法")
                        break
                except Exception as e:
                    logger.error(f"❌ 应用通道{channel_num}电池码失败: {e}")

            # 清空缓存
            self._pending_battery_codes.clear()
            logger.info(f"✅ 缓存电池码应用完成: 成功{success_count}个，缓存已清空")

        except Exception as e:
            logger.error(f"❌ 应用缓存电池码失败: {e}")

    def is_scanner_enabled(self) -> bool:
        """
        检查扫码枪是否启用
        
        Returns:
            是否启用扫码枪
        """
        return self.config_manager.get('device.barcode_scanner.enabled', False)
    
    def get_mode_description(self) -> str:
        """
        获取当前模式描述
        
        Returns:
            模式描述字符串
        """
        if self.is_scanner_enabled():
            return "扫码模式"
        else:
            return "自动生成模式"
    
    def cancel_operation(self):
        """取消当前操作"""
        try:
            # 如果有正在进行的扫码对话框，关闭它
            if hasattr(self, 'current_scan_dialog') and self.current_scan_dialog:
                self.current_scan_dialog.reject()
                self.current_scan_dialog = None

        except Exception as e:
            logger.error(f"取消操作失败: {e}")

    def refresh_ui_display(self):
        """手动刷新UI显示（强制更新所有电池码到界面）"""
        try:
            logger.info("🔄 手动刷新UI显示...")

            if not self.channels_container:
                logger.warning("⚠️ 通道容器未设置，无法刷新UI")
                return False

            if not hasattr(self.channels_container, 'set_channel_battery_code'):
                logger.error("❌ 通道容器不支持电池码设置功能")
                return False

            # 刷新所有通道的电池码
            success_count = 0
            for i, battery_code in enumerate(self.battery_codes):
                if battery_code.strip():  # 只更新非空电池码
                    channel_num = i + 1
                    try:
                        self.channels_container.set_channel_battery_code(channel_num, battery_code)
                        # 刷新通道电池码 - 运行时不输出日志
                        pass
                        success_count += 1
                    except Exception as e:
                        logger.error(f"❌ 刷新通道{channel_num}电池码失败: {e}")

            logger.info(f"✅ UI刷新完成: 成功更新{success_count}个通道")
            return success_count > 0

        except Exception as e:
            logger.error(f"❌ 手动刷新UI显示失败: {e}")
            return False
