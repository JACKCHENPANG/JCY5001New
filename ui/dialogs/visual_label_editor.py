# -*- coding: utf-8 -*-
"""
可视化标签编辑器

提供拖拽编辑、实时预览、网格对齐等功能的标签设计界面

Author: Jack
Date: 2025-01-29
"""

import logging
import os
from typing import Optional, List, Dict, Any, Tuple
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsPixmapItem,
    QPushButton, QCheckBox, QSlider, QLabel, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QTimer
from PyQt5.QtGui import (
    QPen, QBrush, QColor, QFont, QPixmap, QPainter, QTransform
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.ImageDraw import ImageDraw as ImageDrawType
else:
    ImageDrawType = object
from PIL import Image, ImageDraw, ImageFont
import qrcode

from .label_template_config import (
    LabelTemplateConfig, LabelElement, LabelSize, ElementType,
    get_dynamic_parameters
)

logger = logging.getLogger(__name__)


class LabelEditorView(QGraphicsView):
    """支持拖拽的标签编辑器视图"""

    # 信号定义
    parameter_dropped = pyqtSignal(str, float, float)  # 参数拖拽信号 (param_key, x, y)

    def __init__(self, scene=None):
        """初始化视图"""
        super().__init__(scene)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasText():
            # 检查是否是参数拖拽
            param_key = event.mimeData().text()
            if param_key:
                event.acceptProposedAction()
                logger.debug(f"接受参数拖拽: {param_key}")
            else:
                event.ignore()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """拖拽放下事件"""
        if event.mimeData().hasText():
            param_key = event.mimeData().text()

            # 将视图坐标转换为场景坐标
            scene_pos = self.mapToScene(event.pos())
            x = scene_pos.x()
            y = scene_pos.y()

            logger.info(f"🎯 参数拖拽到画布: {param_key} 位置: ({x:.1f}, {y:.1f})")

            # 发射信号
            self.parameter_dropped.emit(param_key, x, y)

            event.acceptProposedAction()
        else:
            event.ignore()


class LabelElementItem(QGraphicsRectItem):
    """标签元素图形项"""
    
    def __init__(self, element: LabelElement, parent=None):
        """
        初始化元素图形项
        
        Args:
            element: 标签元素配置
            parent: 父项
        """
        super().__init__(parent)
        
        self.element = element
        self.is_selected = False
        
        # 设置基本属性 - 修复位置设置
        self.setRect(0, 0, element.width, element.height)  # 矩形相对于自身
        self.setPos(element.x, element.y)  # 设置在场景中的绝对位置
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        # 设置外观
        self._update_appearance()
        
        # 创建内容显示
        self._create_content_display()
    
    def _update_appearance(self):
        """更新外观"""
        if self.is_selected:
            pen = QPen(QColor(0, 120, 215), 2)  # 蓝色选中边框
            brush = QBrush(QColor(0, 120, 215, 30))  # 半透明蓝色填充
        else:
            pen = QPen(QColor(128, 128, 128), 1)  # 灰色边框
            brush = QBrush(QColor(255, 255, 255, 100))  # 半透明白色填充
        
        self.setPen(pen)
        self.setBrush(brush)
    
    def _create_content_display(self):
        """创建内容显示"""
        if self.element.element_type == ElementType.TEXT.value:
            self._create_text_display()
        elif self.element.element_type == ElementType.QR_CODE.value:
            self._create_qr_display()
        elif self.element.element_type == ElementType.BARCODE.value:
            self._create_barcode_display()
    
    def _create_text_display(self):
        """创建文本显示"""
        # 处理动态参数的特殊显示
        display_text = self._format_text_with_parameters(self.element.content)
        text_item = QGraphicsTextItem(display_text, self)

        # 字体一致性优化确保与打印输出完全一致
        font = QFont(self.element.font_family, self.element.font_size)

        # 设置字体渲染质量
        font.setStyleHint(QFont.StyleHint.TypeWriter)  # 使用等宽字体提示
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)  # 完整字体提示

        # 处理字体样式 - 与打印逻辑保持一致
        font_style = getattr(self.element, 'font_style', 'normal')
        if font_style == "bold":
            font.setBold(True)
            font.setWeight(QFont.Weight.Bold)  # 明确设置粗体权重
        elif font_style == "italic":
            font.setItalic(True)
        elif font_style == "bold_italic":
            font.setBold(True)
            font.setItalic(True)
            font.setWeight(QFont.Weight.Bold)

        text_item.setFont(font)
        text_item.setDefaultTextColor(QColor(self.element.text_color))

        # 调整位置
        text_item.setPos(2, 2)  # 小偏移避免与边框重叠

    def _format_text_with_parameters(self, text: str) -> str:
        """格式化文本，使用模拟数据替换动态参数实现WYSIWYG效果"""
        try:
            from .label_template_config import replace_parameters_with_sample_data

            # 使用模拟数据替换动态参数
            formatted_text = replace_parameters_with_sample_data(text)

            if text != formatted_text:
                logger.info(f"✅ 可视化编辑器参数替换成功: '{text}' -> '{formatted_text}'")
            else:
                logger.debug(f"📝 可视化编辑器文本无需替换: '{text}'")

            return formatted_text

        except Exception as e:
            logger.error(f"❌ 可视化编辑器格式化动态参数文本失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return text
    
    def _create_qr_display(self):
        """创建二维码显示"""
        try:
            # WYSIWYG优化显示模拟数据内容而不是QR占位符
            from .label_template_config import replace_parameters_with_sample_data
            display_content = replace_parameters_with_sample_data(self.element.content)

            # 显示实际内容的前几个字符
            display_text = f"QR\n{display_content[:8]}..." if len(display_content) > 8 else f"QR\n{display_content}"

            text_item = QGraphicsTextItem(display_text, self)
            font = QFont("Arial", 8, QFont.Weight.Bold)
            text_item.setFont(font)
            text_item.setPos(2, 2)

        except Exception as e:
            logger.error(f"创建二维码显示失败: {e}")
            # 显示占位符
            text_item = QGraphicsTextItem("QR", self)
            text_item.setPos(self.element.width//2-10, self.element.height//2-10)
    
    def _create_barcode_display(self):
        """创建条形码显示"""
        try:
            # WYSIWYG优化显示模拟数据内容
            from .label_template_config import replace_parameters_with_sample_data
            display_content = replace_parameters_with_sample_data(self.element.content)

            # 显示条形码样式和实际内容
            barcode_pattern = "|||||||||||"
            display_text = f"{barcode_pattern}\n{display_content[:10]}..." if len(display_content) > 10 else f"{barcode_pattern}\n{display_content}"

            text_item = QGraphicsTextItem(display_text, self)
            font = QFont("Courier", 8)
            text_item.setFont(font)
            text_item.setPos(2, 2)

        except Exception as e:
            logger.error(f"创建条形码显示失败: {e}")
            # 简单的条形码占位符
            text_item = QGraphicsTextItem("|||||||", self)
            font = QFont("Courier", 12)
            text_item.setFont(font)
            text_item.setPos(2, self.element.height//2-10)
    
    def itemChange(self, change, value):
        """处理项目变化"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # 更新元素位置
            new_pos = value
            self.element.x = int(new_pos.x())
            self.element.y = int(new_pos.y())

            # 发送位置变化信号
            if hasattr(self.scene(), 'element_changed'):
                self.scene().element_changed.emit(self.element.element_id)

        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selected = True
            self._update_appearance()

            # 通知场景选择变化
            if hasattr(self.scene(), 'element_selected'):
                self.scene().element_selected.emit(self.element.element_id)

        super().mousePressEvent(event)
    
    def update_element(self, element: LabelElement):
        """更新元素配置"""
        try:
            logger.info(f"🔄 开始更新可视化元素: {element.element_id}, 内容: '{element.content}'")

            self.element = element

            # 更新位置和尺寸 - 修复位置设置
            self.setRect(0, 0, element.width, element.height)  # 矩形相对于自身
            self.setPos(element.x, element.y)  # 设置在场景中的绝对位置

            # 清除旧的子项
            for child in self.childItems():
                self.scene().removeItem(child)

            # 重新创建内容显示
            self._create_content_display()

            # 更新外观
            self._update_appearance()

            # 强制刷新确保更新立即生效
            self.update()
            if self.scene():
                self.scene().update()

            logger.info(f"✅ 可视化元素更新完成: {element.element_id}")

        except Exception as e:
            logger.error(f"❌ 更新可视化元素失败: {element.element_id}, 错误: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")


class LabelEditorScene(QGraphicsScene):
    """标签编辑器场景"""

    # 信号定义
    element_selected = pyqtSignal(str)  # 元素选择信号
    element_changed = pyqtSignal(str)   # 元素变化信号
    parameter_dropped = pyqtSignal(str, float, float)  # 参数拖拽信号 (param_key, x, y)

    def __init__(self, parent=None):
        """初始化场景"""
        super().__init__(parent)

        self.template_config: Optional[LabelTemplateConfig] = None
        self.element_items: Dict[str, LabelElementItem] = {}
        self.show_grid = True
        self.grid_size = 10

        # 设置场景背景
        self.setBackgroundBrush(QBrush(QColor(250, 250, 250)))
    
    def set_template(self, template: LabelTemplateConfig):
        """设置模板配置"""
        try:
            self.template_config = template

            # 设置场景大小
            width, height = template.get_size_pixels()
            self.setSceneRect(0, 0, width, height)

            # 清除现有元素
            self.clear_elements()

            # 添加模板元素
            for element in template.elements:
                self.add_element(element)

            # 强制更新场景
            self.update()

            logger.debug(f"场景设置模板完成: {template.name}, 尺寸: {width}x{height}, 元素数: {len(template.elements)}")

        except Exception as e:
            logger.error(f"场景设置模板失败: {e}")
    
    def add_element(self, element: LabelElement):
        """添加元素到场景"""
        if element.element_id in self.element_items:
            logger.warning(f"元素ID已存在: {element.element_id}")
            return
        
        item = LabelElementItem(element)
        self.addItem(item)
        self.element_items[element.element_id] = item
    
    def remove_element(self, element_id: str):
        """从场景移除元素"""
        if element_id in self.element_items:
            item = self.element_items[element_id]
            self.removeItem(item)
            del self.element_items[element_id]
    
    def clear_elements(self):
        """清除所有元素"""
        for item in self.element_items.values():
            self.removeItem(item)
        self.element_items.clear()
    
    def update_element(self, element: LabelElement):
        """更新元素"""
        try:
            if element.element_id in self.element_items:
                logger.info(f"🎯 场景开始更新元素: {element.element_id}, 内容: '{element.content}'")
                item = self.element_items[element.element_id]
                item.update_element(element)

                # 强制刷新场景
                self.update()
                logger.info(f"✅ 场景元素更新完成: {element.element_id}")
            else:
                logger.warning(f"⚠️ 场景中未找到要更新的元素: {element.element_id}")

        except Exception as e:
            logger.error(f"❌ 场景更新元素失败: {element.element_id}, 错误: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def select_element(self, element_id: str):
        """选择元素"""
        # 取消所有选择
        for item in self.element_items.values():
            item.is_selected = False
            item._update_appearance()
        
        # 选择指定元素
        if element_id in self.element_items:
            item = self.element_items[element_id]
            item.is_selected = True
            item._update_appearance()
    
    def drawBackground(self, painter, rect):
        """绘制背景"""
        super().drawBackground(painter, rect)
        
        if self.show_grid and self.template_config:
            self._draw_grid(painter, rect)
    
    def _draw_grid(self, painter, rect):
        """绘制网格"""
        pen = QPen(QColor(200, 200, 200), 1, Qt.PenStyle.DotLine)
        painter.setPen(pen)
        
        # 绘制垂直线
        x = 0
        while x <= self.sceneRect().width():
            painter.drawLine(int(x), 0, int(x), int(self.sceneRect().height()))
            x += self.grid_size

        # 绘制水平线
        y = 0
        while y <= self.sceneRect().height():
            painter.drawLine(0, int(y), int(self.sceneRect().width()), int(y))
            y += self.grid_size


class VisualLabelEditor(QWidget):
    """可视化标签编辑器"""

    # 信号定义
    element_selected = pyqtSignal(str)  # 元素选择信号
    template_changed = pyqtSignal()     # 模板变化信号
    
    def __init__(self, parent=None):
        """初始化编辑器"""
        super().__init__(parent)
        
        self.template_config: Optional[LabelTemplateConfig] = None
        
        # 初始化界面
        self._init_ui()
        
        # 连接信号
        self._connect_signals()
        
        logger.debug("可视化标签编辑器初始化完成")
    
    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 创建工具栏
        self._create_toolbar(layout)
        
        # 创建编辑视图
        self._create_editor_view(layout)
    
    def _create_toolbar(self, layout):
        """创建工具栏"""
        toolbar_frame = QFrame()
        toolbar_frame.setFrameStyle(QFrame.StyledPanel)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)
        
        # 网格显示开关
        self.grid_checkbox = QCheckBox("显示网格")
        self.grid_checkbox.setChecked(True)
        toolbar_layout.addWidget(self.grid_checkbox)
        
        # 缩放控制
        toolbar_layout.addWidget(QLabel("缩放:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(50, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setMaximumWidth(100)
        toolbar_layout.addWidget(self.zoom_slider)
        
        self.zoom_label = QLabel("100%")
        toolbar_layout.addWidget(self.zoom_label)
        
        toolbar_layout.addStretch()
        
        layout.addWidget(toolbar_frame)
    
    def _create_editor_view(self, layout):
        """创建编辑视图"""
        # 创建场景和视图
        self.scene = LabelEditorScene()
        self.view = LabelEditorView(self.scene)

        # 设置视图属性
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.RubberBandDrag)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 启用拖拽接受
        self.view.setAcceptDrops(True)

        layout.addWidget(self.view)
    
    def _connect_signals(self):
        """连接信号"""
        self.grid_checkbox.toggled.connect(self._on_grid_toggled)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)

        # 连接场景信号
        self.scene.element_selected.connect(self.element_selected.emit)
        self.scene.element_changed.connect(lambda: self.template_changed.emit())

        # 连接视图拖拽信号
        self.view.parameter_dropped.connect(self._on_parameter_dropped)

    def set_template(self, template: LabelTemplateConfig):
        """设置模板配置"""
        try:
            self.template_config = template
            self.scene.set_template(template)

            # 调整视图以适应模板尺寸
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

            # 强制刷新视图
            self.view.update()
            self.scene.update()

            logger.debug(f"可视化编辑器设置模板完成: {template.name}")

        except Exception as e:
            logger.error(f"可视化编辑器设置模板失败: {e}")

    def get_template(self) -> Optional[LabelTemplateConfig]:
        """获取当前模板配置"""
        return self.template_config

    def add_element(self, element: LabelElement):
        """添加元素"""
        if self.template_config:
            if self.template_config.add_element(element):
                self.scene.add_element(element)
                self.template_changed.emit()
                return True
        return False

    def remove_element(self, element_id: str):
        """移除元素"""
        if self.template_config:
            if self.template_config.remove_element(element_id):
                self.scene.remove_element(element_id)
                self.template_changed.emit()
                return True
        return False

    def update_element(self, element_id: str, **kwargs):
        """更新元素属性"""
        if self.template_config:
            if self.template_config.update_element(element_id, **kwargs):
                # 获取更新后的元素
                element = self.template_config.get_element(element_id)
                if element:
                    self.scene.update_element(element)
                    self.template_changed.emit()
                    return True
        return False

    def select_element(self, element_id: str):
        """选择元素"""
        self.scene.select_element(element_id)

    def get_selected_element(self) -> Optional[str]:
        """获取选中的元素ID"""
        for element_id, item in self.scene.element_items.items():
            if item.is_selected:
                return element_id
        return None

    def _on_grid_toggled(self, checked: bool):
        """网格显示切换"""
        self.scene.show_grid = checked
        self.scene.update()

    def _on_zoom_changed(self, value: int):
        """缩放变化"""
        scale = value / 100.0
        transform = QTransform()
        transform.scale(scale, scale)
        self.view.setTransform(transform)

        self.zoom_label.setText(f"{value}%")

    def _on_parameter_dropped(self, param_key: str, x: float, y: float):
        """处理参数拖拽到画布"""
        try:
            logger.info(f"🎯 处理参数拖拽: {param_key} 位置: ({x:.1f}, {y:.1f})")

            if not self.template_config:
                logger.warning("没有当前模板，无法添加元素")
                return

            # 根据参数类型创建对应元素
            from datetime import datetime
            element_id = f"dropped_{param_key}_{datetime.now().strftime('%H%M%S%f')}"

            if param_key in ['qr_code', 'battery_code']:
                # 创建二维码元素
                from .label_template_config import LabelElement, ElementType
                element = LabelElement(
                    element_id=element_id,
                    element_type=ElementType.QR_CODE.value,
                    x=int(x),
                    y=int(y),
                    width=80,
                    height=80,
                    content=f"{{{param_key}}}",
                    qr_error_correction="M"
                )
            elif param_key == 'barcode':
                # 创建条形码元素
                from .label_template_config import LabelElement, ElementType
                element = LabelElement(
                    element_id=element_id,
                    element_type=ElementType.BARCODE.value,
                    x=int(x),
                    y=int(y),
                    width=120,
                    height=40,
                    content=f"{{{param_key}}}",
                    barcode_type="CODE128"
                )
            else:
                # 创建文本元素
                from .label_template_config import LabelElement, ElementType
                element = LabelElement(
                    element_id=element_id,
                    element_type=ElementType.TEXT.value,
                    x=int(x),
                    y=int(y),
                    width=100,
                    height=20,
                    content=f"{{{param_key}}}",
                    font_family="微软雅黑",
                    font_size=14,
                    text_color="#000000"
                )

            # 添加元素到模板
            if self.add_element(element):
                logger.info(f"✅ 拖拽创建元素成功: {element_id}")
            else:
                logger.error(f"❌ 拖拽创建元素失败: {element_id}")

        except Exception as e:
            logger.error(f"处理参数拖拽失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def fit_to_view(self):
        """适应视图"""
        if self.template_config:
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

            # 更新缩放滑块
            current_transform = self.view.transform()
            scale = current_transform.m11()  # 获取X轴缩放比例
            zoom_value = int(scale * 100)

            self.zoom_slider.setValue(zoom_value)
            self.zoom_label.setText(f"{zoom_value}%")

    def zoom_to_fit(self):
        """缩放到合适大小"""
        self.fit_to_view()

    def zoom_in(self):
        """放大"""
        current_value = self.zoom_slider.value()
        new_value = min(200, current_value + 10)
        self.zoom_slider.setValue(new_value)

    def zoom_out(self):
        """缩小"""
        current_value = self.zoom_slider.value()
        new_value = max(50, current_value - 10)
        self.zoom_slider.setValue(new_value)

    def reset_zoom(self):
        """重置缩放"""
        self.zoom_slider.setValue(100)

    def generate_preview_image(self) -> Optional[Image.Image]:
        """生成预览图像"""
        if not self.template_config:
            return None

        try:
            # 获取模板尺寸
            width, height = self.template_config.get_size_pixels()

            # 创建PIL图像
            image = Image.new('RGB', (width, height), 'white')
            draw = ImageDraw.Draw(image)

            # 绘制边框
            draw.rectangle([0, 0, width-1, height-1], outline='lightgray', width=1)

            # 绘制元素
            for element in self.template_config.elements:
                self._draw_element_on_image(draw, element, width, height)

            return image

        except Exception as e:
            logger.error(f"生成预览图像失败: {e}")
            return None

    def _draw_element_on_image(self, draw, element: LabelElement,
                              canvas_width: int, canvas_height: int):
        """在图像上绘制元素"""
        try:
            if element.element_type == ElementType.TEXT.value:
                self._draw_text_element(draw, element)
            elif element.element_type == ElementType.QR_CODE.value:
                self._draw_qr_element(draw, element, canvas_width, canvas_height)
            elif element.element_type == ElementType.BARCODE.value:
                self._draw_barcode_element(draw, element)

        except Exception as e:
            logger.error(f"绘制元素失败: {e}")

    def _draw_text_element(self, draw, element: LabelElement):
        """绘制文本元素"""
        try:
            # 加载支持中文的字体
            font = self._load_chinese_font(element.font_family, element.font_size)

            # WYSIWYG优化使用模拟数据替换动态参数
            from .label_template_config import replace_parameters_with_sample_data
            display_text = replace_parameters_with_sample_data(element.content)

            # 优化增强字体样式效果
            font_style = getattr(element, 'font_style', 'normal')

            # 确保文本颜色为纯黑色，提升对比度
            text_color = element.text_color
            if text_color in ['black', '#000000', '#000']:
                text_color = '#000000'  # 纯黑色

            if font_style in ['bold', 'bold_italic']:
                # 🔤 超粗体效果：与打印管理器保持一致，使用4x4网格
                bold_offsets = [
                    (0, 0), (1, 0), (2, 0), (3, 0),     # 第一行
                    (0, 1), (1, 1), (2, 1), (3, 1),     # 第二行
                    (0, 2), (1, 2), (2, 2), (3, 2),     # 第三行
                    (0, 3), (1, 3), (2, 3), (3, 3),     # 第四行
                    (4, 0), (0, 4), (4, 4),             # 边角强化
                    (2, 4), (4, 2)                      # 额外强化点
                ]
                for offset_x, offset_y in bold_offsets:
                    draw.text((element.x + 2 + offset_x, element.y + 2 + offset_y),
                             display_text,
                             fill=text_color,
                             font=font)
            else:
                # 正常绘制
                draw.text((element.x + 2, element.y + 2),
                         display_text,
                         fill=text_color,
                         font=font)

        except Exception as e:
            logger.error(f"绘制文本元素失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _load_chinese_font(self, font_family: str, font_size: int):
        """加载支持中文的字体"""
        try:
            # 中文字体映射
            chinese_font_map = {
                "微软雅黑": ["msyh.ttc", "msyh.ttf"],
                "宋体": ["simsun.ttc", "simsun.ttf"],
                "黑体": ["simhei.ttf"],
                "楷体": ["simkai.ttf"],
                "隶书": ["SIMLI.TTF"],
                "幼圆": ["SIMYOU.TTF"],
                "Arial": ["arial.ttf"],
                "Times New Roman": ["times.ttf"],
                "Courier New": ["cour.ttf"]
            }

            # 尝试加载指定字体
            if font_family in chinese_font_map:
                for font_file in chinese_font_map[font_family]:
                    font_path = f"C:/Windows/Fonts/{font_file}"
                    try:
                        if os.path.exists(font_path):
                            font = ImageFont.truetype(font_path, font_size)
                            logger.debug(f"✅ 编辑器成功加载字体: {font_path} (大小: {font_size})")
                            return font
                    except Exception as e:
                        logger.debug(f"加载字体失败 {font_path}: {e}")
                        continue

            # 如果指定字体失败，尝试默认中文字体
            default_chinese_fonts = [
                "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
                "C:/Windows/Fonts/simsun.ttc",    # 宋体
                "C:/Windows/Fonts/simhei.ttf",    # 黑体
            ]

            for font_path in default_chinese_fonts:
                try:
                    if os.path.exists(font_path):
                        font = ImageFont.truetype(font_path, font_size)
                        logger.debug(f"使用默认中文字体: {font_path}")
                        return font
                except Exception as e:
                    logger.debug(f"加载默认中文字体失败 {font_path}: {e}")
                    continue

            # 最后使用PIL默认字体
            logger.warning("无法加载中文字体，使用默认字体")
            return ImageFont.load_default()

        except Exception as e:
            logger.error(f"加载中文字体失败: {e}")
            return ImageFont.load_default()

    def _draw_qr_element(self, draw, element: LabelElement,
                        canvas_width: int, canvas_height: int):
        """绘制二维码元素"""
        try:
            # 简化处理：绘制二维码占位符
            draw.rectangle([element.x, element.y,
                          element.x + element.width, element.y + element.height],
                         outline='black', width=1)

            # 在中心绘制QR标识
            font = self._load_chinese_font("Arial", 8)
            draw.text((element.x + element.width//2 - 8, element.y + element.height//2 - 4),
                     "QR", fill='black', font=font)

        except Exception as e:
            logger.error(f"绘制二维码元素失败: {e}")
            # 绘制错误占位符
            draw.rectangle([element.x, element.y,
                          element.x + element.width, element.y + element.height],
                         outline='red', width=1)
            font = self._load_chinese_font("Arial", 8)
            draw.text((element.x + 2, element.y + 2), "QR错误", fill='red', font=font)

    def _draw_barcode_element(self, draw, element: LabelElement):
        """绘制条形码元素"""
        try:
            # 简化的条形码绘制
            draw.rectangle([element.x, element.y,
                          element.x + element.width, element.y + element.height],
                         outline='black', width=1)

            # 绘制条形码样式的线条
            for i in range(0, element.width-4, 3):
                x = element.x + 2 + i
                if i % 6 < 3:  # 简单的条形码模式
                    draw.line([x, element.y + 2, x, element.y + element.height - 2],
                             fill='black', width=1)

        except Exception as e:
            logger.error(f"绘制条形码元素失败: {e}")
