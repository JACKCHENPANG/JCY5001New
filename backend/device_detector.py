"""
设备自动识别模块
自动扫描串口并识别 JCY5001AS 设备（Modbus RTU 协议）
"""
import serial
import serial.tools.list_ports
import time
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class DeviceDetector:
    """JCY5001AS 设备自动识别器（Modbus RTU）"""

    # 设备识别信息
    DEVICE_NAME = "JCY5001"

    # Modbus 设备地址
    DEFAULT_DEVICE_ADDRESS = 1

    # 默认连接参数
    DEFAULT_BAUDRATE = 115200
    DEFAULT_TIMEOUT = 2.0

    def __init__(self, baudrate: int = None, timeout: float = None, device_address: int = None):
        self.baudrate = baudrate or self.DEFAULT_BAUDRATE
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.device_address = device_address or self.DEFAULT_DEVICE_ADDRESS

    @staticmethod
    def calculate_crc16(data: bytes) -> int:
        """计算 Modbus CRC16 校验码"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def build_modbus_read_command(self, start_address: int, count: int) -> bytes:
        """
        构建 Modbus 读取命令

        Args:
            start_address: 起始地址
            count: 寄存器数量

        Returns:
            Modbus 命令字节
        """
        # 构建基本命令
        cmd = bytearray([
            self.device_address,
            0x04,  # 读输入寄存器
            (start_address >> 8) & 0xFF,
            start_address & 0xFF,
            (count >> 8) & 0xFF,
            count & 0xFF
        ])

        # 计算并添加 CRC
        crc = self.calculate_crc16(cmd)
        cmd.extend([crc & 0xFF, (crc >> 8) & 0xFF])

        return bytes(cmd)

    def get_available_ports(self) -> List[str]:
        """
        获取所有可用串口
        优先返回 USB 串口
        """
        try:
            ports = list(serial.tools.list_ports.comports())
            logger.info(f"扫描到 {len(ports)} 个串口")

            # 分类：USB 端口优先
            usb_ports = []
            other_ports = []

            for port_info in ports:
                port = port_info.device
                desc = port_info.description.upper()

                # USB 串口优先级最高
                if 'USB' in desc or 'USB' in port.upper():
                    usb_ports.append(port)
                    logger.debug(f"  USB 端口: {port} - {port_info.description}")
                # 排除系统保留端口（COM1）
                elif port != 'COM1':
                    other_ports.append(port)
                    logger.debug(f"  其他端口: {port} - {port_info.description}")

            # USB 端口优先
            result = usb_ports + other_ports
            logger.info(f"可用端口: {result}")
            return result

        except Exception as e:
            logger.error(f"扫描串口失败: {e}")
            return []

    def test_port(self, port: str) -> Tuple[bool, Optional[bytes]]:
        """
        测试指定端口是否是 JCY5001 设备（使用 Modbus 协议）

        Returns:
            (is_device, response): 是否是设备, 设备响应
        """
        try:
            logger.info(f"测试端口: {port}")

            # 打开串口
            ser = serial.Serial(
                port=port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=1
            )

            # 等待稳定
            time.sleep(0.2)

            # 清空缓冲区
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            # 尝试读取通道数寄存器（地址 0x3E00）
            # 这是设备应该响应的基本查询
            cmd = self.build_modbus_read_command(0x3E00, 1)
            logger.debug(f"  发送 Modbus 命令: {cmd.hex()}")

            # 发送命令
            ser.write(cmd)

            # 等待响应
            time.sleep(0.5)

            # 读取响应
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                logger.debug(f"  收到响应: {response.hex()}")

                # 验证响应格式
                # Modbus 正常响应: [地址, 功能码, 字节数, 数据..., CRC低, CRC高]
                if len(response) >= 5:
                    # 检查是否是正常响应（功能码 0x04）
                    if response[0] == self.device_address and response[1] == 0x04:
                        byte_count = response[2]
                        if len(response) >= 3 + byte_count + 2:
                            # 解析通道数
                            data = response[3:3+byte_count]
                            if byte_count >= 2:
                                channel_count = (data[0] << 8) | data[1]
                                logger.info(f"✅ 找到 JCY5001 设备: {port}, 通道数: {channel_count}")
                                ser.close()
                                return True, response

                    # 检查是否是异常响应（功能码 0x84）
                    elif response[1] == 0x84:
                        logger.debug(f"  设备返回异常响应，但设备存在: 异常码={response[2]}")
                        # 异常响应也说明设备存在，只是寄存器地址可能不对
                        ser.close()
                        return True, response

            # 没有收到有效响应
            ser.close()
            logger.debug(f"  不是目标设备")
            return False, None

        except serial.SerialException as e:
            logger.debug(f"  连接失败: {e}")
            return False, None
        except Exception as e:
            logger.debug(f"  测试异常: {e}")
            return False, None

    def detect_device(self, exclude_ports: List[str] = None) -> Optional[str]:
        """
        自动识别 JCY5001 设备

        Args:
            exclude_ports: 要排除的端口列表

        Returns:
            设备端口号，未找到返回 None
        """
        logger.info("🔍 开始自动识别 JCY5001 设备...")

        exclude_ports = exclude_ports or []

        # 获取可用端口
        ports = self.get_available_ports()

        if not ports:
            logger.warning("未找到任何可用串口")
            return None

        # 测试每个端口
        for port in ports:
            # 跳过排除的端口
            if port in exclude_ports:
                logger.debug(f"跳过端口: {port}")
                continue

            # 测试端口
            is_device, response = self.test_port(port)

            if is_device:
                logger.info(f"✅ 设备识别成功: {port}")
                return port

        logger.warning("❌ 未找到 JCY5001 设备")
        return None

    def auto_connect(self, config_manager=None) -> Tuple[Optional[str], bool]:
        """
        自动识别并连接设备

        Args:
            config_manager: 配置管理器实例（用于保存端口配置）

        Returns:
            (port, success): 设备端口, 是否成功
        """
        # 1. 尝试从配置文件读取上次成功的端口
        if config_manager:
            last_port = config_manager.get('device.connection.last_port')
            if last_port:
                logger.info(f"尝试上次成功的端口: {last_port}")
                is_device, _ = self.test_port(last_port)
                if is_device:
                    logger.info(f"✅ 使用上次端口成功: {last_port}")
                    return last_port, True

        # 2. 自动扫描识别
        port = self.detect_device()

        if port:
            # 保存到配置
            if config_manager:
                try:
                    config_manager.set('device.connection.port', port)
                    config_manager.set('device.connection.last_port', port)
                    config_manager.save_config()
                    logger.info(f"✅ 已保存端口配置: {port}")
                except Exception as e:
                    logger.warning(f"保存配置失败: {e}")

            return port, True

        return None, False


def quick_detect() -> Optional[str]:
    """
    快速识别设备（简化接口）

    Returns:
        设备端口号，未找到返回 None
    """
    detector = DeviceDetector()
    return detector.detect_device()


if __name__ == "__main__":
    # 测试代码
    import sys

    print("=" * 60)
    print("JCY5001 设备自动识别测试")
    print("=" * 60)

    detector = DeviceDetector()
    port = detector.detect_device()

    if port:
        print(f"\n✅ 设备识别成功!")
        print(f"端口: {port}")
        print("=" * 60)
    else:
        print(f"\n❌ 未找到设备")
        print("=" * 60)

    sys.exit(0 if port else 1)
