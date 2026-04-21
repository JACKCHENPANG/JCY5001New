#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
奈奎斯特图拟合曲线优化器
基于网络研究和最佳实践，提供更漂亮、更顺滑的拟合曲线

参考资料：
1. SciPy interpolation documentation
2. Electrochemical Impedance Spectroscopy best practices
3. impedance.py library approaches
4. Matplotlib smooth curve techniques

Author: Jack
Date: 2025-07-13
"""

import numpy as np
import logging
from scipy import interpolate
from scipy.signal import savgol_filter
from scipy.optimize import curve_fit
from typing import Tuple, Optional, List

logger = logging.getLogger(__name__)


class NyquistCurveOptimizer:
    """奈奎斯特图拟合曲线优化器"""
    
    def __init__(self):
        self.smoothing_methods = {
            'spline_weighted': self._spline_weighted_fitting,
            'parametric_spline': self._parametric_spline_fitting,
            'savgol_enhanced': self._savgol_enhanced_fitting,
            'hybrid_smooth': self._hybrid_smooth_fitting,
            'physics_based': self._physics_based_fitting
        }
    
    def generate_smooth_curve(self, real_parts: np.ndarray, imag_parts: np.ndarray, 
                            frequencies: np.ndarray, method: str = 'hybrid_smooth',
                            density_factor: float = 3.0) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        生成平滑的奈奎斯特拟合曲线
        
        Args:
            real_parts: 阻抗实部数据
            imag_parts: 阻抗虚部数据  
            frequencies: 频率数据
            method: 拟合方法 ('spline_weighted', 'parametric_spline', 'savgol_enhanced', 'hybrid_smooth', 'physics_based')
            density_factor: 曲线密度因子，越大越平滑
            
        Returns:
            (fitted_real, fitted_imag) 或 (None, None)
        """
        try:
            if len(real_parts) < 4:
                logger.warning("数据点不足，无法生成平滑曲线")
                return None, None
            
            # 数据预处理
            real_clean, imag_clean, freq_clean = self._preprocess_data(real_parts, imag_parts, frequencies)
            
            if len(real_clean) < 4:
                logger.warning("清理后数据点不足")
                return None, None
            
            # 选择拟合方法
            if method not in self.smoothing_methods:
                logger.warning(f"未知方法 {method}，使用默认方法 hybrid_smooth")
                method = 'hybrid_smooth'
            
            fitting_func = self.smoothing_methods[method]
            fitted_real, fitted_imag = fitting_func(real_clean, imag_clean, freq_clean, density_factor)
            
            if fitted_real is not None and fitted_imag is not None:
                logger.debug(f"使用 {method} 方法生成平滑曲线成功，点数: {len(fitted_real)}")
                return fitted_real, fitted_imag
            else:
                logger.warning(f"{method} 方法失败，尝试备用方法")
                return self._fallback_fitting(real_clean, imag_clean, freq_clean, density_factor)
                
        except Exception as e:
            logger.error(f"生成平滑曲线失败: {e}")
            return None, None
    
    def _preprocess_data(self, real_parts: np.ndarray, imag_parts: np.ndarray, 
                        frequencies: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """数据预处理：去除异常值、排序等"""
        try:
            # 转换为numpy数组
            real = np.asarray(real_parts)
            imag = np.asarray(imag_parts)
            freq = np.asarray(frequencies)
            
            # 去除NaN和无穷值
            valid_mask = np.isfinite(real) & np.isfinite(imag) & np.isfinite(freq) & (freq > 0)
            real = real[valid_mask]
            imag = imag[valid_mask]
            freq = freq[valid_mask]
            
            # 按频率排序（从高频到低频）
            sort_indices = np.argsort(freq)[::-1]
            real = real[sort_indices]
            imag = imag[sort_indices]
            freq = freq[sort_indices]
            
            # 去除重复的频率点
            unique_indices = np.unique(freq, return_index=True)[1]
            real = real[unique_indices]
            imag = imag[unique_indices]
            freq = freq[unique_indices]
            
            return real, imag, freq
            
        except Exception as e:
            logger.error(f"数据预处理失败: {e}")
            return real_parts, imag_parts, frequencies
    
    def _spline_weighted_fitting(self, real_parts: np.ndarray, imag_parts: np.ndarray,
                               frequencies: np.ndarray, density_factor: float) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """加权样条插值方法 - 基于SciPy最佳实践"""
        try:
            n_points = len(real_parts)
            
            # 🎯 策略1：智能权重分配
            weights = np.ones(n_points)
            
            # 端点权重更高（保持边界条件）
            weights[0] = 5.0
            weights[-1] = 5.0
            
            # 虚部峰值点权重更高（保持半圆特征）
            if len(imag_parts) > 2:
                peak_idx = np.argmax(imag_parts)
                weights[peak_idx] = 3.0
            
            # 曲率变化大的点权重更高
            if n_points > 4:
                curvature = self._calculate_curvature(real_parts, imag_parts)
                high_curvature_indices = np.where(curvature > np.percentile(curvature, 75))[0]
                weights[high_curvature_indices] *= 2.0
            
            # 🎯 策略2：对数频率参数化
            log_freq = np.log10(frequencies + 1e-12)
            
            # 🎯 策略3：自适应平滑因子
            data_span = np.max(real_parts) - np.min(real_parts)
            noise_level = np.std(np.diff(real_parts)) + np.std(np.diff(imag_parts))
            smoothing_factor = max(0.01, min(1.0, noise_level / data_span)) * n_points
            
            # 创建样条插值
            spline_real = interpolate.UnivariateSpline(log_freq, real_parts, w=weights, s=smoothing_factor)
            spline_imag = interpolate.UnivariateSpline(log_freq, imag_parts, w=weights, s=smoothing_factor)
            
            # 生成密集点
            n_dense = int(n_points * density_factor)
            log_freq_dense = np.linspace(log_freq.min(), log_freq.max(), n_dense)
            
            fitted_real = spline_real(log_freq_dense)
            fitted_imag = spline_imag(log_freq_dense)
            
            # 端点精确匹配
            fitted_real[0] = real_parts[0]
            fitted_real[-1] = real_parts[-1]
            fitted_imag[0] = imag_parts[0]
            fitted_imag[-1] = imag_parts[-1]
            
            return fitted_real, fitted_imag
            
        except Exception as e:
            logger.error(f"加权样条插值失败: {e}")
            return None, None
    
    def _parametric_spline_fitting(self, real_parts: np.ndarray, imag_parts: np.ndarray,
                                 frequencies: np.ndarray, density_factor: float) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """参数化样条插值方法 - 适用于复杂曲线"""
        try:
            n_points = len(real_parts)
            
            # 🎯 使用累积弧长作为参数
            distances = np.zeros(n_points)
            for i in range(1, n_points):
                dx = real_parts[i] - real_parts[i-1]
                dy = imag_parts[i] - imag_parts[i-1]
                distances[i] = distances[i-1] + np.sqrt(dx*dx + dy*dy)
            
            # 归一化参数
            t = distances / distances[-1] if distances[-1] > 0 else np.linspace(0, 1, n_points)
            
            # 创建参数化样条
            smoothing = len(real_parts) * 0.05  # 轻度平滑
            spline_real = interpolate.UnivariateSpline(t, real_parts, s=smoothing)
            spline_imag = interpolate.UnivariateSpline(t, imag_parts, s=smoothing)
            
            # 生成密集参数点
            n_dense = int(n_points * density_factor)
            t_dense = np.linspace(0, 1, n_dense)
            
            fitted_real = spline_real(t_dense)
            fitted_imag = spline_imag(t_dense)
            
            return fitted_real, fitted_imag
            
        except Exception as e:
            logger.error(f"参数化样条插值失败: {e}")
            return None, None
    
    def _savgol_enhanced_fitting(self, real_parts: np.ndarray, imag_parts: np.ndarray,
                               frequencies: np.ndarray, density_factor: float) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """增强Savitzky-Golay滤波方法"""
        try:
            n_points = len(real_parts)
            
            # 🎯 自适应窗口大小
            window_length = min(n_points - 1, max(5, n_points // 3))
            if window_length % 2 == 0:
                window_length += 1
            
            # 应用Savitzky-Golay滤波
            poly_order = min(3, window_length - 1)
            smooth_real = savgol_filter(real_parts, window_length, poly_order)
            smooth_imag = savgol_filter(imag_parts, window_length, poly_order)
            
            # 使用三次样条插值增加密度
            log_freq = np.log10(frequencies + 1e-12)
            n_dense = int(n_points * density_factor)
            log_freq_dense = np.linspace(log_freq.min(), log_freq.max(), n_dense)
            
            cs_real = interpolate.CubicSpline(log_freq, smooth_real)
            cs_imag = interpolate.CubicSpline(log_freq, smooth_imag)
            
            fitted_real = cs_real(log_freq_dense)
            fitted_imag = cs_imag(log_freq_dense)
            
            return fitted_real, fitted_imag
            
        except Exception as e:
            logger.error(f"Savitzky-Golay增强拟合失败: {e}")
            return None, None
    
    def _hybrid_smooth_fitting(self, real_parts: np.ndarray, imag_parts: np.ndarray,
                             frequencies: np.ndarray, density_factor: float) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """混合平滑方法 - 结合多种技术的最佳效果"""
        try:
            n_points = len(real_parts)
            
            # 🎯 第一步：轻度Savitzky-Golay预处理
            if n_points >= 7:
                window_length = min(n_points - 1, max(5, n_points // 4))
                if window_length % 2 == 0:
                    window_length += 1
                poly_order = min(2, window_length - 1)
                
                pre_smooth_real = savgol_filter(real_parts, window_length, poly_order)
                pre_smooth_imag = savgol_filter(imag_parts, window_length, poly_order)
            else:
                pre_smooth_real = real_parts.copy()
                pre_smooth_imag = imag_parts.copy()
            
            # 🎯 第二步：加权样条精细拟合
            log_freq = np.log10(frequencies + 1e-12)
            
            # 智能权重
            weights = np.ones(n_points)
            weights[0] = 3.0  # 起始点
            weights[-1] = 3.0  # 结束点
            
            # 虚部峰值点
            if len(imag_parts) > 2:
                peak_idx = np.argmax(imag_parts)
                weights[peak_idx] = 2.0
            
            # 自适应平滑
            smoothing_factor = n_points * 0.03
            
            spline_real = interpolate.UnivariateSpline(log_freq, pre_smooth_real, w=weights, s=smoothing_factor)
            spline_imag = interpolate.UnivariateSpline(log_freq, pre_smooth_imag, w=weights, s=smoothing_factor)
            
            # 🎯 第三步：生成高密度平滑曲线
            n_dense = int(n_points * density_factor)
            log_freq_dense = np.linspace(log_freq.min(), log_freq.max(), n_dense)
            
            fitted_real = spline_real(log_freq_dense)
            fitted_imag = spline_imag(log_freq_dense)
            
            # 🎯 第四步：端点约束
            fitted_real[0] = real_parts[0]
            fitted_real[-1] = real_parts[-1]
            fitted_imag[0] = imag_parts[0]
            fitted_imag[-1] = imag_parts[-1]
            
            return fitted_real, fitted_imag
            
        except Exception as e:
            logger.error(f"混合平滑拟合失败: {e}")
            return None, None

    def _physics_based_fitting(self, real_parts: np.ndarray, imag_parts: np.ndarray,
                             frequencies: np.ndarray, density_factor: float) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """基于物理模型的拟合方法 - 考虑EIS的物理特性"""
        try:
            # 🎯 基于Randles等效电路模型的拟合
            # 这种方法考虑了电化学阻抗的物理意义

            # 简化的Randles模型：Rs + Rct/(1 + (jωRctCdl)^n)
            def randles_model(freq, Rs, Rct, Cdl, n):
                omega = 2 * np.pi * freq
                Z_cpe = 1 / (Cdl * (1j * omega) ** n)
                Z_total = Rs + (Rct * Z_cpe) / (Rct + Z_cpe)
                return Z_total

            # 初值估算
            Rs_guess = real_parts[0]  # 高频实部
            Rct_guess = real_parts[-1] - Rs_guess  # 电荷转移电阻
            Cdl_guess = 1e-5  # 双电层电容
            n_guess = 0.8  # CPE指数

            initial_guess = [Rs_guess, max(Rct_guess, 0.001), Cdl_guess, n_guess]

            # 拟合目标函数
            def objective(freq, Rs, Rct, Cdl, n):
                z_model = randles_model(freq, Rs, Rct, Cdl, n)
                return np.concatenate([z_model.real, z_model.imag])

            # 数据准备
            z_data = np.concatenate([real_parts, imag_parts])

            # 参数边界
            bounds = ([0, 0, 1e-8, 0.5], [np.inf, np.inf, 1e-2, 1.0])

            # 执行拟合
            popt, _ = curve_fit(objective, frequencies, z_data,
                              p0=initial_guess, bounds=bounds, maxfev=2000)

            # 生成高密度频率点
            freq_min, freq_max = frequencies.min(), frequencies.max()
            n_dense = int(len(frequencies) * density_factor)
            freq_dense = np.logspace(np.log10(freq_min), np.log10(freq_max), n_dense)

            # 计算拟合曲线
            z_fitted = randles_model(freq_dense, *popt)
            fitted_real = z_fitted.real
            fitted_imag = z_fitted.imag

            return fitted_real, fitted_imag

        except Exception as e:
            logger.error(f"基于物理模型的拟合失败: {e}")
            return None, None

    def _calculate_curvature(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """计算曲线的曲率"""
        try:
            if len(x) < 3:
                return np.zeros(len(x))

            # 计算一阶和二阶导数
            dx = np.gradient(x)
            dy = np.gradient(y)
            ddx = np.gradient(dx)
            ddy = np.gradient(dy)

            # 曲率公式: κ = |x'y'' - y'x''| / (x'^2 + y'^2)^(3/2)
            numerator = np.abs(dx * ddy - dy * ddx)
            denominator = (dx**2 + dy**2)**(3/2)

            # 避免除零
            denominator = np.where(denominator < 1e-10, 1e-10, denominator)
            curvature = numerator / denominator

            return curvature

        except Exception as e:
            logger.error(f"曲率计算失败: {e}")
            return np.zeros(len(x))

    def _fallback_fitting(self, real_parts: np.ndarray, imag_parts: np.ndarray,
                         frequencies: np.ndarray, density_factor: float) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """备用拟合方法 - 简单但可靠"""
        try:
            log_freq = np.log10(frequencies + 1e-12)

            # 使用三次样条插值
            cs_real = interpolate.CubicSpline(log_freq, real_parts)
            cs_imag = interpolate.CubicSpline(log_freq, imag_parts)

            # 生成密集点
            n_dense = int(len(real_parts) * density_factor)
            log_freq_dense = np.linspace(log_freq.min(), log_freq.max(), n_dense)

            fitted_real = cs_real(log_freq_dense)
            fitted_imag = cs_imag(log_freq_dense)

            return fitted_real, fitted_imag

        except Exception as e:
            logger.error(f"备用拟合方法失败: {e}")
            return None, None


# 全局实例
_nyquist_optimizer = None


def get_nyquist_optimizer() -> NyquistCurveOptimizer:
    """获取奈奎斯特曲线优化器实例（单例模式）"""
    global _nyquist_optimizer
    if _nyquist_optimizer is None:
        _nyquist_optimizer = NyquistCurveOptimizer()
    return _nyquist_optimizer


def generate_beautiful_nyquist_curve(real_parts: List[float], imag_parts: List[float],
                                   frequencies: List[float], method: str = 'hybrid_smooth',
                                   density_factor: float = 3.0) -> Tuple[Optional[List[float]], Optional[List[float]]]:
    """
    生成漂亮的奈奎斯特拟合曲线（便捷函数）

    Args:
        real_parts: 阻抗实部数据
        imag_parts: 阻抗虚部数据
        frequencies: 频率数据
        method: 拟合方法
        density_factor: 曲线密度因子

    Returns:
        (fitted_real_list, fitted_imag_list) 或 (None, None)
    """
    try:
        optimizer = get_nyquist_optimizer()

        real_array = np.array(real_parts)
        imag_array = np.array(imag_parts)
        freq_array = np.array(frequencies)

        fitted_real, fitted_imag = optimizer.generate_smooth_curve(
            real_array, imag_array, freq_array, method, density_factor
        )

        if fitted_real is not None and fitted_imag is not None:
            return fitted_real.tolist(), fitted_imag.tolist()
        else:
            return None, None

    except Exception as e:
        logger.error(f"生成漂亮奈奎斯特曲线失败: {e}")
        return None, None
