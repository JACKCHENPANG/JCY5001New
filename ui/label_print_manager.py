"""
标签打印管理器模块

负责电池测试结果标签的打印功能，包括：
- 标签数据格式化
- 打印队列管理
- 与打印机管理器集成
- 打印状态反馈
"""

import os
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QThread
from queue import Queue, Empty
import win32print
from PIL import Image, ImageDraw, ImageFont
import qrcode

logger = logging.getLogger(__name__)


class PrintJob:
    """打印任务类"""

    def __init__(self, job_id: str, test_result: Dict[str, Any], print_config: Dict[str, Any]):
        """
        初始化打印任务

        Args:
            job_id: 任务ID
            test_result: 测试结果数据
            print_config: 打印配置
        """
        self.job_id = job_id
        self.test_result = test_result
        self.print_config = print_config
        self.created_time = datetime.now()
        self.status = 'pending'  # pending, printing, completed, failed
        self.error_message: Optional[str] = None

    def __str__(self):
        return f"PrintJob({self.job_id}, {self.status})"


class LabelTemplate:
    """标签模板类 - 集成标签设计器配置"""

    def __init__(self, config_manager):
        """
        初始化标签模板

        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager

        # 从标签设计器配置中获取当前模板信息
        self._load_template_config()

        logger.debug(f"标签模板初始化: {self.label_width}x{self.label_height}像素")

    def _load_template_config(self):
        """从标签设计器配置中加载模板信息"""
        try:
            # 获取当前使用的模板配置
            current_template_id = self.config_manager.get('label_template.current_template_id', 'standard_50x30')

            # 尝试从标签设计器配置中加载模板
            template_config = self._load_designer_template(current_template_id)

            if template_config:
                # 使用设计器模板配置
                self.label_width = template_config.get('width', 400)
                self.label_height = template_config.get('height', 240)
                self.template_elements = template_config.get('elements', [])
                self.template_name = template_config.get('name', '标准模板')
                self.current_template_id = current_template_id  # 保存当前模板ID
                logger.info(f"✅ 已加载标签设计器模板: {self.template_name} (ID: {current_template_id})")
                logger.info(f"📐 模板尺寸: {self.label_width}x{self.label_height}像素，元素数量: {len(self.template_elements)}")
            else:
                # 使用默认配置
                self._load_default_config()
                logger.warning(f"⚠️ 未找到模板 {current_template_id}，使用默认标签模板配置")

        except Exception as e:
            logger.error(f"❌ 加载模板配置失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            self._load_default_config()

    def _load_default_config(self):
        """加载默认配置"""
        # 标签尺寸配置 (像素) - 50x30mm @ 203 DPI
        self.label_width = self.config_manager.get('label.width', 400)  # 50mm @ 203dpi
        self.label_height = self.config_manager.get('label.height', 240)  # 30mm @ 203dpi

        # 🔤 超大字体：进一步大幅放大以获得最佳打印效果
        self.font_size_large = 48      # 标题字体（从36增大到48）
        self.font_size_medium = 36     # 主要信息字体（从28增大到36）
        self.font_size_small = 32      # 详细信息字体（从24增大到32）

        self.template_elements = []
        self.template_name = "默认模板"

    def _load_designer_template(self, template_id: str) -> dict:
        """从标签设计器配置中加载指定模板"""
        try:

            # 尝试导入标签模板管理器
            from ui.dialogs.label_template_manager import LabelTemplateManager

            template_manager = LabelTemplateManager(self.config_manager)
            template_config = template_manager.get_template(template_id)

            if template_config:
                logger.debug(f"✅ 找到模板配置: {template_config.name}")

                # 转换为字典格式
                size_obj = template_config.get_label_size()
                result = {
                    'name': template_config.name,
                    'width': size_obj.width_px,
                    'height': size_obj.height_px,
                    'elements': template_config.elements
                }

                logger.info(f"✅ 设计器模板加载成功: {template_config.name} ({size_obj.width_px}x{size_obj.height_px}px, {len(template_config.elements)}个元素)")
                return result
            else:
                logger.warning(f"⚠️ 未找到模板: {template_id}")

        except ImportError as e:
            logger.warning(f"⚠️ 标签设计器模块未找到: {e}")
        except Exception as e:
            logger.error(f"❌ 加载设计器模板失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

        return None

    def _load_chinese_fonts(self):
        """加载支持中文的字体"""
        # 常见的Windows中文字体路径
        chinese_fonts = [
            "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
            "C:/Windows/Fonts/simsun.ttc",    # 宋体
            "C:/Windows/Fonts/simhei.ttf",    # 黑体
            "C:/Windows/Fonts/simkai.ttf",    # 楷体
            "C:/Windows/Fonts/SIMLI.TTF",     # 隶书
            "C:/Windows/Fonts/SIMYOU.TTF",    # 幼圆
        ]

        # 尝试加载中文字体
        for font_path in chinese_fonts:
            try:
                if os.path.exists(font_path):
                    font_large = ImageFont.truetype(font_path, self.font_size_large)
                    font_medium = ImageFont.truetype(font_path, self.font_size_medium)
                    font_small = ImageFont.truetype(font_path, self.font_size_small)
                    logger.debug(f"成功加载中文字体: {font_path}")
                    return font_large, font_medium, font_small
            except Exception as e:
                logger.debug(f"加载字体失败 {font_path}: {e}")
                continue

        # 如果所有中文字体都失败，尝试使用系统默认字体
        try:
            # 尝试使用系统字体API
            import platform
            if platform.system() == "Windows":
                # Windows系统尝试使用默认字体
                font_large = ImageFont.truetype("arial.ttf", self.font_size_large)
                font_medium = ImageFont.truetype("arial.ttf", self.font_size_medium)
                font_small = ImageFont.truetype("arial.ttf", self.font_size_small)
                logger.warning("使用arial字体，可能不支持中文显示")
                return font_large, font_medium, font_small
        except:
            pass

        # 最后使用PIL默认字体
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
        logger.warning("使用默认字体，可能不支持中文显示")
        return font_large, font_medium, font_small

    def _load_chinese_font_by_name(self, font_family: str, font_size: int):
        """根据字体名称加载支持中文的字体"""
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
                            logger.debug(f"成功加载字体: {font_path}")
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

    def generate_label_image(self, test_result: Dict[str, Any]) -> Image.Image:
        """
        生成标签图像 - 使用标签设计器模板配置

        Args:
            test_result: 测试结果数据

        Returns:
            PIL图像对象
        """
        try:
            # 检查是否有模板元素配置
            if self.template_elements and len(self.template_elements) > 0:
                # 使用标签设计器模板
                return self._generate_label_from_template(test_result)
            else:
                # 使用默认硬编码布局（向后兼容）
                logger.warning(f"模板 '{self.template_name}' 没有元素配置，使用默认布局")
                return self._generate_default_label(test_result)

        except Exception as e:
            logger.error(f"生成标签图像失败: {e}")
            # 返回错误标签
            return self._generate_error_label(str(e))

    def _generate_label_from_template(self, test_result: Dict[str, Any]) -> Image.Image:
        """
        根据标签设计器模板生成标签图像

        Args:
            test_result: 测试结果数据

        Returns:
            PIL图像对象
        """
        try:
            # 创建白色背景图像
            image = Image.new('RGB', (self.label_width, self.label_height), 'white')
            draw = ImageDraw.Draw(image)

            logger.debug(f"使用模板 '{self.template_name}' 生成标签，尺寸: {self.label_width}x{self.label_height}，元素数: {len(self.template_elements)}")

            # 准备动态参数数据
            dynamic_data = self._prepare_dynamic_data(test_result)

            # 渲染每个模板元素
            for element in self.template_elements:
                try:
                    self._render_element(draw, element, dynamic_data, image)
                except Exception as e:
                    # 兼容处理获取元素ID
                    element_id = getattr(element, 'element_id', 'unknown') if hasattr(element, 'element_id') else element.get('element_id', 'unknown')
                    logger.error(f"渲染元素 {element_id} 失败: {e}")
                    continue

            logger.debug(f"模板标签图像生成完成: {test_result.get('battery_code', 'N/A')}")
            return image

        except Exception as e:
            logger.error(f"根据模板生成标签失败: {e}")
            # 回退到默认布局
            return self._generate_default_label(test_result)

    def _prepare_dynamic_data(self, test_result: Dict[str, Any]) -> Dict[str, str]:
        """
        准备动态参数数据

        Args:
            test_result: 测试结果数据

        Returns:
            动态参数字典
        """
        try:

            # 获取基础数据
            battery_code = test_result.get('battery_code', 'N/A')
            channel = test_result.get('channel_number', 'N/A')
            voltage = test_result.get('voltage', 0.0)

            # 修复增强Rs和Rct值的获取逻辑，支持多种字段名
            rs_value = test_result.get('rs_value',
                       test_result.get('rs',
                       test_result.get('current_rs', 0.0)))
            rct_value = test_result.get('rct_value',
                        test_result.get('rct',
                        test_result.get('current_rct', 0.0)))

            # 修复如果仍然为0，尝试从通道组件直接获取
            if rs_value == 0.0 or rct_value == 0.0:
                logger.warning(f"🚨 [打印数据] 检测到Rs/Rct值为0，原始数据: Rs={rs_value}, Rct={rct_value}")
                logger.warning(f"🚨 [打印数据] 完整测试结果: {test_result}")

            rs_grade = test_result.get('rs_grade', 1)
            rct_grade = test_result.get('rct_grade', 1)
            is_pass_raw = test_result.get('is_pass', False)
            timestamp = test_result.get('timestamp', datetime.now())

            # 🔧 修复：检查is_pass字段是否包含异常信息，如果是则根据档位重新判断
            if isinstance(is_pass_raw, str) and ("异常" in is_pass_raw or "获取" in is_pass_raw):
                # is_pass字段包含异常信息，根据档位重新判断
                is_pass = (rs_grade not in [0, '--', None, 'None'] and
                          rct_grade not in [0, '--', None, 'None'])
                logger.debug(f"🔧 [打印数据] 检测到is_pass字段异常: {is_pass_raw}，根据档位重新判断: {is_pass}")
            else:
                is_pass = bool(is_pass_raw)

            logger.debug(f"🔧 解析的基础数据: 电池码={battery_code}, 通道={channel}, "
                        f"电压={voltage:.3f}V, Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ, "
                        f"Rs档位={rs_grade}, Rct档位={rct_grade}, 合格={is_pass}")

            # 格式化时间
            if isinstance(timestamp, datetime):
                time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                time_short = timestamp.strftime('%m-%d %H:%M')
            else:
                time_str = str(timestamp)
                time_short = str(timestamp)[:11]

            # 获取批次信息
            batch_number = self.config_manager.get('batch_info.batch_number', '')
            operator = self.config_manager.get('batch_info.operator', '')

            # 修复增强离群率数据获取逻辑，支持多种字段名和格式
            outlier_rate = test_result.get('outlier_rate',
                          test_result.get('outlier_result',
                          test_result.get('max_deviation_percent', '')))

            # 修复获取完整的离群率相关数据
            frequency_deviations = test_result.get('frequency_deviations', {})
            baseline_filename = test_result.get('baseline_filename', '')
            baseline_id = test_result.get('baseline_id', None)

            # 修复处理离群率数据格式，确保显示具体数值而不是只显示PASS/FAIL
            max_deviation_percent = test_result.get('max_deviation_percent', 0.0)
            frequency_deviations = test_result.get('frequency_deviations', {})


            # 优先使用具体的偏差数值
            if isinstance(outlier_rate, (int, float)):
                # 数值类型，转换为百分比格式
                outlier_rate_display = f"{outlier_rate:.1f}%"
            elif isinstance(outlier_rate, str):
                # 字符串类型处理
                if outlier_rate == "PASS":
                    # PASS状态时，尝试显示具体的偏差值
                    if max_deviation_percent > 0:
                        outlier_rate_display = f"{max_deviation_percent:.1f}%"
                    elif frequency_deviations:
                        # 从频点偏差数据计算最大偏差
                        max_dev = max(frequency_deviations.values()) if frequency_deviations else 0
                        outlier_rate_display = f"{max_dev:.1f}%"
                    else:
                        outlier_rate_display = "0.0%"  # 默认显示0.0%而不是PASS
                elif outlier_rate in ["已禁用", "无数据", "检测失败", ""]:
                    outlier_rate_display = outlier_rate if outlier_rate else "未检测"
                elif outlier_rate.endswith('%'):
                    # 已经是百分比格式，直接使用
                    outlier_rate_display = outlier_rate
                else:
                    # 尝试解析为数值
                    try:
                        rate_value = float(outlier_rate)
                        outlier_rate_display = f"{rate_value:.1f}%"
                    except (ValueError, TypeError):
                        # 无法解析时，检查是否有备用数据
                        if max_deviation_percent > 0:
                            outlier_rate_display = f"{max_deviation_percent:.1f}%"
                        else:
                            outlier_rate_display = outlier_rate
            else:
                # 其他类型，尝试使用备用数据
                if max_deviation_percent > 0:
                    outlier_rate_display = f"{max_deviation_percent:.1f}%"
                else:
                    outlier_rate_display = "未检测"


            # 🔧 修复档位显示逻辑 - 不合格时显示"不合格"，合格时显示档位
            fail_reason = test_result.get('fail_reason', '')
            fail_items = test_result.get('fail_items', [])

            # 🔧 修复：增强失败原因处理逻辑，确保多次测试间的一致性
            if (isinstance(fail_reason, str) and ("异常" in fail_reason or "获取" in fail_reason)) or (not fail_items and not is_pass):
                # 根据实际测试数据生成失败原因
                actual_fail_items = []

                # 检查电压
                if voltage < 2.5 or voltage > 4.2:
                    actual_fail_items.append("电压异常")

                # 检查Rs档位
                if rs_grade in [0, '--', None, 'None']:
                    actual_fail_items.append("Rs超标")

                # 检查Rct档位
                if rct_grade in [0, '--', None, 'None']:
                    actual_fail_items.append("Rct超标")

                # 如果没有找到具体失败原因，使用通用描述
                if not actual_fail_items:
                    actual_fail_items = ["不合格"]

                fail_items = actual_fail_items
                fail_reason = "; ".join(actual_fail_items)
                logger.debug(f"🔧 [打印数据] 重新生成失败原因: {fail_reason}, 触发条件: fail_reason='{fail_reason}', fail_items={fail_items}, is_pass={is_pass}")

            if is_pass:
                # 合格时显示档位
                if rs_grade is not None and rct_grade is not None and rs_grade != 'None' and rct_grade != 'None' and rs_grade != '--' and rct_grade != '--':
                    grade_result = f"{rs_grade}-{rct_grade}"
                    rs_grade_display = str(rs_grade)
                    rct_grade_display = str(rct_grade)
                    test_result_display = "合格"
                else:
                    # 合格但没有档位数据
                    grade_result = "合格"
                    rs_grade_display = "--"
                    rct_grade_display = "--"
                    test_result_display = "合格"
            else:
                # 🔧 不合格时档位显示"不合格"，结果显示具体失败原因
                grade_result = "不合格"
                rs_grade_display = "--"
                rct_grade_display = "--"

                # 🔧 结果显示具体的失败原因
                if fail_items:
                    if len(fail_items) == 1:
                        test_result_display = f"不合格-{fail_items[0]}"
                    else:
                        test_result_display = f"不合格-{'/'.join(fail_items[:2])}"  # 最多显示前两个失败项目
                elif fail_reason and fail_reason != "不合格":
                    test_result_display = fail_reason
                else:
                    test_result_display = "不合格"

            # 返回所有可用的动态参数
            dynamic_data = {
                'battery_code': battery_code,
                'channel_number': str(channel),
                'voltage': f"{voltage:.3f}",
                'rs_value': f"{rs_value:.3f}",
                'rct_value': f"{rct_value:.3f}",
                'rs_grade': rs_grade_display,  # 修复使用优化后的档位显示
                'rct_grade': rct_grade_display,  # 修复使用优化后的档位显示
                'grade_result': grade_result,  # 新增的档位结果参数
                'is_pass': test_result_display,  # 修复使用详细的测试结果
                'timestamp': time_str,
                'test_time': time_short,
                'batch_number': batch_number,
                'operator': operator,
                'outlier_rate': outlier_rate_display,  # 修复使用格式化后的离群率显示
                'qr_code': battery_code,  # 二维码内容
                'barcode': battery_code,   # 条形码内容
                # 新增离群率详细数据
                'baseline_filename': baseline_filename,
                'baseline_id': str(baseline_id) if baseline_id else '',
                'frequency_deviations_count': str(len(frequency_deviations)) if frequency_deviations else '0'
            }

            logger.debug(f" 动态数据准备完成: Rs={dynamic_data['rs_value']}mΩ, "
                       f"Rct={dynamic_data['rct_value']}mΩ, 档位={dynamic_data['grade_result']}, "
                       f"离群率={dynamic_data['outlier_rate']}, 结果={dynamic_data['is_pass']}")

            # 修复验证关键数据是否为0，如果为0则记录警告
            if dynamic_data['rs_value'] == '0.000' or dynamic_data['rct_value'] == '0.000':
                logger.warning(f"🚨 打印数据异常: Rs={dynamic_data['rs_value']}mΩ, Rct={dynamic_data['rct_value']}mΩ - 数值为0可能导致打印显示异常")
                logger.warning(f"🚨 原始测试结果数据: {test_result}")

            return dynamic_data

        except Exception as e:
            logger.error(f"准备动态数据失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return {}

    def _render_element(self, draw: ImageDraw.Draw, element, dynamic_data: Dict[str, str], image: Image.Image):
        """
        渲染单个模板元素

        Args:
            draw: PIL绘图对象
            element: 元素配置对象（LabelElement或字典）
            dynamic_data: 动态参数数据
            image: PIL图像对象（用于粘贴二维码等）
        """
        try:
            # 兼容处理：支持LabelElement对象和字典
            if hasattr(element, 'element_type'):
                # LabelElement对象
                element_type = element.element_type
                element_id = element.element_id
                x = element.x
                y = element.y
                width = element.width
                height = element.height
                visible = element.visible
            else:
                # 字典格式
                element_type = element.get('element_type', 'text')
                element_id = element.get('element_id', 'unknown')
                x = element.get('x', 0)
                y = element.get('y', 0)
                width = element.get('width', 100)
                height = element.get('height', 20)
                visible = element.get('visible', True)

            # 检查元素是否可见
            if not visible:
                return

            if element_type == 'text':
                self._render_text_element(draw, element, dynamic_data)
            elif element_type in ['qr', 'qr_code']:  # 支持两种二维码类型名称
                self._render_qr_element(draw, element, dynamic_data, image)
            elif element_type == 'barcode':
                self._render_barcode_element(draw, element, dynamic_data, image)
            else:
                logger.warning(f"未知元素类型: {element_type}")

        except Exception as e:
            logger.error(f"渲染元素失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _render_text_element(self, draw: ImageDraw.Draw, element, dynamic_data: Dict[str, str]):
        """渲染文本元素"""
        try:
            # 兼容处理：支持LabelElement对象和字典
            if hasattr(element, 'content'):
                # LabelElement对象
                content = element.content
                font_family = element.font_family
                font_size = element.font_size
                font_style = element.font_style
                text_color = element.text_color
                x = element.x
                y = element.y
            else:
                # 字典格式
                content = element.get('content', '')
                font_family = element.get('font_family', '微软雅黑')
                font_size = element.get('font_size', 32)  # 🔤 超大字体：默认字体大小从24增大到32
                font_style = element.get('font_style', 'normal')
                text_color = element.get('text_color', 'black')
                x = element.get('x', 0)
                y = element.get('y', 0)

            # 替换动态参数
            for key, value in dynamic_data.items():
                content = content.replace(f'{{{key}}}', str(value))

            # 优化确保字体颜色为纯黑色，提升对比度
            if text_color in ['black', '#000000', '#000']:
                text_color = '#000000'  # 纯黑色

            # 加载字体
            font = self._load_chinese_font_by_name(font_family, font_size)

            # 🔤 超粗体效果：配合超大字体使用更强的粗体渲染
            if font_style in ['bold', 'bold_italic']:
                # 使用4x4网格模拟超超粗体效果
                bold_offsets = [
                    (0, 0), (1, 0), (2, 0), (3, 0),     # 第一行
                    (0, 1), (1, 1), (2, 1), (3, 1),     # 第二行
                    (0, 2), (1, 2), (2, 2), (3, 2),     # 第三行
                    (0, 3), (1, 3), (2, 3), (3, 3),     # 第四行
                    (4, 0), (0, 4), (4, 4),             # 边角强化
                    (2, 4), (4, 2)                      # 额外强化点
                ]
                for offset_x, offset_y in bold_offsets:
                    draw.text((x + offset_x, y + offset_y), content, fill=text_color, font=font)
            else:
                # 正常绘制
                draw.text((x, y), content, fill=text_color, font=font)

        except Exception as e:
            logger.error(f"渲染文本元素失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _render_qr_element(self, draw: ImageDraw.Draw, element, dynamic_data: Dict[str, str], image: Image.Image):
        """渲染二维码元素"""
        try:
            # 兼容处理：支持LabelElement对象和字典
            if hasattr(element, 'content'):
                # LabelElement对象
                content = element.content
                x = element.x
                y = element.y
                width = element.width
                height = element.height
                logger.debug(f"二维码元素(LabelElement): content='{content}', 位置=({x},{y}), 尺寸={width}x{height}")
            else:
                # 字典格式
                content = element.get('content', '')
                x = element.get('x', 0)
                y = element.get('y', 0)
                width = element.get('width', 80)
                height = element.get('height', 80)
                logger.debug(f"二维码元素(字典): content='{content}', 位置=({x},{y}), 尺寸={width}x{height}")

            logger.debug(f"动态数据: {dynamic_data}")

            # 替换动态参数
            original_content = content
            for key, value in dynamic_data.items():
                if f'{{{key}}}' in content:
                    content = content.replace(f'{{{key}}}', str(value))
                    logger.debug(f"替换参数 {{{key}}} -> '{value}', 结果: '{content}'")

            # 如果内容为空，使用电池码
            if not content or content.strip() == '':
                content = dynamic_data.get('battery_code', 'N/A')
                logger.warning(f"二维码内容为空，使用电池码: '{content}'")

            logger.info(f"最终二维码内容: '{content}' (原始: '{original_content}')")

            # 生成二维码
            qr_image = self._generate_qr_code(content)
            if qr_image:
                # 调整二维码尺寸
                qr_image = qr_image.resize((width, height))
                logger.debug(f"二维码调整尺寸: {qr_image.size} -> {width}x{height}")

                # 粘贴到图像上
                image.paste(qr_image, (x, y))
                logger.info(f"二维码已粘贴到位置 ({x}, {y})")
            else:
                logger.error("二维码生成失败，无法渲染")

        except Exception as e:
            logger.error(f"渲染二维码元素失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _render_barcode_element(self, draw: ImageDraw.Draw, element, dynamic_data: Dict[str, str], image: Image.Image):
        """渲染条形码元素"""
        try:
            # 兼容处理：支持LabelElement对象和字典
            if hasattr(element, 'content'):
                # LabelElement对象
                content = element.content
                x = element.x
                y = element.y
            else:
                # 字典格式
                content = element.get('content', '')
                x = element.get('x', 0)
                y = element.get('y', 0)

            # 替换动态参数
            for key, value in dynamic_data.items():
                content = content.replace(f'{{{key}}}', str(value))

            # 如果内容为空，使用电池码
            if not content:
                content = dynamic_data.get('battery_code', 'N/A')

            # 生成条形码（简化实现，使用文本代替）
            # 在实际项目中，可以使用 python-barcode 库
            # 使用小字体显示条形码内容
            font = self._load_chinese_font_by_name('Arial', 10)
            draw.text((x, y), f"||{content}||", fill='black', font=font)

        except Exception as e:
            logger.error(f"渲染条形码元素失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _generate_default_label(self, test_result: Dict[str, Any]) -> Image.Image:
        """
        生成默认标签图像（原硬编码布局，用于向后兼容）

        Args:
            test_result: 测试结果数据

        Returns:
            PIL图像对象
        """
        try:
            # 创建白色背景图像
            image = Image.new('RGB', (self.label_width, self.label_height), 'white')
            draw = ImageDraw.Draw(image)

            # 尝试使用支持中文的系统字体
            font_large, font_medium, font_small = self._load_chinese_fonts()

            # 优化布局参数 - 充分利用400x240像素空间
            margin_left = 12        # 左边距
            margin_top = 8          # 上边距
            margin_right = 12       # 右边距
            margin_bottom = 8       # 下边距

            # 行间距优化 - 配合更大字体
            line_spacing_large = 24   # 大字体行间距
            line_spacing_medium = 22  # 中字体行间距
            line_spacing_small = 20   # 小字体行间距

            # 二维码配置
            qr_size = 85
            qr_margin = 8

            # 计算左侧文字区域宽度
            text_area_width = self.label_width - margin_left - margin_right - qr_size - qr_margin

            # 获取测试数据
            battery_code = test_result.get('battery_code', 'N/A')
            channel = test_result.get('channel_number', 'N/A')
            voltage = test_result.get('voltage', 0.0)
            rs_value = test_result.get('rs_value', 0.0)
            rct_value = test_result.get('rct_value', 0.0)
            rs_grade = test_result.get('rs_grade', 1)
            rct_grade = test_result.get('rct_grade', 1)
            is_pass = test_result.get('is_pass', False)
            timestamp = test_result.get('timestamp', datetime.now())

            # 开始布局 - 从上到下均匀分布
            y_current = margin_top

            # 1. 标题区域 (顶部)
            title = "JCY5001AS 电池测试"
            draw.text((margin_left, y_current), title, fill='black', font=font_large)
            y_current += line_spacing_large

            # 2. 电池码区域
            # 处理长电池码的显示
            if len(battery_code) > 18:
                battery_display = battery_code[:18] + "..."
            else:
                battery_display = battery_code
            draw.text((margin_left, y_current), f"电池码: {battery_display}", fill='black', font=font_small)
            y_current += line_spacing_small

            # 3. 通道和电压信息 (同一行)
            channel_voltage_text = f"通道: CH{channel}    电压: {voltage:.3f}V"
            draw.text((margin_left, y_current), channel_voltage_text, fill='black', font=font_medium)
            y_current += line_spacing_medium

            # 4. Rs测试结果
            rs_text = f"Rs: {rs_value:.3f}mΩ    档位: G{rs_grade}"
            draw.text((margin_left, y_current), rs_text, fill='black', font=font_medium)
            y_current += line_spacing_medium

            # 5. Rct测试结果
            rct_text = f"Rct: {rct_value:.3f}mΩ   档位: G{rct_grade}"
            draw.text((margin_left, y_current), rct_text, fill='black', font=font_medium)
            y_current += line_spacing_medium

            # 6. 测试状态 (突出显示)
            status_text = "合格" if is_pass else "不合格"
            status_color = 'green' if is_pass else 'red'
            draw.text((margin_left, y_current), f"状态: {status_text}", fill=status_color, font=font_large)
            y_current += line_spacing_large

            # 7. 时间戳 (底部)
            if isinstance(timestamp, datetime):
                time_str = timestamp.strftime('%m-%d %H:%M')  # 简化时间显示
            else:
                time_str = str(timestamp)[:11]  # 限制长度

            # 计算底部位置，确保充分利用空间
            bottom_y = self.label_height - margin_bottom - 16  # 为字体高度预留空间
            if y_current < bottom_y:
                y_current = bottom_y

            draw.text((margin_left, y_current), f"时间: {time_str}", fill='gray', font=font_small)

            # 生成并放置二维码 (右侧居中)
            qr_code = self._generate_qr_code(battery_code)
            if qr_code:
                qr_code = qr_code.resize((qr_size, qr_size))
                # 二维码垂直居中
                qr_x = self.label_width - qr_size - margin_right
                qr_y = (self.label_height - qr_size) // 2
                image.paste(qr_code, (qr_x, qr_y))

                # 在二维码下方添加小字说明
                qr_label_y = qr_y + qr_size + 3
                if qr_label_y < self.label_height - margin_bottom:
                    draw.text((qr_x + 15, qr_label_y), "扫码", fill='gray', font=font_small)

            # 添加边框 (可选)
            border_width = 1
            draw.rectangle([
                (border_width, border_width),
                (self.label_width - border_width, self.label_height - border_width)
            ], outline='lightgray', width=border_width)

            logger.debug(f"默认标签图像生成完成: {battery_code}")
            return image

        except Exception as e:
            logger.error(f"生成默认标签图像失败: {e}")
            # 返回错误标签
            return self._generate_error_label(str(e))

    def _generate_qr_code(self, data: str) -> Optional[Image.Image]:
        """生成二维码"""
        try:
            logger.debug(f"开始生成二维码，数据: '{data}'")

            if not data or data.strip() == '':
                logger.warning("二维码数据为空，使用默认数据")
                data = "TEST-QR-CODE"

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.ERROR_CORRECT_L,
                box_size=3,
                border=1,
            )
            qr.add_data(data)
            qr.make(fit=True)

            qr_image = qr.make_image(fill_color="black", back_color="white")
            logger.info(f"二维码生成成功，数据: '{data}', 图像尺寸: {qr_image.size}")
            return qr_image

        except Exception as e:
            logger.error(f"生成二维码失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return None

    def _get_batch_info(self) -> str:
        """获取批次信息"""
        try:
            batch_number = self.config_manager.get('batch_info.batch_number', '')
            operator = self.config_manager.get('batch_info.operator', '')

            if batch_number and operator:
                return f"{batch_number} ({operator})"
            elif batch_number:
                return batch_number
            else:
                return ""

        except Exception as e:
            logger.error(f"获取批次信息失败: {e}")
            return ""

    def _generate_error_label(self, error_msg: str) -> Image.Image:
        """生成错误标签"""
        image = Image.new('RGB', (self.label_width, self.label_height), 'white')
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()

        draw.text((10, 10), "标签生成错误", fill='red', font=font)
        draw.text((10, 30), error_msg[:50], fill='black', font=font)

        return image


class LabelPrintManager(QObject):
    """标签打印管理器"""

    # 信号定义
    print_started = pyqtSignal(str)  # 打印开始信号 (job_id)
    print_completed = pyqtSignal(str, bool, str)  # 打印完成信号 (job_id, success, message)
    print_queue_updated = pyqtSignal(int)  # 打印队列更新信号 (queue_size)

    def __init__(self, config_manager, printer_manager, parent=None):
        """
        初始化标签打印管理器

        Args:
            config_manager: 配置管理器
            printer_manager: 打印机管理器
            parent: 父对象
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.printer_manager = printer_manager

        # 打印队列
        self.print_queue = Queue()
        self.current_job = None
        self.job_counter = 0

        # 新增打印任务去重缓存
        self.printed_tasks = {}  # 存储已打印的任务，格式: {task_key: timestamp}
        self.cache_cleanup_interval = 3600  # 缓存清理间隔（秒）
        self.current_test_session = None  # 当前测试会话ID

        # 修复：添加强制停止标志
        self._force_stop_printing = False

        # 标签模板
        self.label_template = LabelTemplate(config_manager)

        # 打印处理定时器
        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self._process_print_queue)
        self.process_timer.start(1000)  # 每秒检查一次队列

        # 新增缓存清理定时器
        self.cache_cleanup_timer = QTimer()
        self.cache_cleanup_timer.timeout.connect(self._cleanup_print_cache)
        self.cache_cleanup_timer.start(self.cache_cleanup_interval * 1000)  # 每小时清理一次

        # 退出时停止定时器，避免 KeyboardInterrupt
        try:
            if parent and hasattr(parent, 'destroyed'):
                parent.destroyed.connect(self._stop_timers)
        except Exception:
            pass

        logger.debug("标签打印管理器初始化完成")

    def reload_template_config(self):
        """重新加载模板配置"""
        try:
            self.label_template._load_template_config()
            logger.info("标签模板配置已重新加载")
        except Exception as e:
            logger.error(f"重新加载模板配置失败: {e}")

    def clear_print_cache(self):
        """清理打印缓存（用于新测试开始时）"""
        try:
            old_count = len(self.printed_tasks)
            self.printed_tasks.clear()
            logger.debug(f" 打印缓存已清理，清除了{old_count}个缓存项")
        except Exception as e:
            logger.error(f"清理打印缓存失败: {e}")

    def start_new_test_session(self, session_id=None):
        """开始新的测试会话：清理去重缓存、重置当前任务与队列"""
        try:
            import time
            if session_id is None:
                session_id = int(time.time() * 1000)

            self.current_test_session = session_id
            # 清理旧的打印缓存
            old_count = len(self.printed_tasks)
            self.printed_tasks.clear()
            # 重置当前任务并清空队列
            self.current_job = None
            try:
                while not self.print_queue.empty():
                    self.print_queue.get_nowait()
            except Exception:
                pass

            # 修复：重置强制停止标志
            self._force_stop_printing = False

            logger.info(f"🚀 开始新的测试会话: {session_id}，已清理缓存{old_count}项并重置队列")
        except Exception as e:
            logger.error(f"开始新测试会话失败: {e}")

    def is_auto_print_enabled(self) -> bool:
        """检查是否启用自动打印"""
        return self.config_manager.get('label.auto_print', False)

    def is_printer_ready(self) -> bool:
        """检查打印机是否就绪"""
        return self.printer_manager.is_printer_ready()

    def print_test_result(self, test_result: Dict[str, Any], force_print: bool = False) -> Optional[str]:
        """
        打印测试结果标签

        Args:
            test_result: 测试结果数据
            force_print: 强制打印（忽略自动打印设置）

        Returns:
            任务ID，如果未添加到队列则返回None
        """
        try:
            logger.info(f"🖨️ [标签打印] 开始处理打印请求，force_print={force_print}")

            # 修复：检查测试是否被停止，如果停止则不添加打印任务
            if not force_print and self._is_test_stopped():
                logger.warning("🛑 测试已被停止，跳过打印任务，避免打印脏数据")
                return None

            # 检查是否应该打印
            auto_print_enabled = self.is_auto_print_enabled()
            logger.info(f"🖨️ [标签打印] 自动打印启用状态: {auto_print_enabled}")

            if not force_print and not auto_print_enabled:
                logger.warning("🖨️ [标签打印] 自动打印未启用，跳过打印")
                return None


            # 检查合格打印选项
            print_pass_only = self.config_manager.get('label.print_pass_only', False)
            if not force_print and print_pass_only:
                is_pass = test_result.get('is_pass', False)
                logger.info(f"🖨️ [标签打印] 合格打印模式: is_pass={is_pass}")
                if not is_pass:
                    logger.warning(f"🖨️ [标签打印] 不合格品，跳过打印")
                    return None

            # 检查打印机状态
            printer_ready = self.is_printer_ready()
            logger.info(f"🖨️ [标签打印] 打印机就绪状态: {printer_ready}")

            if not printer_ready:
                logger.warning("🖨️ [标签打印] 打印机未就绪，无法打印")
                return None

            # 不做去重：每次调用都直接入队打印
            logger.debug("🖨️ [标签打印] 已禁用去重，每次请求都会提交打印任务")

            # 兼容旧日志摘要
            channel_num = test_result.get('channel_number', 0)
            battery_code = test_result.get('battery_code', 'unknown')
            rs_value = test_result.get('rs_value', 0)
            rct_value = test_result.get('rct_value', 0)
            voltage = test_result.get('voltage', 0)

            # 生成任务ID
            self.job_counter += 1
            job_id = f"print_{self.job_counter}_{int(time.time())}"

            # 优化创建打印任务：优先使用当前打印机管理器的已连接名称，避免使用配置中的过期值
            current_printer_name = getattr(self.printer_manager, 'last_printer_name', '') or self.config_manager.get('printer.name', '')

            # 允许使用虚拟打印机：后续执行阶段会自动转为保存PDF/PNG文件
            upper_name = (current_printer_name or '').upper()

            print_config = {
                'printer_name': current_printer_name,
                'copies': self.config_manager.get('label_print.copies', 1),
                'quality': self.config_manager.get('printer.quality', '高质量'),
                'density': 'high',
                'contrast': 'high'
            }
            logger.debug(f"🖨️ [标签打印] 打印配置: {print_config}")

            job = PrintJob(job_id, test_result, print_config)

            # 添加到队列
            self.print_queue.put(job)

            logger.info(f"🖨️ [标签打印] 打印任务已入队: {job_id}, 队列长度={self.print_queue.qsize()}")
            logger.info(f"🧾 [标签打印] 任务摘要: CH={channel_num}, 电池码={battery_code}, V={voltage:.3f}V, Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")

            # 发送队列更新信号
            self.print_queue_updated.emit(self.print_queue.qsize())

            return job_id

        except Exception as e:
            logger.error(f"添加打印任务失败: {e}")
            return None

    def _generate_task_key(self, test_result: Dict[str, Any]) -> str:
        """
        生成打印任务的唯一标识键

        Args:
            test_result: 测试结果数据

        Returns:
            任务唯一标识键
        """
        try:
            # 修复使用更稳定的标识符，不依赖可能包含时间戳的电池码
            channel_num = test_result.get('channel_number', 0)
            rs_value = test_result.get('rs_value', 0)
            rct_value = test_result.get('rct_value', 0)
            voltage = test_result.get('voltage', 0)

            # 修复获取稳定的电池码标识符，但保留足够的区分度
            battery_code = test_result.get('battery_code', 'unknown')

            # 使用会话ID增强区分度，避免跨会话去重
            session_id = self.current_test_session or 0
            import time
            current_minute = int(time.time() // 60)  # 仍保留分钟级别辅助，兼容旧日志

            # 如果电池码包含时间戳（如CH1-1234567890格式），提取稳定部分但保留区分度
            if battery_code and ('-' in battery_code):
                # 检查是否是自动生成的格式（包含时间戳）
                parts = battery_code.split('-')
                if len(parts) >= 2 and parts[-1].isdigit() and len(parts[-1]) >= 8:
                    # 这是包含时间戳的自动生成电池码，使用通道号+分钟时间戳作为标识
                    stable_battery_id = f"CH{channel_num}_T{current_minute}"
                else:
                    stable_battery_id = battery_code
            else:
                stable_battery_id = battery_code

            # 生成基于稳定数据 + 会话ID 的唯一键，避免跨会话误判
            task_key = f"S{session_id}_{stable_battery_id}_{channel_num}_{rs_value:.3f}_{rct_value:.3f}_{voltage:.3f}"
            return task_key

        except Exception as e:
            logger.error(f"生成任务键失败: {e}")
            # 返回基于通道号的键作为备用
            channel_num = test_result.get('channel_number', 0)
            return f"fallback_CH{channel_num}"

    def _is_duplicate_task(self, task_key: str) -> bool:
        """
        检查是否为重复任务

        Args:
            task_key: 任务键

        Returns:
            是否为重复任务
        """
        try:
            import time
            current_time = time.time()

            # 检查缓存中是否存在该任务
            if task_key in self.printed_tasks:
                last_print_time = self.printed_tasks[task_key]
                # 将去重窗口进一步缩短到5秒，便于快速复测
                if current_time - last_print_time < 5:  # 5秒内视为重复
                    return True
                else:
                    return False

            return False

        except Exception as e:
            logger.error(f"检查重复任务失败: {e}")
            return False

    def _record_task(self, task_key: str, job_id: str):
        """
        记录已打印的任务

        Args:
            task_key: 任务键
            job_id: 任务ID
        """
        try:
            import time
            self.printed_tasks[task_key] = time.time()

        except Exception as e:
            logger.error(f"记录打印任务失败: {e}")

    def _cleanup_print_cache(self):
        """清理过期的打印缓存"""
        try:
            import time
            current_time = time.time()
            expired_keys = []

            # 查找过期的缓存项（超过1小时）
            for task_key, print_time in self.printed_tasks.items():
                if current_time - print_time > 3600:  # 1小时 = 3600秒
                    expired_keys.append(task_key)

            # 删除过期项
            for key in expired_keys:
                del self.printed_tasks[key]

            if expired_keys:
                logger.debug(f"清理了{len(expired_keys)}个过期的打印任务")

        except Exception as e:
            logger.error(f"清理打印缓存失败: {e}")

    def clear_print_cache_manual(self):
        """手动清理打印缓存"""
        try:
            self.printed_tasks.clear()

        except Exception as e:
            logger.error(f"清理打印缓存失败: {e}")

    def _process_print_queue(self):
        """处理打印队列（防中断版）"""
        try:
            # 如果当前有任务在处理，跳过
            if self.current_job is not None:
                return

            # 检查队列是否为空
            if self.print_queue.empty():
                logger.debug("🖨️ [标签打印] 队列为空，等待新任务")
                return

            # 修复：检查测试是否被停止，如果停止则清空打印队列
            if self._is_test_stopped():
                logger.warning("🛑 测试已被停止，清空打印队列，避免打印脏数据")
                self.clear_queue()
                return

            # 检查打印机状态
            if not self.is_printer_ready():
                logger.warning("打印机未就绪，暂停处理打印队列")
                return

            # 获取下一个任务
            try:
                job = self.print_queue.get_nowait()
                self.current_job = job

                logger.info(f"🖨️ [标签打印] 开始处理任务: {job.job_id}")
                logger.debug(f"🖨️ [标签打印] 当前队列长度: {self.print_queue.qsize()+1}")
                self.print_started.emit(job.job_id)

                # 执行打印
                self._execute_print_job(job)

            except Empty:
                # 队列为空
                pass

        except KeyboardInterrupt:
            logger.info("打印队列处理被中断，停止定时器")
            try:
                self._stop_timers()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"处理打印队列失败: {e}")
            if self.current_job:
                self._complete_job(self.current_job, False, str(e))
    def _stop_timers(self, *args, **kwargs):
        """停止所有定时器，防止退出时触发回调"""
        try:
            if hasattr(self, 'process_timer') and self.process_timer.isActive():
                self.process_timer.stop()
                logger.debug("打印队列处理定时器已停止")
            if hasattr(self, 'cache_cleanup_timer') and self.cache_cleanup_timer.isActive():
                self.cache_cleanup_timer.stop()
                logger.debug("缓存清理定时器已停止")
        except Exception:
            pass

    def _execute_print_job(self, job: PrintJob):
        """执行打印任务"""
        try:
            # 修复：在执行打印前再次检查测试是否被停止
            if self._is_test_stopped():
                logger.warning(f"🛑 测试已被停止，中断打印任务: {job.job_id}")
                self._complete_job(job, False, "测试已停止，打印任务被中断")
                return

            job.status = 'printing'

            # 生成标签图像
            label_image = self.label_template.generate_label_image(job.test_result)
            logger.debug(f"🖼️ [标签打印] 图像生成完成，尺寸={label_image.size}")

            # 修复：在执行实际打印前再次检查测试是否被停止
            if self._is_test_stopped():
                logger.warning(f"🛑 测试已被停止，中断打印任务: {job.job_id}（图像已生成）")
                self._complete_job(job, False, "测试已停止，打印任务被中断")
                return

            # 执行打印或虚拟输出
            printer_name = job.print_config.get('printer_name', '')
            upper_printer = (printer_name or '').upper()
            if any(x in upper_printer for x in ['PDF', 'XPS', 'WPS']):
                logger.debug("🖨️ [标签打印] 检测到虚拟打印机，切换为保存文件模式")
                success = self._virtual_save_label(label_image, job)
            else:
                logger.debug(f"🖨️ [标签打印] 调用底层打印，配置={job.print_config}")
                success = self._print_image_to_printer(label_image, job.print_config)

            if success:
                self._complete_job(job, True, "打印成功")
            else:
                self._complete_job(job, False, "打印失败")

        except Exception as e:
            logger.error(f"执行打印任务失败: {e}")
            self._complete_job(job, False, str(e))

    def _print_image_to_printer(self, image: Image.Image, print_config: Dict[str, Any]) -> bool:
        """将图像打印到打印机 - 使用win32print直接打印"""
        try:
            printer_name = print_config.get('printer_name', '')
            if not printer_name:
                logger.error("🖨️ [标签打印] 未配置打印机名称")
                return False
            logger.debug(f"🖨️ [标签打印] 使用打印机: {printer_name}")

            # 确保图像尺寸正确 (50x30mm @ 203 DPI = 400x240像素)
            target_width = 400
            target_height = 240

            if image.size != (target_width, target_height):
                logger.debug(f"🖼️ [标签打印] 调整图像尺寸: {image.size} -> {(target_width, target_height)}")
                image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
                logger.debug(f"图像已调整为: {target_width}x{target_height}")

            # 使用win32print直接打印
            success = self._print_with_win32(image, printer_name)

            if success:
                logger.info(f"标签打印成功: {printer_name}")
            else:
                logger.error(f"标签打印失败: {printer_name}")

            return success
        except Exception as e:
            logger.error(f"打印图像失败: {e}")
            return False

    def _virtual_save_label(self, image: Image.Image, job: PrintJob) -> bool:
        """将标签图像保存为文件，模拟虚拟打印（避免StartDoc失败和纸张浪费）"""
        try:
            import os
            from datetime import datetime
            # 输出目录
            out_dir = os.path.join(os.getcwd(), 'output', 'virtual_prints')
            os.makedirs(out_dir, exist_ok=True)

            # 生成文件名，包含通道与电池码
            tr = job.test_result or {}
            ch = tr.get('channel_number', 'X')
            bc = str(tr.get('battery_code', 'unknown'))
            # 简单清理文件名非法字符
            safe_bc = ''.join(c for c in bc if c.isalnum() or c in ('-', '_'))[:40] or 'unknown'
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')

            # 对于PDF虚拟打印机输出PDF，否则输出PNG
            printer = (job.print_config.get('printer_name', '') or '').upper()
            if 'PDF' in printer or 'XPS' in printer:
                file_path = os.path.join(out_dir, f'label_CH{ch}_{safe_bc}_{ts}.pdf')
                # 确保为RGB再保存PDF
                img_rgb = image.convert('RGB')
                img_rgb.save(file_path, 'PDF', resolution=203.0)
            else:
                file_path = os.path.join(out_dir, f'label_CH{ch}_{safe_bc}_{ts}.png')
                image.save(file_path, 'PNG')

            logger.info(f"🖨️ [虚拟打印] 标签已保存: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存虚拟打印文件失败: {e}")
            return False

        except Exception as e:
            logger.error(f"打印图像失败: {e}")
            return False

    def _print_with_win32(self, image: Image.Image, printer_name: str) -> bool:
        """使用win32print直接打印图像"""
        try:
            # 导入必要的模块
            import win32print
            import win32ui
            from PIL import ImageWin

            logger.debug(f"开始win32print打印: {printer_name}")

            # 修复检查打印机是否存在，使用精确匹配
            try:
                printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
                printer_found = False
                available_printers = []

                for printer in printers:
                    available_printer_name = printer[2]
                    available_printers.append(available_printer_name)

                    # 首先尝试精确匹配
                    if printer_name == available_printer_name:
                        printer_found = True
                        break
                    # 修复如果配置的打印机名称包含后缀（如"(默认)"），尝试去除后缀匹配
                    elif printer_name.endswith(' (默认)'):
                        base_name = printer_name.replace(' (默认)', '')
                        if base_name == available_printer_name:
                            printer_found = True
                            # 更新printer_name为实际的打印机名称
                            printer_name = available_printer_name
                            break

                if not printer_found:
                    logger.error(f"🔧 未找到打印机: {printer_name}")
                    logger.error(f"🔧 可用打印机列表: {available_printers}")

                    # 如果是PDF/XPS等虚拟打印机，明确拒绝，避免StartDoc失败
                    if "PDF" in printer_name.upper() or "XPS" in printer_name.upper() or "WPS" in printer_name.upper():
                        logger.error(f"🖨️ [标签打印] 目标打印机是虚拟打印机 '{printer_name}'，请在设置中选择真实标签机（如Gprinter）")
                        return False
                    else:
                        return False
                else:
                    printer_found = True

            except Exception as e:
                logger.error(f"检查打印机失败: {e}")
                return False

            # 获取打印机设备上下文
            hprinter = win32print.OpenPrinter(printer_name)
            logger.debug(f"打印机句柄获取成功: {printer_name}")

            # 创建设备上下文
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)

            # 开始打印作业
            hdc.StartDoc("JCY5001AS 50x30mm标签")
            hdc.StartPage()

            # 获取打印机分辨率
            printer_width = hdc.GetDeviceCaps(110)  # HORZRES
            printer_height = hdc.GetDeviceCaps(111)  # VERTRES

            logger.debug(f"打印机分辨率: {printer_width}x{printer_height}")

            # 50x30mm @ 203 DPI = 400x240像素
            target_width = 400
            target_height = 240

            # 居中打印
            x = (printer_width - target_width) // 2
            y = (printer_height - target_height) // 2

            # 打印图像
            dib = ImageWin.Dib(image)
            dib.draw(hdc.GetHandleOutput(), (x, y, x + target_width, y + target_height))

            # 结束打印
            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()
            win32print.ClosePrinter(hprinter)

            logger.info(f"win32print打印完成: {printer_name}")
            return True

        except ImportError as e:
            logger.error(f"缺少win32print模块: {e}")
            return False
        except Exception as e:
            logger.error(f"win32print打印失败: {e}")
            return False



    def _complete_job(self, job: PrintJob, success: bool, message: str):
        """完成打印任务"""
        try:
            job.status = 'completed' if success else 'failed'
            job.error_message = None if success else message

            logger.info(f"打印任务完成: {job.job_id}, 成功: {success}, 消息: {message}")

            # 发送完成信号
            self.print_completed.emit(job.job_id, success, message)

            # 清除当前任务
            self.current_job = None

            # 更新队列大小信号
            self.print_queue_updated.emit(self.print_queue.qsize())

        except Exception as e:
            logger.error(f"完成打印任务失败: {e}")
            self.current_job = None

    def get_queue_size(self) -> int:
        """获取打印队列大小"""
        return self.print_queue.qsize()

    def clear_queue(self):
        """清空打印队列"""
        try:
            while not self.print_queue.empty():
                try:
                    self.print_queue.get_nowait()
                except Empty:
                    break

            logger.info("打印队列已清空")
            self.print_queue_updated.emit(0)

        except Exception as e:
            logger.error(f"清空打印队列失败: {e}")

    def get_print_status(self) -> Dict[str, Any]:
        """获取打印状态"""
        return {
            'queue_size': self.get_queue_size(),
            'current_job': self.current_job.job_id if self.current_job else None,
            'printer_ready': self.is_printer_ready(),
            'auto_print_enabled': self.is_auto_print_enabled()
        }

    def _is_test_stopped(self) -> bool:
        """检查测试是否被停止"""
        try:
            # 修复：优先检查强制停止标志
            if hasattr(self, '_force_stop_printing') and self._force_stop_printing:
                logger.debug("🔍 检测到强制停止打印标志")
                return True

            # 检查主窗口的测试状态
            if hasattr(self, 'parent') and self.parent:
                main_window = self.parent

                # 优先检查主窗口的测试状态
                if hasattr(main_window, 'is_testing') and not main_window.is_testing:
                    logger.debug("🔍 检测到主窗口测试状态为停止")
                    return True

                # 检查测试执行器的停止事件
                if hasattr(main_window, 'test_executor') and main_window.test_executor:
                    if hasattr(main_window.test_executor, 'stop_event') and main_window.test_executor.stop_event.is_set():
                        logger.debug("🔍 检测到测试执行器停止事件")
                        return True

                # 检查统一测试控制器的停止事件
                if hasattr(main_window, 'unified_test_controller') and main_window.unified_test_controller:
                    if hasattr(main_window.unified_test_controller, 'stop_event') and main_window.unified_test_controller.stop_event.is_set():
                        logger.debug("🔍 检测到统一测试控制器停止事件")
                        return True

                # 检查测试流程管理器的状态
                if hasattr(main_window, 'test_flow_manager') and main_window.test_flow_manager:
                    if hasattr(main_window.test_flow_manager, 'is_testing') and not main_window.test_flow_manager.is_testing:
                        logger.debug("🔍 检测到测试流程管理器停止状态")
                        return True

            return False

        except Exception as e:
            logger.error(f"检查测试停止状态失败: {e}")
            return False

    def handle_test_stopped(self):
        """处理测试停止事件"""
        try:
            logger.info("🛑 测试停止，清理打印队列")

            # 修复：立即设置强制停止标志
            self._force_stop_printing = True

            # 清空打印队列
            self.clear_queue()

            # 停止当前打印任务（如果有）
            if self.current_job:
                logger.warning(f"🛑 测试停止，中断当前打印任务: {self.current_job.job_id}")
                self.current_job = None

            logger.info("✅ 打印队列清理完成")

        except Exception as e:
            logger.error(f"处理测试停止失败: {e}")
