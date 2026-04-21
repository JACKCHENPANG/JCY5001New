# -*- coding: utf-8 -*-
"""
监控窗口
实时显示测试过程监控信息和异常日志

Author: Jack
Date: 2025-01-27
"""

import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTextEdit, QLabel, QPushButton, QGroupBox, QGridLayout,
    QProgressBar, QTableWidget, QTableWidgetItem,
    QSplitter
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QFont

from utils.exception_monitor import get_global_monitor
from utils.test_monitor import get_global_test_monitor
import logging

logger = logging.getLogger(__name__)


class MonitorWindow(QMainWindow):
    """监控窗口类"""

    def __init__(self, parent=None):
        """初始化监控窗口"""
        super().__init__(parent)

        self.exception_monitor = get_global_monitor()
        self.test_monitor = get_global_test_monitor()

        self._init_ui()
        self._init_connections()
        self._init_timers()

        logger.debug("监控窗口初始化完成")

    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("JCY5001A测试过程监控器")
        self.setMinimumSize(1000, 700)

        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 创建顶部控制栏
        control_bar = self._create_control_bar()
        main_layout.addWidget(control_bar)

        # 创建选项卡窗口
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # 测试状态选项卡
        test_status_tab = self._create_test_status_tab()
        tab_widget.addTab(test_status_tab, "测试状态")

        # 异常监控选项卡
        exception_tab = self._create_exception_tab()
        tab_widget.addTab(exception_tab, "异常监控")

        # 性能监控选项卡
        performance_tab = self._create_performance_tab()
        tab_widget.addTab(performance_tab, "性能监控")

        # 日志查看选项卡
        log_tab = self._create_log_tab()
        tab_widget.addTab(log_tab, "详细日志")

    def _create_control_bar(self) -> QWidget:
        """创建控制栏"""
        control_widget = QWidget()
        layout = QHBoxLayout(control_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 监控状态标签
        self.status_label = QLabel("监控状态: 未启动")
        self.status_label.setFont(QFont("", 10, QFont.Bold))
        layout.addWidget(self.status_label)

        layout.addStretch()

        # 控制按钮
        self.start_btn = QPushButton("启动监控")
        self.start_btn.clicked.connect(self._start_monitoring)
        layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止监控")
        self.stop_btn.clicked.connect(self._stop_monitoring)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        self.clear_btn = QPushButton("清空日志")
        self.clear_btn.clicked.connect(self._clear_logs)
        layout.addWidget(self.clear_btn)

        return control_widget



    def _create_test_status_tab(self) -> QWidget:
        """创建测试状态选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # 左侧：通道状态
        channels_group = QGroupBox("通道状态")
        channels_layout = QVBoxLayout(channels_group)

        # 通道状态表格
        self.channels_table = QTableWidget(8, 6)
        self.channels_table.setHorizontalHeaderLabels([
            "通道", "状态", "电池码", "当前频率", "进度", "错误数"
        ])
        self.channels_table.horizontalHeader().setStretchLastSection(True)
        channels_layout.addWidget(self.channels_table)

        splitter.addWidget(channels_group)

        # 右侧：测试步骤
        steps_group = QGroupBox("测试步骤")
        steps_layout = QVBoxLayout(steps_group)

        # 当前步骤
        current_steps_label = QLabel("当前执行步骤:")
        current_steps_label.setFont(QFont("", 9, QFont.Bold))
        steps_layout.addWidget(current_steps_label)

        self.current_steps_text = QTextEdit()
        self.current_steps_text.setMaximumHeight(150)
        self.current_steps_text.setFont(QFont("Consolas", 9))
        steps_layout.addWidget(self.current_steps_text)

        # 已完成步骤
        completed_steps_label = QLabel("已完成步骤:")
        completed_steps_label.setFont(QFont("", 9, QFont.Bold))
        steps_layout.addWidget(completed_steps_label)

        self.completed_steps_text = QTextEdit()
        self.completed_steps_text.setFont(QFont("Consolas", 9))
        steps_layout.addWidget(self.completed_steps_text)

        splitter.addWidget(steps_group)

        # 设置分割器比例
        splitter.setSizes([400, 600])

        return widget

    def _create_exception_tab(self) -> QWidget:
        """创建异常监控选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 异常统计
        stats_group = QGroupBox("异常统计")
        stats_layout = QGridLayout(stats_group)

        self.exception_count_label = QLabel("异常总数: 0")
        stats_layout.addWidget(self.exception_count_label, 0, 0)

        self.last_exception_label = QLabel("最后异常: 无")
        stats_layout.addWidget(self.last_exception_label, 0, 1)

        layout.addWidget(stats_group)

        # 异常日志
        log_group = QGroupBox("异常日志")
        log_layout = QVBoxLayout(log_group)

        self.exception_log = QTextEdit()
        self.exception_log.setFont(QFont("Consolas", 9))
        self.exception_log.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555;
            }
        """)
        log_layout.addWidget(self.exception_log)

        layout.addWidget(log_group)

        return widget

    def _create_performance_tab(self) -> QWidget:
        """创建性能监控选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 性能指标
        metrics_group = QGroupBox("性能指标")
        metrics_layout = QGridLayout(metrics_group)

        # 测试时长
        self.test_duration_label = QLabel("测试时长: 0s")
        metrics_layout.addWidget(self.test_duration_label, 0, 0)

        # 活跃通道数
        self.active_channels_label = QLabel("活跃通道: 0")
        metrics_layout.addWidget(self.active_channels_label, 0, 1)

        # 频点进度
        self.frequency_progress_label = QLabel("频点进度: 0/0")
        metrics_layout.addWidget(self.frequency_progress_label, 1, 0)

        # 平均频点时间
        self.avg_frequency_time_label = QLabel("平均频点时间: 0s")
        metrics_layout.addWidget(self.avg_frequency_time_label, 1, 1)

        # 错误计数
        self.error_count_label = QLabel("错误计数: 0")
        metrics_layout.addWidget(self.error_count_label, 2, 0)

        layout.addWidget(metrics_group)

        # 进度条
        progress_group = QGroupBox("整体进度")
        progress_layout = QVBoxLayout(progress_group)

        self.overall_progress = QProgressBar()
        self.overall_progress.setTextVisible(True)
        progress_layout.addWidget(self.overall_progress)

        layout.addWidget(progress_group)

        # 添加弹性空间
        layout.addStretch()

        return widget

    def _create_log_tab(self) -> QWidget:
        """创建日志查看选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 日志控制
        log_control = QHBoxLayout()

        self.auto_scroll_btn = QPushButton("自动滚动: 开")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.auto_scroll_btn.clicked.connect(self._toggle_auto_scroll)
        log_control.addWidget(self.auto_scroll_btn)

        log_control.addStretch()

        self.save_log_btn = QPushButton("保存日志")
        self.save_log_btn.clicked.connect(self._save_logs)
        log_control.addWidget(self.save_log_btn)

        layout.addLayout(log_control)

        # 详细日志显示
        self.detailed_log = QTextEdit()
        self.detailed_log.setFont(QFont("Consolas", 8))
        self.detailed_log.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                color: #333;
                border: 1px solid #ddd;
            }
        """)
        layout.addWidget(self.detailed_log)

        return widget

    def _init_connections(self):
        """初始化信号连接"""
        # 异常监控信号
        self.exception_monitor.exception_occurred.connect(self._on_exception_occurred)
        self.exception_monitor.critical_error.connect(self._on_critical_error)

        # 测试监控信号
        self.test_monitor.step_started.connect(self._on_step_started)
        self.test_monitor.step_completed.connect(self._on_step_completed)
        self.test_monitor.step_failed.connect(self._on_step_failed)
        self.test_monitor.frequency_progress.connect(self._on_frequency_progress)
        self.test_monitor.channel_status_changed.connect(self._on_channel_status_changed)
        self.test_monitor.performance_update.connect(self._on_performance_update)

    def _init_timers(self):
        """初始化定时器"""
        # 状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)  # 每秒更新

    def _start_monitoring(self):
        """启动监控"""
        try:
            self.exception_monitor.start_monitoring()
            self.test_monitor.start_monitoring()

            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.status_label.setText("监控状态: 运行中")
            self.status_label.setStyleSheet("color: green;")

            self._log_message("监控已启动")

        except Exception as e:
            logger.error(f"启动监控失败: {e}")

    def _stop_monitoring(self):
        """停止监控"""
        try:
            self.exception_monitor.stop_monitoring()
            self.test_monitor.stop_monitoring()

            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_label.setText("监控状态: 已停止")
            self.status_label.setStyleSheet("color: red;")

            self._log_message("监控已停止")

        except Exception as e:
            logger.error(f"停止监控失败: {e}")

    def _clear_logs(self):
        """清空日志"""
        self.exception_log.clear()
        self.current_steps_text.clear()
        self.completed_steps_text.clear()
        self.detailed_log.clear()
        self._log_message("日志已清空")

    def _toggle_auto_scroll(self):
        """切换自动滚动"""
        if self.auto_scroll_btn.isChecked():
            self.auto_scroll_btn.setText("自动滚动: 开")
        else:
            self.auto_scroll_btn.setText("自动滚动: 关")

    def _save_logs(self):
        """保存日志"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = f"logs/monitor_log_{timestamp}.txt"

            os.makedirs("logs", exist_ok=True)

            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("=== JCY5001A测试监控日志 ===\n")
                f.write(f"生成时间: {datetime.now()}\n\n")
                f.write("=== 详细日志 ===\n")
                f.write(self.detailed_log.toPlainText())
                f.write("\n\n=== 异常日志 ===\n")
                f.write(self.exception_log.toPlainText())

            self._log_message(f"日志已保存到: {log_file}")

        except Exception as e:
            logger.error(f"保存日志失败: {e}")

    @pyqtSlot(str, str, str)
    def _on_exception_occurred(self, exc_type: str, exc_message: str, stack_trace: str):
        """处理异常发生事件"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        message = f"[{timestamp}] {exc_type}: {exc_message}\n"

        self.exception_log.append(message)
        self._log_message(f"异常: {exc_type} - {exc_message}")

        if self.auto_scroll_btn.isChecked():
            self.exception_log.moveCursor(self.exception_log.textCursor().End)

    @pyqtSlot(str)
    def _on_critical_error(self, error_message: str):
        """处理严重错误事件"""
        self._log_message(f"严重错误: {error_message}", "ERROR")

    @pyqtSlot(str, str)
    def _on_step_started(self, step_name: str, details: str):
        """处理步骤开始事件"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        message = f"[{timestamp}] 开始: {step_name} - {details}\n"
        self.current_steps_text.append(message)
        self._log_message(f"步骤开始: {step_name}")

    @pyqtSlot(str, float, str)
    def _on_step_completed(self, step_name: str, duration: float, status: str):
        """处理步骤完成事件"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        message = f"[{timestamp}] 完成: {step_name} (耗时: {duration:.2f}s)\n"
        self.completed_steps_text.append(message)
        self._log_message(f"步骤完成: {step_name} ({duration:.2f}s)")

    @pyqtSlot(str, str)
    def _on_step_failed(self, step_name: str, error_message: str):
        """处理步骤失败事件"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        message = f"[{timestamp}] 失败: {step_name} - {error_message}\n"
        self.completed_steps_text.append(message)
        self._log_message(f"步骤失败: {step_name} - {error_message}", "ERROR")

    @pyqtSlot(int, float, int, int)
    def _on_frequency_progress(self, channel_num: int, frequency: float,
                             current_index: int, total_count: int):
        """处理频点进度事件"""
        self._log_message(f"通道{channel_num}: {frequency}Hz ({current_index}/{total_count})")

    @pyqtSlot(int, str, dict)
    def _on_channel_status_changed(self, channel_num: int, state: str, details: dict):
        """处理通道状态变更事件"""
        self._log_message(f"通道{channel_num}状态: {state}")

    @pyqtSlot(dict)
    def _on_performance_update(self, performance_data: dict):
        """处理性能更新事件"""
        # 更新性能指标显示
        duration = performance_data.get('test_duration', 0)
        self.test_duration_label.setText(f"测试时长: {duration:.1f}s")

        active = performance_data.get('active_channels', 0)
        self.active_channels_label.setText(f"活跃通道: {active}")

        completed = performance_data.get('completed_frequencies', 0)
        total = performance_data.get('total_frequencies', 0)
        self.frequency_progress_label.setText(f"频点进度: {completed}/{total}")

        avg_time = performance_data.get('average_frequency_time', 0)
        self.avg_frequency_time_label.setText(f"平均频点时间: {avg_time:.2f}s")

        errors = performance_data.get('error_count', 0)
        self.error_count_label.setText(f"错误计数: {errors}")

        # 更新进度条
        if total > 0:
            progress = int((completed / total) * 100)
            self.overall_progress.setValue(progress)

    def _update_status(self):
        """更新状态显示"""
        try:
            # 更新异常统计
            stats = self.exception_monitor.get_statistics()
            self.exception_count_label.setText(f"异常总数: {stats.get('exception_count', 0)}")

            last_time = stats.get('last_exception_time')
            if last_time:
                time_str = last_time.strftime('%H:%M:%S')
                self.last_exception_label.setText(f"最后异常: {time_str}")

            # 更新通道状态表格
            test_status = self.test_monitor.get_status_summary()
            channel_status = test_status.get('channel_status', {})

            for i, (channel_num, status) in enumerate(channel_status.items()):
                if i < self.channels_table.rowCount():
                    self.channels_table.setItem(i, 0, QTableWidgetItem(str(channel_num)))
                    self.channels_table.setItem(i, 1, QTableWidgetItem(status.get('state', 'idle')))
                    self.channels_table.setItem(i, 2, QTableWidgetItem(''))  # 电池码
                    self.channels_table.setItem(i, 3, QTableWidgetItem(f"{status.get('current_frequency', 0):.1f}Hz"))
                    self.channels_table.setItem(i, 4, QTableWidgetItem(f"{status.get('progress', 0)}%"))
                    self.channels_table.setItem(i, 5, QTableWidgetItem(str(status.get('error_count', 0))))

        except Exception as e:
            logger.error(f"更新状态显示失败: {e}")

    def _log_message(self, message: str, level: str = "INFO"):
        """记录日志消息"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        self.detailed_log.append(log_entry)

        if self.auto_scroll_btn.isChecked():
            self.detailed_log.moveCursor(self.detailed_log.textCursor().End)
