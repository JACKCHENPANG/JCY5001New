# -*- coding: utf-8 -*-
"""
数据上传配置对话框
允许用户配置数据上传相关设置
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
    QPushButton, QLabel, QTextEdit, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class DataUploadConfigDialog(QDialog):
    """数据上传配置对话框"""
    
    config_changed = pyqtSignal(dict)  # 配置变更信号
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.upload_manager = None
        
        self.setWindowTitle("数据上传配置")
        self.setFixedSize(600, 700)
        self.setModal(True)
        
        self.init_ui()
        self.load_config()
        
        # 状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(2000)  # 每2秒更新一次状态
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 基本配置组
        basic_group = QGroupBox("基本配置")
        basic_layout = QFormLayout(basic_group)
        
        self.enabled_checkbox = QCheckBox("启用数据上传")
        basic_layout.addRow("功能开关:", self.enabled_checkbox)
        
        self.server_url_edit = QLineEdit()
        self.server_url_edit.setPlaceholderText("https://ukukukukukukukuk.uk")
        basic_layout.addRow("服务器地址:", self.server_url_edit)
        
        self.endpoint_edit = QLineEdit()
        self.endpoint_edit.setPlaceholderText("/api/test-results")
        basic_layout.addRow("API端点:", self.endpoint_edit)
        
        self.device_id_edit = QLineEdit()
        self.device_id_edit.setPlaceholderText("JCY5001A_001")
        basic_layout.addRow("设备ID:", self.device_id_edit)
        
        layout.addWidget(basic_group)
        
        # 认证配置组
        auth_group = QGroupBox("认证配置")
        auth_layout = QFormLayout(auth_group)
        
        self.auth_type_combo = QComboBox()
        self.auth_type_combo.addItems(["bearer", "api_key", "basic", "none"])
        auth_layout.addRow("认证类型:", self.auth_type_combo)
        
        self.auth_token_edit = QLineEdit()
        self.auth_token_edit.setPlaceholderText("认证令牌（可选）")
        self.auth_token_edit.setEchoMode(QLineEdit.Password)
        auth_layout.addRow("认证令牌:", self.auth_token_edit)
        
        layout.addWidget(auth_group)
        
        # 高级配置组
        advanced_group = QGroupBox("高级配置")
        advanced_layout = QFormLayout(advanced_group)
        
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(5, 300)
        self.timeout_spinbox.setSuffix(" 秒")
        advanced_layout.addRow("超时时间:", self.timeout_spinbox)
        
        self.retry_count_spinbox = QSpinBox()
        self.retry_count_spinbox.setRange(0, 10)
        advanced_layout.addRow("重试次数:", self.retry_count_spinbox)
        
        self.retry_delay_spinbox = QDoubleSpinBox()
        self.retry_delay_spinbox.setRange(0.1, 10.0)
        self.retry_delay_spinbox.setSingleStep(0.1)
        self.retry_delay_spinbox.setSuffix(" 秒")
        advanced_layout.addRow("重试延时:", self.retry_delay_spinbox)
        
        layout.addWidget(advanced_group)
        
        # 上传选项组
        options_group = QGroupBox("上传选项")
        options_layout = QFormLayout(options_group)
        
        self.auto_upload_checkbox = QCheckBox("自动上传")
        options_layout.addRow("自动上传:", self.auto_upload_checkbox)
        
        self.upload_on_complete_checkbox = QCheckBox("测试完成后上传")
        options_layout.addRow("完成时上传:", self.upload_on_complete_checkbox)
        
        self.batch_upload_checkbox = QCheckBox("批量上传")
        options_layout.addRow("批量上传:", self.batch_upload_checkbox)
        
        layout.addWidget(options_group)
        
        # 状态显示组
        status_group = QGroupBox("上传状态")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("状态: 未知")
        status_layout.addWidget(self.status_label)
        
        self.queue_label = QLabel("队列: 0")
        status_layout.addWidget(self.queue_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        layout.addWidget(status_group)
        
        # 按钮组
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_button)
        
        button_layout.addStretch()
        
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_button)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def load_config(self):
        """加载配置"""
        try:
            upload_config = self.config_manager.get('data_upload', {})
            
            self.enabled_checkbox.setChecked(upload_config.get('enabled', True))
            self.server_url_edit.setText(upload_config.get('server_url', 'https://ukukukukukukukuk.uk'))
            self.endpoint_edit.setText(upload_config.get('endpoint', '/api/test-results'))
            self.device_id_edit.setText(upload_config.get('device_id', 'JCY5001A_001'))
            
            auth_type = upload_config.get('auth_type', 'bearer')
            index = self.auth_type_combo.findText(auth_type)
            if index >= 0:
                self.auth_type_combo.setCurrentIndex(index)
            
            self.auth_token_edit.setText(upload_config.get('auth_token', ''))
            
            self.timeout_spinbox.setValue(upload_config.get('timeout', 30))
            self.retry_count_spinbox.setValue(upload_config.get('retry_count', 3))
            self.retry_delay_spinbox.setValue(upload_config.get('retry_delay', 1.0))
            
            self.auto_upload_checkbox.setChecked(upload_config.get('auto_upload', True))
            self.upload_on_complete_checkbox.setChecked(upload_config.get('upload_on_test_complete', True))
            self.batch_upload_checkbox.setChecked(upload_config.get('upload_batch_results', False))
            
        except Exception as e:
            logger.error(f"加载数据上传配置失败: {e}")
            QMessageBox.warning(self, "警告", f"加载配置失败:\n{str(e)}")
    
    def save_config(self):
        """保存配置"""
        try:
            upload_config = {
                'enabled': self.enabled_checkbox.isChecked(),
                'server_url': self.server_url_edit.text().strip(),
                'endpoint': self.endpoint_edit.text().strip(),
                'device_id': self.device_id_edit.text().strip(),
                'auth_type': self.auth_type_combo.currentText(),
                'auth_token': self.auth_token_edit.text().strip(),
                'timeout': self.timeout_spinbox.value(),
                'retry_count': self.retry_count_spinbox.value(),
                'retry_delay': self.retry_delay_spinbox.value(),
                'auto_upload': self.auto_upload_checkbox.isChecked(),
                'upload_on_test_complete': self.upload_on_complete_checkbox.isChecked(),
                'upload_batch_results': self.batch_upload_checkbox.isChecked(),
                'description': "数据上传配置 - 测试完成后自动上传结果到远程服务器"
            }
            
            # 验证配置
            if upload_config['enabled']:
                if not upload_config['server_url']:
                    QMessageBox.warning(self, "警告", "请输入服务器地址")
                    return
                
                if not upload_config['endpoint']:
                    QMessageBox.warning(self, "警告", "请输入API端点")
                    return
            
            # 保存配置
            self.config_manager.set('data_upload', upload_config)
            
            # 发送配置变更信号
            self.config_changed.emit(upload_config)
            
            QMessageBox.information(self, "成功", "数据上传配置已保存")
            self.accept()
            
        except Exception as e:
            logger.error(f"保存数据上传配置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存配置失败:\n{str(e)}")
    
    def test_connection(self):
        """测试连接"""
        try:
            from backend.data_upload_manager import DataUploadManager
            
            # 获取当前配置
            test_config = {
                'enabled': True,
                'server_url': self.server_url_edit.text().strip(),
                'endpoint': self.endpoint_edit.text().strip(),
                'timeout': 10,
                'auth_type': self.auth_type_combo.currentText(),
                'auth_token': self.auth_token_edit.text().strip()
            }
            
            if not test_config['server_url']:
                QMessageBox.warning(self, "警告", "请输入服务器地址")
                return
            
            # 创建临时上传管理器
            test_manager = DataUploadManager(test_config)
            
            # 显示进度
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 不确定进度
            self.test_button.setEnabled(False)
            
            # 测试连接
            success = test_manager.test_connection()
            
            # 隐藏进度
            self.progress_bar.setVisible(False)
            self.test_button.setEnabled(True)
            
            if success:
                QMessageBox.information(self, "成功", "服务器连接测试成功！")
            else:
                QMessageBox.warning(self, "失败", "服务器连接测试失败！\n请检查服务器地址和网络连接。")
                
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.test_button.setEnabled(True)
            logger.error(f"测试连接失败: {e}")
            QMessageBox.critical(self, "错误", f"测试连接失败:\n{str(e)}")
    
    def update_status(self):
        """更新状态显示"""
        try:
            if not self.upload_manager:
                # 尝试获取上传管理器
                from backend.test_result_manager import TestResultManager
                # 这里需要从主窗口获取实际的上传管理器实例
                return
            
            status = self.upload_manager.get_upload_status()
            
            if status.get('enabled', False):
                if status.get('thread_running', False):
                    self.status_label.setText("状态: 运行中")
                    self.status_label.setStyleSheet("color: green;")
                else:
                    self.status_label.setText("状态: 已停止")
                    self.status_label.setStyleSheet("color: red;")
            else:
                self.status_label.setText("状态: 已禁用")
                self.status_label.setStyleSheet("color: gray;")
            
            queue_size = status.get('queue_size', 0)
            self.queue_label.setText(f"队列: {queue_size}")
            
        except Exception as e:
            logger.debug(f"更新状态失败: {e}")
    
    def closeEvent(self, event):
        """关闭事件"""
        self.status_timer.stop()
        super().closeEvent(event)
