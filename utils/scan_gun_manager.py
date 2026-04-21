#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USB扫码枪管理器
处理USB扫码枪的输入检测、验证和管理功能

Author: Jack
Date: 2025-01-28
"""

import re
import time
import logging
from typing import Optional, Callable, List
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class ScanGunManager(QObject):
    """USB扫码枪管理器"""

    # 信号定义
    scan_completed = pyqtSignal(str)  # 扫码完成信号 (battery_code)
    scan_failed = pyqtSignal(str)     # 扫码失败信号 (error_message)
    scan_timeout = pyqtSignal()       # 扫码超时信号

    def __init__(self, parent=None):
        """
        初始化扫码枪管理器

        Args:
            parent: 父对象
        """
        super().__init__(parent)

        # 扫码状态
        self.is_scanning = False
        self.scan_buffer = ""
        self.last_input_time = 0
        self.scan_start_time = 0

        # 扫码配置
        self.timeout_seconds = 30.0  # 扫码超时时间(秒)
        self.input_timeout = 3.0  # 输入间隔超时(秒) - 增加到3秒，给扫码枪更多时间
        self.min_scan_length = 3  # 最小扫码长度
        self.max_scan_length = 200 # 最大扫码长度 - 增加到200，支持长URL

        # 电池码格式验证规则
        self.battery_code_patterns = [
            r'^[A-Z0-9]{6,20}$',      # 6-20位字母数字组合
            r'^BAT[A-Z0-9]{3,15}$',   # BAT开头
            r'^[0-9]{8,16}$',         # 8-16位纯数字
            r'^[A-Z]{2}[0-9]{6,12}$', # 2位字母+6-12位数字
        ]

        # 定时器
        self.timeout_timer = QTimer()
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._on_scan_timeout)

        # 输入检测定时器
        self.input_timer = QTimer()
        self.input_timer.setSingleShot(True)
        self.input_timer.timeout.connect(self._on_input_complete)

        logger.debug("扫码枪管理器初始化完成")

    def start_scanning(self) -> bool:
        """
        开始扫码

        Returns:
            是否成功开始扫码
        """
        try:
            if self.is_scanning:
                logger.warning("扫码已在进行中")
                return False

            # 重置状态
            self.is_scanning = True
            self.scan_buffer = ""
            self.last_input_time = 0
            self.scan_start_time = time.time()

            # 启动超时定时器
            self.timeout_timer.start(int(self.timeout_seconds * 1000))

            logger.info("开始扫码，等待扫码枪输入...")
            return True

        except Exception as e:
            logger.error(f"开始扫码失败: {e}")
            return False

    def stop_scanning(self):
        """停止扫码"""
        try:
            if not self.is_scanning:
                return

            self.is_scanning = False
            # 不要清空扫码缓冲区！这会导致扫码内容消失
            # self.scan_buffer = ""

            # 停止定时器
            self.timeout_timer.stop()
            self.input_timer.stop()

            logger.info("扫码已停止")

        except Exception as e:
            logger.error(f"停止扫码失败: {e}")

    def process_input(self, text: str) -> bool:
        """
        处理输入字符

        Args:
            text: 输入的文本

        Returns:
            是否成功处理
        """
        try:
            if not self.is_scanning:
                return False

            current_time = time.time()

            # 不要重置缓冲区！这会导致扫码内容丢失
            # 让扫码内容累积，直到扫码完成
            # if self.last_input_time > 0:
            # input_interval = current_time - self.last_input_time
            # if input_interval > self.input_timeout:
            # # 输入间隔太长，可能是手动输入，重置缓冲区
            # self.scan_buffer = ""
            # logger.debug("输入间隔过长，重置扫码缓冲区")

            # 添加到缓冲区
            self.scan_buffer += text
            self.last_input_time = current_time

            # 检查是否包含回车（扫码完成标志）
            if '\r' in text or '\n' in text:
                self._process_scan_complete()
                return True

            # 检查长度限制
            if len(self.scan_buffer) > self.max_scan_length:
                self._handle_scan_error("扫码内容过长")
                return False

            # 启动输入完成检测定时器
            self.input_timer.start(int(self.input_timeout * 1000))

            logger.debug(f"扫码输入: '{text}', 缓冲区: '{self.scan_buffer}'")
            return True

        except Exception as e:
            logger.error(f"处理扫码输入失败: {e}")
            return False

    def _process_scan_complete(self):
        """处理扫码完成"""
        try:
            # 清理扫码内容
            battery_code = self.scan_buffer.strip().replace('\r', '').replace('\n', '')

            # 无条件发送扫码结果，即使是空的也发送
            # 让用户界面来决定是否接受这个内容
            logger.info(f"扫码完成: '{battery_code}' (长度: {len(battery_code)})")
            logger.debug(f"原始缓冲区: '{self.scan_buffer}' (长度: {len(self.scan_buffer)})")

            self.stop_scanning()
            self.scan_completed.emit(battery_code)

        except Exception as e:
            logger.error(f"🔫 处理扫码完成失败: {e}")
            # 即使出现异常，也尝试发送缓冲区内容
            battery_code = self.scan_buffer.strip() if self.scan_buffer else ""
            logger.info(f"🔫 异常情况下发送扫码内容: '{battery_code}'")
            self.stop_scanning()
            self.scan_completed.emit(battery_code)

    def _validate_battery_code(self, battery_code: str) -> bool:
        """
        验证电池码格式（完全放开验证）

        Args:
            battery_code: 电池码

        Returns:
            是否有效
        """
        try:
            # 只检查是否为空，其他一律通过
            if not battery_code or not battery_code.strip():
                logger.warning("电池码为空")
                return False

            # 完全放开验证：任何非空内容都认为有效
            logger.info(f"电池码验证通过: {battery_code}")
            return True

        except Exception as e:
            logger.error(f"验证电池码格式失败: {e}")
            # 即使出现异常，也返回True，确保不会因为验证失败而丢失内容
            return True

    def _handle_scan_error(self, error_message: str):
        """
        处理扫码错误

        Args:
            error_message: 错误信息
        """
        try:
            logger.warning(f"扫码错误: {error_message}")
            self.stop_scanning()
            self.scan_failed.emit(error_message)

        except Exception as e:
            logger.error(f"处理扫码错误失败: {e}")

    def _on_scan_timeout(self):
        """扫码超时处理"""
        try:
            logger.warning("扫码超时")
            self.stop_scanning()
            self.scan_timeout.emit()

        except Exception as e:
            logger.error(f"扫码超时处理失败: {e}")

    def _on_input_complete(self):
        """输入完成检测"""
        try:
            if not self.is_scanning:
                return

            # 无条件发送缓冲区内容，即使是空的
            battery_code = self.scan_buffer.strip() if self.scan_buffer else ""
            logger.info(f"扫码完成(无回车后缀): '{battery_code}' (长度: {len(battery_code)})")
            logger.info(f"原始缓冲区: '{self.scan_buffer}' (长度: {len(self.scan_buffer) if self.scan_buffer else 0})")

            self.stop_scanning()
            self.scan_completed.emit(battery_code)

        except Exception as e:
            logger.error(f"输入完成检测失败: {e}")
            # 即使出现异常，也尝试发送缓冲区内容
            battery_code = self.scan_buffer.strip() if self.scan_buffer else ""
            logger.info(f"异常情况下发送扫码内容(无回车): '{battery_code}'")
            self.stop_scanning()
            self.scan_completed.emit(battery_code)

    def set_scan_timeout(self, timeout: float):
        """
        设置扫码超时时间

        Args:
            timeout: 超时时间(秒)
        """
        self.timeout_seconds = max(5.0, min(120.0, timeout))
        logger.debug(f"扫码超时时间设置为: {self.timeout_seconds}秒")

    def set_battery_code_patterns(self, patterns: List[str]):
        """
        设置电池码格式验证规则

        Args:
            patterns: 正则表达式模式列表
        """
        try:
            # 验证正则表达式
            valid_patterns = []
            for pattern in patterns:
                try:
                    re.compile(pattern)
                    valid_patterns.append(pattern)
                except re.error as e:
                    logger.warning(f"无效的正则表达式模式: {pattern}, 错误: {e}")

            if valid_patterns:
                self.battery_code_patterns = valid_patterns
                logger.info(f"电池码格式规则已更新: {len(valid_patterns)}个模式")
            else:
                logger.warning("没有有效的电池码格式规则")

        except Exception as e:
            logger.error(f"设置电池码格式规则失败: {e}")

    def get_scan_status(self) -> dict:
        """
        获取扫码状态信息

        Returns:
            扫码状态字典
        """
        return {
            'is_scanning': self.is_scanning,
            'scan_buffer': self.scan_buffer,
            'scan_duration': time.time() - self.scan_start_time if self.is_scanning else 0,
            'timeout_remaining': self.timeout_seconds - (time.time() - self.scan_start_time) if self.is_scanning else 0
        }
