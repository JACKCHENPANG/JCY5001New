# -*- coding: utf-8 -*-
"""
参数配置页面
设置增益、平均次数、电池量程等参数

Author: Jack
Date: 2025-01-27
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, QSpinBox, QPushButton, QMessageBox,
    QDialog, QTextEdit, QDialogButtonBox, QListWidget, QListWidgetItem,
    QSplitter
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont
import logging

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager


class ParameterConfigWidget(QWidget):
    """参数配置页面组件"""

    # 信号定义
    settings_changed = pyqtSignal()  # 设置变更信号

    def __init__(self, config_manager: ConfigManager, parent=None, comm_manager=None):
        """
        初始化参数配置页面

        Args:
            config_manager: 配置管理器
            parent: 父窗口
            comm_manager: 通信管理器（用于回读功能）
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.comm_manager = comm_manager
        self._loading = False  # 防止加载时触发变更信号

        # 初始化界面
        self._init_ui()
        self._init_connections()
        self._apply_channel_styles()

        logger.debug("参数配置页面初始化完成")

    def _init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 创建测量参数组
        measurement_group = self._create_measurement_group()
        main_layout.addWidget(measurement_group)

        # 创建顶针寿命设置组
        probe_pin_group = self._create_probe_pin_group()
        main_layout.addWidget(probe_pin_group)

        # 减少弹性空间，确保内容优先显示
        main_layout.addStretch(1)

    def _create_measurement_group(self) -> QGroupBox:
        """创建测量参数组"""
        group = QGroupBox("测量参数")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QGridLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # 增益设置
        layout.addWidget(QLabel("增益设置:"), 0, 0)
        self.gain_combo = QComboBox()
        self.gain_combo.addItems(["1倍", "4倍", "16倍", "自动"])
        self.gain_combo.setCurrentText("1倍")  # 设置默认值为1倍
        self.gain_combo.setToolTip("设置测量增益\n• 1倍: 适用于高阻抗电池（默认推荐）\n• 4倍: 适用于中等阻抗电池\n• 16倍: 适用于低阻抗电池\n• 自动: 系统自动选择最佳增益（暂不实现）")
        layout.addWidget(self.gain_combo, 0, 1)

        # 增益回读按键（灰化禁用）
        self.gain_readback_btn = QPushButton("回读")
        self.gain_readback_btn.setMaximumWidth(60)
        self.gain_readback_btn.setToolTip("回读设备当前增益设置（功能暂时禁用）")
        self.gain_readback_btn.setEnabled(False)  # 设置为禁用状态
        self.gain_readback_btn.clicked.connect(self._on_gain_readback_clicked)
        layout.addWidget(self.gain_readback_btn, 0, 2)

        # 平均次数
        layout.addWidget(QLabel("平均次数:"), 1, 0)
        self.average_count_spin = QSpinBox()
        self.average_count_spin.setRange(1, 100)
        self.average_count_spin.setValue(5)
        self.average_count_spin.setSuffix(" 次")
        self.average_count_spin.setToolTip("设置测量平均次数\n• 次数越多，测量精度越高，但速度越慢\n• 建议范围: 3-10次")
        layout.addWidget(self.average_count_spin, 1, 1)

        # 平均次数回读按键（灰化禁用）
        self.average_readback_btn = QPushButton("回读")
        self.average_readback_btn.setMaximumWidth(60)
        self.average_readback_btn.setToolTip("回读设备当前平均次数设置（功能暂时禁用）")
        self.average_readback_btn.setEnabled(False)  # 设置为禁用状态
        self.average_readback_btn.clicked.connect(self._on_average_readback_clicked)
        layout.addWidget(self.average_readback_btn, 1, 2)

        # 电阻档位
        layout.addWidget(QLabel("电阻档位:"), 2, 0)
        self.resistance_range_combo = QComboBox()
        self.resistance_range_combo.addItems(["1mΩ以内", "10mΩ以内", "100mΩ以内"])
        self.resistance_range_combo.setToolTip("设置采样电阻档位\n• 1mΩ以内: 适用于极低阻抗电池 (0-1mΩ)\n• 10mΩ以内: 适用于低阻抗电池 (1-10mΩ)\n• 100mΩ以内: 适用于中高阻抗电池 (10-100mΩ)")
        layout.addWidget(self.resistance_range_combo, 2, 1)

        # 电阻档位回读按键（灰化禁用）
        self.resistance_readback_btn = QPushButton("回读")
        self.resistance_readback_btn.setMaximumWidth(60)
        self.resistance_readback_btn.setToolTip("回读设备当前电阻档位设置（功能暂时禁用）")
        self.resistance_readback_btn.setEnabled(False)  # 设置为禁用状态
        self.resistance_readback_btn.clicked.connect(self._on_resistance_readback_clicked)
        layout.addWidget(self.resistance_readback_btn, 2, 2)

        return group



    def _create_probe_pin_group(self) -> QGroupBox:
        """创建顶针寿命设置组"""
        group = QGroupBox("顶针寿命设置")
        group.setFont(QFont("", 10, QFont.Bold))

        # 设置组的最小高度，确保有足够空间显示通道计数
        group.setMinimumHeight(280)

        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # 创建寿命参数设置区域
        self._create_lifetime_settings_area(layout)

        # 创建通道测试次数显示区域
        self._create_channel_counts_area(layout)

        return group

    def _create_lifetime_settings_area(self, layout):
        """创建寿命参数设置区域"""
        settings_layout = QGridLayout()
        settings_layout.setSpacing(15)

        # 警告阈值设置
        settings_layout.addWidget(QLabel("警告阈值:"), 0, 0)
        self.warning_threshold_spin = QSpinBox()
        self.warning_threshold_spin.setRange(100, 50000)
        self.warning_threshold_spin.setValue(1000)
        self.warning_threshold_spin.setSuffix(" 次")
        self.warning_threshold_spin.setToolTip("设置顶针寿命警告阈值\n• 超过此值时显示警告\n• 建议范围: 500-2000次")
        settings_layout.addWidget(self.warning_threshold_spin, 0, 1)

        # 最大寿命设置
        settings_layout.addWidget(QLabel("最大寿命:"), 0, 2)
        self.max_lifetime_spin = QSpinBox()
        self.max_lifetime_spin.setRange(1000, 100000)
        self.max_lifetime_spin.setValue(10000)
        self.max_lifetime_spin.setSuffix(" 次")
        self.max_lifetime_spin.setToolTip("设置顶针最大使用寿命\n• 超过此值时需要更换顶针\n• 建议范围: 5000-20000次")
        settings_layout.addWidget(self.max_lifetime_spin, 0, 3)

        # 全部重置按钮
        self.reset_all_button = QPushButton("重置所有通道计数")
        self.reset_all_button.setObjectName("resetAllButton")
        self.reset_all_button.clicked.connect(self._on_reset_all_clicked)
        settings_layout.addWidget(self.reset_all_button, 1, 0, 1, 4)

        layout.addLayout(settings_layout)

    def _create_channel_counts_area(self, layout):
        """创建通道测试次数显示区域"""
        # 创建分组框
        counts_group = QGroupBox("通道测试计数状态")
        counts_group.setObjectName("channelCountsGroup")
        counts_group.setMinimumHeight(120)  # 设置最小高度确保显示完整
        layout.addWidget(counts_group)

        # 创建网格布局 - 2行4列显示8个通道
        grid_layout = QGridLayout(counts_group)
        grid_layout.setContentsMargins(12, 18, 12, 12)
        grid_layout.setSpacing(8)

        # 设置列的拉伸因子，使布局更均匀
        for col in range(12):  # 4个通道 * 3列 = 12列
            grid_layout.setColumnStretch(col, 1)

        # 创建8个通道的状态显示
        self.channel_widgets = {}
        for i in range(8):
            channel_num = i + 1
            row = i // 4  # 0或1
            col = (i % 4) * 3  # 0, 3, 6, 9
            self._create_channel_widget(grid_layout, channel_num, row, col)

    def _create_channel_widget(self, layout, channel_num: int, row: int, col: int):
        """
        创建单个通道的状态显示组件

        Args:
            layout: 父布局
            channel_num: 通道号 (1-8)
            row: 行位置
            col: 列位置
        """
        # 通道标签
        channel_label = QLabel(f"通道 {channel_num}")
        channel_label.setObjectName("channelLabel")
        layout.addWidget(channel_label, row, col)

        # 测试计数显示
        count_label = QLabel("0")
        count_label.setObjectName("countLabel")
        layout.addWidget(count_label, row, col + 1)

        # 重置按钮
        reset_button = QPushButton("重置")
        reset_button.setObjectName("resetButton")
        reset_button.clicked.connect(lambda: self._on_reset_channel_clicked(channel_num))
        layout.addWidget(reset_button, row, col + 2)

        # 保存组件引用
        self.channel_widgets[channel_num] = {
            'count_label': count_label,
            'reset_button': reset_button
        }

    def _init_connections(self):
        """初始化信号连接"""
        # 连接所有控件的变更信号
        self.gain_combo.currentTextChanged.connect(self._on_setting_changed)
        self.average_count_spin.valueChanged.connect(self._on_setting_changed)
        self.resistance_range_combo.currentTextChanged.connect(self._on_setting_changed)
        self.warning_threshold_spin.valueChanged.connect(self._on_setting_changed)
        self.max_lifetime_spin.valueChanged.connect(self._on_setting_changed)

    def _on_setting_changed(self):
        """设置变更处理"""
        if not self._loading:
            self.settings_changed.emit()

    def _on_reset_channel_clicked(self, channel_num: int):
        """通道重置按钮点击处理"""
        try:
            reply = QMessageBox.question(
                self, "确认重置",
                f"确定要重置通道{channel_num}的测试计数吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 重置配置中的计数
                self.config_manager.set(f'test_count.channel_{channel_num}', 0)
                self.config_manager.save_config()

                # 更新显示
                self.channel_widgets[channel_num]['count_label'].setText("0")
                self._update_count_color(channel_num, 0)

                logger.info(f"通道{channel_num}测试计数已重置")

        except Exception as e:
            logger.error(f"重置通道{channel_num}计数失败: {e}")
            QMessageBox.critical(self, "错误", f"重置失败: {e}")

    def _on_reset_all_clicked(self):
        """全部重置按钮点击处理"""
        try:
            reply = QMessageBox.question(
                self, "确认重置",
                "确定要重置所有通道的测试计数吗？此操作不可撤销！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 重置所有通道的计数
                for channel_num in range(1, 9):
                    self.config_manager.set(f'test_count.channel_{channel_num}', 0)
                    self.channel_widgets[channel_num]['count_label'].setText("0")
                    self._update_count_color(channel_num, 0)

                self.config_manager.save_config()
                logger.info("所有通道测试计数已重置")

        except Exception as e:
            logger.error(f"重置所有通道计数失败: {e}")
            QMessageBox.critical(self, "错误", f"重置失败: {e}")

    def _update_count_color(self, channel_num: int, count: int):
        """
        根据测试计数更新颜色

        Args:
            channel_num: 通道号
            count: 测试计数
        """
        try:
            warning_threshold = self.warning_threshold_spin.value()
            max_lifetime = self.max_lifetime_spin.value()

            count_label = self.channel_widgets[channel_num]['count_label']

            if count >= max_lifetime:
                # 超过最大寿命 - 红色
                count_label.setStyleSheet("""
                    QLabel#countLabel {
                        color: white;
                        background-color: #e74c3c;
                        border: 1px solid #c0392b;
                        border-radius: 4px;
                        padding: 4px 8px;
                        min-width: 50px;
                        text-align: center;
                        font-size: 12pt;
                        font-weight: bold;
                    }
                """)
            elif count >= warning_threshold:
                # 超过警告阈值 - 橙色
                count_label.setStyleSheet("""
                    QLabel#countLabel {
                        color: white;
                        background-color: #f39c12;
                        border: 1px solid #e67e22;
                        border-radius: 4px;
                        padding: 4px 8px;
                        min-width: 50px;
                        text-align: center;
                        font-size: 12pt;
                        font-weight: bold;
                    }
                """)
            else:
                # 正常 - 绿色
                count_label.setStyleSheet("""
                    QLabel#countLabel {
                        color: #27ae60;
                        background-color: #ecf0f1;
                        border: 1px solid #bdc3c7;
                        border-radius: 4px;
                        padding: 4px 8px;
                        min-width: 50px;
                        text-align: center;
                        font-size: 12pt;
                        font-weight: bold;
                    }
                """)

        except Exception as e:
            logger.error(f"更新通道{channel_num}计数颜色失败: {e}")

    def load_settings(self):
        """加载设置"""
        self._loading = True
        try:
            # 加载测量参数（使用正确的配置键名）
            gain = self.config_manager.get('test_params.gain', '1')  # 默认值改为1倍
            # 转换为界面显示的格式
            gain_map = {'auto': '自动', '1': '1倍', '4': '4倍', '16': '16倍'}
            display_gain = gain_map.get(gain, '1倍')  # 默认显示改为1倍
            self.gain_combo.setCurrentText(display_gain)

            average_count = self.config_manager.get('test_params.average_times', 1)
            self.average_count_spin.setValue(average_count)

            # 加载电阻档位（转换为界面显示格式）
            resistance_range = self.config_manager.get('test_params.resistance_range', '10R')
            # 转换为界面显示的格式
            range_display_map = {
                '1R': '1mΩ以内',
                '5R': '10mΩ以内',
                '10R': '100mΩ以内'
            }
            display_range = range_display_map.get(resistance_range, '100mΩ以内')
            self.resistance_range_combo.setCurrentText(display_range)

            # 加载顶针寿命设置
            warning_threshold = self.config_manager.get('probe_pin.warning_threshold', 1000)
            self.warning_threshold_spin.setValue(warning_threshold)

            max_lifetime = self.config_manager.get('probe_pin.max_lifetime', 10000)
            self.max_lifetime_spin.setValue(max_lifetime)

            # 加载各通道的测试计数
            for channel_num in range(1, 9):
                count = self.config_manager.get(f'test_count.channel_{channel_num}', 0)
                self.channel_widgets[channel_num]['count_label'].setText(str(count))

                # 根据计数设置颜色
                self._update_count_color(channel_num, count)

            logger.debug("参数配置设置加载完成")

        except Exception as e:
            logger.error(f"加载参数配置设置失败: {e}")
        finally:
            self._loading = False

    def apply_settings(self):
        """应用设置"""
        try:
            # 保存测量参数（转换为配置格式）
            gain_text = self.gain_combo.currentText()
            gain_map = {'自动': 'auto', '1倍': '1', '4倍': '4', '16倍': '16'}
            gain_value = gain_map.get(gain_text, 'auto')
            self.config_manager.set('test_params.gain', gain_value)

            self.config_manager.set('test_params.average_times', self.average_count_spin.value())

            # 修复电阻档位映射：根据用户要求更正界面到配置的映射关系
            range_text = self.resistance_range_combo.currentText()
            range_config_map = {
                '1mΩ以内': '1R',   # 1mΩ以内 → 1R档位 → 0x00
                '10mΩ以内': '5R',  # 10mΩ以内 → 5R档位 → 0x01
                '100mΩ以内': '10R' # 100mΩ以内 → 10R档位 → 0x02
            }
            range_value = range_config_map.get(range_text, '10R')
            self.config_manager.set('test_params.resistance_range', range_value)

            # 保存顶针寿命设置
            self.config_manager.set('probe_pin.warning_threshold', self.warning_threshold_spin.value())
            self.config_manager.set('probe_pin.max_lifetime', self.max_lifetime_spin.value())

            logger.info("参数配置设置应用成功")

        except Exception as e:
            logger.error(f"应用参数配置设置失败: {e}")
            raise

    def validate_settings(self) -> bool:
        """
        验证设置

        Returns:
            是否验证通过
        """
        try:
            # 验证平均次数
            if self.average_count_spin.value() <= 0:
                return False

            # 验证顶针寿命设置
            warning_threshold = self.warning_threshold_spin.value()
            max_lifetime = self.max_lifetime_spin.value()

            if warning_threshold >= max_lifetime:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "设置错误", "警告阈值不能大于或等于最大寿命！")
                return False

            return True

        except Exception as e:
            logger.error(f"验证参数配置设置失败: {e}")
            return False

    def reset_to_defaults(self):
        """重置为默认值"""
        self._loading = True
        try:
            self.gain_combo.setCurrentText('自动')
            self.average_count_spin.setValue(5)
            self.resistance_range_combo.setCurrentText('100mΩ以内')

            # 重置顶针寿命设置
            self.warning_threshold_spin.setValue(1000)
            self.max_lifetime_spin.setValue(10000)

            # 重置通道测试计数显示（不重置实际配置）
            for channel_num in range(1, 9):
                count = self.config_manager.get(f'test_count.channel_{channel_num}', 0)
                self.channel_widgets[channel_num]['count_label'].setText(str(count))
                self._update_count_color(channel_num, count)

            logger.info("参数配置已重置为默认值")

        finally:
            self._loading = False
            self.settings_changed.emit()

    def refresh_channel_counts(self):
        """刷新通道测试计数显示"""
        try:
            for channel_num in range(1, 9):
                count = self.config_manager.get(f'test_count.channel_{channel_num}', 0)
                self.channel_widgets[channel_num]['count_label'].setText(str(count))
                self._update_count_color(channel_num, count)

        except Exception as e:
            logger.error(f"刷新通道测试计数显示失败: {e}")

    def _apply_channel_styles(self):
        """应用通道计数显示样式"""
        self.setStyleSheet("""
            QGroupBox#channelCountsGroup {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: white;
            }

            QGroupBox#channelCountsGroup::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #3498db;
                font-size: 12pt;
            }

            QLabel#channelLabel {
                font-size: 10pt;
                font-weight: bold;
                color: #2c3e50;
                min-width: 60px;
            }

            QPushButton#resetButton {
                background-color: #f39c12;
                border: none;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 9pt;
                min-width: 50px;
            }

            QPushButton#resetButton:hover {
                background-color: #e67e22;
            }

            QPushButton#resetAllButton {
                background-color: #e74c3c;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11pt;
            }

            QPushButton#resetAllButton:hover {
                background-color: #c0392b;
            }

            /* 禁用的回读按键样式 */
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
                border: 1px solid #95a5a6;
                border-radius: 4px;
                font-weight: normal;
            }
        """)

    def on_tab_activated(self):
        """选项卡激活时调用"""
        # 刷新通道计数显示
        self.refresh_channel_counts()

    def _on_gain_readback_clicked(self):
        """增益回读按键点击处理（群发读取所有8个通道）"""
        try:
            if not self.comm_manager or not self.comm_manager.is_connected:
                QMessageBox.warning(self, "警告", "设备未连接，无法进行回读操作")
                return

            logger.info("开始群发回读所有通道增益设置...")

            # 使用群发命令读取所有8个通道的增益设置
            gain_values = self.comm_manager.read_all_gains()

            if gain_values:
                # 构建显示文本
                result_text = "所有通道增益回读结果：\n\n"

                for i, gain_value in enumerate(gain_values):
                    channel_num = i + 1
                    if gain_value is not None:
                        result_text += f"通道{channel_num}: {gain_value}\n"
                    else:
                        result_text += f"通道{channel_num}: 读取失败\n"

                result_text += "\n注意：这是调试用的原始数值，未经解析处理"

                # 显示结果
                QMessageBox.information(self, "增益回读结果", result_text)
                logger.info(f"增益群发回读成功: {gain_values}")
            else:
                QMessageBox.warning(self, "回读失败", "增益群发回读失败，请检查设备连接")
                logger.warning("增益群发回读失败")

        except Exception as e:
            logger.error(f"增益回读异常: {e}")
            QMessageBox.critical(self, "错误", f"增益回读异常: {e}")

    def _on_average_readback_clicked(self):
        """平均次数回读按键点击处理（全局设置，适用于所有通道）"""
        try:
            if not self.comm_manager or not self.comm_manager.is_connected:
                QMessageBox.warning(self, "警告", "设备未连接，无法进行回读操作")
                return

            logger.info("开始回读平均次数设置...")

            # 读取平均次数设置（全局设置）
            average_value = self.comm_manager.read_average_times()

            if average_value is not None:
                # 构建显示文本
                result_text = "平均次数回读结果：\n\n"
                result_text += f"全局设置值: {average_value}\n"
                result_text += "适用于所有8个通道：\n"

                for i in range(8):
                    channel_num = i + 1
                    result_text += f"通道{channel_num}: {average_value}\n"

                result_text += "\n注意：这是调试用的原始数值，未经解析处理"

                # 显示结果
                QMessageBox.information(self, "平均次数回读结果", result_text)
                logger.info(f"平均次数回读成功: {average_value}")
            else:
                QMessageBox.warning(self, "回读失败", "平均次数回读失败，请检查设备连接")
                logger.warning("平均次数回读失败")

        except Exception as e:
            logger.error(f"平均次数回读异常: {e}")
            QMessageBox.critical(self, "错误", f"平均次数回读异常: {e}")

    def _on_resistance_readback_clicked(self):
        """电阻档位回读按键点击处理（群发读取所有8个通道）"""
        try:
            if not self.comm_manager or not self.comm_manager.is_connected:
                QMessageBox.warning(self, "警告", "设备未连接，无法进行回读操作")
                return

            logger.info("开始群发回读所有通道电阻档位设置...")

            # 修正使用正确的方法名读取所有8个通道的电阻档位设置
            resistance_values = self.comm_manager.read_resistance_range_broadcast()

            if resistance_values:
                # 构建显示文本
                result_text = "所有通道电阻档位回读结果：\n\n"

                for i, resistance_value in enumerate(resistance_values):
                    channel_num = i + 1
                    if resistance_value is not None:
                        result_text += f"通道{channel_num}: {resistance_value}\n"
                    else:
                        result_text += f"通道{channel_num}: 读取失败\n"

                result_text += "\n注意：这是调试用的原始数值，未经解析处理"

                # 显示结果
                QMessageBox.information(self, "电阻档位回读结果", result_text)
                logger.info(f"电阻档位群发回读成功: {resistance_values}")
            else:
                QMessageBox.warning(self, "回读失败", "电阻档位群发回读失败，请检查设备连接")
                logger.warning("电阻档位群发回读失败")

        except Exception as e:
            logger.error(f"电阻档位回读异常: {e}")
            QMessageBox.critical(self, "错误", f"电阻档位回读异常: {e}")





