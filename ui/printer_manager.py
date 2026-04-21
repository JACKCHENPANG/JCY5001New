"""
打印机管理器模块

负责检测打印机连接状态并通知主界面更新状态栏显示
"""

import logging
import win32print
from datetime import datetime
import threading

from typing import Dict, Any, List
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class PrinterManager(QObject):
    """打印机管理器"""

    # 信号定义
    printer_status_changed = pyqtSignal(bool)  # 打印机状态变更信号

    def __init__(self, config_manager, parent=None):
        """
        初始化打印机管理器

        Args:
            config_manager: 配置管理器
            parent: 父对象
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.current_printer_connected = False
        self.last_printer_name = ""
        self.last_status_check = None
        # 异步检查控制标志，防止阻塞UI线程
        self._checking = False
        self._check_started_at = None
        # 🐛 修复：添加失败缓存，避免重复检查已知失败的打印机
        self._failed_printers = set()  # 缓存检查失败的打印机名称
        self._last_failed_check = {}  # 记录上次失败检查的时间

        # 简化初始化：直接设置虚拟打印机为已连接状态
        self._initialize_virtual_printer()

        # 初始化定时器
        self._init_timer()

        # 执行初始检测
        self._check_printer_status()

        logger.debug("打印机管理器初始化完成")
    def _initialize_virtual_printer(self):
        """初始化虚拟打印机设置"""
        try:
            # 获取配置的打印机名称
            configured_printer = self.config_manager.get('printer.name', '')

            # 如果没有配置打印机，自动设置为Microsoft Print to PDF
            if not configured_printer:
                self.config_manager.set('printer.name', 'Microsoft Print to PDF')
                configured_printer = 'Microsoft Print to PDF'
                logger.info("自动设置虚拟打印机: Microsoft Print to PDF")

            # 🐛 修复：扩展虚拟打印机检测，确保Microsoft Print to PDF被正确识别
            is_virtual_printer = (
                "PDF" in configured_printer.upper() or
                "XPS" in configured_printer.upper() or
                "PRINT TO" in configured_printer.upper() or
                configured_printer == "Microsoft Print to PDF"
            )

            # 如果是虚拟打印机，直接设置为已连接并清除失败缓存
            if is_virtual_printer:
                self.current_printer_connected = True
                self.last_printer_name = configured_printer

                # 🐛 修复：清除虚拟打印机的失败缓存
                self._failed_printers.discard(configured_printer)
                self._last_failed_check.pop(configured_printer, None)

                logger.info(f"虚拟打印机 {configured_printer} 已设置为连接状态，缓存已清除")

        except Exception as e:
            logger.error(f"初始化虚拟打印机失败: {e}")

    def _init_timer(self):
        """初始化状态检测定时器"""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._check_printer_status)

        # 🐛 修复：减少检查频率，避免频繁的打印机状态检查
        # 每30秒检测一次打印机状态（原来是5秒）
        check_interval = self.config_manager.get('printer.status_check_interval', 30000)
        self.status_timer.start(check_interval)

        # 添加清理定时器，定期检查并清理卡住的状态检查
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_stuck_checks)
        self.cleanup_timer.start(30000)  # 每30秒清理一次

        logger.debug(f"打印机状态检测定时器已启动，间隔: {check_interval}ms")

    def _check_printer_status(self):
        """检测打印机状态"""
        # 非阻塞：如果上次检查尚未完成，则跳过本次，避免阻塞导致的 KeyboardInterrupt
        try:
            if self._checking:
                from datetime import datetime as _dt
                if self._check_started_at and (_dt.now() - self._check_started_at).total_seconds() > 8:
                    logger.warning("打印机状态检查疑似卡住，已超时重置")
                    self._reset_checking_flag()
                else:
                    logger.debug("上次打印机状态检查仍在进行，跳过本次")
                    return

            # 启动异步检查线程
            self._checking = True
            self._check_started_at = datetime.now()
            logger.debug("启动异步打印机状态检查")

            # 使用更安全的线程启动方式
            check_thread = threading.Thread(target=self._check_printer_status_async, daemon=True)
            check_thread.start()
            return
        except Exception as e:
            logger.error(f"启动异步打印机状态检查失败: {e}")
            # 重置标志并回退到同步路径
            self._reset_checking_flag()

        try:
            # 更新检查时间
            self.last_status_check = datetime.now()

            # 获取配置的打印机名称
            configured_printer = self.config_manager.get('printer.name', '')
            logger.debug(f"配置的打印机名称: '{configured_printer}'")

            if not configured_printer:
                # 没有配置打印机，尝试自动发现NIIMBOT打印机
                logger.debug("未配置打印机，尝试自动发现NIIMBOT打印机")
                connected = self._auto_discover_printer()
            else:
                # 检查指定的打印机
                logger.debug(f"检查指定打印机: {configured_printer}")
                connected = self._check_specific_printer(configured_printer)
                if connected:
                    self.last_printer_name = configured_printer
                else:
                    # 🐛 修复：如果配置的打印机不可用，正确显示离线状态
                    logger.warning(f"[异步] 配置的打印机 {configured_printer} 当前检查失败，保持配置并允许后续尝试")
                    self.last_printer_name = configured_printer
                    # 🐛 修复：不强制设置为连接状态，让状态栏正确显示离线
                    connected = False  # 正确显示离线状态

            # 如果状态发生变化，发送信号
            if connected != self.current_printer_connected:
                self.current_printer_connected = connected
                self.printer_status_changed.emit(connected)

                status_text = "已连接" if connected else "未连接"
                logger.info(f"打印机状态变更: {status_text}")
            else:
                # 即使状态没有变化，也记录当前状态（用于调试）
                status_text = "已连接" if connected else "未连接"
                logger.debug(f"打印机状态保持: {status_text}")

        except Exception as e:
            logger.error(f"检测打印机状态失败: {e}")

            # 出现异常时认为打印机未连接
            if self.current_printer_connected:
                self.current_printer_connected = False
                self.printer_status_changed.emit(False)

    def _check_printer_status_async(self):
        """在后台线程执行打印机状态检查，完成后切回主线程更新UI"""
        try:
            configured_printer = self.config_manager.get('printer.name', '')
            connected = False
            new_last_name = self.last_printer_name

            if not configured_printer:
                logger.debug("[异步] 未配置打印机，尝试自动发现")
                connected = self._auto_discover_printer()
                new_last_name = self.last_printer_name  # 自动发现过程中可能已更新
            else:
                # 🐛 修复：优先检查虚拟打印机，避免不必要的检查
                is_virtual_printer = (
                    "PDF" in configured_printer.upper() or
                    "XPS" in configured_printer.upper() or
                    "PRINT TO" in configured_printer.upper() or
                    configured_printer == "Microsoft Print to PDF"
                )

                if is_virtual_printer:
                    logger.debug(f"[异步] 检测到虚拟打印机，直接设为在线: {configured_printer}")
                    connected = True
                    # 清除虚拟打印机的失败缓存
                    self._failed_printers.discard(configured_printer)
                    self._last_failed_check.pop(configured_printer, None)
                else:
                    # 🐛 修复：快速失败机制，避免重复检查已知失败的打印机
                    from datetime import datetime, timedelta
                    now = datetime.now()

                    # 🐛 修复：减少快速失败时间窗口，从5分钟改为1分钟
                    # 如果这个打印机在最近1分钟内检查失败过，跳过检查
                    if (configured_printer in self._failed_printers and
                        configured_printer in self._last_failed_check and
                        now - self._last_failed_check[configured_printer] < timedelta(minutes=1)):
                        logger.debug(f"[异步] 跳过最近失败的打印机检查: {configured_printer} (失败缓存)")
                        connected = False
                    else:
                        logger.debug(f"[异步] 检查指定打印机: {configured_printer}")
                        # 🐛 修复：使用线程超时机制，避免长时间阻塞
                        import threading
                        import queue

                        result_queue = queue.Queue()

                        def check_printer_with_timeout():
                            try:
                                result = self._check_specific_printer(configured_printer)
                                result_queue.put(('success', result))
                            except Exception as e:
                                result_queue.put(('error', str(e)))

                        # 启动检查线程
                        check_thread = threading.Thread(target=check_printer_with_timeout, daemon=True)
                        check_thread.start()

                        # 等待结果，最多3秒
                        try:
                            result_type, result_value = result_queue.get(timeout=3)
                            if result_type == 'success':
                                connected = result_value
                            else:
                                logger.debug(f"[异步] 打印机检查异常: {result_value}")
                                connected = False
                        except queue.Empty:
                            logger.warning(f"[异步] 打印机检查超时: {configured_printer}")
                            connected = False

                # 🐛 修复：更新失败缓存
                if not connected:
                    self._failed_printers.add(configured_printer)
                    self._last_failed_check[configured_printer] = now
                else:
                    # 如果检查成功，从失败缓存中移除
                    self._failed_printers.discard(configured_printer)
                    self._last_failed_check.pop(configured_printer, None)

                # 🐛 修复：保留配置名，但正确处理连接状态
                new_last_name = configured_printer
                if not connected:
                    logger.warning(f"[异步] 配置的打印机 {configured_printer} 当前检查失败，保持配置并允许后续尝试")
                    # 对于虚拟打印机，强制设为连接状态
                    if "PDF" in configured_printer.upper() or "XPS" in configured_printer.upper():
                        connected = True
                        logger.info(f"[异步] 虚拟打印机 {configured_printer} 强制设为已连接")
                    else:
                        # 🐛 修复：对于物理打印机，如果检查失败就显示离线
                        connected = False

            # 切回主线程应用结果
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._apply_printer_status_update(connected, new_last_name))
        except Exception as e:
            logger.error(f"异步检测打印机状态失败: {e}")
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._apply_printer_status_update(False, self.last_printer_name))
        finally:
            # 🐛 修复：直接在后台线程重置标志，避免主线程延迟
            self._checking = False
            self._check_started_at = None
            logger.debug("[异步] 打印机状态检查标志已重置")

    def _apply_printer_status_update(self, connected: bool, printer_name: str):
        """在主线程更新状态并发信号"""
        try:
            self.last_status_check = datetime.now()
            self.last_printer_name = printer_name or self.last_printer_name

            if connected != self.current_printer_connected:
                self.current_printer_connected = connected
                self.printer_status_changed.emit(connected)
                status_text = "已连接" if connected else "未连接"
                logger.info(f"打印机状态变更: {status_text}")
            else:
                status_text = "已连接" if connected else "未连接"
                logger.debug(f"打印机状态保持: {status_text}")
        except Exception as e:
            logger.error(f"应用打印机状态更新失败: {e}")
        finally:
            # 确保重置检查标志
            self._reset_checking_flag()

    def _reset_checking_flag(self):
        """重置检查标志"""
        try:
            self._checking = False
            self._check_started_at = None
            logger.debug("打印机状态检查标志已重置")
        except Exception as e:
            logger.error(f"重置检查标志失败: {e}")

    def clear_failed_printer_cache(self):
        """清除失败打印机缓存，强制重新检查所有打印机"""
        try:
            self._failed_printers.clear()
            self._last_failed_check.clear()
            logger.info("🔄 已清除打印机失败缓存，将重新检查所有打印机")
        except Exception as e:
            logger.error(f"清除失败缓存失败: {e}")

    def force_refresh_printer_status(self):
        """强制立即刷新打印机状态"""
        try:
            logger.info("🔄 强制刷新打印机状态...")

            # 清除失败缓存
            self.clear_failed_printer_cache()

            # 重新初始化虚拟打印机
            self._initialize_virtual_printer()

            # 立即检查打印机状态
            self._check_printer_status()

            # 强制发送状态更新信号
            self.force_emit_current_status()

            logger.info("✅ 打印机状态强制刷新完成")

        except Exception as e:
            logger.error(f"强制刷新打印机状态失败: {e}")

    def _cleanup_stuck_checks(self):
        """清理卡住的状态检查"""
        try:
            if self._checking and self._check_started_at:
                from datetime import datetime as _dt
                stuck_time = (_dt.now() - self._check_started_at).total_seconds()
                if stuck_time > 20:  # 超过20秒认为卡住
                    logger.warning(f"发现卡住的打印机状态检查，已持续 {stuck_time:.1f} 秒，强制清理")
                    self._reset_checking_flag()

                    # 如果有配置的打印机，强制设为连接状态
                    configured_printer = self.config_manager.get('printer.name', '')
                    if configured_printer and not self.current_printer_connected:
                        logger.info(f"强制设置配置的打印机 {configured_printer} 为连接状态")
                        self.current_printer_connected = True
                        self.last_printer_name = configured_printer
                        self.printer_status_changed.emit(True)
        except Exception as e:
            logger.error(f"清理卡住的状态检查失败: {e}")

    def _check_default_printer(self) -> bool:
        """检查默认打印机是否可用"""
        try:
            # 获取默认打印机
            default_printer = win32print.GetDefaultPrinter()

            if default_printer:
                return self._check_printer_availability(default_printer)
            else:
                logger.debug("未找到默认打印机")
                return False

        except Exception as e:
            logger.debug(f"获取默认打印机失败: {e}")
            return False

    def _check_specific_printer(self, printer_name: str) -> bool:
        """检查指定打印机是否可用"""
        try:
            return self._check_printer_availability(printer_name)
        except Exception as e:
            logger.debug(f"检查打印机 {printer_name} 失败: {e}")
            return False

    def _check_printer_availability(self, printer_name: str) -> bool:
        """检查打印机是否可用"""
        try:
            # 尝试打开打印机
            handle = win32print.OpenPrinter(printer_name)

            # 获取打印机状态
            printer_info = win32print.GetPrinter(handle, 2)
            win32print.ClosePrinter(handle)

            # 检查打印机状态
            status = printer_info.get('Status', 0)
            attributes = printer_info.get('Attributes', 0)

            # 针对NIIMBOT K3_W打印机的特殊处理
            if "NIIMBOT" in printer_name.upper() or "K3_W" in printer_name.upper():
                # NIIMBOT打印机的可用性检查
                is_available = self._check_niimbot_availability(printer_name, status, attributes)
            elif "PDF" in printer_name.upper() or "XPS" in printer_name.upper():
                # 虚拟打印机（PDF/XPS）始终视为可用，因为它们不依赖物理硬件
                is_available = True
                logger.debug(f"虚拟打印机 {printer_name} 视为可用")
            else:
                # 通用打印机可用性检查
                is_available = (
                    status == 0 or  # 正常状态
                    (status & 0x00000001) == 0  # 不是离线状态
                )

            if is_available:
                logger.debug(f"打印机 {printer_name} 可用，状态: {status}")
            else:
                logger.debug(f"打印机 {printer_name} 不可用，状态: {status}")

            return is_available

        except Exception as e:
            logger.debug(f"检查打印机 {printer_name} 可用性失败: {e}")
            return False

    def _auto_discover_printer(self) -> bool:
        """自动发现可用的打印机，优先选择NIIMBOT"""
        try:
            logger.debug("开始自动发现打印机...")

            # 获取所有打印机
            printer_list = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )

            niimbot_printers = []
            other_printers = []

            for printer_info in printer_list:
                printer_name = printer_info[2]

                try:
                    if self._check_printer_availability(printer_name):
                        if 'NIIMBOT' in printer_name.upper() or 'K3_W' in printer_name.upper():
                            niimbot_printers.append(printer_name)
                            logger.debug(f"发现可用的NIIMBOT打印机: {printer_name}")
                        else:
                            other_printers.append(printer_name)
                            logger.debug(f"发现可用的打印机: {printer_name}")
                except Exception as e:
                    logger.debug(f"检查打印机 {printer_name} 失败: {e}")
                    continue

            # 修复只有在没有配置打印机时才自动选择
            current_config = self.config_manager.get('printer.name', '')
            if not current_config:
                # 优先选择NIIMBOT打印机
                if niimbot_printers:
                    selected_printer = niimbot_printers[0]
                    logger.info(f"自动选择NIIMBOT打印机: {selected_printer}")

                    # 更新配置
                    self.config_manager.set('printer.name', selected_printer)
                    self.last_printer_name = selected_printer
                    return True

                elif other_printers:
                    selected_printer = other_printers[0]
                    logger.info(f"自动选择打印机: {selected_printer}")

                    # 更新配置
                    self.config_manager.set('printer.name', selected_printer)
                    self.last_printer_name = selected_printer
                    return True
            else:
                logger.debug(f"已有配置的打印机 '{current_config}'，跳过自动选择")
                return False

            # 如果没有配置且没有发现任何打印机
            logger.warning("未发现任何可用的打印机")
            return False

        except Exception as e:
            logger.error(f"自动发现打印机失败: {e}")
            return False

    def _check_niimbot_availability(self, printer_name: str, status: int, attributes: int) -> bool:
        """检查NIIMBOT打印机的可用性"""
        try:
            # NIIMBOT打印机的状态检查逻辑
            # 状态码参考：
            # 0x00000000 = 正常
            # 0x00000001 = 离线
            # 0x00000002 = 纸张用完
            # 0x00000004 = 纸张卡住
            # 0x00000008 = 门打开
            # 0x00000010 = 错误
            # 0x00000020 = 手动进纸
            # 0x00000040 = 缺纸
            # 0x00000080 = 输出满
            # 0x00000100 = 页面错误
            # 0x00000200 = 用户干预
            # 0x00000400 = 内存不足
            # 0x00000800 = 服务器未知

            # 对于NIIMBOT，我们认为以下状态是可用的：
            # 1. 状态为0（完全正常）
            # 2. 只有手动进纸状态（0x00000020）
            # 3. 只有缺纸状态（0x00000040）- 打印机在线但缺纸

            if status == 0:
                # 完全正常状态
                return True
            elif status == 0x00000020:
                # 手动进纸状态，打印机在线
                logger.debug(f"NIIMBOT打印机 {printer_name} 处于手动进纸状态，但可用")
                return True
            elif status == 0x00000040:
                # 缺纸状态，打印机在线但缺纸
                logger.debug(f"NIIMBOT打印机 {printer_name} 缺纸，但打印机在线")
                return True
            else:
                # 其他状态认为不可用
                logger.debug(f"NIIMBOT打印机 {printer_name} 状态异常: 0x{status:08X}")
                return False

        except Exception as e:
            logger.error(f"检查NIIMBOT打印机 {printer_name} 可用性失败: {e}")
            return False

    def get_current_status(self) -> bool:
        """获取当前打印机连接状态"""
        return self.current_printer_connected

    def refresh_status(self):
        """手动刷新打印机状态"""
        logger.info("手动刷新打印机状态")
        self._check_printer_status()

    def refresh_status_sync(self):
        """同步刷新打印机状态（用于初始化时确保状态正确）"""
        try:
            logger.info("🔄 同步刷新打印机状态")

            # 获取配置的打印机名称
            configured_printer = self.config_manager.get('printer.name', '')
            logger.debug(f"配置的打印机名称: '{configured_printer}'")

            if not configured_printer:
                # 没有配置打印机，设置为未连接
                connected = False
                logger.debug("未配置打印机，设置为未连接")
            else:
                # 同步检查指定的打印机
                logger.debug(f"同步检查指定打印机: {configured_printer}")
                connected = self._check_specific_printer(configured_printer)
                if connected:
                    self.last_printer_name = configured_printer
                else:
                    logger.warning(f"配置的打印机 {configured_printer} 当前不可用")
                    self.last_printer_name = configured_printer

            # 更新状态并发送信号
            if connected != self.current_printer_connected:
                self.current_printer_connected = connected
                self.printer_status_changed.emit(connected)
                status_text = "已连接" if connected else "未连接"
                logger.info(f"✅ 同步状态检查完成，打印机状态变更: {status_text}")
            else:
                status_text = "已连接" if connected else "未连接"
                logger.debug(f"✅ 同步状态检查完成，打印机状态保持: {status_text}")

        except Exception as e:
            logger.error(f"同步刷新打印机状态失败: {e}")
            # 出现异常时认为打印机未连接
            if self.current_printer_connected:
                self.current_printer_connected = False
                self.printer_status_changed.emit(False)

    def force_emit_current_status(self):
        """强制发送当前状态信号（用于UI同步）"""
        try:
            logger.debug(f"强制发送打印机状态信号: {'已连接' if self.current_printer_connected else '未连接'}")
            self.printer_status_changed.emit(self.current_printer_connected)
        except Exception as e:
            logger.error(f"强制发送打印机状态信号失败: {e}")

    def set_check_interval(self, interval_ms: int):
        """设置状态检测间隔"""
        if interval_ms > 0:
            self.status_timer.setInterval(interval_ms)
            logger.info(f"打印机状态检测间隔已设置为: {interval_ms}ms")
        else:
            logger.warning("无效的检测间隔，必须大于0")

    def start_monitoring(self):
        """开始监控打印机状态"""
        if not self.status_timer.isActive():
            self.status_timer.start()
            logger.info("打印机状态监控已启动")

    def stop_monitoring(self):
        """停止监控打印机状态"""
        if self.status_timer.isActive():
            self.status_timer.stop()
            logger.info("打印机状态监控已停止")

    def __del__(self):
        """析构函数"""
        try:
            if hasattr(self, 'status_timer') and self.status_timer:
                self.status_timer.stop()
            if hasattr(self, 'cleanup_timer') and self.cleanup_timer:
                self.cleanup_timer.stop()
        except:
            pass

    def is_printer_ready(self) -> bool:
        """检查打印机是否就绪"""
        try:
            # 如果状态检查卡住太久，强制重置
            if self._checking and self._check_started_at:
                from datetime import datetime as _dt
                if (_dt.now() - self._check_started_at).total_seconds() > 15:
                    logger.warning("打印机状态检查长时间卡住，强制重置并返回就绪状态")
                    self._reset_checking_flag()
                    # 对于配置的打印机，假设就绪
                    configured_printer = self.config_manager.get('printer.name', '')
                    if configured_printer:
                        return True

            return self.current_printer_connected and bool(self.last_printer_name)
        except Exception as e:
            logger.error(f"检查打印机就绪状态失败: {e}")
            return False

    def get_printer_status(self) -> Dict[str, Any]:
        """获取打印机状态信息"""
        try:
            return {
                'connected': self.current_printer_connected,
                'name': self.last_printer_name,
                'type': self.config_manager.get('printer.type', ''),
                'quality': self.config_manager.get('printer.quality', '草稿'),
                'last_check': self.last_status_check.isoformat() if self.last_status_check else None
            }
        except Exception as e:
            logger.error(f"获取打印机状态失败: {e}")
            return {
                'connected': False,
                'name': '',
                'type': '',
                'quality': '',
                'last_check': None
            }

    def get_available_printers(self) -> List[str]:
        """获取可用打印机列表"""
        try:
            printers = []
            printer_list = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)

            for printer_info in printer_list:
                printer_name = printer_info[2]  # 打印机名称
                if self._check_printer_availability(printer_name):
                    printers.append(printer_name)

            return printers

        except Exception as e:
            logger.error(f"获取可用打印机列表失败: {e}")
            return []

    def get_printer_details(self) -> Dict[str, Any]:
        """获取打印机详细信息"""
        try:
            result = {
                'configured_printer': self.config_manager.get('printer.name', ''),
                'current_status': self.current_printer_connected,
                'last_check': self.last_status_check.isoformat() if self.last_status_check else None,
                'available_printers': [],
                'niimbot_printers': []
            }

            # 获取所有打印机信息
            printer_list = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )

            for printer_info in printer_list:
                printer_name = printer_info[2]

                try:
                    handle = win32print.OpenPrinter(printer_name)
                    printer_details = win32print.GetPrinter(handle, 2)
                    win32print.ClosePrinter(handle)

                    is_available = self._check_printer_availability(printer_name)
                    is_niimbot = 'NIIMBOT' in printer_name.upper() or 'K3_W' in printer_name.upper()

                    printer_info_dict = {
                        'name': printer_name,
                        'status': printer_details.get('Status', 0),
                        'driver': printer_details.get('pDriverName', 'Unknown'),
                        'port': printer_details.get('pPortName', 'Unknown'),
                        'is_available': is_available,
                        'is_niimbot': is_niimbot
                    }

                    if is_available:
                        result['available_printers'].append(printer_info_dict)

                    if is_niimbot:
                        result['niimbot_printers'].append(printer_info_dict)

                except Exception as e:
                    logger.debug(f"获取打印机 {printer_name} 详细信息失败: {e}")
                    continue

            return result

        except Exception as e:
            logger.error(f"获取打印机详细信息失败: {e}")
            return {
                'configured_printer': '',
                'current_status': False,
                'available_printers': [],
                'niimbot_printers': []
            }

    def update_printer_config(self, printer_name: str) -> bool:
        """
        更新打印机配置

        Args:
            printer_name: 新的打印机名称

        Returns:
            是否更新成功
        """
        try:
            # 验证打印机是否可用
            if not self._check_printer_availability(printer_name):
                logger.error(f"打印机 {printer_name} 不可用，无法配置")
                return False

            # 更新配置
            old_printer = self.config_manager.get('printer.name', '')
            self.config_manager.set('printer.name', printer_name)

            # 修复立即保存配置到文件，确保设置持久化
            self.config_manager.save_config()

            # 更新内部状态
            self.last_printer_name = printer_name

            # 立即检查新打印机状态
            self._check_printer_status()

            # 新增强制发送状态变更信号，确保UI同步
            self.force_emit_current_status()

            logger.info(f"✅ 打印机配置已更新并保存: {old_printer} -> {printer_name}")
            return True

        except Exception as e:
            logger.error(f"更新打印机配置失败: {e}")
            return False
