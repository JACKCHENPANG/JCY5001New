# -*- coding: utf-8 -*-
"""
标签模板管理器

负责标签模板的保存、加载、导出、导入和预设模板管理

Author: Jack
Date: 2025-01-29
"""

import os
import json
import logging
import shutil
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from .label_template_config import (
    LabelTemplateConfig, LabelElement, LabelSize, ElementType,
    DYNAMIC_PARAMETERS
)

logger = logging.getLogger(__name__)


class LabelTemplateManager:
    """标签模板管理器"""
    
    def __init__(self, config_manager):
        """
        初始化模板管理器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        
        # 模板存储目录
        self.templates_dir = Path("templates/label_templates")
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # 预设模板目录
        self.presets_dir = self.templates_dir / "presets"
        self.presets_dir.mkdir(exist_ok=True)
        
        # 用户模板目录
        self.user_dir = self.templates_dir / "user"
        self.user_dir.mkdir(exist_ok=True)
        
        # 初始化预设模板
        self._init_preset_templates()
        
        logger.debug("标签模板管理器初始化完成")

    def _validate_template_detailed(self, template: LabelTemplateConfig) -> Tuple[bool, str]:
        """
        详细验证模板配置

        Args:
            template: 模板配置

        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 检查基本属性
            if not template.template_id:
                return False, "模板ID不能为空"
            if not template.name:
                return False, "模板名称不能为空"
            if not template.size:
                return False, "模板尺寸不能为空"

            # 检查标签尺寸
            try:
                label_size = template.get_label_size()
                width_px, height_px = template.get_size_pixels()
            except ValueError as e:
                return False, f"无效的标签尺寸: {template.size}"
            except Exception as e:
                return False, f"获取标签尺寸失败: {e}"

            # 验证所有元素
            for i, element in enumerate(template.elements):
                if not element.validate():
                    return False, f"第{i+1}个元素配置无效: {element.element_id}"

                # 检查元素是否在标签范围内
                if element.x < 0 or element.y < 0:
                    return False, f"元素 '{element.element_id}' 位置不能为负数"

                if element.x + element.width > width_px:
                    return False, f"元素 '{element.element_id}' 超出标签宽度范围 (x:{element.x} + width:{element.width} > {width_px})"

                if element.y + element.height > height_px:
                    return False, f"元素 '{element.element_id}' 超出标签高度范围 (y:{element.y} + height:{element.height} > {height_px})"

            # 检查元素ID是否重复
            element_ids = [e.element_id for e in template.elements]
            if len(element_ids) != len(set(element_ids)):
                duplicates = [id for id in element_ids if element_ids.count(id) > 1]
                return False, f"存在重复的元素ID: {', '.join(set(duplicates))}"

            return True, ""

        except Exception as e:
            return False, f"验证过程中发生错误: {e}"

    def _init_preset_templates(self):
        """初始化预设模板"""
        try:
            # 创建标准模板 (50x30mm)
            if not (self.presets_dir / "standard_50x30.json").exists():
                standard_template = self._create_standard_template()
                self.save_preset_template(standard_template, "standard_50x30.json")
            
            # 创建简化模板 (40x30mm)
            if not (self.presets_dir / "simple_40x30.json").exists():
                simple_template = self._create_simple_template()
                self.save_preset_template(simple_template, "simple_40x30.json")
            
            # 创建详细模板 (50x30mm)
            if not (self.presets_dir / "detailed_50x30.json").exists():
                detailed_template = self._create_detailed_template()
                self.save_preset_template(detailed_template, "detailed_50x30.json")
            
            # 创建紧凑模板 (30x20mm)
            if not (self.presets_dir / "compact_30x20.json").exists():
                compact_template = self._create_compact_template()
                self.save_preset_template(compact_template, "compact_30x20.json")
            
            logger.debug("预设模板初始化完成")
            
        except Exception as e:
            logger.error(f"初始化预设模板失败: {e}")
    
    def _create_standard_template(self) -> LabelTemplateConfig:
        """创建标准模板 (50x30mm)"""
        elements = [
            # 标题
            LabelElement(
                element_id="title",
                element_type="text",
                x=12, y=8, width=200, height=24,
                content="JCY5001AS 电池测试",
                font_family="微软雅黑",
                font_size=20,
                font_style="bold"
            ),
            # 电池码
            LabelElement(
                element_id="battery_code",
                element_type="text",
                x=12, y=32, width=200, height=20,
                content="电池码: {battery_code}",
                font_size=14
            ),
            # 通道和电压
            LabelElement(
                element_id="channel_voltage",
                element_type="text",
                x=12, y=54, width=200, height=22,
                content="通道: CH{channel_number}    电压: {voltage:.2f}V",
                font_size=16
            ),
            # Rs值
            LabelElement(
                element_id="rs_value",
                element_type="text",
                x=12, y=76, width=200, height=22,
                content="Rs: {rs_value:.3f}mΩ    档位: G{rs_grade}",
                font_size=16
            ),
            # Rct值
            LabelElement(
                element_id="rct_value",
                element_type="text",
                x=12, y=98, width=200, height=22,
                content="Rct: {rct_value:.3f}mΩ   档位: G{rct_grade}",
                font_size=16
            ),
            # 测试状态
            LabelElement(
                element_id="test_status",
                element_type="text",
                x=12, y=120, width=150, height=24,
                content="状态: {is_pass}",
                font_size=20,
                font_style="bold",
                text_color="green"
            ),
            # 时间戳
            LabelElement(
                element_id="timestamp",
                element_type="text",
                x=12, y=200, width=200, height=16,
                content="时间: {timestamp}",
                font_size=14,
                text_color="gray"
            ),
            # 二维码
            LabelElement(
                element_id="qr_code",
                element_type="qr_code",
                x=315, y=75, width=85, height=85,
                content="{battery_code}"
            )
        ]
        
        return LabelTemplateConfig(
            template_id="standard_50x30",
            name="标准模板",
            description="50x30mm标准标签模板，包含完整的测试信息",
            size="50x30mm",
            elements=elements,
            author="系统预设"
        )
    
    def _create_simple_template(self) -> LabelTemplateConfig:
        """创建简化模板 (40x30mm)"""
        elements = [
            # 标题
            LabelElement(
                element_id="title",
                element_type="text",
                x=10, y=8, width=180, height=20,
                content="电池测试",
                font_size=18,
                font_style="bold"
            ),
            # 电池码
            LabelElement(
                element_id="battery_code",
                element_type="text",
                x=10, y=30, width=180, height=18,
                content="{battery_code}",
                font_size=12
            ),
            # Rs/Rct值
            LabelElement(
                element_id="impedance_values",
                element_type="text",
                x=10, y=50, width=180, height=18,
                content="Rs:{rs_value:.2f} Rct:{rct_value:.2f}",
                font_size=12
            ),
            # 档位
            LabelElement(
                element_id="grades",
                element_type="text",
                x=10, y=70, width=180, height=18,
                content="档位: G{rs_grade}-G{rct_grade}",
                font_size=12
            ),
            # 状态
            LabelElement(
                element_id="status",
                element_type="text",
                x=10, y=90, width=100, height=20,
                content="{is_pass}",
                font_size=16,
                font_style="bold"
            ),
            # 二维码
            LabelElement(
                element_id="qr_code",
                element_type="qr_code",
                x=220, y=50, width=70, height=70,
                content="{battery_code}"
            )
        ]
        
        return LabelTemplateConfig(
            template_id="simple_40x30",
            name="简化模板",
            description="40x30mm简化标签模板，突出重点信息",
            size="40x30mm",
            elements=elements,
            author="系统预设"
        )
    
    def _create_detailed_template(self) -> LabelTemplateConfig:
        """创建详细模板 (50x30mm)"""
        elements = [
            # 标题
            LabelElement(
                element_id="title",
                element_type="text",
                x=12, y=5, width=200, height=18,
                content="JCY5001AS 详细测试报告",
                font_size=16,
                font_style="bold"
            ),
            # 电池码
            LabelElement(
                element_id="battery_code",
                element_type="text",
                x=12, y=25, width=200, height=16,
                content="电池: {battery_code}",
                font_size=12
            ),
            # 通道电压
            LabelElement(
                element_id="channel_voltage",
                element_type="text",
                x=12, y=42, width=200, height=16,
                content="CH{channel_number} 电压:{voltage:.2f}V",
                font_size=12
            ),
            # Rs信息
            LabelElement(
                element_id="rs_info",
                element_type="text",
                x=12, y=59, width=200, height=16,
                content="Rs:{rs_value:.3f}mΩ G{rs_grade}",
                font_size=12
            ),
            # Rct信息
            LabelElement(
                element_id="rct_info",
                element_type="text",
                x=12, y=76, width=200, height=16,
                content="Rct:{rct_value:.3f}mΩ G{rct_grade}",
                font_size=12
            ),
            # 离群率
            LabelElement(
                element_id="outlier_rate",
                element_type="text",
                x=12, y=93, width=200, height=16,
                content="离群率: {outlier_rate}",
                font_size=12
            ),
            # 批次信息
            LabelElement(
                element_id="batch_info",
                element_type="text",
                x=12, y=110, width=200, height=16,
                content="批次:{batch_number} {operator}",
                font_size=10
            ),
            # 状态
            LabelElement(
                element_id="status",
                element_type="text",
                x=12, y=130, width=100, height=20,
                content="{is_pass}",
                font_size=16,
                font_style="bold"
            ),
            # 时间
            LabelElement(
                element_id="timestamp",
                element_type="text",
                x=12, y=155, width=200, height=14,
                content="{timestamp}",
                font_size=10,
                text_color="gray"
            ),
            # 二维码
            LabelElement(
                element_id="qr_code",
                element_type="qr_code",
                x=315, y=60, width=75, height=75,
                content="{battery_code}"
            )
        ]
        
        return LabelTemplateConfig(
            template_id="detailed_50x30",
            name="详细模板",
            description="50x30mm详细标签模板，包含离群率等扩展信息",
            size="50x30mm",
            elements=elements,
            author="系统预设"
        )
    
    def _create_compact_template(self) -> LabelTemplateConfig:
        """创建紧凑模板 (30x20mm)"""
        elements = [
            # 电池码
            LabelElement(
                element_id="battery_code",
                element_type="text",
                x=8, y=5, width=140, height=16,
                content="{battery_code}",
                font_size=10
            ),
            # 阻抗值
            LabelElement(
                element_id="impedance",
                element_type="text",
                x=8, y=22, width=140, height=14,
                content="Rs:{rs_value:.2f} Rct:{rct_value:.2f}",
                font_size=9
            ),
            # 档位
            LabelElement(
                element_id="grade",
                element_type="text",
                x=8, y=38, width=80, height=14,
                content="G{rs_grade}-G{rct_grade}",
                font_size=9
            ),
            # 状态
            LabelElement(
                element_id="status",
                element_type="text",
                x=8, y=54, width=60, height=16,
                content="{is_pass}",
                font_size=12,
                font_style="bold"
            ),
            # 二维码
            LabelElement(
                element_id="qr_code",
                element_type="qr_code",
                x=160, y=20, width=60, height=60,
                content="{battery_code}"
            )
        ]
        
        return LabelTemplateConfig(
            template_id="compact_30x20",
            name="紧凑模板",
            description="30x20mm紧凑标签模板，最小化布局",
            size="30x20mm",
            elements=elements,
            author="系统预设"
        )

    def save_template(self, template: LabelTemplateConfig, filename: Optional[str] = None) -> Tuple[bool, str]:
        """
        保存用户模板

        Args:
            template: 模板配置
            filename: 文件名（可选）

        Returns:
            (是否保存成功, 错误信息)
        """
        try:
            # 详细验证模板配置
            validation_result, validation_error = self._validate_template_detailed(template)
            if not validation_result:
                error_msg = f"模板配置无效: {validation_error}"
                logger.error(error_msg)
                return False, error_msg

            if not filename:
                # 生成默认文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # 清理模板名称，移除特殊字符
                safe_name = "".join(c for c in template.name if c.isalnum() or c in (' ', '-', '_')).strip()
                if not safe_name:
                    safe_name = template.template_id
                filename = f"{safe_name}_{timestamp}.json"

            filepath = self.user_dir / filename

            # 确保目录存在
            self.user_dir.mkdir(parents=True, exist_ok=True)

            # 更新修改时间
            template.modified_time = datetime.now().isoformat()

            # 保存到文件
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(template.to_json())

                # 验证文件是否成功写入
                if not filepath.exists() or filepath.stat().st_size == 0:
                    error_msg = "文件写入失败，文件不存在或为空"
                    logger.error(error_msg)
                    return False, error_msg

            except PermissionError:
                error_msg = f"没有写入权限: {filepath}"
                logger.error(error_msg)
                return False, error_msg
            except OSError as e:
                error_msg = f"文件系统错误: {e}"
                logger.error(error_msg)
                return False, error_msg

            logger.info(f"✅ 模板保存成功: {template.name} -> {filepath}")
            return True, ""

        except Exception as e:
            error_msg = f"保存模板时发生未知错误: {e}"
            logger.error(error_msg)
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False, error_msg

    def save_preset_template(self, template: LabelTemplateConfig, filename: str) -> bool:
        """
        保存预设模板

        Args:
            template: 模板配置
            filename: 文件名

        Returns:
            是否保存成功
        """
        try:
            filepath = self.presets_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(template.to_json())

            logger.debug(f"预设模板保存成功: {filepath}")
            return True

        except Exception as e:
            logger.error(f"保存预设模板失败: {e}")
            return False

    def load_template(self, filepath: str) -> Optional[LabelTemplateConfig]:
        """
        加载模板

        Args:
            filepath: 模板文件路径

        Returns:
            模板配置对象，失败返回None
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json_str = f.read()

            template = LabelTemplateConfig.from_json(json_str)

            if not template.validate():
                logger.error(f"加载的模板配置无效: {filepath}")
                return None

            logger.info(f"模板加载成功: {filepath}")
            return template

        except Exception as e:
            logger.error(f"加载模板失败: {e}")
            return None

    def get_template(self, template_id: str) -> Optional[LabelTemplateConfig]:
        """
        根据模板ID获取模板配置

        Args:
            template_id: 模板ID

        Returns:
            模板配置对象，失败返回None
        """
        try:
            # 首先在预设模板中查找
            preset_file = self.presets_dir / f"{template_id}.json"
            if preset_file.exists():
                return self.load_template(str(preset_file))

            # 然后在用户模板中查找
            for filepath in self.user_dir.glob("*.json"):
                template = self.load_template(str(filepath))
                if template and template.template_id == template_id:
                    return template

            logger.warning(f"未找到模板: {template_id}")
            return None

        except Exception as e:
            logger.error(f"获取模板失败: {e}")
            return None

    def get_preset_templates(self) -> List[LabelTemplateConfig]:
        """
        获取所有预设模板

        Returns:
            预设模板配置列表
        """
        templates = []
        try:
            for filepath in self.presets_dir.glob("*.json"):
                template = self.load_template(str(filepath))
                if template:
                    templates.append(template)

            logger.debug(f"找到 {len(templates)} 个预设模板")
            return templates

        except Exception as e:
            logger.error(f"获取预设模板失败: {e}")
            return []

    def get_user_templates(self) -> List[LabelTemplateConfig]:
        """
        获取所有用户模板

        Returns:
            用户模板配置列表
        """
        templates = []
        try:
            for filepath in self.user_dir.glob("*.json"):
                template = self.load_template(str(filepath))
                if template:
                    templates.append(template)

            logger.debug(f"找到 {len(templates)} 个用户模板")
            return templates

        except Exception as e:
            logger.error(f"获取用户模板失败: {e}")
            return []

    def create_template(self, template_name: str, size: str = "50x30mm") -> Optional[LabelTemplateConfig]:
        """
        创建新的用户模板

        Args:
            template_name: 模板名称
            size: 标签尺寸，默认50x30mm

        Returns:
            创建的模板配置，失败返回None
        """
        try:
            # 生成唯一的模板ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            template_id = f"user_{timestamp}"

            # 创建基本模板配置
            template = LabelTemplateConfig(
                template_id=template_id,
                name=template_name,
                description=f"用户自定义模板 - {template_name}",
                size=size,
                elements=[],  # 空元素列表，用户可以添加
                author="用户"
            )

            # 添加一个默认的标题元素
            from .label_template_config import LabelElement, ElementType
            title_element = LabelElement(
                element_id="default_title",
                element_type=ElementType.TEXT.value,
                x=10, y=10, width=150, height=20,
                content=template_name,
                font_family="微软雅黑",
                font_size=16,
                font_style="bold"
            )
            template.add_element(title_element)

            logger.info(f"创建新模板: {template_name}")
            return template

        except Exception as e:
            logger.error(f"创建模板失败: {e}")
            return None

    def delete_template(self, filepath: str) -> bool:
        """
        删除模板文件

        Args:
            filepath: 模板文件路径

        Returns:
            是否删除成功
        """
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"模板删除成功: {filepath}")
                return True
            else:
                logger.warning(f"模板文件不存在: {filepath}")
                return False

        except Exception as e:
            logger.error(f"删除模板失败: {e}")
            return False

    def delete_template_by_name(self, template_name: str) -> bool:
        """
        根据模板名称删除用户模板

        Args:
            template_name: 模板名称

        Returns:
            是否删除成功
        """
        try:
            # 在用户模板目录中查找匹配的模板文件
            for filepath in self.user_dir.glob("*.json"):
                template = self.load_template(str(filepath))
                if template and template.name == template_name:
                    # 找到匹配的模板，删除文件
                    return self.delete_template(str(filepath))

            logger.warning(f"未找到名为 '{template_name}' 的用户模板")
            return False

        except Exception as e:
            logger.error(f"根据名称删除模板失败: {e}")
            return False

    def rename_template(self, old_filepath: str, new_name: str) -> bool:
        """
        重命名用户模板

        Args:
            old_filepath: 原模板文件路径
            new_name: 新模板名称

        Returns:
            是否重命名成功
        """
        try:
            if not os.path.exists(old_filepath):
                logger.warning(f"模板文件不存在: {old_filepath}")
                return False

            # 构建新的文件路径
            directory = os.path.dirname(old_filepath)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{new_name}_{timestamp}.json"
            new_filepath = os.path.join(directory, new_filename)

            # 加载模板并更新名称
            template = self.load_template(old_filepath)
            if template:
                template.name = new_name

                # 保存到新文件
                try:
                    with open(new_filepath, 'w', encoding='utf-8') as f:
                        f.write(template.to_json())

                    # 删除旧文件
                    os.remove(old_filepath)
                    logger.info(f"模板重命名成功: {old_filepath} -> {new_filepath}")
                    return True
                except Exception as save_error:
                    logger.error(f"保存重命名后的模板失败: {save_error}")
                    return False
            else:
                logger.error("加载原模板失败")
                return False

        except Exception as e:
            logger.error(f"重命名模板失败: {e}")
            return False

    def export_template(self, template: LabelTemplateConfig, export_path: str) -> bool:
        """
        导出模板到指定路径

        Args:
            template: 模板配置
            export_path: 导出路径

        Returns:
            是否导出成功
        """
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(template.to_json())

            logger.info(f"模板导出成功: {export_path}")
            return True

        except Exception as e:
            logger.error(f"导出模板失败: {e}")
            return False

    def import_template(self, import_path: str) -> Optional[LabelTemplateConfig]:
        """
        从指定路径导入模板

        Args:
            import_path: 导入路径

        Returns:
            导入的模板配置，失败返回None
        """
        try:
            template = self.load_template(import_path)
            if template:
                # 生成新的模板ID避免冲突
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                template.template_id = f"imported_{timestamp}"
                template.name = f"导入_{template.name}"

                # 保存到用户模板目录
                if self.save_template(template):
                    logger.info(f"模板导入成功: {template.name}")
                    return template

            return None

        except Exception as e:
            logger.error(f"导入模板失败: {e}")
            return None
