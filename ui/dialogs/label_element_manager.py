#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标签元素管理器
负责标签元素的创建、删除和管理

Author: Jack
Date: 2025-06-04
"""

import logging
from datetime import datetime
from typing import Optional, List, Tuple
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

# 导入标签相关类
from .label_template_config import LabelTemplateConfig, LabelElement, ElementType

logger = logging.getLogger(__name__)


class LabelElementManager(QObject):
    """
    标签元素管理器
    
    职责：
    - 管理标签元素的创建和删除
    - 计算元素的智能位置
    - 处理元素的更新操作
    """
    
    # 信号定义
    element_added = pyqtSignal(str)  # 元素添加信号 (element_id)
    element_removed = pyqtSignal(str)  # 元素删除信号 (element_id)
    element_updated = pyqtSignal(str, dict)  # 元素更新信号 (element_id, properties)
    template_changed = pyqtSignal()  # 模板变更信号
    
    def __init__(self, parent=None):
        """初始化标签元素管理器"""
        super().__init__(parent)
        
        self.current_template: Optional[LabelTemplateConfig] = None
        
        logger.debug("标签元素管理器初始化完成")
    
    def set_current_template(self, template: Optional[LabelTemplateConfig]):
        """设置当前模板"""
        try:
            self.current_template = template
            logger.debug(f"设置当前模板: {template.name if template else 'None'}")
            
        except Exception as e:
            logger.error(f"设置当前模板失败: {e}")
    
    def add_text_element(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """添加文本元素"""
        if not self.current_template:
            return False

        try:
            # 创建新的文本元素，使用微秒确保唯一性
            element_id = f"text_{datetime.now().strftime('%H%M%S%f')}"

            # 计算位置：如果提供了坐标则使用，否则智能计算
            if x is not None and y is not None:
                pos_x, pos_y = x, y
            else:
                pos_x, pos_y = self._calculate_smart_position(100, 20)

            # 🔤 超大字体：使用LabelElement类创建文本元素，超大默认字体
            text_element = LabelElement(
                element_id=element_id,
                element_type=ElementType.TEXT.value,
                x=pos_x,
                y=pos_y,
                width=150,  # 进一步增加宽度以适应超大字体
                height=45,  # 进一步增加高度以适应超大字体
                content="新文本",
                font_family="微软雅黑",  # 使用中文字体
                font_size=36,  # 从28增大到36
                font_style="bold",  # 默认使用粗体
                text_color="#000000"
            )

            # 添加到当前模板
            self.current_template.add_element(text_element)

            # 发送信号
            self.element_added.emit(element_id)
            self.template_changed.emit()

            logger.info(f"添加文本元素: {element_id} 位置: ({pos_x}, {pos_y})")
            return True

        except Exception as e:
            logger.error(f"添加文本元素失败: {e}")
            return False

    def add_qr_element(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """添加二维码元素"""
        if not self.current_template:
            return False

        try:
            # 创建新的二维码元素，使用微秒确保唯一性
            element_id = f"qr_{datetime.now().strftime('%H%M%S%f')}"

            # 计算位置：如果提供了坐标则使用，否则智能计算
            if x is not None and y is not None:
                pos_x, pos_y = x, y
            else:
                pos_x, pos_y = self._calculate_smart_position(80, 80)

            # 使用LabelElement类创建二维码元素
            qr_element = LabelElement(
                element_id=element_id,
                element_type=ElementType.QR_CODE.value,
                x=pos_x,
                y=pos_y,
                width=80,
                height=80,
                content="{battery_code}",
                qr_error_correction="M"
            )

            # 添加到当前模板
            self.current_template.add_element(qr_element)

            # 发送信号
            self.element_added.emit(element_id)
            self.template_changed.emit()

            logger.info(f"添加二维码元素: {element_id} 位置: ({pos_x}, {pos_y})")
            return True

        except Exception as e:
            logger.error(f"添加二维码元素失败: {e}")
            return False

    def add_barcode_element(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """添加条形码元素"""
        if not self.current_template:
            return False

        try:
            # 创建新的条形码元素，使用微秒确保唯一性
            element_id = f"barcode_{datetime.now().strftime('%H%M%S%f')}"

            # 计算位置：如果提供了坐标则使用，否则智能计算
            if x is not None and y is not None:
                pos_x, pos_y = x, y
            else:
                pos_x, pos_y = self._calculate_smart_position(120, 40)

            # 使用LabelElement类创建条形码元素
            barcode_element = LabelElement(
                element_id=element_id,
                element_type=ElementType.BARCODE.value,
                x=pos_x,
                y=pos_y,
                width=120,
                height=40,
                content="{battery_code}",
                barcode_type="CODE128"
            )

            # 添加到当前模板
            self.current_template.add_element(barcode_element)

            # 发送信号
            self.element_added.emit(element_id)
            self.template_changed.emit()

            logger.info(f"添加条形码元素: {element_id} 位置: ({pos_x}, {pos_y})")
            return True

        except Exception as e:
            logger.error(f"添加条形码元素失败: {e}")
            return False

    def remove_element(self, element_id: str) -> bool:
        """移除元素"""
        if not self.current_template:
            return False

        try:
            # 使用模板的remove_element方法
            success = self.current_template.remove_element(element_id)

            if success:
                # 发送信号
                self.element_removed.emit(element_id)
                self.template_changed.emit()
                
                logger.info(f"移除元素: {element_id}")
                return True
            else:
                logger.warning(f"未找到要删除的元素: {element_id}")
                return False

        except Exception as e:
            logger.error(f"移除元素失败: {e}")
            return False

    def update_element(self, element_id: str, properties: dict) -> bool:
        """更新元素属性"""
        if not self.current_template:
            return False

        try:
            # 更新模板中的元素数据
            for element in self.current_template.elements:
                if hasattr(element, 'element_id'):
                    # 如果是LabelElement对象
                    if element.element_id == element_id:
                        # 更新元素属性
                        for key, value in properties.items():
                            if hasattr(element, key):
                                setattr(element, key, value)
                        
                        # 发送信号
                        self.element_updated.emit(element_id, properties)
                        self.template_changed.emit()
                        
                        logger.debug(f"更新元素: {element_id}")
                        return True
                elif isinstance(element, dict):
                    # 如果是字典对象
                    if element.get('element_id') == element_id:
                        element.update(properties)
                        
                        # 发送信号
                        self.element_updated.emit(element_id, properties)
                        self.template_changed.emit()
                        
                        logger.debug(f"更新元素: {element_id}")
                        return True

            logger.warning(f"未找到要更新的元素: {element_id}")
            return False

        except Exception as e:
            logger.error(f"更新元素失败: {e}")
            return False

    def get_element(self, element_id: str) -> Optional[LabelElement]:
        """获取指定元素"""
        if not self.current_template:
            return None

        try:
            return self.current_template.get_element(element_id)
        except Exception as e:
            logger.error(f"获取元素失败: {e}")
            return None

    def get_all_elements(self) -> List[LabelElement]:
        """获取所有元素"""
        if not self.current_template:
            return []

        try:
            return self.current_template.elements.copy()
        except Exception as e:
            logger.error(f"获取所有元素失败: {e}")
            return []

    def _calculate_smart_position(self, element_width: int, element_height: int) -> Tuple[int, int]:
        """
        智能计算新元素的位置，避免重叠
        
        Args:
            element_width: 元素宽度
            element_height: 元素高度
            
        Returns:
            tuple: (x, y) 坐标
        """
        if not self.current_template:
            return 10, 10

        try:
            # 获取模板尺寸
            template_width, template_height = self.current_template.get_size_pixels()

            # 边距设置
            margin = 8
            spacing = 10

            # 如果没有现有元素，从左上角开始
            if not self.current_template.elements:
                return margin, margin

            # 收集所有现有元素的位置信息
            occupied_areas = []
            for element in self.current_template.elements:
                occupied_areas.append({
                    'x': element.x,
                    'y': element.y,
                    'width': element.width,
                    'height': element.height,
                    'right': element.x + element.width,
                    'bottom': element.y + element.height
                })

            # 策略1：优先尝试网格布局 - 从左到右，从上到下
            positions_to_try = []

            # 计算网格步长
            grid_step_x = max(element_width + spacing, 50)  # 最小50像素间距
            grid_step_y = max(element_height + spacing, 35)  # 最小35像素间距

            # 生成网格位置
            for y in range(margin, template_height - element_height - margin, grid_step_y):
                for x in range(margin, template_width - element_width - margin, grid_step_x):
                    positions_to_try.append((x, y))

            # 策略2：在现有元素右侧放置
            for area in occupied_areas:
                x = area['right'] + spacing
                y = area['y']
                if x + element_width <= template_width - margin:
                    positions_to_try.append((x, y))

            # 策略3：在现有元素下方放置
            for area in occupied_areas:
                x = area['x']
                y = area['bottom'] + spacing
                if y + element_height <= template_height - margin:
                    positions_to_try.append((x, y))

            # 检查每个候选位置是否与现有元素重叠
            for x, y in positions_to_try:
                if self._is_position_free(x, y, element_width, element_height, occupied_areas):
                    logger.debug(f"智能位置计算成功: ({x}, {y})")
                    return x, y

            # 如果所有位置都被占用，使用偏移位置
            offset = len(occupied_areas) * 8
            x = margin + offset
            y = margin + offset

            # 确保不超出边界
            if x + element_width > template_width - margin:
                x = template_width - element_width - margin
            if y + element_height > template_height - margin:
                y = template_height - element_height - margin

            logger.warning(f"使用备选位置: ({x}, {y})")
            return max(margin, x), max(margin, y)

        except Exception as e:
            logger.error(f"智能位置计算失败: {e}")
            return 10, 10

    def _is_position_free(self, x: int, y: int, width: int, height: int, occupied_areas: list) -> bool:
        """
        检查指定位置是否与现有元素重叠
        
        Args:
            x, y: 位置坐标
            width, height: 元素尺寸
            occupied_areas: 已占用区域列表
            
        Returns:
            bool: True表示位置空闲
        """
        new_right = x + width
        new_bottom = y + height

        for area in occupied_areas:
            # 检查是否重叠
            if not (new_right <= area['x'] or  # 新元素在左侧
                   x >= area['right'] or      # 新元素在右侧
                   new_bottom <= area['y'] or # 新元素在上方
                   y >= area['bottom']):      # 新元素在下方
                return False  # 有重叠

        return True  # 无重叠

    def cleanup(self):
        """清理资源"""
        try:
            self.current_template = None
            logger.debug("标签元素管理器资源清理完成")
            
        except Exception as e:
            logger.error(f"标签元素管理器清理失败: {e}")
