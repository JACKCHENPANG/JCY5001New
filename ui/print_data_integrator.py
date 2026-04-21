#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印数据集成模块
确保测试数据正确传递到打印系统

Author: Assistant
Date: 2025-06-23
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class PrintDataIntegrator:
    """打印数据集成器"""
    
    def __init__(self):
        """初始化打印数据集成器"""
        self.channel_data_cache = {}  # 缓存通道数据
        
    def extract_print_data_from_channel(self, channel_widget) -> Dict[str, Any]:
        """
        从通道组件提取打印数据
        
        Args:
            channel_widget: 通道显示组件
            
        Returns:
            打印数据字典
        """
        try:
            if not channel_widget:
                logger.error("通道组件为空，无法提取打印数据")
                return {}
            
            channel_number = getattr(channel_widget, 'channel_number', 0)
            
            # 优先使用通道组件的get_print_data方法
            if hasattr(channel_widget, 'get_print_data'):
                print_data = channel_widget.get_print_data()
                if print_data and (print_data.get('rs_value', 0) > 0 or print_data.get('rct_value', 0) > 0):
                    logger.info(f"✅ [打印集成] 通道{channel_number}使用get_print_data方法获取数据成功")
                    return print_data
            
            # 备用方案：直接从属性获取
            print_data = {
                'channel_number': channel_number,
                'battery_code': getattr(channel_widget, 'battery_code', ''),
                'voltage': getattr(channel_widget, 'voltage', 0.0),
                'rs_value': getattr(channel_widget, 'rs_value', 0.0),
                'rct_value': getattr(channel_widget, 'rct_value', 0.0),
                'rs': getattr(channel_widget, 'rs_value', 0.0),  # 兼容字段名
                'rct': getattr(channel_widget, 'rct_value', 0.0),  # 兼容字段名
                'timestamp': None,
                'is_pass': False,
                'rs_grade': None,
                'rct_grade': None
            }
            
            # 尝试从其他属性获取数据
            if print_data['rs_value'] == 0.0:
                print_data['rs_value'] = getattr(channel_widget, 'current_rs', 0.0)
                print_data['rs'] = print_data['rs_value']
            
            if print_data['rct_value'] == 0.0:
                print_data['rct_value'] = getattr(channel_widget, 'current_rct', 0.0)
                print_data['rct'] = print_data['rct_value']
            
            if print_data['voltage'] == 0.0:
                print_data['voltage'] = getattr(channel_widget, 'current_voltage', 0.0)
            
            # 从test_result获取更多数据
            test_result = getattr(channel_widget, 'test_result', None)
            if test_result:
                if hasattr(test_result, '__dict__'):
                    test_result = test_result.__dict__
                
                if isinstance(test_result, dict):
                    print_data.update({
                        'is_pass': test_result.get('is_pass', False),
                        'rs_grade': test_result.get('rs_grade'),
                        'rct_grade': test_result.get('rct_grade'),
                        'outlier_result': test_result.get('outlier_result', '--'),
                        'outlier_rate': test_result.get('outlier_rate', '--'),
                        'frequency_deviations': test_result.get('frequency_deviations', {}),
                        'max_deviation_percent': test_result.get('max_deviation_percent', 0.0)
                    })
            
            # 从datetime导入
            from datetime import datetime
            print_data['timestamp'] = datetime.now()
            
            logger.info(f"✅ [打印集成] 通道{channel_number}使用备用方案获取数据: Rs={print_data['rs_value']:.3f}mΩ, Rct={print_data['rct_value']:.3f}mΩ")
            
            return print_data
            
        except Exception as e:
            logger.error(f"从通道组件提取打印数据失败: {e}")
            return {}
    
    def validate_print_data(self, print_data: Dict[str, Any]) -> bool:
        """
        验证打印数据的完整性
        
        Args:
            print_data: 打印数据字典
            
        Returns:
            数据是否有效
        """
        try:
            if not print_data:
                logger.warning("打印数据为空")
                return False
            
            # 检查必要字段
            required_fields = ['channel_number', 'battery_code', 'voltage', 'rs_value', 'rct_value']
            missing_fields = []
            
            for field in required_fields:
                if field not in print_data:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning(f"打印数据缺少必要字段: {missing_fields}")
                return False
            
            # 检查数据值的合理性
            rs_value = print_data.get('rs_value', 0)
            rct_value = print_data.get('rct_value', 0)
            voltage = print_data.get('voltage', 0)
            
            if rs_value == 0 and rct_value == 0:
                logger.warning(f"打印数据异常: Rs和Rct值都为0")
                return False
            
            if voltage <= 0:
                logger.warning(f"打印数据异常: 电压值为{voltage}")
                # 电压为0不一定是错误，可能是异常状态
            
            logger.debug(f"打印数据验证通过: Rs={rs_value:.3f}mΩ, Rct={rct_value:.3f}mΩ, V={voltage:.3f}V")
            return True
            
        except Exception as e:
            logger.error(f"验证打印数据失败: {e}")
            return False
    
    def cache_channel_data(self, channel_number: int, print_data: Dict[str, Any]):
        """
        缓存通道数据
        
        Args:
            channel_number: 通道号
            print_data: 打印数据
        """
        try:
            self.channel_data_cache[channel_number] = print_data.copy()
            logger.debug(f"通道{channel_number}数据已缓存")
        except Exception as e:
            logger.error(f"缓存通道{channel_number}数据失败: {e}")
    
    def get_cached_data(self, channel_number: int) -> Optional[Dict[str, Any]]:
        """
        获取缓存的通道数据
        
        Args:
            channel_number: 通道号
            
        Returns:
            缓存的数据或None
        """
        return self.channel_data_cache.get(channel_number)
    
    def clear_cache(self):
        """清空缓存"""
        self.channel_data_cache.clear()
        logger.debug("打印数据缓存已清空")

# 全局实例
_print_data_integrator = PrintDataIntegrator()

def get_print_data_integrator() -> PrintDataIntegrator:
    """获取打印数据集成器实例"""
    return _print_data_integrator
