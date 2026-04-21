# -*- coding: utf-8 -*-
"""
电化学阻抗谱(EIS)分析器
按照标准EIS分析方法计算Rs和Rct值

Author: Jack
Date: 2025-01-27
"""

import numpy as np
import math
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime

# numpy安全配置：防止内存访问违例
np.seterr(all='raise')  # 将numpy错误转换为异常
np.seterrcall(None)     # 清除错误回调
import logging
from typing import Dict, List, Tuple, Optional
from scipy import interpolate
from scipy.optimize import curve_fit
import math

logger = logging.getLogger(__name__)


class EISAnalyzer:
    """电化学阻抗谱分析器"""

    def __init__(self):
        """初始化EIS分析器"""
        self.logger = logging.getLogger(__name__)
        self.logger.debug("EIS分析器初始化完成")

        # 增强版EIS分析配置
        self.enhanced_config = {
            'high_freq_threshold': 100,      # 高频阈值 (Hz)
            'low_freq_threshold': 2,         # 低频阈值 (Hz)
            'sei_min_change': 0.05,          # 优化SEI最小变化阈值降低到0.05mΩ（适应低内阻电池）
            'sei_min_ratio': 0.03,           # 优化SEI最小比例阈值降低到3%
            'warburg_corr_threshold': 0.5,   # Warburg相关性阈值
            'min_data_points': 10,           # 最少数据点数
        }


    def _calculate_rs_standard(self, frequencies: np.ndarray,
                              real_parts: np.ndarray,
                              imag_parts: np.ndarray) -> float:
        """
        按照优化方法计算Rs值（虚部过零点优先）

        优化说明：
        1. 优先使用虚部过零点方法（适用于低阻抗电池）
        2. 备用方法：最高频点方法
        3. 最后方法：高频段线性拟合延长线

        Args:
            frequencies: 频率数组
            real_parts: 实部数组
            imag_parts: 虚部数组

        Returns:
            Rs值 (mΩ)
        """
        try:
            self.logger.debug("开始计算Rs值（虚部过零点优先）...")

            # 方法1: 虚部过零点方法（优先使用，适用于低阻抗电池）
            rs_from_zero_crossing = self._find_imaginary_zero_crossing(real_parts, imag_parts)

            if rs_from_zero_crossing is not None and 0.01 <= rs_from_zero_crossing <= 50.0:
                self.logger.info(f"通过虚部过零点计算Rs: {rs_from_zero_crossing:.3f}mΩ")
                return rs_from_zero_crossing

            # 方法2: 最高频点方法（备用方法）
            rs_from_high_freq = self._approximate_rs_from_high_frequency(frequencies, real_parts, imag_parts)
            self.logger.info(f"通过最高频点计算Rs: {rs_from_high_freq:.3f}mΩ")

            # 验证最高频点方法的结果是否合理
            if 0.01 <= rs_from_high_freq <= 50.0:  # 放宽Rs值范围，支持低阻抗电池
                return rs_from_high_freq

            # 方法3: 高频段线性拟合延长线（最后方法）
            rs_from_extrapolation = self._extrapolate_high_frequency_rs(frequencies, real_parts, imag_parts)

            if rs_from_extrapolation is not None and 0.01 <= rs_from_extrapolation <= 50.0:
                self.logger.info(f"通过高频段拟合延长线计算Rs: {rs_from_extrapolation:.3f}mΩ")
                return rs_from_extrapolation

            # 如果虚部过零点方法有结果，即使超出范围也使用
            if rs_from_zero_crossing is not None:
                self.logger.info(f"使用虚部过零点结果（超出范围）: {rs_from_zero_crossing:.3f}mΩ")
                # 重要修复确保Rs值为正数
                rs_corrected = max(0.01, abs(rs_from_zero_crossing))
                if rs_from_zero_crossing < 0:
                    self.logger.warning(f"⚠️ Rs值为负数({rs_from_zero_crossing:.3f}mΩ)，修正为正数: {rs_corrected:.3f}mΩ")
                return rs_corrected

            # 最后使用最高频点结果
            self.logger.warning(f"使用最高频点结果: {rs_from_high_freq:.3f}mΩ")
            # 重要修复确保Rs值为正数
            rs_corrected = max(0.01, abs(rs_from_high_freq))
            if rs_from_high_freq < 0:
                self.logger.warning(f"⚠️ Rs值为负数({rs_from_high_freq:.3f}mΩ)，修正为正数: {rs_corrected:.3f}mΩ")
            return rs_corrected

        except Exception as e:
            self.logger.error(f"计算Rs值失败: {e}")
            return 0.2  # 默认值改为0.2mΩ，适用于低阻抗电池

    def _find_imaginary_zero_crossing(self, real_parts: np.ndarray,
                                     imag_parts: np.ndarray) -> Optional[float]:
        """
        寻找虚部过零点对应的实部值（修复版本）

        修复说明：
        1. 优先寻找虚部符号变化的过零点（线性插值）
        2. 如果有多个过零点，选择最小的实部值（对应高频）
        3. 避免使用低频区域的"最小虚部值"作为过零点

        Args:
            real_parts: 实部数组
            imag_parts: 虚部数组

        Returns:
            Rs值或None
        """
        try:
            # 安全检查：确保数组不为空且长度一致
            if len(real_parts) == 0 or len(imag_parts) == 0:
                self.logger.warning("输入数组为空")
                return None

            if len(real_parts) != len(imag_parts):
                self.logger.warning("实部和虚部数组长度不一致")
                min_len = min(len(real_parts), len(imag_parts))
                real_parts = real_parts[:min_len]
                imag_parts = imag_parts[:min_len]

            if len(imag_parts) < 2:
                self.logger.warning("数据点太少，无法寻找过零点")
                return None

            # 检查数据有效性
            if not np.all(np.isfinite(real_parts)) or not np.all(np.isfinite(imag_parts)):
                self.logger.warning("数据包含无效值(NaN或Inf)")
                return None

            self.logger.debug(f"虚部数据范围: {imag_parts.min():.3f} 到 {imag_parts.max():.3f} mΩ")

            # 方法1: 寻找虚部符号变化的点（优先方法）
            imag_signs = np.sign(imag_parts)
            sign_diffs = np.diff(imag_signs)
            sign_changes = np.where(sign_diffs != 0)[0]

            # 找到所有过零点
            zero_crossings = []
            for i in sign_changes:
                if i + 1 < len(imag_parts):
                    # 线性插值找到精确的过零点
                    y1, y2 = imag_parts[i], imag_parts[i + 1]
                    x1, x2 = real_parts[i], real_parts[i + 1]

                    # 更严格的除零检查
                    if abs(y2 - y1) > 1e-10:  # 避免除零
                        # 线性插值计算过零点的实部值
                        x_zero = x1 - y1 * (x2 - x1) / (y2 - y1)

                        # 检查计算结果的有效性
                        if np.isfinite(x_zero) and 0.01 <= x_zero <= 1000.0:
                            zero_crossings.append(x_zero)
                            self.logger.debug(f"找到过零点: 实部={x_zero:.3f}mΩ")

            if zero_crossings:
                # 选择最小的实部值作为Rs（通常对应高频）
                rs_value = min(zero_crossings)
                self.logger.info(f"通过符号变化找到Rs: {rs_value:.3f}mΩ")
                # 重要修复确保Rs值为正数
                if rs_value < 0:
                    self.logger.warning(f"⚠️ 过零点Rs值为负数({rs_value:.3f}mΩ)，修正为正数")
                    rs_value = abs(rs_value)
                return max(0.001, min(100.0, rs_value))  # Jack算法修正允许小Rs值

            # 方法2: 如果没有符号变化，寻找最接近零的虚部值（但要谨慎）
            abs_imag = np.abs(imag_parts)
            min_abs_idx = np.argmin(abs_imag)
            min_abs_value = abs_imag[min_abs_idx]

            self.logger.debug(f"最接近零的虚部值: {imag_parts[min_abs_idx]:.3f}mΩ (索引{min_abs_idx})")

            # 只有当虚部值非常接近零时才使用（更严格的条件）
            if min_abs_value < 0.1:  # 虚部绝对值小于0.1mΩ认为接近零
                rs_value = real_parts[min_abs_idx]
                self.logger.info(f"通过最小虚部值找到Rs: {rs_value:.3f}mΩ (虚部={imag_parts[min_abs_idx]:.3f}mΩ)")
                # 重要修复确保Rs值为正数
                if rs_value < 0:
                    self.logger.warning(f"⚠️ 最小虚部Rs值为负数({rs_value:.3f}mΩ)，修正为正数")
                    rs_value = abs(rs_value)
                return max(0.001, min(100.0, rs_value))  # Jack算法修正允许小Rs值

            # 如果都没找到合适的过零点，返回None让其他方法处理
            self.logger.debug("未找到合适的虚部过零点")
            return None

        except Exception as e:
            self.logger.error(f"寻找虚部过零点失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            return None

    def _extrapolate_high_frequency_rs(self, frequencies: np.ndarray,
                                      real_parts: np.ndarray,
                                      imag_parts: np.ndarray) -> Optional[float]:
        """
        通过高频段线性拟合延长线计算Rs

        Args:
            frequencies: 频率数组
            real_parts: 实部数组
            imag_parts: 虚部数组

        Returns:
            Rs值或None
        """
        try:
            # 选择高频段数据（频率最高的30%数据点）
            n_points = len(frequencies)
            high_freq_count = max(3, n_points // 3)  # 至少3个点

            # 按频率排序，选择最高频率的数据点
            freq_indices = np.argsort(frequencies)[-high_freq_count:]

            high_freq_real = real_parts[freq_indices]
            high_freq_imag = imag_parts[freq_indices]

            self.logger.debug(f"选择{high_freq_count}个高频点进行线性拟合")

            # 对高频段的奈奎斯特图进行线性拟合
            # 拟合 imag = k * real + b
            if len(high_freq_real) >= 2:
                # 使用最小二乘法拟合
                coeffs = np.polyfit(high_freq_real, high_freq_imag, 1)
                k, b = coeffs[0], coeffs[1]

                # 计算拟合质量
                fitted_imag = k * high_freq_real + b
                r_squared = 1 - np.sum((high_freq_imag - fitted_imag)**2) / np.sum((high_freq_imag - np.mean(high_freq_imag))**2)

                self.logger.debug(f"高频段线性拟合: k={k:.6f}, b={b:.3f}, R²={r_squared:.3f}")

                # 如果拟合质量足够好，计算与虚部=0轴的交点
                if r_squared > 0.5:  # 拟合质量阈值
                    # 求解 0 = k * rs + b，得到 rs = -b/k
                    if abs(k) > 1e-6:  # 避免除零
                        rs_value = -b / k
                        self.logger.debug(f"线性拟合延长线Rs值: {rs_value:.3f}mΩ")

                        # 验证Rs值的合理性
                        if 0.1 <= rs_value <= 100.0:
                            return rs_value
                        else:
                            self.logger.warning(f"拟合得到的Rs值不合理: {rs_value:.3f}mΩ")
                else:
                    self.logger.debug(f"高频段拟合质量不佳: R²={r_squared:.3f}")

            return None

        except Exception as e:
            self.logger.error(f"高频段线性拟合失败: {e}")
            return None

    def _approximate_rs_from_high_frequency(self, frequencies: np.ndarray,
                                           real_parts: np.ndarray,
                                           imag_parts: np.ndarray) -> float:
        """
        通过最高频点计算Rs（修复版本）

        修复说明：
        直接取最高频点的实部阻抗值作为Rs，这是标准的EIS分析方法

        Args:
            frequencies: 频率数组
            real_parts: 实部数组
            imag_parts: 虚部数组

        Returns:
            Rs值
        """
        try:
            # 找到最高频率点的索引
            max_freq_idx = np.argmax(frequencies)

            # 取最高频点的实部阻抗值作为Rs
            rs_value = float(real_parts[max_freq_idx])

            max_freq = frequencies[max_freq_idx]
            imag_at_max_freq = imag_parts[max_freq_idx]

            self.logger.debug(f"最高频点Rs计算: 频率={max_freq:.3f}Hz, Rs={rs_value:.3f}mΩ, 虚部={imag_at_max_freq:.3f}mΩ")

            # 重要修复确保Rs值为正数
            if rs_value < 0:
                self.logger.warning(f"⚠️ 最高频点Rs值为负数({rs_value:.3f}mΩ)，修正为正数")
                rs_value = abs(rs_value)

            # 确保Rs值在合理范围内
            if rs_value < 0.1:
                self.logger.warning(f"Rs值过小: {rs_value:.3f}mΩ，调整为0.1mΩ")
                return 0.1
            elif rs_value > 100.0:
                self.logger.warning(f"Rs值过大: {rs_value:.3f}mΩ，可能存在硬件问题")
                return min(100.0, rs_value)
            else:
                return rs_value

        except Exception as e:
            self.logger.error(f"最高频点Rs计算失败: {e}")
            return 5.0





    def _calculate_rsei_rct_from_valleys(self, frequencies: np.ndarray, real_parts: np.ndarray,
                                       imag_parts: np.ndarray, rs_value: float) -> Tuple[float, float]:
        """
        使用标准谷点分析方法计算Rsei和Rct

        标准算法：
        1. 按频率从低到高排序
        2. 寻找虚部的局部最低点（谷点）
        3. 第一个谷点（低频）：代表 Rct + Rsei
        4. 第二个谷点（高频）：代表 Rsei
        5. 计算：Rct = (Rct + Rsei) - Rsei

        Args:
            frequencies: 频率数组
            real_parts: 实部数组
            imag_parts: 虚部数组
            rs_value: Rs值

        Returns:
            (Rsei值, Rct值) 单位：mΩ
        """
        try:
            self.logger.debug("开始标准谷点分析...")

            # 按频率从低到高排序
            freq_sorted_indices = np.argsort(frequencies)
            sorted_frequencies = frequencies[freq_sorted_indices]
            sorted_real_parts = real_parts[freq_sorted_indices]
            sorted_imag_parts = imag_parts[freq_sorted_indices]

            # 寻找谷点
            valleys = self._find_valleys_in_imaginary_parts(
                sorted_frequencies, sorted_real_parts, sorted_imag_parts
            )

            if len(valleys) >= 2:
                # 双谷点方法
                first_valley = valleys[0]  # 低频谷点：Rct + Rsei
                second_valley = valleys[1]  # 高频谷点：Rsei

                rct_plus_rsei = first_valley['real'] - rs_value
                rsei_value = second_valley['real'] - rs_value
                rct_value = rct_plus_rsei - rsei_value

                self.logger.debug(f"双谷点分析:")
                self.logger.debug(f"  第一个谷点（Rct+Rsei）: {first_valley['real']:.3f} - {rs_value:.3f} = {rct_plus_rsei:.3f}mΩ")
                self.logger.debug(f"  第二个谷点（Rsei）: {second_valley['real']:.3f} - {rs_value:.3f} = {rsei_value:.3f}mΩ")
                self.logger.debug(f"  Rct = {rct_plus_rsei:.3f} - {rsei_value:.3f} = {rct_value:.3f}mΩ")

                return max(0.0, rsei_value), max(0.0, rct_value)

            elif len(valleys) == 1:
                # 单谷点方法
                valley = valleys[0]
                total_resistance = valley['real'] - rs_value
                rsei_value = 0.1  # 假设SEI阻抗很小
                rct_value = total_resistance - rsei_value

                self.logger.debug(f"单谷点分析: 假设Rsei={rsei_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")
                return rsei_value, max(0.0, rct_value)

            else:
                self.logger.warning("未找到谷点，使用默认分配")
                # 使用最低频点作为总阻抗，假设主要是Rct
                min_freq_idx = np.argmin(frequencies)
                total_resistance = real_parts[min_freq_idx] - rs_value
                rsei_value = 0.1
                rct_value = total_resistance - rsei_value

                return max(0.0, rsei_value), max(0.0, rct_value)

        except Exception as e:
            self.logger.error(f"谷点分析失败: {e}")
            return 0.1, 0.5

    def _find_valleys_in_imaginary_parts(self, sorted_frequencies: np.ndarray,
                                        sorted_real_parts: np.ndarray,
                                        sorted_imag_parts: np.ndarray) -> List[dict]:
        """
        在虚部数据中寻找谷点（局部最低点）

        Args:
            sorted_frequencies: 按频率排序的频率数组
            sorted_real_parts: 按频率排序的实部数组
            sorted_imag_parts: 按频率排序的虚部数组

        Returns:
            谷点信息列表，每个包含频率、实部、虚部
        """
        try:
            valleys = []

            # 从第二个点开始检查（需要前后对比）
            for i in range(1, len(sorted_imag_parts) - 1):
                prev_imag = sorted_imag_parts[i-1]
                curr_imag = sorted_imag_parts[i]
                next_imag = sorted_imag_parts[i+1]

                # 检查是否为局部最低点：前面的值 > 当前值 < 后面的值
                if prev_imag > curr_imag and curr_imag < next_imag:
                    valley_info = {
                        'frequency': sorted_frequencies[i],
                        'real': sorted_real_parts[i],
                        'imag': curr_imag
                    }
                    valleys.append(valley_info)
                    self.logger.debug(f"找到谷点{len(valleys)}: 频率={sorted_frequencies[i]:.3f}Hz, "
                                    f"实部={sorted_real_parts[i]:.3f}mΩ, 虚部={curr_imag:.3f}mΩ")

            self.logger.debug(f"总共找到 {len(valleys)} 个谷点")
            return valleys

        except Exception as e:
            self.logger.error(f"寻找谷点失败: {e}")
            return []

    def _analyze_with_dual_model(self, frequencies: np.ndarray, real_parts: np.ndarray,
                                imag_parts: np.ndarray, rs_value: float) -> Dict:
        """
        双模型EIS分析

        Args:
            frequencies: 频率数组
            real_parts: 实部数组
            imag_parts: 虚部数组
            rs_value: Rs值

        Returns:
            分析结果字典，包含模型类型和各组分值
        """
        try:
            self.logger.debug("开始双模型EIS分析...")

            # 1. 模型检测：判断是新电池还是旧电池
            battery_model = self._detect_battery_model(frequencies, real_parts, imag_parts, rs_value)

            # 2. 根据模型选择相应的计算方法
            if battery_model == "新电池":
                result = self._analyze_new_battery_model(frequencies, real_parts, imag_parts, rs_value)
            else:
                result = self._analyze_old_battery_model(frequencies, real_parts, imag_parts, rs_value)

            result['battery_model'] = battery_model

            self.logger.info(f"双模型分析完成: 模型={battery_model}")
            return result

        except Exception as e:
            self.logger.error(f"双模型分析失败: {e}")
            # 返回默认结果
            return {
                'battery_model': '新电池',
                'Rs': rs_value,
                'Rct': 0.5,
                'W_real': 0.0,
                'W_imag': 0.0
            }

    def _detect_battery_model(self, frequencies: np.ndarray, real_parts: np.ndarray,
                            imag_parts: np.ndarray, rs_value: float) -> str:
        """
        检测电池模型：新电池 vs 旧电池

        判断依据：
        1. 谷点数量：2个或以上谷点 → 检查SEI阻抗大小
        2. 谷点数量：1个或0个谷点 → 检查总阻抗大小
        3. SEI阻抗大小：Rsei > 0.5mΩ → 旧电池

        Args:
            frequencies: 频率数组
            real_parts: 实部数组
            imag_parts: 虚部数组
            rs_value: Rs值

        Returns:
            电池模型类型：'新电池' 或 '旧电池'
        """
        try:
            self.logger.debug("开始电池模型检测...")

            # 按频率从低到高排序
            freq_sorted_indices = np.argsort(frequencies)
            sorted_frequencies = frequencies[freq_sorted_indices]
            sorted_real_parts = real_parts[freq_sorted_indices]
            sorted_imag_parts = imag_parts[freq_sorted_indices]

            # 寻找谷点
            valleys = self._find_valleys_in_imaginary_parts(
                sorted_frequencies, sorted_real_parts, sorted_imag_parts
            )

            valley_count = len(valleys)
            self.logger.debug(f"检测到 {valley_count} 个谷点")

            # 判断逻辑
            if valley_count >= 2:
                # 检查第二个谷点是否表示明显的Rsei
                first_valley = valleys[0]
                second_valley = valleys[1]

                rct_plus_rsei = first_valley['real'] - rs_value
                potential_rsei = second_valley['real'] - rs_value

                self.logger.debug(f"第一个谷点阻抗: {rct_plus_rsei:.3f}mΩ")
                self.logger.debug(f"第二个谷点阻抗: {potential_rsei:.3f}mΩ")

                # 如果第二个谷点对应的Rsei > 0.5mΩ，认为是旧电池
                if potential_rsei > 0.5:
                    self.logger.info("判断为旧电池：存在明显的SEI膜阻抗")
                    return "旧电池"
                else:
                    self.logger.info("判断为新电池：SEI膜阻抗很小")
                    return "新电池"

            elif valley_count == 1:
                # 单谷点，检查总阻抗大小
                valley = valleys[0]
                total_resistance = valley['real'] - rs_value

                self.logger.debug(f"单谷点总阻抗: {total_resistance:.3f}mΩ")

                # 如果总阻抗很大（>5mΩ），可能是旧电池但SEI和Rct重叠
                if total_resistance > 5.0:
                    self.logger.info("判断为旧电池：总阻抗较大，可能SEI和Rct重叠")
                    return "旧电池"
                else:
                    self.logger.info("判断为新电池：总阻抗适中")
                    return "新电池"

            else:
                self.logger.info("判断为新电池：未检测到明显谷点")
                return "新电池"

        except Exception as e:
            self.logger.error(f"模型检测失败: {e}")
            return "新电池"  # 默认为新电池模型

    def _analyze_new_battery_model(self, frequencies: np.ndarray, real_parts: np.ndarray,
                                 imag_parts: np.ndarray, rs_value: float) -> Dict:
        """
        新电池模型分析：Rs + Rct + W

        Args:
            frequencies: 频率数组
            real_parts: 实部数组
            imag_parts: 虚部数组
            rs_value: Rs值

        Returns:
            分析结果字典
        """
        try:
            self.logger.debug("开始新电池模型分析...")

            # 对于新电池，使用简化的单半圆模型
            # 找到第一个谷点或使用最低频点
            freq_sorted_indices = np.argsort(frequencies)
            sorted_frequencies = frequencies[freq_sorted_indices]
            sorted_real_parts = real_parts[freq_sorted_indices]
            sorted_imag_parts = imag_parts[freq_sorted_indices]

            valleys = self._find_valleys_in_imaginary_parts(
                sorted_frequencies, sorted_real_parts, sorted_imag_parts
            )

            if valleys:
                # 使用第一个谷点计算Rct
                first_valley = valleys[0]
                rct_value = first_valley['real'] - rs_value
                self.logger.debug(f"通过谷点计算Rct: {first_valley['real']:.3f} - {rs_value:.3f} = {rct_value:.3f}mΩ")
            else:
                # 没有谷点，使用Jack的标准方法：总阻抗减法
                min_freq_idx = np.argmin(frequencies)
                total_resistance = real_parts[min_freq_idx]
                rct_value = total_resistance - rs_value  # Jack的标准方法：Rct = 总阻抗 - Rs
                self.logger.debug(f"通过Jack标准方法计算Rct: {total_resistance:.3f} - {rs_value:.3f} = {rct_value:.3f}mΩ")

            rct_value = max(0.001, rct_value)  # Jack算法修正允许小Rct值

            # 计算W阻抗
            w_real, w_imag, w_magnitude, w_phase = self._calculate_w_impedance_internal(
                frequencies, real_parts, imag_parts, rs_value, 0.0, rct_value
            )

            return {
                'Rs': rs_value,
                'Rct': rct_value,
                'W_real': w_real,
                'W_imag': w_imag,
                'W_magnitude': w_magnitude,
                'W_phase': w_phase,
                'total_real': rs_value + rct_value + w_real
            }

        except Exception as e:
            self.logger.error(f"新电池模型分析失败: {e}")
            return {'Rs': rs_value, 'Rct': 0.5, 'W_real': 0.0, 'W_imag': 0.0, 'W_magnitude': 0.0, 'W_phase': 0.0}

    def _analyze_old_battery_model(self, frequencies: np.ndarray, real_parts: np.ndarray,
                                 imag_parts: np.ndarray, rs_value: float) -> Dict:
        """
        旧电池模型分析：Rs + Rsei + Rct + W

        Args:
            frequencies: 频率数组
            real_parts: 实部数组
            imag_parts: 虚部数组
            rs_value: Rs值

        Returns:
            分析结果字典
        """
        try:
            self.logger.debug("开始旧电池模型分析...")

            # 使用双谷点方法
            freq_sorted_indices = np.argsort(frequencies)
            sorted_frequencies = frequencies[freq_sorted_indices]
            sorted_real_parts = real_parts[freq_sorted_indices]
            sorted_imag_parts = imag_parts[freq_sorted_indices]

            valleys = self._find_valleys_in_imaginary_parts(
                sorted_frequencies, sorted_real_parts, sorted_imag_parts
            )

            if len(valleys) >= 2:
                # 双谷点方法 - 修复计算逻辑
                first_valley = valleys[0]  # 低频谷点：Rct + Rsei
                second_valley = valleys[1]  # 高频谷点：Rsei

                rct_plus_rsei = first_valley['real'] - rs_value
                rsei_value = second_valley['real'] - rs_value
                rct_value_dual = rct_plus_rsei - rsei_value

                self.logger.debug(f"双谷点分析:")
                self.logger.debug(f"  第一个谷点（Rct+Rsei）: {rct_plus_rsei:.3f}mΩ")
                self.logger.debug(f"  第二个谷点（Rsei）: {rsei_value:.3f}mΩ")
                self.logger.debug(f"  双谷点Rct = {rct_value_dual:.3f}mΩ")

                # 使用Jack的标准方法作为验证
                min_freq_idx = np.argmin(frequencies)
                total_resistance = real_parts[min_freq_idx]
                rct_standard = total_resistance - rs_value
                self.logger.debug(f"  Jack标准方法Rct = {rct_standard:.3f}mΩ")

                # 选择更合理的结果
                if 0.1 <= rct_value_dual <= 50.0 and abs(rct_value_dual - rct_standard) / max(rct_value_dual, rct_standard) < 0.8:
                    # 双谷点结果合理且与标准方法接近
                    rct_value = rct_value_dual
                    rsei_value = max(0.1, rsei_value)
                    self.logger.debug(f"  使用双谷点结果: Rct={rct_value:.3f}mΩ, Rsei={rsei_value:.3f}mΩ")
                else:
                    # 双谷点结果异常，使用标准方法
                    rct_value = rct_standard
                    rsei_value = 0.0  # 不分离Rsei
                    self.logger.debug(f"  双谷点结果异常，使用标准方法: Rct={rct_value:.3f}mΩ")

                rct_value = max(0.1, min(100.0, rct_value))

            else:
                # 单谷点或无谷点，使用Jack的标准方法
                min_freq_idx = np.argmin(frequencies)
                total_resistance = real_parts[min_freq_idx] - rs_value

                # Jack的标准方法：不分离Rsei，Rct包含所有极化阻抗
                rsei_value = 0.0  # 不再单独计算Rsei
                rct_value = total_resistance  # 所有极化阻抗都归为Rct

                self.logger.debug(f"单谷点/标准方法: 总阻抗={total_resistance:.3f}mΩ")
                self.logger.debug(f"  Rsei={rsei_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")

                # 确保Rct值在合理范围内
                rct_value = max(0.01, min(100.0, rct_value))

            # 计算W阻抗
            w_real, w_imag, w_magnitude, w_phase = self._calculate_w_impedance_internal(
                frequencies, real_parts, imag_parts, rs_value, rsei_value, rct_value
            )

            return {
                'Rs': rs_value,
                'Rsei': rsei_value,
                'Rct': rct_value,
                'W_real': w_real,
                'W_imag': w_imag,
                'W_magnitude': w_magnitude,
                'W_phase': w_phase,
                'total_real': rs_value + rsei_value + rct_value + w_real
            }

        except Exception as e:
            self.logger.error(f"旧电池模型分析失败: {e}")
            return {'Rs': rs_value, 'Rsei': 1.0, 'Rct': 0.5, 'W_real': 0.0, 'W_imag': 0.0, 'W_magnitude': 0.0, 'W_phase': 0.0}

    def _calculate_w_impedance_internal(self, frequencies: np.ndarray, real_parts: np.ndarray,
                                      imag_parts: np.ndarray, rs_value: float,
                                      rsei_value: float, rct_value: float) -> Tuple[float, float, float, float]:
        """
        内部W阻抗计算方法

        W = 最低频点阻抗 - Rs - Rsei - Rct

        Args:
            frequencies: 频率数组
            real_parts: 实部数组
            imag_parts: 虚部数组
            rs_value: Rs值
            rsei_value: Rsei值
            rct_value: Rct值

        Returns:
            (W_real, W_imag, W_magnitude, W_phase)
        """
        try:
            # 获取最低频点的阻抗
            min_freq_idx = np.argmin(frequencies)
            min_freq_real = real_parts[min_freq_idx]
            min_freq_imag = imag_parts[min_freq_idx]
            min_freq = frequencies[min_freq_idx]

            self.logger.debug(f"最低频点: 频率={min_freq:.3f}Hz, 实部={min_freq_real:.3f}mΩ, 虚部={min_freq_imag:.3f}mΩ")

            # 计算W阻抗
            w_real = min_freq_real - rs_value - rsei_value - rct_value
            w_imag = min_freq_imag

            w_magnitude = math.sqrt(w_real**2 + w_imag**2)
            if w_real != 0:
                w_phase = math.degrees(math.atan2(w_imag, w_real))
            else:
                w_phase = 90.0 if w_imag > 0 else -90.0

            self.logger.debug(f"W阻抗: {w_real:.3f} + {w_imag:.3f}j mΩ, 幅值={w_magnitude:.3f}mΩ, 相位={w_phase:.1f}°")

            return w_real, w_imag, w_magnitude, w_phase

        except Exception as e:
            self.logger.error(f"W阻抗计算失败: {e}")
            return 0.0, 0.0, 0.0, 0.0

    def validate_eis_data(self, frequencies: List[float],
                         real_parts: List[float],
                         imag_parts: List[float]) -> Dict:
        """
        验证EIS数据质量

        Args:
            frequencies: 频率列表
            real_parts: 实部列表
            imag_parts: 虚部列表

        Returns:
            验证结果字典
        """
        try:
            validation_result = {
                'is_valid': True,
                'warnings': [],
                'data_quality': 'good',
                'frequency_range': 'adequate',
                'data_points': len(frequencies)
            }

            # 检查数据点数量
            if len(frequencies) < 3:
                validation_result['warnings'].append("数据点数量过少，可能影响分析精度")
                validation_result['data_quality'] = 'poor'

            # 检查频率范围
            if len(frequencies) > 0:
                freq_range = max(frequencies) / min(frequencies) if min(frequencies) > 0 else 1
                if freq_range < 10:
                    validation_result['warnings'].append("频率范围过窄，建议扩大频率范围")
                    validation_result['frequency_range'] = 'narrow'

            # 检查数据连续性
            unique_real_ratio = len(set(real_parts)) / len(real_parts) if len(real_parts) > 0 else 0
            unique_imag_ratio = len(set(imag_parts)) / len(imag_parts) if len(imag_parts) > 0 else 0

            if unique_real_ratio < 0.8:
                validation_result['warnings'].append("实部数据重复过多")
                validation_result['data_quality'] = 'poor'

            if unique_imag_ratio < 0.8:
                validation_result['warnings'].append("虚部数据重复过多")
                validation_result['data_quality'] = 'poor'

            # 如果数据重复严重，标记为无效
            if unique_real_ratio < 0.3 and unique_imag_ratio < 0.3:
                validation_result['is_valid'] = False
                validation_result['warnings'].append("数据重复过于严重，无法进行有效分析")

            # 检查数据合理性
            if any(r < 0 for r in real_parts):
                validation_result['warnings'].append("存在负实部值，数据可能异常")
                validation_result['is_valid'] = False

            self.logger.debug(f"EIS数据验证完成: {validation_result}")
            return validation_result

        except Exception as e:
            self.logger.error(f"EIS数据验证失败: {e}")
            return {
                'is_valid': False,
                'warnings': [f"验证过程出错: {str(e)}"],
                'data_quality': 'error',
                'frequency_range': 'unknown',
                'data_points': 0
            }

    def calculate_rs_rct_enhanced(self, frequencies: List[float],
                                 real_parts: List[float],
                                 imag_parts: List[float],
                                 cell_id: str = "Unknown") -> Dict:
        """
        Jack的Nyquist曲线分析方法，计算Rs和Rct（统一使用2×峰值法）

        Args:
            frequencies: 频率列表 (Hz)
            real_parts: 实部阻抗列表 (mΩ)
            imag_parts: 虚部阻抗列表 (mΩ)
            cell_id: 电芯ID

        Returns:
            Dict: 包含所有EIS参数的分析结果
        """
        try:
            self.logger.info(f"开始Jack的Nyquist分析（2×峰值法）: {cell_id}")

            # 数据验证
            if len(frequencies) == 0 or len(real_parts) == 0 or len(imag_parts) == 0:
                raise ValueError("输入数据为空")

            if len(frequencies) != len(real_parts) or len(frequencies) != len(imag_parts):
                raise ValueError("频率、实部、虚部数据长度不一致")

            # 转换为numpy数组
            freq_array = np.array(frequencies, dtype=float)
            real_array = np.array(real_parts, dtype=float)
            imag_array = np.array(imag_parts, dtype=float)

            # 检测单频点测试
            if self._is_single_frequency_test(freq_array):
                self.logger.info(f"检测到单频点测试: {frequencies[0]:.1f}Hz")
                return self._handle_single_frequency_test(freq_array, real_array, imag_array)

            # 数据质量检查
            if len(freq_array) < 3:
                raise ValueError("数据点数量不足，无法进行EIS分析")

            # 初始化结果
            results = {
                'analysis_success': True,
                'cell_id': cell_id,
                'data_points': len(freq_array),
                'frequency_range': [freq_array.min(), freq_array.max()],
            }

            # 1) Rs：采用虚部过零点插值
            rs_value = self._calculate_rs_zero_crossing(freq_array, real_array, imag_array)
            results['rs_value'] = rs_value

            # 2) Rct：统一使用2×正虚部峰值法（与图表显示一致）
            rct_value = self._calculate_rct_peak_method(freq_array, imag_array)
            
            results.update({
                'rs_value': float(rs_value),
                'rct_value': float(rct_value),
                'rsei_value': 0.0,
                'w_impedance': 0.0,
                'analysis_method': 'positive_peak_method_unified',
            })

            # 相位角参数维持原有计算
            phase_result = self._calculate_phase_enhanced(freq_array, real_array, imag_array)
            results.update(phase_result)

            self.logger.info(f"2×峰值法完成: Rs={results.get('rs_value', rs_value):.3f}mΩ, "
                             f"Rct={results.get('rct_value', 0.0):.3f}mΩ")
            return results

        except Exception as e:
            self.logger.error(f"增强版EIS分析失败: {e}")
            return {
                'analysis_success': False,
                'error': str(e),
                'analysis_method': 'enhanced_failed'
            }


    def _calculate_rs_zero_crossing(self, frequencies: np.ndarray,
                                   real_parts: np.ndarray,
                                   imag_parts: np.ndarray) -> float:
        """
        Jack的Rs计算方法：虚部过零点
        """
        try:
            # 寻找虚部符号变化点
            for i in range(len(imag_parts) - 1):
                if imag_parts[i] * imag_parts[i + 1] <= 0:  # 符号变化
                    # 线性插值获得精确的过零点
                    y1, y2 = imag_parts[i], imag_parts[i + 1]
                    x1, x2 = real_parts[i], real_parts[i + 1]

                    if y2 != y1:  # 避免除零
                        rs_zero = x1 - y1 * (x2 - x1) / (y2 - y1)
                        self.logger.debug(f"虚部过零点Rs: {rs_zero:.3f}mΩ")
                        return rs_zero
                    else:
                        return x1

            # 如果没找到过零点，使用最小实部
            rs_min = np.min(real_parts)
            self.logger.debug(f"未找到过零点，使用最小实部Rs: {rs_min:.3f}mΩ")
            return rs_min

        except Exception as e:
            self.logger.warning(f"Rs计算失败，使用最小实部: {e}")
            return np.min(real_parts)

    def _calculate_rct_peak_method(self, frequencies: np.ndarray, imag_parts: np.ndarray) -> float:
        """
        统一的Rct计算方法：2×正虚部峰值法（与图表显示一致）

        只考虑正虚部且频率≥1Hz的数据，避免感性效应和扩散阻抗的干扰

        Args:
            frequencies: 频率数组 (Hz)
            imag_parts: 虚部阻抗数组 (mΩ)

        Returns:
            Rct值 (mΩ)
        """
        try:
            # 筛选条件：正虚部且频率≥1Hz（与图表算法一致）
            f_min = 1.0
            pos_mask = (imag_parts >= 0) & (frequencies >= f_min)

            if np.any(pos_mask):
                # 在筛选后的数据中找正虚部峰值
                pos_imag = imag_parts[pos_mask]
                pos_freq = frequencies[pos_mask]

                peak_imag = float(np.max(pos_imag))
                peak_idx = np.argmax(pos_imag)
                peak_freq = float(pos_freq[peak_idx])

                # Rct = 2×正虚部峰值（与图表显示一致）
                rct_value = 2.0 * peak_imag

                # 确保Rct值为正且合理
                rct_value = max(0.001, rct_value)

                self.logger.debug(f"2×正虚部峰值法计算Rct: 峰值={peak_imag:.3f}mΩ@{peak_freq:.1f}Hz, Rct={rct_value:.3f}mΩ")

                return rct_value
            else:
                # 回退到传统方法（如果没有满足条件的数据）
                self.logger.warning("没有满足条件的数据点（正虚部且频率≥1Hz），使用传统2×绝对值峰值法")
                imag_abs_peak = float(np.max(np.abs(imag_parts)))
                rct_value = 2.0 * imag_abs_peak
                rct_value = max(0.001, rct_value)

                self.logger.debug(f"回退算法计算Rct: 绝对值峰值={imag_abs_peak:.3f}mΩ, Rct={rct_value:.3f}mΩ")

                return rct_value

        except Exception as e:
            self.logger.warning(f"2×正虚部峰值法计算失败: {e}")
            # 最终回退到最小值
            return 0.001

    def _is_single_frequency_test(self, frequencies: np.ndarray) -> bool:
        """
        检测是否为单频点测试

        Args:
            frequencies: 频率数组

        Returns:
            bool: 是否为单频点测试
        """
        is_single = len(frequencies) == 1
        if is_single:
            self.logger.info(f"🔍 [SINGLE_FREQ_DEBUG] EIS分析器检测到单频点测试: {frequencies[0]}Hz")
        return is_single

    def _handle_single_frequency_test(self, frequencies: np.ndarray,
                                     real_parts: np.ndarray,
                                     imag_parts: np.ndarray) -> Dict:
        """
        处理单频点测试的特殊逻辑

        单频点测试时：
        - Rs = 实部值（阻抗的实部分量）
        - Rct = 0（单频点无法计算电荷转移阻抗）
        - 其他参数设为0

        Args:
            frequencies: 频率数组（长度为1）
            real_parts: 实部阻抗数组（长度为1）
            imag_parts: 虚部阻抗数组（长度为1）

        Returns:
            Dict: 单频点测试结果
        """
        try:
            frequency = float(frequencies[0])
            rs_value = float(real_parts[0])
            imag_value = float(imag_parts[0])

            self.logger.info(f"单频点测试处理: {frequency:.1f}Hz, Rs={rs_value:.3f}mΩ, 虚部={imag_value:.3f}mΩ")

            # 🔍 [SINGLE_FREQ_DEBUG] 单频点处理详细调试
            self.logger.info(f"🔍 [SINGLE_FREQ_DEBUG] 单频点EIS处理开始:")
            self.logger.info(f"🔍 [SINGLE_FREQ_DEBUG]   输入频率: {frequency}Hz")
            self.logger.info(f"🔍 [SINGLE_FREQ_DEBUG]   输入实部: {rs_value}mΩ")
            self.logger.info(f"🔍 [SINGLE_FREQ_DEBUG]   输入虚部: {imag_value}mΩ")

            # 单频点测试结果
            result = {
                'rs_value': rs_value,
                'rct_value': 0.0,  # 单频点无法计算Rct
                'rsei_value': 0.0,
                'w_impedance': 0.0,
                'analysis_method': 'single_frequency_mode',
                'analysis_success': True,  # 添加分析成功标志
                'frequency': frequency,
                'impedance_real': rs_value,
                'impedance_imag': imag_value,
                'impedance_magnitude': (rs_value**2 + imag_value**2)**0.5,
                'phase_angle': np.degrees(np.arctan2(imag_value, rs_value)),
                'success': True,
                'message': f'单频点测试完成: {frequency:.1f}Hz'
            }

            self.logger.info(f"单频点测试结果: Rs={rs_value:.3f}mΩ, Rct=0.000mΩ (单频点)")

            # 🔍 [SINGLE_FREQ_DEBUG] 单频点结果调试
            self.logger.info(f"🔍 [SINGLE_FREQ_DEBUG] 单频点EIS处理完成:")
            self.logger.info(f"🔍 [SINGLE_FREQ_DEBUG]   Rs值: {rs_value}mΩ")
            self.logger.info(f"🔍 [SINGLE_FREQ_DEBUG]   Rct值: 0.0mΩ")
            self.logger.info(f"🔍 [SINGLE_FREQ_DEBUG]   分析方法: single_frequency_mode")
            self.logger.info(f"🔍 [SINGLE_FREQ_DEBUG]   分析成功: True")

            return result

        except Exception as e:
            self.logger.error(f"单频点测试处理失败: {e}")
            # 返回错误结果
            return {
                'rs_value': 0.001,
                'rct_value': 0.0,
                'rsei_value': 0.0,
                'w_impedance': 0.0,
                'analysis_method': 'single_frequency_error',
                'analysis_success': False,  # 添加分析失败标志
                'success': False,
                'message': f'单频点测试处理失败: {e}'
            }

    def _calculate_rct_jack_method(self, frequencies: np.ndarray,
                                  real_parts: np.ndarray,
                                  imag_parts: np.ndarray,
                                  rs_value: float) -> tuple:
        """
        Jack的Rct计算方法：基于Nyquist曲线拐点分析

        Returns:
            tuple: (rct_value, w_impedance)
        """
        try:
            # 总阻抗 = 最大实部 (通常在最低频)
            total_impedance = np.max(real_parts)

            # 寻找低频(<5Hz)拐点
            inflection_point = self._find_jack_inflection_point(frequencies, real_parts, imag_parts, rs_value)

            if inflection_point:
                inflection_freq, inflection_real, inflection_imag = inflection_point

                # Rct = 拐点实部 - Rs (总极化阻抗，包含原Rsei+Rct)
                rct_value = inflection_real - rs_value

                # W阻抗 = 总阻抗 - 拐点实部
                w_impedance = total_impedance - inflection_real

                self.logger.debug(f"拐点分析: 频率={inflection_freq:.3f}Hz, 实部={inflection_real:.3f}mΩ")
                self.logger.debug(f"Rct={rct_value:.3f}mΩ, W阻抗={w_impedance:.3f}mΩ")

                return max(0.0, rct_value), max(0.0, w_impedance)
            else:
                # 回退方法：使用简单的阻抗范围
                rct_value = total_impedance - rs_value
                w_impedance = 0.0

                self.logger.debug(f"未找到拐点，使用简单方法: Rct={rct_value:.3f}mΩ")
                return max(0.0, rct_value), w_impedance

        except Exception as e:
            self.logger.warning(f"Rct计算失败: {e}")
            total_impedance = np.max(real_parts)
            rct_value = total_impedance - rs_value
            return max(0.0, rct_value), 0.0

    def _find_jack_inflection_point(self, frequencies: np.ndarray,
                                   real_parts: np.ndarray,
                                   imag_parts: np.ndarray,
                                   rs_value: float) -> tuple:
        """
        Jack的拐点查找方法：低频(<5Hz)虚部最低点，且实部 > Rs

        Returns:
            tuple: (frequency, real_part, imag_part) or None
        """
        try:
            # 筛选低频数据
            low_freq_mask = frequencies < 5.0

            if not np.any(low_freq_mask):
                return None

            low_freq_indices = np.where(low_freq_mask)[0]
            low_freq_real = real_parts[low_freq_mask]
            low_freq_imag = imag_parts[low_freq_mask]

            # 修复寻找虚部绝对值最小的点（最接近零的点）
            min_imag_idx_local = np.argmin(np.abs(low_freq_imag))
            min_imag_idx_global = low_freq_indices[min_imag_idx_local]

            inflection_freq = frequencies[min_imag_idx_global]
            inflection_real = real_parts[min_imag_idx_global]
            inflection_imag = imag_parts[min_imag_idx_global]

            # 检查拐点实部是否 > Rs
            if inflection_real <= rs_value:
                # 寻找低频段实部 > Rs的最小点
                valid_mask = low_freq_real > rs_value
                if np.any(valid_mask):
                    valid_indices = low_freq_indices[valid_mask]
                    valid_real = low_freq_real[valid_mask]

                    # 选择实部最小的有效点
                    min_valid_idx_local = np.argmin(valid_real)
                    min_valid_idx_global = valid_indices[min_valid_idx_local]

                    inflection_freq = frequencies[min_valid_idx_global]
                    inflection_real = real_parts[min_valid_idx_global]
                    inflection_imag = imag_parts[min_valid_idx_global]
                else:
                    # 估算一个合理的拐点
                    total_impedance = np.max(real_parts)
                    estimated_rct = (total_impedance - rs_value) * 0.1  # 假设Rct占10%
                    inflection_real = rs_value + estimated_rct
                    inflection_freq = 2.0  # 估算频率
                    inflection_imag = 0.0  # 估算虚部

            return (inflection_freq, inflection_real, inflection_imag)

        except Exception as e:
            self.logger.warning(f"拐点查找失败: {e}")
            return None

    def _calculate_rsei_enhanced(self, frequencies: np.ndarray,
                                real_parts: np.ndarray) -> float:
        """
        增强版SEI膜电阻计算（优化低内阻电池检测）
        """
        try:
            # 优化多种方法计算Rsei，提高检测成功率

            # 方法1：高频到中频的变化（原方法）
            high_freq_mask = frequencies >= self.enhanced_config['high_freq_threshold']
            mid_freq_mask = (frequencies >= 10) & (frequencies < self.enhanced_config['high_freq_threshold'])

            rsei_method1 = 0.0
            if np.any(high_freq_mask) and np.any(mid_freq_mask):
                high_freq_real = np.mean(real_parts[high_freq_mask])
                mid_freq_real = np.mean(real_parts[mid_freq_mask])
                rsei_method1 = mid_freq_real - high_freq_real

            # 方法2：高频区域内部变化（新增，适应低内阻）
            rsei_method2 = 0.0
            if np.any(high_freq_mask) and np.sum(high_freq_mask) >= 3:
                high_freq_real_values = real_parts[high_freq_mask]
                rsei_method2 = np.max(high_freq_real_values) - np.min(high_freq_real_values)

            # 方法3：相邻频点最大变化（备用方法）
            rsei_method3 = 0.0
            if len(real_parts) > 1:
                real_diff = np.diff(real_parts)
                rsei_method3 = np.max(np.abs(real_diff))

            # 选择最合理的结果
            candidates = [rsei_method1, rsei_method2, rsei_method3]
            valid_candidates = [r for r in candidates if r >= self.enhanced_config['sei_min_change']]

            if valid_candidates:
                # 选择最小的有效值（更保守）
                rsei_value = min(valid_candidates)
                self.logger.debug(f"✅ SEI检测成功: 方法1={rsei_method1:.3f}, 方法2={rsei_method2:.3f}, 方法3={rsei_method3:.3f}, 选择={rsei_value:.3f}mΩ")
                return max(0.0, rsei_value)
            else:
                self.logger.debug(f"❌ SEI检测失败: 方法1={rsei_method1:.3f}, 方法2={rsei_method2:.3f}, 方法3={rsei_method3:.3f}mΩ，均低于阈值{self.enhanced_config['sei_min_change']:.3f}mΩ")
                return 0.0

        except Exception as e:
            self.logger.warning(f"SEI计算失败: {e}")
            return 0.0

    def _calculate_rsei_rct_nyquist(self, frequencies: np.ndarray,
                                   real_parts: np.ndarray,
                                   imag_parts: np.ndarray,
                                   rs_value: float) -> tuple:
        """
        基于Jack的Nyquist图分析方法同时计算Rsei和Rct

        方法：
        1. 找到虚部峰值对应的实部（极化阻抗终点）
        2. 极化阻抗 = 虚部峰值实部 - Rs
        3. Rsei和Rct按实际测试比例分配
        """
        try:
            # 寻找中频段虚部峰值对应的实部（极化阻抗终点）
            # 排除低频Warburg阻抗的影响，只在中高频段寻找峰值
            mid_high_freq_mask = frequencies >= 1.0  # 1Hz以上

            if np.any(mid_high_freq_mask):
                # 在中高频段寻找虚部峰值
                mid_high_imag = np.abs(imag_parts[mid_high_freq_mask])
                mid_high_real = real_parts[mid_high_freq_mask]

                if len(mid_high_imag) > 0:
                    peak_idx_local = np.argmax(mid_high_imag)
                    polarization_end_real = mid_high_real[peak_idx_local]
                    peak_frequency = frequencies[mid_high_freq_mask][peak_idx_local]

                    self.logger.debug(f"中频段虚部峰值: 频率={peak_frequency:.3f}Hz, 实部={polarization_end_real:.3f}mΩ")
                else:
                    # 回退到全频段
                    imag_abs = np.abs(imag_parts)
                    peak_idx = np.argmax(imag_abs)
                    polarization_end_real = real_parts[peak_idx]
            else:
                # 回退到全频段
                imag_abs = np.abs(imag_parts)
                peak_idx = np.argmax(imag_abs)
                polarization_end_real = real_parts[peak_idx]

            # 极化阻抗总和 = 虚部峰值实部 - Rs
            polarization_total = polarization_end_real - rs_value

            # Jack的标准方法：不分离Rsei，使用总阻抗减法
            # Rct = 总阻抗 - Rs (包含所有极化阻抗)
            total_impedance = np.max(real_parts)
            rsei_value = 0.0  # 不再单独计算Rsei
            rct_value = total_impedance - rs_value

            # 确保值为正且合理
            rsei_value = max(0.0, min(20.0, rsei_value))
            rct_value = max(0.0, min(200.0, rct_value))

            self.logger.debug(f"Nyquist分析: Rs={rs_value:.3f}mΩ, 虚部峰值实部={polarization_end_real:.3f}mΩ")
            self.logger.debug(f"极化阻抗={polarization_total:.3f}mΩ, Rsei={rsei_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")

            return rsei_value, rct_value

        except Exception as e:
            self.logger.warning(f"Nyquist分析失败，回退到原方法: {e}")
            # 回退到原方法
            rsei_value = self._calculate_rsei_enhanced(frequencies, real_parts)
            rct_value = self._calculate_rct_enhanced(real_parts, rs_value, rsei_value, imag_parts)
            return rsei_value, rct_value

    def _calculate_rct_enhanced(self, real_parts: np.ndarray,
                               rs_value: float,
                               rsei_value: float,
                               imag_parts: np.ndarray = None) -> float:
        """
        增强版Rct计算 - 基于Jack的Nyquist图分析方法
        """
        try:
            # 🎯 Jack的正确方法：基于Nyquist图分析
            # 1. 找到虚部峰值对应的实部（极化阻抗终点）
            # 2. 极化阻抗 = 虚部峰值实部 - Rs
            # 3. Rsei和Rct按比例分配极化阻抗

            if imag_parts is not None and len(imag_parts) > 0:
                # 寻找虚部峰值对应的实部
                imag_abs = np.abs(imag_parts)
                peak_idx = np.argmax(imag_abs)
                polarization_end_real = real_parts[peak_idx]

                # 极化阻抗总和
                polarization_total = polarization_end_real - rs_value

                # Jack的标准方法：不分离Rsei，Rct包含所有极化阻抗
                # Rct = 总阻抗 - Rs (包含原来的Rsei+Rct)
                total_impedance = np.max(real_parts)
                rct_corrected = total_impedance - rs_value

                self.logger.debug(f"Nyquist分析: 虚部峰值实部={polarization_end_real:.3f}mΩ, 极化阻抗={polarization_total:.3f}mΩ")
                self.logger.debug(f"修正结果: Rct={rct_corrected:.3f}mΩ")

                # 确保Rct值为正且合理
                rct_value = max(0.0, rct_corrected)
            else:
                # 回退到原方法
                rp_value = np.max(real_parts)
                rct_value = rp_value - rs_value - rsei_value
                rct_value = max(0.0, rct_value)

            return rct_value

        except Exception as e:
            self.logger.warning(f"Rct计算失败: {e}")
            # 回退到原方法
            rp_value = np.max(real_parts)
            rct_value = rp_value - rs_value - rsei_value
            return max(0.0, rct_value)

    def _calculate_warburg_enhanced(self, frequencies: np.ndarray,
                                   real_parts: np.ndarray,
                                   imag_parts: np.ndarray) -> Dict:
        """
        增强版Warburg扩散阻抗计算
        """
        try:
            # 选择低频段数据进行Warburg分析
            low_freq_mask = frequencies <= self.enhanced_config['low_freq_threshold']

            if np.sum(low_freq_mask) < 3:  # 至少需要3个点
                return {
                    'warburg_coefficient': 0.0,
                    'warburg_detected': False,
                    'warburg_correlation': 0.0
                }

            low_freq_freqs = frequencies[low_freq_mask]
            low_freq_real = real_parts[low_freq_mask]
            low_freq_imag = imag_parts[low_freq_mask]

            # 计算频率的平方根倒数
            omega_sqrt_inv = 1.0 / np.sqrt(2 * np.pi * low_freq_freqs)

            # 线性拟合 Z_real vs ω^(-1/2)
            if len(omega_sqrt_inv) >= 2:
                from scipy import stats
                slope_real, intercept_real, r_real, _, _ = stats.linregress(omega_sqrt_inv, low_freq_real)
                slope_imag, intercept_imag, r_imag, _, _ = stats.linregress(omega_sqrt_inv, low_freq_imag)

                # Warburg系数（取实部和虚部斜率的平均值）
                warburg_coeff = (abs(slope_real) + abs(slope_imag)) / 2.0

                # 相关性（取较好的一个）
                correlation = max(abs(r_real), abs(r_imag))

                # 判断是否检测到Warburg扩散
                warburg_detected = correlation >= self.enhanced_config['warburg_corr_threshold']

                return {
                    'warburg_coefficient': warburg_coeff,
                    'warburg_detected': warburg_detected,
                    'warburg_correlation': correlation
                }

            return {
                'warburg_coefficient': 0.0,
                'warburg_detected': False,
                'warburg_correlation': 0.0
            }

        except Exception as e:
            self.logger.warning(f"Warburg计算失败: {e}")
            return {
                'warburg_coefficient': 0.0,
                'warburg_detected': False,
                'warburg_correlation': 0.0
            }

    def _calculate_phase_enhanced(self, frequencies: np.ndarray,
                                 real_parts: np.ndarray,
                                 imag_parts: np.ndarray) -> Dict:
        """
        增强版相位角计算
        """
        try:
            # 计算相位角
            phase_angles = np.arctan2(-imag_parts, real_parts) * 180 / np.pi

            # 计算特征频率（相位角最大的频率）
            max_phase_idx = np.argmax(np.abs(phase_angles))
            characteristic_freq = frequencies[max_phase_idx]
            max_phase_angle = phase_angles[max_phase_idx]

            return {
                'characteristic_frequency': characteristic_freq,
                'max_phase_angle': max_phase_angle,
                'phase_angles': phase_angles.tolist()
            }

        except Exception as e:
            self.logger.warning(f"相位角计算失败: {e}")
            return {
                'characteristic_frequency': 0.0,
                'max_phase_angle': 0.0,
                'phase_angles': []
            }

        except Exception as e:
            self.logger.error(f"EIS数据验证失败: {e}")
            return {
                'is_valid': False,
                'warnings': [f"验证过程异常: {e}"],
                'data_quality': 'unknown',
                'frequency_range': 'unknown',
                'data_points': 0
            }
