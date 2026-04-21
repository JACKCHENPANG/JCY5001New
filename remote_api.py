#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JCY5001 Remote API - 远程状态监控和控制API
运行在后台线程，和GUI主线程同步状态
支持远程查看状态和远程控制测试
"""

import json
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
    """更新API状态，由GUI主线程调用"""
    global api_state
    api_state.update(kwargs)
    logger.debug(f"API state updated: {kwargs.keys()}")

def get_state():
    """获取当前状态"""
    return api_state.copy()

# ============ API Routes ============

@app.route('/status', methods=['GET'])
def get_status():
    """获取应用当前状态"""
    return jsonify({
        "success": True,
        "data": get_state()
    })

@app.route('/statistics', methods=['GET'])
def get_statistics():
    """获取统计数据"""
    return jsonify({
        "success": True,
        "data": api_state["statistics"]
    })

@app.route('/channels', methods=['GET'])
def get_channels():
    """获取通道状态"""
    return jsonify({
        "success": True,
        "data": api_state["channels"]
    })

@app.route('/start_test', methods=['POST'])
def start_test():
    """远程启动测试
    需要参数: channel (可选, 默认为所有使能通道)
    """
    global _main_window
    try:
        if _main_window is None:
            return jsonify({"success": False, "error": "MainWindow not available"})
        
        if api_state["is_testing"]:
            return jsonify({"success": False, "error": "Test already running"})
        
        # 获取请求参数
        data = request.get_json(silent=True) or {}
        channel = data.get('channel', None)
        
        # 调用主窗口方法启动测试
        # 默认行为：启动所有已使能通道的测试
        if channel is None:
            _main_window.start_all_channels_test()
        else:
            _main_window.start_single_channel_test(channel)
        
        update_state(is_testing=True)
        logger.info(f"Test started via remote API (channel={channel})")
        return jsonify({"success": True, "message": f"Test started (channel={channel})"})
    except Exception as e:
        logger.error(f"Failed to start test via API: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/stop_test', methods=['POST'])
def stop_test():
    """远程停止测试"""
    global _main_window
    try:
        if _main_window is None:
            return jsonify({"success": False, "error": "MainWindow not available"})
        
        if not api_state["is_testing"]:
            return jsonify({"success": False, "error": "No test running"})
        
        _main_window.stop_current_test()
        update_state(is_testing=False)
        logger.info("Test stopped via remote API")
        return jsonify({"success": True, "message": "Test stopped"})
    except Exception as e:
        logger.error(f"Failed to stop test via API: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """远程关闭应用（需要确认）"""
    from werkzeug.serving import make_server
    logger.warning("Remote shutdown requested via API")
    request.environ.get('werkzeug.server.shutdown')()
    return jsonify({
        "success": True,
        "message": "Server shutting down..."
    })

# 后台线程运行Flask服务器
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
    """启动API服务器，在后台线程"""
    if main_window is not None:
        set_main_window(main_window)
    server = APIServer(host, port)
    server.start()
    logger.info(f"JCY5001 Remote API started on port {port}")
    return server
