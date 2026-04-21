# -*- coding: utf-8 -*-
"""
全局异常处理器
防止未捕获的异常导致程序闪退

Author: Jack
Date: 2025-01-27
"""

import sys
import logging
from PyQt5.QtCore import qInstallMessageHandler, QtMsgType

logger = logging.getLogger(__name__)


def qt_message_handler(msg_type, context, message):
    """Qt消息处理器"""
    try:
        if msg_type == QtMsgType.QtDebugMsg:
            logger.debug(f"Qt Debug: {message}")
        elif msg_type == QtMsgType.QtWarningMsg:
            # 过滤掉已知的无害警告
            if any(warning in message for warning in [
                "Recursive repaint detected",
                "QBackingStore::endPaint",
                "QObject::startTimer",
                "sipPyTypeDict() is deprecated"
            ]):
                logger.debug(f"Qt Warning (filtered): {message}")
            else:
                logger.warning(f"Qt Warning: {message}")
        elif msg_type == QtMsgType.QtCriticalMsg:
            logger.error(f"Qt Critical: {message}")
        elif msg_type == QtMsgType.QtFatalMsg:
            logger.critical(f"Qt Fatal: {message}")
    except Exception as e:
        # 避免在消息处理器中产生异常
        print(f"消息处理器异常: {e}")


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """全局异常处理器"""
    try:
        if issubclass(exc_type, KeyboardInterrupt):
            # 允许Ctrl+C正常退出
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # 记录异常信息
        logger.critical("未捕获的异常:", exc_info=(exc_type, exc_value, exc_traceback))

        # 尝试优雅地关闭应用程序
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                logger.info("尝试优雅地关闭应用程序...")
                app.quit()
        except Exception as e:
            logger.error(f"关闭应用程序时异常: {e}")

    except Exception as e:
        # 最后的保护措施
        print(f"全局异常处理器异常: {e}")
        sys.__excepthook__(exc_type, exc_value, exc_traceback)


def install_exception_handlers():
    """安装异常处理器"""
    try:
        # 安装全局异常处理器
        sys.excepthook = global_exception_handler
        
        # 安装Qt消息处理器
        qInstallMessageHandler(qt_message_handler)
        
        logger.info("✅ 全局异常处理器安装完成")
        
    except Exception as e:
        logger.error(f"❌ 安装异常处理器失败: {e}")


def uninstall_exception_handlers():
    """卸载异常处理器"""
    try:
        # 恢复默认异常处理器
        sys.excepthook = sys.__excepthook__
        
        # 恢复默认Qt消息处理器
        qInstallMessageHandler(None)
        
        logger.info("✅ 异常处理器已卸载")
        
    except Exception as e:
        logger.error(f"❌ 卸载异常处理器失败: {e}")
