#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图标管理器
统一管理应用程序的图标资源

Author: Jack
Date: 2025-01-28
"""

import os
import logging
from pathlib import Path
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize

logger = logging.getLogger(__name__)


class IconManager:
    """图标管理器 - 统一管理应用程序图标"""
    
    _instance = None
    _icons_cache = {}
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化图标管理器"""
        if self._initialized:
            return
            
        self.project_root = Path(__file__).parent.parent
        self.icons_dir = self.project_root / "resources" / "icons"
        self.images_dir = self.project_root / "resources" / "images"
        
        # 确保目录存在
        self.icons_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        self._initialized = True
        logger.debug("图标管理器初始化完成")
    
    def get_app_icon(self) -> QIcon:
        """
        获取应用程序主图标
        
        Returns:
            QIcon: 应用程序图标
        """
        if "app_icon" in self._icons_cache:
            return self._icons_cache["app_icon"]
        
        # 图标文件优先级列表
        icon_files = [
            self.icons_dir / "app_icon.ico",
            self.icons_dir / "app_icon.png", 
            self.images_dir / "logo.png",
            self.images_dir / "logo.ico"
        ]
        
        for icon_file in icon_files:
            if icon_file.exists():
                try:
                    icon = QIcon(str(icon_file))
                    if not icon.isNull():
                        self._icons_cache["app_icon"] = icon
                        logger.info(f"应用图标加载成功: {icon_file}")
                        return icon
                except Exception as e:
                    logger.warning(f"加载图标失败 {icon_file}: {e}")
        
        # 如果没有找到图标文件，创建默认图标
        default_icon = self._create_default_icon()
        self._icons_cache["app_icon"] = default_icon
        logger.info("使用默认应用图标")
        return default_icon
    
    def get_logo_pixmap(self, size: QSize = QSize(120, 120)) -> QPixmap:
        """
        获取Logo图片
        
        Args:
            size: 图片尺寸
            
        Returns:
            QPixmap: Logo图片
        """
        cache_key = f"logo_{size.width()}x{size.height()}"
        if cache_key in self._icons_cache:
            return self._icons_cache[cache_key]
        
        # Logo文件优先级列表
        logo_files = [
            self.images_dir / "logo.png",
            self.images_dir / "logo.jpg",
            self.images_dir / "logo.jpeg",
            self.icons_dir / "app_icon.png"
        ]
        
        for logo_file in logo_files:
            if logo_file.exists():
                try:
                    pixmap = QPixmap(str(logo_file))
                    if not pixmap.isNull():
                        # 缩放到指定尺寸
                        scaled_pixmap = pixmap.scaled(
                            size, 
                            aspectRatioMode=1,  # Qt.KeepAspectRatio
                            transformMode=1     # Qt.SmoothTransformation
                        )
                        self._icons_cache[cache_key] = scaled_pixmap
                        logger.info(f"Logo图片加载成功: {logo_file}, 尺寸: {size.width()}x{size.height()}")
                        return scaled_pixmap
                except Exception as e:
                    logger.warning(f"加载Logo失败 {logo_file}: {e}")
        
        # 如果没有找到Logo文件，创建默认Logo
        default_pixmap = self._create_default_logo(size)
        self._icons_cache[cache_key] = default_pixmap
        logger.info(f"使用默认Logo，尺寸: {size.width()}x{size.height()}")
        return default_pixmap
    
    def _create_default_icon(self) -> QIcon:
        """创建默认应用图标"""
        try:
            # 创建一个简单的默认图标
            pixmap = QPixmap(64, 64)
            pixmap.fill()  # 填充为白色
            
            # 这里可以添加绘制默认图标的代码
            # 例如绘制一个简单的电池图标
            
            return QIcon(pixmap)
        except Exception as e:
            logger.error(f"创建默认图标失败: {e}")
            return QIcon()
    
    def _create_default_logo(self, size: QSize) -> QPixmap:
        """创建默认Logo"""
        try:
            # 创建一个简单的默认Logo
            pixmap = QPixmap(size)
            pixmap.fill()  # 填充为白色
            
            # 这里可以添加绘制默认Logo的代码
            # 例如绘制公司名称或产品名称
            
            return pixmap
        except Exception as e:
            logger.error(f"创建默认Logo失败: {e}")
            return QPixmap(size)
    
    def set_window_icon(self, window, icon_name: str = "app_icon"):
        """
        为窗口设置图标
        
        Args:
            window: 要设置图标的窗口
            icon_name: 图标名称
        """
        try:
            if icon_name == "app_icon":
                icon = self.get_app_icon()
            else:
                # 可以扩展支持其他图标
                icon = self.get_app_icon()
            
            window.setWindowIcon(icon)
            logger.debug(f"窗口图标设置成功: {window.__class__.__name__}")
            
        except Exception as e:
            logger.error(f"设置窗口图标失败: {e}")
    
    def save_new_icon(self, source_path: str, icon_type: str = "app_icon") -> bool:
        """
        保存新的图标文件
        
        Args:
            source_path: 源文件路径
            icon_type: 图标类型 ("app_icon" 或 "logo")
            
        Returns:
            bool: 是否保存成功
        """
        try:
            source_file = Path(source_path)
            if not source_file.exists():
                logger.error(f"源文件不存在: {source_path}")
                return False
            
            if icon_type == "app_icon":
                # 保存应用图标
                if source_file.suffix.lower() == '.ico':
                    target_file = self.icons_dir / "app_icon.ico"
                else:
                    target_file = self.icons_dir / "app_icon.png"
            elif icon_type == "logo":
                # 保存Logo
                target_file = self.images_dir / f"logo{source_file.suffix}"
            else:
                logger.error(f"不支持的图标类型: {icon_type}")
                return False
            
            # 复制文件
            import shutil
            shutil.copy2(source_file, target_file)
            
            # 清除缓存
            self._clear_cache()
            
            logger.info(f"图标文件保存成功: {target_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存图标文件失败: {e}")
            return False
    
    def _clear_cache(self):
        """清除图标缓存"""
        self._icons_cache.clear()
        logger.debug("图标缓存已清除")
    
    def get_icon_info(self) -> dict:
        """
        获取当前图标信息
        
        Returns:
            dict: 图标信息
        """
        info = {
            "app_icon_files": [],
            "logo_files": [],
            "icons_dir": str(self.icons_dir),
            "images_dir": str(self.images_dir)
        }
        
        # 检查应用图标文件
        app_icon_patterns = ["app_icon.ico", "app_icon.png"]
        for pattern in app_icon_patterns:
            file_path = self.icons_dir / pattern
            if file_path.exists():
                info["app_icon_files"].append(str(file_path))
        
        # 检查Logo文件
        logo_patterns = ["logo.png", "logo.jpg", "logo.jpeg", "logo.ico"]
        for pattern in logo_patterns:
            file_path = self.images_dir / pattern
            if file_path.exists():
                info["logo_files"].append(str(file_path))
        
        return info


# 全局图标管理器实例
icon_manager = IconManager()


def get_app_icon() -> QIcon:
    """获取应用程序图标的便捷函数"""
    return icon_manager.get_app_icon()


def get_logo_pixmap(size: QSize = QSize(120, 120)) -> QPixmap:
    """获取Logo图片的便捷函数"""
    return icon_manager.get_logo_pixmap(size)


def set_window_icon(window, icon_name: str = "app_icon"):
    """设置窗口图标的便捷函数"""
    icon_manager.set_window_icon(window, icon_name)
