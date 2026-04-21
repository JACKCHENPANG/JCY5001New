from datetime import datetime, date
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import and_, or_

from extensions import db
from models.user import User, Battery

batteries_bp = Blueprint('batteries', __name__)

@batteries_bp.route('/', methods=['GET'])
@jwt_required()
def get_batteries():
    """获取电池列表"""
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
        batch_number = request.args.get('batch_number')
        cell_type = request.args.get('cell_type')
        manufacturer = request.args.get('manufacturer')
        search = request.args.get('search')
        
        # 构建查询
        query = Battery.query
        
        # 批次号过滤
        if batch_number:
            query = query.filter(Battery.batch_number.ilike(f'%{batch_number}%'))
        
        # 电池类型过滤
        if cell_type and Battery.validate_cell_type(cell_type):
            query = query.filter(Battery.cell_type == cell_type)
        
        # 制造商过滤
        if manufacturer:
            query = query.filter(Battery.manufacturer.ilike(f'%{manufacturer}%'))
        
        # 搜索过滤
        if search:
            search_filter = or_(
                Battery.battery_id.ilike(f'%{search}%'),
                Battery.batch_number.ilike(f'%{search}%'),
                Battery.manufacturer.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        # 排序
        query = query.order_by(Battery.created_at.desc())
        
        # 分页
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        batteries = pagination.items
        
        return jsonify({
            'batteries': [battery.to_dict() for battery in batteries],
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
        current_app.logger.error(f"获取电池列表错误: {str(e)}")
        return jsonify({
            'error': 'Battery List Fetch Failed',
            'message': '获取电池列表时发生错误',
            'status_code': 500
        }), 500

@batteries_bp.route('/', methods=['POST'])
@jwt_required()
def create_battery():
    """创建新电池记录"""
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
        if not data.get('battery_id'):
            return jsonify({
                'error': 'Missing Required Field',
                'message': '电池ID是必需的',
                'status_code': 400
            }), 400
        
        battery_id = data['battery_id'].strip()
        batch_number = data.get('batch_number', '').strip()
        cell_type = data.get('cell_type', '').strip()
        nominal_capacity = data.get('nominal_capacity')
        nominal_voltage = data.get('nominal_voltage')
        manufacturer = data.get('manufacturer', '').strip()
        production_date_str = data.get('production_date')
        
        # 验证电池ID格式
        if len(battery_id) < 3 or len(battery_id) > 50:
            return jsonify({
                'error': 'Invalid Battery ID',
                'message': '电池ID长度必须在3-50个字符之间',
                'status_code': 400
            }), 400
        
        # 验证电池类型
        if cell_type and not Battery.validate_cell_type(cell_type):
            return jsonify({
                'error': 'Invalid Cell Type',
                'message': '电池类型必须是 LFP, NMC, LCO, NCA, LTO 之一',
                'status_code': 400
            }), 400
        
        # 验证容量和电压
        if nominal_capacity is not None:
            try:
                nominal_capacity = float(nominal_capacity)
                if nominal_capacity <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                return jsonify({
                    'error': 'Invalid Capacity',
                    'message': '标称容量必须是正数',
                    'status_code': 400
                }), 400
        
        if nominal_voltage is not None:
            try:
                nominal_voltage = float(nominal_voltage)
                if nominal_voltage <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                return jsonify({
                    'error': 'Invalid Voltage',
                    'message': '标称电压必须是正数',
                    'status_code': 400
                }), 400
        
        # 解析生产日期
        production_date = None
        if production_date_str:
            try:
                production_date = datetime.strptime(production_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'error': 'Invalid Date Format',
                    'message': '生产日期格式必须是 YYYY-MM-DD',
                    'status_code': 400
                }), 400
        
        # 检查电池ID是否已存在
        existing_battery = Battery.query.filter_by(battery_id=battery_id).first()
        if existing_battery:
            return jsonify({
                'error': 'Battery ID Exists',
                'message': '电池ID已存在',
                'status_code': 409
            }), 409
        
        # 创建新电池记录
        battery = Battery(
            battery_id=battery_id,
            batch_number=batch_number if batch_number else None,
            cell_type=cell_type if cell_type else None,
            nominal_capacity=nominal_capacity,
            nominal_voltage=nominal_voltage,
            manufacturer=manufacturer if manufacturer else None,
            production_date=production_date
        )
        
        db.session.add(battery)
        db.session.commit()
        
        return jsonify({
            'message': '电池记录创建成功',
            'battery': battery.to_dict(),
            'status_code': 201
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创建电池记录错误: {str(e)}")
        return jsonify({
            'error': 'Battery Creation Failed',
            'message': '创建电池记录时发生错误',
            'status_code': 500
        }), 500

@batteries_bp.route('/batch', methods=['POST'])
@jwt_required()
def create_batteries_batch():
    """批量创建电池记录"""
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
        
        if not data.get('batteries') or not isinstance(data['batteries'], list):
            return jsonify({
                'error': 'Invalid Data',
                'message': '请提供电池数据列表',
                'status_code': 400
            }), 400
        
        batteries_data = data['batteries']
        if len(batteries_data) > 1000:  # 限制批量创建数量
            return jsonify({
                'error': 'Too Many Records',
                'message': '单次最多创建1000条电池记录',
                'status_code': 400
            }), 400
        
        created_batteries = []
        errors = []
        
        for i, battery_data in enumerate(batteries_data):
            try:
                # 验证必需字段
                if not battery_data.get('battery_id'):
                    errors.append(f"第{i+1}条记录：电池ID是必需的")
                    continue
                
                battery_id = battery_data['battery_id'].strip()
                
                # 检查电池ID是否已存在
                existing_battery = Battery.query.filter_by(battery_id=battery_id).first()
                if existing_battery:
                    errors.append(f"第{i+1}条记录：电池ID {battery_id} 已存在")
                    continue
                
                # 解析生产日期
                production_date = None
                if battery_data.get('production_date'):
                    try:
                        production_date = datetime.strptime(
                            battery_data['production_date'], '%Y-%m-%d'
                        ).date()
                    except ValueError:
                        errors.append(f"第{i+1}条记录：生产日期格式错误")
                        continue
                
                # 创建电池记录
                battery = Battery(
                    battery_id=battery_id,
                    batch_number=battery_data.get('batch_number'),
                    cell_type=battery_data.get('cell_type'),
                    nominal_capacity=battery_data.get('nominal_capacity'),
                    nominal_voltage=battery_data.get('nominal_voltage'),
                    manufacturer=battery_data.get('manufacturer'),
                    production_date=production_date
                )
                
                db.session.add(battery)
                created_batteries.append(battery)
                
            except Exception as e:
                errors.append(f"第{i+1}条记录：{str(e)}")
        
        if created_batteries:
            db.session.commit()
        
        return jsonify({
            'message': f'批量创建完成，成功创建 {len(created_batteries)} 条记录',
            'created_count': len(created_batteries),
            'error_count': len(errors),
            'errors': errors,
            'batteries': [battery.to_dict() for battery in created_batteries],
            'status_code': 201 if created_batteries else 400
        }), 201 if created_batteries else 400
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"批量创建电池记录错误: {str(e)}")
        return jsonify({
            'error': 'Batch Creation Failed',
            'message': '批量创建电池记录时发生错误',
            'status_code': 500
        }), 500

@batteries_bp.route('/<int:battery_id>', methods=['GET'])
@jwt_required()
def get_battery(battery_id):
    """获取单个电池信息"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        battery = Battery.query.get(battery_id)
        if not battery:
            return jsonify({
                'error': 'Battery Not Found',
                'message': '电池记录不存在',
                'status_code': 404
            }), 404
        
        # 获取电池的测试统计信息
        from models.user import TestResult
        total_tests = TestResult.query.filter_by(battery_id=battery.id).count()
        pass_tests = TestResult.query.filter_by(
            battery_id=battery.id, test_result='pass'
        ).count()
        
        battery_data = battery.to_dict()
        battery_data['statistics'] = {
            'total_tests': total_tests,
            'pass_tests': pass_tests,
            'pass_rate': round(pass_tests / total_tests * 100, 2) if total_tests > 0 else 0
        }
        
        return jsonify({
            'battery': battery_data,
            'status_code': 200
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取电池信息错误: {str(e)}")
        return jsonify({
            'error': 'Battery Fetch Failed',
            'message': '获取电池信息时发生错误',
            'status_code': 500
        }), 500

@batteries_bp.route('/<int:battery_id>', methods=['PUT'])
@jwt_required()
def update_battery(battery_id):
    """更新电池信息"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        battery = Battery.query.get(battery_id)
        if not battery:
            return jsonify({
                'error': 'Battery Not Found',
                'message': '电池记录不存在',
                'status_code': 404
            }), 404
        
        data = request.get_json()
        
        # 更新允许的字段
        if 'batch_number' in data:
            battery.batch_number = data['batch_number'].strip() if data['batch_number'] else None
        
        if 'cell_type' in data:
            cell_type = data['cell_type'].strip() if data['cell_type'] else None
            if cell_type and not Battery.validate_cell_type(cell_type):
                return jsonify({
                    'error': 'Invalid Cell Type',
                    'message': '电池类型必须是 LFP, NMC, LCO, NCA, LTO 之一',
                    'status_code': 400
                }), 400
            battery.cell_type = cell_type
        
        if 'nominal_capacity' in data:
            if data['nominal_capacity'] is not None:
                try:
                    nominal_capacity = float(data['nominal_capacity'])
                    if nominal_capacity <= 0:
                        raise ValueError()
                    battery.nominal_capacity = nominal_capacity
                except (ValueError, TypeError):
                    return jsonify({
                        'error': 'Invalid Capacity',
                        'message': '标称容量必须是正数',
                        'status_code': 400
                    }), 400
            else:
                battery.nominal_capacity = None
        
        if 'nominal_voltage' in data:
            if data['nominal_voltage'] is not None:
                try:
                    nominal_voltage = float(data['nominal_voltage'])
                    if nominal_voltage <= 0:
                        raise ValueError()
                    battery.nominal_voltage = nominal_voltage
                except (ValueError, TypeError):
                    return jsonify({
                        'error': 'Invalid Voltage',
                        'message': '标称电压必须是正数',
                        'status_code': 400
                    }), 400
            else:
                battery.nominal_voltage = None
        
        if 'manufacturer' in data:
            battery.manufacturer = data['manufacturer'].strip() if data['manufacturer'] else None
        
        if 'production_date' in data:
            if data['production_date']:
                try:
                    battery.production_date = datetime.strptime(
                        data['production_date'], '%Y-%m-%d'
                    ).date()
                except ValueError:
                    return jsonify({
                        'error': 'Invalid Date Format',
                        'message': '生产日期格式必须是 YYYY-MM-DD',
                        'status_code': 400
                    }), 400
            else:
                battery.production_date = None
        
        battery.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': '电池信息更新成功',
            'battery': battery.to_dict(),
            'status_code': 200
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新电池信息错误: {str(e)}")
        return jsonify({
            'error': 'Battery Update Failed',
            'message': '更新电池信息时发生错误',
            'status_code': 500
        }), 500

@batteries_bp.route('/<int:battery_id>', methods=['DELETE'])
@jwt_required()
def delete_battery(battery_id):
    """删除电池记录"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        # 只有管理员可以删除电池记录
        if user.role != 'admin':
            return jsonify({
                'error': 'Access Denied',
                'message': '只有管理员可以删除电池记录',
                'status_code': 403
            }), 403
        
        battery = Battery.query.get(battery_id)
        if not battery:
            return jsonify({
                'error': 'Battery Not Found',
                'message': '电池记录不存在',
                'status_code': 404
            }), 404
        
        # 检查是否有关联的测试数据
        from models.user import TestResult
        test_count = TestResult.query.filter_by(battery_id=battery.id).count()
        if test_count > 0:
            return jsonify({
                'error': 'Battery Has Test Data',
                'message': f'电池有 {test_count} 条测试记录，无法删除。请先删除相关测试数据。',
                'status_code': 409
            }), 409
        
        db.session.delete(battery)
        db.session.commit()
        
        return jsonify({
            'message': '电池记录删除成功',
            'status_code': 200
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除电池记录错误: {str(e)}")
        return jsonify({
            'error': 'Battery Deletion Failed',
            'message': '删除电池记录时发生错误',
            'status_code': 500
        }), 500

@batteries_bp.route('/by-battery-id/<battery_id_str>', methods=['GET'])
@jwt_required()
def get_battery_by_battery_id(battery_id_str):
    """通过电池ID字符串获取电池信息"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        battery = Battery.query.filter_by(battery_id=battery_id_str).first()
        if not battery:
            return jsonify({
                'error': 'Battery Not Found',
                'message': '电池记录不存在',
                'status_code': 404
            }), 404
        
        return jsonify({
            'battery': battery.to_dict(),
            'status_code': 200
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"通过电池ID获取电池错误: {str(e)}")
        return jsonify({
            'error': 'Battery Fetch Failed',
            'message': '获取电池信息时发生错误',
            'status_code': 500
        }), 500

