# -*- coding: utf-8 -*-
"""
连续测试报告对话框

显示详细的连续测试统计信息和分析结果

Author: Jack
Date: 2025-01-03
"""

import json
import statistics
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QTableWidget, QTableWidgetItem, QLabel, QPushButton,
                             QGroupBox, QGridLayout, QHeaderView,
                             QFileDialog, QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QBrush

import logging

logger = logging.getLogger(__name__)


class ContinuousTestReportDialog(QDialog):
    """连续测试报告对话框"""
    
    def __init__(self, parent=None, report_data=None):
        super().__init__(parent)
        self.report_data = report_data or {}
        self.init_ui()
        self.load_report_data()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("连续测试报告")
        self.setGeometry(100, 100, 1200, 800)
        self.setModal(True)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 标题区域
        title_layout = self.create_title_section()
        main_layout.addLayout(title_layout)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # 测试统计标签页
        self.statistics_tab = self.create_statistics_tab()
        self.tab_widget.addTab(self.statistics_tab, "📊 测试统计")
        
        # 通道分析标签页
        self.channel_analysis_tab = self.create_channel_analysis_tab()
        self.tab_widget.addTab(self.channel_analysis_tab, "📈 通道分析")

        # EIS阻抗分析标签页
        self.eis_analysis_tab = self.create_eis_analysis_tab()
        self.tab_widget.addTab(self.eis_analysis_tab, "🔬 EIS阻抗分析")

        # 详细数据标签页
        self.detailed_data_tab = self.create_detailed_data_tab()
        self.tab_widget.addTab(self.detailed_data_tab, "📋 详细数据")
        
        main_layout.addWidget(self.tab_widget)
        
        # 按钮区域
        button_layout = self.create_button_section()
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def create_title_section(self):
        """创建标题区域"""
        layout = QVBoxLayout()
        
        # 主标题
        title_label = QLabel("🔄 连续测试报告")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2E86AB; margin: 10px;")
        layout.addWidget(title_label)
        
        # 基本信息
        info_layout = QHBoxLayout()
        
        self.test_time_label = QLabel("测试时间: --")
        self.test_time_label.setFont(QFont("Arial", 10))
        info_layout.addWidget(self.test_time_label)
        
        info_layout.addStretch()
        
        self.total_cycles_label = QLabel("总循环次数: --")
        self.total_cycles_label.setFont(QFont("Arial", 10, QFont.Bold))
        info_layout.addWidget(self.total_cycles_label)
        
        layout.addLayout(info_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        return layout
    
    def create_statistics_tab(self):
        """创建测试统计标签页"""
        widget = QFrame()
        layout = QVBoxLayout()
        
        # 时间统计组
        time_group = QGroupBox("⏱️ 时间统计")
        time_layout = QGridLayout()
        
        self.avg_time_label = QLabel("平均测试时间: --")
        self.min_time_label = QLabel("最短测试时间: --")
        self.max_time_label = QLabel("最长测试时间: --")
        self.total_time_label = QLabel("总测试时间: --")
        
        time_layout.addWidget(self.avg_time_label, 0, 0)
        time_layout.addWidget(self.min_time_label, 0, 1)
        time_layout.addWidget(self.max_time_label, 1, 0)
        time_layout.addWidget(self.total_time_label, 1, 1)
        
        time_group.setLayout(time_layout)
        layout.addWidget(time_group)
        
        # 测试结果统计组
        result_group = QGroupBox("✅ 测试结果统计")
        result_layout = QGridLayout()
        
        self.pass_rate_label = QLabel("合格率: --")
        self.total_tests_label = QLabel("总测试数: --")
        self.passed_tests_label = QLabel("合格数: --")
        self.failed_tests_label = QLabel("不合格数: --")
        
        result_layout.addWidget(self.pass_rate_label, 0, 0)
        result_layout.addWidget(self.total_tests_label, 0, 1)
        result_layout.addWidget(self.passed_tests_label, 1, 0)
        result_layout.addWidget(self.failed_tests_label, 1, 1)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        # 每轮测试时间表格
        cycle_group = QGroupBox("🔄 各轮测试时间")
        cycle_layout = QVBoxLayout()
        
        self.cycle_time_table = QTableWidget()
        self.cycle_time_table.setColumnCount(3)
        self.cycle_time_table.setHorizontalHeaderLabels(["轮次", "测试时间(秒)", "状态"])
        self.cycle_time_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        cycle_layout.addWidget(self.cycle_time_table)
        cycle_group.setLayout(cycle_layout)
        layout.addWidget(cycle_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_channel_analysis_tab(self):
        """创建通道分析标签页"""
        widget = QFrame()
        layout = QVBoxLayout()

        # Rs值分析组
        rs_group = QGroupBox("🔧 Rs值分析 (mΩ)")
        rs_layout = QVBoxLayout()

        self.rs_analysis_table = QTableWidget()
        self.rs_analysis_table.setColumnCount(6)
        self.rs_analysis_table.setHorizontalHeaderLabels(["通道号", "平均值(mΩ)", "最大值(mΩ)", "最小值(mΩ)", "标准差(mΩ)", "变异系数(%)"])
        self.rs_analysis_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        rs_layout.addWidget(self.rs_analysis_table)
        rs_group.setLayout(rs_layout)
        layout.addWidget(rs_group)

        # Rct值分析组
        rct_group = QGroupBox("⚡ Rct值分析 (mΩ)")
        rct_layout = QVBoxLayout()

        self.rct_analysis_table = QTableWidget()
        self.rct_analysis_table.setColumnCount(6)
        self.rct_analysis_table.setHorizontalHeaderLabels(["通道号", "平均值(mΩ)", "最大值(mΩ)", "最小值(mΩ)", "标准差(mΩ)", "变异系数(%)"])
        self.rct_analysis_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        rct_layout.addWidget(self.rct_analysis_table)
        rct_group.setLayout(rct_layout)
        layout.addWidget(rct_group)

        # 离散度分析表格
        dispersion_group = QGroupBox("📊 离散度分析")
        dispersion_layout = QVBoxLayout()

        self.dispersion_table = QTableWidget()
        self.dispersion_table.setColumnCount(4)
        self.dispersion_table.setHorizontalHeaderLabels(["分析项目", "平均变异系数(%)", "评价等级", "数据一致性"])
        self.dispersion_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dispersion_table.setMaximumHeight(150)

        dispersion_layout.addWidget(self.dispersion_table)
        dispersion_group.setLayout(dispersion_layout)
        layout.addWidget(dispersion_group)

        widget.setLayout(layout)
        return widget

    def create_eis_analysis_tab(self):
        """创建EIS阻抗分析标签页"""
        widget = QFrame()
        layout = QVBoxLayout()

        # 频点阻抗统计表格
        impedance_group = QGroupBox("🔬 频点阻抗统计分析")
        impedance_layout = QVBoxLayout()

        self.impedance_stats_table = QTableWidget()
        self.impedance_stats_table.setColumnCount(8)
        self.impedance_stats_table.setHorizontalHeaderLabels([
            "频率(Hz)", "阻抗幅值|Z|(mΩ)", "相位角θ(°)", "测试次数",
            "|Z|变异系数(%)", "θ变异系数(%)", "|Z|范围", "θ范围"
        ])
        self.impedance_stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        impedance_layout.addWidget(self.impedance_stats_table)
        impedance_group.setLayout(impedance_layout)
        layout.addWidget(impedance_group)

        # 一致性评价表格
        consistency_group = QGroupBox("📊 EIS一致性评价")
        consistency_layout = QVBoxLayout()

        self.consistency_table = QTableWidget()
        self.consistency_table.setColumnCount(4)
        self.consistency_table.setHorizontalHeaderLabels([
            "评价项目", "评价结果", "数值指标", "建议"
        ])
        self.consistency_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.consistency_table.setMaximumHeight(200)

        consistency_layout.addWidget(self.consistency_table)
        consistency_group.setLayout(consistency_layout)
        layout.addWidget(consistency_group)

        # 异常频点识别表格
        anomaly_group = QGroupBox("⚠️ 异常频点识别")
        anomaly_layout = QVBoxLayout()

        self.anomaly_table = QTableWidget()
        self.anomaly_table.setColumnCount(5)
        self.anomaly_table.setHorizontalHeaderLabels([
            "频率(Hz)", "异常类型", "异常程度", "影响通道", "建议措施"
        ])
        self.anomaly_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.anomaly_table.setMaximumHeight(200)

        anomaly_layout.addWidget(self.anomaly_table)
        anomaly_group.setLayout(anomaly_layout)
        layout.addWidget(anomaly_group)

        widget.setLayout(layout)
        return widget

    def create_detailed_data_tab(self):
        """创建详细数据标签页"""
        widget = QFrame()
        layout = QVBoxLayout()
        
        # 详细测试数据表格
        self.detailed_table = QTableWidget()
        self.detailed_table.setColumnCount(8)
        self.detailed_table.setHorizontalHeaderLabels([
            "测试轮次", "通道号", "电压(V)", "Rs(mΩ)", "Rct(mΩ)",
            "Rs档位", "Rct档位", "测试结果"
        ])
        self.detailed_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.detailed_table)
        
        widget.setLayout(layout)
        return widget
    
    def create_button_section(self):
        """创建按钮区域"""
        layout = QHBoxLayout()

        # 生成分析报告按钮
        self.analysis_btn = QPushButton("📊 生成分析报告")
        self.analysis_btn.clicked.connect(self.generate_analysis_report)
        layout.addWidget(self.analysis_btn)

        # 导出Excel报告按钮
        self.export_excel_btn = QPushButton("📄 导出Excel报告")
        self.export_excel_btn.clicked.connect(self.export_excel_report)
        layout.addWidget(self.export_excel_btn)

        # 原有导出按钮（JSON格式）
        self.export_btn = QPushButton("💾 导出JSON")
        self.export_btn.clicked.connect(self.export_report)
        layout.addWidget(self.export_btn)

        layout.addStretch()

        # 🗑️ 新增：删除功能按钮
        self.delete_selected_btn = QPushButton("🗑️ 删除选中")
        self.delete_selected_btn.clicked.connect(self.delete_selected_records)
        self.delete_selected_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        layout.addWidget(self.delete_selected_btn)

        self.clear_all_btn = QPushButton("🧹 清除全部")
        self.clear_all_btn.clicked.connect(self.clear_all_records)
        self.clear_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5722;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e64a19;
            }
            QPushButton:pressed {
                background-color: #d84315;
            }
        """)
        layout.addWidget(self.clear_all_btn)

        # 关闭按钮
        self.close_btn = QPushButton("❌ 关闭")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)

        return layout
    
    def load_report_data(self):
        """加载报告数据"""
        try:
            if not self.report_data:
                logger.warning("没有报告数据可加载")
                return
            
            # 加载基本信息
            self.load_basic_info()
            
            # 加载统计数据
            self.load_statistics_data()
            
            # 加载通道分析数据
            self.load_channel_analysis_data()

            # 加载EIS分析数据
            self.load_eis_analysis_data()

            # 加载详细数据
            self.load_detailed_data()
            
            logger.info("连续测试报告数据加载完成")
            
        except Exception as e:
            logger.error(f"加载报告数据失败: {e}")
    
    def load_basic_info(self):
        """加载基本信息"""
        try:
            # 测试时间
            start_time = self.report_data.get('start_time', '')
            end_time = self.report_data.get('end_time', '')
            if start_time and end_time:
                self.test_time_label.setText(f"测试时间: {start_time} ~ {end_time}")

            # 总循环次数
            total_cycles = self.report_data.get('total_cycles', 0)
            self.total_cycles_label.setText(f"总循环次数: {total_cycles}")

        except Exception as e:
            logger.error(f"加载基本信息失败: {e}")

    def load_statistics_data(self):
        """加载统计数据"""
        try:
            cycle_times = self.report_data.get('cycle_times', [])
            test_results = self.report_data.get('test_results', [])

            if cycle_times:
                # 时间统计
                avg_time = statistics.mean(cycle_times)
                min_time = min(cycle_times)
                max_time = max(cycle_times)
                total_time = sum(cycle_times)

                self.avg_time_label.setText(f"平均测试时间: {avg_time:.1f}秒")
                self.min_time_label.setText(f"最短测试时间: {min_time:.1f}秒")
                self.max_time_label.setText(f"最长测试时间: {max_time:.1f}秒")
                self.total_time_label.setText(f"总测试时间: {total_time:.1f}秒")

                # 填充各轮测试时间表格
                self.cycle_time_table.setRowCount(len(cycle_times))
                for i, cycle_time in enumerate(cycle_times):
                    self.cycle_time_table.setItem(i, 0, QTableWidgetItem(f"第{i+1}轮"))
                    self.cycle_time_table.setItem(i, 1, QTableWidgetItem(f"{cycle_time:.1f}"))

                    # 状态判断
                    if cycle_time > avg_time * 1.2:
                        status = "较慢"
                        color = QColor(255, 200, 200)  # 浅红色
                    elif cycle_time < avg_time * 0.8:
                        status = "较快"
                        color = QColor(200, 255, 200)  # 浅绿色
                    else:
                        status = "正常"
                        color = QColor(255, 255, 255)  # 白色

                    status_item = QTableWidgetItem(status)
                    status_item.setBackground(QBrush(color))
                    self.cycle_time_table.setItem(i, 2, status_item)

            # 测试结果统计
            if test_results:
                total_tests = len(test_results)
                passed_tests = sum(1 for result in test_results if result.get('is_pass', False))
                failed_tests = total_tests - passed_tests
                pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

                self.total_tests_label.setText(f"总测试数: {total_tests}")
                self.passed_tests_label.setText(f"合格数: {passed_tests}")
                self.failed_tests_label.setText(f"不合格数: {failed_tests}")
                self.pass_rate_label.setText(f"合格率: {pass_rate:.1f}%")

        except Exception as e:
            logger.error(f"加载统计数据失败: {e}")

    def load_channel_analysis_data(self):
        """加载通道分析数据"""
        try:
            test_results = self.report_data.get('test_results', [])
            if not test_results:
                return

            # 按通道分组数据
            channel_data = {}
            for result in test_results:
                channel = result.get('channel', 0)
                if channel not in channel_data:
                    channel_data[channel] = {'rs_values': [], 'rct_values': []}

                rs_value = result.get('rs_value', 0)
                rct_value = result.get('rct_value', 0)

                if rs_value > 0:
                    channel_data[channel]['rs_values'].append(rs_value)
                if rct_value > 0:
                    channel_data[channel]['rct_values'].append(rct_value)

            # 分析Rs值
            self.rs_analysis_table.setRowCount(len(channel_data))
            for i, (channel, data) in enumerate(sorted(channel_data.items())):
                rs_values = data['rs_values']
                if rs_values:
                    avg_rs = statistics.mean(rs_values)
                    max_rs = max(rs_values)
                    min_rs = min(rs_values)
                    std_rs = statistics.stdev(rs_values) if len(rs_values) > 1 else 0
                    cv_rs = (std_rs / avg_rs * 100) if avg_rs > 0 else 0

                    self.rs_analysis_table.setItem(i, 0, QTableWidgetItem(f"通道{channel}"))
                    self.rs_analysis_table.setItem(i, 1, QTableWidgetItem(f"{avg_rs:.3f}"))
                    self.rs_analysis_table.setItem(i, 2, QTableWidgetItem(f"{max_rs:.3f}"))
                    self.rs_analysis_table.setItem(i, 3, QTableWidgetItem(f"{min_rs:.3f}"))
                    self.rs_analysis_table.setItem(i, 4, QTableWidgetItem(f"{std_rs:.3f}"))
                    self.rs_analysis_table.setItem(i, 5, QTableWidgetItem(f"{cv_rs:.2f}%"))

            # 分析Rct值
            self.rct_analysis_table.setRowCount(len(channel_data))
            for i, (channel, data) in enumerate(sorted(channel_data.items())):
                rct_values = data['rct_values']
                if rct_values:
                    avg_rct = statistics.mean(rct_values)
                    max_rct = max(rct_values)
                    min_rct = min(rct_values)
                    std_rct = statistics.stdev(rct_values) if len(rct_values) > 1 else 0
                    cv_rct = (std_rct / avg_rct * 100) if avg_rct > 0 else 0

                    self.rct_analysis_table.setItem(i, 0, QTableWidgetItem(f"通道{channel}"))
                    self.rct_analysis_table.setItem(i, 1, QTableWidgetItem(f"{avg_rct:.3f}"))
                    self.rct_analysis_table.setItem(i, 2, QTableWidgetItem(f"{max_rct:.3f}"))
                    self.rct_analysis_table.setItem(i, 3, QTableWidgetItem(f"{min_rct:.3f}"))
                    self.rct_analysis_table.setItem(i, 4, QTableWidgetItem(f"{std_rct:.3f}"))
                    self.rct_analysis_table.setItem(i, 5, QTableWidgetItem(f"{cv_rct:.2f}%"))

            # 生成离散度分析报告
            self.generate_dispersion_analysis(channel_data)

        except Exception as e:
            logger.error(f"加载通道分析数据失败: {e}")

    def generate_dispersion_analysis(self, channel_data):
        """生成离散度分析报告（表格形式）"""
        try:
            # 计算Rs值离散度分析
            rs_cvs = []
            for channel, data in channel_data.items():
                rs_values = data['rs_values']
                if len(rs_values) > 1:
                    avg_rs = statistics.mean(rs_values)
                    std_rs = statistics.stdev(rs_values)
                    cv_rs = (std_rs / avg_rs * 100) if avg_rs > 0 else 0
                    rs_cvs.append(cv_rs)

            # 计算Rct值离散度分析
            rct_cvs = []
            for channel, data in channel_data.items():
                rct_values = data['rct_values']
                if len(rct_values) > 1:
                    avg_rct = statistics.mean(rct_values)
                    std_rct = statistics.stdev(rct_values)
                    cv_rct = (std_rct / avg_rct * 100) if avg_rct > 0 else 0
                    rct_cvs.append(cv_rct)

            # 填充离散度分析表格
            analysis_data = []

            if rs_cvs:
                avg_rs_cv = statistics.mean(rs_cvs)
                if avg_rs_cv < 5:
                    rs_rating = "优秀"
                    rs_consistency = "数据一致性优秀"
                elif avg_rs_cv < 10:
                    rs_rating = "良好"
                    rs_consistency = "数据一致性良好"
                else:
                    rs_rating = "需关注"
                    rs_consistency = "数据离散度较大，需要关注"

                analysis_data.append(["Rs值分析", f"{avg_rs_cv:.2f}", rs_rating, rs_consistency])

            if rct_cvs:
                avg_rct_cv = statistics.mean(rct_cvs)
                if avg_rct_cv < 5:
                    rct_rating = "优秀"
                    rct_consistency = "数据一致性优秀"
                elif avg_rct_cv < 10:
                    rct_rating = "良好"
                    rct_consistency = "数据一致性良好"
                else:
                    rct_rating = "需关注"
                    rct_consistency = "数据离散度较大，需要关注"

                analysis_data.append(["Rct值分析", f"{avg_rct_cv:.2f}", rct_rating, rct_consistency])

            # 总体评价
            if rs_cvs and rct_cvs:
                avg_rs_cv = statistics.mean(rs_cvs)
                avg_rct_cv = statistics.mean(rct_cvs)
                overall_cv = (avg_rs_cv + avg_rct_cv) / 2
                if overall_cv < 5:
                    overall_rating = "优秀"
                    overall_consistency = "连续测试数据稳定性优秀，设备状态良好"
                elif overall_cv < 10:
                    overall_rating = "良好"
                    overall_consistency = "连续测试数据稳定性良好，可继续使用"
                else:
                    overall_rating = "需关注"
                    overall_consistency = "连续测试数据存在较大波动，建议检查设备状态"

                analysis_data.append(["总体评价", f"{overall_cv:.2f}", overall_rating, overall_consistency])

            # 填充表格
            self.dispersion_table.setRowCount(len(analysis_data))
            for i, row_data in enumerate(analysis_data):
                for j, cell_data in enumerate(row_data):
                    item = QTableWidgetItem(str(cell_data))

                    # 根据评价等级设置颜色
                    if j == 2:  # 评价等级列
                        if cell_data == "优秀":
                            item.setBackground(QBrush(QColor(200, 255, 200)))  # 浅绿色
                        elif cell_data == "良好":
                            item.setBackground(QBrush(QColor(255, 255, 200)))  # 浅黄色
                        elif cell_data == "需关注":
                            item.setBackground(QBrush(QColor(255, 200, 200)))  # 浅红色

                    self.dispersion_table.setItem(i, j, item)

        except Exception as e:
            logger.error(f"生成离散度分析失败: {e}")

    def load_eis_analysis_data(self):
        """加载EIS分析数据"""
        try:
            # 检查是否有分析结果
            if not hasattr(self, 'analysis_result') or not self.analysis_result:
                logger.debug("没有EIS分析结果数据")
                return

            # 获取频点阻抗分析数据
            frequency_impedance_analysis = self.analysis_result.get('frequency_impedance_analysis', {})
            if not frequency_impedance_analysis:
                logger.debug("没有频点阻抗分析数据")
                return

            # 加载频点阻抗统计表格
            self.load_impedance_stats_table(frequency_impedance_analysis)

            # 加载一致性评价表格
            self.load_consistency_table()

            # 加载异常频点识别表格
            self.load_anomaly_table()

        except Exception as e:
            logger.error(f"加载EIS分析数据失败: {e}")

    def load_impedance_stats_table(self, frequency_impedance_analysis):
        """加载频点阻抗统计表格"""
        try:
            frequency_analysis = frequency_impedance_analysis.get('frequency_analysis', {})
            analyzed_frequencies = frequency_impedance_analysis.get('analyzed_frequencies', [])

            if not frequency_analysis or not analyzed_frequencies:
                return

            # 按频率排序
            sorted_frequencies = sorted(analyzed_frequencies)

            # 设置表格行数
            self.impedance_stats_table.setRowCount(len(sorted_frequencies))

            for i, frequency in enumerate(sorted_frequencies):
                if frequency not in frequency_analysis:
                    continue

                freq_data = frequency_analysis[frequency]
                magnitude_stats = freq_data.get('overall_magnitude_stats', {})
                phase_stats = freq_data.get('overall_phase_stats', {})

                # 频率
                self.impedance_stats_table.setItem(i, 0, QTableWidgetItem(f"{frequency:.3f}"))

                # 阻抗幅值|Z|
                magnitude_mean = magnitude_stats.get('mean', 0)
                magnitude_std = magnitude_stats.get('std_dev', 0)
                magnitude_text = f"{magnitude_mean:.3f}±{magnitude_std:.3f}"
                self.impedance_stats_table.setItem(i, 1, QTableWidgetItem(magnitude_text))

                # 相位角θ
                phase_mean = phase_stats.get('mean', 0)
                phase_std = phase_stats.get('std_dev', 0)
                phase_text = f"{phase_mean:.2f}±{phase_std:.2f}"
                self.impedance_stats_table.setItem(i, 2, QTableWidgetItem(phase_text))

                # 测试次数
                test_count = magnitude_stats.get('count', 0)
                self.impedance_stats_table.setItem(i, 3, QTableWidgetItem(str(test_count)))

                # |Z|变异系数
                magnitude_cv = magnitude_stats.get('cv', 0)
                self.impedance_stats_table.setItem(i, 4, QTableWidgetItem(f"{magnitude_cv:.2f}"))

                # θ变异系数
                phase_cv = phase_stats.get('cv', 0)
                self.impedance_stats_table.setItem(i, 5, QTableWidgetItem(f"{phase_cv:.2f}"))

                # |Z|范围
                magnitude_min = magnitude_stats.get('min', 0)
                magnitude_max = magnitude_stats.get('max', 0)
                magnitude_range = f"{magnitude_min:.3f}~{magnitude_max:.3f}"
                self.impedance_stats_table.setItem(i, 6, QTableWidgetItem(magnitude_range))

                # θ范围
                phase_min = phase_stats.get('min', 0)
                phase_max = phase_stats.get('max', 0)
                phase_range = f"{phase_min:.2f}~{phase_max:.2f}"
                self.impedance_stats_table.setItem(i, 7, QTableWidgetItem(phase_range))

        except Exception as e:
            logger.error(f"加载频点阻抗统计表格失败: {e}")

    def load_consistency_table(self):
        """加载一致性评价表格"""
        try:
            if not hasattr(self, 'analysis_result') or not self.analysis_result:
                return

            consistency_evaluation = self.analysis_result.get('consistency_evaluation', {})
            if not consistency_evaluation:
                return

            consistency_data = []

            # 频点间一致性
            freq_consistency = consistency_evaluation.get('frequency_consistency', {})
            if freq_consistency:
                rating = freq_consistency.get('consistency_rating', 'unknown')
                avg_magnitude_cv = freq_consistency.get('avg_magnitude_cv', 0)
                avg_phase_cv = freq_consistency.get('avg_phase_cv', 0)

                consistency_data.append([
                    "频点间一致性",
                    rating,
                    f"|Z|平均CV: {avg_magnitude_cv:.2f}%, θ平均CV: {avg_phase_cv:.2f}%",
                    "检查测试环境稳定性" if rating == "需改进" else "保持当前测试条件"
                ])

            # 通道间一致性
            channel_consistency = consistency_evaluation.get('channel_consistency', {})
            if channel_consistency:
                rating = channel_consistency.get('consistency_rating', 'unknown')
                avg_channel_cv = channel_consistency.get('avg_channel_cv', 0)

                consistency_data.append([
                    "通道间一致性",
                    rating,
                    f"通道平均CV: {avg_channel_cv:.2f}%",
                    "检查通道校准" if rating == "需改进" else "通道状态良好"
                ])

            # 整体评价
            overall_rating = consistency_evaluation.get('overall_rating', 'unknown')
            if overall_rating:
                consistency_data.append([
                    "整体评价",
                    overall_rating,
                    "综合所有指标评价",
                    "根据具体问题采取相应措施"
                ])

            # 填充表格
            self.consistency_table.setRowCount(len(consistency_data))
            for i, row_data in enumerate(consistency_data):
                for j, cell_data in enumerate(row_data):
                    item = QTableWidgetItem(str(cell_data))

                    # 根据评价结果设置颜色
                    if j == 1:  # 评价结果列
                        if "优秀" in cell_data or "良好" in cell_data:
                            item.setBackground(QBrush(QColor(200, 255, 200)))  # 浅绿色
                        elif "一般" in cell_data:
                            item.setBackground(QBrush(QColor(255, 255, 200)))  # 浅黄色
                        elif "需改进" in cell_data or "较差" in cell_data:
                            item.setBackground(QBrush(QColor(255, 200, 200)))  # 浅红色

                    self.consistency_table.setItem(i, j, item)

        except Exception as e:
            logger.error(f"加载一致性评价表格失败: {e}")

    def load_anomaly_table(self):
        """加载异常频点识别表格"""
        try:
            if not hasattr(self, 'analysis_result') or not self.analysis_result:
                return

            anomalous_frequencies = self.analysis_result.get('anomalous_frequencies', [])

            # 检查数据类型，确保是列表
            if not isinstance(anomalous_frequencies, list):
                anomalous_frequencies = []

            if not anomalous_frequencies:
                # 如果没有异常频点，显示一行提示信息
                self.anomaly_table.setRowCount(1)
                self.anomaly_table.setItem(0, 0, QTableWidgetItem("--"))
                self.anomaly_table.setItem(0, 1, QTableWidgetItem("无异常"))
                self.anomaly_table.setItem(0, 2, QTableWidgetItem("正常"))
                self.anomaly_table.setItem(0, 3, QTableWidgetItem("--"))
                self.anomaly_table.setItem(0, 4, QTableWidgetItem("继续监测"))
                return

            # 填充异常频点数据
            self.anomaly_table.setRowCount(len(anomalous_frequencies))
            for i, anomaly in enumerate(anomalous_frequencies):
                # 确保anomaly是字典类型
                if not isinstance(anomaly, dict):
                    continue

                frequency = anomaly.get('frequency', 0)
                anomaly_type = anomaly.get('anomaly_type', 'unknown')
                severity = anomaly.get('severity', 'unknown')
                affected_channels = anomaly.get('affected_channels', [])
                recommendation = anomaly.get('recommendation', '需要进一步检查')

                self.anomaly_table.setItem(i, 0, QTableWidgetItem(f"{frequency:.3f}"))
                self.anomaly_table.setItem(i, 1, QTableWidgetItem(anomaly_type))

                # 异常程度设置颜色
                severity_item = QTableWidgetItem(severity)
                if severity == "严重":
                    severity_item.setBackground(QBrush(QColor(255, 200, 200)))  # 浅红色
                elif severity == "中等":
                    severity_item.setBackground(QBrush(QColor(255, 255, 200)))  # 浅黄色
                elif severity == "轻微":
                    severity_item.setBackground(QBrush(QColor(255, 255, 255)))  # 白色
                self.anomaly_table.setItem(i, 2, severity_item)

                # 影响通道
                channels_text = ", ".join([f"CH{ch}" for ch in affected_channels]) if affected_channels else "--"
                self.anomaly_table.setItem(i, 3, QTableWidgetItem(channels_text))

                self.anomaly_table.setItem(i, 4, QTableWidgetItem(recommendation))

        except Exception as e:
            logger.error(f"加载异常频点识别表格失败: {e}")

    def load_detailed_data(self):
        """加载详细数据"""
        try:
            test_results = self.report_data.get('test_results', [])
            if not test_results:
                return

            self.detailed_table.setRowCount(len(test_results))

            for i, result in enumerate(test_results):
                cycle = result.get('cycle', i // 8 + 1)  # 假设8通道
                channel = result.get('channel', 0)
                voltage = result.get('voltage', 0)
                rs_value = result.get('rs_value', 0)
                rct_value = result.get('rct_value', 0)
                rs_grade = result.get('rs_grade', '--')
                rct_grade = result.get('rct_grade', '--')
                is_pass = result.get('is_pass', False)

                self.detailed_table.setItem(i, 0, QTableWidgetItem(str(cycle)))
                self.detailed_table.setItem(i, 1, QTableWidgetItem(str(channel)))
                self.detailed_table.setItem(i, 2, QTableWidgetItem(f"{voltage:.3f}"))
                self.detailed_table.setItem(i, 3, QTableWidgetItem(f"{rs_value:.3f}"))
                self.detailed_table.setItem(i, 4, QTableWidgetItem(f"{rct_value:.3f}"))
                self.detailed_table.setItem(i, 5, QTableWidgetItem(str(rs_grade)))
                self.detailed_table.setItem(i, 6, QTableWidgetItem(str(rct_grade)))

                # 测试结果
                result_text = "合格" if is_pass else "不合格"
                result_item = QTableWidgetItem(result_text)
                if is_pass:
                    result_item.setBackground(QBrush(QColor(200, 255, 200)))  # 浅绿色
                else:
                    result_item.setBackground(QBrush(QColor(255, 200, 200)))  # 浅红色
                self.detailed_table.setItem(i, 7, result_item)

        except Exception as e:
            logger.error(f"加载详细数据失败: {e}")
    
    def generate_analysis_report(self):
        """生成分析报告"""
        try:
            logger.info("开始生成连续测试分析报告")

            # 检查数据
            if not self.report_data or not self.report_data.get('test_results'):
                QMessageBox.warning(self, "警告", "没有可分析的测试数据！")
                return

            # 导入分析器
            from backend.continuous_test_analyzer import ContinuousTestAnalyzer

            # 创建分析器并分析数据
            analyzer = ContinuousTestAnalyzer()
            test_results = self.report_data.get('test_results', [])

            # 检查数据量，如果过大则警告用户
            if len(test_results) > 1000:
                reply = QMessageBox.question(
                    self,
                    "数据量较大",
                    f"测试数据共{len(test_results)}条记录，分析可能需要较长时间。\n是否继续？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply != QMessageBox.Yes:
                    return

            # 使用QProgressDialog提供更好的用户体验
            from PyQt5.QtWidgets import QProgressDialog
            from PyQt5.QtCore import QTimer

            progress_dialog = QProgressDialog("正在分析连续测试数据...", "取消", 0, 100, self)
            progress_dialog.setWindowTitle("分析中")
            progress_dialog.setModal(True)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setValue(0)
            progress_dialog.show()

            # 使用QTimer分步执行分析，避免UI卡死
            self._analysis_step = 0
            self._analysis_steps = [
                ("正在按通道分组数据...", 20),
                ("正在分析各通道数据...", 40),
                ("正在生成整体分析...", 70),
                ("正在评价数据一致性...", 90),
                ("正在格式化结果...", 100)
            ]

            def execute_analysis_step():
                try:
                    if progress_dialog.wasCanceled():
                        logger.info("用户取消了分析操作")
                        return

                    if self._analysis_step == 0:
                        # 开始分析
                        progress_dialog.setLabelText("正在初始化分析器...")
                        progress_dialog.setValue(10)
                        self._analyzer = analyzer
                        self._test_results = test_results

                    elif self._analysis_step < len(self._analysis_steps):
                        step_name, progress_value = self._analysis_steps[self._analysis_step - 1]
                        progress_dialog.setLabelText(step_name)
                        progress_dialog.setValue(progress_value)

                        # 执行实际分析（在这里可以分步进行）
                        if self._analysis_step == 1:
                            # 执行完整分析
                            analysis_result = self._analyzer.analyze_continuous_test_data(self._test_results)
                            self._analysis_result = analysis_result

                    self._analysis_step += 1

                    if self._analysis_step <= len(self._analysis_steps):
                        # 继续下一步
                        QTimer.singleShot(100, execute_analysis_step)
                    else:
                        # 分析完成
                        progress_dialog.close()

                        if hasattr(self, '_analysis_result') and self._analysis_result:
                            self.analysis_result = self._analysis_result

                            # 重新加载EIS分析数据到表格
                            self.load_eis_analysis_data()

                            self._show_analysis_result_dialog(self._analysis_result)
                            logger.info("连续测试分析报告生成完成")
                        else:
                            QMessageBox.warning(self, "警告", "数据分析失败，请检查测试数据！")

                        # 清理临时变量
                        delattr(self, '_analysis_step')
                        delattr(self, '_analysis_steps')
                        delattr(self, '_analyzer')
                        delattr(self, '_test_results')
                        if hasattr(self, '_analysis_result'):
                            delattr(self, '_analysis_result')

                except Exception as e:
                    progress_dialog.close()
                    logger.error(f"分析步骤执行失败: {e}")
                    QMessageBox.critical(self, "分析失败", f"分析过程中发生错误:\n{str(e)}")

            # 开始执行分析
            QTimer.singleShot(100, execute_analysis_step)

        except Exception as e:
            logger.error(f"生成分析报告失败: {e}")
            QMessageBox.critical(self, "错误", f"生成分析报告失败:\n{str(e)}")

    def export_excel_report(self):
        """导出Excel分析报告"""
        try:
            # 检查是否已生成分析结果
            if not hasattr(self, 'analysis_result') or not self.analysis_result:
                reply = QMessageBox.question(
                    self, "确认",
                    "尚未生成分析报告，是否先生成分析报告？",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    self.generate_analysis_report()
                    if not hasattr(self, 'analysis_result') or not self.analysis_result:
                        return
                else:
                    return

            # 打开导出对话框
            from ui.dialogs.continuous_test_report_exporter import ContinuousTestReportExporter

            # 准备批次信息
            batch_info = {
                'batch_number': self.report_data.get('batch_number', ''),
                'operator': self.report_data.get('operator', ''),
                'cell_type': self.report_data.get('cell_type', ''),
                'cell_spec': self.report_data.get('cell_spec', ''),
                'start_time': self.report_data.get('start_time', ''),
                'end_time': self.report_data.get('end_time', '')
            }

            # 创建导出对话框
            exporter_dialog = ContinuousTestReportExporter(
                parent=self,
                analysis_data=self.analysis_result,
                test_results=self.report_data.get('test_results', []),
                batch_info=batch_info
            )

            exporter_dialog.exec_()

        except Exception as e:
            logger.error(f"导出Excel报告失败: {e}")
            QMessageBox.critical(self, "错误", f"导出Excel报告失败:\n{str(e)}")

    def _show_analysis_result_dialog(self, analysis_result: dict):
        """显示分析结果对话框"""
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout

            dialog = QDialog(self)
            dialog.setWindowTitle("连续测试数据分析结果")
            dialog.setGeometry(300, 300, 800, 600)

            layout = QVBoxLayout()

            # 分析结果文本
            result_text = QTextEdit()
            result_text.setReadOnly(True)

            # 格式化分析结果
            result_content = self._format_analysis_result(analysis_result)
            result_text.setPlainText(result_content)

            layout.addWidget(result_text)

            # 按钮
            button_layout = QHBoxLayout()

            export_btn = QPushButton("导出Excel报告")
            def on_export_clicked():
                dialog.accept()
                self.export_excel_report()
            export_btn.clicked.connect(on_export_clicked)
            button_layout.addWidget(export_btn)

            button_layout.addStretch()

            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(close_btn)

            layout.addLayout(button_layout)
            dialog.setLayout(layout)

            dialog.exec_()

        except Exception as e:
            logger.error(f"显示分析结果对话框失败: {e}")

    def _format_analysis_result(self, analysis_result: dict) -> str:
        """格式化分析结果为文本（EIS专业版，避免大数据量卡死）"""
        try:
            lines = []
            lines.append("=" * 70)

            # 检查是否为EIS专业分析
            analysis_type = analysis_result.get('analysis_type', 'Standard')
            if analysis_type == 'EIS_Professional':
                lines.append("EIS连续测试数据专业分析报告")
            else:
                lines.append("连续测试数据分析报告")

            lines.append("=" * 70)
            lines.append("")

            # 基本信息
            lines.append(f"分析时间: {analysis_result.get('analysis_time', '')}")
            lines.append(f"测试记录总数: {analysis_result.get('total_records', 0)}")
            lines.append(f"测试通道数: {analysis_result.get('channel_count', 0)}")
            lines.append(f"分析类型: {'EIS专业分析' if analysis_type == 'EIS_Professional' else '标准分析'}")
            lines.append("")

            # EIS专业分析频点阻抗分析
            frequency_impedance_analysis = analysis_result.get('frequency_impedance_analysis', {})
            if frequency_impedance_analysis and analysis_type == 'EIS_Professional':
                lines.append("EIS频点阻抗分析:")
                lines.append("-" * 50)

                frequency_analysis = frequency_impedance_analysis.get('frequency_analysis', {})
                analyzed_frequencies = frequency_impedance_analysis.get('analyzed_frequencies', [])

                lines.append(f"分析频点数量: {len(analyzed_frequencies)}")

                # 显示关键频点的统计信息（限制显示数量）
                key_frequencies = []
                for freq in analyzed_frequencies:
                    if freq in [0.1, 1.0, 10.0, 100.0, 1000.0]:  # 关键频点
                        key_frequencies.append(freq)

                if not key_frequencies:
                    # 如果没有标准关键频点，选择前5个频点
                    key_frequencies = sorted(analyzed_frequencies)[:5]

                for freq in key_frequencies:
                    if freq in frequency_analysis:
                        freq_data = frequency_analysis[freq]
                        magnitude_stats = freq_data.get('overall_magnitude_stats', {})
                        phase_stats = freq_data.get('overall_phase_stats', {})

                        lines.append(f"  {freq}Hz:")
                        lines.append(f"    |Z|: {magnitude_stats.get('mean', 0):.3f}±{magnitude_stats.get('std_dev', 0):.3f}mΩ (CV={magnitude_stats.get('cv', 0):.2f}%)")
                        lines.append(f"    θ: {phase_stats.get('mean', 0):.2f}±{phase_stats.get('std_dev', 0):.2f}° (CV={phase_stats.get('cv', 0):.2f}%)")

                # 异常频点识别
                anomalous_frequencies = analysis_result.get('anomalous_frequencies', {})
                if anomalous_frequencies:
                    anomaly_count = anomalous_frequencies.get('anomalous_count', 0)
                    anomaly_rate = anomalous_frequencies.get('anomaly_rate', 0)
                    lines.append(f"异常频点: {anomaly_count}个 (异常率: {anomaly_rate:.1f}%)")

                lines.append("")

            # 整体统计（保留原有功能）
            overall = analysis_result.get('overall_analysis', {})
            if overall:
                lines.append("整体统计分析:")
                lines.append("-" * 40)

                rs_stats = overall.get('overall_rs_statistics', {})
                if rs_stats:
                    lines.append(f"Rs统计 (mΩ):")
                    lines.append(f"  平均值: {rs_stats.get('mean', 0):.3f}")
                    lines.append(f"  标准差: {rs_stats.get('std_dev', 0):.3f}")
                    lines.append(f"  变异系数: {rs_stats.get('cv', 0):.2f}%")
                    lines.append(f"  范围: {rs_stats.get('min', 0):.3f} - {rs_stats.get('max', 0):.3f}")

                rct_stats = overall.get('overall_rct_statistics', {})
                if rct_stats:
                    lines.append(f"Rct统计 (mΩ):")
                    lines.append(f"  平均值: {rct_stats.get('mean', 0):.3f}")
                    lines.append(f"  标准差: {rct_stats.get('std_dev', 0):.3f}")
                    lines.append(f"  变异系数: {rct_stats.get('cv', 0):.2f}%")
                    lines.append(f"  范围: {rct_stats.get('min', 0):.3f} - {rct_stats.get('max', 0):.3f}")
                lines.append("")

            # 通道分析（限制显示数量，避免过多数据）
            channel_analysis = analysis_result.get('channel_analysis', {})
            if channel_analysis:
                lines.append("各通道分析:")
                lines.append("-" * 40)

                # 限制显示的通道数量，避免文本过长
                channel_nums = sorted(channel_analysis.keys())
                max_channels_to_show = 20  # 最多显示20个通道

                if len(channel_nums) > max_channels_to_show:
                    lines.append(f"注意：共有{len(channel_nums)}个通道，仅显示前{max_channels_to_show}个通道的详细信息")
                    lines.append("")
                    channel_nums = channel_nums[:max_channels_to_show]

                for channel_num in channel_nums:
                    data = channel_analysis[channel_num]
                    lines.append(f"通道 {channel_num}:")
                    lines.append(f"  测试次数: {data.get('test_count', 0)}")
                    lines.append(f"  合格率: {data.get('pass_rate', 0):.2f}%")

                    rs_stats = data.get('rs_statistics', {})
                    if rs_stats:
                        lines.append(f"  Rs: 均值={rs_stats.get('mean', 0):.3f}mΩ, CV={rs_stats.get('cv', 0):.2f}%")

                    rct_stats = data.get('rct_statistics', {})
                    if rct_stats:
                        lines.append(f"  Rct: 均值={rct_stats.get('mean', 0):.3f}mΩ, CV={rct_stats.get('cv', 0):.2f}%")

                    stability = data.get('stability_analysis', {})
                    if stability:
                        lines.append(f"  稳定性: Rs={stability.get('rs_stability', 'unknown')}, Rct={stability.get('rct_stability', 'unknown')}")

                    lines.append("")

                # 如果有更多通道，显示汇总信息
                if len(sorted(channel_analysis.keys())) > max_channels_to_show:
                    remaining_channels = len(sorted(channel_analysis.keys())) - max_channels_to_show
                    lines.append(f"其余{remaining_channels}个通道的详细信息请查看Excel导出报告")
                    lines.append("")

            # 一致性评价（支持EIS专业评价）
            consistency = analysis_result.get('consistency_evaluation', {})
            if consistency:
                # 检查是否为EIS专业评价
                consistency_type = consistency.get('analysis_type', 'Standard')

                if consistency_type == 'EIS_Professional':
                    lines.append("EIS专业一致性评价:")
                    lines.append("-" * 50)

                    # 频点一致性
                    freq_consistency = consistency.get('frequency_consistency', {})
                    if freq_consistency:
                        lines.append("频点间一致性:")
                        lines.append(f"  评价等级: {freq_consistency.get('consistency_rating', 'unknown')}")
                        lines.append(f"  平均|Z|变异系数: {freq_consistency.get('avg_magnitude_cv', 0):.2f}%")
                        lines.append(f"  平均相位变异系数: {freq_consistency.get('avg_phase_cv', 0):.2f}%")

                    # 通道一致性
                    channel_consistency = consistency.get('channel_consistency', {})
                    if channel_consistency:
                        lines.append("通道间一致性:")
                        lines.append(f"  评价等级: {channel_consistency.get('consistency_rating', 'unknown')}")
                        lines.append(f"  平均Rs变异系数: {channel_consistency.get('avg_rs_cv', 0):.2f}%")
                        lines.append(f"  平均Rct变异系数: {channel_consistency.get('avg_rct_cv', 0):.2f}%")

                    lines.append(f"EIS整体评价: {consistency.get('overall_rating', 'unknown')}")

                    # EIS专业建议
                    eis_recommendations = consistency.get('eis_recommendations', [])
                    if eis_recommendations:
                        lines.append("EIS专业建议:")
                        max_recommendations = 8
                        for i, rec in enumerate(eis_recommendations[:max_recommendations], 1):
                            lines.append(f"{i}. {rec}")
                        if len(eis_recommendations) > max_recommendations:
                            lines.append(f"... 还有{len(eis_recommendations) - max_recommendations}条建议，请查看Excel报告")
                else:
                    # 标准一致性评价
                    lines.append("一致性评价:")
                    lines.append("-" * 40)
                    lines.append(f"整体评价: {consistency.get('overall_rating', 'unknown')}")
                    lines.append(f"稳定性评分: {consistency.get('stability_score', 0):.1f}")

                    recommendations = consistency.get('recommendations', [])
                    if recommendations:
                        lines.append("改进建议:")
                        max_recommendations = 10
                        for i, rec in enumerate(recommendations[:max_recommendations], 1):
                            lines.append(f"{i}. {rec}")
                        if len(recommendations) > max_recommendations:
                            lines.append(f"... 还有{len(recommendations) - max_recommendations}条建议，请查看Excel报告")

                lines.append("")

            lines.append("=" * 60)
            lines.append("提示：完整的分析结果请导出Excel报告查看")

            return '\n'.join(lines)

        except Exception as e:
            logger.error(f"格式化分析结果失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return f"分析结果格式化失败: {str(e)}"

    def export_report(self):
        """导出报告（JSON格式）"""
        try:
            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出连续测试报告",
                f"连续测试报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON文件 (*.json);;所有文件 (*)"
            )

            if file_path:
                # 保存报告数据
                export_data = self.report_data.copy()

                # 如果有分析结果，也包含进去
                if hasattr(self, 'analysis_result') and self.analysis_result:
                    export_data['analysis_result'] = self.analysis_result

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)

                QMessageBox.information(self, "导出成功", f"报告已导出到:\n{file_path}")
                logger.info(f"连续测试报告已导出到: {file_path}")

        except Exception as e:
            logger.error(f"导出报告失败: {e}")
            QMessageBox.critical(self, "导出失败", f"导出报告时发生错误:\n{str(e)}")

    def delete_selected_records(self):
        """删除选中的连续测试记录"""
        try:
            # 获取选中的行
            selected_rows = set()
            for item in self.detailed_table.selectedItems():
                selected_rows.add(item.row())

            if not selected_rows:
                QMessageBox.information(self, "提示", "请先选择要删除的记录")
                return

            # 确认删除
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除选中的 {len(selected_rows)} 条记录吗？\n\n此操作不可撤销！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 获取要删除的记录ID
            record_ids = []
            for row in selected_rows:
                id_item = self.detailed_table.item(row, 0)  # 假设第一列是ID
                if id_item:
                    record_ids.append(int(id_item.text()))

            # 执行删除
            deleted_count = self._delete_records_from_database(record_ids)

            if deleted_count > 0:
                QMessageBox.information(
                    self,
                    "删除成功",
                    f"成功删除 {deleted_count} 条记录"
                )
                # 刷新数据
                self._refresh_data()
            else:
                QMessageBox.warning(self, "删除失败", "未能删除任何记录")

        except Exception as e:
            logger.error(f"删除选中记录失败: {e}")
            QMessageBox.critical(self, "删除失败", f"删除记录时发生错误:\n{str(e)}")

    def clear_all_records(self):
        """清除所有连续测试记录"""
        try:
            # 确认清除
            reply = QMessageBox.question(
                self,
                "确认清除",
                "确定要清除所有连续测试记录吗？\n\n此操作将删除数据库中所有连续测试数据，不可撤销！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 二次确认
            reply2 = QMessageBox.question(
                self,
                "最终确认",
                "这是最后一次确认！\n\n确定要删除所有连续测试数据吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply2 != QMessageBox.Yes:
                return

            # 执行清除
            deleted_count = self._clear_all_continuous_records()

            if deleted_count > 0:
                QMessageBox.information(
                    self,
                    "清除成功",
                    f"成功清除 {deleted_count} 条连续测试记录"
                )
                # 刷新数据
                self._refresh_data()
            else:
                QMessageBox.information(self, "提示", "没有找到连续测试记录")

        except Exception as e:
            logger.error(f"清除所有记录失败: {e}")
            QMessageBox.critical(self, "清除失败", f"清除记录时发生错误:\n{str(e)}")

    def _delete_records_from_database(self, record_ids: list) -> int:
        """从数据库删除指定记录"""
        try:
            if not record_ids:
                return 0

            # 这里需要数据库管理器，从父窗口获取
            if hasattr(self.parent(), 'db_manager'):
                db_manager = self.parent().db_manager
            else:
                logger.error("无法获取数据库管理器")
                return 0

            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # 删除测试结果记录
                placeholders = ','.join(['?' for _ in record_ids])
                query = f"DELETE FROM test_results WHERE id IN ({placeholders})"
                cursor.execute(query, record_ids)

                deleted_count = cursor.rowcount
                conn.commit()

                logger.info(f"从数据库删除了 {deleted_count} 条记录")
                return deleted_count

        except Exception as e:
            logger.error(f"数据库删除操作失败: {e}")
            return 0

    def _clear_all_continuous_records(self) -> int:
        """清除所有连续测试记录"""
        try:
            # 获取数据库管理器
            if hasattr(self.parent(), 'db_manager'):
                db_manager = self.parent().db_manager
            else:
                logger.error("无法获取数据库管理器")
                return 0

            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # 删除所有连续测试模式的记录
                query = "DELETE FROM test_results WHERE test_mode LIKE '%连续%'"
                cursor.execute(query)

                deleted_count = cursor.rowcount
                conn.commit()

                logger.info(f"清除了 {deleted_count} 条连续测试记录")
                return deleted_count

        except Exception as e:
            logger.error(f"清除连续测试记录失败: {e}")
            return 0

    def _refresh_data(self):
        """刷新数据显示"""
        try:
            # 重新查询数据
            if hasattr(self.parent(), '_query_continuous_test_data'):
                new_data = self.parent()._query_continuous_test_data()
                self.report_data = new_data
                self.load_report_data()
            else:
                # 关闭对话框，让用户重新打开
                QMessageBox.information(
                    self,
                    "提示",
                    "数据已删除，请重新打开连续测试报告查看最新数据"
                )
                self.accept()

        except Exception as e:
            logger.error(f"刷新数据失败: {e}")
            QMessageBox.warning(self, "刷新失败", "数据刷新失败，请重新打开报告")
