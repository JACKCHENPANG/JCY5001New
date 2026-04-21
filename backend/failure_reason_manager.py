"""
失败原因详细化管理器

职责：
- 生成详细的失败原因描述
- 包含具体的超标范围信息
- 支持电压、Rs、Rct等参数的失败原因分析
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class FailureReasonManager:
    """
    失败原因详细化管理器
    
    职责：
    - 生成详细的失败原因描述
    - 包含具体的超标范围信息
    - 支持多种参数的失败原因分析
    """
    
    def __init__(self, config_manager):
        """
        初始化失败原因管理器

        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager

        # 缓存配置值，提高性能
        self._cached_config = {}
        self._load_config_cache()

        logger.debug("失败原因详细化管理器初始化完成")

    def reload_config(self):
        """重新加载配置缓存（用于多次测试间的状态重置）"""
        try:
            self._cached_config.clear()
            self._load_config_cache()
            logger.debug("失败原因管理器配置已重新加载")
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")

    def _load_config_cache(self):
        """加载配置缓存"""
        try:
            self._cached_config = {
                'rs_min': self.config_manager.get('impedance.rs_min', 0.5),
                'rs_max': self.config_manager.get('impedance.rs_grade3_max', 50.0),
                'rct_min': self.config_manager.get('impedance.rct_min', 0.5),
                'rct_max': self.config_manager.get('impedance.rct_grade3_max', 100.0),
            }
            logger.debug(f"配置缓存已加载: {self._cached_config}")
        except Exception as e:
            logger.error(f"加载配置缓存失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            # 🔧 修复：使用默认值，避免后续访问_cached_config时出现异常
            self._cached_config = {
                'rs_min': 0.5,
                'rs_max': 50.0,
                'rct_min': 0.5,
                'rct_max': 100.0,
            }
            logger.debug(f"使用默认配置缓存: {self._cached_config}")

    def reload_config(self):
        """重新加载配置（当配置变更时调用）"""
        try:
            self._load_config_cache()
            logger.info("✅ 失败原因管理器配置已重新加载")
        except Exception as e:
            logger.error(f"❌ 重新加载失败原因管理器配置失败: {e}")
    
    def generate_detailed_failure_reason(self, voltage: float, rs_value: float, rct_value: float, 
                                       outlier_result: Optional[str] = None) -> str:
        """
        生成详细的失败原因描述
        
        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)
            outlier_result: 离群率检测结果
            
        Returns:
            详细的失败原因描述
        """
        try:
            failure_reasons = []

            # 检查电压失败原因
            voltage_reason = self._check_voltage_failure(voltage)
            if voltage_reason:
                failure_reasons.append(voltage_reason)

            # 检查Rs失败原因
            rs_reason = self._check_rs_failure(rs_value)
            if rs_reason:
                failure_reasons.append(rs_reason)

            # 检查Rct失败原因
            rct_reason = self._check_rct_failure(rct_value)
            if rct_reason:
                failure_reasons.append(rct_reason)

            # 检查离群率失败原因
            outlier_reason = self._check_outlier_failure(outlier_result)
            if outlier_reason:
                failure_reasons.append(outlier_reason)

            # 组合失败原因
            if failure_reasons:
                return "; ".join(failure_reasons)
            else:
                return ""

        except Exception as e:
            logger.error(f"生成详细失败原因失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return "失败原因获取异常"
    
    def _check_voltage_failure(self, voltage: float) -> Optional[str]:
        """
        检查电压失败原因

        Args:
            voltage: 电压值 (V)

        Returns:
            电压失败原因描述，如果合格则返回None
        """
        try:
            # 修复优先使用界面设置的标准电压和电压差，确保与用户设置一致
            standard_voltage = self.config_manager.get('grade_settings.standard_voltage')
            voltage_diff = self.config_manager.get('grade_settings.voltage_diff')

            if standard_voltage is not None and voltage_diff is not None:
                # 使用界面设置的标准电压和电压差计算范围
                voltage_min = standard_voltage - voltage_diff
                voltage_max = standard_voltage + voltage_diff
                logger.debug(f"失败原因管理器使用界面设置电压参数: 标准电压={standard_voltage:.3f}V, 电压差=±{voltage_diff:.3f}V")
            else:
                # 备用：使用取样测试应用的电压范围
                voltage_min = self.config_manager.get('grade_settings.voltage_min')
                if voltage_min is None:
                    voltage_min = self.config_manager.get('test_params.voltage_range.min', 2.889)

                voltage_max = self.config_manager.get('grade_settings.voltage_max')
                if voltage_max is None:
                    voltage_max = self.config_manager.get('test_params.voltage_range.max', 3.531)
                logger.debug(f"失败原因管理器使用备用电压参数: 范围=({voltage_min:.3f}-{voltage_max:.3f}V)")

            if voltage < voltage_min:
                return f"电压超标，范围{voltage_min:.3f}V~{voltage_max:.3f}V（实测{voltage:.3f}V，过低）"
            elif voltage > voltage_max:
                return f"电压超标，范围{voltage_min:.3f}V~{voltage_max:.3f}V（实测{voltage:.3f}V，过高）"
            else:
                return None

        except Exception as e:
            logger.error(f"检查电压失败原因失败: {e}")
            return f"电压检查异常（{voltage:.3f}V）"
    
    def _check_rs_failure(self, rs_value: float) -> Optional[str]:
        """
        检查Rs失败原因

        Args:
            rs_value: Rs值 (mΩ)

        Returns:
            Rs失败原因描述，如果合格则返回None
        """
        try:
            # 修复：优先从grade_settings获取Rs范围，与测试结果管理器判断逻辑保持一致
            rs_min = self.config_manager.get('grade_settings.rs_min')
            if rs_min is None:
                rs_min = self.config_manager.get('impedance.rs_min', 0.5)

            rs_max = self.config_manager.get('grade_settings.rs_max')
            if rs_max is None:
                rs_max = self.config_manager.get('impedance.rs_grade3_max', 50.0)

            if rs_value < rs_min:
                return f"Rs超标，范围{rs_min:.3f}mΩ~{rs_max:.3f}mΩ（实测{rs_value:.3f}mΩ，过低）"
            elif rs_value > rs_max:
                return f"Rs超标，范围{rs_min:.3f}mΩ~{rs_max:.3f}mΩ（实测{rs_value:.3f}mΩ，过高）"
            else:
                return None

        except Exception as e:
            logger.error(f"检查Rs失败原因失败: {e}")
            return f"Rs检查异常（{rs_value:.3f}mΩ）"
    
    def _check_rct_failure(self, rct_value: float) -> Optional[str]:
        """
        检查Rct失败原因

        Args:
            rct_value: Rct值 (mΩ)

        Returns:
            Rct失败原因描述，如果合格则返回None
        """
        try:
            # 修复：优先从grade_settings获取Rct范围，与测试结果管理器判断逻辑保持一致
            rct_min = self.config_manager.get('grade_settings.rct_min')
            if rct_min is None:
                rct_min = self.config_manager.get('impedance.rct_min', 0.5)

            rct_max = self.config_manager.get('grade_settings.rct_max')
            if rct_max is None:
                rct_max = self.config_manager.get('impedance.rct_grade3_max', 100.0)

            if rct_value < rct_min:
                return f"Rct超标，范围{rct_min:.3f}mΩ~{rct_max:.3f}mΩ（实测{rct_value:.3f}mΩ，过低）"
            elif rct_value > rct_max:
                return f"Rct超标，范围{rct_min:.3f}mΩ~{rct_max:.3f}mΩ（实测{rct_value:.3f}mΩ，过高）"
            else:
                return None

        except Exception as e:
            logger.error(f"检查Rct失败原因失败: {e}")
            return f"Rct检查异常（{rct_value:.3f}mΩ）"

    def _check_outlier_failure(self, outlier_result: Optional[str]) -> Optional[str]:
        """
        检查离群率失败原因

        Args:
            outlier_result: 离群率检测结果

        Returns:
            离群率失败原因描述，如果合格则返回None
        """
        try:
            # 🚫 离群率检测功能已删除，直接返回None
            return None

        except Exception as e:
            logger.error(f"检查离群率失败原因失败: {e}")
            return f"离群率检查异常"


    def get_failure_items_list(self, voltage: float, rs_value: float, rct_value: float,
                              outlier_result: Optional[str] = None) -> List[str]:
        """
        获取失败项目列表（检查所有项目，显示完整失败原因）

        检查顺序：
        1. 电压检测（电压范围不合格）
        2. 离群率检测（偏差超过阈值）
        3. Rs档位判断
        4. Rct档位判断

        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)
            outlier_result: 离群率检测结果

        Returns:
            失败项目列表（包含所有失败项目）
        """
        try:
            fail_items = []

            # 检查电压
            if self._check_voltage_failure(voltage):
                fail_items.append("电压")

            # 检查离群率
            if self._check_outlier_failure(outlier_result):
                fail_items.append("离群率")

            # 检查Rs
            if self._check_rs_failure(rs_value):
                fail_items.append("Rs")

            # 检查Rct
            if self._check_rct_failure(rct_value):
                fail_items.append("Rct")

            return fail_items

        except Exception as e:
            logger.error(f"获取失败项目列表失败: {e}")
            return ["系统错误"]
    
    def is_test_passed(self, voltage: float, rs_value: float, rct_value: float, 
                      outlier_result: Optional[str] = None) -> bool:
        """
        判断测试是否通过
        
        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)
            outlier_result: 离群率检测结果
            
        Returns:
            是否通过测试
        """
        try:
            fail_items = self.get_failure_items_list(voltage, rs_value, rct_value, outlier_result)
            return len(fail_items) == 0
            
        except Exception as e:
            logger.error(f"判断测试通过状态失败: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        try:
            # 🔧 修复：清理配置缓存，确保下次重新创建时重新加载
            self._cached_config.clear()
            logger.debug("失败原因详细化管理器资源清理完成，配置缓存已清空")

        except Exception as e:
            logger.error(f"失败原因详细化管理器清理失败: {e}")
