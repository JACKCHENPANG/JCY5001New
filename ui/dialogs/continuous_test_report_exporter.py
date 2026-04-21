#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连续测试报告导出管理器

负责管理连续测试报告的导出功能，包括：
1. 文件路径选择
2. 导出格式选择
3. 导出进度管理
4. 错误处理

作者：Jack
日期：2025-01-31
"""

import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QProgressBar, QTextEdit, QFileDialog, QMessageBox,
    QGroupBox, QCheckBox, QSpinBox
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class ReportExportWorker(QThread):
    """报告导出工作线程"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    export_completed = pyqtSignal(bool, str)
    
    def __init__(self, analysis_data: Dict[str, Any], test_results: List[Dict[str, Any]], 
                 batch_info: Dict[str, Any], file_path: str, export_format: str):
        super().__init__()
        self.analysis_data = analysis_data
        self.test_results = test_results
        self.batch_info = batch_info
        self.file_path = file_path
        self.export_format = export_format
    
    def run(self):
        """执行导出"""
        try:
            self.status_updated.emit("正在准备导出数据...")
            self.progress_updated.emit(10)
            
            if self.export_format == "Excel":
                self._export_to_excel()
            elif self.export_format == "JSON":
                self._export_to_json()
            else:
                raise ValueError(f"不支持的导出格式: {self.export_format}")
            
            self.progress_updated.emit(100)
            self.status_updated.emit("导出完成")
            self.export_completed.emit(True, f"报告已成功导出到: {self.file_path}")
            
        except Exception as e:
            logger.error(f"导出报告失败: {e}")
            self.export_completed.emit(False, f"导出失败: {str(e)}")
    
    def _export_to_excel(self):
        """导出到Excel"""
        try:
            from backend.continuous_test_excel_exporter import ContinuousTestExcelExporter
            
            self.status_updated.emit("正在生成Excel报告...")
            self.progress_updated.emit(30)
            
            exporter = ContinuousTestExcelExporter()
            success = exporter.export_analysis_report(
                self.analysis_data,
                self.test_results,
                self.batch_info,
                self.file_path
            )
            
            if not success:
                raise Exception("Excel导出失败")
            
            self.progress_updated.emit(90)
            
        except ImportError:
            raise Exception("需要安装xlsxwriter库: pip install xlsxwriter")
        except Exception as e:
            raise Exception(f"Excel导出失败: {str(e)}")
    
    def _export_to_json(self):
        """导出到JSON"""
        try:
            import json
            
            self.status_updated.emit("正在生成JSON报告...")
            self.progress_updated.emit(30)
            
            # 组合所有数据
            export_data = {
                'export_info': {
                    'export_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'export_format': 'JSON',
                    'version': '1.0'
                },
                'batch_info': self.batch_info,
                'analysis_data': self.analysis_data,
                'test_results': self.test_results
            }
            
            self.progress_updated.emit(60)
            
            # 保存到文件
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            
            self.progress_updated.emit(90)
            
        except Exception as e:
            raise Exception(f"JSON导出失败: {str(e)}")


class ContinuousTestReportExporter(QDialog):
    """连续测试报告导出对话框"""
    
    def __init__(self, parent=None, analysis_data: Dict[str, Any] = None, 
                 test_results: List[Dict[str, Any]] = None, batch_info: Dict[str, Any] = None):
        super().__init__(parent)
        
        self.analysis_data = analysis_data or {}
        self.test_results = test_results or []
        self.batch_info = batch_info or {}
        self.export_worker = None
        
        self.init_ui()
        self.setup_connections()
        
        logger.debug("连续测试报告导出对话框初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("导出连续测试分析报告")
        self.setGeometry(200, 200, 600, 500)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("连续测试分析报告导出")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 导出选项组
        options_group = QGroupBox("导出选项")
        options_layout = QVBoxLayout()
        
        # 导出格式
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("导出格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("Excel报告 (*.xlsx)", "Excel")
        self.format_combo.addItem("JSON数据 (*.json)", "JSON")
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        options_layout.addLayout(format_layout)
        
        # 包含选项
        self.include_detailed_data = QCheckBox("包含详细测试数据")
        self.include_detailed_data.setChecked(True)
        options_layout.addWidget(self.include_detailed_data)
        
        self.include_charts = QCheckBox("包含统计图表 (仅Excel)")
        self.include_charts.setChecked(True)
        options_layout.addWidget(self.include_charts)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 数据概览组
        overview_group = QGroupBox("数据概览")
        overview_layout = QVBoxLayout()
        
        self.overview_text = QTextEdit()
        self.overview_text.setMaximumHeight(150)
        self.overview_text.setReadOnly(True)
        self._update_overview_text()
        overview_layout.addWidget(self.overview_text)
        
        overview_group.setLayout(overview_layout)
        layout.addWidget(overview_group)
        
        # 进度组
        progress_group = QGroupBox("导出进度")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("准备导出...")
        progress_layout.addWidget(self.status_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # 按钮组
        button_layout = QHBoxLayout()
        
        self.export_button = QPushButton("📄 导出报告")
        self.export_button.clicked.connect(self.start_export)
        button_layout.addWidget(self.export_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("❌ 关闭")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def setup_connections(self):
        """设置信号连接"""
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
    
    def _update_overview_text(self):
        """更新数据概览文本"""
        try:
            overview_lines = []
            
            # 基本信息
            total_records = self.analysis_data.get('total_records', 0)
            channel_count = self.analysis_data.get('channel_count', 0)
            overview_lines.append(f"• 测试记录总数: {total_records}")
            overview_lines.append(f"• 测试通道数: {channel_count}")
            
            # 整体统计
            overall = self.analysis_data.get('overall_analysis', {})
            cycles = overall.get('total_test_cycles', 0)
            overview_lines.append(f"• 测试轮次: {cycles}")
            
            # 一致性评价
            consistency = self.analysis_data.get('consistency_evaluation', {})
            rating = consistency.get('overall_rating', 'unknown')
            overview_lines.append(f"• 整体评价: {rating}")
            
            # 批次信息
            if self.batch_info:
                batch_number = self.batch_info.get('batch_number', '')
                if batch_number:
                    overview_lines.append(f"• 批次号: {batch_number}")
            
            self.overview_text.setText('\n'.join(overview_lines))
            
        except Exception as e:
            logger.error(f"更新概览文本失败: {e}")
            self.overview_text.setText("数据概览加载失败")
    
    def _on_format_changed(self):
        """格式选择改变"""
        current_format = self.format_combo.currentData()
        
        # Excel格式才支持图表
        self.include_charts.setEnabled(current_format == "Excel")
        if current_format != "Excel":
            self.include_charts.setChecked(False)
    
    def start_export(self):
        """开始导出"""
        try:
            # 检查数据
            if not self.analysis_data or not self.test_results:
                QMessageBox.warning(self, "警告", "没有可导出的数据！")
                return
            
            # 选择保存路径
            export_format = self.format_combo.currentData()
            file_path = self._select_save_path(export_format)
            
            if not file_path:
                return
            
            # 准备导出数据
            export_data = self.analysis_data.copy()
            export_results = self.test_results.copy()
            
            # 根据选项过滤数据
            if not self.include_detailed_data.isChecked():
                export_results = []  # 不包含详细数据
            
            # 开始导出
            self._start_export_worker(export_data, export_results, file_path, export_format)
            
        except Exception as e:
            logger.error(f"开始导出失败: {e}")
            QMessageBox.critical(self, "错误", f"开始导出失败:\n{str(e)}")
    
    def _select_save_path(self, export_format: str) -> str:
        """选择保存路径"""
        try:
            # 生成默认文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if export_format == "Excel":
                default_name = f"连续测试分析报告_{timestamp}.xlsx"
                file_filter = "Excel文件 (*.xlsx);;所有文件 (*)"
            else:  # JSON
                default_name = f"连续测试分析报告_{timestamp}.json"
                file_filter = "JSON文件 (*.json);;所有文件 (*)"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存分析报告",
                default_name,
                file_filter
            )
            
            return file_path
            
        except Exception as e:
            logger.error(f"选择保存路径失败: {e}")
            return ""
    
    def _start_export_worker(self, analysis_data: Dict[str, Any], test_results: List[Dict[str, Any]], 
                           file_path: str, export_format: str):
        """启动导出工作线程"""
        try:
            # 停止之前的导出
            if self.export_worker and self.export_worker.isRunning():
                self.export_worker.terminate()
                self.export_worker.wait()
            
            # 创建导出工作线程
            self.export_worker = ReportExportWorker(
                analysis_data=analysis_data,
                test_results=test_results,
                batch_info=self.batch_info,
                file_path=file_path,
                export_format=export_format
            )
            
            # 连接信号
            self.export_worker.progress_updated.connect(self.progress_bar.setValue)
            self.export_worker.status_updated.connect(self.status_label.setText)
            self.export_worker.export_completed.connect(self._on_export_completed)
            
            # 更新UI状态
            self.export_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("正在导出...")
            
            # 启动导出
            self.export_worker.start()
            
            logger.info(f"开始导出连续测试分析报告: {file_path}")
            
        except Exception as e:
            logger.error(f"启动导出工作线程失败: {e}")
            self._reset_ui_state()
            QMessageBox.critical(self, "错误", f"启动导出失败:\n{str(e)}")
    
    def _on_export_completed(self, success: bool, message: str):
        """导出完成处理"""
        try:
            self._reset_ui_state()
            
            if success:
                QMessageBox.information(self, "导出成功", message)
                logger.info("连续测试分析报告导出成功")
            else:
                QMessageBox.critical(self, "导出失败", message)
                logger.error("连续测试分析报告导出失败")
            
        except Exception as e:
            logger.error(f"处理导出完成事件失败: {e}")
    
    def _reset_ui_state(self):
        """重置UI状态"""
        try:
            self.export_button.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.status_label.setText("准备导出...")
            
        except Exception as e:
            logger.error(f"重置UI状态失败: {e}")
    
    def closeEvent(self, event):
        """关闭事件"""
        try:
            # 停止导出工作线程
            if self.export_worker and self.export_worker.isRunning():
                self.export_worker.terminate()
                self.export_worker.wait()
            
            event.accept()
            
        except Exception as e:
            logger.error(f"关闭对话框失败: {e}")
            event.accept()
