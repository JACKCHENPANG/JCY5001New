# -*- coding: utf-8 -*-
"""
测试流程控制器
负责核心测试流程的启动、停止和状态管理

从TestFlowManager中提取的核心流程控制功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class TestFlowController(QObject):
    """
    测试流程控制器
    
    职责：
    - 测试流程的启动和停止
    - 测试状态管理
    - 流程协调
    """
    
    # 信号定义
    test_started = pyqtSignal()  # 测试开始
    test_stopped = pyqtSignal()  # 测试停止
    test_state_changed = pyqtSignal(str)  # 测试状态变更
    
    def __init__(self, config_manager, comm_manager):
        """
        初始化测试流程控制器
        
        Args:
            config_manager: 配置管理器
            comm_manager: 通信管理器
        """
        super().__init__()
        
        self.config_manager = config_manager
        self.comm_manager = comm_manager
        
        # 测试状态
        self.is_testing = False
        self.current_test_state = "idle"  # idle, preparing, testing, stopping, completed
        self.test_flow_controller = None
        
        # 依赖的管理器（将在后续步骤中注入）
        self.precheck_manager = None
        self.configuration_manager = None
        self.statistics_manager = None
        self.ui_update_manager = None
        self.error_handler = None
        
        # 🧹 初始化测试状态清理器
        from backend.test_state_cleaner import TestStateCleaner
        self.state_cleaner = TestStateCleaner()

        logger.debug("测试流程控制器初始化完成")
    
    def set_managers(self, precheck_manager, configuration_manager, statistics_manager,
                    ui_update_manager, error_handler):
        """
        设置依赖的管理器

        Args:
            precheck_manager: 预检查管理器
            configuration_manager: 配置管理器
            statistics_manager: 统计管理器
            ui_update_manager: UI更新管理器
            error_handler: 错误处理器
        """
        self.precheck_manager = precheck_manager
        self.configuration_manager = configuration_manager
        self.statistics_manager = statistics_manager
        self.ui_update_manager = ui_update_manager
        self.error_handler = error_handler

        logger.info("测试流程控制器依赖管理器设置完成")
    
    def start_test(self) -> bool:
        """
        开始测试
        
        Returns:
            是否启动成功
        """
        try:
            if self.is_testing:
                return False

            logger.info("🚀 开始启动测试流程...")
            self._set_test_state("preparing")

            # 🧹 新增：全面清理测试状态，确保干净的测试环境
            self._clean_test_environment()

            # 1. 检查依赖管理器
            if not self._check_managers():
                return False
            
            # 2. 🚀 优化：检查是否启用快速启动模式
            fast_startup = self.config_manager.get('test_params.fast_startup', False) if hasattr(self, 'config_manager') else False

            if fast_startup:
                logger.info("🚀 快速启动模式：跳过预检查，直接启动测试")
            else:
                # 执行预检查
                if self.precheck_manager and hasattr(self.precheck_manager, 'execute_precheck'):
                    if not self.precheck_manager.execute_precheck():
                        self._set_test_state("idle")
                        return False
                else:
                    logger.warning("预检查管理器未设置或方法不存在，跳过预检查")

            # 3. 配置设备参数
            if self.configuration_manager and hasattr(self.configuration_manager, 'configure_device'):
                if not self.configuration_manager.configure_device():
                    self._set_test_state("idle")
                    return False
            else:
                logger.warning("配置管理器未设置或方法不存在，跳过设备配置")

            # 4. 重置统计数据
            if self.statistics_manager and hasattr(self.statistics_manager, 'reset_statistics'):
                self.statistics_manager.reset_statistics()
            else:
                logger.warning("统计管理器未设置或方法不存在，跳过统计重置")

            # 5. 重置统计数据（移除阻塞的测试执行器调用）

            # 6. 更新测试状态
            self.is_testing = True
            self._set_test_state("testing")

            # 发送测试开始信号
            self.test_started.emit()

            logger.info("✅ 测试流程启动成功")
            return True
            
        except Exception as e:
            logger.error(f"启动测试流程失败: {e}")
            self._set_test_state("idle")
            if self.error_handler:
                self.error_handler.handle_error("启动测试失败", str(e))
            return False
    
    def stop_test(self):
        """停止测试"""
        try:
            if not self.is_testing:
                return

            logger.info("🛑 停止测试流程...")
            self._set_test_state("stopping")

            # 停止测试引擎
            if self.test_flow_controller:
                self.test_flow_controller.stop_test()

            # 关键修复调用完整的状态清理，确保所有状态正确重置
            self._clean_test_environment()
            logger.debug("✅ 测试停止时已执行完整状态清理")

            # 发送测试停止信号
            self.test_stopped.emit()

            logger.info("✅ 测试流程已停止")
            
        except Exception as e:
            logger.error(f"停止测试流程失败: {e}")
            if self.error_handler:
                self.error_handler.handle_error("停止测试失败", str(e))
    
    def _check_managers(self) -> bool:
        """检查依赖管理器是否已设置"""
        required_managers = [
            ('precheck_manager', self.precheck_manager),
            ('configuration_manager', self.configuration_manager),
            ('statistics_manager', self.statistics_manager),
            ('ui_update_manager', self.ui_update_manager),
            ('error_handler', self.error_handler)
        ]
        
        for name, manager in required_managers:
            if manager is None:
                logger.error(f"依赖管理器未设置: {name}")
                return False
        
        return True
    
    def _set_test_state(self, state: str):
        """
        设置测试状态
        
        Args:
            state: 新的测试状态
        """
        if self.current_test_state != state:
            old_state = self.current_test_state
            self.current_test_state = state
            
            logger.debug(f"测试状态变更: {old_state} -> {state}")
            self.test_state_changed.emit(state)
    
    def get_test_state(self) -> str:
        """
        获取当前测试状态
        
        Returns:
            当前测试状态
        """
        return self.current_test_state
    
    def is_test_running(self) -> bool:
        """
        检查测试是否正在运行
        
        Returns:
            是否正在测试
        """
        return self.is_testing
    
    def get_status_info(self) -> Dict[str, Any]:
        """
        获取状态信息
        
        Returns:
            状态信息字典
        """
        return {
            'is_testing': self.is_testing,
            'current_state': self.current_test_state,
            'managers_ready': self._check_managers()
        }



    def _clean_test_environment(self):
        """清理测试环境，确保干净的测试状态"""
        try:

            # 关键修复重置所有内部状态，包括is_testing
            self.is_testing = False
            self.current_test_state = "idle"

            # 清理统计管理器（如果存在）
            if self.statistics_manager and hasattr(self.statistics_manager, 'reset_statistics'):
                self.statistics_manager.reset_statistics()

            logger.debug("✅ 测试流程控制器测试环境清理完成")

        except Exception as e:
            logger.error(f"❌ 测试流程控制器清理测试环境失败: {e}")

    def clean_channel_states(self, channel_widgets: list):
        """清理通道状态（供外部调用）"""
        try:
            if hasattr(self, 'state_cleaner') and self.state_cleaner:
                return self.state_cleaner.clean_all_test_states(channel_widgets)
            else:
                logger.warning("状态清理器未初始化，跳过通道状态清理")
                return False

        except Exception as e:
            logger.error(f"清理通道状态失败: {e}")
            return False
