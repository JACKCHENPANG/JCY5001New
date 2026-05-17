# -*- coding: utf-8 -*-
"""
配置管理器
负责应用程序配置的读取、保存和验证

Author: Jack
Date: 2025-01-27
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal

# 获取日志记录器（不重复配置）
logger = logging.getLogger(__name__)


class ConfigManager(QObject):
    """配置管理器类"""

    # 修复添加配置变更信号
    config_changed = pyqtSignal(str, object)  # 配置键, 新值

    def __init__(self, config_dir: str = "config"):
        """
        初始化配置管理器

        Args:
            config_dir: 配置文件目录
        """
        super().__init__()  # 修复初始化QObject

        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "app_config.json")
        self.default_config_file = os.path.join(config_dir, "default_config.yaml")

        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)

        # 加载配置
        self._config = self._load_config()

        # 🐛 修复：添加数据库管理器引用，供UI组件使用
        self.database_manager = None
        self._init_database_manager()

    def _init_database_manager(self):
        """初始化数据库管理器"""
        try:
            from data.database_manager import DatabaseManager
            self.database_manager = DatabaseManager()
            logger.debug("✅ [配置管理器] 数据库管理器初始化成功")
        except Exception as e:
            logger.error(f"❌ [配置管理器] 数据库管理器初始化失败: {e}")
            self.database_manager = None

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            # 应用程序基本信息
            "app": {
                "name": "JCY5001A鲸测云8路EIS阻抗筛选仪",
                "version": "V0.92.42",
                "trial_days": 30,
                "start_date": None,
                "show_startup_license_dialog": False  # 修复默认禁用启动时授权提醒弹窗，改善客户体验
            },

            # 界面配置
            "ui": {
                "theme": "light",  # light/dark
                "language": "zh_CN",
                "window_size": [1280, 800],
                "window_position": [100, 100],
                "auto_save_layout": True
            },

            # 批次信息配置
            "batch_info": {
                "batch_number": "",
                "operator": "",
                "cell_type": "磷酸铁锂",  # 磷酸铁锂/三元锂
                "cell_spec": "21700",
                "standard_voltage": 3.2,
                "standard_capacity": 3000,
                "standard_capacity_unit": "mAh",
                "new_resistance": 6.0,  # mΩ
                "eol_resistance": 12.0  # mΩ
            },

            # 测试参数配置
            "test_params": {
                "test_mode": "simultaneous",  # 测试模式：simultaneous(同时测试)/staggered(并行错频)
                "gain": "auto",  # 1/4/16/auto
                "average_times": 1,
                "battery_range": "10mΩ以下",  # 1mΩ以下/10mΩ以下/100mΩ以下
                "resistance_range": "10R",  # 电阻档位：1R/5R/10R
                "voltage_range": {
                    "min": 2.0,
                    "max": 5.0
                }
            },

            # 频率设置
            "frequency": {
                "mode": "multi",  # 多频点模式
                "list": [0.119, 1, 10, 100, 1000],  # 主要频率列表
                "multi_freq": {
                    "preset": "磷酸铁锂",
                    "custom_list": [0.119, 1, 10, 100, 1000],
                    "min_freq": 0.01,
                    "max_freq": 7800,
                    "points": 20,
                    "distribution": "log"  # log/linear
                },
                "preset_mode": "生产模式",
                "frequency_order": "high_to_low"
            },

            # 测试配置
            "test": {
                "continuous_mode": False,           # 连续自动测试模式
                "continuous_mode_delay": 2.0,      # 连续测试间隔（秒）
                "auto_detect": False,               # 电池自动侦测模式（已屏蔽）
                "data_optimization": True,
                "optimization_delay": 0.5,         # 秒
                "enabled_channels": [1, 2, 3, 4, 5, 6, 7, 8],  # 启用的通道列表
                "battery_coding": {
                    "mode": "scan",  # scan/auto_generate
                    "length_check": True,
                    "expected_length": 12,
                    "auto_rule": "BATCH_{batch}_{index:04d}"
                },
                "label_print": {
                    "enabled": False,
                    "code_type": "qr"  # qr/barcode
                }
            },

            # 电池自动侦测配置
            "battery_detection": {
                "enabled": True,
                "voltage_threshold_remove": 5.0,    # 电池移除阈值（V）
                "voltage_threshold_min": 2.0,       # 电池插入最小阈值（V）
                "voltage_threshold_max": 5.0,       # 电池插入最大阈值（V）
                "detection_interval": 1.0,          # 侦测间隔（秒）
                "stable_count_required": 3,         # 状态稳定所需的连续检测次数
                "auto_restart_delay": 2.0           # 自动重启测试延迟（秒）
            },

            # 设备设置
            "device": {
                "connection": {
                    "port": "COM1",
                    "baudrate": 115200,
                    "timeout": 1.0
                },
                "channels": 8,
                "printer": {
                    "name": "",
                    "connected": False
                },
                # 扫码枪配置
                "barcode_scanner": {
                    "enabled": False,  # 是否启用扫码枪
                    "serial_length_min": 8,  # 序列号最小长度
                    "serial_length_max": 20,  # 序列号最大长度
                    "format_validation": True,  # 是否启用格式验证
                    "allowed_chars": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",  # 允许的字符
                    "uniqueness_check": True,  # 是否检查唯一性
                    "auto_generation": {
                        "enabled": True,  # 是否启用自动生成
                        "prefix": "BAT",  # 前缀
                        "date_format": "YYYYMMDD",  # 日期格式
                        "sequence_digits": 4,  # 流水号位数
                        "separator": "-"  # 分隔符
                    }
                }
            },

            # 档位设置
            "grade_settings": {
                "rs_grades": 3,
                "rct_grades": 3,
                "rs_boundaries": [5.0, 10.0],  # mΩ
                "rct_boundaries": [8.0, 15.0],  # mΩ
                "rs_min": 0.1,
                "rs_max": 50.0,
                "rct_min": 0.1,
                "rct_max": 100.0,
                "rsei_min": 0.0,
                "rsei_max": 10.0,
                "voltage_min": 2.0,
                "voltage_max": 5.0
            },

            # 数据库配置
            "database": {
                "path": "data/test_results.db",
                "backup_enabled": True,
                "backup_interval": 24  # 小时
            },

            # 优化打印机配置，提升打印质量
            "printer": {
                "type": "热敏打印机",
                "name": "",
                "connection": "USB",
                "quality": "高质量",  # 从草稿改为高质量
                "density": "high",   # 高浓度
                "contrast": "high"   # 高对比度
            },

            # 优化标签打印配置
            "label_print": {
                "auto_print": True,
                "print_pass_only": False,
                "copies": 1,
                "quality": "高质量",  # 高质量打印
                "font_enhancement": True,  # 字体增强
                "bold_enhancement": True   # 粗体增强
            },

            # 优化日志配置 - 生产环境优化
            "logging": {
                "enable_system_log": True,
                "level": "INFO",      # 优化默认INFO级别，减少日志量
            },

            # 新增通信配置
            "communication": {
                "enable_logging": False,  # 通信日志开关
                "protocol": "Modbus RTU",
                "baudrate": "115200",
                "timeout": 1.0
            },

            # 🚫 存储管理配置已删除
        }

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            # 如果配置文件存在，加载它
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"配置文件加载成功: {self.config_file}")

                # 合并默认配置（确保新增的配置项存在）
                default_config = self._get_default_config()
                merged_config = self._merge_config(default_config, config)
                return merged_config
            else:
                # 使用默认配置
                logger.info("使用默认配置")
                default_config = self._get_default_config()
                self.save_config(default_config)
                return default_config

        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            logger.info("使用默认配置")
            return self._get_default_config()

    def _merge_config(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置，确保所有默认配置项都存在"""
        result = default.copy()

        for key, value in user.items():
            if key in result:
                if isinstance(value, dict) and isinstance(result[key], dict):
                    result[key] = self._merge_config(result[key], value)
                else:
                    result[key] = value
            else:
                result[key] = value

        return result

    def _remove_duplicate_frequencies(self, frequencies: list) -> list:
        """
        去除重复的频率点

        Args:
            frequencies: 原始频率列表

        Returns:
            去重后的频率列表（按从高到低排序）
        """
        try:
            if not frequencies:
                return []

            # 使用set去重，然后转换为列表并排序
            unique_frequencies = list(set(frequencies))
            # 按从高到低排序
            unique_frequencies.sort(reverse=True)

            removed_count = len(frequencies) - len(unique_frequencies)
            if removed_count > 0:
                logger.info(f"配置管理器频率去重: 原始{len(frequencies)}个频点，去重后{len(unique_frequencies)}个频点，移除{removed_count}个重复频点")

            return unique_frequencies

        except Exception as e:
            logger.error(f"频率去重失败: {e}")
            return frequencies

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键，支持点号分隔的嵌套键，如 'ui.theme'
            default: 默认值

        Returns:
            配置值
        """
        try:
            keys = key.split('.')
            value = self._config

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default

            return value
        except Exception as e:
            logger.error(f"获取配置失败: {key}, {e}")
            return default

    def set(self, key: str, value: Any, emit_signal: bool = True) -> bool:
        """
        设置配置值

        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
            emit_signal: 是否发送配置变更信号

        Returns:
            是否设置成功
        """
        try:
            # 对频率列表进行特殊处理（自动去重）
            if key == 'frequency.list' and isinstance(value, list):
                value = self._remove_duplicate_frequencies(value)

            # 修复检查值是否真的发生了变化
            old_value = self.get(key)
            if old_value == value:
                logger.debug(f"配置值未变化，跳过更新: {key}")
                return True

            keys = key.split('.')
            config = self._config

            # 导航到目标位置
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]

            # 设置值
            config[keys[-1]] = value
            
            # 优化对于序列号列表，只记录数量而不是详细内容
            if key == 'serial_numbers.used_list' and isinstance(value, list):
                logger.debug(f"🔧 配置已更新: {key} = [列表，{len(value)}项]")
            else:
                # 对于其他配置，正常记录
                if isinstance(value, (str, int, float, bool)) or len(str(value)) < 100:
                    logger.debug(f"🔧 配置已更新: {key} = {value}")
                else:
                    logger.debug(f"🔧 配置已更新: {key} = [复杂对象，长度{len(str(value))}]")

            # 修复发送配置变更信号
            if emit_signal:
                self.config_changed.emit(key, value)
                logger.debug(f"✅ 配置变更信号已发送: {key}")

            return True

        except Exception as e:
            logger.error(f"❌ 设置配置失败: {key}, {e}")
            return False

    def save_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """保存配置到文件"""
        try:
            config_to_save = config if config is not None else self._config

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, ensure_ascii=False, indent=2)

            logger.info(f"配置文件保存成功: {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"配置文件保存失败: {e}")
            return False

    def reload_config(self) -> bool:
        """从文件重新加载配置（丢弃当前内存中的修改）"""
        try:
            self._config = self._load_config()
            logger.info(f"配置文件重新加载成功: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"配置文件重新加载失败: {e}")
            return False

    def validate_config(self) -> bool:
        """验证配置的有效性"""
        try:
            # 验证必要的配置项
            required_keys = [
                'app.name',
                'device.channels',
                'test_params.gain'
            ]

            for key in required_keys:
                if self.get(key) is None:
                    logger.error(f"缺少必要配置项: {key}")
                    return False

            # 验证数值范围
            channels = self.get('device.channels', 8)
            if not isinstance(channels, int) or channels <= 0:
                logger.error(f"通道数配置无效: {channels}")
                return False

            return True

        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False

    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        try:
            self._config = self._get_default_config()
            return self.save_config()
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            return False

    @property
    def config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self._config.copy()
