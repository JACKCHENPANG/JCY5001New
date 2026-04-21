"""
配置验证工具类 - 统一配置验证逻辑
用于减少配置管理中的重复代码
"""

import logging
from typing import Any, Dict, List, Optional, Callable, Union

logger = logging.getLogger(__name__)


class ConfigValidator:
    """配置验证器 - 提供统一的配置验证功能"""
    
    @staticmethod
    def validate_numeric_range(value: Any, min_val: float, max_val: float, 
                              default: float, name: str) -> float:
        """
        验证数值范围
        
        Args:
            value: 要验证的值
            min_val: 最小值
            max_val: 最大值
            default: 默认值
            name: 参数名称
            
        Returns:
            验证后的数值
        """
        try:
            num_val = float(value)
            if min_val <= num_val <= max_val:
                return num_val
            else:
                logger.warning(f"{name}超出范围[{min_val}, {max_val}]: {num_val}，使用默认值: {default}")
                return default
        except (ValueError, TypeError):
            logger.warning(f"无效的{name}: {value}，使用默认值: {default}")
            return default
    
    @staticmethod
    def validate_integer_range(value: Any, min_val: int, max_val: int, 
                              default: int, name: str) -> int:
        """
        验证整数范围
        
        Args:
            value: 要验证的值
            min_val: 最小值
            max_val: 最大值
            default: 默认值
            name: 参数名称
            
        Returns:
            验证后的整数
        """
        try:
            int_val = int(value)
            if min_val <= int_val <= max_val:
                return int_val
            else:
                logger.warning(f"{name}超出范围[{min_val}, {max_val}]: {int_val}，使用默认值: {default}")
                return default
        except (ValueError, TypeError):
            logger.warning(f"无效的{name}: {value}，使用默认值: {default}")
            return default
    
    @staticmethod
    def validate_choice(value: Any, choices: List[Any], default: Any, name: str) -> Any:
        """
        验证选择项
        
        Args:
            value: 要验证的值
            choices: 有效选择列表
            default: 默认值
            name: 参数名称
            
        Returns:
            验证后的值
        """
        if value in choices:
            return value
        else:
            logger.warning(f"无效的{name}: {value}，有效选择: {choices}，使用默认值: {default}")
            return default
    
    @staticmethod
    def validate_list(value: Any, item_validator: Optional[Callable] = None, 
                     default: Optional[List] = None, name: str = "列表") -> List:
        """
        验证列表
        
        Args:
            value: 要验证的值
            item_validator: 列表项验证函数
            default: 默认值
            name: 参数名称
            
        Returns:
            验证后的列表
        """
        if default is None:
            default = []
            
        if not isinstance(value, list):
            logger.warning(f"无效的{name}: {value}，使用默认值: {default}")
            return default
        
        if not value:  # 空列表
            logger.warning(f"{name}为空，使用默认值: {default}")
            return default
        
        if item_validator:
            validated_items = []
            for item in value:
                try:
                    validated_item = item_validator(item)
                    if validated_item is not None:
                        validated_items.append(validated_item)
                except Exception as e:
                    logger.warning(f"{name}中的无效项: {item}，错误: {e}")
            
            if validated_items:
                return validated_items
            else:
                logger.warning(f"{name}中没有有效项，使用默认值: {default}")
                return default
        
        return value
    
    @staticmethod
    def validate_frequency_list(frequencies: Any, name: str = "频率列表") -> List[float]:
        """
        验证频率列表
        
        Args:
            frequencies: 频率列表
            name: 参数名称
            
        Returns:
            验证后的频率列表
        """
        def validate_frequency(freq):
            try:
                freq_val = float(freq)
                if 0.01 <= freq_val <= 10000:  # 频率范围限制
                    return freq_val
                else:
                    logger.warning(f"频率值超出范围[0.01, 10000]: {freq_val}Hz")
                    return None
            except (ValueError, TypeError):
                logger.warning(f"无效的频率值: {freq}")
                return None
        
        return ConfigValidator.validate_list(
            frequencies, 
            item_validator=validate_frequency,
            default=[1000.0],
            name=name
        )
    
    @staticmethod
    def validate_baudrate(baudrate: Any, name: str = "波特率") -> int:
        """
        验证波特率
        
        Args:
            baudrate: 波特率值
            name: 参数名称
            
        Returns:
            验证后的波特率
        """
        valid_baudrates = [9600, 19200, 38400, 57600, 115200]
        return ConfigValidator.validate_choice(baudrate, valid_baudrates, 115200, name)
    
    @staticmethod
    def validate_device_address(address: Any, name: str = "设备地址") -> int:
        """
        验证设备地址
        
        Args:
            address: 设备地址
            name: 参数名称
            
        Returns:
            验证后的设备地址
        """
        return ConfigValidator.validate_integer_range(address, 1, 247, 1, name)
    
    @staticmethod
    def validate_timeout(timeout: Any, name: str = "超时时间") -> float:
        """
        验证超时时间
        
        Args:
            timeout: 超时时间
            name: 参数名称
            
        Returns:
            验证后的超时时间
        """
        return ConfigValidator.validate_numeric_range(timeout, 0.1, 10.0, 2.0, name)
    
    @staticmethod
    def validate_gain(gain: Any, name: str = "增益设置") -> str:
        """
        验证增益设置
        
        Args:
            gain: 增益值
            name: 参数名称
            
        Returns:
            验证后的增益设置
        """
        valid_gains = ['1', '4', '16', 'auto']
        return ConfigValidator.validate_choice(gain, valid_gains, '1', name)
    
    @staticmethod
    def validate_resistance_range(resistance_range: Any, name: str = "电阻档位") -> str:
        """
        验证电阻档位
        
        Args:
            resistance_range: 电阻档位
            name: 参数名称
            
        Returns:
            验证后的电阻档位
        """
        valid_ranges = ['1R', '5R', '10R']
        return ConfigValidator.validate_choice(resistance_range, valid_ranges, '10R', name)
    
    @staticmethod
    def validate_average_times(average_times: Any, name: str = "平均次数") -> int:
        """
        验证平均次数
        
        Args:
            average_times: 平均次数
            name: 参数名称
            
        Returns:
            验证后的平均次数
        """
        return ConfigValidator.validate_integer_range(average_times, 1, 100, 1, name)
    
    @staticmethod
    def validate_test_timeout(timeout: Any, name: str = "测试超时时间") -> int:
        """
        验证测试超时时间
        
        Args:
            timeout: 超时时间
            name: 参数名称
            
        Returns:
            验证后的超时时间
        """
        return ConfigValidator.validate_integer_range(timeout, 5, 300, 60, name)


class ConfigValidationRules:
    """配置验证规则类 - 定义各种配置的验证规则"""
    
    # 测试配置验证规则
    TEST_CONFIG_RULES = {
        'frequencies': {
            'validator': ConfigValidator.validate_frequency_list,
            'required': True
        },
        'gain': {
            'validator': ConfigValidator.validate_gain,
            'required': False
        },
        'average_times': {
            'validator': ConfigValidator.validate_average_times,
            'required': False
        },
        'resistance_range': {
            'validator': ConfigValidator.validate_resistance_range,
            'required': False
        },
        'timeout': {
            'validator': ConfigValidator.validate_test_timeout,
            'required': False
        }
    }
    
    # 通信配置验证规则
    COMMUNICATION_CONFIG_RULES = {
        'baudrate': {
            'validator': ConfigValidator.validate_baudrate,
            'required': True
        },
        'device_address': {
            'validator': ConfigValidator.validate_device_address,
            'required': True
        },
        'timeout': {
            'validator': ConfigValidator.validate_timeout,
            'required': True
        }
    }
    
    @classmethod
    def validate_config_dict(cls, config: Dict, rules: Dict) -> Dict:
        """
        根据规则验证配置字典
        
        Args:
            config: 配置字典
            rules: 验证规则字典
            
        Returns:
            验证后的配置字典
        """
        validated_config = config.copy()
        
        for key, rule in rules.items():
            if key in config:
                validator = rule['validator']
                try:
                    validated_config[key] = validator(config[key])
                except Exception as e:
                    logger.error(f"验证配置项 {key} 失败: {e}")
            elif rule.get('required', False):
                logger.warning(f"缺少必需的配置项: {key}")
        
        return validated_config
