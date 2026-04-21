#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
失败结果显示工具类
统一管理UI界面中的失败原因显示逻辑，避免重复代码
"""

from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

class FailResultDisplayUtils:
    """失败结果显示工具类"""
    
    # 失败项目优先级顺序（异常状态优先级最高）
    PRIORITY_ORDER = ["异常", "接触不良", "电池异常", "硬件异常", "电压", "离群率", "Rs", "Rct"]
    
    # 失败项目对应的样式映射
    STYLE_MAPPING = {
        "异常": "resultException",
        "接触不良": "resultContactPoor", 
        "电池异常": "resultBatteryError",
        "硬件异常": "resultHardwareError",
        "电压": "resultFailV",
        "离群率": "resultFailOutlier",
        "Rs": "resultFailRs",
        "Rct": "resultFailRct"
    }
    
    @classmethod
    def get_fail_result_display(cls, fail_items: Optional[List[str]]) -> Tuple[str, str]:
        """
        根据失败项目获取结果显示文本和样式
        
        Args:
            fail_items: 失败项目列表，如 ["电压", "Rs", "Rct"]
            
        Returns:
            (result_text, result_style) 结果文本和样式名称
        """
        try:
            if not fail_items or len(fail_items) == 0:
                return "不合格", "resultFail"
            
            # 按优先级排序失败项目
            sorted_fail_items = cls._sort_fail_items_by_priority(fail_items)
            
            # 生成显示文本
            result_text = cls._generate_result_text(sorted_fail_items)
            
            # 确定样式
            result_style = cls._determine_result_style(fail_items)
            
            return result_text, result_style
            
        except Exception as e:
            logger.error(f"获取失败结果显示失败: {e}")
            return "不合格", "resultFail"
    
    @classmethod
    def generate_combined_fail_reason(cls, fail_items: List[str]) -> str:
        """
        生成组合失败原因文本（用于打印和数据库存储）
        
        Args:
            fail_items: 失败项目列表，如 ["电压", "离群率", "Rs"]
            
        Returns:
            组合失败原因文本，如 "不合格-电压/离群率/Rs"
        """
        try:
            if not fail_items:
                return "不合格"
            
            # 按优先级排序失败项目
            sorted_fail_items = cls._sort_fail_items_by_priority(fail_items)
            
            # 生成失败原因文本
            if len(sorted_fail_items) == 1:
                return f"不合格-{sorted_fail_items[0]}"
            else:
                # 多个失败项目时，如果包含异常状态，优先显示异常
                exception_items = [item for item in sorted_fail_items 
                                 if item in ["异常", "接触不良", "电池异常", "硬件异常"]]
                if exception_items:
                    if len(exception_items) == 1:
                        return f"不合格-{exception_items[0]}"
                    else:
                        return f"不合格-{'/'.join(exception_items)}"
                else:
                    return f"不合格-{'/'.join(sorted_fail_items)}"
                    
        except Exception as e:
            logger.error(f"生成组合失败原因失败: {e}")
            return "不合格"
    
    @classmethod
    def _sort_fail_items_by_priority(cls, fail_items: List[str]) -> List[str]:
        """按优先级排序失败项目"""
        sorted_fail_items = []
        
        # 按优先级添加失败项目
        for item in cls.PRIORITY_ORDER:
            if item in fail_items:
                sorted_fail_items.append(item)
        
        # 添加其他不在优先级列表中的失败项目
        for item in fail_items:
            if item not in cls.PRIORITY_ORDER and item not in sorted_fail_items:
                sorted_fail_items.append(item)
        
        return sorted_fail_items
    
    @classmethod
    def _generate_result_text(cls, sorted_fail_items: List[str]) -> str:
        """生成结果显示文本"""
        if len(sorted_fail_items) == 1:
            return f"不合格-{sorted_fail_items[0]}"
        else:
            # 多个失败项目时，如果包含异常状态，优先显示异常
            exception_items = [item for item in sorted_fail_items 
                             if item in ["异常", "接触不良", "电池异常", "硬件异常"]]
            if exception_items:
                if len(exception_items) == 1:
                    return f"不合格-{exception_items[0]}"
                else:
                    return f"不合格-{'/'.join(exception_items)}"
            else:
                return f"不合格-{'/'.join(sorted_fail_items)}"
    
    @classmethod
    def _determine_result_style(cls, fail_items: List[str]) -> str:
        """根据失败项目确定样式"""
        # 按优先级确定样式
        for item in cls.PRIORITY_ORDER:
            if item in fail_items and item in cls.STYLE_MAPPING:
                return cls.STYLE_MAPPING[item]
        
        # 默认样式
        return "resultFail"
