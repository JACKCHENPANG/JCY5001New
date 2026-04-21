# -*- coding: utf-8 -*-
"""
通道测试完成管理器
负责单个通道的测试完成状态管理，包括结果设置、显示更新、信号发送等

Author: Jack
Date: 2025-06-27
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal

# 导入统一的失败结果显示工具类
from ui.utils.fail_result_display_utils import FailResultDisplayUtils

logger = logging.getLogger(__name__)


class ChannelTestCompletionManager(QObject):
    """通道测试完成管理器"""
    
    # 信号定义
    test_completed = pyqtSignal(int, dict)  # 测试完成信号 (channel, result)
    statistics_update_requested = pyqtSignal(bool, int, int)  # 统计更新信号 (is_pass, rs_grade, rct_grade)
    
    def __init__(self, channel_number: int, parent=None):
        """
        初始化测试完成管理器
        
        Args:
            channel_number: 通道号
            parent: 父对象
        """
        super().__init__(parent)
        
        self.channel_number = channel_number
        
        # 测试完成状态
        self._test_completed = False
        self.test_result = None
        self._last_test_data = None
        
        # UI元素引用
        self.grade_label = None
        self.result_label = None
        self.progress_bar = None
        self.scan_button = None
        
    def set_ui_elements(self, ui_elements: dict):
        """
        设置UI元素引用
        
        Args:
            ui_elements: UI元素字典
        """
        self.grade_label = ui_elements.get('grade_label')
        self.result_label = ui_elements.get('result_label')
        self.progress_bar = ui_elements.get('progress_bar')
        self.scan_button = ui_elements.get('scan_button')
        
    def set_test_completed(self, is_pass: bool, rs_grade: int, rct_grade: int, 
                          voltage: float, rs_value: float, rct_value: float,
                          battery_code: str, fail_items: Optional[list] = None,
                          outlier_data: Optional[dict] = None) -> dict:
        """
        设置测试完成状态

        Args:
            is_pass: 是否合格
            rs_grade: Rs档位
            rct_grade: Rct档位
            voltage: 电压值
            rs_value: Rs值
            rct_value: Rct值
            battery_code: 电池码
            fail_items: 失败项目列表，如 ["电压", "Rs", "Rct"]
            outlier_data: 离群检测数据

        Returns:
            测试结果字典
        """
        try:
            # 防止重复设置测试完成状态
            if self._test_completed:
                logger.warning(f"通道{self.channel_number}测试已完成，跳过重复设置")
                return self.test_result

            # 标记测试已完成
            self._test_completed = True

            logger.info(f"通道{self.channel_number}设置测试完成状态: {'合格' if is_pass else '不合格'}, Rs档位={rs_grade}, Rct档位={rct_grade}")

            # 🎯 使用统一档位管理器更新UI显示
            self._update_completion_display_unified(is_pass, rs_grade, rct_grade, fail_items)

            # 构建测试结果数据
            self.test_result = self._build_test_result_data(
                is_pass, rs_grade, rct_grade, voltage, rs_value, rct_value,
                battery_code, fail_items, outlier_data
            )

            # 保存最近的测试数据供打印使用
            self._last_test_data = {
                'is_pass': is_pass,
                'rs_grade': rs_grade,
                'rct_grade': rct_grade,
                'voltage': voltage,
                'rs_value': rs_value,
                'rct_value': rct_value,
                'fail_items': fail_items if fail_items else [],
                'fail_reason': self._generate_fail_reason_text(fail_items) if fail_items else ''
            }
            
            logger.info(f"通道{self.channel_number}保存最近测试数据: Rs档位={rs_grade}, Rct档位={rct_grade}, 合格={is_pass}")

            # 发送统计更新信号
            self.statistics_update_requested.emit(is_pass, rs_grade, rct_grade)

            # 发送测试完成信号
            self.test_completed.emit(self.channel_number, self.test_result)

            logger.info(f"通道{self.channel_number}测试完成状态已设置: {'合格' if is_pass else '不合格'}, 档位{rs_grade}-{rct_grade}")

            return self.test_result

        except Exception as e:
            logger.error(f"通道{self.channel_number}设置测试完成状态失败: {e}")
            return {}

    def _update_completion_display_unified(self, is_pass: bool, rs_grade: int, rct_grade: int, fail_items: Optional[list]):
        """使用统一档位管理器更新完成状态显示（修复临时组件问题）"""
        try:
            logger.debug(f"🔍 [完成管理器] 通道{self.channel_number} 使用统一档位管理器...")

            from utils.grade_manager import get_grade_manager
            grade_manager = get_grade_manager()

            # 🎯 修复：创建真实组件对象，包含完整的样式上下文
            real_widget = type('RealChannelWidget', (), {
                'grade_label': self.grade_label,
                'result_label': self.result_label,
                'channel_number': self.channel_number  # 添加通道号
            })()

            # 🎯 修复：直接使用统一档位管理器的内部方法，避免查找组件的问题
            success = grade_manager._update_widget_display(real_widget, rs_grade, rct_grade, is_pass)

            if success:
                logger.info(f"✅ [完成管理器] 通道{self.channel_number} 统一更新成功")
            else:
                logger.warning(f"⚠️ [完成管理器] 通道{self.channel_number} 统一更新失败，使用备用方法")
                # 备用方案
                self._update_completion_display_fallback(is_pass, rs_grade, rct_grade, fail_items)

            # 其他UI更新
            if self.progress_bar:
                self.progress_bar.setValue(100)
            if self.scan_button:
                self.scan_button.setEnabled(True)

        except Exception as e:
            logger.error(f"通道{self.channel_number}统一更新完成状态显示失败: {e}")
            # 备用方案
            self._update_completion_display_fallback(is_pass, rs_grade, rct_grade, fail_items)

    def _update_completion_display_fallback(self, is_pass: bool, rs_grade: int, rct_grade: int, fail_items: Optional[list]):
        """备用完成状态显示更新（统一样式版本）"""
        try:
            if not self.grade_label or not self.result_label:
                logger.warning(f"通道{self.channel_number}UI元素未设置，无法更新显示")
                return

            # 🎯 使用统一显示管理器（按照第一次运行时的标准模式）
            from utils.unified_display_manager import set_channel_display_unified

            success = set_channel_display_unified(
                self.grade_label,
                self.result_label,
                is_pass,
                rs_grade,
                rct_grade
            )

            if success:
                if is_pass and rs_grade is not None and rct_grade is not None and rs_grade != 0 and rct_grade != 0:
                    logger.debug(f"✅ [完成管理器] 通道{self.channel_number} 档位显示: {rs_grade}-{rct_grade}")
                else:
                    logger.debug(f"✅ [完成管理器] 通道{self.channel_number} 显示: 不合格")
            else:
                logger.warning(f"⚠️ [完成管理器] 通道{self.channel_number} 统一显示管理器失败")

        except Exception as e:
            logger.error(f"通道{self.channel_number}备用更新完成状态显示失败: {e}")

    def _apply_unified_style_fallback(self, widget):
        """应用统一样式（备用方法 - 修复字体一致性）"""
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

            logger.debug(f"🎯 [备用样式修复] 组件样式已刷新: ObjectName='{widget.objectName()}'")

        except Exception as e:
            logger.error(f"❌ [备用样式] 应用统一样式失败: {e}")

    def _get_grades_from_database(self) -> tuple:
        """
        从数据库获取最新的档位数据

        Returns:
            (rs_grade, rct_grade, is_pass) 或 (None, None, None) 如果没有数据
        """
        try:
            # 直接创建数据库管理器
            from data.database_manager import DatabaseManager
            database_manager = DatabaseManager()

            # 获取该通道的最新测试结果
            test_results = database_manager.get_test_results(
                channel_number=self.channel_number,
                limit=1
            )

            if test_results and len(test_results) > 0:
                result = test_results[0]
                rs_grade = result.get('rs_grade')
                rct_grade = result.get('rct_grade')
                is_pass = result.get('is_pass', False)

                logger.debug(f"🔍 [完成管理器] 通道{self.channel_number} 从数据库获取档位: Rs={rs_grade}, Rct={rct_grade}, 合格={is_pass}")
                return rs_grade, rct_grade, is_pass
            else:
                logger.debug(f"🔍 [完成管理器] 通道{self.channel_number} 数据库中无测试结果")
                return None, None, None

        except Exception as e:
            logger.error(f"❌ [完成管理器] 通道{self.channel_number} 从数据库获取档位失败: {e}")
            return None, None, None

    def _build_test_result_data(self, is_pass: bool, rs_grade: int, rct_grade: int,
                               voltage: float, rs_value: float, rct_value: float,
                               battery_code: str, fail_items: Optional[list],
                               outlier_data: Optional[dict]) -> dict:
        """构建测试结果数据"""
        try:
            # 处理离群检测数据
            if outlier_data is None:
                outlier_data = {}

            outlier_result = outlier_data.get('outlier_result', '--')
            frequency_deviations = outlier_data.get('frequency_deviations', {})
            max_deviation_percent = outlier_data.get('max_deviation_percent', 0.0)
            baseline_filename = outlier_data.get('baseline_filename', '')
            baseline_id = outlier_data.get('baseline_id', None)

            test_result = {
                'is_pass': is_pass,
                'rs_grade': rs_grade,
                'rct_grade': rct_grade,
                'voltage': voltage,
                'rs': rs_value,  # 保持原有字段名
                'rct': rct_value,  # 保持原有字段名
                'rs_value': rs_value,  # 兼容打印模块的字段名
                'rct_value': rct_value,  # 兼容打印模块的字段名
                'battery_code': battery_code,
                'channel_number': self.channel_number,
                'test_time': datetime.now().isoformat(),
                'rct_coefficient_of_variation': 0.0,  # 可以从外部传入
                # 离群率相关数据
                'outlier_result': outlier_result,
                'outlier_rate': outlier_result,  # 兼容字段名
                'frequency_deviations': frequency_deviations,
                'max_deviation_percent': max_deviation_percent,
                'baseline_filename': baseline_filename,
                'baseline_id': baseline_id,
                # 失败原因信息
                'fail_items': fail_items if fail_items else [],
                'fail_reason': self._generate_fail_reason_text(fail_items) if fail_items else ''
            }

            return test_result

        except Exception as e:
            logger.error(f"通道{self.channel_number}构建测试结果数据失败: {e}")
            return {}

    def _get_fail_result_display(self, fail_items: Optional[list]) -> tuple:
        """
        获取失败结果显示文本和样式（统一使用channel_display_widget的逻辑）

        注意：此方法应与channel_display_widget._get_fail_result_display保持一致

        Args:
            fail_items: 失败项目列表

        Returns:
            (显示文本, 样式名称)
        """
        if not fail_items:
            return "不合格", "resultFail"

        # 🔧 统一使用失败结果显示工具类
        return FailResultDisplayUtils.get_fail_result_display(fail_items)

    def _generate_fail_reason_text(self, fail_items: list) -> str:
        """
        生成失败原因文本

        Args:
            fail_items: 失败项目列表

        Returns:
            失败原因文本
        """
        if not fail_items:
            return ''

        if len(fail_items) == 1:
            return f"不合格-{fail_items[0]}"
        else:
            return f"不合格-{'/'.join(fail_items[:2])}"  # 最多显示前两个失败项目

    def trigger_result_display(self, is_pass: bool, rs_grade: int, rct_grade: int, fail_items: Optional[list] = None):
        """
        由容器触发的结果显示方法

        Args:
            is_pass: 是否合格
            rs_grade: Rs档位
            rct_grade: Rct档位
            fail_items: 失败项目列表
        """
        try:
            logger.debug(f"通道{self.channel_number} 容器触发结果显示: {'合格' if is_pass else '不合格'}")
            # 只更新显示，不重新构建完整的测试结果
            self._update_completion_display(is_pass, rs_grade, rct_grade, fail_items)
        except Exception as e:
            logger.error(f"通道{self.channel_number}容器触发结果显示失败: {e}")

    def get_test_result(self) -> dict:
        """获取测试结果"""
        return self.test_result if self.test_result else {}

    def get_last_test_data(self) -> dict:
        """获取最近的测试数据"""
        return self._last_test_data if self._last_test_data else {}

    def is_test_completed(self) -> bool:
        """检查测试是否已完成"""
        return self._test_completed

    def reset_completion_state(self):
        """重置完成状态"""
        self._test_completed = False
        self.test_result = None
        self._last_test_data = None

        # 重置UI显示为默认状态
        if self.grade_label:
            self.grade_label.setText("--")
            self.grade_label.setObjectName("gradeDisplay")  # 修复设置正确的对象名
            self.grade_label.setStyleSheet("")  # 重新应用样式
            self.grade_label.setVisible(True)  # 确保可见
        if self.result_label:
            self.result_label.setText("待测试")  # 修复设置为待测试状态
            self.result_label.setObjectName("resultWaiting")  # 修复设置正确的对象名
            self.result_label.setStyleSheet("")  # 重新应用样式
            self.result_label.setVisible(True)  # 确保可见
        if self.progress_bar:
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)  # 确保可见

        logger.debug(f"通道{self.channel_number}测试完成状态已重置")
