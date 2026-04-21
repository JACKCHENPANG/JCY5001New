# -*- coding: utf-8 -*-
"""
配置变更管理器
负责处理各种配置变更事件，包括档位设置、产品信息、通用设置等的变更处理

Author: Jack
Date: 2025-06-27
"""

import logging
from typing import Any, Dict, List
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ConfigChangeManager(QObject):
    """配置变更管理器"""
    
    # 信号定义
    config_processed = pyqtSignal(str, object)  # 配置处理完成信号 (key, value)
    config_error = pyqtSignal(str, str)  # 配置处理错误信号 (key, error_message)
    
    def __init__(self, main_window, config_manager, parent=None):
        """
        初始化配置变更管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
            parent: 父对象
        """
        super().__init__(parent)
        
        self.main_window = main_window
        self.config_manager = config_manager
        
        # 配置处理器映射
        self.config_handlers = {
            'label_template.': self._handle_label_template_config_changed,
            'grade_settings.': self._handle_grade_settings_changed,
            'product_info.': self._handle_product_info_changed,
            'general.': self._handle_general_settings_changed,
            'channel_enable.': self._handle_channel_enable_changed,
            'probe_pin.': self._handle_probe_pin_settings_changed,
            'outlier_detection.': self._handle_outlier_detection_config_changed,
            'test_count.': self._handle_test_count_changed,
            'test_mode.': self._handle_test_mode_config_changed,
        }
        
    def initialize(self):
        """初始化配置变更管理器"""
        try:
            # 连接配置变更信号
            self.config_manager.config_changed.connect(self.handle_config_changed)
            
            logger.debug("配置变更管理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化配置变更管理器失败: {e}")

    def handle_config_changed(self, key: str, value: Any):
        """处理配置变更"""
        try:
            logger.debug(f"处理配置变更: {key} = {value}")
            
            # 查找匹配的处理器
            handler = None
            for prefix, handler_func in self.config_handlers.items():
                if key.startswith(prefix):
                    handler = handler_func
                    break
            
            if handler:
                # 调用对应的处理器
                handler(key, value)
                self.config_processed.emit(key, value)
            else:
                logger.debug(f"未找到配置处理器: {key}")
                
        except Exception as e:
            logger.error(f"处理配置变更失败: {key} = {value}, 错误: {e}")
            self.config_error.emit(key, str(e))

    def _handle_label_template_config_changed(self, key: str, value: Any):
        """处理标签模板配置变更"""
        try:
            logger.debug(f"标签模板配置变更: {key} = {value}")
            
            # 通知打印管理器重新加载模板配置
            if hasattr(self.main_window, 'print_manager'):
                print_manager = self.main_window.print_manager
                if hasattr(print_manager, 'reload_template_config'):
                    print_manager.reload_template_config()
                    logger.info("打印管理器模板配置已重新加载")
                    
        except Exception as e:
            logger.error(f"处理标签模板配置变更失败: {e}")

    def _handle_grade_settings_changed(self, key: str, value: Any):
        """处理档位设置变更"""
        try:
            logger.debug(f"档位设置变更: {key} = {value}")

            # 🔧 关键修复：检查是否为强制应用信号
            if key == 'grade_settings.force_apply' and value:
                logger.info("🔄 收到强制应用判断设置信号，开始强制应用...")
                self._force_apply_grade_settings_immediately()
                return

            # 更新所有通道的档位设置
            self._update_all_channels_grade_settings()

            # 更新测试判定管理器
            if hasattr(self.main_window, 'test_judgment_manager'):
                test_judgment_manager = self.main_window.test_judgment_manager
                if hasattr(test_judgment_manager, 'reload_grade_settings'):
                    test_judgment_manager.reload_grade_settings()
                    logger.info("测试判定管理器档位设置已重新加载")

            # 新增更新失败原因管理器配置
            if hasattr(self.main_window, 'failure_reason_manager'):
                failure_reason_manager = self.main_window.failure_reason_manager
                if hasattr(failure_reason_manager, 'reload_config'):
                    failure_reason_manager.reload_config()
                    logger.info("失败原因管理器配置已重新加载")

            # 新增通过测试执行器更新失败原因管理器
            if hasattr(self.main_window, 'test_executor'):
                test_executor = self.main_window.test_executor
                if hasattr(test_executor, 'failure_reason_manager'):
                    failure_manager = test_executor.failure_reason_manager
                    if hasattr(failure_manager, 'reload_config'):
                        failure_manager.reload_config()
                        logger.info("测试执行器中的失败原因管理器配置已重新加载")

        except Exception as e:
            logger.error(f"处理档位设置变更失败: {e}")

    def _force_apply_grade_settings_immediately(self):
        """立即强制应用判断设置"""
        try:
            logger.info("🔄 立即强制应用判断设置...")

            # 方法1：如果设置对话框已打开，直接应用
            if hasattr(self.main_window, 'settings_dialog') and self.main_window.settings_dialog:
                settings_dialog = self.main_window.settings_dialog
                if hasattr(settings_dialog, 'grade_settings_widget') and settings_dialog.grade_settings_widget:
                    grade_widget = settings_dialog.grade_settings_widget
                    if hasattr(grade_widget, 'apply_settings'):
                        grade_widget.apply_settings()
                        logger.info("✅ 通过设置对话框立即应用判断设置成功")

            # 方法2：强制重新加载所有相关组件
            self._update_all_channels_grade_settings()

            # 强制重新加载测试结果管理器
            if hasattr(self.main_window, 'test_flow_manager') and self.main_window.test_flow_manager:
                test_flow_manager = self.main_window.test_flow_manager
                if hasattr(test_flow_manager, 'test_result_manager') and test_flow_manager.test_result_manager:
                    test_result_manager = test_flow_manager.test_result_manager
                    if hasattr(test_result_manager, 'reload_config'):
                        test_result_manager.reload_config()
                        logger.info("✅ 测试结果管理器配置已强制重新加载")

            # 强制重新加载测试判定管理器
            if hasattr(self.main_window, 'test_judgment_manager'):
                test_judgment_manager = self.main_window.test_judgment_manager
                if hasattr(test_judgment_manager, 'reload_grade_settings'):
                    test_judgment_manager.reload_grade_settings()
                    logger.info("✅ 测试判定管理器已强制重新加载")

            logger.info("✅ 判断设置立即强制应用完成")

        except Exception as e:
            logger.error(f"❌ 立即强制应用判断设置失败: {e}")

    def _handle_product_info_changed(self, key: str, value: Any):
        """处理产品信息变更"""
        try:
            logger.debug(f"产品信息变更: {key} = {value}")
            
            # 更新窗口标题
            if key == 'product_info.product_name':
                self._update_window_title(value)
            
            # 更新头部组件显示
            self._update_header_product_info()
            
            # 更新关于对话框信息
            self._update_about_dialog_info()
            
        except Exception as e:
            logger.error(f"处理产品信息变更失败: {e}")

    def _handle_general_settings_changed(self, key: str, value: Any):
        """处理通用设置变更"""
        try:
            logger.debug(f"通用设置变更: {key} = {value}")
            
            # 重新加载通用设置
            self._reload_general_settings()
            
            # 更新UI显示
            self._update_ui_for_general_settings()
            
        except Exception as e:
            logger.error(f"处理通用设置变更失败: {e}")

    def _handle_channel_enable_changed(self, key: str, value: Any):
        """处理通道使能变更"""
        try:
            logger.debug(f"通道使能变更: {key} = {value}")
            
            # 更新通道显示状态
            if isinstance(value, (list, tuple)):
                enabled_channels = value
            else:
                enabled_channels = self.config_manager.get('channel_enable.enabled_channels', [1, 2, 3, 4, 5, 6, 7, 8])
            
            self._update_channels_enable_state(enabled_channels)
            
        except Exception as e:
            logger.error(f"处理通道使能变更失败: {e}")

    def _handle_probe_pin_settings_changed(self, key: str, value: Any):
        """处理顶针寿命设置变更"""
        try:
            logger.debug(f"顶针寿命设置变更: {key} = {value}")
            
            # 更新顶针寿命管理器
            if hasattr(self.main_window, 'probe_pin_manager'):
                probe_pin_manager = self.main_window.probe_pin_manager
                if hasattr(probe_pin_manager, 'reload_settings'):
                    probe_pin_manager.reload_settings()
                    logger.info("顶针寿命管理器设置已重新加载")
                    
        except Exception as e:
            logger.error(f"处理顶针寿命设置变更失败: {e}")

    def _handle_outlier_detection_config_changed(self, key: str, value: Any):
        """处理离群检测配置变更"""
        try:
            logger.debug(f"离群检测配置变更: {key} = {value}")
            
            # 更新离群检测状态
            if key == 'outlier_detection.enabled':
                self._update_outlier_detection_status(value)
            
            # 更新离群检测管理器
            if hasattr(self.main_window, 'outlier_detection_manager'):
                outlier_manager = self.main_window.outlier_detection_manager
                if hasattr(outlier_manager, 'reload_config'):
                    outlier_manager.reload_config()
                    logger.info("离群检测管理器配置已重新加载")
                    
        except Exception as e:
            logger.error(f"处理离群检测配置变更失败: {e}")

    def _handle_test_count_changed(self, key: str, value: Any):
        """处理测试计数变更"""
        try:
            logger.debug(f"测试计数变更: {key} = {value}")
            
            # 更新统计组件显示
            if hasattr(self.main_window, 'statistics_widget'):
                statistics_widget = self.main_window.statistics_widget
                if hasattr(statistics_widget, 'update_test_count_settings'):
                    statistics_widget.update_test_count_settings()
                    logger.info("统计组件测试计数设置已更新")
                    
        except Exception as e:
            logger.error(f"处理测试计数变更失败: {e}")

    def _handle_test_mode_config_changed(self, key: str, value: Any):
        """处理测试模式配置变更"""
        try:
            logger.debug(f"测试模式配置变更: {key} = {value}")
            
            # 更新测试流程管理器
            if hasattr(self.main_window, 'test_flow_manager'):
                test_flow_manager = self.main_window.test_flow_manager
                if hasattr(test_flow_manager, 'reload_test_mode_config'):
                    test_flow_manager.reload_test_mode_config()
                    logger.info("测试流程管理器模式配置已重新加载")
                    
        except Exception as e:
            logger.error(f"处理测试模式配置变更失败: {e}")

    def _update_all_channels_grade_settings(self):
        """更新所有通道的档位设置"""
        try:
            if hasattr(self.main_window, 'channel_display_widget'):
                for channel_num in range(1, 9):
                    channel_widget = getattr(self.main_window.channel_display_widget, f'channel_{channel_num}', None)
                    if channel_widget and hasattr(channel_widget, 'update_grade_settings'):
                        channel_widget.update_grade_settings()
                        
                logger.info("所有通道档位设置已更新")
                
        except Exception as e:
            logger.error(f"更新所有通道档位设置失败: {e}")

    def _update_window_title(self, product_name: str):
        """更新窗口标题"""
        try:
            app_version = self.config_manager.get('app.version', 'V0.92.40')
            title = f"{product_name} {app_version}"
            self.main_window.setWindowTitle(title)
            logger.info(f"窗口标题已更新: {title}")
        except Exception as e:
            logger.error(f"更新窗口标题失败: {e}")

    def _update_header_product_info(self):
        """更新头部产品信息"""
        try:
            if hasattr(self.main_window, 'header_widget'):
                header_widget = self.main_window.header_widget
                if hasattr(header_widget, 'update_product_info'):
                    header_widget.update_product_info()
                    logger.info("头部产品信息已更新")
        except Exception as e:
            logger.error(f"更新头部产品信息失败: {e}")

    def _update_about_dialog_info(self):
        """更新关于对话框信息"""
        try:
            if hasattr(self.main_window, 'about_dialog'):
                about_dialog = self.main_window.about_dialog
                if hasattr(about_dialog, 'update_product_info'):
                    about_dialog.update_product_info()
                    logger.info("关于对话框信息已更新")
        except Exception as e:
            logger.error(f"更新关于对话框信息失败: {e}")

    def _reload_general_settings(self):
        """重新加载通用设置"""
        try:
            # 重新加载通用设置并应用
            logger.debug("重新加载通用设置")
        except Exception as e:
            logger.error(f"重新加载通用设置失败: {e}")

    def _update_ui_for_general_settings(self):
        """为通用设置更新UI"""
        try:
            # 更新UI以反映通用设置变更
            logger.debug("为通用设置更新UI")
        except Exception as e:
            logger.error(f"为通用设置更新UI失败: {e}")

    def _update_channels_enable_state(self, enabled_channels: List[int]):
        """更新通道启用状态"""
        try:
            if hasattr(self.main_window, 'channel_display_widget'):
                for channel_num in range(1, 9):
                    channel_widget = getattr(self.main_window.channel_display_widget, f'channel_{channel_num}', None)
                    if channel_widget:
                        enabled = channel_num in enabled_channels
                        if hasattr(channel_widget, 'set_channel_enabled'):
                            channel_widget.set_channel_enabled(enabled)
                            
                logger.info(f"通道启用状态已更新: {enabled_channels}")
                
        except Exception as e:
            logger.error(f"更新通道启用状态失败: {e}")

    def _update_outlier_detection_status(self, enabled: bool):
        """更新离群检测状态"""
        try:
            if hasattr(self.main_window, 'channel_display_widget'):
                for channel_num in range(1, 9):
                    channel_widget = getattr(self.main_window.channel_display_widget, f'channel_{channel_num}', None)
                    if channel_widget and hasattr(channel_widget, 'update_outlier_detection_status'):
                        channel_widget.update_outlier_detection_status(enabled)
                        
                logger.info(f"离群检测状态已更新: {'启用' if enabled else '禁用'}")
                
        except Exception as e:
            logger.error(f"更新离群检测状态失败: {e}")

    def register_config_handler(self, prefix: str, handler_func):
        """注册配置处理器"""
        try:
            self.config_handlers[prefix] = handler_func
            logger.debug(f"已注册配置处理器: {prefix}")
        except Exception as e:
            logger.error(f"注册配置处理器失败: {e}")

    def unregister_config_handler(self, prefix: str):
        """注销配置处理器"""
        try:
            if prefix in self.config_handlers:
                del self.config_handlers[prefix]
                logger.debug(f"已注销配置处理器: {prefix}")
        except Exception as e:
            logger.error(f"注销配置处理器失败: {e}")

    def get_registered_handlers(self) -> Dict[str, Any]:
        """获取已注册的处理器"""
        return self.config_handlers.copy()

    def force_reload_all_configs(self):
        """强制重新加载所有配置"""
        try:
            logger.info("强制重新加载所有配置")
            
            # 重新加载各种配置
            self._update_all_channels_grade_settings()
            self._update_header_product_info()
            self._reload_general_settings()
            
            # 获取当前启用的通道
            enabled_channels = self.config_manager.get('channel_enable.enabled_channels', [1, 2, 3, 4, 5, 6, 7, 8])
            self._update_channels_enable_state(enabled_channels)
            
            # 获取离群检测状态
            outlier_enabled = self.config_manager.get('outlier_detection.enabled', False)
            self._update_outlier_detection_status(outlier_enabled)
            
            logger.info("所有配置重新加载完成")
            
        except Exception as e:
            logger.error(f"强制重新加载所有配置失败: {e}")

    def cleanup(self):
        """清理资源"""
        try:
            # 清空配置处理器
            self.config_handlers.clear()
            
            logger.debug("配置变更管理器资源已清理")
            
        except Exception as e:
            logger.error(f"清理配置变更管理器资源失败: {e}")
