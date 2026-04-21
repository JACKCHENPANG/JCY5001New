"""
通道使能设置页面
"""

import logging
from typing import Dict, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QCheckBox, QPushButton, QLabel, QFrame, QButtonGroup,
    QMessageBox, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class ChannelEnableWidget(QWidget):
    """通道使能设置页面"""
    
    # 设置变更信号
    settings_changed = pyqtSignal()
    
    def __init__(self, config_manager, parent=None):
        """
        初始化通道使能设置页面
        
        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self._loading = False
        
        # 通道复选框列表
        self.channel_checkboxes = {}
        
        # 初始化UI
        self._init_ui()
        
        # 连接信号
        self._connect_signals()
        
        # 加载设置
        self.load_settings()
        
    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 页面标题
        title_label = QLabel("通道使能设置")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 说明信息
        self._create_info_section(layout)
        
        # 通道使能设置区域
        self._create_channel_enable_section(layout)
        
        # 快速设置区域
        self._create_quick_settings_section(layout)
        
        # 添加弹性空间
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
    def _create_info_section(self, layout):
        """创建说明信息区域"""
        info_group = QGroupBox("功能说明")
        info_layout = QVBoxLayout(info_group)
        
        info_text = """
• 通道使能设置允许您选择哪些通道参与测试
• 禁用的通道将不会进行阻抗测试，可以避免硬件问题影响整体测试
• 适用于单通道测试、部分通道测试或排除故障通道
• 设置保存后立即生效，无需重启软件
        """.strip()
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            QLabel {
                padding: 15px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                color: #495057;
                line-height: 1.5;
            }
        """)
        info_layout.addWidget(info_label)
        
        layout.addWidget(info_group)
        
    def _create_channel_enable_section(self, layout):
        """创建通道使能设置区域"""
        channel_group = QGroupBox("通道使能设置")
        channel_layout = QVBoxLayout(channel_group)
        
        # 创建网格布局 (2行4列)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        
        # 创建8个通道的复选框
        for i in range(8):
            channel_num = i + 1
            row = i // 4
            col = i % 4
            
            # 创建通道复选框
            checkbox = QCheckBox(f"通道 {channel_num}")
            checkbox.setChecked(True)  # 默认启用
            checkbox.setStyleSheet("""
                QCheckBox {
                    font-size: 14px;
                    font-weight: bold;
                    padding: 8px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                }
                QCheckBox::indicator:unchecked {
                    border: 2px solid #6c757d;
                    background-color: white;
                    border-radius: 3px;
                }
                QCheckBox::indicator:checked {
                    border: 2px solid #28a745;
                    background-color: #28a745;
                    border-radius: 3px;
                }
                QCheckBox::indicator:checked:hover {
                    background-color: #218838;
                }
                QCheckBox:disabled {
                    color: #6c757d;
                }
            """)
            
            self.channel_checkboxes[channel_num] = checkbox
            grid_layout.addWidget(checkbox, row, col)
            
        channel_layout.addLayout(grid_layout)
        layout.addWidget(channel_group)
        
    def _create_quick_settings_section(self, layout):
        """创建快速设置区域"""
        quick_group = QGroupBox("快速设置")
        quick_layout = QVBoxLayout(quick_group)
        
        # 第一行按钮
        row1_layout = QHBoxLayout()
        
        # 全选按钮
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setMinimumHeight(35)
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        row1_layout.addWidget(self.select_all_btn)
        
        # 全不选按钮
        self.select_none_btn = QPushButton("全不选")
        self.select_none_btn.setMinimumHeight(35)
        self.select_none_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
            QPushButton:pressed {
                background-color: #3d4142;
            }
        """)
        row1_layout.addWidget(self.select_none_btn)
        
        # 反选按钮
        self.invert_selection_btn = QPushButton("反选")
        self.invert_selection_btn.setMinimumHeight(35)
        self.invert_selection_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #212529;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
            QPushButton:pressed {
                background-color: #d39e00;
            }
        """)
        row1_layout.addWidget(self.invert_selection_btn)
        
        quick_layout.addLayout(row1_layout)
        
        # 第二行按钮
        row2_layout = QHBoxLayout()
        
        # 前4通道按钮
        self.select_first4_btn = QPushButton("前4通道")
        self.select_first4_btn.setMinimumHeight(35)
        self.select_first4_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #117a8b;
            }
            QPushButton:pressed {
                background-color: #0e6674;
            }
        """)
        row2_layout.addWidget(self.select_first4_btn)
        
        # 后4通道按钮
        self.select_last4_btn = QPushButton("后4通道")
        self.select_last4_btn.setMinimumHeight(35)
        self.select_last4_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #1e7e34;
            }
            QPushButton:pressed {
                background-color: #155724;
            }
        """)
        row2_layout.addWidget(self.select_last4_btn)
        
        # 单通道测试按钮
        self.single_channel_btn = QPushButton("单通道测试")
        self.single_channel_btn.setMinimumHeight(35)
        self.single_channel_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        row2_layout.addWidget(self.single_channel_btn)
        
        quick_layout.addLayout(row2_layout)
        layout.addWidget(quick_group)
        
    def _connect_signals(self):
        """连接信号"""
        # 通道复选框变更信号
        for checkbox in self.channel_checkboxes.values():
            checkbox.toggled.connect(self._on_setting_changed)
            
        # 快速设置按钮
        self.select_all_btn.clicked.connect(self._select_all_channels)
        self.select_none_btn.clicked.connect(self._select_no_channels)
        self.invert_selection_btn.clicked.connect(self._invert_selection)
        self.select_first4_btn.clicked.connect(self._select_first4_channels)
        self.select_last4_btn.clicked.connect(self._select_last4_channels)
        self.single_channel_btn.clicked.connect(self._setup_single_channel_test)
        
    def _on_setting_changed(self):
        """设置变更处理"""
        if not self._loading:
            self.settings_changed.emit()
            
    def _select_all_channels(self):
        """全选通道"""
        self._loading = True
        for checkbox in self.channel_checkboxes.values():
            checkbox.setChecked(True)
        self._loading = False
        self._on_setting_changed()
        
    def _select_no_channels(self):
        """全不选通道"""
        self._loading = True
        for checkbox in self.channel_checkboxes.values():
            checkbox.setChecked(False)
        self._loading = False
        self._on_setting_changed()
        
    def _invert_selection(self):
        """反选通道"""
        self._loading = True
        for checkbox in self.channel_checkboxes.values():
            checkbox.setChecked(not checkbox.isChecked())
        self._loading = False
        self._on_setting_changed()
        
    def _select_first4_channels(self):
        """选择前4通道"""
        self._loading = True
        for i in range(1, 9):
            self.channel_checkboxes[i].setChecked(i <= 4)
        self._loading = False
        self._on_setting_changed()
        
    def _select_last4_channels(self):
        """选择后4通道"""
        self._loading = True
        for i in range(1, 9):
            self.channel_checkboxes[i].setChecked(i > 4)
        self._loading = False
        self._on_setting_changed()
        
    def _setup_single_channel_test(self):
        """设置单通道测试"""
        from PyQt5.QtWidgets import QInputDialog
        
        # 弹出对话框选择通道
        channel_num, ok = QInputDialog.getInt(
            self, "单通道测试",
            "请选择要测试的通道号 (1-8):",
            1, 1, 8, 1
        )
        
        if ok:
            self._loading = True
            # 只启用选择的通道
            for i in range(1, 9):
                self.channel_checkboxes[i].setChecked(i == channel_num)
            self._loading = False
            self._on_setting_changed()
            
            QMessageBox.information(
                self, "设置完成",
                f"已设置为单通道测试模式，仅启用通道{channel_num}"
            )
            
    def load_settings(self):
        """加载设置"""
        self._loading = True
        try:
            # 加载通道使能设置
            enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))
            
            # 更新复选框状态
            for i in range(1, 9):
                is_enabled = i in enabled_channels
                self.channel_checkboxes[i].setChecked(is_enabled)
                
            logger.debug(f"通道使能设置加载完成: {enabled_channels}")
            
        except Exception as e:
            logger.error(f"加载通道使能设置失败: {e}")
        finally:
            self._loading = False
            
    def apply_settings(self):
        """应用设置"""
        try:
            # 获取启用的通道列表
            enabled_channels = []
            for i in range(1, 9):
                if self.channel_checkboxes[i].isChecked():
                    enabled_channels.append(i)
                    
            # 保存设置
            self.config_manager.set('test.enabled_channels', enabled_channels)
            
            logger.info(f"通道使能设置应用成功: {enabled_channels}")
            
        except Exception as e:
            logger.error(f"应用通道使能设置失败: {e}")
            raise
            
    def get_enabled_channels(self) -> List[int]:
        """获取启用的通道列表"""
        enabled_channels = []
        for i in range(1, 9):
            if self.channel_checkboxes[i].isChecked():
                enabled_channels.append(i)
        return enabled_channels
