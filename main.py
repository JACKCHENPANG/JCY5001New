#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JCY5001AS 八通道8路EIS电化学阻抗谱测试仪
主要入口

Author: Jack
Date: 2025-09-12
Version: V0.92.53
"""

import logging
from logging.handlers import RotatingFileHandler
import sys
import io

# 修复控制台编码，支持 emoji 日志输出
if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding and 'gb' in sys.stdout.encoding.lower():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import os
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor

# 设置日志格式和大小
SIMPLE_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
CONSOLE_FORMAT = '%(levelname)s: %(message)s'

# 设置日志输出终端大小
logging.basicConfig(
    level=logging.INFO,  # 默认使用INFO级别，减少日志输出
    format=CONSOLE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)  # 输出到控制台
    ]
)

logger = logging.getLogger(__name__)

# 修改资源检查导入
try:
    from startup_resource_check import main as check_resources
except ImportError:
    logger.warning("启动资源检查模块未找到")
    check_resources = None

# 确保日志目录存在
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 设置日志滚动大小
file_handler = RotatingFileHandler(
    os.path.join(log_dir, "app.log"),
    maxBytes=10*1024*1024,  # 10MB每个文件大小
    backupCount=5,          # 保留5个备份文件
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)  # 日志默认INFO级别
file_formatter = logging.Formatter(SIMPLE_FORMAT)
file_handler.setFormatter(file_formatter)
logging.getLogger().addHandler(file_handler)

# 高DPI支持，必须在QApplication创建之前
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow
from utils.exception_handler import install_exception_handlers, uninstall_exception_handlers
from utils.config_manager import ConfigManager


def create_splash_screen(app):
    """创建启动闪屏"""
    try:
        splash_pixmap = QPixmap(500, 300)
        splash_pixmap.fill(QColor(52, 73, 94))

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
            "JCY5001AS 八通道EIS阻抗谱\n正在加载系统组件...",
            Qt.AlignCenter | Qt.AlignBottom,
            Qt.white
        )

        app.processEvents()
        return splash

    except Exception as e:
        logger.error(f"创建启动闪屏失败: {e}")
        return None


def update_splash_message(splash, message):
    """更新闪屏显示信息"""
    if splash:
        splash.showMessage(
            f"JCY5001AS 八通道EIS阻抗谱\n{message}",
            Qt.AlignCenter | Qt.AlignBottom,
            Qt.white
        )
        QApplication.processEvents()


def setup_application():
    """设置应用程序基本信息"""
    app = QApplication(sys.argv)

    app.setApplicationName("JCY5001AS 八通道EIS阻抗谱")
    app.setApplicationVersion("V0.92.53")
    app.setOrganizationName("鲸测云")
    app.setOrganizationDomain("jingceyun.com")

    icon_path = os.path.join(os.path.dirname(__file__), "resources", "icons", "app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    return app


def main():
    """主入口 - 设置和启动"""
    splash = None
    startup_optimizer = None

    try:
        from utils.startup_optimizer import initialize_startup_optimization
        install_exception_handlers()

        if check_resources:
            logger.debug(" 初始化资源检查...")
            check_resources()

        app = setup_application()
        splash = create_splash_screen(app)
        update_splash_message(splash, "正在初始化系统...")

        try:
            from utils.qpainter_fix import QPainterFix
            QPainterFix.apply_global_fixes()
        except ImportError:
            pass

        update_splash_message(splash, "正在加载配置文件...")
        config_manager = ConfigManager()

        from utils.log_config_manager import initialize_log_config_manager
        log_config_manager = initialize_log_config_manager(config_manager)
        logger.info("✅ 日志配置管理器初始化完成")

        startup_optimizer, fast_startup_manager = initialize_startup_optimization(config_manager)
        startup_optimizer.start_optimization()
        startup_optimizer.start_stage("加载配置")

        fast_startup_manager.optimize_logging_for_startup()

        startup_optimizer.start_stage("日志系统初始化")
        update_splash_message(splash, "正在初始化日志系统...")

        from utils.log_deduplicator import initialize_log_deduplicator
        _ = initialize_log_deduplicator(window_size=20, time_window=120)
        logger.info("✅ 日志去重模块初始化")

        startup_optimizer.start_stage("加载数据库")
        update_splash_message(splash, "正在初始化数据库连接...")
        from data.database_manager import initialize_database_manager
        database_manager = initialize_database_manager()
        logger.info("✅ 数据库管理器初始化完成")

        startup_optimizer.start_stage("创建窗口")
        update_splash_message(splash, "正在创建主窗口...")

        def delayed_initialization():
            """延迟初始化（窗口显示后执行，不阻塞界面启动）"""
            try:
                logger.info("✅ 开始延迟初始化")
                fast_startup_manager.restore_normal_logging()

                # 授权验证（后台执行，不阻塞启动）
                try:
                    from utils.license_manager import LicenseManager
                    lm = LicenseManager(config_manager)
                    lm.initialize_trial(config_manager.get('app.trial_days', 30))
                    status = lm.get_license_status()
                    if status['is_licensed']:
                        logger.info("✅ 已获得正式授权")
                    elif not status['is_trial_expired']:
                        logger.info(f"试用版授权 剩余 {status['remaining_days']} 天")
                    else:
                        logger.warning("⚠️ 试用授权已到期，请联系销售获取正式授权")
                except Exception as e:
                    logger.error(f"授权验证失败: {e}")

                # 启动远程API服务（后台线程）
                try:
                    from remote_api import start_api_server
                    start_api_server(host="0.0.0.0", port=5000, main_window=main_window)
                    logger.info("✅ 远程API服务已启动，端口 5000")
                except Exception as e:
                    logger.warning(f"⚠️ 远程API服务启动失败: {e}")

                # 启动MCP服务器（后台线程）
                try:
                    from jcy5001_mcp_server import MCPServerThread
                    mcp_thread = MCPServerThread()
                    mcp_thread.start()
                    logger.info("✅ MCP服务器已启动")
                except Exception as e:
                    logger.warning(f"⚠️ MCP服务器启动失败: {e}")

                if splash:
                    splash.close()

                if startup_optimizer:
                    startup_optimizer.finish_optimization()

            except Exception as e:
                logger.error(f"延迟初始化失败: {e}")
                if splash:
                    splash.close()

        main_window = MainWindow(config_manager, database_manager)

        startup_optimizer.start_stage("显示窗口")
        main_window.showMaximized()
        main_window.raise_()
        main_window.activateWindow()

        logger.debug("✅ 主窗口初始化完成，开始启动延迟任务...")

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, delayed_initialization)

        logger.info("程序主窗口显示完成")

        result = app.exec_()
        uninstall_exception_handlers()
        sys.exit(result)

    except Exception as e:
        print(f"应用程序初始化失败: {e}")
        if splash:
            splash.close()
        try:
            uninstall_exception_handlers()
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
