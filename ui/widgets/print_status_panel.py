# -*- coding: utf-8 -*-
"""
打印状态面板 PrintStatusPanel
显示并调试打印相关状态：
- 打印机名称与连接状态
- 自动打印开关
- 打印队列长度
- 最近一次任务摘要

增量组件，避免主窗口成为上帝类，单一职责：仅负责展示与轮询。
"""
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt, QTimer

import logging
logger = logging.getLogger(__name__)


class PrintStatusPanel(QWidget):
    """打印状态面板（轻量版）"""

    def __init__(self, main_window, parent: Optional[QWidget] = None):  # type: ignore[name-defined]
        super().__init__(parent)
        self.main_window = main_window

        self._init_ui()
        self._init_timer()

    def _init_ui(self):
        self.setObjectName("PrintStatusPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 标题
        title = QLabel("🖨️ 打印状态")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setStyleSheet("font-weight:bold; color:#2E8B57;")
        layout.addWidget(title)

        # 行1：自动打印状态（移除打印机信息）
        row1 = QHBoxLayout()
        self.lbl_auto = QLabel("--")
        row1.addWidget(QLabel("自动打印:"))
        row1.addWidget(self.lbl_auto)
        layout.addLayout(row1)

        # 行2：队列长度
        row2 = QHBoxLayout()
        self.lbl_queue = QLabel("0")
        row2.addWidget(QLabel("队列:"))
        row2.addWidget(self.lbl_queue)
        layout.addLayout(row2)

        # 行3：最近任务摘要
        row3 = QVBoxLayout()
        self.lbl_last = QLabel("最近任务: 无")
        self.lbl_last.setWordWrap(True)
        self.lbl_last.setStyleSheet("color:#555;")
        row3.addWidget(self.lbl_last)
        layout.addLayout(row3)

        # 行4：手动刷新
        btn_row = QHBoxLayout()
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self.refresh_once)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_refresh)
        layout.addLayout(btn_row)

        # 边框
        self.setFrameStyle()

    def setFrameStyle(self):
        self.setStyleSheet(
            "#PrintStatusPanel{border:1px solid #ddd; border-radius:6px; background:#fafafa;}"
        )

    def _init_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_once)
        self._timer.start(1000)  # 每秒刷新一次

    def _get_managers(self):
        printer_manager = getattr(self.main_window, 'printer_manager', None)
        label_print_manager = getattr(self.main_window, 'label_print_manager', None)
        return printer_manager, label_print_manager

    def refresh_once(self):
        try:
            printer_manager, label_print_manager = self._get_managers()

            # 简化状态获取（移除打印机信息）
            auto_print = None
            queue_len = None
            last_summary = None

            if hasattr(self.main_window, 'config_manager') and self.main_window.config_manager:
                auto_print = bool(self.main_window.config_manager.get('label.auto_print', False))

            if label_print_manager:
                try:
                    queue_len = int(label_print_manager.get_queue_size())
                except Exception:
                    queue_len = None
                # 最近任务：尝试从当前任务或队列头拼接信息
                try:
                    job = getattr(label_print_manager, 'current_job', None)
                    if job:
                        tr = job.test_result or {}
                        last_summary = f"{job.job_id} CH={tr.get('channel_number','?')} V={tr.get('voltage',0):.3f} Rs={tr.get('rs_value',0):.3f} Rct={tr.get('rct_value',0):.3f}"
                except Exception:
                    pass

            # 更新UI（移除打印机状态显示）
            self.lbl_auto.setText("开启" if auto_print else "关闭")
            self.lbl_queue.setText(str(queue_len if queue_len is not None else "-"))
            self.lbl_last.setText(last_summary or "最近任务: 无")

        except Exception as e:
            logger.error(f"刷新打印状态面板失败: {e}")

