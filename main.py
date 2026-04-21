#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JCY5001AS������8·EIS�迹ɸѡ�ǲ��߽���
����������ļ�

Author: Jack
Date: 2025-09-12
Version: V0.92.32
"""

import logging
from logging.handlers import RotatingFileHandler
import sys
import os
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor

# �Ż�����־��ʽ�������ļ���С
SIMPLE_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
CONSOLE_FORMAT = '%(levelname)s: %(message)s'

# �Ż�������־��ת����ֹ�����ļ�����
logging.basicConfig(
    level=logging.INFO,  # �Ż�Ĭ��ʹ��INFO���𣬼�����־��
    format=CONSOLE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)  # ���������̨
    ]
)

logger = logging.getLogger(__name__)

# �޸�����������Դ���
try:
    from startup_resource_check import main as check_resources
except ImportError:
    logger.warning("������Դ���ģ��δ�ҵ�")
    check_resources = None

# ȷ����־Ŀ¼����
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# �Ż�������ת�ļ������������Ƶ����ļ���С
file_handler = RotatingFileHandler(
    os.path.join(log_dir, "app.log"),
    maxBytes=10*1024*1024,  # 10MB�����ļ���С����
    backupCount=5,          # ����5�������ļ�
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)  # �Ż��ļ���־Ĭ��INFO����
file_formatter = logging.Formatter(SIMPLE_FORMAT)
file_handler.setFormatter(file_formatter)
logging.getLogger().addHandler(file_handler)

# ���ļ���ͷ���Ӵ��У�ȷ��Qt��HighDpiScaling������QApplication����֮ǰ
# QApplicationʵ��ͨ����main_window.py�д���
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

# ������Ŀ��Ŀ¼��Python·��
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow
from utils.exception_handler import install_exception_handlers, uninstall_exception_handlers
from utils.config_manager import ConfigManager


def create_splash_screen(app):
    """������������"""
    try:
        # ������������
        splash_pixmap = QPixmap(500, 300)
        splash_pixmap.fill(QColor(52, 73, 94))  # ����ɫ����

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
            "JCY5001A����迹����ϵͳ\n\n��������...",
            Qt.AlignCenter | Qt.AlignBottom,
            Qt.white
        )

        # �����¼���ȷ������������ʾ
        app.processEvents()

        return splash

    except Exception as e:
        logger.error(f"������������ʧ��: {e}")
        return None


def update_splash_message(splash, message):
    """��������������Ϣ"""
    if splash:
        splash.showMessage(
            f"JCY5001AS������8·EIS�迹ɸѡ��\n\n{message}",
            Qt.AlignCenter | Qt.AlignBottom,
            Qt.white
        )
        QApplication.processEvents()


def setup_application():
    """����Ӧ�ó����������"""
    app = QApplication(sys.argv)

    # ����Ӧ�ó��������Ϣ
    app.setApplicationName("JCY5001AS������8·EIS�迹ɸѡ��")
    app.setApplicationVersion("V0.92.42")
    app.setOrganizationName("������")
    app.setOrganizationDomain("jingceyun.com")

    # ����Ӧ�ó���ͼ��
    icon_path = os.path.join(os.path.dirname(__file__), "resources", "icons", "app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # ����Ĭ������
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    return app


def main():
    """������ - �Ż���������"""
    splash = None
    startup_optimizer = None

    try:
        # ?? ���������Ż�����ʼ���Ż���
        from utils.startup_optimizer import initialize_startup_optimization

        # ��װȫ���쳣������
        install_exception_handlers()

        # �޸�����ʱ�����޸���Դ�ļ�
        if check_resources:
            logger.debug(f" ��ʼ������Դ���...")
            check_resources()

        # ����Ӧ�ó���
        app = setup_application()

        # ?? �Ż��������������棬�����û�����
        splash = create_splash_screen(app)
        update_splash_message(splash, "���ڳ�ʼ��ϵͳ...")

        # ����QPainter�޸�ģ��
        try:
            from utils.qpainter_fix import QPainterFix
            QPainterFix.apply_global_fixes()
        except ImportError:
            pass

        # ?? �Ż�����ʼ�����ú������Ż���
        update_splash_message(splash, "���ڼ�������...")
        config_manager = ConfigManager()

        from utils.log_config_manager import initialize_log_config_manager
        log_config_manager = initialize_log_config_manager(config_manager)
        logger.info("? ��־���ù������ѳ�ʼ����Ӧ������")

        startup_optimizer, fast_startup_manager = initialize_startup_optimization(config_manager)
        startup_optimizer.start_optimization()
        startup_optimizer.start_stage("���ü���")

        # ?? �Ż���Ϊ�����ڼ��Ż���־
        fast_startup_manager.optimize_logging_for_startup()

        startup_optimizer.start_stage("��־ϵͳ��ʼ��")
        update_splash_message(splash, "���ڳ�ʼ����־ϵͳ...")

        # ��ʼ����־ȥ����
        from utils.log_deduplicator import initialize_log_deduplicator
        _ = initialize_log_deduplicator(window_size=20, time_window=120)
        logger.info("? ��־ȥ�����ѳ�ʼ��")

        startup_optimizer.start_stage("���ݿ��ʼ��")
        update_splash_message(splash, "���ڳ�ʼ�����ݿ�...")
        from data.database_manager import initialize_database_manager
        database_manager = initialize_database_manager()
        logger.info("? ���ݿ�������ѳ�ʼ��")

        startup_optimizer.start_stage("��Ȩ���")
        update_splash_message(splash, "���ڼ��������Ȩ...")
        try:
            from utils.license_manager import LicenseManager
            license_manager = LicenseManager(config_manager)

            # ��ʼ�������ڣ�������״����У�
            trial_days = config_manager.get('app.trial_days', 30)
            license_manager.initialize_trial(trial_days)

            # �����Ȩ״̬
            status = license_manager.get_license_status()
            if status['is_licensed']:
                logger.info("? ��������ʽ��Ȩ")
            elif not status['is_trial_expired']:
                remaining_days = status['remaining_days']
                logger.info(f"����������ʱ��Ȩ״̬��ʣ�� {remaining_days} ��")
            else:
                logger.warning("?? �����������ѵ��ڣ����ܽ�����")

        except Exception as e:
            logger.error(f"? ��ʼ����Ȩ����ʧ��: {e}")

        startup_optimizer.start_stage("�����洴��")
        update_splash_message(splash, "���ڴ���������...")

        # ?? �Ż����ӳٳ�ʼ���ǹؼ����
        def delayed_initialization():
            """�ӳٳ�ʼ���ǹؼ����"""
            try:
                logger.info("?? ��ʼ�ӳٳ�ʼ���ǹؼ����...")

                # ?? �洢��������ɾ��

                logger.info("? �ӳٳ�ʼ�����")

                # �ָ�������־����
                fast_startup_manager.restore_normal_logging()

                # �ر���������
                if splash:
                    splash.close()

                # ��������Ż�
                if startup_optimizer:
                    startup_optimizer.finish_optimization()

            except Exception as e:
                logger.error(f"�ӳٳ�ʼ��ʧ��: {e}")
                if splash:
                    splash.close()

        # ����������
        main_window = MainWindow(config_manager, database_manager)

        startup_optimizer.start_stage("������ʾ")
        # �޸�����ʱ�Զ������ʾ�������������ʹ��ڱ߿�
        main_window.showMaximized()
        main_window.raise_()  # �������ᵽǰ̨
        main_window.activateWindow()  # �����

        logger.debug("?? �����ڳ�ʼ����ɣ�׼����ʾ����...")

        # ?? �Ż���������ʼ���ǹؼ������������������
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, delayed_initialization)  # �����ӳ�ʱ��

        logger.info("����������ʾ�����")

        # 启动远程API服务（后台线程）
        try:
            from remote_api import start_api_server
            api_thread = start_api_server(host="0.0.0.0", port=5000, main_window=main_window)
            logger.info("✓ 远程API服务已启动，端口 5000")
        except Exception as e:
            logger.warning(f"⚠ 远程API服务启动失败: {e}")

        # ����Ӧ�ó���
        result = app.exec_()

        # ж���쳣������
        uninstall_exception_handlers()

        sys.exit(result)

    except Exception as e:
        print(f"Ӧ�ó�������ʧ��: {e}")

        # �ر���������
        if splash:
            splash.close()

        # ȷ��ж���쳣������
        try:
            uninstall_exception_handlers()
        except:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
