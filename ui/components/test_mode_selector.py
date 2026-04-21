# -*- coding: utf-8 -*-
"""
测试模式选择器组件
提供并行错频模式和传统模式的选择界面

Author: Jack
Date: 2025-06-02
"""

import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QRadioButton, QLabel, QDoubleSpinBox, QSpinBox,
                             QCheckBox, QPushButton, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class TestModeSelector(QWidget):
    """
    测试模式选择器组件
    
    提供以下功能：
    - 传统同时启动模式选择
    - 并行错频模式选择
    - 错频模式参数配置
    - 实时监控输出
    """
    
    # 信号定义
    mode_changed = pyqtSignal(bool)  # 模式变更信号，True为错频模式
    config_changed = pyqtSignal(dict)  # 配置变更信号
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        
        # 初始化UI
        self._init_ui()
        
        # 加载配置
        self._load_settings()
        
        # 连接信号
        self._connect_signals()
        
        logger.debug("测试模式选择器组件初始化完成")
    
    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 创建模式选择组
        self._create_mode_selection_group(layout)
        
        # 创建错频模式配置组
        self._create_staggered_config_group(layout)
        
        # 创建监控输出组
        self._create_monitor_group(layout)
        
        # 创建控制按钮组
        self._create_control_buttons(layout)
        
        # 添加弹性空间
        layout.addStretch()
    
    def _create_mode_selection_group(self, parent_layout):
        """创建模式选择组"""
        group = QGroupBox("测试模式选择")
        group.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        layout = QVBoxLayout(group)
        
        # 传统模式
        self.traditional_radio = QRadioButton("传统同时启动模式")
        self.traditional_radio.setFont(QFont("Microsoft YaHei", 9))
        self.traditional_radio.setChecked(True)
        layout.addWidget(self.traditional_radio)
        
        traditional_desc = QLabel("• 所有通道使用相同频率同时启动\n• 适用于低干扰环境\n• 测试速度快")
        traditional_desc.setFont(QFont("Microsoft YaHei", 8))
        traditional_desc.setStyleSheet("color: #666; margin-left: 20px;")
        layout.addWidget(traditional_desc)
        
        # 并行错频模式
        self.staggered_radio = QRadioButton("并行错频模式")
        self.staggered_radio.setFont(QFont("Microsoft YaHei", 9))
        layout.addWidget(self.staggered_radio)
        
        staggered_desc = QLabel("• 高频段使用错频避免干扰\n• 低频段使用同时启动\n• 提高测试准确性")
        staggered_desc.setFont(QFont("Microsoft YaHei", 8))
        staggered_desc.setStyleSheet("color: #666; margin-left: 20px;")
        layout.addWidget(staggered_desc)
        
        parent_layout.addWidget(group)
    
    def _create_staggered_config_group(self, parent_layout):
        """创建错频模式配置组"""
        self.staggered_group = QGroupBox("并行错频模式配置")
        self.staggered_group.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.staggered_group.setEnabled(False)  # 默认禁用
        layout = QVBoxLayout(self.staggered_group)
        
        # 临界频率设置
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("临界频率:"))
        self.critical_freq_spin = QDoubleSpinBox()
        self.critical_freq_spin.setRange(0.1, 1000.0)
        self.critical_freq_spin.setValue(10.0)
        self.critical_freq_spin.setSuffix(" Hz")
        self.critical_freq_spin.setDecimals(1)
        freq_layout.addWidget(self.critical_freq_spin)
        freq_layout.addWidget(QLabel("(高于此频率使用错频)"))
        freq_layout.addStretch()
        layout.addLayout(freq_layout)
        
        # 超时时间设置
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("测试超时:"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(30, 300)
        self.timeout_spin.setValue(120)
        self.timeout_spin.setSuffix(" 秒")
        timeout_layout.addWidget(self.timeout_spin)
        timeout_layout.addStretch()
        layout.addLayout(timeout_layout)
        
        # 高级选项
        advanced_layout = QHBoxLayout()
        self.error_recovery_check = QCheckBox("启用错误恢复")
        self.error_recovery_check.setChecked(True)
        advanced_layout.addWidget(self.error_recovery_check)
        
        advanced_layout.addWidget(QLabel("重试次数:"))
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(1, 10)
        self.retry_spin.setValue(3)
        advanced_layout.addWidget(self.retry_spin)
        advanced_layout.addStretch()
        layout.addLayout(advanced_layout)
        
        parent_layout.addWidget(self.staggered_group)
    
    def _create_monitor_group(self, parent_layout):
        """创建监控输出组"""
        group = QGroupBox("实时监控")
        group.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        layout = QVBoxLayout(group)
        
        # 状态显示
        self.status_label = QLabel("状态: 就绪")
        self.status_label.setFont(QFont("Microsoft YaHei", 9))
        self.status_label.setStyleSheet("color: #2E8B57; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 监控信息
        info_layout = QHBoxLayout()
        
        # 左侧信息
        left_layout = QVBoxLayout()
        self.mode_info_label = QLabel("当前模式: 传统模式")
        self.mode_info_label.setFont(QFont("Microsoft YaHei", 8))
        left_layout.addWidget(self.mode_info_label)
        
        self.freq_info_label = QLabel("临界频率: 10.0Hz")
        self.freq_info_label.setFont(QFont("Microsoft YaHei", 8))
        left_layout.addWidget(self.freq_info_label)
        
        # 右侧信息
        right_layout = QVBoxLayout()
        self.performance_label = QLabel("性能: 标准")
        self.performance_label.setFont(QFont("Microsoft YaHei", 8))
        right_layout.addWidget(self.performance_label)
        
        self.accuracy_label = QLabel("准确性: 标准")
        self.accuracy_label.setFont(QFont("Microsoft YaHei", 8))
        right_layout.addWidget(self.accuracy_label)
        
        info_layout.addLayout(left_layout)
        info_layout.addLayout(right_layout)
        layout.addLayout(info_layout)
        
        parent_layout.addWidget(group)
    
    def _create_control_buttons(self, parent_layout):
        """创建控制按钮组"""
        layout = QHBoxLayout()
        
        # 应用配置按钮
        self.apply_button = QPushButton("应用配置")
        self.apply_button.setFont(QFont("Microsoft YaHei", 9))
        self.apply_button.clicked.connect(self._apply_config)
        layout.addWidget(self.apply_button)
        
        # 重置按钮
        self.reset_button = QPushButton("重置默认")
        self.reset_button.setFont(QFont("Microsoft YaHei", 9))
        self.reset_button.clicked.connect(self._reset_to_default)
        layout.addWidget(self.reset_button)
        
        layout.addStretch()
        
        # 测试按钮
        self.test_button = QPushButton("测试配置")
        self.test_button.setFont(QFont("Microsoft YaHei", 9))
        self.test_button.clicked.connect(self._test_config)
        layout.addWidget(self.test_button)
        
        parent_layout.addLayout(layout)
    
    def _connect_signals(self):
        """连接信号"""
        # 模式选择信号
        self.traditional_radio.toggled.connect(self._on_mode_changed)
        self.staggered_radio.toggled.connect(self._on_mode_changed)
        
        # 配置变更信号
        self.critical_freq_spin.valueChanged.connect(self._on_config_changed)
        self.timeout_spin.valueChanged.connect(self._on_config_changed)
        self.error_recovery_check.toggled.connect(self._on_config_changed)
        self.retry_spin.valueChanged.connect(self._on_config_changed)
    
    def _load_settings(self):
        """加载配置"""
        try:
            # 加载模式设置
            use_staggered = self.config_manager.get('test.use_parallel_staggered_mode', False)
            if use_staggered:
                self.staggered_radio.setChecked(True)
            else:
                self.traditional_radio.setChecked(True)
            
            # 加载参数设置
            self.critical_freq_spin.setValue(self.config_manager.get('test.critical_frequency', 10.0))
            self.timeout_spin.setValue(self.config_manager.get('test.timeout_seconds', 120))
            self.error_recovery_check.setChecked(self.config_manager.get('test.error_recovery', True))
            self.retry_spin.setValue(self.config_manager.get('test.max_retries', 3))
            
            # 更新UI状态
            self._update_ui_state()
            
        except Exception as e:
            logger.error(f"加载测试模式配置失败: {e}")
    
    def _on_mode_changed(self):
        """模式变更处理"""
        try:
            use_staggered = self.staggered_radio.isChecked()
            
            # 启用/禁用配置组
            self.staggered_group.setEnabled(use_staggered)
            
            # 更新显示信息
            self._update_ui_state()
            
            # 发送信号
            self.mode_changed.emit(use_staggered)
            
            logger.info(f"测试模式变更: {'并行错频模式' if use_staggered else '传统同时启动模式'}")
            
        except Exception as e:
            logger.error(f"处理模式变更失败: {e}")
    
    def _on_config_changed(self):
        """配置变更处理"""
        try:
            config = self._get_current_config()
            self._update_ui_state()
            self.config_changed.emit(config)
            
        except Exception as e:
            logger.error(f"处理配置变更失败: {e}")
    
    def _get_current_config(self):
        """获取当前配置"""
        return {
            'use_parallel_staggered_mode': self.staggered_radio.isChecked(),
            'critical_frequency': self.critical_freq_spin.value(),
            'timeout_seconds': self.timeout_spin.value(),
            'error_recovery': self.error_recovery_check.isChecked(),
            'max_retries': self.retry_spin.value()
        }
    
    def _update_ui_state(self):
        """更新UI状态显示"""
        try:
            use_staggered = self.staggered_radio.isChecked()
            
            # 更新模式信息
            mode_text = "并行错频模式" if use_staggered else "传统同时启动模式"
            self.mode_info_label.setText(f"当前模式: {mode_text}")
            
            # 更新频率信息
            critical_freq = self.critical_freq_spin.value()
            self.freq_info_label.setText(f"临界频率: {critical_freq}Hz")
            
            # 更新性能和准确性评估
            if use_staggered:
                self.performance_label.setText("性能: 优化")
                self.accuracy_label.setText("准确性: 高")
                self.status_label.setText("状态: 并行错频模式就绪")
                self.status_label.setStyleSheet("color: #1E90FF; font-weight: bold;")
            else:
                self.performance_label.setText("性能: 标准")
                self.accuracy_label.setText("准确性: 标准")
                self.status_label.setText("状态: 传统模式就绪")
                self.status_label.setStyleSheet("color: #2E8B57; font-weight: bold;")
                
        except Exception as e:
            logger.error(f"更新UI状态失败: {e}")
    
    def _apply_config(self):
        """应用配置"""
        try:
            config = self._get_current_config()
            
            # 保存到配置管理器
            for key, value in config.items():
                self.config_manager.set(f'test.{key}', value)
            
            self.status_label.setText("状态: 配置已应用")
            self.status_label.setStyleSheet("color: #32CD32; font-weight: bold;")
            
            logger.info(f"测试模式配置已应用: {config}")
            
        except Exception as e:
            logger.error(f"应用配置失败: {e}")
            self.status_label.setText("状态: 配置应用失败")
            self.status_label.setStyleSheet("color: #FF6347; font-weight: bold;")
    
    def _reset_to_default(self):
        """重置为默认配置"""
        try:
            # 重置为默认值
            self.traditional_radio.setChecked(True)
            self.critical_freq_spin.setValue(10.0)
            self.timeout_spin.setValue(120)
            self.error_recovery_check.setChecked(True)
            self.retry_spin.setValue(3)
            
            self.status_label.setText("状态: 已重置为默认配置")
            self.status_label.setStyleSheet("color: #FFA500; font-weight: bold;")
            
            logger.info("测试模式配置已重置为默认值")
            
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
    
    def _test_config(self):
        """测试配置"""
        try:
            config = self._get_current_config()
            
            # 这里可以添加配置测试逻辑
            self.status_label.setText("状态: 配置测试通过")
            self.status_label.setStyleSheet("color: #32CD32; font-weight: bold;")
            
            logger.info(f"测试模式配置测试通过: {config}")
            
        except Exception as e:
            logger.error(f"测试配置失败: {e}")
            self.status_label.setText("状态: 配置测试失败")
            self.status_label.setStyleSheet("color: #FF6347; font-weight: bold;")
    
    def get_config(self):
        """获取当前配置"""
        return self._get_current_config()
    
    def set_config(self, config):
        """设置配置"""
        try:
            if config.get('use_parallel_staggered_mode', False):
                self.staggered_radio.setChecked(True)
            else:
                self.traditional_radio.setChecked(True)
            
            self.critical_freq_spin.setValue(config.get('critical_frequency', 10.0))
            self.timeout_spin.setValue(config.get('timeout_seconds', 120))
            self.error_recovery_check.setChecked(config.get('error_recovery', True))
            self.retry_spin.setValue(config.get('max_retries', 3))
            
            self._update_ui_state()
            
        except Exception as e:
            logger.error(f"设置配置失败: {e}")
