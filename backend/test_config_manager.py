# -*- coding: utf-8 -*-
"""
测试配置管理器
负责管理测试配置加载、配置参数验证、配置变更处理等功能

从TestEngine中提取的配置管理功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import logging
from typing import Dict, List, Optional, Callable
from threading import Lock

from utils.config_validator import ConfigValidator, ConfigValidationRules

logger = logging.getLogger(__name__)


class TestConfigManager:
    """
    测试配置管理器

    职责：
    - 测试配置加载和保存
    - 配置参数验证
    - 配置变更通知
    - 默认配置管理
    - 通信配置管理
    """

    def __init__(self, config_manager, config_change_callback=None):
        """
        初始化测试配置管理器

        Args:
            config_manager: 基础配置管理器
            config_change_callback: 配置变更回调函数
        """
        self.config_manager = config_manager
        self.config_change_callback = config_change_callback

        # 配置锁，确保线程安全
        self.config_lock = Lock()

        # 当前测试配置缓存
        self._test_config_cache = None
        self._comm_config_cache = None

        # 配置验证规则（现在使用ConfigValidator统一处理）

        # 默认配置
        self._default_configs = self._init_default_configs()

        logger.debug("测试配置管理器初始化完成")

    def load_test_config(self) -> Dict:
        """
        加载测试配置

        Returns:
            测试配置字典
        """
        try:
            with self.config_lock:
                # 多频点模式
                frequencies = self.config_manager.get('frequency.list', [])
                if not frequencies:
                    frequencies = self.config_manager.get('frequency.custom_list', [])
                if not frequencies:
                    frequencies = [1000.0]  # 默认频率

                # 获取频率顺序设置
                frequency_order = self.config_manager.get('frequency.frequency_order', 'high_to_low')
                frequencies = self._sort_frequencies(frequencies, frequency_order)

                test_mode = self.config_manager.get('frequency.preset_mode', 'research')

                # 整合统一使用continuous_mode配置
                continuous_mode = self.config_manager.get('test.continuous_mode', False)

                config = {
                    'test_mode': test_mode,
                    'frequencies': frequencies,
                    'frequency_order': self.config_manager.get('frequency.frequency_order', 'high_to_low'),
                    'is_single_mode': False,  # 固定为False，已移除单频点模式
                    'continuous_mode': continuous_mode,  # 整合统一的连续模式配置
                    'interval': self.config_manager.get('test.interval', 2),
                    'timeout': self.config_manager.get('test.timeout', 60),
                    'gain': self.config_manager.get('test_params.gain', '1'),
                    'average_times': self.config_manager.get('test_params.average_times', 1),
                    'resistance_range': self._get_validated_resistance_range(),
                    'voltage_range': self.config_manager.get('test_params.voltage_range', {'min': 2.0, 'max': 5.0}),
                    'auto_detect': self.config_manager.get('test.auto_detect', True),
                    'retry_count': self.config_manager.get('test.retry_count', 2),
                    'count_limit_enabled': self.config_manager.get('test.count_limit_enabled', False),
                    'max_count': self.config_manager.get('test.max_count', 100),
                    # 修复添加启用通道配置
                    'enabled_channels': self.config_manager.get('test.enabled_channels', [1, 2, 3, 4, 5, 6, 7, 8]),
                    # 并行错频模式配置
                    'use_parallel_staggered_mode': self.config_manager.get('test.use_parallel_staggered_mode', False),
                    'critical_frequency': self.config_manager.get('test.critical_frequency', 10.0),
                    'timeout_seconds': self.config_manager.get('test.timeout_seconds', 120),
                    'status_check_interval': self.config_manager.get('test.status_check_interval', 0.2),
                    'max_retries': self.config_manager.get('test.max_retries', 3),
                    'error_recovery': self.config_manager.get('test.error_recovery', True),
                }

                # 修复确保测试模式配置一致性
                config = self._ensure_test_mode_consistency(config)

                # 验证配置
                validated_config = self._validate_test_config(config)

                # 缓存配置
                self._test_config_cache = validated_config

                logger.info(f"测试配置加载完成: {validated_config}")
                return validated_config

        except Exception as e:
            logger.error(f"加载测试配置失败: {e}")
            return self._get_default_test_config()

    def _get_validated_resistance_range(self) -> str:
        """
        获取电阻档位配置（直接读取，不进行自动修复）

        Returns:
            电阻档位字符串
        """
        try:
            # 直接读取resistance_range配置，不进行自动修复
            resistance_range = self.config_manager.get('test_params.resistance_range', '5R')
            
            return resistance_range

        except Exception as e:
            logger.error(f"读取电阻档位配置失败: {e}")
            return '5R'  # 默认返回5R档位

    def load_communication_config(self) -> Dict:
        """
        加载通信配置

        Returns:
            通信配置字典
        """
        try:
            with self.config_lock:
                device_config = self.config_manager.get('device.connection', {})

                config = {
                    'type': device_config.get('type', 'modbus_rtu'),
                    'port': device_config.get('port', 'COM16'),
                    'baudrate': int(device_config.get('baudrate', 115200)),
                    'device_address': int(device_config.get('device_address', 1)),
                    'timeout': float(device_config.get('timeout', 2.0)),
                    'retry_count': int(device_config.get('retry_count', 3)),
                    'retry_delay': float(device_config.get('retry_delay', 0.1)),
                    'health_check_interval': float(device_config.get('health_check_interval', 15.0)),
                    'max_consecutive_failures': int(device_config.get('max_consecutive_failures', 8))
                }

                # 验证配置
                validated_config = self._validate_communication_config(config)

                # 缓存配置
                self._comm_config_cache = validated_config

                logger.info(f"通信配置加载完成: {validated_config}")
                return validated_config

        except Exception as e:
            logger.error(f"加载通信配置失败: {e}")
            return self._get_default_communication_config()

    def update_test_config(self, updates: Dict) -> bool:
        """
        更新测试配置

        Args:
            updates: 配置更新字典

        Returns:
            是否更新成功
        """
        try:
            with self.config_lock:
                # 验证更新数据
                validated_updates = self._validate_config_updates(updates)

                # 应用更新到基础配置管理器
                for key, value in validated_updates.items():
                    config_key = self._map_config_key(key)
                    if config_key:
                        self.config_manager.set(config_key, value)
                        logger.debug(f"配置更新: {config_key} = {value}")

                # 清除缓存，强制重新加载
                self._test_config_cache = None

                # 通知配置变更
                self._notify_config_change('test_config', validated_updates)

                logger.info(f"测试配置更新成功: {validated_updates}")
                return True

        except Exception as e:
            logger.error(f"更新测试配置失败: {e}")
            return False

    def update_communication_config(self, updates: Dict) -> bool:
        """
        更新通信配置

        Args:
            updates: 配置更新字典

        Returns:
            是否更新成功
        """
        try:
            with self.config_lock:
                # 验证更新数据
                validated_updates = self._validate_communication_updates(updates)

                # 应用更新到基础配置管理器
                for key, value in validated_updates.items():
                    config_key = f"device.connection.{key}"
                    self.config_manager.set(config_key, value)
                    logger.debug(f"通信配置更新: {config_key} = {value}")

                # 清除缓存，强制重新加载
                self._comm_config_cache = None

                # 通知配置变更
                self._notify_config_change('communication_config', validated_updates)

                logger.info(f"通信配置更新成功: {validated_updates}")
                return True

        except Exception as e:
            logger.error(f"更新通信配置失败: {e}")
            return False

    def get_cached_test_config(self) -> Optional[Dict]:
        """
        获取缓存的测试配置

        Returns:
            缓存的测试配置或None
        """
        return self._test_config_cache

    def get_cached_communication_config(self) -> Optional[Dict]:
        """
        获取缓存的通信配置

        Returns:
            缓存的通信配置或None
        """
        return self._comm_config_cache

    def reload_all_configs(self) -> Dict:
        """
        重新加载所有配置

        Returns:
            包含所有配置的字典
        """
        try:
            with self.config_lock:
                # 清除缓存
                self._test_config_cache = None
                self._comm_config_cache = None

                # 重新加载
                test_config = self.load_test_config()
                comm_config = self.load_communication_config()

                configs = {
                    'test_config': test_config,
                    'communication_config': comm_config
                }

                # 通知配置变更
                self._notify_config_change('all_configs', configs)

                logger.info("所有配置重新加载完成")
                return configs

        except Exception as e:
            logger.error(f"重新加载所有配置失败: {e}")
            return {}

    def validate_config(self, config_type: str, config: Dict) -> bool:
        """
        验证配置

        Args:
            config_type: 配置类型 ('test' 或 'communication')
            config: 配置字典

        Returns:
            是否验证通过
        """
        try:
            if config_type == 'test':
                self._validate_test_config(config)
            elif config_type == 'communication':
                self._validate_communication_config(config)
            else:
                logger.error(f"未知的配置类型: {config_type}")
                return False

            return True

        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False

    def get_default_config(self, config_type: str) -> Dict:
        """
        获取默认配置

        Args:
            config_type: 配置类型

        Returns:
            默认配置字典
        """
        if config_type == 'test':
            return self._get_default_test_config()
        elif config_type == 'communication':
            return self._get_default_communication_config()
        else:
            logger.error(f"未知的配置类型: {config_type}")
            return {}

    def reset_to_default(self, config_type: str) -> bool:
        """
        重置为默认配置

        Args:
            config_type: 配置类型

        Returns:
            是否重置成功
        """
        try:
            default_config = self.get_default_config(config_type)

            if config_type == 'test':
                return self.update_test_config(default_config)
            elif config_type == 'communication':
                return self.update_communication_config(default_config)
            else:
                return False

        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            return False

    def _sort_frequencies(self, frequencies: List[float], order: str) -> List[float]:
        """
        根据指定顺序排序频率列表

        Args:
            frequencies: 频率列表
            order: 排序顺序 ('high_to_low' 或 'low_to_high')

        Returns:
            排序后的频率列表
        """
        try:
            sorted_frequencies = sorted(frequencies)

            if order == 'high_to_low':
                return sorted(sorted_frequencies, reverse=True)
            elif order == 'low_to_high':
                return sorted_frequencies
            else:
                logger.warning(f"未知的频率顺序设置: {order}，使用默认顺序（高频到低频）")
                return sorted(sorted_frequencies, reverse=True)

        except Exception as e:
            logger.error(f"频率排序失败: {e}")
            return frequencies

    def _validate_test_config(self, config: Dict) -> Dict:
        """
        验证测试配置

        Args:
            config: 测试配置

        Returns:
            验证后的配置
        """
        validated = config.copy()

        # 使用ConfigValidator进行验证
        if 'frequencies' in validated:
            validated['frequencies'] = ConfigValidator.validate_frequency_list(
                validated['frequencies'], "测试频率列表"
            )

        if 'gain' in validated:
            validated['gain'] = ConfigValidator.validate_gain(
                validated['gain'], "增益设置"
            )

        if 'average_times' in validated:
            validated['average_times'] = ConfigValidator.validate_average_times(
                validated['average_times'], "平均次数"
            )

        if 'resistance_range' in validated:
            validated['resistance_range'] = ConfigValidator.validate_resistance_range(
                validated['resistance_range'], "电阻档位"
            )

        if 'timeout' in validated:
            validated['timeout'] = ConfigValidator.validate_test_timeout(
                validated['timeout'], "测试超时时间"
            )

        # 验证其他数值参数
        if 'interval' in validated:
            validated['interval'] = ConfigValidator.validate_numeric_range(
                validated['interval'], 0.1, 60.0, 2.0, "连续测试间隔"
            )

        if 'retry_count' in validated:
            validated['retry_count'] = ConfigValidator.validate_integer_range(
                validated['retry_count'], 0, 10, 2, "重试次数"
            )

        if 'max_count' in validated:
            validated['max_count'] = ConfigValidator.validate_integer_range(
                validated['max_count'], 1, 10000, 100, "最大测试次数"
            )

        return validated

    def _ensure_test_mode_consistency(self, config: Dict) -> Dict:
        """
        确保测试模式配置一致性

        Args:
            config: 测试配置

        Returns:
            修正后的配置
        """
        try:
            # 获取当前的测试模式配置
            test_mode = self.config_manager.get('test_params.test_mode', 'simultaneous')
            use_parallel_staggered = config.get('use_parallel_staggered_mode', False)

            # 检查配置一致性并修正
            if test_mode == 'simultaneous' and use_parallel_staggered:
                # 同时测试模式但启用了并行错频，修正为禁用并行错频
                logger.warning("🔧 检测到配置不一致：同时测试模式但启用了并行错频，自动修正为禁用并行错频")
                config['use_parallel_staggered_mode'] = False
                # 同步更新到配置管理器
                self.config_manager.set('test.use_parallel_staggered_mode', False)

            elif test_mode == 'staggered' and not use_parallel_staggered:
                # 增强测试模式但禁用了并行错频，修正为启用并行错频
                logger.warning("🔧 检测到配置不一致：增强测试模式但禁用了并行错频，自动修正为启用并行错频")
                config['use_parallel_staggered_mode'] = True
                # 同步更新到配置管理器
                self.config_manager.set('test.use_parallel_staggered_mode', True)

            elif test_mode == 'sequential' and use_parallel_staggered:
                # 传统模式但启用了并行错频，修正为禁用并行错频
                logger.warning("🔧 检测到配置不一致：传统模式但启用了并行错频，自动修正为禁用并行错频")
                config['use_parallel_staggered_mode'] = False
                # 同步更新到配置管理器
                self.config_manager.set('test.use_parallel_staggered_mode', False)

            logger.debug(f"测试模式一致性检查完成: test_mode={test_mode}, use_parallel_staggered_mode={config.get('use_parallel_staggered_mode')}")
            return config

        except Exception as e:
            logger.error(f"测试模式一致性检查失败: {e}")
            return config

    def _validate_communication_config(self, config: Dict) -> Dict:
        """
        验证通信配置

        Args:
            config: 通信配置

        Returns:
            验证后的配置
        """
        validated = config.copy()

        # 使用ConfigValidator进行验证
        if 'baudrate' in validated:
            validated['baudrate'] = ConfigValidator.validate_baudrate(
                validated['baudrate'], "通信波特率"
            )

        if 'device_address' in validated:
            validated['device_address'] = ConfigValidator.validate_device_address(
                validated['device_address'], "设备地址"
            )

        if 'timeout' in validated:
            validated['timeout'] = ConfigValidator.validate_timeout(
                validated['timeout'], "通信超时时间"
            )

        # 验证其他通信参数
        if 'retry_count' in validated:
            validated['retry_count'] = ConfigValidator.validate_integer_range(
                validated['retry_count'], 0, 10, 3, "通信重试次数"
            )

        if 'retry_delay' in validated:
            validated['retry_delay'] = ConfigValidator.validate_numeric_range(
                validated['retry_delay'], 0.01, 5.0, 0.1, "重试延迟时间"
            )

        if 'health_check_interval' in validated:
            validated['health_check_interval'] = ConfigValidator.validate_numeric_range(
                validated['health_check_interval'], 1.0, 300.0, 15.0, "健康检查间隔"
            )

        if 'max_consecutive_failures' in validated:
            validated['max_consecutive_failures'] = ConfigValidator.validate_integer_range(
                validated['max_consecutive_failures'], 1, 50, 8, "最大连续失败次数"
            )

        return validated

    def _validate_config_updates(self, updates: Dict) -> Dict:
        """
        验证配置更新

        Args:
            updates: 配置更新字典

        Returns:
            验证后的更新字典
        """
        # 使用ConfigValidationRules进行验证
        return ConfigValidationRules.validate_config_dict(
            updates, ConfigValidationRules.TEST_CONFIG_RULES
        )

    def _validate_communication_updates(self, updates: Dict) -> Dict:
        """
        验证通信配置更新

        Args:
            updates: 通信配置更新字典

        Returns:
            验证后的更新字典
        """
        # 使用ConfigValidationRules进行验证
        return ConfigValidationRules.validate_config_dict(
            updates, ConfigValidationRules.COMMUNICATION_CONFIG_RULES
        )

    def _map_config_key(self, key: str) -> Optional[str]:
        """
        映射配置键名到基础配置管理器的键名

        Args:
            key: 配置键名

        Returns:
            映射后的键名或None
        """
        key_mapping = {
            'test_mode': 'frequency.preset_mode',
            'frequencies': 'frequency.custom_list',
            'frequency_order': 'frequency.frequency_order',
            'continuous_mode': 'test.continuous_mode',
            'interval': 'test.interval',
            'timeout': 'test.timeout',
            'gain': 'test_params.gain',
            'average_times': 'test_params.average_times',
            'resistance_range': 'test_params.resistance_range',
            'voltage_range': 'test_params.voltage_range',
            'auto_detect': 'test.auto_detect',
            'retry_count': 'test.retry_count',
            'count_limit_enabled': 'test.count_limit_enabled',
            'max_count': 'test.max_count',
            # 添加并行错频模式配置映射
            'use_parallel_staggered_mode': 'test.use_parallel_staggered_mode',
            'critical_frequency': 'test.critical_frequency',
            'timeout_seconds': 'test.timeout_seconds',
            'status_check_interval': 'test.status_check_interval',
            'max_retries': 'test.max_retries',
            'error_recovery': 'test.error_recovery',
        }
        return key_mapping.get(key)

    def _notify_config_change(self, config_type: str, changes: Dict):
        """
        通知配置变更

        Args:
            config_type: 配置类型
            changes: 变更内容
        """
        if self.config_change_callback:
            try:
                self.config_change_callback(config_type, changes)
            except Exception as e:
                logger.error(f"配置变更回调失败: {e}")

    def _init_default_configs(self) -> Dict:
        """初始化默认配置"""
        return {
            'test_config': {
                'test_mode': 'research',
                'frequencies': [1000.0],
                'frequency_order': 'high_to_low',
                'is_single_mode': False,
                'continuous_mode': False,
                'interval': 2,
                'timeout': 60,
                'gain': '1',
                'average_times': 1,
                'resistance_range': '10R',
                'voltage_range': {'min': 2.0, 'max': 5.0},
                'auto_detect': True,
                'retry_count': 2,
                'count_limit_enabled': False,
                'max_count': 100,
            },
            'communication_config': {
                'type': 'modbus_rtu',
                'port': 'COM16',
                'baudrate': 115200,
                'device_address': 1,
                'timeout': 2.0,
                'retry_count': 3,
                'retry_delay': 0.1,
                'health_check_interval': 15.0,
                'max_consecutive_failures': 8
            }
        }

    def _get_default_test_config(self) -> Dict:
        """获取默认测试配置"""
        return self._default_configs['test_config'].copy()

    def _get_default_communication_config(self) -> Dict:
        """获取默认通信配置"""
        return self._default_configs['communication_config'].copy()

    def set_config_change_callback(self, callback: Callable):
        """设置配置变更回调函数"""
        self.config_change_callback = callback
        logger.debug("配置变更回调函数已设置")

    def get(self, key: str, default=None):
        """
        获取配置值（兼容性方法）

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        return self.config_manager.get(key, default)

    def get_test_config(self) -> Dict:
        """
        获取测试配置（兼容性方法）

        Returns:
            测试配置字典
        """
        if self._test_config_cache is None:
            return self.load_test_config()
        return self._test_config_cache.copy()

    def get_enabled_channels(self) -> List[int]:
        """
        获取启用的通道列表

        Returns:
            启用的通道列表
        """
        try:
            # 从配置获取启用的通道
            enabled_channels = self.config_manager.get('test.enabled_channels', [1, 2, 3, 4, 5, 6, 7, 8])

            # 确保返回有效的通道列表
            if not enabled_channels:
                logger.warning("配置中没有启用的通道，使用默认通道1-8")
                enabled_channels = [1, 2, 3, 4, 5, 6, 7, 8]

            # 验证通道号范围
            valid_channels = []
            for channel in enabled_channels:
                if isinstance(channel, int) and 1 <= channel <= 8:
                    valid_channels.append(channel)
                else:
                    logger.warning(f"无效的通道号: {channel}")

            if not valid_channels:
                logger.warning("没有有效的通道，使用默认通道1-8")
                valid_channels = [1, 2, 3, 4, 5, 6, 7, 8]

            logger.debug(f"启用的通道: {valid_channels}")
            return valid_channels

        except Exception as e:
            logger.error(f"获取启用通道失败: {e}")
            return [1, 2, 3, 4, 5, 6, 7, 8]  # 默认返回所有通道

    def get_config(self) -> Dict:
        """
        获取配置（兼容性方法）

        Returns:
            测试配置字典
        """
        return self.get_test_config()
