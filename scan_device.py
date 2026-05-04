
import serial
import serial.tools.list_ports
import time

def scan_jcy5001_device():
    """扫描并识别 JCY5001AS 设备"""
    print("=== 扫描可用串口 ===")
    ports = list(serial.tools.list_ports.comports())
    print(f"找到 {len(ports)} 个串口")
    
    for port_info in ports:
        port = port_info.device
        desc = port_info.description
        print(f"
尝试端口: {port} ({desc})")
        
        try:
            # 尝试连接
            ser = serial.Serial(port, 115200, timeout=1)
            time.sleep(0.1)
            
            # 发送识别命令（查询设备ID）
            # JCY5001AS 的识别命令
            cmd = b'*IDN?\n'  # 标准SCPI识别命令
            ser.write(cmd)
            time.sleep(0.2)
            
            # 读取回复
            response = ser.read(100)
            if response:
                print(f"  收到回复: {response}")
                if b'JCY5001' in response or b'JCY' in response:
                    print(f"  ✅ 找到 JCY5001 设备: {port}")
                    ser.close()
                    return port
            else:
                print(f"  无回复")
            
            ser.close()
        except Exception as e:
            print(f"  错误: {e}")
    
    print("
未找到 JCY5001 设备")
    return None

if __name__ == "__main__":
    device_port = scan_jcy5001_device()
    if device_port:
        print(f"\n设备端口: {device_port}")
