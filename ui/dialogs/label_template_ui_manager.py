#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标签模板UI管理器
负责标签模板相关的界面管理

Author: Jack
Date: 2025-06-04
"""

import logging
from typing import Optional, List, Dict, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QComboBox, QMessageBox,
    QDialog, QLineEdit, QTextEdit, QFormLayout, QDialogButtonBox,
    QInputDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject

# 导入标签相关类
from .label_template_config import LabelTemplateConfig
from .label_template_manager import LabelTemplateManager

logger = logging.getLogger(__name__)


class SaveTemplateDialog(QDialog):
    """保存模板对话框"""

    def __init__(self, current_template, parent=None):
        """初始化保存模板对话框"""
        super().__init__(parent)
        self.current_template = current_template
        self.setWindowTitle("保存模板")
        self.setModal(True)
        self.resize(400, 300)

        self._init_ui()

    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)

        # 创建表单布局
        form_layout = QFormLayout()

        # 模板名称输入
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入模板名称...")
        if self.current_template and hasattr(self.current_template, 'name'):
            # 如果是预设模板，建议一个新名称
            original_name = self.current_template.name
            if "预设" in original_name or "模板" in original_name:
                suggested_name = f"我的{original_name}"
            else:
                suggested_name = f"{original_name}_副本"
            self.name_edit.setText(suggested_name)

        form_layout.addRow("模板名称:", self.name_edit)

        # 模板描述输入
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("请输入模板描述（可选）...")
        self.description_edit.setMaximumHeight(100)
        if self.current_template and hasattr(self.current_template, 'description'):
            self.description_edit.setPlainText(f"基于 {self.current_template.description}")

        form_layout.addRow("模板描述:", self.description_edit)

        layout.addLayout(form_layout)

        # 添加说明文本
        info_label = QLabel(
            "💡 提示：\n"
            "• 模板将保存到用户模板库中\n"
            "• 保存后可在用户模板列表中找到\n"
            "• 包含当前所有元素的完整配置"
        )
        info_label.setStyleSheet("color: #666; font-size: 12px; padding: 10px;")
        layout.addWidget(info_label)

        # 按钮组
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            self
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        # 设置焦点到名称输入框
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def get_template_name(self) -> str:
        """获取模板名称"""
        return self.name_edit.text().strip()

    def get_template_description(self) -> str:
        """获取模板描述"""
        return self.description_edit.toPlainText().strip()


class LabelTemplateUIManager(QObject):
    """
    标签模板UI管理器
    
    职责：
    - 管理模板列表界面
    - 处理模板选择和切换
    - 管理模板相关的UI组件
    """
    
    # 信号定义
    template_selected = pyqtSignal(object)  # 模板选择信号 (template)
    template_created = pyqtSignal(str)  # 模板创建信号 (template_name)
    template_deleted = pyqtSignal(str)  # 模板删除信号 (template_name)
    
    def __init__(self, config_manager, parent=None):
        """
        初始化标签模板UI管理器
        
        Args:
            config_manager: 配置管理器
            parent: 父对象
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.template_manager = None
        self.current_template = None
        
        # UI组件
        self.preset_list = None
        self.user_list = None
        self.template_combo = None
        
        # 初始化模板管理器
        self._init_template_manager()
        
        logger.debug("标签模板UI管理器初始化完成")
    
    def _init_template_manager(self):
        """初始化模板管理器"""
        try:
            self.template_manager = LabelTemplateManager(self.config_manager)
            logger.debug("模板管理器初始化成功")
        except Exception as e:
            logger.error(f"模板管理器初始化失败: {e}")
            self.template_manager = None
    
    def create_template_panel(self, parent=None) -> QWidget:
        """创建模板管理面板"""
        try:
            logger.debug("🎨 开始创建模板管理面板...")
            panel = QWidget(parent)
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)

            # 预设模板组
            logger.debug("创建预设模板组...")
            preset_group = self._create_preset_group()
            layout.addWidget(preset_group)
            logger.debug(f"预设模板组创建完成，preset_list: {hasattr(self, 'preset_list')}")

            # 用户模板组
            logger.debug("创建用户模板组...")
            user_group = self._create_user_group()
            layout.addWidget(user_group)
            logger.debug(f"用户模板组创建完成，user_list: {hasattr(self, 'user_list')}")

            # 模板操作按钮
            logger.debug("创建模板操作按钮组...")
            button_group = self._create_button_group()
            layout.addWidget(button_group)
            logger.debug("模板操作按钮组创建完成")

            logger.info("✅ 模板管理面板创建完成")
            return panel

        except Exception as e:
            logger.error(f"创建模板管理面板失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return QWidget(parent)  # 返回空面板

    def _create_current_template_group(self) -> QGroupBox:
        """创建当前模板信息组"""
        try:
            group = QGroupBox("当前模板")
            layout = QVBoxLayout(group)
            layout.setSpacing(8)
            layout.setContentsMargins(10, 10, 10, 10)

            # 模板名称显示
            self.current_template_label = QLabel("未选择模板")
            self.current_template_label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 12pt;
                    color: #2c3e50;
                    padding: 8px;
                    background-color: #ecf0f1;
                    border-radius: 4px;
                    border: 1px solid #bdc3c7;
                }
            """)
            layout.addWidget(self.current_template_label)

            # 模板描述显示
            self.template_description_label = QLabel("无描述")
            self.template_description_label.setWordWrap(True)
            self.template_description_label.setStyleSheet("""
                QLabel {
                    color: #7f8c8d;
                    font-size: 9pt;
                    padding: 4px;
                }
            """)
            layout.addWidget(self.template_description_label)

            return group

        except Exception as e:
            logger.error(f"创建当前模板信息组失败: {e}")
            return QGroupBox("当前模板")

    def _create_button_group(self) -> QGroupBox:
        """创建按钮组"""
        group = QGroupBox("模板操作")
        layout = QVBoxLayout(group)

        # 新建模板按钮
        new_btn = QPushButton("新建模板")
        new_btn.clicked.connect(self._create_new_template)
        layout.addWidget(new_btn)

        # 保存模板按钮
        save_btn = QPushButton("保存模板")
        save_btn.clicked.connect(self._save_current_template)
        layout.addWidget(save_btn)

        # 新增导入导出按钮
        import_export_layout = QHBoxLayout()

        # 导入模板按钮
        import_btn = QPushButton("导入模板")
        import_btn.clicked.connect(self._import_template)
        import_btn.setToolTip("从文件导入标签模板")
        import_export_layout.addWidget(import_btn)

        # 导出模板按钮
        export_btn = QPushButton("导出模板")
        export_btn.clicked.connect(self._export_template)
        export_btn.setToolTip("将当前模板导出为文件")
        import_export_layout.addWidget(export_btn)

        layout.addLayout(import_export_layout)

        # 删除模板按钮
        delete_btn = QPushButton("删除模板")
        delete_btn.clicked.connect(self._delete_current_template)
        layout.addWidget(delete_btn)

        return group

    def _create_preset_group(self) -> QGroupBox:
        """创建预设模板组"""
        try:
            logger.debug("🎯 开始创建预设模板组...")
            group = QGroupBox("预设模板")
            layout = QVBoxLayout(group)

            # 预设模板列表
            logger.debug("创建预设模板列表控件...")
            self.preset_list = QListWidget()
            logger.debug(f"预设模板列表控件创建成功: {self.preset_list}")

            self.preset_list.itemClicked.connect(self._on_preset_selected)
            logger.debug("预设模板列表信号连接完成")

            layout.addWidget(self.preset_list)
            logger.debug("预设模板列表已添加到布局")

            logger.info("✅ 预设模板组创建完成")
            return group

        except Exception as e:
            logger.error(f"创建预设模板组失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            # 返回一个空的组，避免程序崩溃
            return QGroupBox("预设模板")
    
    def _create_user_group(self) -> QGroupBox:
        """创建用户模板组"""
        try:
            logger.debug("🎯 开始创建用户模板组...")
            group = QGroupBox("用户模板")
            layout = QVBoxLayout(group)

            # 用户模板列表
            logger.debug("创建用户模板列表控件...")
            self.user_list = QListWidget()
            logger.debug(f"用户模板列表控件创建成功: {self.user_list}")

            self.user_list.itemClicked.connect(self._on_user_template_selected)
            logger.debug("用户模板列表信号连接完成")

            layout.addWidget(self.user_list)
            logger.debug("用户模板列表已添加到布局")

            logger.info("✅ 用户模板组创建完成")
            return group

        except Exception as e:
            logger.error(f"创建用户模板组失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            # 返回一个空的组，避免程序崩溃
            return QGroupBox("用户模板")

    def load_preset_templates(self):
        """加载预设模板"""
        try:
            logger.debug("开始加载预设模板...")
            logger.debug(f"preset_list状态: {self.preset_list}")

            if not self.preset_list:
                logger.error("预设模板列表控件未初始化")
                # 尝试重新初始化
                logger.debug("尝试重新查找preset_list控件...")
                return

            if not self.template_manager:
                logger.error("模板管理器未初始化")
                return

            self.preset_list.clear()
            logger.debug("预设模板列表已清空")

            # 获取预设模板
            preset_templates = self.template_manager.get_preset_templates()
            logger.debug(f"从模板管理器获取到 {len(preset_templates)} 个预设模板")

            for i, template in enumerate(preset_templates):
                item = QListWidgetItem(template.name)
                item.setData(Qt.ItemDataRole.UserRole, template)
                self.preset_list.addItem(item)
                logger.debug(f"添加预设模板 {i+1}: {template.name}")

            # 验证添加结果
            actual_count = self.preset_list.count()
            logger.info(f"预设模板加载完成，预期 {len(preset_templates)} 个，实际 {actual_count} 个")

        except Exception as e:
            logger.error(f"加载预设模板失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def load_user_templates(self):
        """加载用户模板"""
        try:
            logger.debug("开始加载用户模板...")
            logger.debug(f"user_list状态: {self.user_list}")

            if not self.user_list:
                logger.error("用户模板列表控件未初始化")
                return

            if not self.template_manager:
                logger.error("模板管理器未初始化")
                return

            self.user_list.clear()
            logger.debug("用户模板列表已清空")

            # 获取用户模板
            user_templates = self.template_manager.get_user_templates()
            logger.debug(f"从模板管理器获取到 {len(user_templates)} 个用户模板")

            for i, template in enumerate(user_templates):
                item = QListWidgetItem(template.name)
                item.setData(Qt.ItemDataRole.UserRole, template)
                self.user_list.addItem(item)
                logger.debug(f"添加用户模板 {i+1}: {template.name}")

            # 验证添加结果
            actual_count = self.user_list.count()
            logger.info(f"用户模板加载完成，预期 {len(user_templates)} 个，实际 {actual_count} 个")

        except Exception as e:
            logger.error(f"加载用户模板失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def _on_preset_selected(self, item: QListWidgetItem):
        """预设模板选择处理"""
        try:
            template = item.data(Qt.ItemDataRole.UserRole)
            if template:
                self.current_template = template
                self._update_current_template_display()
                self.template_selected.emit(template)
                logger.debug(f"选择预设模板: {template.name}")

        except Exception as e:
            logger.error(f"预设模板选择处理失败: {e}")

    def _on_user_template_selected(self, item: QListWidgetItem):
        """用户模板选择处理"""
        try:
            template = item.data(Qt.ItemDataRole.UserRole)
            if template:
                self.current_template = template
                self._update_current_template_display()
                self.template_selected.emit(template)
                logger.debug(f"选择用户模板: {template.name}")

        except Exception as e:
            logger.error(f"用户模板选择处理失败: {e}")
    
    def _create_new_template(self):
        """创建新模板"""
        try:
            from PyQt5.QtWidgets import QInputDialog
            
            # 获取模板名称
            name, ok = QInputDialog.getText(
                None, "新建模板", "请输入模板名称:"
            )
            
            if ok and name.strip():
                template_name = name.strip()
                
                # 创建新模板
                if self.template_manager:
                    template = self.template_manager.create_template(template_name)
                    if template:
                        # 保存模板到文件
                        success, error_msg = self.template_manager.save_template(template)
                        if success:
                            self.current_template = template
                            self.template_selected.emit(template)
                            self.template_created.emit(template_name)

                            # 刷新用户模板列表
                            self.load_user_templates()

                            # 在用户模板列表中选中新创建的模板
                            if hasattr(self, 'user_list') and self.user_list:
                                for i in range(self.user_list.count()):
                                    item = self.user_list.item(i)
                                    if item and item.text() == template_name:
                                        self.user_list.setCurrentItem(item)
                                        break

                            logger.info(f"创建新模板: {template_name}")
                            QMessageBox.information(None, "成功", f"模板 '{template_name}' 创建成功！")
                        else:
                            error_detail = "模板保存失败"
                            if error_msg:
                                error_detail += f"\n\n详细错误:\n{error_msg}"
                            QMessageBox.warning(None, "失败", error_detail)
                    else:
                        QMessageBox.warning(None, "失败", "模板创建失败")
                
        except Exception as e:
            logger.error(f"创建新模板失败: {e}")
            QMessageBox.critical(None, "错误", f"创建新模板失败: {e}")
    
    def _save_current_template(self):
        """保存当前模板"""
        try:
            if not self.current_template:
                QMessageBox.warning(None, "警告", "没有可保存的模板")
                return

            # 创建保存模板对话框
            dialog = SaveTemplateDialog(self.current_template, None)

            if dialog.exec_() == QDialog.Accepted:
                template_name = dialog.get_template_name()
                template_description = dialog.get_template_description()

                if not template_name:
                    QMessageBox.warning(None, "警告", "模板名称不能为空")
                    return

                # 创建新的模板配置（复制当前模板）
                from datetime import datetime
                import copy

                # 深拷贝当前模板
                new_template = copy.deepcopy(self.current_template)

                # 更新模板信息
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_template.template_id = f"user_{timestamp}"
                new_template.name = template_name
                new_template.description = template_description or f"用户自定义模板 - {template_name}"
                new_template.author = "用户"
                new_template.created_time = datetime.now().isoformat()
                new_template.modified_time = datetime.now().isoformat()

                # 保存模板
                if self.template_manager:
                    success, error_msg = self.template_manager.save_template(new_template)
                    if success:
                        QMessageBox.information(
                            None, "保存成功",
                            f"模板 '{template_name}' 已成功保存到用户模板库！\n\n"
                            f"您可以在用户模板列表中找到并重新加载使用。"
                        )

                        # 刷新用户模板列表
                        self.load_user_templates()

                        logger.info(f"✅ 用户模板保存成功: {template_name}")
                    else:
                        error_detail = f"保存模板 '{template_name}' 失败"
                        if error_msg:
                            error_detail += f"\n\n详细错误:\n{error_msg}"
                        QMessageBox.warning(None, "保存失败", error_detail)
                        logger.error(f"❌ 用户模板保存失败: {template_name} - {error_msg}")
                else:
                    QMessageBox.critical(None, "错误", "模板管理器未初始化")

        except Exception as e:
            logger.error(f"保存当前模板失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            QMessageBox.critical(None, "错误", f"保存模板失败: {e}")
    
    def _delete_current_template(self):
        """删除当前模板"""
        try:
            if not self.current_template:
                QMessageBox.warning(None, "警告", "没有可删除的模板")
                return
            
            # 确认删除
            reply = QMessageBox.question(
                None, "确认删除", 
                f"确定要删除模板 '{self.current_template.name}' 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if self.template_manager:
                    success = self.template_manager.delete_template_by_name(self.current_template.name)
                    if success:
                        self.template_deleted.emit(self.current_template.name)
                        self.current_template = None

                        # 刷新用户模板列表
                        self.load_user_templates()

                        QMessageBox.information(None, "成功", "模板删除成功")
                    else:
                        QMessageBox.warning(None, "警告", "模板删除失败")
                        
        except Exception as e:
            logger.error(f"删除当前模板失败: {e}")
            QMessageBox.critical(None, "错误", f"删除模板失败: {e}")
    
    def get_current_template(self) -> Optional[LabelTemplateConfig]:
        """获取当前模板"""
        return self.current_template
    
    def set_current_template(self, template: Optional[LabelTemplateConfig]):
        """设置当前模板"""
        self.current_template = template
        self._update_current_template_display()

    def _update_current_template_display(self):
        """更新当前模板信息显示"""
        try:
            if hasattr(self, 'current_template_label') and hasattr(self, 'template_description_label'):
                if self.current_template:
                    self.current_template_label.setText(self.current_template.name)
                    description = self.current_template.description or "无描述"
                    self.template_description_label.setText(description)
                else:
                    self.current_template_label.setText("未选择模板")
                    self.template_description_label.setText("无描述")
        except Exception as e:
            logger.error(f"更新当前模板显示失败: {e}")
    
    def refresh_templates(self):
        """刷新模板列表"""
        try:
            self.load_preset_templates()
            self.load_user_templates()
            logger.debug("模板列表刷新完成")

        except Exception as e:
            logger.error(f"刷新模板列表失败: {e}")

    def refresh_template_lists(self):
        """刷新模板列表（向后兼容方法）"""
        self.refresh_templates()

    def force_reload_templates(self):
        """强制重新加载模板列表"""
        try:
            logger.debug("🔄 强制重新加载模板列表...")

            # 检查控件状态
            logger.debug(f"preset_list状态: {self.preset_list is not None}")
            logger.debug(f"user_list状态: {self.user_list is not None}")
            logger.debug(f"template_manager状态: {self.template_manager is not None}")

            # 详细检查控件对象
            if hasattr(self, 'preset_list'):
                logger.debug(f"preset_list属性存在: {self.preset_list}")
            else:
                logger.debug("preset_list属性不存在")

            if hasattr(self, 'user_list'):
                logger.debug(f"user_list属性存在: {self.user_list}")
            else:
                logger.debug("user_list属性不存在")

            # 检查并加载预设模板
            if self.preset_list is not None and self.template_manager is not None:
                logger.debug("开始加载预设模板...")
                self.load_preset_templates()
            else:
                logger.warning(f"preset_list或template_manager未初始化，跳过预设模板加载 (preset_list={self.preset_list is not None}, template_manager={self.template_manager is not None})")

            # 检查并加载用户模板
            if self.user_list is not None and self.template_manager is not None:
                logger.debug("开始加载用户模板...")
                self.load_user_templates()
            else:
                logger.warning(f"user_list或template_manager未初始化，跳过用户模板加载 (user_list={self.user_list is not None}, template_manager={self.template_manager is not None})")

            logger.info("✅ 强制重新加载模板列表完成")

        except Exception as e:
            logger.error(f"强制重新加载模板列表失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def _import_template(self):
        """导入模板"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            import json
            import os

            # 选择要导入的模板文件
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "导入标签模板",
                "",
                "JSON文件 (*.json);;所有文件 (*)"
            )

            if not file_path:
                return

            # 读取模板文件
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)

                # 验证模板数据格式
                if not self._validate_template_data(template_data):
                    QMessageBox.warning(None, "导入失败", "模板文件格式不正确")
                    return

                # 创建模板配置对象
                from .label_template_config import LabelTemplateConfig
                try:
                    template = LabelTemplateConfig.from_dict(template_data)
                    logger.info(f"✅ 模板配置对象创建成功: {template.name}")
                except Exception as e:
                    logger.error(f"❌ 创建模板配置对象失败: {e}")
                    QMessageBox.warning(None, "导入失败", f"无法解析模板文件: {e}")
                    return

                if not template:
                    QMessageBox.warning(None, "导入失败", "无法解析模板文件")
                    return

                # 生成新的模板ID（避免冲突）
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                original_name = template.name
                template.template_id = f"imported_{timestamp}"
                template.name = f"{original_name}_导入"
                template.author = "导入"
                template.created_time = datetime.now().isoformat()
                template.modified_time = datetime.now().isoformat()

                # 保存导入的模板
                if self.template_manager:
                    success = self.template_manager.save_template(template)
                    if success:
                        # 刷新用户模板列表
                        self.load_user_templates()

                        # 选择导入的模板
                        self.current_template = template
                        self.template_selected.emit(template)

                        QMessageBox.information(
                            None, "导入成功",
                            f"模板 '{template.name}' 导入成功！\n\n"
                            f"已自动选择该模板，您可以直接使用或进一步编辑。"
                        )

                        logger.info(f"✅ 模板导入成功: {template.name}")
                    else:
                        QMessageBox.warning(None, "导入失败", "保存导入的模板失败")
                else:
                    QMessageBox.critical(None, "错误", "模板管理器未初始化")

            except json.JSONDecodeError as e:
                QMessageBox.warning(None, "导入失败", f"模板文件格式错误: {e}")
            except Exception as e:
                QMessageBox.critical(None, "导入失败", f"读取模板文件失败: {e}")

        except Exception as e:
            logger.error(f"导入模板失败: {e}")
            QMessageBox.critical(None, "错误", f"导入模板失败: {e}")

    def _export_template(self):
        """导出模板"""
        try:
            if not self.current_template:
                QMessageBox.warning(None, "警告", "没有可导出的模板")
                return

            from PyQt5.QtWidgets import QFileDialog
            import json
            import os

            # 生成默认文件名
            safe_name = "".join(c for c in self.current_template.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            default_filename = f"{safe_name}_模板.json"

            # 选择保存位置
            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "导出标签模板",
                default_filename,
                "JSON文件 (*.json);;所有文件 (*)"
            )

            if not file_path:
                return

            # 确保文件扩展名
            if not file_path.lower().endswith('.json'):
                file_path += '.json'

            # 导出模板数据
            try:
                # 获取模板核心数据
                template_data = self.current_template.to_dict()

                # 创建完整的导出数据结构
                from datetime import datetime
                export_data = {
                    # 模板核心数据
                    **template_data,

                    # 导出元信息（单独字段，不影响导入）
                    'export_info': {
                        'export_time': datetime.now().isoformat(),
                        'export_version': '1.0',
                        'system': 'JCY5001AS电池测试系统',
                        'exported_by': 'JCY5001AS标签设计器'
                    }
                }

                logger.info(f"✅ 准备导出模板: {self.current_template.name}")

                # 写入文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)

                QMessageBox.information(
                    None, "导出成功",
                    f"模板 '{self.current_template.name}' 已成功导出到:\n{file_path}\n\n"
                    f"您可以将此文件分享给其他用户或在其他系统中导入使用。"
                )

                logger.info(f"✅ 模板导出成功: {self.current_template.name} -> {file_path}")

            except Exception as e:
                QMessageBox.critical(None, "导出失败", f"写入模板文件失败: {e}")

        except Exception as e:
            logger.error(f"导出模板失败: {e}")
            QMessageBox.critical(None, "错误", f"导出模板失败: {e}")

    def _validate_template_data(self, data: dict) -> bool:
        """验证模板数据格式"""
        try:
            # 检查必需字段
            required_fields = ['template_id', 'name', 'size', 'elements']
            for field in required_fields:
                if field not in data:
                    logger.warning(f"模板数据缺少必需字段: {field}")
                    return False

            # 检查元素列表格式
            if not isinstance(data['elements'], list):
                logger.warning("模板元素不是列表格式")
                return False

            # 检查每个元素的基本字段
            for i, element in enumerate(data['elements']):
                if not isinstance(element, dict):
                    logger.warning(f"元素 {i} 不是字典格式")
                    return False

                element_required = ['element_id', 'element_type', 'x', 'y', 'width', 'height']
                for field in element_required:
                    if field not in element:
                        logger.warning(f"元素 {i} 缺少必需字段: {field}")
                        return False

            return True

        except Exception as e:
            logger.error(f"验证模板数据失败: {e}")
            return False

    def cleanup(self):
        """清理资源"""
        try:
            self.current_template = None
            self.template_manager = None
            logger.debug("标签模板UI管理器资源清理完成")

        except Exception as e:
            logger.error(f"标签模板UI管理器清理失败: {e}")
