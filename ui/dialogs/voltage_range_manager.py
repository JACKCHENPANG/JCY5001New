#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电压范围管理器
负责电池电压范围的管理和验证

Author: Jack
Date: 2025-06-04
"""

import logging
from typing import Dict, Any, Tuple
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class VoltageRangeManager(QObject):
    """
    电压范围管理器
    
    职责：
    - 管理电池电压范围配置
    - 处理电压验证逻辑
    - 管理电压相关的计算
    """
    
    # 信号定义
    voltage_config_changed = pyqtSignal()  # 电压配置变更信号
    
    def __init__(self, config_manager, parent=None):
        """
        初始化电压范围管理器
        
        Args:
            config_manager: 配置管理器
            parent: 父对象
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        # 电压配置（电压差模式）
        self.voltage_config = {
            'standard_voltage': 3.210,  # 标准电压
            'min_voltage': 2.000,       # 最小电压
            'max_voltage': 5.000,       # 最大电压
            'voltage_diff': 0.16,       # 电压差值
            'auto_calc_range': True,    # 自动计算范围
            'tolerance_percent': 5.0    # 容差百分比
        }
        
        logger.debug("电压范围管理器初始化完成")
    
    def calculate_voltage_range(self, standard_voltage: float, voltage_diff: float) -> Tuple[float, float]:
        """
        计算电压范围（电压差模式）

        Args:
            standard_voltage: 标准电压
            voltage_diff: 电压差值

        Returns:
            Tuple[float, float]: (最小电压, 最大电压)
        """
        try:
            if standard_voltage <= 0:
                logger.warning(f"标准电压设置错误: {standard_voltage}")
                return 2.0, 5.0

            if voltage_diff <= 0:
                logger.warning(f"电压差设置错误: {voltage_diff}")
                voltage_diff = 0.16

            # 修改使用电压差计算范围
            min_voltage = standard_voltage - voltage_diff
            max_voltage = standard_voltage + voltage_diff

            # 确保范围合理
            min_voltage = max(0.1, min_voltage)  # 最小不低于0.1V
            max_voltage = min(50.0, max_voltage)  # 最大不超过50V

            logger.debug(f"电压范围计算: {standard_voltage}V ±{voltage_diff}V = {min_voltage:.3f}V - {max_voltage:.3f}V")

            return min_voltage, max_voltage

        except Exception as e:
            logger.error(f"计算电压范围失败: {e}")
            return 2.0, 5.0
    
    def update_voltage_config(self, **kwargs):
        """更新电压配置（电压差模式）"""
        try:
            old_config = self.voltage_config.copy()

            # 修复检查auto_calc_range的变化状态
            old_auto_calc = old_config.get('auto_calc_range', True)
            new_auto_calc = kwargs.get('auto_calc_range', old_auto_calc)

            # 更新配置
            self.voltage_config.update(kwargs)

            # 修复只有在以下情况才重新计算电压范围：
            # 1. auto_calc_range为True且（标准电压或电压差发生变化）
            # 2. auto_calc_range从False变为True
            should_recalc = False
            if new_auto_calc:
                # 如果启用自动计算
                if (not old_auto_calc or  # 从禁用变为启用
                    'standard_voltage' in kwargs or  # 标准电压变化
                    'voltage_diff' in kwargs):  # 电压差变化
                    should_recalc = True

            if should_recalc:
                min_voltage, max_voltage = self.calculate_voltage_range(
                    self.voltage_config['standard_voltage'],
                    self.voltage_config['voltage_diff']
                )
                self.voltage_config['min_voltage'] = min_voltage
                self.voltage_config['max_voltage'] = max_voltage
                logger.debug(f"重新计算电压范围: {min_voltage:.3f}V - {max_voltage:.3f}V")

            # 发送变更信号
            if old_config != self.voltage_config:
                self.voltage_config_changed.emit()

            logger.debug(f"电压配置更新: {kwargs}")

        except Exception as e:
            logger.error(f"更新电压配置失败: {e}")
    
    def get_voltage_config(self) -> Dict[str, Any]:
        """获取电压配置"""
        return self.voltage_config.copy()
    
    def validate_voltage(self, voltage: float) -> bool:
        """
        验证电压是否在合理范围内
        
        Args:
            voltage: 待验证的电压值
            
        Returns:
            bool: True表示电压合格
        """
        try:
            min_voltage = self.voltage_config['min_voltage']
            max_voltage = self.voltage_config['max_voltage']
            
            return min_voltage <= voltage <= max_voltage
            
        except Exception as e:
            logger.error(f"验证电压失败: {e}")
            return False
    
    def get_voltage_status(self, voltage: float) -> str:
        """
        获取电压状态描述
        
        Args:
            voltage: 电压值
            
        Returns:
            str: 状态描述
        """
        try:
            if self.validate_voltage(voltage):
                return "正常"
            else:
                min_voltage = self.voltage_config['min_voltage']
                max_voltage = self.voltage_config['max_voltage']
                
                if voltage < min_voltage:
                    return f"过低 (< {min_voltage:.3f}V)"
                elif voltage > max_voltage:
                    return f"过高 (> {max_voltage:.3f}V)"
                else:
                    return "异常"
                    
        except Exception as e:
            logger.error(f"获取电压状态失败: {e}")
            return "错误"
    
    def get_voltage_range_text(self) -> str:
        """获取电压范围文本描述（电压差模式）"""
        try:
            min_voltage = self.voltage_config['min_voltage']
            max_voltage = self.voltage_config['max_voltage']
            standard_voltage = self.voltage_config['standard_voltage']

            # 修改计算电压差值而不是百分比
            voltage_diff = self.voltage_config.get('voltage_diff', 0.16)

            return (f"标准电压: {standard_voltage:.3f}V\n"
                   f"容差: ±{voltage_diff:.3f}V\n"
                   f"有效范围: {min_voltage:.3f}V - {max_voltage:.3f}V")

        except Exception as e:
            logger.error(f"获取电压范围文本失败: {e}")
            return "获取失败"
    
    def set_battery_type_preset(self, battery_type: str):
        """
        设置电池类型预设（电压差模式）

        Args:
            battery_type: 电池类型 ('lifepo4', 'ternary', 'custom')
        """
        try:
            if battery_type.lower() == 'lifepo4':
                # 磷酸铁锂电池预设
                self.update_voltage_config(
                    standard_voltage=3.210,
                    voltage_diff=0.16
                )
                logger.info("设置为磷酸铁锂电池预设")

            elif battery_type.lower() == 'ternary':
                # 三元锂电池预设
                self.update_voltage_config(
                    standard_voltage=3.700,
                    voltage_diff=0.18
                )
                logger.info("设置为三元锂电池预设")

            elif battery_type.lower() == 'custom':
                # 自定义设置，不改变当前配置
                logger.info("设置为自定义电池类型")

            else:
                logger.warning(f"未知的电池类型: {battery_type}")

        except Exception as e:
            logger.error(f"设置电池类型预设失败: {e}")
    
    def get_battery_type_suggestions(self) -> Dict[str, Dict[str, Any]]:
        """获取电池类型建议配置（电压差模式）"""
        return {
            'lifepo4': {
                'standard_voltage': 3.210,
                'voltage_diff': 0.16,
                'description': '磷酸铁锂电池'
            },
            'ternary': {
                'standard_voltage': 3.700,
                'voltage_diff': 0.18,
                'description': '三元锂电池'
            },
            'custom': {
                'standard_voltage': 3.500,
                'voltage_diff': 0.20,
                'description': '自定义配置'
            }
        }
    
    def calculate_voltage_deviation(self, voltage: float) -> float:
        """
        计算电压偏差百分比
        
        Args:
            voltage: 实际电压
            
        Returns:
            float: 偏差百分比
        """
        try:
            standard_voltage = self.voltage_config['standard_voltage']
            
            if standard_voltage <= 0:
                return 0.0
            
            deviation = abs(voltage - standard_voltage) / standard_voltage * 100.0
            return round(deviation, 2)
            
        except Exception as e:
            logger.error(f"计算电压偏差失败: {e}")
            return 0.0
    
    def save_config(self):
        """保存配置到配置管理器"""
        try:
            if self.config_manager:
                # 修复同时保存到grade_settings和voltage_前缀的配置键

                # 保存到grade_settings节点（用于取样测试参数应用）
                self.config_manager.set('grade_settings.standard_voltage', self.voltage_config.get('standard_voltage', 3.21))
                self.config_manager.set('grade_settings.min_voltage', self.voltage_config.get('min_voltage', 2.0))
                self.config_manager.set('grade_settings.max_voltage', self.voltage_config.get('max_voltage', 5.0))
                self.config_manager.set('grade_settings.auto_calc_range', self.voltage_config.get('auto_calc_range', True))
                self.config_manager.set('grade_settings.voltage_diff', self.voltage_config.get('voltage_diff', 0.16))

                # 保存到voltage_前缀的配置键（向后兼容）
                for key, value in self.voltage_config.items():
                    self.config_manager.set(f"voltage_{key}", value)

                # 新增同步到通道显示组件使用的配置键
                self._sync_to_test_params()

                logger.debug("电压配置保存完成（同时保存到grade_settings和voltage_前缀）")

        except Exception as e:
            logger.error(f"保存电压配置失败: {e}")

    def _sync_to_test_params(self):
        """同步电压配置到test_params节点"""
        try:
            if self.config_manager:
                min_voltage = self.voltage_config.get('min_voltage', 2.0)
                max_voltage = self.voltage_config.get('max_voltage', 5.0)

                self.config_manager.set('test_params.voltage_range.min', min_voltage)
                self.config_manager.set('test_params.voltage_range.max', max_voltage)

                logger.debug(f"电压配置同步到test_params: {min_voltage}V - {max_voltage}V")
        except Exception as e:
            logger.error(f"同步电压配置到test_params失败: {e}")
    
    def load_config(self):
        """从配置管理器加载配置"""
        try:
            if self.config_manager:
                # 修复优先从grade_settings读取取样测试应用的电压参数

                # 加载标准电压
                standard_voltage = self.config_manager.get('grade_settings.standard_voltage')
                if standard_voltage is not None:
                    self.voltage_config['standard_voltage'] = standard_voltage
                else:
                    # 备用：从voltage_前缀读取
                    value = self.config_manager.get('voltage_standard_voltage')
                    if value is not None:
                        self.voltage_config['standard_voltage'] = value

                # 修复优先从正确的配置键读取电压范围参数
                # 首先尝试从grade_settings.min_voltage和grade_settings.max_voltage读取（这是save_config保存的键）
                min_voltage = self.config_manager.get('grade_settings.min_voltage')
                max_voltage = self.config_manager.get('grade_settings.max_voltage')

                if min_voltage is not None and max_voltage is not None:
                    # 如果有用户设置的参数，使用这些参数
                    self.voltage_config['min_voltage'] = min_voltage
                    self.voltage_config['max_voltage'] = max_voltage
                    logger.info(f"✅ 电压范围管理器使用用户设置的电压参数: {min_voltage:.3f}V - {max_voltage:.3f}V")
                else:
                    # 否则尝试从voltage_前缀配置读取
                    min_voltage = self.config_manager.get('voltage_min_voltage')
                    max_voltage = self.config_manager.get('voltage_max_voltage')

                    if min_voltage is not None:
                        self.voltage_config['min_voltage'] = min_voltage
                    if max_voltage is not None:
                        self.voltage_config['max_voltage'] = max_voltage

                    # 最后尝试从grade_settings.voltage_min和grade_settings.voltage_max读取（系统默认值）
                    if min_voltage is None:
                        voltage_min = self.config_manager.get('grade_settings.voltage_min')
                        if voltage_min is not None:
                            self.voltage_config['min_voltage'] = voltage_min

                    if max_voltage is None:
                        voltage_max = self.config_manager.get('grade_settings.voltage_max')
                        if voltage_max is not None:
                            self.voltage_config['max_voltage'] = voltage_max

                # 加载其他配置项
                auto_calc_range = self.config_manager.get('grade_settings.auto_calc_range')
                if auto_calc_range is None:
                    auto_calc_range = self.config_manager.get('voltage_auto_calc_range')
                if auto_calc_range is not None:
                    self.voltage_config['auto_calc_range'] = auto_calc_range

                voltage_diff = self.config_manager.get('grade_settings.voltage_diff')
                if voltage_diff is None:
                    voltage_diff = self.config_manager.get('voltage_voltage_diff')
                if voltage_diff is not None:
                    self.voltage_config['voltage_diff'] = voltage_diff

                # 确保tolerance_percent字段存在
                if 'tolerance_percent' not in self.voltage_config:
                    self.voltage_config['tolerance_percent'] = 5.0
                    logger.debug("添加默认tolerance_percent字段: 5.0")

                logger.debug("电压配置加载完成")

        except Exception as e:
            logger.error(f"加载电压配置失败: {e}")
    
    def validate_config(self) -> bool:
        """验证配置是否合理"""
        try:
            config = self.voltage_config
            
            # 检查标准电压
            if config['standard_voltage'] <= 0 or config['standard_voltage'] > 50:
                logger.warning("标准电压设置不合理")
                return False
            
            # 检查容差百分比
            if config['tolerance_percent'] <= 0 or config['tolerance_percent'] > 100:
                logger.warning("容差百分比设置不合理")
                return False
            
            # 检查电压范围
            if config['min_voltage'] >= config['max_voltage']:
                logger.warning("电压范围设置不合理")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证电压配置失败: {e}")
            return False
    
    def reset_to_default(self):
        """重置到默认配置（电压差模式）"""
        try:
            self.voltage_config = {
                'standard_voltage': 3.210,
                'min_voltage': 2.000,
                'max_voltage': 5.000,
                'voltage_diff': 0.16,
                'auto_calc_range': True,
                'tolerance_percent': 5.0
            }

            self.voltage_config_changed.emit()
            logger.info("电压配置已重置到默认值")

        except Exception as e:
            logger.error(f"重置电压配置失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        try:
            # 保存配置
            self.save_config()
            
            logger.debug("电压范围管理器资源清理完成")
            
        except Exception as e:
            logger.error(f"电压范围管理器清理失败: {e}")
