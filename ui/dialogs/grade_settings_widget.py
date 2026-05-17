#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构后的档位设置主组件
作为各个管理器的协调器，保持较小的体积

Author: Jack
Date: 2025-06-04
"""

import logging
from typing import Dict, Any
from PyQt5.QtWidgets import QWidget, QMessageBox, QDialog
from PyQt5.QtCore import QTimer

# 导入管理器
from .grade_range_manager import GradeRangeManager
from .voltage_range_manager import VoltageRangeManager
from .grade_settings_ui_manager import GradeSettingsUIManager

# 导入安全数值输入框
from .safe_double_spinbox import SafeDoubleSpinBox

logger = logging.getLogger(__name__)


class GradeSettingsWidget(QWidget):
    """
    档位设置主组件（重构版）
    
    职责：
    - 协调各个管理器
    - 处理管理器间的通信
    - 管理整体状态
    """
    
    def __init__(self, config_manager, parent=None):
        """
        初始化档位设置组件
        
        Args:
            config_manager: 配置管理器
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        # 初始化管理器
        self._init_managers()
        
        # 创建界面
        self._init_ui()
        
        # 连接信号
        self._connect_signals()
        
        # 初始化数据
        self._init_data()
        
        logger.debug("档位设置组件初始化完成")
    
    def _init_managers(self):
        """初始化各个管理器"""
        try:
            # 创建管理器实例
            self.grade_range_manager = GradeRangeManager(self.config_manager, self)
            self.voltage_range_manager = VoltageRangeManager(self.config_manager, self)
            self.ui_manager = GradeSettingsUIManager(self)
            
            logger.debug("所有管理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化管理器失败: {e}")
            QMessageBox.critical(self, "错误", f"初始化失败: {e}")
    
    def _init_ui(self):
        """初始化界面"""
        try:
            # 创建主布局
            main_layout = self.ui_manager.create_main_layout()

            # 设置主布局到当前组件
            self.setLayout(main_layout)

            logger.debug("界面初始化完成")

        except Exception as e:
            logger.error(f"初始化界面失败: {e}")
            # 最后的备用方案：创建简单布局
            try:
                from PyQt5.QtWidgets import QVBoxLayout, QLabel
                if not self.layout():
                    simple_layout = QVBoxLayout(self)
                    error_label = QLabel(f"界面初始化失败: {e}")
                    simple_layout.addWidget(error_label)
                    logger.info("使用简单布局显示错误信息")
            except Exception as final_error:
                logger.error(f"最终备用方案也失败: {final_error}")
    
    def _connect_signals(self):
        """连接管理器间的信号"""
        try:
            # UI管理器信号连接
            self.ui_manager.settings_changed.connect(self._on_settings_changed)

            # 🚫 离群检测UI管理器信号连接已删除

            # 档位范围管理器信号连接
            self.grade_range_manager.ranges_updated.connect(self._on_ranges_updated)
            
            # 电压范围管理器信号连接
            self.voltage_range_manager.voltage_config_changed.connect(self._on_voltage_config_changed)
            
            logger.debug("信号连接完成")
            
        except Exception as e:
            logger.error(f"连接信号失败: {e}")
    
    def _init_data(self):
        """初始化数据"""
        try:
            # 延迟加载数据以提升启动速度
            QTimer.singleShot(100, self._load_initial_data)
            
        except Exception as e:
            logger.error(f"初始化数据失败: {e}")
    
    def _load_initial_data(self):
        """加载初始数据"""
        try:
            # 加载配置
            self.grade_range_manager.load_config()
            self.voltage_range_manager.load_config()

            # 更新显示
            self._update_all_displays()

            # 🚫 离群检测功能已删除

            logger.info("初始数据加载完成")

        except Exception as e:
            logger.error(f"加载初始数据失败: {e}")

    # 🚫 离群检测配置加载已删除
    
    def _on_settings_changed(self):
        """处理设置变更"""
        try:
            # 获取配置
            voltage_config = self.ui_manager.get_voltage_config()
            rs_config = self.ui_manager.get_rs_config()
            rct_config = self.ui_manager.get_rct_config()
            
            # 更新管理器
            self.voltage_range_manager.update_voltage_config(**voltage_config)
            self.grade_range_manager.update_rs_config(**rs_config)
            self.grade_range_manager.update_rct_config(**rct_config)
            
            # 更新显示
            self._update_all_displays()
            
        except Exception as e:
            logger.error(f"处理设置变更失败: {e}")
    
    # 🚫 离群检测相关方法已删除
    
    def _on_ranges_updated(self, range_type: str, ranges: list):
        """处理档位范围更新"""
        try:
            if range_type == 'rs':
                text = self.grade_range_manager.get_rs_ranges_text()
                self.ui_manager.update_rs_display(text)
            elif range_type == 'rct':
                text = self.grade_range_manager.get_rct_ranges_text()
                self.ui_manager.update_rct_display(text)
            
        except Exception as e:
            logger.error(f"处理档位范围更新失败: {e}")
    
    def _on_voltage_config_changed(self):
        """处理电压配置变更"""
        try:
            text = self.voltage_range_manager.get_voltage_range_text()
            self.ui_manager.update_voltage_display(text)
            
        except Exception as e:
            logger.error(f"处理电压配置变更失败: {e}")
    
    def _update_all_displays(self):
        """更新所有显示"""
        try:
            # 更新电压范围显示
            voltage_text = self.voltage_range_manager.get_voltage_range_text()
            self.ui_manager.update_voltage_display(voltage_text)
            
            # 更新Rs档位显示
            rs_text = self.grade_range_manager.get_rs_ranges_text()
            self.ui_manager.update_rs_display(rs_text)
            
            # 更新Rct档位显示
            rct_text = self.grade_range_manager.get_rct_ranges_text()
            self.ui_manager.update_rct_display(rct_text)
            
        except Exception as e:
            logger.error(f"更新所有显示失败: {e}")
    
    # 🚫 基准列表加载已删除
    
    def get_voltage_config(self) -> Dict[str, Any]:
        """获取电压配置（向后兼容）"""
        return self.voltage_range_manager.get_voltage_config()
    
    def get_rs_config(self) -> Dict[str, Any]:
        """获取Rs配置（向后兼容）"""
        return self.grade_range_manager.get_rs_config()
    
    def get_rct_config(self) -> Dict[str, Any]:
        """获取Rct配置（向后兼容）"""
        return self.grade_range_manager.get_rct_config()
    
    def get_outlier_config(self) -> Dict[str, Any]:
        """🚫 离群检测配置获取已删除"""
        return {}
    
    def validate_voltage(self, voltage: float) -> bool:
        """验证电压（向后兼容）"""
        return self.voltage_range_manager.validate_voltage(voltage)
    
    def get_grade_by_value(self, value: float, grade_type: str) -> str:
        """根据值获取档位（已弃用：UI不应该计算档位）"""
        logger.warning(f"⚠️ [已弃用] 档位设置对话框不应该计算档位！")
        logger.warning(f"   调用参数: value={value}, grade_type={grade_type}")
        return "UI不计算档位"
    
    def apply_settings(self):
        """应用设置（设置对话框标准接口）"""
        try:
            # 获取当前UI配置
            voltage_config = self.ui_manager.get_voltage_config()
            rs_config = self.ui_manager.get_rs_config()
            rct_config = self.ui_manager.get_rct_config()

            # 更新管理器配置
            self.voltage_range_manager.update_voltage_config(**voltage_config)
            self.grade_range_manager.update_rs_config(**rs_config)
            self.grade_range_manager.update_rct_config(**rct_config)

            # 保存所有配置
            self.save_all_config()

            logger.info("档位设置应用成功")

        except Exception as e:
            logger.error(f"应用档位设置失败: {e}")
            raise

    def validate_settings(self) -> bool:
        """验证设置（设置对话框标准接口）"""
        try:
            # 验证电压配置
            if not self.voltage_range_manager.validate_config():
                return False

            # 验证档位配置
            validation_result = self.grade_range_manager.validate_ranges()
            if not validation_result.get('rs', True) or not validation_result.get('rct', True):
                return False

            return True

        except Exception as e:
            logger.error(f"验证档位设置失败: {e}")
            return False

    def load_settings(self):
        """加载设置（设置对话框标准接口）"""
        try:
            self.load_all_config()
            logger.debug("档位设置加载完成")

        except Exception as e:
            logger.error(f"加载档位设置失败: {e}")

    def save_all_config(self):
        """保存所有配置"""
        try:
            self.grade_range_manager.save_config()
            self.voltage_range_manager.save_config()

            # 保存UI管理器配置
            if self.config_manager:
                # 保存Rs配置到impedance节点（统一标准）
                rs_config = self.ui_manager.get_rs_config()
                for key, value in rs_config.items():
                    if key == 'grade_count':
                        self.config_manager.set('impedance.rs_grade_count', value)
                    elif key == 'min_value':
                        self.config_manager.set('impedance.rs_min', value)
                    elif key == 'max_value':
                        self.config_manager.set('impedance.rs_grade3_max', value)  # 使用grade3_max作为最大值
                    elif key == 'grade1_max':
                        self.config_manager.set('impedance.rs_grade1_max', value)
                    elif key == 'grade2_max':
                        self.config_manager.set('impedance.rs_grade2_max', value)
                    elif key == 'grade3_max':
                        self.config_manager.set('impedance.rs_grade3_max', value)

                # 保存Rct配置到impedance节点（统一标准）
                rct_config = self.ui_manager.get_rct_config()
                for key, value in rct_config.items():
                    if key == 'min_value':
                        self.config_manager.set('impedance.rct_min', value)
                    elif key == 'max_value':
                        self.config_manager.set('impedance.rct_grade3_max', value)  # 使用grade3_max作为最大值
                    elif key == 'grade1_max':
                        self.config_manager.set('impedance.rct_grade1_max', value)
                    elif key == 'grade2_max':
                        self.config_manager.set('impedance.rct_grade2_max', value)
                    elif key == 'grade3_max':
                        self.config_manager.set('impedance.rct_grade3_max', value)

                # 新增同步根级别配置（向后兼容），确保所有配置节点一致
                self._sync_to_root_level_config(rs_config, rct_config)

                # 简化保存电压配置（仅电压差模式）
                voltage_config = self.ui_manager.get_voltage_config()
                for key, value in voltage_config.items():
                    if key == 'standard_voltage':
                        self.config_manager.set('grade_settings.standard_voltage', value)
                    elif key == 'min_voltage':
                        self.config_manager.set('grade_settings.min_voltage', value)
                    elif key == 'max_voltage':
                        self.config_manager.set('grade_settings.max_voltage', value)
                    elif key == 'auto_calc_range':
                        self.config_manager.set('grade_settings.auto_calc_range', value)
                    elif key == 'battery_type':
                        self.config_manager.set('grade_settings.battery_type', value)
                    elif key == 'voltage_diff':
                        self.config_manager.set('grade_settings.voltage_diff', value)

            # 🚫 离群检测配置保存已删除

            logger.info("所有配置保存完成")

        except Exception as e:
            logger.error(f"保存所有配置失败: {e}")

    def _sync_to_root_level_config(self, rs_config: Dict, rct_config: Dict):
        """同步配置到根级别（向后兼容），确保所有配置节点一致"""
        try:
            # 同步Rs根级别配置
            if rs_config:
                rs_min = rs_config.get('min_value')
                rs_max = rs_config.get('max_value')
                rs_grade1_max = rs_config.get('grade1_max')
                rs_grade2_max = rs_config.get('grade2_max')
                rs_grade3_max = rs_config.get('grade3_max')

                if rs_min is not None:
                    self.config_manager.set('rs_min', rs_min)
                if rs_max is not None:
                    self.config_manager.set('rs_max', rs_max)
                if rs_grade1_max is not None:
                    self.config_manager.set('rs1_max', rs_grade1_max)
                if rs_grade2_max is not None:
                    self.config_manager.set('rs2_max', rs_grade2_max)
                if rs_grade3_max is not None:
                    self.config_manager.set('rs3_max', rs_grade3_max)

                logger.debug(f"Rs根级别配置已同步: rs_min={rs_min}, rs1_max={rs_grade1_max}, rs2_max={rs_grade2_max}, rs3_max={rs_grade3_max}")

            # 同步Rct根级别配置
            if rct_config:
                rct_min = rct_config.get('min_value')
                rct_max = rct_config.get('max_value')
                rct_grade1_max = rct_config.get('grade1_max')
                rct_grade2_max = rct_config.get('grade2_max')
                rct_grade3_max = rct_config.get('grade3_max')

                if rct_min is not None:
                    self.config_manager.set('rct_min', rct_min)
                if rct_max is not None:
                    self.config_manager.set('rct_max', rct_max)
                if rct_grade1_max is not None:
                    self.config_manager.set('rct1_max', rct_grade1_max)
                if rct_grade2_max is not None:
                    self.config_manager.set('rct2_max', rct_grade2_max)
                if rct_grade3_max is not None:
                    self.config_manager.set('rct3_max', rct_grade3_max)

                logger.debug(f"Rct根级别配置已同步: rct_min={rct_min}, rct1_max={rct_grade1_max}, rct2_max={rct_grade2_max}, rct3_max={rct_grade3_max}")

            logger.info("✅ 根级别配置同步完成，确保所有配置节点一致")

        except Exception as e:
            logger.error(f"❌ 同步根级别配置失败: {e}")

    def load_all_config(self):
        """加载所有配置"""
        try:
            # 从文件重新加载，确保读到最新配置（如刚刚生成的判定范围）
            if self.config_manager:
                self.config_manager.reload_config()

            self.grade_range_manager.load_config()
            self.voltage_range_manager.load_config()

            # 加载UI管理器配置
            if self.config_manager:
                # 修复加载Rs配置（优先从grade_settings读取，兼容impedance节点）
                rs_config = {}
                rs_config['grade_count'] = self.config_manager.get('impedance.rs_grade_count', 3)
                # 优先从grade_settings读取，如果没有则从impedance读取
                rs_config['min_value'] = self.config_manager.get('grade_settings.rs_min',
                                                               self.config_manager.get('impedance.rs_min', 0.5))
                rs_config['max_value'] = self.config_manager.get('grade_settings.rs_max',
                                                               self.config_manager.get('impedance.rs_grade3_max', 50.0))
                rs_config['auto_calc'] = self.config_manager.get('grade_settings.rs_auto_calc', True)  # 从配置读取
                rs_config['grade1_max'] = self.config_manager.get('impedance.rs_grade1_max', 17.0)
                rs_config['grade2_max'] = self.config_manager.get('impedance.rs_grade2_max', 33.5)
                rs_config['grade3_max'] = self.config_manager.get('impedance.rs_grade3_max', 50.0)
                self.ui_manager.load_rs_config(rs_config)

                # 修复加载Rct配置（优先从grade_settings读取，兼容impedance节点）
                rct_config = {}
                # 优先从grade_settings读取，如果没有则从impedance读取
                rct_config['min_value'] = self.config_manager.get('grade_settings.rct_min',
                                                                self.config_manager.get('impedance.rct_min', 5.0))
                rct_config['max_value'] = self.config_manager.get('grade_settings.rct_max',
                                                                self.config_manager.get('impedance.rct_grade3_max', 100.0))
                rct_config['auto_calc'] = self.config_manager.get('grade_settings.rct_auto_calc', True)  # 从配置读取
                rct_config['grade1_max'] = self.config_manager.get('impedance.rct_grade1_max', 35.0)
                rct_config['grade2_max'] = self.config_manager.get('impedance.rct_grade2_max', 70.0)
                rct_config['grade3_max'] = self.config_manager.get('impedance.rct_grade3_max', 100.0)
                self.ui_manager.load_rct_config(rct_config)

                # 修复加载电压配置（优先从grade_settings读取取样测试应用的参数）
                voltage_config = {}
                voltage_config['standard_voltage'] = self.config_manager.get('grade_settings.standard_voltage', 3.21)
                # 优先使用取样测试应用的电压范围参数
                voltage_min = self.config_manager.get('grade_settings.voltage_min')
                voltage_max = self.config_manager.get('grade_settings.voltage_max')
                if voltage_min is not None and voltage_max is not None:
                    # 如果有取样测试应用的参数，使用这些参数
                    voltage_config['min_voltage'] = voltage_min
                    voltage_config['max_voltage'] = voltage_max
                    logger.info(f"✅ 使用取样测试应用的电压参数: {voltage_min:.3f}V - {voltage_max:.3f}V")
                else:
                    # 否则使用默认配置
                    voltage_config['min_voltage'] = self.config_manager.get('grade_settings.min_voltage', 3.05)
                    voltage_config['max_voltage'] = self.config_manager.get('grade_settings.max_voltage', 3.37)

                voltage_config['auto_calc_range'] = self.config_manager.get('grade_settings.auto_calc_range', True)
                voltage_config['battery_type'] = self.config_manager.get('grade_settings.battery_type', 0)
                voltage_config['voltage_diff'] = self.config_manager.get('grade_settings.voltage_diff', 0.16)
                self.ui_manager.load_voltage_config(voltage_config)

            # 🚫 离群检测配置加载已删除

            # 更新显示
            self._update_all_displays()

            logger.info("所有配置加载完成")

        except Exception as e:
            logger.error(f"加载所有配置失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        try:
            # 保存配置
            self.save_all_config()
            
            # 清理各个管理器
            # 🚫 离群检测UI管理器清理已删除

            if hasattr(self, 'grade_range_manager'):
                self.grade_range_manager.cleanup()
            
            if hasattr(self, 'voltage_range_manager'):
                self.voltage_range_manager.cleanup()
            
            if hasattr(self, 'ui_manager'):
                self.ui_manager.cleanup()
            
            logger.info("档位设置组件资源清理完成")
            
        except Exception as e:
            logger.error(f"清理资源失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self.cleanup()
        super().closeEvent(event)
