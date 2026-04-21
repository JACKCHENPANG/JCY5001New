# -*- coding: utf-8 -*-
"""
UI组件管理器
负责UI组件的创建、管理和信号连接

从MainWindow中提取的UI组件管理功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class UIComponentManager(QObject):
    """
    UI组件管理器
    
    职责：
    - UI组件创建和初始化
    - 组件信号连接
    - 组件状态管理
    - 组件数据更新
    """
    
    # 信号定义
    component_ready = pyqtSignal(str)  # 组件就绪
    component_error = pyqtSignal(str, str)  # 组件错误
    
    def __init__(self, main_window, config_manager):
        """
        初始化UI组件管理器
        
        Args:
            main_window: 主窗口实例
            config_manager: 配置管理器
        """
        super().__init__()

        self.main_window = main_window
        self.config_manager = config_manager

        # 组件引用
        self.components = {}

        # 恢复防重复统计机制
        self._processed_test_results = set()  # 存储已处理的测试结果ID

        logger.debug("UI组件管理器初始化完成")
    
    def create_header_widget(self, main_layout):
        """
        创建顶部标题栏
        
        Args:
            main_layout: 主布局
        """
        try:
            from ui.components.header_widget import HeaderWidget
            
            self.components['header'] = HeaderWidget(self.config_manager)
            main_layout.addWidget(self.components['header'])
            
            self.component_ready.emit('header')
            logger.info("顶部标题栏创建完成")
            
        except Exception as e:
            logger.error(f"创建顶部标题栏失败: {e}")
            self.component_error.emit('header', str(e))
    
    def create_upper_widgets(self, upper_layout):
        """
        创建上层区域组件

        Args:
            upper_layout: 上层区域布局
        """
        try:
            # 批次信息区域
            self._create_batch_info_widget(upper_layout)

            # 统计区域
            self._create_statistics_widget(upper_layout)

            # 测试控制区域
            self._create_test_control_widget(upper_layout)

            logger.info("上层区域组件创建完成")

        except Exception as e:
            logger.error(f"创建上层区域组件失败: {e}")
    
    def _create_batch_info_widget(self, layout):
        """创建批次信息组件"""
        try:
            from ui.components.batch_info_widget import BatchInfoWidget
            
            self.components['batch_info'] = BatchInfoWidget(self.config_manager)
            layout.addWidget(self.components['batch_info'])
            
            self.component_ready.emit('batch_info')
            
        except Exception as e:
            logger.error(f"创建批次信息组件失败: {e}")
            self.component_error.emit('batch_info', str(e))
    
    def _create_statistics_widget(self, layout):
        """创建统计组件"""
        try:
            from ui.components.statistics_widget import StatisticsWidget
            
            self.components['statistics'] = StatisticsWidget(self.config_manager)
            layout.addWidget(self.components['statistics'])
            
            self.component_ready.emit('statistics')
            
        except Exception as e:
            logger.error(f"创建统计组件失败: {e}")
            self.component_error.emit('statistics', str(e))
    
    def _create_test_control_widget(self, layout):
        """创建测试控制组件"""
        try:
            from ui.components.test_control_widget import TestControlWidget

            self.components['test_control'] = TestControlWidget(self.config_manager)
            layout.addWidget(self.components['test_control'])

            self.component_ready.emit('test_control')

        except Exception as e:
            logger.error(f"创建测试控制组件失败: {e}")
            self.component_error.emit('test_control', str(e))


    
    def create_channels_container(self, splitter):
        """
        创建通道容器
        
        Args:
            splitter: 分割器
        """
        try:
            from ui.components.channels_container_widget import ChannelsContainerWidget
            
            self.components['channels_container'] = ChannelsContainerWidget(self.config_manager)
            splitter.addWidget(self.components['channels_container'])
            
            self.component_ready.emit('channels_container')
            logger.info("通道容器创建完成")
            
        except Exception as e:
            logger.error(f"创建通道容器失败: {e}")
            self.component_error.emit('channels_container', str(e))
    
    def create_status_bar(self):
        """创建状态栏"""
        try:
            from ui.components.status_bar_widget import StatusBarWidget
            
            self.components['status_bar'] = StatusBarWidget(self.config_manager)
            self.main_window.setStatusBar(self.components['status_bar'])
            
            self.component_ready.emit('status_bar')
            logger.info("状态栏创建完成")
            
        except Exception as e:
            logger.error(f"创建状态栏失败: {e}")
            self.component_error.emit('status_bar', str(e))
    
    def setup_signal_connections(self):
        """设置信号连接"""
        try:
            # 测试控制信号
            if 'test_control' in self.components:
                test_control = self.components['test_control']
                test_control.start_test.connect(self.main_window._on_start_test)
                test_control.stop_test.connect(self.main_window._on_stop_test)
                test_control.clear_statistics.connect(self.main_window._on_clear_statistics)
                test_control.export_data.connect(self.main_window._on_export_data)
                test_control.open_settings.connect(self.main_window._on_open_settings)
            
            # 通道容器信号
            if 'channels_container' in self.components:
                channels_container = self.components['channels_container']
                # 紧急修复恢复通道容器的channel_test_completed信号连接，确保手动模式测试能正常结束
                channels_container.channel_test_completed.connect(self.main_window._on_channel_test_completed)
                channels_container.channel_battery_code_changed.connect(self.main_window._on_channel_battery_code_changed)

                # 添加调试信息
                logger.info("🔗 正在连接all_channels_ready信号到_on_all_channels_ready方法")
                channels_container.all_channels_ready.connect(self.main_window._on_all_channels_ready)
                logger.info("✅ all_channels_ready信号连接完成")
            
            # 状态栏信号
            if 'status_bar' in self.components:
                status_bar = self.components['status_bar']
                status_bar.device_status_changed.connect(self.main_window._on_device_status_changed)
                status_bar.printer_status_changed.connect(self.main_window._on_printer_status_changed)

            # 头部组件信号（授权相关）
            if 'header' in self.components:
                header = self.components['header']
                header.trial_expired.connect(self.main_window._on_trial_expired)
                header.unlock_requested.connect(self.main_window._on_unlock_requested)

            logger.info("信号连接设置完成")
            
        except Exception as e:
            logger.error(f"设置信号连接失败: {e}")
    
    def get_component(self, component_name: str):
        """
        获取组件实例
        
        Args:
            component_name: 组件名称
            
        Returns:
            组件实例或None
        """
        return self.components.get(component_name)
    
    def update_component_data(self, component_name: str, data: dict):
        """
        更新组件数据
        
        Args:
            component_name: 组件名称
            data: 数据字典
        """
        try:
            component = self.components.get(component_name)
            if component and hasattr(component, 'update_data'):
                component.update_data(data)
            else:
                logger.warning(f"组件 {component_name} 不存在或不支持数据更新")
                
        except Exception as e:
            logger.error(f"更新组件 {component_name} 数据失败: {e}")
    
    def set_component_enabled(self, component_name: str, enabled: bool):
        """
        设置组件启用状态
        
        Args:
            component_name: 组件名称
            enabled: 是否启用
        """
        try:
            component = self.components.get(component_name)
            if component:
                component.setEnabled(enabled)
            else:
                logger.warning(f"组件 {component_name} 不存在")
                
        except Exception as e:
            logger.error(f"设置组件 {component_name} 状态失败: {e}")
    
    def update_test_progress(self, channel_num: int, progress_data: dict):
        """
        更新测试进度

        Args:
            channel_num: 通道号
            progress_data: 进度数据
        """
        try:
            # 调试日志：跟踪组件更新
            logger.debug(f"UI组件管理器更新进度: 通道{channel_num}, 状态={progress_data.get('state')}, 进度={progress_data.get('progress')}%, 频率={progress_data.get('frequency')}Hz")

            # 更新通道容器
            channels_container = self.components.get('channels_container')
            if channels_container:
                # 修复先处理离群率更新，确保数据传递到通道卡片
                state = progress_data.get('state')
                if state in ['outlier_rate_update', 'final_outlier_rate_update', 'completed']:
                    outlier_result = progress_data.get('outlier_result')
                    baseline_filename = progress_data.get('baseline_filename', '')
                    frequency_deviations = progress_data.get('frequency_deviations', {})

                    # 修复确定是否为最终结果
                    is_final = (state == 'final_outlier_rate_update') or (state == 'completed')


                    # 已移除离群率结果UI更新（功能已完全移除）
                    # 离群率功能已完全移除，不再更新离群率UI

                # 然后更新通道进度（包括测试完成状态）
                channels_container.update_channel_progress(channel_num, progress_data)
            else:
                logger.warning("通道容器组件未找到")

            # 修复统计更新逻辑，简化防重复机制
            if progress_data.get('state') == 'completed':
                statistics = self.components.get('statistics')
                if statistics:
                    # 获取测试结果的关键信息
                    is_pass = progress_data.get('is_pass', False)
                    rs_grade = progress_data.get('rs_grade')
                    rct_grade = progress_data.get('rct_grade')


                    # 修复简化条件检查，确保有效数据能被统计
                    if rs_grade is not None and rct_grade is not None and isinstance(rs_grade, int) and isinstance(rct_grade, int):
                        # 修复使用更简单的防重复机制
                        import time
                        current_time = time.time()
                        unique_key = f"ch{channel_num}_{int(current_time)}"

                        # 检查最近1秒内是否已处理过相同通道的统计
                        recent_keys = [k for k in self._processed_test_results if current_time - float(k.split('_')[1]) < 1.0]
                        channel_recent_keys = [k for k in recent_keys if k.startswith(f"ch{channel_num}_")]

                        if not channel_recent_keys:
                            statistics.add_test_result(is_pass, rs_grade, rct_grade)

                            # 记录已处理的测试结果
                            self._processed_test_results.add(unique_key)

                            # 清理超过10秒的旧记录
                            old_keys = [k for k in self._processed_test_results if current_time - float(k.split('_')[1]) > 10.0]
                            for old_key in old_keys:
                                self._processed_test_results.discard(old_key)

                        else:
                            logger.debug(f"通道{channel_num} 统计结果重复，跳过")
                    else:
                        # 减少重复的档位数据无效警告
                        if not hasattr(self, '_grade_invalid_warned'):
                            self._grade_invalid_warned = set()
                        if channel_num not in self._grade_invalid_warned:
                            logger.debug(f"通道{channel_num}档位数据无效: Rs档位={rs_grade}, Rct档位={rct_grade}")
                            self._grade_invalid_warned.add(channel_num)
                else:
                    logger.warning("统计组件未找到，无法更新统计")

        except Exception as e:
            logger.error(f"更新测试进度失败: {e}")

    def update_channel_exception(self, channel_num: int, exception_data: dict):
        """
        更新通道异常状态

        Args:
            channel_num: 通道号
            exception_data: 异常数据
        """
        try:
            # 获取通道容器组件
            channels_container = self.components.get('channels_container')
            if channels_container and hasattr(channels_container, 'update_channel_exception'):
                channels_container.update_channel_exception(channel_num, exception_data)
            else:
                logger.warning("通道容器组件未找到或不支持异常状态更新")

            logger.warning(f"通道{channel_num}异常状态已更新: {exception_data.get('error_message', '未知异常')}")

        except Exception as e:
            logger.error(f"更新通道{channel_num}异常状态失败: {e}")

    def update_device_status(self, connected: bool, device_info: Optional[dict] = None):
        """
        更新设备状态

        Args:
            connected: 是否连接
            device_info: 设备信息
        """
        try:
            status_bar = self.components.get('status_bar')
            if status_bar:
                # 获取端口信息
                port = ""
                if device_info and 'port' in device_info:
                    port = device_info['port']

                # 更新设备状态和端口信息
                status_bar.set_device_status(connected, port)

                if device_info:
                    status_bar.set_system_status(
                        f"设备: {device_info.get('device_type', 'Unknown')}",
                        "success" if connected else "error"
                    )

        except Exception as e:
            logger.error(f"更新设备状态失败: {e}")

    def update_printer_status(self, connected: bool, printer_info: Optional[dict] = None):
        """
        更新打印机状态

        Args:
            connected: 是否连接
            printer_info: 打印机信息
        """
        try:
            status_bar = self.components.get('status_bar')
            if status_bar and hasattr(status_bar, 'set_printer_status'):
                status_bar.set_printer_status(connected)
                logger.debug(f"状态栏打印机状态已更新: {'已连接' if connected else '未连接'}")

                if printer_info:
                    printer_name = printer_info.get('name', 'Unknown')
                    status_bar.set_system_status(
                        f"打印机: {printer_name}",
                        "success" if connected else "warning"
                    )
            else:
                logger.warning("状态栏组件未找到或不支持打印机状态更新")

        except Exception as e:
            logger.error(f"更新打印机状态失败: {e}")

    def clear_test_data(self):
        """清空测试数据"""
        try:
            # 清空统计数据
            statistics = self.components.get('statistics')
            if statistics and hasattr(statistics, 'clear_statistics'):
                statistics.clear_statistics()

            # 重置通道状态
            channels_container = self.components.get('channels_container')
            if channels_container and hasattr(channels_container, 'reset_all_channels'):
                channels_container.reset_all_channels()

            # 恢复清空防重复统计缓存
            self._processed_test_results.clear()
            logger.debug("防重复统计缓存已清空")

            logger.info("测试数据已清空")

        except Exception as e:
            logger.error(f"清空测试数据失败: {e}")
    
    def get_components_info(self) -> dict:
        """
        获取组件信息
        
        Returns:
            组件信息字典
        """
        try:
            info = {}
            for name, component in self.components.items():
                info[name] = {
                    'type': type(component).__name__,
                    'enabled': component.isEnabled() if hasattr(component, 'isEnabled') else True,
                    'visible': component.isVisible() if hasattr(component, 'isVisible') else True
                }
            
            return info
            
        except Exception as e:
            logger.error(f"获取组件信息失败: {e}")
            return {}
    
    def create_header_widget_in_container(self, container):
        """
        在指定容器中创建顶部标题栏

        Args:
            container: 容器窗口部件
        """
        try:
            from ui.components.header_widget import HeaderWidget
            from PyQt5.QtWidgets import QVBoxLayout

            # 为容器创建布局
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            # 创建标题栏组件
            self.components['header'] = HeaderWidget(self.config_manager)
            layout.addWidget(self.components['header'])

            self.component_ready.emit('header')
            logger.info("顶部标题栏在容器中创建完成")

        except Exception as e:
            logger.error(f"在容器中创建顶部标题栏失败: {e}")
            self.component_error.emit('header', str(e))

    def create_split_channels_container(self, row1_container, row2_container):
        """
        创建分行的通道容器

        Args:
            row1_container: 第一行容器
            row2_container: 第二行容器
        """
        try:
            from ui.components.split_channels_container_widget import SplitChannelsContainerWidget

            # 创建分行通道容器组件
            self.components['channels_container'] = SplitChannelsContainerWidget(
                self.config_manager, row1_container, row2_container
            )

            self.component_ready.emit('channels_container')
            logger.info("分行通道容器创建完成")

        except Exception as e:
            logger.error(f"创建分行通道容器失败: {e}")
            self.component_error.emit('channels_container', str(e))

    def cleanup(self):
        """清理资源"""
        try:
            # 清理组件引用
            self.components.clear()

            logger.info("UI组件管理器资源已清理")

        except Exception as e:
            logger.error(f"清理UI组件管理器资源失败: {e}")
