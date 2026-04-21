# -*- coding: utf-8 -*-
"""
标签模板配置类

负责定义标签模板的数据结构、序列化和验证功能
支持多种标签尺寸和元素类型的配置

Author: Jack
Date: 2025-01-29
"""

import json
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


class LabelSize(Enum):
    """标签尺寸枚举"""
    SIZE_30x20 = (240, 160, "30x20mm", 30, 20)  # width_px, height_px, display_name, width_mm, height_mm
    SIZE_40x30 = (320, 240, "40x30mm", 40, 30)
    SIZE_50x30 = (400, 240, "50x30mm", 50, 30)
    
    def __init__(self, width_px: int, height_px: int, display_name: str, width_mm: int, height_mm: int):
        self.width_px = width_px
        self.height_px = height_px
        self.display_name = display_name
        self.width_mm = width_mm
        self.height_mm = height_mm
    
    @classmethod
    def from_display_name(cls, display_name: str) -> 'LabelSize':
        """根据显示名称获取标签尺寸"""
        for size in cls:
            if size.display_name == display_name:
                return size
        raise ValueError(f"未知的标签尺寸: {display_name}")
    
    @classmethod
    def get_all_sizes(cls) -> List[str]:
        """获取所有标签尺寸的显示名称"""
        return [size.display_name for size in cls]


class ElementType(Enum):
    """元素类型枚举"""
    TEXT = "text"
    QR_CODE = "qr_code"
    BARCODE = "barcode"
    
    @classmethod
    def get_all_types(cls) -> List[str]:
        """获取所有元素类型"""
        return [elem_type.value for elem_type in cls]


class FontStyle(Enum):
    """字体样式枚举"""
    NORMAL = "normal"
    BOLD = "bold"
    ITALIC = "italic"
    BOLD_ITALIC = "bold_italic"


class TextAlignment(Enum):
    """文本对齐方式枚举"""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


@dataclass
class LabelElement:
    """标签元素配置"""
    element_id: str                    # 元素唯一ID
    element_type: str                  # 元素类型 (ElementType.value)
    x: int                            # X坐标 (像素)
    y: int                            # Y坐标 (像素)
    width: int                        # 宽度 (像素)
    height: int                       # 高度 (像素)
    content: str                      # 内容或参数名
    
    # 文本相关属性
    font_family: str = "微软雅黑"      # 字体族
    font_size: int = 14               # 字体大小 (pt)
    font_style: str = "normal"        # 字体样式
    text_color: str = "black"         # 文本颜色
    text_alignment: str = "left"      # 文本对齐
    
    # 二维码/条形码相关属性
    qr_error_correction: str = "M"    # 二维码纠错级别 (L/M/Q/H)
    barcode_type: str = "CODE128"     # 条形码类型
    
    # 其他属性
    background_color: str = "transparent"  # 背景颜色
    border_width: int = 0             # 边框宽度
    border_color: str = "black"       # 边框颜色
    visible: bool = True              # 是否可见
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LabelElement':
        """从字典创建元素"""
        return cls(**data)
    
    def validate(self) -> bool:
        """验证元素配置是否有效"""
        try:
            # 检查基本属性
            if not self.element_id or not self.element_type:
                return False
            
            # 检查坐标和尺寸
            if self.x < 0 or self.y < 0 or self.width <= 0 or self.height <= 0:
                return False
            
            # 检查元素类型
            if self.element_type not in ElementType.get_all_types():
                return False
            
            # 修复扩大字体大小范围，支持超大字体
            if self.font_size < 8 or self.font_size > 72:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证元素配置失败: {e}")
            return False


@dataclass
class LabelTemplateConfig:
    """标签模板配置"""
    template_id: str                  # 模板唯一ID
    name: str                         # 模板名称
    description: str                  # 模板描述
    size: str                         # 标签尺寸 (LabelSize.display_name)
    elements: List[LabelElement]      # 元素列表
    
    # 元数据
    version: str = "1.0"              # 配置版本
    created_time: str = ""            # 创建时间
    modified_time: str = ""           # 修改时间
    author: str = "系统"              # 作者
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.created_time:
            self.created_time = datetime.now().isoformat()
        if not self.modified_time:
            self.modified_time = self.created_time
    
    def get_label_size(self) -> LabelSize:
        """获取标签尺寸对象"""
        return LabelSize.from_display_name(self.size)
    
    def get_size_pixels(self) -> Tuple[int, int]:
        """获取标签尺寸（像素）"""
        label_size = self.get_label_size()
        return label_size.width_px, label_size.height_px
    
    def add_element(self, element: LabelElement) -> bool:
        """添加元素"""
        try:
            if not element.validate():
                logger.error("元素配置无效，无法添加")
                return False
            
            # 检查ID是否重复
            if any(e.element_id == element.element_id for e in self.elements):
                logger.error(f"元素ID重复: {element.element_id}")
                return False
            
            self.elements.append(element)
            self.modified_time = datetime.now().isoformat()
            return True
            
        except Exception as e:
            logger.error(f"添加元素失败: {e}")
            return False
    
    def remove_element(self, element_id: str) -> bool:
        """移除元素"""
        try:
            original_count = len(self.elements)
            self.elements = [e for e in self.elements if e.element_id != element_id]
            
            if len(self.elements) < original_count:
                self.modified_time = datetime.now().isoformat()
                return True
            else:
                logger.warning(f"未找到要移除的元素: {element_id}")
                return False
                
        except Exception as e:
            logger.error(f"移除元素失败: {e}")
            return False
    
    def get_element(self, element_id: str) -> Optional[LabelElement]:
        """获取指定元素"""
        for element in self.elements:
            if element.element_id == element_id:
                return element
        return None
    
    def update_element(self, element_id: str, **kwargs) -> bool:
        """更新元素属性"""
        try:
            element = self.get_element(element_id)
            if not element:
                logger.error(f"未找到要更新的元素: {element_id}")
                return False
            
            # 更新属性
            for key, value in kwargs.items():
                if hasattr(element, key):
                    setattr(element, key, value)
            
            # 验证更新后的元素
            if not element.validate():
                logger.error("更新后的元素配置无效")
                return False
            
            self.modified_time = datetime.now().isoformat()
            return True
            
        except Exception as e:
            logger.error(f"更新元素失败: {e}")
            return False
    
    def validate(self) -> bool:
        """验证模板配置是否有效"""
        try:
            # 检查基本属性
            if not self.template_id or not self.name or not self.size:
                return False
            
            # 检查标签尺寸
            try:
                self.get_label_size()
            except ValueError:
                return False
            
            # 验证所有元素
            for element in self.elements:
                if not element.validate():
                    return False
            
            # 检查元素是否在标签范围内
            width_px, height_px = self.get_size_pixels()
            for element in self.elements:
                if (element.x + element.width > width_px or 
                    element.y + element.height > height_px):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证模板配置失败: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'template_id': self.template_id,
            'name': self.name,
            'description': self.description,
            'size': self.size,
            'elements': [element.to_dict() for element in self.elements],
            'version': self.version,
            'created_time': self.created_time,
            'modified_time': self.modified_time,
            'author': self.author
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LabelTemplateConfig':
        """从字典创建模板配置"""
        # 创建数据副本，避免修改原始数据
        data_copy = data.copy()

        # 提取元素数据
        elements_data = data_copy.pop('elements', [])
        elements = [LabelElement.from_dict(elem_data) for elem_data in elements_data]

        # 移除不属于模板配置的字段（如导出信息等）
        data_copy.pop('export_info', None)  # 移除导出信息

        # 只保留模板配置的有效字段
        valid_fields = {
            'template_id', 'name', 'description', 'size',
            'version', 'created_time', 'modified_time', 'author'
        }
        filtered_data = {k: v for k, v in data_copy.items() if k in valid_fields}

        config = cls(elements=elements, **filtered_data)
        return config
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'LabelTemplateConfig':
        """从JSON字符串创建模板配置"""
        data = json.loads(json_str)
        return cls.from_dict(data)


# 预定义的动态参数
DYNAMIC_PARAMETERS = {
    '{battery_code}': '电池编码',
    '{test_date}': '测试日期',
    '{test_time}': '测试时间',
    '{channel_number}': '通道号',
    '{rs_value}': 'Rs阻值',
    '{rct_value}': 'Rct阻值',
    '{voltage}': '电压值',
    '{grade}': '等级',
    '{operator}': '操作员',
    '{batch_number}': '批次号',
    '{rs_grade}': 'Rs档位',
    '{rct_grade}': 'Rct档位',
    '{grade_result}': '档位结果',
    '{is_pass}': '测试结果',
    '{timestamp}': '完整时间戳',
    '{outlier_rate}': '离群率',
    '{cell_type}': '电池类型'
}


def get_dynamic_parameters() -> Dict[str, str]:
    """获取所有动态参数"""
    return DYNAMIC_PARAMETERS.copy()


def validate_dynamic_parameter(param: str) -> bool:
    """验证动态参数是否有效"""
    return param in DYNAMIC_PARAMETERS


def get_sample_data() -> Dict[str, str]:
    """
    获取模拟数据，用于标签编辑器预览

    Returns:
        包含所有动态参数模拟值的字典
    """
    from datetime import datetime

    # 生成当前时间
    now = datetime.now()

    return {
        'battery_code': 'ABC123456789',
        'test_date': now.strftime('%Y-%m-%d'),
        'test_time': now.strftime('%H:%M:%S'),
        'channel_number': '5',
        'rs_value': '0.125',
        'rct_value': '2.456',
        'voltage': '3.250',
        'grade': '合格',
        'operator': '张工程师',
        'batch_number': 'B20241221001',
        'rs_grade': '3',
        'rct_grade': '2',
        'grade_result': 'G3-G2',
        'is_pass': '合格',
        'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
        'outlier_rate': '2.5%',
        'cell_type': 'LiFePO4'
    }


def replace_parameters_with_sample_data(text: str) -> str:
    """
    将文本中的动态参数替换为模拟数据

    Args:
        text: 包含动态参数的文本

    Returns:
        替换后的文本
    """
    if not text:
        return text

    sample_data = get_sample_data()
    result_text = text

    # 替换所有动态参数
    for param_key, param_desc in DYNAMIC_PARAMETERS.items():
        if param_key in result_text:
            # 获取参数名（去掉大括号）
            param_name = param_key.strip('{}')
            sample_value = sample_data.get(param_name, param_desc)
            result_text = result_text.replace(param_key, sample_value)

    return result_text
