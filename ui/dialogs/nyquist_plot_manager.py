# -*- coding: utf-8 -*-
"""
奈奎斯特图管理器
负责奈奎斯特图绘制和交互功能

从data_export_dialog.py中提取，遵循单一职责原则

Author: Augment Agent
Date: 2025-06-04
"""

import logging
from typing import List, Dict, Optional
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
                             QGroupBox, QListWidget, QListWidgetItem)
from PyQt5.QtCore import QTimer, Qt

logger = logging.getLogger(__name__)

# matplotlib导入处理
try:
    import numpy as np
    import matplotlib
    matplotlib.use('Qt5Agg')  # 设置后端

    import matplotlib.pyplot as plt
    try:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    except ImportError:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.font_manager as fm

    # 设置中文字体
    try:
        chinese_fonts = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS']
        for font_name in chinese_fonts:
            try:
                plt.rcParams['font.sans-serif'] = [font_name]
                plt.rcParams['axes.unicode_minus'] = False
                logger.debug(f"成功设置matplotlib中文字体: {font_name}")
                break
            except:
                continue
        else:
            logger.warning("未找到合适的中文字体，使用默认字体")
    except Exception as e:
        logger.warning(f"设置matplotlib中文字体失败: {e}")

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

    # 创建占位符类
    class DummyFigureCanvas:
        def __init__(self, *args, **kwargs):
            pass
        def setMinimumSize(self, *args):
            pass
        def draw(self):
            pass
        def draw_idle(self):
            pass
        def mpl_connect(self, *args):
            pass

    class DummyFigure:
        def __init__(self, *args, **kwargs):
            pass
        def add_subplot(self, *args):
            return DummyAxes()
        def clear(self):
            pass

    class DummyAxes:
        def __init__(self):
            pass
        def set_xlabel(self, *args): pass
        def set_ylabel(self, *args): pass
        def set_title(self, *args): pass
        def grid(self, *args, **kwargs): pass
        def set_aspect(self, *args): pass
        def clear(self): pass
        def scatter(self, *args, **kwargs): return None
        def plot(self, *args, **kwargs): return None
        def legend(self, *args, **kwargs): pass
        def set_xlim(self, *args): pass
        def set_ylim(self, *args): pass
        def text(self, *args, **kwargs): pass
        def get_xlim(self): return (0, 1)
        def get_ylim(self): return (0, 1)
        def annotate(self, *args, **kwargs): return None

    FigureCanvas = DummyFigureCanvas
    Figure = DummyFigure
    np = None
    plt = None


class NyquistPlotManager:
    """
    奈奎斯特图管理器

    职责：
    - 管理奈奎斯特图的绘制
    - 处理图表交互（缩放、悬停等）
    - 管理多通道显示
    - 阻抗单位切换功能
    """

    def __init__(self, parent_widget: QWidget):
        """
        初始化奈奎斯特图管理器

        Args:
            parent_widget: 父窗口部件
        """
        self.parent_widget = parent_widget

        # 图表相关变量
        self.nyquist_canvas = None
        self.nyquist_figure = None
        self.nyquist_ax = None

        # 交互相关变量
        self._hover_annotation = None
        self._current_hover_data = None
        self._current_plot_data = []  # 处理后的数据（用于悬停等功能）
        self._original_test_data = []  # 新增保存原始测试数据（用于重绘）

        # 多通道显示相关变量
        self._selected_channels_data = {}
        self._channel_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
        self._multi_channel_mode = False

        # 阻抗单位相关变量 - 固定使用mΩ
        self._impedance_unit = 'mΩ'  # 固定使用毫欧，不再支持单位切换

        # 延迟绘制相关变量
        self._pending_plot_details = None
        self._plot_timer = None

        # 新增智能显示范围设置
        self._use_fixed_range = True  # 使用固定显示范围，避免自动缩放问题
        self._fixed_x_range = (-5, 50)  # 默认X轴范围 (mΩ)
        self._fixed_y_range = (-10, 20)  # 默认Y轴范围 (mΩ)
        self._auto_adjust_range = True  # 自动调整范围以适应数据

        # 新增拟合曲线显示控制
        self._show_fitted_curve = False  # 默认不显示拟合曲线，避免初始问题
        self._fit_curves = {}  # 存储拟合曲线数据 {curve_id: {'real': [], 'imag': [], 'label': ''}}

        # 新增图例显示控制
        self._show_legend = True  # 默认显示图例

        # 新增辅助标记（Rs/半圆峰）显示控制
        self._show_assist_markers = True  # 默认显示辅助标记

        # 创建图表组件
        self._create_plot_components()

        logger.debug("奈奎斯特图管理器初始化完成")

    def _create_plot_components(self):
        """创建图表组件"""
        if not MATPLOTLIB_AVAILABLE:
            from PyQt5.QtWidgets import QLabel
            self.nyquist_canvas = QLabel("奈奎斯特图功能需要安装matplotlib库")
            self.nyquist_canvas.setMinimumSize(400, 300)
            return

        # 创建matplotlib图表
        self.nyquist_figure = Figure(figsize=(8, 6), dpi=100)
        self.nyquist_canvas = FigureCanvas(self.nyquist_figure)
        self.nyquist_canvas.setMinimumSize(400, 300)

        # 创建坐标轴
        self.nyquist_ax = self.nyquist_figure.add_subplot(111)
        self._update_axis_labels()
        self.nyquist_ax.set_title('奈奎斯特图')
        self.nyquist_ax.grid(True, alpha=0.3)
        self.nyquist_ax.set_aspect('equal')

        # 设置鼠标悬停事件
        self._setup_hover_events()

    def get_plot_widget(self) -> QWidget:
        """获取图表组件"""
        return self.nyquist_canvas

    def _update_axis_labels(self):
        """更新坐标轴标签"""
        if not MATPLOTLIB_AVAILABLE or not self.nyquist_ax:
            return

        self.nyquist_ax.set_xlabel(f'实部阻抗 ({self._impedance_unit})')
        self.nyquist_ax.set_ylabel(f'虚部阻抗 ({self._impedance_unit})')

    def set_impedance_unit(self, unit: str):
        """
        设置阻抗单位 - 现在固定为mΩ

        Args:
            unit: 阻抗单位 (固定为 'mΩ')
        """
        if unit != 'mΩ':
            logger.warning(f"系统已简化为固定mΩ单位，忽略单位切换请求: {unit}")
            return

        # 固定使用mΩ单位，无需转换
        self._impedance_unit = 'mΩ'

        # 更新坐标轴标签
        self._update_axis_labels()

        logger.info("阻抗单位固定为: mΩ")

    def get_impedance_unit(self) -> str:
        """获取当前阻抗单位"""
        return self._impedance_unit

    def _convert_impedance_value(self, value_in_mohm: float) -> float:
        """
        阻抗值处理 - 现在固定使用mΩ单位，无需转换

        Args:
            value_in_mohm: mΩ单位的阻抗值

        Returns:
            原始mΩ值（无转换）
        """
        # 固定使用mΩ单位，直接返回原始值
        return value_in_mohm

    def _validate_and_fix_data_range(self, real_parts, imag_parts, valid_data):
        """
        简化的数据验证 - 现在固定使用mΩ单位，无需复杂检测

        Args:
            real_parts: 实部数据列表
            imag_parts: 虚部数据列表
            valid_data: 原始验证数据

        Returns:
            (real_parts, imag_parts) - 固定使用mΩ，直接返回
        """
        # 固定使用mΩ单位，数据已经是正确的，直接返回
        return real_parts, imag_parts



    def _set_fixed_axis_limits(self, real_parts=None, imag_parts=None):
        """设置智能的坐标轴范围"""
        try:
            if not MATPLOTLIB_AVAILABLE or not hasattr(self, 'nyquist_ax') or self.nyquist_ax is None:
                return

            # 智能调整范围
            if self._auto_adjust_range and real_parts and imag_parts:
                # 计算数据范围
                data_x_min, data_x_max = min(real_parts), max(real_parts)
                data_y_min, data_y_max = min(imag_parts), max(imag_parts)
                data_max = max(abs(data_x_max), abs(data_x_min), abs(data_y_max), abs(data_y_min))

                logger.debug(f"🔧 数据范围分析: X[{data_x_min:.3f}, {data_x_max:.3f}], Y[{data_y_min:.3f}, {data_y_max:.3f}], 最大值={data_max:.3f}")

                # 根据数据大小选择合适的显示范围
                if data_max < 0.1:
                    # 数据很小，可能是单位转换错误，使用小范围
                    x_range = (-0.01, 0.1)
                    y_range = (-0.01, 0.01)
                    logger.warning(f"🔧 检测到异常小的数据，使用小范围: X{x_range}, Y{y_range}")
                elif data_max < 1.0:
                    # 数据较小，使用中等范围
                    x_range = (-1, 5)
                    y_range = (-2, 2)
                    logger.debug(f"🔧 数据较小，使用中等范围: X{x_range}, Y{y_range}")
                else:
                    # 数据正常，使用标准范围
                    x_range = self._fixed_x_range
                    y_range = self._fixed_y_range
                    logger.debug(f"🔧 数据正常，使用标准范围: X{x_range}, Y{y_range}")
            else:
                # 使用默认固定范围
                x_range = self._fixed_x_range
                y_range = self._fixed_y_range
                logger.debug(f"🔧 使用默认固定范围: X{x_range}, Y{y_range}")

            # 设置坐标轴范围
            self.nyquist_ax.set_xlim(x_range[0], x_range[1])
            self.nyquist_ax.set_ylim(y_range[0], y_range[1])

            logger.debug(f"设置坐标轴范围完成: X{x_range}, Y{y_range}")

        except Exception as e:
            logger.error(f"设置坐标轴范围失败: {e}")

    def set_fixed_range_enabled(self, enabled: bool, x_range=None, y_range=None):
        """
        设置是否使用固定显示范围

        Args:
            enabled: 是否使用固定范围
            x_range: X轴范围 (min, max)，如果为None则使用默认值
            y_range: Y轴范围 (min, max)，如果为None则使用默认值
        """
        self._use_fixed_range = enabled

        if x_range is not None:
            self._fixed_x_range = x_range
        if y_range is not None:
            self._fixed_y_range = y_range

        logger.info(f"固定显示范围: {'启用' if enabled else '禁用'}")
        if enabled:
            logger.info(f"  X轴范围: {self._fixed_x_range}")
            logger.info(f"  Y轴范围: {self._fixed_y_range}")

    def create_zoom_controls(self) -> QWidget:
        """创建缩放控制按钮组"""
        controls_widget = QWidget()
        controls_widget.setMaximumHeight(80)  # 增加高度以容纳两行控件
        main_layout = QVBoxLayout(controls_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 第一行：缩放控制按钮
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(10)

        # 自动回正按钮
        auto_fit_btn = QPushButton("自动回正")
        auto_fit_btn.setToolTip("重新计算最佳显示范围")
        auto_fit_btn.clicked.connect(self._auto_fit_plot)
        zoom_layout.addWidget(auto_fit_btn)

        # 智能缩放按钮
        smart_zoom_btn = QPushButton("智能缩放")
        smart_zoom_btn.setToolTip("根据数据大小智能调整缩放级别，解决图形太小问题")
        smart_zoom_btn.clicked.connect(self._smart_zoom_plot)
        zoom_layout.addWidget(smart_zoom_btn)

        # 居中显示按钮
        center_btn = QPushButton("居中显示")
        center_btn.setToolTip("以数据中心为基准居中显示")
        center_btn.clicked.connect(self._center_plot)
        zoom_layout.addWidget(center_btn)

        # 重置缩放按钮
        reset_zoom_btn = QPushButton("重置缩放")
        reset_zoom_btn.setToolTip("重置到默认缩放级别")
        reset_zoom_btn.clicked.connect(self._reset_zoom)
        zoom_layout.addWidget(reset_zoom_btn)

        # 完全重建按钮
        rebuild_btn = QPushButton("完全重建")
        rebuild_btn.setToolTip("完全重建matplotlib组件，解决累积问题")
        rebuild_btn.clicked.connect(self._rebuild_and_replot)
        zoom_layout.addWidget(rebuild_btn)

        zoom_layout.addStretch()
        main_layout.addLayout(zoom_layout)

        # 第二行：显示选项控制
        options_layout = QHBoxLayout()
        options_layout.setSpacing(15)

        # 简化移除单位选择器，固定使用mΩ
        from PyQt5.QtWidgets import QLabel
        unit_label = QLabel("阻抗单位: mΩ (固定)")
        unit_label.setToolTip("系统已简化为固定使用毫欧(mΩ)单位")
        options_layout.addWidget(unit_label)

        options_layout.addStretch()

        # 拟合曲线显示复选框
        self.fitted_curve_checkbox = QCheckBox("显示拟合曲线")
        self.fitted_curve_checkbox.setChecked(self._show_fitted_curve)
        self.fitted_curve_checkbox.setToolTip("显示数据平滑后的拟合曲线，有助于观察数据趋势")
        self.fitted_curve_checkbox.toggled.connect(self._on_fitted_curve_toggled)
        options_layout.addWidget(self.fitted_curve_checkbox)

        # 多通道显示复选框
        self.multi_channel_checkbox = QCheckBox("多通道对比显示")
        self.multi_channel_checkbox.setToolTip("选中后可以同时显示多个通道的奈奎斯特图进行对比")
        self.multi_channel_checkbox.toggled.connect(self._on_multi_channel_toggled)
        options_layout.addWidget(self.multi_channel_checkbox)

        # 多通道数据管理区域
        self._create_multi_channel_management_ui(main_layout)

        # 图例显示控制复选框
        self.legend_checkbox = QCheckBox("显示图例")
        self.legend_checkbox.setChecked(self._show_legend)
        self.legend_checkbox.setToolTip("控制图例的显示/隐藏，隐藏图例可避免遮挡数据显示区域")
        self.legend_checkbox.toggled.connect(self._on_legend_toggled)
        # 辅助标记显示复选框
        self.assist_markers_checkbox = QCheckBox("显示辅助标记(Rs/峰值)")
        self.assist_markers_checkbox.setChecked(self._show_assist_markers)
        self.assist_markers_checkbox.setToolTip("在图上标注Rs过零点与半圆峰及窗口")
        self.assist_markers_checkbox.toggled.connect(self._on_assist_markers_toggled)
        options_layout.addWidget(self.assist_markers_checkbox)

        options_layout.addWidget(self.legend_checkbox)

        main_layout.addLayout(options_layout)

        return controls_widget

    def _create_multi_channel_management_ui(self, parent_layout):
        """创建多通道数据管理UI"""
        # 多通道数据管理组
        self.multi_channel_group = QGroupBox("已选择的对比数据")
        self.multi_channel_group.setVisible(False)  # 初始隐藏
        group_layout = QVBoxLayout(self.multi_channel_group)

        # 已选择数据列表
        self.selected_data_list = QListWidget()
        self.selected_data_list.setMaximumHeight(120)
        self.selected_data_list.setToolTip("显示当前已选择的对比数据，双击可移除")
        group_layout.addWidget(self.selected_data_list)

        # 管理按钮布局
        buttons_layout = QHBoxLayout()

        # 移除选中按钮
        self.remove_selected_button = QPushButton("移除选中")
        self.remove_selected_button.setToolTip("移除当前选中的对比数据")
        self.remove_selected_button.clicked.connect(self._on_remove_selected_data)
        buttons_layout.addWidget(self.remove_selected_button)

        # 清空所有按钮
        self.clear_all_button = QPushButton("清空所有")
        self.clear_all_button.setToolTip("清空所有已选择的对比数据")
        self.clear_all_button.clicked.connect(self._on_clear_all_data)
        buttons_layout.addWidget(self.clear_all_button)

        buttons_layout.addStretch()
        group_layout.addLayout(buttons_layout)

        parent_layout.addWidget(self.multi_channel_group)

        # 连接双击事件
        self.selected_data_list.itemDoubleClicked.connect(self._on_data_item_double_clicked)

    def _on_fitted_curve_toggled(self, checked: bool):
        """拟合曲线显示切换处理"""
        self._show_fitted_curve = checked
        logger.debug(f" 拟合曲线显示切换: {'启用' if checked else '禁用'}")
        logger.debug(f"🔧 当前数据状态: _current_plot_data={'有数据' if self._current_plot_data else '无数据'}")

        # 重新绘制当前图表
        if self._current_plot_data:
            logger.debug(f"🔧 开始重新绘制图表...")
            self._redraw_current_plot()
            # 强制刷新画布，确保显示更新
            if hasattr(self, 'nyquist_canvas') and self.nyquist_canvas:
                self.nyquist_canvas.draw_idle()
                self.nyquist_canvas.flush_events()
                logger.debug(f"🔧 画布刷新完成")
        else:
            logger.warning(f"🔧 无当前数据，跳过重绘")

    def _on_multi_channel_toggled(self, checked: bool):
        """多通道显示切换处理"""
        self._multi_channel_mode = checked
        logger.info(f"多通道对比显示: {'启用' if checked else '禁用'}")

        # 控制数据管理UI的显示
        if hasattr(self, 'multi_channel_group'):
            self.multi_channel_group.setVisible(checked)
            if checked:
                self._update_selected_data_list()

        if checked:
            # 启用多通道模式时，如果有选中的数据，切换到多通道显示
            if self._selected_channels_data:
                self._update_multi_channel_display()
        else:
            # 禁用多通道模式时，如果有当前数据，显示单通道
            if self._current_plot_data:
                self._redraw_current_plot()

    def _redraw_current_plot(self):
        """重新绘制当前图表"""
        if not self._original_test_data:
            logger.warning("🔧 _redraw_current_plot: 无原始数据")
            return

        logger.debug(f"🔧 _redraw_current_plot: 原始数据点数={len(self._original_test_data)}")

        if self._multi_channel_mode and self._selected_channels_data:
            logger.debug("🔧 _redraw_current_plot: 使用多通道模式")
            self._update_multi_channel_display()
        else:
            # 修复使用原始数据重新调用完整的绘制流程
            logger.debug("🔧 _redraw_current_plot: 使用单通道模式，重新处理原始数据")

            # 重新调用完整的绘制流程，这样会重新处理数据并应用拟合曲线设置
            if hasattr(self, '_last_test_result'):
                self.update_single_channel_plot(self._original_test_data, self._last_test_result)
            else:
                self.update_single_channel_plot(self._original_test_data)

    def _on_legend_toggled(self, checked: bool):
        """图例显示切换处理"""
        self._show_legend = checked
        logger.info(f"图例显示: {'启用' if checked else '禁用'}")

        # 重新绘制当前图表以应用图例设置
    def _on_assist_markers_toggled(self, checked: bool):
        """辅助标记显示切换处理"""
        self._show_assist_markers = checked
        logger.info(f"辅助标记显示: {'启用' if checked else '禁用'}")
        if self._current_plot_data:
            self._redraw_current_plot()
            if hasattr(self, 'nyquist_canvas') and self.nyquist_canvas:
                self.nyquist_canvas.draw_idle()
                self.nyquist_canvas.flush_events()

        if self._current_plot_data:
            self._redraw_current_plot()
        else:
            logger.debug("无当前数据，跳过重绘")

    def update_single_channel_plot(self, details: List[Dict], test_result: Dict = None):
        """更新单通道奈奎斯特图 - 完全重写版本，修复显示问题"""
        try:
            logger.debug(f"开始更新单通道奈奎斯特图，数据点数: {len(details) if details else 0}")

            if not MATPLOTLIB_AVAILABLE or not details:
                self._clear_plot()
                return

            # 保存原始数据和测试结果用于重绘
            self._original_test_data = details.copy()  # 保存原始测试数据
            self._last_test_result = test_result
            logger.debug(f"🔧 保存原始数据: {len(self._original_test_data)}个点")

            # 如果启用了多通道模式，将数据添加到选中通道数据中
            if self._multi_channel_mode and test_result:
                # 修复使用通道号和电池码组合作为键值，支持同一通道不同电池码的对比
                channel_number = test_result.get('channel_number', 'unknown')
                battery_code = test_result.get('battery_code', 'unknown')
                channel_key = f"ch_{channel_number}_{battery_code}"
                self._selected_channels_data[channel_key] = {
                    'details': details,
                    'channel_info': test_result
                }
                self._update_multi_channel_display()
                return

            # 清空之前的图表
            self.nyquist_ax.clear()

            # 提取并验证数据
            valid_data = []
            for detail in details:
                real_mohm = detail.get('impedance_real', 0)  # mΩ
                imag_mohm = detail.get('impedance_imag', 0)  # mΩ
                freq = detail.get('frequency', 0)

                # 数据验证
                if isinstance(real_mohm, (int, float)) and isinstance(imag_mohm, (int, float)) and freq > 0:
                    # 应用单位转换
                    real_converted = self._convert_impedance_value(real_mohm)
                    imag_converted = self._convert_impedance_value(imag_mohm)



                    valid_data.append({
                        'real': real_converted,
                        'imag': imag_converted,
                        'real_mohm': real_mohm,  # 保留原始mΩ值用于悬停显示
                        'imag_mohm': imag_mohm,
                        'frequency': freq,
                        'sequence': detail.get('test_sequence', 0)
                    })

            if not valid_data:
                logger.warning("没有有效的阻抗数据")
                self._clear_plot()
                return

            # 按频率排序（从高频到低频，这是奈奎斯特图的标准顺序）
            valid_data.sort(key=lambda x: x['frequency'], reverse=True)

            # 提取排序后的数据
            real_parts = [d['real'] for d in valid_data]
            imag_parts = [d['imag'] for d in valid_data]
            frequencies = [d['frequency'] for d in valid_data]

            logger.debug(f"🔧 提取数据: 点数={len(real_parts)}")
            if real_parts:
                logger.debug(f"🔧 实部范围: [{min(real_parts):.3f}, {max(real_parts):.3f}]")
                logger.debug(f"🔧 虚部范围: [{min(imag_parts):.3f}, {max(imag_parts):.3f}]")
                logger.debug(f"🔧 频率范围: [{min(frequencies):.1f}, {max(frequencies):.1f}] Hz")

            # 数据范围检查和修正
            real_parts, imag_parts = self._validate_and_fix_data_range(real_parts, imag_parts, valid_data)



            # 绘制奈奎斯特图
            self._draw_nyquist_plot(real_parts, imag_parts, frequencies, test_result)

            # 保存当前数据用于悬停功能
            self._current_plot_data = valid_data

            # 新增数据更新后自动应用最佳缩放
            self._apply_auto_scaling_if_needed(real_parts, imag_parts)

            logger.debug("单通道奈奎斯特图更新完成")

        except Exception as e:
            logger.error(f"更新单通道奈奎斯特图失败: {e}")
            self._clear_plot()

    def _draw_nyquist_plot(self, real_parts, imag_parts, frequencies, test_result=None):
        """绘制奈奎斯特图的核心方法 - 修复颜色条重复问题"""
        try:
            if not MATPLOTLIB_AVAILABLE:
                return

            # 完全清理图形，包括所有子图和颜色条
            self.nyquist_figure.clear()

            # 重新创建坐标轴
            self.nyquist_ax = self.nyquist_figure.add_subplot(111)

            # 设置标题和标签
            if test_result:
                title = f"奈奎斯特图 - 通道{test_result.get('channel_number', 'N/A')} - {test_result.get('battery_code', 'N/A')}"
            else:
                title = "奈奎斯特图"
            self.nyquist_ax.set_title(title)

            # 使用当前单位设置坐标轴标签
            self._update_axis_labels()

            # 检查数据点数量
            if len(real_parts) < 3:
                logger.warning(f"数据点太少({len(real_parts)}个)，无法绘制完整奈奎斯特图")
                # 仍然绘制，但添加警告文本
                self.nyquist_ax.text(0.5, 0.95, f'数据点不足({len(real_parts)}个)',
                                   transform=self.nyquist_ax.transAxes,
                                   ha='center', va='top',
                                   bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

            # 绘制原始数据连线（奈奎斯特图的特征）
            has_line_plot = False
            logger.debug(f"🔧 准备绘制原始数据连线: 数据点数={len(real_parts)}, 拟合曲线={'启用' if self._show_fitted_curve else '禁用'}")

            if len(real_parts) >= 2:
                # 根据是否显示拟合曲线调整原始数据线条的样式
                try:
                    if self._show_fitted_curve:
                        # 有拟合曲线时，原始数据线条稍微淡一些
                        logger.debug(f"🔧 绘制原始数据线条 (拟合模式): 'b-', linewidth=2.0, alpha=0.6")
                        line_objects = self.nyquist_ax.plot(real_parts, imag_parts,
                                           'b-', linewidth=2.0, alpha=0.6,
                                           label='原始数据')
                    else:
                        # 没有拟合曲线时，原始数据线条更突出
                        logger.debug(f"🔧 绘制原始数据线条 (普通模式): 'b-', linewidth=2.5, alpha=0.8")
                        line_objects = self.nyquist_ax.plot(real_parts, imag_parts,
                                           'b-', linewidth=2.5, alpha=0.8,
                                           label='阻抗轨迹')

                    # 检查plot()方法的返回值
                    if line_objects:
                        has_line_plot = True
                        logger.debug(f"🔧 原始数据线条绘制成功: {len(line_objects)}个线条对象")
                    else:
                        logger.error(f"🔧 原始数据线条绘制失败: plot()返回空列表")

                except Exception as e:
                    logger.error(f"🔧 原始数据线条绘制异常: {e}")

                logger.debug(f"🔧 原始数据线条绘制完成: has_line_plot={has_line_plot}")
            else:
                logger.warning(f"数据点不足，无法绘制连线: {len(real_parts)}个点")

            # 新增绘制拟合曲线（如果启用）
            has_fitted_curve = False
            fitted_real, fitted_imag = None, None
            logger.debug(f"🔧 检查拟合曲线绘制条件: 启用={self._show_fitted_curve}, 数据点数={len(real_parts)}")

            if self._show_fitted_curve and len(real_parts) >= 5:
                logger.debug(f"🔧 开始生成拟合曲线...")
                try:
                    fitted_real, fitted_imag = self._generate_fitted_curve(real_parts, imag_parts, frequencies)
                    if fitted_real is not None and fitted_imag is not None:
                        logger.debug(f"🔧 绘制拟合曲线: 'r-', linewidth=3.0, alpha=0.8, 点数={len(fitted_real)}")
                        fitted_line_objects = self.nyquist_ax.plot(fitted_real, fitted_imag,
                                           'r-', linewidth=3.0, alpha=0.8,
                                           label='拟合曲线', zorder=5)

                        # 检查拟合曲线绘制结果
                        if fitted_line_objects:
                            has_fitted_curve = True
                            logger.debug(f"🔧 拟合曲线绘制成功: {len(fitted_line_objects)}个线条对象")
                        else:
                            logger.error(f"🔧 拟合曲线绘制失败: plot()返回空列表")

                        logger.debug(f"🔧 拟合曲线绘制完成: has_fitted_curve={has_fitted_curve}")
                    else:
                        logger.warning(f"🔧 拟合曲线生成失败: fitted_real={fitted_real}, fitted_imag={fitted_imag}")
                except Exception as e:
                    logger.error(f"🔧 拟合曲线绘制异常: {e}")
            elif self._show_fitted_curve:
                logger.warning(f"🔧 数据点不足，无法绘制拟合曲线: {len(real_parts)}个点 < 5")

            # 绘制数据点，使用频率作为颜色映射
            if len(real_parts) > 0:
                scatter = self.nyquist_ax.scatter(real_parts, imag_parts,
                                                c=frequencies, cmap='plasma',
                                                s=80, alpha=0.9, edgecolors='white',
                                                linewidth=1.5)

                # 标记起始点和结束点
                if len(real_parts) > 0:
                    # 高频起始点（红色圆圈）
                    self.nyquist_ax.scatter(real_parts[0], imag_parts[0],
                                           c='red', s=120, marker='o',
                                           edgecolors='darkred', linewidth=2,
                                           label=f'高频起点 ({frequencies[0]:.1f} Hz)')

                    if len(real_parts) > 1:
                        # 低频结束点（蓝色方块）
                        self.nyquist_ax.scatter(real_parts[-1], imag_parts[-1],
                                               c='blue', s=120, marker='s',
                                               edgecolors='darkblue', linewidth=2,
                                               label=f'低频终点 ({frequencies[-1]:.1f} Hz)')

                # 颜色条已移除 - 简化界面，避免占用显示空间
                # 频率信息通过起点/终点标记和悬停提示提供

            # 添加图例（只有在启用图例显示且有线条绘制时才显示）
            logger.debug(f"🔧 图例显示条件: show_legend={self._show_legend}, has_line_plot={has_line_plot}, has_fitted_curve={has_fitted_curve}")
            if self._show_legend and (has_line_plot or has_fitted_curve):
                self.nyquist_ax.legend(loc='upper right', fontsize=8)
                logger.debug(f"🔧 图例已显示")
            else:
                logger.debug(f"🔧 无图例显示（图例禁用或无线条绘制）")

            # 设置网格
            self.nyquist_ax.grid(True, alpha=0.3)

            # 修复使用智能显示范围，避免自动缩放导致的单位转换问题
            if self._use_fixed_range:
                self._set_fixed_axis_limits(real_parts, imag_parts)
                logger.debug(f"使用智能显示范围")
            else:
                # 备用：自适应缩放（如果需要的话）
                all_real_data = real_parts.copy()
                all_imag_data = imag_parts.copy()

                if has_fitted_curve and fitted_real is not None and fitted_imag is not None:
                    all_real_data.extend(fitted_real)
                    all_imag_data.extend(fitted_imag)

                self._set_optimal_axis_limits(all_real_data, all_imag_data)

            # 设置等比例（奈奎斯特图的重要特性）
            self.nyquist_ax.set_aspect('equal')
            # === 辅助标记：Rs（虚部过零点）与半圆峰窗口 ===
            if getattr(self, '_show_assist_markers', True):
                try:
                    import numpy as _np
                    # 计算Rs：虚部过零点（选取频率更高的一次过零）
                    rs_value = None
                    if len(imag_parts) >= 2:
                        crossings = []
                        for i in range(len(imag_parts) - 1):
                            y1, y2 = imag_parts[i], imag_parts[i + 1]
                            if y1 == 0:
                                crossings.append((frequencies[i], real_parts[i]))
                            elif y1 * y2 < 0 or (y1 < 0 <= y2) or (y1 > 0 >= y2):
                                # 线性插值：以虚部为自变量求实轴截距
                                x1, x2 = real_parts[i], real_parts[i + 1]
                                rs_zero = x1 - y1 * (x2 - x1) / (y2 - y1) if (y2 - y1) != 0 else x1
                                f_mid = (frequencies[i] + frequencies[i + 1]) / 2.0
                                crossings.append((f_mid, float(rs_zero)))
                        if crossings:
                            # 选择频率更高的过零点
                            crossings.sort(key=lambda t: t[0], reverse=True)
                            rs_value = crossings[0][1]
                    # 绘制Rs垂线与标注
                    if rs_value is not None and _np.isfinite(rs_value):
                        try:
                            ylim = self.nyquist_ax.get_ylim()
                            # 确保ylim是有效的
                            if ylim and len(ylim) >= 2 and _np.isfinite(ylim[1]):
                                self.nyquist_ax.axvline(rs_value, color='#2ca02c', linestyle='--', linewidth=1.2, alpha=0.8)
                                self.nyquist_ax.text(rs_value, ylim[1], f"Rs≈{rs_value:.3f} mΩ",
                                                     color='#2ca02c', fontsize=8, rotation=90,
                                                     va='bottom', ha='right', alpha=0.9,
                                                     bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.6, edgecolor='none'))
                        except Exception as rs_e:
                            logger.debug(f"Rs标记绘制失败: {rs_e}")
                            # 简化版本：只绘制垂线，不加文字
                            self.nyquist_ax.axvline(rs_value, color='#2ca02c', linestyle='--', linewidth=1.2, alpha=0.8)
                    # 半圆正虚部峰与频率窗口（f_min=1Hz, 窗口= [f_peak/5, f_peak*5]）
                    try:
                        f_min = 1.0
                        freq_arr = _np.array(frequencies, dtype=float)
                        real_arr = _np.array(real_parts, dtype=float)
                        imag_arr = _np.array(imag_parts, dtype=float)
                        pos_mask = (imag_arr >= 0) & (freq_arr >= f_min)
                        if _np.any(pos_mask):
                            pos_imag = imag_arr[pos_mask]
                            pos_real = real_arr[pos_mask]
                            pos_freq = freq_arr[pos_mask]
                            peak_idx_local = int(_np.argmax(pos_imag))
                            peak_imag = float(pos_imag[peak_idx_local])
                            peak_real = float(pos_real[peak_idx_local])
                            f_peak = float(pos_freq[peak_idx_local])

                            # 确保峰值数据有效
                            if _np.isfinite(peak_real) and _np.isfinite(peak_imag):
                                # 频率窗口（围绕峰值，避免扩散尾）
                                f_lo = max(f_min, f_peak / 5.0)
                                f_hi = f_peak * 5.0
                                win_mask = (freq_arr >= f_lo) & (freq_arr <= f_hi) & (imag_arr >= 0)
                                if _np.any(win_mask):
                                    try:
                                        x_min_win = float(_np.min(real_arr[win_mask]))
                                        x_max_win = float(_np.max(real_arr[win_mask]))
                                        # 在x范围上绘制半透明窗口
                                        if _np.isfinite(x_min_win) and _np.isfinite(x_max_win):
                                            self.nyquist_ax.axvspan(x_min_win, x_max_win, color='#ff7f0e', alpha=0.08)
                                    except Exception as win_e:
                                        logger.debug(f"频率窗口绘制失败: {win_e}")

                                # 标出峰点（主图略小，放大窗口更大）
                                try:
                                    self.nyquist_ax.scatter([peak_real], [peak_imag], s=130, marker='*',
                                                            color='#ff7f0e', edgecolors='k', linewidths=0.8, zorder=6)
                                    self.nyquist_ax.annotate(f"峰≈{peak_imag:.3f} mΩ\nRct≈{(2*peak_imag):.3f} mΩ",
                                                              xy=(peak_real, peak_imag), xytext=(10, 10), textcoords='offset points',
                                                              fontsize=9, color='#ff7f0e',
                                                              bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='none'),
                                                              arrowprops=dict(arrowstyle='->', color='#ff7f0e'))
                                except Exception as peak_e:
                                    logger.debug(f"峰值标记绘制失败: {peak_e}")
                    except Exception as peak_section_e:
                        logger.debug(f"峰值处理失败: {peak_section_e}")

                    # 扩散起始参考功能已移除，避免影响图表显示
                except Exception as _ann_e:
                    logger.debug(f"辅助标记绘制失败: {_ann_e}")


            # 调整布局以防止颜色条重叠
            self.nyquist_figure.tight_layout()

            # 刷新画布
            self.nyquist_canvas.draw()

        except Exception as e:
            logger.error(f"绘制奈奎斯特图失败: {e}")
            raise

    def update_multi_channel_plot(self, all_channel_data: Dict):
        """更新多通道奈奎斯特图"""
        try:
            logger.debug(f"开始更新多通道奈奎斯特图，通道数: {len(all_channel_data) if all_channel_data else 0}")

            if not MATPLOTLIB_AVAILABLE or not all_channel_data:
                self._clear_plot()
                return

            # 清空之前的图表
            self.nyquist_ax.clear()

            # 重新设置坐标轴标签和标题
            self._update_axis_labels()
            self.nyquist_ax.set_title(f"多通道奈奎斯特图对比 ({len(all_channel_data)}个通道)")

            # 绘制多个通道的数据
            all_real_parts = []
            all_imag_parts = []
            legend_labels = []

            # 保存数据点信息用于悬停功能
            self._current_plot_data = []

            for i, (channel_key, channel_data) in enumerate(all_channel_data.items()):
                details = channel_data['details']
                channel_info = channel_data['channel_info']

                if not details:
                    continue

                # 提取数据并应用单位转换
                real_parts = []
                imag_parts = []

                for detail in details:
                    real_mohm = detail.get('impedance_real', 0)  # 数据本身是mΩ
                    imag_mohm = detail.get('impedance_imag', 0)  # 数据本身是mΩ

                    # 应用单位转换
                    real_converted = self._convert_impedance_value(real_mohm)
                    imag_converted = self._convert_impedance_value(imag_mohm)

                    real_parts.append(real_converted)
                    imag_parts.append(imag_converted)

                    # 保存数据点信息
                    self._current_plot_data.append({
                        'real': real_converted,
                        'imag': imag_converted,
                        'real_mohm': real_mohm,  # 保留原始mΩ值
                        'imag_mohm': imag_mohm,
                        'frequency': detail.get('frequency', 0),
                        'sequence': detail.get('test_sequence', 0),
                        'channel': channel_info.get('channel_number', 'N/A'),
                        'battery_code': channel_info.get('battery_code', 'N/A')
                    })

                # 选择颜色
                color = self._channel_colors[i % len(self._channel_colors)]

                # 提取频率数据用于拟合曲线
                frequencies = [detail.get('frequency', 0) for detail in details]

                # 绘制轨迹线（连接各数据点）
                if len(real_parts) >= 2:
                    # 根据是否显示拟合曲线调整原始数据线条的样式
                    if self._show_fitted_curve:
                        # 有拟合曲线时，原始数据线条稍微淡一些
                        self.nyquist_ax.plot(real_parts, imag_parts,
                                           color=color, linewidth=1.5, alpha=0.6,
                                           linestyle='-',
                                           label=f"{channel_info.get('battery_code', 'N/A')}-Ch{channel_info.get('channel_number', 'N/A')} (原始)")
                    else:
                        # 没有拟合曲线时，原始数据线条更突出
                        self.nyquist_ax.plot(real_parts, imag_parts,
                                           color=color, linewidth=2.0, alpha=0.8,
                                           label=f"{channel_info.get('battery_code', 'N/A')}-Ch{channel_info.get('channel_number', 'N/A')}")

                # 绘制拟合曲线（如果启用）
                if self._show_fitted_curve and len(real_parts) >= 5:
                    try:
                        fitted_real, fitted_imag = self._generate_fitted_curve(real_parts, imag_parts, frequencies)
                        if fitted_real is not None and fitted_imag is not None:
                            # 使用相同颜色但更粗的线条绘制拟合曲线
                            self.nyquist_ax.plot(fitted_real, fitted_imag,
                                               color=color, linewidth=3.0, alpha=0.9,
                                               linestyle='-',
                                               label=f"{channel_info.get('battery_code', 'N/A')}-Ch{channel_info.get('channel_number', 'N/A')} (拟合)")
                            logger.debug(f"通道{channel_info.get('channel_number')}拟合曲线绘制成功")
                        else:
                            logger.warning(f"通道{channel_info.get('channel_number')}拟合曲线生成失败")
                    except Exception as e:
                        logger.error(f"通道{channel_info.get('channel_number')}拟合曲线绘制异常: {e}")

                # 绘制散点图
                self.nyquist_ax.scatter(real_parts, imag_parts,
                                      c=color, s=50, alpha=0.9,
                                      edgecolors='white', linewidth=1.0)



                # 辅助标记（当前通道的Rs与峰值），受全局开关控制
                if getattr(self, '_show_assist_markers', True):
                    try:
                        import numpy as _np
                        freq = _np.array(frequencies, dtype=float)
                        real_arr = _np.array(real_parts, dtype=float)
                        imag_arr = _np.array(imag_parts, dtype=float)
                        # Rs：过零点取高频一侧
                        rs_val = None
                        if len(imag_arr) >= 2:
                            crossings = []
                            for k in range(len(imag_arr) - 1):
                                y1, y2 = imag_arr[k], imag_arr[k+1]
                                if y1 == 0:
                                    crossings.append((freq[k], real_arr[k]))
                                elif y1 * y2 < 0 or (y1 < 0 <= y2) or (y1 > 0 >= y2):
                                    x1, x2 = real_arr[k], real_arr[k+1]
                                    rs_zero = x1 - y1 * (x2 - x1) / (y2 - y1) if (y2 - y1) != 0 else x1
                                    f_mid = (freq[k] + freq[k+1]) / 2.0
                                    crossings.append((f_mid, float(rs_zero)))
                            if crossings:
                                crossings.sort(key=lambda t: t[0], reverse=True)
                                rs_val = crossings[0][1]
                        if rs_val is not None and _np.isfinite(rs_val):
                            self.nyquist_ax.axvline(rs_val, color='gray', linestyle=':', linewidth=0.8, alpha=0.5)
                        # 正峰与窗口
                        f_min = 1.0
                        pos_mask = (imag_arr >= 0) & (freq >= f_min)
                        if _np.any(pos_mask):
                            pos_im = imag_arr[pos_mask]
                            pos_re = real_arr[pos_mask]
                            peak_idx = int(_np.argmax(pos_im))
                            peak_im = float(pos_im[peak_idx])
                            peak_re = float(pos_re[peak_idx])
                            self.nyquist_ax.scatter([peak_re], [peak_im], s=60, marker='*',
                                                    color=color,
                                                    edgecolors='k', linewidths=0.6, zorder=5)
                            # 扩散起始参考功能已移除，避免影响图表显示
                    except Exception as _e:
                        logger.debug(f"多通道辅助标记绘制失败: {_e}")

                # 收集所有数据点用于设置坐标轴范围
                all_real_parts.extend(real_parts)
                all_imag_parts.extend(imag_parts)

                # 添加图例标签（已在plot中设置，这里不再重复添加）
                # legend_labels.append(f"通道{channel_info.get('channel_number', 'N/A')} - {channel_info.get('battery_code', 'N/A')}")

            # 添加图例（图例标签已在plot方法中设置，只有在启用图例显示时才显示）
            if self._show_legend:
                self.nyquist_ax.legend(loc='best', fontsize=8)
                logger.debug("多通道图例已显示")
            else:
                logger.debug("多通道图例已隐藏")

            # 设置网格和等比例
            self.nyquist_ax.grid(True, alpha=0.3)
            self.nyquist_ax.set_aspect('equal')

            # 设置坐标轴范围
            if all_real_parts and all_imag_parts:
                self._set_optimal_axis_limits(all_real_parts, all_imag_parts)

            # 刷新画布
            self.nyquist_canvas.draw()

            logger.debug("多通道奈奎斯特图更新完成")

        except Exception as e:
            logger.error(f"更新多通道奈奎斯特图失败: {e}")
            self._clear_plot()

    def clear_plot(self):
        """清空奈奎斯特图"""
        self._clear_plot()

    def _clear_plot(self):
        """内部清空图表方法"""
        try:
            if not MATPLOTLIB_AVAILABLE:
                return

            self.nyquist_ax.clear()
            self._update_axis_labels()
            self.nyquist_ax.set_title('奈奎斯特图')
            self.nyquist_ax.grid(True, alpha=0.3)
            self.nyquist_ax.set_aspect('equal')

            # 清空数据
            self._current_plot_data = []
            self._original_test_data = []  # 同时清空原始数据

            # 刷新画布
            self.nyquist_canvas.draw()

        except Exception as e:
            logger.error(f"清空奈奎斯特图失败: {e}")

    def _update_multi_channel_display(self):
        """更新多通道显示"""
        if not self._multi_channel_mode or not self._selected_channels_data:
            return

        try:
            logger.debug(f"更新多通道显示，通道数: {len(self._selected_channels_data)}")
            self.update_multi_channel_plot(self._selected_channels_data)
        except Exception as e:
            logger.error(f"更新多通道显示失败: {e}")

    def add_channel_to_comparison(self, details: List[Dict], test_result: Dict):
        """
        添加通道到多通道对比中

        Args:
            details: 阻抗明细数据
            test_result: 测试结果信息
        """
        if not test_result:
            return

        # 修复使用通道号和电池码组合作为键值，支持同一通道不同电池码的对比
        channel_number = test_result.get('channel_number', 'unknown')
        battery_code = test_result.get('battery_code', 'unknown')
        channel_key = f"ch_{channel_number}_{battery_code}"

        self._selected_channels_data[channel_key] = {
            'details': details,
            'channel_info': test_result
        }

        if self._multi_channel_mode:
            self._update_multi_channel_display()

        # 更新已选择数据列表UI
        self._update_selected_data_list()

        logger.info(f"通道{channel_number}电池码{battery_code}已添加到对比显示")

    def remove_channel_from_comparison(self, channel_key: str):
        """
        从多通道对比中移除指定数据

        Args:
            channel_key: 数据键值 (格式: ch_{channel_number}_{battery_code})
        """
        if channel_key in self._selected_channels_data:
            channel_info = self._selected_channels_data[channel_key].get('channel_info', {})
            channel_number = channel_info.get('channel_number', 'unknown')
            battery_code = channel_info.get('battery_code', 'unknown')

            del self._selected_channels_data[channel_key]

            if self._multi_channel_mode:
                self._update_multi_channel_display()

            # 更新已选择数据列表UI
            self._update_selected_data_list()

            logger.info(f"通道{channel_number}电池码{battery_code}已从对比显示中移除")

    def clear_all_channels(self):
        """清空所有通道数据"""
        self._selected_channels_data.clear()
        self._clear_plot()

        # 更新已选择数据列表UI
        self._update_selected_data_list()

        logger.info("已清空所有通道对比数据")

    def _update_selected_data_list(self):
        """更新已选择数据列表"""
        if not hasattr(self, 'selected_data_list'):
            return

        self.selected_data_list.clear()

        for channel_key, data in self._selected_channels_data.items():
            channel_info = data.get('channel_info', {})
            channel_number = channel_info.get('channel_number', 'unknown')
            battery_code = channel_info.get('battery_code', 'unknown')

            # 创建显示文本
            display_text = f"{battery_code}-Ch{channel_number}"

            # 创建列表项
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, channel_key)  # 存储键值用于删除
            item.setToolTip(f"通道: {channel_number}\n电池码: {battery_code}\n双击移除")

            self.selected_data_list.addItem(item)

        # 更新按钮状态
        has_data = len(self._selected_channels_data) > 0
        if hasattr(self, 'remove_selected_button'):
            self.remove_selected_button.setEnabled(has_data)
        if hasattr(self, 'clear_all_button'):
            self.clear_all_button.setEnabled(has_data)

    def _on_remove_selected_data(self):
        """移除选中的数据"""
        current_item = self.selected_data_list.currentItem()
        if current_item:
            channel_key = current_item.data(Qt.UserRole)
            if channel_key:
                self.remove_channel_from_comparison(channel_key)

    def _on_clear_all_data(self):
        """清空所有数据"""
        self.clear_all_channels()

    def _on_data_item_double_clicked(self, item):
        """数据项双击处理"""
        channel_key = item.data(Qt.UserRole)
        if channel_key:
            self.remove_channel_from_comparison(channel_key)

    def _setup_hover_events(self):
        """设置鼠标悬停事件"""
        if not MATPLOTLIB_AVAILABLE:
            return

        def on_hover(event):
            """鼠标悬停事件处理"""
            try:
                if event.inaxes != self.nyquist_ax:
                    self._hide_hover_annotation()
                    return

                # 查找最近的数据点
                point_data = self._find_closest_point(event.xdata, event.ydata)
                if point_data:
                    self._show_hover_annotation(event, point_data)
                else:
                    self._hide_hover_annotation()

            except Exception as e:
                logger.debug(f"悬停事件处理失败: {e}")

        # 连接事件
        self.nyquist_canvas.mpl_connect('motion_notify_event', on_hover)

    def _find_closest_point(self, x, y):
        """查找最近的数据点"""
        if not MATPLOTLIB_AVAILABLE or not self._current_plot_data:
            return None

        try:
            min_distance = float('inf')
            closest_point = None

            for point in self._current_plot_data:
                distance = ((point['real'] - x) ** 2 + (point['imag'] - y) ** 2) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    closest_point = point

            # 只有距离足够近才显示
            if min_distance < 50:  # 调整这个阈值来控制敏感度
                return closest_point

            return None

        except Exception as e:
            logger.debug(f"查找最近数据点失败: {e}")
            return None

    def _show_hover_annotation(self, event, point_data):
        """显示悬停标注"""
        if not MATPLOTLIB_AVAILABLE:
            return

        try:
            # 移除之前的标注
            self._hide_hover_annotation()

            # 获取原始mΩ值用于显示（更准确）
            real_mohm = point_data.get('real_mohm', point_data.get('real', 0))
            imag_mohm = point_data.get('imag_mohm', point_data.get('imag', 0))

            # 根据当前单位转换显示值
            real_display = self._convert_impedance_value(real_mohm) if 'real_mohm' in point_data else point_data.get('real', 0)
            imag_display = self._convert_impedance_value(imag_mohm) if 'imag_mohm' in point_data else point_data.get('imag', 0)

            # 创建标注文本 - 改为3位小数显示
            if 'channel' in point_data:
                # 多通道模式
                text = f"通道: {point_data['channel']}\n电池: {point_data['battery_code']}\n频率: {point_data['frequency']:.3f} Hz\n实部: {real_display:.3f} {self._impedance_unit}\n虚部: {imag_display:.3f} {self._impedance_unit}"
            else:
                # 单通道模式
                text = f"频率: {point_data['frequency']:.3f} Hz\n实部: {real_display:.3f} {self._impedance_unit}\n虚部: {imag_display:.3f} {self._impedance_unit}\n序号: {point_data['sequence']}"

            # 智能定位标注位置，避免遮挡数据
            # 获取图表范围
            xlim = self.nyquist_ax.get_xlim()
            ylim = self.nyquist_ax.get_ylim()
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]

            # 根据数据点位置调整标注位置
            x_pos = point_data['real']
            y_pos = point_data['imag']

            # 计算相对位置
            x_rel = (x_pos - xlim[0]) / x_range
            y_rel = (y_pos - ylim[0]) / y_range

            # 智能选择标注位置
            if x_rel > 0.7:  # 右侧
                xytext = (-80, 20)
            elif x_rel < 0.3:  # 左侧
                xytext = (80, 20)
            else:  # 中间
                if y_rel > 0.7:  # 上方
                    xytext = (20, -60)
                else:  # 下方
                    xytext = (20, 60)

            # 创建标注
            self._hover_annotation = self.nyquist_ax.annotate(
                text,
                xy=(x_pos, y_pos),
                xytext=xytext, textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.9, edgecolor='gray'),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.1", color='gray'),
                fontsize=8,
                ha='left'
            )

            # 刷新画布
            self.nyquist_canvas.draw_idle()

        except Exception as e:
            logger.debug(f"显示悬停标注失败: {e}")

    def _hide_hover_annotation(self):
        """隐藏悬停标注"""
        if not MATPLOTLIB_AVAILABLE:
            return

        try:
            if self._hover_annotation:
                self._hover_annotation.remove()
                self._hover_annotation = None
                self.nyquist_canvas.draw_idle()

        except Exception as e:
            logger.debug(f"隐藏悬停标注失败: {e}")

    def _set_optimal_axis_limits(self, real_parts: list, imag_parts: list):
        """设置最佳的坐标轴范围 - 改进的自适应缩放算法"""
        try:
            if not real_parts or not imag_parts:
                logger.warning("数据为空，无法设置坐标轴范围")
                return

            # 计算数据范围
            x_min, x_max = min(real_parts), max(real_parts)
            y_min, y_max = min(imag_parts), max(imag_parts)

            # 计算数据中心
            x_center = (x_min + x_max) / 2
            y_center = (y_min + y_max) / 2

            # 计算数据跨度
            x_span = x_max - x_min
            y_span = y_max - y_min

            # 改进智能最小显示范围计算
            # 根据数据的绝对大小动态调整最小显示范围
            abs_max = max(abs(x_min), abs(x_max), abs(y_min), abs(y_max))

            if abs_max < 0.001:  # 微欧级别
                min_span = abs_max * 2 if abs_max > 0 else 0.001
            elif abs_max < 0.01:  # 毫欧级别
                min_span = abs_max * 1.5 if abs_max > 0 else 0.01
            elif abs_max < 0.1:  # 十毫欧级别
                min_span = abs_max * 1.2 if abs_max > 0 else 0.1
            else:  # 更大的值
                min_span = max(abs_max * 0.1, 1.0)

            # 确保最小显示范围
            if x_span < min_span:
                x_span = min_span
            if y_span < min_span:
                y_span = min_span

            # 改进自适应边距计算
            # 根据数据点数量和分布调整边距
            data_count = len(real_parts)
            if data_count <= 5:
                margin_ratio = 0.3  # 数据点少时给更多边距
            elif data_count <= 20:
                margin_ratio = 0.25
            else:
                margin_ratio = 0.2  # 数据点多时减少边距

            # 计算边距
            x_margin = x_span * margin_ratio
            y_margin = y_span * margin_ratio

            # 计算最终的显示范围
            x_display_min = x_center - (x_span + x_margin) / 2
            x_display_max = x_center + (x_span + x_margin) / 2
            y_display_min = y_center - (y_span + y_margin) / 2
            y_display_max = y_center + (y_span + y_margin) / 2

            # 设置坐标轴范围
            self.nyquist_ax.set_xlim(x_display_min, x_display_max)
            self.nyquist_ax.set_ylim(y_display_min, y_display_max)

            logger.debug(f"   数据范围: X={x_span:.6f}, Y={y_span:.6f}, 数据点数={data_count}, 边距比例={margin_ratio}")

        except Exception as e:
            logger.error(f"设置坐标轴范围失败: {e}")

    def _apply_auto_scaling_if_needed(self, real_parts: list, imag_parts: list):
        """数据更新后自动应用最佳缩放（如果需要）"""
        try:
            if not MATPLOTLIB_AVAILABLE or not real_parts or not imag_parts:
                return

            # 检查当前显示范围是否合适
            current_xlim = self.nyquist_ax.get_xlim()
            current_ylim = self.nyquist_ax.get_ylim()

            # 计算数据范围
            data_x_min, data_x_max = min(real_parts), max(real_parts)
            data_y_min, data_y_max = min(imag_parts), max(imag_parts)

            # 检查数据是否超出当前显示范围或显示范围过大
            x_out_of_range = (data_x_min < current_xlim[0] or data_x_max > current_xlim[1])
            y_out_of_range = (data_y_min < current_ylim[0] or data_y_max > current_ylim[1])

            # 检查显示范围是否过大（数据只占显示范围的很小一部分）
            data_x_span = data_x_max - data_x_min
            data_y_span = data_y_max - data_y_min
            display_x_span = current_xlim[1] - current_xlim[0]
            display_y_span = current_ylim[1] - current_ylim[0]

            # 如果数据范围小于显示范围的20%，认为显示范围过大
            x_too_large = data_x_span > 0 and (data_x_span / display_x_span) < 0.2
            y_too_large = data_y_span > 0 and (data_y_span / display_y_span) < 0.2

            # 如果需要重新缩放
            if x_out_of_range or y_out_of_range or x_too_large or y_too_large:
                self._set_optimal_axis_limits(real_parts, imag_parts)
                self.nyquist_canvas.draw()
            else:
                logger.debug("当前显示范围合适，无需自动缩放")

        except Exception as e:
            logger.debug(f"自动缩放检查失败: {e}")

    def _set_stable_axis_limits(self, real_parts: list, imag_parts: list):
        """设置稳定的坐标轴范围，防止X轴自动缩小"""
        try:
            if not real_parts or not imag_parts:
                logger.warning("数据为空，无法设置坐标轴范围")
                return

            # 计算数据范围
            x_min, x_max = min(real_parts), max(real_parts)
            y_min, y_max = min(imag_parts), max(imag_parts)

            # 计算数据中心
            x_center = (x_min + x_max) / 2
            y_center = (y_min + y_max) / 2

            # 计算数据跨度
            x_span = x_max - x_min
            y_span = y_max - y_min

            # 设置最小显示范围，防止范围过小
            min_span = 5.0  # mΩ
            if x_span < min_span:
                x_span = min_span
            if y_span < min_span:
                y_span = min_span

            # 添加固定的边距比例，防止数据点贴边
            margin_ratio = 0.2  # 20%的边距
            x_margin = x_span * margin_ratio
            y_margin = y_span * margin_ratio

            # 计算最终的显示范围
            x_display_min = x_center - (x_span + x_margin) / 2
            x_display_max = x_center + (x_span + x_margin) / 2
            y_display_min = y_center - (y_span + y_margin) / 2
            y_display_max = y_center + (y_span + y_margin) / 2

            # 设置坐标轴范围
            self.nyquist_ax.set_xlim(x_display_min, x_display_max)
            self.nyquist_ax.set_ylim(y_display_min, y_display_max)

            logger.debug(f"设置稳定坐标轴范围: X[{x_display_min:.2f}, {x_display_max:.2f}], Y[{y_display_min:.2f}, {y_display_max:.2f}]")

        except Exception as e:
            logger.error(f"设置稳定坐标轴范围失败: {e}")

    def _calculate_adaptive_range(self, real_parts: list, imag_parts: list, x_range: float, y_range: float):
        """计算自适应的数据范围 - 智能缩放优化"""
        try:
            # 计算数据的实际范围
            actual_x_range = max(real_parts) - min(real_parts)
            actual_y_range = max(imag_parts) - min(imag_parts)

            # 智能最小显示范围：根据数据大小动态调整
            if actual_x_range > 0:
                # 如果有实际数据范围，使用数据范围的1.5倍作为最小显示范围
                min_x_display_range = max(actual_x_range * 1.5, 0.01)  # 最小0.01 mΩ
            else:
                min_x_display_range = 0.1  # 默认0.1 mΩ

            if actual_y_range > 0:
                min_y_display_range = max(actual_y_range * 1.5, 0.01)  # 最小0.01 mΩ
            else:
                min_y_display_range = 0.1  # 默认0.1 mΩ

            # 应用智能最小显示范围
            if x_range < min_x_display_range:
                x_range = min_x_display_range
            if y_range < min_y_display_range:
                y_range = min_y_display_range

            logger.debug(f"智能缩放计算: 实际范围X={actual_x_range:.4f}, Y={actual_y_range:.4f}, 显示范围X={x_range:.4f}, Y={y_range:.4f}")
            return x_range, y_range

        except Exception as e:
            logger.error(f"计算自适应范围失败: {e}")
            return max(x_range, 0.1), max(y_range, 0.1)

    def _calculate_adaptive_margins(self, x_range: float, y_range: float, data_count: int):
        """计算自适应的边距 - 智能缩放优化"""
        try:
            # 智能基础边距比例：根据数据范围动态调整
            if x_range > 10.0 or y_range > 10.0:
                base_margin_ratio = 0.1  # 大范围数据使用较小边距
            elif x_range > 1.0 or y_range > 1.0:
                base_margin_ratio = 0.15  # 中等范围数据使用中等边距
            else:
                base_margin_ratio = 0.25  # 小范围数据使用较大边距，确保可见性

            # 根据数据点数量调整
            if data_count < 10:
                margin_ratio = base_margin_ratio * 1.5  # 数据点少时增加边距
            elif data_count > 50:
                margin_ratio = base_margin_ratio * 0.8  # 数据点多时减少边距
            else:
                margin_ratio = base_margin_ratio

            # 智能最小边距：根据数据范围动态调整
            min_x_margin = max(x_range * 0.05, 0.001)  # 最小边距为数据范围的5%或0.001 mΩ
            min_y_margin = max(y_range * 0.05, 0.001)  # 最小边距为数据范围的5%或0.001 mΩ

            # 计算边距
            x_margin = max(x_range * margin_ratio, min_x_margin)
            y_margin = max(y_range * margin_ratio, min_y_margin)

            logger.debug(f"智能边距计算: 数据范围X={x_range:.4f}, Y={y_range:.4f}, 边距X={x_margin:.4f}, Y={y_margin:.4f}")
            return x_margin, y_margin

        except Exception as e:
            logger.error(f"计算自适应边距失败: {e}")
            return max(x_range * 0.15, 0.001), max(y_range * 0.15, 0.001)

    def _auto_fit_plot(self):
        """自动回正：恢复到固定显示范围"""
        try:
            if not MATPLOTLIB_AVAILABLE:
                return

            # 修复使用智能范围，避免自动缩放问题
            if self._use_fixed_range:
                # 如果有当前数据，传递给智能范围设置
                if self._current_plot_data:
                    real_parts = [point['real'] for point in self._current_plot_data]
                    imag_parts = [point['imag'] for point in self._current_plot_data]
                    self._set_fixed_axis_limits(real_parts, imag_parts)
                else:
                    self._set_fixed_axis_limits()

                if hasattr(self, 'nyquist_canvas') and self.nyquist_canvas:
                    self.nyquist_canvas.draw()
                logger.info("自动回正完成：恢复到智能显示范围")
            else:
                # 备用：如果禁用固定范围，使用数据范围
                if not self._current_plot_data:
                    return

                real_parts = [point['real'] for point in self._current_plot_data]
                imag_parts = [point['imag'] for point in self._current_plot_data]

                if real_parts and imag_parts:
                    self._set_optimal_axis_limits(real_parts, imag_parts)
                    if hasattr(self, 'nyquist_canvas') and self.nyquist_canvas:
                        self.nyquist_canvas.draw()
                    logger.info("自动回正完成：基于数据范围")

        except Exception as e:
            logger.error(f"自动回正失败: {e}")

    def _smart_zoom_plot(self):
        """智能缩放：根据数据大小智能调整缩放级别，解决图形太小问题"""
        try:

            if not MATPLOTLIB_AVAILABLE or not self._current_plot_data:
                return

            # 提取数据
            real_parts = [point['real'] for point in self._current_plot_data]
            imag_parts = [point['imag'] for point in self._current_plot_data]

            if real_parts and imag_parts:
                # 计算数据的实际范围
                x_min, x_max = min(real_parts), max(real_parts)
                y_min, y_max = min(imag_parts), max(imag_parts)

                actual_x_range = x_max - x_min
                actual_y_range = y_max - y_min

                logger.debug(f"数据实际范围: X={actual_x_range:.6f} mΩ, Y={actual_y_range:.6f} mΩ")

                # 智能缩放策略：根据数据大小选择合适的显示范围
                if actual_x_range < 0.01 or actual_y_range < 0.01:
                    # 非常小的数据：使用紧密缩放
                    zoom_factor = 3.0
                    logger.info("检测到微小数据，使用紧密缩放")
                elif actual_x_range < 0.1 or actual_y_range < 0.1:
                    # 小数据：使用中等缩放
                    zoom_factor = 2.0
                    logger.info("检测到小范围数据，使用中等缩放")
                else:
                    # 正常数据：使用标准缩放
                    zoom_factor = 1.5
                    logger.info("检测到正常范围数据，使用标准缩放")

                # 计算智能显示范围
                x_center = (x_min + x_max) / 2
                y_center = (y_min + y_max) / 2

                # 确保最小显示范围
                display_x_range = max(actual_x_range * zoom_factor, 0.005)  # 最小5微欧
                display_y_range = max(actual_y_range * zoom_factor, 0.005)  # 最小5微欧

                # 设置显示范围
                x_half_range = display_x_range / 2
                y_half_range = display_y_range / 2

                self.nyquist_ax.set_xlim(x_center - x_half_range, x_center + x_half_range)
                self.nyquist_ax.set_ylim(y_center - y_half_range, y_center + y_half_range)

                self.nyquist_canvas.draw()

                logger.info(f"智能缩放完成: 显示范围X=[{x_center - x_half_range:.6f}, {x_center + x_half_range:.6f}], Y=[{y_center - y_half_range:.6f}, {y_center + y_half_range:.6f}]")

        except Exception as e:
            logger.error(f"智能缩放失败: {e}")

    def _center_plot(self):
        """居中显示：以数据中心为基准居中显示"""
        try:
            logger.info("🎯 执行居中显示操作")

            if not MATPLOTLIB_AVAILABLE or not self._current_plot_data:
                return

            # 计算数据中心
            real_parts = [point['real'] for point in self._current_plot_data]
            imag_parts = [point['imag'] for point in self._current_plot_data]

            if real_parts and imag_parts:
                center_x = (min(real_parts) + max(real_parts)) / 2
                center_y = (min(imag_parts) + max(imag_parts)) / 2

                # 获取当前显示范围
                current_xlim = self.nyquist_ax.get_xlim()
                current_ylim = self.nyquist_ax.get_ylim()

                # 计算当前显示范围的大小
                x_span = current_xlim[1] - current_xlim[0]
                y_span = current_ylim[1] - current_ylim[0]

                # 以数据中心为基准设置新的显示范围
                self.nyquist_ax.set_xlim(center_x - x_span/2, center_x + x_span/2)
                self.nyquist_ax.set_ylim(center_y - y_span/2, center_y + y_span/2)

                self.nyquist_canvas.draw()
                logger.info("居中显示完成")

        except Exception as e:
            logger.error(f"居中显示失败: {e}")

    def _reset_zoom(self):
        """重置缩放：重置到默认缩放级别"""
        try:
            logger.info("🔄 执行缩放重置操作")

            if not MATPLOTLIB_AVAILABLE:
                return

            # 重建图表组件并重新绘制
            self._rebuild_and_replot()

        except Exception as e:
            logger.error(f"缩放重置失败: {e}")

    def _rebuild_and_replot(self):
        """完全重建matplotlib组件并重新绘制当前数据"""
        try:
            logger.info("🔄 执行完全重建和重新绘制操作")

            if not MATPLOTLIB_AVAILABLE:
                return

            # 保存当前数据
            current_data = self._current_plot_data.copy()

            # 重建matplotlib组件
            self._rebuild_matplotlib_components()

            # 多通道模式下：点击完全重建后，清除所有已显示的曲线与选择
            if getattr(self, '_multi_channel_mode', False):
                try:
                    if hasattr(self, 'clear_fit_curves'):
                        self.clear_fit_curves()
                except Exception as ce:
                    logger.debug(f"清除拟合曲线时出现异常: {ce}")
                # 清空多通道选择与图形
                self.clear_all_channels()
                logger.info("✅ 已清空多通道显示的所有曲线与选择")
                return

            # 单通道：默认清空图并提示外部重新绘制
            self._current_plot_data = []
            self._original_test_data = []
            self._clear_plot()
            logger.info("完全重建完成（单通道），已清空图形，请重新选择数据进行绘制")

        except Exception as e:
            logger.error(f"完全重建和重新绘制失败: {e}")

    def _rebuild_matplotlib_components(self):
        """重建matplotlib组件"""
        try:
            if not MATPLOTLIB_AVAILABLE:
                return

            # 清理现有组件
            if self.nyquist_figure:
                self.nyquist_figure.clear()

            # 重新创建坐标轴
            self.nyquist_ax = self.nyquist_figure.add_subplot(111)
            self._update_axis_labels()
            self.nyquist_ax.set_title('奈奎斯特图')
            self.nyquist_ax.grid(True, alpha=0.3)
            self.nyquist_ax.set_aspect('equal')

            # 重新设置悬停事件
            self._setup_hover_events()

            # 刷新画布
            self.nyquist_canvas.draw()

            logger.debug("matplotlib组件重建完成")

        except Exception as e:
            logger.error(f"重建matplotlib组件失败: {e}")

    def _generate_fitted_curve(self, real_parts, imag_parts, frequencies):
        """
        生成拟合曲线数据 - 使用新的奈奎斯特曲线优化器

        Args:
            real_parts: 实部数据
            imag_parts: 虚部数据
            frequencies: 频率数据

        Returns:
            (fitted_real, fitted_imag) 拟合后的数据，如果失败返回(None, None)
        """
        try:
            if not MATPLOTLIB_AVAILABLE:
                return None, None

            # 检查数据有效性
            if len(real_parts) < 4 or len(imag_parts) < 4:
                logger.debug("数据点不足，跳过拟合曲线生成")
                return None, None

            # 🎯 使用新的奈奎斯特曲线优化器
            try:
                from utils.nyquist_curve_optimizer import generate_beautiful_nyquist_curve

                # 使用混合平滑方法生成漂亮的拟合曲线
                fitted_real, fitted_imag = generate_beautiful_nyquist_curve(
                    real_parts, imag_parts, frequencies,
                    method='hybrid_smooth',
                    density_factor=3.0
                )

                if fitted_real is not None and fitted_imag is not None:
                    logger.debug(f"🎨 新优化器拟合成功: 原始{len(real_parts)}点 -> 拟合{len(fitted_real)}点")
                    return fitted_real, fitted_imag
                else:
                    logger.warning("新优化器拟合失败，使用备用方法")

            except ImportError:
                logger.warning("奈奎斯特曲线优化器不可用，使用传统方法")
            except Exception as e:
                logger.warning(f"新优化器拟合失败: {e}，使用备用方法")

            # 备用方案使用原有的拟合方法
            import numpy as np
            from scipy import interpolate

            # 转换为numpy数组
            real_array = np.array(real_parts)
            imag_array = np.array(imag_parts)
            freq_array = np.array(frequencies)

            # 按频率排序
            sort_indices = np.argsort(freq_array)
            sorted_real = real_array[sort_indices]
            sorted_imag = imag_array[sort_indices]
            sorted_freq = freq_array[sort_indices]

            # 使用原有的三次样条插值方法
            fitted_real, fitted_imag = self._apply_cubic_spline_fitting(
                sorted_real, sorted_imag, sorted_freq)

            if fitted_real is not None and fitted_imag is not None:
                logger.debug(f"备用拟合曲线生成成功: 原始{len(real_parts)}点 -> 拟合{len(fitted_real)}点")
                return fitted_real, fitted_imag
            else:
                # 如果三次样条失败，使用加权样条方法
                return self._apply_segmented_fitting(sorted_real, sorted_imag, sorted_freq)

        except Exception as e:
            logger.error(f"生成拟合曲线失败: {e}")
            return None, None

    def _apply_cubic_spline_fitting(self, real_parts, imag_parts, frequencies):
        """
        应用优化的三次样条拟合 - 高精度，保持EIS特征

        Args:
            real_parts: 排序后的实部数据
            imag_parts: 排序后的虚部数据
            frequencies: 排序后的频率数据

        Returns:
            (fitted_real, fitted_imag) 或 (None, None)
        """
        try:
            import numpy as np
            from scipy import interpolate

            # 使用对数频率作为参数，更适合EIS数据的指数特性
            log_freq = np.log10(frequencies + 1e-10)

            # 优化1自适应密度控制
            n_points = len(real_parts)
            if n_points <= 10:
                dense_factor = 2.0  # 少量数据点，适度增密
            elif n_points <= 20:
                dense_factor = 1.8  # 中等数据点，轻度增密
            else:
                dense_factor = 1.5  # 大量数据点，保持原有密度

            n_dense = max(n_points + 5, int(n_points * dense_factor))
            log_freq_dense = np.linspace(log_freq.min(), log_freq.max(), n_dense)

            # 优化2使用三次样条插值，保持数据的自然特征
            # 不使用平滑参数，完全保持数据特征
            cs_real = interpolate.CubicSpline(log_freq, real_parts, bc_type='natural')
            cs_imag = interpolate.CubicSpline(log_freq, imag_parts, bc_type='natural')

            fitted_real = cs_real(log_freq_dense)
            fitted_imag = cs_imag(log_freq_dense)

            # 优化3边界条件优化
            # 确保端点完全匹配原始数据
            fitted_real[0] = real_parts[0]
            fitted_real[-1] = real_parts[-1]
            fitted_imag[0] = imag_parts[0]
            fitted_imag[-1] = imag_parts[-1]

            # 优化4数据质量检查
            # 检查拟合结果是否合理
            if self._validate_fitted_curve(fitted_real, fitted_imag, real_parts, imag_parts):
                logger.debug(f"三次样条拟合完成: 密度因子={dense_factor:.2f}, 数据点={n_points}->{n_dense}")
                return fitted_real, fitted_imag
            else:
                logger.warning("三次样条拟合结果质量不佳，将使用备用方法")
                return None, None

        except Exception as e:
            logger.error(f"三次样条拟合失败: {e}")
            return None, None

    def _validate_fitted_curve(self, fitted_real, fitted_imag, orig_real, orig_imag):
        """
        验证拟合曲线的质量

        Args:
            fitted_real, fitted_imag: 拟合后的数据
            orig_real, orig_imag: 原始数据

        Returns:
            bool: 拟合质量是否合格
        """
        try:
            import numpy as np

            # 检查1：数据范围合理性
            real_range_orig = np.max(orig_real) - np.min(orig_real)
            real_range_fitted = np.max(fitted_real) - np.min(fitted_real)

            imag_range_orig = np.max(orig_imag) - np.min(orig_imag)
            imag_range_fitted = np.max(fitted_imag) - np.min(fitted_imag)

            # 拟合后的数据范围不应该超出原始数据范围太多
            if (real_range_fitted > real_range_orig * 1.5 or
                imag_range_fitted > imag_range_orig * 1.5):
                return False

            # 检查2：端点匹配度
            start_error = abs(fitted_real[0] - orig_real[0]) + abs(fitted_imag[0] - orig_imag[0])
            end_error = abs(fitted_real[-1] - orig_real[-1]) + abs(fitted_imag[-1] - orig_imag[-1])

            # 端点误差应该很小
            if start_error > 0.1 or end_error > 0.1:
                return False

            # 检查3：无异常值
            if (np.any(np.isnan(fitted_real)) or np.any(np.isnan(fitted_imag)) or
                np.any(np.isinf(fitted_real)) or np.any(np.isinf(fitted_imag))):
                return False

            return True

        except Exception:
            return False

    def _apply_segmented_fitting(self, real_parts, imag_parts, frequencies):
        """
        应用分段拟合策略 - 针对EIS数据的特殊处理

        Args:
            real_parts: 排序后的实部数据
            imag_parts: 排序后的虚部数据
            frequencies: 排序后的频率数据

        Returns:
            (fitted_real, fitted_imag) 或 (None, None)
        """
        try:
            import numpy as np
            from scipy import interpolate

            # 策略1保持端点固定，重点平滑中间部分
            n_points = len(real_parts)

            # 识别关键点：起始点、峰值点、结束点
            start_idx = 0
            end_idx = n_points - 1

            # 找到虚部的峰值点（通常是半圆的顶点）
            peak_idx = np.argmax(imag_parts) if len(imag_parts) > 0 else n_points // 2

            # 策略2使用加权样条插值，端点权重更高
            weights = np.ones(n_points)
            weights[0] = 10.0      # 起始点高权重
            weights[-1] = 10.0     # 结束点高权重
            weights[peak_idx] = 5.0 # 峰值点中等权重

            # 对数频率参数
            log_freq = np.log10(frequencies + 1e-10)

            # 策略3自适应平滑因子
            # 根据数据的变化程度调整平滑强度
            real_variation = np.std(real_parts)
            imag_variation = np.std(imag_parts)

            # 变化越大，平滑因子越小（保持更多细节）
            base_smoothing = len(real_parts) * 0.02  # 降低基础平滑因子
            real_smoothing = base_smoothing * (1.0 + real_variation / 10.0)
            imag_smoothing = base_smoothing * (1.0 + imag_variation / 10.0)

            # 创建加权样条插值
            spline_real = interpolate.UnivariateSpline(
                log_freq, real_parts, w=weights, s=real_smoothing)
            spline_imag = interpolate.UnivariateSpline(
                log_freq, imag_parts, w=weights, s=imag_smoothing)

            # 策略4生成适度密集的插值点
            # 不要过度密集，保持合理的点数
            dense_factor = min(2.5, max(1.5, 30.0 / n_points))  # 自适应密度
            n_dense = int(n_points * dense_factor)
            log_freq_dense = np.linspace(log_freq.min(), log_freq.max(), n_dense)

            fitted_real = spline_real(log_freq_dense)
            fitted_imag = spline_imag(log_freq_dense)

            # 策略5后处理 - 确保端点精确匹配
            if len(fitted_real) > 0 and len(fitted_imag) > 0:
                fitted_real[0] = real_parts[0]    # 强制起始点匹配
                fitted_real[-1] = real_parts[-1]  # 强制结束点匹配
                fitted_imag[0] = imag_parts[0]    # 强制起始点匹配
                fitted_imag[-1] = imag_parts[-1]  # 强制结束点匹配

            logger.debug(f"分段拟合完成: 密度因子={dense_factor:.2f}, 平滑因子=({real_smoothing:.3f}, {imag_smoothing:.3f})")
            return fitted_real, fitted_imag

        except Exception as e:
            logger.error(f"分段拟合失败: {e}")
            return None, None

    def _apply_fallback_fitting(self, real_parts, imag_parts, frequencies):
        """
        备用拟合方法 - 简单但可靠的插值

        Args:
            real_parts: 实部数据
            imag_parts: 虚部数据
            frequencies: 频率数据

        Returns:
            (fitted_real, fitted_imag) 或 (None, None)
        """
        try:
            import numpy as np
            from scipy import interpolate

            # 使用三次样条插值（不平滑）
            log_freq = np.log10(frequencies + 1e-10)

            # 生成适度密集的点
            n_dense = len(real_parts) * 2
            log_freq_dense = np.linspace(log_freq.min(), log_freq.max(), n_dense)

            # 三次样条插值
            cs_real = interpolate.CubicSpline(log_freq, real_parts)
            cs_imag = interpolate.CubicSpline(log_freq, imag_parts)

            fitted_real = cs_real(log_freq_dense)
            fitted_imag = cs_imag(log_freq_dense)

            logger.debug("备用拟合方法完成")
            return fitted_real, fitted_imag

        except Exception as e:
            logger.error(f"备用拟合失败: {e}")
            return None, None

    def cleanup(self):
        """清理资源"""
        try:
            if self._plot_timer:
                self._plot_timer.stop()
                self._plot_timer = None

            self._current_plot_data = []
            self._original_test_data = []  # 同时清空原始数据
            self._selected_channels_data = {}

            if MATPLOTLIB_AVAILABLE and self.nyquist_figure:
                self.nyquist_figure.clear()

            logger.debug("奈奎斯特图管理器清理完成")

        except Exception as e:
            logger.error(f"清理奈奎斯特图管理器失败: {e}")

    def add_fit_curve(self, curve_id: str, real_parts: List[float], imag_parts: List[float], label: str = ""):
        """
        添加拟合曲线

        Args:
            curve_id: 曲线唯一标识
            real_parts: 实部数据
            imag_parts: 虚部数据
            label: 曲线标签
        """
        try:
            if not MATPLOTLIB_AVAILABLE:
                return

            self._fit_curves[curve_id] = {
                'real': real_parts,
                'imag': imag_parts,
                'label': label
            }

            # 重新绘制图表以包含拟合曲线
            self._redraw_with_fit_curves()

            logger.debug(f"添加拟合曲线: {curve_id}")

        except Exception as e:
            logger.error(f"添加拟合曲线失败: {e}")

    def clear_fit_curves(self):
        """清除所有拟合曲线"""
        try:
            self._fit_curves.clear()

            # 重新绘制图表
            self._redraw_current_plot()

            logger.debug("清除所有拟合曲线")

        except Exception as e:
            logger.error(f"清除拟合曲线失败: {e}")

    def get_selected_plot_items(self) -> List[str]:
        """获取选中的绘图项目"""
        try:
            # 这里可以根据实际需要实现选择逻辑
            # 目前返回所有当前显示的数据项
            selected_items = []

            if self._current_plot_data:
                # 基于当前绘图数据生成项目标识
                for i, data_point in enumerate(self._current_plot_data):
                    # 生成项目标识，可以根据实际数据结构调整
                    item_id = f"item_{i}"
                    selected_items.append(item_id)

            return selected_items

        except Exception as e:
            logger.error(f"获取选中项目失败: {e}")
            return []

    def _redraw_with_fit_curves(self):
        """重新绘制图表并包含拟合曲线"""
        try:
            if not MATPLOTLIB_AVAILABLE or not self.nyquist_ax:
                return

            # 在现有图表上添加拟合曲线
            for curve_id, curve_data in self._fit_curves.items():
                real_parts = curve_data['real']
                imag_parts = curve_data['imag']
                label = curve_data['label']

                # 绘制拟合曲线（使用虚线样式区分）
                self.nyquist_ax.plot(real_parts, imag_parts,
                                   '--', linewidth=2, alpha=0.8,
                                   label=label if label else f"拟合曲线 {curve_id}")

            # 更新图例
            if self._show_legend and self._fit_curves:
                self.nyquist_ax.legend()

            # 刷新画布
            self.nyquist_canvas.draw()

        except Exception as e:
            logger.error(f"重新绘制拟合曲线失败: {e}")

    def set_show_fitted_curve(self, show: bool):
        """设置是否显示拟合曲线"""
        try:
            self._show_fitted_curve = show

            if show and self._fit_curves:
                self._redraw_with_fit_curves()
            elif not show:
                self._redraw_current_plot()

        except Exception as e:
            logger.error(f"设置拟合曲线显示失败: {e}")

    def get_show_fitted_curve(self) -> bool:
        """获取是否显示拟合曲线"""
        return self._show_fitted_curve
