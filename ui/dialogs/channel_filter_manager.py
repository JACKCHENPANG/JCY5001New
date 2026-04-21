# -*- coding: utf-8 -*-
"""
通道筛选管理器
负责管理多通道选择功能

Author: Jack
Date: 2024-12-14
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QCheckBox, QPushButton, QGroupBox, QScrollArea)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class ChannelFilterWidget(QWidget):
    """
    通道筛选组件
    
    职责：
    - 提供多通道选择界面
    - 管理通道选择状态
    - 发送选择变更信号
    """
    
    # 信号定义
    selection_changed = pyqtSignal(list)  # 选择变更信号，传递选中的通道列表
    
    def __init__(self, parent=None):
        """
        初始化通道筛选组件
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        
        # 通道复选框列表
        self.channel_checkboxes = {}
        
        # 初始化界面
        self._init_ui()
        self._init_connections()
        
        logger.debug("通道筛选组件初始化完成")
    
    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 标题
        title_label = QLabel("通道选择")
        title_label.setFont(QFont("", 9, QFont.Bold))
        layout.addWidget(title_label)
        
        # 全选/全不选按钮
        button_layout = QHBoxLayout()
        self.select_all_button = QPushButton("全选")
        self.select_none_button = QPushButton("全不选")
        
        self.select_all_button.setMaximumHeight(25)
        self.select_none_button.setMaximumHeight(25)
        
        button_layout.addWidget(self.select_all_button)
        button_layout.addWidget(self.select_none_button)
        layout.addLayout(button_layout)
        
        # 通道复选框区域
        self._create_channel_checkboxes()
        layout.addWidget(self.channel_group)
    
    def _create_channel_checkboxes(self):
        """创建通道复选框"""
        self.channel_group = QGroupBox()
        channel_layout = QVBoxLayout(self.channel_group)
        channel_layout.setContentsMargins(5, 5, 5, 5)
        channel_layout.setSpacing(3)

        # 初始创建8个通道的复选框（默认）
        self._create_checkboxes_for_channels(8)

    def _create_checkboxes_for_channels(self, channel_count: int):
        """
        为指定数量的通道创建复选框

        Args:
            channel_count: 通道数量
        """
        # 清除现有的复选框
        self._clear_checkboxes()

        # 创建新的复选框
        for i in range(1, channel_count + 1):
            checkbox = QCheckBox(f"通道{i}")
            checkbox.setChecked(True)  # 默认全选
            self.channel_checkboxes[i] = checkbox
            self.channel_group.layout().addWidget(checkbox)

    def _clear_checkboxes(self):
        """清除所有复选框"""
        # 断开信号连接
        for checkbox in self.channel_checkboxes.values():
            checkbox.stateChanged.disconnect()

        # 清除布局中的组件
        layout = self.channel_group.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # 清空字典
        self.channel_checkboxes.clear()
    
    def _init_connections(self):
        """初始化信号连接"""
        # 全选/全不选按钮
        self.select_all_button.clicked.connect(self._select_all_channels)
        self.select_none_button.clicked.connect(self._select_no_channels)
        
        # 通道复选框变更
        for checkbox in self.channel_checkboxes.values():
            checkbox.stateChanged.connect(self._on_channel_selection_changed)
    
    def _select_all_channels(self):
        """全选所有通道"""
        for checkbox in self.channel_checkboxes.values():
            checkbox.setChecked(True)
    
    def _select_no_channels(self):
        """取消选择所有通道"""
        for checkbox in self.channel_checkboxes.values():
            checkbox.setChecked(False)
    
    def _on_channel_selection_changed(self):
        """通道选择变更处理"""
        selected_channels = self.get_selected_channels()
        self.selection_changed.emit(selected_channels)
        logger.debug(f"通道选择变更: {selected_channels}")
    
    def get_selected_channels(self) -> List[int]:
        """
        获取选中的通道列表
        
        Returns:
            选中的通道号列表
        """
        selected = []
        for channel_num, checkbox in self.channel_checkboxes.items():
            if checkbox.isChecked():
                selected.append(channel_num)
        return selected
    
    def set_selected_channels(self, channels: List[int]):
        """
        设置选中的通道
        
        Args:
            channels: 要选中的通道号列表
        """
        # 先取消所有选择
        for checkbox in self.channel_checkboxes.values():
            checkbox.setChecked(False)
        
        # 选中指定通道
        for channel_num in channels:
            if channel_num in self.channel_checkboxes:
                self.channel_checkboxes[channel_num].setChecked(True)
    
    def is_all_selected(self) -> bool:
        """
        检查是否全选
        
        Returns:
            是否全选
        """
        return len(self.get_selected_channels()) == len(self.channel_checkboxes)
    
    def is_none_selected(self) -> bool:
        """
        检查是否全不选
        
        Returns:
            是否全不选
        """
        return len(self.get_selected_channels()) == 0

    def update_channel_count(self, channel_count: int):
        """
        更新通道数量

        Args:
            channel_count: 新的通道数量
        """
        if channel_count <= 0:
            channel_count = 8  # 默认8通道

        current_count = len(self.channel_checkboxes)
        if current_count != channel_count:
            logger.info(f"更新通道数量: {current_count} -> {channel_count}")

            # 保存当前选择状态
            current_selection = self.get_selected_channels()

            # 重新创建复选框
            self._create_checkboxes_for_channels(channel_count)

            # 恢复选择状态（仅对有效通道）
            valid_selection = [ch for ch in current_selection if ch <= channel_count]
            if valid_selection:
                self.set_selected_channels(valid_selection)

            # 重新连接信号
            self._init_connections()

            # 发送选择变更信号
            self._on_channel_selection_changed()

    def get_communication_manager(self):
        """获取通信管理器实例"""
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in QApplication.topLevelWidgets():
                    if hasattr(widget, 'comm_manager'):
                        return widget.comm_manager
            return None
        except Exception as e:
            logger.debug(f"获取通信管理器失败: {e}")
            return None

    def refresh_from_device(self):
        """从设备刷新通道数量"""
        try:
            comm_manager = self.get_communication_manager()
            if comm_manager and comm_manager.is_connected:
                channel_count = comm_manager.get_channel_count()
                if channel_count > 0:
                    self.update_channel_count(channel_count)
                    logger.info(f"从设备获取通道数量: {channel_count}")
                else:
                    logger.warning("设备返回的通道数量为0，使用默认8通道")
                    self.update_channel_count(8)
            else:
                logger.info("设备未连接，使用默认8通道")
                self.update_channel_count(8)
        except Exception as e:
            logger.error(f"从设备刷新通道数量失败: {e}")
            self.update_channel_count(8)


class ChannelFilterManager:
    """
    通道筛选管理器
    
    职责：
    - 管理通道筛选逻辑
    - 处理通道筛选条件转换
    - 提供筛选条件接口
    """
    
    def __init__(self):
        """初始化通道筛选管理器"""
        self.selected_channels = list(range(1, 9))  # 默认全选
        logger.debug("通道筛选管理器初始化完成")
    
    def update_selected_channels(self, channels: List[int]):
        """
        更新选中的通道
        
        Args:
            channels: 选中的通道列表
        """
        self.selected_channels = channels.copy()
        logger.debug(f"更新选中通道: {self.selected_channels}")
    
    def get_filter_condition(self) -> Optional[List[int]]:
        """
        获取筛选条件
        
        Returns:
            筛选条件，None表示不筛选，空列表表示无匹配，非空列表表示筛选条件
        """
        if len(self.selected_channels) == 8:
            # 全选时不需要筛选
            return None
        elif len(self.selected_channels) == 0:
            # 全不选时返回空列表（无匹配）
            return []
        else:
            # 部分选择时返回选中的通道
            return self.selected_channels.copy()
    
    def is_channel_selected(self, channel_num: int) -> bool:
        """
        检查指定通道是否被选中
        
        Args:
            channel_num: 通道号
            
        Returns:
            是否被选中
        """
        return channel_num in self.selected_channels
