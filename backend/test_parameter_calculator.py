"""
测试参数计算管理器

职责：
- 计算Rct变异系数
- 计算容量预测
- 提供相关的统计分析功能
"""

import logging
import math
import statistics
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TestParameterCalculator:
    """
    测试参数计算管理器
    
    职责：
    - 计算Rct变异系数（变异系数 = 标准差/平均值 × 100%）
    - 计算容量预测（基于阻抗与容量的关系模型）
    - 提供统计分析功能
    """
    
    def __init__(self, config_manager):
        """
        初始化测试参数计算器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        
        # 容量预测模型参数（可配置）
        self.capacity_model_params = {
            'base_capacity': 3.0,  # 基准容量 (AH)
            'rs_coefficient': -0.1,  # Rs系数
            'rct_coefficient': -0.05,  # Rct系数
            'voltage_coefficient': 0.5,  # 电压系数
            'min_capacity': 0.5,  # 最小容量限制
            'max_capacity': 5.0   # 最大容量限制
        }
        
        logger.debug("测试参数计算管理器初始化完成")
    
    def calculate_rct_coefficient_of_variation(self, rct_values: List[float]) -> float:
        """
        计算Rct变异系数
        
        Args:
            rct_values: Rct值列表 (mΩ)
            
        Returns:
            变异系数百分比
        """
        try:
            if not rct_values or len(rct_values) < 2:
                logger.warning("Rct值数量不足，无法计算变异系数")
                return 0.0
            
            # 过滤无效值
            valid_values = [v for v in rct_values if v > 0 and not math.isnan(v) and not math.isinf(v)]
            
            if len(valid_values) < 2:
                logger.warning("有效Rct值数量不足，无法计算变异系数")
                return 0.0
            
            # 计算平均值和标准差
            mean_value = statistics.mean(valid_values)
            std_dev = statistics.stdev(valid_values)
            
            # 计算变异系数（百分比）
            if mean_value == 0:
                logger.warning("Rct平均值为0，无法计算变异系数")
                return 0.0
            
            coefficient_of_variation = (std_dev / mean_value) * 100.0
            
            logger.debug(f"Rct变异系数计算: 平均值={mean_value:.3f}mΩ, "
                        f"标准差={std_dev:.3f}mΩ, 变异系数={coefficient_of_variation:.2f}%")
            
            return round(coefficient_of_variation, 2)
            
        except Exception as e:
            logger.error(f"计算Rct变异系数失败: {e}")
            return 0.0
    
    def calculate_capacity_prediction(self, voltage: float, rs_value: float, rct_value: float) -> float:
        """
        计算容量预测
        
        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)
            
        Returns:
            预测容量 (AH)
        """
        try:
            # 获取模型参数
            base_capacity = self.capacity_model_params['base_capacity']
            rs_coeff = self.capacity_model_params['rs_coefficient']
            rct_coeff = self.capacity_model_params['rct_coefficient']
            voltage_coeff = self.capacity_model_params['voltage_coefficient']
            min_capacity = self.capacity_model_params['min_capacity']
            max_capacity = self.capacity_model_params['max_capacity']
            
            # 获取标准参考值
            standard_voltage = self.config_manager.get('product.standard_voltage', 3.2)
            
            # 计算偏差
            voltage_deviation = voltage - standard_voltage
            
            # 容量预测模型：
            # 预测容量 = 基准容量 + 电压偏差影响 + Rs影响 + Rct影响
            predicted_capacity = (
                base_capacity +
                voltage_deviation * voltage_coeff +
                rs_value * rs_coeff +
                rct_value * rct_coeff
            )
            
            # 应用容量限制
            predicted_capacity = max(min_capacity, min(predicted_capacity, max_capacity))
            
            logger.debug(f"容量预测计算: 电压={voltage:.3f}V, Rs={rs_value:.3f}mΩ, "
                        f"Rct={rct_value:.3f}mΩ, 预测容量={predicted_capacity:.3f}AH")
            
            return round(predicted_capacity, 3)
            
        except Exception as e:
            logger.error(f"计算容量预测失败: {e}")
            return self.capacity_model_params['base_capacity']
    
    def calculate_advanced_capacity_prediction(self, voltage: float, rs_value: float, rct_value: float,
                                             frequency_data: Optional[List[Dict]] = None) -> float:
        """
        计算高级容量预测（考虑频率响应）
        
        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)
            frequency_data: 频率数据列表（可选）
            
        Returns:
            预测容量 (AH)
        """
        try:
            # 基础容量预测
            base_prediction = self.calculate_capacity_prediction(voltage, rs_value, rct_value)
            
            # 如果没有频率数据，返回基础预测
            if not frequency_data:
                return base_prediction
            
            # 分析频率响应特征
            frequency_factor = self._analyze_frequency_response(frequency_data)
            
            # 应用频率响应修正
            corrected_capacity = base_prediction * frequency_factor
            
            # 应用容量限制
            min_capacity = self.capacity_model_params['min_capacity']
            max_capacity = self.capacity_model_params['max_capacity']
            corrected_capacity = max(min_capacity, min(corrected_capacity, max_capacity))
            
            logger.debug(f"高级容量预测: 基础预测={base_prediction:.3f}AH, "
                        f"频率修正因子={frequency_factor:.3f}, 修正后={corrected_capacity:.3f}AH")
            
            return round(corrected_capacity, 3)
            
        except Exception as e:
            logger.error(f"计算高级容量预测失败: {e}")
            return self.calculate_capacity_prediction(voltage, rs_value, rct_value)
    
    def _analyze_frequency_response(self, frequency_data: List[Dict]) -> float:
        """
        分析频率响应特征
        
        Args:
            frequency_data: 频率数据列表
            
        Returns:
            频率响应修正因子
        """
        try:
            if not frequency_data:
                return 1.0
            
            # 分析低频和高频阻抗特征
            low_freq_impedances = []
            high_freq_impedances = []
            
            for data in frequency_data:
                freq = data.get('frequency', 0)
                magnitude = data.get('impedance_magnitude', 0)
                
                if freq <= 1.0:  # 低频
                    low_freq_impedances.append(magnitude)
                elif freq >= 100.0:  # 高频
                    high_freq_impedances.append(magnitude)
            
            # 计算低频/高频阻抗比值
            if low_freq_impedances and high_freq_impedances:
                low_freq_avg = statistics.mean(low_freq_impedances)
                high_freq_avg = statistics.mean(high_freq_impedances)
                
                if high_freq_avg > 0:
                    freq_ratio = low_freq_avg / high_freq_avg
                    
                    # 根据频率比值计算修正因子
                    # 正常电池的低频/高频比值通常在2-10之间
                    if 2.0 <= freq_ratio <= 10.0:
                        correction_factor = 1.0 + (freq_ratio - 6.0) * 0.02
                    else:
                        correction_factor = 0.9  # 异常频率响应，降低容量预测
                    
                    return max(0.5, min(correction_factor, 1.5))
            
            return 1.0
            
        except Exception as e:
            logger.error(f"分析频率响应失败: {e}")
            return 1.0
    
    def calculate_statistical_summary(self, values: List[float], parameter_name: str) -> Dict[str, float]:
        """
        计算统计摘要
        
        Args:
            values: 数值列表
            parameter_name: 参数名称
            
        Returns:
            统计摘要字典
        """
        try:
            if not values:
                return {
                    'count': 0,
                    'mean': 0.0,
                    'std_dev': 0.0,
                    'min': 0.0,
                    'max': 0.0,
                    'coefficient_of_variation': 0.0
                }
            
            # 过滤无效值
            valid_values = [v for v in values if not math.isnan(v) and not math.isinf(v)]
            
            if not valid_values:
                return {
                    'count': 0,
                    'mean': 0.0,
                    'std_dev': 0.0,
                    'min': 0.0,
                    'max': 0.0,
                    'coefficient_of_variation': 0.0
                }
            
            # 计算统计量
            count = len(valid_values)
            mean_val = statistics.mean(valid_values)
            std_dev = statistics.stdev(valid_values) if count > 1 else 0.0
            min_val = min(valid_values)
            max_val = max(valid_values)
            
            # 计算变异系数
            cv = (std_dev / mean_val * 100.0) if mean_val != 0 else 0.0
            
            summary = {
                'count': count,
                'mean': round(mean_val, 3),
                'std_dev': round(std_dev, 3),
                'min': round(min_val, 3),
                'max': round(max_val, 3),
                'coefficient_of_variation': round(cv, 2)
            }
            
            logger.debug(f"{parameter_name}统计摘要: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"计算{parameter_name}统计摘要失败: {e}")
            return {
                'count': 0,
                'mean': 0.0,
                'std_dev': 0.0,
                'min': 0.0,
                'max': 0.0,
                'coefficient_of_variation': 0.0
            }
    
    def update_capacity_model_params(self, new_params: Dict[str, float]):
        """
        更新容量预测模型参数
        
        Args:
            new_params: 新的模型参数
        """
        try:
            self.capacity_model_params.update(new_params)
            logger.info(f"容量预测模型参数已更新: {new_params}")
            
        except Exception as e:
            logger.error(f"更新容量预测模型参数失败: {e}")
    
    def get_capacity_model_info(self) -> Dict[str, Any]:
        """
        获取容量预测模型信息
        
        Returns:
            模型信息字典
        """
        try:
            return {
                'model_type': '线性回归模型',
                'parameters': self.capacity_model_params.copy(),
                'description': '基于电压、Rs、Rct的线性容量预测模型',
                'formula': 'C = C0 + α×ΔV + β×Rs + γ×Rct'
            }
            
        except Exception as e:
            logger.error(f"获取容量预测模型信息失败: {e}")
            return {'error': str(e)}
    
    def cleanup(self):
        """清理资源"""
        try:
            logger.debug("测试参数计算管理器资源清理完成")
            
        except Exception as e:
            logger.error(f"测试参数计算管理器清理失败: {e}")
