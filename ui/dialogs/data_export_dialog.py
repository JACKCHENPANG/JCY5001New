# -*- coding: utf-8 -*-
"""
数据导出对话框 - 重构版本
使用专门的管理器类，遵循单一职责原则

重构自原始的data_export_dialog.py，拆分为多个管理器：
- DataQueryManager: 数据查询管理
- DataExportManager: 数据导出管理  
- NyquistPlotManager: 奈奎斯特图管理

Author: Augment Agent (重构)
Original Author: Jack
Date: 2025-06-04
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QGroupBox, QLabel, QComboBox, QDateEdit,
    QPushButton, QTableWidget, QTableWidgetItem,
    QProgressBar, QMessageBox, QFileDialog, QHeaderView,
    QAbstractItemView, QSplitter, QCheckBox, QWidget,
    QProgressDialog, QTextEdit, QApplication, QListWidget
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor
import logging
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional

# 导入重构后的管理器类
from .data_query_manager import DataQueryManager
from .data_export_manager import DataExportManager
from .nyquist_plot_manager import NyquistPlotManager
from .channel_filter_manager import ChannelFilterWidget, ChannelFilterManager
from .battery_code_filter_manager import BatteryCodeFilterWidget, BatteryCodeFilterManager
from data.database_manager import DatabaseManager
from backend.product_info_manager import ProductInfoManager
from utils.config_manager import ConfigManager
# DRT功能已移除

logger = logging.getLogger(__name__)


class DataExportDialog(QDialog):
    """
    数据导出对话框 - 重构版本
    
    职责：
    - 协调各个管理器的工作
    - 管理UI界面
    - 处理用户交互
    """
    
    def __init__(self, db_manager: DatabaseManager, parent=None):
        """
        初始化数据导出对话框
        
        Args:
            db_manager: 数据库管理器
            parent: 父窗口
        """
        super().__init__(parent)

        self.db_manager = db_manager
        self.current_data = []

        # 创建配置和产品信息管理器
        self.config_manager = ConfigManager()
        self.product_info_manager = ProductInfoManager(self.config_manager)

        # 修复确保数据库管理器有配置管理器
        if not hasattr(self.db_manager, 'config_manager') or self.db_manager.config_manager is None:
            self.db_manager.config_manager = self.config_manager

        # 创建管理器
        self.query_manager = DataQueryManager(db_manager)
        self.export_manager = DataExportManager(db_manager)
        self.plot_manager = NyquistPlotManager(self)
        self.channel_filter_manager = ChannelFilterManager()
        self.battery_code_filter_manager = BatteryCodeFilterManager()

        # DRT功能已移除
        
        # 全屏显示相关变量
        self._is_fullscreen = False
        self._normal_geometry = None
        
        # 初始化界面
        self._init_ui()
        self._init_connections()
        
        # 性能优化：延迟加载初始数据
        QTimer.singleShot(100, self._load_recent_batches_async)
        
        # 默认全屏显示
        self._set_default_fullscreen()
        
        logger.debug("数据导出对话框初始化完成")

    def _get_voltage_range_text(self) -> str:
        """获取电压范围文本 - 从测试配置中获取"""
        try:
            # 从测试配置中获取电压范围
            voltage_range = self.config_manager.get('test_params.voltage_range', {'min': 2.0, 'max': 5.0})
            min_voltage = voltage_range.get('min', 2.0)
            max_voltage = voltage_range.get('max', 5.0)
            return f"{min_voltage:.3f}V-{max_voltage:.3f}V"
        except Exception as e:
            logger.error(f"获取电压范围失败: {e}")
            return "--"

    def _get_rs_range_text(self) -> str:
        """获取Rs范围文本 - 从判断设置配置中获取"""
        try:
            # 修复从grade_settings配置中获取Rs范围，与实际判断逻辑一致
            rs_min = self.config_manager.get('grade_settings.rs_min', 0.1)
            rs_max = self.config_manager.get('grade_settings.rs_max', 50.0)

            return f"{rs_min:.3f}mΩ-{rs_max:.3f}mΩ"
        except Exception as e:
            logger.error(f"获取Rs范围失败: {e}")
            return "--"

    def _get_rct_range_text(self) -> str:
        """获取Rct范围文本 - 从判断设置配置中获取"""
        try:
            # 修复从grade_settings配置中获取Rct范围，与实际判断逻辑一致
            rct_min = self.config_manager.get('grade_settings.rct_min', 5.0)
            rct_max = self.config_manager.get('grade_settings.rct_max', 100.0)

            return f"{rct_min:.3f}mΩ-{rct_max:.3f}mΩ"
        except Exception as e:
            logger.error(f"获取Rct范围失败: {e}")
            return "--"

    def _get_voltage_range_from_db(self, item: Dict) -> str:
        """从数据库记录中获取电压范围文本"""
        try:
            voltage_min = item.get('voltage_range_min')
            voltage_max = item.get('voltage_range_max')

            if voltage_min is not None and voltage_max is not None:
                return f"{voltage_min:.3f}V-{voltage_max:.3f}V"
            else:
                # 如果数据库中没有范围信息，使用当前配置作为备用
                return self._get_voltage_range_text()
        except Exception as e:
            logger.error(f"从数据库获取电压范围失败: {e}")
            return "--"

    def _get_rs_range_from_db(self, item: Dict) -> str:
        """从数据库记录中获取Rs范围文本"""
        try:
            rs_min = item.get('rs_range_min')
            rs_max = item.get('rs_range_max')

            if rs_min is not None and rs_max is not None:
                return f"{rs_min:.3f}mΩ-{rs_max:.3f}mΩ"
            else:
                # 如果数据库中没有范围信息，使用当前配置作为备用
                return self._get_rs_range_text()
        except Exception as e:
            logger.error(f"从数据库获取Rs范围失败: {e}")
            return "--"

    def _get_rct_range_from_db(self, item: Dict) -> str:
        """从数据库记录中获取Rct范围文本"""
        try:
            rct_min = item.get('rct_range_min')
            rct_max = item.get('rct_range_max')

            if rct_min is not None and rct_max is not None:
                return f"{rct_min:.3f}mΩ-{rct_max:.3f}mΩ"
            else:
                # 如果数据库中没有范围信息，使用当前配置作为备用
                return self._get_rct_range_text()
        except Exception as e:
            logger.error(f"从数据库获取Rct范围失败: {e}")
            return "--"

    def _init_ui(self):
        """初始化用户界面 - 4宫格布局"""
        # 设置对话框属性
        self.setWindowTitle("数据分析")
        self.setWindowIcon(QIcon("resources/icons/export.png"))
        self.setModal(True)
        self.resize(1200, 800)
        self.setMinimumSize(1000, 700)

        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 创建4宫格布局
        grid_splitter = self._create_grid_layout()
        main_layout.addWidget(grid_splitter)

        # 创建按钮区域
        button_layout = self._create_button_area()
        main_layout.addLayout(button_layout)

        # 应用样式
        self._apply_styles()

    def _create_grid_layout(self):
        """创建4宫格布局"""
        # 主分割器（垂直分割）
        main_splitter = QSplitter(Qt.Orientation.Vertical)

        # 上半部分（水平分割）
        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左上角：查询条件
        query_widget = self._create_query_widget()
        top_splitter.addWidget(query_widget)

        # 右上角：查询结果表格
        results_widget = self._create_results_widget()
        top_splitter.addWidget(results_widget)

        # 设置上半部分比例 (查询条件:查询结果 = 1:2)
        top_splitter.setSizes([400, 800])

        # 下半部分（水平分割）
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左下角：奈奎斯特图
        nyquist_widget = self._create_nyquist_widget()
        bottom_splitter.addWidget(nyquist_widget)

        # 右下角：明细数据
        details_widget = self._create_details_widget()
        bottom_splitter.addWidget(details_widget)

        # 设置下半部分比例 (奈奎斯特图:明细数据 = 1:1)
        bottom_splitter.setSizes([600, 600])

        # 将上下两部分添加到主分割器
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(bottom_splitter)

        # 设置主分割器比例 (上半部分:下半部分 = 1:1)
        main_splitter.setSizes([400, 400])

        return main_splitter
    
    def _create_query_widget(self) -> QGroupBox:
        """创建查询条件区域"""
        group = QGroupBox("查询条件")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # 查询条件表单
        form_layout = QGridLayout()
        form_layout.setSpacing(8)

        # 批次号
        form_layout.addWidget(QLabel("批次号:"), 0, 0)
        self.batch_combo = QComboBox()
        self.batch_combo.setEditable(True)  # 支持可编辑
        self.batch_combo.setMinimumWidth(150)
        form_layout.addWidget(self.batch_combo, 0, 1)

        # 开始日期
        form_layout.addWidget(QLabel("开始日期:"), 1, 0)
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        self.start_date.setCalendarPopup(True)
        form_layout.addWidget(self.start_date, 1, 1)

        # 结束日期
        form_layout.addWidget(QLabel("结束日期:"), 2, 0)
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        form_layout.addWidget(self.end_date, 2, 1)

        # 通道号
        form_layout.addWidget(QLabel("通道号:"), 3, 0)
        self.channel_combo = QComboBox()
        self.channel_combo.addItem("全部", None)
        for i in range(1, 9):
            self.channel_combo.addItem(f"通道{i}", i)
        form_layout.addWidget(self.channel_combo, 3, 1)

        # 测试结果
        form_layout.addWidget(QLabel("测试结果:"), 4, 0)
        self.result_combo = QComboBox()
        self.result_combo.addItem("全部", None)
        self.result_combo.addItem("合格", True)
        self.result_combo.addItem("不合格", False)
        form_layout.addWidget(self.result_combo, 4, 1)

        layout.addLayout(form_layout)

        # 高级筛选区域
        advanced_filter_layout = self._create_advanced_filter_area()
        layout.addLayout(advanced_filter_layout)

        # 查询按钮
        self.query_button = QPushButton("查询数据")
        self.query_button.setMinimumHeight(35)
        layout.addWidget(self.query_button)

        # 分隔线
        layout.addWidget(self._create_separator())

        # 数据管理区域
        data_mgmt_layout = self._create_data_management_area()
        layout.addLayout(data_mgmt_layout)

        return group

    def _create_advanced_filter_area(self) -> QHBoxLayout:
        """创建高级筛选区域"""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        # 通道筛选组件
        self.channel_filter_widget = ChannelFilterWidget(self)
        self.channel_filter_widget.setMaximumWidth(200)
        layout.addWidget(self.channel_filter_widget)

        # 电池码筛选组件
        self.battery_code_filter_widget = BatteryCodeFilterWidget(self)
        self.battery_code_filter_widget.setMaximumWidth(250)
        layout.addWidget(self.battery_code_filter_widget)

        layout.addStretch()

        return layout

    def _create_separator(self):
        """创建分隔线"""
        from PyQt5.QtWidgets import QFrame
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def _create_data_management_area(self):
        """创建数据管理区域"""
        layout = QVBoxLayout()

        # 数据管理标题
        mgmt_label = QLabel("数据管理")
        mgmt_label.setFont(QFont("", 9, QFont.Bold))
        layout.addWidget(mgmt_label)

        # 删除数据按钮
        self.delete_button = QPushButton("删除选中数据")
        self.delete_button.setMinimumHeight(30)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        layout.addWidget(self.delete_button)

        # 重置数据库按钮
        self.reset_db_button = QPushButton("重置数据库")
        self.reset_db_button.setMinimumHeight(30)
        self.reset_db_button.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        layout.addWidget(self.reset_db_button)

        # 新增序列号管理按钮
        self.serial_manage_button = QPushButton("序列号管理")
        self.serial_manage_button.setMinimumHeight(30)
        self.serial_manage_button.setStyleSheet("""
            QPushButton {
                background-color: #9c27b0;
                color: white;
            }
            QPushButton:hover {
                background-color: #7b1fa2;
            }
        """)
        layout.addWidget(self.serial_manage_button)

        return layout
    
    def _create_results_widget(self) -> QGroupBox:
        """创建查询结果表格区域（右上角）"""
        group = QGroupBox("查询结果")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 统计信息
        stats_layout = self._create_statistics_area()
        layout.addLayout(stats_layout)

        # 分页控制
        pagination_layout = self._create_pagination_area()
        layout.addLayout(pagination_layout)

        # 数据表格
        self._create_results_table()
        layout.addWidget(self.data_table)

        return group

    def _create_details_widget(self) -> QGroupBox:
        """创建明细数据区域（右下角）"""
        group = QGroupBox("明细数据")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 明细数据表格
        self.details_table = QTableWidget()
        self.details_table.setAlternatingRowColors(True)

        # 优化明细数据表格列标题，使用更专业的术语
        detail_headers = ["测试时间", "频率(Hz)", "阻抗实部Re(Z)(mΩ)", "阻抗虚部Im(Z)(mΩ)",
                         "阻抗模值|Z|(mΩ)", "电压(V)", "相位角θ(°)", "测试序号"]
        self.details_table.setColumnCount(len(detail_headers))
        self.details_table.setHorizontalHeaderLabels(detail_headers)

        # 设置表格属性
        header = self.details_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)

        # 设置明细数据表格各列宽度
        self.details_table.setColumnWidth(0, 140)  # 测试时间
        self.details_table.setColumnWidth(1, 100)  # 频率
        self.details_table.setColumnWidth(2, 120)  # 阻抗实部
        self.details_table.setColumnWidth(3, 120)  # 阻抗虚部
        self.details_table.setColumnWidth(4, 120)  # 阻抗模值
        self.details_table.setColumnWidth(5, 80)   # 电压
        self.details_table.setColumnWidth(6, 100)  # 相位角
        self.details_table.setColumnWidth(7, 80)   # 测试序号

        layout.addWidget(self.details_table)

        return group
    
    def _create_statistics_area(self) -> QHBoxLayout:
        """创建统计信息区域"""
        layout = QHBoxLayout()
        
        self.total_label = QLabel("总数: 0")
        self.pass_label = QLabel("合格: 0")
        self.fail_label = QLabel("不合格: 0")
        self.yield_label = QLabel("良率: 0.0%")
        
        # 设置样式
        for label in [self.total_label, self.pass_label, self.fail_label, self.yield_label]:
            label.setFont(QFont("", 10, QFont.Bold))
        
        layout.addWidget(self.total_label)
        layout.addWidget(self.pass_label)
        layout.addWidget(self.fail_label)
        layout.addWidget(self.yield_label)
        layout.addStretch()
        
        # 状态标签
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
        return layout
    
    def _create_pagination_area(self) -> QHBoxLayout:
        """创建分页控制区域"""
        layout = QHBoxLayout()
        
        self.prev_button = QPushButton("上一页")
        self.next_button = QPushButton("下一页")
        self.load_more_button = QPushButton("加载更多")
        self.page_info_label = QLabel("第 0 页，共 0 页")
        
        layout.addWidget(self.prev_button)
        layout.addWidget(self.next_button)
        layout.addWidget(self.load_more_button)
        layout.addStretch()
        layout.addWidget(self.page_info_label)
        
        return layout
    
    def _create_results_table(self):
        """创建测试结果表格"""
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setSelectionMode(QAbstractItemView.ExtendedSelection)  # 支持多选

        # Jack要求清理后的表头（移除了Rsei、阻抗比、相位角、电容、时间常数、贡献度、健康状态、分析方法、离群率、基准ID等）
        headers = ["选择", "批次号", "通道号", "电池编码", "测试开始时间", "测试时长(秒)", "电压(V)",
                  "Rs(mΩ)", "Rct(mΩ)", "Rs-Rct档位", "电压范围", "Rs范围", "Rct范围",
                  "测试结果", "失败原因", "操作员", "电池类型", "规格"]
        self.data_table.setColumnCount(len(headers))
        self.data_table.setHorizontalHeaderLabels(headers)

        # 设置表格属性
        header = self.data_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)

        # 修复调整各列宽度，合并Rs-Rct档位列
        self.data_table.setColumnWidth(0, 60)   # 选择列固定宽度
        self.data_table.setColumnWidth(1, 80)   # 批次号
        self.data_table.setColumnWidth(2, 60)   # 通道号
        self.data_table.setColumnWidth(3, 120)  # 电池编码
        self.data_table.setColumnWidth(4, 140)  # 测试开始时间
        self.data_table.setColumnWidth(5, 80)   # 测试时长
        self.data_table.setColumnWidth(6, 80)   # 电压
        self.data_table.setColumnWidth(7, 80)   # Rs值
        self.data_table.setColumnWidth(8, 80)   # Rct值
        self.data_table.setColumnWidth(9, 80)   # W阻抗
        self.data_table.setColumnWidth(25, 80)  # Rs-Rct档位（合并列）
        self.data_table.setColumnWidth(26, 120) # 电压范围
        self.data_table.setColumnWidth(27, 120) # Rs范围
        self.data_table.setColumnWidth(28, 120) # Rct范围
        self.data_table.setColumnWidth(15, 80)  # 离群率
        self.data_table.setColumnWidth(16, 60)  # 基准ID
        self.data_table.setColumnWidth(17, 80)  # 测试结果
        self.data_table.setColumnWidth(18, 120) # 失败原因
        self.data_table.setColumnWidth(19, 80)  # 操作员
        self.data_table.setColumnWidth(20, 80)  # 电池类型
        self.data_table.setColumnWidth(21, 80)  # 规格
    
    def _create_nyquist_widget(self):
        """创建奈奎斯特图组件（左下角）"""
        group = QGroupBox("奈奎斯特图")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 奈奎斯特图
        nyquist_plot = self.plot_manager.get_plot_widget()
        layout.addWidget(nyquist_plot)

        # 缩放控制按钮
        zoom_controls = self.plot_manager.create_zoom_controls()
        layout.addWidget(zoom_controls)

        # DRT功能已移除

        return group

    # DRT功能已移除

    def _create_button_area(self) -> QHBoxLayout:
        """创建按钮区域"""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        # 导出格式选择
        layout.addWidget(QLabel("导出格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("Excel (.xlsx)", "Excel")
        self.format_combo.addItem("CSV (.csv)", "CSV")
        layout.addWidget(self.format_combo)

        layout.addStretch()

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 按钮
        self.export_button = QPushButton("导出全部数据")
        self.export_button.setMinimumHeight(35)
        layout.addWidget(self.export_button)

        # 新增导出选中数据按钮
        self.export_selected_button = QPushButton("导出选中数据")
        self.export_selected_button.setMinimumHeight(35)
        self.export_selected_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #E65100;
            }
        """)
        layout.addWidget(self.export_selected_button)

        # 新增手动上传选中数据按钮
        self.upload_selected_button = QPushButton("上传选中数据")
        self.upload_selected_button.setMinimumHeight(35)
        self.upload_selected_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        layout.addWidget(self.upload_selected_button)

        # 🔄 新增：连续测试报告按钮
        self.continuous_report_button = QPushButton("连续测试报告")
        self.continuous_report_button.setMinimumHeight(35)
        self.continuous_report_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        layout.addWidget(self.continuous_report_button)

        self.fullscreen_button = QPushButton("全屏显示")
        self.fullscreen_button.setMinimumHeight(35)
        layout.addWidget(self.fullscreen_button)

        self.close_button = QPushButton("关闭")
        self.close_button.setMinimumHeight(35)
        layout.addWidget(self.close_button)

        return layout

    def _apply_styles(self):
        """应用样式表"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
            }
        """)

    def _init_connections(self):
        """初始化信号连接"""
        # 查询相关
        self.query_button.clicked.connect(self._start_new_query)
        self.batch_combo.currentTextChanged.connect(self._on_batch_changed)

        # 分页相关
        self.prev_button.clicked.connect(self._prev_page)
        self.next_button.clicked.connect(self._next_page)
        self.load_more_button.clicked.connect(self._load_more_data)

        # 导出相关
        self.export_button.clicked.connect(self._export_data)

        # 新增导出选中数据
        self.export_selected_button.clicked.connect(self._export_selected_data)

        # 新增上传选中数据
        self.upload_selected_button.clicked.connect(self._upload_selected_data)

        # 🔄 连续测试报告相关
        self.continuous_report_button.clicked.connect(self._show_continuous_test_report)

        # 界面相关
        self.fullscreen_button.clicked.connect(self._toggle_fullscreen)
        self.close_button.clicked.connect(self.accept)

        # 表格选择变更
        self.data_table.itemSelectionChanged.connect(self._on_result_selection_changed)

        # 数据管理相关
        self.delete_button.clicked.connect(self._delete_selected_data)
        self.reset_db_button.clicked.connect(self._reset_database)
        self.serial_manage_button.clicked.connect(self._manage_serial_numbers)

        # 高级筛选相关
        self.channel_filter_widget.selection_changed.connect(self._on_channel_filter_changed)
        self.battery_code_filter_widget.filter_changed.connect(self._on_battery_code_filter_changed)

        # 设备连接状态监听（用于动态更新通道数量）
        self._setup_device_connection_monitoring()

    def _load_recent_batches_async(self):
        """异步加载最近的批次列表"""
        try:
            logger.debug("开始异步加载批次列表")

            # 显示加载状态
            self.batch_combo.clear()
            self.batch_combo.addItem("正在加载...", None)
            self.batch_combo.setEnabled(False)

            # 延迟执行实际加载
            QTimer.singleShot(50, self._do_load_batches)

        except Exception as e:
            logger.error(f"异步加载批次列表失败: {e}")
            self.batch_combo.clear()
            self.batch_combo.addItem("加载失败", None)

    def _do_load_batches(self):
        """执行实际的批次加载"""
        try:
            # 从测试结果中获取实际使用的批次号
            batches = self.db_manager.get_test_results_batches(20)

            self.batch_combo.clear()
            self.batch_combo.addItem("全部批次", None)

            for batch in batches:
                batch_id = batch.get('batch_id')
                batch_number = batch.get('batch_number', f'BATCH-{batch_id}')
                test_count = batch.get('test_count', 0)
                # 显示批次号和测试数量
                display_text = f"{batch_number} ({test_count}条)"
                self.batch_combo.addItem(display_text, batch_id)

            self.batch_combo.setEnabled(True)
            logger.debug(f"批次列表加载完成，共{len(batches)}个批次")

        except Exception as e:
            logger.error(f"加载批次列表失败: {e}")
            self.batch_combo.clear()
            self.batch_combo.addItem("加载失败", None)
            self.batch_combo.setEnabled(True)
            QMessageBox.warning(self, "警告", f"加载批次列表失败: {e}")

    def _on_batch_changed(self):
        """批次选择变更处理"""
        current_text = self.batch_combo.currentText()
        if current_text in ["正在加载...", "加载失败"]:
            return

        # 延迟查询，避免频繁查询
        if hasattr(self, '_query_timer'):
            self._query_timer.stop()

        self._query_timer = QTimer()
        self._query_timer.setSingleShot(True)
        self._query_timer.timeout.connect(self._start_new_query)
        self._query_timer.start(300)

    def _on_channel_filter_changed(self, selected_channels):
        """通道筛选条件变更处理"""
        self.channel_filter_manager.update_selected_channels(selected_channels)
        # 延迟查询，避免频繁查询
        self._trigger_delayed_query()

    def _on_battery_code_filter_changed(self, search_text, is_fuzzy):
        """电池码筛选条件变更处理"""
        self.battery_code_filter_manager.update_filter_condition(search_text, is_fuzzy)
        # 延迟查询，避免频繁查询
        self._trigger_delayed_query()

    def _trigger_delayed_query(self):
        """触发延迟查询"""
        if hasattr(self, '_filter_query_timer'):
            self._filter_query_timer.stop()

        self._filter_query_timer = QTimer()
        self._filter_query_timer.setSingleShot(True)
        self._filter_query_timer.timeout.connect(self._start_new_query)
        self._filter_query_timer.start(500)  # 500ms延迟

    def _setup_device_connection_monitoring(self):
        """设置设备连接状态监听"""
        try:
            # 创建定时器定期检查设备连接状态
            self._device_check_timer = QTimer()
            self._device_check_timer.timeout.connect(self._check_device_connection)
            self._device_check_timer.start(5000)  # 每5秒检查一次

            # 初始检查
            self._check_device_connection()

        except Exception as e:
            logger.error(f"设置设备连接监听失败: {e}")

    def _check_device_connection(self):
        """检查设备连接状态并更新通道数量"""
        try:
            # 从通道筛选组件刷新设备信息
            self.channel_filter_widget.refresh_from_device()

        except Exception as e:
            logger.debug(f"检查设备连接状态失败: {e}")

    def _start_new_query(self):
        """开始新的查询"""
        try:
            # 获取查询条件
            query_conditions = self._get_query_conditions()

            # 更新状态
            self._update_status("正在查询数据...")
            self.query_button.setEnabled(False)

            # 使用查询管理器开始查询
            query_worker = self.query_manager.start_new_query(**query_conditions)

            if query_worker:
                # 连接信号
                query_worker.query_completed.connect(self._on_query_completed)
                query_worker.query_failed.connect(self._on_query_failed)
                query_worker.progress_updated.connect(self._update_status)

        except Exception as e:
            logger.error(f"启动查询失败: {e}")
            self._update_status(f"查询失败: {e}")
            self.query_button.setEnabled(True)

    def _get_query_conditions(self):
        """获取当前的查询条件"""
        # 获取基本查询条件
        batch_id = self.batch_combo.currentData()
        batch_text = self.batch_combo.currentText()
        start_date = self.start_date.date().toPyDate()
        end_date = self.end_date.date().toPyDate()
        is_pass = self.result_combo.currentData()

        # 处理批次号查询：如果用户输入了自定义批次号，使用模糊查询
        batch_number = None
        if batch_text and batch_text != "全部批次" and not batch_id:
            # 用户输入了自定义批次号，使用模糊查询
            batch_number = batch_text
            batch_id = None

        # 获取高级筛选条件
        channel_filter_condition = self.channel_filter_manager.get_filter_condition()
        battery_code_filter = self.battery_code_filter_manager.get_filter_condition()

        # 处理通道筛选条件
        channel_number = None
        channel_numbers = None

        # 如果原有的通道下拉框不是"全部"，优先使用它
        original_channel = self.channel_combo.currentData()
        if original_channel is not None:
            channel_number = original_channel
        elif channel_filter_condition is not None:
            # 使用高级筛选的通道条件
            if len(channel_filter_condition) == 0:
                # 全不选，返回空结果
                channel_numbers = []
            else:
                # 部分选择
                channel_numbers = channel_filter_condition

        # 处理电池码筛选条件
        battery_code = None
        battery_code_fuzzy = False
        if battery_code_filter is not None:
            battery_code, battery_code_fuzzy = battery_code_filter

        return {
            'batch_id': batch_id,
            'batch_number': batch_number,
            'start_date': start_date,
            'end_date': end_date,
            'channel_number': channel_number,
            'channel_numbers': channel_numbers,
            'battery_code': battery_code,
            'battery_code_fuzzy': battery_code_fuzzy,
            'is_pass': is_pass
        }

    def _prev_page(self):
        """上一页"""
        try:
            # 获取查询条件
            query_conditions = self._get_query_conditions()

            # 使用查询管理器查询上一页
            query_worker = self.query_manager.prev_page(**query_conditions)

            if query_worker:
                query_worker.query_completed.connect(self._on_query_completed)
                query_worker.query_failed.connect(self._on_query_failed)

        except Exception as e:
            logger.error(f"上一页查询失败: {e}")

    def _next_page(self):
        """下一页"""
        try:
            # 获取查询条件
            query_conditions = self._get_query_conditions()

            # 使用查询管理器查询下一页
            query_worker = self.query_manager.next_page(**query_conditions)

            if query_worker:
                query_worker.query_completed.connect(self._on_query_completed)
                query_worker.query_failed.connect(self._on_query_failed)

        except Exception as e:
            logger.error(f"下一页查询失败: {e}")

    def _load_more_data(self):
        """加载更多数据"""
        try:
            # 获取查询条件
            query_conditions = self._get_query_conditions()

            # 使用查询管理器加载更多数据
            query_worker = self.query_manager.load_more_data(**query_conditions)

            if query_worker:
                query_worker.query_completed.connect(
                    lambda data, total: self._on_query_completed(data, total, append_mode=True)
                )
                query_worker.query_failed.connect(self._on_query_failed)

        except Exception as e:
            logger.error(f"加载更多数据失败: {e}")

    def _delete_selected_data(self):
        """删除选中的数据"""
        try:
            # 获取选中的行（通过复选框）
            selected_rows = []
            for row in range(self.data_table.rowCount()):
                checkbox = self.data_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    selected_rows.append(row)

            if not selected_rows:
                QMessageBox.warning(self, "警告", "请先勾选要删除的数据")
                return

            # 确认对话框
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除选中的 {len(selected_rows)} 条数据吗？\n\n此操作不可撤销！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 获取要删除的数据ID
            delete_ids = []
            for row in selected_rows:
                if row < len(self.current_data):
                    data_item = self.current_data[row]
                    if 'id' in data_item:
                        delete_ids.append(data_item['id'])

            if not delete_ids:
                QMessageBox.warning(self, "警告", "无法获取要删除的数据ID")
                return

            # 执行删除
            self._update_status("正在删除数据...")
            try:
                # 逐个删除数据
                deleted_count = 0
                for data_id in delete_ids:
                    if self.db_manager.delete_test_result(data_id):
                        deleted_count += 1

                if deleted_count > 0:
                    QMessageBox.information(self, "删除成功", f"成功删除 {deleted_count} 条数据")
                    # 刷新批次列表
                    self._load_recent_batches_async()
                    # 重新查询数据
                    self._start_new_query()
                else:
                    QMessageBox.warning(self, "删除失败", "没有数据被删除")
            except AttributeError:
                # 如果数据库管理器没有delete_test_result方法，使用备用方案
                QMessageBox.warning(self, "功能暂不可用", "删除功能暂时不可用，请联系开发人员")

        except Exception as e:
            logger.error(f"删除数据失败: {e}")
            QMessageBox.critical(self, "删除失败", f"删除数据时发生错误：\n{e}")

    def _reset_database(self):
        """重置数据库"""
        try:
            # 确认对话框
            reply = QMessageBox.question(
                self,
                "确认重置",
                "确定要重置整个数据库吗？\n\n这将删除所有测试数据，此操作不可撤销！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 新增询问是否同时清空序列号记录
            clear_serials_reply = QMessageBox.question(
                self,
                "序列号记录",
                "是否同时清空序列号记录？\n\n选择'是'：清空所有已使用的电池码记录，扫码时不会提示重复\n选择'否'：保留序列号记录，扫码时仍会检查重复",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes  # 默认选择清空
            )

            clear_serial_numbers = (clear_serials_reply == QMessageBox.Yes)

            # 二次确认
            confirm_message = "请再次确认：\n\n您真的要删除所有测试数据吗？"
            if clear_serial_numbers:
                confirm_message += "\n同时清空所有序列号记录？"
            confirm_message += "\n\n这个操作无法撤销！"

            reply2 = QMessageBox.question(
                self,
                "最终确认",
                confirm_message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply2 != QMessageBox.Yes:
                return

            # 执行重置
            self._update_status("正在重置数据库...")
            result = self.db_manager.reset_database(keep_batches=True, clear_serial_numbers=clear_serial_numbers)

            if 'error' not in result:
                deleted_count = result.get('deleted_test_results', 0)
                serial_cleared = result.get('serial_numbers_cleared', 0)

                success_message = f"数据库已成功重置\n删除了 {deleted_count} 条测试记录"
                if clear_serial_numbers:
                    success_message += f"\n清空了 {serial_cleared} 个序列号记录"

                QMessageBox.information(self, "重置成功", success_message)

                # 刷新批次列表
                self._load_recent_batches_async()
                # 清空当前显示的数据
                self.current_data = []
                self._update_table()
                self._update_statistics()
            else:
                error_msg = result.get('error', '未知错误')
                QMessageBox.warning(self, "重置失败", f"数据库重置失败：{error_msg}")

        except Exception as e:
            logger.error(f"重置数据库失败: {e}")
            QMessageBox.critical(self, "重置失败", f"重置数据库时发生错误：\n{e}")

    def _manage_serial_numbers(self):
        """序列号管理"""
        try:
            # 获取当前序列号信息
            used_serials = self.config_manager.get('serial_numbers.used_list', [])
            current_sequence = self.config_manager.get('serial_numbers.current_sequence', 1)

            # 创建序列号管理对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("序列号管理")
            dialog.setModal(True)
            dialog.resize(500, 400)

            layout = QVBoxLayout(dialog)

            # 信息显示
            info_group = QGroupBox("序列号统计")
            info_layout = QFormLayout(info_group)

            info_layout.addRow("已使用序列号数量:", QLabel(f"{len(used_serials)} 个"))
            info_layout.addRow("当前序列号计数器:", QLabel(str(current_sequence)))

            layout.addWidget(info_group)

            # 操作按钮
            button_group = QGroupBox("管理操作")
            button_layout = QVBoxLayout(button_group)

            # 清空序列号按钮
            clear_button = QPushButton("清空所有序列号记录")
            clear_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    padding: 8px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            clear_button.clicked.connect(lambda: self._clear_serial_numbers_confirm(dialog))
            button_layout.addWidget(clear_button)

            # 查看序列号列表按钮
            view_button = QPushButton("查看序列号列表")
            view_button.setStyleSheet("""
                QPushButton {
                    background-color: #2196f3;
                    color: white;
                    padding: 8px;
                }
                QPushButton:hover {
                    background-color: #1976d2;
                }
            """)
            view_button.clicked.connect(lambda: self._view_serial_numbers_list(used_serials))
            button_layout.addWidget(view_button)

            layout.addWidget(button_group)

            # 关闭按钮
            close_button = QPushButton("关闭")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)

            dialog.exec_()

        except Exception as e:
            logger.error(f"序列号管理失败: {e}")
            QMessageBox.critical(self, "错误", f"序列号管理时发生错误：\n{e}")

    def _clear_serial_numbers_confirm(self, parent_dialog):
        """确认清空序列号记录"""
        try:
            reply = QMessageBox.question(
                parent_dialog,
                "确认清空",
                "确定要清空所有序列号记录吗？\n\n这将删除所有已使用的电池码记录，\n扫码时不会再提示重复。\n\n此操作不可撤销！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 执行清空
                serial_count = self.db_manager._clear_serial_numbers()

                QMessageBox.information(
                    parent_dialog,
                    "清空成功",
                    f"已成功清空 {serial_count} 个序列号记录"
                )

                # 关闭对话框
                parent_dialog.accept()

        except Exception as e:
            logger.error(f"清空序列号记录失败: {e}")
            QMessageBox.critical(parent_dialog, "清空失败", f"清空序列号记录时发生错误：\n{e}")

    def _view_serial_numbers_list(self, used_serials):
        """查看序列号列表"""
        try:
            # 创建序列号列表对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("序列号列表")
            dialog.setModal(True)
            dialog.resize(600, 500)

            layout = QVBoxLayout(dialog)

            # 信息标签
            info_label = QLabel(f"共 {len(used_serials)} 个已使用的序列号:")
            layout.addWidget(info_label)

            # 序列号列表
            list_widget = QListWidget()
            for serial in sorted(used_serials, reverse=True):  # 按时间倒序排列
                list_widget.addItem(serial)
            layout.addWidget(list_widget)

            # 关闭按钮
            close_button = QPushButton("关闭")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)

            dialog.exec_()

        except Exception as e:
            logger.error(f"查看序列号列表失败: {e}")
            QMessageBox.critical(self, "错误", f"查看序列号列表时发生错误：\n{e}")

    def _on_query_completed(self, data, total_count, append_mode=False):
        """查询完成处理"""
        try:
            if append_mode:
                # 追加模式：添加到现有数据
                self.current_data.extend(data)
                self._append_table_data(data)
            else:
                # 替换模式：替换所有数据
                self.current_data = data
                self._update_table()

            # 更新统计信息
            self._update_statistics()

            # 更新分页信息
            pagination_info = self.query_manager.get_pagination_info()
            self._update_pagination_info(pagination_info)
            self._update_pagination_buttons(True)

            # 更新状态
            self._update_status(f"查询完成，共 {total_count} 条记录")
            self.query_button.setEnabled(True)

            logger.debug(f"查询完成，当前数据量: {len(self.current_data)}")

        except Exception as e:
            logger.error(f"查询完成处理失败: {e}")
            self._update_status(f"数据处理失败: {e}")

    def _on_query_failed(self, error_msg):
        """查询失败处理"""
        logger.error(f"数据查询失败: {error_msg}")
        self._update_status(f"查询失败: {error_msg}")
        self._update_pagination_buttons(False)
        self.query_button.setEnabled(True)

    def _update_table(self):
        """更新表格显示"""
        try:
            total_rows = len(self.current_data)
            self.data_table.setRowCount(total_rows)

            for row, item in enumerate(self.current_data):
                self._populate_table_row(row, item)

            logger.debug(f"表格更新完成，共处理 {total_rows} 行数据")

        except Exception as e:
            logger.error(f"更新表格失败: {e}")

    def _append_table_data(self, new_data):
        """追加表格数据"""
        try:
            current_row_count = self.data_table.rowCount()
            self.data_table.setRowCount(current_row_count + len(new_data))

            for i, item in enumerate(new_data):
                row = current_row_count + i
                self._populate_table_row(row, item)

        except Exception as e:
            logger.error(f"追加表格数据失败: {e}")

    def _populate_table_row(self, row, item):
        """填充表格行数据"""
        try:
            # 选择复选框
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            self.data_table.setCellWidget(row, 0, checkbox)

            # 修复批次号 - 优先从批次表中获取，确保与批次号列表显示一致
            batch_number = (item.get('batch_table_batch_number', '') or
                           item.get('batch_number', ''))
            self.data_table.setItem(row, 1, QTableWidgetItem(str(batch_number)))

            # 通道号
            self.data_table.setItem(row, 2, QTableWidgetItem(str(item.get('channel_number', ''))))

            # 电池编码（统一使用"电池编码"）
            self.data_table.setItem(row, 3, QTableWidgetItem(str(item.get('battery_code', ''))))

            # 测试开始时间
            test_time = item.get('test_start_time', '')
            if isinstance(test_time, str) and len(test_time) > 16:
                test_time = test_time[:16]  # 截取到分钟
            self.data_table.setItem(row, 4, QTableWidgetItem(str(test_time)))

            # 修复添加测试时长字段，只保留整数
            test_duration = item.get('test_duration', 0)
            if test_duration:
                self.data_table.setItem(row, 5, QTableWidgetItem(str(int(test_duration))))
            else:
                self.data_table.setItem(row, 5, QTableWidgetItem(''))

            # 电压
            voltage = item.get('voltage', 0)
            if voltage is not None:
                self.data_table.setItem(row, 6, QTableWidgetItem(f"{voltage:.3f}"))
            else:
                self.data_table.setItem(row, 6, QTableWidgetItem("--"))

            # Rs值
            rs_value = item.get('rs_value', 0)
            if rs_value is not None:
                self.data_table.setItem(row, 7, QTableWidgetItem(f"{rs_value:.3f}"))
            else:
                self.data_table.setItem(row, 7, QTableWidgetItem("--"))

            # Rct值
            rct_value = item.get('rct_value', 0)
            if rct_value is not None:
                self.data_table.setItem(row, 8, QTableWidgetItem(f"{rct_value:.3f}"))
            else:
                self.data_table.setItem(row, 8, QTableWidgetItem("--"))

            # Jack要求移除Rsei、阻抗比、W阻抗、相位角等字段
            # 这些字段已从数据库中删除，不再显示

            # Jack要求移除电容、时间常数、贡献度、健康状态、分析方法等字段
            # 这些字段已从数据库中删除，不再显示

            # 获取测试结果状态，用于后续的档位和范围显示逻辑
            fail_reason = item.get('fail_reason', '')
            is_pass = item.get('is_pass', False)

            # Rs-Rct档位（合并列）- 如果测试结果不合格，显示"--"
            if is_pass:
                rs_grade = item.get('rs_grade', '')
                rct_grade = item.get('rct_grade', '')
                combined_grade = f"{rs_grade}-{rct_grade}"
                self.data_table.setItem(row, 9, QTableWidgetItem(combined_grade))  # 更新列索引
            else:
                self.data_table.setItem(row, 9, QTableWidgetItem("--"))

            # 电压范围 - 从数据库历史记录中获取，而不是从当前配置
            if not is_pass and ('电压' in fail_reason):
                voltage_range_text = "--"
            else:
                voltage_range_text = self._get_voltage_range_from_db(item)
            self.data_table.setItem(row, 10, QTableWidgetItem(voltage_range_text))  # 更新列索引

            # Rs范围 - 从数据库历史记录中获取，而不是从当前配置
            if not is_pass and ('Rs' in fail_reason):
                rs_range_text = "--"
            else:
                rs_range_text = self._get_rs_range_from_db(item)
            self.data_table.setItem(row, 11, QTableWidgetItem(rs_range_text))  # 更新列索引

            # Rct范围 - 从数据库历史记录中获取，而不是从当前配置
            if not is_pass and ('Rct' in fail_reason):
                rct_range_text = "--"
            else:
                rct_range_text = self._get_rct_range_from_db(item)
            self.data_table.setItem(row, 12, QTableWidgetItem(rct_range_text))  # 更新列索引

            # Jack要求移除离群率和基准ID字段
            # 这些字段已从数据库中删除，不再显示

            # Jack要求的测试结果显示逻辑：合格显示"合格"，不合格显示"不合格"
            if is_pass:
                result_text = '合格'
            else:
                result_text = '不合格'

            result_item = QTableWidgetItem(result_text)

            # 设置颜色
            if is_pass:
                result_item.setBackground(QColor('#E8F5E8'))  # 浅绿色
            else:
                result_item.setBackground(QColor('#FFEBEE'))  # 浅红色

            self.data_table.setItem(row, 13, result_item)  # 更新列索引

            # Jack要求的失败原因显示逻辑：合格时空白，不合格时显示具体失败原因
            if is_pass:
                # 合格时失败原因显示空白
                detailed_reason = ''
            else:
                # 不合格时显示具体的失败原因
                if fail_reason:
                    if '电压' in fail_reason:
                        detailed_reason = '电压超标'
                    elif 'Rs' in fail_reason:
                        detailed_reason = 'Rs超标'
                    elif 'Rct' in fail_reason:
                        detailed_reason = 'Rct超标'
                    elif '离群' in fail_reason:
                        detailed_reason = '离群率超标'
                    elif '接触不良' in fail_reason:
                        detailed_reason = '接触不良'
                    elif '失败原因获取异常' in fail_reason:
                        # 🔧 修复：当失败原因获取异常时，根据实际数值判断失败原因
                        detailed_reason = self._analyze_failure_from_values(item)
                    elif '异常' in fail_reason:
                        detailed_reason = '测试异常'
                    else:
                        detailed_reason = '不合格'
                else:
                    # 如果没有失败原因但测试不合格，根据实际数值分析
                    detailed_reason = self._analyze_failure_from_values(item)

            self.data_table.setItem(row, 14, QTableWidgetItem(str(detailed_reason)))  # 更新列索引

            # 修复操作员 - 优先从测试结果记录中获取，如果没有则从批次信息或产品信息中获取
            operator = (item.get('operator', '') or
                       item.get('batch_operator', '') or
                       self.product_info_manager.get_operator())
            self.data_table.setItem(row, 15, QTableWidgetItem(str(operator)))  # 更新列索引

            # 修复电池类型 - 优先从测试结果记录中获取，如果没有则从批次信息或产品信息中获取
            battery_type = (item.get('battery_type', '') or
                           item.get('batch_cell_type', '') or
                           self.product_info_manager.get_battery_type())
            self.data_table.setItem(row, 16, QTableWidgetItem(str(battery_type)))  # 更新列索引

            # 修复规格 - 优先从测试结果记录中获取，如果没有则从批次信息或产品信息中获取
            battery_spec = (item.get('battery_spec', '') or
                           item.get('batch_cell_spec', '') or
                           self.product_info_manager.get_battery_spec())
            self.data_table.setItem(row, 17, QTableWidgetItem(str(battery_spec)))  # 更新列索引

        except Exception as e:
            logger.error(f"填充表格行数据失败: {e}")

    def _analyze_failure_from_values(self, item: dict) -> str:
        """
        根据实际测试数值分析失败原因（当失败原因获取异常时使用）

        Args:
            item: 测试数据项

        Returns:
            分析得出的失败原因
        """
        try:
            voltage = item.get('voltage', 0)
            rs_value = item.get('rs_value', 0)
            rct_value = item.get('rct_value', 0)

            # 获取配置范围（使用默认值）
            voltage_min = 2.5  # 默认电压最小值
            voltage_max = 4.2  # 默认电压最大值
            rs_min = 0.5       # 默认Rs最小值
            rs_max = 50.0      # 默认Rs最大值
            rct_min = 0.5      # 默认Rct最小值
            rct_max = 100.0    # 默认Rct最大值

            # 按优先级检查失败原因
            if voltage < voltage_min or voltage > voltage_max:
                return '电压超标'
            elif rs_value < rs_min or rs_value > rs_max:
                return 'Rs超标'
            elif rct_value < rct_min or rct_value > rct_max:
                return 'Rct超标'
            else:
                return '不合格'

        except Exception as e:
            logger.error(f"分析失败原因失败: {e}")
            return '不合格'

    def _update_statistics(self):
        """更新统计信息"""
        total_count = len(self.current_data)
        pass_count = sum(1 for item in self.current_data if item.get('is_pass'))
        fail_count = total_count - pass_count
        yield_rate = (pass_count / total_count * 100) if total_count > 0 else 0.0

        self.total_label.setText(f"总数: {total_count}")
        self.pass_label.setText(f"合格: {pass_count}")
        self.fail_label.setText(f"不合格: {fail_count}")
        self.yield_label.setText(f"良率: {yield_rate:.1f}%")

    def _update_pagination_info(self, pagination_info):
        """更新分页信息"""
        current_page = pagination_info['current_page']
        total_pages = pagination_info['total_pages']

        if total_pages > 0:
            self.page_info_label.setText(f"第 {current_page + 1} 页，共 {total_pages} 页")
        else:
            self.page_info_label.setText("第 0 页，共 0 页")

    def _update_pagination_buttons(self, enabled):
        """更新分页按钮状态"""
        if enabled:
            pagination_info = self.query_manager.get_pagination_info()
            self.prev_button.setEnabled(pagination_info['has_prev'])
            self.next_button.setEnabled(pagination_info['has_next'])
            self.load_more_button.setEnabled(pagination_info['has_next'])
        else:
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.load_more_button.setEnabled(False)

    def _update_status(self, message):
        """更新状态信息"""
        self.status_label.setText(message)

    def _on_result_selection_changed(self):
        """测试结果选择变更处理"""
        try:
            selected_rows = set()
            for item in self.data_table.selectedItems():
                selected_rows.add(item.row())

            if not selected_rows:
                # 没有选择，清空明细数据
                self._clear_impedance_details()
                return

            # 获取选中的第一行数据
            row = list(selected_rows)[0]
            if row < len(self.current_data):
                test_result = self.current_data[row]
                self._load_impedance_details(test_result)

        except Exception as e:
            logger.error(f"处理结果选择变更失败: {e}")

    def _load_impedance_details(self, test_result: Dict):
        """加载阻抗明细数据"""
        try:
            # 查询明细数据
            details = self.db_manager.get_impedance_details(
                batch_id=test_result.get('batch_id'),
                channel_number=test_result.get('channel_number'),
                battery_code=test_result.get('battery_code')
            )

            if details:
                # 更新明细数据表格
                self._update_details_table(details)

                # 检查是否启用了多通道对比模式
                if hasattr(self.plot_manager, '_multi_channel_mode') and self.plot_manager._multi_channel_mode:
                    # 多通道模式：添加到对比显示
                    self.plot_manager.add_channel_to_comparison(details, test_result)
                else:
                    # 单通道模式：直接更新显示
                    self.plot_manager.update_single_channel_plot(details, test_result)
            else:
                self._clear_impedance_details()

        except Exception as e:
            logger.error(f"加载阻抗明细数据失败: {e}")
            self._clear_impedance_details()

    def _update_details_table(self, details: List[Dict]):
        """更新明细数据表格"""
        self.details_table.setRowCount(len(details))

        for row, detail in enumerate(details):
            # 时间戳
            timestamp = detail.get('test_timestamp', '')
            if isinstance(timestamp, str) and len(timestamp) > 19:
                timestamp = timestamp[:19]  # 截取到秒
            self.details_table.setItem(row, 0, QTableWidgetItem(str(timestamp)))

            # 频率
            frequency = detail.get('frequency', 0)
            self.details_table.setItem(row, 1, QTableWidgetItem(f"{frequency:.3f}"))

            # 实部阻抗 - 改为3位小数显示
            real_impedance = detail.get('impedance_real', 0)
            self.details_table.setItem(row, 2, QTableWidgetItem(f"{real_impedance:.3f}"))

            # 虚部阻抗 - 改为3位小数显示
            imag_impedance = detail.get('impedance_imag', 0)
            self.details_table.setItem(row, 3, QTableWidgetItem(f"{imag_impedance:.3f}"))

            # Z值 - 改为3位小数显示
            z_value = (real_impedance**2 + imag_impedance**2)**0.5
            self.details_table.setItem(row, 4, QTableWidgetItem(f"{z_value:.3f}"))

            # 电压
            voltage = detail.get('voltage', 0)
            self.details_table.setItem(row, 5, QTableWidgetItem(f"{voltage:.3f}"))

            # 相位（计算）
            import math
            if real_impedance != 0:
                phase = math.atan2(imag_impedance, real_impedance) * 180 / math.pi
            else:
                phase = 0
            self.details_table.setItem(row, 6, QTableWidgetItem(f"{phase:.2f}"))

            # 序号
            sequence = detail.get('test_sequence', 0)
            self.details_table.setItem(row, 7, QTableWidgetItem(str(sequence)))

    def _clear_impedance_details(self):
        """清空明细数据"""
        self.details_table.setRowCount(0)
        self.plot_manager.clear_plot()

    def _get_selected_data(self) -> List[Dict]:
        """获取选中的数据"""
        selected_data = []
        selected_rows = set()

        # 获取选中的行
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())

        # 根据选中的行获取对应的数据
        for row in selected_rows:
            if row < len(self.current_data):
                selected_data.append(self.current_data[row])

        return selected_data

    def _export_data(self):
        """导出数据"""
        if not self.current_data:
            QMessageBox.warning(self, "警告", "没有数据可导出！")
            return

        # 获取导出格式
        export_format = self.format_combo.currentData()

        # 选择文件路径
        if export_format == "Excel":
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出Excel文件", f"测试数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel文件 (*.xlsx)"
            )
        else:  # CSV
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出CSV文件", f"测试数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV文件 (*.csv)"
            )

        if not file_path:
            return

        # 开始导出
        self._start_export(file_path, export_format, self.current_data)

    def _export_selected_data(self):
        """导出选中的数据"""
        selected_data = self._get_selected_data()

        if not selected_data:
            QMessageBox.warning(self, "警告", "请先选择要导出的数据！")
            return

        # 获取导出格式
        export_format = self.format_combo.currentData()

        # 选择文件路径
        if export_format == "Excel":
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出选中数据Excel文件",
                f"选中数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel文件 (*.xlsx)"
            )
        else:  # CSV
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出选中数据CSV文件",
                f"选中数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV文件 (*.csv)"
            )

        if not file_path:
            return

        # 开始导出选中数据
        self._start_export(file_path, export_format, selected_data)

    def _upload_selected_data(self):
        """上传选中的数据到云端"""
        selected_data = self._get_selected_data()

        if not selected_data:
            QMessageBox.warning(self, "警告", "请先选择要上传的数据！")
            return

        # 确认上传
        reply = QMessageBox.question(
            self, "确认上传",
            f"确定要上传选中的 {len(selected_data)} 条数据到云端吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            # 导入数据上传管理器
            from backend.data_upload_manager import DataUploadManager
            from utils.config_manager import ConfigManager

            # 获取上传配置
            config_manager = ConfigManager()
            upload_config = config_manager.get('data_upload', {})

            if not upload_config.get('enabled', False):
                QMessageBox.warning(
                    self, "警告",
                    "数据上传功能未启用！\n请在设置中启用数据上传功能。"
                )
                return

            # 创建数据上传管理器
            upload_manager = DataUploadManager(upload_config)

            # 测试连接
            if not upload_manager.test_connection():
                QMessageBox.critical(
                    self, "连接失败",
                    "无法连接到服务器！\n请检查网络连接和服务器配置。"
                )
                return

            # 创建进度对话框
            progress_dialog = QProgressDialog("正在上传数据...", "取消", 0, len(selected_data), self)
            progress_dialog.setWindowTitle("数据上传")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.show()

            # 上传数据
            uploaded_count = 0
            failed_count = 0

            for i, data_row in enumerate(selected_data):
                if progress_dialog.wasCanceled():
                    break

                try:
                    # 转换数据格式为测试结果格式
                    test_result = self._convert_to_test_result_format(data_row)

                    # 创建批次信息
                    batch_info = {
                        'batch_number': data_row.get('batch_number', 'MANUAL_UPLOAD'),
                        'operator': data_row.get('operator', 'DataAnalysis'),
                        'cell_type': data_row.get('battery_type', '磷酸铁锂'),
                        'cell_spec': data_row.get('battery_spec', '21700')
                    }

                    # 上传测试结果
                    upload_manager.upload_test_result(test_result, batch_info)
                    uploaded_count += 1

                except Exception as e:
                    logger.error(f"上传数据失败: {e}")
                    failed_count += 1

                # 更新进度
                progress_dialog.setValue(i + 1)
                QApplication.processEvents()

            progress_dialog.close()

            # 等待上传完成
            import time
            time.sleep(2)

            # 显示结果
            if uploaded_count > 0:
                QMessageBox.information(
                    self, "上传完成",
                    f"数据上传完成！\n"
                    f"成功上传: {uploaded_count} 条\n"
                    f"失败: {failed_count} 条"
                )
                logger.info(f"手动上传数据完成: 成功{uploaded_count}条, 失败{failed_count}条")
            else:
                QMessageBox.warning(self, "上传失败", "没有数据成功上传！")

        except Exception as e:
            logger.error(f"手动上传数据失败: {e}")
            QMessageBox.critical(
                self, "上传错误",
                f"上传过程中发生错误：\n{str(e)}"
            )

    def _convert_to_test_result_format(self, data_row: Dict) -> Dict:
        """将数据行转换为测试结果格式"""
        try:
            # 解析时间戳
            timestamp = data_row.get('test_start_time')
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now()
            elif timestamp is None:
                timestamp = datetime.now()

            # 构建测试结果数据
            test_result = {
                'channel_number': data_row.get('channel_number', 1),
                'timestamp': timestamp,
                'voltage': data_row.get('voltage', 0.0),
                'rs_value': data_row.get('rs_value', 0.0),
                'rct_value': data_row.get('rct_value', 0.0),
                'capacity': data_row.get('capacity', 3000),
                'temperature': data_row.get('temperature', 25.0),
                'is_pass': data_row.get('is_pass', True),
                'battery_code': data_row.get('battery_code', ''),

                # 详细数据
                'test_start_time': data_row.get('test_start_time'),
                'test_end_time': data_row.get('test_end_time'),
                'test_duration': data_row.get('test_duration', 0),
                'test_mode': data_row.get('test_mode', '手动上传'),
                'operator': data_row.get('operator', 'DataAnalysis'),
                'battery_type': data_row.get('battery_type', '磷酸铁锂'),
                'battery_spec': data_row.get('battery_spec', '21700'),
                'batch_number': data_row.get('batch_number', 'MANUAL_UPLOAD'),

                # EIS分析结果
                'w_impedance': data_row.get('w_impedance', 0.0),
                'rsei_value': data_row.get('rsei_value', 0.0),
                'rs_grade': data_row.get('rs_grade', ''),
                'rct_grade': data_row.get('rct_grade', ''),
                'fail_reason': data_row.get('fail_reason', ''),

                # 频率数据（如果有的话，从数据库查询）
                'frequency_data': self._get_frequency_data_for_result(data_row.get('id'))
            }

            return test_result

        except Exception as e:
            logger.error(f"转换数据格式失败: {e}")
            raise

    def _get_frequency_data_for_result(self, result_id: int) -> List[Dict]:
        """获取测试结果的频率数据"""
        if not result_id:
            return []

        try:
            query = """
                SELECT frequency, impedance_real, impedance_imag,
                       impedance_magnitude, phase_angle
                FROM impedance_details
                WHERE test_result_id = ?
                ORDER BY frequency DESC
            """

            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (result_id,))
                results = cursor.fetchall()

            frequency_data = []
            for row in results:
                frequency_data.append({
                    'frequency': row[0],
                    'impedance_real': row[1],
                    'impedance_imag': row[2],
                    'impedance_magnitude': row[3],
                    'impedance_phase': row[4]
                })

            return frequency_data

        except Exception as e:
            logger.error(f"获取频率数据失败: {e}")
            return []

    def _start_export(self, file_path: str, export_format: str, data_to_export: List[Dict] = None):
        """开始导出任务"""
        # 如果没有指定数据，使用当前数据
        if data_to_export is None:
            data_to_export = self.current_data

        # 禁用按钮
        self.export_button.setEnabled(False)
        self.export_selected_button.setEnabled(False)
        self.query_button.setEnabled(False)

        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # 使用导出管理器开始导出
        export_worker = self.export_manager.start_export(data_to_export, file_path, export_format)

        if export_worker:
            # 连接信号
            export_worker.progress_updated.connect(self.progress_bar.setValue)
            export_worker.export_completed.connect(self._on_export_completed)
            export_worker.export_failed.connect(self._on_export_failed)

    def _on_export_completed(self, file_path: str):
        """导出完成处理"""
        # 恢复界面
        self.export_button.setEnabled(True)
        self.export_selected_button.setEnabled(True)
        self.query_button.setEnabled(True)
        self.progress_bar.setVisible(False)

        # 显示成功消息
        QMessageBox.information(
            self, "导出成功",
            f"数据导出成功！\n文件路径: {file_path}"
        )

        logger.info(f"数据导出成功: {file_path}")

    def _on_export_failed(self, error_msg: str):
        """导出失败处理"""
        # 恢复界面
        self.export_button.setEnabled(True)
        self.export_selected_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.query_button.setEnabled(True)
        self.progress_bar.setVisible(False)

        # 显示错误消息
        QMessageBox.critical(self, "导出失败", f"数据导出失败: {error_msg}")

        logger.error(f"数据导出失败: {error_msg}")

    def _toggle_fullscreen(self):
        """切换全屏显示"""
        try:
            if not self._is_fullscreen:
                # 进入全屏模式
                self._normal_geometry = self.geometry()
                self.showFullScreen()
                self._is_fullscreen = True
                self.fullscreen_button.setText("退出全屏")
            else:
                # 退出全屏模式
                self.showNormal()
                if self._normal_geometry is not None:
                    self.setGeometry(self._normal_geometry)
                self._is_fullscreen = False
                self.fullscreen_button.setText("全屏显示")

        except Exception as e:
            logger.error(f"切换全屏模式失败: {e}")
            QMessageBox.warning(self, "警告", f"切换全屏模式失败: {e}")

    def _set_default_fullscreen(self):
        """设置默认全屏显示"""
        try:
            # 延迟执行全屏，确保界面完全初始化
            QTimer.singleShot(100, self._apply_fullscreen)
            logger.debug("设置默认全屏显示")
        except Exception as e:
            logger.error(f"设置默认全屏失败: {e}")

    def _apply_fullscreen(self):
        """应用全屏显示"""
        try:
            if not self._is_fullscreen:
                self._normal_geometry = self.geometry()
                self.showFullScreen()
                self._is_fullscreen = True
                self.fullscreen_button.setText("退出全屏")
                logger.info("应用默认全屏模式")
        except Exception as e:
            logger.error(f"应用全屏模式失败: {e}")

    def keyPressEvent(self, event):
        """键盘事件处理"""
        # F11键切换全屏
        if event.key() == Qt.Key.Key_F11:
            self._toggle_fullscreen()
        # ESC键退出全屏
        elif event.key() == Qt.Key.Key_Escape and self._is_fullscreen:
            self._toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 如果正在导出，询问是否取消
        if self.export_manager.is_exporting():
            reply = QMessageBox.question(
                self, "确认关闭",
                "正在导出数据，确定要关闭窗口吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.No:
                event.ignore()
                return
            else:
                # 停止导出
                self.export_manager.stop_export()

        # 清理资源
        try:
            self.query_manager.cleanup()
            self.export_manager.cleanup()
            self.plot_manager.cleanup()
        except Exception as e:
            logger.error(f"清理资源失败: {e}")

    # DRT功能已移除

    # DRT功能已移除



    # DRT功能已移除

    # DRT功能已移除

    # DRT功能已移除

    def _show_continuous_test_report(self):
        """显示连续测试报告"""
        try:
            logger.info("打开连续测试报告对话框")

            # 查询连续测试数据
            continuous_data = self._query_continuous_test_data()

            if not continuous_data:
                QMessageBox.information(
                    self,
                    "提示",
                    "未找到连续测试数据。\n\n请确保已进行过连续测试。"
                )
                return

            # 导入连续测试报告对话框
            from ui.continuous_test_report_dialog import ContinuousTestReportDialog

            # 创建并显示报告对话框
            report_dialog = ContinuousTestReportDialog(self, continuous_data)
            report_dialog.exec_()

        except Exception as e:
            logger.error(f"显示连续测试报告失败: {e}")
            QMessageBox.critical(
                self,
                "错误",
                f"打开连续测试报告失败：\n{str(e)}"
            )

    def _query_continuous_test_data(self) -> Dict:
        """查询连续测试数据"""
        try:
            logger.debug("开始查询连续测试数据")

            # 查询连续测试模式的数据
            query = """
                SELECT
                    id, batch_id, channel_number, battery_code,
                    test_start_time, test_end_time, test_duration,
                    voltage, rs_value, rct_value, rsei_value, w_impedance,
                    rs_grade, rct_grade, is_pass, fail_reason,
                    test_mode, created_at,
                    -- 🔋 新增：完整EIS参数
                    warburg_coefficient, has_warburg_diffusion, has_sei,
                    health_status, health_score, analysis_method
                FROM test_results
                WHERE test_mode LIKE '%连续%'
                ORDER BY created_at DESC
                LIMIT 1000
            """

            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                results = cursor.fetchall()

            if not results:
                logger.info("未找到连续测试数据")
                return {}

            # 转换为字典格式
            continuous_tests = []
            for row in results:
                test_data = {
                    'id': row[0],
                    'batch_id': row[1],
                    'channel_number': row[2],
                    'battery_code': row[3],
                    'test_start_time': row[4],
                    'test_end_time': row[5],
                    'test_duration': row[6],
                    'voltage': row[7],
                    'rs_value': row[8],
                    'rct_value': row[9],
                    'rsei_value': row[10],
                    'w_impedance': row[11],
                    'rs_grade': row[12],
                    'rct_grade': row[13],
                    'is_pass': row[14],
                    'fail_reason': row[15],
                    'test_mode': row[16],
                    'created_at': row[17],
                    'warburg_coefficient': row[18],
                    'has_warburg_diffusion': row[19],
                    'has_sei': row[20],
                    'health_status': row[21],
                    'health_score': row[22],
                    'analysis_method': row[23]
                }
                continuous_tests.append(test_data)

            # 构建报告数据
            report_data = {
                'test_results': continuous_tests,
                'total_tests': len(continuous_tests),
                'query_time': datetime.now().isoformat(),
                'data_source': 'database'
            }

            logger.info(f"查询到 {len(continuous_tests)} 条连续测试记录")
            return report_data

        except Exception as e:
            logger.error(f"查询连续测试数据失败: {e}")
            return {}

        event.accept()
        logger.debug("数据导出对话框已关闭")
