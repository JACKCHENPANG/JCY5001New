#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JCY5001 Remote API - 远程状态监控和控制API
运行在后台线程，和GUI主线程同步状态
支持远程查看状态、远程控制测试、参数配置、数据库访问

Author: Jack
Date: 2025-09-12
"""

import json
import time
import threading
from flask import Flask, jsonify, request
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)

# 全局状态存储，由GUI主线程更新
api_state = {
    "app_running": True,
    "connected_device": None,
    "is_testing": False,
    "current_test": None,
    "channels": [],
    "last_error": None,
    "statistics": {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0
    }
}

# 保存对主窗口的引用，用于远程控制
_main_window = None

def set_main_window(main_window):
    """设置主窗口引用，用于远程控制"""
    global _main_window
    _main_window = main_window
    logger.debug("MainWindow reference set for remote API")

def update_state(**kwargs):
    """更新API状态，由UI主线程调用"""
    global api_state
    api_state.update(kwargs)
    logger.debug(f"API state updated: {kwargs.keys()}")

def get_state():
    """获取当前状态"""
    state = api_state.copy()
    # 同步主窗口的实际测试状态
    if _main_window is not None:
        if hasattr(_main_window, 'is_testing'):
            state['is_testing'] = _main_window.is_testing
        # 同步连接状态 - 只有当真正连接时才报告端口
        state['connected_device'] = None
        if hasattr(_main_window, 'comm_manager') and _main_window.comm_manager:
            if hasattr(_main_window.comm_manager, 'is_connected') and _main_window.comm_manager.is_connected:
                state['connected_device'] = getattr(_main_window.comm_manager, 'port', None)
    return state

def _get_manager(name):
    """通过main_window获取管理器实例"""
    if _main_window is None:
        return None
    try:
        result = _main_window.get_manager(name)
        if result is not None:
            return result
    except Exception:
        pass
    return getattr(_main_window, name, None)

# ============ 状态监控 API ============

@app.route('/health', methods=['GET'])
def health_check():
    """轻量健康检查，不依赖主窗口或设备通信。"""
    return jsonify({
        "success": True,
        "status": "ok",
        "app_running": api_state.get("app_running", True),
        "api_ready": True,
        "has_main_window": _main_window is not None
    })

@app.route('/status', methods=['GET'])
@app.route('/api/status', methods=['GET'])
def get_status():
    """获取应用当前状态"""
    return jsonify({
        "success": True,
        "data": get_state()
    })

@app.route('/statistics', methods=['GET'])
def get_statistics():
    """获取测试统计信息"""
    return jsonify({
        "success": True,
        "data": api_state["statistics"]
    })

@app.route('/channels', methods=['GET'])
def get_channels():
    """获取所有通道状态"""
    return jsonify({
        "success": True,
        "data": api_state["channels"]
    })

# ============ 测试控制 API ============

@app.route('/start_test', methods=['POST'])
def start_test():
    """启动测试，参数: channel (可选, 默认为所有已启用通道)"""
    global _main_window
    try:
        if _main_window is None:
            return jsonify({"success": False, "error": "MainWindow not available"})
        current_state = get_state()
        if current_state.get("is_testing"):
            return jsonify({"success": False, "error": "Test already running"})

        data = request.get_json(silent=True) or {}
        channel = data.get('channel', None)

        # 优先通过测试控制组件信号进入既有GUI启动链路；Qt会跨线程排队投递到主线程
        control_widget = None
        if hasattr(_main_window, 'ui_component_manager') and _main_window.ui_component_manager:
            try:
                control_widget = _main_window.ui_component_manager.get_component('test_control')
            except Exception:
                control_widget = None

        start_triggered = False
        if control_widget is not None and hasattr(control_widget, 'start_test'):
            logger.info("Remote API: emitting test_control.start_test")
            control_widget.start_test.emit()
            start_triggered = True
            time.sleep(0.2)
            current_state = get_state()
            if not current_state.get("is_testing"):
                logger.warning("Remote API: start_test emit后状态未拉起，回退到_main_window._on_start_test()")
                _main_window._on_start_test()
        else:
            logger.warning("Remote API: test_control组件不可用，直接回退到_main_window._on_start_test()")
            _main_window._on_start_test()

        update_state(is_testing=True)
        logger.info(f"Test started via remote API (channel={channel}, triggered={start_triggered})")
        return jsonify({"success": True, "message": f"Test started (channel={channel})"})
    except Exception as e:
        logger.error(f"Failed to start test via API: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/stop_test', methods=['POST'])
def stop_test():
    """停止当前测试"""
    global _main_window
    try:
        if _main_window is None:
            return jsonify({"success": False, "error": "MainWindow not available"})
        current_state = get_state()
        if not current_state.get("is_testing"):
            return jsonify({"success": False, "error": "No test running"})

        # 优先通过测试控制组件信号进入既有GUI停止链路；Qt会跨线程排队投递到主线程
        control_widget = None
        if hasattr(_main_window, 'ui_component_manager') and _main_window.ui_component_manager:
            try:
                control_widget = _main_window.ui_component_manager.get_component('test_control')
            except Exception:
                control_widget = None

        if control_widget is not None and hasattr(control_widget, 'stop_test'):
            control_widget.stop_test.emit()
        else:
            # 回退：直接调用主窗口入口（兼容旧结构）
            _main_window._on_stop_test()
        update_state(is_testing=False)
        logger.info("Test stopped via remote API")
        return jsonify({"success": True, "message": "Test stopped"})
    except Exception as e:
        logger.error(f"Failed to stop test via API: {e}")
        return jsonify({"success": False, "error": str(e)})

# ============ 参数配置 API ============

@app.route('/config', methods=['GET'])
def get_all_config():
    """获取所有配置参数"""
    config_mgr = _get_manager('config_manager')
    if config_mgr is None:
        return jsonify({"success": False, "error": "ConfigManager not available"})
    try:
        cfg = config_mgr.config if hasattr(config_mgr, 'config') else {}
        return jsonify({"success": True, "data": cfg})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/config/<path:key>', methods=['GET'])
def get_config(key):
    """获取指定配置参数"""
    config_mgr = _get_manager('config_manager')
    if config_mgr is None:
        return jsonify({"success": False, "error": "ConfigManager not available"})
    try:
        value = config_mgr.get(key)
        return jsonify({"success": True, "key": key, "data": value})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/config', methods=['POST'])
def set_config():
    """设置配置参数
    Body: {"key": "xxx", "value": yyy} 或 {"updates": {"key1": val1, "key2": val2}}
    """
    config_mgr = _get_manager('config_manager')
    if config_mgr is None:
        return jsonify({"success": False, "error": "ConfigManager not available"})
    try:
        data = request.get_json(silent=True) or {}

        if 'updates' in data:
            base_key = data.get('key')
            updates = data['updates'] or {}
            for k, v in updates.items():
                target_key = f"{base_key}.{k}" if base_key else k
                config_mgr.set(target_key, v)
            config_mgr.save_config()
            updated_keys = [f"{base_key}.{k}" if base_key else k for k in updates.keys()]
            logger.info(f"Config updated via API: {updated_keys}")
            return jsonify({"success": True, "message": f"Updated {len(updates)} config items", "updated_keys": updated_keys})
        elif 'key' in data:
            config_mgr.set(data['key'], data.get('value'))
            config_mgr.save_config()
            logger.info(f"Config updated via API: {data['key']} = {data.get('value')}")
            return jsonify({"success": True, "message": f"Config {data['key']} updated", "updated_keys": [data['key']]})
        else:
            return jsonify({"success": False, "error": "Missing 'key' or 'updates' in request body"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============ 数据库/测试数据 API ============

@app.route('/test_results', methods=['GET'])
def get_test_results():
    """获取测试结果列表
    Query params: limit (默认20), offset (默认0), batch_id (可选)
    """
    db = _get_manager('database_manager')
    if db is None:
        return jsonify({"success": False, "error": "DatabaseManager not available"})
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        batch_id = request.args.get('batch_id', None, type=int)

        results = db.get_test_results(limit=limit, offset=offset, batch_id=batch_id)
        total = db.get_test_results_count(batch_id=batch_id)

        return jsonify({
            "success": True,
            "data": {
                "results": results,
                "total": total,
                "limit": limit,
                "offset": offset
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/test_results/<int:result_id>', methods=['GET'])
def get_test_result_detail(result_id):
    """获取单个测试结果详情"""
    db = _get_manager('database_manager')
    if db is None:
        return jsonify({"success": False, "error": "DatabaseManager not available"})
    try:
        results = db.get_test_results(limit=1, offset=0)
        detail = next((r for r in (results or []) if r.get('id') == result_id), None)
        if detail is None:
            return jsonify({"success": False, "error": "Test result not found"})

        # 获取阻抗详情
        impedance = db.get_impedance_details(result_id)

        return jsonify({
            "success": True,
            "data": {
                "result": detail,
                "impedance": impedance
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/test_results/<int:result_id>', methods=['DELETE'])
def delete_test_result(result_id):
    """删除测试结果"""
    db = _get_manager('database_manager')
    if db is None:
        return jsonify({"success": False, "error": "DatabaseManager not available"})
    try:
        db.delete_test_result(result_id)
        logger.info(f"Test result {result_id} deleted via API")
        return jsonify({"success": True, "message": f"Test result {result_id} deleted"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/batches', methods=['GET'])
def get_batches():
    """获取批次列表"""
    db = _get_manager('database_manager')
    if db is None:
        return jsonify({"success": False, "error": "DatabaseManager not available"})
    try:
        limit = request.args.get('limit', 20, type=int)
        batches = db.get_recent_batches(limit=limit)
        return jsonify({"success": True, "data": batches})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/database/info', methods=['GET'])
def get_database_info():
    """获取数据库信息"""
    db = _get_manager('database_manager')
    if db is None:
        return jsonify({"success": False, "error": "DatabaseManager not available"})
    try:
        info = db.get_database_info()
        return jsonify({"success": True, "data": info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/database/backup', methods=['POST'])
def backup_database():
    """备份数据库"""
    db = _get_manager('database_manager')
    if db is None:
        return jsonify({"success": False, "error": "DatabaseManager not available"})
    try:
        path = db.backup_database()
        logger.info(f"Database backup created via API: {path}")
        return jsonify({"success": True, "message": "Backup created", "path": path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============ 通道配置 API ============

@app.route('/channels/<int:channel_id>/config', methods=['GET'])
def get_channel_config(channel_id):
    """获取指定通道的配置"""
    config_mgr = _get_manager('config_manager')
    if config_mgr is None:
        return jsonify({"success": False, "error": "ConfigManager not available"})
    try:
        prefix = f"channel_{channel_id}"
        # 查找所有以 channel_X 开头的配置
        cfg = config_mgr.config if hasattr(config_mgr, 'config') else {}
        channel_cfg = {k.replace(f"{prefix}.", ""): v for k, v in cfg.items() if k.startswith(prefix)}
        return jsonify({"success": True, "channel": channel_id, "data": channel_cfg})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/channels/<int:channel_id>/config', methods=['POST'])
def set_channel_config(channel_id):
    """设置指定通道的配置"""
    config_mgr = _get_manager('config_manager')
    if config_mgr is None:
        return jsonify({"success": False, "error": "ConfigManager not available"})
    try:
        data = request.get_json(silent=True) or {}
        prefix = f"channel_{channel_id}"
        for k, v in data.items():
            config_mgr.set(f"{prefix}.{k}", v)
        config_mgr.save_config()
        logger.info(f"Channel {channel_id} config updated via API")
        return jsonify({"success": True, "message": f"Channel {channel_id} config updated"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============ 设备连接 API ============


# ============ 自动扫描串口 API ============
@app.route('/device/scan', methods=['GET'])
def scan_serial_ports():
    """自动扫描所有串口，尝试检测JCY5001设备"""
    results = []
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        logger.info(f"扫描到 {len(ports)} 个串口")
        
        for port in ports:
            port_name = port.device
            try:
                # 尝试连接并发送Modbus读命令
                ser = serial.Serial(port_name, baudrate=115200, timeout=1.0)
                time.sleep(0.1)
                
                # 发送Modbus读保持寄存器命令（设备地址1，起始地址0，读2个寄存器）
                # 01 03 00 00 00 02 CRC
                modbus_cmd = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x02, 0xC4, 0x0B])
                ser.write(modbus_cmd)
                
                resp = ser.read(200)
                ser.close()
                
                device_name = "未知设备"
                device_id = 0
                
                if len(resp) >= 9 and resp[0] == 0x01 and resp[1] == 0x03:
                    # 有效Modbus响应，读取设备信息
                    if len(resp) >= 15:
                        device_id = (resp[3] << 8) | resp[4]
                        device_name = "JCY5001AS"
                elif len(resp) > 0:
                    device_name = "未知响应设备"
                    
                results.append({
                    "port": port_name,
                    "description": port.description,
                    "vid": port.vid,
                    "pid": port.pid,
                    "serial_number": port.serial_number,
                    "connected": len(resp) > 0,
                    "device_name": device_name,
                    "device_id": device_id,
                    "response_hex": resp.hex() if resp else ""
                })
                
            except Exception as port_err:
                results.append({
                    "port": port_name,
                    "description": port.description,
                    "vid": port.vid,
                    "pid": port.pid,
                    "connected": False,
                    "error": str(port_err)[:50]
                })
        
        return jsonify({
            "success": True,
            "total_ports": len(ports),
            "available_devices": [r for r in results if r.get("connected")],
            "all_ports": results
        })
    except Exception as e:
        logger.error(f"串口扫描失败: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/device/connect', methods=['POST'])
def connect_device():
    """连接设备
    Body: {"port": "COM3"} (可选, 默认自动扫描)
    """
    device_mgr = _get_manager('device_connection_manager')
    if device_mgr is None:
        return jsonify({"success": False, "error": "DeviceConnectionManager not available"})
    try:
        data = request.get_json(silent=True) or {}
        port = data.get('port', None)
        if port:
            result = device_mgr.reconnect_with_new_port(port)
            connected_port = port if result else None
        else:
            result = device_mgr.auto_connect()
            connected_port = getattr(device_mgr, 'current_port', None) if result else None

        # 同步API状态，避免/status显示null导致误判
        if result:
            update_state(connected_device=connected_port or 'connected')

        return jsonify({"success": True, "message": "Device connected", "data": result, "port": connected_port})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/device/disconnect', methods=['POST'])
def disconnect_device():
    """断开设备连接"""
    device_mgr = _get_manager('device_connection_manager')
    if device_mgr is None:
        return jsonify({"success": False, "error": "DeviceConnectionManager not available"})
    try:
        device_mgr.disconnect_device()
        update_state(connected_device=None)
        logger.info("Device disconnected via API")
        return jsonify({"success": True, "message": "Device disconnected"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/battery_detection/stop', methods=['POST'])
def stop_battery_detection():
    """停止电池检测线程，并可选禁用配置"""
    if _main_window is None:
        return jsonify({"success": False, "error": "MainWindow not available"})
    try:
        data = request.get_json(silent=True) or {}
        disable = bool(data.get('disable', False))

        mgr = getattr(_main_window, 'battery_detection_manager', None)
        if mgr is not None:
            mgr.stop_detection()

        if disable and hasattr(_main_window, 'config_manager') and _main_window.config_manager:
            try:
                _main_window.config_manager.set('battery_detection.enabled', False)
                if hasattr(_main_window.config_manager, 'save_config'):
                    _main_window.config_manager.save_config()
            except Exception as cfg_e:
                logger.warning(f"Disable battery detection config failed: {cfg_e}")

        if hasattr(_main_window, '_battery_detection_active'):
            _main_window._battery_detection_active = False

        logger.info(f"Battery detection stopped via API (disable={disable})")
        return jsonify({"success": True, "message": "Battery detection stopped", "disabled": disable})
    except Exception as e:
        logger.error(f"Failed to stop battery detection via API: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/battery_detection/start', methods=['POST'])
def start_battery_detection():
    """启动电池检测线程，并可选启用配置"""
    if _main_window is None:
        return jsonify({"success": False, "error": "MainWindow not available"})
    try:
        data = request.get_json(silent=True) or {}
        enable = bool(data.get('enable', False))
        channels = data.get('channels', None)

        if enable and hasattr(_main_window, 'config_manager') and _main_window.config_manager:
            try:
                _main_window.config_manager.set('battery_detection.enabled', True)
                if hasattr(_main_window.config_manager, 'save_config'):
                    _main_window.config_manager.save_config()
            except Exception as cfg_e:
                logger.warning(f"Enable battery detection config failed: {cfg_e}")

        mgr = getattr(_main_window, 'battery_detection_manager', None)
        if mgr is None:
            return jsonify({"success": False, "error": "battery_detection_manager not available"})

        mgr.start_detection(channels)
        if hasattr(_main_window, '_battery_detection_active'):
            _main_window._battery_detection_active = True

        logger.info(f"Battery detection started via API (enable={enable}, channels={channels})")
        return jsonify({"success": True, "message": "Battery detection started", "enabled": enable, "channels": channels})
    except Exception as e:
        logger.error(f"Failed to start battery detection via API: {e}")
        return jsonify({"success": False, "error": str(e)})

# ============ 服务器管理 ============

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """关闭API服务"""
    logger.warning("Remote shutdown requested via API")
    request.environ.get('werkzeug.server.shutdown')()
    return jsonify({
        "success": True,
        "message": "Server shutting down..."
    })

# ============ 服务器启动 ============

class APIServer(threading.Thread):
    def __init__(self, host='0.0.0.0', port=5000):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.running = False

    def run(self):
        self.running = True
        logger.info(f"Starting JCY5001 Remote API on http://{self.host}:{self.port}")
        app.run(host=self.host, port=self.port, threaded=True, use_reloader=False)
        self.running = False

def start_api_server(host='0.0.0.0', port=5000, main_window=None):
    """启动API服务器（后台线程模式）"""
    if main_window is not None:
        set_main_window(main_window)
    server = APIServer(host, port)
    server.start()
    logger.info(f"JCY5001 Remote API started on port {port}")
    return server

# ============ 数据分析 API ============
@app.route('/analysis/show', methods=['POST'])
def show_analysis_window():
    """远程打开数据分析窗口（在GUI桌面显示）"""
    if _main_window is None:
        return jsonify({"success": False, "error": "Main window not available"})
    try:
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, _main_window._on_export_data)
        return jsonify({"success": True, "message": "数据分析窗口已请求打开"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/analysis/nyquist_data', methods=['GET'])
@app.route('/analysis/nyquist_data/<int:result_id>', methods=['GET'])
def get_nyquist_data(result_id=None):
    """获取Nyquist图数据（用于AI分析）"""
    try:
        from backend.eis_analyzer import EISAnalyzer
        from data.database_manager import DatabaseManager
        
        db = DatabaseManager()
        if result_id:
            result = db.get_test_result(result_id)
        else:
            results = db.get_recent_test_results(limit=1)
            result = results[0] if results else None
        
        if not result:
            return jsonify({"success": False, "error": "No test results found"})
        
        analyzer = EISAnalyzer()
        nyquist_data = analyzer.get_nyquist_data(result)
        
        return jsonify({
            "success": True,
            "data": nyquist_data,
            "result_id": result.get('id'),
            "channel": result.get('channel')
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/analysis/nyquist_plot/<int:result_id>', methods=['GET'])
def get_nyquist_plot(result_id):
    """生成并返回Nyquist图（base64图片）"""
    import base64, io
    try:
        from backend.eis_analyzer import EISAnalyzer
        from data.database_manager import DatabaseManager
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        db = DatabaseManager()
        result = db.get_test_result(result_id)
        if not result:
            return jsonify({"success": False, "error": f"No result found for id {result_id}"})
        
        analyzer = EISAnalyzer()
        nyquist_data = analyzer.get_nyquist_data(result)
        
        fig, ax = plt.subplots(figsize=(8, 6))
        if nyquist_data and 'Z_real' in nyquist_data and 'Z_imag' in nyquist_data:
            ax.plot(nyquist_data['Z_real'], nyquist_data['Z_imag'], 'bo-', markersize=3)
            ax.set_xlabel("Z' (m\u03a9)")
            ax.set_ylabel('-Z" (m\u03a9)')
            ax.set_title(f"Nyquist Plot - Channel {result.get('channel')}")
            ax.grid(True)
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode()
        
        return jsonify({
            "success": True,
            "image_base64": img_b64,
            "result_id": result_id,
            "channel": result.get('channel'),
            "voltage": result.get('voltage'),
            "rs": result.get('rs'),
            "rct": result.get('rct')
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


