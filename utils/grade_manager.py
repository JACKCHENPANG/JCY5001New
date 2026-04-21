#!/usr/bin/env python3
"""
统一的档位管理器
负责所有档位相关的计算、存储、获取和显示操作
"""

import logging
from typing import Tuple, Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class GradeManager(QObject):
    """
    统一的档位管理器
    
    职责：
    1. 统一档位数据获取（只从数据库）
    2. 统一UI显示更新
    3. 统一档位计算接口
    4. 消除重复的档位处理逻辑
    """
    
    # 信号定义
    grade_updated = pyqtSignal(int, int, int, bool)  # channel, rs_grade, rct_grade, is_pass
    
    def __init__(self, config_manager=None):
        """
        初始化档位管理器
        
        Args:
            config_manager: 配置管理器（可选）
        """
        super().__init__()
        
        self.config_manager = config_manager
        self._database_manager = None
        self._test_result_manager = None
        
        logger.debug("✅ 统一档位管理器初始化完成")
    
    @property
    def database_manager(self):
        """获取数据库管理器（懒加载）"""
        if self._database_manager is None:
            try:
                from data.database_manager import DatabaseManager
                self._database_manager = DatabaseManager()
                logger.debug("✅ 档位管理器：数据库管理器初始化成功")
            except Exception as e:
                logger.error(f"❌ 档位管理器：数据库管理器初始化失败: {e}")
        return self._database_manager
    
    @property
    def test_result_manager(self):
        """获取测试结果管理器（懒加载）"""
        if self._test_result_manager is None and self.config_manager:
            try:
                from backend.test_result_manager import TestResultManager
                self._test_result_manager = TestResultManager(self.config_manager, self.database_manager)
                logger.debug("✅ 档位管理器：测试结果管理器初始化成功")
            except Exception as e:
                logger.error(f"❌ 档位管理器：测试结果管理器初始化失败: {e}")
        return self._test_result_manager
    
    def get_channel_grade_from_database(self, channel_number: int) -> Tuple[Optional[int], Optional[int], Optional[bool]]:
        """
        从数据库获取指定通道的最新档位数据
        
        Args:
            channel_number: 通道号
            
        Returns:
            (rs_grade, rct_grade, is_pass) 或 (None, None, None) 如果没有数据
        """
        try:
            if not self.database_manager:
                logger.error(f"❌ [档位管理器] 通道{channel_number} 数据库管理器未初始化")
                return None, None, None
            
            # 获取该通道的最新测试结果
            test_results = self.database_manager.get_test_results(
                channel_number=channel_number,
                limit=1
            )
            
            if test_results and len(test_results) > 0:
                result = test_results[0]
                rs_grade = result.get('rs_grade')
                rct_grade = result.get('rct_grade')
                is_pass = result.get('is_pass', False)
                
                logger.debug(f"🔍 [档位管理器] 通道{channel_number} 从数据库获取档位: Rs={rs_grade}, Rct={rct_grade}, 合格={is_pass}")
                return rs_grade, rct_grade, is_pass
            else:
                logger.debug(f"🔍 [档位管理器] 通道{channel_number} 数据库中无测试结果")
                return None, None, None
                
        except Exception as e:
            logger.error(f"❌ [档位管理器] 通道{channel_number} 从数据库获取档位失败: {e}")
            return None, None, None
    
    def calculate_grades(self, rs_value: float, rct_value: float) -> Tuple[int, int]:
        """
        计算档位（统一入口）
        
        Args:
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)
            
        Returns:
            (rs_grade, rct_grade) 档位编号
        """
        try:
            if self.test_result_manager:
                return self.test_result_manager.calculate_grades(rs_value, rct_value)
            else:
                # 备用计算逻辑（如果测试结果管理器不可用）
                return self._fallback_calculate_grades(rs_value, rct_value)
                
        except Exception as e:
            logger.error(f"❌ [档位管理器] 计算档位失败: Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ, 错误: {e}")
            return 0, 0
    
    def _fallback_calculate_grades(self, rs_value: float, rct_value: float) -> Tuple[int, int]:
        """
        备用档位计算逻辑
        
        Args:
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)
            
        Returns:
            (rs_grade, rct_grade) 档位编号
        """
        try:
            # 默认档位边界（如果配置不可用）
            rs_boundaries = [5.0, 10.0]  # mΩ
            rct_boundaries = [8.0, 15.0]  # mΩ
            
            # 从配置获取边界值
            if self.config_manager:
                rs_boundaries = self.config_manager.get('grade_settings.rs_boundaries', rs_boundaries)
                rct_boundaries = self.config_manager.get('grade_settings.rct_boundaries', rct_boundaries)
            
            # 计算Rs档位
            if rs_value <= rs_boundaries[0]:
                rs_grade = 1
            elif rs_value <= rs_boundaries[1]:
                rs_grade = 2
            else:
                rs_grade = 3
            
            # 计算Rct档位
            if rct_value <= rct_boundaries[0]:
                rct_grade = 1
            elif rct_value <= rct_boundaries[1]:
                rct_grade = 2
            else:
                rct_grade = 3
            
            logger.debug(f"🔍 [档位管理器] 备用计算: Rs={rs_value:.3f}mΩ→{rs_grade}档, Rct={rct_value:.3f}mΩ→{rct_grade}档")
            return rs_grade, rct_grade
            
        except Exception as e:
            logger.error(f"❌ [档位管理器] 备用计算失败: {e}")
            return 0, 0
    
    def update_channel_display(self, channel_number: int, channel_widget=None) -> bool:
        """
        更新指定通道的档位显示（统一UI更新入口）
        
        Args:
            channel_number: 通道号
            channel_widget: 通道组件（可选，如果不提供会自动查找）
            
        Returns:
            是否更新成功
        """
        try:
            # 从数据库获取最新档位数据
            rs_grade, rct_grade, is_pass = self.get_channel_grade_from_database(channel_number)
            
            if rs_grade is None or rct_grade is None:
                logger.warning(f"⚠️ [档位管理器] 通道{channel_number} 无档位数据，跳过UI更新")
                return False
            
            # 如果没有提供通道组件，尝试查找
            if channel_widget is None:
                channel_widget = self._find_channel_widget(channel_number)
            
            if channel_widget is None:
                logger.warning(f"⚠️ [档位管理器] 通道{channel_number} 未找到通道组件")
                return False
            
            # 更新UI显示
            success = self._update_widget_display(channel_widget, rs_grade, rct_grade, is_pass)
            
            if success:
                # 发送更新信号
                self.grade_updated.emit(channel_number, rs_grade, rct_grade, is_pass)
                logger.info(f"✅ [档位管理器] 通道{channel_number} UI显示已更新: Rs={rs_grade}, Rct={rct_grade}, 合格={is_pass}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ [档位管理器] 通道{channel_number} 更新UI显示失败: {e}")
            return False
    
    def _find_channel_widget(self, channel_number: int):
        """查找通道组件"""
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            
            if app is None:
                return None
            
            # 查找主窗口
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'ui_component_manager'):
                    ui_manager = getattr(widget, 'ui_component_manager', None)
                    if ui_manager:
                        channels_container = ui_manager.get_component('channels_container')
                        if channels_container and hasattr(channels_container, 'channels'):
                            if 1 <= channel_number <= len(channels_container.channels):
                                return channels_container.channels[channel_number - 1]
            
            return None
            
        except Exception as e:
            logger.error(f"❌ [档位管理器] 查找通道{channel_number}组件失败: {e}")
            return None
    
    def _update_widget_display(self, channel_widget, rs_grade: int, rct_grade: int, is_pass: bool) -> bool:
        """更新组件显示（使用统一显示管理器）"""
        try:
            if not hasattr(channel_widget, 'grade_label') or not hasattr(channel_widget, 'result_label'):
                logger.warning(f"⚠️ [档位管理器] 通道组件缺少必要的UI元素")
                return False

            # 🎯 使用统一显示管理器，按照第一次运行时的标准模式
            from .unified_display_manager import set_channel_display_unified

            success = set_channel_display_unified(
                channel_widget.grade_label,
                channel_widget.result_label,
                is_pass,
                rs_grade,
                rct_grade
            )

            if success:
                logger.debug(f"✅ [档位管理器] 使用统一显示管理器更新成功")
            else:
                logger.warning(f"⚠️ [档位管理器] 统一显示管理器更新失败")

            return success

        except Exception as e:
            logger.error(f"❌ [档位管理器] 更新组件显示失败: {e}")
            return False

    def _apply_unified_style(self, widget):
        """应用统一样式（修复字体一致性）"""
        try:
            # 🎯 修复：清空内联样式，让ObjectName样式生效
            widget.setStyleSheet("")

            # 🎯 修复：强制重新应用样式，确保CSS文件中的样式生效
            if hasattr(widget, 'style'):
                style = widget.style()
                if hasattr(style, 'unpolish') and hasattr(style, 'polish'):
                    style.unpolish(widget)
                    style.polish(widget)

            # 🎯 修复：强制刷新父组件样式，确保继承正确
            parent = widget.parent()
            if parent and hasattr(parent, 'style'):
                parent_style = parent.style()
                if hasattr(parent_style, 'polish'):
                    parent_style.polish(widget)

            # 🎯 修复：强制更新显示
            widget.update()
            widget.repaint()  # 添加repaint确保立即重绘

            logger.debug(f"🎯 [样式修复] 组件样式已刷新: ObjectName='{widget.objectName()}'")

        except Exception as e:
            logger.error(f"❌ [档位管理器] 应用统一样式失败: {e}")
    
    def refresh_all_channels(self) -> int:
        """
        刷新所有通道的档位显示
        
        Returns:
            成功刷新的通道数量
        """
        try:
            success_count = 0
            
            for channel_number in range(1, 9):
                if self.update_channel_display(channel_number):
                    success_count += 1
            
            logger.info(f"✅ [档位管理器] 批量刷新完成，成功刷新{success_count}/8个通道")
            return success_count
            
        except Exception as e:
            logger.error(f"❌ [档位管理器] 批量刷新失败: {e}")
            return 0
    
    def get_print_grade_data(self, channel_number: int) -> Dict[str, Any]:
        """
        获取打印用的档位数据（统一打印数据入口）
        
        Args:
            channel_number: 通道号
            
        Returns:
            包含档位信息的字典
        """
        try:
            rs_grade, rct_grade, is_pass = self.get_channel_grade_from_database(channel_number)
            
            return {
                'rs_grade': rs_grade,
                'rct_grade': rct_grade,
                'is_pass': is_pass,
                'grade_text': f"{rs_grade}-{rct_grade}" if (rs_grade is not None and rct_grade is not None and is_pass) else "不合格"
            }
            
        except Exception as e:
            logger.error(f"❌ [档位管理器] 通道{channel_number} 获取打印档位数据失败: {e}")
            return {
                'rs_grade': None,
                'rct_grade': None,
                'is_pass': False,
                'grade_text': "错误"
            }


# 全局档位管理器实例
_grade_manager_instance = None


def get_grade_manager(config_manager=None) -> GradeManager:
    """
    获取全局档位管理器实例（单例模式）
    
    Args:
        config_manager: 配置管理器（首次调用时需要）
        
    Returns:
        档位管理器实例
    """
    global _grade_manager_instance
    
    if _grade_manager_instance is None:
        _grade_manager_instance = GradeManager(config_manager)
        logger.debug("✅ 创建全局档位管理器实例")
    
    return _grade_manager_instance
