# -*- coding: utf-8 -*-
"""
测试配置页面
设置连续测试、自动侦测、数据优化等测试相关配置

Author: Jack
Date: 2025-01-27
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QCheckBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QSlider, QRadioButton, QFrame,
    QScrollArea, QMessageBox, QComboBox, QDialog
)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
import logging

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager


class TestConfigWidget(QWidget):
    """测试配置页面组件"""

    # 信号定义
    settings_changed = pyqtSignal()  # 设置变更信号

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        初始化测试配置页面

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

        # 🚀 性能优化：延迟加载模板列表，避免构造函数阻塞
        self._template_list_loaded = False
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self._load_template_list)

        logger.debug("测试配置页面初始化完成")

    def _init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # 创建内容容器
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)

        # 创建2列布局
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(20)

        # 创建左列布局
        left_column = QVBoxLayout()
        left_column.setSpacing(15)

        # 创建右列布局
        right_column = QVBoxLayout()
        right_column.setSpacing(15)

        # 左列：测试模式组 + 错频启动模式组
        test_mode_group = self._create_test_mode_group()
        left_column.addWidget(test_mode_group)

        staggered_startup_group = self._create_staggered_startup_group()
        left_column.addWidget(staggered_startup_group)

        # 左列添加弹性空间
        left_column.addStretch()

        # 右列：数据处理组 + 标签打印组
        data_processing_group = self._create_data_processing_group()
        right_column.addWidget(data_processing_group)

        label_printing_group = self._create_label_printing_group()
        right_column.addWidget(label_printing_group)

        # 右列添加弹性空间
        right_column.addStretch()

        # 将左右列添加到内容布局
        content_layout.addLayout(left_column, 1)  # 左列占1份
        content_layout.addLayout(right_column, 1)  # 右列占1份

        # 将滚动区域添加到主布局
        main_layout.addWidget(scroll_area)

    def _create_test_mode_group(self) -> QGroupBox:
        """创建测试模式组"""
        group = QGroupBox("测试模式")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QGridLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 添加模式说明
        mode_info_label = QLabel("⚠️ 测试模式互斥：连续测试、电池侦测、取样测试只能选择其中一种模式")
        mode_info_label.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(mode_info_label, 0, 0, 1, 2)

        # 连续测试模式
        self.continuous_mode_check = QCheckBox("启用连续测试模式")
        self.continuous_mode_check.setToolTip("启用后将连续进行测试，测试完成后等待2秒自动开始下一次测试\n与电池侦测模式和取样测试模式互斥")
        layout.addWidget(self.continuous_mode_check, 1, 0, 1, 2)

        # 连续测试说明
        continuous_desc = QLabel("• 测试完成后自动重启测试，无需用户干预\n• 适用于同一电池的重复测试")
        continuous_desc.setStyleSheet("color: #27ae60; font-size: 8pt; margin-left: 20px;")
        layout.addWidget(continuous_desc, 2, 0, 1, 2)

        # 自动侦测电池
        self.auto_detect_check = QCheckBox("启用电池自动侦测模式")
        self.auto_detect_check.setToolTip("启用后，系统会自动检测电池插入状态，当所有启用通道都插入电池后自动开始测试\n与连续测试模式和取样测试模式互斥")
        self.auto_detect_check.setEnabled(True)  # 启用功能
        self.auto_detect_check.setStyleSheet("color: #2c3e50; font-weight: bold;")  # 正常显示
        layout.addWidget(self.auto_detect_check, 3, 0, 1, 2)

        # 电池侦测说明
        detect_desc = QLabel("• 自动检测电池插入状态，所有启用通道插入电池后自动开始测试\n• 使用错频测试避免同频干扰，提高测试效率")
        detect_desc.setStyleSheet("color: #27ae60; font-size: 8pt; margin-left: 20px;")
        layout.addWidget(detect_desc, 4, 0, 1, 2)

        # 取样测试模式
        self.sampling_test_check = QCheckBox("启用取样测试模式")
        self.sampling_test_check.setToolTip("收集指定数量的测试样本，用于分析和设置判断参数\n与连续测试模式和电池侦测模式互斥")
        layout.addWidget(self.sampling_test_check, 5, 0, 1, 2)

        # 取样测试说明
        sampling_desc = QLabel("• 收集指定数量的测试样本，无合格判断\n• 自动分析数据并建议判断参数范围")
        sampling_desc.setStyleSheet("color: #e67e22; font-size: 8pt; margin-left: 20px;")
        layout.addWidget(sampling_desc, 6, 0, 1, 2)

        # 取样数量设置（直接在界面中显示）
        sampling_count_label = QLabel("取样数量:")
        sampling_count_label.setStyleSheet("margin-left: 20px; color: #e67e22; font-weight: bold;")
        layout.addWidget(sampling_count_label, 7, 0)

        self.sampling_count_spin = QSpinBox()
        self.sampling_count_spin.setRange(1, 200)
        self.sampling_count_spin.setValue(30)
        self.sampling_count_spin.setSuffix(" 个")
        self.sampling_count_spin.setToolTip("设置需要收集的有效样本数量\n建议：快速评估1-20个，标准评估30-50个，精确评估50-100个")
        self.sampling_count_spin.setEnabled(False)  # 默认禁用，启用取样测试时才启用
        layout.addWidget(self.sampling_count_spin, 7, 1)

        # 测试超时时间
        layout.addWidget(QLabel("测试超时:"), 8, 0)
        self.test_timeout_spin = QSpinBox()
        self.test_timeout_spin.setRange(10, 300)
        self.test_timeout_spin.setValue(60)
        self.test_timeout_spin.setSuffix(" 秒")
        self.test_timeout_spin.setToolTip("单次测试的最大允许时间")
        layout.addWidget(self.test_timeout_spin, 8, 1)

        # 重试次数
        layout.addWidget(QLabel("重试次数:"), 9, 0)
        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(0, 10)
        self.retry_count_spin.setValue(2)
        self.retry_count_spin.setSuffix(" 次")
        self.retry_count_spin.setToolTip("测试失败时的重试次数")
        layout.addWidget(self.retry_count_spin, 9, 1)

        # 连续测试间隔（仅在连续测试模式下显示）
        layout.addWidget(QLabel("连续测试间隔:"), 10, 0)
        self.test_interval_spin = QSpinBox()
        self.test_interval_spin.setRange(1, 10)  # 扩展范围1-10秒
        self.test_interval_spin.setValue(2)
        self.test_interval_spin.setSuffix(" 秒")
        self.test_interval_spin.setToolTip("连续测试模式下两次测试之间的间隔时间（1-10秒）")
        layout.addWidget(self.test_interval_spin, 10, 1)

        # 连续测试次数限制
        layout.addWidget(QLabel("次数限制:"), 11, 0)
        self.test_count_limit_check = QCheckBox("启用次数限制")
        self.test_count_limit_check.setToolTip("启用后将在达到指定次数后自动停止连续测试")
        layout.addWidget(self.test_count_limit_check, 11, 1)

        # 最大测试次数
        layout.addWidget(QLabel("最大次数:"), 12, 0)
        self.max_test_count_spin = QSpinBox()
        self.max_test_count_spin.setRange(1, 1000)
        self.max_test_count_spin.setValue(100)
        self.max_test_count_spin.setSuffix(" 次")
        self.max_test_count_spin.setToolTip("连续测试的最大次数")
        self.max_test_count_spin.setEnabled(False)  # 默认禁用
        layout.addWidget(self.max_test_count_spin, 12, 1)

        return group

    def _create_staggered_startup_group(self) -> QGroupBox:
        """创建测试模式组"""
        group = QGroupBox("阻抗测试模式")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 模式选择说明
        mode_label = QLabel("选择多通道阻抗测试的执行方式：")
        mode_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(mode_label)



        # 模式2：增强测试模式（包含临界频点设置）
        mode2_layout = QHBoxLayout()

        # 左侧：模式2选项和说明
        mode2_left_layout = QVBoxLayout()
        self.parallel_staggered_radio = QRadioButton("模式2：增强测试模式")
        self.parallel_staggered_radio.setChecked(True)  # 设为默认选中（因为其他模式被灰化）
        self.parallel_staggered_radio.setToolTip("针对磷酸铁锂等电池优化测试")
        mode2_left_layout.addWidget(self.parallel_staggered_radio)

        # 增强测试模式说明
        parallel_staggered_desc = QLabel("针对磷酸铁锂等电池优化测试")
        parallel_staggered_desc.setStyleSheet("color: #3498db; font-size: 8pt; margin-left: 20px; font-weight: bold;")
        mode2_left_layout.addWidget(parallel_staggered_desc)

        mode2_layout.addLayout(mode2_left_layout, 2)  # 左侧占2份

        # 右侧：增强模式参数设置
        mode2_right_layout = QVBoxLayout()

        # 增强模式参数标题
        params_label = QLabel("增强模式参数：")
        params_label.setStyleSheet("color: #666; font-size: 9pt; font-weight: bold;")
        mode2_right_layout.addWidget(params_label)

        # 临界频点设置
        critical_layout = QHBoxLayout()
        critical_layout.addWidget(QLabel("临界频点:"))

        self.critical_frequency_spin = QDoubleSpinBox()
        self.critical_frequency_spin.setRange(0.01, 10000.0)
        self.critical_frequency_spin.setValue(10.0)
        self.critical_frequency_spin.setSuffix(" Hz")
        self.critical_frequency_spin.setDecimals(2)
        self.critical_frequency_spin.setToolTip("设置高频/低频的分界点\n• >临界频点：使用错频策略避免干扰\n• ≤临界频点：使用同时启动提高效率")
        self.critical_frequency_spin.setEnabled(True)  # 默认启用（因为增强模式是默认选中）
        critical_layout.addWidget(self.critical_frequency_spin)

        critical_desc = QLabel("(高频/低频分界点)")
        critical_desc.setStyleSheet("color: #888; font-size: 8pt;")
        critical_layout.addWidget(critical_desc)

        mode2_right_layout.addLayout(critical_layout)

        mode2_layout.addLayout(mode2_right_layout, 1)  # 右侧占1份

        layout.addLayout(mode2_layout)





        return group

    def _create_data_processing_group(self) -> QGroupBox:
        """创建数据处理组"""
        group = QGroupBox("数据处理")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QGridLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 数据优化
        self.data_optimization_check = QCheckBox("启用数据优化")
        self.data_optimization_check.setToolTip("对测试数据进行优化处理，提高数据质量")
        layout.addWidget(self.data_optimization_check, 0, 0, 1, 2)

        # 异常值过滤
        self.outlier_filter_check = QCheckBox("异常值过滤")
        self.outlier_filter_check.setToolTip("自动过滤明显异常的测试数据")
        layout.addWidget(self.outlier_filter_check, 1, 0, 1, 2)

        # 数据平滑
        self.data_smoothing_check = QCheckBox("数据平滑")
        self.data_smoothing_check.setToolTip("对测试数据进行平滑处理，减少噪声影响")
        layout.addWidget(self.data_smoothing_check, 2, 0, 1, 2)

        # 平滑强度
        layout.addWidget(QLabel("平滑强度:"), 3, 0)
        self.smoothing_strength_slider = QSlider()  # 默认水平方向
        self.smoothing_strength_slider.setRange(1, 10)
        self.smoothing_strength_slider.setValue(5)
        self.smoothing_strength_slider.setToolTip("数据平滑的强度，值越大平滑效果越强")
        layout.addWidget(self.smoothing_strength_slider, 3, 1)

        # 平滑强度标签
        self.smoothing_strength_label = QLabel("5")
        layout.addWidget(self.smoothing_strength_label, 3, 2)

        # 自动保存数据
        self.auto_save_check = QCheckBox("自动保存测试数据")
        self.auto_save_check.setToolTip("测试完成后自动保存数据到数据库")
        layout.addWidget(self.auto_save_check, 4, 0, 1, 2)

        # 保存原始数据
        self.save_raw_data_check = QCheckBox("保存原始数据")
        self.save_raw_data_check.setToolTip("同时保存未处理的原始测试数据")
        layout.addWidget(self.save_raw_data_check, 5, 0, 1, 2)



        return group



    def _create_label_printing_group(self) -> QGroupBox:
        """创建标签设置组"""
        group = QGroupBox("标签设置")
        group.setFont(QFont("", 10, QFont.Bold))

        layout = QGridLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 自动打印标签
        self.auto_print_check = QCheckBox("自动打印标签")
        self.auto_print_check.setToolTip("测试完成后自动打印电池标签")
        layout.addWidget(self.auto_print_check, 0, 0, 1, 2)

        # 仅打印合格品
        self.print_pass_only_check = QCheckBox("仅打印合格品")
        self.print_pass_only_check.setToolTip("只为测试合格的电池打印标签")
        layout.addWidget(self.print_pass_only_check, 1, 0, 1, 2)

        # 打印份数
        layout.addWidget(QLabel("打印份数:"), 2, 0)
        self.print_copies_spin = QSpinBox()
        self.print_copies_spin.setRange(1, 10)
        self.print_copies_spin.setValue(1)
        self.print_copies_spin.setSuffix(" 份")
        self.print_copies_spin.setToolTip("每个电池标签的打印份数")
        layout.addWidget(self.print_copies_spin, 2, 1)

        # 模板选择下拉框
        layout.addWidget(QLabel("当前模板:"), 3, 0)
        self.template_combo = QComboBox()
        self.template_combo.setToolTip("选择要使用的标签模板")
        self.template_combo.setMinimumWidth(200)
        self.template_combo.currentTextChanged.connect(self._on_template_selection_changed)
        layout.addWidget(self.template_combo, 3, 1)

        # 标签设计器按钮
        self.label_designer_btn = QPushButton("打开标签设计器")
        self.label_designer_btn.setToolTip("打开可视化标签设计器，自定义标签布局和内容")
        self.label_designer_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        self.label_designer_btn.clicked.connect(self._open_label_designer)
        layout.addWidget(self.label_designer_btn, 4, 0, 1, 2)

        # 模板信息显示
        info_text = """
💡 标签设计器功能：
• 支持多种标签尺寸 (30x20mm, 40x30mm, 50x30mm)
• 可视化拖拽编辑界面
• 丰富的动态参数支持
• 预设模板和自定义模板管理
• 实时预览和导出功能
        """
        self.template_info_label = QLabel(info_text.strip())
        self.template_info_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 9pt;
                padding: 8px;
                background-color: #ecf0f1;
                border-radius: 4px;
                border-left: 3px solid #3498db;
            }
        """)
        self.template_info_label.setWordWrap(True)
        layout.addWidget(self.template_info_label, 5, 0, 1, 2)

        return group

    def _open_label_designer(self):
        """打开标签设计器"""
        try:
            logger.info("🎯 用户点击了标签设计器按钮")
            logger.debug("开始导入标签设计器对话框...")
            from ui.dialogs.label_designer_dialog import LabelDesignerDialog
            logger.debug("标签设计器对话框导入成功")

            # 创建标签设计器对话框
            logger.debug("开始创建标签设计器对话框实例...")
            dialog = LabelDesignerDialog(self.config_manager, self)
            logger.debug("标签设计器对话框实例创建成功")

            # 显示对话框
            logger.debug("开始显示标签设计器对话框...")
            if dialog.exec_() == dialog.Accepted:
                # 用户确认了设计器中的设置，更新当前模板显示
                self._update_current_template_display()

                # 发送设置变更信号
                self._on_setting_changed()

                logger.info("标签设计器设置已应用")
            else:
                logger.debug("用户取消了标签设计器设置")
            logger.debug("标签设计器对话框已关闭")

        except ImportError as e:
            logger.error(f"无法导入标签设计器: {e}")
            QMessageBox.critical(self, "错误", "标签设计器模块未找到，请检查安装")
        except Exception as e:
            logger.error(f"打开标签设计器失败: {e}")
            QMessageBox.critical(self, "错误", f"打开标签设计器失败: {e}")

    def _load_template_list(self):
        """加载模板列表到下拉框（优化版本）"""
        try:
            if self._template_list_loaded:
                return  # 已经加载过

            logger.info("🔄 开始加载打印设置模板列表...")
            from ui.dialogs.label_template_manager import LabelTemplateManager

            # 创建模板管理器
            template_manager = LabelTemplateManager(self.config_manager)

            # 修复阻塞信号，避免在加载过程中触发变更事件
            self.template_combo.blockSignals(True)

            # 清空现有选项
            self.template_combo.clear()

            # 添加预设模板（包含尺寸信息）
            preset_templates = template_manager.get_preset_templates()
            logger.debug(f"📋 找到 {len(preset_templates)} 个预设模板")
            for template in preset_templates:
                display_text = f"[预设] {template.name} ({template.size})"
                # 使用模板ID作为数据，而不是文件路径
                self.template_combo.addItem(display_text, template.template_id)
                logger.debug(f"  + 预设模板: {template.name} (ID: {template.template_id})")

            # 添加用户模板（包含尺寸信息）
            user_templates = template_manager.get_user_templates()
            logger.debug(f"👤 找到 {len(user_templates)} 个用户模板")
            for template in user_templates:
                display_text = f"[用户] {template.name} ({template.size})"
                # 使用模板ID作为数据，而不是文件路径
                self.template_combo.addItem(display_text, template.template_id)
                logger.debug(f"  + 用户模板: {template.name} (ID: {template.template_id})")

            # 修复恢复信号连接
            self.template_combo.blockSignals(False)

            # 设置当前选中的模板
            current_template_id = self.config_manager.get('label_template.current_template_id', 'standard_50x30')
            logger.info(f"🎯 尝试选择配置中的模板: {current_template_id}")
            self._select_current_template(current_template_id)

            total_templates = len(preset_templates) + len(user_templates)
            logger.info(f"✅ 打印设置模板列表加载完成，共 {total_templates} 个模板")
            self._template_list_loaded = True

        except Exception as e:
            logger.error(f"❌ 加载模板列表失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

            # 添加默认选项作为备用
            try:
                self.template_combo.blockSignals(True)
                self.template_combo.clear()
                self.template_combo.addItem("[预设] 标准模板 (50x30mm)", "standard_50x30")
                self.template_combo.blockSignals(False)
                logger.warning("⚠️ 已添加默认模板选项作为备用")
            except Exception as fallback_error:
                logger.error(f"❌ 添加默认模板选项也失败: {fallback_error}")

    def _select_current_template(self, template_id: str):
        """选择当前模板"""
        try:

            # 遍历下拉框选项，找到匹配的模板
            for i in range(self.template_combo.count()):
                item_template_id = self.template_combo.itemData(i)
                if item_template_id == template_id:
                    # 修复使用阻塞信号的方式设置当前选项，避免触发变更事件
                    self.template_combo.blockSignals(True)
                    self.template_combo.setCurrentIndex(i)
                    self.template_combo.blockSignals(False)
                    logger.info(f"✅ 成功选择模板: {template_id} (索引: {i})")
                    return

            # 如果没找到指定模板，选择第一个可用模板
            if self.template_combo.count() > 0:
                logger.warning(f"⚠️ 未找到模板 {template_id}，选择第一个可用模板")
                self.template_combo.blockSignals(True)
                self.template_combo.setCurrentIndex(0)
                self.template_combo.blockSignals(False)

                # 新增更新配置为实际选中的模板
                first_template_id = self.template_combo.itemData(0)
                if first_template_id:
                    self.config_manager.set('label_template.current_template_id', first_template_id)
                    logger.info(f"✅ 已更新配置为第一个可用模板: {first_template_id}")
            else:
                logger.error("❌ 没有可用的模板选项")

        except Exception as e:
            logger.error(f"❌ 选择当前模板失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _on_template_selection_changed(self, template_text=None):
        """模板选择变更处理"""
        if self._loading:
            return

        try:
            # 获取选中模板的ID
            current_index = self.template_combo.currentIndex()
            if current_index < 0:
                return

            template_id = self.template_combo.itemData(current_index)
            if not template_id:
                return

            logger.info(f"🎯 用户在打印设置中选择模板: {template_id}")

            # 加载模板配置
            from ui.dialogs.label_template_manager import LabelTemplateManager
            template_manager = LabelTemplateManager(self.config_manager)
            template = template_manager.get_template(template_id)

            if template:
                # 保存当前模板配置到配置管理器
                self.config_manager.set('label_template.current_template_id', template.template_id)
                self.config_manager.set('label_template.current_name', template.name)
                self.config_manager.set('label_template.current_size', template.size)

                # 关键修复立即保存配置到文件，确保持久化
                self.config_manager.save_config()
                logger.info(f"✅ 模板配置已保存到文件: {template.name} ({template.size}) -> ID: {template.template_id}")

                # 新增通知主界面模板配置已变更（通过设置变更信号）
                try:
                    # 由于配置管理器没有信号机制，我们通过设置变更信号来通知
                    # 主界面会在接收到设置变更信号后重新初始化标签打印管理器
                    logger.info("✅ 模板配置变更将通过设置变更信号通知主界面")
                except Exception as signal_error:
                    logger.warning(f"处理模板配置变更通知失败: {signal_error}")

                # 发送设置变更信号到设置对话框
                self._on_setting_changed()

                logger.info(f"🎉 打印设置模板选择完成: {template.name} ({template.size}) -> ID: {template.template_id}")
            else:
                logger.error(f"❌ 加载模板失败: {template_id}")

        except Exception as e:
            logger.error(f"❌ 模板选择变更处理失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _update_current_template_display(self):
        """更新当前模板显示（保留用于兼容性）"""
        try:
            # 重新加载模板列表
            self._load_template_list()

        except Exception as e:
            logger.error(f"更新当前模板显示失败: {e}")

    def _init_connections(self):
        """初始化信号连接"""
        # 测试模式变更（添加互斥性逻辑）
        self.continuous_mode_check.toggled.connect(self._on_continuous_mode_changed)
        self.auto_detect_check.toggled.connect(self._on_auto_detect_changed)
        self.sampling_test_check.toggled.connect(self._on_sampling_test_changed)

        # 取样数量控件
        self.sampling_count_spin.valueChanged.connect(self._on_sampling_count_changed)
        self.test_timeout_spin.valueChanged.connect(self._on_setting_changed)
        self.retry_count_spin.valueChanged.connect(self._on_setting_changed)
        self.test_interval_spin.valueChanged.connect(self._on_setting_changed)
        self.test_count_limit_check.toggled.connect(self._on_count_limit_changed)
        self.max_test_count_spin.valueChanged.connect(self._on_setting_changed)

        # 错频启动模式变更 - 只保留增强测试模式
        self.parallel_staggered_radio.toggled.connect(self._on_test_mode_changed)

        # 临界频点变更
        self.critical_frequency_spin.valueChanged.connect(self._on_setting_changed)

        # 数据处理变更
        self.data_optimization_check.toggled.connect(self._on_setting_changed)
        self.outlier_filter_check.toggled.connect(self._on_setting_changed)
        self.data_smoothing_check.toggled.connect(self._on_data_smoothing_changed)
        self.smoothing_strength_slider.valueChanged.connect(self._on_smoothing_strength_changed)
        self.auto_save_check.toggled.connect(self._on_setting_changed)
        self.save_raw_data_check.toggled.connect(self._on_setting_changed)

        # 标签打印变更
        self.auto_print_check.toggled.connect(self._on_auto_print_changed)
        self.print_pass_only_check.toggled.connect(self._on_setting_changed)
        self.print_copies_spin.valueChanged.connect(self._on_setting_changed)

    def _on_data_smoothing_changed(self, checked: bool):
        """数据平滑开关变更处理"""
        self.smoothing_strength_slider.setEnabled(checked)
        self.smoothing_strength_label.setEnabled(checked)
        self._on_setting_changed()

    def _on_smoothing_strength_changed(self, value: int):
        """平滑强度变更处理"""
        self.smoothing_strength_label.setText(str(value))
        self._on_setting_changed()

    def _on_continuous_mode_changed(self, checked: bool):
        """连续测试开关变更处理"""
        if self._loading:
            return

        # 🔧 实现完整的互斥性：如果启用连续测试，则禁用其他测试模式
        if checked:
            # 禁用电池侦测模式
            if self.auto_detect_check.isChecked():
                self.auto_detect_check.setChecked(False)
                logger.info("启用连续测试模式，自动禁用电池侦测模式")

            # 禁用取样测试模式
            if self.sampling_test_check.isChecked():
                self.sampling_test_check.setChecked(False)
                logger.info("启用连续测试模式，自动禁用取样测试模式")

        # 启用/禁用相关控件
        self.test_interval_spin.setEnabled(checked)
        self.test_count_limit_check.setEnabled(checked)
        if checked and self.test_count_limit_check.isChecked():
            self.max_test_count_spin.setEnabled(True)
        else:
            self.max_test_count_spin.setEnabled(False)

        # 移除连续测试模式的确认弹窗，直接记录日志
        if checked:
            interval = self.test_interval_spin.value()
            count_limit_enabled = self.test_count_limit_check.isChecked()
            max_count = self.max_test_count_spin.value() if count_limit_enabled else 0
            logger.info(f"连续测试模式已启用：间隔{interval}秒，最大次数{max_count if count_limit_enabled else '无限制'}")

        self._on_setting_changed()

    def _on_sampling_test_changed(self, checked: bool):
        """取样测试开关变更处理"""
        if self._loading:
            return

        # 🔧 实现完整的互斥性：如果启用取样测试，则禁用其他测试模式
        if checked:
            # 禁用连续测试模式
            if self.continuous_mode_check.isChecked():
                self.continuous_mode_check.setChecked(False)
                logger.info("启用取样测试模式，自动禁用连续测试模式")

            # 禁用电池侦测模式
            if self.auto_detect_check.isChecked():
                self.auto_detect_check.setChecked(False)
                logger.info("启用取样测试模式，自动禁用电池侦测模式")

            # 禁用连续测试相关控件
            self.test_interval_spin.setEnabled(False)
            self.test_count_limit_check.setEnabled(False)
            self.max_test_count_spin.setEnabled(False)

            # 启用取样数量控件
            self.sampling_count_spin.setEnabled(True)

            logger.info("取样测试模式已启用")
        else:
            # 禁用取样数量控件
            self.sampling_count_spin.setEnabled(False)

            # 取消取样测试模式后进入手动模式，不自动启用其他测试模式
            logger.info("取样测试模式已禁用，进入手动模式")

        self._on_setting_changed()

    def _on_sampling_count_changed(self, value: int):
        """取样数量变更处理"""
        if self._loading:
            return

        try:
            # 保存配置到配置管理器
            self.config_manager.set('test.sampling_count', value)
            logger.info(f"✅ 取样数量已更新: {value}个")

            # 修复：通知取样管理器更新目标数量
            self._update_sampling_manager_target_count()

            # 触发设置变更
            self._on_setting_changed()

        except Exception as e:
            logger.error(f"❌ 更新取样数量失败: {e}")

    def _on_auto_detect_changed(self, checked: bool):
        """电池侦测开关变更处理"""
        if self._loading:
            return

        try:
            # 🔧 实现完整的互斥性：如果启用电池侦测，则禁用其他测试模式
            if checked:
                # 禁用连续测试模式
                if self.continuous_mode_check.isChecked():
                    self.continuous_mode_check.setChecked(False)
                    logger.info("启用电池侦测模式，自动禁用连续测试模式")

                # 禁用取样测试模式
                if self.sampling_test_check.isChecked():
                    self.sampling_test_check.setChecked(False)
                    logger.info("启用电池侦测模式，自动禁用取样测试模式")

                # 禁用连续测试相关控件
                self.test_interval_spin.setEnabled(False)
                self.test_count_limit_check.setEnabled(False)
                self.max_test_count_spin.setEnabled(False)

                # 禁用取样数量控件
                self.sampling_count_spin.setEnabled(False)

            # 保存配置到配置管理器
            self.config_manager.set('test.auto_detect', checked)
            logger.info(f"✅ 电池侦测模式已{'启用' if checked else '禁用'}")

            # 触发设置变更
            self._on_setting_changed()

        except Exception as e:
            logger.error(f"❌ 更新电池侦测设置失败: {e}")

    def _on_count_limit_changed(self, checked: bool):
        """次数限制开关变更处理"""
        self.max_test_count_spin.setEnabled(checked and self.continuous_mode_check.isChecked())
        self._on_setting_changed()

    def _on_auto_print_changed(self, checked: bool):
        """自动打印开关变更处理"""
        # 启用/禁用相关控件
        self.print_pass_only_check.setEnabled(checked)
        self.print_copies_spin.setEnabled(checked)
        self.label_designer_btn.setEnabled(checked)
        self._on_setting_changed()

    def _on_test_mode_changed(self, checked: bool):
        """测试模式变更处理"""
        if self._loading:
            return

        # 只有增强测试模式选中时，临界频点设置才可用
        enhanced_mode_enabled = self.parallel_staggered_radio.isChecked()
        self.critical_frequency_spin.setEnabled(enhanced_mode_enabled)

        # 更新临界频点标签的样式
        critical_labels = self.findChildren(QLabel)
        for label in critical_labels:
            if "临界频点" in label.text():
                if enhanced_mode_enabled:
                    label.setStyleSheet("color: #333;")
                else:
                    label.setStyleSheet("color: #888;")
                break

        # 记录模式变更日志 - 只有增强测试模式
        if checked:
            logger.info("切换到增强测试模式，临界频点设置已启用")

        self._on_setting_changed()

    def _on_setting_changed(self):
        """设置变更处理"""
        if not self._loading:
            self.settings_changed.emit()

    def _show_continuous_mode_info(self):
        """显示连续测试状态提示框"""
        try:
            from PyQt5.QtWidgets import QMessageBox

            # 获取当前设置
            interval = self.test_interval_spin.value()
            count_limit_enabled = self.test_count_limit_check.isChecked()
            max_count = self.max_test_count_spin.value() if count_limit_enabled else 0

            # 构建提示信息
            info_text = "连续测试功能已启用\n\n"
            info_text += f"📋 当前设置：\n"
            info_text += f"   • 测试间隔：{interval} 秒\n"

            if count_limit_enabled:
                info_text += f"   • 最大次数：{max_count} 次\n"
            else:
                info_text += f"   • 最大次数：无限制\n"

            info_text += f"\n⚠️  注意事项：\n"
            info_text += f"   • 连续测试将在每次测试完成后自动重启\n"
            info_text += f"   • 系统会在每次重启前检查电池电压\n"
            info_text += f"   • 电压异常时会暂停连续测试\n"
            info_text += f"   • 可随时在主界面停止连续测试\n"
            info_text += f"   • 连续测试与电池侦测功能互斥\n"

            # 显示信息对话框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("连续测试状态")
            msg_box.setText(info_text)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()

            logger.info(f"显示连续测试状态提示：间隔{interval}秒，最大次数{max_count}")

        except Exception as e:
            logger.error(f"显示连续测试状态提示失败: {e}")

    def load_settings(self):
        """加载设置"""
        self._loading = True
        try:
            # 加载测试模式
            continuous_mode = self.config_manager.get('test.continuous_mode', False)
            self.continuous_mode_check.setChecked(continuous_mode)

            # 加载电池侦测设置
            auto_detect = self.config_manager.get('test.auto_detect', False)
            self.auto_detect_check.setChecked(auto_detect)

            sampling_test = self.config_manager.get('test.sampling_test', False)
            self.sampling_test_check.setChecked(sampling_test)

            # 加载取样数量
            sampling_count = self.config_manager.get('test.sampling_count', 30)
            self.sampling_count_spin.setValue(sampling_count)

            # 检查互斥性：如果多个模式同时启用，优先级：电池侦测 > 连续测试 > 取样测试
            active_modes = sum([continuous_mode, auto_detect, sampling_test])
            if active_modes > 1:
                logger.warning(f"检测到多个测试模式同时启用，应用优先级规则")
                if auto_detect:
                    # 保留电池侦测，禁用其他
                    self.continuous_mode_check.setChecked(False)
                    self.sampling_test_check.setChecked(False)
                    continuous_mode = False
                    sampling_test = False
                elif continuous_mode:
                    # 保留连续测试，禁用取样测试
                    self.sampling_test_check.setChecked(False)
                    sampling_test = False

            timeout = self.config_manager.get('test.timeout', 60)
            self.test_timeout_spin.setValue(timeout)

            retry_count = self.config_manager.get('test.retry_count', 2)
            self.retry_count_spin.setValue(retry_count)

            interval = self.config_manager.get('test.interval', 2)
            self.test_interval_spin.setValue(interval)

            # 加载连续测试次数限制
            count_limit_enabled = self.config_manager.get('test.count_limit_enabled', False)
            self.test_count_limit_check.setChecked(count_limit_enabled)

            max_count = self.config_manager.get('test.max_count', 100)
            self.max_test_count_spin.setValue(max_count)

            # 加载阻抗测试模式
            test_mode = self.config_manager.get('test_params.test_mode', 'simultaneous')
            # 只有增强测试模式可用
            self.parallel_staggered_radio.setChecked(True)

            # 加载临界频点设置
            critical_frequency = self.config_manager.get('test_params.critical_frequency', 10.0)
            self.critical_frequency_spin.setValue(critical_frequency)

            # 加载数据处理
            data_opt = self.config_manager.get('data.optimization', True)
            self.data_optimization_check.setChecked(data_opt)

            outlier_filter = self.config_manager.get('data.outlier_filter', True)
            self.outlier_filter_check.setChecked(outlier_filter)

            smoothing = self.config_manager.get('data.smoothing', False)
            self.data_smoothing_check.setChecked(smoothing)

            smoothing_strength = self.config_manager.get('data.smoothing_strength', 5)
            self.smoothing_strength_slider.setValue(smoothing_strength)
            self.smoothing_strength_label.setText(str(smoothing_strength))

            auto_save = self.config_manager.get('data.auto_save', True)
            self.auto_save_check.setChecked(auto_save)

            save_raw = self.config_manager.get('data.save_raw', False)
            self.save_raw_data_check.setChecked(save_raw)



            # 加载标签打印
            auto_print = self.config_manager.get('label.auto_print', False)
            self.auto_print_check.setChecked(auto_print)

            print_pass_only = self.config_manager.get('label.print_pass_only', True)
            self.print_pass_only_check.setChecked(print_pass_only)

            copies = self.config_manager.get('label.copies', 1)
            self.print_copies_spin.setValue(copies)

            # 更新当前模板显示
            self._update_current_template_display()

            # 更新控件状态
            self._on_continuous_mode_changed(continuous_mode)
            self._on_sampling_test_changed(sampling_test)
            self._on_count_limit_changed(count_limit_enabled)
            self._on_data_smoothing_changed(smoothing)
            self._on_auto_print_changed(auto_print)

            # 更新测试模式状态（确保临界频点设置的启用/禁用状态正确）
            self._on_test_mode_changed(True)

            logger.debug("测试配置设置加载完成")

        except Exception as e:
            logger.error(f"加载测试配置设置失败: {e}")
        finally:
            self._loading = False



    def apply_settings(self):
        """应用设置"""
        try:
            # 保存测试模式
            self.config_manager.set('test.continuous_mode', self.continuous_mode_check.isChecked())
            self.config_manager.set('test.continuous_mode_delay', self.test_interval_spin.value())
            # 保存电池侦测设置
            self.config_manager.set('test.auto_detect', self.auto_detect_check.isChecked())

            # 关键修复处理取样测试模式的启动和停止
            sampling_test_enabled = self.sampling_test_check.isChecked()
            sampling_count = self.sampling_count_spin.value()

            self.config_manager.set('test.sampling_test', sampling_test_enabled)
            self.config_manager.set('test.sampling_count', sampling_count)  # 保存取样数量

            # 如果启用了取样测试，需要启动取样测试管理器
            if sampling_test_enabled:
                logger.info(f"🎯 配置对话框：启用取样测试模式，目标数量: {sampling_count}")
                self._start_sampling_test_from_config(sampling_count)
            else:
                logger.info("🎯 配置对话框：禁用取样测试模式")
                self._stop_sampling_test_from_config()
            self.config_manager.set('test.timeout', self.test_timeout_spin.value())
            self.config_manager.set('test.retry_count', self.retry_count_spin.value())
            self.config_manager.set('test.interval', self.test_interval_spin.value())
            self.config_manager.set('test.count_limit_enabled', self.test_count_limit_check.isChecked())
            self.config_manager.set('test.max_count', self.max_test_count_spin.value())

            # 保存阻抗测试模式 - 只有增强测试模式
            test_mode = 'staggered'
            # 强制启用并行错频模式
            self.config_manager.set('test.use_parallel_staggered_mode', True)
            logger.info("✅ 增强测试模式已选择，并行错频模式已启用")
            self.config_manager.set('test_params.test_mode', test_mode)

            # 保存临界频点设置
            self.config_manager.set('test_params.critical_frequency', self.critical_frequency_spin.value())

            # 保存数据处理
            self.config_manager.set('data.optimization', self.data_optimization_check.isChecked())
            self.config_manager.set('data.outlier_filter', self.outlier_filter_check.isChecked())
            self.config_manager.set('data.smoothing', self.data_smoothing_check.isChecked())
            self.config_manager.set('data.smoothing_strength', self.smoothing_strength_slider.value())
            self.config_manager.set('data.auto_save', self.auto_save_check.isChecked())
            self.config_manager.set('data.save_raw', self.save_raw_data_check.isChecked())



            # 保存标签打印
            self.config_manager.set('label.auto_print', self.auto_print_check.isChecked())
            self.config_manager.set('label.print_pass_only', self.print_pass_only_check.isChecked())
            self.config_manager.set('label.copies', self.print_copies_spin.value())

            logger.info("测试配置设置应用成功")

        except Exception as e:
            logger.error(f"应用测试配置设置失败: {e}")
            raise



    def validate_settings(self) -> bool:
        """
        验证设置

        Returns:
            是否验证通过
        """
        try:
            # 放宽验证条件，允许编码前缀为空（使用默认值）

            # 只验证超时时间合理性
            if self.test_timeout_spin.value() < 10:
                logger.warning(f"超时时间过短: {self.test_timeout_spin.value()}")
                return False

            return True

        except Exception as e:
            logger.error(f"验证测试配置设置失败: {e}")
            return False

    def on_tab_activated(self):
        """选项卡激活时调用"""
        # 更新控件状态
        self._on_continuous_mode_changed(self.continuous_mode_check.isChecked())
        self._on_count_limit_changed(self.test_count_limit_check.isChecked())
        self._on_data_smoothing_changed(self.data_smoothing_check.isChecked())
        self._on_auto_print_changed(self.auto_print_check.isChecked())
        self._on_test_mode_changed(True)

    def _start_sampling_test_from_config(self, sample_count: int):
        """从配置对话框启动取样测试"""
        try:
            # 尝试获取主窗口
            main_window = self._get_main_window()
            if not main_window:
                logger.warning("⚠️ 无法获取主窗口，跳过取样测试启动")
                return

            # 获取取样测试集成管理器
            sampling_integration_manager = main_window._get_sampling_integration_manager()
            if sampling_integration_manager:
                # 启动取样测试（这会重置所有计数）
                success = sampling_integration_manager.start_sampling_test(sample_count)
                if success:
                    logger.info(f"✅ 从配置对话框成功启动取样测试，目标数量: {sample_count}")
                else:
                    logger.error("❌ 从配置对话框启动取样测试失败")
            else:
                logger.warning("⚠️ 无法获取取样测试集成管理器")

        except Exception as e:
            logger.error(f"❌ 从配置对话框启动取样测试失败: {e}")

    def _update_sampling_manager_target_count(self):
        """更新取样管理器的目标数量"""
        try:
            # 尝试获取主窗口
            main_window = self._get_main_window()
            if not main_window:
                logger.debug("无法获取主窗口，跳过取样管理器更新")
                return

            # 获取取样测试集成管理器
            sampling_integration_manager = main_window._get_sampling_integration_manager()
            if sampling_integration_manager:
                sampling_integration_manager._update_sampling_manager_config()
                logger.debug("✅ 取样管理器目标数量已更新")
            else:
                logger.debug("无法获取取样测试集成管理器")

        except Exception as e:
            logger.error(f"❌ 更新取样管理器目标数量失败: {e}")

    def _stop_sampling_test_from_config(self):
        """从配置对话框停止取样测试"""
        try:
            # 尝试获取主窗口
            main_window = self._get_main_window()
            if not main_window:
                logger.warning("⚠️ 无法获取主窗口，跳过取样测试停止")
                return

            # 获取取样测试集成管理器
            sampling_integration_manager = main_window._get_sampling_integration_manager()
            if sampling_integration_manager:
                # 停止取样测试（这会重置所有计数）
                sampling_integration_manager.stop_sampling_test()
                logger.info("✅ 从配置对话框成功停止取样测试")
            else:
                logger.warning("⚠️ 无法获取取样测试集成管理器")

        except Exception as e:
            logger.error(f"❌ 从配置对话框停止取样测试失败: {e}")

    def _get_main_window(self):
        """获取主窗口引用"""
        try:
            # 向上查找主窗口
            parent = self.parent()
            while parent:
                if hasattr(parent, '_get_sampling_integration_manager'):
                    return parent
                parent = parent.parent()
            return None
        except Exception as e:
            logger.error(f"获取主窗口失败: {e}")
            return None