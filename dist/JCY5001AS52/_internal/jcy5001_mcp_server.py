#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JCY5001 MCP Server - Model Context Protocol 接口
为 Hermes AI 生态提供 JCY5001 EIS 测试仪的远程控制能力

整合现有 remote_api 的状态，提供 MCP 标准化接口
"""

import json
import threading
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.types import Tool, Resource, Prompt, TextContent, ImageContent, EmbeddedResource
import logging

# 导入现有的 remote_api
import sys
from pathlib import Path
# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from remote_api import get_state, api_state, _main_window
except ImportError:
    get_state = None
    api_state = {
        "app_running": False,
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
    _main_window = None

logger = logging.getLogger(__name__)

app = Server("jcy5001-eis")

@app.list_tools()
async def list_tools() -> List[Tool]:
    """列出所有可用工具"""
    return [
        Tool(
            name="get_status",
            description="获取 JCY5001 EIS 测试仪当前状态",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_statistics",
            description="获取测试统计信息",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_channels",
            description="获取所有通道状态",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="start_test",
            description="开始EIS测试，可以指定通道（不指定则测试所有通道）",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel": {
                        "type": ["integer", "null"],
                        "description": "通道编号 (1-8)，null 表示测试所有已启用通道"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="stop_test",
            description="停止当前正在运行的测试",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@app.list_resources()
async def list_resources() -> List[Resource]:
    """列出所有可用资源"""
    return [
        Resource(
            uri="jcy5001://status",
            name="JCY5001 Current Status",
            description="JCY5001 EIS测试仪当前运行状态",
            mimeType="application/json"
        ),
        Resource(
            uri="jcy5001://statistics",
            name="Test Statistics",
            description="历史测试统计数据",
            mimeType="application/json"
        ),
        Resource(
            uri="jcy5001://channels",
            name="Channel Status",
            description="所有通道的当前状态",
            mimeType="application/json"
        )
    ]

@app.list_prompts()
async def list_prompts() -> List[Prompt]:
    """列出可用提示词"""
    return [
        Prompt(
            name="eis_test_analysis",
            description="分析EIS测试结果，给出等效电路拟合建议"
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent | ImageContent | EmbeddedResource]:
    """执行工具调用"""
    
    if name == "get_status":
        if get_state:
            state = get_state()
        else:
            state = api_state
        return [
            TextContent(
                type="text",
                text=json.dumps(state, indent=2, ensure_ascii=False)
            )
        ]
    
    elif name == "get_statistics":
        if get_state:
            stats = get_state()["statistics"]
        else:
            stats = api_state["statistics"]
        return [
            TextContent(
                type="text",
                text=json.dumps(stats, indent=2, ensure_ascii=False)
            )
        ]
    
    elif name == "get_channels":
        if get_state:
            channels = get_state()["channels"]
        else:
            channels = api_state["channels"]
        return [
            TextContent(
                type="text",
                text=json.dumps(channels, indent=2, ensure_ascii=False)
            )
        ]
    
    elif name == "start_test":
        channel = arguments.get("channel", None)
        
        if _main_window is None:
            return [
                TextContent(
                    type="text",
                    text="错误: MainWindow 引用不可用，请确保 GUI 已启动并正确集成 MCP"
                )
            ]
        
        if api_state.get("is_testing", False):
            return [
                TextContent(
                    type="text",
                    text="错误: 已有测试正在运行，请先停止当前测试"
                )
            ]
        
        try:
            if channel is None:
                _main_window.start_all_channels_test()
                msg = "已启动所有已启用通道的测试"
            else:
                _main_window.start_single_channel_test(channel)
                msg = f"已启动通道 {channel} 的测试"
            
            # 更新状态
            if get_state:
                # 状态由 remote_api 维护
                pass
            api_state["is_testing"] = True
            api_state["current_test"] = f"channel_{channel}" if channel else "all_channels"
            logger.info(f"MCP: {msg}")
            
            return [
                TextContent(
                    type="text",
                    text=f"成功: {msg}"
                )
            ]
        except Exception as e:
            error_msg = f"启动测试失败: {str(e)}"
            logger.error(f"MCP: {error_msg}")
            return [
                TextContent(
                    type="text",
                    text=f"错误: {error_msg}"
                )
            ]
    
    elif name == "stop_test":
        if _main_window is None:
            return [
                TextContent(
                    type="text",
                    text="错误: MainWindow 引用不可用，请确保 GUI 已启动并正确集成 MCP"
                )
            ]
        
        if not api_state.get("is_testing", False):
            return [
                TextContent(
                    type="text",
                    text="提示: 当前没有正在运行的测试"
                )
            ]
        
        try:
            _main_window.stop_current_test()
            api_state["is_testing"] = False
            api_state["current_test"] = None
            logger.info("MCP: 测试已停止")
            
            return [
                TextContent(
                    type="text",
                    text="成功: 测试已停止"
                )
            ]
        except Exception as e:
            error_msg = f"停止测试失败: {str(e)}"
            logger.error(f"MCP: {error_msg}")
            return [
                TextContent(
                    type="text",
                    text=f"错误: {error_msg}"
                )
            ]
    
    else:
        return [
            TextContent(
                type="text",
                text=f"错误: 未知工具 '{name}'"
            )
        ]

@app.read_resource()
async def read_resource(uri: str) -> str:
    """读取资源内容"""
    
    if uri == "jcy5001://status":
        if get_state:
            return json.dumps(get_state(), indent=2, ensure_ascii=False)
        else:
            return json.dumps(api_state, indent=2, ensure_ascii=False)
    
    elif uri == "jcy5001://statistics":
        if get_state:
            return json.dumps(get_state()["statistics"], indent=2, ensure_ascii=False)
        else:
            return json.dumps(api_state["statistics"], indent=2, ensure_ascii=False)
    
    elif uri == "jcy5001://channels":
        if get_state:
            return json.dumps(get_state()["channels"], indent=2, ensure_ascii=False)
        else:
            return json.dumps(api_state["channels"], indent=2, ensure_ascii=False)
    
    else:
        raise ValueError(f"未知资源: {uri}")

def start_mcp_server(host: str = "127.0.0.1", port: int = 8000):
    """启动 MCP 服务器（独立运行模式）"""
    import asyncio
    from mcp.server.stdio import stdio_server
    
    logger.info(f"Starting JCY5001 MCP Server on {host}:{port}")
    
    async def run():
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())
    
    asyncio.run(run())

class MCPServerThread(threading.Thread):
    """后台线程运行 MCP 服务器（与 GUI 集成模式）"""
    
    def __init__(self):
        super().__init__(daemon=True)
        self.running = False
    
    def run(self):
        self.running = True
        import asyncio
        from mcp.server.stdio import stdio_server
        
        logger.info("Starting JCY5001 MCP Server in background thread")
        
        try:
            asyncio.run(self._run_server())
        except Exception as e:
            logger.error(f"MCP server error: {e}")
        finally:
            self.running = False
    
    async def _run_server(self):
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    start_mcp_server()
