# -*- coding: utf-8 -*-
"""
统计区域组件
显示总测试数、合格数、不合格数、良率和Rs-Rct档位分布图

Author: Jack
Date: 2025-01-27
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QGridLayout, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from typing import Optional
import logging

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager
from utils.statistics_counter_manager import StatisticsCounterManager


class StatisticsWidget(QWidget):
    """统计区域组件"""

    # 信号定义
    statistics_updated = pyqtSignal(dict)  # 统计数据更新信号

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        初始化统计组件

        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)

        self.config_manager = config_manager

        # 新增使用独立的统计计数器管理器
        self.counter_manager = StatisticsCounterManager(config_manager)

        # 统计数据
        self.total_count = 0
        self.pass_count = 0
        self.fail_count = 0
        self.grade_distribution = {}  # Rs-Rct档位分布

        # 初始化界面
        self._init_ui()
        self._init_grade_table()

        # 修复启动时加载统计计数器数据
        self._load_counter_statistics()

        logger.debug("统计区域组件初始化完成")

    def _init_ui(self):
        """初始化用户界面"""
        # 创建主布局 - 压缩优化：减少边距和间距
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(3, 3, 3, 3)  # 从5减少到3
        main_layout.setSpacing(2)  # 从5减少到2

        # 创建分组框
        group_box = QGroupBox("测试统计")
        group_box.setObjectName("statisticsGroup")
        main_layout.addWidget(group_box)

        # 创建内容布局 - 压缩优化：进一步减少边距和间距
        content_layout = QHBoxLayout(group_box)
        content_layout.setContentsMargins(4, 4, 4, 4)  # 从8减少到4
        content_layout.setSpacing(4)  # 从8减少到4

        # 左侧：统计数据 - 优化：统计数据与档位分布图1:1比例
        stats_widget = self._create_statistics_section()
        content_layout.addWidget(stats_widget, 1)  # 统计数据占1份空间

        # 右侧：档位分布图 - 优化：与统计数据等宽显示
        grade_widget = self._create_grade_distribution_section()
        content_layout.addWidget(grade_widget, 1)  # 档位分布图占1份空间

        # 设置组件样式
        self._apply_styles()

    def _create_statistics_section(self):
        """创建统计数据区域"""
        stats_widget = QWidget()
        stats_layout = QGridLayout(stats_widget)
        stats_layout.setSpacing(2)  # 压缩优化：从4减少到2

        # 总测试数
        stats_layout.addWidget(QLabel("总测试数:"), 0, 0)
        self.total_count_label = QLabel("0")
        self.total_count_label.setObjectName("valueLabel")
        self.total_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 显示优化：居中对齐
        stats_layout.addWidget(self.total_count_label, 0, 1)

        # 合格数
        stats_layout.addWidget(QLabel("合格数:"), 1, 0)
        self.pass_count_label = QLabel("0")
        self.pass_count_label.setObjectName("passLabel")
        self.pass_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 显示优化：居中对齐
        stats_layout.addWidget(self.pass_count_label, 1, 1)

        # 不合格数
        stats_layout.addWidget(QLabel("不合格数:"), 2, 0)
        self.fail_count_label = QLabel("0")
        self.fail_count_label.setObjectName("failLabel")
        self.fail_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 显示优化：居中对齐
        stats_layout.addWidget(self.fail_count_label, 2, 1)

        # 良率
        stats_layout.addWidget(QLabel("良率:"), 3, 0)
        self.yield_rate_label = QLabel("0.0%")
        self.yield_rate_label.setObjectName("yieldLabel")
        self.yield_rate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 显示优化：居中对齐
        stats_layout.addWidget(self.yield_rate_label, 3, 1)

        # 设置列拉伸
        stats_layout.setColumnStretch(1, 1)

        return stats_widget

    def _create_grade_distribution_section(self):
        """创建档位分布图区域"""
        grade_widget = QWidget()
        grade_layout = QVBoxLayout(grade_widget)
        grade_layout.setSpacing(1)  # 压缩优化：从2减少到1

        # 档位范围信息区域（垂直对齐优化：减少权重，使其紧凑）
        range_container = self._create_grade_range_display()
        grade_layout.addWidget(range_container, 0)  # 垂直对齐优化：从权重1减少到0（固定高度）

        # 档位分布表格（垂直对齐优化：增加权重，向上移动与"合格数"对齐）
        self.grade_table = QTableWidget()
        self.grade_table.setObjectName("gradeTable")
        self.grade_table.setMinimumHeight(80)  # 设置最小高度，确保九宫格完全显示
        grade_layout.addWidget(self.grade_table, 3)  # 垂直对齐优化：从权重1增加到3，占用更多空间

        return grade_widget

    def _create_grade_range_display(self):
        """创建档位范围显示区域（垂直对齐优化：紧凑布局）"""
        container = QWidget()
        container_layout = QGridLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(1)  # 最大化压缩：从2减少到1，更紧凑

        # Rs档位范围显示（紧凑显示）
        rs_title_label = QLabel("Rs档位范围:")
        container_layout.addWidget(rs_title_label, 0, 0)

        self.rs_range_label = QLabel()
        self.rs_range_label.setObjectName("rangeValueLabel")
        self.rs_range_label.setWordWrap(True)  # 启用自动换行，避免文本被截断
        container_layout.addWidget(self.rs_range_label, 0, 1)

        # Rct档位范围显示（紧凑显示）
        rct_title_label = QLabel("Rct档位范围:")
        container_layout.addWidget(rct_title_label, 1, 0)

        self.rct_range_label = QLabel()
        self.rct_range_label.setObjectName("rangeValueLabel")
        self.rct_range_label.setWordWrap(True)  # 启用自动换行，避免文本被截断
        container_layout.addWidget(self.rct_range_label, 1, 1)

        # 垂直对齐优化：移除多余空行，让表格能够向上移动
        # 不再添加空行，让档位范围区域保持最小高度

        # 设置列拉伸
        container_layout.setColumnStretch(1, 1)

        # 设置固定高度，防止过度拉伸 - 最大化压缩给九宫格更多空间
        container.setMaximumHeight(35)  # 最大化减小高度：45px→35px，确保九宫格完全显示

        # 初始化档位范围显示
        self._update_grade_range_display()

        return container

    def _init_grade_table(self):
        """初始化档位分布表格"""
        try:
            # 获取档位设置
            rs_grades = self.config_manager.get('grade_settings.rs_grade_count', 3)
            rct_grades = 3  # Rct固定3档

            # 设置表格大小
            self.grade_table.setRowCount(rs_grades)
            self.grade_table.setColumnCount(rct_grades)

            # 设置表头
            rs_headers = [f"Rs{i+1}" for i in range(rs_grades)]
            rct_headers = [f"Rct{i+1}" for i in range(rct_grades)]

            self.grade_table.setVerticalHeaderLabels(rs_headers)
            self.grade_table.setHorizontalHeaderLabels(rct_headers)

            # 初始化表格内容
            for row in range(rs_grades):
                for col in range(rct_grades):
                    item = QTableWidgetItem("0")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    # 设置背景颜色
                    if row == 0:  # Rs1 - 绿色
                        item.setBackground(QColor("#d5f4e6"))
                    elif row == 1:  # Rs2 - 黄色
                        item.setBackground(QColor("#fef9e7"))
                    else:  # Rs3+ - 红色
                        item.setBackground(QColor("#fadbd8"))

                    self.grade_table.setItem(row, col, item)

            # 设置表格属性
            self.grade_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.grade_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.grade_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.grade_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

            # 字体优化：设置更紧凑的行高和列宽，确保档位明细完全显示
            self.grade_table.verticalHeader().setDefaultSectionSize(20)  # 进一步减小行高：24px→20px
            self.grade_table.horizontalHeader().setDefaultSectionSize(50)  # 进一步减小列宽：55px→50px

        except Exception as e:
            logger.error(f"初始化档位分布表格失败: {e}")

    def _get_grade_ranges(self):
        """获取当前档位范围配置（直接同步判定设置页面的计算结果）"""
        try:
            # 获取Rs档位配置
            rs_ranges = self._get_rs_grade_ranges_from_settings()

            # 获取Rct档位配置
            rct_ranges = self._get_rct_grade_ranges_from_settings()

            return rs_ranges, rct_ranges

        except Exception as e:
            logger.error(f"获取档位范围失败: {e}")
            return ["配置错误"], ["配置错误"]

    def _get_rs_grade_ranges_from_settings(self):
        """获取Rs档位范围配置（使用与判定设置页面完全相同的逻辑）"""
        try:
            # 获取Rs档位数量
            rs_grade_count = self.config_manager.get('grade_settings.rs_grade_count', 3)

            # 获取自动计算选项
            rs_auto_calc = self.config_manager.get('grade_settings.rs_auto_calc', True)

            # 移除1档特殊处理，统一显示具体数值范围

            if rs_auto_calc:
                # 自动计算模式：使用与判定设置页面相同的计算逻辑
                min_value = self.config_manager.get('grade_settings.rs_min', 0.5)
                max_value = self.config_manager.get('grade_settings.rs_max', 50.0)

                ranges = self._calculate_auto_ranges(min_value, max_value, rs_grade_count)
                display_text = self._format_ranges_text("Rs", ranges)
            else:
                # 手动模式：使用与判定设置页面相同的逻辑
                ranges = []

                if rs_grade_count >= 1:
                    grade1_max = self.config_manager.get('grade_settings.rs1_max', 17.0)
                    ranges.append((0.0, grade1_max))

                if rs_grade_count >= 2:
                    grade2_max = self.config_manager.get('grade_settings.rs2_max', 33.5)
                    ranges.append((grade1_max, grade2_max))

                if rs_grade_count >= 3:
                    grade3_max = self.config_manager.get('grade_settings.rs3_max', 50.0)
                    ranges.append((grade2_max, grade3_max))

                display_text = self._format_ranges_text("Rs", ranges)

            # 将多行文本转换为单行显示格式
            return self._convert_to_single_line_format(display_text)

        except Exception as e:
            logger.error(f"获取Rs档位范围失败: {e}")
            return ["Rs配置错误"]

    def _get_rct_grade_ranges_from_settings(self):
        """获取Rct档位范围配置（使用与判定设置页面完全相同的逻辑，固定3档）"""
        try:
            # 获取自动计算选项
            rct_auto_calc = self.config_manager.get('grade_settings.rct_auto_calc', True)

            if rct_auto_calc:
                # 自动计算模式：使用与判定设置页面相同的计算逻辑
                min_value = self.config_manager.get('grade_settings.rct_min', 5.0)
                max_value = self.config_manager.get('grade_settings.rct_max', 100.0)

                ranges = self._calculate_auto_ranges(min_value, max_value, 3)
                display_text = self._format_ranges_text("Rct", ranges)
            else:
                # 手动模式：使用与判定设置页面相同的逻辑
                grade1_max = self.config_manager.get('grade_settings.rct1_max', 35.0)
                grade2_max = self.config_manager.get('grade_settings.rct2_max', 70.0)
                grade3_max = self.config_manager.get('grade_settings.rct3_max', 100.0)

                ranges = [
                    (0.0, grade1_max),
                    (grade1_max, grade2_max),
                    (grade2_max, grade3_max)
                ]
                display_text = self._format_ranges_text("Rct", ranges)

            # 将多行文本转换为单行显示格式
            return self._convert_to_single_line_format(display_text)

        except Exception as e:
            logger.error(f"获取Rct档位范围失败: {e}")
            return ["Rct配置错误"]

    def _calculate_auto_ranges(self, min_value: float, max_value: float, grade_count: int) -> list:
        """自动计算档位范围（与判定设置页面完全相同的算法）"""
        try:
            ranges = []
            if grade_count <= 0:
                return ranges

            step = (max_value - min_value) / grade_count

            for i in range(grade_count):
                range_min = min_value + i * step
                range_max = min_value + (i + 1) * step
                ranges.append((range_min, range_max))

            return ranges

        except Exception as e:
            logger.error(f"自动计算档位范围失败: {e}")
            return []

    def _format_ranges_text(self, prefix: str, ranges: list) -> str:
        """格式化档位范围文本（与判定设置页面完全相同的格式）"""
        try:
            if not ranges:
                return f"{prefix}档位范围计算失败"

            lines = []
            for i, (min_val, max_val) in enumerate(ranges, 1):
                lines.append(f"{prefix}{i}档: {min_val:.3f} - {max_val:.3f} mΩ")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"格式化档位范围文本失败: {e}")
            return f"{prefix}档位范围显示错误"

    def _convert_to_single_line_format(self, multi_line_text: str) -> list:
        """将多行文本转换为单行显示格式（显示完整范围信息）"""
        try:
            lines = multi_line_text.strip().split('\n')
            single_line_ranges = []

            for line in lines:
                if ':' in line:
                    # 提取档位信息，转换格式
                    parts = line.split(':')
                    if len(parts) >= 2:
                        grade_part = parts[0].strip()  # 如 "Rs1档"
                        range_part = parts[1].strip()  # 如 "0.500 - 17.167 mΩ"

                        # 解析范围值
                        if ' - ' in range_part:
                            range_values = range_part.replace(' mΩ', '').split(' - ')
                            if len(range_values) == 2:
                                min_val = float(range_values[0])
                                max_val = float(range_values[1])

                                # 提取档位数字
                                grade_num = grade_part[-2]  # 提取档位数字

                                # 转换为主界面完整范围显示格式（显示上下限，保留3位小数）
                                single_line_ranges.append(f"{grade_num}档({min_val:.3f}-{max_val:.3f}mΩ)")

            return single_line_ranges if single_line_ranges else [multi_line_text]

        except Exception as e:
            logger.error(f"转换显示格式失败: {e}")
            return [multi_line_text]

    def _update_grade_range_display(self):
        """更新档位范围显示"""
        try:
            rs_ranges, rct_ranges = self._get_grade_ranges()

            # 更新Rs档位范围显示（简洁格式）
            rs_text = " | ".join(rs_ranges)
            self.rs_range_label.setText(rs_text)

            # 更新Rct档位范围显示（简洁格式）
            rct_text = " | ".join(rct_ranges)
            self.rct_range_label.setText(rct_text)

        except Exception as e:
            logger.error(f"更新档位范围显示失败: {e}")

    def _load_counter_statistics(self):
        """加载统计计数器数据"""
        try:

            # 从计数器管理器获取统计数据
            stats = self.counter_manager.get_statistics()

            # 更新统计数据
            self.total_count = stats['total_count']
            self.pass_count = stats['pass_count']
            self.fail_count = stats['fail_count']
            self.grade_distribution = stats['grade_distribution']

            # 更新档位分布表格
            self._update_grade_table_from_distribution()

            # 更新UI显示
            self._update_statistics_display()

            logger.info(f"✅ 统计计数器数据加载完成: 总数={self.total_count}, 合格={self.pass_count}, 不合格={self.fail_count}")

        except Exception as e:
            logger.error(f"❌ 加载统计计数器数据失败: {e}")
            # 如果加载失败，保持默认值0
            self.total_count = 0
            self.pass_count = 0
            self.fail_count = 0
            self.grade_distribution = {}
            self._update_statistics_display()

    def _update_grade_table_from_distribution(self):
        """从档位分布数据更新表格"""
        try:
            # 重置表格
            for row in range(self.grade_table.rowCount()):
                for col in range(self.grade_table.columnCount()):
                    item = self.grade_table.item(row, col)
                    if item:
                        item.setText("0")

            # 更新档位分布表格
            for grade_key, count in self.grade_distribution.items():
                if grade_key.startswith('Rs') and '-Rct' in grade_key:
                    # 解析档位信息，如 "Rs1-Rct2"
                    parts = grade_key.split('-')
                    if len(parts) == 2:
                        rs_part = parts[0].replace('Rs', '')
                        rct_part = parts[1].replace('Rct', '')

                        try:
                            rs_grade = int(rs_part)
                            rct_grade = int(rct_part)

                            if 1 <= rs_grade <= 3 and 1 <= rct_grade <= 3:
                                row_index = rs_grade - 1
                                col_index = rct_grade - 1

                                if (row_index < self.grade_table.rowCount() and
                                    col_index < self.grade_table.columnCount()):
                                    item = self.grade_table.item(row_index, col_index)
                                    if item:
                                        item.setText(str(count))
                        except ValueError:
                            continue

            logger.debug(f"档位分布表格更新完成: {len(self.grade_distribution)} 个档位组合")

        except Exception as e:
            logger.error(f"更新档位分布表格失败: {e}")

    def _update_statistics_display(self):
        """更新统计数据显示"""
        try:
            # 更新统计标签
            self.total_count_label.setText(str(self.total_count))
            self.pass_count_label.setText(str(self.pass_count))
            self.fail_count_label.setText(str(self.fail_count))

            # 计算良率
            if self.total_count > 0:
                yield_rate = (self.pass_count / self.total_count) * 100
                self.yield_rate_label.setText(f"{yield_rate:.1f}%")
            else:
                self.yield_rate_label.setText("0.0%")

            logger.debug(f"统计显示更新完成: 总数={self.total_count}, 良率={self.yield_rate_label.text()}")

        except Exception as e:
            logger.error(f"更新统计显示失败: {e}")

    def refresh_statistics(self):
        """🔧 公共方法：刷新统计数据（供外部调用）"""
        try:
            logger.debug("🔄 刷新统计数据...")
            self._load_counter_statistics()

        except Exception as e:
            logger.error(f"刷新统计数据失败: {e}")

    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QGroupBox#statisticsGroup {
                font-weight: bold;
                border: 2px solid #27ae60;
                border-radius: 5px;
                margin-top: 0.2ex;  /* 进一步压缩优化：从0.3ex减少到0.2ex */
                padding-top: 2px;   /* 进一步压缩优化：从3px减少到2px */
                background-color: white;
            }

            QGroupBox#statisticsGroup::title {
                subcontrol-origin: margin;
                left: 5px;          /* 进一步压缩优化：从6px减少到5px */
                padding: 0 3px 0 3px;  /* 进一步压缩优化：从4px减少到3px */
                color: #27ae60;
                font-size: 11pt;    /* 字体优化：从9pt增加到11pt */
                font-weight: bold;  /* 字体优化：加粗 */
            }

            QLabel {
                font-size: 13pt;    /* 字体优化：标签文字从11pt增加到13pt（+2pt） */
                font-weight: bold;  /* 字体优化：标签文字加粗 */
                color: #2c3e50;
            }

            QLabel#valueLabel {
                font-size: 14pt;    /* 字体优化：增大字体从12pt到14pt（+2pt） */
                font-weight: bold;  /* 显示优化：加粗显示 */
                color: #2c3e50;
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 2px;
                padding: 2px 5px;  /* 进一步压缩优化：从3px 6px减少到2px 5px */
                min-width: 55px;   /* 字体优化：增加最小宽度适应更大字体（从50px到55px） */
                text-align: center; /* 显示优化：居中对齐显示 */
            }

            QLabel#passLabel {
                font-size: 14pt;    /* 字体优化：增大字体从12pt到14pt（+2pt） */
                font-weight: bold;  /* 显示优化：加粗显示 */
                color: #27ae60;
                background-color: #d5f4e6;
                border: 1px solid #27ae60;
                border-radius: 2px;  /* 进一步压缩优化：从3px减少到2px */
                padding: 2px 5px;   /* 进一步压缩优化：从3px 6px减少到2px 5px */
                min-width: 55px;    /* 字体优化：增加最小宽度适应更大字体（从50px到55px） */
                text-align: center; /* 显示优化：居中对齐显示 */
            }

            QLabel#failLabel {
                font-size: 14pt;    /* 字体优化：增大字体从12pt到14pt（+2pt） */
                font-weight: bold;  /* 显示优化：加粗显示 */
                color: #e74c3c;
                background-color: #fadbd8;
                border: 1px solid #e74c3c;
                border-radius: 2px;  /* 进一步压缩优化：从3px减少到2px */
                padding: 2px 5px;   /* 进一步压缩优化：从3px 6px减少到2px 5px */
                min-width: 55px;    /* 字体优化：增加最小宽度适应更大字体（从50px到55px） */
                text-align: center; /* 显示优化：居中对齐显示 */
            }

            QLabel#yieldLabel {
                font-size: 14pt;    /* 字体优化：增大字体从12pt到14pt（+2pt） */
                font-weight: bold;  /* 显示优化：加粗显示 */
                color: #3498db;
                background-color: #ebf3fd;
                border: 1px solid #3498db;
                border-radius: 2px;  /* 进一步压缩优化：从3px减少到2px */
                padding: 2px 5px;   /* 进一步压缩优化：从3px 6px减少到2px 5px */
                min-width: 55px;    /* 字体优化：增加最小宽度适应更大字体（从50px到55px） */
                text-align: center; /* 显示优化：居中对齐显示 */
            }

            QLabel#subtitleLabel {
                font-size: 10pt;
                font-weight: bold;
                color: #34495e;
                margin-bottom: 2px;  /* 压缩优化：从5px减少到2px */
            }

            QTableWidget#gradeTable {
                gridline-color: #bdc3c7;
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 4px;  /* 压缩优化：从6px减少到4px */
                font-size: 10pt;     /* 进一步减小字体：12pt→10pt，确保完全显示 */
                font-weight: bold;   /* 显示优化：加粗显示 */
            }

            QTableWidget#gradeTable::item {
                padding: 2px;  /* 进一步压缩：3px→2px，最大化节省空间 */
                border: 1px solid #bdc3c7;
                font-size: 10pt;     /* 进一步减小字体：12pt→10pt，确保完全显示 */
                font-weight: bold;   /* 显示优化：加粗显示 */
                text-align: center;  /* 显示优化：居中对齐显示 */
            }

            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 1px;  /* 最大化压缩：2px→1px，节省更多空间 */
                border: none;
                font-weight: bold;
                font-size: 9pt;      /* 进一步减小表头字体：10pt→9pt，确保完全显示 */
            }

            QLabel#rangeValueLabel {
                font-size: 7pt;      /* 再次减小字体：8pt→7pt，给九宫格更多空间 */
                font-weight: bold;
                color: #2c3e50;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 2px;  /* 压缩优化：从3px减少到2px */
                padding: 1px 2px;    /* 进一步压缩padding：2px 3px→1px 2px */
                min-width: 120px;    /* 字体优化：增加最小宽度适应完整范围格式（从85px到120px） */
                max-height: 20px;    /* 减小最大高度：24px→20px，给九宫格更多空间 */
                word-wrap: break-word;  /* 启用自动换行 */
            }
        """)



    def _update_display(self):
        """更新显示"""
        try:
            # 更新统计数据
            self.total_count_label.setText(str(self.total_count))
            self.pass_count_label.setText(str(self.pass_count))
            self.fail_count_label.setText(str(self.fail_count))

            # 计算良率
            if self.total_count > 0:
                yield_rate = (self.pass_count / self.total_count) * 100
                self.yield_rate_label.setText(f"{yield_rate:.1f}%")
            else:
                self.yield_rate_label.setText("0.0%")

        except Exception as e:
            logger.error(f"更新显示失败: {e}")

    def clear_statistics(self):
        """清理统计数据"""
        try:
            # 修复使用计数器管理器清除统计数据
            self.counter_manager.clear_statistics()

            # 重置本地数据
            self.total_count = 0
            self.pass_count = 0
            self.fail_count = 0
            self.grade_distribution.clear()

            # 重置表格
            for row in range(self.grade_table.rowCount()):
                for col in range(self.grade_table.columnCount()):
                    item = self.grade_table.item(row, col)
                    if item:
                        item.setText("0")

            # 更新显示
            self._update_display()

            # 发送信号
            self.statistics_updated.emit(self.get_statistics())

            logger.info("统计数据已清理")

        except Exception as e:
            logger.error(f"清理统计数据失败: {e}")

    def add_test_result(self, is_pass: bool, rs_grade: Optional[int] = None, rct_grade: Optional[int] = None):
        """
        添加测试结果到统计

        Args:
            is_pass: 是否通过测试
            rs_grade: Rs档位 (整数: 1, 2, 3 或 None)
            rct_grade: Rct档位 (整数: 1, 2, 3 或 None)
        """
        try:
            
            # 修复只使用计数器管理器添加测试结果，避免重复计算
            self.counter_manager.add_test_result(is_pass, rs_grade, rct_grade)

            # 修复从计数器管理器重新加载统计数据，确保数据一致性
            stats = self.counter_manager.get_statistics()
            old_total = self.total_count
            self.total_count = stats['total_count']
            self.pass_count = stats['pass_count']
            self.fail_count = stats['fail_count']
            self.grade_distribution = stats['grade_distribution'].copy()

            # 修复添加统计变化日志

            # 更新档位分布表格显示
            self._update_grade_table_from_distribution()

            # 更新UI显示
            self._update_statistics_display()

            # 发送信号
            self.statistics_updated.emit(self.get_statistics())


        except Exception as e:
            logger.error(f"添加测试结果失败: {e}")

    def get_statistics(self) -> dict:
        """
        获取统计数据

        Returns:
            统计数据字典
        """
        yield_rate = (self.pass_count / self.total_count * 100) if self.total_count > 0 else 0.0

        return {
            'total_count': self.total_count,
            'pass_count': self.pass_count,
            'fail_count': self.fail_count,
            'yield_rate': yield_rate,
            'grade_distribution': self.grade_distribution.copy()
        }

    def load_settings(self):
        """重新加载设置"""
        # 重新初始化档位表格
        self._init_grade_table()
        # 更新档位范围显示
        self._update_grade_range_display()

    def update_grade_settings(self):
        """更新档位设置（外部调用接口）"""
        try:
            # 重新初始化档位表格
            self._init_grade_table()
            # 更新档位范围显示
            self._update_grade_range_display()
            logger.debug("档位设置已更新")
        except Exception as e:
            logger.error(f"更新档位设置失败: {e}")
