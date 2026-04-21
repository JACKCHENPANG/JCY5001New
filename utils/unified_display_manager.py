#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一档位结果显示管理器
按照第一次运行时的模式统一所有档位结果显示
"""

import logging
from enum import Enum
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class DisplayState(Enum):
    """显示状态枚举"""
    INITIAL = "initial"          # 初始状态：-- / 待测试
    WAITING = "waiting"          # 等待状态：-- / 待测试  
    TESTING = "testing"          # 测试中：-- / 测试中
    PASS = "pass"               # 合格：1-1 / 合格
    FAIL = "fail"               # 不合格：不合格 / 不合格

class UnifiedDisplayManager:
    """
    统一档位结果显示管理器
    确保所有地方都按照第一次运行时的标准模式显示
    """
    
    def __init__(self):
        """初始化统一显示管理器"""
        self._display_config = {
            DisplayState.INITIAL: {
                'grade_text': '--',
                'grade_object_name': 'gradeDisplay',
                'result_text': '待测试',
                'result_object_name': 'resultWaiting'
            },
            DisplayState.WAITING: {
                'grade_text': '--',
                'grade_object_name': 'gradeDisplay', 
                'result_text': '待测试',
                'result_object_name': 'resultWaiting'
            },
            DisplayState.TESTING: {
                'grade_text': '--',
                'grade_object_name': 'gradeDisplay',
                'result_text': '测试中',
                'result_object_name': 'resultTesting'
            },
            DisplayState.PASS: {
                'grade_text': '{grade}',  # 将被替换为实际档位
                'grade_object_name': 'gradeDisplay',  # 🎯 使用第一次运行时的标准ObjectName
                'result_text': '合格',
                'result_object_name': 'resultPass'
            },
            DisplayState.FAIL: {
                'grade_text': '不合格',
                'grade_object_name': 'gradeDisplay',  # 🎯 使用第一次运行时的标准ObjectName
                'result_text': '不合格', 
                'result_object_name': 'resultFail'
            }
        }
        
        logger.info("✅ 统一显示管理器初始化完成")
    
    def set_display_state(self, grade_label, result_label, state: DisplayState, 
                         rs_grade: Optional[int] = None, rct_grade: Optional[int] = None) -> bool:
        """
        设置显示状态（统一入口）
        
        Args:
            grade_label: 档位标签组件
            result_label: 结果标签组件
            state: 显示状态
            rs_grade: Rs档位（合格时需要）
            rct_grade: Rct档位（合格时需要）
            
        Returns:
            是否设置成功
        """
        try:
            if not grade_label or not result_label:
                logger.warning("⚠️ [统一显示] 标签组件为空，跳过设置")
                return False
            
            config = self._display_config.get(state)
            if not config:
                logger.error(f"❌ [统一显示] 未知的显示状态: {state}")
                return False
            
            # 设置档位标签
            grade_text = config['grade_text']
            if state == DisplayState.PASS and rs_grade is not None and rct_grade is not None:
                grade_text = f"{rs_grade}-{rct_grade}"
            
            grade_label.setText(grade_text)
            grade_label.setObjectName(config['grade_object_name'])
            
            # 设置结果标签
            result_label.setText(config['result_text'])
            result_label.setObjectName(config['result_object_name'])
            
            # 🎯 按照第一次运行时的模式应用样式
            self._apply_standard_style(grade_label)
            self._apply_standard_style(result_label)
            
            logger.debug(f"✅ [统一显示] 状态设置成功: {state.value} - 档位:'{grade_text}' 结果:'{config['result_text']}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ [统一显示] 设置显示状态失败: {e}")
            return False
    
    def _apply_standard_style(self, widget):
        """
        应用标准样式（按照第一次运行时的模式）
        """
        try:
            # 🎯 关键：清空内联样式，让ObjectName对应的CSS样式生效
            widget.setStyleSheet("")
            
            # 🎯 强制重新应用样式（确保CSS文件中的样式生效）
            if hasattr(widget, 'style'):
                style = widget.style()
                if hasattr(style, 'unpolish') and hasattr(style, 'polish'):
                    style.unpolish(widget)
                    style.polish(widget)
            
            # 🎯 强制更新显示
            widget.update()
            widget.repaint()
            
        except Exception as e:
            logger.error(f"❌ [统一显示] 应用标准样式失败: {e}")
    
    def set_initial_state(self, grade_label, result_label) -> bool:
        """设置初始状态（第一次运行时的状态）"""
        return self.set_display_state(grade_label, result_label, DisplayState.INITIAL)
    
    def set_waiting_state(self, grade_label, result_label) -> bool:
        """设置等待状态"""
        return self.set_display_state(grade_label, result_label, DisplayState.WAITING)
    
    def set_testing_state(self, grade_label, result_label) -> bool:
        """设置测试中状态"""
        return self.set_display_state(grade_label, result_label, DisplayState.TESTING)
    
    def set_pass_state(self, grade_label, result_label, rs_grade: int, rct_grade: int) -> bool:
        """设置合格状态"""
        return self.set_display_state(grade_label, result_label, DisplayState.PASS, rs_grade, rct_grade)
    
    def set_fail_state(self, grade_label, result_label) -> bool:
        """设置不合格状态"""
        return self.set_display_state(grade_label, result_label, DisplayState.FAIL)
    
    def get_display_config(self, state: DisplayState) -> Optional[dict]:
        """获取显示配置"""
        return self._display_config.get(state)

# 全局统一显示管理器实例
_unified_display_manager = None

def get_unified_display_manager() -> UnifiedDisplayManager:
    """获取统一显示管理器实例（单例模式）"""
    global _unified_display_manager
    if _unified_display_manager is None:
        _unified_display_manager = UnifiedDisplayManager()
    return _unified_display_manager

def set_channel_display_unified(grade_label, result_label, is_pass: bool, 
                               rs_grade: Optional[int] = None, rct_grade: Optional[int] = None) -> bool:
    """
    统一设置通道显示（便捷方法）
    
    Args:
        grade_label: 档位标签
        result_label: 结果标签
        is_pass: 是否合格
        rs_grade: Rs档位
        rct_grade: Rct档位
        
    Returns:
        是否设置成功
    """
    manager = get_unified_display_manager()
    
    if is_pass and rs_grade is not None and rct_grade is not None:
        return manager.set_pass_state(grade_label, result_label, rs_grade, rct_grade)
    else:
        return manager.set_fail_state(grade_label, result_label)

def reset_channel_display_unified(grade_label, result_label) -> bool:
    """
    统一重置通道显示（便捷方法）
    
    Args:
        grade_label: 档位标签
        result_label: 结果标签
        
    Returns:
        是否重置成功
    """
    manager = get_unified_display_manager()
    return manager.set_initial_state(grade_label, result_label)
