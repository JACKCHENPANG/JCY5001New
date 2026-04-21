# -*- coding: utf-8 -*-
"""
设置同步管理器
负责设置的同步、加载、保存等功能

Author: Jack
Date: 2025-06-27
"""

import logging
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

logger = logging.getLogger(__name__)


class SettingsSyncManager(QObject):
    """设置同步管理器"""
    
    # 信号定义
    sync_completed = pyqtSignal(str)  # 同步完成信号 (message)
    sync_failed = pyqtSignal(str, str)  # 同步失败信号 (sync_type, error_message)
    settings_loaded = pyqtSignal(dict)  # 设置加载完成信号 (settings)
    
    def __init__(self, main_window, config_manager, parent=None):
        """
        初始化设置同步管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
            parent: 父对象
        """
        super().__init__(parent)
        
        self.main_window = main_window
        self.config_manager = config_manager
        
        # 同步状态
        self.sync_in_progress = False
        self.last_sync_time = None
        
        # 设置同步定时器
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self._perform_periodic_sync)
        
    def initialize(self):
        """初始化设置同步管理器"""
        try:
            # 连接配置变更信号
            self.config_manager.config_changed.connect(self._on_config_changed)
            
            # 启动定期同步（如果启用）
            sync_interval = self.config_manager.get('settings.sync_interval_minutes', 0)
            if sync_interval > 0:
                self.sync_timer.start(sync_interval * 60 * 1000)  # 转换为毫秒
                logger.info(f"设置同步定时器已启动，间隔: {sync_interval}分钟")
            
            logger.debug("设置同步管理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化设置同步管理器失败: {e}")

    def _on_config_changed(self, key: str, value: Any):
        """配置变更处理"""
        try:
            # 根据配置键分发到不同的处理方法
            if key.startswith('label_template.'):
                self._handle_label_template_config_changed(key, value)
            elif key.startswith('grade_settings.'):
                self._handle_grade_settings_changed(key, value)
            elif key.startswith('product_info.'):
                self._handle_product_info_changed(key, value)
            elif key.startswith('general.'):
                self._handle_general_settings_changed(value)
            elif key.startswith('channel_enable.'):
                self._handle_channel_enable_changed(value)
            elif key.startswith('probe_pin.'):
                self._handle_probe_pin_settings_changed(key, value)
            elif key.startswith('outlier_detection.'):
                self._handle_outlier_detection_config_changed(key, value)
            elif key.startswith('test_count.'):
                self._handle_test_count_changed(key, value)
            elif key.startswith('test_mode.'):
                self._handle_test_mode_config_changed(key, value)
            else:
                logger.debug(f"未处理的配置变更: {key} = {value}")
                
        except Exception as e:
            logger.error(f"处理配置变更失败: {e}")

    def _handle_label_template_config_changed(self, key: str, value: Any):
        """处理标签模板配置变更"""
        try:
            logger.debug(f"标签模板配置变更: {key} = {value}")
            
            # 通知打印管理器更新模板
            if hasattr(self.main_window, 'print_manager'):
                self.main_window.print_manager.reload_template_config()
                
        except Exception as e:
            logger.error(f"处理标签模板配置变更失败: {e}")

    def _handle_grade_settings_changed(self, key: str, value: Any):
        """处理档位设置变更"""
        try:
            logger.debug(f"档位设置变更: {key} = {value}")

            # 更新通道显示组件的档位设置
            if hasattr(self.main_window, 'channel_display_widget'):
                for channel_num in range(1, 9):
                    channel_widget = getattr(self.main_window.channel_display_widget, f'channel_{channel_num}', None)
                    if channel_widget and hasattr(channel_widget, 'update_grade_settings'):
                        channel_widget.update_grade_settings()

            # 更新测试判定管理器
            if hasattr(self.main_window, 'test_judgment_manager'):
                self.main_window.test_judgment_manager.reload_grade_settings()

            # 新增如果有打开的设置对话框，也需要刷新判断设置界面
            self._refresh_settings_dialog_grade_settings()

        except Exception as e:
            logger.error(f"处理档位设置变更失败: {e}")

    def _refresh_settings_dialog_grade_settings(self):
        """刷新设置对话框中的判断设置界面"""
        try:
            # 检查是否有打开的设置对话框
            if hasattr(self.main_window, 'settings_dialog') and self.main_window.settings_dialog:
                settings_dialog = self.main_window.settings_dialog

                # 检查设置对话框是否可见
                if settings_dialog.isVisible():
                    # 获取判断设置组件
                    if hasattr(settings_dialog, 'grade_settings_widget'):
                        grade_widget = settings_dialog.grade_settings_widget
                        if grade_widget:
                            # 重新加载配置并更新显示
                            if hasattr(grade_widget, 'load_all_config'):
                                grade_widget.load_all_config()
                                logger.info("✅ 设置对话框中的判断设置界面已刷新")
                            elif hasattr(grade_widget, '_update_all_displays'):
                                grade_widget._update_all_displays()
                                logger.info("✅ 设置对话框显示已更新")

        except Exception as e:
            logger.error(f"刷新设置对话框判断设置界面失败: {e}")

    def _handle_product_info_changed(self, key: str, value: Any):
        """处理产品信息变更"""
        try:
            logger.debug(f"产品信息变更: {key} = {value}")
            
            # 更新标题栏显示
            if key == 'product_info.product_name':
                app_version = self.config_manager.get('app.version', 'V0.92.40')
                title = f"{value} {app_version}"
                self.main_window.setWindowTitle(title)
                
            # 更新头部组件显示
            if hasattr(self.main_window, 'header_widget'):
                self.main_window.header_widget.update_product_info()
                
        except Exception as e:
            logger.error(f"处理产品信息变更失败: {e}")

    def _handle_general_settings_changed(self, value: Any):
        """处理通用设置变更"""
        try:
            logger.debug(f"通用设置变更: {value}")
            
            # 重新加载通用设置
            self.load_general_settings()
            
        except Exception as e:
            logger.error(f"处理通用设置变更失败: {e}")

    def _handle_channel_enable_changed(self, enabled_channels: Any):
        """处理通道使能变更"""
        try:
            logger.debug(f"通道使能变更: {enabled_channels}")
            
            # 更新通道显示状态
            if hasattr(self.main_window, 'channel_display_widget'):
                for channel_num in range(1, 9):
                    channel_widget = getattr(self.main_window.channel_display_widget, f'channel_{channel_num}', None)
                    if channel_widget:
                        enabled = channel_num in enabled_channels if isinstance(enabled_channels, (list, tuple)) else False
                        channel_widget.set_channel_enabled(enabled)
                        
        except Exception as e:
            logger.error(f"处理通道使能变更失败: {e}")

    def _handle_probe_pin_settings_changed(self, key: str, value: Any):
        """处理顶针寿命设置变更"""
        try:
            logger.debug(f"顶针寿命设置变更: {key} = {value}")
            
            # 更新顶针寿命管理器
            if hasattr(self.main_window, 'probe_pin_manager'):
                self.main_window.probe_pin_manager.reload_settings()
                
        except Exception as e:
            logger.error(f"处理顶针寿命设置变更失败: {e}")

    def _handle_outlier_detection_config_changed(self, key: str, value: Any):
        """处理离群检测配置变更"""
        try:
            logger.debug(f"离群检测配置变更: {key} = {value}")
            
            # 更新离群检测状态
            if key == 'outlier_detection.enabled':
                if hasattr(self.main_window, 'channel_display_widget'):
                    for channel_num in range(1, 9):
                        channel_widget = getattr(self.main_window.channel_display_widget, f'channel_{channel_num}', None)
                        if channel_widget and hasattr(channel_widget, 'update_outlier_detection_status'):
                            channel_widget.update_outlier_detection_status(value)
                            
        except Exception as e:
            logger.error(f"处理离群检测配置变更失败: {e}")

    def _handle_test_count_changed(self, key: str, value: Any):
        """处理测试计数变更"""
        try:
            logger.debug(f"测试计数变更: {key} = {value}")
            
            # 更新测试计数显示
            if hasattr(self.main_window, 'statistics_widget'):
                self.main_window.statistics_widget.update_test_count_settings()
                
        except Exception as e:
            logger.error(f"处理测试计数变更失败: {e}")

    def _handle_test_mode_config_changed(self, key: str, value: Any):
        """处理测试模式配置变更"""
        try:
            logger.debug(f"测试模式配置变更: {key} = {value}")
            
            # 更新测试流程管理器
            if hasattr(self.main_window, 'test_flow_manager'):
                self.main_window.test_flow_manager.reload_test_mode_config()
                
        except Exception as e:
            logger.error(f"处理测试模式配置变更失败: {e}")

    def load_startup_settings(self):
        """加载启动设置"""
        try:
            logger.info("开始加载启动设置...")
            
            settings = {}
            
            # 1. 加载通道使能状态
            settings['channel_enable'] = self._load_channel_enable_settings()
            
            # 2. 加载产品信息设置
            settings['product_info'] = self._load_product_info_settings()
            
            # 3. 加载测试参数设置
            settings['test_parameters'] = self._load_test_parameter_settings()
            
            # 4. 加载界面显示设置
            settings['ui_display'] = self._load_ui_display_settings()
            
            # 5. 加载离群检测设置
            settings['outlier_detection'] = self._load_outlier_detection_settings()
            
            # 6. 加载历史统计数据
            settings['historical_statistics'] = self._load_historical_statistics()
            
            # 发送设置加载完成信号
            self.settings_loaded.emit(settings)
            
            logger.info("启动设置加载完成")
            
        except Exception as e:
            logger.error(f"加载启动设置失败: {e}")
            self.sync_failed.emit("startup_load", str(e))

    def _load_channel_enable_settings(self) -> dict:
        """加载通道使能状态设置"""
        try:
            enabled_channels = self.config_manager.get('channel_enable.enabled_channels', [1, 2, 3, 4, 5, 6, 7, 8])
            return {'enabled_channels': enabled_channels}
        except Exception as e:
            logger.error(f"加载通道使能设置失败: {e}")
            return {}

    def _load_product_info_settings(self) -> dict:
        """加载产品信息设置"""
        try:
            return {
                'product_name': self.config_manager.get('product_info.product_name', 'JCY5001A鲸测云8路EIS阻抗筛选仪'),
                'company_name': self.config_manager.get('product_info.company_name', '深圳市鲸测科技有限公司'),
                'version': self.config_manager.get('app.version', 'V0.80.09')
            }
        except Exception as e:
            logger.error(f"加载产品信息设置失败: {e}")
            return {}

    def _load_test_parameter_settings(self) -> dict:
        """加载测试参数设置"""
        try:
            return {
                'test_mode': self.config_manager.get('test.mode', 'manual'),
                'continuous_mode': self.config_manager.get('test.continuous_mode', False),
                'auto_print': self.config_manager.get('test.auto_print', False)
            }
        except Exception as e:
            logger.error(f"加载测试参数设置失败: {e}")
            return {}

    def _load_ui_display_settings(self) -> dict:
        """加载界面显示设置"""
        try:
            return {
                'show_voltage': self.config_manager.get('ui.display.show_voltage', True),
                'show_rs': self.config_manager.get('ui.display.show_rs', True),
                'show_rct': self.config_manager.get('ui.display.show_rct', True),
                'show_outlier_rate': self.config_manager.get('ui.display.show_outlier_rate', True)
            }
        except Exception as e:
            logger.error(f"加载界面显示设置失败: {e}")
            return {}

    def _load_outlier_detection_settings(self) -> dict:
        """加载离群检测设置"""
        try:
            return {
                'enabled': self.config_manager.get('outlier_detection.enabled', False),
                'threshold': self.config_manager.get('outlier_detection.threshold', 50.0),
                'baseline_file': self.config_manager.get('outlier_detection.baseline_file', '')
            }
        except Exception as e:
            logger.error(f"加载离群检测设置失败: {e}")
            return {}

    def _load_historical_statistics(self) -> dict:
        """加载历史统计数据"""
        try:
            return {
                'total_tests': self.config_manager.get('statistics.total_tests', 0),
                'pass_count': self.config_manager.get('statistics.pass_count', 0),
                'fail_count': self.config_manager.get('statistics.fail_count', 0)
            }
        except Exception as e:
            logger.error(f"加载历史统计数据失败: {e}")
            return {}

    def load_general_settings(self):
        """加载通用设置"""
        try:
            # 重新加载通用设置并应用
            logger.debug("重新加载通用设置")
        except Exception as e:
            logger.error(f"加载通用设置失败: {e}")

    def _perform_periodic_sync(self):
        """执行定期同步"""
        try:
            if self.sync_in_progress:
                logger.debug("同步正在进行中，跳过本次定期同步")
                return
                
            self.sync_in_progress = True
            
            # 执行同步操作
            self.config_manager.save_config()
            
            self.sync_in_progress = False
            self.sync_completed.emit("定期同步完成")
            
        except Exception as e:
            self.sync_in_progress = False
            logger.error(f"定期同步失败: {e}")
            self.sync_failed.emit("periodic", str(e))

    def force_sync(self):
        """强制同步"""
        try:
            self.config_manager.save_config()
            self.sync_completed.emit("强制同步完成")
        except Exception as e:
            logger.error(f"强制同步失败: {e}")
            self.sync_failed.emit("force", str(e))
