"""
数据库同步对话框
提供数据同步功能的用户界面
"""

import logging
import threading
from datetime import datetime
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QTextEdit, QGroupBox, QGridLayout, QCheckBox,
    QSpinBox, QLineEdit, QComboBox, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QIcon

logger = logging.getLogger(__name__)


class SyncWorkerThread(QThread):
    """同步工作线程"""
    
    progress_updated = pyqtSignal(str)  # 进度更新信号
    sync_completed = pyqtSignal(dict)   # 同步完成信号
    error_occurred = pyqtSignal(str)    # 错误信号
    
    def __init__(self, sync_manager, sync_type='incremental'):
        super().__init__()
        self.sync_manager = sync_manager
        self.sync_type = sync_type
        self.is_running = False
    
    def run(self):
        """执行同步任务"""
        try:
            self.is_running = True
            self.progress_updated.emit("开始数据同步...")
            
            if self.sync_type == 'full':
                result = self.sync_manager.perform_full_sync()
            elif self.sync_type == 'incremental':
                result = self.sync_manager.perform_incremental_sync()
            else:
                result = {'success': False, 'errors': ['未知的同步类型']}
            
            self.sync_completed.emit(result)
            
        except Exception as e:
            logger.error(f"同步线程异常: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.is_running = False
    
    def stop(self):
        """停止同步"""
        self.is_running = False
        self.terminate()


class DatabaseSyncDialog(QDialog):
    """数据库同步对话框"""
    
    def __init__(self, sync_manager=None, parent=None):
        """
        初始化数据库同步对话框
        
        Args:
            sync_manager: 数据库同步管理器
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.sync_manager = sync_manager
        self.sync_worker = None
        
        self._init_ui()
        self._init_timer()
        self._load_sync_status()
        
        logger.debug("数据库同步对话框初始化完成")
    
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("数据库同步管理")
        self.setFixedSize(600, 700)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建各个功能区域
        self._create_status_section(main_layout)
        self._create_config_section(main_layout)
        self._create_sync_section(main_layout)
        self._create_progress_section(main_layout)
        self._create_log_section(main_layout)
        self._create_button_section(main_layout)
    
    def _create_status_section(self, main_layout):
        """创建状态显示区域"""
        status_group = QGroupBox("同步状态")
        status_group.setFont(QFont("", 10, QFont.Bold))
        main_layout.addWidget(status_group)
        
        status_layout = QGridLayout(status_group)
        
        # 设备ID显示
        status_layout.addWidget(QLabel("设备ID:"), 0, 0)
        self.device_id_label = QLabel("获取中...")
        self.device_id_label.setStyleSheet("color: #2c3e50; font-family: monospace;")
        status_layout.addWidget(self.device_id_label, 0, 1)
        
        # 服务器状态
        status_layout.addWidget(QLabel("服务器状态:"), 1, 0)
        self.server_status_label = QLabel("检查中...")
        status_layout.addWidget(self.server_status_label, 1, 1)
        
        # 上次同步时间
        status_layout.addWidget(QLabel("上次同步:"), 2, 0)
        self.last_sync_label = QLabel("从未同步")
        status_layout.addWidget(self.last_sync_label, 2, 1)
        
        # 同步统计
        status_layout.addWidget(QLabel("已同步记录:"), 3, 0)
        self.synced_count_label = QLabel("0")
        status_layout.addWidget(self.synced_count_label, 3, 1)
        
        # 失败记录
        status_layout.addWidget(QLabel("失败记录:"), 4, 0)
        self.failed_count_label = QLabel("0")
        status_layout.addWidget(self.failed_count_label, 4, 1)
    
    def _create_config_section(self, main_layout):
        """创建配置区域"""
        config_group = QGroupBox("同步配置")
        config_group.setFont(QFont("", 10, QFont.Bold))
        main_layout.addWidget(config_group)
        
        config_layout = QGridLayout(config_group)
        
        # 服务器地址
        config_layout.addWidget(QLabel("服务器地址:"), 0, 0)
        self.server_url_input = QLineEdit()
        self.server_url_input.setPlaceholderText("https://ukukukukukukukuk.uk")
        config_layout.addWidget(self.server_url_input, 0, 1)
        
        # 同步间隔
        config_layout.addWidget(QLabel("同步间隔(分钟):"), 1, 0)
        self.sync_interval_input = QSpinBox()
        self.sync_interval_input.setRange(1, 1440)  # 1分钟到24小时
        self.sync_interval_input.setValue(5)
        config_layout.addWidget(self.sync_interval_input, 1, 1)
        
        # 批量大小
        config_layout.addWidget(QLabel("批量大小:"), 2, 0)
        self.batch_size_input = QSpinBox()
        self.batch_size_input.setRange(1, 1000)
        self.batch_size_input.setValue(50)
        config_layout.addWidget(self.batch_size_input, 2, 1)
        
        # 自动同步
        self.auto_sync_checkbox = QCheckBox("启用自动同步")
        self.auto_sync_checkbox.setChecked(True)
        config_layout.addWidget(self.auto_sync_checkbox, 3, 0, 1, 2)
        
        # 增量同步
        self.incremental_sync_checkbox = QCheckBox("启用增量同步")
        self.incremental_sync_checkbox.setChecked(True)
        config_layout.addWidget(self.incremental_sync_checkbox, 4, 0, 1, 2)
    
    def _create_sync_section(self, main_layout):
        """创建同步操作区域"""
        sync_group = QGroupBox("同步操作")
        sync_group.setFont(QFont("", 10, QFont.Bold))
        main_layout.addWidget(sync_group)
        
        sync_layout = QHBoxLayout(sync_group)
        
        # 增量同步按钮
        self.incremental_sync_btn = QPushButton("增量同步")
        self.incremental_sync_btn.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.incremental_sync_btn.clicked.connect(self._start_incremental_sync)
        sync_layout.addWidget(self.incremental_sync_btn)
        
        # 完整同步按钮
        self.full_sync_btn = QPushButton("完整同步")
        self.full_sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.full_sync_btn.clicked.connect(self._start_full_sync)
        sync_layout.addWidget(self.full_sync_btn)
        
        # 停止同步按钮
        self.stop_sync_btn = QPushButton("停止同步")
        self.stop_sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.stop_sync_btn.clicked.connect(self._stop_sync)
        self.stop_sync_btn.setEnabled(False)
        sync_layout.addWidget(self.stop_sync_btn)
    
    def _create_progress_section(self, main_layout):
        """创建进度显示区域"""
        progress_group = QGroupBox("同步进度")
        progress_group.setFont(QFont("", 10, QFont.Bold))
        main_layout.addWidget(progress_group)
        
        progress_layout = QVBoxLayout(progress_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        # 进度文本
        self.progress_label = QLabel("就绪")
        self.progress_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.progress_label)
    
    def _create_log_section(self, main_layout):
        """创建日志显示区域"""
        log_group = QGroupBox("同步日志")
        log_group.setFont(QFont("", 10, QFont.Bold))
        main_layout.addWidget(log_group)
        
        log_layout = QVBoxLayout(log_group)
        
        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                font-family: 'Courier New', monospace;
                font-size: 9pt;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        # 清除日志按钮
        clear_log_btn = QPushButton("清除日志")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_log_btn)
    
    def _create_button_section(self, main_layout):
        """创建底部按钮区域"""
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)
        
        button_layout.addStretch()
        
        # 刷新状态按钮
        refresh_btn = QPushButton("刷新状态")
        refresh_btn.clicked.connect(self._load_sync_status)
        button_layout.addWidget(refresh_btn)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

    def _init_timer(self):
        """初始化定时器"""
        # 状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(5000)  # 每5秒更新一次状态

    def _load_sync_status(self):
        """加载同步状态"""
        try:
            if self.sync_manager:
                # 获取设备ID
                device_id = self.sync_manager.device_id
                if device_id:
                    self.device_id_label.setText(f"{device_id[:16]}...")

                # 获取同步状态
                status = self.sync_manager.get_sync_status()

                # 更新配置显示
                config = status.get('sync_config', {})
                self.server_url_input.setText(config.get('server_url', ''))
                self.sync_interval_input.setValue(config.get('sync_interval', 300) // 60)
                self.auto_sync_checkbox.setChecked(config.get('enabled', False))
                self.incremental_sync_checkbox.setChecked(config.get('incremental_sync', True))

                # 更新同步统计
                sync_status = status.get('sync_status', {})
                self.synced_count_label.setText(str(sync_status.get('total_synced', 0)))
                self.failed_count_label.setText(str(sync_status.get('failed_count', 0)))

                # 更新上次同步时间
                last_sync = sync_status.get('last_sync')
                if last_sync:
                    try:
                        last_sync_time = datetime.fromisoformat(last_sync)
                        self.last_sync_label.setText(last_sync_time.strftime('%Y-%m-%d %H:%M:%S'))
                    except:
                        self.last_sync_label.setText(last_sync)
                else:
                    self.last_sync_label.setText("从未同步")

                # 更新服务器状态
                if status.get('is_running'):
                    self.server_status_label.setText("✅ 同步服务运行中")
                    self.server_status_label.setStyleSheet("color: #27ae60;")
                else:
                    self.server_status_label.setText("❌ 同步服务已停止")
                    self.server_status_label.setStyleSheet("color: #e74c3c;")

                self._add_log("状态更新完成")
            else:
                self.device_id_label.setText("同步管理器未初始化")
                self.server_status_label.setText("❌ 未初始化")
                self.server_status_label.setStyleSheet("color: #e74c3c;")

        except Exception as e:
            logger.error(f"加载同步状态失败: {e}")
            self._add_log(f"加载状态失败: {e}")

    def _update_status(self):
        """定时更新状态"""
        if not self.isVisible():
            return

        try:
            if self.sync_manager:
                status = self.sync_manager.get_sync_status()
                sync_status = status.get('sync_status', {})

                # 更新统计数据
                self.synced_count_label.setText(str(sync_status.get('total_synced', 0)))
                self.failed_count_label.setText(str(sync_status.get('failed_count', 0)))

                # 检查最后错误
                last_error = sync_status.get('last_error')
                if last_error and hasattr(self, '_last_error') and self._last_error != last_error:
                    self._add_log(f"错误: {last_error}")
                    self._last_error = last_error

        except Exception as e:
            logger.debug(f"更新状态异常: {e}")

    def _start_incremental_sync(self):
        """开始增量同步"""
        if not self.sync_manager:
            QMessageBox.warning(self, "警告", "同步管理器未初始化")
            return

        self._start_sync('incremental')

    def _start_full_sync(self):
        """开始完整同步"""
        if not self.sync_manager:
            QMessageBox.warning(self, "警告", "同步管理器未初始化")
            return

        reply = QMessageBox.question(
            self, "确认",
            "完整同步将上传所有数据，可能需要较长时间。\n确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._start_sync('full')

    def _start_sync(self, sync_type):
        """开始同步"""
        try:
            if self.sync_worker and self.sync_worker.is_running:
                QMessageBox.warning(self, "警告", "同步正在进行中，请等待完成")
                return

            # 创建同步工作线程
            self.sync_worker = SyncWorkerThread(self.sync_manager, sync_type)
            self.sync_worker.progress_updated.connect(self._on_progress_updated)
            self.sync_worker.sync_completed.connect(self._on_sync_completed)
            self.sync_worker.error_occurred.connect(self._on_sync_error)

            # 更新UI状态
            self.incremental_sync_btn.setEnabled(False)
            self.full_sync_btn.setEnabled(False)
            self.stop_sync_btn.setEnabled(True)

            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 不确定进度

            # 启动同步
            self.sync_worker.start()

            sync_type_text = "完整同步" if sync_type == 'full' else "增量同步"
            self._add_log(f"开始{sync_type_text}...")

        except Exception as e:
            logger.error(f"启动同步失败: {e}")
            self._add_log(f"启动同步失败: {e}")
            self._reset_sync_ui()

    def _stop_sync(self):
        """停止同步"""
        try:
            if self.sync_worker and self.sync_worker.is_running:
                self.sync_worker.stop()
                self._add_log("正在停止同步...")

            self._reset_sync_ui()

        except Exception as e:
            logger.error(f"停止同步失败: {e}")
            self._add_log(f"停止同步失败: {e}")

    def _reset_sync_ui(self):
        """重置同步UI状态"""
        self.incremental_sync_btn.setEnabled(True)
        self.full_sync_btn.setEnabled(True)
        self.stop_sync_btn.setEnabled(False)

        self.progress_bar.setVisible(False)
        self.progress_label.setText("就绪")

    def _on_progress_updated(self, message):
        """处理进度更新"""
        self.progress_label.setText(message)
        self._add_log(message)

    def _on_sync_completed(self, result):
        """处理同步完成"""
        try:
            success = result.get('success', False)
            synced_count = result.get('synced_count', 0)
            failed_count = result.get('failed_count', 0)
            errors = result.get('errors', [])

            if success:
                self._add_log(f"✅ 同步成功完成！同步了 {synced_count} 条记录")
                QMessageBox.information(self, "同步完成", f"同步成功完成！\n同步记录: {synced_count} 条")
            else:
                error_text = "\n".join(errors[:3])  # 只显示前3个错误
                self._add_log(f"❌ 同步部分失败：成功 {synced_count}，失败 {failed_count}")
                QMessageBox.warning(
                    self, "同步完成",
                    f"同步部分失败！\n成功: {synced_count} 条\n失败: {failed_count} 条\n\n错误信息:\n{error_text}"
                )

            # 刷新状态
            self._load_sync_status()

        except Exception as e:
            logger.error(f"处理同步完成事件失败: {e}")
            self._add_log(f"处理同步结果失败: {e}")
        finally:
            self._reset_sync_ui()

    def _on_sync_error(self, error_message):
        """处理同步错误"""
        self._add_log(f"❌ 同步异常: {error_message}")
        QMessageBox.critical(self, "同步错误", f"同步过程中发生错误:\n{error_message}")
        self._reset_sync_ui()

    def _add_log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        self.log_text.append(log_message)

        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        """关闭事件处理"""
        try:
            # 停止定时器
            if hasattr(self, 'status_timer'):
                self.status_timer.stop()

            # 停止同步线程
            if self.sync_worker and self.sync_worker.is_running:
                self.sync_worker.stop()
                self.sync_worker.wait(3000)  # 等待3秒

            event.accept()

        except Exception as e:
            logger.error(f"关闭对话框异常: {e}")
            event.accept()
