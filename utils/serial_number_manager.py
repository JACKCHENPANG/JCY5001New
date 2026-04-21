#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
序列号管理器

负责电池序列号的验证、生成和管理功能

Author: Jack
Date: 2025-01-31
"""

import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 导入日志优化器
try:
    from .log_optimizer import should_suppress_serial_log
except ImportError:
    # 如果导入失败，提供默认实现
    def should_suppress_serial_log(operation_type: str) -> bool:
        return False


@dataclass
class SerialValidationResult:
    """序列号验证结果"""
    is_valid: bool
    error_message: str = ""
    error_code: str = ""


@dataclass
class SerialGenerationConfig:
    """序列号生成配置"""
    prefix: str = "BAT"
    separator: str = "-"
    date_format: str = "YYYYMMDD"
    sequence_digits: int = 4


class SerialNumberManager:
    """序列号管理器"""
    
    def __init__(self, config_manager):
        """
        初始化序列号管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self._sequence_counter = 1
        self._used_serials = set()  # 已使用的序列号集合（仅内存，不持久化）
        
        # 检查是否启用轻量级模式
        lightweight_mode = self.config_manager.get('serial_numbers.lightweight_mode', True)
        
        if not lightweight_mode:
            # 完整模式：加载已使用的序列号
            self._load_used_serials()
        else:
            # 轻量级模式：不加载历史记录，从当前时间戳开始
            import time
            self._sequence_counter = int(time.time()) % 10000  # 使用时间戳避免重复
        
    def _load_used_serials(self):
        """加载已使用的序列号"""
        try:
            # 从配置或数据库中加载已使用的序列号
            used_serials = self.config_manager.get('serial_numbers.used_list', [])
            self._used_serials = set(used_serials)
            
            # 获取当前序列号计数器
            self._sequence_counter = self.config_manager.get('serial_numbers.current_sequence', 1)
            
            # 优化日志记录 - 运行时不输出序列号相关日志
            count = len(self._used_serials)
            
            # 只在严重问题时才输出警告（数量过多影响性能）
            if count > 5000:
                logger.warning(f"⚠️ 序列号数量过多({count}个)，严重影响启动性能，建议立即优化")
            
            # 其他情况下不输出任何序列号相关日志，避免日志污染
            
        except Exception as e:
            logger.error(f"加载已使用序列号失败: {e}")
            self._used_serials = set()
            self._sequence_counter = 1
    
    def _save_used_serials(self):
        """保存已使用的序列号"""
        try:
            # 保存已使用的序列号列表
            self.config_manager.set('serial_numbers.used_list', list(self._used_serials))
            
            # 保存当前序列号计数器
            self.config_manager.set('serial_numbers.current_sequence', self._sequence_counter)
            
            # 优化日志记录 - 运行时不输出序列号保存日志
            # 序列号保存是正常操作，不需要在日志中体现
            pass
            
        except Exception as e:
            logger.error(f"保存已使用序列号失败: {e}")
    
    def validate_serial_number(self, serial_number: str) -> SerialValidationResult:
        """
        验证序列号
        
        Args:
            serial_number: 要验证的序列号
            
        Returns:
            验证结果
        """
        try:
            # 检查是否为空
            if not serial_number or not serial_number.strip():
                return SerialValidationResult(
                    is_valid=False,
                    error_message="序列号不能为空",
                    error_code="EMPTY_SERIAL"
                )
            
            serial_number = serial_number.strip()
            
            # 获取验证配置
            scanner_enabled = self.config_manager.get('device.barcode_scanner.enabled', False)
            
            if scanner_enabled:
                return self._validate_scanned_serial(serial_number)
            else:
                # 禁用扫码枪时，所有序列号都有效（自动生成模式）
                return SerialValidationResult(is_valid=True)
                
        except Exception as e:
            logger.error(f"验证序列号失败: {e}")
            return SerialValidationResult(
                is_valid=False,
                error_message=f"验证过程出错: {e}",
                error_code="VALIDATION_ERROR"
            )
    
    def _validate_scanned_serial(self, serial_number: str) -> SerialValidationResult:
        """验证扫描的序列号"""
        try:
            # 长度验证
            min_length = self.config_manager.get('device.barcode_scanner.serial_length_min', 8)
            max_length = self.config_manager.get('device.barcode_scanner.serial_length_max', 20)
            
            if len(serial_number) < min_length:
                return SerialValidationResult(
                    is_valid=False,
                    error_message=f"序列号长度不足，最少需要 {min_length} 位",
                    error_code="LENGTH_TOO_SHORT"
                )
            
            if len(serial_number) > max_length:
                return SerialValidationResult(
                    is_valid=False,
                    error_message=f"序列号长度超限，最多允许 {max_length} 位",
                    error_code="LENGTH_TOO_LONG"
                )
            
            # 格式验证
            format_validation = self.config_manager.get('device.barcode_scanner.format_validation', True)
            if format_validation:
                allowed_chars = self.config_manager.get('device.barcode_scanner.allowed_chars', 
                                                       "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
                
                # 检查是否包含非法字符
                for char in serial_number.upper():
                    if char not in allowed_chars:
                        return SerialValidationResult(
                            is_valid=False,
                            error_message=f"序列号包含非法字符: {char}",
                            error_code="INVALID_CHARACTER"
                        )
            
            # 唯一性验证
            uniqueness_check = self.config_manager.get('device.barcode_scanner.uniqueness_check', True)
            if uniqueness_check:
                if serial_number.upper() in self._used_serials:
                    return SerialValidationResult(
                        is_valid=False,
                        error_message="序列号已存在，请使用其他序列号",
                        error_code="DUPLICATE_SERIAL"
                    )
            
            return SerialValidationResult(is_valid=True)
            
        except Exception as e:
            logger.error(f"验证扫描序列号失败: {e}")
            return SerialValidationResult(
                is_valid=False,
                error_message=f"验证过程出错: {e}",
                error_code="VALIDATION_ERROR"
            )
    
    def generate_serial_number(self) -> str:
        """
        生成新的序列号
        
        Returns:
            生成的序列号
        """
        try:
            # 获取生成配置
            prefix = self.config_manager.get('device.barcode_scanner.auto_generation.prefix', 'BAT')
            separator = self.config_manager.get('device.barcode_scanner.auto_generation.separator', '-')
            date_format = self.config_manager.get('device.barcode_scanner.auto_generation.date_format', 'YYYYMMDD')
            sequence_digits = self.config_manager.get('device.barcode_scanner.auto_generation.sequence_digits', 4)
            
            # 生成日期部分
            current_date = datetime.now()
            if date_format == "YYYYMMDD":
                date_part = current_date.strftime("%Y%m%d")
            elif date_format == "YYMMDD":
                date_part = current_date.strftime("%y%m%d")
            elif date_format == "MMDD":
                date_part = current_date.strftime("%m%d")
            else:
                date_part = current_date.strftime("%Y%m%d")  # 默认格式
            
            # 生成序列号
            while True:
                sequence_part = str(self._sequence_counter).zfill(sequence_digits)
                
                # 组装序列号
                if prefix and separator:
                    serial_number = f"{prefix}{separator}{date_part}{separator}{sequence_part}"
                elif prefix:
                    serial_number = f"{prefix}{date_part}{sequence_part}"
                else:
                    serial_number = f"{date_part}{separator}{sequence_part}" if separator else f"{date_part}{sequence_part}"
                
                # 检查是否已使用
                if serial_number.upper() not in self._used_serials:
                    break
                    
                # 递增计数器
                self._sequence_counter += 1
                
                # 防止无限循环
                if self._sequence_counter > 10**sequence_digits:
                    raise ValueError("序列号计数器溢出")
            
            # 优化日志记录 - 运行时不输出序列号生成日志
            # 序列号生成是正常操作，不需要在日志中体现
            return serial_number
            
        except Exception as e:
            logger.error(f"生成序列号失败: {e}")
            # 返回一个简单的备用序列号
            return f"BAT{datetime.now().strftime('%Y%m%d')}{self._sequence_counter:04d}"
    
    def register_serial_number(self, serial_number: str) -> bool:
        """
        注册序列号为已使用
        
        Args:
            serial_number: 要注册的序列号
            
        Returns:
            是否注册成功
        """
        try:
            if not serial_number or not serial_number.strip():
                return False
                
            serial_number = serial_number.strip().upper()
            
            # 检查是否启用轻量级模式
            lightweight_mode = self.config_manager.get('serial_numbers.lightweight_mode', True)
            
            if lightweight_mode:
                # 轻量级模式：只在内存中记录，不持久化
                self._used_serials.add(serial_number)
                
                # 如果是自动生成的序列号，更新计数器
                scanner_enabled = self.config_manager.get('device.barcode_scanner.enabled', False)
                if not scanner_enabled:
                    self._sequence_counter += 1
            else:
                # 完整模式：添加到已使用集合并持久化
                self._used_serials.add(serial_number)
                
                # 如果是自动生成的序列号，更新计数器
                scanner_enabled = self.config_manager.get('device.barcode_scanner.enabled', False)
                if not scanner_enabled:
                    self._sequence_counter += 1
                
                # 保存到配置
                self._save_used_serials()
            
            # 优化日志记录 - 运行时不输出序列号注册日志
            # 序列号注册是正常操作，不需要在日志中体现
            return True
            
        except Exception as e:
            logger.error(f"注册序列号失败: {e}")
            return False
    
    def is_scanner_enabled(self) -> bool:
        """
        检查扫码枪是否启用
        
        Returns:
            是否启用扫码枪
        """
        return self.config_manager.get('device.barcode_scanner.enabled', False)
    
    def get_validation_config(self) -> Dict[str, Any]:
        """
        获取验证配置
        
        Returns:
            验证配置字典
        """
        return {
            'scanner_enabled': self.config_manager.get('device.barcode_scanner.enabled', False),
            'min_length': self.config_manager.get('device.barcode_scanner.serial_length_min', 8),
            'max_length': self.config_manager.get('device.barcode_scanner.serial_length_max', 20),
            'format_validation': self.config_manager.get('device.barcode_scanner.format_validation', True),
            'allowed_chars': self.config_manager.get('device.barcode_scanner.allowed_chars', 
                                                   "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
            'uniqueness_check': self.config_manager.get('device.barcode_scanner.uniqueness_check', True)
        }
    
    def get_generation_config(self) -> SerialGenerationConfig:
        """
        获取生成配置
        
        Returns:
            生成配置对象
        """
        return SerialGenerationConfig(
            prefix=self.config_manager.get('device.barcode_scanner.auto_generation.prefix', 'BAT'),
            separator=self.config_manager.get('device.barcode_scanner.auto_generation.separator', '-'),
            date_format=self.config_manager.get('device.barcode_scanner.auto_generation.date_format', 'YYYYMMDD'),
            sequence_digits=self.config_manager.get('device.barcode_scanner.auto_generation.sequence_digits', 4)
        )
    
    def clear_used_serials(self) -> bool:
        """
        清空已使用的序列号记录
        
        Returns:
            是否清空成功
        """
        try:
            self._used_serials.clear()
            self._sequence_counter = 1
            self._save_used_serials()
            
            logger.info("已清空所有已使用的序列号记录")
            return True
            
        except Exception as e:
            logger.error(f"清空已使用序列号记录失败: {e}")
            return False
    
    def get_used_serials_count(self) -> int:
        """
        获取已使用序列号的数量
        
        Returns:
            已使用序列号数量
        """
        return len(self._used_serials)
    
    def get_next_sequence_number(self) -> int:
        """
        获取下一个序列号
        
        Returns:
            下一个序列号
        """
        return self._sequence_counter
