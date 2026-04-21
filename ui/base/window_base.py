"""
窗口基础类 - 提取UI初始化公共逻辑
用于减少主窗口类中的重复代码
"""

import os
import logging
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

logger = logging.getLogger(__name__)


class WindowBase(QMainWindow):
    """窗口基础类 - 提供通用的窗口初始化功能"""
    
    def __init__(self, config_manager, parent=None):
        """
        初始化窗口基础类
        
        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)
        self.config_manager = config_manager
        
        # 初始化基础属性
        self._init_base_properties()
    
    def _init_base_properties(self):
        """初始化基础属性"""
        # 设置窗口基本属性
        self._setup_window_properties()
        
        # 设置窗口图标
        self._setup_window_icon()
        
        # 应用基础样式
        self._apply_base_styles()
    
    def _setup_window_properties(self):
        """设置窗口基本属性"""
        try:
            # 设置窗口标题，包含版本号
            app_name = self.config_manager.get('app.name', 'JCY5001AS鲸测云8路EIS阻抗筛选仪')
            app_version = self.config_manager.get('app.version', 'V0.92.42')
            title = f"{app_name} {app_version}"
            self.setWindowTitle(title)
            
            # 设置最小尺寸
            min_size = self.config_manager.get('ui.min_window_size', [1200, 800])
            self.setMinimumSize(min_size[0], min_size[1])
            
            # 设置默认尺寸
            default_size = self.config_manager.get('ui.default_window_size', [1280, 800])
            self.resize(default_size[0], default_size[1])
            
            logger.debug(f"窗口属性设置完成: {app_name}, 尺寸: {default_size}")
            
        except Exception as e:
            logger.error(f"设置窗口属性失败: {e}")
    
    def _setup_window_icon(self):
        """设置窗口图标"""
        try:
            # 获取图标路径
            icon_path = self.config_manager.get('ui.icon_path', 
                                               os.path.join("resources", "icons", "app_icon.ico"))
            
            # 设置图标
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                logger.debug(f"窗口图标设置成功: {icon_path}")
            else:
                logger.warning(f"窗口图标文件不存在: {icon_path}")
                
        except Exception as e:
            logger.error(f"设置窗口图标失败: {e}")
    
    def _apply_base_styles(self):
        """应用基础样式"""
        try:
            # 获取样式文件路径
            style_file = self.config_manager.get('ui.style_file', 
                                                os.path.join("resources", "styles", "main_style.qss"))
            
            # 加载样式文件
            if os.path.exists(style_file):
                with open(style_file, 'r', encoding='utf-8') as f:
                    style_content = f.read()
                    self.setStyleSheet(style_content)
                    logger.debug(f"样式文件加载成功: {style_file}")
            else:
                logger.warning(f"样式文件不存在: {style_file}")
                
        except Exception as e:
            logger.error(f"应用样式失败: {e}")
    
    def load_window_settings(self):
        """加载窗口设置"""
        try:
            # 加载窗口大小
            size = self.config_manager.get('ui.window_size', [1280, 800])
            self.resize(size[0], size[1])
            
            # 加载窗口位置
            pos = self.config_manager.get('ui.window_position', [100, 100])
            self.move(pos[0], pos[1])
            
            # 加载窗口状态
            maximized = self.config_manager.get('ui.window_maximized', False)
            if maximized:
                self.showMaximized()
            
            logger.debug("窗口设置加载完成")
            
        except Exception as e:
            logger.warning(f"窗口设置加载失败: {e}")
    
    def save_window_settings(self):
        """保存窗口设置"""
        try:
            # 保存窗口大小
            if not self.isMaximized():
                size = self.size()
                self.config_manager.set('ui.window_size', [size.width(), size.height()])
                
                # 保存窗口位置
                pos = self.pos()
                self.config_manager.set('ui.window_position', [pos.x(), pos.y()])
            
            # 保存窗口状态
            self.config_manager.set('ui.window_maximized', self.isMaximized())
            
            logger.debug("窗口设置保存完成")
            
        except Exception as e:
            logger.warning(f"窗口设置保存失败: {e}")
    
    def show_error_message(self, title: str, message: str):
        """显示错误消息"""
        try:
            QMessageBox.critical(self, title, message)
        except Exception as e:
            logger.error(f"显示错误消息失败: {e}")
    
    def show_info_message(self, title: str, message: str):
        """显示信息消息"""
        try:
            QMessageBox.information(self, title, message)
        except Exception as e:
            logger.error(f"显示信息消息失败: {e}")
    
    def show_warning_message(self, title: str, message: str):
        """显示警告消息"""
        try:
            QMessageBox.warning(self, title, message)
        except Exception as e:
            logger.error(f"显示警告消息失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 保存窗口设置
            self.save_window_settings()
            
            # 保存配置
            if hasattr(self.config_manager, 'save_config'):
                self.config_manager.save_config()
            
            logger.info("窗口正在关闭")
            event.accept()
            
        except Exception as e:
            logger.error(f"窗口关闭处理失败: {e}")
            event.accept()  # 即使出错也要关闭窗口


class ConfigValidatorMixin:
    """配置验证混入类 - 提供通用的配置验证功能"""
    
    @staticmethod
    def validate_numeric_range(value: Any, min_val: float, max_val: float, 
                              default: float, name: str) -> float:
        """
        验证数值范围
        
        Args:
            value: 要验证的值
            min_val: 最小值
            max_val: 最大值
            default: 默认值
            name: 参数名称
            
        Returns:
            验证后的数值
        """
        try:
            num_val = float(value)
            if min_val <= num_val <= max_val:
                return num_val
            else:
                logger.warning(f"{name}超出范围[{min_val}, {max_val}]: {num_val}，使用默认值: {default}")
                return default
        except (ValueError, TypeError):
            logger.warning(f"无效的{name}: {value}，使用默认值: {default}")
            return default
    
    @staticmethod
    def validate_choice(value: Any, choices: list, default: Any, name: str) -> Any:
        """
        验证选择项
        
        Args:
            value: 要验证的值
            choices: 有效选择列表
            default: 默认值
            name: 参数名称
            
        Returns:
            验证后的值
        """
        if value in choices:
            return value
        else:
            logger.warning(f"无效的{name}: {value}，有效选择: {choices}，使用默认值: {default}")
            return default
    
    @staticmethod
    def validate_list(value: Any, item_validator=None, default: list = None, name: str = "列表") -> list:
        """
        验证列表
        
        Args:
            value: 要验证的值
            item_validator: 列表项验证函数
            default: 默认值
            name: 参数名称
            
        Returns:
            验证后的列表
        """
        if default is None:
            default = []
            
        if not isinstance(value, list):
            logger.warning(f"无效的{name}: {value}，使用默认值: {default}")
            return default
        
        if item_validator:
            validated_items = []
            for item in value:
                try:
                    validated_item = item_validator(item)
                    validated_items.append(validated_item)
                except Exception as e:
                    logger.warning(f"{name}中的无效项: {item}，错误: {e}")
            return validated_items
        
        return value


class ErrorHandlerMixin:
    """错误处理混入类 - 提供通用的错误处理功能"""
    
    def safe_execute(self, func, *args, error_msg: str = "操作失败", **kwargs):
        """
        安全执行函数
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            error_msg: 错误消息
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果或None
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{error_msg}: {e}")
            return None
    
    def safe_get_attribute(self, obj, attr_name: str, default=None):
        """
        安全获取对象属性
        
        Args:
            obj: 对象
            attr_name: 属性名
            default: 默认值
            
        Returns:
            属性值或默认值
        """
        try:
            return getattr(obj, attr_name, default)
        except Exception as e:
            logger.error(f"获取属性 {attr_name} 失败: {e}")
            return default
