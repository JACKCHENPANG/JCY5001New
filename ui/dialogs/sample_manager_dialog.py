#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
样本管理对话框

提供样本列表显示、打开、删除、导出等功能
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView, QAbstractItemView,
    QSplitter, QTextEdit, QGroupBox, QFormLayout, QLineEdit,
    QComboBox, QFileDialog, QProgressBar, QApplication, QWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)

class SampleLoadThread(QThread):
    """样本加载线程"""
    
    progress_updated = pyqtSignal(int)
    sample_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, sample_file_path: str):
        super().__init__()
        self.sample_file_path = sample_file_path
        
    def run(self):
        """执行样本加载"""
        try:
            self.progress_updated.emit(20)
            
            # 读取样本文件
            with open(self.sample_file_path, 'r', encoding='utf-8') as f:
                sample_data = json.load(f)
            
            self.progress_updated.emit(50)
            
            # 验证样本数据完整性
            required_fields = ['info', 'median_data', 'created_at']
            for field in required_fields:
                if field not in sample_data:
                    raise ValueError(f"样本文件缺少必需字段: {field}")
            
            self.progress_updated.emit(80)
            
            # 添加文件路径信息
            sample_data['file_path'] = self.sample_file_path
            
            self.progress_updated.emit(100)
            self.sample_loaded.emit(sample_data)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

class SampleManagerDialog(QDialog):
    """样本管理对话框"""
    
    sample_selected = pyqtSignal(dict)  # 样本选择信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("样本管理")
        self.setModal(True)
        self.resize(1000, 700)
        
        # 样本数据
        self.samples_data = []
        self.current_sample = None
        self.load_thread = None
        
        self._init_ui()
        self._load_samples()
        
    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("📋 样本管理")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 创建主分割器
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)
        
        # 左侧：样本列表
        left_widget = self._create_sample_list_area()
        main_splitter.addWidget(left_widget)
        
        # 右侧：样本详情
        right_widget = self._create_sample_detail_area()
        main_splitter.addWidget(right_widget)
        
        # 设置分割器比例（左侧60%，右侧40%）
        main_splitter.setSizes([600, 400])
        
        # 底部：操作按钮
        button_widget = QWidget()
        button_area = self._create_button_area()
        button_widget.setLayout(button_area)
        layout.addWidget(button_widget)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
    def _create_sample_list_area(self) -> QGroupBox:
        """创建样本列表区域"""
        group = QGroupBox("样本列表")
        layout = QVBoxLayout(group)
        
        # 筛选控件
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("筛选:"))
        
        self.filter_name_edit = QLineEdit()
        self.filter_name_edit.setPlaceholderText("样本名称...")
        self.filter_name_edit.textChanged.connect(self._filter_samples)
        filter_layout.addWidget(self.filter_name_edit)
        
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItems(["全部类型", "磷酸铁锂", "三元锂", "其他"])
        self.filter_type_combo.currentTextChanged.connect(self._filter_samples)
        filter_layout.addWidget(self.filter_type_combo)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["按时间排序", "按名称排序", "按类型排序"])
        self.sort_combo.currentTextChanged.connect(self._sort_samples)
        filter_layout.addWidget(self.sort_combo)
        
        layout.addLayout(filter_layout)
        
        # 样本列表表格
        self.samples_table = QTableWidget()
        self.samples_table.setColumnCount(6)
        self.samples_table.setHorizontalHeaderLabels([
            "样本名称", "电池类型", "容量", "标准电阻", "创建时间", "文件大小"
        ])
        
        # 设置表格属性
        self.samples_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.samples_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.samples_table.setAlternatingRowColors(True)
        self.samples_table.setSortingEnabled(True)
        
        # 设置列宽
        header = self.samples_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 样本名称
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 电池类型
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 容量
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 标准电阻
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 创建时间
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 文件大小
        
        # 连接信号
        self.samples_table.itemSelectionChanged.connect(self._on_sample_selection_changed)
        self.samples_table.itemDoubleClicked.connect(self._on_sample_double_clicked)
        
        layout.addWidget(self.samples_table)
        
        return group
        
    def _create_sample_detail_area(self) -> QGroupBox:
        """创建样本详情区域"""
        group = QGroupBox("样本详情")
        layout = QVBoxLayout(group)
        
        # 基本信息
        info_group = QGroupBox("基本信息")
        info_layout = QFormLayout(info_group)
        
        self.detail_name_label = QLabel("-")
        info_layout.addRow("样本名称:", self.detail_name_label)
        
        self.detail_brand_label = QLabel("-")
        info_layout.addRow("电芯品牌:", self.detail_brand_label)
        
        self.detail_type_label = QLabel("-")
        info_layout.addRow("电芯类型:", self.detail_type_label)
        
        self.detail_capacity_label = QLabel("-")
        info_layout.addRow("电芯容量:", self.detail_capacity_label)
        
        self.detail_impedance_label = QLabel("-")
        info_layout.addRow("标准电阻:", self.detail_impedance_label)
        
        self.detail_created_label = QLabel("-")
        info_layout.addRow("创建时间:", self.detail_created_label)
        
        layout.addWidget(info_group)
        
        # 分析信息
        analysis_group = QGroupBox("分析信息")
        analysis_layout = QFormLayout(analysis_group)
        
        self.detail_threshold_label = QLabel("-")
        analysis_layout.addRow("偏差阈值:", self.detail_threshold_label)
        
        self.detail_mode_label = QLabel("-")
        analysis_layout.addRow("测试模式:", self.detail_mode_label)
        
        self.detail_data_count_label = QLabel("-")
        analysis_layout.addRow("数据点数:", self.detail_data_count_label)
        
        layout.addWidget(analysis_group)
        
        # 样本描述
        desc_group = QGroupBox("样本描述")
        desc_layout = QVBoxLayout(desc_group)
        
        self.detail_description_text = QTextEdit()
        self.detail_description_text.setReadOnly(True)
        self.detail_description_text.setMaximumHeight(100)
        desc_layout.addWidget(self.detail_description_text)
        
        layout.addWidget(desc_group)
        
        return group
        
    def _create_button_area(self) -> QHBoxLayout:
        """创建按钮区域"""
        layout = QHBoxLayout()
        
        # 左侧按钮
        self.open_sample_btn = QPushButton("📂 打开样本")
        self.open_sample_btn.setEnabled(False)
        self.open_sample_btn.clicked.connect(self._open_selected_sample)
        layout.addWidget(self.open_sample_btn)
        
        self.delete_sample_btn = QPushButton("🗑️ 删除样本")
        self.delete_sample_btn.setEnabled(False)
        self.delete_sample_btn.clicked.connect(self._delete_selected_sample)
        layout.addWidget(self.delete_sample_btn)
        
        self.export_sample_btn = QPushButton("📤 导出样本")
        self.export_sample_btn.setEnabled(False)
        self.export_sample_btn.clicked.connect(self._export_selected_sample)
        layout.addWidget(self.export_sample_btn)
        
        layout.addStretch()
        
        # 右侧按钮
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self._load_samples)
        layout.addWidget(self.refresh_btn)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.reject)
        layout.addWidget(self.close_btn)
        
        return layout

    def _load_samples(self):
        """加载样本列表"""
        try:
            self.samples_data.clear()

            # 样本存储目录
            samples_dir = "data/samples"
            if not os.path.exists(samples_dir):
                os.makedirs(samples_dir, exist_ok=True)
                logger.info(f"创建样本目录: {samples_dir}")
                self._update_samples_table()
                return

            # 扫描样本文件
            sample_files = []
            for filename in os.listdir(samples_dir):
                if filename.endswith('.json') and filename.startswith('sample_'):
                    # 使用绝对路径，确保路径正确
                    filepath = os.path.abspath(os.path.join(samples_dir, filename))
                    sample_files.append(filepath)

            logger.info(f"找到 {len(sample_files)} 个样本文件")

            # 读取样本信息
            for filepath in sample_files:
                try:
                    # 验证文件是否存在
                    if not os.path.exists(filepath):
                        logger.warning(f"样本文件不存在: {filepath}")
                        continue

                    with open(filepath, 'r', encoding='utf-8') as f:
                        sample_data = json.load(f)

                    # 验证样本数据
                    if self._validate_sample_data(sample_data):
                        # 添加文件信息（使用标准化路径）
                        sample_data['file_path'] = os.path.normpath(filepath)
                        sample_data['file_size'] = os.path.getsize(filepath)
                        self.samples_data.append(sample_data)
                    else:
                        logger.warning(f"样本文件格式不正确: {filepath}")

                except Exception as e:
                    logger.error(f"读取样本文件失败 {filepath}: {e}")

            # 更新表格显示
            self._update_samples_table()

            logger.info(f"成功加载 {len(self.samples_data)} 个样本")

        except Exception as e:
            logger.error(f"加载样本列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载样本列表失败: {e}")

    def _validate_sample_data(self, sample_data: Dict) -> bool:
        """验证样本数据完整性"""
        try:
            required_fields = ['info', 'median_data', 'created_at']
            for field in required_fields:
                if field not in sample_data:
                    return False

            # 验证样本信息
            info = sample_data['info']
            required_info_fields = ['sample_name', 'brand', 'cell_type']
            for field in required_info_fields:
                if field not in info:
                    return False

            return True

        except Exception:
            return False

    def _update_samples_table(self):
        """更新样本表格显示"""
        try:
            self.samples_table.setRowCount(len(self.samples_data))

            for row, sample_data in enumerate(self.samples_data):
                info = sample_data.get('info', {})

                # 样本名称 - 存储样本数据索引作为用户数据
                name_item = QTableWidgetItem(info.get('sample_name', '未知'))
                name_item.setData(Qt.ItemDataRole.UserRole, row)  # 存储原始数据索引
                self.samples_table.setItem(row, 0, name_item)

                # 电池类型
                cell_type_item = QTableWidgetItem(info.get('cell_type', '未知'))
                self.samples_table.setItem(row, 1, cell_type_item)

                # 容量
                capacity_display = info.get('capacity_display', f"{info.get('capacity', 0)}mAh")
                capacity_item = QTableWidgetItem(capacity_display)
                self.samples_table.setItem(row, 2, capacity_item)

                # 标准电阻
                impedance_display = info.get('standard_impedance_display', f"{info.get('standard_impedance', 0):.3f}mΩ")
                impedance_item = QTableWidgetItem(impedance_display)
                self.samples_table.setItem(row, 3, impedance_item)

                # 创建时间
                created_at = sample_data.get('created_at', '')
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        time_str = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        time_str = created_at[:16] if len(created_at) >= 16 else created_at
                else:
                    time_str = '未知'
                time_item = QTableWidgetItem(time_str)
                self.samples_table.setItem(row, 4, time_item)

                # 文件大小
                file_size = sample_data.get('file_size', 0)
                if file_size > 1024 * 1024:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                elif file_size > 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size} B"
                size_item = QTableWidgetItem(size_str)
                self.samples_table.setItem(row, 5, size_item)

            # 应用筛选
            self._filter_samples()

        except Exception as e:
            logger.error(f"更新样本表格失败: {e}")

    def _filter_samples(self):
        """筛选样本"""
        try:
            name_filter = self.filter_name_edit.text().lower()
            type_filter = self.filter_type_combo.currentText()

            for row in range(self.samples_table.rowCount()):
                show_row = True

                # 名称筛选
                if name_filter:
                    name_item = self.samples_table.item(row, 0)
                    if name_item and name_filter not in name_item.text().lower():
                        show_row = False

                # 类型筛选
                if type_filter != "全部类型":
                    type_item = self.samples_table.item(row, 1)
                    if type_item and type_filter not in type_item.text():
                        show_row = False

                self.samples_table.setRowHidden(row, not show_row)

        except Exception as e:
            logger.error(f"筛选样本失败: {e}")

    def _sort_samples(self):
        """排序样本"""
        try:
            sort_type = self.sort_combo.currentText()

            if sort_type == "按时间排序":
                self.samples_table.sortItems(4, Qt.SortOrder.DescendingOrder)
            elif sort_type == "按名称排序":
                self.samples_table.sortItems(0, Qt.SortOrder.AscendingOrder)
            elif sort_type == "按类型排序":
                self.samples_table.sortItems(1, Qt.SortOrder.AscendingOrder)

        except Exception as e:
            logger.error(f"排序样本失败: {e}")

    def _on_sample_selection_changed(self):
        """样本选择改变事件"""
        try:
            current_row = self.samples_table.currentRow()

            if current_row >= 0:
                # 从第一列获取存储的原始数据索引
                name_item = self.samples_table.item(current_row, 0)
                if name_item:
                    data_index = name_item.data(Qt.ItemDataRole.UserRole)
                    if data_index is not None and 0 <= data_index < len(self.samples_data):
                        # 获取选中的样本
                        self.current_sample = self.samples_data[data_index]

                        # 更新详情显示
                        self._update_sample_details(self.current_sample)

                        # 启用操作按钮
                        self.open_sample_btn.setEnabled(True)
                        self.delete_sample_btn.setEnabled(True)
                        self.export_sample_btn.setEnabled(True)
                        return

            # 如果没有有效选择，清空状态
            self.current_sample = None
            self._clear_sample_details()

            # 禁用操作按钮
            self.open_sample_btn.setEnabled(False)
            self.delete_sample_btn.setEnabled(False)
            self.export_sample_btn.setEnabled(False)

        except Exception as e:
            logger.error(f"处理样本选择事件失败: {e}")
            # 发生错误时也要清空状态
            self.current_sample = None
            self._clear_sample_details()
            self.open_sample_btn.setEnabled(False)
            self.delete_sample_btn.setEnabled(False)
            self.export_sample_btn.setEnabled(False)

    def _on_sample_double_clicked(self, item):
        """样本双击事件"""
        try:
            if self.current_sample:
                self._open_selected_sample()
        except Exception as e:
            logger.error(f"处理样本双击事件失败: {e}")

    def _update_sample_details(self, sample_data: Dict):
        """更新样本详情显示"""
        try:
            info = sample_data.get('info', {})

            # 基本信息
            self.detail_name_label.setText(info.get('sample_name', '未知'))
            self.detail_brand_label.setText(info.get('brand', '未知'))
            self.detail_type_label.setText(info.get('cell_type', '未知'))

            # 容量显示
            capacity_display = info.get('capacity_display', f"{info.get('capacity', 0)}mAh")
            self.detail_capacity_label.setText(capacity_display)

            # 标准电阻显示
            impedance_display = info.get('standard_impedance_display', f"{info.get('standard_impedance', 0):.3f}mΩ")
            self.detail_impedance_label.setText(impedance_display)

            # 创建时间
            created_at = sample_data.get('created_at', '')
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    time_str = created_at
            else:
                time_str = '未知'
            self.detail_created_label.setText(time_str)

            # 分析信息
            threshold = sample_data.get('threshold', 0)
            self.detail_threshold_label.setText(f"{threshold}%")

            mode = sample_data.get('mode', '未知')
            self.detail_mode_label.setText(mode)

            # 数据点数统计
            median_data = sample_data.get('median_data', {})
            total_points = 0
            for channel_data in median_data.values():
                total_points += len(channel_data)
            self.detail_data_count_label.setText(str(total_points))

            # 样本描述
            description = info.get('description', '无描述')
            self.detail_description_text.setPlainText(description)

        except Exception as e:
            logger.error(f"更新样本详情失败: {e}")

    def _clear_sample_details(self):
        """清空样本详情显示"""
        self.detail_name_label.setText("-")
        self.detail_brand_label.setText("-")
        self.detail_type_label.setText("-")
        self.detail_capacity_label.setText("-")
        self.detail_impedance_label.setText("-")
        self.detail_created_label.setText("-")
        self.detail_threshold_label.setText("-")
        self.detail_mode_label.setText("-")
        self.detail_data_count_label.setText("-")
        self.detail_description_text.clear()

    def _open_selected_sample(self):
        """打开选中的样本"""
        try:
            if not self.current_sample:
                QMessageBox.warning(self, "警告", "请先选择要打开的样本")
                return

            # 显示进度条
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

            # 创建加载线程
            sample_file_path = self.current_sample['file_path']
            self.load_thread = SampleLoadThread(sample_file_path)
            self.load_thread.progress_updated.connect(self.progress_bar.setValue)
            self.load_thread.sample_loaded.connect(self._on_sample_loaded)
            self.load_thread.error_occurred.connect(self._on_sample_load_error)

            # 启动加载
            self.load_thread.start()

        except Exception as e:
            logger.error(f"打开样本失败: {e}")
            QMessageBox.critical(self, "错误", f"打开样本失败: {e}")
            self.progress_bar.setVisible(False)

    def _on_sample_loaded(self, sample_data: Dict):
        """样本加载完成事件"""
        try:
            self.progress_bar.setVisible(False)

            # 发送样本选择信号
            self.sample_selected.emit(sample_data)

            # 显示成功消息
            sample_name = sample_data.get('info', {}).get('sample_name', '未知样本')
            QMessageBox.information(
                self, "样本加载成功",
                f"✅ 样本 '{sample_name}' 加载成功！\n\n"
                "样本数据已加载到学习功能界面，\n"
                "您可以查看中位值曲线和分析结果。"
            )

            # 关闭对话框
            self.accept()

        except Exception as e:
            logger.error(f"处理样本加载完成事件失败: {e}")
            self.progress_bar.setVisible(False)

    def _on_sample_load_error(self, error_message: str):
        """样本加载错误事件"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(
            self, "样本加载失败",
            f"❌ 样本加载失败:\n\n{error_message}\n\n"
            "请检查样本文件是否完整或格式是否正确。"
        )

    def _delete_selected_sample(self):
        """删除选中的样本"""
        try:
            if not self.current_sample:
                QMessageBox.warning(self, "警告", "请先选择要删除的样本")
                return

            sample_name = self.current_sample.get('info', {}).get('sample_name', '未知样本')

            # 确认删除
            reply = QMessageBox.question(
                self, "确认删除",
                f"⚠️ 确定要删除样本 '{sample_name}' 吗？\n\n"
                "此操作不可撤销，样本文件将被永久删除。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 删除文件
                file_path = self.current_sample['file_path']
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"删除样本文件: {file_path}")

                # 重新加载样本列表
                self._load_samples()

                QMessageBox.information(
                    self, "删除成功",
                    f"✅ 样本 '{sample_name}' 已成功删除！"
                )

        except Exception as e:
            logger.error(f"删除样本失败: {e}")
            QMessageBox.critical(self, "错误", f"删除样本失败: {e}")

    def _export_selected_sample(self):
        """导出选中的样本"""
        try:
            if not self.current_sample:
                QMessageBox.warning(self, "警告", "请先选择要导出的样本")
                return

            sample_name = self.current_sample.get('info', {}).get('sample_name', '未知样本')

            # 生成安全的默认文件名
            safe_name = "".join(c for c in sample_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_') if safe_name else 'sample'
            default_filename = f"{safe_name}_导出.json"

            # 选择保存位置
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出样本",
                default_filename,
                "JSON文件 (*.json);;所有文件 (*.*)"
            )

            if not filename:
                return

            # 验证源文件路径
            source_file = self.current_sample.get('file_path', '')
            if not source_file or not os.path.exists(source_file):
                # 如果源文件不存在，直接保存当前样本数据
                logger.warning(f"源文件不存在: {source_file}，将保存当前样本数据")

                # 移除文件路径和大小信息，避免序列化问题
                export_data = dict(self.current_sample)
                export_data.pop('file_path', None)
                export_data.pop('file_size', None)

                # 直接保存样本数据
                import json
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            else:
                # 复制样本文件
                import shutil
                shutil.copy2(source_file, filename)

            QMessageBox.information(
                self, "导出成功",
                f"✅ 样本 '{sample_name}' 已成功导出到:\n{filename}"
            )

        except Exception as e:
            logger.error(f"导出样本失败: {e}")
            QMessageBox.critical(self, "错误", f"导出样本失败:\n{str(e)}\n\n请检查文件路径和权限。")

    def get_selected_sample(self) -> Optional[Dict]:
        """获取选中的样本数据"""
        return self.current_sample
