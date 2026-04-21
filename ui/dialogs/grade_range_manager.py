#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
档位范围管理器
负责Rs和Rct档位范围的计算和管理

Author: Jack
Date: 2025-06-04
"""

import logging
from typing import Dict, Any, List, Tuple
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class GradeRangeManager(QObject):
    """
    档位范围管理器
    
    职责：
    - 管理Rs和Rct档位的计算逻辑
    - 处理档位范围的自动计算
    - 管理档位配置的保存和加载
    """
    
    # 信号定义
    ranges_updated = pyqtSignal(str, list)  # 范围更新信号 (type, ranges)
    
    def __init__(self, config_manager, parent=None):
        """
        初始化档位范围管理器
        
        Args:
            config_manager: 配置管理器
            parent: 父对象
        """
        super().__init__(parent)
        
        self.config_manager = config_manager

        # 🐛 修复：统一使用impedance配置节点，确保与档位计算逻辑一致
        # Rs档位配置
        self.rs_config = {
            'grade_count': self.config_manager.get('impedance.rs_grade_count', 3),
            'min_value': self.config_manager.get('impedance.rs_min', 0.169),
            'max_value': self.config_manager.get('impedance.rs_grade3_max', 0.225),
            'auto_calc': self.config_manager.get('grade_settings.rs_auto_calc', True),
            'grade1_max': self.config_manager.get('impedance.rs_grade1_max', 0.188),
            'grade2_max': self.config_manager.get('impedance.rs_grade2_max', 0.206),
            'grade3_max': self.config_manager.get('impedance.rs_grade3_max', 0.225)
        }

        # Rct档位配置（固定3档）
        self.rct_config = {
            'grade_count': 3,  # 固定3档
            'min_value': self.config_manager.get('grade_settings.rct_min', 0.001),
            'max_value': self.config_manager.get('grade_settings.rct_max', 0.086),
            'auto_calc': self.config_manager.get('grade_settings.rct_auto_calc', True),
            'grade1_max': self.config_manager.get('grade_settings.rct1_max', 0.029),
            'grade2_max': self.config_manager.get('grade_settings.rct2_max', 0.058),
            'grade3_max': self.config_manager.get('grade_settings.rct3_max', 0.086)
        }
        
        logger.debug("档位范围管理器初始化完成")
        logger.debug(f"🔍 [档位配置] Rs范围: {self.rs_config['min_value']:.3f} - {self.rs_config['max_value']:.3f}mΩ")
        logger.debug(f"🔍 [档位配置] Rct范围: {self.rct_config['min_value']:.3f} - {self.rct_config['max_value']:.3f}mΩ")
    
    def calculate_rs_ranges(self, grade_count: int, min_val: float, max_val: float) -> List[Tuple[float, float]]:
        """
        计算Rs档位范围
        
        Args:
            grade_count: 档位数量
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            List[Tuple[float, float]]: 档位范围列表 [(min, max), ...]
        """
        try:
            if min_val >= max_val:
                logger.warning(f"Rs范围设置错误: min({min_val}) >= max({max_val})")
                return []
            
            ranges = []
            
            if grade_count == 1:
                # 1档：全范围
                ranges.append((min_val, max_val))
                
            elif grade_count == 2:
                # 2档：平均分割
                mid_val = (min_val + max_val) / 2
                ranges.append((min_val, mid_val))
                ranges.append((mid_val, max_val))
                
            elif grade_count == 3:
                # 3档：三等分
                range_size = (max_val - min_val) / 3
                grade1_max = min_val + range_size
                grade2_max = min_val + 2 * range_size
                
                ranges.append((min_val, grade1_max))
                ranges.append((grade1_max, grade2_max))
                ranges.append((grade2_max, max_val))
            
            # 更新配置
            self.rs_config.update({
                'grade_count': grade_count,
                'min_value': min_val,
                'max_value': max_val
            })
            
            if grade_count >= 1:
                self.rs_config['grade1_max'] = ranges[0][1]
            if grade_count >= 2:
                self.rs_config['grade2_max'] = ranges[1][1]
            if grade_count >= 3:
                self.rs_config['grade3_max'] = ranges[2][1]
            
            logger.debug(f"Rs档位范围计算完成: {ranges}")
            return ranges
            
        except Exception as e:
            logger.error(f"计算Rs档位范围失败: {e}")
            return []
    
    def calculate_rct_ranges(self, min_val: float, max_val: float) -> List[Tuple[float, float]]:
        """
        计算Rct档位范围（固定3档）
        
        Args:
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            List[Tuple[float, float]]: 档位范围列表 [(min, max), ...]
        """
        try:
            if min_val >= max_val:
                logger.warning(f"Rct范围设置错误: min({min_val}) >= max({max_val})")
                return []
            
            # 固定3档：三等分
            range_size = (max_val - min_val) / 3
            grade1_max = min_val + range_size
            grade2_max = min_val + 2 * range_size
            
            ranges = [
                (min_val, grade1_max),
                (grade1_max, grade2_max),
                (grade2_max, max_val)
            ]
            
            # 更新配置
            self.rct_config.update({
                'min_value': min_val,
                'max_value': max_val,
                'grade1_max': grade1_max,
                'grade2_max': grade2_max,
                'grade3_max': max_val
            })
            
            logger.debug(f"Rct档位范围计算完成: {ranges}")
            return ranges
            
        except Exception as e:
            logger.error(f"计算Rct档位范围失败: {e}")
            return []
    
    def get_rs_ranges_text(self) -> str:
        """获取Rs档位范围文本"""
        try:
            ranges = self.calculate_rs_ranges(
                self.rs_config['grade_count'],
                self.rs_config['min_value'],
                self.rs_config['max_value']
            )
            
            if not ranges:
                return "计算失败"
            
            text_parts = []
            for i, (min_val, max_val) in enumerate(ranges, 1):
                text_parts.append(f"Rs{i}: {min_val:.3f}-{max_val:.3f} mΩ")
            
            return "\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"获取Rs档位范围文本失败: {e}")
            return "获取失败"
    
    def get_rct_ranges_text(self) -> str:
        """获取Rct档位范围文本"""
        try:
            ranges = self.calculate_rct_ranges(
                self.rct_config['min_value'],
                self.rct_config['max_value']
            )
            
            if not ranges:
                return "计算失败"
            
            text_parts = []
            for i, (min_val, max_val) in enumerate(ranges, 1):
                text_parts.append(f"Rct{i}: {min_val:.3f}-{max_val:.3f} mΩ")
            
            return "\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"获取Rct档位范围文本失败: {e}")
            return "获取失败"
    
    def update_rs_config(self, **kwargs):
        """更新Rs配置"""
        try:
            self.rs_config.update(kwargs)
            
            # 如果启用自动计算，重新计算范围
            if self.rs_config.get('auto_calc', True):
                ranges = self.calculate_rs_ranges(
                    self.rs_config['grade_count'],
                    self.rs_config['min_value'],
                    self.rs_config['max_value']
                )
                self.ranges_updated.emit('rs', ranges)
            
            logger.debug(f"Rs配置更新: {kwargs}")
            
        except Exception as e:
            logger.error(f"更新Rs配置失败: {e}")
    
    def update_rct_config(self, **kwargs):
        """更新Rct配置"""
        try:
            self.rct_config.update(kwargs)
            
            # 如果启用自动计算，重新计算范围
            if self.rct_config.get('auto_calc', True):
                ranges = self.calculate_rct_ranges(
                    self.rct_config['min_value'],
                    self.rct_config['max_value']
                )
                self.ranges_updated.emit('rct', ranges)
            
            logger.debug(f"Rct配置更新: {kwargs}")
            
        except Exception as e:
            logger.error(f"更新Rct配置失败: {e}")
    
    def get_rs_config(self) -> Dict[str, Any]:
        """获取Rs配置"""
        return self.rs_config.copy()
    
    def get_rct_config(self) -> Dict[str, Any]:
        """获取Rct配置"""
        return self.rct_config.copy()
    
    def save_config(self):
        """保存配置到配置管理器"""
        try:
            if self.config_manager:
                # 🐛 修复：同时保存到grade_settings和impedance节点，确保配置一致性

                # 保存Rs配置到grade_settings节点（向后兼容）
                self.config_manager.set('grade_settings.rs_grade_count', self.rs_config['grade_count'])
                self.config_manager.set('grade_settings.rs_min', self.rs_config['min_value'])
                self.config_manager.set('grade_settings.rs_max', self.rs_config['max_value'])
                self.config_manager.set('grade_settings.rs_auto_calc', self.rs_config['auto_calc'])

                # 🔧 关键修复：同时保存到impedance节点（档位计算逻辑使用）
                self.config_manager.set('impedance.rs_grade_count', self.rs_config['grade_count'])
                self.config_manager.set('impedance.rs_min', self.rs_config['min_value'])
                self.config_manager.set('impedance.rs_grade3_max', self.rs_config['max_value'])

                # 计算并保存Rs档位阈值到两个节点
                rs_ranges = self.calculate_rs_ranges(
                    self.rs_config['grade_count'],
                    self.rs_config['min_value'],
                    self.rs_config['max_value']
                )
                for i, (min_val, max_val) in enumerate(rs_ranges, 1):
                    # 保存到grade_settings节点
                    self.config_manager.set(f'grade_settings.rs{i}_max', max_val)
                    # 保存到impedance节点
                    self.config_manager.set(f'impedance.rs_grade{i}_max', max_val)

                # 保存Rct配置到grade_settings节点（向后兼容）
                self.config_manager.set('grade_settings.rct_min', self.rct_config['min_value'])
                self.config_manager.set('grade_settings.rct_max', self.rct_config['max_value'])
                self.config_manager.set('grade_settings.rct_auto_calc', self.rct_config['auto_calc'])

                # 🔧 关键修复：同时保存到impedance节点（档位计算逻辑使用）
                self.config_manager.set('impedance.rct_min', self.rct_config['min_value'])
                self.config_manager.set('impedance.rct_grade3_max', self.rct_config['max_value'])
                self.config_manager.set('impedance.rct_grade_count', 3)  # Rct固定3档

                # 计算并保存Rct档位阈值到两个节点（固定3档）
                rct_ranges = self.calculate_rct_ranges(
                    self.rct_config['min_value'],
                    self.rct_config['max_value']
                )
                for i, (min_val, max_val) in enumerate(rct_ranges, 1):
                    # 保存到grade_settings节点
                    self.config_manager.set(f'grade_settings.rct{i}_max', max_val)
                    # 保存到impedance节点
                    self.config_manager.set(f'impedance.rct_grade{i}_max', max_val)

                # 同步到主界面使用的配置键（向后兼容）
                self._sync_to_channel_display_config()

                logger.debug("档位配置保存完成")

        except Exception as e:
            logger.error(f"保存档位配置失败: {e}")

    def _sync_to_channel_display_config(self):
        """同步配置到通道显示组件使用的配置键"""
        try:
            if not self.config_manager:
                return

            # 同步Rs档位配置
            rs_ranges = self.calculate_rs_ranges(
                self.rs_config['grade_count'],
                self.rs_config['min_value'],
                self.rs_config['max_value']
            )

            # 同步Rs档位阈值到impedance节点
            for i, (min_val, max_val) in enumerate(rs_ranges, 1):
                self.config_manager.set(f'impedance.rs_grade{i}_max', max_val)

            # 同步Rs档位数量
            self.config_manager.set('impedance.rs_grade_count', self.rs_config['grade_count'])

            # 同步Rct档位配置
            rct_ranges = self.calculate_rct_ranges(
                self.rct_config['min_value'],
                self.rct_config['max_value']
            )

            # 同步Rct档位阈值到impedance节点
            for i, (min_val, max_val) in enumerate(rct_ranges, 1):
                self.config_manager.set(f'impedance.rct_grade{i}_max', max_val)

            # 同步Rct档位数量（固定3档）
            self.config_manager.set('impedance.rct_grade_count', 3)

            # 新增同步Rs/Rct最小值配置
            self.config_manager.set('impedance.rs_min', self.rs_config['min_value'])
            self.config_manager.set('impedance.rct_min', self.rct_config['min_value'])

            logger.debug("档位配置同步到通道显示配置完成")

        except Exception as e:
            logger.error(f"同步档位配置失败: {e}")
    
    def load_config(self):
        """从配置管理器加载配置"""
        try:
            if self.config_manager:
                # 加载Rs配置从grade_settings节点
                rs_grade_count = self.config_manager.get('grade_settings.rs_grade_count', 3)
                rs_min = self.config_manager.get('grade_settings.rs_min', 0.5)
                rs_max = self.config_manager.get('grade_settings.rs_max', 50.0)
                rs_auto_calc = self.config_manager.get('grade_settings.rs_auto_calc', True)

                self.rs_config.update({
                    'grade_count': rs_grade_count,
                    'min_value': rs_min,
                    'max_value': rs_max,
                    'auto_calc': rs_auto_calc
                })

                # 加载Rct配置从grade_settings节点
                rct_min = self.config_manager.get('grade_settings.rct_min', 5.0)
                rct_max = self.config_manager.get('grade_settings.rct_max', 100.0)
                rct_auto_calc = self.config_manager.get('grade_settings.rct_auto_calc', True)

                self.rct_config.update({
                    'grade_count': 3,  # 固定3档
                    'min_value': rct_min,
                    'max_value': rct_max,
                    'auto_calc': rct_auto_calc
                })

                # 向后兼容：如果grade_settings节点没有数据，尝试从旧的配置键加载
                self._load_from_legacy_config()

                logger.debug("档位配置加载完成")

        except Exception as e:
            logger.error(f"加载档位配置失败: {e}")

    def _load_from_legacy_config(self):
        """从旧的配置键加载配置（向后兼容）"""
        try:
            if not self.config_manager:
                return

            # 检查是否有旧的rs_配置
            legacy_rs_grade_count = self.config_manager.get('rs_grade_count')
            if legacy_rs_grade_count is not None:
                self.rs_config['grade_count'] = legacy_rs_grade_count

            legacy_rs_min = self.config_manager.get('rs_min_value')
            if legacy_rs_min is not None:
                self.rs_config['min_value'] = legacy_rs_min

            legacy_rs_max = self.config_manager.get('rs_max_value')
            if legacy_rs_max is not None:
                self.rs_config['max_value'] = legacy_rs_max

            legacy_rs_auto = self.config_manager.get('rs_auto_calc')
            if legacy_rs_auto is not None:
                self.rs_config['auto_calc'] = legacy_rs_auto

            # 检查是否有旧的rct_配置
            legacy_rct_min = self.config_manager.get('rct_min_value')
            if legacy_rct_min is not None:
                self.rct_config['min_value'] = legacy_rct_min

            legacy_rct_max = self.config_manager.get('rct_max_value')
            if legacy_rct_max is not None:
                self.rct_config['max_value'] = legacy_rct_max

            legacy_rct_auto = self.config_manager.get('rct_auto_calc')
            if legacy_rct_auto is not None:
                self.rct_config['auto_calc'] = legacy_rct_auto

            logger.debug("旧配置兼容性加载完成")

        except Exception as e:
            logger.error(f"加载旧配置失败: {e}")
    
    def get_grade_by_value(self, value: float, grade_type: str) -> str:
        """
        根据值获取档位（已弃用：UI不应该计算档位，应该使用后端传递的数据）

        Args:
            value: 测试值
            grade_type: 档位类型 ('rs' 或 'rct')

        Returns:
            str: 档位字符串
        """
        logger.warning(f"⚠️ [已弃用] UI层不应该计算档位！应该使用后端传递的档位数据")
        logger.warning(f"   调用参数: value={value}, grade_type={grade_type}")

        # 🐛 修复：UI不再计算档位，直接返回警告信息
        return "UI不计算档位"
    
    def validate_ranges(self) -> Dict[str, bool]:
        """验证档位范围设置是否合理"""
        try:
            result = {'rs': True, 'rct': True}
            
            # 验证Rs范围
            if self.rs_config['min_value'] >= self.rs_config['max_value']:
                result['rs'] = False
                logger.warning("Rs范围设置不合理：最小值大于等于最大值")
            
            # 验证Rct范围
            if self.rct_config['min_value'] >= self.rct_config['max_value']:
                result['rct'] = False
                logger.warning("Rct范围设置不合理：最小值大于等于最大值")
            
            return result
            
        except Exception as e:
            logger.error(f"验证档位范围失败: {e}")
            return {'rs': False, 'rct': False}
    
    def cleanup(self):
        """清理资源"""
        try:
            # 保存配置
            self.save_config()
            
            logger.debug("档位范围管理器资源清理完成")
            
        except Exception as e:
            logger.error(f"档位范围管理器清理失败: {e}")
