#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电池阻抗测试系统 - 管理员API路由
实现模型管理、系统监控等管理员功能
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import os
import sys
import threading
import time

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ml_models import BatteryPerformancePredictor
from extensions import db

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# 全局变量存储训练状态
training_status = {
    'is_training': False,
    'progress': 0,
    'message': '',
    'start_time': None,
    'end_time': None,
    'task_id': None
}

def check_admin_permission(user_id):
    """检查管理员权限"""
    from models.user import User
    user = User.query.get(user_id)
    return user and user.role == 'admin'

@admin_bp.route('/models/train', methods=['POST'])
@jwt_required()
def train_models():
    """
    触发模型训练API
    POST /api/admin/models/train
    """
    try:
        user_id = get_jwt_identity()
        
        # 检查管理员权限
        if not check_admin_permission(user_id):
            return jsonify({
                'error': 'Permission Denied',
                'message': '需要管理员权限',
                'status_code': 403
            }), 403
        
        # 检查是否已有训练任务在进行
        if training_status['is_training']:
            return jsonify({
                'error': 'Training In Progress',
                'message': '已有模型训练任务在进行中',
                'status_code': 409,
                'data': {
                    'task_id': training_status['task_id'],
                    'progress': training_status['progress'],
                    'start_time': training_status['start_time']
                }
            }), 409
        
        # 获取训练参数
        data = request.get_json() or {}
        model_type = data.get('model_type', 'all')  # all, capacity, cycle_life, temperature
        training_parameters = data.get('training_parameters', {})
        
        # 生成任务ID
        task_id = f"train_{int(time.time())}"
        
        # 更新训练状态
        training_status.update({
            'is_training': True,
            'progress': 0,
            'message': '开始模型训练...',
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'task_id': task_id
        })
        
        # 启动后台训练任务
        def train_models_background():
            try:
                predictor = BatteryPerformancePredictor()
                
                # 更新进度
                training_status['progress'] = 10
                training_status['message'] = '生成训练数据...'
                
                # 生成训练数据
                n_samples = training_parameters.get('n_samples', 2000)
                X, y_dict = predictor.generate_synthetic_data(n_samples=n_samples)
                
                training_status['progress'] = 30
                training_status['message'] = '训练模型...'
                
                results = {}
                
                # 根据model_type训练相应模型
                if model_type in ['all', 'capacity']:
                    training_status['message'] = '训练容量预测模型...'
                    results['capacity'] = predictor.train_capacity_model(X, y_dict['capacity'])
                    training_status['progress'] = 50
                
                if model_type in ['all', 'cycle_life']:
                    training_status['message'] = '训练循环寿命预测模型...'
                    results['cycle_life'] = predictor.train_cycle_life_model(X, y_dict['cycle_life'])
                    training_status['progress'] = 70
                
                if model_type in ['all', 'temperature']:
                    training_status['message'] = '训练温度性能预测模型...'
                    results['temperature'] = predictor.train_temperature_model(X, y_dict['temp_performance'])
                    training_status['progress'] = 90
                
                # 保存模型
                training_status['message'] = '保存模型...'
                model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
                predictor.save_models(model_dir)
                
                # 训练完成
                training_status.update({
                    'is_training': False,
                    'progress': 100,
                    'message': '模型训练完成',
                    'end_time': datetime.now().isoformat(),
                    'results': results
                })
                
                current_app.logger.info(f"模型训练任务 {task_id} 完成")
                
            except Exception as e:
                training_status.update({
                    'is_training': False,
                    'progress': -1,
                    'message': f'训练失败: {str(e)}',
                    'end_time': datetime.now().isoformat(),
                    'error': str(e)
                })
                current_app.logger.error(f"模型训练任务 {task_id} 失败: {str(e)}")
        
        # 启动后台线程
        thread = threading.Thread(target=train_models_background)
        thread.daemon = True
        thread.start()
        
        current_app.logger.info(f"用户 {user_id} 启动模型训练任务 {task_id}")
        
        return jsonify({
            'message': '模型训练任务已启动',
            'data': {
                'task_id': task_id,
                'model_type': model_type,
                'training_parameters': training_parameters,
                'status': 'started'
            }
        }), 202
        
    except Exception as e:
        current_app.logger.error(f"启动模型训练API错误: {str(e)}")
        return jsonify({
            'error': 'Training Start Error',
            'message': '启动模型训练时发生错误',
            'status_code': 500
        }), 500

@admin_bp.route('/models/train/status', methods=['GET'])
@jwt_required()
def get_training_status():
    """
    获取训练状态API
    GET /api/admin/models/train/status
    """
    try:
        user_id = get_jwt_identity()
        
        # 检查管理员权限
        if not check_admin_permission(user_id):
            return jsonify({
                'error': 'Permission Denied',
                'message': '需要管理员权限',
                'status_code': 403
            }), 403
        
        return jsonify({
            'message': '获取训练状态成功',
            'data': training_status
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取训练状态API错误: {str(e)}")
        return jsonify({
            'error': 'Status Query Error',
            'message': '获取训练状态时发生错误',
            'status_code': 500
        }), 500

@admin_bp.route('/models', methods=['GET'])
@jwt_required()
def get_models():
    """
    获取模型列表API
    GET /api/admin/models
    """
    try:
        user_id = get_jwt_identity()
        
        # 检查管理员权限
        if not check_admin_permission(user_id):
            return jsonify({
                'error': 'Permission Denied',
                'message': '需要管理员权限',
                'status_code': 403
            }), 403
        
        model_type = request.args.get('model_type', 'all')
        
        # 检查模型文件
        model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        model_types = ['capacity', 'cycle_life', 'temperature']
        
        models_info = []
        
        for mtype in model_types:
            if model_type != 'all' and model_type != mtype:
                continue
                
            model_path = os.path.join(model_dir, f'{mtype}_model.joblib')
            metadata_path = os.path.join(model_dir, f'{mtype}_metadata.joblib')
            
            if os.path.exists(model_path) and os.path.exists(metadata_path):
                # 读取元数据
                import joblib
                metadata = joblib.load(metadata_path)
                
                model_info = {
                    'model_type': mtype,
                    'model_path': model_path,
                    'file_size': os.path.getsize(model_path),
                    'created_at': datetime.fromtimestamp(os.path.getctime(model_path)).isoformat(),
                    'modified_at': datetime.fromtimestamp(os.path.getmtime(model_path)).isoformat(),
                    'is_active': True,
                    'metadata': metadata
                }
                models_info.append(model_info)
            else:
                models_info.append({
                    'model_type': mtype,
                    'model_path': None,
                    'file_size': 0,
                    'created_at': None,
                    'modified_at': None,
                    'is_active': False,
                    'metadata': None
                })
        
        return jsonify({
            'message': '获取模型列表成功',
            'data': {
                'models': models_info,
                'total_count': len(models_info),
                'active_count': len([m for m in models_info if m['is_active']])
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取模型列表API错误: {str(e)}")
        return jsonify({
            'error': 'Models Query Error',
            'message': '获取模型列表时发生错误',
            'status_code': 500
        }), 500

@admin_bp.route('/models/<model_type>/status', methods=['PUT'])
@jwt_required()
def update_model_status(model_type):
    """
    激活/停用模型API
    PUT /api/admin/models/{model_type}/status
    """
    try:
        user_id = get_jwt_identity()
        
        # 检查管理员权限
        if not check_admin_permission(user_id):
            return jsonify({
                'error': 'Permission Denied',
                'message': '需要管理员权限',
                'status_code': 403
            }), 403
        
        # 验证模型类型
        valid_types = ['capacity', 'cycle_life', 'temperature']
        if model_type not in valid_types:
            return jsonify({
                'error': 'Invalid Model Type',
                'message': f'无效的模型类型，支持的类型: {valid_types}',
                'status_code': 400
            }), 400
        
        data = request.get_json()
        is_active = data.get('is_active', True)
        
        # 检查模型文件是否存在
        model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        model_path = os.path.join(model_dir, f'{model_type}_model.joblib')
        
        if not os.path.exists(model_path):
            return jsonify({
                'error': 'Model Not Found',
                'message': f'模型文件 {model_type} 不存在',
                'status_code': 404
            }), 404
        
        # 这里可以实现模型的激活/停用逻辑
        # 目前只是返回状态更新成功的消息
        
        current_app.logger.info(f"用户 {user_id} 更新模型 {model_type} 状态为 {'激活' if is_active else '停用'}")
        
        return jsonify({
            'message': f'模型 {model_type} 状态更新成功',
            'data': {
                'model_type': model_type,
                'is_active': is_active,
                'updated_at': datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"更新模型状态API错误: {str(e)}")
        return jsonify({
            'error': 'Status Update Error',
            'message': '更新模型状态时发生错误',
            'status_code': 500
        }), 500

@admin_bp.route('/system/stats', methods=['GET'])
@jwt_required()
def get_system_stats():
    """
    获取系统统计信息API
    GET /api/admin/system/stats
    """
    try:
        user_id = get_jwt_identity()
        
        # 检查管理员权限
        if not check_admin_permission(user_id):
            return jsonify({
                'error': 'Permission Denied',
                'message': '需要管理员权限',
                'status_code': 403
            }), 403
        
        # 获取数据库统计信息
        from models.user import User, Device, Battery, TestBatch, TestResult
        
        stats = {
            'users': {
                'total': User.query.count(),
                'active': User.query.filter_by(is_active=True).count() if hasattr(User, 'is_active') else User.query.count(),
                'admins': User.query.filter_by(role='admin').count()
            },
            'devices': {
                'total': Device.query.count(),
                'online': Device.query.filter_by(status='online').count() if hasattr(Device, 'status') else 0
            },
            'batteries': {
                'total': Battery.query.count()
            },
            'test_batches': {
                'total': TestBatch.query.count(),
                'completed': TestBatch.query.filter_by(status='completed').count() if hasattr(TestBatch, 'status') else 0
            },
            'test_results': {
                'total': TestResult.query.count()
            }
        }
        
        # 系统信息
        import psutil
        import platform
        
        system_info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_usage': psutil.disk_usage('/').percent
        }
        
        return jsonify({
            'message': '获取系统统计信息成功',
            'data': {
                'database_stats': stats,
                'system_info': system_info,
                'timestamp': datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取系统统计信息API错误: {str(e)}")
        return jsonify({
            'error': 'Stats Query Error',
            'message': '获取系统统计信息时发生错误',
            'status_code': 500
        }), 500

