# -*- coding: utf-8 -*-
"""
全局QPainter修复模块
防止QPainter绘图状态混乱导致的闪退问题

Author: Jack
Date: 2025-01-27
"""

import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

logger = logging.getLogger(__name__)

# 全局标志，防止重复应用
_qpainter_fix_applied = False

class QPainterFix:
    """QPainter修复类"""
    
    @staticmethod
    def apply_global_fixes():
        """应用全局QPainter修复（单例模式）"""
        global _qpainter_fix_applied
        
        # 如果已经应用过，直接返回
        if _qpainter_fix_applied:
            return True
        
        try:
            # 设置Qt应用程序属性
            app = QApplication.instance()
            if app:
                # 尝试启用高DPI缩放（兼容不同PyQt版本）
                try:
                    # 使用getattr安全访问属性
                    aa_enable_highdpi = getattr(app, 'AA_EnableHighDpiScaling', None)
                    if aa_enable_highdpi is not None:
                        app.setAttribute(aa_enable_highdpi, True)
                        logger.debug("✅ 高DPI缩放已启用")
                    else:
                        logger.debug("ℹ️ 当前PyQt版本不支持AA_EnableHighDpiScaling")
                except Exception as e:
                    logger.debug(f"ℹ️ 高DPI缩放设置跳过: {e}")

                # 设置更新策略（兼容性检查）
                try:
                    # 使用getattr安全访问属性
                    aa_dont_create_native = getattr(app, 'AA_DontCreateNativeWidgetSiblings', None)
                    if aa_dont_create_native is not None:
                        app.setAttribute(aa_dont_create_native, True)
                        logger.debug("✅ 原生组件策略已设置")
                    else:
                        logger.debug("ℹ️ 当前PyQt版本不支持AA_DontCreateNativeWidgetSiblings")
                except Exception as e:
                    logger.debug(f"ℹ️ 原生组件策略设置跳过: {e}")

                # 标记为已应用
                _qpainter_fix_applied = True
                logger.info("✅ 全局QPainter修复已应用")
                return True
            else:
                logger.warning("⚠️ 未找到QApplication实例")
                return False

        except Exception as e:
            logger.error(f"❌ 应用全局QPainter修复失败: {e}")
            return False
    
    @staticmethod
    def safe_update_widget(widget, update_func, *args, **kwargs):
        """安全更新组件"""
        try:
            if widget and hasattr(widget, 'setUpdatesEnabled'):
                widget.setUpdatesEnabled(False)
                try:
                    result = update_func(*args, **kwargs)
                    return result
                finally:
                    widget.setUpdatesEnabled(True)
            else:
                return update_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"安全更新组件失败: {e}")
            if widget and hasattr(widget, 'setUpdatesEnabled'):
                widget.setUpdatesEnabled(True)
            raise

# 自动应用修复（只在首次导入时执行）
def _auto_apply_fix():
    """自动应用修复（防止重复调用）"""
    global _qpainter_fix_applied
    if not _qpainter_fix_applied:
        QPainterFix.apply_global_fixes()

_auto_apply_fix()

def is_windows_7():
    """检查是否为Windows 7系统"""
    try:
        import platform
        return platform.system() == 'Windows' and platform.release() == '7'
    except:
        return False

def apply_win7_compatible_settings():
    """应用Windows 7兼容设置"""
    if not is_windows_7():
        return
    
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            # Windows 7兼容的设置
            app.setAttribute(app.AA_DisableWindowContextHelpButton, True)
            logger.debug("✅ Windows 7兼容设置已应用")
    except Exception as e:
        logger.debug(f"ℹ️ Windows 7兼容设置跳过: {e}")
