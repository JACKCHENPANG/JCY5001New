"""
电池侦测模式启动引导对话框

功能：
1. 提示用户放入电池
2. 显示使能的通道数量和有效的通道
3. 当使能通道和有效通道一样后就开始启动
4. 如果开启了扫描枪功能，显示表格形式的扫码界面
5. 每个扫码完后跳到下一个通道，直到全部有效通道都输入了才开始启动
"""

import logging
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QProgressBar, QGroupBox, QLineEdit, QFrame,
                             QHeaderView, QMessageBox, QTextEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPalette, QColor
from utils.input_method_manager import InputMethodManager
from utils.serial_number_manager import SerialNumberManager

logger = logging.getLogger(__name__)

class BatteryDetectionGuideDialog(QDialog):
    """电池侦测模式启动引导对话框"""
    
    # 信号定义
    start_test_requested = pyqtSignal()  # 请求启动测试
    dialog_cancelled = pyqtSignal()      # 对话框被取消
    
    def __init__(self, parent=None, config_manager=None, battery_detection_manager=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.battery_detection_manager = battery_detection_manager
        
        # 状态变量
        self.enabled_channels = []
        self.connected_channels = set()
        self.barcode_scanner_enabled = False
        self.channel_barcodes = {}  # 存储每个通道的条码
        self.current_scan_channel = None  # 当前扫码的通道
        self.all_barcodes_entered = False
        self._auto_start_triggered = False  # 防止重复触发自动启动
        self._last_input_time = {}  # 记录每个通道的最后输入时间，用于检测扫码枪输入

        # 定时器用于更新电池状态
        self.status_update_timer = QTimer()
        self.status_update_timer.timeout.connect(self.update_battery_status)

        # 初始化输入法管理器
        self.input_method_manager = InputMethodManager(self)

        # 初始化序列号管理器（用于电池码唯一性检测）
        self.serial_manager = SerialNumberManager(self.config_manager)

        self.init_ui()
        self.load_config()
        self.setup_connections()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("电池侦测模式 - 启动引导")
        self.setModal(True)
        # 初始设置基础尺寸，后续会根据扫码枪状态动态调整
        self.setFixedSize(600, 500)
        
        # 主布局
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 标题
        title_label = QLabel("🔋 电池侦测模式启动引导")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background-color: #ecf0f1;
                border-radius: 5px;
                margin-bottom: 10px;
            }
        """)
        main_layout.addWidget(title_label)
        
        # 状态信息组
        self.create_status_group(main_layout)
        
        # 扫码组（如果启用）
        self.barcode_group = QGroupBox("📱 扫码输入")
        self.barcode_group.setVisible(False)  # 默认隐藏
        self.create_barcode_group()
        main_layout.addWidget(self.barcode_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("等待电池插入... (%p%)")
        main_layout.addWidget(self.progress_bar)
        
        # 按钮组
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("🚀 开始测试")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.on_start_test)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            QPushButton:hover:enabled {
                background-color: #2ecc71;
            }
        """)
        
        self.cancel_button = QPushButton("❌ 取消")
        self.cancel_button.clicked.connect(self.on_cancel)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)
        
    def create_status_group(self, parent_layout):
        """创建状态信息组"""
        status_group = QGroupBox("📊 通道状态")
        status_layout = QVBoxLayout()
        status_group.setLayout(status_layout)
        
        # 通道信息
        info_layout = QHBoxLayout()
        
        self.enabled_channels_label = QLabel("使能通道: 0")
        self.enabled_channels_label.setStyleSheet("font-weight: bold; color: #3498db;")
        
        self.connected_channels_label = QLabel("已连接: 0")
        self.connected_channels_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        
        info_layout.addWidget(self.enabled_channels_label)
        info_layout.addWidget(self.connected_channels_label)
        info_layout.addStretch()
        
        status_layout.addLayout(info_layout)
        
        # 详细状态显示
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 3px;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        status_layout.addWidget(self.status_text)
        
        parent_layout.addWidget(status_group)
        
    def create_barcode_group(self):
        """创建扫码组"""
        layout = QVBoxLayout()
        self.barcode_group.setLayout(layout)
        
        # 说明文字
        instruction_label = QLabel("请为每个通道扫描或输入电池条码：")
        instruction_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(instruction_label)
        
        # 扫码表格
        self.barcode_table = QTableWidget()
        self.barcode_table.setColumnCount(3)
        self.barcode_table.setHorizontalHeaderLabels(["通道", "电池条码", "状态"])
        
        # 设置表格样式
        header = self.barcode_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        
        self.barcode_table.setColumnWidth(0, 60)
        self.barcode_table.setColumnWidth(2, 80)
        
        layout.addWidget(self.barcode_table)
        
    def load_config(self):
        """加载配置"""
        try:
            # 获取使能通道
            self.enabled_channels = self.config_manager.get('test.enabled_channels', list(range(1, 9)))
            logger.info(f"使能通道: {self.enabled_channels}")

            # 检查扫码枪是否启用
            self.barcode_scanner_enabled = self.config_manager.get('device.barcode_scanner.enabled', False)
            logger.info(f"扫码枪启用状态: {self.barcode_scanner_enabled}")

            # 更新UI
            self.update_enabled_channels_display()

            if self.barcode_scanner_enabled:
                self.setup_barcode_table()
                self.barcode_group.setVisible(True)
                # 🔧 动态调整界面高度以适应扫码表格
                self._adjust_dialog_size_for_barcode_table()
            else:
                self.barcode_group.setVisible(False)
                # 🔧 恢复基础高度
                self.setFixedSize(600, 500)

        except Exception as e:
            logger.error(f"加载配置失败: {e}")

    def _adjust_dialog_size_for_barcode_table(self):
        """根据扫码表格动态调整对话框大小"""
        try:
            # 基础高度
            base_height = 500

            # 计算扫码表格需要的额外高度
            # 每行大约需要30px，加上表头、说明文字、边距等
            channel_count = len(self.enabled_channels)
            table_header_height = 30  # 表头高度
            row_height = 30  # 每行高度
            instruction_height = 25  # 说明文字高度
            margins_and_spacing = 40  # 边距和间距

            # 计算扫码组需要的总高度
            barcode_group_height = (
                instruction_height +
                table_header_height +
                (row_height * channel_count) +
                margins_and_spacing
            )

            # 计算新的对话框高度
            # 如果通道数量较多，需要更多高度
            if channel_count <= 4:
                # 4个通道以下，适度增加高度
                new_height = base_height + barcode_group_height
            elif channel_count <= 6:
                # 5-6个通道，增加更多高度
                new_height = base_height + barcode_group_height + 50
            else:
                # 7-8个通道，需要最大高度
                new_height = base_height + barcode_group_height + 100

            # 限制最大高度，避免超出屏幕
            max_height = 800
            new_height = min(new_height, max_height)

            logger.info(f"🔧 扫码模式：调整对话框高度 {base_height} -> {new_height} (通道数: {channel_count})")

            # 应用新尺寸
            self.setFixedSize(600, new_height)

        except Exception as e:
            logger.error(f"调整对话框大小失败: {e}")

    def setup_barcode_table(self):
        """设置扫码表格"""
        try:
            self.barcode_table.setRowCount(len(self.enabled_channels))
            
            for i, channel in enumerate(self.enabled_channels):
                # 通道号
                channel_item = QTableWidgetItem(f"通道{channel}")
                channel_item.setFlags(Qt.ItemIsEnabled)
                channel_item.setTextAlignment(Qt.AlignCenter)
                self.barcode_table.setItem(i, 0, channel_item)
                
                # 条码输入框
                barcode_edit = QLineEdit()
                barcode_edit.setPlaceholderText("扫描或输入条码...")
                barcode_edit.textChanged.connect(lambda text, ch=channel: self.on_barcode_changed(ch, text))
                barcode_edit.returnPressed.connect(lambda ch=channel: self.on_barcode_entered(ch))
                self.barcode_table.setCellWidget(i, 1, barcode_edit)
                
                # 状态
                status_item = QTableWidgetItem("等待")
                status_item.setFlags(Qt.ItemIsEnabled)
                status_item.setTextAlignment(Qt.AlignCenter)
                status_item.setBackground(QColor("#f39c12"))
                self.barcode_table.setItem(i, 2, status_item)
                
                # 初始化条码字典
                self.channel_barcodes[channel] = ""
                
            # 设置第一个通道为当前扫码通道
            if self.enabled_channels:
                self.current_scan_channel = self.enabled_channels[0]
                self.highlight_current_scan_channel()
                # 🔧 自动聚焦到第一个通道的输入框（延迟执行，确保界面完全加载）
                QTimer.singleShot(100, self._focus_first_input)
                
        except Exception as e:
            logger.error(f"设置扫码表格失败: {e}")

    def _focus_first_input(self):
        """自动聚焦到第一个通道的输入框"""
        try:
            if self.enabled_channels and self.barcode_scanner_enabled:
                # 🔤 自动切换输入法到英文，防止中文输入法干扰扫码
                logger.info("🔤 电池侦测模式开始扫码，自动切换输入法")
                if self.input_method_manager.auto_switch_for_scanning():
                    logger.info("🔤 电池侦测模式输入法切换成功")
                else:
                    logger.warning("🔤 电池侦测模式输入法切换失败，但继续扫码")

                # 获取第一个通道的输入框
                first_channel = self.enabled_channels[0]
                for i, channel in enumerate(self.enabled_channels):
                    if channel == first_channel:
                        barcode_edit = self.barcode_table.cellWidget(i, 1)
                        if barcode_edit:
                            barcode_edit.setFocus()
                            logger.info(f"✅ 自动聚焦到通道{first_channel}的输入框")
                        break
        except Exception as e:
            logger.error(f"自动聚焦到第一个输入框失败: {e}")

    def setup_connections(self):
        """设置信号连接"""
        try:
            # 不在这里启动定时器，等对话框显示后再启动
            pass

        except Exception as e:
            logger.error(f"设置信号连接失败: {e}")

    def showEvent(self, event):
        """对话框显示事件"""
        super().showEvent(event)
        try:
            # 对话框显示后，延迟启动状态检测
            logger.info("🔋 电池侦测引导对话框已显示，准备启动状态检测")

            # 🔧 如果启用了扫码枪，自动聚焦到第一个输入框
            if self.barcode_scanner_enabled:
                # 延迟500ms聚焦，确保对话框完全显示
                QTimer.singleShot(500, self._focus_first_input)

            # 延迟2秒启动状态检测，给用户时间查看对话框
            QTimer.singleShot(2000, self.start_status_monitoring)

        except Exception as e:
            logger.error(f"对话框显示事件处理失败: {e}")

    def start_status_monitoring(self):
        """开始状态监控"""
        try:
            logger.info("🔋 开始电池状态监控和自动启动检测")

            # 立即更新一次状态
            self.update_battery_status()

            # 启动定时器进行持续监控
            self.status_update_timer.start(1000)  # 每秒更新一次

        except Exception as e:
            logger.error(f"启动状态监控失败: {e}")

    def update_enabled_channels_display(self):
        """更新使能通道显示"""
        self.enabled_channels_label.setText(f"使能通道: {len(self.enabled_channels)} ({', '.join(map(str, self.enabled_channels))})")

    def update_battery_status(self):
        """更新电池状态"""
        try:
            if not self.battery_detection_manager:
                return

            # 获取当前连接的通道
            new_connected_channels = set()
            status_lines = []

            for channel in self.enabled_channels:
                # 获取通道的详细状态信息
                is_connected = self.is_channel_connected(channel)
                voltage_info = self.get_channel_voltage(channel)

                if is_connected:
                    new_connected_channels.add(channel)
                    if voltage_info:
                        status_lines.append(f"通道{channel}: ✅ 已连接 ({voltage_info:.3f}V)")
                    else:
                        status_lines.append(f"通道{channel}: ✅ 已连接")
                else:
                    if voltage_info:
                        status_lines.append(f"通道{channel}: ❌ 未连接 ({voltage_info:.3f}V)")
                    else:
                        status_lines.append(f"通道{channel}: ❌ 未连接")

            # 更新连接状态
            self.connected_channels = new_connected_channels
            self.connected_channels_label.setText(f"已连接: {len(self.connected_channels)} ({', '.join(map(str, sorted(self.connected_channels)))})")

            # 更新状态文本
            self.status_text.setText("\n".join(status_lines))

            # 更新进度条
            total_channels = len(self.enabled_channels)
            connected_count = len(self.connected_channels)

            if total_channels > 0:
                progress = int((connected_count / total_channels) * 100)
                self.progress_bar.setValue(progress)

                if connected_count == total_channels:
                    self.progress_bar.setFormat("所有电池已连接! (%p%)")
                else:
                    self.progress_bar.setFormat(f"电池连接进度: {connected_count}/{total_channels} (%p%)")

            # 检查是否可以启动测试
            self.check_start_conditions()

        except Exception as e:
            logger.error(f"更新电池状态失败: {e}")

    def is_channel_connected(self, channel):
        """检查通道是否连接了电池"""
        try:
            # 尝试从电池检测管理器获取状态
            if self.battery_detection_manager:
                # 方法1：使用get_channel_state方法
                if hasattr(self.battery_detection_manager, 'get_channel_state'):
                    channel_state = self.battery_detection_manager.get_channel_state(channel)
                    if channel_state:
                        battery_state = channel_state.get('battery_state', 'unknown')
                        return battery_state == 'connected'

                # 方法2：直接访问channels属性
                elif hasattr(self.battery_detection_manager, 'channels'):
                    channel_info = self.battery_detection_manager.channels.get(channel)
                    if channel_info:
                        # 检查电池状态
                        if hasattr(channel_info, 'battery_state'):
                            return channel_info.battery_state.value == 'connected'
                        # 备用：检查电压范围
                        elif hasattr(channel_info, 'last_voltage'):
                            voltage = channel_info.last_voltage
                            return 2.5 <= voltage <= 4.0  # 正常电池电压范围

                # 方法3：使用is_battery_connected方法（如果存在）
                elif hasattr(self.battery_detection_manager, 'is_battery_connected'):
                    return self.battery_detection_manager.is_battery_connected(channel)

            # 如果没有电池检测管理器，返回False
            return False

        except Exception as e:
            logger.error(f"检查通道{channel}连接状态失败: {e}")
            return False

    def get_channel_voltage(self, channel):
        """获取通道电压"""
        try:
            if self.battery_detection_manager:
                # 方法1：使用get_channel_state方法
                if hasattr(self.battery_detection_manager, 'get_channel_state'):
                    channel_state = self.battery_detection_manager.get_channel_state(channel)
                    if channel_state:
                        return channel_state.get('last_voltage', None)

                # 方法2：直接访问channels属性
                elif hasattr(self.battery_detection_manager, 'channels'):
                    channel_info = self.battery_detection_manager.channels.get(channel)
                    if channel_info:
                        if hasattr(channel_info, 'last_voltage'):
                            return channel_info.last_voltage
                        elif hasattr(channel_info, 'voltage'):
                            return channel_info.voltage

            return None

        except Exception as e:
            logger.error(f"获取通道{channel}电压失败: {e}")
            return None

    def check_start_conditions(self):
        """检查启动条件"""
        try:
            # 如果已经触发自动启动，不再检查
            if self._auto_start_triggered:
                return

            # 条件1：所有使能通道都连接了电池
            all_batteries_connected = len(self.connected_channels) == len(self.enabled_channels) and len(self.enabled_channels) > 0

            # 条件2：如果启用扫码枪，所有条码都已输入
            all_barcodes_ready = True
            if self.barcode_scanner_enabled:
                all_barcodes_ready = self.all_barcodes_entered

            # 更新开始按钮状态
            can_start = all_batteries_connected and all_barcodes_ready
            self.start_button.setEnabled(can_start)

            if can_start:
                self.start_button.setText("🚀 自动开始测试...")
                self.start_button.setStyleSheet("""
                    QPushButton {
                        background-color: #27ae60;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 5px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #2ecc71;
                    }
                """)

                # 🎯 当条件满足时，自动开始测试（延迟1秒给用户反馈）
                logger.info("🚀 电池侦测模式：所有条件满足，1秒后自动开始测试")
                self._auto_start_triggered = True  # 标记已触发，防止重复
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(1000, self.auto_start_test)

            else:
                reasons = []
                if not all_batteries_connected:
                    missing_count = len(self.enabled_channels) - len(self.connected_channels)
                    reasons.append(f"还需插入{missing_count}个电池")
                if self.barcode_scanner_enabled and not all_barcodes_ready:
                    missing_barcodes = sum(1 for ch in self.enabled_channels if not self.channel_barcodes.get(ch, "").strip())
                    reasons.append(f"还需扫描{missing_barcodes}个条码")

                reason_text = "、".join(reasons)
                self.start_button.setText(f"等待中... ({reason_text})")

        except Exception as e:
            logger.error(f"检查启动条件失败: {e}")

    def auto_start_test(self):
        """自动开始测试"""
        try:
            logger.info("🚀 电池侦测模式：自动开始测试")

            # 更新按钮状态
            self.start_button.setText("✅ 正在启动...")
            self.start_button.setEnabled(False)

            # 调用开始测试方法
            self.on_start_test()

        except Exception as e:
            logger.error(f"自动开始测试失败: {e}")
            # 重置状态
            self._auto_start_triggered = False
            self.start_button.setText("🚀 开始测试")
            self.start_button.setEnabled(True)

    def on_barcode_changed(self, channel, text):
        """条码输入变化"""
        try:
            import time
            current_time = time.time()

            battery_code = text.strip()
            self.channel_barcodes[channel] = battery_code

            # 更新表格状态
            for i, ch in enumerate(self.enabled_channels):
                if ch == channel:
                    status_item = self.barcode_table.item(i, 2)
                    if battery_code:
                        # 🔧 电池码唯一性检测
                        validation_result = self._validate_battery_code_uniqueness(channel, battery_code)
                        if validation_result['is_valid']:
                            status_item.setText("已输入")
                            status_item.setBackground(QColor("#27ae60"))
                        else:
                            status_item.setText("重复码")
                            status_item.setBackground(QColor("#e74c3c"))
                            # 显示重复提示
                            self._show_duplicate_code_warning(channel, battery_code, validation_result['message'])
                    else:
                        status_item.setText("等待")
                        status_item.setBackground(QColor("#f39c12"))
                    break

            # 🔧 扫码枪自动跳转逻辑
            if text.strip() and channel == self.current_scan_channel:
                # 检测是否为扫码枪输入（快速输入完整条码）
                last_time = self._last_input_time.get(channel, 0)
                time_diff = current_time - last_time

                # 如果输入间隔很短且条码长度合理，认为是扫码枪输入
                if time_diff < 0.1 and len(text.strip()) >= 6:  # 扫码枪通常在100ms内完成输入
                    logger.info(f"🔧 检测到扫码枪输入，通道{channel}扫码完成，自动跳转到下一个通道")
                    # 延迟200ms执行跳转，确保当前输入处理完成
                    QTimer.singleShot(200, lambda: self._auto_jump_to_next_channel(channel))
                elif len(text.strip()) >= 10:  # 如果条码长度足够长，也认为是扫码枪输入
                    logger.info(f"🔧 检测到长条码输入，通道{channel}扫码完成，自动跳转到下一个通道")
                    QTimer.singleShot(200, lambda: self._auto_jump_to_next_channel(channel))

            # 记录输入时间
            self._last_input_time[channel] = current_time

            # 检查是否所有条码都已输入
            self.all_barcodes_entered = all(
                self.channel_barcodes.get(ch, "").strip()
                for ch in self.enabled_channels
            )

            # 重新检查启动条件
            self.check_start_conditions()

        except Exception as e:
            logger.error(f"处理条码变化失败: {e}")

    def _validate_battery_code_uniqueness(self, channel: int, battery_code: str) -> dict:
        """
        验证电池码唯一性

        Args:
            channel: 当前通道号
            battery_code: 电池码

        Returns:
            验证结果字典 {'is_valid': bool, 'message': str}
        """
        try:
            if not battery_code or not battery_code.strip():
                return {'is_valid': True, 'message': ''}

            battery_code = battery_code.strip()

            # 检查是否与其他通道的电池码重复
            for ch, code in self.channel_barcodes.items():
                if ch != channel and code.strip() and code.strip().upper() == battery_code.upper():
                    return {
                        'is_valid': False,
                        'message': f'电池码与通道{ch}重复'
                    }

            # 使用序列号管理器进行验证（检查历史记录等）
            if self.serial_manager:
                validation_result = self.serial_manager.validate_serial_number(battery_code)
                if not validation_result.is_valid:
                    if validation_result.error_code == "DUPLICATE_SERIAL":
                        return {
                            'is_valid': False,
                            'message': validation_result.error_message
                        }
                    # 其他验证错误（格式错误等）暂时允许通过，只检查重复性

            return {'is_valid': True, 'message': ''}

        except Exception as e:
            logger.error(f"验证电池码唯一性失败: {e}")
            # 验证失败时默认允许通过，避免阻塞用户操作
            return {'is_valid': True, 'message': ''}

    def _show_duplicate_code_warning(self, channel: int, battery_code: str, message: str):
        """
        显示重复电池码警告

        Args:
            channel: 通道号
            battery_code: 重复的电池码
            message: 错误信息
        """
        try:
            from PyQt5.QtWidgets import QMessageBox

            # 显示警告对话框
            reply = QMessageBox.question(
                self, "电池码重复",
                f"通道 {channel} 检测到重复电池码：\n{message}\n\n电池码: {battery_code}\n\n是否清除当前输入重新扫码？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes  # 默认选择清除重新扫码
            )

            if reply == QMessageBox.Yes:
                # 清除当前输入，让用户重新扫码
                self._clear_channel_barcode(channel)
                logger.info(f"🔧 用户选择清除通道{channel}的重复电池码，重新扫码")
            else:
                # 用户选择保留重复的电池码
                logger.warning(f"⚠️ 用户选择保留通道{channel}的重复电池码: {battery_code}")

        except Exception as e:
            logger.error(f"显示重复电池码警告失败: {e}")

    def _clear_channel_barcode(self, channel: int):
        """
        清除指定通道的电池码

        Args:
            channel: 通道号
        """
        try:
            # 清除内存中的记录
            self.channel_barcodes[channel] = ""

            # 清除界面上的输入框
            for i, ch in enumerate(self.enabled_channels):
                if ch == channel:
                    barcode_edit = self.barcode_table.cellWidget(i, 1)
                    if barcode_edit:
                        # 临时断开信号，避免触发递归
                        barcode_edit.textChanged.disconnect()
                        barcode_edit.clear()
                        # 重新连接信号
                        barcode_edit.textChanged.connect(lambda text, ch=ch: self.on_barcode_changed(ch, text))
                        # 重新聚焦到该输入框
                        barcode_edit.setFocus()

                    # 更新状态显示
                    status_item = self.barcode_table.item(i, 2)
                    if status_item:
                        status_item.setText("等待")
                        status_item.setBackground(QColor("#f39c12"))
                    break

        except Exception as e:
            logger.error(f"清除通道{channel}电池码失败: {e}")

    def _auto_jump_to_next_channel(self, current_channel):
        """自动跳转到下一个通道"""
        try:
            # 找到下一个未输入条码的通道
            current_index = self.enabled_channels.index(current_channel)
            next_channel = None

            for i in range(current_index + 1, len(self.enabled_channels)):
                ch = self.enabled_channels[i]
                if not self.channel_barcodes.get(ch, "").strip():
                    next_channel = ch
                    break

            if next_channel:
                self.current_scan_channel = next_channel
                self.highlight_current_scan_channel()

                # 聚焦到下一个输入框
                for i, ch in enumerate(self.enabled_channels):
                    if ch == next_channel:
                        barcode_edit = self.barcode_table.cellWidget(i, 1)
                        if barcode_edit:
                            barcode_edit.setFocus()
                            logger.info(f"✅ 自动跳转到通道{next_channel}")
                        break
            else:
                # 所有条码都已输入
                logger.info("🎉 所有通道扫码完成，可以开始测试")

        except Exception as e:
            logger.error(f"自动跳转到下一个通道失败: {e}")

    def on_barcode_entered(self, channel):
        """条码输入完成，跳到下一个通道"""
        try:
            if not self.channel_barcodes.get(channel, "").strip():
                return

            # 找到下一个未输入条码的通道
            current_index = self.enabled_channels.index(channel)
            next_channel = None

            for i in range(current_index + 1, len(self.enabled_channels)):
                ch = self.enabled_channels[i]
                if not self.channel_barcodes.get(ch, "").strip():
                    next_channel = ch
                    break

            if next_channel:
                self.current_scan_channel = next_channel
                self.highlight_current_scan_channel()

                # 聚焦到下一个输入框
                for i, ch in enumerate(self.enabled_channels):
                    if ch == next_channel:
                        barcode_edit = self.barcode_table.cellWidget(i, 1)
                        if barcode_edit:
                            barcode_edit.setFocus()
                        break
            else:
                # 所有条码都已输入
                logger.info("所有条码都已输入完成")

        except Exception as e:
            logger.error(f"处理条码输入完成失败: {e}")

    def highlight_current_scan_channel(self):
        """高亮当前扫码通道"""
        try:
            for i, channel in enumerate(self.enabled_channels):
                channel_item = self.barcode_table.item(i, 0)
                if channel == self.current_scan_channel:
                    channel_item.setBackground(QColor("#3498db"))
                    channel_item.setForeground(QColor("white"))
                else:
                    channel_item.setBackground(QColor("white"))
                    channel_item.setForeground(QColor("black"))

        except Exception as e:
            logger.error(f"高亮当前扫码通道失败: {e}")

    def on_start_test(self):
        """开始测试"""
        try:
            logger.info("用户确认开始测试")

            # 如果启用了扫码枪，保存条码信息到全局配置
            if self.barcode_scanner_enabled:
                # 🔧 开始测试前进行最终的唯一性验证
                validation_errors = self._validate_all_battery_codes()
                if validation_errors:
                    # 显示验证错误，阻止开始测试
                    self._show_validation_errors(validation_errors)
                    return

                logger.info(f"🔧 电池侦测模式：保存扫码结果到全局配置: {self.channel_barcodes}")

                # 🔧 将扫码结果保存到配置管理器的临时区域，供测试流程使用
                battery_codes_list = [""] * 8  # 初始化8个通道的电池码列表
                for channel_num, barcode in self.channel_barcodes.items():
                    if 1 <= channel_num <= 8 and barcode.strip():
                        battery_codes_list[channel_num - 1] = barcode.strip()
                        # 注册序列号到序列号管理器
                        if self.serial_manager:
                            self.serial_manager.register_serial_number(barcode.strip())

                # 保存到配置管理器的临时区域
                self.config_manager.set('temp.battery_detection_barcodes', battery_codes_list)
                self.config_manager.set('temp.battery_detection_barcodes_ready', True)
                logger.info(f"✅ 电池侦测模式扫码结果已保存: {battery_codes_list}")

            # 停止状态更新定时器
            self.status_update_timer.stop()

            # 发送开始测试信号
            self.start_test_requested.emit()

            # 关闭对话框
            self.accept()

        except Exception as e:
            logger.error(f"开始测试失败: {e}")
            QMessageBox.critical(self, "错误", f"开始测试失败: {e}")

    def _validate_all_battery_codes(self) -> list:
        """
        验证所有电池码的唯一性

        Returns:
            验证错误列表，空列表表示验证通过
        """
        try:
            errors = []

            # 检查通道间重复
            codes_map = {}  # {code: [channels]}
            for channel, code in self.channel_barcodes.items():
                if code.strip():
                    code_upper = code.strip().upper()
                    if code_upper not in codes_map:
                        codes_map[code_upper] = []
                    codes_map[code_upper].append(channel)

            # 找出重复的电池码
            for code, channels in codes_map.items():
                if len(channels) > 1:
                    errors.append(f"电池码 '{code}' 在通道 {', '.join(map(str, channels))} 中重复")

            # 检查与历史记录的重复
            if self.serial_manager:
                for channel, code in self.channel_barcodes.items():
                    if code.strip():
                        validation_result = self.serial_manager.validate_serial_number(code.strip())
                        if not validation_result.is_valid and validation_result.error_code == "DUPLICATE_SERIAL":
                            errors.append(f"通道 {channel} 电池码 '{code.strip()}' 与历史记录重复")

            return errors

        except Exception as e:
            logger.error(f"验证所有电池码失败: {e}")
            return [f"验证过程出错: {e}"]

    def _show_validation_errors(self, errors: list):
        """
        显示验证错误

        Args:
            errors: 错误信息列表
        """
        try:
            from PyQt5.QtWidgets import QMessageBox

            error_message = "检测到以下电池码重复问题：\n\n" + "\n".join(errors)
            error_message += "\n\n请修正重复的电池码后再开始测试。"

            QMessageBox.warning(
                self, "电池码重复检测",
                error_message,
                QMessageBox.Ok
            )

            logger.warning(f"⚠️ 电池码验证失败，阻止开始测试: {errors}")

        except Exception as e:
            logger.error(f"显示验证错误失败: {e}")

    def on_cancel(self):
        """取消操作"""
        try:
            logger.info("用户取消电池侦测模式启动")

            # 停止状态更新定时器
            self.status_update_timer.stop()

            # 发送取消信号
            self.dialog_cancelled.emit()

            # 关闭对话框
            self.reject()

        except Exception as e:
            logger.error(f"取消操作失败: {e}")

    def closeEvent(self, event):
        """关闭事件"""
        try:
            # 停止定时器
            self.status_update_timer.stop()

            # 🔤 恢复之前的输入法
            if self.barcode_scanner_enabled:
                logger.info("🔤 电池侦测引导对话框关闭，恢复输入法")
                if self.input_method_manager.restore_previous_input_method():
                    logger.info("🔤 电池侦测模式输入法恢复成功")
                else:
                    logger.warning("🔤 电池侦测模式输入法恢复失败")

            super().closeEvent(event)
        except Exception as e:
            logger.error(f"关闭事件处理失败: {e}")

    def get_channel_barcodes(self):
        """获取通道条码信息"""
        return self.channel_barcodes.copy()
