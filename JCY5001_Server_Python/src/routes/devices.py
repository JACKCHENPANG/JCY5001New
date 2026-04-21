from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import and_, or_

from extensions import db
from models.user import User, Device

devices_bp = Blueprint('devices', __name__)

@devices_bp.route('/', methods=['GET'])
@jwt_required()
def get_devices():
    """获取设备列表"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status')
        model = request.args.get('model')
        search = request.args.get('search')
        
        # 构建查询
        query = Device.query
        
        # 权限控制：普通用户只能看到自己的设备，管理员可以看到所有设备
        if user.role != 'admin':
            query = query.filter(Device.user_id == current_user_id)
        
        # 状态过滤
        if status and Device.validate_status(status):
            query = query.filter(Device.status == status)
        
        # 型号过滤
        if model:
            query = query.filter(Device.model.ilike(f'%{model}%'))
        
        # 搜索过滤
        if search:
            search_filter = or_(
                Device.device_id.ilike(f'%{search}%'),
                Device.name.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        # 排序
        query = query.order_by(Device.created_at.desc())
        
        # 分页
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        devices = pagination.items
        
        return jsonify({
            'devices': [device.to_dict() for device in devices],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'status_code': 200
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取设备列表错误: {str(e)}")
        return jsonify({
            'error': 'Device List Fetch Failed',
            'message': '获取设备列表时发生错误',
            'status_code': 500
        }), 500

@devices_bp.route('/', methods=['POST'])
@jwt_required()
def create_device():
    """创建新设备"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        data = request.get_json()
        
        # 验证必需字段
        required_fields = ['device_id', 'name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'error': 'Missing Required Field',
                    'message': f'字段 {field} 是必需的',
                    'status_code': 400
                }), 400
        
        device_id = data['device_id'].strip()
        name = data['name'].strip()
        model = data.get('model', 'JCY5001').strip()
        firmware_version = data.get('firmware_version', '').strip()
        
        # 验证设备ID格式（放宽限制以支持硬件指纹）
        if len(device_id) < 3 or len(device_id) > 64:
            return jsonify({
                'error': 'Invalid Device ID',
                'message': '设备ID长度必须在3-64个字符之间',
                'status_code': 400
            }), 400
        
        # 验证设备名称
        if len(name) < 2 or len(name) > 100:
            return jsonify({
                'error': 'Invalid Device Name',
                'message': '设备名称长度必须在2-100个字符之间',
                'status_code': 400
            }), 400
        
        # 检查设备ID是否已存在
        existing_device = Device.query.filter_by(device_id=device_id).first()
        if existing_device:
            return jsonify({
                'error': 'Device ID Exists',
                'message': '设备ID已存在',
                'status_code': 409
            }), 409
        
        # 创建新设备
        device = Device(
            device_id=device_id,
            user_id=current_user_id,
            name=name,
            model=model,
            firmware_version=firmware_version if firmware_version else None
        )
        
        db.session.add(device)
        db.session.commit()
        
        return jsonify({
            'message': '设备创建成功',
            'device': device.to_dict(),
            'status_code': 201
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创建设备错误: {str(e)}")
        return jsonify({
            'error': 'Device Creation Failed',
            'message': '创建设备时发生错误',
            'status_code': 500
        }), 500

@devices_bp.route('/<int:device_id>', methods=['GET'])
@jwt_required()
def get_device(device_id):
    """获取单个设备信息"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        device = Device.query.get(device_id)
        if not device:
            return jsonify({
                'error': 'Device Not Found',
                'message': '设备不存在',
                'status_code': 404
            }), 404
        
        # 权限检查
        if user.role != 'admin' and device.user_id != current_user_id:
            return jsonify({
                'error': 'Access Denied',
                'message': '无权访问此设备',
                'status_code': 403
            }), 403
        
        # 获取设备的测试统计信息
        from models.user import TestBatch
        total_batches = TestBatch.query.filter_by(device_id=device.id).count()
        completed_batches = TestBatch.query.filter_by(
            device_id=device.id, status='completed'
        ).count()
        
        device_data = device.to_dict()
        device_data['statistics'] = {
            'total_batches': total_batches,
            'completed_batches': completed_batches,
            'success_rate': round(completed_batches / total_batches * 100, 2) if total_batches > 0 else 0
        }
        
        return jsonify({
            'device': device_data,
            'status_code': 200
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取设备信息错误: {str(e)}")
        return jsonify({
            'error': 'Device Fetch Failed',
            'message': '获取设备信息时发生错误',
            'status_code': 500
        }), 500

@devices_bp.route('/<int:device_id>', methods=['PUT'])
@jwt_required()
def update_device(device_id):
    """更新设备信息"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        device = Device.query.get(device_id)
        if not device:
            return jsonify({
                'error': 'Device Not Found',
                'message': '设备不存在',
                'status_code': 404
            }), 404
        
        # 权限检查
        if user.role != 'admin' and device.user_id != current_user_id:
            return jsonify({
                'error': 'Access Denied',
                'message': '无权修改此设备',
                'status_code': 403
            }), 403
        
        data = request.get_json()
        
        # 更新允许的字段
        if 'name' in data:
            name = data['name'].strip()
            if len(name) < 2 or len(name) > 100:
                return jsonify({
                    'error': 'Invalid Device Name',
                    'message': '设备名称长度必须在2-100个字符之间',
                    'status_code': 400
                }), 400
            device.name = name
        
        if 'model' in data:
            device.model = data['model'].strip()
        
        if 'firmware_version' in data:
            firmware_version = data['firmware_version'].strip()
            device.firmware_version = firmware_version if firmware_version else None
        
        if 'status' in data:
            status = data['status']
            if not Device.validate_status(status):
                return jsonify({
                    'error': 'Invalid Status',
                    'message': '设备状态必须是 active, inactive 或 maintenance 之一',
                    'status_code': 400
                }), 400
            device.status = status
        
        device.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': '设备信息更新成功',
            'device': device.to_dict(),
            'status_code': 200
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新设备信息错误: {str(e)}")
        return jsonify({
            'error': 'Device Update Failed',
            'message': '更新设备信息时发生错误',
            'status_code': 500
        }), 500

@devices_bp.route('/<int:device_id>', methods=['DELETE'])
@jwt_required()
def delete_device(device_id):
    """删除设备"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        device = Device.query.get(device_id)
        if not device:
            return jsonify({
                'error': 'Device Not Found',
                'message': '设备不存在',
                'status_code': 404
            }), 404
        
        # 权限检查：只有管理员或设备所有者可以删除
        if user.role != 'admin' and device.user_id != current_user_id:
            return jsonify({
                'error': 'Access Denied',
                'message': '无权删除此设备',
                'status_code': 403
            }), 403
        
        # 检查是否有关联的测试数据
        from models.user import TestBatch
        batch_count = TestBatch.query.filter_by(device_id=device.id).count()
        if batch_count > 0:
            return jsonify({
                'error': 'Device Has Data',
                'message': f'设备有 {batch_count} 个测试批次，无法删除。请先删除相关数据或联系管理员。',
                'status_code': 409
            }), 409
        
        db.session.delete(device)
        db.session.commit()
        
        return jsonify({
            'message': '设备删除成功',
            'status_code': 200
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除设备错误: {str(e)}")
        return jsonify({
            'error': 'Device Deletion Failed',
            'message': '删除设备时发生错误',
            'status_code': 500
        }), 500

@devices_bp.route('/<int:device_id>/sync', methods=['POST'])
@jwt_required()
def sync_device(device_id):
    """设备同步时间更新"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        device = Device.query.get(device_id)
        if not device:
            return jsonify({
                'error': 'Device Not Found',
                'message': '设备不存在',
                'status_code': 404
            }), 404
        
        # 权限检查
        if user.role != 'admin' and device.user_id != current_user_id:
            return jsonify({
                'error': 'Access Denied',
                'message': '无权操作此设备',
                'status_code': 403
            }), 403
        
        # 更新同步时间
        device.update_sync_time()
        
        return jsonify({
            'message': '设备同步时间更新成功',
            'device': device.to_dict(),
            'status_code': 200
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"设备同步错误: {str(e)}")
        return jsonify({
            'error': 'Device Sync Failed',
            'message': '设备同步时发生错误',
            'status_code': 500
        }), 500

@devices_bp.route('/by-device-id/<device_id_str>', methods=['GET'])
@jwt_required()
def get_device_by_device_id(device_id_str):
    """通过设备ID字符串获取设备信息"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        device = Device.query.filter_by(device_id=device_id_str).first()
        if not device:
            return jsonify({
                'error': 'Device Not Found',
                'message': '设备不存在',
                'status_code': 404
            }), 404
        
        # 权限检查
        if user.role != 'admin' and device.user_id != current_user_id:
            return jsonify({
                'error': 'Access Denied',
                'message': '无权访问此设备',
                'status_code': 403
            }), 403
        
        return jsonify({
            'device': device.to_dict(),
            'status_code': 200
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"通过设备ID获取设备错误: {str(e)}")
        return jsonify({
            'error': 'Device Fetch Failed',
            'message': '获取设备信息时发生错误',
            'status_code': 500
        }), 500

