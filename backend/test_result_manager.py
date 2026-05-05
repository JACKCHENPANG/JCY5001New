# -*- coding: utf-8 -*-
"""
测试结果管理器
负责测试结果的计算、保存、批次管理等功能

从TestFlowController中提取的测试结果管理功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
import time
import sys
import os
import json
import math
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class TestResultManager:
    """
    测试结果管理器
    
    职责：
    - Rs/Rct计算和分析
    - 测试结果保存
    - 批次管理
    - 档位计算和合格性判断
    - 测试时间记录
    """
    
    def __init__(self, config_manager, impedance_data_manager, data_upload_manager=None):
        """
        初始化测试结果管理器

        Args:
            config_manager: 配置管理器
            impedance_data_manager: 阻抗数据管理器
            data_upload_manager: 数据上传管理器（可选）
        """
        self.config_manager = config_manager
        self.impedance_data_manager = impedance_data_manager
        self.data_upload_manager = data_upload_manager

        # 测试执行器引用（用于获取测试前电压）
        self.test_executor = None

        # 🔥 新增：主窗口引用（用于自动打印）
        self.main_window = None

        # 🚀 性能优化配置
        self.fast_mode_enabled = False
        self.calculation_times = []
        self.max_calculation_time = 2.0  # 最大计算时间阈值（秒）

        # 测试时间记录
        self.test_start_times = {}  # 记录每个通道的测试开始时间
        self.test_end_times = {}    # 记录每个通道的测试结束时间

        # 批次信息
        self.current_batch_id = None
        self.batch_info = {}

        # 电池码信息
        self.battery_codes = []

        # 数据库管理器（延迟初始化）
        self._db_manager = None

        # EIS分析器（延迟初始化）
        self._eis_analyzer = None

        # 修复不要重复设置data_upload_manager为None
        # self.data_upload_manager = None  # 已在第47行设置

        # 新增初始化新的管理器
        self._failure_reason_manager = None
        self._test_mode_manager = None
        self._product_info_manager = None
        self._test_parameter_calculator = None

        logger.info("测试结果管理器初始化完成")

    def _is_using_enhanced_algorithm(self) -> bool:
        """
        检查是否正在使用增强型EIS算法

        Returns:
            是否使用增强型算法
        """
        try:
            # 检查阻抗数据管理器是否使用增强型算法
            if hasattr(self.impedance_data_manager, 'data_processor'):
                data_processor = self.impedance_data_manager.data_processor
                if hasattr(data_processor, 'use_enhanced_analysis'):
                    return data_processor.use_enhanced_analysis and data_processor.enhanced_eis_analyzer is not None

            # 检查自身是否有增强型算法配置
            if hasattr(self, 'use_enhanced_analysis'):
                return self.use_enhanced_analysis

            # 默认返回False（使用标准算法）
            return False
        except Exception as e:
            logger.warning(f"检查增强型算法状态失败: {e}")
            return False

    def set_test_executor(self, test_executor):
        """
        设置测试执行器引用（用于获取测试前电压）

        Args:
            test_executor: 测试执行器实例
        """
        self.test_executor = test_executor
        logger.debug("测试执行器引用已设置")

    def set_data_upload_manager(self, data_upload_manager):
        """
        设置数据上传管理器

        Args:
            data_upload_manager: 数据上传管理器实例
        """
        logger.debug(f" [结果管理器] 正在设置数据上传管理器: {data_upload_manager is not None}")
        self.data_upload_manager = data_upload_manager
        logger.info(f"✅ 数据上传管理器已设置到测试结果管理器: {self.data_upload_manager is not None}")

    @property
    def failure_reason_manager(self):
        """失败原因管理器（延迟初始化）"""
        if self._failure_reason_manager is None:
            from backend.failure_reason_manager import FailureReasonManager
            self._failure_reason_manager = FailureReasonManager(self.config_manager)
            # 🔧 修复：确保配置正确加载，避免多次测试间的状态问题
            self._failure_reason_manager.reload_config()
            logger.debug("失败原因管理器已重新创建并重新加载配置")
        return self._failure_reason_manager

    @property
    def test_mode_manager(self):
        """测试模式管理器（延迟初始化）"""
        if self._test_mode_manager is None:
            from backend.test_mode_manager import TestModeManager
            self._test_mode_manager = TestModeManager(self.config_manager)
        return self._test_mode_manager

    @property
    def product_info_manager(self):
        """产品信息管理器（延迟初始化）"""
        if self._product_info_manager is None:
            from backend.product_info_manager import ProductInfoManager
            self._product_info_manager = ProductInfoManager(self.config_manager)
        return self._product_info_manager

    @property
    def test_parameter_calculator(self):
        """测试参数计算器（延迟初始化）"""
        if self._test_parameter_calculator is None:
            from backend.test_parameter_calculator import TestParameterCalculator
            self._test_parameter_calculator = TestParameterCalculator(self.config_manager)
        return self._test_parameter_calculator
    
    @property
    def db_manager(self):
        """延迟初始化数据库管理器"""
        if self._db_manager is None:
            try:
                # 修复使用全局数据库管理器实例
                from data.database_manager import _database_manager
                if _database_manager is not None:
                    self._db_manager = _database_manager
                    logger.info("✅ 使用全局数据库管理器实例")
                else:
                    # 如果全局实例不存在，创建新实例
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from data.database_manager import DatabaseManager
                    self._db_manager = DatabaseManager()
                    logger.info("✅ 创建新的数据库管理器实例")

                # 测试数据库连接
                if self._db_manager:
                    db_info = self._db_manager.get_database_info()
                    logger.info(f"数据库管理器初始化成功: {db_info['db_path']}")

            except Exception as e:
                logger.error(f"❌ 初始化数据库管理器失败: {e}")
                import traceback
                logger.error(f"详细错误: {traceback.format_exc()}")
                self._db_manager = None
        return self._db_manager
    
    @property
    def eis_analyzer(self):
        """延迟初始化EIS分析器"""
        if self._eis_analyzer is None:
            try:
                from backend.eis_analyzer import EISAnalyzer
                self._eis_analyzer = EISAnalyzer()
            except Exception as e:
                logger.error(f"初始化EIS分析器失败: {e}")
                self._eis_analyzer = None
        return self._eis_analyzer
    
    def setup_new_batch(self, batch_info: Dict, battery_codes: List[str]) -> int:
        """
        设置新的批次信息，确保批次ID的独立性

        Args:
            batch_info: 批次信息
            battery_codes: 电池码列表

        Returns:
            新创建的批次ID
        """
        try:
            logger.info("📋 设置新批次信息...")

            # 修复确保使用产品信息中的最新批次号
            updated_batch_info = batch_info.copy()
            current_batch_number = self.product_info_manager.get_batch_number()
            if current_batch_number and current_batch_number != 'BATCH-UNKNOWN':
                updated_batch_info['batch_number'] = current_batch_number
                logger.info(f"📋 使用产品信息中的批次号: {current_batch_number}")

            # 1. 创建新的批次记录（确保独立性）
            new_batch_id = self._create_new_batch(updated_batch_info)

            # 2. 设置当前批次信息
            self.current_batch_id = new_batch_id
            self.batch_info = updated_batch_info.copy()  # 使用更新后的批次信息
            self.batch_info['batch_id'] = new_batch_id  # 确保批次ID一致

            # 3. 记录电池码信息
            self.battery_codes = battery_codes.copy() if battery_codes else []

            logger.info(f"✅ 新批次设置完成: ID={new_batch_id}, 批次号={updated_batch_info.get('batch_number', 'Unknown')}")
            logger.info(f"📦 电池码数量: {len(self.battery_codes)}")

            return new_batch_id

        except Exception as e:
            logger.error(f"设置新批次失败: {e}")
            # 使用默认批次ID作为备用
            self.current_batch_id = self._ensure_batch_exists()
            self.batch_info = batch_info.copy()
            return self.current_batch_id
    
    def record_test_start(self, channel_nums: List[int]):
        """
        记录测试开始时间
        
        Args:
            channel_nums: 通道号列表
        """
        test_start_time = time.time()
        for channel_num in channel_nums:
            self.test_start_times[channel_num] = test_start_time
        
        logger.info(f"记录测试开始时间: 通道{channel_nums}")
    
    def record_test_end(self, channel_nums: List[int]):
        """
        记录测试结束时间
        
        Args:
            channel_nums: 通道号列表
        """
        test_end_time = time.time()
        for channel_num in channel_nums:
            self.test_end_times[channel_num] = test_end_time
        
        logger.info(f"记录测试结束时间: 通道{channel_nums}")
    
    def calculate_rs_rct_for_channel(self, channel_num: int) -> Tuple[float, float]:
        """
        为指定通道计算Rs和Rct值（使用真实阻抗数据）

        Args:
            channel_num: 通道号（1-8）

        Returns:
            (rs_value, rct_value) 元组
        """
        try:
            # 修复检查是否为采样测试模式，采样测试模式下即使停止也要计算Rs/Rct
            sampling_test = False
            if hasattr(self, 'config_manager') and self.config_manager:
                sampling_test = self.config_manager.get('test.sampling_test', False)

            # 修复：检查测试是否被停止，但如果有部分阻抗数据则尝试计算
            test_stopped = False
            if not sampling_test and hasattr(self, 'test_executor') and self.test_executor and hasattr(self.test_executor, 'stop_event'):
                if self.test_executor.stop_event.is_set():
                    test_stopped = True
                    logger.info(f"🛑 通道{channel_num}测试已被停止，但将尝试基于已有数据计算Rs/Rct")
            elif sampling_test:
                logger.info(f"🎯 通道{channel_num}采样测试模式：即使测试停止也继续计算Rs/Rct")

            import time
            start_time = time.time()
            logger.info(f"🚀 [性能监控版本] 开始为通道{channel_num}计算Rs和Rct值（使用真实数据）")

            # 从阻抗数据管理器获取该通道的所有频点数据
            data_start_time = time.time()
            channel_data = self.impedance_data_manager.get_channel_impedance_data(channel_num)
            data_time = time.time() - data_start_time
            logger.info(f"⏱️ 通道{channel_num}获取阻抗数据耗时: {data_time:.3f}秒")

            # 添加调试信息
            logger.info(f"通道{channel_num}阻抗数据获取结果: {len(channel_data) if channel_data else 0}个频点")
            if channel_data:
                frequencies = list(channel_data.keys())
                logger.info(f"通道{channel_num}频点列表: {sorted(frequencies)}")
                # 显示前几个数据点的详细信息
                for i, (freq, data) in enumerate(list(channel_data.items())[:3]):
                    logger.info(f"通道{channel_num}频点{freq}Hz: Re={data.get('real', 0):.3f}μΩ, Im={data.get('imag', 0):.3f}μΩ")

            if not channel_data:
                if test_stopped:
                    logger.warning(f"🛑 通道{channel_num}测试被停止且无阻抗数据，返回0值避免错误档位判定")
                    return 0.0, 0.0
                else:
                    logger.warning(f"通道{channel_num}没有阻抗数据，使用默认值")
                    return 5.0, 10.0
            
            # 提取频率和阻抗数据
            frequencies = []
            real_parts = []
            imag_parts = []
            
            for freq, impedance_info in channel_data.items():
                frequencies.append(freq)
                real_parts.append(impedance_info['real'] / 1000.0)  # 转换为mΩ
                imag_parts.append(impedance_info['imag'] / 1000.0)  # 转换为mΩ
            
            if len(frequencies) == 0:
                logger.warning(f"通道{channel_num}没有有效的阻抗数据点")
                return 5.0, 10.0
            
            logger.info(f"通道{channel_num}阻抗数据: {len(frequencies)}个频点，"
                       f"频率范围{min(frequencies):.3f}-{max(frequencies):.3f}Hz")
            
            # 使用EIS分析器计算Rs和Rct
            if not self.eis_analyzer:
                logger.error("EIS分析器未初始化")
                return 5.0, 10.0
            
            # 仅使用增强版EIS算法（半圆直径法），失败直接报错，不回退
            eis_start_time = time.time()
            from backend.eis_analyzer import EISAnalyzer
            eis_analyzer = EISAnalyzer()

            cell_id = f"CH_{channel_num}"
            enhanced_result = eis_analyzer.calculate_rs_rct_enhanced(
                frequencies, real_parts, imag_parts, cell_id
            )
            eis_time = time.time() - eis_start_time
            self.calculation_times.append(eis_time)
            logger.info(f"⏱️ 通道{channel_num}增强版EIS分析耗时: {eis_time:.3f}秒")

            if not (enhanced_result and enhanced_result.get('analysis_success')):
                err_msg = enhanced_result.get('error') if isinstance(enhanced_result, dict) else '增强版分析失败'
                logger.error(f"通道{channel_num}增强版EIS分析失败（不回退）：{err_msg}")
                raise RuntimeError(err_msg)

            rs_value = enhanced_result['rs_value']
            rct_value = enhanced_result['rct_value']
            rsei_value = enhanced_result.get('rsei_value', 0.0)
            logger.info(f"✅ 通道{channel_num}增强版EIS分析成功: Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ, Rsei={rsei_value:.3f}mΩ")

            # 存储Rsei值和增强版分析结果到通道数据中
            if hasattr(self, '_channel_rsei_cache'):
                self._channel_rsei_cache[channel_num] = rsei_value
            else:
                self._channel_rsei_cache = {channel_num: rsei_value}

            # 存储增强版分析结果
            if enhanced_result and hasattr(self, '_channel_enhanced_cache'):
                self._channel_enhanced_cache[channel_num] = enhanced_result
            elif enhanced_result:
                self._channel_enhanced_cache = {channel_num: enhanced_result}

            total_time = time.time() - start_time
            logger.info(f"⏱️ ✅ 通道{channel_num}Rs/Rct计算完成，总耗时: {total_time:.3f}秒")
            return rs_value, rct_value
            
        except Exception as e:
            logger.error(f"计算通道{channel_num}的Rs/Rct失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return 5.0, 10.0

    def _calculate_rsei_for_channel(self, frequencies: List[float], real_parts: List[float],
                                   imag_parts: List[float]) -> float:
        """
        计算通道的Rsei值（SEI膜电阻）

        Args:
            frequencies: 频率列表 (Hz)
            real_parts: 实部阻抗列表 (mΩ)
            imag_parts: 虚部阻抗列表 (mΩ)

        Returns:
            Rsei值 (mΩ)
        """
        try:
            if len(frequencies) < 5:
                logger.debug("频率点数量不足，无法计算Rsei")
                return 0.0

            # 转换为numpy数组便于计算
            import numpy as np
            freq_array = np.array(frequencies)
            real_array = np.array(real_parts)

            # 修复针对磷酸铁锂电池，降低高频阈值并增加备用方案
            high_freq_mask = freq_array > 50  # 从100Hz降到50Hz
            high_freq_indices = np.where(high_freq_mask)[0]

            if len(high_freq_indices) < 2:  # 降低最小点数要求
                logger.debug("高频点数量不足，尝试使用中频区域计算Rsei")
                # 备用方案：使用中频区域（10-100Hz）
                mid_freq_mask = (freq_array >= 10) & (freq_array <= 100)
                mid_freq_indices = np.where(mid_freq_mask)[0]
                if len(mid_freq_indices) >= 2:
                    high_freq_indices = mid_freq_indices
                    logger.debug(f"使用中频区域计算Rsei，频率范围: 10-100Hz，点数: {len(mid_freq_indices)}")
                else:
                    logger.debug("中频点数量也不足，无法计算Rsei")
                    return 0.0

            # 计算高频区域的阻抗变化
            high_freq_real = real_array[high_freq_indices]
            real_change = np.max(high_freq_real) - np.min(high_freq_real)
            total_change = np.max(real_array) - np.min(real_array)  # 使用全范围计算总变化

            # 修复针对磷酸铁锂电池，进一步放宽检测条件
            min_absolute_change = 0.02  # 进一步降低绝对阈值
            min_relative_change = 0.01  # 进一步降低相对阈值（1%）

            if (real_change > min_relative_change * total_change and  # 相对变化检查
                real_change > min_absolute_change and                # 绝对变化检查
                total_change > 0.1):                                 # 总变化足够大

                logger.info(f"✅ 检测到SEI特征: Rsei={real_change:.3f}mΩ, "
                           f"高频变化={real_change:.4f}mΩ, 占总变化比例={real_change/total_change*100:.1f}%")
                return float(real_change)
            else:
                # 新增磷酸铁锂电池的备用计算方法
                if total_change > 0.5:  # 如果总变化足够大
                    # 使用经验公式：Rsei约为总阻抗变化的10-20%
                    estimated_rsei = total_change * 0.15  # 15%经验值
                    if estimated_rsei >= 0.05:  # 如果估算值合理
                        logger.info(f"✅ 使用经验公式计算Rsei: {estimated_rsei:.3f}mΩ (总变化的15%)")
                        return estimated_rsei

                logger.debug(f"❌ 未检测到明显SEI特征: 高频变化={real_change:.4f}mΩ, "
                           f"占总变化比例={real_change/total_change*100:.1f}%, 总变化={total_change:.3f}mΩ")
                return 0.0

        except Exception as e:
            logger.error(f"计算Rsei失败: {e}")
            return 0.0

    def get_channel_rsei_value(self, channel_num: int) -> float:
        """
        获取通道的Rsei值

        Args:
            channel_num: 通道号（1-8）

        Returns:
            Rsei值 (mΩ)
        """
        try:
            if hasattr(self, '_channel_rsei_cache') and channel_num in self._channel_rsei_cache:
                return self._channel_rsei_cache[channel_num]
            else:
                logger.debug(f"通道{channel_num}没有缓存的Rsei值")
                return 0.0
        except Exception as e:
            logger.error(f"获取通道{channel_num}Rsei值失败: {e}")
            return 0.0

    def get_channel_enhanced_analysis(self, channel_num: int) -> Optional[Dict]:
        """
        获取通道的增强版EIS分析结果

        Args:
            channel_num: 通道号（1-8）

        Returns:
            增强版分析结果字典，如果没有则返回None
        """
        try:
            if hasattr(self, '_channel_enhanced_cache') and channel_num in self._channel_enhanced_cache:
                return self._channel_enhanced_cache[channel_num]
            else:
                logger.debug(f"通道{channel_num}没有缓存的增强版分析结果")
                return None
        except Exception as e:
            logger.error(f"获取通道{channel_num}增强版分析结果失败: {e}")
            return None
    
    def calculate_grades(self, rs_value: float, rct_value: float) -> Tuple[int, int]:
        """
        计算Rs和Rct档位 - 使用范围区间判断

        Args:
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)

        Returns:
            (rs_grade, rct_grade) 元组
        """
        try:
            # 修复：如果Rs和Rct都为0（测试停止导致），返回None表示无效档位
            if rs_value == 0.0 and rct_value == 0.0:
                logger.warning("Rs和Rct值都为0，可能是测试被停止，返回None档位")
                return None, None

            # 🔧 [单频点修复] 单频点测试时Rct=0是正常的，Rct默认为1档，Rs正常计算档位
            is_single_freq_test = (rct_value == 0.0 and rs_value > 0)
            if is_single_freq_test:
                logger.info(f"🔧 [单频点测试] 检测到单频点测试: Rs={rs_value:.3f}mΩ, Rct=0.000mΩ，Rs正常计算档位，Rct默认为1档")
                # 单频点测试：Rs正常计算档位，Rct固定为1档
                rs_grade = self._calculate_rs_grade_only(rs_value)
                return rs_grade, 1
            # 修复使用范围区间判断而不是上限值判断
            # 获取Rs档位范围配置
            rs_grade_count = self.config_manager.get('impedance.rs_grade_count', 3)

            # 修复获取Rs档位范围，超出范围时归到最接近的档位
            if rs_grade_count == 1:
                # 1档模式：检查Rs值是否在1档范围内
                rs_min = self.config_manager.get('impedance.rs_min', 0.0)
                rs_max = self.config_manager.get('impedance.rs_grade1_max', 50.0)

                if rs_min <= rs_value <= rs_max:
                    rs_grade = 1
                else:
                    rs_grade = 0  # 超出范围标记为不合格

                # 🔧 修复：为1档模式定义rs1_min等变量，避免后续日志输出时出现未定义错误
                rs1_min = rs_min
                rs1_max = rs_max
                rs2_min = rs_min  # 1档模式下不使用rs2，但需要定义以避免日志错误
                rs2_max = rs_max
                rs3_min = rs_min  # 1档模式下不使用rs3，但需要定义以避免日志错误
                rs3_max = rs_max

                logger.info(f"🔧 [Rs 1档] 范围检查: Rs({rs_min:.3f}-{rs_max:.3f})mΩ, 值={rs_value:.3f}mΩ, 档位={rs_grade}")
            elif rs_grade_count == 2:
                # 🔧 修复：检查是否启用自动计算
                rs_auto_calc = self.config_manager.get('grade_settings.rs_auto_calc', False)

                if rs_auto_calc:
                    # 自动计算模式：使用grade_settings中的rs_min和rs_max自动计算档位范围
                    rs_min = self.config_manager.get('grade_settings.rs_min', 0.0)
                    rs_max = self.config_manager.get('grade_settings.rs_max', 50.0)

                    # 2档均分
                    mid_val = (rs_min + rs_max) / 2
                    rs1_max = mid_val
                    rs2_max = rs_max

                    logger.info(f"🔧 [Rs 2档-自动计算] 使用grade_settings范围: Rs({rs_min:.3f}-{rs_max:.3f})mΩ, 中间值={mid_val:.3f}mΩ")
                else:
                    # 手动模式：使用impedance中的rs_grade1_max和rs_grade2_max
                    rs_min = self.config_manager.get('impedance.rs_min', 0.0)
                    rs_max = self.config_manager.get('impedance.rs_grade3_max', 50.0)

                    # 2档：使用impedance中的rs_grade1_max和rs_grade2_max
                    rs1_max = self.config_manager.get('impedance.rs_grade1_max')
                    rs2_max = self.config_manager.get('impedance.rs_grade2_max')

                    # 如果impedance中没有配置，则尝试从grade_settings读取
                    if rs1_max is None or rs2_max is None:
                        rs1_max = self.config_manager.get('grade_settings.rs1_max')
                        rs2_max = self.config_manager.get('grade_settings.rs2_max')

                    # 如果还是没有配置，则使用均分
                    if rs1_max is None or rs2_max is None:
                        mid_val = (rs_min + rs_max) / 2
                        rs1_max = mid_val
                        rs2_max = rs_max

                    logger.info(f"🔧 [Rs 2档-手动设置] 使用impedance范围: Rs1_max={rs1_max:.3f}, Rs2_max={rs2_max:.3f}mΩ")

                rs1_min = rs_min
                rs2_min = rs1_max

                # 边界值判断逻辑：边界值属于较高档位
                if rs1_min <= rs_value <= rs1_max:
                    rs_grade = 1
                elif rs2_min <= rs_value <= rs2_max:  # 最高档位包含上边界
                    rs_grade = 2
                else:
                    rs_grade = 0  # 超出范围标记为不合格

                logger.info(f"🔧 [Rs 2档] 范围计算: Rs1({rs1_min:.3f}-{rs1_max:.3f}), Rs2({rs2_min:.3f}-{rs2_max:.3f})mΩ")

            else:  # 3档
                # 🔧 修复：检查是否启用自动计算
                rs_auto_calc = self.config_manager.get('grade_settings.rs_auto_calc', False)

                if rs_auto_calc:
                    # 自动计算模式：使用grade_settings中的rs_min和rs_max自动计算档位范围
                    rs_min = self.config_manager.get('grade_settings.rs_min', 0.0)
                    rs_max = self.config_manager.get('grade_settings.rs_max', 50.0)

                    # 3档均分
                    range_size = (rs_max - rs_min) / 3
                    rs1_max = rs_min + range_size
                    rs2_max = rs_min + 2 * range_size
                    rs3_max = rs_max

                    logger.info(f"🔧 [Rs 3档-自动计算] 使用grade_settings范围: Rs({rs_min:.3f}-{rs_max:.3f})mΩ, 均分为3档")
                else:
                    # 手动模式：使用grade_settings中的具体值
                    rs_min = self.config_manager.get('impedance.rs_min', 0.0)
                    rs_max = self.config_manager.get('impedance.rs_grade3_max', 50.0)

                    # 3档：使用grade_settings中的rs1_max、rs2_max、rs3_max
                    rs1_max = self.config_manager.get('grade_settings.rs1_max')
                    rs2_max = self.config_manager.get('grade_settings.rs2_max')
                    rs3_max = self.config_manager.get('grade_settings.rs3_max')

                    # 如果grade_settings中没有完整配置，则使用均分
                    if rs1_max is None or rs2_max is None or rs3_max is None:
                        range_size = (rs_max - rs_min) / 3
                        rs1_max = rs_min + range_size
                        rs2_max = rs_min + 2 * range_size
                        rs3_max = rs_max

                    logger.info(f"🔧 [Rs 3档-手动设置] 使用grade_settings范围: Rs1_max={rs1_max:.3f}, Rs2_max={rs2_max:.3f}, Rs3_max={rs3_max:.3f}mΩ")

                rs1_min = rs_min
                rs2_min = rs1_max
                rs3_min = rs2_max

                logger.info(f"🔧 [Rs 3档] 范围计算: Rs1({rs1_min:.3f}-{rs1_max:.3f}), Rs2({rs2_min:.3f}-{rs2_max:.3f}), Rs3({rs3_min:.3f}-{rs3_max:.3f})mΩ")

                # 🐛 修复：边界值判断逻辑，边界值属于较高档位
                if rs1_min <= rs_value < rs1_max:
                    rs_grade = 1
                elif rs2_min <= rs_value < rs2_max:
                    rs_grade = 2
                elif rs3_min <= rs_value <= rs3_max:  # 最高档位包含上边界
                    rs_grade = 3
                else:
                    rs_grade = 0  # 超出所有档位范围，标记为不合格

            # 修复从配置文件获取Rct档位范围，支持新旧配置格式
            # 优先使用完整的min/max配置
            rct1_min = self.config_manager.get('grade_settings.rct1_min')
            rct1_max = self.config_manager.get('grade_settings.rct1_max')
            rct2_min = self.config_manager.get('grade_settings.rct2_min')
            rct2_max = self.config_manager.get('grade_settings.rct2_max')
            rct3_min = self.config_manager.get('grade_settings.rct3_min')
            rct3_max = self.config_manager.get('grade_settings.rct3_max')

            logger.debug(f"🔍 [调试] Rct配置读取: rct1_min={rct1_min}, rct1_max={rct1_max}, rct2_min={rct2_min}, rct2_max={rct2_max}, rct3_min={rct3_min}, rct3_max={rct3_max}")

            # 如果min/max配置不完整，尝试从现有配置计算
            if any(v is None for v in [rct1_min, rct1_max, rct2_min, rct2_max, rct3_min, rct3_max]):
                # 从现有配置获取总范围和档位最大值
                rct_min_total = self.config_manager.get('grade_settings.rct_min', self.config_manager.get('rct_min', 0.001))
                rct_max_total = self.config_manager.get('grade_settings.rct_max', self.config_manager.get('rct_max', 0.086))
                # 🐛 修复：使用正确的配置路径
                rct1_max_config = self.config_manager.get('grade_settings.rct1_max') or self.config_manager.get('rct1_max')
                rct2_max_config = self.config_manager.get('grade_settings.rct2_max') or self.config_manager.get('rct2_max')
                rct3_max_config = self.config_manager.get('grade_settings.rct3_max') or self.config_manager.get('rct3_max')

                if all(v is not None for v in [rct1_max_config, rct2_max_config, rct3_max_config]):
                    # 🐛 修复：使用正确的档位范围计算逻辑，边界值包含在较高档位中
                    rct1_min = rct_min_total
                    rct1_max = rct1_max_config
                    rct2_min = rct1_max_config  # Rct2最小值 = Rct1最大值，边界值属于Rct2
                    rct2_max = rct2_max_config
                    rct3_min = rct2_max_config  # Rct3最小值 = Rct2最大值，边界值属于Rct3
                    rct3_max = rct3_max_config
                    logger.info(f"🐛 [档位修复] 使用配置档位范围: Rct1({rct1_min:.3f}-{rct1_max:.3f}), Rct2({rct2_min:.3f}-{rct2_max:.3f}), Rct3({rct3_min:.3f}-{rct3_max:.3f})mΩ")
                else:
                    # 使用备用配置
                    logger.warning("Rct档位配置不完整，使用备用配置")
                    rct1_min, rct1_max = 3.807, 4.368
                    rct2_min, rct2_max = 4.368, 4.930
                    rct3_min, rct3_max = 4.930, 5.491

            # 🐛 修复：边界值判断逻辑，边界值属于较高档位
            rct_grade = 0  # 默认为不合格
            logger.debug(f"🔍 [调试] Rct档位判断: rct_value={rct_value:.3f}, rct1_min={rct1_min}, rct1_max={rct1_max}, rct2_min={rct2_min}, rct2_max={rct2_max}, rct3_min={rct3_min}, rct3_max={rct3_max}")

            if rct1_min <= rct_value <= rct1_max:
                rct_grade = 1
                logger.debug(f"🔍 [调试] Rct档位判断: {rct_value:.3f} 在 [{rct1_min:.3f}, {rct1_max:.3f}] → 1档")
            elif rct2_min <= rct_value <= rct2_max:
                rct_grade = 2
                logger.debug(f"🔍 [调试] Rct档位判断: {rct_value:.3f} 在 [{rct2_min:.3f}, {rct2_max:.3f}] → 2档")
            elif rct3_min <= rct_value <= rct3_max:  # 最高档位包含上边界
                rct_grade = 3
                logger.debug(f"🔍 [调试] Rct档位判断: {rct_value:.3f} 在 [{rct3_min:.3f}, {rct3_max:.3f}] → 3档")
            else:
                rct_grade = 0  # 不在任何档位范围内
                logger.debug(f"🔍 [调试] Rct档位判断: {rct_value:.3f} 不在任何范围内 → 0档")

            # 修复：根据档位数量打印相应的范围信息
            if rs_grade_count == 2:
                logger.info(f"🎯 档位计算范围: Rs1({rs1_min:.3f}-{rs1_max:.3f}), Rs2({rs2_min:.3f}-{rs2_max:.3f})mΩ")
            else:  # 3档
                logger.info(f"🎯 档位计算范围: Rs1({rs1_min:.3f}-{rs1_max:.3f}), Rs2({rs2_min:.3f}-{rs2_max:.3f}), Rs3({rs3_min:.3f}-{rs3_max:.3f})mΩ")

            logger.info(f"🎯 档位计算范围: Rct1({rct1_min:.3f}-{rct1_max:.3f}), Rct2({rct2_min:.3f}-{rct2_max:.3f}), Rct3({rct3_min:.3f}-{rct3_max:.3f})mΩ")
            logger.info(f"🎯 档位计算结果: Rs={rs_value:.3f}mΩ→{rs_grade}档, Rct={rct_value:.3f}mΩ→{rct_grade}档")

            return rs_grade, rct_grade

        except Exception as e:
            logger.error(f"计算档位失败: {e}")
            return 1, 1

    def _calculate_rs_grade_only(self, rs_value: float) -> int:
        """
        仅计算Rs档位（用于单频点测试）

        Args:
            rs_value: Rs值 (mΩ)

        Returns:
            rs_grade: Rs档位
        """
        try:
            # 获取Rs档位范围配置
            rs_grade_count = self.config_manager.get('impedance.rs_grade_count', 3)

            # 修复获取Rs档位范围，超出范围时归到最接近的档位
            if rs_grade_count == 1:
                # 1档模式：检查Rs值是否在1档范围内
                rs_min = self.config_manager.get('impedance.rs_min', 0.0)
                rs_max = self.config_manager.get('impedance.rs_grade1_max', 50.0)

                if rs_min <= rs_value <= rs_max:
                    rs_grade = 1
                else:
                    rs_grade = 0  # 超出范围标记为不合格

                logger.info(f"🔧 [单频点] Rs 1档范围检查: Rs({rs_min:.3f}-{rs_max:.3f})mΩ, 值={rs_value:.3f}mΩ, 档位={rs_grade}")
            elif rs_grade_count == 2:
                # 🔧 修复：使用impedance中的rs_grade1_max和rs_grade2_max
                rs_min = self.config_manager.get('impedance.rs_min', 0.0)
                rs_max = self.config_manager.get('impedance.rs_grade3_max', 50.0)

                # 2档：使用impedance中的rs_grade1_max和rs_grade2_max
                rs1_max = self.config_manager.get('impedance.rs_grade1_max')
                rs2_max = self.config_manager.get('impedance.rs_grade2_max')

                # 如果impedance中没有配置，则尝试从grade_settings读取
                if rs1_max is None or rs2_max is None:
                    rs1_max = self.config_manager.get('grade_settings.rs1_max')
                    rs2_max = self.config_manager.get('grade_settings.rs2_max')

                # 如果还是没有配置，则使用均分
                if rs1_max is None or rs2_max is None:
                    mid_val = (rs_min + rs_max) / 2
                    rs1_max = mid_val
                    rs2_max = rs_max

                rs1_min = rs_min
                rs2_min = rs1_max

                # 边界值判断逻辑：边界值属于较高档位
                if rs1_min <= rs_value <= rs1_max:
                    rs_grade = 1
                elif rs2_min <= rs_value <= rs2_max:  # 最高档位包含上边界
                    rs_grade = 2
                else:
                    rs_grade = 0  # 超出范围标记为不合格

            else:  # 3档
                # 🔧 修复：使用grade_settings中的具体值，而不是均分
                rs_min = self.config_manager.get('impedance.rs_min', 0.0)
                rs_max = self.config_manager.get('impedance.rs_grade3_max', 50.0)

                # 3档：使用grade_settings中的rs1_max、rs2_max、rs3_max
                rs1_max = self.config_manager.get('grade_settings.rs1_max')
                rs2_max = self.config_manager.get('grade_settings.rs2_max')
                rs3_max = self.config_manager.get('grade_settings.rs3_max')

                # 如果grade_settings中没有完整配置，则使用均分
                if rs1_max is None or rs2_max is None or rs3_max is None:
                    range_size = (rs_max - rs_min) / 3
                    rs1_max = rs_min + range_size
                    rs2_max = rs_min + 2 * range_size
                    rs3_max = rs_max

                rs1_min = rs_min
                rs2_min = rs1_max
                rs3_min = rs2_max

                # 边界值判断逻辑
                if rs1_min <= rs_value < rs1_max:
                    rs_grade = 1
                elif rs2_min <= rs_value < rs2_max:
                    rs_grade = 2
                elif rs3_min <= rs_value <= rs3_max:  # 最高档位包含上边界
                    rs_grade = 3
                else:
                    rs_grade = 0  # 超出所有档位范围

            logger.info(f"🔧 [单频点] Rs档位计算: Rs={rs_value:.3f}mΩ→{rs_grade}档")
            return rs_grade

        except Exception as e:
            logger.error(f"计算Rs档位失败: {e}")
            return 1
    
    def judge_test_result(self, voltage: float, rs_value: float, rct_value: float, outlier_result: Optional[str] = None, channel_num: Optional[int] = None) -> Tuple[bool, List[str]]:
        """
        判断测试结果（按优先级判断）

        优先级顺序：
        1. 电压检测（电压范围不合格）
        2. 离群率检测（偏差超过阈值）
        3. Rs档位判断
        4. Rct档位判断

        Args:
            voltage: 电压值 (V)
            rs_value: Rs值 (mΩ)
            rct_value: Rct值 (mΩ)
            outlier_result: 离群率检测结果（"PASS"或偏差百分比）
            channel_num: 通道号（用于调试日志）

        Returns:
            (is_pass, fail_items) 元组
        """
        try:
            # 修复优先从grade_settings获取判断参数，确保使用最新的测试配置
            # 电压参数：优先使用界面设置的standard_voltage和voltage_diff，备用取样测试的voltage_min/max
            standard_voltage = self.config_manager.get('grade_settings.standard_voltage')
            voltage_diff = self.config_manager.get('grade_settings.voltage_diff')

            if standard_voltage is not None and voltage_diff is not None:
                # 使用界面设置的标准电压和电压差计算范围
                voltage_min = standard_voltage - voltage_diff
                voltage_max = standard_voltage + voltage_diff
                logger.debug(f"使用界面设置电压参数: 标准电压={standard_voltage:.3f}V, 电压差=±{voltage_diff:.3f}V, 范围=({voltage_min:.3f}-{voltage_max:.3f}V)")
            else:
                # 备用：使用取样测试应用的电压范围
                voltage_min = self.config_manager.get('grade_settings.voltage_min')
                if voltage_min is None:
                    voltage_min = self.config_manager.get('test_params.voltage_range.min', 2.889)

                voltage_max = self.config_manager.get('grade_settings.voltage_max')
                if voltage_max is None:
                    voltage_max = self.config_manager.get('test_params.voltage_range.max', 3.531)
                logger.debug(f"使用备用电压参数: 范围=({voltage_min:.3f}-{voltage_max:.3f}V)")

            # Rs参数：优先使用grade_settings，备用impedance配置
            rs_min = self.config_manager.get('grade_settings.rs_min')
            if rs_min is None:
                rs_min = self.config_manager.get('impedance.rs_min', 0.5)

            rs_max = self.config_manager.get('grade_settings.rs_max')
            if rs_max is None:
                rs_max = self.config_manager.get('impedance.rs_grade3_max', 50.0)

            # Rct参数：优先使用grade_settings，备用impedance配置
            rct_min = self.config_manager.get('grade_settings.rct_min')
            if rct_min is None:
                rct_min = self.config_manager.get('impedance.rct_min', 0.5)

            rct_max = self.config_manager.get('grade_settings.rct_max')
            if rct_max is None:
                rct_max = self.config_manager.get('impedance.rct_grade3_max', 100.0)

            fail_items = []

            # 修复将判断参数日志改为DEBUG级别，减少日志噪音
            try:
                logger.debug(f"🔍 通道{channel_num}判断参数: 电压({voltage_min:.3f}-{voltage_max:.3f}V), "
                            f"Rs({rs_min:.3f}-{rs_max:.3f}mΩ), Rct({rct_min:.3f}-{rct_max:.3f}mΩ)")
            except (TypeError, ValueError):
                logger.debug(f"🔍 通道{channel_num}判断参数: 电压({voltage_min}-{voltage_max}V), "
                            f"Rs({rs_min}-{rs_max}mΩ), Rct({rct_min}-{rct_max}mΩ)")

            # 检查所有失败项目（不按优先级提前返回，显示完整失败原因）

            # 检查电压
            if voltage < voltage_min or voltage > voltage_max:
                fail_items.append("电压")
                logger.debug(f"通道{channel_num}电压不合格: {voltage:.3f}V (范围: {voltage_min:.3f}-{voltage_max:.3f}V)")

            # 🚫 离群率检测功能已删除

            # 检查Rs档位判断 - 检查是否在有效档位范围内
            rs_grade, rct_grade = self.calculate_grades(rs_value, rct_value)

            # 修复：正确处理None档位（测试停止导致）
            if rs_grade is None:
                fail_items.append("Rs")
                logger.debug(f"通道{channel_num}Rs无法判定: {rs_value:.3f}mΩ (测试被停止)")
            elif rs_grade == 0:
                fail_items.append("Rs")
                logger.debug(f"通道{channel_num}Rs不合格: {rs_value:.3f}mΩ (超出所有档位范围)")
            elif rs_value > rs_max or rs_value < rs_min:
                fail_items.append("Rs")
                logger.debug(f"通道{channel_num}Rs不合格: {rs_value:.3f}mΩ (范围: {rs_min:.3f}-{rs_max:.3f}mΩ)")

            # 检查Rct档位判断 - 检查是否在有效档位范围内
            # 🔧 [单频点修复] 单频点测试时不做Rct判断，直接默认为合格
            is_single_freq_test = (rct_value == 0.0 and rs_value > 0)
            if not is_single_freq_test:
                if rct_grade is None:
                    fail_items.append("Rct")
                    logger.debug(f"通道{channel_num}Rct无法判定: {rct_value:.3f}mΩ (测试被停止)")
                elif rct_grade == 0:
                    fail_items.append("Rct")
                    logger.debug(f"通道{channel_num}Rct不合格: {rct_value:.3f}mΩ (超出所有档位范围)")
                elif rct_value > rct_max or rct_value < rct_min:
                    fail_items.append("Rct")
                    logger.debug(f"通道{channel_num}Rct不合格: {rct_value:.3f}mΩ (范围: {rct_min:.3f}-{rct_max:.3f}mΩ)")
            else:
                logger.debug(f"🔧 [单频点测试] 通道{channel_num}跳过Rct判断: Rct={rct_value:.3f}mΩ (单频点测试默认合格)")

            is_pass = len(fail_items) == 0

            # 修复将详细判断日志改为DEBUG级别，避免与统一结果日志重复
            if is_pass:
                logger.debug(f"🔍 通道{channel_num}判断详情: 测试合格 - 电压={voltage:.3f}V, Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ, 离群率={outlier_result}")
            else:
                logger.debug(f"🔍 通道{channel_num}判断详情: 测试不合格 - 失败项目={fail_items}")

            return is_pass, fail_items

        except Exception as e:
            logger.error(f"判断测试结果失败: {e}")
            return False, ["系统错误"]

    def get_latest_test_results(self, enabled_channels: List[int]) -> List[Dict[str, Any]]:
        """
        获取最新的测试结果数据

        Args:
            enabled_channels: 启用的通道列表

        Returns:
            测试结果列表
        """
        try:
            # Jack要求检查测试是否被停止，如果停止则不获取最新结果
            if hasattr(self, 'test_executor') and self.test_executor and hasattr(self.test_executor, 'stop_event'):
                if self.test_executor.stop_event.is_set():
                    logger.warning("🛑 测试已被停止，跳过获取最新测试结果，避免计算脏数据")
                    return []

            results = []

            for channel_num in enabled_channels:
                # 计算Rs和Rct值（使用真实阻抗数据）
                rs_value, rct_value = self.calculate_rs_rct_for_channel(channel_num)

                # 修复优先使用测试前保存的电压值（静置状态下的准确电压）
                voltage = 3.7  # 默认电压
                voltage_source = 'default'  # 记录电压来源

                # 尝试从测试执行器获取测试前保存的电压
                try:
                    # 从测试执行器获取测试前电压
                    if hasattr(self, 'test_executor') and self.test_executor and hasattr(self.test_executor, 'pre_test_voltages'):
                        pre_test_voltage = self.test_executor.pre_test_voltages.get(channel_num)
                        if pre_test_voltage is not None and pre_test_voltage > 0:
                            voltage = pre_test_voltage
                            voltage_source = 'pre_test'
                            logger.info(f"✅ 通道{channel_num}使用测试前保存的电压: {voltage:.3f}V")
                        else:
                            logger.warning(f"⚠️ 通道{channel_num}未找到测试前保存的电压")
                    else:
                        logger.warning(f"⚠️ 无法访问测试执行器的测试前电压数据")

                    # 如果没有测试前电压，尝试从最近的测试结果中获取
                    if voltage == 3.7:  # 仍然是默认值
                        if self.db_manager:
                            recent_results = self.db_manager.get_recent_test_results(
                                channel_number=channel_num,
                                limit=1
                            )
                            if recent_results:
                                db_voltage = recent_results[0].get('voltage', 3.7)
                                if db_voltage > 0:
                                    voltage = db_voltage
                                    voltage_source = 'database'
                                    logger.debug(f"从数据库获取通道{channel_num}最近电压: {voltage:.3f}V")

                    # 最后备用方案：读取当前电压
                    if voltage == 3.7:  # 仍然是默认值
                        try:
                            # 尝试从设备配置管理器读取当前电压
                            if hasattr(self, 'device_config_manager') and self.device_config_manager:
                                current_voltage = self.device_config_manager.read_channel_voltage(channel_num)
                                if current_voltage and current_voltage > 0:
                                    voltage = current_voltage
                                    voltage_source = 'current'
                                    logger.info(f"通道{channel_num}使用当前读取电压: {voltage:.3f}V")
                        except Exception as current_e:
                            logger.debug(f"读取当前电压失败: {current_e}")

                    logger.info(f"通道{channel_num}最终电压: {voltage:.3f}V (来源: {voltage_source})")

                except Exception as e:
                    logger.debug(f"获取电压失败: {e}")
                    voltage = 3.7
                    voltage_source = 'default'

                # 修复计算档位和判断合格性，避免重复日志
                rs_grade, rct_grade = self.calculate_grades(rs_value, rct_value)
                is_pass, fail_items = self.judge_test_result(voltage, rs_value, rct_value, channel_num=channel_num)

                # 新增统一的测试结果日志输出（包含档位信息）
                if is_pass:
                    logger.info(f"✅ 通道{channel_num}测试合格: 电压={voltage:.3f}V, Rs={rs_value:.3f}mΩ(档位{rs_grade}), Rct={rct_value:.3f}mΩ(档位{rct_grade})")
                else:
                    logger.info(f"❌ 通道{channel_num}测试不合格: 失败项目={fail_items}, Rs={rs_value:.3f}mΩ(档位{rs_grade}), Rct={rct_value:.3f}mΩ(档位{rct_grade})")

                # 获取频点数据（用于EIS专业分析）
                frequency_data = []  # 🚫 离群检测功能已删除，简化处理
                if not frequency_data:
                    frequency_data = []
                try:
                    if self.impedance_data_manager:
                        # 修复优先从内存获取，如果内存为空则从数据库获取
                        channel_impedance_data = self.impedance_data_manager.get_channel_impedance_data(channel_num)
                        logger.debug(f"通道{channel_num}从内存获取阻抗数据: {len(channel_impedance_data)}个频点")

                        # 如果内存中没有数据，尝试从数据库获取
                        if not channel_impedance_data and self.db_manager:
                            logger.info(f"通道{channel_num}内存中无阻抗数据，尝试从数据库获取")
                            try:
                                # 获取当前批次的阻抗明细数据
                                current_batch_id = self.current_batch_id
                                logger.debug(f"当前批次ID: {current_batch_id}")
                                if current_batch_id:
                                    # 从数据库获取该通道的阻抗数据
                                    db_impedance_data = self.db_manager.get_impedance_details_by_channel(
                                        current_batch_id, channel_num
                                    )
                                    logger.debug(f"从数据库获取到{len(db_impedance_data) if db_impedance_data else 0}条阻抗记录")
                                    if db_impedance_data:
                                        # 转换数据库格式为内存格式
                                        channel_impedance_data = {}
                                        for record in db_impedance_data:
                                            freq = record.get('frequency')
                                            real_imp = record.get('impedance_real', 0.0) * 1000.0  # mΩ转换为μΩ
                                            imag_imp = record.get('impedance_imag', 0.0) * 1000.0  # mΩ转换为μΩ
                                            channel_impedance_data[freq] = {
                                                'real': real_imp,
                                                'imag': imag_imp
                                            }
                                        logger.info(f"通道{channel_num}从数据库获取到{len(channel_impedance_data)}个频点数据")
                                    else:
                                        logger.warning(f"数据库中没有找到通道{channel_num}的阻抗数据")
                                else:
                                    logger.warning(f"当前批次ID为空，无法从数据库获取阻抗数据")
                            except Exception as db_e:
                                logger.error(f"从数据库获取通道{channel_num}阻抗数据失败: {db_e}")
                                import traceback
                                logger.error(f"详细错误: {traceback.format_exc()}")

                        if channel_impedance_data:
                            # 转换为EIS分析器期望的格式
                            for freq, impedance_info in channel_impedance_data.items():
                                if isinstance(impedance_info, dict):
                                    # 修复使用正确的字段名
                                    real_imp = impedance_info.get('real', 0.0) / 1000.0  # μΩ转换为mΩ
                                    imag_imp = impedance_info.get('imag', 0.0) / 1000.0  # μΩ转换为mΩ

                                    # 计算阻抗模值
                                    magnitude = math.sqrt(real_imp**2 + imag_imp**2)

                                    # 修复相位角计算 - 不再对虚部取反，因为设备数据已经是正确符号
                                    phase = math.degrees(math.atan2(imag_imp, real_imp)) if real_imp != 0 else 0.0

                                    frequency_data.append({
                                        'frequency': freq,
                                        'impedance_real': real_imp,
                                        'impedance_imag': imag_imp,
                                        'impedance_magnitude': magnitude,
                                        'impedance_phase': phase
                                    })

                            logger.debug(f"通道{channel_num}获取到{len(frequency_data)}个频点的阻抗数据")
                        else:
                            logger.debug(f"通道{channel_num}没有阻抗数据")
                except Exception as e:
                    logger.debug(f"获取通道{channel_num}频点数据失败: {e}")

                # 构建结果数据（包含EIS频点数据）
                result = {
                    'channel': channel_num,
                    'voltage': round(voltage, 3),
                    'rs_value': round(rs_value, 3),
                    'rct_value': round(rct_value, 3),
                    'rs_grade': rs_grade,
                    'rct_grade': rct_grade,
                    'is_pass': is_pass,
                    'fail_items': fail_items,
                    'frequency_data': frequency_data,  # 新增EIS频点数据
                    'timestamp': datetime.now().isoformat()  # 添加时间戳
                }

                results.append(result)
                logger.debug(f"获取通道{channel_num}最新测试结果: Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ")

            logger.info(f"获取最新测试结果完成: {len(results)} 个通道")
            return results

        except Exception as e:
            logger.error(f"获取最新测试结果失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return []

    def save_test_result(self, channel_num: int, result_data: Dict[str, Any], test_config: Dict[str, Any]):
        """
        保存测试结果到数据库

        Args:
            channel_num: 通道号（1-8）
            result_data: 测试结果数据
            test_config: 测试配置
        """
        try:
            # Jack要求检查测试是否被停止，如果停止则不保存数据库
            # 🔧 [单频点修复] 但是单频点测试完成后需要保存数据，即使stop_event被设置
            if hasattr(self, 'test_executor') and self.test_executor and hasattr(self.test_executor, 'stop_event'):
                if self.test_executor.stop_event.is_set():
                    # 检查是否为单频点测试
                    is_single_freq_test = False
                    if test_config and 'frequencies' in test_config:
                        frequencies = test_config.get('frequencies', [])
                        is_single_freq_test = len(frequencies) == 1

                    if is_single_freq_test:
                        logger.info(f"🔧 [单频点测试] 测试停止但允许单频点数据保存: 通道{channel_num}")
                    else:
                        logger.warning(f"🛑 通道{channel_num}测试已被停止，跳过数据库保存，避免保存脏数据")
                        return

            # 修复检查是否为连续测试模式（优先从配置管理器读取，确保准确性）
            continuous_mode = test_config.get('continuous_mode', False)
            if not continuous_mode:
                # 如果test_config中没有continuous_mode，从配置管理器中读取
                continuous_mode = self.config_manager.get('test.continuous_mode', False)
                logger.debug(f"从配置管理器读取连续测试模式状态: {continuous_mode}")

            cycle_count = getattr(self, 'continuous_test_count', 0) if hasattr(self, 'continuous_test_count') else 0

            if continuous_mode:
                logger.info(f"🔄 连续测试模式：开始保存通道{channel_num}第{cycle_count}轮测试结果到数据库...")
            else:
                logger.info(f"开始保存通道{channel_num}测试结果到数据库...")

            if not self.db_manager:
                logger.error("数据库管理器未初始化，尝试重新初始化...")
                # 尝试重新初始化数据库管理器
                try:
                    from data.database_manager import DatabaseManager
                    self._db_manager = DatabaseManager()
                    logger.info("数据库管理器重新初始化成功")
                except Exception as e:
                    logger.error(f"重新初始化数据库管理器失败: {e}")
                    return

            if not self.db_manager:
                logger.error("数据库管理器仍然未初始化，无法保存测试结果")
                return

            logger.info(f"数据库管理器状态正常，开始保存通道{channel_num}数据...")

            # 修复确保frequency_data变量在方法开始时就被定义
            frequency_data = result_data.get('frequency_data', [])
            logger.debug(f"通道{channel_num}获取到频率数据: {len(frequency_data)}个频点")

            # 修复确保连续测试模式下批次ID的持续性
            current_batch_id = self.current_batch_id
            if current_batch_id is None:
                current_batch_id = self._ensure_batch_exists()
                self.current_batch_id = current_batch_id
                if continuous_mode:
                    logger.info(f"🔄 连续测试模式：创建新批次ID: {current_batch_id}")
            elif continuous_mode:
                logger.debug(f"🔄 连续测试模式：使用现有批次ID: {current_batch_id}")

            # 新增连续测试模式下为电池码添加测试序号，确保每次测试都能保存
            original_battery_code = self._get_current_battery_code(channel_num)
            logger.debug(f" 获取到原始电池码: {original_battery_code}")

            if continuous_mode:
                # 获取同一电池码的测试次数
                test_sequence = self._get_battery_test_sequence(original_battery_code, channel_num)
                enhanced_battery_code = f"{original_battery_code}-T{test_sequence:03d}"
                logger.info(f"🔄 连续测试模式：通道{channel_num}电池码增强为: {enhanced_battery_code} (第{test_sequence}次测试)")

                # 新增设置阻抗数据管理器的增强电池码，确保明细数据使用正确的电池码
                if self.impedance_data_manager:
                    self.impedance_data_manager.set_enhanced_battery_code(channel_num, enhanced_battery_code)
                    logger.debug(f" 已设置通道{channel_num}增强电池码到阻抗数据管理器: {enhanced_battery_code}")
            else:
                enhanced_battery_code = original_battery_code
                logger.debug(f" 单次测试模式：使用原始电池码: {enhanced_battery_code}")

                # 单次测试模式下清空增强电池码
                if self.impedance_data_manager:
                    self.impedance_data_manager.clear_enhanced_battery_codes()

            # 计算测试时间
            start_time = self.test_start_times.get(channel_num, time.time())
            end_time = self.test_end_times.get(channel_num, time.time())
            test_duration = end_time - start_time

            # 转换为ISO格式时间字符串
            start_time_iso = datetime.fromtimestamp(start_time).isoformat()
            end_time_iso = datetime.fromtimestamp(end_time).isoformat()

            # 修复使用增强的电池码（连续测试模式下包含序号）
            battery_code = enhanced_battery_code

            # 🔧 修复：生成详细失败原因，添加异常处理和调试日志
            try:
                detailed_fail_reason = self.failure_reason_manager.generate_detailed_failure_reason(
                    result_data['voltage'],
                    result_data['rs_value'],
                    result_data['rct_value'],
                    result_data.get('outlier_result')
                )
                logger.debug(f"🔧 [失败原因] 通道{channel_num}详细失败原因生成成功: {detailed_fail_reason}")
            except Exception as e:
                logger.error(f"生成详细失败原因失败: {e}")
                # 🔧 修复：当失败原因生成异常时，使用简化的失败原因
                fail_items = result_data.get('fail_items', [])
                is_pass = result_data.get('is_pass', True)
                if not is_pass and fail_items:
                    if len(fail_items) == 1:
                        detailed_fail_reason = f"不合格-{fail_items[0]}"
                    else:
                        detailed_fail_reason = f"不合格-{'/'.join(fail_items[:2])}"
                else:
                    detailed_fail_reason = "不合格" if not is_pass else ""
                logger.debug(f"🔧 [失败原因] 通道{channel_num}使用简化失败原因: {detailed_fail_reason}")

            # 获取测试模式信息
            test_mode_description = self.test_mode_manager.get_mode_description_for_database()

            # 获取产品信息
            product_info = self.product_info_manager.get_complete_product_info()

            # 计算Rct变异系数（连续测试模式下基于历史数据）
            rct_coefficient_of_variation = 0.0

            # 检查是否为连续测试模式
            test_mode = test_config.get('test_mode', '')
            continuous_mode = test_config.get('continuous_mode', False)

            if continuous_mode:
                # 连续测试模式：获取同一电池的历史Rct值（使用原始电池码）
                historical_rct_values = self._get_historical_rct_values(original_battery_code, channel_num)

                # 添加当前Rct值
                current_rct = result_data['rct_value']
                if current_rct > 0:
                    historical_rct_values.append(current_rct)

                # 计算变异系数（需要至少2个值）
                if len(historical_rct_values) >= 2:
                    rct_coefficient_of_variation = self.test_parameter_calculator.calculate_rct_coefficient_of_variation(historical_rct_values)
                    logger.info(f"通道{channel_num}连续测试Rct变异系数: {rct_coefficient_of_variation:.2f}% (基于{len(historical_rct_values)}个值)")
                else:
                    logger.debug(f"通道{channel_num}Rct值数量不足({len(historical_rct_values)})，无法计算变异系数")
            else:
                # 单次测试模式：从频率数据中提取多个Rct相关值
                # frequency_data 已在前面定义，这里不需要重新定义
                if frequency_data:
                    # 从不同频率点提取阻抗值作为Rct变化的参考
                    rct_values = [result_data['rct_value']]  # 基础值
                    # 可以根据需要添加更多频率相关的阻抗值
                    rct_coefficient_of_variation = self.test_parameter_calculator.calculate_rct_coefficient_of_variation(rct_values)

            # 计算容量预测（仅在启用时）
            capacity_prediction = 0.0  # 默认值
            if self.config_manager.get('test.capacity_prediction_enabled', False):
                capacity_prediction = self.test_parameter_calculator.calculate_capacity_prediction(
                    result_data['voltage'],
                    result_data['rs_value'],
                    result_data['rct_value']
                )
                logger.debug(f"通道{channel_num}容量预测已启用，计算结果: {capacity_prediction:.3f}AH")
            else:
                logger.debug(f"通道{channel_num}容量预测功能已禁用，跳过计算")

            # 🎯 处理取样测试模式的is_pass字段
            is_pass_value = result_data['is_pass']
            sampling_test = self.config_manager.get('test.sampling_test', False)
            if sampling_test and is_pass_value is None:
                # 取样测试模式下，is_pass不能为None，设置为False（表示未判断）
                is_pass_value = False
                logger.info(f"🎯 通道{channel_num}取样测试模式：is_pass设置为False（未判断）")

            # 获取测试时的实际判断条件（作为历史记录保存，不随配置变化）
            test_time_conditions = self._get_test_time_conditions()

            # 准备测试结果记录
            test_result = {
                'batch_id': current_batch_id,
                'channel_number': channel_num,
                'battery_code': battery_code,  # 使用实际的电池码
                'test_start_time': start_time_iso,
                'test_end_time': end_time_iso,
                'test_duration': test_duration,  # 测试持续时间（秒）
                'voltage': result_data['voltage'],
                'voltage_source': result_data.get('voltage_source', 'unknown'),  # 记录电压来源
                'rs_value': result_data['rs_value'],
                'rct_value': result_data['rct_value'],
                'w_impedance': result_data.get('w_impedance'),  # W阻抗（如果有的话）
                'rs_grade': result_data['rs_grade'],
                'rct_grade': result_data['rct_grade'],
                'is_pass': is_pass_value,  # 🎯 使用处理后的is_pass值
                'fail_reason': detailed_fail_reason,  # 使用详细的失败原因
                'test_mode': test_mode_description,  # 使用详细的测试模式描述
                'frequency_list': test_config.get('frequencies', []),  # 当前测试的频率列表
                'raw_data': {
                    'impedance_data': self._format_impedance_data_for_storage(channel_num),
                    'test_config': test_config
                },
                # 新增字段
                'operator': product_info['operator'],  # 操作员信息
                'battery_type': product_info['battery_type'],  # 电池类型
                'battery_spec': product_info['battery_spec'],  # 电池规格
                'batch_number': product_info.get('batch_number', self.batch_info.get('batch_number', 'AUTO_BATCH')),  # 修复优先使用产品信息中的批次号
                'rct_coefficient_of_variation': rct_coefficient_of_variation,  # Rct变异系数
                'capacity_prediction': capacity_prediction,  # 容量预测
                # 离群率相关字段（如果有）
                'outlier_result': result_data.get('outlier_result'),
                'baseline_filename': result_data.get('baseline_filename'),
                'baseline_id': result_data.get('baseline_id'),
                'max_deviation_percent': result_data.get('max_deviation_percent'),
                'frequency_deviations': result_data.get('frequency_deviations', {}),
                # 频率数据
                'frequency_data': frequency_data,
                # 🔧 测试时的实际判断条件（历史记录，不随配置变化）
                'voltage_range_min': test_time_conditions['voltage_min'],
                'voltage_range_max': test_time_conditions['voltage_max'],
                'rs_range_min': test_time_conditions['rs_min'],
                'rs_range_max': test_time_conditions['rs_max'],
                'rct_range_min': test_time_conditions['rct_min'],
                'rct_range_max': test_time_conditions['rct_max']
            }

            # 🔋 修复：只有在真正计算出Rsei值时才保存（不保存虚假的0值）
            basic_rsei_value = result_data.get('rsei_value', 0.0)
            if basic_rsei_value >= 0.001:  # 修复放宽阈值，适应低内阻电池
                test_result['rsei_value'] = basic_rsei_value
                logger.debug(f"通道{channel_num}有效Rsei值: {basic_rsei_value:.3f}mΩ")
            else:
                test_result['rsei_value'] = None  # 保存NULL而不是0
                basic_rsei_value = 0.0  # 用于阻抗比计算
                logger.debug(f"通道{channel_num}Rsei值无效({basic_rsei_value:.3f}mΩ)，保存为NULL")

            # 新增计算基本阻抗比 Rp/Rs，其中 Rp = Rsei + Rct
            basic_rs = result_data.get('rs_value', 0.0)
            basic_rct = result_data.get('rct_value', 0.0)

            logger.debug(f"通道{channel_num}阻抗比计算输入: Rs={basic_rs:.3f}mΩ, Rct={basic_rct:.3f}mΩ, Rsei={basic_rsei_value:.3f}mΩ")

            # 修复如果Rs或Rct值无效，尝试重新计算
            # 🔧 [单频点修复] 单频点测试时Rct=0是正常的，不应重新计算
            is_single_freq_test = (basic_rct == 0.0 and basic_rs > 0)
            if (basic_rs <= 0 or basic_rct < 0) and not is_single_freq_test:
                logger.warning(f"通道{channel_num}检测到无效的Rs或Rct值，尝试重新计算: Rs={basic_rs:.3f}mΩ, Rct={basic_rct:.3f}mΩ")
                try:
                    # 尝试重新计算Rs和Rct值
                    recalc_rs, recalc_rct = self.calculate_rs_rct_for_channel(channel_num)
                    if recalc_rs > 0 and recalc_rct > 0:
                        basic_rs = recalc_rs
                        basic_rct = recalc_rct
                        logger.info(f"通道{channel_num}重新计算成功: Rs={basic_rs:.3f}mΩ, Rct={basic_rct:.3f}mΩ")
                        # 同时更新test_result中的值
                        test_result['rs_value'] = basic_rs
                        test_result['rct_value'] = basic_rct
                    else:
                        logger.warning(f"通道{channel_num}重新计算仍然无效，阻抗比设为0")
                        basic_impedance_ratio = 0.0
                        test_result['impedance_ratio'] = basic_impedance_ratio
                        return  # 提前返回，不继续计算
                except Exception as e:
                    logger.error(f"通道{channel_num}重新计算Rs/Rct失败: {e}")
                    basic_impedance_ratio = 0.0
                    test_result['impedance_ratio'] = basic_impedance_ratio
                    return  # 提前返回，不继续计算

            # 计算阻抗比
            basic_rp = basic_rsei_value + basic_rct  # 极化电阻
            basic_impedance_ratio = basic_rp / basic_rs
            test_result['impedance_ratio'] = basic_impedance_ratio
            logger.info(f"通道{channel_num}基本阻抗比计算: Rp({basic_rp:.3f})/Rs({basic_rs:.3f}) = {basic_impedance_ratio:.3f}")

            # 🔋 添加增强版EIS分析结果（如果有的话）
            enhanced_analysis = result_data.get('enhanced_analysis')
            if enhanced_analysis and enhanced_analysis.get('analysis_success'):
                logger.info(f"通道{channel_num}检测到增强版EIS分析结果，添加到数据库记录")

                # 检查增强版Rsei值是否有效
                enhanced_rsei = enhanced_analysis.get('rsei_value', 0.0)
                if enhanced_rsei >= 0.001:  # 修复放宽阈值，适应低内阻电池
                    test_result['rsei_value'] = enhanced_rsei
                    logger.info(f"通道{channel_num}使用增强版Rsei值: {enhanced_rsei:.3f}mΩ")

                # 更新支持完整版EIS算法的所有参数
                # 新增计算阻抗比 Rp/Rs，其中 Rp = Rsei + Rct
                enhanced_rs = enhanced_analysis.get('rs_value', result_data.get('rs_value', 0.0))
                enhanced_rct = enhanced_analysis.get('rct_value', result_data.get('rct_value', 0.0))
                enhanced_rsei = enhanced_analysis.get('rsei_value', 0.0)

                logger.info(f"通道{channel_num}增强版阻抗比计算输入: Rs={enhanced_rs:.3f}mΩ, Rct={enhanced_rct:.3f}mΩ, Rsei={enhanced_rsei:.3f}mΩ")

                if enhanced_rs <= 0:
                    logger.warning(f"通道{channel_num}增强版Rs值无效，阻抗比设为0: Rs={enhanced_rs:.3f}mΩ")
                    impedance_ratio = 0.0
                else:
                    rp_value = enhanced_rsei + enhanced_rct  # 极化电阻
                    impedance_ratio = rp_value / enhanced_rs
                    logger.info(f"通道{channel_num}增强版阻抗比计算: Rp({rp_value:.3f})/Rs({enhanced_rs:.3f}) = {impedance_ratio:.3f}")

                test_result.update({
                    # 新增阻抗比
                    'impedance_ratio': impedance_ratio,

                    # Warburg扩散参数
                    'warburg_coefficient': enhanced_analysis.get('warburg_coefficient'),
                    'warburg_01hz': enhanced_analysis.get('warburg_01hz'),
                    'warburg_001hz': enhanced_analysis.get('warburg_001hz'),
                    'has_warburg_diffusion': enhanced_analysis.get('has_warburg_diffusion'),
                    'diffusion_time_constant': enhanced_analysis.get('diffusion_time_constant_s'),

                    # SEI膜参数
                    'has_sei': enhanced_analysis.get('has_sei'),
                    'sei_confidence': enhanced_analysis.get('sei_confidence'),

                    # 电容参数（完整版EIS算法新增）
                    'double_layer_capacitance': enhanced_analysis.get('double_layer_capacitance_mf'),
                    'sei_capacitance': enhanced_analysis.get('sei_capacitance_mf'),
                    'total_capacitance': enhanced_analysis.get('total_capacitance_mf'),

                    # 时间常数参数（完整版EIS算法新增）
                    'characteristic_frequency': enhanced_analysis.get('characteristic_frequency'),
                    'main_time_constant': enhanced_analysis.get('tau_main_ms'),
                    'sei_time_constant': enhanced_analysis.get('tau_sei_ms'),

                    # 相位角参数
                    'phase_angle_range': enhanced_analysis.get('phase_angle_range'),
                    'max_phase_angle': enhanced_analysis.get('max_phase_angle'),
                    'min_phase_angle': enhanced_analysis.get('min_phase_angle'),

                    # 贡献比例参数（完整版EIS算法新增）
                    'rs_contribution': enhanced_analysis.get('rs_contribution_percent'),
                    'sei_contribution': enhanced_analysis.get('rsei_contribution_percent'),
                    'ct_contribution': enhanced_analysis.get('rct_contribution_percent'),
                    'polarization_contribution': enhanced_analysis.get('polarization_contribution'),

                    # 健康状态参数（完整版EIS算法新增）
                    'health_status': enhanced_analysis.get('health_status'),
                    'health_score': enhanced_analysis.get('health_score'),
                    'health_level': enhanced_analysis.get('health_level'),
                    'performance_grade': enhanced_analysis.get('performance_grade'),

                    # 分析方法标识
                    'analysis_method': enhanced_analysis.get('analysis_method')
                })
                logger.info(f"通道{channel_num}增强版EIS参数: "
                           f"Rsei={enhanced_analysis.get('rsei_value', 0):.3f}mΩ, "
                           f"阻抗比={impedance_ratio:.3f}, "
                           f"W={enhanced_analysis.get('warburg_coefficient', 0):.3f}mΩ·s^(-0.5), "
                           f"健康状态={enhanced_analysis.get('health_status', '未知')}")
            else:
                logger.debug(f"通道{channel_num}未检测到增强版EIS分析结果，使用默认值")

            logger.info(f"通道{channel_num}测试时长: {test_duration:.1f}秒 ({start_time_iso} - {end_time_iso})")

            # 记录详细的保存信息
            logger.info(f"通道{channel_num}详细信息: 测试模式={test_mode_description}, "
                       f"操作员={product_info['operator']}, 电池类型={product_info['battery_type']}, "
                       f"电池规格={product_info['battery_spec']}")

            if detailed_fail_reason:
                logger.info(f"通道{channel_num}失败原因: {detailed_fail_reason}")

            # 根据容量预测启用状态显示不同的日志信息
            if self.config_manager.get('test.capacity_prediction_enabled', False):
                logger.info(f"通道{channel_num}计算参数: Rct变异系数={rct_coefficient_of_variation:.2f}%, "
                           f"容量预测={capacity_prediction:.3f}AH")
            else:
                logger.info(f"通道{channel_num}计算参数: Rct变异系数={rct_coefficient_of_variation:.2f}%")

            logger.info(f"准备保存通道{channel_num}测试结果到数据库...")
            logger.debug(f"数据库管理器状态: {self.db_manager is not None}")
            logger.debug(f"测试结果数据: {test_result}")

            try:
                from debug_data_consistency_checker import data_consistency_checker

                # 性能优化：仅在调试开关开启时捕获一致性数据
                if self.config_manager.get('debug.data_consistency.enabled', False):
                    db_debug_data = {
                        'voltage': test_result.get('voltage', 0.0),
                        'rs_value': test_result.get('rs_value', 0.0),
                        'rct_value': test_result.get('rct_value', 0.0),
                        'rsei_value': test_result.get('rsei_value', 0.0),
                        'algorithm_used': 'enhanced' if self._is_using_enhanced_algorithm() else 'standard',
                        'unit_converted': True,
                        'voltage_source': 'pre_test' if test_result.get('voltage_source') == 'pre_test' else 'current'
                    }
                    data_consistency_checker.capture_db_data(channel_num, db_debug_data)

                    logger.info(f"   电压: {test_result.get('voltage', 0.0):.3f}V (来源: {db_debug_data['voltage_source']})")
                    logger.info(f"   Rs: {test_result.get('rs_value', 0.0):.3f}mΩ")
                    logger.info(f"   Rct: {test_result.get('rct_value', 0.0):.3f}mΩ")
                    logger.info(f"   算法: {db_debug_data['algorithm_used']}")
                    logger.info(f"   单位转换: {db_debug_data['unit_converted']}")

            except ImportError:
                # 调试模块不存在时，只输出基本信息
                algorithm_used = 'enhanced' if self._is_using_enhanced_algorithm() else 'standard'
                voltage_source = 'pre_test' if test_result.get('voltage_source') == 'pre_test' else 'current'

                logger.info(f"   电压: {test_result.get('voltage', 0.0):.3f}V (来源: {voltage_source})")
                logger.info(f"   Rs: {test_result.get('rs_value', 0.0):.3f}mΩ")
                logger.info(f"   Rct: {test_result.get('rct_value', 0.0):.3f}mΩ")
                logger.info(f"   算法: {algorithm_used}")
            except Exception as debug_e:
                logger.debug(f"数据一致性调试失败: {debug_e}")

            # 修复增加数据库保存重试机制（特别是连续测试模式）
            max_retries = 3 if continuous_mode else 1
            result_id = None

            logger.debug(f" 准备保存测试结果到数据库，重试次数: {max_retries}")
            logger.debug(f" 测试结果数据摘要: 电池码={test_result.get('battery_code', 'UNKNOWN')}, Rs={test_result.get('rs_value', 0):.3f}mΩ, Rct={test_result.get('rct_value', 0):.3f}mΩ")

            for attempt in range(max_retries):
                try:
                    logger.debug(f" 第{attempt + 1}次尝试保存数据到数据库...")
                    result_id = self.db_manager.save_test_result(test_result)
                    logger.debug(f" 数据库保存返回结果ID: {result_id}")

                    if result_id:
                        logger.info(f"✅ 第{attempt + 1}次保存成功，结果ID: {result_id}")
                        break  # 保存成功，退出重试循环
                    else:
                        if continuous_mode and attempt < max_retries - 1:
                            logger.warning(f"🔄 连续测试模式：通道{channel_num}第{attempt + 1}次保存失败，准备重试...")
                            time.sleep(0.1)  # 短暂等待后重试
                        else:
                            logger.error(f"❌ 通道{channel_num}测试结果保存失败: 数据库返回空结果ID")
                except Exception as save_e:
                    logger.error(f"❌ 第{attempt + 1}次保存异常: {save_e}")
                    import traceback
                    logger.error(f"❌ 保存异常详情: {traceback.format_exc()}")

                    if continuous_mode and attempt < max_retries - 1:
                        logger.warning(f"🔄 连续测试模式：通道{channel_num}第{attempt + 1}次保存异常，准备重试: {save_e}")
                        time.sleep(0.1)  # 短暂等待后重试
                    else:
                        logger.error(f"❌ 通道{channel_num}测试结果保存异常: {save_e}")
                        raise

            if result_id:
                if continuous_mode:
                    logger.info(f"✅ 连续测试模式：通道{channel_num}第{cycle_count}轮测试结果已保存到数据库: ID={result_id}")
                    logger.info(f"📊 连续测试数据：电池码={battery_code}, Rs={result_data['rs_value']:.3f}mΩ, Rct={result_data['rct_value']:.3f}mΩ")

                    # 新增验证明细数据是否正确保存和查询
                    try:
                        # 性能优化：仅在调试开关开启时验证明细数据
                        if self.config_manager.get('debug.data_consistency.enabled', False):
                            impedance_details = self.db_manager.get_impedance_details(
                                batch_id=current_batch_id,
                                channel_number=channel_num,
                                battery_code=battery_code
                            )
                            logger.debug(f" 连续测试明细数据验证：电池码={battery_code}, 明细记录数={len(impedance_details)}")
                            if len(impedance_details) == 0:
                                # 尝试用原始电池码查询
                                original_battery_code = battery_code.rsplit('-T', 1)[0] if '-T' in battery_code else battery_code
                                impedance_details_original = self.db_manager.get_impedance_details(
                                    batch_id=current_batch_id,
                                    channel_number=channel_num,
                                    battery_code=original_battery_code
                                )
                                logger.debug(f" 用原始电池码查询明细数据：原始码={original_battery_code}, 明细记录数={len(impedance_details_original)}")
                    except Exception as detail_e:
                        logger.error(f"❌ 验证明细数据失败: {detail_e}")
                else:
                    logger.info(f"✅ 通道{channel_num}测试结果已保存到数据库: ID={result_id}")

                # Jack要求：数据库保存成功后，直接传递测试结果给UI界面显示
                self._trigger_direct_ui_result_display(channel_num, test_result)

                # 🔥 新增：测试结果保存成功后，直接触发自动打印
                self._trigger_auto_print(test_result, channel_num, result_id)

                # 新增测试结果保存成功后，触发数据上传
                self._trigger_data_upload(test_result, channel_num)

            else:
                if continuous_mode:
                    logger.error(f"❌ 连续测试模式：通道{channel_num}第{cycle_count}轮测试结果保存失败: 数据库返回空结果ID")
                else:
                    logger.error(f"❌ 通道{channel_num}测试结果保存失败: 数据库返回空结果ID")
                logger.error(f"测试结果数据: {test_result}")
                # 尝试检查数据库连接状态
                try:
                    db_info = self.db_manager.get_database_info()
                    logger.error(f"数据库信息: {db_info}")
                except Exception as db_e:
                    logger.error(f"获取数据库信息失败: {db_e}")

            # 在连续测试模式下保存容量预测数据
            if continuous_mode and rct_coefficient_of_variation > 0:
                self._save_capacity_prediction_data_if_enabled(
                    channel_num, test_result, rct_coefficient_of_variation
                )

        except Exception as e:
            logger.error(f"保存通道{channel_num}测试结果失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

    def _trigger_ui_refresh(self, channel_num: int, test_result: Dict[str, Any]):
        """
        触发UI刷新，确保显示的档位与数据库一致

        Args:
            channel_num: 通道号
            test_result: 测试结果数据
        """
        try:
            logger.debug(f"🔄 [UI刷新] 通道{channel_num} 开始刷新UI显示...")

            # 获取主窗口引用
            main_window = None
            if hasattr(self, 'test_executor') and self.test_executor:
                if hasattr(self.test_executor, 'main_window') and self.test_executor.main_window:
                    main_window = self.test_executor.main_window
                    logger.debug(f"✅ [UI刷新] 通道{channel_num} 通过测试执行器获取到主窗口")

            if not main_window:
                # 尝试通过全局方式获取主窗口
                try:
                    from PyQt5.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app:
                        for widget in app.topLevelWidgets():
                            if hasattr(widget, 'ui_component_manager'):
                                main_window = widget
                                logger.debug(f"✅ [UI刷新] 通道{channel_num} 通过全局搜索获取到主窗口")
                                break
                except Exception as e:
                    logger.debug(f"全局搜索主窗口失败: {e}")

            if not main_window:
                logger.warning(f"⚠️ [UI刷新] 通道{channel_num} 无法获取主窗口引用，跳过UI刷新")
                return

            # 获取通道容器并刷新指定通道
            ui_manager = getattr(main_window, 'ui_component_manager', None)
            if ui_manager:
                channels_container = ui_manager.get_component('channels_container')
                if channels_container and hasattr(channels_container, 'refresh_channel_from_database'):
                    # 使用QTimer确保在主线程中执行UI更新
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(100, lambda: channels_container.refresh_channel_from_database(channel_num))
                    logger.info(f"✅ [UI刷新] 通道{channel_num} UI刷新已触发")
                else:
                    logger.warning(f"⚠️ [UI刷新] 通道{channel_num} 通道容器组件未找到或不支持刷新")
            else:
                logger.warning(f"⚠️ [UI刷新] 通道{channel_num} UI组件管理器未找到")

        except Exception as e:
            logger.error(f"❌ [UI刷新] 通道{channel_num} 触发UI刷新失败: {e}")

    def _trigger_direct_ui_result_display(self, channel_num: int, test_result: Dict[str, Any]):
        """
        Jack要求：数据库保存成功后，直接传递测试结果给UI界面显示，不再进行多次判断

        Args:
            channel_num: 通道号
            test_result: 测试结果数据（包含is_pass和fail_reason）
        """
        try:
            logger.info(f"🎯 [直接UI显示] 通道{channel_num} 开始直接传递测试结果给UI...")

            # 从测试结果中提取关键信息
            is_pass = test_result.get('is_pass', False)
            fail_reason = test_result.get('fail_reason', '')
            voltage = test_result.get('voltage', 0.0)
            rs_value = test_result.get('rs_value', 0.0)
            rct_value = test_result.get('rct_value', 0.0)
            rs_grade = test_result.get('rs_grade', '')
            rct_grade = test_result.get('rct_grade', '')

            logger.info(f"🎯 [直接UI显示] 通道{channel_num} 测试结果: {'合格' if is_pass else '不合格'}, 失败原因: {fail_reason}")

            # 获取主窗口引用
            main_window = None
            if hasattr(self, 'test_executor') and self.test_executor:
                if hasattr(self.test_executor, 'main_window') and self.test_executor.main_window:
                    main_window = self.test_executor.main_window
                    logger.debug(f"✅ [直接UI显示] 通道{channel_num} 通过测试执行器获取到主窗口")

            if not main_window:
                # 尝试通过全局方式获取主窗口
                try:
                    from PyQt5.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app:
                        for widget in app.topLevelWidgets():
                            if hasattr(widget, 'ui_component_manager'):
                                main_window = widget
                                logger.debug(f"✅ [直接UI显示] 通道{channel_num} 通过全局搜索获取到主窗口")
                                break
                except Exception as e:
                    logger.debug(f"全局搜索主窗口失败: {e}")

            if not main_window:
                logger.warning(f"⚠️ [直接UI显示] 通道{channel_num} 无法获取主窗口引用，跳过UI显示")
                return

            # 获取通道容器并直接设置测试结果
            ui_manager = getattr(main_window, 'ui_component_manager', None)
            if ui_manager:
                channels_container = ui_manager.get_component('channels_container')
                if channels_container:
                    # 获取通道组件
                    channel_widget = None
                    if hasattr(channels_container, '_get_channel_widget'):
                        channel_widget = channels_container._get_channel_widget(channel_num)

                    if channel_widget and hasattr(channel_widget, 'set_test_completed'):
                        # 使用QTimer确保在主线程中执行UI更新
                        from PyQt5.QtCore import QTimer

                        def update_ui():
                            try:
                                # 直接设置测试完成状态，不再进行任何判断
                                channel_widget.set_test_completed(is_pass, rs_grade, rct_grade, [fail_reason] if fail_reason else [])
                                logger.info(f"✅ [直接UI显示] 通道{channel_num} 测试结果已直接设置到UI")
                            except Exception as e:
                                logger.error(f"❌ [直接UI显示] 通道{channel_num} UI更新失败: {e}")

                        QTimer.singleShot(50, update_ui)
                    else:
                        logger.debug(f"⚠️ [直接UI显示] 通道{channel_num} 通道组件未找到或不支持直接设置结果")
                else:
                    logger.debug(f"⚠️ [直接UI显示] 通道{channel_num} 通道容器组件未找到")
            else:
                logger.debug(f"⚠️ [直接UI显示] 通道{channel_num} UI组件管理器未找到")

        except Exception as e:
            logger.error(f"❌ [直接UI显示] 通道{channel_num} 直接传递测试结果失败: {e}")

    def _trigger_auto_print(self, test_result: Dict[str, Any], channel_num: int, result_id: int):
        """
        触发自动打印 - 直接实现版本

        Args:
            test_result: 测试结果数据
            channel_num: 通道号
            result_id: 数据库结果ID
        """
        try:
            # Jack要求检查测试是否被停止，如果停止则不打印
            if hasattr(self, 'test_executor') and self.test_executor and hasattr(self.test_executor, 'stop_event'):
                if self.test_executor.stop_event.is_set():
                    logger.warning(f"🛑 [直接打印] 通道{channel_num}测试已被停止，跳过自动打印")
                    return


            # 直接通过测试执行器获取主窗口引用
            main_window = None
            if hasattr(self, 'test_executor') and self.test_executor:
                if hasattr(self.test_executor, 'main_window') and self.test_executor.main_window:
                    main_window = self.test_executor.main_window
                    logger.debug(f"🔥 [直接打印] 通道{channel_num}通过测试执行器获取到主窗口引用")
                else:
                    logger.debug(f"🔥 [直接打印] 通道{channel_num}测试执行器中没有主窗口引用")

            # 如果还没有主窗口引用，尝试其他方式
            if not main_window:
                if hasattr(self, 'main_window') and self.main_window:
                    main_window = self.main_window
                    logger.debug(f"🔥 [直接打印] 通道{channel_num}通过self.main_window获取到主窗口引用")
                else:
                    # 尝试通过全局方式获取主窗口（最后的备用方案）
                    try:
                        from PyQt5.QtWidgets import QApplication
                        app = QApplication.instance()
                        if app:
                            for widget in app.topLevelWidgets():
                                if hasattr(widget, 'auto_print_manager') and hasattr(widget, 'label_print_manager'):
                                    main_window = widget
                                    logger.debug(f"🔥 [直接打印] 通道{channel_num}通过全局搜索获取到主窗口引用")
                                    break
                    except Exception as e:
                        logger.debug(f"全局搜索主窗口失败: {e}")

                    if not main_window:
                        logger.warning(f"🔥 [直接打印] 通道{channel_num}无法获取主窗口引用，跳过自动打印")
                        return

            # 🔥 直接实现打印逻辑，不依赖自动打印管理器

            # 检查是否启用自动打印
            if not hasattr(main_window, 'label_print_manager') or not main_window.label_print_manager:
                logger.warning(f"🔥 [直接打印] 通道{channel_num}标签打印管理器未找到，跳过打印")
                return

            # 检查是否启用自动打印
            if not main_window.label_print_manager.is_auto_print_enabled():
                return

            # 检查打印机是否就绪
            if not main_window.label_print_manager.is_printer_ready():
                logger.warning(f"🔥 [直接打印] 通道{channel_num}打印机未就绪，跳过打印")
                return

            # 检查取样测试模式
            if hasattr(main_window, 'config_manager') and main_window.config_manager:
                sampling_test = main_window.config_manager.get('test.sampling_test', False)
                if sampling_test:
                    return

            # 准备打印数据
            print_data = {
                'channel_number': channel_num,
                'rs_value': test_result.get('rs_value', 0),
                'rct_value': test_result.get('rct_value', 0),
                'rsei_value': test_result.get('rsei_value', 0),
                'voltage': test_result.get('voltage', 0),
                'rs_grade': test_result.get('rs_grade', 0),
                'rct_grade': test_result.get('rct_grade', 0),
                'is_pass': test_result.get('is_pass', False),
                'fail_reason': test_result.get('fail_reason', ''),
                'battery_code': test_result.get('battery_code', ''),
                'test_time': test_result.get('test_start_time', ''),
                'impedance_ratio': test_result.get('impedance_ratio', 0),
            }

            # 检查数据有效性
            rs_value = print_data.get('rs_value', 0)
            rct_value = print_data.get('rct_value', 0)
            if rs_value == 0 and rct_value == 0:
                logger.warning(f"🔥 [直接打印] 通道{channel_num}测试数据异常: Rs={rs_value}, Rct={rct_value}")
                return

            # 执行打印
            job_id = main_window.label_print_manager.print_test_result(print_data)

            if job_id:
                logger.info(f"✅ [直接打印] 通道{channel_num}打印任务已提交，任务ID: {job_id}")
            else:
                logger.error(f"❌ [直接打印] 通道{channel_num}打印失败")

        except Exception as e:
            logger.error(f"触发通道{channel_num}直接打印失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

    def _trigger_data_upload(self, test_result: Dict[str, Any], channel_num: int):
        """
        触发数据上传

        Args:
            test_result: 测试结果数据
            channel_num: 通道号
        """
        try:
            has_attr = hasattr(self, 'data_upload_manager')
            manager_exists = self.data_upload_manager if has_attr else None


            if not has_attr or not self.data_upload_manager:
                logger.warning(f"⚠️ 通道{channel_num}数据上传管理器未初始化，跳过数据上传")
                logger.warning(f"   hasattr(data_upload_manager): {has_attr}")
                logger.warning(f"   self.data_upload_manager: {getattr(self, 'data_upload_manager', 'NOT_SET')}")
                return

            # 格式化上传数据
            # 处理时间戳：将ISO字符串转换为datetime对象
            test_start_time = test_result.get('test_start_time')
            if isinstance(test_start_time, str):
                try:
                    timestamp = datetime.fromisoformat(test_start_time)
                except (ValueError, AttributeError):
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()

            # 新增获取完整的产品信息
            product_info = self.product_info_manager.get_complete_product_info()

            upload_test_result = {
                'channel_number': channel_num,
                'battery_code': test_result.get('battery_code', ''),
                'timestamp': timestamp,  # 使用datetime对象
                'voltage': test_result.get('voltage'),
                'rs_value': test_result.get('rs_value'),
                'rct_value': test_result.get('rct_value'),
                'rsei_value': test_result.get('rsei_value'),
                'w_impedance': test_result.get('w_impedance'),
                'is_pass': test_result.get('is_pass', False),
                'fail_reason': test_result.get('fail_reason', ''),
                'test_mode': test_result.get('test_mode', 'research'),

                # 新增使用产品信息管理器获取的完整信息
                'operator': product_info.get('operator', 'Unknown'),
                'battery_type': product_info.get('battery_type', '磷酸铁锂'),
                'battery_spec': product_info.get('battery_spec', '21700'),
                'standard_voltage': product_info.get('standard_voltage', 3.2),
                'standard_capacity': product_info.get('standard_capacity', 3.0),
                'batch_number': product_info.get('batch_number', 'BATCH-UNKNOWN'),

                # 新增额外的电池信息字段
                'capacity': product_info.get('standard_capacity', 3.0) * 1000,  # 转换为mAh
                'nominal_voltage': product_info.get('standard_voltage', 3.2),
                'temperature': 25.0,  # 默认温度，后续可从传感器获取

                # 新增制造商和生产日期信息
                'manufacturer': self.config_manager.get('product.manufacturer', ''),
                'production_date': self.config_manager.get('product.production_date', ''),
            }

            # 添加阻抗详情数据
            frequency_data = test_result.get('frequency_data', [])
            if frequency_data:
                upload_test_result['frequency_data'] = frequency_data
                logger.debug(f"通道{channel_num}包含{len(frequency_data)}个频点数据")

            # 修改创建包含完整产品信息的批次信息
            batch_info = {
                'batch_number': product_info.get('batch_number', 'AUTO_BATCH'),
                'operator': product_info.get('operator', 'System'),
                'cell_type': product_info.get('battery_type', '磷酸铁锂'),
                'cell_spec': product_info.get('battery_spec', '21700'),

                # 新增额外的批次信息
                'standard_voltage': product_info.get('standard_voltage', 3.2),
                'standard_capacity': product_info.get('standard_capacity', 3.0),
                'production_date': self.config_manager.get('product.production_date', ''),
                'manufacturer': self.config_manager.get('product.manufacturer', ''),
                'remarks': self.config_manager.get('product.remarks', ''),
            }

            # 触发数据上传
            self.data_upload_manager.upload_test_result(upload_test_result, batch_info)
            logger.info(f"✅ 通道{channel_num}测试结果已提交上传队列")

        except Exception as e:
            logger.error(f"触发通道{channel_num}数据上传失败: {e}")

    def _get_actual_battery_code(self, channel_num: int) -> str:
        """
        获取实际的电池码（修复电池码保存逻辑）

        Args:
            channel_num: 通道号（1-8）

        Returns:
            实际的电池码
        """
        try:
            # 方法1：从批次电池码列表获取（主要方法）
            if self.battery_codes and len(self.battery_codes) >= channel_num:
                battery_code = self.battery_codes[channel_num - 1]
                if battery_code and battery_code.strip():
                    logger.debug(f"从批次电池码列表获取通道{channel_num}电池码: {battery_code}")
                    return battery_code.strip()

            # 方法2：使用默认电池码（备用方案）
            default_code = f'BAT{channel_num:03d}'
            logger.warning(f"无法获取通道{channel_num}的实际电池码，使用默认值: {default_code}")
            return default_code

        except Exception as e:
            logger.error(f"获取通道{channel_num}电池码失败: {e}")
            return f'BAT{channel_num:03d}'

    def _create_new_batch(self, batch_info: Dict) -> int:
        """
        创建或获取批次记录，确保相同批次号使用相同的批次ID

        Args:
            batch_info: 批次信息

        Returns:
            批次ID（新创建或已存在的）
        """
        try:
            if not self.db_manager:
                logger.error("数据库管理器未初始化")
                return 1

            # 修复使用用户设置的原始批次号，不添加时间戳
            original_batch_number = batch_info.get('batch_number', 'BATCH')

            # 每次测试创建独立批次（添加时间戳确保唯一性）
            import time
            unique_batch_number = f"{original_batch_number}-{time.strftime('%H%M%S')}"
            logger.info(f"🆕 创建独立批次: {unique_batch_number}")

            # 创建新批次
            new_batch_data = {
                'batch_number': unique_batch_number,  # 每次测试独立批次号
                'operator': batch_info.get('operator', 'system'),
                'cell_type': batch_info.get('cell_type', '磷酸铁锂'),
                'cell_spec': batch_info.get('cell_spec', '21700'),
                'standard_voltage': batch_info.get('standard_voltage', 3.2),
                'standard_capacity': batch_info.get('standard_capacity', 3000),
                'remarks': batch_info.get('remarks', f'批次创建时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
            }

            # 创建新批次
            batch_id = self.db_manager.create_batch(new_batch_data)

            logger.info(f"🆕 创建新批次成功: ID={batch_id}, 批次号={original_batch_number}")
            return batch_id

        except Exception as e:
            logger.error(f"创建批次失败: {e}")
            # 如果创建失败，使用默认批次
            return self._ensure_batch_exists()

    def _ensure_batch_exists(self) -> int:
        """
        确保批次记录存在，如果不存在则创建

        Returns:
            批次ID
        """
        try:
            if not self.db_manager:
                logger.error("数据库管理器未初始化")
                return 1

            # 获取最近的批次
            recent_batches = self.db_manager.get_recent_batches(limit=1)
            if recent_batches:
                batch_id = recent_batches[0]['id']
                logger.debug(f"使用现有批次: ID={batch_id}")
                return batch_id

            # 如果没有批次，创建默认批次
            batch_data = {
                'batch_number': f'DEFAULT-BATCH-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
                'operator': 'system',
                'cell_type': '磷酸铁锂',
                'cell_spec': '21700',
                'standard_voltage': 3.2,
                'standard_capacity': 3000,
                'remarks': '系统自动创建的默认批次'
            }
            batch_id = self.db_manager.create_batch(batch_data)
            logger.info(f"创建新批次记录: ID={batch_id}, 批次号={batch_data['batch_number']}")
            return batch_id

        except Exception as e:
            logger.error(f"确保批次存在失败: {e}")
            return 1  # 返回默认批次ID

    def clear_test_data(self, preserve_batch_context: bool = False):
        """清理测试数据，防止数据覆盖"""
        try:
            logger.info(f"🧹 开始清理测试数据... preserve_batch_context={preserve_batch_context}")

            # 1. 清空测试时间记录
            self.test_start_times.clear()
            self.test_end_times.clear()
            logger.info("✅ 测试时间记录已清空")

            # 2. 重置批次相关信息
            if preserve_batch_context:
                logger.info(f"✅ 保留批次上下文: batch_id={self.current_batch_id}")
            else:
                self.current_batch_id = None
                self.batch_info.clear()
                logger.info("✅ 批次信息已重置")

            # 3. 清空电池码信息
            self.battery_codes.clear()
            logger.info("✅ 电池码信息已清空")

            # 新增清空阻抗数据管理器的增强电池码映射
            if self.impedance_data_manager:
                self.impedance_data_manager.clear_enhanced_battery_codes()
                logger.info("✅ 增强电池码映射已清空")

            # 4. 清理新管理器资源
            if self._failure_reason_manager:
                self._failure_reason_manager.cleanup()
                self._failure_reason_manager = None

            if self._test_mode_manager:
                self._test_mode_manager.cleanup()
                self._test_mode_manager = None

            if self._product_info_manager:
                self._product_info_manager.cleanup()
                self._product_info_manager = None

            if self._test_parameter_calculator:
                self._test_parameter_calculator.cleanup()
                self._test_parameter_calculator = None

            logger.info("✅ 新管理器资源已清理")

            logger.info("🎯 测试数据清理完成")

        except Exception as e:
            logger.error(f"清理测试数据失败: {e}")

    def get_batch_info(self) -> Dict[str, Any]:
        """获取当前批次信息"""
        return {
            'current_batch_id': self.current_batch_id,
            'batch_info': self.batch_info.copy(),
            'battery_codes': self.battery_codes.copy()
        }

    def get_test_duration(self, channel_num: int) -> float:
        """
        获取指定通道的测试持续时间

        Args:
            channel_num: 通道号（1-8）

        Returns:
            测试持续时间（秒）
        """
        start_time = self.test_start_times.get(channel_num, 0)
        end_time = self.test_end_times.get(channel_num, 0)
        return end_time - start_time if start_time and end_time else 0

    def _get_current_battery_code(self, channel_num: int) -> str:
        """
        获取当前通道的电池编码

        Args:
            channel_num: 通道号（1-8）

        Returns:
            电池编码
        """
        try:
            # 从电池码列表中获取（通道号从1开始，列表索引从0开始）
            if self.battery_codes and len(self.battery_codes) >= channel_num:
                battery_code = self.battery_codes[channel_num - 1]
                if battery_code and battery_code.strip():
                    return battery_code.strip()

            # 如果没有记录，生成默认编码
            default_code = f"CH{channel_num:02d}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            logger.debug(f"通道{channel_num}未找到电池编码，使用默认编码: {default_code}")
            return default_code

        except Exception as e:
            logger.error(f"获取通道{channel_num}电池编码失败: {e}")
            return f"CH{channel_num:02d}-UNKNOWN"

    def _get_battery_test_sequence(self, battery_code: str, channel_num: int) -> int:
        """
        获取指定电池码的测试序号（连续测试模式下使用）

        Args:
            battery_code: 原始电池编码
            channel_num: 通道号

        Returns:
            测试序号（从1开始）
        """
        try:
            if not self.db_manager or not battery_code:
                return 1

            # 查询同一电池码的测试记录数量（包括带序号的）
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # 查询以该电池码开头的所有记录
                cursor.execute('''
                    SELECT COUNT(*) FROM test_results
                    WHERE battery_code LIKE ? AND channel_number = ?
                ''', (f"{battery_code}%", channel_num))

                count = cursor.fetchone()[0]
                next_sequence = count + 1

                logger.debug(f"电池码 {battery_code} 通道{channel_num} 已有{count}条记录，下次序号: {next_sequence}")
                return next_sequence

        except Exception as e:
            logger.error(f"获取电池码 {battery_code} 测试序号失败: {e}")
            return 1

    def _get_historical_rct_values(self, battery_code: str, channel_num: int, limit: int = 10) -> List[float]:
        """
        获取指定电池的历史Rct值

        Args:
            battery_code: 电池编码
            channel_num: 通道号
            limit: 获取的历史记录数量限制

        Returns:
            历史Rct值列表
        """
        try:
            if not self.db_manager or not battery_code:
                return []

            # 查询同一电池的历史测试结果
            historical_results = self.db_manager.get_test_results(
                battery_code=battery_code,
                channel_number=channel_num,
                limit=limit,
                offset=0,
                include_json=False
            )

            # 提取Rct值
            rct_values = []
            for result in historical_results:
                rct_value = result.get('rct_value', 0)
                if rct_value > 0:  # 只包含有效的Rct值
                    rct_values.append(rct_value)

            logger.debug(f"获取电池{battery_code}通道{channel_num}的历史Rct值: {len(rct_values)}个")
            return rct_values

        except Exception as e:
            logger.error(f"获取历史Rct值失败: {e}")
            return []

    def _format_impedance_data_for_storage(self, channel_num: int) -> Dict:
        """
        格式化阻抗数据用于存储
        将内存中的阻抗数据转换为适合EIS分析的格式

        Args:
            channel_num: 通道号

        Returns:
            格式化后的阻抗数据
        """
        try:
            # 从内存获取原始阻抗数据
            raw_impedance_data = self.impedance_data_manager.get_channel_impedance_data(channel_num)

            if not raw_impedance_data:
                logger.warning(f"通道{channel_num}没有阻抗数据")
                return {}

            # 转换格式：{frequency: {'real': value, 'imag': value}} -> {'real_parts': [...], 'imag_parts': [...]}
            frequencies = sorted(raw_impedance_data.keys(), reverse=True)  # 从高频到低频
            real_parts = []
            imag_parts = []

            for freq in frequencies:
                freq_data = raw_impedance_data[freq]
                real_parts.append(freq_data.get('real', 0.0))
                imag_parts.append(freq_data.get('imag', 0.0))

            formatted_data = {
                'frequencies': frequencies,
                'real_parts': real_parts,
                'imag_parts': imag_parts,
                'channel': channel_num,
                'data_points': len(frequencies)
            }

            logger.debug(f"通道{channel_num}阻抗数据格式化完成: {len(frequencies)}个频点")
            return formatted_data

        except Exception as e:
            logger.error(f"通道{channel_num}阻抗数据格式化失败: {e}")
            return {}

    def _save_capacity_prediction_data_if_enabled(self, channel_num: int, test_result: Dict[str, Any], rct_cv: float):
        """
        如果启用容量预测功能，保存容量预测数据

        Args:
            channel_num: 通道号
            test_result: 测试结果数据
            rct_cv: Rct变异系数
        """
        try:
            # 检查是否启用容量预测功能
            if not self.config_manager.get('test.capacity_prediction_enabled', False):
                logger.debug(f"通道{channel_num}容量预测功能未启用，跳过保存")
                return

            # 构建容量预测数据
            prediction_data = {
                'battery_code': test_result['battery_code'],
                'batch_id': test_result['batch_id'],
                'channel_number': channel_num,
                'test_date': datetime.now().date(),
                'voltage': test_result['voltage'],
                'rs_value': test_result['rs_value'],
                'rct_value': test_result['rct_value'],
                'rct_coefficient_of_variation': rct_cv,
                'voltage_range_min': self.config_manager.get('capacity_prediction.voltage_min', 3.0),
                'voltage_range_max': self.config_manager.get('capacity_prediction.voltage_max', 3.4),
                'rs_range_min': self.config_manager.get('capacity_prediction.rs_min', 0.1),
                'rs_range_max': self.config_manager.get('capacity_prediction.rs_max', 5.0),
                'notes': f'连续测试模式自动保存 - 通道{channel_num}'
            }

            # 保存到数据库
            prediction_id = self.db_manager.save_capacity_prediction_data(prediction_data)

            if prediction_id:
                logger.info(f"通道{channel_num}容量预测数据保存成功: ID={prediction_id}, Rct变异系数={rct_cv:.2f}%")
            else:
                logger.warning(f"通道{channel_num}容量预测数据保存失败")

        except Exception as e:
            logger.error(f"通道{channel_num}保存容量预测数据失败: {e}")

    def _should_use_fast_mode(self) -> bool:
        """判断是否应该使用快速模式"""
        if self.fast_mode_enabled:
            return True

        # 根据历史计算时间判断
        if len(self.calculation_times) >= 3:
            avg_time = sum(self.calculation_times[-3:]) / 3
            if avg_time > self.max_calculation_time:
                logger.info(f"⚡ 自动启用快速模式，平均计算时间: {avg_time:.2f}秒")
                return True

        return False

    def enable_fast_mode(self):
        """启用快速计算模式"""
        self.fast_mode_enabled = True
        logger.info("⚡ 测试结果管理器快速模式已启用")

    def disable_fast_mode(self):
        """禁用快速计算模式"""
        self.fast_mode_enabled = False
        logger.info("🔄 测试结果管理器快速模式已禁用")

    def get_performance_stats(self) -> dict:
        """获取性能统计"""
        if not self.calculation_times:
            return {}

        return {
            'average_calculation_time': sum(self.calculation_times) / len(self.calculation_times),
            'total_calculations': len(self.calculation_times),
            'fast_mode_enabled': self.fast_mode_enabled,
            'max_calculation_time': max(self.calculation_times) if self.calculation_times else 0,
            'min_calculation_time': min(self.calculation_times) if self.calculation_times else 0
        }

    def reset_channel_results(self, channel_num: int):
        """
        重置指定通道的计算结果

        当用户停止测试时，清理该通道的缓存结果，
        避免脏数据影响后续测试

        Args:
            channel_num: 通道号（1-8）
        """
        try:
            logger.info(f"🛑 重置通道{channel_num}的计算结果...")

            # Jack要求移除Rsei缓存清理逻辑
            # 清理Rsei缓存 - 已移除
            # if hasattr(self, '_channel_rsei_cache') and channel_num in self._channel_rsei_cache:
            #     del self._channel_rsei_cache[channel_num]
            #     logger.debug(f"✅ 通道{channel_num}Rsei缓存已清理")

            # 清理增强分析结果缓存
            if hasattr(self, '_channel_enhanced_cache') and channel_num in self._channel_enhanced_cache:
                del self._channel_enhanced_cache[channel_num]
                logger.debug(f"✅ 通道{channel_num}增强分析缓存已清理")

            # 清理测试时间记录
            if channel_num in self.test_start_times:
                del self.test_start_times[channel_num]
                logger.debug(f"✅ 通道{channel_num}测试开始时间已清理")

            if channel_num in self.test_end_times:
                del self.test_end_times[channel_num]
                logger.debug(f"✅ 通道{channel_num}测试结束时间已清理")

            logger.info(f"🛑 通道{channel_num}计算结果重置完成")

        except Exception as e:
            logger.error(f"🛑 重置通道{channel_num}计算结果失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

    def _get_test_time_conditions(self) -> Dict[str, float]:
        """
        获取测试时的实际判断条件（作为历史记录保存）

        Returns:
            包含测试时判断条件的字典
        """
        try:
            # 获取电压范围（优先使用界面设置）
            standard_voltage = self.config_manager.get('grade_settings.standard_voltage')
            voltage_diff = self.config_manager.get('grade_settings.voltage_diff')

            if standard_voltage is not None and voltage_diff is not None:
                voltage_min = standard_voltage - voltage_diff
                voltage_max = standard_voltage + voltage_diff
            else:
                voltage_min = self.config_manager.get('grade_settings.voltage_min')
                if voltage_min is None:
                    voltage_min = self.config_manager.get('test_params.voltage_range.min', 2.889)

                voltage_max = self.config_manager.get('grade_settings.voltage_max')
                if voltage_max is None:
                    voltage_max = self.config_manager.get('test_params.voltage_range.max', 3.531)

            # 获取Rs范围
            rs_min = self.config_manager.get('grade_settings.rs_min')
            if rs_min is None:
                rs_min = self.config_manager.get('impedance.rs_min', 0.5)

            rs_max = self.config_manager.get('grade_settings.rs_max')
            if rs_max is None:
                rs_max = self.config_manager.get('impedance.rs_grade3_max', 50.0)

            # 获取Rct范围
            rct_min = self.config_manager.get('grade_settings.rct_min')
            if rct_min is None:
                rct_min = self.config_manager.get('impedance.rct_min', 0.5)

            rct_max = self.config_manager.get('grade_settings.rct_max')
            if rct_max is None:
                rct_max = self.config_manager.get('impedance.rct_grade3_max', 100.0)

            conditions = {
                'voltage_min': voltage_min,
                'voltage_max': voltage_max,
                'rs_min': rs_min,
                'rs_max': rs_max,
                'rct_min': rct_min,
                'rct_max': rct_max
            }

            logger.debug(f"获取测试时判断条件: {conditions}")
            return conditions

        except Exception as e:
            logger.error(f"获取测试时判断条件失败: {e}")
            # 返回默认值
            return {
                'voltage_min': 2.889,
                'voltage_max': 3.531,
                'rs_min': 0.5,
                'rs_max': 50.0,
                'rct_min': 0.5,
                'rct_max': 100.0
            }
