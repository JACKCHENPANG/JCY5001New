# -*- coding: utf-8 -*-
"""
串口连接管理器
负责串口连接的建立、维护、健康检查等功能

从CommunicationManager中提取的连接管理功能，遵循单一职责原则

Author: Jack
Date: 2025-01-30
"""

import serial
import time
import threading
import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class SerialConnectionManager:
    """
    串口连接管理器
    
    职责：
    - 串口连接建立和断开
    - 连接状态监控
    - 连接健康检查
    - 重试机制管理
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化串口连接管理器
        
        Args:
            config: 连接配置字典
        """
        self.config = config
        self.connection = None
        self.is_connected = False
        
        # 串口配置（性能优化）
        self.port = config.get('port', 'COM16')  # 修复使用正确的默认端口
        self.baudrate = config.get('baudrate', 115200)
        self.timeout = config.get('timeout', 1.0)  # 优化超时时间

        # 性能优化参数
        self.write_timeout = config.get('write_timeout', 0.3)  # 写入超时
        self.inter_byte_timeout = config.get('inter_byte_timeout', 0.05)  # 字节间超时
        self.read_buffer_size = config.get('read_buffer_size', 4096)  # 读取缓冲区
        self.fast_response_timeout = config.get('fast_response_timeout', 0.8)  # 快速响应超时

        # 通信锁
        self.comm_lock = threading.Lock()

        # 回调函数
        self.status_callback = None

        # 连接健康检查配置（优化）
        self.retry_count = config.get('retry_count', 2)  # 减少重试次数
        self.retry_delay = config.get('retry_delay', 0.05)  # 减少重试延时
        self.health_check_interval = config.get('health_check_interval', 30.0)  # 增加健康检查间隔
        self.last_health_check = 0
        self.consecutive_failures = 0
        self.max_consecutive_failures = config.get('max_consecutive_failures', 5)  # 减少最大失败次数
        
        logger.debug(f"串口连接管理器初始化完成: {self.port}, {self.baudrate}")
    
    def set_status_callback(self, callback: Callable[[bool], None]):
        """
        设置状态回调函数
        
        Args:
            callback: 状态变更回调函数
        """
        self.status_callback = callback
    
    def connect(self) -> bool:
        """
        建立串口连接
        
        Returns:
            是否连接成功
        """
        try:
            logger.info(f"尝试连接串口: {self.port}")
            
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                write_timeout=self.write_timeout,
                inter_byte_timeout=self.inter_byte_timeout
            )

            # 优化串口稳定等待时间
            time.sleep(0.05)  # 减少等待时间

            # 清空缓冲区
            self.connection.reset_input_buffer()
            self.connection.reset_output_buffer()
            
            self.is_connected = True
            self.consecutive_failures = 0
            self._notify_status(True)
            
            logger.info(f"串口连接成功: {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"串口连接失败: {e}")
            self.is_connected = False
            self._notify_status(False)
            return False
    
    def disconnect(self):
        """断开串口连接"""
        try:
            self.is_connected = False

            if self.connection:
                try:
                    # 清空缓冲区
                    if self.connection.is_open:
                        self.connection.reset_input_buffer()
                        self.connection.reset_output_buffer()

                    # 关闭连接
                    self.connection.close()

                    # 等待端口完全释放
                    import time
                    time.sleep(0.1)

                except Exception as close_error:
                    logger.warning(f"关闭串口时出现警告: {close_error}")
                finally:
                    self.connection = None

            self._notify_status(False)
            logger.info("串口连接已断开")

        except Exception as e:
            logger.error(f"断开串口连接失败: {e}")
            # 强制清理连接对象
            self.connection = None
    
    def is_connection_alive(self) -> bool:
        """
        检查连接是否存活
        
        Returns:
            连接是否存活
        """
        try:
            if not self.connection or not self.is_connected:
                return False
            
            # 检查串口是否仍然打开
            return self.connection.is_open
            
        except Exception as e:
            logger.error(f"检查连接状态失败: {e}")
            return False
    
    def send_data(self, data: bytes) -> bool:
        """
        发送数据
        
        Args:
            data: 要发送的数据
            
        Returns:
            是否发送成功
        """
        try:
            if not self.is_connection_alive():
                logger.error("连接未建立，无法发送数据")
                return False
            
            with self.comm_lock:
                # 清空接收缓冲区
                self.connection.reset_input_buffer()
                
                # 发送数据
                self.connection.write(data)
                self.connection.flush()
                
                logger.debug(f"数据已发送: {' '.join([f'{b:02X}' for b in data])}")
                return True
                
        except Exception as e:
            logger.error(f"发送数据失败: {e}")
            self._handle_communication_failure(f"发送失败: {e}")
            return False
    
    def receive_data(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """
        接收数据
        
        Args:
            timeout: 接收超时时间（秒）
            
        Returns:
            接收到的数据
        """
        try:
            if not self.is_connection_alive():
                logger.error("连接未建立，无法接收数据")
                return None
            
            if timeout is None:
                timeout = self.timeout
            
            response = bytearray()
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.connection.in_waiting > 0:
                    data = self.connection.read(self.connection.in_waiting)
                    response.extend(data)
                    logger.debug(f"接收到数据: {' '.join([f'{b:02X}' for b in data])}")
                    
                    # 如果有数据，继续等待一小段时间看是否还有更多数据
                    if len(response) > 0:
                        time.sleep(0.01)
                        if self.connection.in_waiting == 0:
                            break
                
                time.sleep(0.005)
            
            if len(response) > 0:
                logger.debug(f"接收完成，总长度: {len(response)}")
                return bytes(response)
            else:
                logger.debug("未接收到数据")
                return None
                
        except Exception as e:
            logger.error(f"接收数据失败: {e}")
            self._handle_communication_failure(f"接收失败: {e}")
            return None
    
    def send_and_receive(self, data: bytes, timeout: Optional[float] = None) -> Optional[bytes]:
        """
        发送数据并接收响应

        Args:
            data: 要发送的数据
            timeout: 接收超时时间

        Returns:
            接收到的响应数据
        """
        try:
            if not self.is_connection_alive():
                logger.error("连接未建立，无法发送数据")
                return None

            with self.comm_lock:
                # 清空接收缓冲区
                self.connection.reset_input_buffer()

                # 发送数据
                self.connection.write(data)
                self.connection.flush()

                logger.debug(f"数据已发送: {' '.join([f'{b:02X}' for b in data])}")

                # 等待一小段时间让设备处理
                time.sleep(0.02)

                # 接收响应
                if timeout is None:
                    timeout = self.timeout

                response = bytearray()
                start_time = time.time()

                while time.time() - start_time < timeout:
                    if self.connection.in_waiting > 0:
                        data_received = self.connection.read(self.connection.in_waiting)
                        response.extend(data_received)
                        logger.debug(f"接收到数据: {' '.join([f'{b:02X}' for b in data_received])}")

                        # 如果有数据，继续等待一小段时间看是否还有更多数据
                        if len(response) > 0:
                            time.sleep(0.01)
                            if self.connection.in_waiting == 0:
                                break

                    time.sleep(0.005)

                if len(response) > 0:
                    logger.debug(f"接收完成，总长度: {len(response)}")
                    self.reset_failure_count()
                    return bytes(response)
                else:
                    logger.debug("未接收到数据")
                    return None

        except Exception as e:
            logger.error(f"发送并接收数据失败: {e}")
            self._handle_communication_failure(f"发送并接收失败: {e}")
            return None
    
    def perform_health_check(self) -> bool:
        """
        执行连接健康检查
        
        Returns:
            连接是否健康
        """
        try:
            current_time = time.time()
            
            # 检查是否需要进行健康检查
            if current_time - self.last_health_check < self.health_check_interval:
                return self.is_connected
            
            self.last_health_check = current_time
            
            # 检查连接状态
            if not self.is_connection_alive():
                logger.warning("健康检查失败：连接已断开")
                self._handle_connection_lost()
                return False
            
            logger.debug("连接健康检查通过")
            return True
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            self._handle_connection_lost()
            return False
    
    def _handle_communication_failure(self, error_msg: str):
        """
        处理通信失败
        
        Args:
            error_msg: 错误消息
        """
        self.consecutive_failures += 1
        logger.warning(f"通信失败 ({self.consecutive_failures}/{self.max_consecutive_failures}): {error_msg}")
        
        if self.consecutive_failures >= self.max_consecutive_failures:
            logger.error("连续通信失败次数过多，标记连接为断开状态")
            self._handle_connection_lost()
    
    def _handle_connection_lost(self):
        """处理连接丢失"""
        try:
            self.is_connected = False
            self._notify_status(False)
            
            if self.connection:
                self.connection.close()
                self.connection = None
            
            logger.warning("连接已丢失")
            
        except Exception as e:
            logger.error(f"处理连接丢失失败: {e}")
    
    def _notify_status(self, connected: bool):
        """
        通知状态变更
        
        Args:
            connected: 是否已连接
        """
        try:
            if self.status_callback:
                self.status_callback(connected)
        except Exception as e:
            logger.error(f"状态回调失败: {e}")
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        获取连接信息

        Returns:
            连接信息字典
        """
        # 获取实际连接的串口号
        actual_port = self.get_actual_port()

        return {
            'port': actual_port,  # 返回实际连接的串口号
            'configured_port': self.port,  # 配置中的串口号
            'baudrate': self.baudrate,
            'timeout': self.timeout,
            'is_connected': self.is_connected,
            'consecutive_failures': self.consecutive_failures,
            'max_consecutive_failures': self.max_consecutive_failures,
            'last_health_check': self.last_health_check
        }

    def get_actual_port(self) -> str:
        """
        获取实际连接的串口号

        Returns:
            实际连接的串口号，如果未连接则返回配置中的串口号
        """
        try:
            if self.is_connected and self.connection and hasattr(self.connection, 'port'):
                # 从实际的串口对象获取串口号
                actual_port = self.connection.port
                logger.debug(f"获取实际连接串口: {actual_port} (配置串口: {self.port})")
                return actual_port
            else:
                # 未连接时返回配置中的串口号
                return self.port
        except Exception as e:
            logger.debug(f"获取实际串口号失败: {e}，返回配置串口: {self.port}")
            return self.port
    
    def reset_failure_count(self):
        """重置失败计数"""
        self.consecutive_failures = 0
        logger.debug("通信失败计数已重置")
    
    def get_retry_config(self) -> Dict[str, Any]:
        """
        获取重试配置
        
        Returns:
            重试配置字典
        """
        return {
            'retry_count': self.retry_count,
            'retry_delay': self.retry_delay,
            'health_check_interval': self.health_check_interval
        }
    
    def update_retry_config(self, config: Dict[str, Any]):
        """
        更新重试配置
        
        Args:
            config: 新的重试配置
        """
        if 'retry_count' in config:
            self.retry_count = config['retry_count']
        if 'retry_delay' in config:
            self.retry_delay = config['retry_delay']
        if 'health_check_interval' in config:
            self.health_check_interval = config['health_check_interval']
        if 'max_consecutive_failures' in config:
            self.max_consecutive_failures = config['max_consecutive_failures']
        
        logger.info(f"重试配置已更新: {config}")
    
    def get_lock(self):
        """获取通信锁（用于外部同步）"""
        return self.comm_lock
