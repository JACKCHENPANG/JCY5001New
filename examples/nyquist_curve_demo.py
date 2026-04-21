#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
奈奎斯特曲线优化器使用示例
展示如何使用新的优化器生成更漂亮、更顺滑的拟合曲线

Author: Jack
Date: 2025-07-13
"""

import sys
import numpy as np
import matplotlib.pyplot as plt

# 添加项目路径
sys.path.append('..')

from utils.nyquist_curve_optimizer import generate_beautiful_nyquist_curve


def generate_sample_eis_data():
    """生成示例EIS数据"""
    # 模拟典型的锂电池EIS数据
    frequencies = np.logspace(4, -2, 15)  # 10kHz到0.01Hz，15个点
    
    # Randles等效电路参数
    Rs = 0.05    # 溶液电阻 (Ω)
    Rct = 0.12   # 电荷转移电阻 (Ω)
    Cdl = 8e-5   # 双电层电容 (F)
    n = 0.82     # CPE指数
    
    # 计算理论阻抗
    omega = 2 * np.pi * frequencies
    Z_cpe = 1 / (Cdl * (1j * omega) ** n)
    Z_total = Rs + (Rct * Z_cpe) / (Rct + Z_cpe)
    
    real_parts = Z_total.real
    imag_parts = Z_total.imag
    
    # 添加一些噪声模拟实际测量
    noise_level = 0.003
    real_parts += np.random.normal(0, noise_level, len(real_parts))
    imag_parts += np.random.normal(0, noise_level, len(imag_parts))
    
    return frequencies, real_parts.tolist(), imag_parts.tolist()


def demo_all_methods():
    """演示所有拟合方法"""
    print("=" * 60)
    print("奈奎斯特曲线优化器演示")
    print("=" * 60)
    
    # 生成示例数据
    frequencies, real_parts, imag_parts = generate_sample_eis_data()
    print(f"生成示例数据: {len(frequencies)} 个频率点")
    
    # 测试所有方法
    methods = {
        'spline_weighted': '加权样条插值',
        'parametric_spline': '参数化样条',
        'savgol_enhanced': '增强Savitzky-Golay',
        'hybrid_smooth': '混合平滑 (推荐)',
        'physics_based': '基于物理模型'
    }
    
    # 创建图表
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('奈奎斯特曲线优化器效果对比', fontsize=16, fontweight='bold')
    
    colors = ['red', 'blue', 'green', 'orange', 'purple']
    
    for i, (method, name) in enumerate(methods.items()):
        row = i // 3
        col = i % 3
        ax = axes[row, col]
        
        print(f"\n测试方法: {name}")
        
        # 生成拟合曲线
        fitted_real, fitted_imag = generate_beautiful_nyquist_curve(
            real_parts, imag_parts, frequencies, 
            method=method, 
            density_factor=3.0
        )
        
        if fitted_real is not None and fitted_imag is not None:
            print(f"  ✅ 成功 - 生成 {len(fitted_real)} 个拟合点")
            
            # 绘制原始数据
            ax.plot(real_parts, [-x for x in imag_parts], 'ko-', 
                   markersize=6, linewidth=1, label='原始数据', alpha=0.7)
            
            # 绘制拟合曲线
            ax.plot(fitted_real, [-x for x in fitted_imag], 
                   color=colors[i], linewidth=3, label=f'{name}拟合', alpha=0.8)
            
            # 标注频率点
            ax.annotate(f'{frequencies[0]:.0f}Hz', 
                       (real_parts[0], -imag_parts[0]),
                       xytext=(5, 5), textcoords='offset points', fontsize=8)
            ax.annotate(f'{frequencies[-1]:.2f}Hz', 
                       (real_parts[-1], -imag_parts[-1]),
                       xytext=(5, 5), textcoords='offset points', fontsize=8)
            
        else:
            print(f"  ❌ 失败")
            # 只绘制原始数据
            ax.plot(real_parts, [-x for x in imag_parts], 'ko-', 
                   markersize=6, linewidth=1, label='原始数据', alpha=0.7)
        
        ax.set_xlabel('Z\' (Ω)')
        ax.set_ylabel('-Z\'\' (Ω)')
        ax.set_title(name)
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_aspect('equal')
    
    # 最后一个子图显示推荐方法
    ax = axes[1, 2]
    fitted_real, fitted_imag = generate_beautiful_nyquist_curve(
        real_parts, imag_parts, frequencies, 
        method='hybrid_smooth', 
        density_factor=4.0  # 更高密度
    )
    
    if fitted_real is not None and fitted_imag is not None:
        ax.plot(real_parts, [-x for x in imag_parts], 'ko-', 
               markersize=8, linewidth=2, label='原始数据', alpha=0.8)
        ax.plot(fitted_real, [-x for x in fitted_imag], 
               'r-', linewidth=4, label='混合平滑 (高密度)', alpha=0.9)
        
        print(f"\n🎯 推荐方法效果:")
        print(f"   原始数据点: {len(real_parts)}")
        print(f"   拟合数据点: {len(fitted_real)}")
        print(f"   密度提升: {len(fitted_real) / len(real_parts):.1f}x")
    
    ax.set_xlabel('Z\' (Ω)')
    ax.set_ylabel('-Z\'\' (Ω)')
    ax.set_title('推荐方案 (混合平滑)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_aspect('equal')
    
    plt.tight_layout()
    plt.savefig('nyquist_optimizer_demo.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"\n演示图表已保存为 nyquist_optimizer_demo.png")


def demo_density_comparison():
    """演示不同密度因子的效果"""
    print("\n" + "=" * 60)
    print("密度因子效果对比")
    print("=" * 60)
    
    # 生成示例数据
    frequencies, real_parts, imag_parts = generate_sample_eis_data()
    
    # 测试不同密度因子
    density_factors = [1.5, 2.0, 3.0, 4.0]
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('密度因子效果对比 (混合平滑方法)', fontsize=14, fontweight='bold')
    
    for i, density in enumerate(density_factors):
        row = i // 2
        col = i % 2
        ax = axes[row, col]
        
        fitted_real, fitted_imag = generate_beautiful_nyquist_curve(
            real_parts, imag_parts, frequencies, 
            method='hybrid_smooth', 
            density_factor=density
        )
        
        if fitted_real is not None and fitted_imag is not None:
            # 原始数据
            ax.plot(real_parts, [-x for x in imag_parts], 'ko-', 
                   markersize=6, linewidth=1, label='原始数据', alpha=0.7)
            
            # 拟合曲线
            ax.plot(fitted_real, [-x for x in fitted_imag], 
                   'r-', linewidth=3, label=f'拟合曲线 ({len(fitted_real)}点)', alpha=0.8)
            
            print(f"密度因子 {density}: {len(real_parts)} -> {len(fitted_real)} 点")
        
        ax.set_xlabel('Z\' (Ω)')
        ax.set_ylabel('-Z\'\' (Ω)')
        ax.set_title(f'密度因子 = {density}')
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_aspect('equal')
    
    plt.tight_layout()
    plt.savefig('density_comparison_demo.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"密度对比图表已保存为 density_comparison_demo.png")


def main():
    """主函数"""
    print("JCY5001AS 奈奎斯特曲线优化器演示")
    print("基于网络研究和最佳实践的拟合曲线优化")
    
    try:
        # 演示所有方法
        demo_all_methods()
        
        # 演示密度对比
        demo_density_comparison()
        
        print("\n" + "=" * 60)
        print("演示完成")
        print("=" * 60)
        print("🎉 奈奎斯特曲线优化器可以显著改善拟合曲线的视觉效果！")
        print("💡 推荐在实际应用中使用 'hybrid_smooth' 方法")
        print("🔧 可以根据需要调整 density_factor 参数控制曲线密度")
        
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
