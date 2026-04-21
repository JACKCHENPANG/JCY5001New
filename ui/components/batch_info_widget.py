# -*- coding: utf-8 -*-
"""
批次信息显示组件
显示批次号、电芯规格、当前时间、测试时长、操作员等信息

Author: Jack
Date: 2025-01-27
"""

import os
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QGridLayout, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
import logging

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager


class BatchInfoWidget(QWidget):
    """批次信息显示组件"""

    # 信号定义
    batch_info_changed = pyqtSignal(str, object)  # 批次信息变更信号

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        初始化批次信息组件

        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.test_start_time = None  # 测试开始时间

        # 系统运行时间相关
        self.system_start_time = datetime.now()

        # 初始化界面
        self._init_ui()
        self._init_timer()
        self._load_batch_info()

        logger.debug("批次信息组件初始化完成")

    def _init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 创建分组框
        group_box = QGroupBox("批次信息")
        group_box.setObjectName("batchInfoGroup")
        main_layout.addWidget(group_box)

        # 创建网格布局
        grid_layout = QGridLayout(group_box)
        grid_layout.setContentsMargins(8, 8, 8, 8)  # 减少边距以适配14%布局空间
        grid_layout.setSpacing(4)  # 减少间距以适配14%布局空间

        # 创建信息显示项
        self._create_info_items(grid_layout)

        # 设置组件样式
        self._apply_styles()

    def _create_info_items(self, layout):
        """创建信息显示项"""
        # 批次号
        layout.addWidget(QLabel("批次号:"), 0, 0)
        self.batch_number_label = QLabel("未设置")
        self.batch_number_label.setObjectName("valueLabel")
        self.batch_number_label.setWordWrap(True)  # 启用自动换行
        # 移除对齐设置，使用默认对齐方式
        layout.addWidget(self.batch_number_label, 0, 1)

        # 电池规格（与产品设置保持一致）
        layout.addWidget(QLabel("电池规格:"), 0, 2)
        self.cell_spec_label = QLabel("未设置")
        self.cell_spec_label.setObjectName("valueLabel")
        layout.addWidget(self.cell_spec_label, 0, 3)

        # 当前时间
        layout.addWidget(QLabel("当前时间:"), 1, 0)
        self.current_time_label = QLabel()
        self.current_time_label.setObjectName("valueLabel")
        layout.addWidget(self.current_time_label, 1, 1)

        # 操作员
        layout.addWidget(QLabel("操作员:"), 1, 2)
        self.operator_label = QLabel("未设置")
        self.operator_label.setObjectName("valueLabel")
        layout.addWidget(self.operator_label, 1, 3)

        # 电池类型
        layout.addWidget(QLabel("电池类型:"), 2, 0)
        self.cell_type_label = QLabel("未设置")
        self.cell_type_label.setObjectName("valueLabel")
        layout.addWidget(self.cell_type_label, 2, 1)

        # 运行时间
        layout.addWidget(QLabel("运行时间:"), 2, 2)
        self.system_uptime_label = QLabel("00:00:00")
        self.system_uptime_label.setObjectName("valueLabel")
        layout.addWidget(self.system_uptime_label, 2, 3)

        # 设置列拉伸 - 布局优化：减少标签列间距，增加数值列空间
        layout.setColumnStretch(0, 0)  # 标签列固定宽度
        layout.setColumnStretch(1, 3)  # 数值列更多空间（从2增加到3）
        layout.setColumnStretch(2, 0)  # 标签列固定宽度
        layout.setColumnStretch(3, 3)  # 数值列更多空间（从2增加到3）

        # 布局优化：减少列间距，使信息框紧贴标签
        layout.setHorizontalSpacing(2)  # 减少水平间距
        layout.setVerticalSpacing(2)    # 减少垂直间距

    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QGroupBox#batchInfoGroup {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 6px;
                margin-top: 0.2ex;
                padding-top: 3px;
                background-color: white;
            }

            QGroupBox#batchInfoGroup::title {
                subcontrol-origin: margin;
                left: 6px;
                padding: 0 4px 0 4px;
                color: #3498db;
                font-size: 11pt;  /* 字体优化：从9pt增加到11pt */
                font-weight: bold;  /* 字体优化：加粗 */
            }

            QLabel {
                font-size: 11pt;  /* 字体优化：标签文字从9pt增加到11pt */
                font-weight: bold;  /* 字体优化：标签文字加粗 */
                color: #2c3e50;
            }

            QLabel#valueLabel {
                font-size: 9pt;   /* 字体优化：数值内容从8pt增加到9pt */
                font-weight: bold;
                color: #2c3e50;
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 2px;
                padding: 1px 6px;  /* 布局优化：减少内边距，使信息框更紧凑 */
                min-width: 160px;  /* 布局优化：进一步增加最小宽度从120px到160px，确保长批次号完整显示 */
                max-width: none;   /* 布局优化：允许根据内容自动扩展宽度 */
                min-height: 10px;  /* 字体优化：适应更大字体的高度 */
                max-height: 18px;  /* 字体优化：适应更大字体的高度 */
            }
        """)

    def _init_timer(self):
        """初始化定时器"""
        # 时间更新定时器
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self._update_time_display)
        self.time_timer.start(1000)  # 每秒更新一次

    def _load_batch_info(self):
        """加载批次信息"""
        try:
            # 从配置中加载批次信息
            batch_number = self.config_manager.get('batch_info.batch_number', '')
            operator = self.config_manager.get('batch_info.operator', '')
            cell_type = self.config_manager.get('batch_info.cell_type', '磷酸铁锂')

            # 优化电池规格优先从产品设置中读取，确保与产品设置保持一致
            cell_spec = self.config_manager.get('product.battery_spec',
                                              self.config_manager.get('batch_info.cell_spec', '21700'))

            # 更新显示
            self.set_batch_number(batch_number if batch_number else "未设置")
            self.set_operator(operator if operator else "未设置")
            self.set_cell_type(cell_type)
            self.set_cell_spec(cell_spec)

        except Exception as e:
            logger.error(f"加载批次信息失败: {e}")

    def _update_time_display(self):
        """更新时间显示"""
        try:
            # 更新当前时间 - 优化：使用更紧凑的时间格式
            current_time = datetime.now().strftime("%m-%d %H:%M:%S")
            self.current_time_label.setText(current_time)

            # 更新系统运行时间
            system_uptime = datetime.now() - self.system_start_time
            hours, remainder = divmod(int(system_uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.system_uptime_label.setText(uptime_str)



        except Exception as e:
            logger.error(f"更新时间显示失败: {e}")

    def set_batch_number(self, batch_number: str):
        """
        设置批次号

        Args:
            batch_number: 批次号
        """
        self.batch_number_label.setText(batch_number)
        self.config_manager.set('batch_info.batch_number', batch_number)
        self.batch_info_changed.emit('batch_number', batch_number)

    def set_operator(self, operator: str):
        """
        设置操作员

        Args:
            operator: 操作员姓名
        """
        self.operator_label.setText(operator)
        self.config_manager.set('batch_info.operator', operator)
        self.batch_info_changed.emit('operator', operator)

    def set_cell_type(self, cell_type: str):
        """
        设置电池类型

        Args:
            cell_type: 电池类型
        """
        self.cell_type_label.setText(cell_type)
        self.config_manager.set('batch_info.cell_type', cell_type)
        self.batch_info_changed.emit('cell_type', cell_type)

    def set_cell_spec(self, cell_spec: str):
        """
        设置电池规格（与产品设置保持同步）

        Args:
            cell_spec: 电池规格
        """
        self.cell_spec_label.setText(cell_spec)
        # 优化同时更新批次信息和产品设置，确保数据一致性
        self.config_manager.set('batch_info.cell_spec', cell_spec)
        self.config_manager.set('product.battery_spec', cell_spec)
        self.batch_info_changed.emit('cell_spec', cell_spec)

    def refresh_battery_spec_from_product(self):
        """
        从产品设置刷新电池规格显示
        """
        try:
            # 从产品设置中读取电池规格
            battery_spec = self.config_manager.get('product.battery_spec', '21700')

            # 更新显示（不触发配置变更事件，避免循环）
            self.cell_spec_label.setText(battery_spec)

            # 同步到批次信息配置
            self.config_manager.set('batch_info.cell_spec', battery_spec)

            logger.debug(f"从产品设置刷新电池规格: {battery_spec}")

        except Exception as e:
            logger.error(f"刷新电池规格失败: {e}")

    def get_batch_info(self) -> dict:
        """
        获取当前批次信息

        Returns:
            批次信息字典
        """
        return {
            'batch_number': self.batch_number_label.text(),
            'operator': self.operator_label.text(),
            'cell_type': self.cell_type_label.text(),
            'cell_spec': self.cell_spec_label.text(),
            'test_start_time': self.test_start_time.isoformat() if self.test_start_time else None
        }

    def get_test_duration_seconds(self) -> int:
        """
        获取测试时长（秒）

        Returns:
            测试时长秒数
        """
        if self.test_start_time:
            duration = datetime.now() - self.test_start_time
            return int(duration.total_seconds())
        return 0

    def load_settings(self):
        """重新加载设置"""
        self._load_batch_info()

    def refresh_display(self):
        """刷新显示（用于设置变更后的界面更新）"""
        try:
            logger.debug("刷新批次信息显示...")
            self._load_batch_info()
            logger.debug("批次信息显示刷新完成")
        except Exception as e:
            logger.error(f"刷新批次信息显示失败: {e}")
