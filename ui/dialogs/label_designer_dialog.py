#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构后的标签设计器主对话框
作为各个管理器的协调器，保持较小的体积

Author: Jack
Date: 2025-06-04
"""

import logging
from typing import Optional
from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QKeySequence

# 导入管理器
from .element_property_manager import ElementPropertyManager
from .label_element_manager import LabelElementManager
from .label_template_ui_manager import LabelTemplateUIManager
from .label_designer_ui_manager import LabelDesignerUIManager

# 导入标签相关类
from .label_template_config import LabelTemplateConfig

logger = logging.getLogger(__name__)


class LabelDesignerDialog(QDialog):
    """
    标签设计器主对话框（重构版）
    
    职责：
    - 协调各个管理器
    - 处理管理器间的通信
    - 管理整体状态
    """
    
    def __init__(self, config_manager, parent=None):
        """
        初始化标签设计器对话框

        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        logger.info("🎨 开始初始化标签设计器对话框...")
        super().__init__(parent)

        self.config_manager = config_manager
        logger.debug("配置管理器已设置")
        self.current_template: Optional[LabelTemplateConfig] = None
        
        # 设置窗口属性
        self.setWindowTitle("标签设计器")
        self.setModal(True)
        self.resize(1400, 900)
        self.setMinimumSize(1200, 800)

        # 设置样式表，确保背景色正确
        self._apply_styles()
        
        # 初始化管理器
        self._init_managers()
        
        # 创建界面
        self._init_ui()
        
        # 连接信号
        self._connect_signals()
        
        # 初始化数据
        self._init_data()
        
        logger.debug("标签设计器对话框初始化完成")

    def keyPressEvent(self, event):
        """处理键盘事件"""
        try:
            # 检查是否按下了Delete或Backspace键
            if event.key() in (0x01000007, 0x01000003):  # Qt.Key_Delete, Qt.Key_Backspace
                logger.debug(f"🔑 按下删除键，当前选中元素: {getattr(self, 'selected_element_id', 'None')}")

                # 检查是否有选中的元素
                if hasattr(self, 'selected_element_id') and self.selected_element_id:
                    # 验证元素是否真的存在
                    element_exists = self.element_manager.get_element(self.selected_element_id) is not None
                    logger.debug(f"🔑 元素是否存在: {element_exists}")

                    if element_exists:
                        logger.debug(f"🔑 键盘删除元素: {self.selected_element_id}")
                        self._on_remove_element_requested(self.selected_element_id)
                        event.accept()
                        return
                    else:
                        logger.warning(f"🔑 尝试删除不存在的元素: {self.selected_element_id}")
                        self.selected_element_id = None  # 清除无效的选中状态
                else:
                    logger.debug("🔑 按下删除键，但没有选中的元素")

            # 其他键盘事件交给父类处理
            super().keyPressEvent(event)

        except Exception as e:
            logger.error(f"处理键盘事件失败: {e}")
            super().keyPressEvent(event)

    def _init_managers(self):
        """初始化各个管理器"""
        try:
            # 创建管理器实例
            self.property_manager = ElementPropertyManager(self)
            self.element_manager = LabelElementManager(self)
            self.template_ui_manager = LabelTemplateUIManager(self.config_manager, self)
            self.designer_ui_manager = LabelDesignerUIManager(self)
            
            logger.debug("所有管理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化管理器失败: {e}")
            QMessageBox.critical(self, "错误", f"初始化失败: {e}")

    def _apply_styles(self):
        """应用标签设计器样式表"""
        try:
            style_sheet = """
            /* 标签设计器主对话框样式 */
            QDialog {
                background-color: #ffffff;  /* 纯白色背景 */
                color: #2c3e50;  /* 深色文字 */
                font-family: "Microsoft YaHei UI", "Segoe UI", Arial, sans-serif;
                font-size: 9pt;
            }

            /* 分组框样式 */
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 8px;
                background-color: #ffffff;
                color: #2c3e50;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #2c3e50;
                background-color: #ffffff;
            }

            /* 按钮样式 */
            QPushButton {
                background-color: #3498db;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                min-width: 80px;
                min-height: 32px;
            }

            QPushButton:hover {
                background-color: #2980b9;
            }

            QPushButton:pressed {
                background-color: #21618c;
            }

            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }

            /* 列表控件样式 */
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                color: #2c3e50;
                selection-background-color: #3498db;
                selection-color: white;
            }

            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #ecf0f1;
            }

            QListWidget::item:hover {
                background-color: #ecf0f1;
            }

            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }

            /* 输入框样式 */
            QLineEdit, QSpinBox, QComboBox {
                background-color: #ffffff;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 4px 8px;
                color: #2c3e50;
                min-height: 20px;
            }

            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border-color: #3498db;
            }

            /* 分割器样式 */
            QSplitter::handle {
                background-color: #bdc3c7;
                border: none;
            }

            QSplitter::handle:horizontal {
                width: 3px;
            }

            QSplitter::handle:vertical {
                height: 3px;
            }

            QSplitter::handle:hover {
                background-color: #95a5a6;
            }

            /* 标签样式 */
            QLabel {
                color: #2c3e50;
                background-color: transparent;
            }

            /* 复选框样式 */
            QCheckBox {
                color: #2c3e50;
                background-color: transparent;
            }

            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                background-color: #ffffff;
            }

            QCheckBox::indicator:checked {
                background-color: #3498db;
                border-color: #3498db;
            }
            """

            self.setStyleSheet(style_sheet)
            logger.debug("标签设计器样式表应用成功")

        except Exception as e:
            logger.error(f"应用标签设计器样式表失败: {e}")
    
    def _init_ui(self):
        """初始化界面"""
        try:
            # 创建主布局
            main_layout = self.designer_ui_manager.create_main_layout()
            
            # 创建左侧模板管理面板
            left_panel = self.template_ui_manager.create_template_panel(self)
            self.designer_ui_manager.main_splitter.addWidget(left_panel)
            
            # 创建中间可视化编辑器
            center_editor = self.designer_ui_manager.create_center_editor()
            self.designer_ui_manager.main_splitter.addWidget(center_editor)
            
            # 创建右侧面板（元素列表 + 属性编辑）
            right_panel = self._create_right_panel()
            self.designer_ui_manager.main_splitter.addWidget(right_panel)
            
            # 设置分割器比例
            self.designer_ui_manager.set_splitter_sizes([280, 800, 320])
            
            logger.debug("界面初始化完成")
            
        except Exception as e:
            logger.error(f"初始化界面失败: {e}")
    
    def _create_right_panel(self):
        """创建右侧面板"""
        try:
            from PyQt5.QtWidgets import QWidget, QVBoxLayout
            
            panel = QWidget()
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(10)
            
            # 元素管理面板
            elements_panel = self.designer_ui_manager.create_elements_panel()
            layout.addWidget(elements_panel)
            
            # 属性编辑面板
            property_widget = self.property_manager.create_property_widget(panel)
            if property_widget:
                layout.addWidget(property_widget)
            
            return panel
            
        except Exception as e:
            logger.error(f"创建右侧面板失败: {e}")
            return QWidget()
    
    def _connect_signals(self):
        """连接管理器间的信号"""
        try:
            # 模板UI管理器信号连接
            self.template_ui_manager.template_selected.connect(self._on_template_selected)
            
            # 设计器UI管理器信号连接
            self.designer_ui_manager.element_selected.connect(self._on_element_selected)
            self.designer_ui_manager.add_text_requested.connect(self._on_add_text_requested)
            self.designer_ui_manager.add_qr_requested.connect(self._on_add_qr_requested)
            self.designer_ui_manager.add_barcode_requested.connect(self._on_add_barcode_requested)
            self.designer_ui_manager.remove_element_requested.connect(self._on_remove_element_requested)
            self.designer_ui_manager.add_element_requested.connect(self._on_add_element_requested)
            self.designer_ui_manager.insert_parameter_to_selected.connect(self._on_insert_parameter_to_selected)

            # 元素管理器信号连接
            self.element_manager.element_added.connect(self._on_element_added)
            self.element_manager.element_removed.connect(self._on_element_removed)
            self.element_manager.template_changed.connect(self._on_template_changed)

            # 属性管理器信号连接
            self.property_manager.element_updated.connect(self._on_element_property_updated)



            logger.debug("信号连接完成")
            
        except Exception as e:
            logger.error(f"连接信号失败: {e}")

    def _init_data(self):
        """初始化数据"""
        try:
            # 延迟加载数据以提升启动速度，确保UI完全创建后再加载
            QTimer.singleShot(200, self._load_initial_data)

        except Exception as e:
            logger.error(f"初始化数据失败: {e}")

    def _load_initial_data(self):
        """加载初始数据"""
        try:
            logger.debug("开始加载初始数据...")

            # 检查模板UI管理器是否存在
            if not hasattr(self, 'template_ui_manager') or not self.template_ui_manager:
                logger.error("模板UI管理器未初始化")
                return

            # 检查模板面板是否已创建
            preset_list_exists = hasattr(self.template_ui_manager, 'preset_list')
            preset_list_valid = preset_list_exists and self.template_ui_manager.preset_list is not None

            logger.debug(f"模板面板检查: preset_list存在={preset_list_exists}, 有效={preset_list_valid}")

            if not preset_list_valid:
                logger.warning("模板面板尚未创建，延迟加载数据")
                QTimer.singleShot(100, self._load_initial_data)
                return

            logger.debug("模板面板已创建，开始加载模板数据...")

            # 直接手动加载模板列表
            self._manual_load_templates()

            # 设置默认模板（选择第一个预设模板）
            self._set_default_template()

            logger.info("初始数据加载完成")

        except Exception as e:
            logger.error(f"加载初始数据失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _manual_load_templates(self):
        """手动加载模板列表"""
        try:

            # 检查模板UI管理器
            if not self.template_ui_manager:
                logger.error("模板UI管理器未初始化")
                return

            # 检查模板管理器
            if not self.template_ui_manager.template_manager:
                logger.error("模板管理器未初始化")
                return

            # 直接获取控件引用并加载模板
            preset_list = self.template_ui_manager.preset_list
            user_list = self.template_ui_manager.user_list

            logger.debug(f"preset_list控件: {preset_list}")
            logger.debug(f"user_list控件: {user_list}")
            logger.debug(f"preset_list类型: {type(preset_list)}")
            logger.debug(f"user_list类型: {type(user_list)}")
            logger.debug(f"preset_list is None: {preset_list is None}")
            logger.debug(f"user_list is None: {user_list is None}")

            # 手动加载预设模板
            try:
                if preset_list is not None:
                    logger.debug("手动加载预设模板...")
                    preset_list.clear()

                    preset_templates = self.template_ui_manager.template_manager.get_preset_templates()
                    logger.debug(f"获取到 {len(preset_templates)} 个预设模板")

                    for i, template in enumerate(preset_templates):
                        from PyQt5.QtWidgets import QListWidgetItem
                        from PyQt5.QtCore import Qt

                        item = QListWidgetItem(template.name)
                        item.setData(Qt.ItemDataRole.UserRole, template)
                        preset_list.addItem(item)
                        logger.debug(f"添加预设模板 {i+1}: {template.name}")

                    logger.info(f"✅ 预设模板手动加载完成，共 {preset_list.count()} 个")
                else:
                    logger.warning("preset_list控件为None")
            except Exception as e:
                logger.error(f"加载预设模板时出错: {e}")

            # 手动加载用户模板
            try:
                if user_list is not None:
                    logger.debug("手动加载用户模板...")
                    user_list.clear()

                    user_templates = self.template_ui_manager.template_manager.get_user_templates()
                    logger.debug(f"获取到 {len(user_templates)} 个用户模板")

                    for i, template in enumerate(user_templates):
                        from PyQt5.QtWidgets import QListWidgetItem
                        from PyQt5.QtCore import Qt

                        item = QListWidgetItem(template.name)
                        item.setData(Qt.ItemDataRole.UserRole, template)
                        user_list.addItem(item)
                        logger.debug(f"添加用户模板 {i+1}: {template.name}")

                    logger.info(f"✅ 用户模板手动加载完成，共 {user_list.count()} 个")
                else:
                    logger.warning("user_list控件为None")
            except Exception as e:
                logger.error(f"加载用户模板时出错: {e}")

            logger.info("✅ 手动模板加载完成")

        except Exception as e:
            logger.error(f"手动加载模板失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _set_default_template(self):
        """设置默认模板"""
        try:
            # 尝试获取第一个预设模板
            if self.template_ui_manager.template_manager:
                preset_templates = self.template_ui_manager.template_manager.get_preset_templates()
                if preset_templates:
                    default_template = preset_templates[0]
                    self._on_template_selected(default_template)

                    # 在UI中选中这个模板
                    if hasattr(self.template_ui_manager, 'preset_list') and self.template_ui_manager.preset_list:
                        self.template_ui_manager.preset_list.setCurrentRow(0)

                    logger.debug(f"设置默认模板: {default_template.name}")
                    return

            # 如果没有预设模板，创建一个默认模板
            self._create_default_template()

        except Exception as e:
            logger.error(f"设置默认模板失败: {e}")

    def _create_default_template(self):
        """创建默认模板"""
        try:
            if self.template_ui_manager.template_manager:
                # 创建一个基本的默认模板
                default_template = self.template_ui_manager.template_manager.create_template("默认模板")
                if default_template:
                    self._on_template_selected(default_template)
                    logger.debug("创建并设置默认模板")

        except Exception as e:
            logger.error(f"创建默认模板失败: {e}")
    
    def _on_template_selected(self, template: LabelTemplateConfig):
        """处理模板选择"""
        try:
            self.current_template = template

            # 关键修改将当前选择的模板ID保存到配置管理器
            if hasattr(template, 'template_id') and template.template_id:
                self.config_manager.set('label_template.current_template_id', template.template_id)
                logger.info(f"✅ 当前模板ID已保存到配置: {template.template_id}")
            else:
                logger.warning(f"模板缺少template_id属性: {template.name}")

            # 更新各个管理器
            self.element_manager.set_current_template(template)
            self.designer_ui_manager.set_current_template(template)

            # 新增通知主窗口模板配置已变更，触发打印管理器重新加载
            try:
                # 发送配置变更信号，触发标签打印管理器重新加载模板配置
                if hasattr(self.config_manager, 'config_changed'):
                    self.config_manager.config_changed.emit('label_template.current_template_id', template.template_id)
                    logger.debug("✅ 已发送模板配置变更信号")
            except Exception as signal_error:
                logger.warning(f"发送模板配置变更信号失败: {signal_error}")

            logger.info(f"✅ 模板选择完成: {template.name} (ID: {getattr(template, 'template_id', 'N/A')})")

        except Exception as e:
            logger.error(f"处理模板选择失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def _on_element_selected(self, element_id: str):
        """处理元素选择"""
        try:
            # 保存当前选中的元素ID
            self.selected_element_id = element_id

            # 获取元素
            element = self.element_manager.get_element(element_id)

            # 更新属性管理器
            self.property_manager.set_current_element(element)

            # 更新UI管理器的选中文本元素状态
            if element and hasattr(self.designer_ui_manager, 'selected_text_element'):
                element_type = getattr(element, 'element_type', element.get('element_type') if isinstance(element, dict) else None)
                if element_type == 'text':
                    self.designer_ui_manager.selected_text_element = element_id
                    logger.debug(f"设置选中的文本元素: {element_id}")
                else:
                    self.designer_ui_manager.selected_text_element = None
                    logger.debug(f"选中的元素不是文本类型: {element_type}")

            logger.debug(f"元素选择: {element_id}")

        except Exception as e:
            logger.error(f"处理元素选择失败: {e}")
    
    def _on_add_text_requested(self):
        """处理添加文本请求"""
        try:
            logger.debug("🎯 收到添加文本请求")
            logger.debug(f"当前模板: {self.current_template.name if self.current_template else 'None'}")

            if not self.current_template:
                logger.warning("没有当前模板，显示警告")
                QMessageBox.warning(self, "警告", "请先选择或创建一个模板")
                return

            logger.debug("开始调用元素管理器添加文本元素")
            success = self.element_manager.add_text_element()
            logger.debug(f"添加文本元素结果: {success}")

            if not success:
                logger.error("添加文本元素失败，显示错误消息")
                QMessageBox.critical(self, "错误", "添加文本元素失败")
            else:
                logger.debug("✅ 文本元素添加成功")

        except Exception as e:
            logger.error(f"处理添加文本请求失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def _on_add_qr_requested(self):
        """处理添加二维码请求"""
        try:
            logger.debug("🎯 收到添加二维码请求")
            logger.debug(f"当前模板: {self.current_template.name if self.current_template else 'None'}")

            if not self.current_template:
                logger.warning("没有当前模板，显示警告")
                QMessageBox.warning(self, "警告", "请先选择或创建一个模板")
                return

            logger.debug("开始调用元素管理器添加二维码元素")
            success = self.element_manager.add_qr_element()
            logger.debug(f"添加二维码元素结果: {success}")

            if not success:
                logger.error("添加二维码元素失败，显示错误消息")
                QMessageBox.critical(self, "错误", "添加二维码元素失败")
            else:
                logger.debug("✅ 二维码元素添加成功")

        except Exception as e:
            logger.error(f"处理添加二维码请求失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _on_add_barcode_requested(self):
        """处理添加条形码请求"""
        try:
            logger.debug("🎯 收到添加条形码请求")
            logger.debug(f"当前模板: {self.current_template.name if self.current_template else 'None'}")

            if not self.current_template:
                logger.warning("没有当前模板，显示警告")
                QMessageBox.warning(self, "警告", "请先选择或创建一个模板")
                return

            logger.debug("开始调用元素管理器添加条形码元素")
            success = self.element_manager.add_barcode_element()
            logger.debug(f"添加条形码元素结果: {success}")

            if not success:
                logger.error("添加条形码元素失败，显示错误消息")
                QMessageBox.critical(self, "错误", "添加条形码元素失败")
            else:
                logger.debug("✅ 条形码元素添加成功")

        except Exception as e:
            logger.error(f"处理添加条形码请求失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def _on_remove_element_requested(self, element_id: str):
        """处理删除元素请求"""
        try:
            # 获取元素信息用于确认对话框
            element_name = "未知元素"
            if self.current_template:
                for element in self.current_template.elements:
                    if hasattr(element, 'element_id') and element.element_id == element_id:
                        element_name = f"{element.element_id} ({element.element_type})"
                        break
                    elif isinstance(element, dict) and element.get('element_id') == element_id:
                        element_name = f"{element.get('element_id')} ({element.get('element_type', 'unknown')})"
                        break

            # 删除确认对话框
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除元素 '{element_name}' 吗？\n\n此操作无法撤销。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                success = self.element_manager.remove_element(element_id)
                if success:
                    logger.info(f"✅ 元素删除成功: {element_name}")

                    # 注意：不需要再次调用visual_editor.remove_element，因为element_manager.remove_element已经处理了
                    # 这避免了重复删除导致的问题

                    # 更新元素列表
                    if hasattr(self.designer_ui_manager, 'update_elements_list'):
                        self.designer_ui_manager.update_elements_list()
                        logger.debug("✅ 元素列表已更新")

                    # 清除选中状态
                    self.selected_element_id = None
                    if hasattr(self.designer_ui_manager, 'selected_text_element'):
                        self.designer_ui_manager.selected_text_element = None

                    # 清除属性编辑器
                    if hasattr(self, 'property_manager') and self.property_manager:
                        self.property_manager.set_current_element(None)

                    # 强制刷新可视化编辑器
                    if hasattr(self.designer_ui_manager, 'visual_editor') and self.designer_ui_manager.visual_editor:
                        self.designer_ui_manager.visual_editor.scene.update()
                        self.designer_ui_manager.visual_editor.view.update()
                        logger.debug("✅ 可视化编辑器已强制刷新")

                else:
                    QMessageBox.warning(self, "删除失败", f"删除元素 '{element_name}' 失败")
                    logger.warning(f"❌ 元素删除失败: {element_name}")

        except Exception as e:
            logger.error(f"处理删除元素请求失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _on_add_element_requested(self, param_key: str, display_name: str):
        """处理添加元素请求"""
        try:
            if not self.element_manager:
                logger.warning("元素管理器未初始化")
                return

            logger.info(f"🎯 处理添加元素请求: {param_key} ({display_name})")

            # 检查是否是带参数的文本元素
            if param_key.startswith('text_with_param:'):
                # 提取参数名
                actual_param = param_key.replace('text_with_param:', '')
                success = self.element_manager.add_text_element()

                if success:
                    # 获取最新添加的元素并设置内容
                    if self.current_template and self.current_template.elements:
                        latest_element = self.current_template.elements[-1]
                        latest_element.content = f"{{{actual_param}}}"
                        logger.info(f"✅ 文本元素内容已设置为: {{{actual_param}}}")

                        # 更新可视化编辑器
                        if hasattr(self.designer_ui_manager, 'visual_editor') and self.designer_ui_manager.visual_editor:
                            self.designer_ui_manager.visual_editor.scene.update_element(latest_element)

            else:
                # 根据参数类型添加对应元素
                success = False
                if param_key == 'qr_code':
                    success = self.element_manager.add_qr_element()
                elif param_key == 'barcode':
                    success = self.element_manager.add_barcode_element()
                else:
                    success = self.element_manager.add_text_element()

            if success:
                logger.info(f"✅ 成功添加参数元素: {param_key} ({display_name})")
            else:
                logger.warning(f"❌ 添加参数元素失败: {param_key}")

        except Exception as e:
            logger.error(f"处理添加元素请求失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _on_element_property_updated(self, element_id: str, properties: dict):
        """处理元素属性更新"""
        try:
            if not self.element_manager:
                logger.warning("元素管理器未初始化")
                return

            # 更新元素属性
            success = self.element_manager.update_element(element_id, properties)

            if success:
                # 更新可视化编辑器
                if hasattr(self.designer_ui_manager, 'visual_editor') and self.designer_ui_manager.visual_editor:
                    self.designer_ui_manager.visual_editor.update_element(element_id, **properties)

                # 更新元素列表显示
                self.designer_ui_manager.update_elements_list()

                logger.debug(f"元素属性更新成功: {element_id}")
            else:
                logger.warning(f"元素属性更新失败: {element_id}")

        except Exception as e:
            logger.error(f"处理元素属性更新失败: {e}")

    def _get_element_type_for_param(self, param_key: str) -> str:
        """根据参数键获取元素类型"""
        try:
            # 特殊参数映射到特定元素类型
            if param_key in ['qr_code']:
                return 'qr_code'
            elif param_key in ['barcode']:
                return 'barcode'
            else:
                return 'text'  # 默认为文本类型

        except Exception as e:
            logger.error(f"获取参数元素类型失败: {e}")
            return 'text'

    def _on_element_added(self, element_id: str):
        """处理元素添加"""
        try:
            logger.info(f"🎯 处理元素添加: {element_id}")

            # 关键修复获取新添加的元素并添加到可视化编辑器
            if self.current_template:
                # 查找新添加的元素
                new_element = None
                for element in self.current_template.elements:
                    if getattr(element, 'element_id', None) == element_id:
                        new_element = element
                        break

                if new_element:
                    # 添加到可视化编辑器场景
                    if hasattr(self.designer_ui_manager, 'visual_editor') and self.designer_ui_manager.visual_editor:
                        self.designer_ui_manager.visual_editor.scene.add_element(new_element)
                        logger.info(f"✅ 新元素已添加到可视化编辑器: {element_id}")
                    else:
                        logger.warning("可视化编辑器不可用")
                else:
                    logger.warning(f"未找到新添加的元素: {element_id}")

            # 更新界面
            self.designer_ui_manager.update_elements_list()

            # 选择新添加的元素
            self.designer_ui_manager.select_element(element_id)

            logger.info(f"✅ 元素添加处理完成: {element_id}")

        except Exception as e:
            logger.error(f"处理元素添加失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def _on_element_removed(self, element_id: str):
        """处理元素删除"""
        try:
            # 更新可视化编辑器场景
            if hasattr(self.designer_ui_manager, 'visual_editor') and self.designer_ui_manager.visual_editor:
                self.designer_ui_manager.visual_editor.scene.remove_element(element_id)
                logger.debug(f"✅ 可视化编辑器场景已移除元素: {element_id}")

            # 更新界面
            self.designer_ui_manager.update_elements_list()

            # 清除属性编辑器
            self.property_manager.set_current_element(None)

            # 清除选中状态
            self.selected_element_id = None
            if hasattr(self.designer_ui_manager, 'selected_text_element'):
                self.designer_ui_manager.selected_text_element = None

        except Exception as e:
            logger.error(f"处理元素删除失败: {e}")
    
    def _on_template_changed(self):
        """处理模板变更"""
        try:
            # 更新界面
            self.designer_ui_manager.update_elements_list()
            
        except Exception as e:
            logger.error(f"处理模板变更失败: {e}")
    

    
    def get_current_template(self) -> Optional[LabelTemplateConfig]:
        """获取当前模板（向后兼容）"""
        return self.current_template
    
    def cleanup(self):
        """清理资源"""
        try:
            # 清理各个管理器
            if hasattr(self, 'property_manager'):
                self.property_manager.cleanup()
            
            if hasattr(self, 'element_manager'):
                self.element_manager.cleanup()
            
            if hasattr(self, 'template_ui_manager'):
                self.template_ui_manager.cleanup()
            
            if hasattr(self, 'designer_ui_manager'):
                self.designer_ui_manager.cleanup()
            
            logger.info("标签设计器对话框资源清理完成")
            
        except Exception as e:
            logger.error(f"清理资源失败: {e}")
    
    def _on_insert_parameter_to_selected(self, param_key: str):
        """处理插入参数到选中元素"""
        try:
            logger.info(f"🎯 插入参数到选中元素: {param_key}")

            # 检查是否有选中的元素
            if not hasattr(self, 'selected_element_id') or not self.selected_element_id:
                logger.warning("没有选中的元素，无法插入参数")
                return

            # 获取选中的元素
            selected_element = None
            if self.current_template:
                for element in self.current_template.elements:
                    element_id = getattr(element, 'element_id', element.get('element_id') if isinstance(element, dict) else None)
                    if element_id == self.selected_element_id:
                        selected_element = element
                        break

            if not selected_element:
                logger.warning(f"未找到选中的元素: {self.selected_element_id}")
                return

            # 检查是否为文本元素
            element_type = getattr(selected_element, 'element_type', selected_element.get('element_type') if isinstance(selected_element, dict) else None)
            if element_type != 'text':
                logger.warning(f"选中的元素不是文本类型: {element_type}")
                return

            # 获取当前内容
            current_content = getattr(selected_element, 'content', selected_element.get('content', '') if isinstance(selected_element, dict) else '')

            # 插入参数到内容末尾
            new_content = current_content + f"{{{param_key}}}"

            # 更新元素内容
            if hasattr(selected_element, 'content'):
                selected_element.content = new_content
            elif isinstance(selected_element, dict):
                selected_element['content'] = new_content

            # 更新属性编辑器显示
            if hasattr(self, 'property_manager') and self.property_manager:
                self.property_manager.set_current_element(selected_element)

            # 更新可视化编辑器
            if hasattr(self, 'designer_ui_manager') and self.designer_ui_manager.visual_editor:
                # 修复使用正确的更新方法
                self.designer_ui_manager.visual_editor.scene.update_element(selected_element)

            logger.info(f"✅ 参数插入成功: {param_key} -> '{new_content}'")

        except Exception as e:
            logger.error(f"插入参数到选中元素失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.cleanup()
        super().closeEvent(event)
