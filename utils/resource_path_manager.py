# -*- coding: utf-8 -*-
"""
资源路径管理器
解决打包后资源文件路径问题

Author: Jack
Date: 2025-01-27
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ResourcePathManager:
    """资源路径管理器 - 统一处理资源文件路径"""
    
    _instance = None
    _base_path = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化资源路径管理器"""
        if self._initialized:
            return
            
        self._determine_base_path()
        self._initialized = True
        logger.debug(f"资源路径管理器初始化完成，基础路径: {self._base_path}")
    
    def _determine_base_path(self):
        """确定基础路径"""
        try:
            # 1. PyInstaller 打包后的路径
            if hasattr(sys, '_MEIPASS'):
                self._base_path = sys._MEIPASS
                logger.info(f"检测到 PyInstaller 环境，基础路径: {self._base_path}")
                return
            
            # 2. Nuitka 打包后的路径
            if hasattr(sys, 'frozen'):
                self._base_path = os.path.dirname(sys.executable)
                logger.info(f"检测到 Nuitka 环境，基础路径: {self._base_path}")
                return
            
            # 3. 开发环境路径
            # 从当前文件向上查找项目根目录（包含main.py的目录）
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent  # utils的上级目录
            
            # 验证是否为项目根目录
            if (project_root / "main.py").exists():
                self._base_path = str(project_root)
                logger.info(f"检测到开发环境，基础路径: {self._base_path}")
                return
            
            # 4. 备用方案：使用当前工作目录
            self._base_path = os.getcwd()
            logger.warning(f"使用备用基础路径: {self._base_path}")
            
        except Exception as e:
            logger.error(f"确定基础路径失败: {e}")
            self._base_path = os.getcwd()
    
    def get_resource_path(self, relative_path: str) -> str:
        """
        获取资源文件的绝对路径
        
        Args:
            relative_path: 相对路径（相对于项目根目录）
            
        Returns:
            绝对路径
        """
        try:
            # 构建完整路径
            full_path = os.path.join(self._base_path, relative_path)
            
            # 如果文件存在，直接返回
            if os.path.exists(full_path):
                return full_path
            
            # 尝试其他可能的路径
            alternative_paths = [
                os.path.join(os.getcwd(), relative_path),  # 当前工作目录
                os.path.join(os.path.dirname(sys.executable), relative_path) if hasattr(sys, 'frozen') else None,  # 可执行文件目录
                relative_path  # 原始相对路径
            ]
            
            for alt_path in alternative_paths:
                if alt_path and os.path.exists(alt_path):
                    logger.debug(f"资源文件在备用路径找到: {relative_path} -> {alt_path}")
                    return alt_path
            
            # 如果都找不到，返回基于基础路径的完整路径
            logger.warning(f"资源文件不存在: {relative_path}")
            return full_path
            
        except Exception as e:
            logger.error(f"获取资源路径失败: {relative_path}, {e}")
            return relative_path
    
    def get_config_path(self, config_file: str = "app_config.json") -> str:
        """
        获取配置文件路径
        
        Args:
            config_file: 配置文件名
            
        Returns:
            配置文件绝对路径
        """
        return self.get_resource_path(f"config/{config_file}")
    
    def get_icon_path(self, icon_file: str) -> str:
        """
        获取图标文件路径
        
        Args:
            icon_file: 图标文件名
            
        Returns:
            图标文件绝对路径
        """
        return self.get_resource_path(f"resources/icons/{icon_file}")
    
    def get_style_path(self, style_file: str = "main_style.qss") -> str:
        """
        获取样式文件路径
        
        Args:
            style_file: 样式文件名
            
        Returns:
            样式文件绝对路径
        """
        return self.get_resource_path(f"resources/styles/{style_file}")
    
    def get_algorithm_path(self, algorithm_file: str) -> str:
        """
        获取算法文件路径

        Args:
            algorithm_file: 算法文件名

        Returns:
            算法文件绝对路径
        """
        # 修复使用英文目录名，兼容打包环境
        return self.get_resource_path(f"algorithms/{algorithm_file}")
    
    def ensure_directory_exists(self, relative_path: str) -> str:
        """
        确保目录存在，如果不存在则创建
        
        Args:
            relative_path: 相对目录路径
            
        Returns:
            目录绝对路径
        """
        try:
            dir_path = self.get_resource_path(relative_path)
            os.makedirs(dir_path, exist_ok=True)
            return dir_path
        except Exception as e:
            logger.error(f"创建目录失败: {relative_path}, {e}")
            return self.get_resource_path(relative_path)
    
    def list_resource_files(self, relative_dir: str, pattern: str = "*") -> list:
        """
        列出资源目录中的文件
        
        Args:
            relative_dir: 相对目录路径
            pattern: 文件匹配模式
            
        Returns:
            文件路径列表
        """
        try:
            dir_path = Path(self.get_resource_path(relative_dir))
            if dir_path.exists() and dir_path.is_dir():
                return [str(f) for f in dir_path.glob(pattern) if f.is_file()]
            else:
                logger.warning(f"资源目录不存在: {relative_dir}")
                return []
        except Exception as e:
            logger.error(f"列出资源文件失败: {relative_dir}, {e}")
            return []
    
    @property
    def base_path(self) -> str:
        """获取基础路径"""
        return self._base_path
    
    def is_packaged(self) -> bool:
        """检查是否为打包后的环境"""
        return hasattr(sys, '_MEIPASS') or hasattr(sys, 'frozen')


# 全局实例
_resource_manager = ResourcePathManager()


def get_resource_path(relative_path: str) -> str:
    """
    获取资源文件的绝对路径（便捷函数）
    
    Args:
        relative_path: 相对路径
        
    Returns:
        绝对路径
    """
    return _resource_manager.get_resource_path(relative_path)


def get_config_path(config_file: str = "app_config.json") -> str:
    """获取配置文件路径（便捷函数）"""
    return _resource_manager.get_config_path(config_file)


def get_icon_path(icon_file: str) -> str:
    """获取图标文件路径（便捷函数）"""
    return _resource_manager.get_icon_path(icon_file)


def get_style_path(style_file: str = "main_style.qss") -> str:
    """获取样式文件路径（便捷函数）"""
    return _resource_manager.get_style_path(style_file)


def is_packaged() -> bool:
    """检查是否为打包后的环境（便捷函数）"""
    return _resource_manager.is_packaged()


def ensure_directory_exists(relative_path: str) -> str:
    """确保目录存在（便捷函数）"""
    return _resource_manager.ensure_directory_exists(relative_path)
