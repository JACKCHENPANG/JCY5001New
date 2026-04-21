# -*- coding: utf-8 -*-
"""
基准管理对话框
管理中位Z值基准数据

Author: Jack
Date: 2025-06-01
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QAbstractItemView, QTextEdit,
    QGroupBox, QSplitter, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class BaselineManagerDialog(QDialog):
    """基准管理对话框"""

    def __init__(self, outlier_manager, parent=None):
        """
        初始化基准管理对话框

        Args:
            outlier_manager: 离群检测管理器
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.outlier_manager = outlier_manager
        self.current_baseline_id = None
        
        self._init_ui()
        self._init_connections()
        self._load_baselines()
        
        logger.debug("基准管理对话框初始化完成")

    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("基准数据管理")
        self.setModal(True)
        self.resize(900, 600)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧：基准列表
        left_widget = self._create_baseline_list_widget()
        splitter.addWidget(left_widget)
        
        # 右侧：基准详情
        right_widget = self._create_baseline_details_widget()
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([400, 500])
        
        # 创建按钮区域
        button_layout = self._create_button_area()
        main_layout.addLayout(button_layout)

    def _create_baseline_list_widget(self) -> QGroupBox:
        """创建基准列表组件"""
        group = QGroupBox("基准列表")
        group.setFont(QFont("", 10, QFont.Bold))
        
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # 创建基准列表表格
        self.baseline_table = QTableWidget()
        self.baseline_table.setColumnCount(5)
        self.baseline_table.setHorizontalHeaderLabels([
            "基准名称", "通道模式", "数据点数", "创建时间", "状态"
        ])
        
        # 设置表格属性
        self.baseline_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.baseline_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.baseline_table.setAlternatingRowColors(True)
        
        # 设置列宽
        header = self.baseline_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.baseline_table)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setMaximumWidth(80)
        button_layout.addWidget(self.refresh_btn)
        
        self.delete_btn = QPushButton("删除")
        self.delete_btn.setMaximumWidth(80)
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return group

    def _create_baseline_details_widget(self) -> QGroupBox:
        """创建基准详情组件"""
        group = QGroupBox("基准详情")
        group.setFont(QFont("", 10, QFont.Bold))
        
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # 基准信息
        info_layout = QGridLayout()
        info_layout.setSpacing(8)
        
        info_layout.addWidget(QLabel("基准名称:"), 0, 0)
        self.baseline_name_label = QLabel("未选择")
        info_layout.addWidget(self.baseline_name_label, 0, 1)
        
        info_layout.addWidget(QLabel("通道模式:"), 0, 2)
        self.channel_mode_label = QLabel("未选择")
        info_layout.addWidget(self.channel_mode_label, 0, 3)
        
        info_layout.addWidget(QLabel("数据点数:"), 1, 0)
        self.data_count_label = QLabel("0")
        info_layout.addWidget(self.data_count_label, 1, 1)
        
        info_layout.addWidget(QLabel("创建时间:"), 1, 2)
        self.created_time_label = QLabel("未知")
        info_layout.addWidget(self.created_time_label, 1, 3)
        
        layout.addLayout(info_layout)
        
        # 描述信息
        layout.addWidget(QLabel("描述信息:"))
        self.description_text = QTextEdit()
        self.description_text.setMaximumHeight(80)
        self.description_text.setReadOnly(True)
        layout.addWidget(self.description_text)
        
        # 详细数据表格
        layout.addWidget(QLabel("详细数据:"))
        self.details_table = QTableWidget()
        self.details_table.setColumnCount(5)
        self.details_table.setHorizontalHeaderLabels([
            "通道", "频率(Hz)", "中位Z值(mΩ)", "实部(mΩ)", "虚部(mΩ)"
        ])
        
        # 设置详情表格属性
        self.details_table.setAlternatingRowColors(True)
        self.details_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # 设置详情表格列宽
        details_header = self.details_table.horizontalHeader()
        details_header.setStretchLastSection(True)
        for i in range(5):
            details_header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.details_table)
        
        return group

    def _create_button_area(self) -> QHBoxLayout:
        """创建按钮区域"""
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.setMinimumWidth(80)
        layout.addWidget(self.close_btn)
        
        return layout

    def _init_connections(self):
        """初始化信号连接"""
        try:
            self.baseline_table.itemSelectionChanged.connect(self._on_baseline_selection_changed)
            self.refresh_btn.clicked.connect(self._load_baselines)
            self.delete_btn.clicked.connect(self._delete_baseline)
            self.close_btn.clicked.connect(self.accept)
            
        except Exception as e:
            logger.error(f"初始化信号连接失败: {e}")

    def _load_baselines(self):
        """加载基准列表"""
        try:
            baselines = self.outlier_manager.get_all_baselines()
            
            self.baseline_table.setRowCount(len(baselines))
            
            for row, baseline in enumerate(baselines):
                # 基准名称
                name_item = QTableWidgetItem(baseline['baseline_name'])
                name_item.setData(Qt.UserRole, baseline['id'])
                self.baseline_table.setItem(row, 0, name_item)
                
                # 通道模式
                mode_text = "固定通道" if baseline['channel_mode'] == 'fixed_channel' else "平均模式"
                self.baseline_table.setItem(row, 1, QTableWidgetItem(mode_text))
                
                # 数据点数
                self.baseline_table.setItem(row, 2, QTableWidgetItem(str(baseline['detail_count'])))
                
                # 创建时间
                created_at = baseline['created_at']
                if created_at:
                    try:
                        # 尝试解析时间戳
                        if isinstance(created_at, str):
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        else:
                            dt = datetime.fromtimestamp(created_at)
                        time_str = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        time_str = str(created_at)
                else:
                    time_str = "未知"
                self.baseline_table.setItem(row, 3, QTableWidgetItem(time_str))
                
                # 状态
                status_text = "激活" if baseline.get('is_active') else "未激活"
                status_item = QTableWidgetItem(status_text)
                if baseline.get('is_active'):
                    status_item.setBackground(Qt.green)
                self.baseline_table.setItem(row, 4, status_item)
            
            logger.info(f"基准列表加载完成，共{len(baselines)}个基准")
            
        except Exception as e:
            logger.error(f"加载基准列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载基准列表失败: {e}")

    def _on_baseline_selection_changed(self):
        """基准选择变更处理"""
        try:
            current_row = self.baseline_table.currentRow()
            if current_row >= 0:
                name_item = self.baseline_table.item(current_row, 0)
                if name_item:
                    baseline_id = name_item.data(Qt.UserRole)
                    self.current_baseline_id = baseline_id
                    self._load_baseline_details(baseline_id)
                    self.delete_btn.setEnabled(True)
            else:
                self.current_baseline_id = None
                self._clear_baseline_details()
                self.delete_btn.setEnabled(False)
                
        except Exception as e:
            logger.error(f"基准选择变更处理失败: {e}")

    def _load_baseline_details(self, baseline_id: int):
        """加载基准详情"""
        try:
            # 获取基准信息
            baselines = self.outlier_manager.get_all_baselines()
            baseline_info = None
            for baseline in baselines:
                if baseline['id'] == baseline_id:
                    baseline_info = baseline
                    break
            
            if not baseline_info:
                self._clear_baseline_details()
                return
            
            # 更新基准信息
            self.baseline_name_label.setText(baseline_info['baseline_name'])
            mode_text = "固定通道模式" if baseline_info['channel_mode'] == 'fixed_channel' else "平均模式"
            self.channel_mode_label.setText(mode_text)
            self.data_count_label.setText(str(baseline_info['detail_count']))
            
            # 创建时间
            created_at = baseline_info['created_at']
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = datetime.fromtimestamp(created_at)
                    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    time_str = str(created_at)
            else:
                time_str = "未知"
            self.created_time_label.setText(time_str)
            
            # 描述信息
            description = baseline_info.get('description', '') or '无描述'
            self.description_text.setPlainText(description)
            
            # 获取详细数据
            details = self.outlier_manager.get_baseline_details(baseline_id)
            
            # 更新详细数据表格
            self.details_table.setRowCount(len(details))
            
            for row, detail in enumerate(details):
                self.details_table.setItem(row, 0, QTableWidgetItem(str(detail['channel_number'])))
                self.details_table.setItem(row, 1, QTableWidgetItem(f"{detail['frequency']:.3f}"))
                self.details_table.setItem(row, 2, QTableWidgetItem(f"{detail['median_z_value']:.3f}"))
                self.details_table.setItem(row, 3, QTableWidgetItem(f"{detail['median_real']:.3f}"))
                self.details_table.setItem(row, 4, QTableWidgetItem(f"{detail['median_imag']:.3f}"))
            
            logger.debug(f"基准详情加载完成: {baseline_info['baseline_name']}")
            
        except Exception as e:
            logger.error(f"加载基准详情失败: {e}")
            self._clear_baseline_details()

    def _clear_baseline_details(self):
        """清空基准详情"""
        self.baseline_name_label.setText("未选择")
        self.channel_mode_label.setText("未选择")
        self.data_count_label.setText("0")
        self.created_time_label.setText("未知")
        self.description_text.clear()
        self.details_table.setRowCount(0)

    def _delete_baseline(self):
        """删除基准"""
        try:
            if not self.current_baseline_id:
                return
            
            # 确认删除
            current_row = self.baseline_table.currentRow()
            baseline_name = self.baseline_table.item(current_row, 0).text()
            
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除基准 '{baseline_name}' 吗？\n\n此操作不可撤销！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                success = self.outlier_manager.delete_baseline(self.current_baseline_id)
                if success:
                    QMessageBox.information(self, "成功", "基准删除成功！")
                    self._load_baselines()  # 重新加载列表
                    self._clear_baseline_details()
                    self.current_baseline_id = None
                    self.delete_btn.setEnabled(False)
                else:
                    QMessageBox.warning(self, "删除失败", "无法删除当前激活的基准，请先切换到其他基准。")
            
        except Exception as e:
            logger.error(f"删除基准失败: {e}")
            QMessageBox.critical(self, "错误", f"删除基准失败: {e}")
