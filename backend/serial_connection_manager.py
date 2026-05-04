# -*- coding: utf-8 -*-
"""
ӹ
𴮿ӵĽάȹ

CommunicationManagerȡӹܣѭһְԭ

Author: Jack
Date: 2025-01-30
"""

import serial
import time
import threading
import logging
from typing import Dict, Any, Optional, Callable
from .device_detector import DeviceDetector

logger = logging.getLogger(__name__)


class SerialConnectionManager:
    """
    ӹ
    
    ְ
    - ӽͶϿ
    - ״̬
    - ӽ
    - Իƹ
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        ʼӹ
        
        Args:
            config: ֵ
        """
        self.config = config
        self.connection = None
        self.is_connected = False
        
        # ãŻ
        self.port = config.get('port', 'COM16')  # ޸ʹȷĬ϶˿
        self.baudrate = config.get('baudrate', 115200)
        self.timeout = config.get('timeout', 1.5)  # DNB1101 1.05s周期  # Żʱʱ

        # Ż
        self.write_timeout = config.get('write_timeout', 0.3)  # д볬ʱ
        self.inter_byte_timeout = config.get('inter_byte_timeout', 0.05)  # ֽڼ䳬ʱ
        self.read_buffer_size = config.get('read_buffer_size', 4096)  # ȡ
        self.fast_response_timeout = config.get('fast_response_timeout', 0.8)  # Ӧʱ

        # ͨ
        self.comm_lock = threading.Lock()

        # ص
        self.status_callback = None

        # ӽãŻ
        self.retry_count = config.get('retry_count', 2)  # Դ
        self.retry_delay = config.get('retry_delay', 0.05)  # ʱ
        self.health_check_interval = config.get('health_check_interval', 30.0)  # ӽ
        self.last_health_check = 0
        self.consecutive_failures = 0
        self.max_consecutive_failures = config.get('max_consecutive_failures', 5)  # ʧܴ
        
        logger.debug(f"ӹʼ: {self.port}, {self.baudrate}")
        
        # 自动识别配置
        self.auto_detect = config.get('auto_detect', True)
        self.config_manager = None  # 外部注入配置管理器
    
    def set_status_callback(self, callback: Callable[[bool], None]):
        """
        ״̬ص
        
        Args:
            callback: ״̬ص
        """
        self.status_callback = callback
    
    def connect(self) -> bool:
        """
        
        
        Returns:
            Ƿӳɹ
        """
        try:
            logger.info(f"Ӵ: {self.port}")
            
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

            # Żȶȴʱ
            time.sleep(0.05)  # ٵȴʱ

            # ջ
            self.connection.reset_input_buffer()
            self.connection.reset_output_buffer()
            
            self.is_connected = True
            self.consecutive_failures = 0
            self._notify_status(True)
            
            logger.info(f"ӳɹ: {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"ʧ: {e}")
            self.is_connected = False
            self._notify_status(False)
            return False
    
    def disconnect(self):
        """Ͽ"""
        try:
            self.is_connected = False

            if self.connection:
                try:
                    # ջ
                    if self.connection.is_open:
                        self.connection.reset_input_buffer()
                        self.connection.reset_output_buffer()

                    # ر
                    self.connection.close()

                    # ȴ˿ȫͷ
                    import time
                    time.sleep(0.1)

                except Exception as close_error:
                    logger.warning(f"رմʱ־: {close_error}")
                finally:
                    self.connection = None

            self._notify_status(False)
            logger.info("ѶϿ")

        except Exception as e:
            logger.error(f"Ͽʧ: {e}")
            # ǿӶ
            self.connection = None
    
    def is_connection_alive(self) -> bool:
        """
        Ƿ
        
        Returns:
            Ƿ
        """
        try:
            if not self.connection or not self.is_connected:
                return False
            
            # 鴮ǷȻ
            return self.connection.is_open
            
        except Exception as e:
            logger.error(f"״̬ʧ: {e}")
            return False
    
    def send_data(self, data: bytes) -> bool:
        """
        
        
        Args:
            data: Ҫ͵
            
        Returns:
            Ƿͳɹ
        """
        try:
            if not self.is_connection_alive():
                logger.error("δ޷")
                return False
            
            with self.comm_lock:
                # սջ
                self.connection.reset_input_buffer()
                
                # 
                self.connection.write(data)
                self.connection.flush()
                
                logger.debug(f"ѷ: {' '.join([f'{b:02X}' for b in data])}")
                return True
                
        except Exception as e:
            logger.error(f"ʧ: {e}")
            self._handle_communication_failure(f"ʧ: {e}")
            return False
    
    def receive_data(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """
        
        
        Args:
            timeout: ճʱʱ䣨룩
            
        Returns:
            յ
        """
        try:
            if not self.is_connection_alive():
                logger.error("δ޷")
                return None
            
            if timeout is None:
                timeout = self.timeout
            
            response = bytearray()
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.connection.in_waiting > 0:
                    data = self.connection.read(self.connection.in_waiting)
                    response.extend(data)
                    logger.debug(f"յ: {' '.join([f'{b:02X}' for b in data])}")
                    
                    # ݣȴһСʱ俴Ƿи
                    if len(response) > 0:
                        time.sleep(0.01)
                        if self.connection.in_waiting == 0:
                            break
                
                time.sleep(0.005)
            
            if len(response) > 0:
                logger.debug(f"ɣܳ: {len(response)}")
                return bytes(response)
            else:
                logger.debug("δյ")
                return None
                
        except Exception as e:
            logger.error(f"ʧ: {e}")
            self._handle_communication_failure(f"ʧ: {e}")
            return None
    
    def send_and_receive(self, data: bytes, timeout: Optional[float] = None) -> Optional[bytes]:
        """
        ݲӦ

        Args:
            data: Ҫ͵
            timeout: ճʱʱ

        Returns:
            յӦ
        """
        try:
            if not self.is_connection_alive():
                logger.error("δ޷")
                return None

            with self.comm_lock:
                # սջ
                self.connection.reset_input_buffer()

                # 
                self.connection.write(data)
                self.connection.flush()

                logger.debug(f"ѷ: {' '.join([f'{b:02X}' for b in data])}")

                # ȴһСʱ豸
                time.sleep(0.02)

                # Ӧ
                if timeout is None:
                    timeout = self.timeout

                response = bytearray()
                start_time = time.time()

                while time.time() - start_time < timeout:
                    if self.connection.in_waiting > 0:
                        data_received = self.connection.read(self.connection.in_waiting)
                        response.extend(data_received)
                        logger.debug(f"յ: {' '.join([f'{b:02X}' for b in data_received])}")

                        # ݣȴһСʱ俴Ƿи
                        if len(response) > 0:
                            time.sleep(0.01)
                            if self.connection.in_waiting == 0:
                                break

                    time.sleep(0.005)

                if len(response) > 0:
                    logger.debug(f"ɣܳ: {len(response)}")
                    self.reset_failure_count()
                    return bytes(response)
                else:
                    logger.debug("δյ")
                    return None

        except Exception as e:
            logger.error(f"Ͳʧ: {e}")
            self._handle_communication_failure(f"Ͳʧ: {e}")
            return None
    
    def perform_health_check(self) -> bool:
        """
        ִӽ
        
        Returns:
            Ƿ񽡿
        """
        try:
            current_time = time.time()
            
            # ǷҪн
            if current_time - self.last_health_check < self.health_check_interval:
                return self.is_connected
            
            self.last_health_check = current_time
            
            # ״̬
            if not self.is_connection_alive():
                logger.warning("ʧܣѶϿ")
                self._handle_connection_lost()
                return False
            
            logger.debug("ӽͨ")
            return True
            
        except Exception as e:
            logger.error(f"ʧ: {e}")
            self._handle_connection_lost()
            return False
    
    def _handle_communication_failure(self, error_msg: str):
        """
        ͨʧ
        
        Args:
            error_msg: Ϣ
        """
        self.consecutive_failures += 1
        logger.warning(f"ͨʧ ({self.consecutive_failures}/{self.max_consecutive_failures}): {error_msg}")
        
        if self.consecutive_failures >= self.max_consecutive_failures:
            logger.error("ͨʧܴ࣬ΪϿ״̬")
            self._handle_connection_lost()
    
    def _handle_connection_lost(self):
        """Ӷʧ"""
        try:
            self.is_connected = False
            self._notify_status(False)
            
            if self.connection:
                self.connection.close()
                self.connection = None
            
            logger.warning("Ѷʧ")
            
        except Exception as e:
            logger.error(f"Ӷʧʧ: {e}")
    
    def _notify_status(self, connected: bool):
        """
        ֪ͨ״̬
        
        Args:
            connected: Ƿ
        """
        try:
            if self.status_callback:
                self.status_callback(connected)
        except Exception as e:
            logger.error(f"״̬صʧ: {e}")
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        ȡϢ

        Returns:
            Ϣֵ
        """
        # ȡʵӵĴں
        actual_port = self.get_actual_port()

        return {
            'port': actual_port,  # ʵӵĴں
            'configured_port': self.port,  # еĴں
            'baudrate': self.baudrate,
            'timeout': self.timeout,
            'is_connected': self.is_connected,
            'consecutive_failures': self.consecutive_failures,
            'max_consecutive_failures': self.max_consecutive_failures,
            'last_health_check': self.last_health_check
        }

    def get_actual_port(self) -> str:
        """
        ȡʵӵĴں

        Returns:
            ʵӵĴںţδ򷵻еĴں
        """
        try:
            if self.is_connected and self.connection and hasattr(self.connection, 'port'):
                # ʵʵĴڶȡں
                actual_port = self.connection.port
                logger.debug(f"ȡʵӴ: {actual_port} (ô: {self.port})")
                return actual_port
            else:
                # δʱеĴں
                return self.port
        except Exception as e:
            logger.debug(f"ȡʵʴںʧ: {e}ô: {self.port}")
            return self.port
    
    def reset_failure_count(self):
        """ʧܼ"""
        self.consecutive_failures = 0
        logger.debug("ͨʧܼ")
    
    def get_retry_config(self) -> Dict[str, Any]:
        """
        ȡ
        
        Returns:
            ֵ
        """
        return {
            'retry_count': self.retry_count,
            'retry_delay': self.retry_delay,
            'health_check_interval': self.health_check_interval
        }
    
    def update_retry_config(self, config: Dict[str, Any]):
        """
        
        
        Args:
            config: µ
        """
        if 'retry_count' in config:
            self.retry_count = config['retry_count']
        if 'retry_delay' in config:
            self.retry_delay = config['retry_delay']
        if 'health_check_interval' in config:
            self.health_check_interval = config['health_check_interval']
        if 'max_consecutive_failures' in config:
            self.max_consecutive_failures = config['max_consecutive_failures']
        
        logger.info(f"Ѹ: {config}")
    
    def get_lock(self):
        """ȡͨⲿͬ"""
        return self.comm_lock

    def auto_detect_device(self) -> tuple:
        """自动识别设备"""
        try:
            logger.info("开始自动识别设备...")
            detector = DeviceDetector(baudrate=self.baudrate, timeout=self.timeout)
            port = detector.detect_device()
            if port:
                self.port = port
                logger.info(f"设备识别成功: {port}")
                if self.config_manager:
                    self.config_manager.set('device.connection.port', port)
                    self.config_manager.save_config()
                return port, True
            return None, False
        except Exception as e:
            logger.error(f"自动识别失败: {e}")
            return None, False

    def connect_with_auto_detect(self) -> bool:
        """连接设备，支持自动识别"""
        # 先尝试直接连接
        if self.port and self.port not in ['AUTO', '']:
            result = self.connect()
            if result:
                return True
            # 连接失败，尝试自动识别其他端口
            if self.auto_detect:
                logger.info(f"端口 {self.port} 连接失败，尝试自动识别...")
                port, success = self.auto_detect_device()
                if success:
                    return self.connect()
        else:
            # 端口未配置，直接自动识别
            port, success = self.auto_detect_device()
            if success:
                return self.connect()
        
        return False

    def set_config_manager(self, config_manager):
        """设置配置管理器"""
        self.config_manager = config_manager
