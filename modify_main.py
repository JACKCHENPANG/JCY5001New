# Auto-detect integration script 
import sys 
content = open("main.py", "r", encoding="utf-8").read() 
old_text = "startup_optimizer.start_stage(\"窗口显示\")" 
update_splash_message(splash, "正在自动识别设备...") 
try: 
    from backend.device_detector import DeviceDetector 
    from backend.serial_connection_manager import SerialConnectionManager 
    detector = DeviceDetector() 
    detected = detector.auto_detect() 
    if detected: 
        port, device_info = detected 
        if hasattr(main_window, "comm_manager") and main_window.comm_manager: 
            connection_manager = SerialConnectionManager(main_window.comm_manager) 
            connection_manager.connect_device(port) 
except Exception as e: 
    logger.error(f"自动识别失败: {e}") 
content = content.replace(old_text, new_text) 
open("main.py", "w", encoding="utf-8").write(content) 
