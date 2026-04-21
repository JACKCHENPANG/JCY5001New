# -*- coding: utf-8 -*-
"""
产品信息页面
设置批次号、操作员、电池类型等产品信息
移除阻抗标准相关设置项

Author: Jack
Date: 2025-01-27
Modified: 2025-01-28 - 移除阻抗标准设置
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, QDoubleSpinBox,
    QTextEdit, QPushButton, QDateEdit, QSpinBox, QLineEdit
)
from PyQt5.QtCore import pyqtSignal, QDate
from PyQt5.QtGui import QFont
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager
from utils.user_permission_manager import permission_manager
from ui.widgets.safe_line_edit import SafeLineEdit


class ProductInfoWidget(QWidget):
    """产品信息页面组件"""

    # 信号定义
    settings_changed = pyqtSignal()  # 设置变更信号

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        初始化产品信息页面

        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self._loading = False  # 防止加载时触发变更信号

        # 初始化界面
        self._init_ui()
        self._init_connections()

        # 连接权限管理器信号
        permission_manager.role_changed.connect(self._on_role_changed)

        # 初始化权限状态
        self._update_permission_state()

        logger.debug("产品信息页面初始化完成")

    def _init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 创建批次信息组
        batch_group = self._create_batch_group()
        main_layout.addWidget(batch_group)

        # 创建电池信息组
        battery_group = self._create_battery_group()
        main_layout.addWidget(battery_group)

        # 添加弹性空间
        main_layout.addStretch()

    def _create_batch_group(self) -> QGroupBox:
        """创建批次信息组"""
        group = QGroupBox("批次信息")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QGridLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 批次号
        layout.addWidget(QLabel("批次号:"), 0, 0)
        self.batch_number_edit = SafeLineEdit()
        self.batch_number_edit.setPlaceholderText("例如: BATCH-20250127-001")
        self.batch_number_edit.setToolTip("设置当前批次号\n• 用于标识测试批次\n• 建议格式: BATCH-YYYYMMDD-XXX")
        layout.addWidget(self.batch_number_edit, 0, 1)

        # 自动生成批次号按钮
        self.auto_batch_button = QPushButton("自动生成")
        self.auto_batch_button.setMaximumWidth(80)
        self.auto_batch_button.setToolTip("根据当前日期自动生成批次号")
        layout.addWidget(self.auto_batch_button, 0, 2)

        # 操作员
        layout.addWidget(QLabel("操作员:"), 1, 0)
        self.operator_edit = SafeLineEdit()
        self.operator_edit.setPlaceholderText("输入操作员姓名")
        self.operator_edit.setToolTip("设置当前操作员姓名")
        layout.addWidget(self.operator_edit, 1, 1, 1, 2)

        # 生产日期
        layout.addWidget(QLabel("生产日期:"), 2, 0)
        self.production_date = QDateEdit()
        self.production_date.setDate(QDate.currentDate())
        self.production_date.setCalendarPopup(True)
        self.production_date.setToolTip("设置产品生产日期\n• 自动跟随当前系统日期")
        layout.addWidget(self.production_date, 2, 1, 1, 1)

        # 添加"今天"按钮
        self.today_button = QPushButton("今天")
        self.today_button.setMaximumWidth(60)
        self.today_button.setToolTip("设置为当前日期")
        layout.addWidget(self.today_button, 2, 2)

        # 备注
        layout.addWidget(QLabel("备注:"), 3, 0)
        self.remarks_edit = QTextEdit()
        self.remarks_edit.setMaximumHeight(60)
        self.remarks_edit.setPlaceholderText("输入批次备注信息...")
        self.remarks_edit.setToolTip("输入批次相关的备注信息")
        layout.addWidget(self.remarks_edit, 3, 1, 1, 2)

        return group

    def _create_battery_group(self) -> QGroupBox:
        """创建电池信息组"""
        group = QGroupBox("电池信息")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QGridLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 电池类型
        layout.addWidget(QLabel("电池类型:"), 0, 0)
        self.battery_type_combo = QComboBox()
        self.battery_type_combo.addItems([
            "磷酸铁锂", "三元锂", "钛酸锂", "锰酸锂", "钴酸锂", "其他"
        ])
        self.battery_type_combo.setToolTip("选择电池化学类型")
        layout.addWidget(self.battery_type_combo, 0, 1)

        # 电池规格
        layout.addWidget(QLabel("电池规格:"), 1, 0)
        self.battery_spec_combo = QComboBox()
        self.battery_spec_combo.setEditable(True)
        self.battery_spec_combo.addItems([
            "18650", "21700", "26650", "32650", "方形", "软包", "其他"
        ])
        self.battery_spec_combo.setToolTip("选择或输入电池规格型号")
        layout.addWidget(self.battery_spec_combo, 1, 1)

        # 标准电压
        layout.addWidget(QLabel("标准电压:"), 2, 0)
        self.standard_voltage_spin = QDoubleSpinBox()
        self.standard_voltage_spin.setRange(0.1, 50.0)
        self.standard_voltage_spin.setValue(3.2)
        self.standard_voltage_spin.setDecimals(2)
        self.standard_voltage_spin.setSuffix(" V")
        self.standard_voltage_spin.setToolTip("设置电池标准电压\n• 磷酸铁锂: 3.2V\n• 三元锂: 3.7V")
        layout.addWidget(self.standard_voltage_spin, 2, 1)

        # 容量（带单位选择）
        layout.addWidget(QLabel("标准容量:"), 3, 0)

        # 创建容量输入和单位选择的水平布局
        capacity_layout = QHBoxLayout()

        self.capacity_spin = QSpinBox()
        self.capacity_spin.setRange(1, 50000)
        self.capacity_spin.setValue(3000)
        self.capacity_spin.setToolTip("设置电池标准容量")
        capacity_layout.addWidget(self.capacity_spin)

        # 单位选择下拉菜单
        self.capacity_unit_combo = QComboBox()
        self.capacity_unit_combo.addItems(["mAh", "Ah"])
        self.capacity_unit_combo.setCurrentText("mAh")
        self.capacity_unit_combo.setToolTip("选择容量单位\nmAh: 毫安时\nAh: 安时")
        self.capacity_unit_combo.currentTextChanged.connect(self._on_capacity_unit_changed)
        capacity_layout.addWidget(self.capacity_unit_combo)

        # 创建容器widget
        capacity_widget = QWidget()
        capacity_widget.setLayout(capacity_layout)
        layout.addWidget(capacity_widget, 3, 1)

        # 新增制造商
        layout.addWidget(QLabel("制造商:"), 4, 0)
        self.manufacturer_edit = QLineEdit()
        self.manufacturer_edit.setPlaceholderText("请输入电池制造商名称")
        self.manufacturer_edit.setToolTip("输入电池制造商名称，用于数据追溯和检索")
        layout.addWidget(self.manufacturer_edit, 4, 1)

        return group

    def _init_connections(self):
        """初始化信号连接"""
        # 批次信息变更
        self.batch_number_edit.textChanged.connect(self._on_setting_changed)
        self.operator_edit.textChanged.connect(self._on_setting_changed)
        self.production_date.dateChanged.connect(self._on_setting_changed)
        self.remarks_edit.textChanged.connect(self._on_setting_changed)

        # 电池信息变更
        self.battery_type_combo.currentTextChanged.connect(self._on_battery_type_changed)
        self.battery_spec_combo.currentTextChanged.connect(self._on_setting_changed)
        self.standard_voltage_spin.valueChanged.connect(self._on_setting_changed)
        self.capacity_spin.valueChanged.connect(self._on_setting_changed)
        self.capacity_unit_combo.currentTextChanged.connect(self._on_setting_changed)
        self.manufacturer_edit.textChanged.connect(self._on_setting_changed)

        # 按钮点击
        self.auto_batch_button.clicked.connect(self._generate_batch_number)
        self.today_button.clicked.connect(self._set_today_date)

    def _on_battery_type_changed(self, battery_type: str):
        """电池类型变更处理"""
        # 根据电池类型自动设置标准电压
        voltage_map = {
            "磷酸铁锂": 3.2,
            "三元锂": 3.7,
            "钛酸锂": 2.4,
            "锰酸锂": 3.7,
            "钴酸锂": 3.7
        }

        if battery_type in voltage_map and not self._loading:
            self.standard_voltage_spin.setValue(voltage_map[battery_type])

        self._on_setting_changed()

    def _on_capacity_unit_changed(self, unit: str):
        """容量单位变更处理"""
        if self._loading:
            return

        current_value = self.capacity_spin.value()

        # 单位转换
        if unit == "Ah":
            # mAh转Ah：除以1000
            if self.capacity_unit_combo.currentText() != "Ah":  # 避免重复转换
                new_value = current_value / 1000.0
                self.capacity_spin.setRange(1, 50)  # Ah范围
                self.capacity_spin.setValue(int(new_value))
                self.capacity_spin.setSuffix("")  # 清除后缀，由下拉菜单显示
        else:  # mAh
            # Ah转mAh：乘以1000
            if self.capacity_unit_combo.currentText() != "mAh":  # 避免重复转换
                new_value = current_value * 1000
                self.capacity_spin.setRange(1, 50000)  # mAh范围
                self.capacity_spin.setValue(int(new_value))
                self.capacity_spin.setSuffix("")  # 清除后缀，由下拉菜单显示

        self._on_setting_changed()

    def _generate_batch_number(self):
        """生成批次号"""
        current_date = datetime.now()
        batch_number = f"BATCH-{current_date.strftime('%Y%m%d')}-001"
        self.batch_number_edit.setText(batch_number)

    def _set_today_date(self):
        """设置为今天日期"""
        self.production_date.setDate(QDate.currentDate())

    def _on_setting_changed(self):
        """设置变更处理"""
        if not self._loading:
            self.settings_changed.emit()

    def _on_role_changed(self, role: str):
        """用户角色变更处理"""
        self._update_permission_state()

    def _update_permission_state(self):
        """更新权限状态"""
        # 获取当前权限状态
        can_edit_batch = permission_manager.can_edit_batch_info()
        can_edit_product = permission_manager.can_edit_product_info()
        is_admin = permission_manager.is_administrator()

        logger.debug(f"权限状态更新 - 管理员: {is_admin}, 可编辑批次: {can_edit_batch}, 可编辑产品: {can_edit_product}")

        # 批次信息：所有用户都可以编辑
        self.batch_number_edit.setReadOnly(not can_edit_batch)
        self.operator_edit.setReadOnly(not can_edit_batch)
        self.production_date.setReadOnly(not can_edit_batch)
        self.remarks_edit.setReadOnly(not can_edit_batch)
        self.auto_batch_button.setEnabled(can_edit_batch)
        self.today_button.setEnabled(can_edit_batch)

        # 产品信息：只有管理员可以编辑
        self.battery_type_combo.setEnabled(can_edit_product)
        self.battery_spec_combo.setEnabled(can_edit_product)
        self.standard_voltage_spin.setReadOnly(not can_edit_product)
        self.capacity_spin.setReadOnly(not can_edit_product)
        self.capacity_unit_combo.setEnabled(can_edit_product)

        # 更新样式以显示只读状态
        readonly_style = "background-color: #f0f0f0; color: #666;"
        normal_style = ""

        # 应用样式
        if not can_edit_product:
            self.battery_type_combo.setStyleSheet(readonly_style)
            self.battery_spec_combo.setStyleSheet(readonly_style)
            self.standard_voltage_spin.setStyleSheet(readonly_style)
            self.capacity_spin.setStyleSheet(readonly_style)
            self.capacity_unit_combo.setStyleSheet(readonly_style)
        else:
            self.battery_type_combo.setStyleSheet(normal_style)
            self.battery_spec_combo.setStyleSheet(normal_style)
            self.standard_voltage_spin.setStyleSheet(normal_style)
            self.capacity_spin.setStyleSheet(normal_style)
            self.capacity_unit_combo.setStyleSheet(normal_style)

        logger.debug(f"电池类型控件启用状态: {self.battery_type_combo.isEnabled()}")
        logger.debug(f"标准电压控件只读状态: {self.standard_voltage_spin.isReadOnly()}")

    def load_settings(self):
        """加载设置"""
        self._loading = True
        try:
            # 加载批次信息（优先从batch_info加载，如果没有则从product加载）
            batch_number = self.config_manager.get('batch_info.batch_number',
                                                 self.config_manager.get('product.batch_number', ''))
            self.batch_number_edit.setText(batch_number)

            operator = self.config_manager.get('batch_info.operator',
                                             self.config_manager.get('product.operator', ''))
            self.operator_edit.setText(operator)

            # 生产日期：如果配置中没有或者是今天之前的日期，则自动设置为当前日期
            production_date_str = self.config_manager.get('product.production_date', '')
            if production_date_str:
                saved_date = QDate.fromString(production_date_str)
                # 如果保存的日期有效且不是今天之前的日期，则使用保存的日期
                if saved_date.isValid() and saved_date >= QDate.currentDate():
                    self.production_date.setDate(saved_date)
                else:
                    # 否则使用当前日期
                    self.production_date.setDate(QDate.currentDate())
            else:
                # 如果没有保存的日期，使用当前日期
                self.production_date.setDate(QDate.currentDate())

            remarks = self.config_manager.get('product.remarks', '')
            self.remarks_edit.setPlainText(remarks)

            # 加载电池信息
            battery_type = self.config_manager.get('product.battery_type', '磷酸铁锂')
            self.battery_type_combo.setCurrentText(battery_type)

            battery_spec = self.config_manager.get('product.battery_spec', '21700')
            self.battery_spec_combo.setCurrentText(battery_spec)

            standard_voltage = self.config_manager.get('product.standard_voltage', 3.2)
            self.standard_voltage_spin.setValue(standard_voltage)

            capacity = self.config_manager.get('product.capacity', 3000)
            self.capacity_spin.setValue(capacity)

            # 加载容量单位
            capacity_unit = self.config_manager.get('product.capacity_unit', 'mAh')
            self.capacity_unit_combo.setCurrentText(capacity_unit)

            # 新增加载制造商
            manufacturer = self.config_manager.get('product.manufacturer', '')
            self.manufacturer_edit.setText(manufacturer)

            logger.debug("产品信息设置加载完成")

        except Exception as e:
            logger.error(f"加载产品信息设置失败: {e}")
        finally:
            self._loading = False
            # 重新应用权限控制状态
            self._update_permission_state()

    def apply_settings(self):
        """应用设置"""
        try:
            # 保存批次信息（同时保存到batch_info和product两个配置节点，确保兼容性）
            batch_number = self.batch_number_edit.text()
            operator = self.operator_edit.text()

            self.config_manager.set('batch_info.batch_number', batch_number)
            self.config_manager.set('batch_info.operator', operator)
            self.config_manager.set('product.batch_number', batch_number)
            self.config_manager.set('product.operator', operator)
            self.config_manager.set('product.production_date', self.production_date.date().toString())
            self.config_manager.set('product.remarks', self.remarks_edit.toPlainText())

            # 保存电池信息
            battery_type = self.battery_type_combo.currentText()
            battery_spec = self.battery_spec_combo.currentText()

            self.config_manager.set('product.battery_type', battery_type)
            self.config_manager.set('product.battery_spec', battery_spec)
            self.config_manager.set('product.standard_voltage', self.standard_voltage_spin.value())
            self.config_manager.set('product.capacity', self.capacity_spin.value())
            self.config_manager.set('product.capacity_unit', self.capacity_unit_combo.currentText())

            # 新增保存制造商
            self.config_manager.set('product.manufacturer', self.manufacturer_edit.text())

            # 优化同步电池信息到批次信息，确保数据一致性
            self.config_manager.set('batch_info.cell_type', battery_type)
            self.config_manager.set('batch_info.cell_spec', battery_spec)

            logger.info("产品信息设置应用成功")

        except Exception as e:
            logger.error(f"应用产品信息设置失败: {e}")
            raise

    def validate_settings(self) -> bool:
        """
        验证设置

        Returns:
            是否验证通过
        """
        try:
            # 放宽验证条件，允许批次号和操作员为空（可以后续填写）
            logger.debug("开始验证产品信息设置...")

            # 基本验证：确保电池信息合理
            if self.standard_voltage_spin.value() <= 0:
                logger.warning("标准电压必须大于0")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "验证失败", "标准电压必须大于0")
                return False

            if self.capacity_spin.value() <= 0:
                logger.warning("标准容量必须大于0")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "验证失败", "标准容量必须大于0")
                return False

            logger.debug("产品信息设置验证通过")
            return True

        except Exception as e:
            logger.error(f"验证产品信息设置失败: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "验证错误", f"验证过程中发生错误: {e}")
            return False

    def on_tab_activated(self):
        """选项卡激活时调用"""
        # 重新加载设置，确保控件值是最新的
        try:
            logger.debug("产品信息页面激活，重新加载设置...")
            self.load_settings()
            # 确保权限状态正确应用
            self._update_permission_state()
            # 强制刷新权限状态，确保管理员登录后控件可编辑
            logger.debug(f"当前权限状态 - 管理员: {permission_manager.is_administrator()}, 可编辑产品信息: {permission_manager.can_edit_product_info()}")
        except Exception as e:
            logger.error(f"重新加载产品信息设置失败: {e}")

    def force_reload_settings(self):
        """强制重新加载设置"""
        try:
            logger.debug("强制重新加载产品信息设置...")

            # 重新加载所有设置
            self.load_settings()

            logger.debug("强制重新加载完成")

        except Exception as e:
            logger.error(f"强制重新加载设置失败: {e}")

    def refresh_permission_state(self):
        """公共方法：刷新权限状态"""
        try:
            logger.debug("手动刷新产品信息页面权限状态...")
            self._update_permission_state()
            logger.debug("权限状态刷新完成")
        except Exception as e:
            logger.error(f"刷新权限状态失败: {e}")