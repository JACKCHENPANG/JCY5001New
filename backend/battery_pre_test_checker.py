"""
电池测试前检测器
负责在测试启动前检测电池连接状态，优化测试时间
增强版：添加阻抗响应能力检测，识别接触不良通道
"""

import logging
import time
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class BatteryPreTestChecker:
    """电池测试前检测器（增强版）"""

    def __init__(self, device_config_manager, exception_manager, progress_callback: Optional[Callable] = None):
        """
        初始化电池测试前检测器

        Args:
            device_config_manager: 设备配置管理器
            exception_manager: 通道异常管理器
            progress_callback: 进度回调函数
        """
        self.device_config_manager = device_config_manager
        self.exception_manager = exception_manager
        self.progress_callback = progress_callback

        # 修复从配置文件读取电压范围，而不是使用硬编码值
        self._load_voltage_thresholds()
        self.voltage_check_timeout = 1.0  # 电压检查超时时间（秒）

        # 优化阻抗响应能力检测配置（已禁用以节省12秒）
        self.impedance_response_check_enabled = False  # 强制禁用阻抗响应检测，节省12秒
        self.fast_detection_mode = True  # 新增启用快速检测模式
        self.impedance_test_frequency = 1000.0  # 用于检测的测试频率（Hz）
        self.impedance_response_timeout = 3.0  # 阻抗响应超时时间（秒）
        self.max_status_check_attempts = 10  # 最大状态检查次数
        self.status_check_interval = 0.2  # 状态检查间隔（秒）

        # 检测结果缓存
        self.last_check_results = {}
        self.last_check_time = None

    def _load_voltage_thresholds(self):
        """设置电池检测的电压阈值（用于检测是否有电池）"""
        # Jack修正：电压不在2.0V-5.0V范围内认为是没有接电池，跳过测试
        # 这是电池连接检测，不是电压合格性判断
        self.voltage_min_threshold = 2.0  # 最小电压阈值（检测是否有电池）
        self.voltage_max_threshold = 5.0  # 最大电压阈值（超过5V认为没有接电池）

    def check_batteries_before_test(self, enabled_channels: List[int], force_check: bool = False) -> Dict[str, List[int]]:
        """
        测试前检查所有通道的电池连接状态（增强版）

        Args:
            enabled_channels: 启用的通道列表
            force_check: 是否强制重新检查（忽略缓存）

        Returns:
            检测结果字典：{
                'valid_channels': [有电池且响应正常的通道列表],
                'no_battery_channels': [无电池的通道列表],
                'error_channels': [检测失败的通道列表],
                'contact_poor_channels': [接触不良的通道列表]
            }
        """
        try:
            logger.info(f"🔋 开始增强版测试前电池检测，检查通道: {enabled_channels}")

            # 检查是否需要重新检测
            current_time = datetime.now()
            if not force_check and self.last_check_time and self.last_check_results:
                time_diff = (current_time - self.last_check_time).total_seconds()
                if time_diff < 5.0:  # 5秒内的检测结果可以复用
                    logger.debug("使用缓存的电池检测结果")
                    return self._filter_cached_results(enabled_channels)

            # 初始化结果
            results = {
                'valid_channels': [],
                'no_battery_channels': [],
                'error_channels': [],
                'contact_poor_channels': []  # 新增接触不良通道
            }

            # 逐个检查通道
            for channel_num in enabled_channels:
                check_result = self._check_single_channel_battery_enhanced(channel_num)

                if check_result['status'] == 'valid':
                    results['valid_channels'].append(channel_num)
                elif check_result['status'] == 'no_battery':
                    results['no_battery_channels'].append(channel_num)
                    self._mark_channel_as_no_battery(channel_num, check_result['reason'])
                elif check_result['status'] == 'contact_poor':
                    results['contact_poor_channels'].append(channel_num)
                    self._mark_channel_as_contact_poor(channel_num, check_result['reason'])
                else:  # error
                    results['error_channels'].append(channel_num)
                    self._mark_channel_as_error(channel_num, check_result['reason'])

            # 更新缓存
            self.last_check_results = results
            self.last_check_time = current_time

            # 记录检测结果
            detection_time = (datetime.now() - current_time).total_seconds()
            fast_mode = getattr(self, 'fast_detection_mode', True)
            time_saved = len(enabled_channels) * 1.5 if fast_mode else 0
            
            logger.info(f"🔋 增强版电池检测完成 ({'快速模式' if fast_mode else '完整模式'}):")
            logger.info(f"  ✅ 有效通道: {results['valid_channels']}")
            logger.info(f"  ❌ 无电池通道: {results['no_battery_channels']}")
            logger.info(f"  🔌 接触不良通道: {results['contact_poor_channels']}")
            logger.info(f"  ⚠️ 检测失败通道: {results['error_channels']}")
            logger.info(f"  ⏱️ 检测耗时: {detection_time:.2f}秒" + (f" (节省约{time_saved:.1f}秒)" if time_saved > 0 else ""))

            return results

        except Exception as e:
            logger.error(f"测试前电池检测失败: {e}")
            # 出错时返回所有通道为有效，避免阻塞测试
            return {
                'valid_channels': enabled_channels,
                'no_battery_channels': [],
                'error_channels': [],
                'contact_poor_channels': []
            }
    
    def _check_single_channel_battery_enhanced(self, channel_num: int) -> Dict[str, Any]:
        """
        增强版单通道电池状态检查（包含阻抗响应能力检测）

        Args:
            channel_num: 通道号

        Returns:
            检测结果：{'status': 'valid'|'no_battery'|'contact_poor'|'error', 'reason': '原因', 'voltage': 电压值}
        """
        try:
            # 第一步：电压检测
            voltage = self.device_config_manager.read_channel_voltage(channel_num)

            if voltage is None:
                return {
                    'status': 'error',
                    'reason': '电压读取失败',
                    'voltage': 0.0
                }

            # 检查电压范围
            if voltage < self.voltage_min_threshold:
                return {
                    'status': 'no_battery',
                    'reason': f'电压过低: {voltage:.3f}V',
                    'voltage': voltage
                }
            elif voltage > self.voltage_max_threshold:
                return {
                    'status': 'no_battery',
                    'reason': f'电压过高: {voltage:.3f}V',
                    'voltage': voltage
                }

            # 第二步：阻抗响应能力检测（已优化禁用，节省12秒）
            if self.impedance_response_check_enabled and not getattr(self, 'fast_detection_mode', True):
                # 优化在快速检测模式下跳过阻抗响应检测
                impedance_check_result = self._check_impedance_response_capability(channel_num, voltage)
                if impedance_check_result['status'] != 'valid':
                    return impedance_check_result
            else:
                logger.debug(f"🚀 通道{channel_num}跳过阻抗响应检测（快速模式）")

            # 所有检测都通过
            return {
                'status': 'valid',
                'reason': f'电压正常且响应正常: {voltage:.3f}V',
                'voltage': voltage
            }

        except Exception as e:
            return {
                'status': 'error',
                'reason': f'检测异常: {str(e)}',
                'voltage': 0.0
            }

    def _check_single_channel_battery(self, channel_num: int) -> Dict[str, Any]:
        """
        原版单通道电池状态检查（保持兼容性）

        Args:
            channel_num: 通道号

        Returns:
            检测结果：{'status': 'valid'|'no_battery'|'error', 'reason': '原因', 'voltage': 电压值}
        """
        try:
            # 读取通道电压
            voltage = self.device_config_manager.read_channel_voltage(channel_num)

            if voltage is None:
                return {
                    'status': 'error',
                    'reason': '电压读取失败',
                    'voltage': 0.0
                }

            # 检查电压范围
            if voltage < self.voltage_min_threshold:
                return {
                    'status': 'no_battery',
                    'reason': f'电压过低: {voltage:.3f}V',
                    'voltage': voltage
                }
            elif voltage > self.voltage_max_threshold:
                return {
                    'status': 'no_battery',
                    'reason': f'电压过高: {voltage:.3f}V',
                    'voltage': voltage
                }
            else:
                return {
                    'status': 'valid',
                    'reason': f'电压正常: {voltage:.3f}V',
                    'voltage': voltage
                }

        except Exception as e:
            return {
                'status': 'error',
                'reason': f'检测异常: {str(e)}',
                'voltage': 0.0
            }

    def _check_impedance_response_capability(self, channel_num: int, voltage: float) -> Dict[str, Any]:
        """
        检查通道的阻抗响应能力（识别接触不良）

        Args:
            channel_num: 通道号
            voltage: 已检测到的电压值

        Returns:
            检测结果：{'status': 'valid'|'contact_poor'|'error', 'reason': '原因', 'voltage': 电压值}
        """
        try:
            logger.debug(f"🔌 开始检查通道{channel_num}的阻抗响应能力")

            # 获取通信管理器
            comm_manager = getattr(self.device_config_manager, 'comm_manager', None)
            if not comm_manager:
                logger.warning(f"通道{channel_num}无法获取通信管理器，跳过阻抗响应检测")
                return {
                    'status': 'valid',
                    'reason': f'电压正常: {voltage:.3f}V (跳过阻抗检测)',
                    'voltage': voltage
                }

            # 转换为通道索引（0-7）
            channel_index = channel_num - 1

            # 第一步：检查通道状态码
            status_code = comm_manager.read_channel_status(channel_num)
            if status_code is None:
                return {
                    'status': 'error',
                    'reason': f'状态码读取失败: {voltage:.3f}V',
                    'voltage': voltage
                }

            # 检查是否为明显的异常状态码
            if status_code == 0x0003:  # 电池错误
                return {
                    'status': 'contact_poor',
                    'reason': f'状态码异常(0x{status_code:04X}): {voltage:.3f}V',
                    'voltage': voltage
                }

            # 第二步：快速阻抗响应测试
            response_result = self._perform_quick_impedance_response_test(channel_index, comm_manager)
            if not response_result['success']:
                return {
                    'status': 'contact_poor',
                    'reason': f'阻抗响应异常: {response_result["reason"]} ({voltage:.3f}V)',
                    'voltage': voltage
                }

            # 所有检测都通过
            logger.debug(f"✅ 通道{channel_num}阻抗响应能力正常")
            return {
                'status': 'valid',
                'reason': f'电压和阻抗响应正常: {voltage:.3f}V',
                'voltage': voltage
            }

        except Exception as e:
            logger.error(f"通道{channel_num}阻抗响应能力检测失败: {e}")
            return {
                'status': 'error',
                'reason': f'阻抗检测异常: {str(e)} ({voltage:.3f}V)',
                'voltage': voltage
            }

    def _perform_quick_impedance_response_test(self, channel_index: int, comm_manager) -> Dict[str, Any]:
        """
        执行快速阻抗响应测试

        Args:
            channel_index: 通道索引（0-7）
            comm_manager: 通信管理器

        Returns:
            测试结果：{'success': bool, 'reason': str}
        """
        try:
            # 设置测试频率
            if not comm_manager.set_frequency(self.impedance_test_frequency):
                return {'success': False, 'reason': '频率设置失败'}

            # 启动单通道测试
            if not comm_manager.start_single_channel_measurement(channel_index):
                return {'success': False, 'reason': '测试启动失败'}

            # 等待响应（快速检测）
            start_time = time.time()
            response_detected = False

            for attempt in range(self.max_status_check_attempts):
                if time.time() - start_time > self.impedance_response_timeout:
                    break

                status = comm_manager.get_measurement_status(channel_index)
                if status is not None:
                    if status == 0x0006:  # 测试完成
                        response_detected = True
                        break
                    elif status in [0x0003, 0x0004, 0x0005]:  # 异常状态
                        return {'success': False, 'reason': f'状态异常(0x{status:04X})'}

                time.sleep(self.status_check_interval)

            if not response_detected:
                return {'success': False, 'reason': '响应超时'}

            return {'success': True, 'reason': '响应正常'}

        except Exception as e:
            return {'success': False, 'reason': f'测试异常: {str(e)}'}

    def _filter_cached_results(self, enabled_channels: List[int]) -> Dict[str, List[int]]:
        """
        从缓存结果中筛选出当前启用通道的结果
        
        Args:
            enabled_channels: 启用的通道列表
            
        Returns:
            筛选后的结果
        """
        if not self.last_check_results:
            return {
                'valid_channels': enabled_channels,
                'no_battery_channels': [],
                'error_channels': []
            }
        
        return {
            'valid_channels': [ch for ch in enabled_channels if ch in self.last_check_results.get('valid_channels', [])],
            'no_battery_channels': [ch for ch in enabled_channels if ch in self.last_check_results.get('no_battery_channels', [])],
            'error_channels': [ch for ch in enabled_channels if ch in self.last_check_results.get('error_channels', [])],
            'contact_poor_channels': [ch for ch in enabled_channels if ch in self.last_check_results.get('contact_poor_channels', [])]
        }
    
    def _mark_channel_as_no_battery(self, channel_num: int, reason: str):
        """
        标记通道为无电池状态
        
        Args:
            channel_num: 通道号
            reason: 无电池的原因
        """
        try:
            from backend.channel_exception_manager import ChannelExceptionType, ChannelExceptionInfo
            
            exception_info = ChannelExceptionInfo(
                channel_number=channel_num,
                exception_type=ChannelExceptionType.BATTERY_ERROR,
                status_code=0x0003,  # 使用电池错误状态码
                error_message=f"无电池: {reason}",
                detection_time=datetime.now(),
                frequency_when_detected=None,
                should_skip=True
            )
            
            # 添加到异常管理器
            self.exception_manager.exception_channels[channel_num] = exception_info
            self.exception_manager.skipped_channels.add(channel_num)
            
            # 通知UI更新状态
            if self.progress_callback:
                self.progress_callback(channel_num, {
                    'state': 'no_battery',
                    'progress': 0,
                    'message': f'无电池: {reason}',
                    'exception_type': 'BATTERY_ERROR',
                    'error_message': f'无电池: {reason}',
                    'voltage': 0.0
                })
            
            logger.info(f"🚫 通道{channel_num}已标记为无电池: {reason}")
            
        except Exception as e:
            logger.error(f"标记通道{channel_num}无电池状态失败: {e}")

    def _mark_channel_as_contact_poor(self, channel_num: int, reason: str):
        """
        标记通道为接触不良状态

        Args:
            channel_num: 通道号
            reason: 接触不良的原因
        """
        try:
            from backend.channel_exception_manager import ChannelExceptionType, ChannelExceptionInfo

            exception_info = ChannelExceptionInfo(
                channel_number=channel_num,
                exception_type=ChannelExceptionType.HARDWARE_ERROR,  # 使用硬件错误类型
                status_code=0x0004,  # 使用设置错误状态码表示接触不良
                error_message=f"接触不良: {reason}",
                detection_time=datetime.now(),
                frequency_when_detected=None,
                should_skip=True
            )

            # 添加到异常管理器
            self.exception_manager.exception_channels[channel_num] = exception_info
            self.exception_manager.skipped_channels.add(channel_num)

            # 通知UI更新状态
            if self.progress_callback:
                self.progress_callback(channel_num, {
                    'state': 'contact_poor',
                    'progress': 0,
                    'message': f'接触不良: {reason}',
                    'exception_type': 'CONTACT_POOR',
                    'error_message': f'不合格-接触不良: {reason}',
                    'voltage': 0.0
                })

            logger.warning(f"🔌 通道{channel_num}已标记为接触不良: {reason}")

        except Exception as e:
            logger.error(f"标记通道{channel_num}接触不良状态失败: {e}")

    def _mark_channel_as_error(self, channel_num: int, reason: str):
        """
        标记通道为检测错误状态
        
        Args:
            channel_num: 通道号
            reason: 错误原因
        """
        try:
            from backend.channel_exception_manager import ChannelExceptionType, ChannelExceptionInfo
            
            exception_info = ChannelExceptionInfo(
                channel_number=channel_num,
                exception_type=ChannelExceptionType.HARDWARE_ERROR,
                status_code=0x0005,  # 使用硬件错误状态码
                error_message=f"检测失败: {reason}",
                detection_time=datetime.now(),
                frequency_when_detected=None,
                should_skip=True
            )
            
            # 添加到异常管理器
            self.exception_manager.exception_channels[channel_num] = exception_info
            self.exception_manager.skipped_channels.add(channel_num)
            
            # 通知UI更新状态
            if self.progress_callback:
                self.progress_callback(channel_num, {
                    'state': 'error',
                    'progress': 0,
                    'message': f'检测失败: {reason}',
                    'exception_type': 'HARDWARE_ERROR',
                    'error_message': f'检测失败: {reason}',
                    'voltage': 0.0
                })
            
            logger.warning(f"⚠️ 通道{channel_num}已标记为检测失败: {reason}")
            
        except Exception as e:
            logger.error(f"标记通道{channel_num}检测失败状态失败: {e}")
    
    def get_valid_channels_only(self, enabled_channels: List[int]) -> List[int]:
        """
        获取有电池连接且响应正常的有效通道列表

        Args:
            enabled_channels: 启用的通道列表

        Returns:
            有效通道列表（排除无电池、接触不良和错误通道）
        """
        results = self.check_batteries_before_test(enabled_channels)
        valid_channels = results['valid_channels']

        # 记录被排除的通道
        excluded_channels = {
            '无电池': results.get('no_battery_channels', []),
            '接触不良': results.get('contact_poor_channels', []),
            '检测失败': results.get('error_channels', [])
        }

        for reason, channels in excluded_channels.items():
            if channels:
                logger.info(f"🚫 排除{reason}通道: {channels}")

        return valid_channels
    
    def clear_cache(self):
        """清除检测结果缓存"""
        self.last_check_results = {}
        self.last_check_time = None
        logger.debug("电池检测缓存已清除")

    def configure_impedance_response_check(self, enabled: bool = True, test_frequency: float = 1000.0,
                                         timeout: float = 3.0, max_attempts: int = 10):
        """
        配置阻抗响应能力检测参数

        Args:
            enabled: 是否启用阻抗响应检测
            test_frequency: 测试频率（Hz）
            timeout: 响应超时时间（秒）
            max_attempts: 最大状态检查次数
        """
        self.impedance_response_check_enabled = enabled
        self.impedance_test_frequency = test_frequency
        self.impedance_response_timeout = timeout
        self.max_status_check_attempts = max_attempts



    def enable_fast_detection_mode(self, enabled: bool = True):
        """
        启用/禁用快速检测模式
        
        Args:
            enabled: 是否启用快速检测模式（跳过阻抗响应检测）
        """
        self.fast_detection_mode = enabled
        if enabled:
            self.impedance_response_check_enabled = False
            logger.info("🚀 已启用快速检测模式，跳过阻抗响应检测（节省约12秒）")
        else:
            logger.info("已禁用快速检测模式，恢复完整检测")

    def get_detection_time_estimate(self, channel_count: int) -> float:
        """
        估算检测时间
        
        Args:
            channel_count: 通道数量
            
        Returns:
            预估检测时间（秒）
        """
        if getattr(self, 'fast_detection_mode', True):
            # 快速模式：每通道约0.1秒
            return channel_count * 0.1
        else:
            # 完整模式：每通道约1.5秒（包含阻抗检测）
            return channel_count * 1.5

    def get_detection_statistics(self) -> Dict[str, Any]:
        """
        获取检测统计信息

        Returns:
            统计信息字典
        """
        if not self.last_check_results:
            return {'message': '暂无检测数据'}

        total_channels = sum(len(channels) for channels in self.last_check_results.values())

        return {
            'last_check_time': self.last_check_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_check_time else None,
            'total_checked': total_channels,
            'valid_channels': len(self.last_check_results.get('valid_channels', [])),
            'no_battery_channels': len(self.last_check_results.get('no_battery_channels', [])),
            'contact_poor_channels': len(self.last_check_results.get('contact_poor_channels', [])),
            'error_channels': len(self.last_check_results.get('error_channels', [])),
            'impedance_check_enabled': self.impedance_response_check_enabled
        }
