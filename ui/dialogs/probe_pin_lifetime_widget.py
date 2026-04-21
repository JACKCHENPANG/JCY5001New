# -*- coding: utf-8 -*-
"""
顶针寿命设置页面
管理各通道的测试计数和顶针寿命设置

Author: Jack
Date: 2025-01-27
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QGridLayout, QPushButton, QSpinBox,
    QProgressBar, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import logging

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager


class ProbePinLifetimeWidget(QWidget):
    """顶针寿命设置页面"""
    
    # 信号定义
    settings_changed = pyqtSignal()  # 设置变更信号
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        初始化顶针寿命设置页面
        
        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self._loading = False
        
        # 初始化顶针寿命管理器
        self._init_probe_pin_manager()
        
        # 初始化界面
        self._init_ui()
        
        logger.debug("顶针寿命设置页面初始化完成")
    
    def _init_probe_pin_manager(self):
        """初始化顶针寿命管理器"""
        try:
            from utils.probe_pin_manager import ProbePinManager
            
            self.probe_pin_manager = ProbePinManager(
                config_manager=self.config_manager,
                parent=self
            )
            
            # 连接信号
            self.probe_pin_manager.lifetime_reset.connect(self._on_lifetime_reset)
            self.probe_pin_manager.test_count_updated.connect(self._on_test_count_updated)
            
            logger.debug("顶针寿命管理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化顶针寿命管理器失败: {e}")
            self.probe_pin_manager = None
    
    def _init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 创建设置区域
        self._create_lifetime_settings(main_layout)
        self._create_channel_status(main_layout)
        
        # 添加弹性空间
        main_layout.addStretch()
        
        # 应用样式
        self._apply_styles()
    
    def _create_lifetime_settings(self, layout):
        """创建寿命设置区域"""
        # 创建分组框
        group_box = QGroupBox("顶针寿命设置")
        group_box.setObjectName("lifetimeGroup")
        layout.addWidget(group_box)
        
        # 创建网格布局
        grid_layout = QGridLayout(group_box)
        grid_layout.setContentsMargins(15, 20, 15, 15)
        grid_layout.setSpacing(10)
        
        # 警告阈值设置
        grid_layout.addWidget(QLabel("警告阈值:"), 0, 0)
        self.warning_threshold_spin = QSpinBox()
        self.warning_threshold_spin.setRange(100, 50000)
        self.warning_threshold_spin.setValue(1000)
        self.warning_threshold_spin.setSuffix(" 次")
        self.warning_threshold_spin.valueChanged.connect(self._on_setting_changed)
        grid_layout.addWidget(self.warning_threshold_spin, 0, 1)
        
        # 最大寿命设置
        grid_layout.addWidget(QLabel("最大寿命:"), 0, 2)
        self.max_lifetime_spin = QSpinBox()
        self.max_lifetime_spin.setRange(1000, 100000)
        self.max_lifetime_spin.setValue(10000)
        self.max_lifetime_spin.setSuffix(" 次")
        self.max_lifetime_spin.valueChanged.connect(self._on_setting_changed)
        grid_layout.addWidget(self.max_lifetime_spin, 0, 3)
        
        # 全部重置按钮
        self.reset_all_button = QPushButton("重置所有通道计数")
        self.reset_all_button.setObjectName("resetAllButton")
        self.reset_all_button.clicked.connect(self._on_reset_all_clicked)
        grid_layout.addWidget(self.reset_all_button, 1, 0, 1, 4)
    
    def _create_channel_status(self, layout):
        """创建通道状态区域"""
        # 创建分组框
        group_box = QGroupBox("通道测试计数状态")
        group_box.setObjectName("channelStatusGroup")
        layout.addWidget(group_box)
        
        # 创建网格布局
        grid_layout = QGridLayout(group_box)
        grid_layout.setContentsMargins(15, 20, 15, 15)
        grid_layout.setSpacing(10)
        
        # 创建8个通道的状态显示
        self.channel_widgets = {}
        for i in range(8):
            channel_num = i + 1
            self._create_channel_widget(grid_layout, channel_num, i // 4, (i % 4) * 3)
    
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
    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QGroupBox#lifetimeGroup, QGroupBox#channelStatusGroup {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: white;
            }
            
            QGroupBox#lifetimeGroup::title, QGroupBox#channelStatusGroup::title {
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
            
            QLabel#countLabel {
                font-size: 12pt;
                font-weight: bold;
                color: #27ae60;
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 50px;
                text-align: center;
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
            
            QSpinBox {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: white;
                font-size: 10pt;
                min-width: 80px;
            }
            
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
    
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
                if self.probe_pin_manager:
                    # 使用顶针寿命管理器重置
                    success = self.probe_pin_manager.reset_test_count(channel_num)
                    if success:
                        logger.info(f"通道{channel_num}测试计数已重置")
                    else:
                        QMessageBox.critical(self, "错误", f"重置通道{channel_num}失败")
                else:
                    # 备用方案：直接操作配置
                    self.config_manager.set(f'test_count.channel_{channel_num}', 0)
                    self.config_manager.save_config()
                    
                    # 更新显示
                    self.channel_widgets[channel_num]['count_label'].setText("0")
                    self._update_count_color(channel_num, 0)
                    self._notify_test_count_reset(channel_num, 0)
                    
                    logger.info(f"通道{channel_num}测试计数已重置（备用方案）")

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
                if self.probe_pin_manager:
                    # 使用顶针寿命管理器重置所有通道
                    success = self.probe_pin_manager.reset_all_test_counts()
                    if success:
                        logger.info("所有通道测试计数已重置")
                    else:
                        QMessageBox.critical(self, "错误", "重置所有通道失败")
                else:
                    # 备用方案：直接操作配置
                    for channel_num in range(1, 9):
                        self.config_manager.set(f'test_count.channel_{channel_num}', 0)
                        self.channel_widgets[channel_num]['count_label'].setText("0")
                        self._update_count_color(channel_num, 0)
                        self._notify_test_count_reset(channel_num, 0)

                    self.config_manager.save_config()
                    logger.info("所有通道测试计数已重置（备用方案）")

        except Exception as e:
            logger.error(f"重置所有通道计数失败: {e}")
            QMessageBox.critical(self, "错误", f"重置失败: {e}")
    
    def load_settings(self):
        """加载设置"""
        self._loading = True
        try:
            # 加载寿命设置
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
            
        except Exception as e:
            logger.error(f"加载顶针寿命设置失败: {e}")
        finally:
            self._loading = False
    
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
                    }
                """)
            elif count >= warning_threshold:
                # 超过警告阈值 - 橙色
                count_label.setStyleSheet("""
                    QLabel#countLabel {
                        color: white;
                        background-color: #f39c12;
                        border: 1px solid #e67e22;
                    }
                """)
            else:
                # 正常 - 绿色
                count_label.setStyleSheet("")
                
        except Exception as e:
            logger.error(f"更新通道{channel_num}计数颜色失败: {e}")
    
    def apply_settings(self):
        """应用设置"""
        try:
            # 保存寿命设置
            self.config_manager.set('probe_pin.warning_threshold', self.warning_threshold_spin.value())
            self.config_manager.set('probe_pin.max_lifetime', self.max_lifetime_spin.value())
            
            logger.info("顶针寿命设置已保存")
            
        except Exception as e:
            logger.error(f"保存顶针寿命设置失败: {e}")
            raise
    
    def validate_settings(self) -> bool:
        """
        验证设置
        
        Returns:
            是否验证通过
        """
        try:
            warning_threshold = self.warning_threshold_spin.value()
            max_lifetime = self.max_lifetime_spin.value()
            
            if warning_threshold >= max_lifetime:
                QMessageBox.warning(self, "设置错误", "警告阈值不能大于或等于最大寿命！")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证顶针寿命设置失败: {e}")
            return False
    
    def refresh_counts(self):
        """刷新测试计数显示"""
        try:
            for channel_num in range(1, 9):
                count = self.config_manager.get(f'test_count.channel_{channel_num}', 0)
                self.channel_widgets[channel_num]['count_label'].setText(str(count))
                self._update_count_color(channel_num, count)
                
        except Exception as e:
            logger.error(f"刷新测试计数显示失败: {e}")
    
    def _on_lifetime_reset(self):
        """处理顶针寿命归零信号"""
        try:
            logger.info("🔄 收到顶针寿命归零信号，刷新界面显示")
            
            # 刷新所有通道的测试计数显示
            self.refresh_counts()
            
            # 显示成功消息
            QMessageBox.information(
                self, 
                "顶针寿命归零", 
                "所有通道的测试计数已成功归零！\n\n界面显示已更新。"
            )
            
        except Exception as e:
            logger.error(f"处理顶针寿命归零信号失败: {e}")
    
    def _on_test_count_updated(self, channel_num: int, new_count: int):
        """处理顶针测试计数更新信号"""
        try:
            logger.debug(f"收到通道{channel_num}测试计数更新信号: {new_count}")
            
            # 更新对应通道的显示
            if channel_num in self.channel_widgets:
                self.channel_widgets[channel_num]['count_label'].setText(str(new_count))
                self._update_count_color(channel_num, new_count)
                
                # 通知主界面更新
                self._notify_test_count_reset(channel_num, new_count)
            
        except Exception as e:
            logger.error(f"处理通道{channel_num}测试计数更新信号失败: {e}")

    def _notify_test_count_reset(self, channel_num: int, count: int):
        """
        通知主界面测试计数已重置

        Args:
            channel_num: 通道号
            count: 重置后的计数值
        """
        try:
            # 获取主界面引用
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'config_changed'):
                main_window = main_window.parent()

            if main_window and hasattr(main_window, 'config_changed'):
                # 发送测试计数变更信号
                main_window.config_changed.emit(f'test_count.channel_{channel_num}', count)
                logger.debug(f"已通知主界面通道{channel_num}测试计数重置: {count}")
            else:
                # 如果找不到主界面，尝试直接更新通道显示组件
                self._update_main_window_channel_count(channel_num, count)

        except Exception as e:
            logger.error(f"通知主界面测试计数重置失败: {e}")

    def _update_main_window_channel_count(self, channel_num: int, count: int):
        """
        直接更新主界面通道显示组件的测试计数

        Args:
            channel_num: 通道号
            count: 测试计数
        """
        try:
            # 获取主界面引用
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'ui_component_manager'):
                main_window = main_window.parent()

            if main_window and hasattr(main_window, 'ui_component_manager'):
                ui_manager = main_window.ui_component_manager

                # 更新通道容器的测试计数
                if hasattr(ui_manager, 'channels_container_widget'):
                    channels_container = ui_manager.channels_container_widget
                    if hasattr(channels_container, 'update_channel_test_count'):
                        channels_container.update_channel_test_count(channel_num, count)
                        logger.debug(f"已直接更新主界面通道{channel_num}测试计数: {count}")
                    elif hasattr(channels_container, 'channels') and len(channels_container.channels) >= channel_num:
                        # 直接更新通道显示组件
                        channel_widget = channels_container.channels[channel_num - 1]
                        if hasattr(channel_widget, 'test_count'):
                            channel_widget.test_count = count
                        if hasattr(channel_widget, '_update_test_count_display'):
                            channel_widget._update_test_count_display()
                        logger.debug(f"已直接更新通道{channel_num}显示组件测试计数: {count}")

        except Exception as e:
            logger.error(f"直接更新主界面通道{channel_num}测试计数失败: {e}")
