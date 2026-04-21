# -*- coding: utf-8 -*-
"""
硬件指纹显示组件
显示硬件指纹信息和系统信息

Author: Jack
Date: 2025-06-08
"""

import logging
import platform
import subprocess
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QGroupBox, QMessageBox, QApplication, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class HardwareFingerprintWidget(QWidget):
    """硬件指纹显示组件"""
    
    def __init__(self, license_manager, parent=None):
        """
        初始化硬件指纹组件
        
        Args:
            license_manager: 授权管理器
            parent: 父组件
        """
        super().__init__(parent)
        
        self.license_manager = license_manager
        
        self._init_ui()
        self.refresh_status()
        
        logger.debug("硬件指纹组件初始化完成")
    
    def _init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建硬件指纹显示区域
        self._create_fingerprint_section(main_layout)
        
        # 创建系统信息区域
        self._create_system_info_section(main_layout)
        
        # 创建硬件详细信息区域
        self._create_hardware_details_section(main_layout)
    
    def _create_fingerprint_section(self, main_layout):
        """创建硬件指纹显示区域"""
        fingerprint_group = QGroupBox("硬件指纹")
        fingerprint_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14pt;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        fingerprint_layout = QVBoxLayout(fingerprint_group)
        
        # 说明文字
        info_label = QLabel("硬件指纹是基于您的计算机硬件生成的唯一标识符，用于软件授权验证：")
        info_label.setFont(QFont("", 10))
        info_label.setStyleSheet("color: #34495e; margin-bottom: 10px;")
        info_label.setWordWrap(True)
        fingerprint_layout.addWidget(info_label)
        
        # 硬件指纹显示
        self.fingerprint_display = QTextEdit()
        self.fingerprint_display.setMaximumHeight(80)
        self.fingerprint_display.setReadOnly(True)
        self.fingerprint_display.setPlaceholderText("正在获取硬件指纹...")
        self.fingerprint_display.setStyleSheet("""
            QTextEdit {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Courier New', monospace;
                font-size: 11pt;
                background-color: #f8f9fa;
                color: #2c3e50;
            }
        """)
        fingerprint_layout.addWidget(self.fingerprint_display)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 复制按钮
        copy_button = QPushButton("复制硬件指纹")
        copy_button.clicked.connect(self._copy_fingerprint)
        copy_button.setStyleSheet("""
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
        """)
        
        # 刷新按钮
        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self.refresh_status)
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        
        button_layout.addWidget(copy_button)
        button_layout.addWidget(refresh_button)
        button_layout.addStretch()
        
        fingerprint_layout.addLayout(button_layout)
        
        main_layout.addWidget(fingerprint_group)
    
    def _create_system_info_section(self, main_layout):
        """创建系统信息区域"""
        system_group = QGroupBox("系统信息")
        system_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14pt;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        system_layout = QGridLayout(system_group)
        system_layout.setSpacing(10)
        
        # 系统信息标签
        system_info_labels = [
            ("操作系统:", "os_info"),
            ("计算机名:", "computer_name"),
            ("处理器:", "processor_info"),
            ("Python版本:", "python_version"),
            ("系统架构:", "system_arch"),
            ("用户名:", "username")
        ]
        
        for i, (label_text, attr_name) in enumerate(system_info_labels):
            # 标签
            label = QLabel(label_text)
            label.setFont(QFont("", 10, QFont.Bold))
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # 值
            value_label = QLabel("获取中...")
            value_label.setFont(QFont("", 10))
            value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value_label.setWordWrap(True)
            setattr(self, attr_name, value_label)
            
            system_layout.addWidget(label, i, 0)
            system_layout.addWidget(value_label, i, 1)
        
        main_layout.addWidget(system_group)
    
    def _create_hardware_details_section(self, main_layout):
        """创建硬件详细信息区域"""
        hardware_group = QGroupBox("硬件详细信息")
        hardware_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14pt;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        hardware_layout = QVBoxLayout(hardware_group)
        
        # 硬件详细信息显示
        self.hardware_details = QTextEdit()
        self.hardware_details.setMaximumHeight(150)
        self.hardware_details.setReadOnly(True)
        self.hardware_details.setPlaceholderText("正在获取硬件详细信息...")
        self.hardware_details.setStyleSheet("""
            QTextEdit {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 8px;
                font-size: 9pt;
                background-color: #f8f9fa;
                color: #2c3e50;
            }
        """)
        
        hardware_layout.addWidget(self.hardware_details)
        
        main_layout.addWidget(hardware_group)
    
    def _copy_fingerprint(self):
        """复制硬件指纹"""
        try:
            fingerprint_text = self.fingerprint_display.toPlainText().strip()
            if fingerprint_text:
                clipboard = QApplication.clipboard()
                clipboard.setText(fingerprint_text)
                QMessageBox.information(self, "复制成功", "硬件指纹已复制到剪贴板")
            else:
                QMessageBox.warning(self, "复制失败", "没有可复制的硬件指纹")
                
        except Exception as e:
            logger.error(f"复制硬件指纹失败: {e}")
            QMessageBox.warning(self, "复制失败", f"复制失败：{e}")
    
    def refresh_status(self):
        """刷新状态"""
        try:
            # 获取硬件指纹
            self._update_fingerprint()
            
            # 获取系统信息
            self._update_system_info()
            
            # 获取硬件详细信息
            self._update_hardware_details()
            
        except Exception as e:
            logger.error(f"刷新硬件信息失败: {e}")
    
    def _update_fingerprint(self):
        """更新硬件指纹显示"""
        try:
            if self.license_manager:
                fingerprint = self.license_manager.get_hardware_fingerprint()
                if fingerprint:
                    # 格式化显示硬件指纹
                    formatted_fingerprint = self._format_fingerprint(fingerprint)
                    self.fingerprint_display.setText(formatted_fingerprint)
                else:
                    self.fingerprint_display.setText("无法获取硬件指纹")
            else:
                self.fingerprint_display.setText("授权管理器未初始化")
                
        except Exception as e:
            logger.error(f"更新硬件指纹失败: {e}")
            self.fingerprint_display.setText(f"获取失败: {e}")
    
    def _format_fingerprint(self, fingerprint):
        """格式化硬件指纹显示"""
        try:
            # 将长字符串分行显示，每行16个字符
            lines = []
            for i in range(0, len(fingerprint), 16):
                line = fingerprint[i:i+16]
                # 每4个字符加一个空格
                formatted_line = ' '.join([line[j:j+4] for j in range(0, len(line), 4)])
                lines.append(formatted_line)
            
            return '\n'.join(lines)
            
        except Exception as e:
            logger.error(f"格式化硬件指纹失败: {e}")
            return fingerprint
    
    def _update_system_info(self):
        """更新系统信息"""
        try:
            # 操作系统
            os_info = f"{platform.system()} {platform.release()}"
            self.os_info.setText(os_info)
            
            # 计算机名
            computer_name = platform.node()
            self.computer_name.setText(computer_name)
            
            # 处理器
            processor = platform.processor() or "未知"
            self.processor_info.setText(processor)
            
            # Python版本
            python_version = platform.python_version()
            self.python_version.setText(python_version)
            
            # 系统架构
            system_arch = platform.machine()
            self.system_arch.setText(system_arch)
            
            # 用户名
            import getpass
            username = getpass.getuser()
            self.username.setText(username)
            
        except Exception as e:
            logger.error(f"更新系统信息失败: {e}")
    
    def _update_hardware_details(self):
        """更新硬件详细信息"""
        try:
            details = []
            
            # 获取CPU信息
            cpu_info = self._get_cpu_info()
            if cpu_info:
                details.append(f"CPU信息: {cpu_info}")
            
            # 获取内存信息
            memory_info = self._get_memory_info()
            if memory_info:
                details.append(f"内存信息: {memory_info}")
            
            # 获取磁盘信息
            disk_info = self._get_disk_info()
            if disk_info:
                details.append(f"磁盘信息: {disk_info}")
            
            # 获取网络信息
            network_info = self._get_network_info()
            if network_info:
                details.append(f"网络信息: {network_info}")
            
            if details:
                self.hardware_details.setText('\n\n'.join(details))
            else:
                self.hardware_details.setText("无法获取硬件详细信息")
                
        except Exception as e:
            logger.error(f"更新硬件详细信息失败: {e}")
            self.hardware_details.setText(f"获取失败: {e}")
    
    def _get_cpu_info(self):
        """获取CPU信息"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['wmic', 'cpu', 'get', 'Name', '/value'],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.split('\n'):
                    if 'Name=' in line:
                        cpu_name = line.split('=')[1].strip()
                        if cpu_name:
                            return cpu_name
            return platform.processor()
        except:
            return "获取失败"
    
    def _get_memory_info(self):
        """获取内存信息"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['wmic', 'computersystem', 'get', 'TotalPhysicalMemory', '/value'],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.split('\n'):
                    if 'TotalPhysicalMemory=' in line:
                        memory_bytes = line.split('=')[1].strip()
                        if memory_bytes:
                            memory_gb = round(int(memory_bytes) / (1024**3), 2)
                            return f"{memory_gb} GB"
            return "获取失败"
        except:
            return "获取失败"
    
    def _get_disk_info(self):
        """获取磁盘信息"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['wmic', 'diskdrive', 'get', 'Size,Model', '/value'],
                    capture_output=True, text=True, timeout=5
                )
                disks = []
                current_disk = {}
                for line in result.stdout.split('\n'):
                    if 'Model=' in line:
                        model = line.split('=')[1].strip()
                        if model:
                            current_disk['model'] = model
                    elif 'Size=' in line:
                        size = line.split('=')[1].strip()
                        if size:
                            size_gb = round(int(size) / (1024**3), 2)
                            current_disk['size'] = f"{size_gb} GB"
                            if 'model' in current_disk:
                                disks.append(f"{current_disk['model']} ({current_disk['size']})")
                            current_disk = {}
                
                return '; '.join(disks) if disks else "获取失败"
            return "获取失败"
        except:
            return "获取失败"
    
    def _get_network_info(self):
        """获取网络信息"""
        try:
            import uuid
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                           for elements in range(0, 2*6, 2)][::-1])
            return f"MAC地址: {mac}"
        except:
            return "获取失败"
