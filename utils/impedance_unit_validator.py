#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单位验证工具模块

提供阻抗数据单位验证和转换功能，确保产线和研发系统数据一致性。

Author: Augment Agent
Date: 2025-01-28
"""

import logging
from typing import Union, Tuple

logger = logging.getLogger(__name__)


class ImpedanceUnitValidator:
    """阻抗单位验证器"""
    
    # 锂电池阻抗合理范围定义
    VALID_RANGES = {
        'mΩ': {
            'rs_min': 0.001, 'rs_max': 50.0,     # Rs: 0.001-50 mΩ（放宽下限）
            'rct_min': 0.001, 'rct_max': 100.0,  # Rct: 0.001-100 mΩ（放宽下限，上限沿用100）
            'real_min': 0.001, 'real_max': 50.0, # 实部: 0.001-50 mΩ（放宽下限）
            'imag_min': -50.0, 'imag_max': 50.0  # 虚部: -50 to 50 mΩ
        },
        'μΩ': {
            'rs_min': 10.0, 'rs_max': 50000.0,      # Rs: 10-50000 μΩ
            'rct_min': 10.0, 'rct_max': 50000.0,    # Rct: 10-50000 μΩ
            'real_min': 10.0, 'real_max': 50000.0,  # 实部: 10-50000 μΩ
            'imag_min': -50000.0, 'imag_max': 50000.0  # 虚部: -50000 to 50000 μΩ
        }
    }
    
    @classmethod
    def validate_rs_value(cls, value: float, unit: str = 'mΩ') -> bool:
        """验证Rs值"""
        if unit not in cls.VALID_RANGES:
            logger.warning(f"不支持的单位: {unit}")
            return False
        
        range_def = cls.VALID_RANGES[unit]
        is_valid = range_def['rs_min'] <= value <= range_def['rs_max']
        
        if not is_valid:
            logger.warning(f"Rs值超出合理范围: {value} {unit} (期望: {range_def['rs_min']}-{range_def['rs_max']} {unit})")
        
        return is_valid
    
    @classmethod
    def validate_rct_value(cls, value: float, unit: str = 'mΩ') -> bool:
        """验证Rct值（特殊处理单频点测试的Rct=0）"""
        if unit not in cls.VALID_RANGES:
            logger.warning(f"不支持的单位: {unit}")
            return False

        # 特殊处理：单频点测试时Rct=0是正常的
        if value == 0.0:
            logger.info(f"检测到单频点测试: Rct=0.000 {unit} (正常)")
            return True

        range_def = cls.VALID_RANGES[unit]
        is_valid = range_def['rct_min'] <= value <= range_def['rct_max']

        if not is_valid:
            logger.warning(f"Rct值超出合理范围: {value} {unit} (期望: {range_def['rct_min']}-{range_def['rct_max']} {unit} 或单频点测试的0)")

        return is_valid
    
    @classmethod
    def validate_impedance_data(cls, real: float, imag: float, unit: str = 'mΩ') -> Tuple[bool, bool]:
        """验证阻抗数据"""
        if unit not in cls.VALID_RANGES:
            logger.warning(f"不支持的单位: {unit}")
            return False, False
        
        range_def = cls.VALID_RANGES[unit]
        
        real_valid = range_def['real_min'] <= real <= range_def['real_max']
        imag_valid = range_def['imag_min'] <= imag <= range_def['imag_max']
        
        if not real_valid:
            logger.warning(f"实部阻抗超出合理范围: {real} {unit}")
        if not imag_valid:
            logger.warning(f"虚部阻抗超出合理范围: {imag} {unit}")
        
        return real_valid, imag_valid
    
    @classmethod
    def convert_uohm_to_mohm(cls, value_uohm: float) -> float:
        """μΩ转换为mΩ"""
        return value_uohm / 1000.0

    @classmethod
    def convert_mohm_to_uohm(cls, value_mohm: float) -> float:
        """mΩ转换为μΩ"""
        return value_mohm * 1000.0

    @classmethod
    def convert_ohm_to_mohm(cls, value_ohm: float) -> float:
        """Ω转换为mΩ"""
        return value_ohm * 1000.0

    @classmethod
    def convert_mohm_to_ohm(cls, value_mohm: float) -> float:
        """mΩ转换为Ω"""
        return value_mohm / 1000.0

    @classmethod
    def convert_uohm_to_ohm(cls, value_uohm: float) -> float:
        """μΩ转换为Ω"""
        return value_uohm / 1000000.0

    @classmethod
    def convert_ohm_to_uohm(cls, value_ohm: float) -> float:
        """Ω转换为μΩ"""
        return value_ohm * 1000000.0

    @classmethod
    def standardize_to_mohm(cls, value: float, source_unit: str) -> float:
        """
        统一转换为mΩ标准单位

        Args:
            value: 原始数值
            source_unit: 源单位 ('μΩ', 'mΩ', 'Ω')

        Returns:
            转换为mΩ的数值
        """
        if source_unit == 'μΩ':
            return cls.convert_uohm_to_mohm(value)
        elif source_unit == 'Ω':
            return cls.convert_ohm_to_mohm(value)
        elif source_unit == 'mΩ':
            return value
        else:
            logger.warning(f"未知单位: {source_unit}，假设为mΩ")
            return value

    @classmethod
    def detect_unit_from_value(cls, rs_value: float, rct_value: float) -> str:
        """根据数值大小推测单位"""
        # 修复更准确的单位检测逻辑

        # 检查是否为μΩ范围（通常很大的数值）
        if rs_value > 1000 or rct_value > 1000:
            logger.info(f"检测到大数值，推测为μΩ单位: Rs={rs_value}, Rct={rct_value}")
            return 'μΩ'

        # 检查是否为Ω范围（通常很小的数值）
        if rs_value < 0.1 and rct_value < 0.1:
            logger.info(f"检测到小数值，推测为Ω单位: Rs={rs_value}, Rct={rct_value}")
            return 'Ω'

        # 默认为mΩ范围
        logger.info(f"推测为mΩ单位: Rs={rs_value}, Rct={rct_value}")
        return 'mΩ'

    @classmethod
    def fix_database_unit_conversion(cls, rs_db: float, rct_db: float, rsei_db: float = None,
                                   w_coefficient: float = None) -> dict:
        """
        🔧 修复数据库单位转换问题

        Args:
            rs_db: 数据库中的Rs值
            rct_db: 数据库中的Rct值
            rsei_db: 数据库中的Rsei值
            w_coefficient: 数据库中的W系数

        Returns:
            修正后的参数字典
        """
        # 检测当前数据的单位
        detected_unit = cls.detect_unit_from_value(rs_db, rct_db)

        # 统一转换为mΩ
        rs_corrected = cls.standardize_to_mohm(rs_db, detected_unit)
        rct_corrected = cls.standardize_to_mohm(rct_db, detected_unit)

        rsei_corrected = None
        if rsei_db is not None:
            rsei_corrected = cls.standardize_to_mohm(rsei_db, detected_unit)

        # W系数单位修正（如果异常大，可能需要缩放）
        w_corrected = w_coefficient
        if w_coefficient is not None and w_coefficient > 100:
            # 如果W系数过大，可能需要缩放
            w_corrected = w_coefficient / 100.0
            logger.warning(f"W系数过大，已缩放: {w_coefficient} -> {w_corrected}")

        result = {
            'rs_mohm': rs_corrected,
            'rct_mohm': rct_corrected,
            'rsei_mohm': rsei_corrected,
            'w_coefficient_corrected': w_corrected,
            'detected_unit': detected_unit,
            'conversion_applied': detected_unit != 'mΩ'
        }

        if result['conversion_applied']:
            logger.info(f"应用单位转换: {detected_unit} -> mΩ")
            logger.info(f"Rs: {rs_db} -> {rs_corrected:.3f} mΩ")
            logger.info(f"Rct: {rct_db} -> {rct_corrected:.3f} mΩ")

        return result

    @classmethod
    def validate_eis_parameters(cls, rs: float, rct: float, rsei: float = None,
                              w_coefficient: float = None) -> dict:
        """
        EIS参数合理性验证

        Args:
            rs: Rs值 (mΩ)
            rct: Rct值 (mΩ)
            rsei: Rsei值 (mΩ)
            w_coefficient: W系数 (mΩ·s^(-1/2))

        Returns:
            验证结果字典
        """
        validation_result = {
            'rs_valid': False,
            'rct_valid': False,
            'rsei_valid': True,  # 可选参数，默认有效
            'w_coefficient_valid': True,  # 可选参数，默认有效
            'overall_valid': False,
            'warnings': [],
            'errors': []
        }

        # Rs验证 (0.001-50 mΩ正常范围)
        if 0.001 <= rs <= 50.0:
            validation_result['rs_valid'] = True
        else:
            validation_result['errors'].append(f"Rs值异常: {rs:.3f} mΩ (正常范围: 0.001-50 mΩ)")

        # Rct验证 (0.001-100 mΩ正常范围，特殊处理单频点测试的Rct=0)
        if rct == 0.0:
            # 单频点测试的特殊情况：Rct=0是正常的
            validation_result['rct_valid'] = True
            validation_result['warnings'].append("检测到单频点测试: Rct=0.000mΩ (正常)")
        elif 0.001 <= rct <= 100.0:
            validation_result['rct_valid'] = True
        else:
            validation_result['errors'].append(f"Rct值异常: {rct:.3f} mΩ (正常范围: 0.001-100 mΩ 或单频点测试的0)")

        # Rsei验证 (0-20 mΩ正常范围)
        if rsei is not None:
            if 0 <= rsei <= 20.0:
                validation_result['rsei_valid'] = True
            else:
                validation_result['warnings'].append(f"Rsei值可能异常: {rsei:.3f} mΩ (正常范围: 0-20 mΩ)")
                validation_result['rsei_valid'] = False

        # W系数验证 (0.1-10 mΩ·s^(-1/2)正常范围)
        if w_coefficient is not None:
            if 0.1 <= w_coefficient <= 10.0:
                validation_result['w_coefficient_valid'] = True
            else:
                validation_result['warnings'].append(f"W系数可能异常: {w_coefficient:.3f} mΩ·s^(-1/2) (正常范围: 0.1-10)")
                validation_result['w_coefficient_valid'] = False

        # 整体验证
        validation_result['overall_valid'] = (
            validation_result['rs_valid'] and
            validation_result['rct_valid'] and
            validation_result['rsei_valid'] and
            validation_result['w_coefficient_valid']
        )

        return validation_result
