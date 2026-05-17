#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JCY5001AS鲸测云8路EIS阻抗筛选仪产线界面
主程序入口文件

Author: Jack
Date: 2025-09-12
Version: V0.92.59
"""

import logging
from logging.handlers import RotatingFileHandler
import sys
import os
import io
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor

# 设置stdout/stderr为UTF-8编码，防止emoji日志出现乱码
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# 优化简化日志格式，减少文件大小
SIMPLE_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
CONSOLE_FORMAT = '%(levelname)s: %(message)s'

# 优化配置日志轮转，防止单个文件过大
# 创建控制台处理器，指定UTF-8编码
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(CONSOLE_FORMAT)
console_handler.setFormatter(console_formatter)

# 配置根logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)

# 修复导入启动资源检查
try:
    from startup_resource_check import main as check_resources
except ImportError:
    logger.warning("启动资源检查模块未找到")
    check_resources = None

# 确保日志目录存在
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 优化添加轮转文件处理器，限制单个文件大小
file_handler = RotatingFileHandler(
    os.path.join(log_dir, "app.log"),
    maxBytes=10*1024*1024,  # 10MB单个文件大小限制
    backupCount=5,          # 保留5个备份文件
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)  # 优化文件日志默认INFO级别
file_formatter = logging.Formatter(SIMPLE_FORMAT)
file_handler.setFormatter(file_formatter)
logging.getLogger().addHandler(file_handler)

# 在文件开头添加此行，确保Qt的HighDpiScaling设置在QApplication创建之前
# QApplication实例通常在main_window.py中创建
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow
from utils.exception_handler import install_exception_handlers, uninstall_exception_handlers
from utils.config_manager import ConfigManager


def create_splash_screen(app):
    """创建启动画面"""
    try:
        # 创建启动画面
        splash_pixmap = QPixmap(500, 300)
        splash_pixmap.fill(QColor(52, 73, 94))  # 深蓝色背景

        splash = QSplashScreen(splash_pixmap)
        splash.setStyleSheet("""
            QSplashScreen {
                background-color: #34495e;
                color: white;
                font-size: 14pt;
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 10px;
            }
        """)

        splash.show()
        splash.showMessage(
            "JCY5001A电池阻抗测试系统\n\n正在启动...",
            Qt.AlignCenter | Qt.AlignBottom,
            Qt.white
        )

        # 处理事件，确保启动画面显示
        app.processEvents()

        return splash

    except Exception as e:
        logger.error(f"创建启动画面失败: {e}")
        return None


def update_splash_message(splash, message):
    """更新启动画面消息"""
    if splash:
        splash.showMessage(
            f"JCY5001AS鲸测云8路EIS阻抗筛选仪\n\n{message}",
            Qt.AlignCenter | Qt.AlignBottom,
            Qt.white
        )
        QApplication.processEvents()


def setup_application():
    """设置应用程序基本属性"""
    app = QApplication(sys.argv)

    # 关键修复：主窗口意外关闭/隐藏时，不要让 Qt 自动带退整个进程。
    # 5000 远程 API 依赖主进程常驻，后续可由窗口监控或远程逻辑自行恢复窗口。
    app.setQuitOnLastWindowClosed(False)

    # 设置应用程序基本信息
    app.setApplicationName("JCY5001AS鲸测云8路EIS阻抗筛选仪")
    app.setApplicationVersion("V0.92.59")
    app.setOrganizationName("鲸测云")
    app.setOrganizationDomain("jingceyun.com")

    # 设置应用程序图标
    icon_path = os.path.join(os.path.dirname(__file__), "resources", "icons", "app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 设置默认字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    return app


def main():
    """主函数 - 优化启动性能"""
    splash = None
    startup_optimizer = None

    try:
        # 🚀 启动性能优化：初始化优化器
        from utils.startup_optimizer import initialize_startup_optimization

        # 安装全局异常处理器
        install_exception_handlers()

        # 修复启动时检查和修复资源文件
        if check_resources:
            logger.debug(f" 开始启动资源检查...")
            check_resources()

        # 创建应用程序
        app = setup_application()

        # 🚀 优化：创建启动画面，提升用户体验
        splash = create_splash_screen(app)
        update_splash_message(splash, "正在初始化系统...")

        # 导入QPainter修复模块
        try:
            from utils.qpainter_fix import QPainterFix
            QPainterFix.apply_global_fixes()
        except ImportError:
            pass

        # 🚀 优化：初始化配置和启动优化器
        update_splash_message(splash, "正在加载配置...")
        config_manager = ConfigManager()

        from utils.log_config_manager import initialize_log_config_manager
        log_config_manager = initialize_log_config_manager(config_manager)
        logger.info("✅ 日志配置管理器已初始化并应用设置")

        startup_optimizer, fast_startup_manager = initialize_startup_optimization(config_manager)
        startup_optimizer.start_optimization()
        startup_optimizer.start_stage("配置加载")

        # 🚀 优化：为启动期间优化日志
        fast_startup_manager.optimize_logging_for_startup()

        startup_optimizer.start_stage("日志系统初始化")
        update_splash_message(splash, "正在初始化日志系统...")

        # 初始化日志去重器
        from utils.log_deduplicator import initialize_log_deduplicator
        _ = initialize_log_deduplicator(window_size=20, time_window=120)
        logger.info("✅ 日志去重器已初始化")

        startup_optimizer.start_stage("数据库初始化")
        update_splash_message(splash, "正在初始化数据库...")
        from data.database_manager import initialize_database_manager
        database_manager = initialize_database_manager()
        logger.info("✅ 数据库管理器已初始化")

        startup_optimizer.start_stage("授权检查")
        update_splash_message(splash, "正在检查软件授权...")
        try:
            from utils.license_manager import LicenseManager
            license_manager = LicenseManager(config_manager)

            # 初始化试用期（如果是首次运行）
            trial_days = config_manager.get('app.trial_days', 30)
            license_manager.initialize_trial(trial_days)

            # 检查授权状态
            status = license_manager.get_license_status()
            if status['is_licensed']:
                logger.info("✅ 软件已正式授权")
            elif not status['is_trial_expired']:
                remaining_days = status['remaining_days']
                logger.info(f"软件处于临时授权状态，剩余 {remaining_days} 天")
            else:
                logger.warning("⚠️ 软件试用期已到期，功能将受限")

        except Exception as e:
            logger.error(f"❌ 初始化授权管理失败: {e}")

        startup_optimizer.start_stage("主界面创建")
        update_splash_message(splash, "正在创建主界面...")

        # 🚀 优化：延迟初始化非关键组件
        def delayed_initialization():
            """延迟初始化非关键组件"""
            try:
                logger.info("🔄 开始延迟初始化非关键组件...")

                # 启动远程 API 服务
                try:
                    from remote_api import start_api_server
                    api_server = start_api_server(host="0.0.0.0", port=5000, main_window=main_window)
                    logger.info("✅ 远程 API 服务已启动 (端口 5000)")
                except Exception as api_err:
                    logger.error(f"远程 API 启动失败: {api_err}")


                # 🚫 存储管理器已删除

                logger.info("✅ 延迟初始化完成")

                # 恢复正常日志级别
                fast_startup_manager.restore_normal_logging()

                # 关闭启动画面
                if splash:
                    splash.close()

                # 完成启动优化
                if startup_optimizer:
                    startup_optimizer.finish_optimization()

            except Exception as e:
                logger.error(f"延迟初始化失败: {e}")
                if splash:
                    splash.close()

        # 创建主窗口
        main_window = MainWindow(config_manager, database_manager)

        startup_optimizer.start_stage("窗口显示")
        # 修改启动时自动最大化显示（保留任务栏和窗口边框）
        main_window.showMaximized()
        main_window.raise_()  # 将窗口提到前台
        main_window.activateWindow()  # 激活窗口

        logger.debug("🎯 主窗口初始化完成，准备显示窗口...")

        # 🚀 优化：立即初始化非关键组件，减少启动卡顿
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, delayed_initialization)  # 减少延迟时间

        # 自动连接到设备 - 延迟到UI初始化完成后
        def do_autoconnect():
            try:
                cm = getattr(main_window, 'comm_manager', None)
                if not cm:
                    return

                def _is_connected(cm):
                    try:
                        if hasattr(cm, 'is_device_connected') and callable(cm.is_device_connected):
                            return cm.is_device_connected()
                        v = getattr(cm, 'is_connected', False)
                        return v() if callable(v) else bool(v)
                    except Exception:
                        return False

                def _get_port(cm):
                    try:
                        if hasattr(cm, 'get_connection_info') and callable(cm.get_connection_info):
                            info = cm.get_connection_info()
                            if info and info.get('port'):
                                return info['port']
                        return getattr(cm, 'port', None)
                    except Exception:
                        return None

                # 已连接则只同步 API 状态，无需重复连接
                if _is_connected(cm):
                    current_port = _get_port(cm)
                    if current_port:
                        logger.info(f"✅ 设备已连接: {current_port}，同步API状态")
                        try:
                            from remote_api import update_state
                            update_state(connected_device=current_port)
                        except Exception:
                            pass
                        return

                # 未连接则尝试自动识别并连接
                from backend.device_detector import DeviceDetector
                logger.info("🔍 开始自动识别设备...")
                detector = DeviceDetector()
                port = detector.detect_device()

                if port:
                    logger.info(f"✅ 检测到设备: {port}，正在连接...")
                    success = cm.reconnect_with_new_port(port)
                    if success:
                        logger.info(f"✅ 已自动连接到设备: {port}")
                        try:
                            from remote_api import update_state
                            update_state(connected_device=port)
                        except Exception:
                            pass
                    else:
                        logger.warning(f"⚠️ 自动连接失败: {port}")
                else:
                    # detect_device失败可能是因为端口已被本进程占用（已连接）
                    if _is_connected(cm):
                        current_port = _get_port(cm)
                        logger.info(f"✅ 设备已连接: {current_port or 'unknown'}")
                    else:
                        logger.warning("⚠️ 未检测到设备，请手动连接")
            except Exception as e:
                logger.warning(f"⚠️ 自动识别设备失败: {e}")

        QTimer.singleShot(4000, do_autoconnect)

        logger.info("主窗口已显示并最大化")

        # 运行应用程序
        result = app.exec_()

        # 卸载异常处理器
        uninstall_exception_handlers()

        sys.exit(result)

    except Exception as e:
        print(f"应用程序启动失败: {e}")

        # 关闭启动画面
        if splash:
            splash.close()

        # 确保卸载异常处理器
        try:
            uninstall_exception_handlers()
        except:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()


# 强制启动 API（如果延迟初始化失败）
def force_start_api():
    try:
        from remote_api import start_api_server
        api_server = start_api_server(host="0.0.0.0", port=5000, main_window=None)
        print("API server force started on port 5000")
    except Exception as e:
        print(f"Force start API failed: {e}")

# 在程序启动后尝试强制启动
import threading
threading.Timer(5.0, force_start_api).start()
