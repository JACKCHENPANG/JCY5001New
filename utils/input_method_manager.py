#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输入法管理器
自动切换系统输入法，防止在扫码时中文输入法干扰

Author: Jack
Date: 2025-08-16
"""

import logging
import ctypes
import ctypes.wintypes
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class InputMethodManager(QObject):
    """输入法管理器"""
    
    # 信号定义
    input_method_changed = pyqtSignal(str)  # 输入法切换信号 (method_name)
    
    def __init__(self, parent=None):
        """
        初始化输入法管理器
        
        Args:
            parent: 父对象
        """
        super().__init__(parent)
        
        # Windows API 常量
        self.HKL_NEXT = 1
        self.HKL_PREV = 0
        
        # 常用输入法标识
        self.INPUT_METHODS = {
            '00000409': 'English (US)',  # 英文输入法
            '00000804': 'Chinese (Simplified)',  # 中文简体输入法
            'E0010804': 'Microsoft Pinyin',  # 微软拼音输入法
            'E0200804': 'Sogou Pinyin',  # 搜狗拼音输入法
            'E0040804': 'QQ Pinyin',  # QQ拼音输入法
        }
        
        # 保存切换前的输入法
        self._previous_input_method = None
        
        logger.debug("输入法管理器初始化完成")
    
    def get_current_input_method(self) -> Optional[str]:
        """
        获取当前输入法
        
        Returns:
            当前输入法标识，失败返回None
        """
        try:
            # 获取前台窗口
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                logger.warning("无法获取前台窗口")
                return None
            
            # 获取窗口线程ID
            thread_id = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
            if not thread_id:
                logger.warning("无法获取窗口线程ID")
                return None
            
            # 获取输入法布局
            hkl = ctypes.windll.user32.GetKeyboardLayout(thread_id)
            if not hkl:
                logger.warning("无法获取键盘布局")
                return None
            
            # 转换为16进制字符串
            input_method_id = f"{hkl & 0xFFFFFFFF:08X}"
            
            logger.debug(f"当前输入法ID: {input_method_id}")
            return input_method_id
            
        except Exception as e:
            logger.error(f"获取当前输入法失败: {e}")
            return None
    
    def get_input_method_name(self, input_method_id: str) -> str:
        """
        获取输入法名称
        
        Args:
            input_method_id: 输入法标识
            
        Returns:
            输入法名称
        """
        return self.INPUT_METHODS.get(input_method_id, f"Unknown ({input_method_id})")
    
    def switch_to_english(self) -> bool:
        """
        切换到英文输入法
        
        Returns:
            是否切换成功
        """
        try:
            # 保存当前输入法
            current_method = self.get_current_input_method()
            if current_method:
                self._previous_input_method = current_method
                logger.info(f"保存当前输入法: {self.get_input_method_name(current_method)}")
            
            # 获取前台窗口
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                logger.warning("无法获取前台窗口")
                return False
            
            # 英文输入法的HKL值
            english_hkl = 0x00000409
            
            # 加载英文输入法
            hkl = ctypes.windll.user32.LoadKeyboardLayoutW(
                ctypes.wintypes.LPCWSTR("00000409"), 
                ctypes.wintypes.UINT(0x00000001)  # KLF_ACTIVATE
            )
            
            if hkl:
                # 激活英文输入法
                result = ctypes.windll.user32.ActivateKeyboardLayout(hkl, 0)
                if result:
                    logger.info("✅ 成功切换到英文输入法")
                    self.input_method_changed.emit("English (US)")
                    return True
                else:
                    logger.warning("激活英文输入法失败")
            else:
                logger.warning("加载英文输入法失败")
            
            # 备用方法：发送Alt+Shift切换输入法
            logger.info("尝试使用Alt+Shift切换到英文输入法")
            return self._switch_using_hotkey()
            
        except Exception as e:
            logger.error(f"切换到英文输入法失败: {e}")
            return False
    
    def restore_previous_input_method(self) -> bool:
        """
        恢复之前的输入法
        
        Returns:
            是否恢复成功
        """
        try:
            if not self._previous_input_method:
                logger.info("没有保存的输入法，跳过恢复")
                return True
            
            # 如果之前就是英文输入法，不需要切换
            if self._previous_input_method == '00000409':
                logger.info("之前就是英文输入法，无需恢复")
                return True
            
            # 尝试恢复到之前的输入法
            logger.info(f"尝试恢复到之前的输入法: {self.get_input_method_name(self._previous_input_method)}")
            
            # 使用热键切换回去（通常需要多次切换才能回到指定输入法）
            success = self._switch_using_hotkey()
            
            if success:
                logger.info("✅ 输入法恢复完成")
                self.input_method_changed.emit(self.get_input_method_name(self._previous_input_method))
            
            # 清除保存的输入法
            self._previous_input_method = None
            
            return success
            
        except Exception as e:
            logger.error(f"恢复输入法失败: {e}")
            return False
    
    def _switch_using_hotkey(self) -> bool:
        """
        使用热键切换输入法
        
        Returns:
            是否切换成功
        """
        try:
            # 模拟按下Alt+Shift切换输入法
            # 按下Alt键
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)  # VK_MENU (Alt)
            # 按下Shift键
            ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)  # VK_SHIFT
            # 释放Shift键
            ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)  # KEYEVENTF_KEYUP
            # 释放Alt键
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)  # KEYEVENTF_KEYUP
            
            logger.debug("已发送Alt+Shift热键切换输入法")
            return True
            
        except Exception as e:
            logger.error(f"使用热键切换输入法失败: {e}")
            return False
    
    def is_chinese_input_method(self, input_method_id: Optional[str] = None) -> bool:
        """
        检查是否为中文输入法
        
        Args:
            input_method_id: 输入法标识，为None时获取当前输入法
            
        Returns:
            是否为中文输入法
        """
        try:
            if input_method_id is None:
                input_method_id = self.get_current_input_method()
            
            if not input_method_id:
                return False
            
            # 检查是否为中文输入法
            chinese_methods = ['00000804', 'E0010804', 'E0200804', 'E0040804']
            return input_method_id in chinese_methods
            
        except Exception as e:
            logger.error(f"检查中文输入法失败: {e}")
            return False
    
    def auto_switch_for_scanning(self) -> bool:
        """
        为扫码自动切换输入法
        
        Returns:
            是否切换成功
        """
        try:
            current_method = self.get_current_input_method()
            if not current_method:
                logger.warning("无法获取当前输入法，跳过切换")
                return False
            
            current_name = self.get_input_method_name(current_method)
            logger.info(f"🔤 当前输入法: {current_name}")
            
            # 如果当前是中文输入法，切换到英文
            if self.is_chinese_input_method(current_method):
                logger.info("🔤 检测到中文输入法，切换到英文输入法以确保扫码正常")
                return self.switch_to_english()
            else:
                logger.info("🔤 当前已是英文输入法，无需切换")
                return True
                
        except Exception as e:
            logger.error(f"自动切换输入法失败: {e}")
            return False
    
    def get_status_info(self) -> dict:
        """
        获取输入法状态信息
        
        Returns:
            状态信息字典
        """
        try:
            current_method = self.get_current_input_method()
            return {
                'current_method_id': current_method,
                'current_method_name': self.get_input_method_name(current_method) if current_method else 'Unknown',
                'is_chinese': self.is_chinese_input_method(current_method),
                'previous_method_id': self._previous_input_method,
                'previous_method_name': self.get_input_method_name(self._previous_input_method) if self._previous_input_method else None
            }
        except Exception as e:
            logger.error(f"获取输入法状态信息失败: {e}")
            return {}
