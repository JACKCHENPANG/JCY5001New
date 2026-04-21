#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标签设计器UI管理器
负责标签设计器的整体界面管理

Author: Jack
Date: 2025-06-04
"""

import logging
from typing import Optional, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QPushButton, QListWidget, QListWidgetItem, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer, QMimeData
from PyQt5.QtGui import QDrag

# 导入标签相关类
from .label_template_config import LabelTemplateConfig, LabelElement

logger = logging.getLogger(__name__)


class DraggableParameterList(QListWidget):
    """支持拖拽的参数列表控件"""

    def __init__(self, parent=None):
        """初始化拖拽参数列表"""
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.DragOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def startDrag(self, supportedActions):
        """开始拖拽"""
        item = self.currentItem()
        if item:
            param_key = item.data(Qt.ItemDataRole.UserRole)
            if param_key:
                # 创建拖拽对象
                drag = QDrag(self)
                mimeData = QMimeData()
                mimeData.setText(param_key)
                drag.setMimeData(mimeData)

                logger.debug(f"开始拖拽参数: {param_key}")

                # 执行拖拽
                drag.exec_(Qt.DropAction.CopyAction)


# 安全导入可视化编辑器
try:
    from .visual_label_editor import VisualLabelEditor
    VISUAL_EDITOR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"可视化编辑器导入失败: {e}")
    VisualLabelEditor = None
    VISUAL_EDITOR_AVAILABLE = False


class LabelDesignerUIManager(QObject):
    """
    标签设计器UI管理器
    
    职责：
    - 管理设计器的整体界面布局
    - 协调各个UI组件
    - 处理界面交互逻辑
    """
    
    # 信号定义
    element_selected = pyqtSignal(str)  # 元素选择信号 (element_id)
    add_text_requested = pyqtSignal()  # 添加文本请求
    add_qr_requested = pyqtSignal()  # 添加二维码请求
    add_barcode_requested = pyqtSignal()  # 添加条形码请求
    remove_element_requested = pyqtSignal(str)  # 删除元素请求 (element_id)
    add_element_requested = pyqtSignal(str, str)  # 添加元素请求信号 (param_key, display_name)
    insert_parameter_to_selected = pyqtSignal(str)  # 插入参数到选中元素
    
    def __init__(self, parent_widget: QWidget):
        """
        初始化标签设计器UI管理器
        
        Args:
            parent_widget: 父窗口部件
        """
        super().__init__(parent_widget)
        
        self.parent_widget = parent_widget
        self.current_template = None
        self.selected_text_element = None  # 当前选中的文本元素ID (str | None)

        # UI组件
        self.main_splitter = None
        self.visual_editor = None
        # 移除删除elements_list，不再需要元素列表控件
        self.toolbar_buttons = {}
        
        logger.debug("标签设计器UI管理器初始化完成")
    
    def create_main_layout(self) -> QVBoxLayout:
        """创建主布局"""
        try:
            main_layout = QVBoxLayout(self.parent_widget)
            main_layout.setContentsMargins(15, 15, 15, 15)
            main_layout.setSpacing(12)
            
            # 创建工具栏
            toolbar = self._create_toolbar()
            main_layout.addWidget(toolbar)
            
            # 创建主分割器
            self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
            main_layout.addWidget(self.main_splitter)
            
            # 创建底部按钮
            bottom_buttons = self._create_bottom_buttons()
            main_layout.addWidget(bottom_buttons)
            
            logger.debug("主布局创建完成")
            return main_layout
            
        except Exception as e:
            logger.error(f"创建主布局失败: {e}")
            return QVBoxLayout(self.parent_widget)
    
    def _create_toolbar(self) -> QWidget:
        """创建工具栏"""
        try:
            toolbar = QWidget()
            layout = QHBoxLayout(toolbar)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(10)
            
            # 添加元素按钮
            add_text_btn = QPushButton("添加文本")
            add_text_btn.clicked.connect(self._on_add_text_clicked)
            layout.addWidget(add_text_btn)
            self.toolbar_buttons['add_text'] = add_text_btn

            add_qr_btn = QPushButton("添加二维码")
            add_qr_btn.clicked.connect(self._on_add_qr_clicked)
            layout.addWidget(add_qr_btn)
            self.toolbar_buttons['add_qr'] = add_qr_btn

            add_barcode_btn = QPushButton("添加条形码")
            add_barcode_btn.clicked.connect(self._on_add_barcode_clicked)
            layout.addWidget(add_barcode_btn)
            self.toolbar_buttons['add_barcode'] = add_barcode_btn

            layout.addStretch()

            # 删除元素按钮
            remove_btn = QPushButton("删除元素")
            remove_btn.clicked.connect(self._on_remove_element)
            layout.addWidget(remove_btn)
            self.toolbar_buttons['remove'] = remove_btn

            # 初始化时禁用所有添加按钮
            self._disable_all_add_buttons()
            logger.debug("工具栏按钮初始化完成，默认禁用状态")

            logger.debug("工具栏创建完成")
            return toolbar
            
        except Exception as e:
            logger.error(f"创建工具栏失败: {e}")
            return QWidget()
    
    def create_center_editor(self) -> QWidget:
        """创建中间可视化编辑器"""
        try:
            if VISUAL_EDITOR_AVAILABLE and VisualLabelEditor:
                # 创建可视化编辑器
                self.visual_editor = VisualLabelEditor()
                
                # 连接信号
                if hasattr(self.visual_editor, 'element_selected'):
                    self.visual_editor.element_selected.connect(self.element_selected.emit)
                
                logger.debug("可视化编辑器创建完成")
                return self.visual_editor
            else:
                # 创建占位符
                placeholder = QLabel("可视化编辑器\n\n功能开发中...")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setStyleSheet("""
                    background-color: #ecf0f1;
                    border: 2px dashed #bdc3c7;
                    border-radius: 10px;
                    font-size: 14pt;
                    color: #2c3e50;
                    padding: 50px;
                """)
                placeholder.setMinimumHeight(400)
                
                logger.debug("可视化编辑器占位符创建完成")
                return placeholder
                
        except Exception as e:
            logger.error(f"创建中间编辑器失败: {e}")
            return QLabel("编辑器创建失败")
    
    def create_elements_panel(self) -> QWidget:
        """创建元素管理面板"""
        try:
            logger.debug("开始创建元素管理面板...")

            panel = QWidget()
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)

            # 可用参数组
            logger.debug("创建可用参数组...")
            params_group = QGroupBox("可用参数")
            params_layout = QVBoxLayout(params_group)

            # 参数操作说明
            help_label = QLabel("💡 使用方法：\n• 双击参数：直接创建对应元素\n• 拖拽参数：拖拽到画布创建元素\n• 选中文本元素后单击：插入到文本内容")
            help_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px; background: #f5f5f5; border-radius: 3px;")
            help_label.setWordWrap(True)
            params_layout.addWidget(help_label)

            logger.debug("创建参数列表控件...")
            self.params_list = DraggableParameterList()

            # 验证控件创建成功
            if self.params_list is None:
                logger.error("参数列表控件创建失败")
                raise Exception("参数列表控件创建失败")

            logger.debug("参数列表控件创建成功，设置属性...")
            self.params_list.setMinimumHeight(200)  # 设置最小高度
            self.params_list.setMaximumHeight(300)  # 增加最大高度
            self.params_list.setDragDropMode(QListWidget.DragDropMode.DragOnly)  # 启用拖拽
            self.params_list.setDefaultDropAction(Qt.DropAction.CopyAction)  # 设置拖拽动作
            self.params_list.itemDoubleClicked.connect(self._on_param_double_clicked)
            self.params_list.itemClicked.connect(self._on_param_selected)  # 添加单击选择处理

            logger.debug("开始填充参数列表...")
            # 立即填充参数列表
            self._populate_available_params()

            logger.debug("将参数列表添加到布局...")
            params_layout.addWidget(self.params_list)
            layout.addWidget(params_group)

            # 移除删除模板元素选择组，用户不需要这个功能
            # 用户可以直接在画布上选择和编辑元素，不需要额外的元素列表

            logger.debug("元素管理面板创建完成（已移除模板元素选择组）")
            return panel

        except Exception as e:
            logger.error(f"创建元素管理面板失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

            # 返回一个简单的占位符面板
            fallback_panel = QWidget()
            fallback_layout = QVBoxLayout(fallback_panel)
            fallback_label = QLabel("元素管理面板创建失败\n请检查日志获取详细信息")
            fallback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback_layout.addWidget(fallback_label)
            return fallback_panel

    def _populate_available_params(self):
        """填充可用参数列表"""
        try:
            # 使用更安全的检查方式
            if self.params_list is None:
                logger.error("params_list 控件未初始化")
                return

            logger.debug(f"params_list 控件状态: {type(self.params_list)}")

            # 清空现有项目
            self.params_list.clear()

            # 定义可用的参数
            available_params = [
                ("电池码", "battery_code", "电池唯一标识码"),
                ("通道号", "channel_number", "测试通道编号"),
                ("电压值", "voltage", "电池电压测量值"),
                ("Rs值", "rs_value", "串联电阻值"),
                ("Rct值", "rct_value", "电荷转移电阻值"),
                ("Rs档位", "rs_grade", "Rs阻抗档位等级"),
                ("Rct档位", "rct_grade", "Rct阻抗档位等级"),
                ("档位结果", "grade_result", "Rs档位-Rct档位综合评级"),
                ("测试结果", "is_pass", "合格/不合格状态"),
                ("测试时间", "timestamp", "测试完成时间"),
                ("批次号", "batch_number", "生产批次编号"),
                ("操作员", "operator", "测试操作员"),
                ("离群率", "outlier_rate", "数据离群检测率"),
                ("二维码", "qr_code", "包含电池信息的二维码"),
                ("条形码", "barcode", "包含电池信息的条形码")
            ]

            logger.debug(f"开始填充可用参数列表，共{len(available_params)}个参数")

            for i, (display_name, param_key, description) in enumerate(available_params):
                try:
                    item_text = f"{display_name} ({param_key})"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, param_key)
                    item.setToolTip(description)

                    # 设置拖拽标志
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)

                    self.params_list.addItem(item)
                    logger.debug(f"添加参数 {i+1}: {item_text}")
                except Exception as item_error:
                    logger.error(f"添加参数项失败 {display_name}: {item_error}")

            # 验证添加结果
            actual_count = self.params_list.count()
            logger.info(f"可用参数列表填充完成，预期{len(available_params)}个，实际{actual_count}个参数")

            if actual_count == 0:
                logger.warning("参数列表为空，可能存在问题")

            # 强制刷新控件
            self.params_list.update()

        except Exception as e:
            logger.error(f"填充可用参数列表失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def _create_bottom_buttons(self) -> QWidget:
        """创建底部按钮"""
        try:
            button_widget = QWidget()
            layout = QHBoxLayout(button_widget)
            layout.setContentsMargins(0, 10, 0, 0)
            
            layout.addStretch()
            
            # 预览按钮
            preview_btn = QPushButton("预览")
            preview_btn.clicked.connect(self._on_preview)
            layout.addWidget(preview_btn)

            # 预打印按钮
            preprint_btn = QPushButton("预打印")
            preprint_btn.clicked.connect(self._on_preprint)
            layout.addWidget(preprint_btn)
            
            # 确定按钮
            ok_btn = QPushButton("确定")
            ok_btn.clicked.connect(self.parent_widget.accept)
            layout.addWidget(ok_btn)
            
            # 取消按钮
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(self.parent_widget.reject)
            layout.addWidget(cancel_btn)
            
            return button_widget
            
        except Exception as e:
            logger.error(f"创建底部按钮失败: {e}")
            return QWidget()
    
    def set_current_template(self, template: Optional[LabelTemplateConfig]):
        """设置当前模板"""
        try:
            self.current_template = template

            # 更新可视化编辑器
            if self.visual_editor and hasattr(self.visual_editor, 'set_template') and template:
                self.visual_editor.set_template(template)
                logger.debug(f"可视化编辑器已设置模板: {template.name}")
            elif not self.visual_editor:
                logger.warning("可视化编辑器未初始化")
            elif not template:
                logger.warning("模板为空，无法设置到可视化编辑器")

            # 更新元素列表
            self.update_elements_list()

            logger.debug(f"设置当前模板: {template.name if template else 'None'}")

        except Exception as e:
            logger.error(f"设置当前模板失败: {e}")
    
    def update_elements_list(self):
        """更新元素列表（已移除元素列表控件，此方法保留以兼容现有代码）"""
        try:
            # 移除不再更新元素列表，因为已删除元素列表控件
            # 用户可以直接在画布上查看和选择元素
            logger.debug("元素列表更新跳过（已移除元素列表控件）")

        except Exception as e:
            logger.error(f"更新元素列表失败: {e}")

    def select_element(self, element_id: str):
        """选择指定元素（仅在可视化编辑器中选择）"""
        try:
            # 移除不再在元素列表中选择，只在可视化编辑器中选择

            # 在可视化编辑器中选择元素
            if self.visual_editor and hasattr(self.visual_editor, 'select_element'):
                self.visual_editor.select_element(element_id)

            logger.debug(f"选择元素: {element_id}")

        except Exception as e:
            logger.error(f"选择元素失败: {e}")

    def _on_element_list_selected(self, item: QListWidgetItem):
        """元素列表选择处理（已移除，保留以兼容现有代码）"""
        try:
            # 移除元素列表已删除，此方法不再需要
            logger.debug("元素列表选择处理跳过（已移除元素列表控件）")

        except Exception as e:
            logger.error(f"元素列表选择处理失败: {e}")

    def _on_param_double_clicked(self, item: QListWidgetItem):
        """参数双击处理 - 智能添加元素到模板"""
        try:
            param_key = item.data(Qt.ItemDataRole.UserRole)
            if not param_key:
                return

            # 获取参数显示名称
            param_text = item.text()
            display_name = param_text.split(' (')[0]

            logger.info(f"🎯 双击参数: {param_key} ({display_name})")

            # 智能判断创建元素类型
            if param_key in ['qr_code', 'battery_code']:
                # 二维码相关参数 - 创建二维码元素
                logger.debug("创建二维码元素")
                self.add_element_requested.emit('qr_code', '二维码')
            elif param_key == 'barcode':
                # 条形码参数 - 创建条形码元素
                logger.debug("创建条形码元素")
                self.add_element_requested.emit('barcode', '条形码')
            else:
                # 其他参数 - 创建文本元素并设置内容
                logger.debug(f"创建文本元素，内容: {{{param_key}}}")
                self.add_element_requested.emit(f'text_with_param:{param_key}', display_name)

        except Exception as e:
            logger.error(f"参数双击处理失败: {e}")

    def _on_param_selected(self, item: QListWidgetItem):
        """参数选择处理 - 智能插入到选中的文本元素"""
        try:
            param_key = item.data(Qt.ItemDataRole.UserRole)
            if not param_key:
                return

            # 检查是否有选中的文本元素
            if hasattr(self, 'selected_text_element') and self.selected_text_element:
                # 如果有选中的文本元素，直接插入参数
                logger.info(f"🎯 插入参数到选中文本元素: {param_key}")
                self.insert_parameter_to_selected.emit(param_key)
            else:
                # 没有选中文本元素，只是选择参数
                logger.debug(f"参数选择: {param_key}")

            # 根据参数类型更新工具栏按钮状态
            self._update_toolbar_buttons(param_key)

        except Exception as e:
            logger.error(f"参数选择处理失败: {e}")

    def _update_toolbar_buttons(self, param_key: str):
        """根据选中的参数类型更新工具栏按钮状态"""
        try:
            # 修复：当有模板时，所有添加按钮都应该可用
            # 用户可以添加任何类型的元素，然后在属性中设置内容和参数
            if self.current_template:
                self._enable_all_add_buttons()
                logger.debug(f"有模板时启用所有添加按钮，当前选择参数: {param_key}")
            else:
                self._disable_all_add_buttons()
                logger.debug("无模板时禁用所有添加按钮")

        except Exception as e:
            logger.error(f"更新工具栏按钮状态失败: {e}")

    def _disable_all_add_buttons(self):
        """禁用所有添加按钮"""
        try:
            for btn_key in ['add_text', 'add_qr', 'add_barcode']:
                if btn_key in self.toolbar_buttons:
                    self.toolbar_buttons[btn_key].setEnabled(False)

            logger.debug("所有添加按钮已禁用")

        except Exception as e:
            logger.error(f"禁用添加按钮失败: {e}")

    def _enable_all_add_buttons(self):
        """启用所有添加按钮"""
        try:
            for btn_key in ['add_text', 'add_qr', 'add_barcode']:
                if btn_key in self.toolbar_buttons:
                    self.toolbar_buttons[btn_key].setEnabled(True)

            logger.debug("所有添加按钮已启用")

        except Exception as e:
            logger.error(f"启用添加按钮失败: {e}")

    def _on_add_text_clicked(self):
        """添加文本按钮点击处理"""
        try:
            logger.debug("🔘 添加文本按钮被点击")
            logger.debug(f"按钮启用状态: {self.toolbar_buttons.get('add_text', {}).isEnabled() if 'add_text' in self.toolbar_buttons else 'N/A'}")
            self.add_text_requested.emit()
            logger.debug("✅ 添加文本信号已发射")
        except Exception as e:
            logger.error(f"添加文本按钮点击处理失败: {e}")

    def _on_add_qr_clicked(self):
        """添加二维码按钮点击处理"""
        try:
            logger.debug("🔘 添加二维码按钮被点击")
            logger.debug(f"按钮启用状态: {self.toolbar_buttons.get('add_qr', {}).isEnabled() if 'add_qr' in self.toolbar_buttons else 'N/A'}")
            self.add_qr_requested.emit()
            logger.debug("✅ 添加二维码信号已发射")
        except Exception as e:
            logger.error(f"添加二维码按钮点击处理失败: {e}")

    def _on_add_barcode_clicked(self):
        """添加条形码按钮点击处理"""
        try:
            logger.debug("🔘 添加条形码按钮被点击")
            logger.debug(f"按钮启用状态: {self.toolbar_buttons.get('add_barcode', {}).isEnabled() if 'add_barcode' in self.toolbar_buttons else 'N/A'}")
            self.add_barcode_requested.emit()
            logger.debug("✅ 添加条形码信号已发射")
        except Exception as e:
            logger.error(f"添加条形码按钮点击处理失败: {e}")

    def _on_remove_element(self):
        """删除元素处理（已移除元素列表，通过可视化编辑器删除）"""
        try:
            # 修改由于移除了元素列表，删除功能现在通过可视化编辑器处理
            # 用户可以在画布上选择元素后按Delete键或右键菜单删除

            # 检查是否有选中的元素（通过可视化编辑器）
            if hasattr(self.parent_widget, 'selected_element_id') and self.parent_widget.selected_element_id:
                element_id = self.parent_widget.selected_element_id
                logger.debug(f"🗑️ 删除按钮点击，元素ID: {element_id}")
                self.remove_element_requested.emit(element_id)
            else:
                QMessageBox.warning(self.parent_widget, "警告",
                                  "请先在画布上选择要删除的元素\n\n"
                                  "提示：点击画布上的元素选中后，再点击删除按钮")

        except Exception as e:
            logger.error(f"删除元素处理失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def _on_preview(self):
        """预览处理"""
        try:
            if not self.current_template:
                QMessageBox.warning(self.parent_widget, "警告", "没有可预览的模板")
                return

            # 预览功能已在打印管理器中实现
            QMessageBox.information(self.parent_widget, "预览", "请使用打印功能进行预览")

        except Exception as e:
            logger.error(f"预览处理失败: {e}")

    def _on_preprint(self):
        """预打印处理 - 真实打印到打印机"""
        try:
            if not self.current_template:
                QMessageBox.warning(self.parent_widget, "警告", "没有可预打印的模板")
                return

            logger.info("🖨️ 开始执行标签设计器预打印...")

            # 获取主窗口的打印管理器
            main_window = self._get_main_window()
            if not main_window:
                QMessageBox.critical(self.parent_widget, "错误", "无法获取主窗口，预打印失败")
                return

            # 检查打印机管理器
            if not hasattr(main_window, 'printer_manager') or not main_window.printer_manager:
                QMessageBox.warning(self.parent_widget, "打印机未就绪", "打印机管理器未初始化")
                return

            # 检查标签打印管理器
            if not hasattr(main_window, 'label_print_manager') or not main_window.label_print_manager:
                QMessageBox.warning(self.parent_widget, "打印机未就绪", "标签打印管理器未初始化")
                return

            # 检查打印机状态
            if not main_window.printer_manager.get_current_status():
                QMessageBox.warning(self.parent_widget, "打印机未连接",
                                  "打印机未连接或不可用，请检查打印机状态")
                return

            # 直接从可视化编辑器生成当前设计的图像
            logger.debug("从可视化编辑器生成预打印标签图像...")
            label_image = self._generate_current_design_image()

            if not label_image:
                QMessageBox.warning(self.parent_widget, "生成失败", "无法生成当前设计的标签图像，请检查模板配置")
                return

            # 执行真实打印
            logger.debug("开始执行真实打印...")
            success = self._execute_real_print(main_window.label_print_manager, label_image)

            if success:
                QMessageBox.information(self.parent_widget, "预打印成功",
                                      "预打印已发送到打印机！\n\n请检查打印机输出的标签效果。")
                logger.info("✅ 标签设计器预打印成功")
            else:
                QMessageBox.critical(self.parent_widget, "打印失败",
                                   "预打印失败，请检查打印机状态和连接")
                logger.error("❌ 标签设计器预打印失败")

        except Exception as e:
            logger.error(f"预打印处理失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            QMessageBox.critical(self.parent_widget, "预打印错误",
                               f"预打印执行失败：{str(e)}")

    def _get_main_window(self):
        """获取主窗口实例"""
        try:
            # 从父组件向上查找主窗口
            widget = self.parent_widget
            while widget:
                if hasattr(widget, 'printer_manager') and hasattr(widget, 'label_print_manager'):
                    return widget
                widget = widget.parent()

            # 尝试从QApplication获取主窗口
            from PyQt5.QtWidgets import QApplication
            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, 'printer_manager') and hasattr(widget, 'label_print_manager'):
                    return widget

            return None

        except Exception as e:
            logger.error(f"获取主窗口失败: {e}")
            return None

    def _generate_preview_test_data(self) -> dict:
        """生成预打印测试数据"""
        try:
            from datetime import datetime

            test_data = {
                'battery_code': 'PREVIEW123456',
                'channel_number': '1',
                'voltage': 3.25,
                'rs_value': 0.045,
                'rct_value': 0.123,
                'rs_grade': '1',
                'rct_grade': '2',
                'is_pass': True,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'batch_number': 'PREVIEW_BATCH',
                'operator': '设计器预览',
                'outlier_rate': '2.5%',
                'qr_code': 'PREVIEW123456',
                'barcode': 'PREVIEW123456'
            }

            logger.debug(f"生成预打印测试数据: {test_data}")
            return test_data

        except Exception as e:
            logger.error(f"生成预打印测试数据失败: {e}")
            return {}

    def _generate_current_design_image(self):
        """生成当前设计的标签图像"""
        try:
            # 检查可视化编辑器是否存在
            if not hasattr(self, 'visual_editor') or not self.visual_editor:
                logger.error("可视化编辑器未初始化")
                return None

            # 检查当前模板是否存在
            if not self.current_template:
                logger.error("当前模板为空")
                return None

            # 使用可视化编辑器生成预览图像
            logger.debug("使用可视化编辑器生成当前设计图像...")
            preview_image = self.visual_editor.generate_preview_image()

            if preview_image:
                logger.info(f"✅ 成功生成当前设计图像，尺寸: {preview_image.size}")
                logger.info(f"🎨 图像反映了标签设计器中的实际设计内容")
                return preview_image
            else:
                logger.error("可视化编辑器生成图像失败")
                return None

        except Exception as e:
            logger.error(f"生成当前设计图像失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return None





    def _execute_real_print(self, label_print_manager, label_image) -> bool:
        """执行真实打印"""
        try:
            # 获取打印配置
            print_config = {
                'printer_name': label_print_manager.config_manager.get('printer.name', ''),
                'copies': 1,  # 预打印只打印一份
                'quality': 'standard'
            }

            # 直接使用标签打印管理器的打印方法
            success = label_print_manager._print_image_to_printer(label_image, print_config)

            if success:
                logger.info("预打印执行成功")
            else:
                logger.error("预打印执行失败")

            return success

        except Exception as e:
            logger.error(f"执行真实打印失败: {e}")
            return False
    
    def set_splitter_sizes(self, sizes: List[int]):
        """设置分割器尺寸"""
        try:
            if self.main_splitter:
                self.main_splitter.setSizes(sizes)
                
        except Exception as e:
            logger.error(f"设置分割器尺寸失败: {e}")
    
    def get_visual_editor(self):
        """获取可视化编辑器"""
        return self.visual_editor
    
    def get_elements_list(self) -> Optional[QListWidget]:
        """获取元素列表（已移除，返回None以兼容现有代码）"""
        # 移除元素列表已删除，返回None
        return None
    
    def cleanup(self):
        """清理资源"""
        try:
            self.current_template = None
            self.visual_editor = None
            # 移除删除elements_list清理，不再需要元素列表控件
            self.toolbar_buttons.clear()

            logger.debug("标签设计器UI管理器资源清理完成")

        except Exception as e:
            logger.error(f"标签设计器UI管理器清理失败: {e}")
