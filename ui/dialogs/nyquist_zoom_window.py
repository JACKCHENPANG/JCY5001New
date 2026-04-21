# -*- coding: utf-8 -*-
"""
奈奎斯特图放大显示窗口

用于在独立窗口中放大显示奈奎斯特图，提供更好的查看体验。
支持单通道和多通道模式，保持所有当前的显示设置。

Author: Augment Agent
Date: 2025-06-29
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QCheckBox, QLabel, QGroupBox, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
import logging
from typing import List, Dict, Optional

# 导入matplotlib相关组件
try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    # 如果matplotlib不可用，创建虚拟类
    class DummyFigureCanvas:
        def __init__(self, figure):
            pass
        def setMinimumSize(self, w, h):
            pass
        def draw(self):
            pass
        def draw_idle(self):
            pass
        def flush_events(self):
            pass

    class DummyFigure:
        def __init__(self, figsize=None, dpi=None):
            pass
        def clear(self):
            pass
        def add_subplot(self, *args):
            return None

    FigureCanvas = DummyFigureCanvas
    Figure = DummyFigure
    np = None
    MATPLOTLIB_AVAILABLE = False

logger = logging.getLogger(__name__)


class NyquistZoomWindow(QDialog):
    """
    奈奎斯特图放大显示窗口

    功能：
    - 在独立窗口中放大显示奈奎斯特图
    - 支持单通道和多通道模式
    - 保持所有当前的显示设置（拟合曲线、图例等）
    - 可调整窗口大小
    - 提供控制选项
    """

    # 信号定义
    window_closed = pyqtSignal()

    def __init__(self, parent=None,
                 single_channel_data: List[Dict] = None,
                 test_result: Dict = None,
                 multi_channel_data: Dict = None,
                 show_fitted_curve: bool = False,
                 show_legend: bool = True,
                 show_assist_markers: bool = True,
                 impedance_unit: str = 'mΩ'):
        """
        初始化放大显示窗口

        Args:
            parent: 父窗口
            single_channel_data: 单通道数据
            test_result: 测试结果信息
            multi_channel_data: 多通道数据
            show_fitted_curve: 是否显示拟合曲线
            show_legend: 是否显示图例
            impedance_unit: 阻抗单位
        """
        super().__init__(parent)

        # 保存参数
        self.single_channel_data = single_channel_data
        self.test_result = test_result
        self.multi_channel_data = multi_channel_data
        self.show_fitted_curve = show_fitted_curve
        self.show_legend = show_legend
        self.show_assist_markers = show_assist_markers

        # 如果父窗口有辅助标记设置，优先使用父窗口的设置
        try:
            if hasattr(parent, '_show_assist_markers'):
                self.show_assist_markers = bool(getattr(parent, '_show_assist_markers'))
        except Exception:
            pass

        self.impedance_unit = impedance_unit

        # 图表相关变量
        self.figure = None
        self.canvas = None
        self.ax = None


        # 多通道颜色
        self._channel_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']

        # 初始化界面
        self._init_ui()
        self._create_plot()
        self._plot_data()

        logger.info("奈奎斯特图放大显示窗口初始化完成")

    def _init_ui(self):
        """初始化用户界面"""
        # 设置窗口属性
        self.setWindowTitle("奈奎斯特图 - 放大显示")
        self.setWindowIcon(QIcon("resources/icons/chart.png"))
        self.setModal(False)  # 非模态窗口
        self.resize(1000, 700)
        self.setMinimumSize(800, 600)

        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 创建控制区域
        control_group = self._create_control_area()
        main_layout.addWidget(control_group)

        # 创建图表区域
        self._create_plot_area(main_layout)

        # 创建按钮区域
        button_layout = self._create_button_area()
        main_layout.addLayout(button_layout)

    def _create_control_area(self) -> QGroupBox:
        """创建控制区域"""
        group = QGroupBox("显示控制")
        group.setFont(QFont("", 9, QFont.Bold))
        group.setMaximumHeight(80)

        layout = QHBoxLayout(group)
        layout.setSpacing(15)

        # 拟合曲线控制
        self.fitted_curve_cb = QCheckBox("显示拟合曲线")
        self.fitted_curve_cb.setChecked(self.show_fitted_curve)
        self.fitted_curve_cb.toggled.connect(self._on_fitted_curve_toggled)
        layout.addWidget(self.fitted_curve_cb)

        # 图例控制
        self.legend_cb = QCheckBox("显示图例")
        self.legend_cb.setChecked(self.show_legend)
        self.legend_cb.toggled.connect(self._on_legend_toggled)
        layout.addWidget(self.legend_cb)
        # 辅助标记（Rs/峰值）控制
        self.assist_cb = QCheckBox("显示辅助标记(Rs/峰值)")
        self.assist_cb.setChecked(self.show_assist_markers)
        self.assist_cb.toggled.connect(self._on_assist_toggled)
        layout.addWidget(self.assist_cb)


        # 阻抗单位显示
        unit_label = QLabel(f"阻抗单位: {self.impedance_unit}")
        unit_label.setFont(QFont("", 9))
        layout.addWidget(unit_label)

        layout.addStretch()

        return group

    def _create_plot_area(self, main_layout):
        """创建图表区域"""
        if not MATPLOTLIB_AVAILABLE:
            error_label = QLabel("奈奎斯特图功能需要安装matplotlib库")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setMinimumHeight(400)
            main_layout.addWidget(error_label)
            return

        # 创建matplotlib图表
        self.figure = Figure(figsize=(12, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main_layout.addWidget(self.canvas)

    def _create_button_area(self) -> QHBoxLayout:
        """创建按钮区域"""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        layout.addStretch()

        # 重置视图按钮
        reset_btn = QPushButton("重置视图")
        reset_btn.setMinimumHeight(35)
        reset_btn.clicked.connect(self._reset_view)
        layout.addWidget(reset_btn)

        # 导出图片按钮
        export_btn = QPushButton("导出图片")
        export_btn.setMinimumHeight(35)
        export_btn.clicked.connect(self._export_image)
        layout.addWidget(export_btn)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setMinimumHeight(35)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        return layout

    def _create_plot(self):
        """创建图表"""
        if not MATPLOTLIB_AVAILABLE:
            return

        # 创建坐标轴
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel(f'实部阻抗 ({self.impedance_unit})')
        self.ax.set_ylabel(f'虚部阻抗 ({self.impedance_unit})')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_aspect('equal')

        # 设置标题
        if self.multi_channel_data:
            self.ax.set_title(f"多通道奈奎斯特图对比 ({len(self.multi_channel_data)}个通道)")
        elif self.test_result:
            self.ax.set_title(f"奈奎斯特图 - 通道{self.test_result.get('channel_number', 'N/A')} - {self.test_result.get('battery_code', 'N/A')}")
        else:
            self.ax.set_title("奈奎斯特图")

    def _plot_data(self):
        """绘制数据"""
        if not MATPLOTLIB_AVAILABLE:
            return

        try:
            if self.multi_channel_data:
                self._plot_multi_channel_data()
            elif self.single_channel_data:
                self._plot_single_channel_data()

            # 刷新画布
            self.canvas.draw()

        except Exception as e:
            logger.error(f"绘制数据失败: {e}")

    def _plot_single_channel_data(self):
        """绘制单通道数据"""
        if not self.single_channel_data:
            return

        # 提取数据
        real_parts = []
        imag_parts = []
        frequencies = []

        for detail in self.single_channel_data:
            real_mohm = detail.get('impedance_real', 0)
            imag_mohm = detail.get('impedance_imag', 0)
            freq = detail.get('frequency', 0)

            if isinstance(real_mohm, (int, float)) and isinstance(imag_mohm, (int, float)) and freq > 0:
                real_parts.append(real_mohm)
                imag_parts.append(imag_mohm)
                frequencies.append(freq)

        if not real_parts:
            return

        # 绘制轨迹线
        self.ax.plot(real_parts, imag_parts, 'b-', linewidth=2.0, alpha=0.8, label='测试数据')

        # 绘制散点图
        scatter = self.ax.scatter(real_parts, imag_parts, c=frequencies, cmap='plasma',
                                s=80, alpha=0.9, edgecolors='white', linewidth=1.5)

        # 标记起始点和结束点
        if len(real_parts) > 0:
            self.ax.scatter(real_parts[0], imag_parts[0], c='red', s=120, marker='o',
                          edgecolors='darkred', linewidth=2, label=f'高频起点 ({frequencies[0]:.1f} Hz)')

            if len(real_parts) > 1:
                self.ax.scatter(real_parts[-1], imag_parts[-1], c='blue', s=120, marker='s',
                              edgecolors='darkblue', linewidth=2, label=f'低频终点 ({frequencies[-1]:.1f} Hz)')

        # 颜色条已移除 - 简化界面，避免占用显示空间
        # 频率信息通过起点/终点标记和悬停提示提供

        # 辅助标记绘制（单通道）
        if self.show_assist_markers:
            try:
                import numpy as _np
                # Rs 过零点（取高频一侧）
                rs_val = None
                if len(imag_parts) >= 2:
                    for i in range(len(imag_parts)-1):
                        y1, y2 = imag_parts[i], imag_parts[i+1]
                        if y1 == 0:
                            rs_val = real_parts[i]
                            break
                        if y1 * y2 < 0 or (y1 < 0 <= y2) or (y1 > 0 >= y2):
                            x1, x2 = real_parts[i], real_parts[i+1]
                            rs_val = x1 - y1*(x2-x1)/(y2-y1) if (y2-y1)!=0 else x1
                            break
                if rs_val is not None and _np.isfinite(rs_val):
                    ylim = self.ax.get_ylim()
                    self.ax.axvline(rs_val, color='#2ca02c', linestyle='--', linewidth=1.0, alpha=0.8)
                    self.ax.text(rs_val, ylim[1], f"Rs≈{rs_val:.3f} mΩ", color='#2ca02c', fontsize=9,
                                 rotation=90, va='bottom', ha='right')
                # 半圆正峰
                f_min = 1.0
                freq_arr = _np.array(frequencies, dtype=float)
                real_arr = _np.array(real_parts, dtype=float)
                imag_arr = _np.array(imag_parts, dtype=float)
                pos_mask = (imag_arr >= 0) & (freq_arr >= f_min)
                if _np.any(pos_mask):
                    pos_imag = imag_arr[pos_mask]
                    pos_real = real_arr[pos_mask]
                    peak_idx = int(_np.argmax(pos_imag))
                    peak_im = float(pos_imag[peak_idx])
                    peak_re = float(pos_real[peak_idx])
                    self.ax.scatter([peak_re], [peak_im], s=160, marker='*', color='#ff7f0e', edgecolors='k')
                    self.ax.annotate(f"峰≈{peak_im:.3f} mΩ\nRct≈{(2*peak_im):.3f} mΩ",
                                     xy=(peak_re, peak_im), xytext=(10,10), textcoords='offset points',
                                     fontsize=10, color='#ff7f0e',
                                     bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='none'),
                                     arrowprops=dict(arrowstyle='->', color='#ff7f0e'))

                    # 橙色窗口阴影（放大窗口也显示，稍微更明显）
                    try:
                        f_min = 1.0
                        pmask = (imag_arr >= 0) & (freq_arr >= f_min)
                        if _np.any(pmask):
                            pos_imag = imag_arr[pmask]
                            pos_real = real_arr[pmask]
                            peak_idx = int(_np.argmax(pos_imag))
                            f_peak = float(freq_arr[pmask][peak_idx])
                            f_lo = max(f_min, f_peak / 5.0)
                            f_hi = f_peak * 5.0
                            win_mask = (freq_arr >= f_lo) & (freq_arr <= f_hi) & (imag_arr >= 0)
                            if _np.any(win_mask):
                                x_min_win = float(_np.min(real_arr[win_mask]))
                                x_max_win = float(_np.max(real_arr[win_mask]))
                                self.ax.axvspan(x_min_win, x_max_win, color='#ff7f0e', alpha=0.08, zorder=0)
                    except Exception:
                        pass

                    # 扩散起始参考功能已移除，避免影响图表显示
            except Exception as _e:
                logger.debug(f"放大窗口单通道辅助标记失败: {_e}")

        # 绘制拟合曲线（如果启用）
        if self.show_fitted_curve and len(real_parts) >= 5:
            try:
                fitted_real, fitted_imag = self._generate_fitted_curve(real_parts, imag_parts, frequencies)
                if fitted_real is not None and fitted_imag is not None:
                    self.ax.plot(fitted_real, fitted_imag, 'r-', linewidth=3.0, alpha=0.9, label='拟合曲线')
            except Exception as e:
                logger.warning(f"拟合曲线绘制失败: {e}")

        # 辅助标记（多通道）
        if self.show_assist_markers:
            try:
                import numpy as _np
                for i, (channel_key, channel_data) in enumerate(self.multi_channel_data.items()):
                    details = channel_data.get('details') or []
                    if not details:
                        continue
                    freq = _np.array([d.get('frequency', 0.0) for d in details], dtype=float)
                    real = _np.array([d.get('impedance_real', 0.0) for d in details], dtype=float)
                    imag = _np.array([d.get('impedance_imag', 0.0) for d in details], dtype=float)
                    # Rs（灰色虚线）
                    rs_val = None
                    if len(imag) >= 2:
                        crossings = []
                        for k in range(len(imag) - 1):
                            y1, y2 = imag[k], imag[k+1]
                            if y1 == 0:
                                crossings.append((freq[k], real[k]))
                            elif y1 * y2 < 0 or (y1 < 0 <= y2) or (y1 > 0 >= y2):
                                x1, x2 = real[k], real[k+1]
                                rs_zero = x1 - y1 * (x2 - x1) / (y2 - y1) if (y2 - y1) != 0 else x1
                                f_mid = (freq[k] + freq[k+1]) / 2.0
                                crossings.append((f_mid, float(rs_zero)))
                        if crossings:
                            crossings.sort(key=lambda t: t[0], reverse=True)
                            rs_val = crossings[0][1]
                    if rs_val is not None and _np.isfinite(rs_val):
                        self.ax.axvline(rs_val, color='gray', linestyle=':', linewidth=0.8, alpha=0.5)
                    # 峰值（彩色星标）
                    f_min = 1.0
                    pos_mask = (imag >= 0) & (freq >= f_min)
                    if _np.any(pos_mask):
                        pos_im = imag[pos_mask]
                        pos_re = real[pos_mask]
                        peak_idx = int(_np.argmax(pos_im))
                        peak_im = float(pos_im[peak_idx])
                        peak_re = float(pos_re[peak_idx])
                        self.ax.scatter([peak_re], [peak_im], s=100, marker='*',
                                        color=self._channel_colors[i % len(self._channel_colors)],
                                        edgecolors='k', linewidths=0.8)
                        # 扩散起始参考功能已移除，避免影响图表显示
            except Exception as _e:
                logger.debug(f"放大窗口多通道辅助标记失败: {_e}")

        # 显示图例
        if self.show_legend:
            self.ax.legend(loc='upper right', fontsize=10)

    def _plot_multi_channel_data(self):
        """绘制多通道数据"""
        if not self.multi_channel_data:
            return

        for i, (channel_key, channel_data) in enumerate(self.multi_channel_data.items()):
            details = channel_data['details']
            channel_info = channel_data['channel_info']

            if not details:
                continue

            # 提取数据
            real_parts = []
            imag_parts = []
            frequencies = []

            for detail in details:
                real_mohm = detail.get('impedance_real', 0)
                imag_mohm = detail.get('impedance_imag', 0)
                freq = detail.get('frequency', 0)

                if isinstance(real_mohm, (int, float)) and isinstance(imag_mohm, (int, float)) and freq > 0:
                    real_parts.append(real_mohm)
                    imag_parts.append(imag_mohm)
                    frequencies.append(freq)

            if not real_parts:
                continue

            # 选择颜色
            color = self._channel_colors[i % len(self._channel_colors)]

            # 绘制轨迹线
            if len(real_parts) >= 2:
                if self.show_fitted_curve:
                    self.ax.plot(real_parts, imag_parts, color=color, linewidth=1.5, alpha=0.6,
                               linestyle='-', label=f"{channel_info.get('battery_code', 'N/A')}-Ch{channel_info.get('channel_number', 'N/A')} (原始)")
                else:
                    self.ax.plot(real_parts, imag_parts, color=color, linewidth=2.0, alpha=0.8,
                               label=f"{channel_info.get('battery_code', 'N/A')}-Ch{channel_info.get('channel_number', 'N/A')}")

            # 绘制拟合曲线（如果启用）
            if self.show_fitted_curve and len(real_parts) >= 5:
                try:
                    fitted_real, fitted_imag = self._generate_fitted_curve(real_parts, imag_parts, frequencies)
                    if fitted_real is not None and fitted_imag is not None:
                        self.ax.plot(fitted_real, fitted_imag, color=color, linewidth=3.0, alpha=0.9,
                                   linestyle='-', label=f"{channel_info.get('battery_code', 'N/A')}-Ch{channel_info.get('channel_number', 'N/A')} (拟合)")
                except Exception as e:
                    logger.warning(f"通道{channel_info.get('channel_number')}拟合曲线绘制失败: {e}")

            # 绘制散点图
            self.ax.scatter(real_parts, imag_parts, c=color, s=50, alpha=0.9,
                          edgecolors='white', linewidth=1.0)

        # 显示图例
        if self.show_legend:
            self.ax.legend(loc='best', fontsize=9)

    def _generate_fitted_curve(self, real_parts, imag_parts, frequencies):
        """生成拟合曲线（简化版本）"""
        try:
            if not np or len(real_parts) < 5:
                return None, None

            # 使用简单的移动平均平滑
            window_size = min(3, len(real_parts) // 3)
            if window_size < 2:
                return real_parts, imag_parts

            # 计算移动平均
            fitted_real = []
            fitted_imag = []

            for i in range(len(real_parts)):
                start_idx = max(0, i - window_size // 2)
                end_idx = min(len(real_parts), i + window_size // 2 + 1)

                fitted_real.append(np.mean(real_parts[start_idx:end_idx]))
                fitted_imag.append(np.mean(imag_parts[start_idx:end_idx]))

            return fitted_real, fitted_imag

        except Exception as e:
            logger.error(f"拟合曲线生成失败: {e}")
            return None, None

    def _on_fitted_curve_toggled(self, checked: bool):
        """拟合曲线显示切换"""
        self.show_fitted_curve = checked
        self._replot()

    def _on_assist_toggled(self, checked: bool):
        """辅助标记显示切换"""
        self.show_assist_markers = checked
        self._replot()

    def _on_legend_toggled(self, checked: bool):
        """图例显示切换"""
        self.show_legend = checked
        self._replot()

    def _replot(self):
        """重新绘制图表"""
        if not MATPLOTLIB_AVAILABLE:
            return

        try:
            # 清空图表
            self.ax.clear()

            # 重新设置坐标轴
            self.ax.set_xlabel(f'实部阻抗 ({self.impedance_unit})')
            self.ax.set_ylabel(f'虚部阻抗 ({self.impedance_unit})')
            self.ax.grid(True, alpha=0.3)
            self.ax.set_aspect('equal')

            # 重新设置标题
            if self.multi_channel_data:
                self.ax.set_title(f"多通道奈奎斯特图对比 ({len(self.multi_channel_data)}个通道)")
            elif self.test_result:
                self.ax.set_title(f"奈奎斯特图 - 通道{self.test_result.get('channel_number', 'N/A')} - {self.test_result.get('battery_code', 'N/A')}")
            else:
                self.ax.set_title("奈奎斯特图")

            # 重新绘制数据
            self._plot_data()

        except Exception as e:
            logger.error(f"重新绘制失败: {e}")

    def _reset_view(self):
        """重置视图"""
        if not MATPLOTLIB_AVAILABLE:
            return

        try:
            self.ax.relim()
            self.ax.autoscale()
            self.canvas.draw()
            logger.info("视图已重置")
        except Exception as e:
            logger.error(f"重置视图失败: {e}")

    def _export_image(self):
        """导出图片"""
        try:
            from PyQt5.QtWidgets import QFileDialog

            # 选择保存路径
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出图片", "nyquist_plot.png",
                "PNG图片 (*.png);;JPEG图片 (*.jpg);;PDF文件 (*.pdf)"
            )

            if not filename:
                return

            # 保存图片
            self.figure.savefig(filename, dpi=300, bbox_inches='tight',
                              facecolor='white', edgecolor='none')

            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "导出成功", f"图片已保存到:\n{filename}")
            logger.info(f"图片导出成功: {filename}")

        except Exception as e:
            logger.error(f"导出图片失败: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "导出失败", f"导出图片失败:\n{str(e)}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.window_closed.emit()
        super().closeEvent(event)
        logger.info("放大显示窗口已关闭")
