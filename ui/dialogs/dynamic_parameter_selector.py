"""
动态参数选择器组件
用于在标签设计器中选择和插入动态参数
"""

import logging
from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMenu, QAction,
    QLineEdit, QLabel, QFrame, QToolButton, QCompleter, QListWidget,
    QListWidgetItem, QDialog, QDialogButtonBox, QTextEdit, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal, QStringListModel
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor

from .label_template_config import get_dynamic_parameters

logger = logging.getLogger(__name__)


class DynamicParameterSelector(QWidget):
    """动态参数选择器组件"""
    
    # 信号定义
    parameter_selected = pyqtSignal(str)  # 参数选择信号
    
    def __init__(self, parent=None):
        """初始化动态参数选择器"""
        super().__init__(parent)
        
        self.dynamic_params = get_dynamic_parameters()
        
        # 初始化界面
        self._init_ui()
        
        logger.debug("动态参数选择器初始化完成")
    
    def _init_ui(self):
        """初始化用户界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 创建下拉按钮
        self.param_button = QToolButton()
        self.param_button.setText("动态参数")
        self.param_button.setToolTip("点击选择动态参数")
        self.param_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        # 创建参数菜单
        self._create_parameter_menu()
        
        layout.addWidget(self.param_button)
        
        # 添加帮助按钮
        self.help_button = QPushButton("?")
        self.help_button.setFixedSize(24, 24)
        self.help_button.setToolTip("查看动态参数帮助")
        self.help_button.clicked.connect(self._show_parameter_help)
        
        layout.addWidget(self.help_button)
    
    def _create_parameter_menu(self):
        """创建参数菜单"""
        menu = QMenu(self)
        
        # 按类别分组参数
        categories = {
            "基本信息": ['{battery_code}', '{test_date}', '{test_time}', '{channel_number}'],
            "测试数据": ['{rs_value}', '{rct_value}', '{voltage}', '{grade}'],
            "档位信息": ['{rs_grade}', '{rct_grade}', '{grade_result}'],
            "批次信息": ['{operator}', '{batch_number}', '{cell_type}'],
            "其他": ['{is_pass}', '{timestamp}', '{outlier_rate}']
        }
        
        for category, params in categories.items():
            # 添加分类标题
            category_action = QAction(f"── {category} ──", self)
            category_action.setEnabled(False)
            menu.addAction(category_action)
            
            # 添加该分类下的参数
            for param in params:
                if param in self.dynamic_params:
                    description = self.dynamic_params[param]
                    action = QAction(f"{param} - {description}", self)
                    action.setData(param)
                    action.triggered.connect(lambda checked, p=param: self._on_parameter_selected(p))
                    menu.addAction(action)
            
            # 添加分隔符
            menu.addSeparator()
        
        self.param_button.setMenu(menu)
    
    def _on_parameter_selected(self, parameter: str):
        """参数选择处理"""
        logger.debug(f"选择动态参数: {parameter}")
        self.parameter_selected.emit(parameter)
    
    def _show_parameter_help(self):
        """显示参数帮助对话框"""
        dialog = DynamicParameterHelpDialog(self.dynamic_params, self)
        dialog.exec()


class DynamicParameterHelpDialog(QDialog):
    """动态参数帮助对话框"""
    
    def __init__(self, parameters: dict, parent=None):
        """初始化帮助对话框"""
        super().__init__(parent)
        
        self.parameters = parameters
        
        self.setWindowTitle("动态参数帮助")
        self.setModal(True)
        self.resize(600, 400)
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("可用的动态参数")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 说明文本
        desc_label = QLabel("在文本内容中使用以下参数，打印时会自动替换为实际数据：")
        layout.addWidget(desc_label)
        
        # 参数列表
        params_text = QTextEdit()
        params_text.setReadOnly(True)
        
        # 构建参数说明文本
        help_text = ""
        categories = {
            "基本信息": ['{battery_code}', '{test_date}', '{test_time}', '{channel_number}'],
            "测试数据": ['{rs_value}', '{rct_value}', '{voltage}', '{grade}'],
            "档位信息": ['{rs_grade}', '{rct_grade}', '{grade_result}'],
            "批次信息": ['{operator}', '{batch_number}', '{cell_type}'],
            "其他": ['{is_pass}', '{timestamp}', '{outlier_rate}']
        }
        
        for category, params in categories.items():
            help_text += f"\n【{category}】\n"
            for param in params:
                if param in self.parameters:
                    description = self.parameters[param]
                    help_text += f"  {param:<20} - {description}\n"
        
        help_text += "\n使用示例：\n"
        help_text += "  电池: {battery_code}\n"
        help_text += "  测试时间: {test_date} {test_time}\n"
        help_text += "  Rs: {rs_value}mΩ  Rct: {rct_value}mΩ\n"
        help_text += "  等级: {grade}  操作员: {operator}\n"
        
        params_text.setPlainText(help_text)
        layout.addWidget(params_text)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)


class EnhancedTextEdit(QWidget):
    """
    增强的文本编辑器，支持动态参数预览和WYSIWYG显示

    功能特性：
    1. 实际编辑框显示原始文本（包含参数变量）
    2. 预览标签显示模拟数据替换后的效果
    3. 实时同步编辑内容和预览效果
    """

    # 信号定义
    textChanged = pyqtSignal()  # 文本变化信号

    def __init__(self, parent=None):
        """初始化增强文本编辑器"""
        super().__init__(parent)

        self.dynamic_params = get_dynamic_parameters()

        # 初始化界面
        self._init_ui()

        # 连接信号
        self._connect_signals()

    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 实际编辑框
        self.edit_line = QLineEdit()
        self.edit_line.setPlaceholderText("输入文本内容，可使用动态参数如{battery_code}")
        layout.addWidget(self.edit_line)

        # 预览标签
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                padding: 4px;
                border-radius: 3px;
                color: #666;
                font-style: italic;
            }
        """)
        self.preview_label.setWordWrap(True)
        self.preview_label.setText("预览: (空)")
        layout.addWidget(self.preview_label)

    def _connect_signals(self):
        """连接信号"""
        self.edit_line.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self):
        """文本变化处理 - 更新预览"""
        try:
            from .label_template_config import replace_parameters_with_sample_data

            # 获取原始文本
            original_text = self.edit_line.text()

            # 生成预览文本
            if original_text.strip():
                preview_text = replace_parameters_with_sample_data(original_text)
                self.preview_label.setText(f"预览: {preview_text}")
            else:
                self.preview_label.setText("预览: (空)")

            # 发送文本变化信号
            self.textChanged.emit()

        except Exception as e:
            logger.error(f"更新文本预览失败: {e}")
            self.preview_label.setText("预览: (错误)")

    def insert_parameter(self, parameter: str):
        """插入动态参数"""
        cursor_pos = self.edit_line.cursorPosition()
        current_text = self.edit_line.text()

        # 在光标位置插入参数
        new_text = current_text[:cursor_pos] + parameter + current_text[cursor_pos:]
        self.edit_line.setText(new_text)

        # 设置光标位置到参数后面
        self.edit_line.setCursorPosition(cursor_pos + len(parameter))

        logger.debug(f"插入动态参数: {parameter}")

    def text(self) -> str:
        """获取文本内容"""
        return self.edit_line.text()

    def setText(self, text: str):
        """设置文本内容"""
        self.edit_line.setText(text)

    def get_parameters_in_text(self) -> list:
        """获取文本中的所有动态参数"""
        text = self.edit_line.text()
        found_params = []

        for param in self.dynamic_params.keys():
            if param in text:
                found_params.append(param)

        return found_params
