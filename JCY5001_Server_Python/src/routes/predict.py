#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电池阻抗测试系统 - 预测API路由
实现基于机器学习模型的电池性能预测API
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import os
import sys

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ml_models import BatteryPerformancePredictor
from extensions import db

# 创建蓝图
predict_bp = Blueprint('predict', __name__, url_prefix='/api/predict')

# 全局预测器实例
predictor = None

def init_predictor():
    """初始化预测器"""
    global predictor
    if predictor is None:
        predictor = BatteryPerformancePredictor()
        model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        
        # 如果模型文件不存在，先训练模型
        if not os.path.exists(os.path.join(model_dir, 'capacity_model.joblib')):
            current_app.logger.info("模型文件不存在，开始训练模型...")
            predictor.train_all_models()
        else:
            # 加载已训练的模型
            predictor.load_models(model_dir)
            current_app.logger.info("机器学习模型加载完成")

@predict_bp.route('/performance', methods=['POST'])
@jwt_required()
def predict_performance():
    """
    性能预测API
    POST /api/predict/performance
    """
    try:
        # 初始化预测器
        init_predictor()
        
        # 获取请求数据
        data = request.get_json()
        
        # 验证必需参数
        required_fields = ['rs', 'rct']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'error': 'Missing Required Field',
                    'message': f'字段 {field} 是必需的',
                    'status_code': 400
                }), 400
        
        # 提取参数
        rs = float(data['rs'])
        rct = float(data['rct'])
        voltage = float(data.get('voltage', 3.2))
        temperature = float(data.get('temperature', 25))
        battery_type = data.get('battery_type', 'LFP')
        
        # 参数验证
        if rs <= 0 or rs > 1:
            return jsonify({
                'error': 'Invalid Parameter',
                'message': 'Rs值必须在0-1Ω范围内',
                'status_code': 400
            }), 400
            
        if rct <= 0 or rct > 1:
            return jsonify({
                'error': 'Invalid Parameter',
                'message': 'Rct值必须在0-1Ω范围内',
                'status_code': 400
            }), 400
        
        # 执行预测
        result = predictor.predict_performance(
            rs=rs,
            rct=rct,
            voltage=voltage,
            temperature=temperature,
            battery_type=battery_type
        )
        
        # 记录预测历史（如果需要）
        user_id = get_jwt_identity()
        current_app.logger.info(f"用户 {user_id} 执行性能预测: Rs={rs}, Rct={rct}")
        
        return jsonify({
            'message': '预测完成',
            'data': result,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except ValueError as e:
        return jsonify({
            'error': 'Invalid Parameter',
            'message': f'参数格式错误: {str(e)}',
            'status_code': 400
        }), 400
    except Exception as e:
        current_app.logger.error(f"预测API错误: {str(e)}")
        return jsonify({
            'error': 'Prediction Error',
            'message': '预测过程中发生错误',
            'status_code': 500
        }), 500

@predict_bp.route('/batch', methods=['POST'])
@jwt_required()
def predict_batch():
    """
    批量预测API
    POST /api/predict/batch
    """
    try:
        # 初始化预测器
        init_predictor()
        
        # 获取请求数据
        data = request.get_json()
        
        # 验证数据格式
        if 'batteries' not in data:
            return jsonify({
                'error': 'Missing Required Field',
                'message': '字段 batteries 是必需的',
                'status_code': 400
            }), 400
        
        batteries = data['batteries']
        if not isinstance(batteries, list):
            return jsonify({
                'error': 'Invalid Parameter',
                'message': 'batteries 必须是数组格式',
                'status_code': 400
            }), 400
        
        if len(batteries) == 0:
            return jsonify({
                'error': 'Invalid Parameter',
                'message': 'batteries 数组不能为空',
                'status_code': 400
            }), 400
        
        if len(batteries) > 100:  # 限制批量大小
            return jsonify({
                'error': 'Invalid Parameter',
                'message': '批量预测最多支持100个电池',
                'status_code': 400
            }), 400
        
        # 验证每个电池的数据
        for i, battery in enumerate(batteries):
            if 'rs' not in battery or 'rct' not in battery:
                return jsonify({
                    'error': 'Invalid Parameter',
                    'message': f'第{i+1}个电池缺少rs或rct参数',
                    'status_code': 400
                }), 400
        
        # 执行批量预测
        results = predictor.batch_predict(batteries)
        
        # 统计结果
        success_count = len([r for r in results if 'error' not in r])
        error_count = len(results) - success_count
        
        # 记录批量预测历史
        user_id = get_jwt_identity()
        current_app.logger.info(f"用户 {user_id} 执行批量预测: {len(batteries)}个电池, 成功{success_count}个")
        
        return jsonify({
            'message': '批量预测完成',
            'data': {
                'results': results,
                'summary': {
                    'total_count': len(batteries),
                    'success_count': success_count,
                    'error_count': error_count
                }
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"批量预测API错误: {str(e)}")
        return jsonify({
            'error': 'Batch Prediction Error',
            'message': '批量预测过程中发生错误',
            'status_code': 500
        }), 500

@predict_bp.route('/history', methods=['GET'])
@jwt_required()
def get_prediction_history():
    """
    获取预测历史API
    GET /api/predict/history
    """
    try:
        # 获取查询参数
        battery_id = request.args.get('battery_id')
        batch_id = request.args.get('batch_id')
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        user_id = get_jwt_identity()
        
        # 这里应该从数据库查询预测历史
        # 由于我们还没有实现预测历史存储，先返回模拟数据
        
        # 模拟预测历史数据
        mock_history = [
            {
                'id': 1,
                'battery_id': 'BAT001',
                'predicted_capacity': 2950.5,
                'predicted_cycle_life': 1850,
                'confidence_level': 0.85,
                'input_parameters': {
                    'rs': 0.045,
                    'rct': 0.018,
                    'voltage': 3.2,
                    'temperature': 25
                },
                'created_at': '2025-06-08T10:30:00Z'
            },
            {
                'id': 2,
                'battery_id': 'BAT002',
                'predicted_capacity': 3120.8,
                'predicted_cycle_life': 2150,
                'confidence_level': 0.92,
                'input_parameters': {
                    'rs': 0.038,
                    'rct': 0.015,
                    'voltage': 3.25,
                    'temperature': 23
                },
                'created_at': '2025-06-08T11:15:00Z'
            }
        ]
        
        # 应用筛选条件
        filtered_history = mock_history
        if battery_id:
            filtered_history = [h for h in filtered_history if h['battery_id'] == battery_id]
        
        # 分页
        total = len(filtered_history)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_history = filtered_history[start:end]
        
        return jsonify({
            'message': '获取预测历史成功',
            'data': {
                'predictions': paginated_history,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }
        }), 200
        
    except ValueError as e:
        return jsonify({
            'error': 'Invalid Parameter',
            'message': f'参数格式错误: {str(e)}',
            'status_code': 400
        }), 400
    except Exception as e:
        current_app.logger.error(f"获取预测历史API错误: {str(e)}")
        return jsonify({
            'error': 'History Query Error',
            'message': '获取预测历史时发生错误',
            'status_code': 500
        }), 500

@predict_bp.route('/models/info', methods=['GET'])
@jwt_required()
def get_model_info():
    """
    获取模型信息API
    GET /api/predict/models/info
    """
    try:
        # 初始化预测器
        init_predictor()
        
        # 获取模型元数据
        model_info = {}
        for model_name, metadata in predictor.model_metadata.items():
            model_info[model_name] = {
                'accuracy_r2': metadata.get('r2', 0),
                'rmse': metadata.get('rmse', 0),
                'cross_validation_mean': metadata.get('cv_mean', 0),
                'cross_validation_std': metadata.get('cv_std', 0),
                'training_samples': metadata.get('n_samples', 0),
                'trained_at': metadata.get('trained_at'),
                'status': 'active' if model_name in predictor.models else 'inactive'
            }
        
        return jsonify({
            'message': '获取模型信息成功',
            'data': {
                'models': model_info,
                'total_models': len(model_info),
                'active_models': len([m for m in model_info.values() if m['status'] == 'active'])
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取模型信息API错误: {str(e)}")
        return jsonify({
            'error': 'Model Info Error',
            'message': '获取模型信息时发生错误',
            'status_code': 500
        }), 500

@predict_bp.route('/battery-matching', methods=['POST'])
@jwt_required()
def battery_matching():
    """
    电池匹配推荐API
    POST /api/predict/battery-matching
    """
    try:
        # 获取请求数据
        data = request.get_json()
        
        # 验证数据格式
        if 'batteries' not in data:
            return jsonify({
                'error': 'Missing Required Field',
                'message': '字段 batteries 是必需的',
                'status_code': 400
            }), 400
        
        batteries = data['batteries']
        if not isinstance(batteries, list) or len(batteries) < 2:
            return jsonify({
                'error': 'Invalid Parameter',
                'message': '至少需要2个电池进行匹配分析',
                'status_code': 400
            }), 400
        
        # 简单的电池匹配算法
        matching_results = []
        
        for i, battery in enumerate(batteries):
            rs = battery.get('rs', 0)
            rct = battery.get('rct', 0)
            battery_id = battery.get('battery_id', f'BATTERY_{i}')
            
            # 计算匹配度评分（基于阻抗值的相似性）
            scores = []
            for j, other_battery in enumerate(batteries):
                if i != j:
                    other_rs = other_battery.get('rs', 0)
                    other_rct = other_battery.get('rct', 0)
                    
                    # 计算欧几里得距离的倒数作为相似度
                    distance = ((rs - other_rs) ** 2 + (rct - other_rct) ** 2) ** 0.5
                    similarity = 1 / (1 + distance * 100)  # 归一化相似度
                    
                    scores.append({
                        'battery_id': other_battery.get('battery_id', f'BATTERY_{j}'),
                        'similarity_score': round(similarity, 3),
                        'rs_diff': abs(rs - other_rs),
                        'rct_diff': abs(rct - other_rct)
                    })
            
            # 按相似度排序
            scores.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            matching_results.append({
                'battery_id': battery_id,
                'rs': rs,
                'rct': rct,
                'best_matches': scores[:3],  # 返回前3个最佳匹配
                'average_similarity': round(sum(s['similarity_score'] for s in scores) / len(scores), 3) if scores else 0
            })
        
        # 生成整体匹配建议
        all_similarities = [r['average_similarity'] for r in matching_results]
        overall_score = sum(all_similarities) / len(all_similarities) if all_similarities else 0
        
        if overall_score > 0.8:
            recommendation = "电池组匹配度很高，适合组成电池包"
        elif overall_score > 0.6:
            recommendation = "电池组匹配度中等，建议进一步筛选"
        else:
            recommendation = "电池组匹配度较低，建议重新选择电池"
        
        user_id = get_jwt_identity()
        current_app.logger.info(f"用户 {user_id} 执行电池匹配分析: {len(batteries)}个电池")
        
        return jsonify({
            'message': '电池匹配分析完成',
            'data': {
                'matching_results': matching_results,
                'overall_score': round(overall_score, 3),
                'recommendation': recommendation,
                'analysis_summary': {
                    'total_batteries': len(batteries),
                    'high_similarity_pairs': len([r for r in matching_results if r['average_similarity'] > 0.8]),
                    'medium_similarity_pairs': len([r for r in matching_results if 0.6 <= r['average_similarity'] <= 0.8]),
                    'low_similarity_pairs': len([r for r in matching_results if r['average_similarity'] < 0.6])
                }
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"电池匹配API错误: {str(e)}")
        return jsonify({
            'error': 'Battery Matching Error',
            'message': '电池匹配分析时发生错误',
            'status_code': 500
        }), 500

