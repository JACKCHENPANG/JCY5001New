# -*- coding: utf-8 -*-
"""
通道打印数据管理器
负责单个通道的打印数据收集、格式化和提供

Author: Jack
Date: 2025-06-27
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ChannelPrintDataManager:
    """通道打印数据管理器"""
    
    def __init__(self, channel_number: int):
        """
        初始化打印数据管理器
        
        Args:
            channel_number: 通道号
        """
        self.channel_number = channel_number
        
        # 数据源引用
        self.test_completion_manager = None
        self.data_manager = None
        
    def set_data_sources(self, test_completion_manager, data_manager):
        """
        设置数据源引用
        
        Args:
            test_completion_manager: 测试完成管理器
            data_manager: 数据管理器
        """
        self.test_completion_manager = test_completion_manager
        self.data_manager = data_manager
        
    def get_print_data(self) -> dict:
        """
        获取用于打印的测试数据
        
        Returns:
            包含完整测试数据的字典
        """
        try:
            # 获取基本测试数据
            current_voltage = self._get_current_voltage()
            current_rs = self._get_current_rs()
            current_rct = self._get_current_rct()
            battery_code = self._get_battery_code()
            
            logger.info(f"通道{self.channel_number} 开始获取打印数据")
            logger.info(f"通道{self.channel_number} 基本数据: V={current_voltage:.3f}V, Rs={current_rs:.3f}mΩ, Rct={current_rct:.3f}mΩ")
            
            # 获取档位和合格状态信息
            rs_grade, rct_grade, is_pass = self._get_grade_and_pass_info()
            
            logger.info(f"通道{self.channel_number}从测试数据获取档位: Rs={rs_grade}, Rct={rct_grade}, 合格={is_pass}")
            
            # 获取离群检测数据
            outlier_data = self._get_outlier_data()
            
            # 构建打印数据
            print_data = {
                'channel_number': self.channel_number,
                'battery_code': battery_code,
                'voltage': current_voltage,
                'rs': current_rs,  # 保持原有字段名
                'rct': current_rct,  # 保持原有字段名
                'rs_value': current_rs,  # 兼容打印模块的字段名
                'rct_value': current_rct,  # 兼容打印模块的字段名
                'rs_grade': rs_grade,
                'rct_grade': rct_grade,
                'is_pass': is_pass,
                'timestamp': datetime.now(),
                # 离群率相关数据
                'outlier_result': outlier_data.get('outlier_result', '--'),
                'outlier_rate': outlier_data.get('outlier_result', '--'),  # 兼容字段名
                'frequency_deviations': outlier_data.get('frequency_deviations', {}),
                'max_deviation_percent': outlier_data.get('max_deviation_percent', 0.0),
                'baseline_filename': outlier_data.get('baseline_filename', ''),
                'baseline_id': outlier_data.get('baseline_id', None)
            }
            
            logger.info(f"通道{self.channel_number}获取打印数据: Rs={current_rs:.3f}mΩ, Rct={current_rct:.3f}mΩ, V={current_voltage:.3f}V, 档位={rs_grade}-{rct_grade}")
            
            return print_data
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}获取打印数据失败: {e}")
            return {}

    def _get_current_voltage(self) -> float:
        """获取当前电压值"""
        try:
            if self.data_manager:
                return self.data_manager.test_data.voltage
            return 0.0
        except Exception as e:
            logger.debug(f"通道{self.channel_number}获取电压值失败: {e}")
            return 0.0

    def _get_current_rs(self) -> float:
        """获取当前Rs值"""
        try:
            if self.data_manager:
                return self.data_manager.test_data.rs_value
            return 0.0
        except Exception as e:
            logger.debug(f"通道{self.channel_number}获取Rs值失败: {e}")
            return 0.0

    def _get_current_rct(self) -> float:
        """获取当前Rct值"""
        try:
            if self.data_manager:
                return self.data_manager.test_data.rct_value
            return 0.0
        except Exception as e:
            logger.debug(f"通道{self.channel_number}获取Rct值失败: {e}")
            return 0.0

    def _get_battery_code(self) -> str:
        """获取电池码"""
        try:
            if self.data_manager:
                return self.data_manager.test_data.battery_code
            return ""
        except Exception as e:
            logger.debug(f"通道{self.channel_number}获取电池码失败: {e}")
            return ""

    def _get_grade_and_pass_info(self) -> tuple:
        """
        获取档位和合格状态信息
        
        Returns:
            (rs_grade, rct_grade, is_pass)
        """
        try:
            rs_grade = None
            rct_grade = None
            is_pass = False

            # 优先从最近的测试数据获取档位信息，这是最可靠的数据源
            if self.test_completion_manager:
                last_test_data = self.test_completion_manager.get_last_test_data()
                if last_test_data:
                    rs_grade = last_test_data.get('rs_grade')
                    rct_grade = last_test_data.get('rct_grade')
                    is_pass = last_test_data.get('is_pass', False)
                    logger.info(f"通道{self.channel_number}从最近测试数据获取档位: Rs={rs_grade}, Rct={rct_grade}, 合格={is_pass}")

            # 备用：从test_result获取
            if rs_grade is None or rct_grade is None:
                if self.test_completion_manager:
                    test_result = self.test_completion_manager.get_test_result()
                    if test_result:
                        rs_grade = test_result.get('rs_grade')
                        rct_grade = test_result.get('rct_grade')
                        is_pass = test_result.get('is_pass', False)
                        logger.info(f"通道{self.channel_number} 从test_result获取: Rs={rs_grade}, Rct={rct_grade}, 合格={is_pass}")

            # 如果仍然没有档位信息，根据测试结果设置正确的档位显示
            if rs_grade is None or rct_grade is None:
                if is_pass:
                    # 合格但没有档位信息，使用默认值
                    rs_grade = rs_grade if rs_grade is not None else 1
                    rct_grade = rct_grade if rct_grade is not None else 1
                    logger.info(f"通道{self.channel_number}测试合格，使用默认档位: Rs={rs_grade}, Rct={rct_grade}")
                else:
                    # 不合格时档位应该显示为"--"
                    rs_grade = "--"
                    rct_grade = "--"
                    logger.info(f"通道{self.channel_number}测试不合格，档位设为--")

            return rs_grade, rct_grade, is_pass

        except Exception as e:
            logger.error(f"通道{self.channel_number}获取档位和合格状态信息失败: {e}")
            return "--", "--", False

    def _get_outlier_data(self) -> dict:
        """🚫 离群检测功能已删除"""
        return {
            'outlier_result': '--',
            'frequency_deviations': {},
            'max_deviation_percent': 0.0,
            'baseline_filename': '',
            'baseline_id': None
        }

    def get_formatted_print_data(self, template_fields: Optional[list] = None) -> dict:
        """
        获取格式化的打印数据
        
        Args:
            template_fields: 模板需要的字段列表
            
        Returns:
            格式化的打印数据字典
        """
        try:
            print_data = self.get_print_data()
            
            if not template_fields:
                return print_data
            
            # 根据模板字段过滤和格式化数据
            formatted_data = {}
            for field in template_fields:
                if field in print_data:
                    value = print_data[field]
                    # 根据字段类型进行格式化
                    if field in ['voltage', 'rs', 'rct', 'rs_value', 'rct_value']:
                        formatted_data[field] = f"{value:.3f}"
                    elif field in ['rs_grade', 'rct_grade']:
                        formatted_data[field] = str(value)
                    elif field == 'is_pass':
                        formatted_data[field] = "合格" if value else "不合格"
                    elif field == 'timestamp':
                        formatted_data[field] = value.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        formatted_data[field] = str(value)
                else:
                    formatted_data[field] = "--"
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}获取格式化打印数据失败: {e}")
            return {}

    def validate_print_data(self, print_data: dict) -> bool:
        """
        验证打印数据的完整性
        
        Args:
            print_data: 打印数据字典
            
        Returns:
            数据是否有效
        """
        try:
            required_fields = ['channel_number', 'battery_code', 'voltage', 'rs_value', 'rct_value', 'rs_grade', 'rct_grade', 'is_pass']
            
            for field in required_fields:
                if field not in print_data:
                    logger.warning(f"通道{self.channel_number}打印数据缺少必需字段: {field}")
                    return False
            
            # 检查数值字段的有效性
            if print_data['voltage'] < 0:
                logger.warning(f"通道{self.channel_number}电压值无效: {print_data['voltage']}")
                return False
            
            if print_data['rs_value'] < 0:
                logger.warning(f"通道{self.channel_number}Rs值无效: {print_data['rs_value']}")
                return False
            
            if print_data['rct_value'] < 0:
                logger.warning(f"通道{self.channel_number}Rct值无效: {print_data['rct_value']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}验证打印数据失败: {e}")
            return False
