#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JCY5001A数据接收服务器示例
用于接收电池测试系统上传的数据

依赖安装：
pip install flask

运行方法：
python example_server.py

访问地址：
http://localhost:5002
"""

import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

# 存储接收到的数据
received_data = []

# 简单的认证令牌（实际使用时应该使用更安全的方式）
VALID_TOKENS = {
    'test-token-123': 'JCY5001A_001',
    'device-token-456': 'JCY5001A_002'
}


def verify_auth(request):
    """验证认证信息"""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header:
        return False, "缺少认证头"
    
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]  # 移除 "Bearer " 前缀
        if token in VALID_TOKENS:
            return True, VALID_TOKENS[token]
        else:
            return False, "无效的认证令牌"
    
    return False, "不支持的认证类型"


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'service': 'JCY5001A Data Server',
        'version': '1.0.0'
    })


@app.route('/api/test-results', methods=['POST'])
def receive_test_results():
    """接收测试结果数据"""
    try:
        # 验证认证（可选，根据需要启用）
        # is_valid, device_id = verify_auth(request)
        # if not is_valid:
        # return jsonify({
        # 'error': 'Authorization Required',
        # 'message': '需要提供有效的访问令牌',
        # 'status_code': 401
        # }), 401
        
        # 获取请求数据
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'No data provided',
                'message': '请求中没有数据',
                'status_code': 400
            }), 400
        
        # 验证数据格式
        upload_type = data.get('upload_type')
        if upload_type not in ['single_result', 'batch_results']:
            return jsonify({
                'error': 'Invalid upload type',
                'message': f'不支持的上传类型: {upload_type}',
                'status_code': 400
            }), 400
        
        # 记录接收到的数据
        record = {
            'id': len(received_data) + 1,
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'headers': dict(request.headers),
            'remote_addr': request.remote_addr
        }
        received_data.append(record)
        
        # 处理数据
        device_info = data.get('device_info', {})
        batch_info = data.get('batch_info', {})
        
        logger.info(f"接收到数据上传请求:")
        logger.info(f"  ID: {record['id']}")
        logger.info(f"  来源: {request.remote_addr}")
        logger.info(f"  设备ID: {device_info.get('device_id', 'N/A')}")
        logger.info(f"  软件版本: {device_info.get('software_version', 'N/A')}")
        logger.info(f"  上传类型: {upload_type}")
        logger.info(f"  批次号: {batch_info.get('batch_number', 'N/A')}")
        logger.info(f"  操作员: {batch_info.get('operator', 'N/A')}")
        
        if upload_type == 'single_result':
            test_result = data.get('test_result', {})
            logger.info(f"  单个测试结果:")
            logger.info(f"    通道: {test_result.get('channel_number', 'N/A')}")
            logger.info(f"    电池码: {test_result.get('battery_code', 'N/A')}")
            logger.info(f"    电压: {test_result.get('voltage', 'N/A')}V")
            logger.info(f"    Rs值: {test_result.get('rs_value', 'N/A')}mΩ")
            logger.info(f"    Rct值: {test_result.get('rct_value', 'N/A')}mΩ")
            logger.info(f"    测试结果: {'合格' if test_result.get('is_pass') else '不合格'}")
            
            # 这里可以添加数据处理逻辑，如保存到数据库
            process_single_result(test_result, batch_info, device_info)
            
        elif upload_type == 'batch_results':
            test_results = data.get('test_results', [])
            result_count = data.get('result_count', len(test_results))
            logger.info(f"  批量测试结果: {result_count}个结果")
            
            for i, result in enumerate(test_results[:3]):  # 只显示前3个
                logger.info(f"    [{i+1}] 通道{result.get('channel_number', 'N/A')}: "
                          f"{result.get('battery_code', 'N/A')} - "
                          f"{'合格' if result.get('is_pass') else '不合格'}")
            if len(test_results) > 3:
                logger.info(f"    ... 还有{len(test_results)-3}个结果")
            
            # 这里可以添加批量数据处理逻辑
            process_batch_results(test_results, batch_info, device_info)
        
        # 返回成功响应
        response = {
            'status': 'success',
            'message': '数据接收成功',
            'timestamp': datetime.now().isoformat(),
            'record_id': record['id'],
            'data_type': upload_type
        }
        
        logger.info(f"响应: {response['message']} (ID: {record['id']})")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"处理上传数据失败: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': f'服务器内部错误: {str(e)}',
            'status_code': 500
        }), 500


def process_single_result(test_result, batch_info, device_info):
    """处理单个测试结果"""
    # 这里添加你的数据处理逻辑
    # 例如：保存到数据库、发送通知、数据分析等
    
    logger.debug(f"处理单个测试结果: {test_result.get('battery_code', 'N/A')}")
    
    # 示例：检查测试结果
    if not test_result.get('is_pass', False):
        logger.warning(f"检测到不合格电池: {test_result.get('battery_code', 'N/A')} "
                      f"- {test_result.get('fail_reason', '未知原因')}")


def process_batch_results(test_results, batch_info, device_info):
    """处理批量测试结果"""
    # 这里添加你的批量数据处理逻辑
    
    logger.debug(f"处理批量测试结果: {len(test_results)}个结果")
    
    # 示例：统计合格率
    total_count = len(test_results)
    pass_count = sum(1 for result in test_results if result.get('is_pass', False))
    pass_rate = (pass_count / total_count * 100) if total_count > 0 else 0
    
    logger.info(f"批次{batch_info.get('batch_number', 'N/A')}统计: "
               f"总数={total_count}, 合格={pass_count}, 合格率={pass_rate:.1f}%")


@app.route('/api/data', methods=['GET'])
def get_received_data():
    """获取接收到的数据"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    start = (page - 1) * per_page
    end = start + per_page
    
    return jsonify({
        'total_count': len(received_data),
        'page': page,
        'per_page': per_page,
        'data': received_data[start:end]
    })


@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """获取统计信息"""
    total_records = len(received_data)
    
    # 统计上传类型
    single_count = sum(1 for record in received_data 
                      if record['data'].get('upload_type') == 'single_result')
    batch_count = sum(1 for record in received_data 
                     if record['data'].get('upload_type') == 'batch_results')
    
    # 统计设备
    devices = {}
    for record in received_data:
        device_id = record['data'].get('device_info', {}).get('device_id', 'unknown')
        devices[device_id] = devices.get(device_id, 0) + 1
    
    return jsonify({
        'total_records': total_records,
        'upload_types': {
            'single_result': single_count,
            'batch_results': batch_count
        },
        'devices': devices,
        'last_update': received_data[-1]['timestamp'] if received_data else None
    })


@app.route('/api/clear', methods=['POST'])
def clear_data():
    """清空接收到的数据"""
    global received_data
    count = len(received_data)
    received_data.clear()
    
    logger.info(f"清空了{count}条接收数据")
    return jsonify({
        'status': 'success',
        'message': f'已清空{count}条数据',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/', methods=['GET'])
def index():
    """首页"""
    stats = {
        'total_records': len(received_data),
        'last_update': received_data[-1]['timestamp'] if received_data else '无'
    }
    
    return f"""
    <h1>JCY5001A 数据接收服务器</h1>
    <p>当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>已接收数据: {stats['total_records']} 条</p>
    <p>最后更新: {stats['last_update']}</p>
    
    <h2>API 接口:</h2>
    <ul>
        <li><a href="/health">GET /health</a> - 健康检查</li>
        <li>POST /api/test-results - 接收测试结果</li>
        <li><a href="/api/data">GET /api/data</a> - 查看接收到的数据</li>
        <li><a href="/api/stats">GET /api/stats</a> - 查看统计信息</li>
        <li>POST /api/clear - 清空数据</li>
    </ul>
    
    <h2>最近接收的数据:</h2>
    <pre>{json.dumps(received_data[-3:], ensure_ascii=False, indent=2)}</pre>
    """


if __name__ == '__main__':
    logger.info("启动JCY5001A数据接收服务器...")
    logger.info("服务器地址: http://localhost:5002")
    logger.info("健康检查: http://localhost:5002/health")
    logger.info("数据接收: POST http://localhost:5002/api/test-results")
    logger.info("数据查看: http://localhost:5002/api/data")
    logger.info("统计信息: http://localhost:5002/api/stats")
    
    # 启动服务器
    app.run(
        host='0.0.0.0',  # 监听所有网络接口
        port=5002,
        debug=False,     # 生产环境建议设为False
        use_reloader=False
    )
